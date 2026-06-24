#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_artboard_renderer as artboard
import beautiful_template_runtime


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_legacy_fixture_registries(project: Path) -> None:
    write_json(project / "02-plan/theme-registry.json", beautiful_template_runtime.theme_registry(include_legacy=True))
    write_json(project / "02-plan/template-registry.json", beautiful_template_runtime.template_registry(include_legacy=True))


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
    def test_production_beautiful_renderer_missing_dedicated_module_fails_closed(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        renderer_dir = scripts_dir / "artboard_renderer"
        sample_template_id = "executive-dashboard"
        script = """
import { renderTree } from './templates/p0-templates.mjs'
import { beautifulRendererContract, dedicatedBeautifulRendererIds } from './templates/beautiful/index.mjs'

const sampleTemplateId = process.argv[1]
const registeredIds = dedicatedBeautifulRendererIds()
if (!registeredIds.includes(sampleTemplateId)) {
  console.error(JSON.stringify({ missingSample: sampleTemplateId, registeredIds }))
  process.exit(1)
}
const contract = beautifulRendererContract(sampleTemplateId)
if (contract?.status !== 'production' || contract?.renderer_stage !== 'closed_loop_sample') {
  console.error(JSON.stringify({ badContract: contract }))
  process.exit(2)
}

try {
  renderTree({
    template_id: '__missing_production_beautiful_template__',
    template_status: 'production',
    selection_scope: 'production',
    theme: { colors: { background: '#fff', panel: '#f8fafc', primary: '#111', accent: '#555', text: '#111', muted: '#555' } },
    content: { title: 'Missing renderer should fail' }
  })
} catch (error) {
  const message = String(error?.message || error)
  if (message.includes('missing dedicated beautiful renderer')) {
    console.log(JSON.stringify({ registeredIds, message }))
    process.exit(0)
  }
  console.error(message)
  process.exit(3)
}
console.error('production beautiful template rendered without a dedicated renderer')
process.exit(4)
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script, sample_template_id],
            cwd=renderer_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_renderer_font_manifest_registers_required_roles(self) -> None:
        renderer_dir = Path(__file__).resolve().parent / "artboard_renderer"
        manifest = json.loads((renderer_dir / "font-manifest.json").read_text(encoding="utf-8"))
        roles = manifest.get("roles")
        self.assertIsInstance(roles, dict)
        required_roles = {"display", "body", "label", "metric"}
        self.assertTrue(required_roles.issubset(roles))
        families = {roles[role]["family"] for role in required_roles}
        self.assertGreaterEqual(len(families), 2)
        for role in required_roles:
            record = roles[role]
            self.assertIsInstance(record.get("family"), str)
            self.assertIsInstance(record.get("weight"), int)
            self.assertTrue(record.get("candidates"))
        typography = (renderer_dir / "components/typography.mjs").read_text(encoding="utf-8")
        for helper in ["fontRole", "withFontRole", "fontRolesFromTheme"]:
            self.assertIn(f"export function {helper}", typography)

    def test_theme_font_roles_are_reflected_in_renderer_metadata(self) -> None:
        renderer_dir = Path(__file__).resolve().parent / "artboard_renderer"
        spec = canvas_spec()
        spec["template_id"] = "executive-dashboard"
        spec["theme_id"] = "blue-professional"
        spec["theme"] = {
            "colors": {
                "background": "#101018",
                "panel": "#171727",
                "surface": "#202036",
                "primary": "#7DF9FF",
                "accent": "#F8E16C",
                "text": "#F8FAFC",
                "muted": "#B7C4D8",
            },
            "typography": {
                "font_roles": {
                    "display": "SVGlideDisplayOverride",
                    "body": "SVGlideBodyOverride",
                    "label": "SVGlideLabelOverride",
                    "metric": "SVGlideMetricOverride",
                }
            },
        }
        spec["content"] = {
            "eyebrow": "FONT ROLES",
            "title": "Renderer roles",
            "subtitle": "Theme role aliases must be auditable.",
            "stats": ["Display", "Body", "Label", "Metric"],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "canvas-spec.json"
            output_path = tmp / "out.svg"
            png_path = tmp / "out.png"
            metadata_path = tmp / "metadata.json"
            observations_path = tmp / "observations.json"
            write_json(input_path, spec)
            result = subprocess.run(
                [
                    "node",
                    (renderer_dir / "render.mjs").as_posix(),
                    input_path.as_posix(),
                    output_path.as_posix(),
                    png_path.as_posix(),
                    metadata_path.as_posix(),
                    observations_path.as_posix(),
                ],
                cwd=renderer_dir,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            font_receipt = metadata.get("font_receipt")
            self.assertIsInstance(font_receipt, dict)
            requested_roles = font_receipt.get("requested_roles")
            self.assertEqual(requested_roles["display"], "SVGlideDisplayOverride")
            resolved_roles = font_receipt.get("resolved_roles")
            self.assertEqual(set(resolved_roles), {"display", "body", "label", "metric"})
            self.assertEqual(resolved_roles["display"]["family"], "SVGlideDisplayOverride")
            self.assertGreaterEqual(len({resolved_roles[role]["family"] for role in resolved_roles}), 2)

    def test_compiler_nodes_do_not_synthesize_template_eyebrow(self) -> None:
        spec = canvas_spec()
        spec["template_id"] = "comparison-cards"
        content = dict(spec["content"])
        content.pop("eyebrow", None)
        spec["content"] = content

        nodes = artboard.compiler_nodes_from_canvas_spec(spec)

        text_by_id = {str(node.get("id")): str(node.get("text") or "") for node in nodes if node.get("kind") == "text"}
        self.assertNotIn("eyebrow", text_by_id)
        self.assertNotIn("COMPARISON CARDS", "".join(text_by_id.values()))

    def test_semantic_elements_attach_origin_for_decorative_nodes(self) -> None:
        elements = artboard.semantic_elements_from_nodes(
            [
                {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
                {"id": "agenda-rail", "kind": "line", "x": 100, "y": 100, "width": 1, "height": 200},
                {"id": "title", "kind": "text", "x": 64, "y": 80, "width": 400, "height": 80, "text": "Title"},
            ],
            {"template_id": "agenda-list", "theme_id": "cobalt-grid"},
        )

        by_id = {item["element_id"]: item for item in elements}
        self.assertEqual(by_id["background"]["origin"]["type"], "theme")
        self.assertEqual(by_id["agenda-rail"]["element_type"], "decorative_line")
        self.assertEqual(by_id["agenda-rail"]["origin"]["type"], "template")
        self.assertNotIn("origin", by_id["title"])
        summary = artboard.decorative_trace_summary(elements)
        self.assertEqual(summary["missing_origin_count"], 0)

    def test_p0_theme_registry_components_and_fixtures_are_registered(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        renderer_dir = scripts_dir / "artboard_renderer"
        theme_registry = beautiful_template_runtime.theme_registry(include_legacy=True)
        theme_ids = [item["id"] for item in theme_registry["themes"]]
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
            self.assertTrue({"background", "surface", "panel", "primary", "accent", "text", "muted"}.issubset(record["colors"]))

        template_registry = beautiful_template_runtime.template_registry(include_legacy=True)
        active_templates = {
            item["id"]: item
            for item in template_registry["templates"]
            if beautiful_template_runtime.is_runtime_selectable(item, include_legacy_debug=True)
        }
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
            supported_theme_ids = set(template["supported_theme_ids"])
            if template.get("selection_scope") == "production":
                self.assertTrue(supported_theme_ids)
                self.assertTrue(supported_theme_ids.issubset(set(theme_ids)))
            else:
                self.assertTrue(set(theme_ids).issubset(supported_theme_ids))

        components = (renderer_dir / "components/primitives.mjs").read_text(encoding="utf-8")
        for export_name in ["Title", "Subtitle", "Chip", "StatCard", "ImageFrame"]:
            self.assertIn(f"export function {export_name}", components)

        component_registry = beautiful_template_runtime.component_registry()
        active_components = [item for item in component_registry["components"] if isinstance(item, dict)]
        self.assertGreaterEqual(len(active_components), 15)
        layout_registry = json.loads((scripts_dir.parent / "references/svglide-layout-archetypes.json").read_text(encoding="utf-8"))
        layout_records = [item for item in layout_registry["archetypes"] if isinstance(item, dict)]
        legacy_layouts = [item for item in layout_records if item.get("status") == "legacy_debug"]
        self.assertGreaterEqual(len(layout_records), 8)
        self.assertTrue(legacy_layouts)
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
            with tempfile.TemporaryDirectory() as tmpdir:
                project = Path(tmpdir)
                write_legacy_fixture_registries(project)
                registry_issues, _ = artboard.validate_registry_bindings(project, golden, page=1)
            self.assertEqual([], issues + registry_issues)

    def test_p1_active_template_golden_fixtures_render(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        golden_dir = scripts_dir / "fixtures/svglide_artboard/golden"
        template_registry = beautiful_template_runtime.template_registry(include_legacy=True)
        active_template_ids = sorted(item["id"] for item in template_registry["templates"] if beautiful_template_runtime.is_runtime_selectable(item))
        slides = []
        for page, template_id in enumerate(active_template_ids, 1):
            golden = json.loads((golden_dir / f"{template_id}.canvas-spec.json").read_text(encoding="utf-8"))
            slides.append({"page": page, "title": golden["content"]["title"], "canvas_spec": golden})
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": slides})

            result = artboard.render_project(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["max_workers"], min(4, len(active_template_ids)))
            self.assertEqual(len(result["artboard_receipts"]), len(active_template_ids))
            self.assertTrue((project / "05-preview/contact-sheet.png").exists())
            self.assertTrue((project / "04-artboard/raw/manifest.json").exists())
            self.assertTrue((project / "04-svg/contract/manifest.json").exists())
            for page in range(1, len(active_template_ids) + 1):
                self.assertTrue((project / f"04-artboard/raw/page-{page:03d}.visual.png").exists())
                self.assertTrue((project / f"04-artboard/raw/page-{page:03d}.visual.svg").exists())
                self.assertTrue((project / f"04-svg/page-{page:03d}.svg").exists())
                semantic_map = json.loads((project / f"04-artboard/raw/page-{page:03d}.semantic-map.json").read_text(encoding="utf-8"))
                self.assertEqual(semantic_map["extraction_strategy"], "canvas_spec_compiler_nodes_with_satori_preview")
                self.assertLessEqual(len(semantic_map["elements"]), 18)

    def test_p1_template_uses_real_satori_source_not_python_generic(self) -> None:
        spec = canvas_spec()
        spec["template_id"] = "executive-dashboard"
        spec["theme_id"] = "blue-professional"
        spec["theme"] = {
            "colors": {
                "background": "#FDFAE7",
                "panel": "#FFFFFF",
                "surface": "#F5F7FF",
                "primary": "#1E2BFA",
                "accent": "#1E2BFA",
                "text": "#111111",
                "muted": "#6B6B6B",
                "border": "#D4D8FE",
            }
        }
        spec["content"] = {
            "eyebrow": "BUSINESS REVIEW",
            "title": "智谱和 MiniMax",
            "subtitle": "用户预览链路不应注入无来源参考线。",
            "metrics": ["主题非 baseline", "模板非 baseline", "本地预览", "无旧装饰"],
            "actions": ["确认来源", "跑通预览", "检查质量门"],
        }

        with self.assertRaisesRegex(artboard.ArtboardError, "Python generic fallback is not allowed"):
            artboard.render_satori_compatible_svg(spec)

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": [{"page": 1, "canvas_spec": spec}]})

            result = artboard.render_project(project)

            self.assertEqual(result["status"], "passed")
            raw_satori = (project / "04-artboard/raw/page-001.visual.svg").read_text(encoding="utf-8")
            for token in [
                "template_p1_generic",
                "reference-flow-path",
                "reference-annotation-line",
                "dashboard-metric-bar",
                "accent-panel",
            ]:
                self.assertNotIn(token, raw_satori)
            self.assertNotIn("slide:role", raw_satori)
            receipt = json.loads((project / "04-artboard/raw/page-001.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["compiler"]["semantic_source"], "SatoriSVG")
            self.assertEqual(receipt["compiler"]["compiler_input"], "RawSatoriSVG")
            self.assertEqual(receipt["compiler"]["satori_svg_usage"], "compiler_input")
            self.assertEqual(receipt["compiler_input"], "04-artboard/raw/page-001.visual.svg")
            self.assertEqual(receipt["input_semantic_hash"], receipt["satori_svg_sha256"])
            self.assertEqual(receipt["canvas_template_svg_sha256"], receipt["satori_svg_sha256"])
            bridge_receipt = json.loads((project / "receipts/satori-bridge.json").read_text(encoding="utf-8"))
            self.assertEqual(bridge_receipt["pages"][0]["semantic_source"], "SatoriSVG")
            self.assertEqual(bridge_receipt["pages"][0]["compiler_input_type"], "RawSatoriSVG")
            self.assertEqual(bridge_receipt["pages"][0]["satori_svg_usage"], "compiler_input")

    def test_p1_template_fails_closed_when_node_satori_is_disabled(self) -> None:
        spec = canvas_spec()
        spec["template_id"] = "executive-dashboard"
        spec["theme_id"] = "blue-professional"
        spec["content"] = {"title": "No Python Generic", "subtitle": "P1 must not fall back", "metrics": ["A", "B", "C", "D"]}
        old_value = os.environ.get("SVGLIDE_ARTBOARD_USE_NODE_SATORI")
        os.environ["SVGLIDE_ARTBOARD_USE_NODE_SATORI"] = "0"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                project = Path(tmpdir)
                write_legacy_fixture_registries(project)
                write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": [{"page": 1, "canvas_spec": spec}]})

                with self.assertRaisesRegex(artboard.ArtboardError, "Python generic fallback is not allowed"):
                    artboard.render_project(project)
        finally:
            if old_value is None:
                os.environ.pop("SVGLIDE_ARTBOARD_USE_NODE_SATORI", None)
            else:
                os.environ["SVGLIDE_ARTBOARD_USE_NODE_SATORI"] = old_value

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
            write_legacy_fixture_registries(project)
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
            self.assertEqual(result["artboard_receipts"], ["04-artboard/raw/page-001.receipt.json"])
            self.assertEqual(
                result["additional_receipts"],
                [
                    "receipts/canvas-spec-validate.json",
                    "receipts/artboard-render.json",
                    "receipts/satori-bridge.json",
                ],
            )
            self.assertEqual(result["contact_sheet"]["path"], "05-preview/contact-sheet.png")
            self.assertTrue((project / "04-artboard/raw/page-001.visual.png").exists())
            self.assertTrue((project / "04-artboard/raw/page-001.render-metadata.json").exists())
            self.assertTrue((project / "04-artboard/raw/page-001.canvas-template.svg").exists())
            self.assertTrue((project / "04-artboard/raw/manifest.json").exists())
            self.assertTrue((project / "05-preview/contact-sheet.png").exists())
            visual_svg = (project / "04-artboard/raw/page-001.visual.svg").read_text(encoding="utf-8")
            self.assertNotIn('xmlns:slide="https://slides.bytedance.com/ns"', visual_svg)
            self.assertNotIn('slide:role="slide"', visual_svg)
            self.assertNotIn('slide:shape-type="text"', visual_svg)
            self.assertTrue((project / "04-svg/page-001.svg").exists())
            self.assertTrue((project / "04-svg/contract/manifest.json").exists())
            canonical_svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")
            self.assertIn('slide:role="slide"', canonical_svg)
            self.assertIn('slide:shape-type="text"', canonical_svg)
            receipt = json.loads((project / "04-artboard/raw/page-001.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["version"], "svglide-artboard-receipt/v1")
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["template_id"], "cover-hero")
            self.assertEqual(receipt["theme_id"], "dark-clarity")
            self.assertEqual(receipt["png_sha256"], artboard.file_sha256(project / "04-artboard/raw/page-001.visual.png"))
            self.assertEqual(receipt["render_metadata_sha256"], artboard.file_sha256(project / "04-artboard/raw/page-001.render-metadata.json"))
            self.assertEqual(receipt["canvas_template_svg"], "04-artboard/raw/page-001.canvas-template.svg")
            self.assertEqual(receipt["canvas_template_svg_sha256"], artboard.file_sha256(project / "04-artboard/raw/page-001.canvas-template.svg"))
            self.assertEqual(receipt["canvas_template_svg_sha256"], receipt["satori_svg_sha256"])
            self.assertEqual(receipt["compiler_input"], "04-artboard/raw/page-001.visual.svg")
            self.assertEqual(receipt["compiler_input_sha256"], artboard.file_sha256(project / "04-artboard/raw/page-001.visual.svg"))
            self.assertEqual(receipt["input_semantic_hash"], artboard.file_sha256(project / "04-artboard/raw/page-001.visual.svg"))
            self.assertEqual(receipt["compiler"]["semantic_source"], "SatoriSVG")
            self.assertEqual(receipt["compiler"]["compiler_input"], "RawSatoriSVG")
            self.assertEqual(receipt["compiler"]["satori_svg_usage"], "compiler_input")
            self.assertEqual(receipt["compiler"]["input_semantic_hash"], receipt["input_semantic_hash"])
            self.assertEqual(receipt["renderer"]["engine"], "satori-node")
            self.assertEqual(receipt["resvg_version"], "2.6.2")
            self.assertTrue(receipt["font_hashes"])
            semantic_map = json.loads((project / "04-artboard/raw/page-001.semantic-map.json").read_text(encoding="utf-8"))
            self.assertEqual(semantic_map["semantic_source"], "SatoriSVG")
            self.assertEqual(semantic_map["extraction_strategy"], "canvas_spec_compiler_nodes_with_satori_preview")
            self.assertTrue(semantic_map["elements"])
            self.assertLessEqual(len(semantic_map["elements"]), 18)
            observed_text = "".join(str(item.get("text") or "") for item in semantic_map["elements"])
            self.assertIn("受控画板生成", observed_text)
            node_layout = json.loads((project / "04-artboard/raw/page-001.node-layout-map.json").read_text(encoding="utf-8"))
            self.assertEqual(node_layout["source"], "measured-layout-observation")
            self.assertEqual(node_layout["observation_source"], "rendered_satori_svg_parse")
            self.assertEqual(node_layout["drift"]["status"], "passed")
            self.assertEqual(node_layout["drift"]["missing_count"], 0)
            render_receipt = json.loads((project / "receipts/artboard-render.json").read_text(encoding="utf-8"))
            self.assertEqual(render_receipt["pages"][0]["render_metadata"], "04-artboard/raw/page-001.render-metadata.json")
            self.assertEqual(render_receipt["pages"][0]["render_metadata_sha256"], artboard.file_sha256(project / "04-artboard/raw/page-001.render-metadata.json"))
            self.assertEqual(render_receipt["pages"][0]["node_observations"], "04-artboard/raw/page-001.node-observations.json")
            bridge_receipt = json.loads((project / "receipts/satori-bridge.json").read_text(encoding="utf-8"))
            self.assertEqual(bridge_receipt["pages"][0]["semantic_source"], "SatoriSVG")
            self.assertEqual(bridge_receipt["pages"][0]["compiler_input_type"], "RawSatoriSVG")
            self.assertEqual(bridge_receipt["pages"][0]["satori_svg_usage"], "compiler_input")
            self.assertEqual(bridge_receipt["pages"][0]["compiler_input"], "04-artboard/raw/page-001.visual.svg")
            self.assertEqual(bridge_receipt["pages"][0]["input_semantic_hash"], receipt["input_semantic_hash"])

    def test_render_project_uses_bounded_workers_and_stable_page_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            fixture_plan = json.loads(
                (Path(__file__).resolve().parent / "fixtures/svglide_artboard/p0b-three-page/02-plan/slide_plan.json").read_text(
                    encoding="utf-8"
                )
            )
            write_legacy_fixture_registries(project)
            write_json(project / "02-plan/slide_plan.json", fixture_plan)

            result = artboard.render_project(project)

            self.assertEqual(result["max_workers"], 3)
            self.assertEqual(
                result["artboard_receipts"],
                [
                    "04-artboard/raw/page-001.receipt.json",
                    "04-artboard/raw/page-002.receipt.json",
                    "04-artboard/raw/page-003.receipt.json",
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

    def write_page_family_registry(self, project: Path, *, visual_contract_path: str | None = None) -> None:
        template = next(
            item
            for item in beautiful_template_runtime.template_registry()["templates"]
            if item.get("id") == "executive-dashboard"
        )
        template = dict(template)
        template["source_family"] = "blue-professional"
        template["family_id"] = "blue-professional"
        template["visual_contract"] = {"path": visual_contract_path or "missing-contract.json"}
        template["visual_contract_path"] = visual_contract_path or "missing-contract.json"
        for key in ("implemented_page_variants", "supported_page_variants", "page_family", "page_variants"):
            template.pop(key, None)
        theme = next(
            item
            for item in beautiful_template_runtime.theme_registry()["themes"]
            if item.get("id") == "blue-professional"
        )
        write_json(project / "02-plan/template-registry.json", {"templates": [template]})
        write_json(project / "02-plan/theme-registry.json", {"themes": [theme]})
        write_json(
            project / "02-plan/theme-template-selection.json",
            {
                "selected_family_id": "blue-professional",
                "selected_template_id": "executive-dashboard",
                "selected_page_family": {
                    "family_id": "blue-professional",
                    "runtime_template_id": "executive-dashboard",
                    "supported_page_variants": ["cover", "metrics"],
                    "variant_usage_policy": {"singletons": ["cover"], "repeatable": ["metrics"]},
                },
            },
        )

    def page_family_spec(self) -> dict[str, object]:
        spec = canvas_spec()
        spec["template_id"] = "executive-dashboard"
        spec["theme_id"] = "blue-professional"
        spec["family_id"] = "blue-professional"
        spec["page_role"] = "cover"
        spec["theme"] = {
            "colors": {
                "background": "#FDFAE7",
                "panel": "#FFFFFF",
                "surface": "#F5F7FF",
                "primary": "#1E2BFA",
                "accent": "#1E2BFA",
                "text": "#111111",
                "muted": "#6B6B6B",
            }
        }
        spec["content"] = {"title": "Family Cover", "subtitle": "Variant validation", "metrics": ["A", "B"]}
        return spec

    def test_registry_binding_requires_page_variant_from_full_visual_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            contract_rel = "contracts/blue-professional.json"
            write_json(
                project / contract_rel,
                {
                    "family_id": "blue-professional",
                    "runtime_template_id": "executive-dashboard",
                    "page_variants": {
                        "cover": {"page_roles": ["cover"]},
                        "metrics": {"page_roles": ["content"]},
                    },
                },
            )
            self.write_page_family_registry(project, visual_contract_path=contract_rel)
            spec = self.page_family_spec()

            issues, binding = artboard.validate_registry_bindings(project, spec, page=1)

            self.assertIn("canvas_spec_page_variant_missing", {item["code"] for item in issues})
            self.assertEqual(["cover", "metrics"], binding["page_variant_binding"]["supported_page_variants"])
            self.assertEqual(contract_rel, binding["page_variant_binding"]["visual_contract_path"])

    def test_registry_binding_rejects_unknown_variant_and_family_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            contract_rel = "contracts/blue-professional.json"
            write_json(
                project / contract_rel,
                {
                    "family_id": "blue-professional",
                    "runtime_template_id": "executive-dashboard",
                    "page_variants": {"cover": {"page_roles": ["cover"]}},
                },
            )
            self.write_page_family_registry(project, visual_contract_path=contract_rel)
            spec = self.page_family_spec()
            spec["family_id"] = "wrong-family"
            spec["page_variant_id"] = "unknown"

            issues, _ = artboard.validate_registry_bindings(project, spec, page=1)

            codes = {item["code"] for item in issues}
            self.assertIn("canvas_spec_page_variant_unsupported", codes)
            self.assertIn("canvas_spec_family_template_mismatch", codes)

    def test_render_project_rejects_missing_required_content_and_card_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_legacy_fixture_registries(project)
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
            write_legacy_fixture_registries(project)
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

    def test_repair_foreign_object_layout_expands_two_digit_number_boxes(self) -> None:
        svglide_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">'
            '<foreignObject slide:role="shape" slide:shape-type="text" x="72" y="314.3" width="25.8" height="40">'
            '<div xmlns="http://www.w3.org/1999/xhtml" style="font-size:23px;line-height:1">01</div>'
            '</foreignObject>'
            '</svg>'
        )

        repaired = artboard.repair_foreign_object_layout(svglide_svg)
        root = artboard.ElementTree.fromstring(repaired)
        box = next(element for element in root.iter() if artboard.local_name(element.tag) == "foreignObject")

        self.assertGreaterEqual(float(box.attrib["width"]), 35.7)
        self.assertGreaterEqual(float(box.attrib["height"]), 57.5)


if __name__ == "__main__":
    unittest.main()
