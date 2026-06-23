# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import subprocess
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
    def completed(self, command: list[str], payload: dict[str, object] | None = None, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=json.dumps(payload or {"ok": True}), stderr=stderr)

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
                "inject_headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg", "x-use-ppe": "1"},
            },
            "headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg", "x-use-ppe": "1"},
            "route": {"name": "slides +create-svg"},
        }

    def test_ppe_proof_requires_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)

            result = svglide_ppe_proof.run_ppe_proof(project, command_runner=lambda command, **_: self.completed(command))

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["issues"][0]["code"], "ppe_proof_input_missing")

    def test_ppe_proof_passes_complete_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            write_json(project / "07-create/ppe-proof.input.json", self.complete_proof_input(project))
            commands: list[list[str]] = []

            def fake(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                return self.completed(command)

            result = svglide_ppe_proof.run_ppe_proof(project, command_runner=fake)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project / "07-create/ppe-proof.json").exists())
            self.assertEqual(result["ppe_create_probe"]["status"], "create_route_passed")
            self.assertIn("--ppe-profile", commands[0])
            self.assertIn("ppe_pure_svg", commands[0])
            self.assertNotIn("--request-header", commands[0])

    def test_ppe_proof_rejects_missing_proxy_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            proof = self.complete_proof_input(project)
            proxy = proof["proxy"]
            assert isinstance(proxy, dict)
            proxy.pop("capture")
            write_json(project / "07-create/ppe-proof.input.json", proof)

            result = svglide_ppe_proof.run_ppe_proof(project, command_runner=lambda command, **_: self.completed(command))

            self.assertEqual(result["status"], "failed")
            self.assertIn("ppe_proxy_capture_missing", [item["code"] for item in result["issues"]])

    def test_ppe_proof_rejects_incomplete_fixed_header_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            proof = self.complete_proof_input(project)
            headers = proof["headers"]
            proxy = proof["proxy"]
            assert isinstance(headers, dict)
            assert isinstance(proxy, dict)
            headers.pop("x-use-ppe")
            inject_headers = proxy["inject_headers"]
            assert isinstance(inject_headers, dict)
            inject_headers.pop("x-use-ppe")
            write_json(project / "07-create/ppe-proof.input.json", proof)

            result = svglide_ppe_proof.run_ppe_proof(project, command_runner=lambda command, **_: self.completed(command))

            codes = [item["code"] for item in result["issues"]]
            self.assertEqual(result["status"], "failed")
            self.assertIn("ppe_header_missing_x_use_ppe", codes)
            self.assertIn("ppe_proxy_x_use_ppe_header_missing", codes)

    def test_ppe_proof_rejects_rule_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            self.write_inputs(project)
            proof = self.complete_proof_input(project)
            proxy = proof["proxy"]
            assert isinstance(proxy, dict)
            proxy["rule_sha256"] = "not-the-real-hash"
            write_json(project / "07-create/ppe-proof.input.json", proof)

            result = svglide_ppe_proof.run_ppe_proof(project, command_runner=lambda command, **_: self.completed(command))

            self.assertEqual(result["status"], "failed")
            self.assertIn("ppe_proxy_rule_sha256_mismatch", [item["code"] for item in result["issues"]])

    def test_image_probe_classifies_5090000_as_readback_blocked(self) -> None:
        completed = subprocess.CompletedProcess(
            ["lark-cli"],
            1,
            stdout="",
            stderr="nodeServer internal error [5090000]",
        )

        status, detail = svglide_ppe_proof.classify_image_probe(completed)

        self.assertEqual(status, "readback_blocked")
        self.assertEqual(detail["classification"], "nodeserver_5090000")
        self.assertNotEqual(detail["classification"], "api_error")


if __name__ == "__main__":
    unittest.main()
