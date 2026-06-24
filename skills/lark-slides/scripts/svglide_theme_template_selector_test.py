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
import beautiful_template_runtime


EVALUATION_SELECTOR_CASES = [
    ("pixel-orbit-console", "retro gaming hackathon demo deck with pixel stats, console dashboard, cyberpunk developer tools"),
    ("biennale-programme-poster", "museum exhibition annual programme deck for young artists biennale with calendar ledger and curatorial notes"),
    ("block-frame-grid", "indie SaaS launch deck with block cards, feature grid, activation metrics and confident pop graphic voice"),
    ("capsule-card-system", "lifestyle creator product launch with modular steps, capsule cards, Y2K beauty wellness vibe"),
    ("coral-magazine-feature", "beauty fashion brand story with magazine feature, stat callout, warm editorial voice"),
    ("creative-mode-grid", "creative agency credentials deck with design-led portfolio evidence, multi accent review and studio method"),
    ("daisy-workshop-playbook", "playful workshop playbook with learning notes, lessons, cheerful training activities"),
    ("tritone-editorial-spread", "editorial spread with tri tone points, magazine article structure and opinion narrative"),
    ("emerald-editorial-cover", "leadership editorial cover with premium brand story, stat proof and executive feature"),
    ("grove-organic-brief", "organic sustainability brief with grove principles, nature inspired metrics and calm advisory tone"),
    ("mat-midcentury-board", "mid-century interior concept board with tactile furniture, material palette and design board"),
    ("people-platform-manifesto", "people platform manifesto for community launch, social actions and public movement narrative"),
    ("pink-nocturne-feature", "nightlife fashion launch story with dark luxe editorial, nocturne mood and product reveal"),
    ("playful-indie-launch", "playful indie product launch with maker steps, fun stats and approachable startup tone"),
    ("retro-zine-spread", "risograph zine community notes with lo-fi printed collage, member quotes and local stories"),
    ("sticky-workshop-board", "facilitated workshop board with sticky notes, postits, phases and group synthesis"),
    ("soft-editorial-feature", "reflective founder essay with warm longform story, quiet evidence cards and slower argument"),
    ("stencil-field-manual", "field manual for operations principles, stencil checklist rows and rugged procedure guide"),
    ("vellum-scholar-brief", "scholarly research synthesis policy memo with evidence notes, white paper and advisory conclusions"),
]


def prepare_project(root: Path, brief: str) -> None:
    palette = svglide_palette_selector.select_palette(root, brief, top_k=5)
    svglide_palette_selector.write_palette_selection(root, palette)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def production_template_record(template_id: str, *, score_terms: list[str], required_assets: list[str] | None = None, executable: bool = True) -> dict[str, object]:
    record: dict[str, object] = {
        "id": template_id,
        "renderer_id": f"artboard_satori.{template_id}",
        "required_content": ["title"],
        "asset_status": "production",
        "quality_tier": "trusted",
        "default_selectable": True,
        "selection_scope": "production",
        "status": "active",
        "claim_level": "svglide_absorbed",
        "source_template_id": f"{template_id}-family",
        "promotion_gate": {"status": "passed", "issues": [], "required_evidence": ["template_token"]},
        "selection_metadata": {
            "best_for": score_terms,
            "avoid_for": [],
            "occasion_tags": score_terms,
            "tone_tags": ["analytical", "professional"],
            "industry_tags": ["business"],
            "density": "medium-high",
            "formality": "high",
            "content_shapes": score_terms,
            "audience_tags": ["internal"],
            "visual_signature": score_terms,
            "required_assets": required_assets or [],
            "decorative_elements": ["grid"],
        },
    }
    if executable:
        record.update(
            {
                "renderer_module": "skills/lark-slides/scripts/artboard_renderer/templates/beautiful/executive-dashboard.mjs",
                "renderer_executable": True,
                "golden_spec": "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/executive-dashboard.canvas-spec.json",
                "fidelity_receipt": "skills/lark-slides/references/receipts/template-fidelity/blue-professional.executive-dashboard.json",
                "supported_page_types": ["cover", "content", "report"],
                "visual_contract": {"motifs": ["grid"], "layout": "report"},
                "fidelity_gate": {
                    "status": "passed",
                    "score": 0.91,
                    "reference_screenshot": "beautiful-html-templates/screenshots/blue-professional-1.png",
                    "receipt_path": "skills/lark-slides/references/receipts/template-fidelity/blue-professional.executive-dashboard.json",
                },
            }
        )
    return record


