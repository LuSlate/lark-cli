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

import svglide_visual_distinctness_review as review


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def plan_payload(title: str, archetype: str) -> dict[str, object]:
    return {
        "title": title,
        "style_preset": "riptide_cobalt",
        "style_system": {"palette": ["#06111F", "#0B1E33", "#22D3EE", "#F8FAFC"]},
        "visual_identity": {
            "theme_archetype": archetype,
            "design_dna": {
                "palette": "dark technical",
                "layout_motif": "signal map",
                "shape_language": "cards and rails",
                "image_treatment": "scrim overlay",
                "component_bias": "scorecards",
            },
        },
        "art_direction": {"cover_treatment": "dark full bleed image cover"},
        "slides": [
            {"page": 1, "renderer_id": "cover_full_bleed", "layout_family": "cover", "visual_recipe": "hero_typography"},
            {"page": 2, "renderer_id": "market_signal", "layout_family": "market", "visual_recipe": "infographic_scorecard"},
            {"page": 3, "renderer_id": "timeline_rail", "layout_family": "timeline", "visual_recipe": "path_flow"},
            {"page": 4, "renderer_id": "closing_cta", "layout_family": "closing", "visual_recipe": "brand_system"},
        ],
    }


class SVGlideVisualDistinctnessReviewTest(unittest.TestCase):
    def test_fails_when_different_theme_reuses_recent_style_and_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            previous = root / "spacex"
            current = root / "bytedance"
            write_json(previous / "02-plan/slide_plan.json", plan_payload("SpaceX 上市为什么引人瞩目", "space_capital_market"))
            write_json(current / "02-plan/slide_plan.json", plan_payload("字节跳动", "company_ecosystem"))

            result = review.run_visual_distinctness_review(current)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("visual_identity_too_similar_to_recent_deck", codes)

    def test_allows_same_theme_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            previous = root / "bytedance-old"
            current = root / "bytedance-new"
            write_json(previous / "02-plan/slide_plan.json", plan_payload("字节跳动旧版", "company_ecosystem"))
            write_json(current / "02-plan/slide_plan.json", plan_payload("字节跳动新版", "company_ecosystem"))

            result = review.run_visual_distinctness_review(current)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["comparison_count"], 1)

    def test_fails_default_only_renderer_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "default-only"
            payload = plan_payload("字节跳动", "company_ecosystem")
            for slide in payload["slides"]:  # type: ignore[index]
                slide["renderer_id"] = "chart"
                slide["layout_family"] = "chart"
            write_json(project / "02-plan/slide_plan.json", payload)

            result = review.run_visual_distinctness_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("renderer_sequence_default_only", codes)


if __name__ == "__main__":
    unittest.main()
