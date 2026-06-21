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

import svglide_visual_acceptance as visual_acceptance


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return visual_acceptance.file_sha256(path)


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def make_project(root: Path, *, generation_mode: str = "artboard_satori", overlap: bool = False) -> Path:
    project = root / "project"
    for directory in ["00-input", "02-plan", "03-assets", "04-svg/artboard", "05-preview", "06-check", "07-create", "receipts"]:
        (project / directory).mkdir(parents=True, exist_ok=True)
    write_json(project / "00-input/instruction.json", {"topic": "visual acceptance", "target_slide_count": 1, "language": "zh-CN"})
    slide = {
        "page": 1,
        "title": "Visual Acceptance",
        "key_message": "Rendered evidence must pass before delivery claims.",
        "renderer_id": "artboard_satori.cover-hero" if generation_mode == "artboard_satori" else "direct_svg.cover",
        "layout_family": "cover",
        "canvas_spec": {
            "version": "svglide-canvas-spec/v1",
            "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
            "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "theme": {"colors": {"background": "#0F172A", "text": "#F8FAFC", "accent": "#38BDF8"}},
            "content": {"title": "Visual Acceptance"},
        },
    }
    write_json(
        project / "02-plan/slide_plan.json",
        {
            "route": "svglide-svg",
            "generation_mode": generation_mode,
            "page_count": 1,
            "target_slide_count": 1,
            "slides": [slide],
        },
    )
    write_json(project / "03-assets/asset-manifest.json", {"status": "passed", "summary": {"error_count": 0}})
    write(project / "04-svg/page-001.svg", '<svg width="960" height="540"></svg>')
    write(project / "04-svg/artboard/page-001.png", b"page-png")
    write(project / "05-preview/contact-sheet.png", b"contact-sheet")
    write(project / "05-preview/preview.html", "<html><body>preview</body></html>")
    write_json(
        project / "05-preview/preview-manifest.json",
        {
            "page_count": 1,
            "pages": [{"page": 1, "source_path": "04-svg/prepared/page-001.svg", "source_bytes": 42}],
        },
    )
    elements: list[dict[str, object]] = [
        {
            "element_id": "title",
            "kind": "text",
            "role": "title",
            "text": "Visual Acceptance",
            "bbox": {"x": 80, "y": 80, "width": 720, "height": 72},
        }
    ]
    if overlap:
        elements.append(
            {
                "element_id": "subtitle",
                "kind": "text",
                "role": "subtitle",
                "text": "Overlapping",
                "bbox": {"x": 100, "y": 90, "width": 500, "height": 60},
            }
        )
    write_json(
        project / "04-svg/artboard/page-001.semantic-map.json",
        {
            "version": "svglide-semantic-map/v1",
            "page": 1,
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "elements": elements,
        },
    )
    nodes = [
        {"id": "title", "kind": "text", "x": 80, "y": 80, "width": 720, "height": 72, "text": "Visual Acceptance"}
    ]
    if overlap:
        nodes.append({"id": "subtitle", "kind": "text", "x": 100, "y": 90, "width": 500, "height": 60, "text": "Overlapping"})
    write_json(project / "04-svg/artboard/page-001.node-layout-map.json", {"version": "svglide-node-layout-map/v1", "page": 1, "nodes": nodes})
    write_json(
        project / "04-svg/artboard/page-001.receipt.json",
        {
            "status": "passed",
            "page": 1,
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "semantic_map": "04-svg/artboard/page-001.semantic-map.json",
            "semantic_map_sha256": sha(project / "04-svg/artboard/page-001.semantic-map.json"),
            "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
            "node_layout_map_sha256": sha(project / "04-svg/artboard/page-001.node-layout-map.json"),
            "png": "04-svg/artboard/page-001.png",
            "png_sha256": sha(project / "04-svg/artboard/page-001.png"),
        },
    )
    write_json(
        project / "receipts/generate_svg.json",
        {
            "status": "passed",
            "generation_mode": generation_mode,
            "artboard_receipts": ["04-svg/artboard/page-001.receipt.json"] if generation_mode == "artboard_satori" else [],
            "contact_sheet": {
                "path": "05-preview/contact-sheet.png",
                "sha256": sha(project / "05-preview/contact-sheet.png"),
            },
        },
    )
    write_json(
        project / "06-check/quality-gate.json",
        {"status": "passed", "prepared_files": [{"path": "04-svg/prepared/page-001.svg", "sha256": "prepared"}]},
    )
    write_json(
        project / "07-create/dry-run.json",
        {"status": "passed", "prepared_files": [{"path": "04-svg/prepared/page-001.svg", "sha256": "prepared"}]},
    )
    return project


