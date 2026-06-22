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

import svglide_selection_metadata_lint as lint


def template_metadata() -> dict[str, object]:
    return {
        "best_for": ["internal review"],
        "avoid_for": [],
        "industry_tags": ["business"],
        "occasion_tags": ["business review"],
        "audience_tags": ["internal"],
        "tone_tags": ["analytical"],
        "density": "medium-high",
        "formality": "high",
        "content_shapes": ["dashboard"],
        "visual_signature": ["metric cards"],
        "required_assets": [],
        "decorative_elements": ["section rule"],
    }


def theme_metadata() -> dict[str, object]:
    return {
        "scheme": "light",
        "mood_tags": ["professional"],
        "brand_affinity": [],
        "primary_color_bias": ["blue"],
        "contrast_profile": "high readability",
        "supported_template_ids": ["executive-dashboard"],
        "token_override_policy": "allowed",
    }


def palette_record() -> dict[str, object]:
    return {
        "palette_id": "business-blue",
        "status": "active",
        "mode": "light",
        "colors": {
            "background": "#FFFFFF",
            "surface": "#F8FAFC",
            "text": "#111827",
            "muted": "#64748B",
            "primary": "#2563EB",
            "accent": "#06B6D4",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "danger": "#EF4444",
        },
        "data_series": ["#2563EB", "#06B6D4"],
        "selection_metadata": {
            "best_for": ["business review"],
            "avoid_for": [],
            "brand_affinity": [],
            "industry_tags": ["business"],
            "tone_tags": ["analytical"],
            "density": "medium-high",
            "formality": "high",
        },
        "source_trace": [{"type": "fixture", "source": "test", "checked_at": "2026-06-22"}],
    }


class SelectionMetadataLintTest(unittest.TestCase):
    def test_template_requires_selection_metadata(self) -> None:
        issues = lint.validate_template_metadata({"id": "missing", "status": "active"})
        self.assertIn("selection_metadata_missing", {item["code"] for item in issues})

    def test_template_rejects_empty_required_lists(self) -> None:
        metadata = template_metadata()
        metadata["best_for"] = []
        issues = lint.validate_template_metadata({"id": "bad", "status": "active", "selection_metadata": metadata})
        self.assertIn("selection_metadata_list_empty", {item["code"] for item in issues})

    def test_theme_rejects_invalid_scheme_and_override_policy(self) -> None:
        metadata = theme_metadata()
        metadata["scheme"] = "purple"
        metadata["token_override_policy"] = "maybe"
        issues = lint.validate_theme_metadata({"id": "bad-theme", "status": "active", "selection_metadata": metadata})
        codes = {item["code"] for item in issues}
        self.assertIn("selection_metadata_scheme_invalid", codes)
        self.assertIn("selection_metadata_token_override_policy_invalid", codes)

    def test_palette_requires_core_colors_and_data_series(self) -> None:
        record = palette_record()
        record["data_series"] = ["#2563EB"]
        record["colors"]["primary"] = "#12GGGG"  # type: ignore[index]
        issues = lint.validate_palette_metadata(record)
        codes = {item["code"] for item in issues}
        self.assertIn("palette_color_invalid", codes)
        self.assertIn("palette_data_series_invalid", codes)

    def test_brand_record_requires_source_trace_and_confidence(self) -> None:
        issues = lint.validate_brand_palette_record({"brand_id": "x", "aliases": ["x"], "palette": {}})
        codes = {item["code"] for item in issues}
        self.assertIn("brand_source_trace_missing", codes)
        self.assertIn("brand_confidence_invalid", codes)

    def test_run_lint_uses_real_fixture_registries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            refs = root / "skills/lark-slides/references"
            themes = root / "skills/lark-slides/scripts/artboard_renderer/themes"
            refs.mkdir(parents=True)
            themes.mkdir(parents=True)
            (refs / "svglide-template-registry.json").write_text(
                json.dumps({"templates": [{"id": "executive-dashboard", "status": "active", "selection_metadata": template_metadata()}]}),
                encoding="utf-8",
            )
            (themes / "registry.json").write_text(
                json.dumps({"themes": [{"id": "business-theme", "status": "active", "selection_metadata": theme_metadata()}]}),
                encoding="utf-8",
            )
            (refs / "svglide-palette-registry.json").write_text(json.dumps({"palettes": [palette_record()]}), encoding="utf-8")
            (refs / "svglide-brand-palette-registry.json").write_text(
                json.dumps(
                    {
                        "brands": [
                            {
                                "brand_id": "nvidia",
                                "display_name": "NVIDIA",
                                "aliases": ["NVIDIA"],
                                "palette": {"primary": "#76B900", "accent": "#111111", "background": "#000000", "text": "#FFFFFF"},
                                "source_trace": [{"type": "fixture", "source": "test", "checked_at": "2026-06-22"}],
                                "confidence": "medium",
                                "updated_at": "2026-06-22",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = lint.run_lint(root)

        self.assertEqual(result["status"], "passed", result["issues"])


if __name__ == "__main__":
    unittest.main()
