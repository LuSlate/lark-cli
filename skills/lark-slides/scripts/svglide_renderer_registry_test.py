# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import svglide_renderer_registry as registry


class SVGlideRendererRegistryTest(unittest.TestCase):
    def test_registry_validates_active_renderers_against_catalogs(self) -> None:
        report = registry.validate_registry(registry.load_registry(), registry.load_catalog_ids())

        self.assertEqual("passed", report["status"])
        self.assertGreaterEqual(report["summary"]["active_count"], 10)
        self.assertGreaterEqual(report["summary"]["active_page_kind_count"], 10)
        self.assertEqual(0, report["summary"]["error_count"])

    def test_registry_has_no_external_reference_project_words(self) -> None:
        encoded = json.dumps(registry.load_registry(), ensure_ascii=False).lower()
        banned_tokens = [
            "ppt" + "-master",
            "ppt" + "_master",
            "ppt" + " master",
            "hugo" + "he3",
            "ppt" + "169",
        ]

        for token in banned_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, encoded)

    def test_cli_json_report(self) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = registry.main(["--json"])

        self.assertEqual(0, exit_code)
        report = json.loads(stdout.getvalue())
        self.assertEqual("svglide-renderer-registry/v1", report["schema_version"])
        self.assertEqual("passed", report["status"])


if __name__ == "__main__":
    unittest.main()
