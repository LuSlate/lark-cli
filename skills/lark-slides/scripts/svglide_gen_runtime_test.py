# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import svglide_gen_runtime as runtime
import svg_preview_lint as preview_lint


class SVGlideGenRuntimeTest(unittest.TestCase):
    def test_render_demo_slide_emits_protocol_svg_and_component_report(self) -> None:
        report = runtime.ComponentReport()

        svg = runtime.render_demo_slide(
            page=1,
            kind="timeline",
            title="Timeline",
            summary="Pick for milestone events.",
            asset_id="chart.timeline",
            report=report,
        )
        data = report.to_dict()

        self.assertIn('slide:role="slide"', svg)
        self.assertIn('width="960"', svg)
        self.assertEqual(data["schema_version"], "svglide-component-report/v1")
        self.assertEqual(data["pages"][0]["page"], 1)
        self.assertGreaterEqual(len(data["pages"][0]["components"]), 3)
        component = data["pages"][0]["components"][0]
        self.assertIn("bbox", component)
        self.assertTrue(component["primitives"])

    def test_design_pattern_usage_receipt_requires_page_trace(self) -> None:
        report = runtime.ComponentReport()
        runtime.render_demo_slide(
            page=2,
            kind="bar_chart",
            title="Bar Chart",
            summary="Pick for category comparison.",
            asset_id="chart.bar_chart",
            report=report,
        )

        receipt = runtime.design_pattern_usage_receipt(report.to_dict())

        self.assertEqual(receipt["schema_version"], "svglide-design-pattern-usage/v1")
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["page_usages"][0]["asset_id"], "chart.bar_chart")
        self.assertEqual(receipt["page_usages"][0]["page"], 2)
        self.assertTrue(receipt["page_usages"][0]["component_ids"])
        self.assertTrue(receipt["page_usages"][0]["source_trace"])

    def test_design_pattern_visual_contracts_for_hero_pages(self) -> None:
        cover_report = runtime.ComponentReport()
        cover_svg = runtime.render_demo_slide(
            page=1,
            kind="cover",
            title="Global AI Capital 2026",
            summary="Capital, compute, and control.",
            asset_id="layout.page_type.cover",
            report=cover_report,
        )
        self.assertIn('id="cover-master-title"', cover_svg)
        self.assertIn('font-size:64px', cover_svg)
        self.assertIn("Cambria", cover_svg)
        self.assertIn('id="slash-1"', cover_svg)
        self.assertNotIn('id="title-surface"', cover_svg)
        self.assertIn("large_hero_type", json.dumps(cover_report.to_dict()))

        note_report = runtime.ComponentReport()
        note_svg = runtime.render_demo_slide(
            page=2,
            kind="editor_note",
            title="Why AI Capital Now",
            summary="Editorial note.",
            asset_id="layout.page_type.content",
            report=note_report,
        )
        self.assertIn('id="quote_ticks-1"', note_svg)
        self.assertIn('font-size:50px', note_svg)
        self.assertIn("Cambria", note_svg)
        self.assertIn("hero_metrics", json.dumps(note_report.to_dict()))

        closing_report = runtime.ComponentReport()
        closing_svg = runtime.render_demo_slide(
            page=8,
            kind="closing",
            title="Closing Thesis",
            summary="Takeaways.",
            asset_id="layout.page_type.ending",
            report=closing_report,
        )
        self.assertIn('id="closing-red-index-1"', closing_svg)
        self.assertIn("numbered_hierarchy", json.dumps(closing_report.to_dict()))

    def test_hub_renderer_uses_orbit_system_not_plain_cards(self) -> None:
        report = runtime.ComponentReport()
        svg = runtime.render_demo_slide(
            page=7,
            kind="hub_spoke",
            title="Stargate Hub",
            summary="Project finance meets compute scarcity.",
            asset_id="chart.hub_spoke",
            report=report,
        )

        self.assertIn('id="hub-orbit-outer"', svg)
        self.assertIn('id="hub-core-glow"', svg)
        self.assertIn("CAPEX LOOP", svg)
        self.assertIn("orbit_system", json.dumps(report.to_dict()))

    def test_chart_renderers_use_design_pattern_asset_level_structures(self) -> None:
        cases = [
            ("kpi_cards", "kpi-observation-label", "editorial_sidebar"),
            ("bar_chart", "bar-insight-value", "editorial_sidebar"),
            ("donut_chart", "donut-investor-label", "investor_breakdown"),
            ("sankey_chart", "sankey-return-block", "return_flow"),
        ]

        for kind, required_id, required_effect in cases:
            with self.subTest(kind=kind):
                report = runtime.ComponentReport()
                svg = runtime.render_demo_slide(
                    page=3,
                    kind=kind,
                    title=kind.replace("_", " "),
                    summary="SVGlide pattern-level renderer contract",
                    asset_id=f"chart.{kind}",
                    report=report,
                )
                self.assertIn(f'id="{required_id}"', svg)
                self.assertIn(required_effect, json.dumps(report.to_dict()))
                self.assertIn("Cambria", svg)

    def test_global_ai_pages_7_8_keep_design_pattern_bubble_then_donut_archetypes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "title": "Global AI Capital 2026",
                        "slides": [
                            {"page_kind": "cover", "title": "Cover"},
                            {"page_kind": "editor_note", "title": "Editor's Note"},
                            {"page_kind": "kpi_cards", "title": "Q1 VC Landscape"},
                            {"page_kind": "bar_chart", "title": "Hyperscaler Capex"},
                            {"page_kind": "donut_chart", "title": "OpenAI Investors"},
                            {"page_kind": "sankey_chart", "title": "Nvidia Loop"},
                            {
                                "page_kind": "bubble_chart",
                                "asset_id": "chart.bubble_chart",
                                "title": "估值兑现度：气泡大小 = 投资人数",
                                "summary": "Valuation × ARR × investor count",
                                "bubbles": [
                                    {"name": "xAI", "arr": 5, "valuation": 230, "investors": 8, "note": "$5B / $230B · 8+ investors"},
                                    {"name": "OpenAI", "arr": 24, "valuation": 852, "investors": 7, "note": "$24B / $852B · 7+ investors"},
                                    {"name": "Anthropic", "arr": 30, "valuation": 380, "investors": 5, "note": "$30B / $380B · 5 investors"},
                                ],
                                "insight": "所有气泡都站在公允线之上，xAI 偏离最远。",
                            },
                            {
                                "page_kind": "donut_chart",
                                "asset_id": "chart.donut_chart",
                                "title": "OpenAI $122B 这笔钱，从哪来",
                                "center": {"value": "$122B", "label": "TOTAL ROUND", "note": "@ $852B post-money"},
                                "segments": [
                                    {"name": "Amazon", "value": "$50B", "share": 41, "note": "41% · AWS 算力承诺"},
                                    {"name": "Nvidia", "value": "$30B", "share": 25, "note": "25% · 10GW 系统部署"},
                                    {"name": "SoftBank", "value": "$30B", "share": 25, "note": "25% · Stargate 联合主体"},
                                    {"name": "MSFT + 其他", "value": "$12B", "share": 9, "note": "9% · 其他投资人"},
                                ],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            page7 = (project / "pages" / "page-007.svg").read_text(encoding="utf-8")
            page8 = (project / "pages" / "page-008.svg").read_text(encoding="utf-8")
            cache = json.loads((project / "receipts" / "runtime-cache.json").read_text(encoding="utf-8"))
            usage = json.loads((project / "receipts" / "design-pattern-usage.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["pages"][6]["page_kind"], "bubble_chart")
            self.assertEqual(cache["pages"][7]["page_kind"], "donut_chart")
            self.assertIn('id="bubble-openai"', page7)
            self.assertIn('id="bubble-anthropic"', page7)
            self.assertIn('id="bubble-xai"', page7)
            self.assertIn('id="bubble-insight-band"', page7)
            self.assertIn('id="bubble-openai-name-plate"', page7)
            self.assertNotIn('id="bubble-openai-label-back"', page7)
            self.assertIn('id="donut-track"', page8)
            self.assertIn("$122B", page8)
            self.assertNotIn('id="hub-orbit-outer"', page7)
            self.assertNotIn('id="closing-list"', page8)
            self.assertEqual(usage["page_usages"][6]["asset_id"], "chart.bubble_chart")
            self.assertEqual(usage["page_usages"][7]["asset_id"], "chart.donut_chart")
            root = ET.fromstring(page7)
            elements = {element.get("id"): element for element in root.iter() if element.get("id")}
            for name in ("bubble-xai", "bubble-openai", "bubble-anthropic"):
                label = elements[f"{name}-label"]
                note = elements[f"{name}-note"]
                plate = elements[f"{name}-name-plate"]
            self.assertGreaterEqual(float(note.get("y", "0")) - float(label.get("y", "0")), 24)
            self.assertLessEqual(float(plate.get("y", "0")) + float(plate.get("height", "0")), float(note.get("y", "0")))

    def test_strategist_contract_renderer_uses_real_labels_not_placeholder_footer(self) -> None:
        spec = {
            "schema_version": "svglide-strategist-contract/v1",
            "page_type": "kpi_overview",
            "key_message": "低空物流网络的关键运营指标，包括时效、成本、覆盖、可靠性",
            "text_budget_by_role": {
                "title": {"max_chars": 18, "max_boxes": 1},
                "metric": {"max_chars": 12, "max_boxes": 1},
                "body": {"max_chars": 72, "max_boxes": 1},
                "footer": {"max_chars": 32, "max_boxes": 1},
            },
            "layout_boxes": [
                {"id": "title", "role": "title", "x": 48, "y": 34, "width": 864, "height": 48},
                {"id": "primary-kpi", "role": "metric", "x": 64, "y": 106, "width": 260, "height": 128},
                {"id": "secondary-grid", "role": "grid", "x": 348, "y": 106, "width": 548, "height": 128},
                {"id": "chart-row", "role": "chart", "x": 64, "y": 258, "width": 832, "height": 150},
                {"id": "body", "role": "body", "x": 64, "y": 426, "width": 832, "height": 56},
                {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
            ],
        }
        report = runtime.ComponentReport()

        svg = runtime.render_contract_slide(
            page=2,
            kind="kpi_cards",
            title="",
            summary="",
            asset_id="chart.kpi_cards",
            accent="#2563EB",
            spec=spec,
            report=report,
            deck_title="城市级低空物流网络策划案",
        )

        self.assertNotIn("SVGlide contract renderer", svg)
        self.assertIn("准点率", svg)
        self.assertIn("时效", svg)
        self.assertIn("城市级低空物流网络策划案", svg)

    def test_strategist_contract_dense_pages_emit_semantic_visual_labels(self) -> None:
        base_spec = {
            "schema_version": "svglide-strategist-contract/v1",
            "key_message": "低空物流网络需要把订单入口、空域调度、无人机执行和末端交付串成闭环",
            "text_budget_by_role": {
                "title": {"max_chars": 24, "max_boxes": 1},
                "body": {"max_chars": 96, "max_boxes": 1},
                "callout": {"max_chars": 60, "max_boxes": 1},
                "footer": {"max_chars": 32, "max_boxes": 1},
            },
            "layout_boxes": [
                {"id": "title", "role": "title", "x": 64, "y": 46, "width": 680, "height": 52},
                {"id": "visual", "role": "visual", "x": 92, "y": 132, "width": 776, "height": 300},
                {"id": "body", "role": "body", "x": 96, "y": 388, "width": 760, "height": 46},
                {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
            ],
        }

        cases = [
            ("process_flow", "process_flow", 'id="callout"', "订单入口"),
            ("capability_map", "hub_spoke", 'id="legend"', "空域调度"),
            ("comparison", "comparison_table", 'id="comparison-dimension-1"', "拥堵"),
            ("chart_takeaway", "bar_chart", 'id="callout"', "订单入口"),
            ("closing", "closing", 'id="closing-step-card-1"', "一中台"),
        ]

        for page_type, kind, required_id, required_copy in cases:
            with self.subTest(page_type=page_type):
                spec = dict(base_spec, page_type=page_type, title=page_type)
                report = runtime.ComponentReport()
                svg = runtime.render_contract_slide(
                    page=3,
                    kind=kind,
                    title="",
                    summary="",
                    asset_id=f"chart.{kind}",
                    accent="#2563EB",
                    spec=spec,
                    report=report,
                    deck_title="城市级低空物流网络策划案",
                )

                self.assertIn(required_id, svg)
                self.assertIn(required_copy, svg)

    def test_insight_callout_contract_uses_annotation_renderer_not_flow_fallback(self) -> None:
        spec = {
            "schema_version": "svglide-strategist-contract/v1",
            "page_type": "insight_callout",
            "title": "关键洞察",
            "key_message": "企业战略复盘需要把核心诊断、证据和下一步判断放在一个聚焦视场里",
            "visual_design_contract": {
                "required_visual_evidence": ["spotlight", "annotation", "semantic_labels"],
            },
            "layout_boxes": [
                {"id": "title", "role": "title", "x": 64, "y": 56, "width": 640, "height": 56},
                {"id": "spotlight", "role": "spotlight", "x": 88, "y": 146, "width": 532, "height": 248},
                {"id": "callout", "role": "callout", "x": 650, "y": 168, "width": 218, "height": 176},
                {"id": "caption", "role": "caption", "x": 104, "y": 418, "width": 720, "height": 38},
                {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
            ],
        }
        report = runtime.ComponentReport()

        svg = runtime.render_contract_slide(
            page=2,
            kind="insight_callout",
            title="",
            summary="",
            asset_id="chart.labeled_card",
            accent="#2563EB",
            spec=spec,
            report=report,
            deck_title="企业战略复盘",
        )
        encoded_report = json.dumps(report.to_dict(), ensure_ascii=False)

        self.assertIn('id="spotlight-stage"', svg)
        self.assertIn('id="annotation-callout-panel"', svg)
        self.assertIn("contract.annotation", encoded_report)
        self.assertIn("semantic_labels", encoded_report)
        self.assertNotIn("contract.flow", encoded_report)

    def test_strategist_contract_uses_full_page_archetype_geometry(self) -> None:
        base_spec = {
            "schema_version": "svglide-strategist-contract/v1",
            "key_message": "低空物流网络需要形成可运营、可调度、可复盘的城市级基础设施",
            "text_budget_by_role": {
                "title": {"max_chars": 24, "max_boxes": 1},
                "body": {"max_chars": 96, "max_boxes": 1},
                "callout": {"max_chars": 60, "max_boxes": 1},
                "footer": {"max_chars": 32, "max_boxes": 1},
            },
            "layout_boxes": [
                {"id": "title", "role": "title", "x": 64, "y": 46, "width": 680, "height": 52},
                {"id": "visual", "role": "visual", "x": 92, "y": 132, "width": 776, "height": 300},
                {"id": "body", "role": "body", "x": 96, "y": 388, "width": 760, "height": 46},
                {"id": "callout", "role": "callout", "x": 612, "y": 380, "width": 250, "height": 60},
                {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
            ],
        }

        cases = [
            ("cover", "cover", ["cover-map-field", "cover-route-ribbon", "cover-coordinate-stack-1"], ["full_page_archetype", "hero_route", "title_field"]),
            ("agenda", "agenda", ["agenda-route-backplane", "agenda-number-1", "agenda-route-path"], ["numbered_path", "section_index", "semantic_labels"]),
            ("section_divider", "section", ["section-signal-field", "section-index-rail", "section-hero-number"], ["section_index", "hero_signal", "full_page_archetype"]),
            ("process_flow", "process_flow", ["flow-backplane", "flow-lane-upper", "flow-lane-lower"], ["connector_flow", "flow_lanes", "full_page_archetype"]),
            ("capability_map", "hub_spoke", ["hub-backplane", "hub-sector-1", "hub-satellite-panel-1"], ["hub_spoke", "sector_field", "semantic_labels"]),
            ("chart_takeaway", "bar_chart", ["bar-plot-backplane", "bar-insight-strip", "bar-variance-path"], ["chart_geometry", "insight_strip", "full_page_archetype"]),
            ("closing", "closing", ["closing-backplane", "closing-step-card-1", "closing-route-ribbon"], ["closing_ribbon", "action_cards", "full_page_archetype"]),
        ]

        for page_type, kind, required_ids, required_evidence in cases:
            with self.subTest(page_type=page_type):
                spec = dict(base_spec, page_type=page_type, title=page_type)
                spec["visual_design_contract"] = {
                    "required_visual_evidence": required_evidence,
                }
                if page_type == "cover":
                    spec["layout_boxes"] = [
                        {"id": "title", "role": "title", "x": 72, "y": 150, "width": 560, "height": 120},
                        {"id": "body", "role": "body", "x": 76, "y": 284, "width": 520, "height": 72},
                        {"id": "visual", "role": "visual", "x": 600, "y": 84, "width": 288, "height": 360},
                        {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
                    ]
                report = runtime.ComponentReport()

                svg = runtime.render_contract_slide(
                    page=4,
                    kind=kind,
                    title="",
                    summary="",
                    asset_id=f"chart.{kind}",
                    accent="#2563EB",
                    spec=spec,
                    report=report,
                    deck_title="城市级低空物流网络策划案",
                )

                for required_id in required_ids:
                    self.assertIn(f'id="{required_id}"', svg)
                if page_type == "agenda":
                    self.assertIn('id="agenda-index-tick-1"', svg)
                    self.assertNotIn('id="agenda-number-label-1"', svg)
                encoded_report = json.dumps(report.to_dict())
                for evidence in spec["visual_design_contract"]["required_visual_evidence"]:
                    self.assertIn(evidence, encoded_report)

    def test_evidence_effects_does_not_echo_contract_required_evidence_as_proof(self) -> None:
        effects = runtime.evidence_effects(
            {"visual_design_contract": {"required_visual_evidence": ["fake_contract_evidence"]}},
            ["chart_geometry"],
        )

        self.assertEqual(["chart_geometry"], effects)
        self.assertNotIn("fake_contract_evidence", effects)

    def test_style_system_palette_changes_rendered_svg_fingerprint(self) -> None:
        def compose_with_accent(accent: str) -> str:
            with tempfile.TemporaryDirectory() as raw:
                project = Path(raw) / "runtime-project"
                project.mkdir()
                plan = project / "slide_plan.json"
                plan.write_text(
                    json.dumps(
                        {
                            "schema_version": "svglide-strategist-contract/v1",
                            "title": "Theme Accent Test",
                            "style_system": {"palette": {"accent": accent}},
                            "slides": [
                                {
                                    "page": 1,
                                    "page_type": "agenda",
                                    "title": "Contents",
                                    "key_message": "Agenda route",
                                    "visual_design_contract": {
                                        "required_visual_evidence": ["numbered_path", "section_index", "semantic_labels"],
                                    },
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                runtime.compose_project(project, plan)
                return (project / "pages" / "page-001.svg").read_text(encoding="utf-8")

        blue = compose_with_accent("#4A90E2")
        red = compose_with_accent("#E91E63")

        self.assertIn("#4A90E2", blue)
        self.assertIn("#E91E63", red)
        self.assertNotEqual(blue, red)

    def test_contract_theme_visual_language_varies_by_domain(self) -> None:
        base_spec = {
            "schema_version": "svglide-strategist-contract/v1",
            "page_type": "cover",
            "title": "Theme Cover",
            "key_message": "Theme-specific visual language should alter the SVG motif.",
            "layout_boxes": [
                {"id": "title", "role": "title", "x": 72, "y": 150, "width": 560, "height": 120},
                {"id": "body", "role": "body", "x": 76, "y": 284, "width": 520, "height": 72},
                {"id": "visual", "role": "visual", "x": 600, "y": 84, "width": 288, "height": 360},
                {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
            ],
        }
        cases = [
            ("新疆阿克苏城区生态居住区策划案", "theme-oasis-water-ribbon", "oasis_water_ribbon", "theme-ai-grid-field"),
            ("Global AI Capital 2026", "theme-ai-grid-field", "ai_grid_field", "theme-oasis-water-ribbon"),
            ("城市级低空物流网络策划案", "theme-logistics-air-lane-1", "logistics_air_lane", "theme-oasis-water-ribbon"),
        ]

        for deck_title, required_id, required_effect, forbidden_id in cases:
            with self.subTest(deck_title=deck_title):
                report = runtime.ComponentReport()
                svg = runtime.render_contract_slide(
                    page=1,
                    kind="cover",
                    title="",
                    summary="",
                    asset_id="layout.page_type.cover",
                    accent="#4A90E2",
                    spec=base_spec,
                    report=report,
                    deck_title=deck_title,
                )
                encoded_report = json.dumps(report.to_dict(), ensure_ascii=False)
                self.assertIn(f'id="{required_id}"', svg)
                self.assertIn(required_effect, encoded_report)
                self.assertNotIn(f'id="{forbidden_id}"', svg)

    def test_unseen_topics_extract_labels_from_brief_instead_of_defaulting(self) -> None:
        tea = {
            "title": "茶产业出海品牌策划",
            "key_message": "茶产业出海需要围绕产地故事、品牌信任、渠道试销、内容种草形成闭环",
        }
        ecommerce = {
            "title": "跨境电商增长方案",
            "key_message": "跨境电商增长聚焦选品矩阵、达人内容、物流履约、复购会员形成闭环",
        }

        tea_labels = runtime.topic_node_labels(tea, "茶产业出海品牌策划", count=4)
        ecommerce_labels = runtime.topic_node_labels(ecommerce, "跨境电商增长方案", count=4)
        tea_metrics = runtime.dashboard_metrics_for_topic(tea, "茶产业出海品牌策划")
        ecommerce_metrics = runtime.dashboard_metrics_for_topic(ecommerce, "跨境电商增长方案")
        tea_rows = runtime.comparison_rows_for_topic(tea, "茶产业出海品牌策划")

        self.assertIn("产地故事", tea_labels)
        self.assertIn("品牌信任", tea_labels)
        self.assertIn("选品矩阵", ecommerce_labels)
        self.assertIn("物流履约", ecommerce_labels)
        self.assertNotEqual(tea_labels, ecommerce_labels)
        self.assertNotEqual(tea_metrics, ecommerce_metrics)
        self.assertNotIn(("4", "关键抓手"), tea_metrics)
        self.assertEqual("产地故事", tea_rows[0][0])

    def test_contract_navigation_pages_emit_enough_semantic_labels_for_preview_lint(self) -> None:
        deck_title = "新疆阿克苏城区居住区策划案"
        cases = [
            (
                "cover",
                "cover",
                {
                    "page_type": "cover",
                    "title": "以水为脉·四时为序",
                    "key_message": "四境共生·四季归心的绿洲栖居范本",
                    "layout_boxes": [
                        {"id": "title", "role": "title", "x": 72, "y": 150, "width": 560, "height": 120},
                        {"id": "body", "role": "body", "x": 76, "y": 284, "width": 520, "height": 72},
                        {"id": "visual", "role": "visual", "x": 600, "y": 84, "width": 288, "height": 360},
                        {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
                    ],
                },
            ),
            (
                "agenda",
                "agenda",
                {
                    "page_type": "agenda",
                    "title": "目录",
                    "layout_boxes": [
                        {"id": "title", "role": "title", "x": 64, "y": 54, "width": 600, "height": 54},
                        {"id": "rail", "role": "timeline", "x": 96, "y": 136, "width": 48, "height": 312},
                        {"id": "body", "role": "body", "x": 154, "y": 126, "width": 650, "height": 330},
                        {"id": "visual", "role": "visual", "x": 820, "y": 156, "width": 64, "height": 64},
                        {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
                    ],
                },
            ),
            (
                "section",
                "section",
                {
                    "page_type": "section_divider",
                    "title": "01 项目核心定位与愿景",
                    "key_message": "以水串联四季，打造全季态生态居住区",
                    "layout_boxes": [
                        {"id": "section-number", "role": "kicker", "x": 72, "y": 92, "width": 160, "height": 90},
                        {"id": "title", "role": "title", "x": 180, "y": 188, "width": 600, "height": 88},
                        {"id": "body", "role": "body", "x": 184, "y": 292, "width": 560, "height": 38},
                        {"id": "visual", "role": "visual", "x": 0, "y": 320, "width": 960, "height": 180},
                        {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24},
                    ],
                },
            ),
        ]

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            for page, (kind, asset_id, spec) in enumerate(cases, 1):
                svg = runtime.render_contract_slide(
                    page=page,
                    kind=kind,
                    title="",
                    summary="",
                    asset_id=asset_id,
                    accent="#4A90E2",
                    spec={**spec, "_deck_title": deck_title},
                    report=runtime.ComponentReport(),
                    deck_title=deck_title,
                )
                source = preview_lint.SvgSource(page=page, label=f"page-{page}", root=ET.fromstring(svg), base_dir=project)
                codes = {check["code"] for check in preview_lint.lint_svg_source(project, source)}
                self.assertNotIn("unlabeled_visual_system", codes)

    def test_asset_marks_are_arc_free_and_reject_unknown_ids(self) -> None:
        spark = "".join(runtime.asset_mark("spark", 12, 24, 1.25, "#E63946", opacity=0.8))

        self.assertIn("<path", spark)
        self.assertIn('id="spark-1"', spark)
        self.assertNotRegex(spark, r'\sd="[^"]*[Aa](?=[\s,\d.+-])')

        with self.assertRaisesRegex(ValueError, "unknown asset mark"):
            runtime.asset_mark("missing", 0, 0, 1, "#000000")

    def test_path_rejects_arc_commands(self) -> None:
        with self.assertRaisesRegex(ValueError, "arc commands"):
            runtime.path("bad-arc", "M10 10 A20 20 0 0 1 30 30")

    def test_compose_cli_writes_supported_pages_and_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            kinds = [
                "cover",
                "editor_note",
                "kpi_cards",
                "bar_chart",
                "bubble_chart",
                "donut_chart",
                "sankey_chart",
                "hub_spoke",
                "closing",
            ]
            chart_assets = [
                "chart.kpi_cards",
                "chart.bar_chart",
                "chart.bubble_chart",
                "chart.donut_chart",
                "chart.sankey_chart",
                "chart.hub_spoke",
            ]
            plan.write_text(
                json.dumps(
                    {
                        "title": "Runtime Slice",
                        "design_pattern_selection": {"selected_assets": [{"id": asset} for asset in chart_assets]},
                        "slides": [
                            {
                                "page_kind": kind,
                                "title": kind.replace("_", " ").title(),
                                "summary": f"Compose fixture for {kind}",
                            }
                            for kind in kinds
                        ],
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["schema_version"], "svglide-gen-runtime-cache/v1")
            self.assertEqual(result["page_count"], len(kinds))
            self.assertEqual([page["page_kind"] for page in result["pages"]], kinds)

            for index in range(1, len(kinds) + 1):
                svg_path = project / "pages" / f"page-{index:03d}.svg"
                self.assertTrue(svg_path.exists())
                svg = svg_path.read_text(encoding="utf-8")
                self.assertIn('slide:role="slide"', svg)
                self.assertIn('viewBox="0 0 960 540"', svg)
                self.assertNotRegex(svg, r'<path\b[^>]*\sd="[^"]*[Aa](?=[\s,\d.+-])')
                ET.parse(svg_path)

            component_report = json.loads((project / "receipts" / "emitted_components.json").read_text(encoding="utf-8"))
            self.assertEqual(component_report["schema_version"], "svglide-component-report/v1")
            self.assertEqual(len(component_report["pages"]), len(kinds))
            self.assertGreaterEqual(component_report["summary"]["component_count"], 16)

            usage = json.loads((project / "receipts" / "design-pattern-usage.json").read_text(encoding="utf-8"))
            self.assertEqual(usage["schema_version"], "svglide-design-pattern-usage/v1")
            used_assets = {item["asset_id"] for item in usage["page_usages"]}
            self.assertTrue(set(chart_assets).issubset(used_assets))
            self.assertTrue(set(chart_assets).issubset(set(usage["used_asset_ids"])))

            cache = json.loads((project / "receipts" / "runtime-cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache, result)
            self.assertTrue(set(kinds).issubset(set(cache["supported_page_kinds"])))
            self.assertIn("agenda", cache["supported_page_kinds"])
            self.assertIn("section", cache["supported_page_kinds"])

    def test_compose_uses_real_slide_plan_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "title": "Field Mapping",
                        "slides": [
                            {
                                "page": 1,
                                "page_type": "chart",
                                "chart_type": "bar_chart",
                                "reference_asset": {"asset_id": "chart.bar_chart", "source": "svglide_design_pattern"},
                                "visual_plan": {
                                    "key_message": "Capex bar chart",
                                    "body": "Renderer should use chart_type and nested copy.",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            svg = (project / "pages" / "page-001.svg").read_text(encoding="utf-8")
            cache = json.loads((project / "receipts" / "runtime-cache.json").read_text(encoding="utf-8"))
            usage = json.loads((project / "receipts" / "design-pattern-usage.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["pages"][0]["page_kind"], "bar_chart")
            self.assertIn("Capex bar chart", svg)
            self.assertIn("Renderer should use chart_type", svg)
            self.assertEqual(usage["page_usages"][0]["asset_id"], "chart.bar_chart")

    def test_compose_uses_nested_reference_asset(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "title": "Nested Asset Mapping",
                        "slides": [
                            {
                                "page": 1,
                                "page_type": "content",
                                "visual_plan": {
                                    "page_kind": "editor_note",
                                    "reference_asset": {"asset_id": "layout.page_type.content", "source": "svglide_design_pattern"},
                                    "key_message": "Nested reference should drive the receipt",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            cache = json.loads((project / "receipts" / "runtime-cache.json").read_text(encoding="utf-8"))
            usage = json.loads((project / "receipts" / "design-pattern-usage.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["pages"][0]["page_kind"], "editor_note")
            self.assertEqual(cache["pages"][0]["asset_id"], "layout.page_type.content")
            self.assertEqual(usage["page_usages"][0]["asset_id"], "layout.page_type.content")

    def test_compose_uses_nested_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "title": "Nested Asset ID Mapping",
                        "slides": [
                            {
                                "page": 1,
                                "page_type": "chart",
                                "chart_type": "donut_chart",
                                "visual_plan": {
                                    "asset_id": "chart.donut_chart",
                                    "key_message": "Nested asset_id should drive the receipt",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            cache = json.loads((project / "receipts" / "runtime-cache.json").read_text(encoding="utf-8"))
            usage = json.loads((project / "receipts" / "design-pattern-usage.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["pages"][0]["page_kind"], "donut_chart")
            self.assertEqual(cache["pages"][0]["asset_id"], "chart.donut_chart")
            self.assertEqual(usage["page_usages"][0]["asset_id"], "chart.donut_chart")

    def test_compose_parameterizes_design_pattern_renderers_for_non_ai_topic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "runtime-project"
            project.mkdir()
            plan = project / "slide_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "title": "Aksu Oasis Living District",
                        "slides": [
                            {
                                "page_kind": "cover",
                                "title": "以水为脉 四时为序",
                                "summary": "阿克苏城区生态居住区策划案",
                                "kicker": "AKSU OASIS / RESIDENTIAL STRATEGY",
                                "meta_1": "OASIS PLANNING",
                                "meta_2": "FOUR SEASONS\nLIVING MAP",
                                "year": "2026",
                            },
                            {
                                "page_kind": "kpi_cards",
                                "title": "四季地块价值矩阵",
                                "metrics": [
                                    {"value": "4", "label": "四季地块", "note": "春夏秋冬差异化主题"},
                                    {"value": "1", "label": "水系闭环", "note": "串联全区公共空间"},
                                    {"value": "3", "label": "价值引擎", "note": "配套 景观 文化"},
                                    {"value": "全年龄", "label": "人群覆盖", "note": "儿童 青年 长者"},
                                ],
                                "insight": {
                                    "label": "PLANNING NOTE",
                                    "title": "水系不是装饰，\n是组织结构。",
                                    "copy": "用一条蓝绿生态脉络串联地块、配套和归家体验。",
                                    "number": "4境",
                                },
                            },
                            {
                                "page_kind": "sankey_chart",
                                "title": "水系如何转化为空间价值",
                                "origin": {"name": "水系", "value": "1环", "label": "ecological spine"},
                                "targets": [
                                    {"name": "春配套", "value": "繁"},
                                    {"name": "夏活力", "value": "乐"},
                                    {"name": "秋静谧", "value": "享"},
                                    {"name": "冬暖居", "value": "暖"},
                                ],
                                "return_flow": {"title": "归心体验", "value": "全年", "note": "four-season loop"},
                                "insight": "Water organizes the community into a legible four-season living loop.",
                            },
                            {
                                "page_kind": "hub_spoke",
                                "title": "四境联动系统",
                                "hub": {"value": "水脉", "label": "OASIS LOOP"},
                                "nodes": [
                                    {"name": "春之地块", "note": "配套入口"},
                                    {"name": "夏之地块", "note": "运动活力"},
                                    {"name": "秋之地块", "note": "胡杨静谧"},
                                    {"name": "冬之地块", "note": "暖廊归家"},
                                    {"name": "艾德莱斯", "note": "地域纹样"},
                                    {"name": "公共服务", "note": "全年龄覆盖"},
                                ],
                                "side_note": "四境共生 四季归心",
                                "side_index": "OASIS LOOP",
                            },
                            {
                                "page_kind": "closing",
                                "title": "总结与展望",
                                "takeaways": [
                                    "以水为脉组织归家体验",
                                    "四季地块形成差异化记忆",
                                    "胡杨与艾德莱斯强化地域识别",
                                    "配套共享覆盖全年龄需求",
                                    "生态景观提升长期溢价",
                                    "成为阿克苏人居升级样板",
                                ],
                                "critical_copy": "四境共生，四季归心。",
                                "sidebar": "OASIS\nLIVING\nAKSU",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            runtime.main(["compose", "--project", str(project), "--plan", "slide_plan.json"])

            all_svg = "\n".join(
                (project / "pages" / f"page-{index:03d}.svg").read_text(encoding="utf-8")
                for index in range(1, 6)
            )
            self.assertIn("AKSU OASIS", all_svg)
            self.assertIn("四季地块", all_svg)
            self.assertIn("水系不是装饰", all_svg)
            self.assertIn("归心体验", all_svg)
            self.assertIn("胡杨静谧", all_svg)
            self.assertIn("四境共生，四季归心", all_svg)
            self.assertNotIn("Global AI", all_svg)
            self.assertNotIn("Nvidia", all_svg)


if __name__ == "__main__":
    unittest.main()
