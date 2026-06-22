# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_runtime_review


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideRuntimeReviewTest(unittest.TestCase):
    def test_runtime_review_blocks_renderer_monoculture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            slides = [
                {"page": index, "renderer_id": "same", "layout_family": "same"}
                for index in range(1, 5)
            ]
            write_json(project / "02-plan/slide_plan.json", {"slides": slides})

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("renderer_monoculture", codes)
            self.assertIn("layout_family_monoculture", codes)

    def test_runtime_review_passes_diverse_renderers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            slides = [
                {"page": 1, "renderer_id": "cover", "layout_family": "cover"},
                {"page": 2, "renderer_id": "chart", "layout_family": "chart"},
                {"page": 3, "renderer_id": "timeline", "layout_family": "timeline"},
                {"page": 4, "renderer_id": "closing", "layout_family": "closing"},
            ]
            write_json(project / "02-plan/slide_plan.json", {"slides": slides})

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "passed")
            self.assertIn("registry", result)
            self.assertEqual(result["pages"][0]["registry_status"], "active")

    def test_runtime_review_blocks_unknown_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "unknown", "layout_family": "cover"}]})

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("renderer_unknown", codes)

    def test_runtime_review_blocks_inactive_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/renderer-registry.json",
                {
                    "schema_version": "svglide-renderer-registry/v1",
                    "renderers": [
                        {"id": "candidate_renderer", "status": "candidate", "family": "cover"},
                        {"id": "blocked_renderer", "status": "blocked", "family": "content"},
                    ],
                },
            )
            write_json(
                project / "02-plan/slide_plan.json",
                {"slides": [{"page": 1, "renderer_id": "candidate_renderer", "layout_family": "cover"}]},
            )

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("renderer_not_active", codes)

    def test_runtime_review_blocks_family_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "cover", "layout_family": "chart"}]})

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("renderer_family_mismatch", codes)

    def test_runtime_review_blocks_cover_asset_with_non_cover_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "chart", "layout_family": "chart"}]})
            write_json(
                project / "03-assets/asset-manifest.json",
                {
                    "status": "passed",
                    "acquired_assets": [
                        {"asset_id": "hero", "page": 1, "placement_role": "cover", "status": "acquired"}
                    ],
                },
            )

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("asset_renderer_mismatch", codes)

    def test_runtime_review_accepts_artboard_family_aliases_and_page_type_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/slide_plan.json",
                {
                    "slides": [
                        {
                            "page": 1,
                            "page_type": "cover",
                            "renderer_id": "artboard_satori.intelligence-brief",
                            "layout_family": "briefing",
                        },
                        {
                            "page": 2,
                            "page_type": "content",
                            "renderer_id": "artboard_satori.executive-dashboard",
                            "layout_family": "dashboard",
                        },
                        {
                            "page": 3,
                            "page_type": "closing",
                            "renderer_id": "artboard_satori.poster-stat-punch",
                            "layout_family": "poster_stat",
                        },
                    ]
                },
            )
            write_json(
                project / "03-assets/asset-manifest.json",
                {
                    "status": "passed",
                    "acquired_assets": [
                        {"asset_id": "hero", "page": 1, "placement_role": "cover", "status": "acquired"},
                        {"asset_id": "closing", "page": 3, "placement_role": "closing", "status": "acquired"},
                    ],
                },
            )

            result = svglide_runtime_review.run_runtime_review(project)

        self.assertEqual(result["status"], "passed", result["issues"])

    def test_runtime_review_blocks_decorative_semantic_element_without_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "cover", "layout_family": "cover"}]})
            write_json(
                project / "04-svg/artboard/page-001.semantic-map.json",
                {
                    "version": "svglide-semantic-map/v1",
                    "page": 1,
                    "template_id": "cover-hero",
                    "semantic_source": "CanvasSpec",
                    "elements": [
                        {
                            "element_id": "decorative-line-01",
                            "kind": "line",
                            "role": "decorative",
                            "bbox": {"x": 64, "y": 80, "width": 400, "height": 1},
                        }
                    ],
                },
            )

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("decorative_origin_missing", {item["code"] for item in result["issues"]})

    def test_runtime_review_blocks_unbound_decorative_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "cover", "layout_family": "cover"}]})
            write_json(
                project / "04-svg/artboard/page-001.semantic-map.json",
                {
                    "version": "svglide-semantic-map/v1",
                    "page": 1,
                    "template_id": "cover-hero",
                    "semantic_source": "CanvasSpec",
                    "elements": [
                        {
                            "element_id": "random-line-01",
                            "kind": "line",
                            "role": "decorative",
                            "element_type": "decorative_line",
                            "origin": {"type": "template", "id": "cover-hero", "reason": "template decorative rule"},
                            "bbox": {"x": 64, "y": 80, "width": 400, "height": 1},
                        }
                    ],
                },
            )

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("decorative_semantic_purpose_missing", {item["code"] for item in result["issues"]})

    def test_runtime_review_accepts_semantic_connector_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "renderer_id": "cover", "layout_family": "cover"}]})
            write_json(
                project / "04-svg/artboard/page-001.semantic-map.json",
                {
                    "version": "svglide-semantic-map/v1",
                    "page": 1,
                    "template_id": "timeline-steps",
                    "semantic_source": "CanvasSpec",
                    "elements": [
                        {
                            "element_id": "timeline-connector-01",
                            "kind": "line",
                            "role": "decorative",
                            "element_type": "decorative_line",
                            "semantic_purpose": "timeline connector",
                            "origin": {"type": "template", "id": "timeline-steps", "reason": "template timeline connector"},
                            "bbox": {"x": 120, "y": 260, "width": 620, "height": 1},
                        }
                    ],
                },
            )

            result = svglide_runtime_review.run_runtime_review(project)

            self.assertEqual(result["status"], "passed", result["issues"])


if __name__ == "__main__":
    unittest.main()