def issue_codes(result: dict[str, object]) -> set[str]:
    issues = result.get("issues")
    return {item.get("code") for item in issues if isinstance(item, dict)} if isinstance(issues, list) else set()


def rewrite_semantic_map(project: Path, payload: dict[str, object]) -> None:
    semantic_path = project / "04-svg/artboard/page-001.semantic-map.json"
    write_json(semantic_path, payload)
    receipt_path = project / "04-svg/artboard/page-001.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["semantic_map_sha256"] = sha(semantic_path)
    if isinstance(payload.get("template_id"), str):
        receipt["template_id"] = payload["template_id"]
    write_json(receipt_path, receipt)


class VisualAcceptanceTest(unittest.TestCase):
    def test_valid_artboard_project_passes_and_writes_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertTrue(result["deliverable_pass"])
            artifacts = result["artboard_artifacts"]
            self.assertEqual(
                {item["path"] for item in artifacts if isinstance(item, dict)},
                {
                    "04-svg/artboard/page-001.receipt.json",
                    "04-svg/artboard/page-001.semantic-map.json",
                    "04-svg/artboard/page-001.node-layout-map.json",
                    "04-svg/artboard/page-001.png",
                },
            )
            evidence_pages = result["visual_evidence"]["pages"]
            self.assertEqual(evidence_pages[0]["page"], 1)
            self.assertEqual(evidence_pages[0]["evidence_path"], "05-preview/contact-sheet.png")
            self.assertEqual(evidence_pages[0]["preview_anchor"], "05-preview/preview.html#page-1")
            self.assertEqual(evidence_pages[0]["contact_sheet_tile"], {"x": 16, "y": 16, "width": 320, "height": 180})
            self.assertEqual(result["deck_rhythm"]["schema_version"], "svglide-deck-rhythm/v1")
            self.assertTrue((project / "06-check/visual-acceptance.json").exists())
            self.assertEqual(
                json.loads((project / "06-check/visual-acceptance.json").read_text(encoding="utf-8")),
                json.loads((project / "receipts/visual_acceptance.json").read_text(encoding="utf-8")),
            )

    def test_missing_contact_sheet_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            (project / "05-preview/contact-sheet.png").unlink()

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("contact_sheet_missing", issue_codes(result))

    def test_stale_contact_sheet_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            (project / "05-preview/contact-sheet.png").write_bytes(b"changed")

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("contact_sheet_stale", issue_codes(result))

    def test_stale_page_png_failure_includes_visual_evidence_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            (project / "04-svg/artboard/page-001.png").write_bytes(b"changed")

            result = visual_acceptance.run_visual_acceptance(project)

            stale = [issue for issue in result["issues"] if issue["code"] == "page_png_png_stale"][0]
            self.assertEqual(stale["page"], 1)
            self.assertEqual(stale["path"], "04-svg/artboard/page-001.png")
            self.assertEqual(stale["evidence_path"], "05-preview/contact-sheet.png")
            self.assertEqual(stale["preview_anchor"], "05-preview/preview.html#page-1")
            self.assertEqual(stale["contact_sheet_tile"], {"x": 16, "y": 16, "width": 320, "height": 180})

    def test_unregistered_decorative_path_fails_template_guardrail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["elements"].append(
                {
                    "element_id": "spike",
                    "kind": "path",
                    "role": "decorative",
                    "bbox": {"x": 700, "y": 60, "width": 120, "height": 90},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            codes = issue_codes(result)
            self.assertIn("decorative_kind_not_allowed", codes)
            self.assertIn("unregistered_template_motif", codes)
            self.assertIn("unregistered_sharp_decoration", codes)

    def test_template_motif_boolean_does_not_bypass_admitted_motif(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            plan_path = project / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["slides"][0]["canvas_spec"]["template_id"] = "comparison-cards"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["template_id"] = "comparison-cards"
            semantic["elements"].append(
                {
                    "element_id": "random-spike",
                    "kind": "path",
                    "role": "decorative",
                    "template_motif": True,
                    "bbox": {"x": 700, "y": 60, "width": 120, "height": 90},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("unregistered_template_motif", issue_codes(result))

    def test_registered_decorative_motif_passes_template_guardrail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["elements"].append(
                {
                    "element_id": "accent-orbit",
                    "kind": "circle",
                    "role": "decorative",
                    "motif_id": "orbit",
                    "bbox": {"x": 720, "y": 70, "width": 90, "height": 90},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "passed", result["issues"])

    def test_chart_like_mark_requires_chart_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["elements"].append(
                {
                    "element_id": "chart-bars",
                    "kind": "rect",
                    "role": "chart",
                    "bbox": {"x": 620, "y": 180, "width": 180, "height": 120},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("chart_like_mark_without_contract", issue_codes(result))

    def test_image_element_requires_canvas_slot_and_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["elements"].append(
                {
                    "element_id": "hero-image",
                    "kind": "image",
                    "role": "image",
                    "bbox": {"x": 600, "y": 120, "width": 220, "height": 180},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            codes = issue_codes(result)
            self.assertIn("image_without_canvas_slot", codes)
            self.assertIn("image_without_canvas_source_ref", codes)

    def test_image_element_with_canvas_slot_passes_template_guardrail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            plan_path = project / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            slide = plan["slides"][0]
            slide["canvas_spec"]["template_id"] = "image-feature"
            slide["canvas_spec"]["content"]["key_visual"] = {"asset_id": "asset:hero", "slot": "hero_image"}
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            semantic = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic["template_id"] = "image-feature"
            semantic["elements"].append(
                {
                    "element_id": "hero-image",
                    "kind": "image",
                    "role": "image",
                    "source_ref": "canvas_spec.content.key_visual",
                    "bbox": {"x": 600, "y": 120, "width": 220, "height": 180},
                }
            )
            rewrite_semantic_map(project, semantic)

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "passed", result["issues"])

    def test_deck_rhythm_flags_collapsed_visual_recipe_and_fragmented_theme(self) -> None:
        plan = {
            "slides": [
                {"layout_family": "content", "renderer_id": "same-renderer", "visual_recipe": "same-look"},
                {"layout_family": "content", "renderer_id": "same-renderer", "visual_recipe": "same-look"},
                {"layout_family": "content", "renderer_id": "same-renderer", "visual_recipe": "same-look"},
                {"layout_family": "content", "renderer_id": "same-renderer", "visual_recipe": "same-look"},
            ]
        }
        page_results = [
            {"page": 1, "theme_id": "theme-a"},
            {"page": 2, "theme_id": "theme-b"},
            {"page": 3, "theme_id": "theme-c"},
            {"page": 4, "theme_id": "theme-d"},
        ]
        issues: list[dict[str, object]] = []

        rhythm = visual_acceptance.build_deck_rhythm(plan, page_results, issues)

        codes = {item["code"] for item in issues}
        self.assertEqual(rhythm["unique_visual_recipe_count"], 1)
        self.assertIn("layout_rhythm_collapsed", codes)
        self.assertIn("renderer_sequence_collapsed", codes)
        self.assertIn("visual_recipe_collapsed", codes)
        self.assertIn("renderer_sequence_repetition_too_long", codes)
        self.assertIn("theme_palette_too_fragmented", codes)

    def test_high_priority_text_overlap_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp), overlap=True)

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "failed")
            overlap = [issue for issue in result["issues"] if issue["code"] == "high_priority_text_overlap"][0]
            self.assertEqual(overlap["evidence_path"], "05-preview/contact-sheet.png")
            self.assertEqual(overlap["preview_anchor"], "05-preview/preview.html#page-1")
            self.assertEqual(overlap["contact_sheet_tile"], {"x": 16, "y": 16, "width": 320, "height": 180})

    def test_direct_svg_is_engineering_only_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp), generation_mode="direct_svg")

            result = visual_acceptance.run_visual_acceptance(project)

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["action"], "engineering_only")
            self.assertFalse(result["deliverable_pass"])


if __name__ == "__main__":
    unittest.main()
