# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_aesthetic_review


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideAestheticReviewTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}]})
        (project / "05-preview").mkdir(parents=True, exist_ok=True)
        (project / "05-preview/preview.html").write_text("<html></html>", encoding="utf-8")
        write_json(project / "05-preview/preview-manifest.json", {"page_count": 1, "pages": [{"page": 1, "source_bytes": 12}]})
        write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
        return project

    def test_aesthetic_review_passes_with_clean_preview_artifacts(self) -> None:
        project = self.make_project()

        result = svglide_aesthetic_review.run_aesthetic_review(project)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["action"], "create_live")
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertTrue((project / "06-check/aesthetic-review.json").exists())

    def test_aesthetic_review_blocks_when_preview_lint_blocks(self) -> None:
        project = self.make_project()
        write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "repair_and_rerun"})

        result = svglide_aesthetic_review.run_aesthetic_review(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["action"], "repair_and_rerun")
        self.assertEqual(result["issues"][0]["code"], "preview_lint_not_clean")

    def test_aesthetic_review_blocks_page_count_mismatch(self) -> None:
        project = self.make_project()
        write_json(project / "05-preview/preview-manifest.json", {"page_count": 2, "pages": [{"page": 1, "source_bytes": 12}]})

        result = svglide_aesthetic_review.run_aesthetic_review(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["action"], "repair_and_rerun")
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("preview_page_count_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
