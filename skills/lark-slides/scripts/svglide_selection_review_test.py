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

import svglide_palette_selector
import svglide_recipe_selector
import svglide_selection_review as review
import svglide_theme_template_selector


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_project(root: Path, brief: str = "内部业务复盘，高管经营看板") -> tuple[dict[str, object], dict[str, object]]:
    palette = svglide_palette_selector.select_palette(root, brief, top_k=5)
    svglide_palette_selector.write_palette_selection(root, palette)
    selection = svglide_theme_template_selector.select_theme_template(root, brief, top_k=5)
    svglide_theme_template_selector.write_selection(root, selection)
    project_palette = palette["project_palette"]
    colors = project_palette["colors"]
    template_id = selection["template_candidates"][0]["template_id"]
    theme_id = selection["theme_candidates"][0]["theme_id"]
    write_json(
        root / "02-plan/slide_plan.json",
        {
            "palette_selection_receipt": "02-plan/palette-selection.json",
            "selection_receipt": "02-plan/theme-template-selection.json",
            "fallback_policy": {
                "when": "selection_confidence_low",
                "action": "use structured fallback with selected candidate family and keep plan-declared template IDs auditable",
            },
            "project_palette": project_palette,
            "project_theme": {
                "base_theme_id": theme_id,
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
            "slides": [
                {
                    "page": 1,
                    "canvas_spec": {
                        "template_id": template_id,
                        "theme_id": theme_id,
                        "palette_id": project_palette["palette_id"],
                        "selection_trace": {
                            "palette_candidate_rank": 1,
                            "template_candidate_rank": 1,
                            "theme_candidate_rank": 1,
                            "selection_reason": ["test"],
                        },
                    },
                }
            ],
        },
    )
    return palette, selection


class SelectionReviewTest(unittest.TestCase):
    def test_selection_review_passes_candidate_bound_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)

            result = review.run_review(root)

        self.assertEqual(result["status"], "passed", result["issues"])

    def test_selection_review_fails_candidate_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][0]["canvas_spec"]["template_id"] = "not-a-candidate"
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("template_not_allowed", {item["code"] for item in result["issues"]})

    def test_selection_review_fails_selected_legacy_template_theme_or_palette(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            palette, selection = make_project(root)
            palette["selected_palette_id"] = "family.blueprint-technical"
            palette["palette_candidates"] = [
                {
                    "palette_id": "family.blueprint-technical",
                    "status": "legacy_debug",
                    "asset_status": "legacy_debug",
                    "quality_tier": "fixture_only",
                    "default_selectable": False,
                }
            ]
            selection["selected_template_id"] = "architecture-blueprint"
            selection["selected_theme_id"] = "blueprint-technical"
            selection["template_candidates"] = [
                {
                    "template_id": "architecture-blueprint",
                    "status": "legacy_debug",
                    "asset_status": "legacy_debug",
                    "quality_tier": "fixture_only",
                    "default_selectable": False,
                }
            ]
            selection["theme_candidates"] = [
                {
                    "theme_id": "blueprint-technical",
                    "status": "legacy_debug",
                    "asset_status": "legacy_debug",
                    "quality_tier": "fixture_only",
                    "default_selectable": False,
                }
            ]
            write_json(root / "02-plan/palette-selection.json", palette)
            write_json(root / "02-plan/theme-template-selection.json", selection)

            result = review.run_review(root)

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("selected_legacy_template", codes)
        self.assertIn("selected_legacy_theme", codes)
        self.assertIn("selected_legacy_palette", codes)

    def test_selection_review_fails_source_inventory_template_even_if_candidate_claims_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _, selection = make_project(root)
            fake_template = {
                "template_id": "fake-source-template",
                "status": "active",
                "asset_status": "production",
                "quality_tier": "trusted",
                "default_selectable": True,
                "selection_scope": "production",
                "claim_level": "source_inventory_only",
                "promotion_gate": {"status": "blocked", "issues": [{"code": "source_inventory_only_family"}]},
            }
            selection["selected_template_id"] = "fake-source-template"
            selection["template_candidates"] = [fake_template]
            write_json(root / "02-plan/theme-template-selection.json", selection)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][0]["canvas_spec"]["template_id"] = "fake-source-template"
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_review(root)

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("selected_source_inventory_template", codes)
        self.assertIn("selected_template_promotion_gate_not_passed", codes)

    def test_selection_review_passes_plan_declared_multi_template_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            brief = "生成一份内部战略复盘，使用多种 P1 artboard 版式"
            palette = svglide_palette_selector.select_palette(root, brief, top_k=5)
            svglide_palette_selector.write_palette_selection(root, palette)
            write_json(
                root / "02-plan/slide_plan.json",
                {
                    "slides": [
                        {"page": 1, "canvas_spec": {"template_id": "intelligence-brief", "theme_id": "stone-architect"}},
                        {"page": 2, "canvas_spec": {"template_id": "poster-stat-punch", "theme_id": "stone-architect"}},
                    ]
                },
            )
            selection = svglide_theme_template_selector.select_theme_template(root, brief, top_k=1)
            svglide_theme_template_selector.write_selection(root, selection)
            project_palette = palette["project_palette"]
            colors = project_palette["colors"]
            write_json(
                root / "02-plan/slide_plan.json",
                {
                    "palette_selection_receipt": "02-plan/palette-selection.json",
                    "selection_receipt": "02-plan/theme-template-selection.json",
                    "fallback_policy": {
                        "when": "selection_confidence_low",
                        "action": "keep plan-declared template IDs and require selection_trace for each page",
                    },
                    "project_palette": project_palette,
                    "project_theme": {
                        "base_theme_id": selection["selected_theme_id"],
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
                    "slides": [
                        {
                            "page": 1,
                            "canvas_spec": {
                                "template_id": "intelligence-brief",
                                "theme_id": "stone-architect",
                                "palette_id": project_palette["palette_id"],
                                "selection_trace": {"selection_reason": ["plan_declared"]},
                            },
                        },
                        {
                            "page": 2,
                            "canvas_spec": {
                                "template_id": "poster-stat-punch",
                                "theme_id": "stone-architect",
                                "palette_id": project_palette["palette_id"],
                                "selection_trace": {"selection_reason": ["plan_declared"]},
                            },
                        },
                    ],
                },
            )

            result = review.run_review(root)

        self.assertEqual(result["status"], "passed", result["issues"])

    def test_selection_review_fails_missing_selection_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            del plan["slides"][0]["canvas_spec"]["selection_trace"]
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("selection_trace_missing", {item["code"] for item in result["issues"]})

    def test_selection_review_requires_design_asset_metadata_for_svg_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["route"] = "svglide-svg"
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_review(root)

        self.assertEqual(result["status"], "failed")
        self.assertIn("design_asset_selection_missing", {item["code"] for item in result["issues"]})

    def test_selection_review_accepts_complete_design_asset_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            make_project(root)
            metadata = svglide_recipe_selector.select_design_assets("内部业务复盘，管理层阅读，包含 KPI 和行动")
            write_json(root / "02-plan/selection-metadata.json", metadata)
            write_json(root / "02-plan/recipe-routing-receipt.json", metadata)
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["route"] = "svglide-svg"
            plan["selection_metadata_receipt"] = "02-plan/selection-metadata.json"
            plan["recipe_routing_receipt"] = "02-plan/recipe-routing-receipt.json"
            for key in [
                "deck_recipe_selection",
                "template_family_selection",
                "style_pack_selection",
                "density_mode_selection",
                "component_variant_selection",
                "image_treatment_selection",
                "style_lock",
            ]:
                plan[key] = metadata[key]
            write_json(root / "02-plan/slide_plan.json", plan)

            result = review.run_review(root)

        self.assertEqual(result["status"], "passed", result["issues"])


if __name__ == "__main__":
    unittest.main()
