#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_instruction_adherence as adherence


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_happy_project(project: Path) -> None:
    write_json(
        project / adherence.INSTRUCTION_FILE,
        {
            "version": "svglide-instruction/v1",
            "language": "zh-CN",
            "target_slide_count": 1,
            "must_include": ["冰岛火山研究"],
            "must_avoid": ["自由 HTML"],
            "slides": [
                {
                    "page": 1,
                    "title": "冰岛火山研究",
                    "key_message": "不编造具体数值",
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                    "required_text": ["冰岛火山研究"],
                }
            ],
            "explicit_constraints": [
                {
                    "id": "no_metrics",
                    "required_plan_text": ["不编造具体数值"],
                    "required_output_text": ["不编造具体数值"],
                    "required_readback_text": ["不编造具体数值"],
                }
            ],
            "repair_policy": {"target_plan_path": "02-plan/slide_plan.json", "allowed_path_prefixes": ["/slides/"]},
        },
    )
    for rel in (adherence.DECK_PLAN, adherence.SLIDE_PLAN):
        write_json(
            project / rel,
            {
                "target_slide_count": 1,
                "slides": [
                    {
                        "page": 1,
                        "title": "冰岛火山研究",
                        "key_message": "不编造具体数值",
                        "template_id": "cover-hero",
                        "theme_id": "dark-clarity",
                    }
                ],
            },
        )
    write_json(
        project / adherence.CANVAS_PLAN,
        {
            "target_slide_count": 1,
            "slides": [
                {
                    "page": 1,
                    "title": "冰岛火山研究",
                    "key_message": "不编造具体数值",
                    "canvas_spec": {
                        "template_id": "cover-hero",
                        "theme_id": "dark-clarity",
                        "content": {"title": "冰岛火山研究", "note": "不编造具体数值"},
                    },
                }
            ],
        },
    )
    (project / "04-svg").mkdir(parents=True)
    (project / "04-svg/page-001.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>冰岛火山研究 不编造具体数值</text></svg>',
        encoding="utf-8",
    )
    write_json(
        project / adherence.READBACK_CHECK,
        {
            "status": "passed",
            "checks": {
                "page_count": {"status": "passed", "actual": 1},
                "slide_order": {"status": "passed", "actual": ["s1"], "expected": ["s1"]},
                "core_visible_text": {"status": "passed", "missing": []},
            },
        },
    )
    write_json(
        project / adherence.READBACK_RAW,
        {
            "json": {
                "data": {
                    "xml_presentation": {
                        "content": '<presentation><slide id="s1"><shape type="text"><content>冰岛火山研究 不编造具体数值</content></shape></slide></presentation>'
                    }
                }
            }
        },
    )


class InstructionAdherenceTest(unittest.TestCase):
    def test_contains_text_ignores_spacing(self) -> None:
        self.assertTrue(adherence.contains_text(["冰岛 火山 研究"], "冰岛火山"))
        self.assertFalse(adherence.contains_text(["火山研究"], "连续监测"))

    def test_repair_scope_rejects_broad_object_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            write_json(
                project / adherence.REPAIR_PLAN,
                {
                    "target_plan_path": "02-plan/slide_plan.json",
                    "patches": [
                        {"op": "replace", "path": "/slides/0/canvas_spec/content", "value": {"title": "bad"}}
                    ],
                },
            )
            issues, scope = adherence.validate_repair_scope(
                project,
                {
                    "repair_policy": {
                        "target_plan_path": "02-plan/slide_plan.json",
                        "allowed_path_prefixes": ["/slides/"],
                    }
                },
            )
            codes = {issue["code"] for issue in issues}
            self.assertIn("repair_patch_too_broad", codes)
            self.assertIn("repair_patch_value_too_broad", codes)
            self.assertEqual(scope["patch_count"], 1)

    def test_validate_instruction_adherence_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            payload = adherence.validate_instruction_adherence(project)
            self.assertEqual(payload["status"], "passed", payload["issues"])
            adherence.write_check_outputs(project, payload)
            self.assertTrue((project / adherence.CHECK_PATH).exists())
            self.assertTrue((project / adherence.RECEIPT_PATH).exists())

    def test_slide_count_drift_fails_with_scoped_repair_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            deck_plan = json.loads((project / adherence.DECK_PLAN).read_text(encoding="utf-8"))
            deck_plan["slides"] = []
            write_json(project / adherence.DECK_PLAN, deck_plan)

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            strategies = {item["strategy"] for item in payload["repair_recommendations"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("planner_slide_count_mismatch", codes)
            self.assertIn("scoped_append_or_delete_page", strategies)

    def test_missing_canvas_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            canvas_plan = json.loads((project / adherence.CANVAS_PLAN).read_text(encoding="utf-8"))
            canvas_plan["slides"] = []
            write_json(project / adherence.CANVAS_PLAN, canvas_plan)

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("plan_slides_missing", codes)
            self.assertIn("plan_slide_count_mismatch", codes)

    def test_missing_slide_plan_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            slide_plan = json.loads((project / adherence.SLIDE_PLAN).read_text(encoding="utf-8"))
            slide_plan["slides"] = []
            write_json(project / adherence.SLIDE_PLAN, slide_plan)

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            strategies = {item["strategy"] for item in payload["repair_recommendations"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("planner_slide_count_mismatch", codes)
            self.assertIn("scoped_append_or_delete_page", strategies)

    def test_final_slide_key_message_drift_fails_even_with_fresh_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            canvas_plan = json.loads((project / adherence.CANVAS_PLAN).read_text(encoding="utf-8"))
            canvas_plan["slides"][0]["key_message"] = "漂移后的错误 key message"
            write_json(project / adherence.CANVAS_PLAN, canvas_plan)
            readback_check = json.loads((project / adherence.READBACK_CHECK).read_text(encoding="utf-8"))
            readback_check["input_binding"] = {"plan_sha256": adherence.file_sha256(project / adherence.CANVAS_PLAN)}
            write_json(project / adherence.READBACK_CHECK, readback_check)

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("page_key_message_mismatch", codes)

    def test_forbidden_text_in_output_or_readback_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            (project / "04-svg/page-001.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><text>冰岛火山研究 自由 HTML</text></svg>',
                encoding="utf-8",
            )

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("must_avoid_present_in_output", codes)

    def test_readback_binding_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            make_happy_project(project)
            readback_check = json.loads((project / adherence.READBACK_CHECK).read_text(encoding="utf-8"))
            readback_check["input_binding"] = {"plan_sha256": "stale"}
            write_json(project / adherence.READBACK_CHECK, readback_check)

            payload = adherence.validate_instruction_adherence(project)
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertEqual(payload["status"], "failed")
            self.assertIn("readback_binding_hash_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
