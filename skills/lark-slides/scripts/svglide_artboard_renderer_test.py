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

import svglide_artboard_renderer as artboard


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def canvas_spec() -> dict[str, object]:
    return {
        "version": "svglide-canvas-spec/v1",
        "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
        "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
        "template_id": "cover-hero",
        "theme_id": "dark-clarity",
        "theme": {
            "colors": {
                "background": "#0F172A",
                "panel": "#111827",
                "primary": "#38BDF8",
                "accent": "#A78BFA",
                "text": "#F8FAFC",
                "muted": "#CBD5E1",
            }
        },
        "content": {
            "eyebrow": "P0A",
            "title": "受控画板生成",
            "subtitle": "CanvasSpec 作为语义真源。",
            "chips": ["CanvasSpec", "Satori Preview", "SVGlide"],
        },
        "semantic_elements": [
            {
                "element_id": "title",
                "kind": "text",
                "role": "title",
                "source_ref": "canvas_spec.content.title",
                "bbox": {"x": 84, "y": 142, "width": 628, "height": 142},
            }
        ],
        "quality_constraints": {
            "max_title_lines": 2,
            "min_font_size": 18,
            "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
        },
    }


class SVGlideArtboardRendererTest(unittest.TestCase):
    def test_p0_theme_registry_components_and_fixtures_are_registered(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        renderer_dir = scripts_dir / "artboard_renderer"
        theme_registry = json.loads((renderer_dir / "themes/registry.json").read_text(encoding="utf-8"))
        theme_ids = [item["id"] for item in theme_registry["themes"] if item.get("status") == "active"]
        repo_root = scripts_dir.parents[2]
        required_theme_ids = {
            "dark-clarity",
            "forest-signal",
            "warm-editorial",
            "blueprint-technical",
            "editorial-tritone",
            "cobalt-grid",
            "finance-dark",
            "swiss-red",
            "glass-neon",
            "paper-research",
        }
        self.assertGreaterEqual(len(theme_ids), 10)
        self.assertTrue(required_theme_ids.issubset(set(theme_ids)))
        for record in theme_registry["themes"]:
            theme_path = repo_root / record["path"]
            payload = json.loads(theme_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["theme_id"], record["id"])
            self.assertTrue({"background", "panel", "primary", "accent", "text", "muted"}.issubset(payload["colors"]))

        template_registry = json.loads((scripts_dir.parent / "references/svglide-template-registry.json").read_text(encoding="utf-8"))
        active_templates = {item["id"]: item for item in template_registry["templates"] if item.get("status") == "active"}
        required_template_ids = {
            "cover-hero",
            "comparison-cards",
            "summary-final",
            "section-title",
            "agenda-list",
            "timeline-steps",
            "process-flow",
            "metric-dashboard",
            "quote-focus",
            "image-feature",
            "research-poster",
            "data-story",
            "risk-alert",
            "roadmap-lanes",
            "architecture-blueprint",
        }
        self.assertGreaterEqual(len(active_templates), 15)
        self.assertTrue(required_template_ids.issubset(set(active_templates)))
        for template in active_templates.values():
            self.assertTrue(set(theme_ids).issubset(set(template["supported_theme_ids"])))

        components = (renderer_dir / "components/primitives.mjs").read_text(encoding="utf-8")
        for export_name in ["Title", "Subtitle", "Chip", "StatCard", "ImageFrame"]:
            self.assertIn(f"export function {export_name}", components)

        component_registry = json.loads((scripts_dir.parent / "references/svglide-component-registry.json").read_text(encoding="utf-8"))
        active_components = [item for item in component_registry["components"] if item.get("status") == "active"]
        self.assertGreaterEqual(len(active_components), 20)
        layout_registry = json.loads((scripts_dir.parent / "references/svglide-layout-archetypes.json").read_text(encoding="utf-8"))
        active_layouts = [item for item in layout_registry["archetypes"] if item.get("status") == "active"]
        self.assertGreaterEqual(len(active_layouts), 8)
        source_intake = json.loads((scripts_dir.parent / "references/svglide-p1-source-intake.json").read_text(encoding="utf-8"))
        self.assertEqual("forbidden", source_intake["policy"]["runtime_import"])
        self.assertGreaterEqual(source_intake["p1_abstractions"]["template_count"], 15)
        required_source_fields = {
            "source_path",
            "source_type",
            "extract_fields",
            "conversion_target",
            "acceptance_rule",
            "forbidden_usage",
            "source_hash_or_version",
            "license_or_provenance",
        }
        for source in source_intake["sources"]:
            self.assertTrue(required_source_fields.issubset(source))
            if source["id"] == "ppt-master-examples":
                self.assertIn("MIT", source["license_or_provenance"])
                self.assertNotIn("no LICENSE", source["license_or_provenance"])
            self.assertTrue(source["conversion_records"])
            for record in source["conversion_records"]:
                self.assertTrue(record["source_examples"])
                self.assertTrue(record["abstraction_record"])
                self.assertTrue(record["canvas_spec_fields"])
                self.assertTrue(record["registry_output"]["templates"])
                self.assertTrue(record["registry_output"]["themes"])
                self.assertTrue(record["registry_output"]["components"])
                self.assertTrue(record["registry_output"]["layouts"])
                self.assertTrue(record["registry_output"]["golden_fixtures"])
                self.assertTrue(record["acceptance_rule"])

        p0b_plan = json.loads((scripts_dir / "fixtures/svglide_artboard/p0b-three-page/02-plan/slide_plan.json").read_text(encoding="utf-8"))
        fixture_theme_ids = [slide["canvas_spec"]["theme_id"] for slide in p0b_plan["slides"]]
        self.assertEqual(["dark-clarity", "forest-signal", "warm-editorial"], fixture_theme_ids)
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        for template_id in active_templates:
            golden = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            self.assertEqual(golden["template_id"], template_id)
            self.assertIn(golden["theme_id"], theme_ids)
            issues = artboard.validate_canvas_spec(golden, page=1)
            registry_issues, _ = artboard.validate_registry_bindings(Path(tempfile.gettempdir()), golden, page=1)
            self.assertEqual([], issues + registry_issues)

    def test_p1_active_template_golden_fixtures_render(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        template_registry = json.loads((scripts_dir.parent / "references/svglide-template-registry.json").read_text(encoding="utf-8"))
        active_template_ids = sorted(item["id"] for item in template_registry["templates"] if item.get("status") == "active")
        slides = []
        for page, template_id in enumerate(active_template_ids, 1):
            golden = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            slides.append({"page": page, "title": golden["content"]["title"], "canvas_spec": golden})
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})

            result = artboard.render_project(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["max_workers"], 4)
            self.assertEqual(len(result["artboard_receipts"]), len(active_template_ids))
            self.assertTrue((project / "05-preview/contact-sheet.png").exists())
            for page in range(1, len(active_template_ids) + 1):
                self.assertTrue((project / f"04-svg/artboard/page-{page:03d}.png").exists())
                self.assertTrue((project / f"04-svg/page-{page:03d}.svg").exists())

    def test_satori_adapter_packaging_is_release_safe(self) -> None:
        renderer_dir = Path(__file__).resolve().parent / "artboard_renderer"
        package = json.loads((renderer_dir / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"]["satori"], "0.26.0")
        self.assertEqual(package["dependencies"]["@resvg/resvg-js"], "2.6.2")
        self.assertNotIn("file:", json.dumps(package))
        self.assertTrue((renderer_dir / "dist/render.mjs").exists())
        lockfile = (renderer_dir / "pnpm-lock.yaml").read_text(encoding="utf-8")
        self.assertNotIn("satori@file:", lockfile)
        self.assertNotIn("@resvg/resvg-js@file:", lockfile)
        self.assertNotIn("file:../../", lockfile)

    def test_render_project_writes_artboard_and_svglide_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/slide_plan.json",
                {
                    "generation_mode": "artboard_satori",
                    "slides": [
                        {
                            "page": 1,
                            "title": "受控画板生成",
                            "canvas_spec": canvas_spec(),
                        }
                    ],
                },
            )

            result = artboard.render_project(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["max_workers"], 1)
            self.assertEqual(result["artboard_receipts"], ["04-svg/artboard/page-001.receipt.json"])
            self.assertEqual(
                result["additional_receipts"],
                [
                    "receipts/canvas-spec-validate.json",
                    "receipts/artboard-render.json",
                    "receipts/satori-bridge.json",
                ],
            )
            self.assertEqual(result["contact_sheet"]["path"], "05-preview/contact-sheet.png")
            self.assertTrue((project / "04-svg/artboard/page-001.png").exists())
            self.assertTrue((project / "04-svg/artboard/page-001.render-metadata.json").exists())
            self.assertTrue((project / "04-svg/artboard/page-001.canvas-template.svg").exists())
            self.assertTrue((project / "05-preview/contact-sheet.png").exists())
            svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")
            self.assertIn('xmlns:slide="https://slides.bytedance.com/ns"', svg)
            self.assertIn('slide:role="slide"', svg)
            self.assertIn('slide:shape-type="text"', svg)
            self.assertIn('<div xmlns="http://www.w3.org/1999/xhtml"', svg)
            self.assertNotIn("html:div", svg)
            receipt = json.loads((project / "04-svg/artboard/page-001.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["version"], "svglide-artboard-receipt/v1")
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["template_id"], "cover-hero")
            self.assertEqual(receipt["theme_id"], "dark-clarity")
            self.assertEqual(receipt["png_sha256"], artboard.file_sha256(project / "04-svg/artboard/page-001.png"))
            self.assertEqual(receipt["render_metadata_sha256"], artboard.file_sha256(project / "04-svg/artboard/page-001.render-metadata.json"))
            self.assertEqual(receipt["canvas_template_svg"], "04-svg/artboard/page-001.canvas-template.svg")
            self.assertEqual(receipt["canvas_template_svg_sha256"], artboard.file_sha256(project / "04-svg/artboard/page-001.canvas-template.svg"))
            self.assertEqual(receipt["compiler_input"], "04-svg/artboard/page-001.semantic-map.json")
            self.assertEqual(receipt["compiler_input_sha256"], artboard.file_sha256(project / "04-svg/artboard/page-001.semantic-map.json"))
            self.assertEqual(receipt["input_semantic_hash"], artboard.file_sha256(project / "04-svg/artboard/page-001.semantic-map.json"))
            self.assertEqual(receipt["svglide_svg_sha256"], artboard.file_sha256(project / "04-svg/page-001.svg"))
            self.assertEqual(receipt["compiler"]["semantic_source"], "CanvasSpec")
            self.assertEqual(receipt["compiler"]["compiler_input"], "SemanticMapIR")
            self.assertEqual(receipt["compiler"]["satori_svg_usage"], "preview_only")
            self.assertEqual(receipt["compiler"]["input_semantic_hash"], receipt["input_semantic_hash"])
            self.assertEqual(receipt["renderer"]["engine"], "satori-node")
            self.assertEqual(receipt["resvg_version"], "2.6.2")
            self.assertTrue(receipt["font_hashes"])
            semantic_map = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            self.assertEqual(semantic_map["semantic_source"], "CanvasSpec")
            self.assertTrue(semantic_map["elements"])
            title = next(item for item in semantic_map["elements"] if item["element_id"] == "title")
            self.assertEqual(title["source_ref"], "canvas_spec.content.title")
            self.assertEqual(title["bbox"]["width"], 628)
            self.assertIn('data-source-ref="canvas_spec.content.title"', svg)
            node_layout = json.loads((project / "04-svg/artboard/page-001.node-layout-map.json").read_text(encoding="utf-8"))
            self.assertEqual(node_layout["source"], "measured-layout-observation")
            self.assertIn(node_layout["observation_source"], {"satori_on_node_detected", "rendered_satori_svg_parse"})
            self.assertNotEqual(node_layout["drift"]["status"], "not_measured_in_p0")
            render_receipt = json.loads((project / "receipts/artboard-render.json").read_text(encoding="utf-8"))
            self.assertEqual(render_receipt["pages"][0]["render_metadata"], "04-svg/artboard/page-001.render-metadata.json")
            self.assertEqual(render_receipt["pages"][0]["render_metadata_sha256"], artboard.file_sha256(project / "04-svg/artboard/page-001.render-metadata.json"))
            self.assertEqual(render_receipt["pages"][0]["node_observations"], "04-svg/artboard/page-001.node-observations.json")
            bridge_receipt = json.loads((project / "receipts/satori-bridge.json").read_text(encoding="utf-8"))
            self.assertEqual(bridge_receipt["pages"][0]["compiler_input_type"], "SemanticMapIR")
            self.assertEqual(bridge_receipt["pages"][0]["satori_svg_usage"], "preview_only")
            self.assertEqual(bridge_receipt["pages"][0]["compiler_input"], "04-svg/artboard/page-001.semantic-map.json")
            self.assertEqual(bridge_receipt["pages"][0]["input_semantic_hash"], receipt["input_semantic_hash"])

    def test_render_project_uses_bounded_workers_and_stable_page_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            fixture_plan = json.loads(
                (Path(__file__).resolve().parent / "fixtures/svglide_artboard/p0b-three-page/02-plan/slide_plan.json").read_text(
                    encoding="utf-8"
                )
            )
            write_json(project / "02-plan/slide_plan.json", fixture_plan)

            result = artboard.render_project(project)

            self.assertEqual(result["max_workers"], 3)
            self.assertEqual(
                result["artboard_receipts"],
                [
                    "04-svg/artboard/page-001.receipt.json",
                    "04-svg/artboard/page-002.receipt.json",
                    "04-svg/artboard/page-003.receipt.json",
                ],
            )
            render_receipt = json.loads((project / "receipts/artboard-render.json").read_text(encoding="utf-8"))
            bridge_receipt = json.loads((project / "receipts/satori-bridge.json").read_text(encoding="utf-8"))
            self.assertEqual(render_receipt["summary"]["max_workers"], 3)
            self.assertEqual(bridge_receipt["summary"]["max_workers"], 3)
            self.assertEqual([page["page"] for page in render_receipt["pages"]], [1, 2, 3])
            self.assertEqual([page["page"] for page in bridge_receipt["pages"]], [1, 2, 3])

    def test_render_project_rejects_unsupported_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            spec = canvas_spec()
            spec["template_id"] = "freeform_html"
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": spec}]})

            with self.assertRaisesRegex(artboard.ArtboardError, "canvas_spec_template_unsupported"):
                artboard.render_project(project)

    def test_render_project_rejects_unknown_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            spec = canvas_spec()
            spec["theme_id"] = "unregistered-theme"
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": spec}]})

            with self.assertRaisesRegex(artboard.ArtboardError, "canvas_spec_theme_unknown"):
                artboard.render_project(project)

    def test_render_project_rejects_missing_required_content_and_card_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            spec = {
                "version": "svglide-canvas-spec/v1",
                "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
                "template_id": "comparison-cards",
                "theme_id": "forest-signal",
                "theme": {"colors": {"background": "#0B1F1A"}},
                "content": {
                    "title": "新旧链路差异",
                    "left_title": "旧链路",
                    "left_points": ["一", "二", "三", "四"],
                    "right_points": ["一"],
                },
            }
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": spec}]})

            with self.assertRaisesRegex(artboard.ArtboardError, "canvas_spec_template_required_content_missing"):
                artboard.render_project(project)

            try:
                artboard.render_project(project)
            except artboard.ArtboardError as error:
                self.assertIn("canvas_spec_template_too_many_items", str(error))

    def test_render_project_rejects_overlong_title_text_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            spec = canvas_spec()
            spec["content"]["title"] = "这是一段明显超过封面模板标题预算的超长标题，用来证明输入质量门禁会在渲染前阻断"
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": spec}]})

            with self.assertRaisesRegex(artboard.ArtboardError, "canvas_spec_text_budget_exceeded"):
                artboard.render_project(project)

    def test_render_project_rejects_semantic_bbox_outside_safe_area(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            spec = canvas_spec()
            spec["semantic_elements"][0]["bbox"] = {"x": 12, "y": 12, "width": 628, "height": 142}
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "canvas_spec": spec}]})

            with self.assertRaisesRegex(artboard.ArtboardError, "canvas_spec_bbox_out_of_safe_area"):
                artboard.render_project(project)

    def test_satori_bridge_fails_fast_on_filter(self) -> None:
        source = '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="10" height="10" filter="url(#x)"/></svg>'

        with self.assertRaisesRegex(artboard.ArtboardError, "satori_svg_effect_fail_fast"):
            artboard.compile_satori_svg_to_svglide(source)

    def test_satori_bridge_ignores_unreferenced_mask_definitions(self) -> None:
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<mask id="m"><rect x="0" y="0" width="10" height="10" fill="#fff"/></mask>'
            '<rect x="0" y="0" width="10" height="10" fill="#111"/>'
            '</svg>'
        )

        svg, compiler = artboard.compile_satori_svg_to_svglide(source)

        self.assertIn('slide:role="shape"', svg)
        self.assertIn("rect", compiler["native_mapped"])

    def test_satori_bridge_fails_fast_on_mask_usage(self) -> None:
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<mask id="m"><rect x="0" y="0" width="10" height="10" fill="#fff"/></mask>'
            '<rect x="0" y="0" width="10" height="10" fill="#111" mask="url(#m)"/>'
            '</svg>'
        )

        with self.assertRaisesRegex(artboard.ArtboardError, "satori_svg_effect_fail_fast"):
            artboard.compile_satori_svg_to_svglide(source)

    def test_satori_bridge_recursively_maps_nested_groups(self) -> None:
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g opacity="0.8"><g transform="translate(10 20)">'
            '<rect x="0" y="0" width="100" height="40" fill="#111"/>'
            '<text data-box-x="12" data-box-y="8" data-box-width="80" data-box-height="30" x="12" y="28" fill="#fff" font-size="18">Nested</text>'
            '</g></g>'
            '</svg>'
        )

        svg, compiler = artboard.compile_satori_svg_to_svglide(source)

        self.assertIn('slide:role="shape"', svg)
        self.assertIn('<g opacity="0.8">', svg)
        self.assertIn('transform="translate(10 20)"', svg)
        self.assertIn('slide:shape-type="text"', svg)
        self.assertEqual(compiler["semantic_source"], "SatoriSVG")
        self.assertEqual(compiler["compiler_input"], "RawSatoriSVG")
        self.assertEqual(compiler["satori_svg_usage"], "compiler_input")

    def test_align_text_boxes_merges_wrapped_satori_text_runs(self) -> None:
        svglide_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="104" y="295" width="420" height="45">'
            '<div xmlns="http://www.w3.org/1999/xhtml">先稳定 renderer 并推进 live/</div>'
            '</foreignObject>'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="104" y="325" width="120" height="45">'
            '<div xmlns="http://www.w3.org/1999/xhtml">readback。</div>'
            '</foreignObject>'
            '</svg>'
        )
        nodes = [{"id": "subtitle", "kind": "text", "x": 108, "y": 322, "width": 640, "height": 66}]

        aligned = artboard.align_text_boxes_to_node_layout(svglide_svg, nodes)

        self.assertEqual(aligned.count("<foreignObject"), 1)
        self.assertIn('data-node-id="subtitle"', aligned)
        self.assertIn('x="108"', aligned)
        self.assertIn("live/readback。", aligned)

    def test_align_text_boxes_keeps_short_labels_that_appear_in_subtitle(self) -> None:
        svglide_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="66" y="168" width="640" height="58">'
            '<div xmlns="http://www.w3.org/1999/xhtml">发射复用、Starlink、Starship 期权共同支撑估值。</div>'
            '</foreignObject>'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="138" y="286" width="146" height="30">'
            '<div xmlns="http://www.w3.org/1999/xhtml">发射复用</div>'
            '</foreignObject>'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="666" y="286" width="146" height="30">'
            '<div xmlns="http://www.w3.org/1999/xhtml">Starship期权</div>'
            '</foreignObject>'
            '</svg>'
        )
        nodes = [
            {"id": "subtitle", "kind": "text", "x": 66, "y": 168, "width": 640, "height": 58, "text": "发射复用、Starlink、Starship 期权共同支撑估值。"},
            {"id": "node-1", "kind": "text", "x": 138, "y": 286, "width": 146, "height": 30, "text": "发射复用"},
            {"id": "node-3", "kind": "text", "x": 666, "y": 286, "width": 146, "height": 30, "text": "Starship期权"},
        ]

        aligned = artboard.align_text_boxes_to_node_layout(svglide_svg, nodes)

        self.assertEqual(aligned.count("<foreignObject"), 3)
        self.assertIn('data-node-id="node-1"', aligned)
        self.assertIn('data-node-id="node-3"', aligned)
        self.assertIn(">发射复用<", aligned)
        self.assertIn(">Starship期权<", aligned)


if __name__ == "__main__":
    unittest.main()
