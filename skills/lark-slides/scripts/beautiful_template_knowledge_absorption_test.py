# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beautiful_template_asset_extractor
import beautiful_template_e2e_dry_run
import beautiful_template_matcher
import beautiful_template_runtime
import svglide_prompt_planner
import svglide_quality_gate
import svglide_theme_template_selector
import svg_preflight
import beautiful_template_runtime


REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"
SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")
REQUIRED_M15_CODES = {
    "cross_family_layout_mix",
    "missing_extension_grammar",
    "remote_font_dependency",
    "cjk_fake_italic",
    "cjk_letter_spacing_inherited",
    "cjk_mixed_run_spacing_missing",
    "family_recolor_without_override",
    "source_inventoried_claim_escalation",
    "missing_screenshot_benchmark_role",
}
REQUIRED_BENCHMARK_ROLES = {"cover_reference", "mid_deck_reference", "late_deck_reference"}


def load_json(name: str) -> dict:
    return json.loads((REFERENCES_DIR / name).read_text(encoding="utf-8"))


def family_by_id(registry: dict) -> dict[str, dict]:
    return {family["template_id"]: family for family in registry["families"]}


def all_issue_codes(payload: object) -> set[str]:
    codes: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"code", "id"} and isinstance(value, str):
                codes.add(value)
            elif isinstance(value, str) and key.endswith("codes"):
                codes.add(value)
            else:
                codes.update(all_issue_codes(value))
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                codes.add(item)
            else:
                codes.update(all_issue_codes(item))
    return codes


def issue_codes(result: dict) -> set[str]:
    codes: set[str] = set()
    for issue in result.get("issues", []):
        if isinstance(issue, dict) and issue.get("code"):
            codes.add(issue["code"])
    return codes


