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

import svglide_strategy_review


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def base_plan(title: str, archetype: str = "company_ecosystem") -> dict[str, object]:
    return {
        "language": "zh-CN",
        "title": title,
        "deck_intent": "sample",
        "audience": "业务负责人",
        "deck_structure": ["cover", "content", "closing"],
        "style_preset": "avocado_press",
        "visual_identity": {
            "theme_archetype": archetype,
            "design_dna": {
                "palette": "light corporate product ecosystem",
                "palette_intent": "light",
                "layout_motif": "产品生态墙",
                "shape_language": "低圆角应用卡片",
                "image_treatment": "官网图作为弱背景",
                "component_bias": "生态墙、组织网络、结论条",
                "theme_visual_anchors": ["产品生态墙", "App tile", "组织网络"],
            },
            "forbidden_reuse": {"recent_decks": 5, "avoid_default_skeleton": True},
            "distinctness_target": {"palette_overlap_max": 0.67},
        },
        "slides": [
            {
                "page": 1,
                "page_type": "cover",
                "section": "开场",
                "role": "thesis",
                "title": title,
                "key_message": "这是一条中文主结论。",
                "body_points": ["中文要点一", "中文要点二"],
                "renderer_id": "cover_full_bleed",
                "layout_family": "cover",
            },
            {
                "page": 2,
                "page_type": "content",
                "section": "正文",
                "role": "evidence",
                "title": "产品生态如何展开",
                "key_message": "这是一条中文正文结论。",
                "body_points": ["中文证据一", "中文证据二"],
                "source_refs": ["item-001"],
                "renderer_id": "ecosystem_wall",
                "layout_family": "ecosystem",
            },
            {
                "page": 3,
                "page_type": "closing",
                "section": "结论",
                "role": "takeaway",
                "title": "结论页",
                "key_message": "这是一条中文总结。",
                "body_points": ["中文行动一", "中文行动二"],
                "renderer_id": "closing_cta",
                "layout_family": "closing",
            },
        ],
    }


class SVGlideStrategyReviewTest(unittest.TestCase):
    def test_fails_without_visual_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            plan = base_plan("字节跳动")
            plan.pop("visual_identity")
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_strategy_review.run_strategy_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("visual_identity_missing", codes)

    def test_fails_theme_archetype_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", base_plan("字节跳动", archetype="space_capital_market"))

            result = svglide_strategy_review.run_strategy_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("visual_identity_theme_mismatch", codes)

    def test_passes_topic_specific_visual_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", base_plan("字节跳动"))

            result = svglide_strategy_review.run_strategy_review(project)

            self.assertEqual(result["status"], "passed")

    def test_passes_volcanic_research_visual_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            plan = base_plan("冰岛火山研究", archetype="volcanic_research_lab")
            plan["audience"] = "地理研究读者"
            plan["slides"][1]["title"] = "监测信号如何展开"
            plan["slides"][1]["body_points"] = ["地震活动", "地表形变"]
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_strategy_review.run_strategy_review(project)

            self.assertEqual(result["status"], "passed")

    def test_passes_new_zealand_landscape_visual_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            plan = base_plan("新西兰风光路线", archetype="alpine_coast_travel_board")
            plan["audience"] = "旅行内容策划读者"
            plan["slides"][1]["title"] = "路线层次如何展开"
            plan["slides"][1]["body_points"] = ["高山湖泊", "海岸路线"]
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_strategy_review.run_strategy_review(project)

            self.assertEqual(result["status"], "passed")

    def test_full_deck_fails_for_four_page_sample_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            plan = base_plan("智谱和 MiniMax")
            plan["deck_intent"] = "full_deck"
            plan["target_slide_count"] = 10
            plan["deck_structure"] = ["cover", "content", "content", "closing"]
            plan["slides"].insert(
                2,
                {
                    "page": 3,
                    "page_type": "content",
                    "section": "对比",
                    "role": "comparison",
                    "title": "能力路径对比",
                    "key_message": "这是一条中文对比结论。",
                    "body_points": ["中文证据一", "中文证据二"],
                    "source_refs": ["item-002"],
                    "renderer_id": "comparison_matrix",
                    "layout_family": "matrix",
                },
            )
            plan["slides"][3]["page"] = 4
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_strategy_review.run_strategy_review(project)

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("full_deck_slide_count_too_low", codes)
        self.assertIn("full_deck_minimal_sample_structure", codes)

    def test_full_deck_passes_with_ten_page_narrative(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            plan = base_plan("智谱和 MiniMax")
            plan["deck_intent"] = "full_deck"
            plan["target_slide_count"] = 10
            plan["deck_structure"] = ["cover", "content", "closing"]
            titles = [
                ("核心结论", "thesis", "核心结论是两家公司路径不同。"),
                ("公司定位", "context", "公司定位决定产品路径。"),
                ("模型能力对比", "comparison", "模型能力需要按场景比较。"),
                ("产品入口", "evidence", "产品入口体现用户路径。"),
                ("场景与用户路径", "evidence", "场景拆分能解释差异。"),
                ("商业化与生态", "evidence", "生态协同影响交付。"),
                ("安全治理与合规风险", "risk", "安全治理需要持续观察。"),
                ("差异矩阵", "comparison", "差异矩阵帮助统一判断口径。"),
            ]
            slides = [plan["slides"][0]]
            for index, (title, role, key_message) in enumerate(titles, start=2):
                slides.append(
                    {
                        "page": index,
                        "page_type": "content",
                        "section": "正文",
                        "role": role,
                        "title": title,
                        "key_message": key_message,
                        "body_points": ["中文证据一", "中文证据二"],
                        "source_refs": ["item-001"],
                        "renderer_id": "ecosystem_wall" if index % 2 else "comparison_matrix",
                        "layout_family": "ecosystem" if index % 2 else "matrix",
                    }
                )
            closing = dict(plan["slides"][-1])
            closing["page"] = 10
            closing["title"] = "后续观察指标"
            closing["key_message"] = "后续观察指标包括治理、合规和产品留存。"
            slides.append(closing)
            plan["slides"] = slides
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_strategy_review.run_strategy_review(project)

        self.assertEqual(result["status"], "passed", result["issues"])


if __name__ == "__main__":
    unittest.main()