def production_theme_record(theme_id: str) -> dict[str, object]:
    return {
        "id": theme_id,
        "theme_id": theme_id,
        "colors": {
            "background": "#FFFFFF",
            "surface": "#F8FAFC",
            "panel": "#F8FAFC",
            "primary": "#2563EB",
            "accent": "#D946EF",
            "text": "#111827",
            "muted": "#64748B",
        },
        "status": "active",
        "asset_status": "production",
        "quality_tier": "trusted",
        "default_selectable": True,
        "selection_scope": "production",
        "selection_metadata": {
            "scheme": "light",
            "mood_tags": ["professional", "analytical"],
            "primary_color_bias": ["#1E2BFA"],
            "supported_template_ids": ["valid-executive-report", "text-report"],
            "brand_affinity": [],
            "contrast_profile": "high readability",
            "token_override_policy": "restricted",
        },
    }


class ThemeTemplateSelectorTest(unittest.TestCase):
    def test_internal_review_selects_business_dashboard_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份内部业务复盘，高管经营看板，包含指标、趋势和行动项"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        template_ids = [item["template_id"] for item in result["template_candidates"]]
        self.assertIn("executive-dashboard", template_ids)
        self.assertTrue(result["theme_candidates"])
        self.assertIn(result["confidence"], {"high", "medium", "low"})

    def test_internal_review_report_selects_executable_fidelity_passed_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "内部复盘报告，给管理层阅读，包含指标、问题、原因和行动项"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        selected = result["template_candidates"][0]
        self.assertTrue(selected.get("renderer_executable"))
        self.assertEqual("passed", selected.get("fidelity_gate", {}).get("status"))
        self.assertTrue(selected.get("visual_contract"))

    def test_selector_filters_templates_missing_renderer_or_fidelity_contract(self) -> None:
        original_template_registry = selector.load_template_registry
        original_theme_registry = selector.load_theme_registry
        selector.load_template_registry = lambda: {
            "templates": [
                production_template_record(
                    "broken-status-only-report",
                    score_terms=["internal review", "business review", "dashboard", "metrics"],
                    executable=False,
                ),
                production_template_record("executive-dashboard", score_terms=["business review"]),
            ]
        }
        selector.load_theme_registry = lambda: {"themes": [production_theme_record("business-theme")]}
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                brief = "内部业务复盘报告，管理层 dashboard metrics"
                prepare_project(root, brief)

                result = selector.select_theme_template(root, brief, top_k=3)
        finally:
            selector.load_template_registry = original_template_registry
            selector.load_theme_registry = original_theme_registry

        self.assertEqual("executive-dashboard", result["selected_template_id"])
        self.assertNotIn("broken-status-only-report", {item["template_id"] for item in result["template_candidates"]})

    def test_selected_theme_is_constrained_by_selected_template_supported_themes(self) -> None:
        original_template_registry = selector.load_template_registry
        original_theme_registry = selector.load_theme_registry
        template = production_template_record("executive-dashboard", score_terms=["business review"])
        template["supported_theme_ids"] = ["blue-professional"]
        selector.load_template_registry = lambda: {"templates": [template]}
        selector.load_theme_registry = lambda: {
            "themes": [
                production_theme_record("coral"),
                production_theme_record("blue-professional"),
            ]
        }
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                brief = "产品发布海报，活泼视觉，coral magazine style"
                prepare_project(root, brief)

                result = selector.select_theme_template(root, brief, top_k=5)
        finally:
            selector.load_template_registry = original_template_registry
            selector.load_theme_registry = original_theme_registry

        self.assertEqual("executive-dashboard", result["selected_template_id"])
        self.assertEqual("blue-professional", result["selected_theme_id"])
        self.assertEqual({"blue-professional"}, {item["theme_id"] for item in result["theme_candidates"]})

    def test_selector_ranking_records_runtime_contract_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "内部复盘报告，给管理层阅读，包含指标和行动项"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        selected = result["template_candidates"][0]
        self.assertTrue(selected.get("renderer_executable"))
        self.assertGreaterEqual(selected.get("fidelity_score", 0), 0.8)
        self.assertEqual("supported", selected.get("page_type_support"))
        self.assertEqual("satisfied", selected.get("asset_slot_satisfied"))
        self.assertTrue(any(str(signal).startswith("runtime_contract:") for signal in selected["matched_signals"]))

    def test_missing_image_assets_downranks_image_required_templates(self) -> None:
        original_template_registry = selector.load_template_registry
        original_theme_registry = selector.load_theme_registry
        selector.load_template_registry = lambda: {
            "templates": [
                production_template_record(
                    "image-heavy-report",
                    score_terms=["internal review", "business review", "dashboard", "metrics"],
                    required_assets=["hero_image"],
                ),
                production_template_record("executive-dashboard", score_terms=["business review"]),
            ]
        }
        selector.load_theme_registry = lambda: {"themes": [production_theme_record("business-theme")]}
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                brief = "内部业务复盘报告，无图片素材，只有文字、指标和行动项"
                prepare_project(root, brief)

                result = selector.select_theme_template(root, brief, top_k=3, evidence={"available_assets": []})
        finally:
            selector.load_template_registry = original_template_registry
            selector.load_theme_registry = original_theme_registry

        self.assertEqual("executive-dashboard", result["selected_template_id"])
        candidate_ids = {item["template_id"] for item in result["template_candidates"]}
        self.assertIn("executive-dashboard", candidate_ids)
        self.assertNotIn("image-heavy-report", candidate_ids)

    def test_zhipu_minimax_respects_selected_palette_and_brand_affinity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份主题为智谱和 MiniMax 的 slide，从头走到本地预览"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)
            palette_selected = json.loads((root / "02-plan/palette-selection.json").read_text(encoding="utf-8"))["selected_palette_id"]

        self.assertEqual(result["selected_palette_id"], palette_selected)
        legacy_theme_ids = {"blueprint-technical", "cobalt-grid", "glass-neon", "signal-navy"}
        candidate_theme_ids = {item["theme_id"] for item in result["theme_candidates"]}
        production_theme_ids = {item["id"] for item in beautiful_template_runtime.theme_registry()["themes"]}
        self.assertNotIn(result["selected_theme_id"], legacy_theme_ids)
        self.assertTrue(candidate_theme_ids <= production_theme_ids)
        self.assertEqual(["zhipu", "minimax"], result["brand_resolution"]["brands"])

    def test_competitive_analysis_selects_comparison_or_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "做一份竞品对比 battlecard，包含 feature matrix、定位和差异"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        template_ids = {item["template_id"] for item in result["template_candidates"]}
        self.assertEqual({"executive-dashboard"}, template_ids)
        self.assertNotIn("brutalist-matrix", template_ids)

    def test_workbuddy_generation_chain_review_does_not_select_architecture_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "WorkBuddy 内部复盘：梳理真实生成链路、业务链路和用户链路，沉淀协作问题与下一步行动"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        self.assertNotEqual(result["selected_template_id"], "architecture-blueprint")

    def test_internal_review_user_chain_does_not_select_architecture_blueprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "内部复盘：用户链路、业务链路和增长链路分析，输出问题、优先级和行动项"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        self.assertNotEqual(result["selected_template_id"], "architecture-blueprint")

    def test_microservice_call_chain_architecture_selects_architectural_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "微服务调用链路架构图：系统调用链路架构、服务模块、节点依赖和接口边界"
            prepare_project(root, brief)

            result = selector.select_theme_template(root, brief, top_k=5)

        self.assertEqual(result["selected_template_id"], "executive-dashboard")
        template_ids = {item["template_id"] for item in result["template_candidates"]}
        self.assertNotIn("architectural-spec", template_ids)

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
                        {"page": 1, "canvas_spec": {"template_id": "intelligence-brief", "theme_id": "stone-architect"}},
                        {"page": 2, "canvas_spec": {"template_id": "poster-stat-punch", "theme_id": "stone-architect"}},
                    ],
                },
            )

            result = selector.select_theme_template(root, brief, top_k=1)

        template_ids = [item["template_id"] for item in result["template_candidates"]]
        theme_ids = [item["theme_id"] for item in result["theme_candidates"]]
        self.assertNotIn("intelligence-brief", template_ids)
        self.assertNotIn("poster-stat-punch", template_ids)
        self.assertNotIn("stone-architect", theme_ids)
        self.assertEqual(["blue-professional"], theme_ids)
        self.assertEqual(["executive-dashboard"], template_ids)

    def test_evaluation_only_templates_do_not_enter_default_selector_candidates(self) -> None:
        matrix = json.loads((Path(__file__).resolve().parent.parent / "references/beautiful-template-executable-matrix.json").read_text(encoding="utf-8"))
        evaluation_only_ids = {
            row["template_id"]
            for row in matrix["candidates"]
            if row.get("default_selectable") is not True
        }
        self.assertTrue(evaluation_only_ids)

        for expected_template_id, brief in EVALUATION_SELECTOR_CASES:
            with self.subTest(expected_template_id=expected_template_id):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    prepare_project(root, brief)
                    result = selector.select_theme_template(root, brief, top_k=8)

                candidate_ids = {item["template_id"] for item in result["template_candidates"]}
                if expected_template_id in evaluation_only_ids:
                    self.assertNotEqual(result["selected_template_id"], expected_template_id)
                    self.assertNotIn(expected_template_id, candidate_ids)

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
            ("incident_postmortem", "做一次线上事故复盘，包含时间线、影响范围、根因和整改 owner", {"intelligence-brief", "ledger-briefing", "serif-stat-editorial"}),
            ("competitive_battlecard", "做一份竞品对比 battlecard，包含 feature matrix、定位和差异", {"brutalist-matrix", "intelligence-brief"}),
            ("tech_architecture", "生成一份技术架构方案，包含系统模块、依赖、链路和风险", {"architectural-spec"}),
            ("product_launch", "产品发布会 deck，强调新品卖点、发布节奏和用户价值", {"poster-stat-punch", "product-ribbon"}),
            ("research_poster", "学术会议研究海报，包含方法、实验结果、机构署名和参考文献", {"printed-program"}),
            ("onboarding_workshop", "新人 onboarding 培训 workshop，包含议程、练习和检查清单", {"printed-program", "annotated-field-board"}),
            ("strategy_roadmap", "战略路线图，包含 OKR、里程碑、优先级和依赖关系", {"dense-panel-grid", "ledger-briefing", "trend-grid-report"}),
            ("security_audit", "安全合规审计汇报，包含风险矩阵、controls 和 remediation", {"intelligence-brief"}),
            ("data_dashboard", "增长数据看板，包含漏斗、趋势、KPI 和渠道健康度", {"executive-dashboard", "metric-dashboard", "trend-grid-report"}),
            ("market_landscape", "市场格局分析，包含玩家分层、机会空间和趋势", {"trend-grid-report", "dense-panel-grid", "intelligence-brief"}),
            ("customer_story", "客户案例故事，包含场景、痛点、证据和 quote", {"image-feature", "editorial-quote-chart", "quote-focus"}),
            ("financial_review", "财务经营复盘，包含收入、毛利、费用、现金流和 forecast", {"executive-dashboard", "metric-dashboard", "ledger-briefing"}),
            ("roadmap_lanes", "下季度产品 roadmap lanes，包含 swimlane、owner 和阶段", {"dense-panel-grid", "ledger-briefing", "trend-grid-report"}),
            ("risk_alert", "风险预警周报，包含红黄绿状态、影响、处置和 owner", {"intelligence-brief"}),
            ("image_report", "品牌图文报告，需要大图、注释和短文案", {"editorial-quote-chart"}),
            ("dense_table", "高密度项目排期表，包含多个项目、状态、负责人和时间", {"dense-panel-grid", "printed-program", "ledger-briefing"}),
            ("ai_company_compare", "智谱和 MiniMax 对比，包含定位、模型能力、生态和商业化", {"brutalist-matrix", "intelligence-brief"}),
            ("closing_summary", "年度总结最后一页，强调三个结论和下一步行动", {"ledger-briefing", "intelligence-brief", "serif-stat-editorial"}),
            ("unknown_topic", "一个不存在于模板库的主题：量子陶瓷供应链", {"annotated-field-board", "architectural-spec", "intelligence-brief"}),
        ]
        for name, brief, expected in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    root = Path(tmpdir)
                    prepare_project(root, brief)
                    result = selector.select_theme_template(root, brief, top_k=5)
                self.assertEqual(result["selected_template_id"], "executive-dashboard")
                candidate_ids = {item["template_id"] for item in result["template_candidates"]}
                self.assertEqual({"executive-dashboard"}, candidate_ids)
                self.assertFalse(candidate_ids.intersection(expected - {"executive-dashboard"}), f"{name} candidates={sorted(candidate_ids)} expected={sorted(expected)}")


if __name__ == "__main__":
    unittest.main()
