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

import svglide_theme
import beautiful_template_runtime


LEGACY_DEBUG_THEME_IDS = {
    "blueprint-technical",
    "cobalt-grid",
    "glass-neon",
    "retro-desktop",
    "warm-editorial",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strict_theme() -> dict[str, object]:
    colors = {
        "background": "#FFFFFF",
        "surface": "#F8FAFC",
        "text": "#111827",
        "muted": "#64748B",
        "primary": "#2563EB",
        "accent": "#D946EF",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
    }
    return {
        "schema_version": "svglide-theme/v1",
        "theme_id": "strict-demo",
        "mode": "light",
        "colors": colors,
        "semantic_colors": {
            "canvas.background": colors["background"],
            "text.default": colors["text"],
            "chart.highlight": "#0F766E",
        },
        "tokens": {f"color.{role}": value for role, value in colors.items()},
        "contrast": {"min_text_contrast": 4.5},
        "allowed_color_roles": list(colors.keys()),
        "data_series": ["#7C3AED", "#0891B2"],
    }


def issue_codes(issues: list[dict[str, str]]) -> set[str]:
    return {item["code"] for item in issues}


class SVGlideThemeTest(unittest.TestCase):
    def test_default_theme_registry_excludes_legacy_themes(self) -> None:
        registry = beautiful_template_runtime.theme_registry()
        themes = {item["id"]: item for item in registry["themes"]}

        for legacy_id in ["blueprint-technical", "cobalt-grid", "glass-neon", "retro-desktop"]:
            self.assertNotIn(legacy_id, themes)
        self.assertIn("blue-professional", themes)
        self.assertEqual("production", themes["blue-professional"]["asset_status"])
        self.assertEqual("trusted", themes["blue-professional"]["quality_tier"])
        self.assertTrue(themes["blue-professional"]["default_selectable"])
        self.assertIn("executive-dashboard", themes["blue-professional"]["template_bindings"]["supported_template_ids"])

    def test_include_legacy_theme_registry_marks_legacy_debug(self) -> None:
        registry = beautiful_template_runtime.theme_registry(include_legacy=True)
        themes = {item["id"]: item for item in registry["themes"]}

        self.assertIn("blueprint-technical", themes)
        self.assertEqual("legacy_debug", themes["blueprint-technical"]["status"])
        self.assertEqual("fixture_only", themes["blueprint-technical"]["quality_tier"])
        self.assertFalse(themes["blueprint-technical"]["default_selectable"])

    def test_default_template_registry_excludes_legacy_p0_templates(self) -> None:
        registry = beautiful_template_runtime.template_registry()
        templates = {item["id"]: item for item in registry["templates"]}

        for legacy_id in beautiful_template_runtime.LEGACY_TEMPLATE_IDS:
            self.assertNotIn(legacy_id, templates)
        self.assertIn("executive-dashboard", templates)
        self.assertIn("architectural-spec", templates)
        for template in templates.values():
            self.assertEqual("production", template.get("asset_status"))
            self.assertEqual("trusted", template.get("quality_tier"))
            self.assertTrue(template.get("default_selectable"))

    def test_include_legacy_template_registry_marks_p0_as_debug_only(self) -> None:
        registry = beautiful_template_runtime.template_registry(include_legacy=True)
        templates = {item["id"]: item for item in registry["templates"]}

        self.assertIn("architecture-blueprint", templates)
        self.assertEqual("legacy_debug", templates["architecture-blueprint"].get("asset_status"))
        self.assertEqual("fixture_only", templates["architecture-blueprint"].get("quality_tier"))
        self.assertFalse(templates["architecture-blueprint"].get("default_selectable"))

    def test_theme_schema_requires_p0_fields(self) -> None:
        schema_path = Path(__file__).resolve().parent.parent / "references" / "svglide-theme-spec.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema_version"]["const"], "svglide-theme/v1")
        self.assertTrue(
            {
                "theme_id",
                "mode",
                "colors",
                "semantic_colors",
                "tokens",
                "contrast",
                "allowed_color_roles",
            }.issubset(set(schema["required"]))
        )
        for role in ["background", "surface", "text", "muted", "primary", "accent", "success", "warning", "danger"]:
            self.assertIn(role, schema["properties"]["colors"]["required"])

    def test_validate_theme_spec_rejects_illegal_hex(self) -> None:
        theme = strict_theme()
        theme["colors"]["primary"] = "#12GGGG"  # type: ignore[index]

        issues = svglide_theme.validate_theme_spec(theme)

        self.assertIn("theme_color_hex_invalid", issue_codes(issues))

    def test_validate_theme_spec_rejects_missing_core_token(self) -> None:
        theme = strict_theme()
        del theme["tokens"]["color.primary"]  # type: ignore[index]

        issues = svglide_theme.validate_theme_spec(theme)

        self.assertIn("theme_token_missing", issue_codes(issues))

    def test_validate_theme_spec_rejects_missing_and_non_numeric_min_text_contrast(self) -> None:
        missing = strict_theme()
        del missing["contrast"]["min_text_contrast"]  # type: ignore[index]
        non_numeric = strict_theme()
        non_numeric["contrast"]["min_text_contrast"] = "4.5"  # type: ignore[index]

        self.assertIn("theme_contrast_min_text_invalid", issue_codes(svglide_theme.validate_theme_spec(missing)))
        self.assertIn("theme_contrast_min_text_invalid", issue_codes(svglide_theme.validate_theme_spec(non_numeric)))

    def test_theme_hash_is_stable_for_key_order_and_hex_case(self) -> None:
        first = strict_theme()
        second = {
            "allowed_color_roles": first["allowed_color_roles"],
            "contrast": first["contrast"],
            "tokens": dict(reversed(list(first["tokens"].items()))),  # type: ignore[union-attr]
            "semantic_colors": first["semantic_colors"],
            "colors": {**first["colors"], "primary": "#2563eb"},  # type: ignore[arg-type]
            "mode": "light",
            "theme_id": "strict-demo",
            "schema_version": "svglide-theme/v1",
            "data_series": first["data_series"],
        }

        self.assertEqual(svglide_theme.theme_sha256(first), svglide_theme.theme_sha256(second))

    def test_contrast_ratio_black_white(self) -> None:
        self.assertAlmostEqual(21.0, svglide_theme.contrast_ratio("#000000", "#FFFFFF"), places=3)
        self.assertAlmostEqual(0.0, svglide_theme.relative_luminance("#000"), places=6)
        self.assertAlmostEqual(1.0, svglide_theme.relative_luminance("#fff"), places=6)

    def test_extract_svg_colors_reads_fill_stroke_color_and_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "page-001.svg"
            write_text(
                path,
                """<svg xmlns="http://www.w3.org/2000/svg">
  <rect fill="#abc" stroke="#AABBCC"/>
  <text color="#000">Label</text>
  <path style="fill:#123456; stroke: #0f0; color:#00AAff; background:#fed;"/>
</svg>""",
            )

            colors = svglide_theme.extract_svg_colors(path)

        self.assertEqual(["#AABBCC", "#000000", "#123456", "#00FF00", "#00AAFF", "#FFEEDD"], colors)

    def test_classify_color_does_not_allow_unknown_by_default(self) -> None:
        theme = strict_theme()

        self.assertEqual("theme_token", svglide_theme.classify_color("#2563EB", theme)["kind"])
        self.assertEqual("semantic", svglide_theme.classify_color("#0F766E", theme)["kind"])
        self.assertEqual("data_series", svglide_theme.classify_color("#0891B2", theme)["kind"])
        self.assertEqual("unknown", svglide_theme.classify_color("#123456", theme)["kind"])

    def test_load_theme_adapts_existing_artboard_renderer_theme(self) -> None:
        theme = svglide_theme.load_theme("swiss-red")

        self.assertEqual("svglide-theme/v1", theme["schema_version"])
        self.assertEqual("swiss-red", theme["theme_id"])
        self.assertEqual("#FFFFFF", theme["colors"]["surface"])
        self.assertEqual([], svglide_theme.validate_theme_spec(theme))

    def test_runtime_theme_registry_default_excludes_legacy_debug_themes(self) -> None:
        registry = beautiful_template_runtime.theme_registry()
        themes = {item["id"]: item for item in registry["themes"]}

        self.assertTrue(LEGACY_DEBUG_THEME_IDS.isdisjoint(themes))
        self.assertIn("swiss-red", themes)
        for theme in themes.values():
            self.assertEqual("production", theme.get("asset_status"))
            self.assertEqual("trusted", theme.get("quality_tier"))
            self.assertTrue(theme.get("default_selectable"))
            self.assertEqual("production", theme.get("selection_scope"))

    def test_runtime_theme_registry_include_legacy_is_debug_only(self) -> None:
        registry = beautiful_template_runtime.theme_registry(include_legacy=True)
        themes = {item["id"]: item for item in registry["themes"]}

        self.assertIn("blueprint-technical", themes)
        self.assertEqual("legacy_debug", themes["blueprint-technical"].get("asset_status"))
        self.assertEqual("fixture_only", themes["blueprint-technical"].get("quality_tier"))
        self.assertFalse(themes["blueprint-technical"].get("default_selectable"))
        self.assertEqual("debug", themes["blueprint-technical"].get("selection_scope"))

    def test_blue_professional_promoted_to_production_theme(self) -> None:
        registry = beautiful_template_runtime.theme_registry()
        themes = {item["id"]: item for item in registry["themes"]}

        self.assertIn("blue-professional", themes)
        theme = themes["blue-professional"]
        self.assertEqual("production", theme.get("asset_status"))
        self.assertEqual("trusted", theme.get("quality_tier"))
        self.assertTrue(theme.get("default_selectable"))
        self.assertEqual("production", theme.get("selection_scope"))
        self.assertEqual("blue-professional", theme.get("theme_token", {}).get("theme_id"))
        self.assertIn("executive-dashboard", theme.get("template_bindings", {}).get("supported_template_ids", []))
        self.assertTrue(theme.get("source_trace"))
        self.assertEqual("passed", theme.get("promotion_gate", {}).get("status"))
        self.assertNotIn("blueprint-technical", themes)

    def test_prepared_svg_hashes_are_stable_and_repo_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_text(project / "04-svg/prepared/page-002.svg", "<svg><rect /></svg>")
            write_text(project / "04-svg/prepared/page-001.svg", "<svg></svg>")

            hashes = svglide_theme.prepared_svg_hashes(project)

        self.assertEqual(["04-svg/prepared/page-001.svg", "04-svg/prepared/page-002.svg"], [item["path"] for item in hashes])
        self.assertRegex(hashes[0]["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
