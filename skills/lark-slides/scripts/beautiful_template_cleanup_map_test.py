# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_schema


REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


def load_json(name: str) -> dict:
    return json.loads((REFERENCES_DIR / name).read_text(encoding="utf-8"))


class BeautifulTemplateCleanupMapTest(unittest.TestCase):
    def test_cleanup_map_matches_schema(self) -> None:
        cleanup_map = load_json("beautiful-html-template-cleanup-map.json")
        schema = load_json("beautiful-html-template-cleanup-map.schema.json")

        self.assertEqual(svglide_schema.validate_json_schema(cleanup_map, schema), [])

    def test_cleanup_map_defaults_old_design_assets_to_delete(self) -> None:
        cleanup_map = load_json("beautiful-html-template-cleanup-map.json")
        candidates = {item["target"]: item for item in cleanup_map["cleanup_candidates"]}

        for target in [
            "skills/lark-slides/references/style-presets.json",
            "skills/lark-slides/references/style-presets.md",
            "skills/lark-slides/references/svg-visual-recipes.md",
            "skills/lark-slides/references/beautiful-html-template-presets.json",
            "skills/lark-slides/references/beautiful-html-template-presets.md",
        ]:
            self.assertEqual(candidates[target]["action"], "default_delete")
            self.assertFalse(candidates[target]["runtime_import_allowed"])
            self.assertEqual(candidates[target]["unique_signal_evidence"], [])
            self.assertEqual(candidates[target]["extract_to"], [])

    def test_cleanup_map_extracts_absorption_provenance_before_delete(self) -> None:
        cleanup_map = load_json("beautiful-html-template-cleanup-map.json")
        candidates = {item["target"]: item for item in cleanup_map["cleanup_candidates"]}
        absorption = candidates["skills/lark-slides/references/absorptions/beautiful-html-templates"]

        self.assertEqual(absorption["action"], "extract_minimal_signal_then_delete")
        self.assertTrue(absorption["unique_signal_evidence"])
        self.assertIn("skills/lark-slides/references/beautiful-html-template-families.json::families[].svglide_mapping", absorption["extract_to"])

    def test_cleanup_map_protects_runtime_boundaries(self) -> None:
        cleanup_map = load_json("beautiful-html-template-cleanup-map.json")
        protected = {item["target"] for item in cleanup_map["protected_assets"]}

        for target in [
            "satori",
            "og-images-generator",
            "skills/lark-slides/scripts/svglide_contract_compile.py",
            "skills/lark-slides/scripts/svg_preflight.py",
            "skills/lark-slides/references/safe-native-v1.profile.json",
            "skills/lark-slides/references/svglide-brand-palette-registry.json",
        ]:
            self.assertIn(target, protected)

    def test_cleanup_map_blocks_low_level_svg_instruction_patterns(self) -> None:
        cleanup_map = load_json("beautiful-html-template-cleanup-map.json")
        patterns = set(cleanup_map["banned_low_level_svg_instruction_patterns"])

        for pattern in ["path_flow", "connector_flow", "svg_effects", "required_primitives", "svg_primitives", "SVG-native advantage"]:
            self.assertIn(pattern, patterns)


if __name__ == "__main__":
    unittest.main()
