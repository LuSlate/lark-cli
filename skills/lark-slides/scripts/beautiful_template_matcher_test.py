# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beautiful_template_asset_extractor
import beautiful_template_matcher


REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


def load_json(name: str) -> dict:
    return json.loads((REFERENCES_DIR / name).read_text(encoding="utf-8"))


class BeautifulTemplateMatcherTest(unittest.TestCase):
    def test_phase0_contract_files_exist(self) -> None:
        for name in [
            "beautiful-html-template-families.schema.json",
            "component-registry.schema.json",
            "asset-strategy-registry.schema.json",
            "asset-slot-contract.schema.json",
            "beautiful-html-template-cleanup-map.json",
            "beautiful-html-template-cleanup-map.schema.json",
            "beautiful-template-issue-codes.json",
            "component-registry.json",
            "asset-strategy-registry.json",
            "font-fallback-policy.json",
        ]:
            self.assertTrue((REFERENCES_DIR / name).exists(), name)

    def test_issue_codes_include_m13_m14_contract_freeze(self) -> None:
        issue_codes = load_json("beautiful-template-issue-codes.json")["phase_0_contract_freeze"]
        for code in [
            "asset_slot_unfilled",
            "preview_missing_required_image",
            "generated_bitmap_not_real_image",
            "semantic_mismatch",
            "asset_source_type_not_allowed",
            "live_submit_missing_file_token",
            "unowned_decorative_primitive",
            "decorative_motif_overuse",
        ]:
            self.assertIn(code, issue_codes)

    def test_extractor_reads_all_beautiful_templates(self) -> None:
        registry = beautiful_template_asset_extractor.extract_registry()
        self.assertEqual(registry["version"], "beautiful-html-template-families/v1")
        self.assertEqual(registry["source"]["template_count"], 34)
        self.assertEqual(len(registry["families"]), 34)
        self.assertEqual(registry["source"]["absorbed_family_count"], 15)

    def test_extractor_preserves_inventory_and_absorption_provenance(self) -> None:
        registry = beautiful_template_asset_extractor.extract_registry()
        families = {family["template_id"]: family for family in registry["families"]}
        blue = families["blue-professional"]

        self.assertEqual(blue["status"], "absorbed")
        self.assertEqual(blue["claim_level"], "svglide_absorbed")
        self.assertTrue(blue["source"]["inventory_item_ids"])
        self.assertIn("skills/lark-slides/references/absorptions/beautiful-html-templates/blue-professional.executive-dashboard.json", blue["source"]["absorption_records"])
        self.assertIn("beautiful-html-templates.template.blue-professional.design.md", blue["source"]["source_item_ids"])
        self.assertTrue(blue["source"]["absorption_provenance"][0]["sha256"])
        self.assertIn("template.executive-dashboard", blue["svglide_mapping"]["svglide_asset_ids"])
        self.assertIn("beautiful-html-templates.template.blue-professional.design.md", blue["svglide_mapping"]["source_item_ids"])

    def test_family_registry_extracts_design_assets_not_only_html(self) -> None:
        family = beautiful_template_matcher.load_family("blue-professional")
        self.assertTrue(family["source"]["source_template_json"].endswith("template.json"))
        self.assertTrue(family["source"]["source_design_md"].endswith("design.md"))
        self.assertTrue(family["source"]["source_template_html"].endswith("template.html"))
        self.assertTrue(family["source"]["source_screenshots"])
        self.assertTrue(family["visual_dna"]["palette_roles"])
        self.assertTrue(family["visual_dna"]["typography_roles"])
        self.assertTrue(family["visual_dna"]["decorative_motifs"])
        self.assertTrue(family["visual_dna"]["visual_effects"])
        self.assertTrue(family["visual_dna"]["screenshot_benchmarks"])
        self.assertTrue(all("lowering_policy" in item for item in family["visual_dna"]["visual_effects"]))
        self.assertTrue(family["design_tokens"]["colors"])
        self.assertTrue(family["design_tokens"]["typography"])
        self.assertTrue(family["design_tokens"]["css_variables"])
        self.assertTrue(family["design_tokens"]["css_class_names"])
        self.assertTrue(family["layout_variants"])
        palette_blob = json.dumps(family["visual_dna"]["palette_roles"], ensure_ascii=False)
        self.assertNotIn("source-defined", palette_blob)

    def test_all_families_have_runtime_and_font_policy(self) -> None:
        families = beautiful_template_matcher.load_families()
        self.assertEqual(len(families), 34)
        blob = json.dumps(families, ensure_ascii=False)
        self.assertNotIn("fonts.googleapis.com", blob)
        self.assertNotIn("@font-face", blob)
        for family in families:
            self.assertFalse(family["runtime_policy"]["direct_satori_svg_allowed"])
            self.assertTrue(family["runtime_policy"]["requires_contract_compile"])
            self.assertEqual(family["font_policy"]["fallback_stack"], "system-sans-cjk")
            self.assertGreaterEqual(len(family["variants"]), 8)
            self.assertTrue(family["design_tokens"]["colors"], family["template_id"])
            self.assertTrue(family["layout_variants"], family["template_id"])
            self.assertGreaterEqual(len(family["component_candidates"]), 5)

    def test_internal_review_matches_business_templates(self) -> None:
        result = beautiful_template_matcher.match_templates("内部业务复盘，管理层阅读，有指标、问题、原因、后续动作", limit=3)
        ids = [item["template_id"] for item in result["matches"]]
        self.assertTrue({"blue-professional", "emerald-editorial", "signal"} & set(ids))
        self.assertEqual(result["query_signals"]["content_type"], "internal_review")
        self.assertIn("metrics", result["query_signals"]["needs"])

    def test_cultural_event_does_not_match_business_first(self) -> None:
        result = beautiful_template_matcher.match_templates("青年艺术展活动介绍，视觉要大胆，有海报感", limit=3)
        ids = [item["template_id"] for item in result["matches"]]
        self.assertNotEqual(ids[0], "blue-professional")
        self.assertTrue(any(item in ids for item in ["biennale-yellow", "bold-poster", "stencil-tablet", "studio"]))

    def test_matcher_covers_24_representative_theme_prompts(self) -> None:
        cases = [
            ("内部业务复盘，给管理层看，有指标、问题、原因、后续动作", {"blue-professional", "signal", "emerald-editorial"}),
            ("季度经营 review，董事会阅读，正式、克制、需要 KPI dashboard", {"blue-professional", "signal", "editorial-forest"}),
            ("投资人材料，讲财务进展和风险，偏 institutional", {"signal", "blue-professional", "cartesian"}),
            ("用户研究 synthesis，访谈洞察、证据卡片、定性结论", {"monochrome", "vellum", "pin-and-paper"}),
            ("青年艺术展 exhibition proposal，美术馆策展语气", {"biennale-yellow", "stencil-tablet", "studio"}),
            ("品牌宣言 poster，像 magazine cover，一页要有冲击力", {"bold-poster", "broadside", "coral"}),
            ("案例证据 field board，贴纸、手作、notebook 氛围", {"pin-and-paper", "retro-zine", "scatterbrain"}),
            ("高密度 comparison matrix，产品能力对比表", {"raw-grid", "cartesian", "neo-grid-bold"}),
            ("复古游戏 arcade hackathon demo，cyberpunk neon", {"8-bit-orbit", "retro-windows", "sakura-chroma"}),
            ("白板 brainstorm workshop，总结想法和下一步", {"scatterbrain", "daisy-days", "pin-and-paper"}),
            ("香港小吃 food menu，餐厅推荐，温暖但有信息密度", {"long-table", "playful", "coral"}),
            ("fashion magazine editorial spread，时尚品牌季度故事", {"editorial-tri-tone", "coral", "pink-script"}),
            ("学术研究报告 scholarly policy brief，严肃、可读", {"vellum", "cartesian", "signal"}),
            ("SaaS 产品 launch deck，设计感强，给 founder pitch", {"block-frame", "neo-grid-bold", "raw-grid", "blue-professional"}),
            ("creative agency studio credentials，展示作品集和方法论", {"creative-mode", "studio", "neo-grid-bold"}),
            ("社区公益 campaign，people platform，倡议和行动号召", {"peoples-platform", "broadside", "playful"}),
            ("organic wellness brand lifestyle deck，健康生活方式", {"grove", "mat", "soft-editorial"}),
            ("教育 training lesson workshop，亲和、轻松、鼓励", {"daisy-days", "playful", "scatterbrain"}),
            ("archive archival history deck，文献、档案、历史资料", {"stencil-tablet", "vellum", "cartesian"}),
            ("vintage Japanese cassette product story，80s 日系包装感", {"sakura-chroma", "retro-zine", "retro-windows"}),
            ("nightlife nocturnal editorial，夜间活动和 sultry 氛围", {"pink-script", "studio", "coral"}),
            ("设计系统变更说明，dense table 和工程矩阵", {"raw-grid", "cartesian", "neo-grid-bold"}),
            ("温暖餐桌 long-table event programme，社区晚餐流程", {"long-table", "playful", "grove"}),
            ("MiniMax 和智谱产品对比，需要公司 identity 和真实图策略", {"blue-professional", "raw-grid", "neo-grid-bold", "signal"}),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                result = beautiful_template_matcher.match_templates(query, limit=3)
                ids = {item["template_id"] for item in result["matches"]}
                self.assertTrue(ids & expected, f"{query}: got {ids}, expected one of {expected}")

    def test_recommended_deck_has_multiple_variants_for_review(self) -> None:
        result = beautiful_template_matcher.plan_with_template_family("内部业务复盘", page_count=10)
        variants = [slide["template_variant"] for slide in result["slides"]]
        self.assertGreaterEqual(len(set(variants)), 6)
        self.assertIn("metric_dashboard", variants)
        self.assertIn("problem_analysis", variants)
        self.assertIn("action_plan", variants)

    def test_semantic_blocks_select_expected_components(self) -> None:
        blocks = [
            {"block_id": "m1", "type": "metric", "content": "DAU 同比增长 18%"},
            {"block_id": "f1", "type": "finding", "content": "新增主要来自渠道 A"},
            {"block_id": "a1", "type": "action", "content": "下阶段提升留存"},
        ]
        selected = beautiful_template_matcher.select_components(blocks)
        ids = [item["component_id"] for item in selected]
        self.assertIn("metric_card", ids)
        self.assertIn("finding_callout", ids)
        self.assertIn("action_list", ids)

    def test_asset_strategy_uses_chart_only_when_data_exists(self) -> None:
        strategy = beautiful_template_matcher.choose_asset_strategy(
            semantic_block={"type": "metric", "content": "增长明显，但没有具体数字"},
            data_available=False,
        )
        self.assertEqual(strategy["strategy_id"], "structured_fallback")
        self.assertTrue(strategy["no_fake_data"])

    def test_company_topic_requires_real_image_or_identity_fallback(self) -> None:
        strategy = beautiful_template_matcher.choose_asset_strategy(
            semantic_block={"type": "company", "content": "智谱和 MiniMax 产品对比"},
            data_available=False,
        )
        self.assertIn(strategy["strategy_id"], ["real_image_required", "identity_structured_fallback"])
        self.assertIn("fallback_if_missing", strategy)

    def test_golden_plans_lock_template_fields(self) -> None:
        for name in [
            "examples/beautiful-template-internal-review-plan.json",
            "examples/beautiful-template-zhipu-minimax-plan.json",
        ]:
            plan = load_json(name)
            self.assertTrue(plan["template_family_selection"]["enabled"])
            self.assertIn("selected_template_id", plan["template_family_selection"])
            self.assertGreaterEqual(plan["target_slide_count"], 10)
            self.assertEqual(len(plan["slides"]), plan["target_slide_count"])
            self.assertGreaterEqual(len({slide["template_variant"] for slide in plan["slides"]}), 6)
            for slide in plan["slides"]:
                self.assertIn("template_variant", slide)
                self.assertIn("semantic_blocks", slide)
                self.assertIn("component_selection", slide)
                self.assertIn("asset_strategy", slide)


if __name__ == "__main__":
    unittest.main()
