# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_ppe_proof


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlidePPEProofTest(unittest.TestCase):
    def write_inputs(self, project: Path) -> None:
        write_json(project / "06-check/quality-gate.json", {"status": "passed"})
        write_json(project / "07-create/dry-run.json", {"status": "passed"})

    def write_rule(self, project: Path) -> Path:
        rule = project / "ppe-pure-svg.whistle.js"
        rule.write_text("module.exports = function () {}\n", encoding="utf-8")
        return rule

    def complete_proof_input(self, project: Path) -> dict[str, object]:
        rule = self.write_rule(project)
        return {
            "status": "passed",
            "environment": {"name": "Pre_release", "x-tt-env": "ppe_pure_svg"},
            "auth": {"identity": "user"},
            "proxy": {
                "mode": "whistle",
                "capture": True,
                "http_proxy": "http://127.0.0.1:8899",
                "https_proxy": "http://127.0.0.1:8899",
                "rewrite_host": "open.feishu-pre.cn",
                "rule_file": rule.name,
                "rule_sha256": svglide_ppe_proof.file_sha256(rule),
                "inject_headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
            },
            "headers": {"x-tt-env": "ppe_pure_svg"},
            "route": {"name": "slides +create-svg"},
        }

    def test_ppe_proof_requires_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)

            result = svglide_ppe_proof.run_ppe_proof(project)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["issues"][0]["code"], "ppe_proof_input_missing")

    def test_ppe_proof_passes_complete_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            write_json(project / "07-create/ppe-proof.input.json", self.complete_proof_input(project))

            result = svglide_ppe_proof.run_ppe_proof(project)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project / "07-create/ppe-proof.json").exists())

    def test_ppe_proof_rejects_missing_proxy_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            proof = self.complete_proof_input(project)
            proxy = proof["proxy"]
            assert isinstance(proxy, dict)
            proxy.pop("capture")
            write_json(project / "07-create/ppe-proof.input.json", proof)

            result = svglide_ppe_proof.run_ppe_proof(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("ppe_proxy_capture_missing", [item["code"] for item in result["issues"]])

    def test_ppe_proof_rejects_rule_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            proof = self.complete_proof_input(project)
            proxy = proof["proxy"]
            assert isinstance(proxy, dict)
            proxy["rule_sha256"] = "not-the-real-hash"
            write_json(project / "07-create/ppe-proof.input.json", proof)

            result = svglide_ppe_proof.run_ppe_proof(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("ppe_proxy_rule_sha256_mismatch", [item["code"] for item in result["issues"]])


if __name__ == "__main__":
    unittest.main()
