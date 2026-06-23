#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_recipe_selector as selector


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
FIXTURE_DIR = SCRIPT_DIR / "fixtures" / "svglide_recipe_matching"
LEVEL_RANK = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
REQUIRED_METADATA_FIELDS = {"mood", "tone", "best_for", "avoid_for", "density", "formality"}
FORBIDDEN_BASELINES = {"svglide-baseline", "svglide baseline theme", "baseline"}


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return payload


class SVGlideRecipeSelectorTest(unittest.TestCase):
    def test_registry_contract_files_exist(self) -> None:
        for name in [
            "svglide-deck-recipe-registry.schema.json",
            "svglide-deck-recipe-registry.json",
            "svglide-style-pack-registry.schema.json",
            "svglide-style-pack-registry.json",
            "svglide-semantic-route-cases.schema.json",
            "svglide-semantic-route-cases.json",
        ]:
            self.assertTrue((REFERENCES_DIR / name).exists(), name)

    def test_registries_have_routeable_metadata(self) -> None:
        recipes = selector.load_recipe_registry()
        style_packs = selector.load_style_pack_registry()
        self.assertGreaterEqual(len(recipes), 10)
        self.assertGreaterEqual(len(style_packs), 8)
        style_pack_ids = {item["style_pack_id"] for item in style_packs}
        for recipe in recipes:
            with self.subTest(recipe=recipe.get("recipe_id")):
                self.assertTrue(recipe.get("recipe_id"))
                self.assertTrue(REQUIRED_METADATA_FIELDS.issubset(recipe.get("metadata", {})))
                self.assertTrue(recipe.get("template_family_candidates"))
                self.assertTrue(recipe.get("style_pack_candidates"))
                self.assertTrue(recipe.get("component_slots"))
                self.assertTrue(recipe.get("image_treatment_candidates"))
                self.assertTrue(set(recipe["style_pack_candidates"]) & style_pack_ids)
        for pack in style_packs:
            with self.subTest(style_pack=pack.get("style_pack_id")):
                self.assertTrue(pack.get("style_pack_id"))
                self.assertTrue(REQUIRED_METADATA_FIELDS.issubset(pack.get("metadata", {})))
                for field in [
                    "palette_id",
                    "typography_id",
                    "background_system_id",
                    "chart_palette_id",
                    "image_treatment_id",
                    "decoration_policy_id",
                    "component_variant_bias",
                ]:
                    self.assertIn(field, pack)

    def test_42_golden_cases_are_all_l1_or_l2(self) -> None:
        payload = load_json(FIXTURE_DIR / "cases_42.json")
        cases = payload["cases"]
        self.assertEqual(len(cases), 42)
        results = []
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = selector.select_design_assets(case["prompt"])
                recipe = result["deck_recipe_selection"]
                self.assertIn(recipe["recipe_id"], case["expected_recipe_ids"])
                self.assertLessEqual(LEVEL_RANK[recipe["match_level"]], LEVEL_RANK[case["min_match_level"]])
                self.assertIn(recipe["match_level"], {"L1", "L2"})
                self.assertGreaterEqual(recipe["confidence"], 0.5)
                self.assert_complete_selection(result)
                results.append(recipe["match_level"])
        self.assertEqual(len([level for level in results if level in {"L1", "L2"}]), 42)

    def test_out_of_sample_routes_or_fails_closed_with_explanation(self) -> None:
        payload = load_json(FIXTURE_DIR / "out_of_sample.json")
        cases = payload["cases"]
        self.assertGreaterEqual(len(cases), 9)
        observed_non_l1 = False
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = selector.select_design_assets(case["prompt"])
                recipe = result["deck_recipe_selection"]
                self.assertLessEqual(LEVEL_RANK[recipe["match_level"]], LEVEL_RANK[case["max_match_level"]])
                if recipe["match_level"] != "L1":
                    observed_non_l1 = True
                if recipe["match_level"] == "L4":
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["action"], "fail_closed")
                    self.assertTrue(recipe["missing_signals"])
                else:
                    self.assertEqual(result["status"], "passed")
                    self.assertTrue(recipe["signals"])
                    self.assert_complete_selection(result)
        self.assertTrue(observed_non_l1)

    def test_selection_never_uses_baseline_as_successful_fallback(self) -> None:
        for prompt in ["随便做一个好看的 PPT", "完全没有主题，只要高级感", ""]:
            with self.subTest(prompt=prompt):
                result = selector.select_design_assets(prompt)
                blob = json.dumps(result, ensure_ascii=False).lower()
                self.assertFalse(any(item in blob for item in FORBIDDEN_BASELINES))
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["action"], "fail_closed")

    def test_style_lock_is_deck_level_and_auditable(self) -> None:
        result = selector.select_design_assets("豆包 App 竞品分析，关注产品能力、用户场景和真实产品截图")
        self.assertEqual(result["status"], "passed")
        style_lock = result["style_lock"]
        self.assertEqual(style_lock["style_pack_id"], result["style_pack_selection"]["selected_style_pack_id"])
        self.assertEqual(style_lock["image_treatment_id"], result["image_treatment_selection"]["selected_image_treatment_id"])
        self.assertNotEqual(style_lock["decoration_policy_id"], "random_decorations")
        self.assertIn("selection_reason", result["style_pack_selection"])
        self.assertIn("selection_reason", result["image_treatment_selection"])

    def assert_complete_selection(self, result: dict) -> None:
        for key in [
            "deck_recipe_selection",
            "template_family_selection",
            "style_pack_selection",
            "density_mode_selection",
            "component_variant_selection",
            "image_treatment_selection",
            "style_lock",
        ]:
            self.assertIn(key, result)
        self.assertEqual(result["template_family_selection"]["enabled"], True)
        self.assertTrue(result["template_family_selection"]["selected_template_id"])
        self.assertTrue(result["style_pack_selection"]["selected_style_pack_id"])
        self.assertTrue(result["density_mode_selection"]["selected_density_mode"])
        self.assertTrue(result["component_variant_selection"]["selected_component_variants"])
        self.assertTrue(result["image_treatment_selection"]["selected_image_treatment_id"])


if __name__ == "__main__":
    unittest.main()
