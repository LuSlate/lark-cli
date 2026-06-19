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

import svglide_readback


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideReadbackTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        (project / "07-create").mkdir(parents=True)
        return project

    def completed(self, payload: dict[str, object], returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["lark-cli"], returncode, stdout=json.dumps(payload), stderr="")

    def test_readback_passes_when_page_count_and_slide_ids_match(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}, {"page": 2}]})
        write_json(project / "06-check/quality-gate.json", {"status": "passed"})
        write_json(project / "07-create/dry-run.json", {"status": "passed"})
        write_json(project / "07-create/ppe-proof.json", {"status": "passed"})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "revision_id": "rev_1", "slide_ids": ["s1", "s2"]})

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1"}, {"id": "s2"}]}}),
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checks"]["page_count"]["status"], "passed")
        self.assertEqual(result["checks"]["asset_tokens"]["status"], "skipped")
        self.assertEqual(result["input_binding"]["revision_id"], "rev_1")
        self.assertEqual(result["input_binding"]["expected_slide_count"], 2)
        self.assertEqual(result["input_binding"]["created_slide_count"], 2)
        self.assertIsNotNone(result["input_binding"]["plan_sha256"])
        self.assertIsNotNone(result["input_binding"]["quality_gate_sha256"])
        self.assertIsNotNone(result["input_binding"]["dry_run_sha256"])
        self.assertIsNotNone(result["input_binding"]["ppe_proof_sha256"])
        self.assertIsNotNone(result["input_binding"]["live_create_sha256"])
        self.assertTrue((project / "08-readback/readback-check.json").exists())

    def test_readback_fails_without_presentation_id(self) -> None:
        project = self.make_project()
        write_json(project / "07-create/live-create.json", {"slide_ids": ["s1"]})

        result = svglide_readback.run_readback(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("presentation_id", result["failed_checks"])

    def test_readback_fails_on_page_count_mismatch(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"svg_files": [{"page": 1}, {"page": 2}]})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "slide_ids": ["s1", "s2"]})

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1"}]}}),
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["page_count"]["status"], "failed")

    def test_readback_checks_expected_asset_tokens(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}]})
        write_json(project / "03-assets/assets.json", {"@./hero.png": "boxcn_hero"})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]})

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1", "image": "boxcn_hero"}]}}),
        )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checks"]["asset_tokens"]["status"], "passed")

    def test_readback_fails_when_business_claim_is_missing(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}], "business_claims": [{"fragment": "Revenue 130.5B"}]})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]})

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1", "text": "Revenue"}]}}),
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["business_claims"]["status"], "failed")

    def test_readback_fails_when_text_overflow_marker_is_present(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}]})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]})

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1", "text_overflow": True}]}}),
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["text_fit"]["status"], "failed")

    def test_readback_fails_when_expected_chart_marker_is_missing(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}]})
        write_json(project / "07-create/live-create.json", {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]})
        (project / "04-svg/prepared").mkdir(parents=True, exist_ok=True)
        (project / "04-svg/prepared/page-001.svg").write_text('<svg><g slide:role="chart"></g></svg>', encoding="utf-8")

        result = svglide_readback.run_readback(
            project,
            command_runner=lambda *args, **kwargs: self.completed({"data": {"slides": [{"id": "s1"}]}}),
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["chart_markers"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
