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

import svglide_semantic_review


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "svglide_semantic_review"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SVGlideSemanticReviewTest(unittest.TestCase):
    def make_valid_project(self, root: Path) -> Path:
        project = root / "valid"
        write_json(
            project / "02-plan/slide_plan.json",
            {
                "language": "zh-CN",
                "audience": "企业管理层",
                "deck_structure": ["cover", "content", "closing"],
                "slides": [
                    {
                        "page": 1,
                        "page_type": "cover",
                        "section": "开场",
                        "role": "thesis",
                        "title": "英伟达供应链拐点",
                        "key_message": "供应链正在从图形芯片转向 AI 基础设施",
                        "body_points": ["面向管理层的中文汇报", "聚焦产能与交付风险"],
                        "source_refs": ["source:item-001"],
                    },
                    {
                        "page": 2,
                        "page_type": "content",
                        "section": "供需判断",
                        "role": "evidence",
                        "title": "需求增长压缩交付窗口",
                        "key_message": "关键瓶颈来自先进封装与高带宽内存协同",
                        "body_points": ["订单节奏提前暴露产能缺口", "交付稳定性决定客户扩容节奏"],
                        "source_refs": ["source:item-001"],
                    },
                    {
                        "page": 3,
                        "page_type": "closing",
                        "section": "结论",
                        "role": "takeaway",
                        "title": "结论与行动",
                        "key_message": "下一步应优先跟踪产能、交付和客户集中度",
                        "body_points": ["跟踪先进封装产能变化", "复核主要客户交付节奏"],
                        "source_refs": ["source:item-001"],
                    },
                ],
            },
        )
        write_json(
            project / "source/evidence.json",
            {
                "schema_version": "svglide-evidence/v1",
                "source_status": "ready",
                "items": [
                    {
                        "id": "item-001",
                        "text": "先进封装与高带宽内存协同影响 AI 基础设施交付稳定性",
                        "source": "source-notes.md",
                    }
                ],
            },
        )
        prepared = project / "04-svg/prepared"
        prepared.mkdir(parents=True)
        (prepared / "page-001.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>英伟达供应链拐点</text><text>供应链正在从图形芯片转向 AI 基础设施</text></svg>',
            encoding="utf-8",
        )
        (prepared / "page-002.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>需求增长压缩交付窗口</text><text>订单节奏提前暴露产能缺口</text></svg>',
            encoding="utf-8",
        )
        (prepared / "page-003.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>结论与行动</text><text>跟踪先进封装产能变化</text></svg>',
            encoding="utf-8",
        )
        return project

    def test_semantic_review_passes_valid_chinese_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["error_count"], 0)
            self.assertTrue((project / "06-check/semantic-review.json").exists())
            inventory = json.loads((project / "06-check/text-inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(inventory["summary"]["unmatched_text_count"], 0)

    def test_nvidia_negative_fixture_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "nvidia-negative"
            shutil.copytree(FIXTURE_ROOT / "nvidia-negative", project)

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("language_not_zh_cn", codes)
            self.assertIn("audience_missing", codes)
            self.assertIn("slide_page_type_missing", codes)
            self.assertIn("slide_section_missing", codes)
            self.assertIn("slide_role_missing", codes)
            self.assertIn("slide_title_not_chinese", codes)
            self.assertIn("visible_text_not_in_plan_or_source", codes)
            self.assertIn("missing_evidence_json", codes)

    def test_semantic_review_blocks_stale_or_unknown_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            plan = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][1]["source_refs"] = ["source:missing"]
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("source_ref_not_found", codes)

    def test_semantic_review_extracts_foreign_object_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            (project / "04-svg/prepared/page-001.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div xmlns="http://www.w3.org/1999/xhtml">Hardcoded English Takeaway</div></foreignObject></svg>',
                encoding="utf-8",
            )

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("visible_text_not_in_plan_or_source", codes)
            inventory = json.loads((project / "06-check/text-inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(inventory["summary"]["unmatched_text_count"], 1)

    def test_semantic_review_limits_text_provenance_to_current_page_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            evidence = json.loads((project / "source/evidence.json").read_text(encoding="utf-8"))
            evidence["items"].append(
                {
                    "id": "item-002",
                    "text": "这是一条只属于第二页引用的证据内容，不应该替第一页的可见文本背书",
                    "source": "source-notes.md",
                }
            )
            write_json(project / "source/evidence.json", evidence)
            plan = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][1]["source_refs"] = ["source:item-002"]
            write_json(project / "02-plan/slide_plan.json", plan)
            (project / "04-svg/prepared/page-001.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><text>这是一条只属于第二页引用的证据内容</text></svg>',
                encoding="utf-8",
            )

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("visible_text_not_in_plan_or_source", codes)

    def test_semantic_review_blocks_thin_source_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            evidence = json.loads((project / "source/evidence.json").read_text(encoding="utf-8"))
            evidence["source_status"] = "thin"
            write_json(project / "source/evidence.json", evidence)

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("source_status_not_ready", codes)

    def test_semantic_review_blocks_chart_rich_thin_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            plan = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][1]["layout_family"] = "chart"
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("chart_rich_content_too_thin", codes)

    def test_semantic_review_blocks_numeric_claim_without_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = self.make_valid_project(Path(tmpdir))
            plan = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][0]["key_message"] = "市场规模增长 30%"
            plan["slides"][0]["source_refs"] = []
            write_json(project / "02-plan/slide_plan.json", plan)
            (project / "04-svg/prepared/page-001.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><text>英伟达供应链拐点</text><text>市场规模增长 30%</text></svg>',
                encoding="utf-8",
            )

            result = svglide_semantic_review.run_semantic_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("numeric_claim_uncited", codes)


if __name__ == "__main__":
    unittest.main()
