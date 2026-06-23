#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_theme_validate
import beautiful_template_runtime


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_plan(project: Path, *, theme_id: str = "dark-clarity", template_id: str = "cover-hero") -> None:
    if theme_id in beautiful_template_runtime.LEGACY_THEME_COLORS:
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
                        "template_id": template_id,
                        "theme_id": theme_id,
                        "theme": {"colors": {"background": "#0F172A"}},
                    },
                }
            ],
        },
    )


def write_multi_theme_plan(project: Path, *, allow_multi_theme: bool | None = None, scope: str = "deck") -> None:
    write_legacy_fixture_registries(project)
    plan: dict[str, object] = {
        "generation_mode": "artboard_satori",
        "slides": [
            {
                "page": 1,
                "title": "第一页",
                "canvas_spec": {
                    "version": "svglide-canvas-spec/v1",
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                    "theme": {"colors": {"background": "#0F172A"}},
                },
            },
            {
                "page": 2,
                "title": "第二页",
                "canvas_spec": {
                    "version": "svglide-canvas-spec/v1",
                    "template_id": "data-story",
                    "theme_id": "forest-signal",
                    "theme": {"colors": {"background": "#102A1B"}},
                },
            },
        ],
    }
    if allow_multi_theme is not None:
        plan["theme_policy"] = {"allow_multi_theme": allow_multi_theme, "scope": scope}
    write_json(project / "02-plan/slide_plan.json", plan)


def write_project_theme(project: Path, *, theme_id: str = "project-theme", primary: str = "#123456") -> None:
    write_json(
        project / "02-plan/theme-registry.json",
        {
            "schema_version": "svglide-theme-registry/v1",
            "themes": [
                {
                    "id": theme_id,
                    "status": "active",
                    "path": "themes/project-theme.json",
                    "template_bindings": {"supported_template_ids": ["executive-dashboard"]},
                }
            ],
        },
    )
    write_json(
        project / "themes/project-theme.json",
        {
            "schema_version": "svglide-theme/v1",
            "theme_id": theme_id,
            "mode": "light",
            "colors": {
                "background": "#FFFFFF",
                "surface": "#F8FAFC",
                "text": "#111111",
                "muted": "#64748B",
                "primary": primary,
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


class SVGlideThemeValidateTest(unittest.TestCase):
    def test_validate_project_passes_for_known_theme_and_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_plan(project)

            result = svglide_theme_validate.validate_project(project)
            svglide_theme_validate.write_outputs(project, result)

            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertEqual(result["summary"]["error_count"], 0)
            self.assertEqual(result["pages"][0]["theme_id"], "dark-clarity")
            self.assertTrue((project / "06-check/theme-validate.json").exists())
            self.assertTrue((project / "receipts/theme-validate.json").exists())

    def test_validate_project_uses_project_theme_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_project_theme(project)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "theme_id": "project-theme"}]})

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["inputs"]["theme_registry"], "02-plan/theme-registry.json")
        self.assertEqual(result["theme_files"][0]["path"], "themes/project-theme.json")
        self.assertEqual(result["pages"][0]["theme_id"], "project-theme")

    def test_validate_project_allows_project_theme_template_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_project_theme(project)
            write_plan(project, theme_id="project-theme", template_id="executive-dashboard")

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["pages"][0]["template_id"], "executive-dashboard")

    def test_validate_project_fails_unknown_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_plan(project, theme_id="missing-theme")

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("theme_invalid", {item["code"] for item in result["issues"]})

    def test_validate_project_fails_template_theme_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_plan(project, theme_id="dark-clarity", template_id="missing-template")

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("template_unknown", {item["code"] for item in result["issues"]})

    def test_cli_writes_failed_receipt_for_missing_theme_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": {"template_id": "cover-hero"}}]})

            with contextlib.redirect_stdout(io.StringIO()):
                code = svglide_theme_validate.main([project.as_posix()])

            payload = json.loads((project / "06-check/theme-validate.json").read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("theme_id_missing", {item["code"] for item in payload["issues"]})

    def test_validate_project_fails_multiple_themes_without_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_multi_theme_plan(project)

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"]["theme_count"], 2)
        self.assertIn("deck_theme_not_unified", {item["code"] for item in result["issues"]})

    def test_validate_project_allows_intentional_multiple_themes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_multi_theme_plan(project, allow_multi_theme=True, scope="page")

            result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["summary"]["theme_count"], 2)


if __name__ == "__main__":
    unittest.main()
