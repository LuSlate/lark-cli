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

import svglide_planner_contracts as planner


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class SVGlidePlannerContractsTest(unittest.TestCase):
    def copy_fixture(self, tmpdir: str) -> Path:
        source = Path(__file__).resolve().parent / "fixtures/svglide_artboard/gate10_planner"
        target = Path(tmpdir) / "gate10_planner"
        shutil.copytree(source, target)
        return target

    def test_gate10_planner_fixture_passes_contracts_and_canvas_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.copy_fixture(tmpdir)

            result = planner.run(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["prompt_contract_count"], 4)
            self.assertEqual(result["summary"]["planner_output_count"], 4)
            self.assertEqual([], result["issues"])
            self.assertTrue((project / "06-check/planner-contract-check.json").exists())
            self.assertTrue((project / "receipts/planner-contract-check.json").exists())
            outputs = {item["prompt_id"]: item for item in result["planner_outputs"]}
            self.assertEqual(0, outputs["canvas-planner"]["error_count"])
            self.assertEqual("02-plan/slide_plan.json", outputs["canvas-planner"]["output_path"])

    def test_rejects_free_html_css_svg_markup_in_planner_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.copy_fixture(tmpdir)
            deck_plan_path = project / "02-plan/deck-plan.json"
            deck_plan = read_json(deck_plan_path)
            deck_plan["objective"] = "<div class=\"poster\">bad free markup</div>"
            write_json(deck_plan_path, deck_plan)

            result = planner.run(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("planner_output_forbidden_markup", codes)

    def test_rejects_unscoped_repair_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.copy_fixture(tmpdir)
            repair_path = project / "02-plan/repair-plan.json"
            repair_plan = read_json(repair_path)
            repair_plan["patches"] = [{"op": "replace", "path": "/slides", "value": [], "reason": "too broad"}]
            write_json(repair_path, repair_plan)

            result = planner.run(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("repair_patch_unscoped", codes)

    def test_rejects_unregistered_slide_plan_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.copy_fixture(tmpdir)
            slide_plan_path = project / "02-plan/slide-plan.json"
            slide_plan = read_json(slide_plan_path)
            slide_plan["slides"][0]["template_id"] = "missing-template"
            write_json(slide_plan_path, slide_plan)

            result = planner.run(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("slide_plan_template_unknown", codes)

    def test_rejects_broad_repair_content_object_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.copy_fixture(tmpdir)
            repair_path = project / "02-plan/repair-plan.json"
            repair_plan = read_json(repair_path)
            repair_plan["patches"] = [
                {
                    "op": "replace",
                    "path": "/slides/0/canvas_spec/content",
                    "value": {"title": "whole object rewrite"},
                    "reason": "too broad",
                }
            ]
            write_json(repair_path, repair_plan)

            result = planner.run(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("repair_patch_broad_path", codes)
            self.assertIn("repair_patch_value_too_broad", codes)


if __name__ == "__main__":
    unittest.main()
