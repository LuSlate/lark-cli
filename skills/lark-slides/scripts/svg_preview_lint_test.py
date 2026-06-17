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

    def lint(self, project: Path, validation_profile: str = "") -> dict[str, object]:
        return svg_preview_lint.lint_project(
            project,
            project / "preview" / "preview.html",
            project / "slide_plan.json",
            validation_profile,
        )

    def write_sparse_pages(self, project: Path, page_count: int, *, validation_profile: object | None = None) -> None:
        refs = []
        preview_images = []
        for page in range(1, page_count + 1):
            name = f"page-{page:03d}.svg"
            refs.append({"page": page, "path": f"prepared/{name}"})
            preview_images.append(f'<img src="../prepared/{name}" />')
            (project / "prepared" / name).write_text(
                f"""
                <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
                  <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
                  <path d="M80 420 C240 360 420 470 620 390" fill="none" stroke="#94a3b8" stroke-width="6" />
                  <text x="80" y="120" font-size="34" fill="#111827">Thin visual idea {page}</text>
                  <text x="80" y="172" font-size="18" fill="#334155">One short line is not enough structure.</text>
                </svg>
                """,
                encoding="utf-8",
            )
        plan: dict[str, object] = {"svg_files": refs}
        if validation_profile is not None:
            plan["validation_profile"] = validation_profile
        write_json(project / "slide_plan.json", plan)
        (project / "preview" / "preview.html").write_text("<html><body>" + "".join(preview_images) + "</body></html>", encoding="utf-8")

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

    def test_detects_bubble_label_backing_overlapping_note(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#111827" />
            <circle id="bubble-openai" cx="460" cy="260" r="82" fill="#2563eb" />
            <rect id="bubble-openai-name-plate" x="382" y="222" width="156" height="52" rx="10" fill="#0f172a" />
            <text id="bubble-openai-label" x="408" y="254" font-size="18" fill="#ffffff">OpenAI</text>
            <foreignObject id="bubble-openai-note" x="392" y="252" width="180" height="74" color="#e5e7eb">
              <div xmlns="http://www.w3.org/1999/xhtml">Large funding round and GPU demand concentration.</div>
            </foreignObject>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertIn("shape_text_overlap", self.codes(result))

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
        self.assertEqual(result["validation_profile"], "authoring")
        self.assertEqual(result["visual_score_threshold"], 75)

    def test_sparse_decorative_page_gets_density_warning(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
            <path d="M80 420 C240 360 420 470 620 390" fill="none" stroke="#94a3b8" stroke-width="6" />
            <text x="80" y="120" font-size="34" fill="#111827">Thin visual idea</text>
            <text x="80" y="172" font-size="18" fill="#334155">One short line is not enough structure.</text>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "passed")
        self.assertIn("low_information_density", self.codes(result))
        self.assertLess(result["visual_score"], 100)

    def test_repeated_multi_page_layout_gets_variety_warning(self) -> None:
        project = self.make_project()
        refs = []
        preview_images = []
        for page in range(1, 5):
            name = f"page-{page:03d}.svg"
            refs.append({"page": page, "path": f"prepared/{name}"})
            preview_images.append(f'<img src="../prepared/{name}" />')
            (project / "prepared" / name).write_text(
                f"""
                <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
                  <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
                  <rect x="80" y="120" width="260" height="120" fill="#e2e8f0" />
                  <rect x="380" y="140" width="160" height="24" fill="#2563eb" />
                  <rect x="380" y="180" width="120" height="24" fill="#60a5fa" />
                  <circle cx="760" cy="190" r="52" fill="#c7d2fe" />
                  <text x="80" y="82" font-size="28" fill="#111827">Page {page}</text>
                  <text x="96" y="170" font-size="18" fill="#334155">Status item</text>
                </svg>
                """,
                encoding="utf-8",
            )
        write_json(project / "slide_plan.json", {"svg_files": refs})
        (project / "preview" / "preview.html").write_text("<html><body>" + "".join(preview_images) + "</body></html>", encoding="utf-8")

        result = self.lint(project)

        self.assertEqual(result["status"], "passed")
        self.assertIn("low_visual_variety", self.codes(result))

    def test_authoring_allows_warnings_above_authoring_threshold(self) -> None:
        project = self.make_project()
        self.write_sparse_pages(project, 4)

        result = self.lint(project, "authoring")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["warning_count"], 5)
        self.assertEqual(result["visual_score"], 65)
        self.assertEqual(result["visual_score_threshold"], 75)
        self.assertFalse(result["visual_score_passed"])
        self.assertEqual(result["visual_score_mode"], "advisory")

    def test_production_fails_when_visual_score_is_below_threshold(self) -> None:
        project = self.make_project()
        self.write_sparse_pages(project, 3)

        result = self.lint(project, "production")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["warning_count"], 3)
        self.assertEqual(result["visual_score"], 79)
        self.assertEqual(result["visual_score_threshold"], 85)
        self.assertFalse(result["visual_score_passed"])

    def test_golden_fails_when_warning_count_is_nonzero(self) -> None:
        project = self.make_project()
        self.write_preview(project)
        write_json(
            project / "slide_plan.json",
            {
                "validation_profile": {"profile": "golden"},
                "svg_files": [{"page": 1, "path": "prepared/page-001.svg"}],
            },
        )
        self.write_svg(
            project,
            """
            <rect x="0" y="0" width="960" height="540" fill="#f8fafc" />
            <path d="M80 420 C240 360 420 470 620 390" fill="none" stroke="#94a3b8" stroke-width="6" />
            <text x="80" y="120" font-size="34" fill="#111827">Thin visual idea</text>
            <text x="80" y="172" font-size="18" fill="#334155">One short line is not enough structure.</text>
            """,
        )

        result = self.lint(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_profile"], "golden")
        self.assertEqual(result["visual_score"], 93)
        self.assertEqual(result["visual_score_threshold"], 90)
        self.assertFalse(result["warning_gate_passed"])

    def test_cli_reads_validation_profile_from_plan(self) -> None:
        project = self.make_project()
        self.write_sparse_pages(project, 3, validation_profile="production")

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

        self.assertEqual(exit_code, 1)
        self.assertEqual(result["validation_profile"], "production")
        self.assertEqual(result["visual_score_threshold"], 85)


if __name__ == "__main__":
    unittest.main()