class BeautifulTemplateKnowledgeAbsorptionTest(unittest.TestCase):
    def test_blue_professional_promotes_to_production_theme_through_gate(self) -> None:
        registry = load_json("beautiful-html-template-families.json")
        family = family_by_id(registry)["blue-professional"]

        candidate = beautiful_template_runtime.theme_promotion_candidate(family)
        promoted = {item["id"]: item for item in beautiful_template_runtime.promoted_theme_records()}

        self.assertEqual("blue-professional", candidate["source_family"])
        self.assertEqual("has_theme_mapping", candidate["promotion_status"])
        self.assertIn("theme.blue-professional", family["svglide_mapping"]["svglide_asset_ids"])
        self.assertIn("blue-professional", promoted)
        self.assertEqual("production", promoted["blue-professional"]["status"])
        self.assertEqual("trusted", promoted["blue-professional"]["quality_tier"])

    def test_source_inventory_only_family_cannot_promote_theme(self) -> None:
        records = beautiful_template_runtime.promoted_theme_records()
        source_families = {item["source_family"] for item in records}

        for family_id in ["8-bit-orbit", "block-frame", "capsule"]:
            self.assertNotIn(family_id, source_families)

    def test_issue_codes_freeze_m15_contract(self) -> None:
        codes = all_issue_codes(load_json("beautiful-template-issue-codes.json"))
        self.assertTrue(REQUIRED_M15_CODES <= codes, REQUIRED_M15_CODES - codes)

    def test_all_families_have_cjk_policy_usage_policy_and_extension_grammar(self) -> None:
        registry = load_json("beautiful-html-template-families.json")
        self.assertEqual(len(registry["families"]), 34)
        cjk_signatures: set[str] = set()
        extension_signatures: set[str] = set()
        for family in registry["families"]:
            with self.subTest(family=family["template_id"]):
                cjk = family.get("cjk_policy")
                usage = family.get("family_usage_policy")
                grammar = family.get("extension_grammar")
                self.assertIsInstance(cjk, dict)
                self.assertIsInstance(usage, dict)
                self.assertIsInstance(grammar, dict)
                for key in [
                    "strategy",
                    "display_font_cn",
                    "body_font_cn",
                    "runtime_font_policy",
                    "emphasis_policy",
                    "italic_policy",
                    "letter_spacing_policy",
                    "mixed_run_spacing",
                    "known_degradation",
                    "source_section_sha256",
                ]:
                    self.assertTrue(cjk.get(key), f"{family['template_id']} missing cjk_policy.{key}")
                self.assertEqual(cjk["runtime_font_policy"], "system_font_only_no_remote_dependency")
                self.assertTrue(usage.get("closed_visual_system"))
                self.assertFalse(usage.get("cross_family_layout_mix_allowed"))
                self.assertFalse(usage.get("recolor_allowed"))
                self.assertFalse(usage.get("font_substitution_allowed"))
                self.assertTrue(usage.get("extend_missing_layout_policy", {}).get("same_component_grammar"))
                for key in [
                    "layout_rhythm",
                    "spacing_rhythm",
                    "component_grammar",
                    "chrome_rules",
                    "decorative_vocabulary",
                    "allowed_new_layouts",
                    "forbidden_mutations",
                    "source_basis",
                ]:
                    self.assertTrue(grammar.get(key), f"{family['template_id']} missing extension_grammar.{key}")
                cjk_signatures.add(json.dumps(cjk, sort_keys=True, ensure_ascii=False))
                extension_signatures.add(json.dumps(grammar, sort_keys=True, ensure_ascii=False))
        self.assertGreaterEqual(len(cjk_signatures), 20)
        self.assertGreaterEqual(len(extension_signatures), 20)

    def test_screenshot_benchmarks_have_cover_mid_late_roles(self) -> None:
        for family in load_json("beautiful-html-template-families.json")["families"]:
            benchmarks = family["visual_dna"]["screenshot_benchmarks"]
            roles = {item.get("role") for item in benchmarks}
            with self.subTest(family=family["template_id"]):
                self.assertEqual(roles, REQUIRED_BENCHMARK_ROLES)
                for item in benchmarks:
                    self.assertRegex(item["path"], rf"beautiful-html-templates/screenshots/{family['template_id']}-\d+\.png")
                    self.assertIsInstance(item.get("slide_number"), int)
                    self.assertGreater(item["slide_number"], 0)
                    self.assertTrue(item.get("why_selected"))
                    self.assertTrue(item.get("visual_targets"))
                    self.assertTrue(item.get("acceptance_use"))
                    self.assertNotEqual(item.get("role"), "reference")

    def test_cjk_policy_contains_no_remote_font_runtime_dependency(self) -> None:
        registry = load_json("beautiful-html-template-families.json")
        for family in registry["families"]:
            cjk = family["cjk_policy"]
            runtime_blob = json.dumps(
                {
                    "runtime_font_policy": cjk.get("runtime_font_policy"),
                    "runtime_font_stack": cjk.get("runtime_font_stack"),
                    "font_role_map": family.get("font_policy", {}).get("font_role_map"),
                },
                ensure_ascii=False,
            )
            with self.subTest(family=family["template_id"]):
                self.assertNotIn("fonts.googleapis.com", runtime_blob)
                self.assertNotIn("@font-face", runtime_blob)
                self.assertNotIn("http://", runtime_blob)
                self.assertNotIn("https://", runtime_blob)

    def test_source_inventoried_families_do_not_claim_absorbed(self) -> None:
        for family in load_json("beautiful-html-template-families.json")["families"]:
            if family["status"] == "source_inventoried":
                self.assertEqual(family["claim_level"], "source_inventory_only", family["template_id"])
                self.assertFalse(family.get("svglide_mapping", {}).get("svglide_asset_ids"), family["template_id"])

    def test_blue_professional_has_passed_theme_promotion_gate(self) -> None:
        registry = load_json("beautiful-html-template-families.json")
        family = family_by_id(registry)["blue-professional"]

        candidate = beautiful_template_runtime.theme_promotion_candidate(family)

        self.assertEqual("blue-professional", candidate["source_family"])
        self.assertEqual("passed", candidate["promotion_gate"]["status"])
        self.assertEqual("blue-professional", candidate["theme_token"]["theme_id"])
        self.assertIn("theme.blue-professional", family["svglide_mapping"]["svglide_asset_ids"])
        for key in ("source_trace", "semantic_fit", "visual_dna", "cjk_policy", "family_usage_policy"):
            self.assertTrue(candidate[key], key)

    def test_all_source_inventory_only_families_cannot_promote_theme(self) -> None:
        records = beautiful_template_runtime.promoted_theme_records()
        promoted_sources = {item["source_family"] for item in records}
        registry = load_json("beautiful-html-template-families.json")

        source_inventory_only = {
            family["template_id"]
            for family in registry["families"]
            if family["claim_level"] == "source_inventory_only"
        }

        self.assertTrue(source_inventory_only)
        self.assertTrue(promoted_sources.isdisjoint(source_inventory_only))

    def test_extractor_reads_cjk_sections_from_all_design_md(self) -> None:
        registry = beautiful_template_asset_extractor.extract_registry()
        self.assertEqual(len(registry["families"]), 34)
        for family in registry["families"]:
            with self.subTest(family=family["template_id"]):
                cjk = family.get("cjk_policy", {})
                self.assertEqual(cjk.get("source_section_heading"), "CJK & International Content")
                self.assertTrue(cjk.get("source_section_sha256"))
                self.assertIn(cjk.get("mixed_run_spacing"), {"pangu_spacing", "none_required"})
                self.assertIn("letter", cjk.get("letter_spacing_policy", ""))
                self.assertTrue(cjk.get("known_degradation"))

    def test_extractor_assigns_screenshot_benchmark_roles(self) -> None:
        registry = beautiful_template_asset_extractor.extract_registry()
        for family in registry["families"]:
            roles = {item.get("role") for item in family["visual_dna"]["screenshot_benchmarks"]}
            self.assertEqual(roles, REQUIRED_BENCHMARK_ROLES, family["template_id"])

    def test_matcher_outputs_policy_summaries_without_claim_escalation(self) -> None:
        result = beautiful_template_matcher.match_templates("内部业务复盘，管理层阅读，有指标、问题、原因、后续动作", limit=5)
        self.assertGreaterEqual(len(result["matches"]), 3)
        for match in result["matches"]:
            with self.subTest(match=match["template_id"]):
                self.assertIn(match.get("claim_level"), {"svglide_absorbed", "source_inventory_only"})
                self.assertTrue(match.get("family_usage_policy_summary"))
                self.assertTrue(match.get("cjk_policy_summary"))
                self.assertTrue(match.get("extension_grammar_summary"))
                self.assertEqual(set(match.get("benchmark_roles", [])), REQUIRED_BENCHMARK_ROLES)
                if match.get("status") == "source_inventoried":
                    self.assertEqual(match["claim_level"], "source_inventory_only")

    def test_prompt_context_includes_policy_summaries(self) -> None:
        templates = svglide_prompt_planner.template_registry_bundle()
        self.assertTrue(templates)
        sample = next((item for item in templates if item.get("source_template_id")), None)
        self.assertIsNotNone(sample)
        for key in [
            "source_template_id",
            "claim_level",
            "family_usage_policy_summary",
            "cjk_policy_summary",
            "extension_grammar_summary",
            "benchmark_roles",
        ]:
            self.assertIn(key, sample)
        family_context = svglide_prompt_planner.template_family_policy_context_bundle()
        self.assertEqual(len(family_context), 34)

    def test_theme_template_selector_preserves_policy_fields(self) -> None:
        templates = [
            item
            for item in svglide_theme_template_selector.load_template_registry().get("templates", [])
            if isinstance(item, dict) and item.get("source_template_id")
        ]
        self.assertTrue(templates)
        scored = svglide_theme_template_selector.score_template({}, templates[0], brief="内部复盘")
        for key in [
            "source_template_id",
            "claim_level",
            "family_usage_policy_summary",
            "cjk_policy_summary",
            "extension_grammar_summary",
            "benchmark_roles",
        ]:
            self.assertIn(key, scored)

    def test_quality_gate_blocks_m15_preflight_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            check_path = project / "06-check/preflight.json"
            check_path.parent.mkdir(parents=True, exist_ok=True)
            check_path.write_text(
                json.dumps(
                    {
                        "summary": {"error_count": 0},
                        "plan": {"issues": [{"level": "error", "code": "cross_family_layout_mix"}]},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            check = svglide_quality_gate.load_check(project, "preflight", Path("06-check/preflight.json"), required=True, profile="production")
        codes = {issue["code"] for issue in check["issues"]}
        self.assertIn("m15_policy_gate_failed", codes)

    def test_preflight_rejects_family_usage_misuse(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            "template_family_selection": {
                "enabled": True,
                "source": "beautiful-html-template-families",
                "selected_template_id": "blue-professional",
                "claim_level": "svglide_absorbed",
                "palette_override": {"primary": "#ff0000"},
            },
            "slides": [
                {
                    "page": 1,
                    "title": "复盘",
                    "template_family_id": "studio",
                    "template_variant": "custom_risk_board",
                    "variant_source": "generated_extension",
                    "semantic_blocks": [{"block_id": "title_1", "type": "title", "content": "复盘"}],
                    "component_selection": [{"component_id": "title_block", "binds": ["title_1"]}],
                    "asset_strategy": {"strategy_id": "structured_fallback", "no_fake_data": True},
                    "asset_contract": "none_required",
                    "risk_flags": [],
                    "source_policy": "prompt only",
                    "content_density_contract": "medium-density structured template page",
                }
            ],
        }
        codes = issue_codes(svg_preflight.lint_plan(plan))
        self.assertIn("cross_family_layout_mix", codes)
        self.assertIn("missing_extension_grammar", codes)
        self.assertIn("family_recolor_without_override", codes)

    def test_preflight_rejects_source_inventoried_claim_escalation(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            "template_family_selection": {
                "enabled": True,
                "source": "beautiful-html-template-families",
                "selected_template_id": "8-bit-orbit",
                "claim_level": "svglide_absorbed",
            },
            "slides": [
                {
                    "page": 1,
                    "title": "Demo",
                    "template_variant": "cover",
                    "semantic_blocks": [{"block_id": "title_1", "type": "title", "content": "Demo"}],
                    "component_selection": [{"component_id": "title_block", "binds": ["title_1"]}],
                    "asset_strategy": {"strategy_id": "structured_fallback", "no_fake_data": True},
                    "asset_contract": "none_required",
                    "risk_flags": [],
                    "source_policy": "prompt only",
                    "content_density_contract": "medium-density structured template page",
                }
            ],
        }
        self.assertIn("source_inventoried_claim_escalation", issue_codes(svg_preflight.lint_plan(plan)))

    def test_preflight_rejects_cjk_fake_italic_and_letter_spacing(self) -> None:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="svglide-authoring-contract/v1" width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="80" y="80" width="600" height="120">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:32px;font-style:italic;letter-spacing:4px;color:#111;">内部复盘 AI 产品 2026</div>
  </foreignObject>
</svg>"""
        codes = issue_codes(svg_preflight.lint_svg(svg))
        self.assertIn("cjk_fake_italic", codes)
        self.assertIn("cjk_letter_spacing_inherited", codes)

    def test_dry_run_receipt_records_policy_hashes_and_preflight_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = beautiful_template_e2e_dry_run.run_all(Path(tmpdir))
        self.assertEqual(summary["status"], "passed")
        for receipt in summary["receipts"]:
            with self.subTest(case=receipt["case_id"]):
                self.assertTrue(receipt.get("selected_template_family"))
                self.assertTrue(receipt.get("claim_level"))
                self.assertRegex(receipt.get("cjk_policy_hash", ""), r"^sha256:[0-9a-f]{64}$")
                self.assertRegex(receipt.get("family_usage_policy_hash", ""), r"^sha256:[0-9a-f]{64}$")
                self.assertRegex(receipt.get("extension_grammar_hash", ""), r"^sha256:[0-9a-f]{64}$")
                self.assertEqual(set(receipt.get("benchmark_roles", [])), REQUIRED_BENCHMARK_ROLES)
                checks = receipt.get("preflight_policy_checks", {})
                for code in [
                    "cross_family_layout_mix",
                    "cjk_fake_italic",
                    "cjk_letter_spacing_inherited",
                    "family_recolor_without_override",
                ]:
                    self.assertEqual(checks.get(code), "passed")


if __name__ == "__main__":
    unittest.main()
