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

import svglide_diversity_gate as gate


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def design_selection(style_pack_id: str = "corporate_blue_data", palette_id: str = "corporate_blue") -> dict[str, object]:
    return {
        "schema_version": "svglide-design-asset-selection/v1",
        "status": "passed",
        "style_pack_selection": {"selected_style_pack_id": style_pack_id, "palette_id": palette_id},
        "style_lock": {
            "deck_level": True,
            "template_family_id": "blue-professional",
            "style_pack_id": style_pack_id,
            "palette_id": palette_id,
            "image_treatment_id": "chart_first",
            "decoration_policy_id": "minimal_grid_only",
        },
    }


def plan_payload(style_pack_id: str = "corporate_blue_data", palette_id: str = "style_pack.corporate_blue_data") -> dict[str, object]:
    return {
        "title": "内部业务复盘",
        "template_family_selection": {
            "enabled": True,
            "source": "beautiful-html-template-families",
            "selected_template_id": "blue-professional",
            "candidate_template_ids": ["blue-professional"],
            "selection_reason": "test",
        },
        "style_lock": {
            "deck_level": True,
            "template_family_id": "blue-professional",
            "style_pack_id": style_pack_id,
            "palette_id": "corporate_blue",
            "image_treatment_id": "chart_first",
            "decoration_policy_id": "minimal_grid_only",
        },
        "project_palette": {
            "palette_id": palette_id,
            "source": "style_pack_registry",
            "confidence": "high",
            "style_pack_id": style_pack_id,
            "colors": {"background": "#F8FAFF", "text": "#111827", "primary": "#1E3A8A", "accent": "#2563EB"},
        },
        "component_variant_selection": {"selected_component_variants": ["metric_cards", "comparison_matrix"]},
        "slides": [
            {
                "page": 1,
                "layout_family": "cover",
                "template_variant": "cover",
                "canvas_spec": {"template_id": "executive-dashboard", "palette_id": palette_id},
                "component_selection": [{"component_id": "title_block"}],
            },
            {
                "page": 2,
                "layout_family": "dashboard",
                "template_variant": "kpi_strip",
                "canvas_spec": {"template_id": "executive-dashboard", "palette_id": palette_id},
                "component_selection": [{"component_id": "metric_cards"}],
            },
            {
                "page": 3,
                "layout_family": "closing",
                "template_variant": "closing",
                "canvas_spec": {"template_id": "executive-dashboard", "palette_id": palette_id},
                "component_selection": [{"component_id": "action_list"}],
            },
        ],
    }


def write_project(project: Path, plan: dict[str, object] | None = None, selection: dict[str, object] | None = None) -> None:
    write_json(project / "02-plan/slide_plan.json", plan or plan_payload())
    write_json(project / "02-plan/selection-metadata.json", selection or design_selection())


class SVGlideDiversityGateTest(unittest.TestCase):
    def test_passes_with_deck_level_style_lock_and_varied_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "current"
            write_project(project)

            result = gate.run_diversity_gate(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["summary"]["combo_count"], 3)

    def test_fails_missing_style_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "current"
            plan = plan_payload()
            plan.pop("style_lock")
            write_json(project / "02-plan/slide_plan.json", plan)

            result = gate.run_diversity_gate(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("style_lock_missing", {item["code"] for item in result["issues"]})

    def test_fails_slide_palette_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "current"
            plan = plan_payload()
            slides = plan["slides"]  # type: ignore[index]
            slides[1]["canvas_spec"]["palette_id"] = "style_pack.graphite_red_risk"  # type: ignore[index]
            write_project(project, plan=plan)

            result = gate.run_diversity_gate(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("slide_palette_drift", {item["code"] for item in result["issues"]})

    def test_warns_recent_combo_reuse_when_only_one_production_template_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            previous = root / "previous"
            current = root / "current"
            write_project(previous)
            write_project(current)

            result = gate.run_diversity_gate(current)

        self.assertEqual(result["status"], "passed")
        self.assertIn("diversity_combo_reuse_too_high", {item["code"] for item in result["warnings"]})
        self.assertIn("claim_boundary", result)


if __name__ == "__main__":
    unittest.main()
