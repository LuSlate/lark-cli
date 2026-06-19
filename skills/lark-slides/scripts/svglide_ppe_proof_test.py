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
            write_json(
                project / "07-create/ppe-proof.input.json",
                {
                    "status": "passed",
                    "environment": {"name": "Pre_release", "x-tt-env": "ppe_pure_svg"},
                    "auth": {"identity": "user"},
                    "proxy": {"mode": "whistle"},
                    "headers": {"x-tt-env": "ppe_pure_svg"},
                    "route": {"name": "slides +create-svg"},
                },
            )

            result = svglide_ppe_proof.run_ppe_proof(project)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project / "07-create/ppe-proof.json").exists())


if __name__ == "__main__":
    unittest.main()
