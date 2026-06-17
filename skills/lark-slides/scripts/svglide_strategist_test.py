# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import svglide_strategist as strategist


class SVGlideStrategistTest(unittest.TestCase):
    def test_build_contract_from_brief_and_page_descriptions(self) -> None:
        plan = strategist.build_contract(
            brief="Create an operations review with KPI dashboard, roadmap, and closing next steps.",
            page_descriptions=[
                "Cover: operating thesis and review scope",
                "KPI dashboard: four health metrics with micro trends",
                "Roadmap: three milestone phases and ownership",
                "Closing: next steps and decision request",
            ],
        )

        self.assertEqual("svglide-svg", plan["output_mode"])
        self.assertEqual("briefing", plan["mode"])
        self.assertEqual("briefing", plan["narrative_mode"])
        self.assertEqual("operational_dashboard", plan["visual_style"])
        self.assertEqual("svg", plan["asset_strategy"]["image_strategy"])
        self.assertEqual("svglide-source-pack/v1", plan["source_pack"]["schema_version"])
        self.assertEqual("user_prompt_only", plan["source_pack"]["source_status"])
        self.assertEqual(8, len(plan["strategy_locks"]))
        self.assertEqual(
            ["canvas", "page_count", "audience", "narrative_mode", "visual_style", "style_preset", "asset_strategy", "chart_policy"],
            [item["id"] for item in plan["strategy_locks"]],
        )
        self.assertEqual("raw_grid", plan["style_preset"])
        self.assertEqual({"background", "text", "accent"}, set(plan["style_system"]["palette"]).intersection({"background", "text", "accent"}))
        self.assertEqual(4, plan["page_count"])
        self.assertEqual(
            [
                {"page": 1, "rhythm": "anchor", "page_type": "cover"},
                {"page": 2, "rhythm": "dense", "page_type": "kpi_overview"},
                {"page": 3, "rhythm": "dense", "page_type": "roadmap"},
                {"page": 4, "rhythm": "anchor", "page_type": "closing"},
            ],
            plan["page_rhythm"],
        )
        self.assertEqual(["chart.vertical_list", "chart.kpi_cards", "chart.timeline", "chart.numbered_steps"], [asset["id"] for asset in plan["design_pattern_selection"]["selected_assets"]])
        self.assertTrue(all(asset["copy_policy"] == "derive_contract_only" for asset in plan["design_pattern_selection"]["selected_assets"]))
        self.assertTrue(all(asset["selection_reason"] for asset in plan["design_pattern_selection"]["selected_assets"]))

        dashboard = plan["slides"][1]
        self.assertEqual("KPI dashboard: four health metrics with micro trends", dashboard["key_message"])
        self.assertEqual("dense", dashboard["page_rhythm"])
        self.assertEqual("kpi_overview", dashboard["page_type"])
        self.assertEqual("", dashboard["chart_type"])
        self.assertEqual({"layout_box_role": "chart", "description": "KPI dashboard grid with hero metrics and micro trends"}, dashboard["main_visual_anchor"])
        self.assertEqual("kpi_overview / dashboard_kpi_grid / chart.kpi_cards", dashboard["visual_signature"])
        self.assertEqual(["typography", "chart_geometry"], dashboard["svg_effects"])
        self.assertEqual("fake_ui_dashboard", dashboard["visual_recipe"])
        self.assertEqual("chart.kpi_cards", dashboard["reference_asset"]["asset_id"])
        self.assertEqual(["brief"], dashboard["source_refs"])
        self.assertIn("chart.kpi_cards is selected", dashboard["asset_selection_reason"])
        self.assertEqual("not_required", dashboard["chart_decision"]["status"])
        self.assertIn("main text and chart labels stay inside safe area", dashboard["layout_guardrails"])
        self.assertEqual(
            {
                "schema_version": "svglide-visual-design-contract/v1",
                "page_kind": "kpi_overview",
                "visual_thesis": "KPI dashboard: four health metrics with micro trends",
                "composition_archetype": "data_stage",
                "pattern_bundle": ["chart.kpi_cards"],
                "density": "dense",
                "primary_motif": "metric_grid",
                "required_visual_evidence": ["metric_hierarchy", "chart_geometry", "dashboard_grid"],
                "renderer_id": "dashboard_kpi_grid",
                "layout_seed_id": "dashboard_kpi_grid",
                "visual_recipe": "fake_ui_dashboard",
                "style_preset": "raw_grid",
            },
            dashboard["visual_design_contract"],
        )

        chart_contracts = strategist.load_catalogs()["chart_type_contracts"]
        allowed_rhythms = {"anchor", "breathing", "dense"}
        for slide in plan["slides"]:
            self.assertIn(slide["page_rhythm"], allowed_rhythms)
            if slide["chart_type"]:
                self.assertIn(slide["chart_type"], chart_contracts)

    def test_brief_hex_colors_drive_style_system_palette(self) -> None:
        plan = strategist.build_contract(
            brief="新疆阿克苏城区居住区策划案，主色澄澈水蓝 #4A90E2，辅色春芽嫩绿 #8BC34A，强调色艾德莱斯绸朱红 #E91E63。",
            page_descriptions=["Cover: 以水为脉·四时为序"],
        )

        palette = plan["style_system"]["palette"]
        self.assertEqual("#4A90E2", palette["accent"])
        self.assertEqual(["#8BC34A", "#E91E63"], palette["support"])
        self.assertEqual("brief_hex_colors", plan["style_system"]["palette_source"])

    def test_visual_style_does_not_pollute_narrative_mode(self) -> None:
        plan = strategist.build_contract(
            brief="Global AI capital market data report.",
            slide_plan={
                "mode": "data_journalism",
                "visual_style": "data_journalism",
                "slides": [{"title": "Capital Flow", "description": "chart page with bar chart", "chart_type": "bar_chart"}],
            },
        )

        self.assertEqual("briefing", plan["mode"])
        self.assertEqual("briefing", plan["narrative_mode"])
        self.assertEqual("data_journalism", plan["visual_style"])
        slide = plan["slides"][0]
        self.assertEqual("required", slide["chart_decision"]["status"])
        self.assertEqual("bar_chart", slide["chart_decision"]["chart_type"])
        self.assertTrue(slide["chart_decision"]["reason"])
        self.assertEqual("brief", slide["chart_decision"]["data_ref"])
        self.assertEqual("required", slide["chart_verification"]["status"])

    def test_complete_existing_plan_preserves_manual_fields(self) -> None:
        base = {
            "title": "Pipeline Decision",
            "style_preset": "monochrome",
            "slides": [
                {
                    "page": 1,
                    "title": "Keep this title",
                    "page_type": "custom_decision",
                    "chart_type": "comparison_table",
                    "visual_recipe": "geometric_composition",
                    "reference_asset": {"source": "manual", "asset_id": "chart.comparison_table", "usage": "approved"},
                }
            ],
        }

        plan = strategist.build_contract(brief="Compare two launch options.", slide_plan=base)
        slide = plan["slides"][0]

        self.assertEqual("monochrome", plan["style_preset"])
        self.assertEqual("pyramid", plan["mode"])
        self.assertEqual("Keep this title", slide["title"])
        self.assertEqual("custom_decision", slide["page_type"])
        self.assertEqual("comparison_table", slide["chart_type"])
        self.assertEqual("geometric_composition", slide["visual_recipe"])
        self.assertEqual({"source": "manual", "asset_id": "chart.comparison_table", "usage": "approved"}, slide["reference_asset"])
        self.assertIn("layout_boxes", slide)
        self.assertIn("footer_safe_zone", slide)
        self.assertIn("layout_guardrails", slide)

    def test_existing_plan_refreshes_seed_derived_contract_fields(self) -> None:
        base = {
            "slides": [
                {
                    "description": "KPI dashboard with secondary metric cards and chart labels",
                    "seed_id": "dashboard_kpi_grid",
                    "layout_boxes": [
                        {"id": "title", "role": "title", "x": 48, "y": 34, "width": 864, "height": 48},
                        {"id": "primary-kpi", "role": "metric", "x": 64, "y": 106, "width": 260, "height": 128},
                        {"id": "secondary-grid", "role": "grid", "x": 348, "y": 106, "width": 548, "height": 128},
                    ],
                    "text_budget_by_role": {
                        "metric": {"max_chars": 80, "max_lines": 3, "max_boxes": 1, "min_font_px": 12},
                    },
                }
            ]
        }

        plan = strategist.build_contract(brief="KPI dashboard", slide_plan=base)
        slide = plan["slides"][0]

        self.assertIn("secondary-metric-grid", [box["id"] for box in slide["layout_boxes"]])
        self.assertEqual(7, slide["text_budget_by_role"]["metric"]["max_boxes"])
        self.assertEqual(4, slide["text_budget_by_role"]["chart"]["max_boxes"])

    def test_normalizes_none_chart_type_to_empty_contract(self) -> None:
        plan = strategist.build_contract(
            brief="Brand showcase opening.",
            slide_plan={"slides": [{"title": "Opening", "chart_type": "none"}]},
        )

        self.assertEqual("", plan["slides"][0]["chart_type"])

    def test_classifies_agenda_and_section_as_first_class_profiles(self) -> None:
        plan = strategist.build_contract(
            brief="新疆阿克苏城区居住区策划案，包含目录和章节过渡。",
            page_descriptions=[
                "Cover: 以水为脉·四时为序",
                "目录：项目核心定位、春之地块、夏之地块、秋之地块、冬之地块",
                "章节过渡页：01 项目核心定位与愿景",
            ],
        )

        agenda = plan["slides"][1]
        section = plan["slides"][2]

        self.assertEqual("agenda", agenda["page_type"])
        self.assertEqual("agenda_numbered_path", agenda["seed_id"])
        self.assertEqual("indexed_path", agenda["visual_design_contract"]["composition_archetype"])
        self.assertEqual(["numbered_path", "section_index", "semantic_labels"], agenda["visual_design_contract"]["required_visual_evidence"])
        self.assertEqual("chart.agenda_list", agenda["reference_asset"]["asset_id"])

        self.assertEqual("section_divider", section["page_type"])
        self.assertEqual("section_divider_index", section["seed_id"])
        self.assertEqual("section_signal", section["visual_design_contract"]["composition_archetype"])
        self.assertEqual(["section_index", "hero_signal", "full_page_archetype"], section["visual_design_contract"]["required_visual_evidence"])
        self.assertEqual("chart.numbered_steps", section["reference_asset"]["asset_id"])

    def test_cli_reads_text_and_plan_and_writes_clean_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            brief_path = tmp / "brief.txt"
            plan_path = tmp / "slide_plan.json"
            out_path = tmp / "contract.json"
            brief_path.write_text("Technical KPI dashboard for weekly status.", encoding="utf-8")
            plan_path.write_text(json.dumps({"slides": [{"title": "Status", "description": "KPI dashboard with micro bars"}]}), encoding="utf-8")

            exit_code = strategist.main(["--brief", str(brief_path), "--plan", str(plan_path), "--output", str(out_path)])

            self.assertEqual(0, exit_code)
            result = json.loads(out_path.read_text(encoding="utf-8"))
            encoded = json.dumps(result, ensure_ascii=False).lower()
            self.assertEqual("fake_ui_dashboard", result["slides"][0]["visual_recipe"])
        self.assertNotIn("source" + "_token", encoded)
        self.assertNotIn("beautiful" + "-feishu-whiteboard", encoded)
        self.assertNotIn("ppt" + "-master", encoded)
        self.assertNotIn("hugo" + "he3", encoded)

    def test_preserves_manual_visual_design_contract_and_fills_missing_fields(self) -> None:
        plan = strategist.build_contract(
            brief="AI capital market briefing with one chart.",
            slide_plan={
                "slides": [
                    {
                        "title": "Capital Flow",
                        "chart_type": "bar_chart",
                        "visual_design_contract": {
                            "visual_thesis": "Manual thesis",
                            "composition_archetype": "manual_data_stage",
                            "required_visual_evidence": ["custom_evidence"],
                        },
                    }
                ]
            },
        )

        contract = plan["slides"][0]["visual_design_contract"]

        self.assertEqual("Manual thesis", contract["visual_thesis"])
        self.assertEqual("manual_data_stage", contract["composition_archetype"])
        self.assertEqual(["custom_evidence", "chart_geometry", "insight_strip", "full_page_archetype"], contract["required_visual_evidence"])
        self.assertEqual(["chart.bar_chart"], contract["pattern_bundle"])
        self.assertEqual("dense", contract["density"])
        self.assertEqual("takeaway_chart", contract["primary_motif"])
        self.assertEqual(plan["style_preset"], contract["style_preset"])


if __name__ == "__main__":
    unittest.main()
