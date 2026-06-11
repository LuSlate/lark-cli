#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import svglide_route_contamination_lint as lint


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def valid_svg_slide() -> dict[str, object]:
    return {
        "page": 1,
        "title": "Title",
        "key_message": "Message",
        "renderer_id": "hero_path_cover",
        "layout_family": "hero",
        "visual_recipe": "hero_typography",
        "visual_intent": "Use SVG geometry for a distinctive cover.",
        "visual_focal_point": "Large title",
        "visual_signature": "Layered title and path frame",
        "svg_effects": ["path", "typography"],
        "required_primitives": ["typography", "geometric_shape"],
        "svg_primitives": ["typography", "geometric_shape", "path"],
        "xml_like_risk": "Would become a plain title slide in XML.",
        "content_density_contract": "hero >= 1 focal title",
        "risk_flags": [],
        "source_policy": "No invented metrics.",
    }


def valid_svg_plan() -> dict[str, object]:
    return {
        "route": "svglide-svg",
        "style_preset": "raw_grid",
        "style_selection_reason": "Matches the topic.",
        "style_system": {
            "palette": {"background": "#fff", "text": "#111", "accent": "#f00"},
            "typography": "bold titles",
            "background_strategy": "stable background",
            "motif": "path frame",
        },
        "slides": [valid_svg_slide()],
    }


class SVGlideRouteContaminationLintTest(unittest.TestCase):
    def test_lint_plan_rejects_svg_fields_on_xml_route(self) -> None:
        issues = lint.lint_plan(
            {
                "presentation_goal": "Create XML deck",
                "slides": [
                    {
                        "page": 1,
                        "title": "Title",
                        "visual_recipe": "path_flow",
                    }
                ],
            },
            "xml_plan.json",
        )
        self.assertIn("xml_plan_svg_only_field", {item["code"] for item in issues})

    def test_lint_plan_accepts_valid_svg_route(self) -> None:
        self.assertEqual(lint.lint_plan(valid_svg_plan(), "svg_plan.json"), [])

    def test_lint_plan_reports_missing_svg_fields(self) -> None:
        plan = valid_svg_plan()
        plan["slides"] = [{"page": 1, "title": "Title"}]
        issues = lint.lint_plan(plan, "svg_plan.json")
        self.assertIn("svg_plan_missing_required_slide_field", {item["code"] for item in issues})

    def test_repository_lint_rejects_top_skill_private_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self._write_minimal_repo(repo)
            write(repo / "skills/lark-slides/SKILL.md", "slides +create-svg\nsvglide-route-admission.md\nsvg-private-manifest.json\nvisual_recipe\n")
            issues = lint.lint_repository(repo, "skills/lark-slides", "skills/lark-slides/references/svg-private-manifest.json")
        self.assertIn("top_skill_private_token", {item["code"] for item in issues})

    def test_repository_lint_rejects_xml_doc_private_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self._write_minimal_repo(repo)
            write(repo / "skills/lark-slides/references/planning-layer.md", "XML docs must not read style-presets.md\n")
            issues = lint.lint_repository(repo, "skills/lark-slides", "skills/lark-slides/references/svg-private-manifest.json")
        self.assertIn("xml_doc_private_reference", {item["code"] for item in issues})

    def test_repository_lint_rejects_route_admission_strategy_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self._write_minimal_repo(repo)
            write(repo / "skills/lark-slides/references/svglide-route-admission.md", "After activation set visual_recipe in each page.\n")
            issues = lint.lint_repository(repo, "skills/lark-slides", "skills/lark-slides/references/svg-private-manifest.json")
        self.assertIn("route_admission_private_body_token", {item["code"] for item in issues})

    def test_repository_lint_rejects_xml_create_private_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            self._write_minimal_repo(repo)
            write(repo / "shortcuts/slides/slides_create.go", "package slides\nfunc f(){ _ = \"SVGlide\" }\n")
            issues = lint.lint_repository(repo, "skills/lark-slides", "skills/lark-slides/references/svg-private-manifest.json")
        self.assertIn("xml_create_private_symbol", {item["code"] for item in issues})

    def test_current_repository_passes_lint(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        issues = lint.lint_repository(repo, "skills/lark-slides", "skills/lark-slides/references/svg-private-manifest.json")
        self.assertEqual([], issues)

    def _write_minimal_repo(self, repo: Path) -> None:
        manifest = {
            "route": "svglide-svg",
            "route_admission_files": ["skills/lark-slides/references/svglide-route-admission.md"],
            "private_strategy_files": [
                "skills/lark-slides/references/style-presets.md",
                "skills/lark-slides/references/svglide-planning-layer.md",
            ],
            "allowed_route_entrypoints": ["skills/lark-slides/references/lark-slides-create-svg.md"],
        }
        write(repo / "skills/lark-slides/references/svg-private-manifest.json", json.dumps(manifest))
        write(repo / "skills/lark-slides/SKILL.md", "slides +create-svg\nsvglide-route-admission.md\nsvg-private-manifest.json\n")
        write(repo / "skills/lark-slides/references/svglide-route-admission.md", "Activate by user request, then load private file index.\n")
        for name in ["planning-layer.md", "validation-checklist.md", "visual-planning.md", "asset-planning.md"]:
            write(repo / f"skills/lark-slides/references/{name}", "XML route shared doc.\n")
        write(repo / "shortcuts/slides/slides_create.go", "package slides\nfunc f(){}\n")
        write(repo / "shortcuts/slides/slides_create_svg.go", "package slides\nfunc f(){ _ = \"SVGlide\" }\n")


if __name__ == "__main__":
    unittest.main()
