#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_model_repair_loop as repair_loop
import svglide_project_runner as runner
import svglide_prompt_planner as prompt_planner


class SVGlideModelRepairLoopTest(unittest.TestCase):
    def fixture_dir(self) -> Path:
        return Path(__file__).resolve().parent / "fixtures/svglide_artboard/followup_model_loop"

    def fixture_provider_command(self) -> str:
        provider = self.fixture_dir() / "fixture_model_provider.py"
        return f"{sys.executable} {provider} --stage {{stage}} --raw-output {{raw_output}}"

    def create_model_generated_project(self, tmpdir: str) -> Path:
        topic = json.loads((self.fixture_dir() / "topic.json").read_text(encoding="utf-8"))
        plan_root = Path(tmpdir) / ".lark-slides/plan"
        result = runner.init_project("followup-model-loop", "Followup Model Loop", plan_root=plan_root)
        project = Path(result["project_root"])
        prompt_planner.run_prompt_plan(
            project,
            prompt=str(topic["prompt"]),
            target_slide_count=int(topic["target_slide_count"]),
            language=str(topic["language"]),
            audience=str(topic["audience"]),
            provider="command",
            planner_command=self.fixture_provider_command(),
        )
        return project

    def install_repair_inputs(self, project: Path, repair_fixture: str) -> None:
        (project / "06-check").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.fixture_dir() / "failing-receipt.json", project / "06-check/preflight.json")
        shutil.copyfile(self.fixture_dir() / repair_fixture, project / "02-plan/repair-plan.json")

    def test_scoped_json_patch_updates_slide_plan_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.create_model_generated_project(tmpdir)
            self.install_repair_inputs(project, "repair-plan.scoped.json")
            before_hash = runner.file_sha256(project / "02-plan/slide_plan.json")

            receipt = repair_loop.run_repair_loop(project, failing_receipt=Path("06-check/preflight.json"))

            self.assertEqual("passed", receipt["status"])
            self.assertEqual(2, receipt["summary"]["patch_count"])
            self.assertTrue(receipt["summary"]["scoped_patch_only"])
            self.assertEqual(before_hash, receipt["inputs"]["plan_sha256"])
            self.assertNotEqual(before_hash, receipt["outputs"]["plan_sha256"])
            updated = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            self.assertEqual("SpaceX IPO 框架", updated["slides"][0]["canvas_spec"]["content"]["title"])
            self.assertEqual("SpaceX IPO 分析框架", updated["slides"][0]["title"])
            self.assertTrue((project / "receipts/repair-loop.json").exists())

    def test_broad_object_rewrite_is_rejected_without_changing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.create_model_generated_project(tmpdir)
            self.install_repair_inputs(project, "repair-plan.broad.json")
            before_hash = runner.file_sha256(project / "02-plan/slide_plan.json")

            with self.assertRaisesRegex(repair_loop.RepairLoopError, "broad|scalar|whole object/list"):
                repair_loop.run_repair_loop(project, failing_receipt=Path("06-check/preflight.json"))

            self.assertEqual(before_hash, runner.file_sha256(project / "02-plan/slide_plan.json"))
            failed = json.loads((project / "receipts/repair-loop.json").read_text(encoding="utf-8"))
            self.assertEqual("failed", failed["status"])
            self.assertEqual(1, failed["summary"]["error_count"])

    def test_runner_stage_repair_loop_uses_fixture_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.create_model_generated_project(tmpdir)
            self.install_repair_inputs(project, "repair-plan.scoped.json")

            result = runner.run_stage(project, "repair-loop")

            self.assertEqual("passed", result["status"])
            state = runner.load_state(project)
            self.assertEqual("passed", state["stages"]["repair_loop"]["status"])
            receipt = json.loads((project / "receipts/repair-loop.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", receipt["status"])


if __name__ == "__main__":
    unittest.main()
