#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_artboard_package_check as package_check


class ArtboardPackageCheckTest(unittest.TestCase):
    def test_structural_check_passes_current_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = package_check.inspect_artboard_package(run_runtime=False)
            package_check.write_check_outputs(Path(tmp), payload)
            self.assertEqual(payload["status"], "passed", payload["issues"])
            self.assertEqual(payload["stage"], "package_check")
            self.assertEqual(payload["action"], "create_live")
            self.assertEqual(payload["summary"]["error_count"], 0)
            self.assertFalse(payload["dependency_policy"]["manual_satori_source_checkout_required"])
            self.assertTrue(payload["distribution_decision"]["runtime_requires_native_resvg_install"])
            self.assertTrue((Path(tmp) / package_check.PACKAGE_CHECK).exists())
            self.assertTrue((Path(tmp) / package_check.PACKAGE_RECEIPT).exists())

    def test_dependency_policy_rejects_file_dependency(self) -> None:
        package = {
            "dependencies": {
                "satori": "file:../../satori",
                "@resvg/resvg-js": "2.6.2",
            }
        }
        issues = package_check.validate_dependency_policy(package, "satori@file:../../satori\n@resvg/resvg-js@2.6.2")
        codes = {issue["code"] for issue in issues}
        self.assertIn("package_dependency_version_mismatch", codes)
        self.assertIn("package_local_dependency", codes)
        self.assertIn("lockfile_local_dependency", codes)

    def test_embed_policy_rejects_broad_scripts_directory(self) -> None:
        embed_text = """
//go:embed skills/*/SKILL.md skills/*/references
//go:embed skills/*/scripts skills/*/scripts/artboard_renderer/node_modules
var skillsEmbedFS embed.FS
"""
        issues = package_check.validate_embed_policy(embed_text)
        codes = {issue["code"] for issue in issues}
        self.assertIn("go_embed_forbidden_broad_pattern", codes)
        self.assertIn("go_embed_node_modules", codes)
        self.assertIn("go_embed_missing_pattern", codes)

    def test_runtime_check_payload_shape_from_fixture(self) -> None:
        payload = {
            "version": package_check.CHECK_VERSION,
            "stage": "package_check",
            "status": "passed",
            "action": "create_live",
            "summary": {"error_count": 0},
            "runtime_checks": [
                {
                    "passed": True,
                    "payload": {
                        "ok": True,
                        "renderer": "satori-resvg",
                        "satori_version": "0.26.0",
                        "resvg_version": "2.6.2",
                    },
                }
            ],
        }
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["runtime_checks"][0]["payload"]["renderer"], "satori-resvg")

    def test_required_x64_host_blocks_on_arm64_host(self) -> None:
        with mock.patch.object(package_check.platform, "system", return_value="Darwin"), mock.patch.object(package_check.platform, "machine", return_value="arm64"):
            payload = package_check.inspect_artboard_package(run_runtime=False, require_system="Darwin", require_arch="x64")

        self.assertEqual(payload["status"], "blocked", payload["issues"])
        self.assertEqual(payload["host"]["normalized_arch"], "arm64")
        self.assertEqual(payload["host_requirements"]["required_arch"], "x64")
        self.assertEqual(payload["blockers"][0]["code"], "runtime_host_arch_mismatch")

    def test_required_x64_host_passes_requirement_on_x86_64_host(self) -> None:
        with mock.patch.object(package_check.platform, "system", return_value="Darwin"), mock.patch.object(package_check.platform, "machine", return_value="x86_64"):
            payload = package_check.inspect_artboard_package(run_runtime=False, require_system="Darwin", require_arch="x64")

        self.assertEqual(payload["status"], "passed", payload["issues"])
        self.assertEqual(payload["host"]["normalized_arch"], "x64")
        self.assertEqual(payload["host_requirements"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
