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

import svglide_palette_selector as selector
import beautiful_template_runtime


LEGACY_DEBUG_FAMILY_PALETTE_IDS = {
    "family.blueprint-technical",
    "family.cobalt-grid",
    "family.glass-neon",
    "family.retro-desktop",
    "family.warm-editorial",
}


class PaletteSelectorTest(unittest.TestCase):
    def test_default_palette_registry_excludes_legacy_family_palettes(self) -> None:
        registry = beautiful_template_runtime.palette_registry()
        palettes = {item["palette_id"]: item for item in registry["palettes"]}

        self.assertIn("family.blue-professional", palettes)
        self.assertEqual("production", palettes["family.blue-professional"]["asset_status"])
        self.assertEqual("trusted", palettes["family.blue-professional"]["quality_tier"])
        self.assertTrue(palettes["family.blue-professional"]["default_selectable"])
        for legacy_id in ["family.blueprint-technical", "family.cobalt-grid", "family.glass-neon", "family.retro-desktop"]:
            self.assertNotIn(legacy_id, palettes)

    def test_ai_brand_brief_uses_brand_resolution_and_outputs_project_palette(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = selector.select_palette(Path(tmpdir), "生成一份主题为智谱和 MiniMax 的 slide", top_k=5)

        self.assertEqual("brand_registry", result["brand_resolution"]["source"])
        self.assertEqual(["zhipu", "minimax"], result["brand_resolution"]["brands"])
        self.assertEqual("brand.zhipu", result["selected_palette_id"])
        self.assertEqual(result["project_palette"]["colors"]["primary"], "#315CFF")
        self.assertEqual(result["project_palette"]["colors"]["accent"], "#06B6D4")

    def test_user_provided_palette_wins_over_brand_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = selector.select_palette(Path(tmpdir), "NVIDIA 复盘，主色 #123456，强调色 #ABCDEF", top_k=3)

        self.assertEqual("user_provided", result["brand_resolution"]["source"])
        self.assertEqual("#123456", result["project_palette"]["colors"]["primary"])
        self.assertEqual("#ABCDEF", result["project_palette"]["colors"]["accent"])

    def test_style_pack_palette_wins_over_stable_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "02-plan").mkdir(parents=True, exist_ok=True)
            (root / "02-plan/selection-metadata.json").write_text(
                json.dumps(
                    {
                        "schema_version": "svglide-design-asset-selection/v1",
                        "status": "passed",
                        "style_pack_selection": {
                            "selected_style_pack_id": "corporate_blue_data",
                            "palette_id": "corporate_blue",
                        },
                        "style_lock": {
                            "style_pack_id": "corporate_blue_data",
                            "palette_id": "corporate_blue",
                            "deck_level": True,
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = selector.select_palette(root, "生成一份内部业务复盘，高管经营看板", top_k=3)

        self.assertEqual("style_pack_registry", result["brand_resolution"]["source"])
        self.assertEqual("style_pack.corporate_blue_data", result["selected_palette_id"])
        self.assertEqual("style_pack_registry", result["project_palette"]["source"])
        self.assertNotIn("quality_gate_fallback", result["brand_resolution"])
        self.assertNotIn("quality_gate_fallback", result["project_palette"])

    def test_unknown_topic_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = selector.select_palette(root, "一个不存在于模板库的主题：量子陶瓷供应链", top_k=5)
            second = selector.select_palette(root, "一个不存在于模板库的主题：量子陶瓷供应链", top_k=5)

        self.assertEqual(first["selected_palette_id"], second["selected_palette_id"])
        self.assertEqual(first["deterministic_seed"], second["deterministic_seed"])

    def test_palette_registry_default_excludes_legacy_family_palettes(self) -> None:
        registry = beautiful_template_runtime.palette_registry()
        palettes = {item["palette_id"]: item for item in registry["palettes"]}

        self.assertTrue(LEGACY_DEBUG_FAMILY_PALETTE_IDS.isdisjoint(palettes))
        for palette_id, palette in palettes.items():
            if palette_id.startswith("family."):
                self.assertEqual("production", palette.get("asset_status"))
                self.assertEqual("trusted", palette.get("quality_tier"))
                self.assertTrue(palette.get("default_selectable"))
                self.assertEqual("production", palette.get("selection_scope"))

    def test_palette_registry_include_legacy_is_explicit_debug_channel(self) -> None:
        registry = beautiful_template_runtime.palette_registry(include_legacy=True)
        palettes = {item["palette_id"]: item for item in registry["palettes"]}

        self.assertIn("family.blueprint-technical", palettes)
        legacy = palettes["family.blueprint-technical"]
        self.assertEqual("legacy_debug", legacy.get("asset_status"))
        self.assertEqual("fixture_only", legacy.get("quality_tier"))
        self.assertFalse(legacy.get("default_selectable"))
        self.assertEqual("debug", legacy.get("selection_scope"))

    def test_blue_professional_promoted_theme_gets_production_palette(self) -> None:
        registry = beautiful_template_runtime.palette_registry()
        palettes = {item["palette_id"]: item for item in registry["palettes"]}

        self.assertIn("family.blue-professional", palettes)
        palette = palettes["family.blue-professional"]
        self.assertEqual("production", palette.get("asset_status"))
        self.assertEqual("trusted", palette.get("quality_tier"))
        self.assertTrue(palette.get("default_selectable"))
        self.assertEqual("production", palette.get("selection_scope"))
        self.assertEqual("blue-professional", palette.get("source_family"))
        self.assertTrue(palette.get("source_trace"))
        self.assertNotIn("family.blueprint-technical", palettes)

    def test_write_palette_selection_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = selector.select_palette(root, "内部业务复盘", top_k=3)
            output = selector.write_palette_selection(root, result)

            written = json.loads(output.read_text(encoding="utf-8"))
            receipt = json.loads((root / "receipts/palette_selection.json").read_text(encoding="utf-8"))

        self.assertEqual(written["schema_version"], "svglide-palette-selection/v1")
        self.assertEqual(receipt["selected_palette_id"], written["selected_palette_id"])


if __name__ == "__main__":
    unittest.main()
