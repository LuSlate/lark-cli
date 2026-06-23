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

import svglide_palette_review as review
import svglide_palette_selector


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_project(root: Path, brief: str = "智谱和 MiniMax 内部业务复盘") -> dict[str, object]:
    selection = svglide_palette_selector.select_palette(root, brief, top_k=5)
    svglide_palette_selector.write_palette_selection(root, selection)
    palette = selection["project_palette"]
    colors = palette["colors"]
    write_json(
        root / "02-plan/slide_plan.json",
        {
            "project_palette": palette,
            "project_theme": {
                "base_theme_id": "glass-neon",
                "palette_ref": "project_palette",
                "token_overrides": {
                    "color.background": colors["background"],
                    "color.surface": colors["surface"],
                    "color.text": colors["text"],
                    "color.muted": colors["muted"],
                    "color.primary": colors["primary"],
                    "color.accent": colors["accent"],
                },
            },
            "slides": [{"page": 1}],
        },
    )
    return selection


class PaletteReviewTest(unittest.TestCase):
    def test_palette_review_passes_with_project_palette_and_token_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)

            result = review.run_palette_review(root)

        self.assertEqual(result["status"], "passed", result["issues"])

    def test_palette_review_fails_missing_brand_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            selection = make_project(root)
            selection["brand_resolution"]["evidence"] = []
            write_json(root / "02-plan/palette-selection.json", selection)

            result = review.run_palette_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("brand_resolution_evidence_missing", {item["code"] for item in result["issues"]})

    def test_palette_review_fails_low_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            selection = make_project(root)
            selection["project_palette"]["colors"]["text"] = "#111111"
            selection["project_palette"]["colors"]["background"] = "#111111"
            write_json(root / "02-plan/palette-selection.json", selection)

            result = review.run_palette_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("palette_contrast_too_low", {item["code"] for item in result["issues"]})

    def test_palette_review_fails_insufficient_data_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            selection = make_project(root)
            selection["project_palette"]["data_series"] = ["#315CFF", "#06B6D4"]
            write_json(root / "02-plan/palette-selection.json", selection)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["chart_contract"] = {"required_series_count": 4}
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_palette_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("palette_data_series_insufficient", {item["code"] for item in result["issues"]})

    def test_stable_fallback_selection_is_marked_for_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            selection = svglide_palette_selector.select_palette(root, "一个不存在的抽象主题：量子陶瓷供应链", top_k=5)

        self.assertEqual("stable_fallback", selection["brand_resolution"]["source"])
        self.assertTrue(selection["brand_resolution"]["quality_gate_fallback"])
        self.assertTrue(selection["project_palette"]["quality_gate_fallback"])


if __name__ == "__main__":
    unittest.main()
