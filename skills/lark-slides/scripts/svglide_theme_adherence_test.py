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
import svglide_theme_adherence
import svglide_theme_validate
import beautiful_template_runtime


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_project(tmpdir: str) -> Path:
    project = Path(tmpdir)
    write_legacy_fixture_registries(project)
    write_json(
        project / "02-plan/slide_plan.json",
        {
            "generation_mode": "artboard_satori",
            "slides": [
                {
                    "page": 1,
                    "title": "主题测试",
                    "canvas_spec": {
                        "version": "svglide-canvas-spec/v1",
                        "template_id": "cover-hero",
                        "theme_id": "dark-clarity",
                        "theme": {"colors": {"background": "#0F172A"}},
                    },
                }
            ],
        },
    )
    validation = svglide_theme_validate.validate_project(project)
    svglide_theme_validate.write_outputs(project, validation)
    return project


def write_svg(project: Path, body: str) -> None:
    path = project / "04-svg/prepared/page-001.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_project_theme_override(project: Path) -> None:
    write_json(
        project / "02-plan/theme-registry.json",
        {
            "schema_version": "svglide-theme-registry/v1",
            "themes": [{"id": "dark-clarity", "status": "active", "path": "themes/dark-clarity.json"}],
        },
    )
    write_json(
        project / "themes/dark-clarity.json",
        {
            "schema_version": "svglide-theme/v1",
            "theme_id": "dark-clarity",
            "mode": "light",
            "colors": {
                "background": "#FFFFFF",
                "surface": "#F8FAFC",
                "text": "#111111",
                "muted": "#64748B",
                "primary": "#123456",
                "accent": "#D946EF",
                "success": "#16A34A",
                "warning": "#D97706",
                "danger": "#DC2626",
            },
        },
    )


def write_legacy_fixture_registries(project: Path) -> None:
    write_json(project / "02-plan/theme-registry.json", beautiful_template_runtime.theme_registry(include_legacy=True))
    write_json(project / "02-plan/template-registry.json", beautiful_template_runtime.template_registry(include_legacy=True))


class SVGlideThemeAdherenceTest(unittest.TestCase):
    def test_adherence_passes_for_theme_colors_and_direct_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(
                project,
                '<svg xmlns="http://www.w3.org/2000/svg"><rect width="960" height="540" fill="#0F172A"/><text fill="#F8FAFC">标题</text><circle fill="#38BDF8"/></svg>',
            )

            result = svglide_theme_adherence.validate_project(project)
            svglide_theme_adherence.write_outputs(project, result)

            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertEqual(result["prepared_files"], svglide_theme.prepared_svg_hashes(project))
            self.assertTrue((project / "06-check/theme-adherence.json").exists())
            self.assertTrue((project / "receipts/theme-adherence.json").exists())

    def test_adherence_uses_project_theme_registry_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_project_theme_override(project)
            write_json(
                project / "02-plan/slide_plan.json",
                {"slides": [{"page": 1, "theme_id": "dark-clarity"}]},
            )
            validation = svglide_theme_validate.validate_project(project)
            svglide_theme_validate.write_outputs(project, validation)
            write_svg(
                project,
                '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#FFFFFF"/><circle fill="#123456"/><text fill="#111111">标题</text></svg>',
            )

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(validation["status"], "passed", validation["issues"])
            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertEqual(result["pages"][0]["theme_id"], "dark-clarity")

    def test_adherence_accepts_project_theme_token_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(
                project / "02-plan/slide_plan.json",
                {
                    "project_palette": {
                        "palette_id": "style.monochrome",
                        "data_series": ["#8A8A80", "#5E5E54", "#22C55E"],
                    },
                    "project_theme": {
                        "base_theme_id": "dark-clarity",
                        "palette_ref": "project_palette",
                        "token_overrides": {
                            "color.background": "#FAFADF",
                            "color.surface": "#FFFFFF",
                            "color.text": "#1A1A16",
                            "color.muted": "#8A8A80",
                            "color.primary": "#8A8A80",
                            "color.accent": "#5E5E54",
                        },
                    },
                    "slides": [{"page": 1, "theme_id": "dark-clarity"}],
                },
            )
            validation = svglide_theme_validate.validate_project(project)
            svglide_theme_validate.write_outputs(project, validation)
            write_svg(
                project,
                '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#FAFADF"/><rect fill="#FFFFFF"/><circle fill="#8A8A80"/><text fill="#1A1A16">标题</text></svg>',
            )

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(validation["status"], "passed", validation["issues"])
            self.assertEqual(result["status"], "passed", result["issues"])

    def test_adherence_fails_unknown_color(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(project, '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#0F172A"/><text fill="#F8FAFC">标题</text><circle fill="#123456"/></svg>')

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("theme_unknown_color", {item["code"] for item in result["issues"]})
            self.assertEqual(result["unknown_colors"][0]["color"], "#123456")

    def test_adherence_fails_contrast_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(project, '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#0F172A"/><text>标题</text></svg>')

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("contrast_unresolved", {item["code"] for item in result["issues"]})

    def test_adherence_reads_foreign_object_descendant_color(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(
                project,
                (
                    '<svg xmlns="http://www.w3.org/2000/svg">'
                    '<rect width="960" height="540" fill="#0F172A"/>'
                    '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml" style="color:#F8FAFC">标题</div></foreignObject>'
                    '</svg>'
                ),
            )

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertEqual([], result["contrast_unresolved"])

    def test_adherence_fails_low_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(project, '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#0F172A"/><text fill="#111827">标题</text></svg>')

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("contrast_too_low", {item["code"] for item in result["issues"]})

    def test_adherence_fails_stale_theme_validate_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = make_project(tmpdir)
            write_svg(project, '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#0F172A"/><text fill="#F8FAFC">标题</text></svg>')
            plan = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            plan["slides"][0]["title"] = "变更后的标题"
            write_json(project / "02-plan/slide_plan.json", plan)

            result = svglide_theme_adherence.validate_project(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("theme_validate_plan_stale", {item["code"] for item in result["issues"]})


if __name__ == "__main__":
    unittest.main()
