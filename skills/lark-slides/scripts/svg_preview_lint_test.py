# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import svg_preview_lint


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class SvgPreviewLintTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        project = root / "demo"
        (project / "preview").mkdir(parents=True)
        (project / "prepared").mkdir()
        (project / "assets").mkdir()
        write_json(project / "slide_plan.json", {"svg_files": [{"page": 1, "path": "prepared/page-001.svg"}]})
        return project

    def write_preview(self, project: Path, ref: str = "../prepared/page-001.svg") -> None:
        (project / "preview" / "preview.html").write_text(
            f"<html><body><img src=\"{ref}\" /></body></html>",
            encoding="utf-8",
        )

    def write_svg(self, project: Path, body: str) -> None:
        (project / "prepared" / "page-001.svg").write_text(
            f"""
            <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
              {body}
            </svg>
            """,
            encoding="utf-8",
        )

    def lint(self, project: Path) -> dict[str, object]:
        return svg_preview_lint.lint_project(
            project,
            project / "preview" / "preview.html",
            project / "slide_plan.json",
        )

    def codes(self, result: dict[str, object]) -> list[str]:
        checks = result.get("checks")
        self.assertIsInstance(checks, list)
        return [str(item.get("code")) for item in checks if isinstance(item, dict)]

    def test_missing_preview_fails(self) -> None:
        project = self.make_project()
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
            <text x="80" y="90" font-size="28" fill="#111827">Title</text>
            <text x="80" y="150" font-size="18" fill="#334155">Body</text>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("preview_missing", self.codes(result))

    def test_missing_svg_fails(self) -> None:
        project = self.make_project()
        self.write_preview(project)

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("svg_file_missing", self.codes(result))

    def test_svg_parse_failure_fails(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        (project / "prepared" / "page-001.svg").write_text("<svg><text>broken", encoding="utf-8")

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("svg_parse_failed", self.codes(result))

    def test_detects_obvious_text_overlap(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
            <text x="120" y="150" font-size="36" fill="#111827">Overlap text</text>
            <text x="126" y="154" font-size="36" fill="#111827">Overlap text</text>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("text_overlap", self.codes(result))

    def test_detects_light_text_without_dark_backing(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#ffffff" />
            <circle cx="720" cy="190" r="64" fill="#dbeafe" />
            <text x="120" y="150" font-size="34" fill="#ffffff">Invisible title</text>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("light_text_without_dark_backing", self.codes(result))

    def test_normal_preview_passes_and_cli_outputs_schema(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        (project / "assets" / "hero.png").write_bytes(b"not-a-real-png-but-present")
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
            <rect x="76" y="118" width="280" height="150" fill="#e2e8f0" />
            <text x="80" y="82" font-size="28" fill="#111827">Strategy review</text>
            <text x="96" y="170" font-size="18" fill="#334155">Pipeline status</text>
            <image href="@./assets/hero.png" x="560" y="120" width="300" height="180" />
            """,
        )

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = svg_preview_lint.main(
                [
                    "--project",
                    str(project),
                    "--preview",
                    str(project / "preview" / "preview.html"),
                    "--plan",
                    str(project / "slide_plan.json"),
                ]
            )
        result = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["schema_version"], "svglide-preview-lint/v1")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["visual_score_mode"], "advisory")


if __name__ == "__main__":
    unittest.main()
