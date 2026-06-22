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

import svglide_palette_selector
import svglide_theme_template_selector as selector


def prepare_project(root: Path, brief: str) -> None:
    palette = svglide_palette_selector.select_palette(root, brief, top_k=5)
    svglide_palette_selector.write_palette_selection(root, palette)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class ThemeTemplateSelectorTest(unittest.TestCase):
    def test_internal_review_selects_business_dashboard_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份内部业务复盘，高管经营看板，包含指标、趋势和行动项"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        template_ids = [item["template_id"] for item in result["template_candidates"]]
        self.assertTrue({"executive-dashboard", "metric-dashboard", "trend-grid-report"}.intersection(template_ids))
        self.assertTrue(result["theme_candidates"])
        self.assertIn(result["confidence"], {"high", "medium", "low"})

    def test_zhipu_minimax_respects_selected_palette_and_brand_affinity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份主题为智谱和 MiniMax 的 slide，从头走到本地预览"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)
            palette_selected = json.loads((root / "02-plan/palette-selection.json").read_text(encoding="utf-8"))["selected_palette_id"]

        self.assertEqual(result["selected_palette_id"], palette_selected)
        self.assertIn(result["selected_theme_id"], {"blueprint-technical", "cobalt-grid", "glass-neon", "magazine-cobalt"})
        self.assertEqual(["zhipu", "minimax"], result["brand_resolution"]["brands"])

    def test_competitive_analysis_selects_comparison_or_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "做一份竞品对比 battlecard，包含 feature matrix、定位和差异"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        template_ids = [item["template_id"] for item in result["template_candidates"]]
        self.assertTrue({"comparison-cards", "brutalist-matrix"}.intersection(template_ids))

    def test_output_is_stable_for_unknown_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "一个不存在于模板库的主题：量子陶瓷供应链"
            prepare_project(root, brief)
            first = selector.select_theme_template(root, brief, top_k=5)
            second = selector.select_theme_template(root, brief, top_k=5)

        self.assertEqual(first["selected_template_id"], second["selected_template_id"])
        self.assertEqual(first["selected_theme_id"], second["selected_theme_id"])
        self.assertEqual(first["deterministic_seed"], second["deterministic_seed"])

    def test_plan_declared_templates_are_included_beyond_top_k(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份内部战略复盘，使用多种 P1 artboard 版式"
            prepare_project(root, brief)
            write_json(
                root / "02-plan/slide_plan.json",
                {
                    "slides": [
                        {"page": 1, "canvas_spec": {"template_id": "intelligence-brief", "theme_id": "signal-navy"}},
                        {"page": 2, "canvas_spec": {"template_id": "poster-stat-punch", "theme_id": "signal-navy"}},
                    ],
                },
            )

            result = selector.select_theme_template(root, brief, top_k=1)

        template_ids = [item["template_id"] for item in result["template_candidates"]]
        theme_ids = [item["theme_id"] for item in result["theme_candidates"]]
        self.assertIn("intelligence-brief", template_ids)
        self.assertIn("poster-stat-punch", template_ids)
        self.assertIn("signal-navy", theme_ids)
        declared = [item for item in result["template_candidates"] if item["template_id"] == "poster-stat-punch"][0]
        self.assertIn("plan_declared", declared["matched_signals"])

    def test_write_selection_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "事故复盘，包含时间线、根因和行动项"
            prepare_project(root, brief)
            result = selector.select_theme_template(root, brief, top_k=5)

            output = selector.write_selection(root, result)
            output_exists = output.exists()

            receipt = json.loads((root / "receipts/theme_template_selection.json").read_text(encoding="utf-8"))
        self.assertTrue(output_exists)
        self.assertEqual(receipt["selected_template_id"], result["selected_template_id"])

    def test_twenty_business_scenarios_select_fit_templates(self) -> None:
        cases = [
            ("internal_review", "生成一份内部业务复盘，高管经营看板，包含指标、趋势和行动项", {"executive-dashboard", "metric-dashboard", "trend-grid-report"}),
            ("incident_postmortem", "做一次线上事故复盘，包含时间线、影响范围、根因和整改 owner", {"timeline-steps", "risk-alert", "process-flow"}),
            ("competitive_battlecard", "做一份竞品对比 battlecard，包含 feature matrix、定位和差异", {"comparison-cards", "brutalist-matrix"}),
            ("tech_architecture", "生成一份技术架构方案，包含系统模块、依赖、链路和风险", {"architectural-spec", "architecture-blueprint"}),
            ("product_launch", "产品发布会 deck，强调新品卖点、发布节奏和用户价值", {"poster-stat-punch", "product-ribbon", "cover-hero"}),
            ("research_poster", "学术会议研究海报，包含方法、实验结果、机构署名和参考文献", {"research-poster", "printed-program"}),
            ("onboarding_workshop", "新人 onboarding 培训 workshop，包含议程、练习和检查清单", {"agenda-list", "printed-program", "annotated-field-board"}),
            ("strategy_roadmap", "战略路线图，包含 OKR、里程碑、优先级和依赖关系", {"roadmap-lanes", "process-flow", "timeline-steps"}),
            ("security_audit", "安全合规审计汇报，包含风险矩阵、controls 和 remediation", {"risk-alert", "intelligence-brief"}),
            ("data_dashboard", "增长数据看板，包含漏斗、趋势、KPI 和渠道健康度", {"executive-dashboard", "metric-dashboard", "trend-grid-report"}),
            ("market_landscape", "市场格局分析，包含玩家分层、机会空间和趋势", {"trend-grid-report", "dense-panel-grid", "intelligence-brief"}),
            ("customer_story", "客户案例故事，包含场景、痛点、证据和 quote", {"image-feature", "editorial-quote-chart", "quote-focus"}),
            ("financial_review", "财务经营复盘，包含收入、毛利、费用、现金流和 forecast", {"executive-dashboard", "metric-dashboard", "ledger-briefing"}),
            ("roadmap_lanes", "下季度产品 roadmap lanes，包含 swimlane、owner 和阶段", {"roadmap-lanes", "timeline-steps", "process-flow"}),
            ("risk_alert", "风险预警周报，包含红黄绿状态、影响、处置和 owner", {"risk-alert", "intelligence-brief"}),
            ("image_report", "品牌图文报告，需要大图、注释和短文案", {"image-feature", "editorial-quote-chart"}),
            ("dense_table", "高密度项目排期表，包含多个项目、状态、负责人和时间", {"dense-panel-grid", "printed-program", "ledger-briefing"}),
            ("ai_company_compare", "智谱和 MiniMax 对比，包含定位、模型能力、生态和商业化", {"comparison-cards", "brutalist-matrix", "intelligence-brief"}),
            ("closing_summary", "年度总结最后一页，强调三个结论和下一步行动", {"summary-final"}),
            ("unknown_topic", "一个不存在于模板库的主题：量子陶瓷供应链", {"agenda-list", "annotated-field-board", "architectural-spec", "intelligence-brief"}),
        ]
        for name, brief, expected in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    prepare_project(root, brief)
                    result = selector.select_theme_template(root, brief, top_k=5)
                self.assertIn(result["selected_template_id"], expected)
                candidate_ids = {item["template_id"] for item in result["template_candidates"]}
                self.assertTrue(candidate_ids.intersection(expected), f"{name} candidates={sorted(candidate_ids)} expected={sorted(expected)}")


if __name__ == "__main__":
    unittest.main()
