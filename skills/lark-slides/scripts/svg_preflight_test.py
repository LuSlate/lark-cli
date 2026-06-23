# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svg_preflight


VALID_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     slide:contract-version="svglide-authoring-contract/v1"
     width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
  <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
    <div xmlns="http://www.w3.org/1999/xhtml"
         style="font-size:32px;font-weight:800;font-family:Arial;color:#111827;line-height:1.15;text-align:left;">
      Strategy review
    </div>
  </foreignObject>
  <image id="hero" slide:role="image" href="@./assets/hero.jpg" x="560" y="96" width="320" height="220" />
  <path id="trend" slide:role="shape" d="M64 360 L180 330 C260 300 340 340 420 300 Q500 260 580 290" fill="none" stroke="#2563eb" />
</svg>
"""


def with_contract(svg: str) -> str:
    if "slide:contract-version=" in svg:
        return svg
    return svg.replace(
        'slide:role="slide"',
        f'slide:role="slide"\n             slide:contract-version="{svg_preflight.SVG_CONTRACT_VERSION}"',
        1,
    )


def style_plan_fields(template_id: str = "raw-grid") -> dict[str, object]:
    return {
        "deck_recipe_selection": {
            "recipe_id": "technical_architecture_review",
            "match_level": "L1",
            "confidence": 0.88,
            "signals": {"keywords": ["技术", "架构"]},
            "missing_signals": [],
        },
        "template_family_selection": {
            "enabled": True,
            "source": "beautiful-html-template-families",
            "selected_template_id": template_id,
            "candidate_template_ids": [template_id, "blue-professional", "signal"],
            "selection_reason": f"{template_id} fits technical training pages that need dense but readable visual structure",
        },
        "style_pack_selection": {
            "selected_style_pack_id": "architecture_mono_cyan",
            "candidate_style_pack_ids": ["architecture_mono_cyan", "corporate_blue_data"],
            "selection_reason": "technical architecture requires diagram-first, controlled mono/cyan system",
            "palette_id": "mono_cyan",
            "typography_id": "system_sans_technical",
            "background_system_id": "diagram_grid",
            "chart_palette_id": "technical_chart",
            "image_treatment_id": "diagram_first",
            "decoration_policy_id": "minimal_grid_only",
            "component_variant_bias": ["architecture_diagram", "dependency_map"],
        },
        "density_mode_selection": {
            "selected_density_mode": "diagram-heavy",
            "candidate_density_modes": ["diagram-heavy", "data-heavy"],
            "selection_reason": "architecture decks need diagram-heavy density",
        },
        "component_variant_selection": {
            "selected_component_variants": ["architecture_diagram", "dependency_map"],
            "candidate_component_variants": ["architecture_diagram", "dependency_map", "risk_matrix"],
            "selection_reason": "selected from recipe component slots",
        },
        "image_treatment_selection": {
            "selected_image_treatment_id": "diagram_first",
            "candidate_image_treatment_ids": ["diagram_first", "chart_first"],
            "selection_reason": "architecture plan should use diagrams before photos",
        },
        "style_lock": {
            "template_family_id": template_id,
            "style_pack_id": "architecture_mono_cyan",
            "palette_id": "mono_cyan",
            "typography_id": "system_sans_technical",
            "background_system_id": "diagram_grid",
            "chart_palette_id": "technical_chart",
            "image_treatment_id": "diagram_first",
            "decoration_policy_id": "minimal_grid_only",
            "component_variant_bias": ["architecture_diagram", "dependency_map"],
            "deck_level": True,
        },
        "loaded_rule_set": sorted(svg_preflight.SVG_PRIVATE_REQUIRED_RULE_FILES),
        "plan_path": ".lark-slides/plan/test/slide_plan.json",
        "quality_gates": {
            "no_text_overflow": True,
            "no_debug_guides": True,
            "no_xml_like_pages": True,
        },
        "art_direction": {
            "cover_treatment": "hero_typography with one dominant title and SVG geometric carrier",
            "section_divider_treatment": "large chapter number and sparse claim when section pages exist",
            "closing_treatment": "brand_system or metaphor_loop that mirrors the cover motif",
            "deck_motif": "grid panels with restrained accent labels",
            "svg_native_moments": [
                "cover hero geometry",
                "data micro chart",
                "closing motif mirror",
            ],
        },
    }


def effects_for_primitives(primitives: list[str]) -> list[str]:
    effects = {"typography"}
    primitive_set = set(primitives)
    if "path" in primitive_set or "annotation" in primitive_set:
        effects.add("path")
        effects.add("connector_flow")
    if "micro_chart" in primitive_set or "dashboard" in primitive_set:
        effects.add("chart_geometry")
    if "gradient" in primitive_set:
        effects.add("gradient")
    if "texture" in primitive_set:
        effects.add("texture")
    if "image_overlay" in primitive_set:
        effects.add("image_overlay")
    if "spotlight" in primitive_set:
        effects.add("spotlight")
    return sorted(effects)


def template_slide_fields(variant: str = "path_flow") -> dict[str, object]:
    return {
        "template_variant": variant,
        "semantic_blocks": [
            {"block_id": "title", "type": "title", "content": "Unit test title"},
            {"block_id": "message", "type": "finding", "content": f"Use {variant}"},
        ],
        "component_selection": [
            {"component_id": "title_block", "binds": ["title"]},
            {"component_id": "finding_callout", "binds": ["message"]},
        ],
        "asset_strategy": {"strategy_id": "structured_fallback", "expected_asset_count": 0},
    }


def recipe_fields(recipe: str, primitives: list[str]) -> dict[str, object]:
    return {
        "layout_family": recipe,
        "visual_recipe": recipe,
        "visual_intent": f"use {recipe} as the SVG-native visual carrier",
        "visual_focal_point": "main visual structure",
        "visual_signature": f"{recipe} creates a distinct SVG visual memory point",
        "svg_effects": effects_for_primitives(primitives),
        "required_primitives": primitives,
        "svg_primitives": primitives,
        "xml_like_risk": "would fall back to generic cards and bullets in XML",
        "content_density_contract": "dashboard >= 4 metrics",
        "asset_contract": "none_required",
        "risk_flags": [],
        "source_policy": "Use prompt-provided content only; mark missing numbers as pending.",
        **template_slide_fields(recipe),
    }


def chart_spec(chart_type: str = "bar") -> str:
    return (
        '{"version":"svglide-chart-spec/v1",'
        f'"chartType":"{chart_type}",'
        '"data":{"categories":["Q1","Q2"],"series":[{"name":"Revenue","values":[12.5,18]}]}}'
    )


def chart_metadata(chart_json: str, payload_hash: str | None = None, data_format: str = "svglide-chart-spec-v1", data_encoding: str = "base64url-json") -> str:
    payload = base64.urlsafe_b64encode(chart_json.encode("utf-8")).decode("ascii").rstrip("=")
    if payload_hash is None:
        payload_hash = "sha256:" + hashlib.sha256(chart_json.encode("utf-8")).hexdigest()
    return (
        '<metadata data-svglide-chart="svglide-chart-inline/v1" '
        f'data-format="{data_format}" data-encoding="{data_encoding}" '
        f'data-payload-hash="{payload_hash}">{payload}</metadata>'
    )


def chart_marker(metadata: str) -> str:
    return f'<g slide:role="chart" slide:chart-ref="chart-1" x="80" y="96" width="420" height="260">{metadata}</g>'


class SvgPreflightTest(unittest.TestCase):
    def test_lint_svg_accepts_valid_svglide(self) -> None:
        result = svg_preflight.lint_svg(VALID_SVG)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_svg_reports_canvas_mismatch(self) -> None:
        result = svg_preflight.lint_svg(
            VALID_SVG.replace('width="960" height="540" viewBox="0 0 960 540"', 'width="1280" height="720" viewBox="0 0 1280 720"')
        )
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertIn("root_canvas_mismatch", codes)
        self.assertIn("root_viewbox_mismatch", codes)
        self.assertEqual(result["summary"]["error_count"], 2)

    def test_lint_svg_reports_missing_contract_version(self) -> None:
        svg = VALID_SVG.replace('     slide:contract-version="svglide-authoring-contract/v1"\n', "")
        result = svg_preflight.lint_svg(svg)
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertIn("root_contract_version_missing", codes)
        self.assertEqual(result["summary"]["error_count"], 1)

    def test_lint_svg_reports_contract_version_mismatch(self) -> None:
        svg = VALID_SVG.replace(
            'slide:contract-version="svglide-authoring-contract/v1"',
            'slide:contract-version="legacy"',
        )
        result = svg_preflight.lint_svg(svg)
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertIn("root_contract_version_mismatch", codes)
        self.assertEqual(result["summary"]["error_count"], 1)

    def test_parse_args_accepts_contract_manifest(self) -> None:
        options = svg_preflight.parse_args(["--input", "page.svg", "--contract-manifest", "manifest.json"])

        self.assertEqual(options["inputs"], ["page.svg"])
        self.assertEqual(options["contract_manifest"], "manifest.json")

    def test_contract_manifest_does_not_replace_missing_slide_role_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            svg_path = project / "04-svg/page-001.svg"
            manifest_path = project / "04-svg/contract/manifest.json"
            svg_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>', encoding="utf-8")
            digest = svg_preflight.file_sha256(svg_path)
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "svglide-contract-compile-manifest/v1",
                        "stage": "contract_compile",
                        "status": "passed",
                        "pages": [
                            {
                                "page": 1,
                                "source": "04-artboard/raw/page-001.visual.svg",
                                "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                                "output": "04-svg/page-001.svg",
                                "report": "04-svg/contract/page-001.report.json",
                                "status": "passed",
                                "input_sha256": "raw",
                                "semantic_map_sha256": "semantic",
                                "output_sha256": digest,
                            }
                        ],
                        "summary": {"pages": 1, "blocking_issues": 0, "degraded_elements": 0, "rasterized_regions": 0, "dropped_decorations": 0},
                    }
                ),
                encoding="utf-8",
            )

            result = svg_preflight.lint_files([svg_path.as_posix()], contract_manifest_path=manifest_path.as_posix())

            codes = [issue["code"] for issue in result["files"][0]["issues"]]
            self.assertIn("missing_root_role", codes)
            self.assertEqual(result["contract_compile"]["summary"]["error_count"], 0)

    def test_contract_manifest_hash_mismatch_blocks_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            svg_path = project / "04-svg/page-001.svg"
            manifest_path = project / "04-svg/contract/manifest.json"
            svg_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "svglide-contract-compile-manifest/v1",
                        "stage": "contract_compile",
                        "status": "passed",
                        "pages": [
                            {
                                "page": 1,
                                "source": "04-artboard/raw/page-001.visual.svg",
                                "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                                "output": "04-svg/page-001.svg",
                                "report": "04-svg/contract/page-001.report.json",
                                "status": "passed",
                                "input_sha256": "raw",
                                "semantic_map_sha256": "semantic",
                                "output_sha256": "stale",
                            }
                        ],
                        "summary": {"pages": 1, "blocking_issues": 0, "degraded_elements": 0, "rasterized_regions": 0, "dropped_decorations": 0},
                    }
                ),
                encoding="utf-8",
            )

            result = svg_preflight.lint_files([svg_path.as_posix()], contract_manifest_path=manifest_path.as_posix())

            self.assertEqual(result["contract_compile"]["summary"]["error_count"], 1)
            self.assertEqual(result["contract_compile"]["issues"][0]["code"], "contract_output_hash_mismatch")

    def test_contract_manifest_prepared_hash_mismatch_blocks_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            compiled_path = project / "04-svg/page-001.svg"
            prepared_path = project / "04-svg/prepared/page-001.svg"
            manifest_path = project / "04-svg/contract/manifest.json"
            prepared_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True)
            compiled_path.write_text(VALID_SVG, encoding="utf-8")
            prepared_path.write_text(VALID_SVG.replace("#f8fafc", "#f1f5f9"), encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "version": "svglide-contract-compile-manifest/v1",
                        "stage": "contract_compile",
                        "status": "passed",
                        "pages": [
                            {
                                "page": 1,
                                "source": "04-artboard/raw/page-001.visual.svg",
                                "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                                "output": "04-svg/page-001.svg",
                                "report": "04-svg/contract/page-001.report.json",
                                "status": "passed",
                                "input_sha256": "raw",
                                "semantic_map_sha256": "semantic",
                                "output_sha256": svg_preflight.file_sha256(compiled_path),
                            }
                        ],
                        "summary": {"pages": 1, "blocking_issues": 0, "degraded_elements": 0, "rasterized_regions": 0, "dropped_decorations": 0},
                    }
                ),
                encoding="utf-8",
            )

            result = svg_preflight.lint_files([prepared_path.as_posix()], contract_manifest_path=manifest_path.as_posix())

            codes = [issue["code"] for issue in result["contract_compile"]["issues"]]
            self.assertIn("contract_prepared_hash_mismatch", codes)

    def test_lint_svg_warns_external_image_and_reports_font_shorthand(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font: 700 24px Arial;color:#111827;">Title</div>
          </foreignObject>
          <image id="hero" slide:role="image" href="https://example.com/hero.jpg" x="560" y="96" width="320" height="220" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertIn("external_image_href", codes)
        self.assertIn("font_shorthand", codes)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_warns_image_opacity_as_unsupported(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <image id="faded" slide:role="image" href="@./assets/bg.png" x="80" y="80" width="320" height="180" opacity="0.2" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("image_opacity_unsupported", codes)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_accepts_chart_marker(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          {chart_marker(chart_metadata(chart_spec()))}
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertIn("micro_chart", result["visual_primitives"]["present"])
        self.assertIn("chart_geometry", result["visual_primitives"]["effects"])

    def test_lint_svg_rejects_invalid_chart_marker(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <g>{chart_marker(chart_metadata(chart_spec(), "sha256:" + "0" * 64))}</g>
          <g slide:role="whiteboard" x="0" y="0" width="100" height="60" />
          <metadata data-svglide-whiteboard="svglide-whiteboard-inline/v1">abc</metadata>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("chart_marker_not_root_child", codes)
        self.assertIn("unsupported_whiteboard_role", codes)
        self.assertIn("legacy_whiteboard_marker", codes)

    def test_lint_svg_rejects_chart_marker_payload_hash_and_spec(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          {chart_marker(chart_metadata(chart_spec(), "sha256:" + "0" * 64))}
          {chart_marker(chart_metadata('{"version":"svglide-chart-spec/v1","chartType":"pie","data":{"categories":["Q1"],"series":[{"name":"Revenue","values":[12]}]}}'))}
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("chart_marker_payload_hash_mismatch", codes)
        self.assertIn("chart_marker_payload_spec", codes)

    def test_lint_svg_rejects_old_sxsd_chart_marker_format(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          {chart_marker(chart_metadata("<chart />", data_format="sxsd-chart-v1", data_encoding="base64url"))}
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("chart_marker_metadata_format", codes)
        self.assertIn("chart_marker_metadata_encoding", codes)

    def test_lint_svg_rejects_chart_marker_values_mismatch(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          {chart_marker(chart_metadata('{"version":"svglide-chart-spec/v1","chartType":"bar","data":{"categories":["Q1","Q2"],"series":[{"name":"Revenue","values":[12]}]}}'))}
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("chart_marker_payload_spec", codes)

    def test_lint_svg_rejects_duplicate_chart_refs(self) -> None:
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          {chart_marker(chart_metadata(chart_spec()))}
          {chart_marker(chart_metadata(chart_spec("line")))}
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("chart_marker_duplicate_ref", codes)

    def test_lint_svg_warns_circle_stroke_width_is_unstable(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <circle id="ring" slide:role="shape" cx="180" cy="180" r="48" fill="#fff" stroke="#EE1A3B" stroke-width="4" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("ellipse_stroke_width_unstable", codes)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_warns_decorative_stroke_dasharray_is_unstable(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <path id="decorative-divider" slide:role="shape" data-svglide-motif-owner="unit-test" data-svglide-motif-id="decorative-divider" d="M80 80 L220 160" fill="none" stroke="#EE1A3B" stroke-width="2" stroke-dasharray="8 8" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("stroke_dasharray_unstable", codes)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_reports_key_path_stroke_dasharray_as_error(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <path id="conversion-flow-route" slide:role="shape" data-svglide-semantic-role="conversion-flow-route" d="M80 80 L220 160" fill="none" stroke="#EE1A3B" stroke-width="2" stroke-dasharray="8 8" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("stroke_dasharray_key_path", codes)
        self.assertEqual(result["summary"]["error_count"], 1)

    def test_lint_svg_reports_canvas_error_and_safe_area_warning(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="badge" slide:role="shape" x="12" y="20" width="80" height="40" />
          <rect id="overflow" slide:role="shape" x="920" y="500" width="120" height="80" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("safe_area", codes)
        self.assertIn("canvas_bounds", codes)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_does_not_warn_for_edge_backing_and_decorative_frame(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="right-backing" slide:role="shape" x="332" y="0" width="628" height="540" fill="#06100E" opacity="0.76" />
          <rect id="bottom-backing" slide:role="shape" x="0" y="320" width="960" height="220" fill="#06100E" opacity="0.82" />
          <rect id="decorative-frame" slide:role="shape" x="42" y="36" width="876" height="466" fill="none" stroke="#D7B46A" stroke-width="2" opacity="0.35" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="76" y="76" width="650" height="68">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:42px;font-weight:900;color:#F6E8BC;line-height:1.2;">Title</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("safe_area", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_svg_reports_text_bbox_overlap(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="a" slide:role="shape" slide:shape-type="text" x="80" y="80" width="240" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:24px;font-weight:700;color:#111;">A</div>
          </foreignObject>
          <foreignObject id="b" slide:role="shape" slide:shape-type="text" x="120" y="100" width="240" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:400;color:#111;">B</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "text_bbox_overlap")

    def test_lint_svg_reports_badge_headline_overlap(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="chapter-badge" slide:role="shape" x="66" y="48" width="86" height="28" fill="#111827" />
          <foreignObject id="headline" slide:role="shape" slide:shape-type="text" x="66" y="76" width="320" height="56">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:34px;font-weight:900;color:#111;line-height:1.1;">回顾与复盘</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("badge_headline_overlap", codes)

    def test_lint_svg_accepts_badge_headline_safe_gap(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="chapter-badge" slide:role="shape" x="66" y="48" width="86" height="28" fill="#111827" />
          <foreignObject id="headline" slide:role="shape" slide:shape-type="text" x="66" y="88" width="320" height="56">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:34px;font-weight:900;color:#111;line-height:1.1;">回顾与复盘</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("badge_headline_overlap", codes)

    def test_lint_svg_reports_text_container_overflow(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="footer-card" slide:role="shape" x="72" y="430" width="420" height="52" fill="#FFF8EE" stroke="#D9C8AE" />
          <foreignObject id="footer-text" slide:role="shape" slide:shape-type="text" x="96" y="444" width="430" height="24">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:16px;font-weight:800;color:#111;line-height:1.1;">会议输出：统一市场判断、年度策略、团队分工与执行节奏</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("text_container_overflow", codes)

    def test_lint_svg_warns_decorative_line_title_pressure(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="decorative-title-rule" slide:role="shape" x="80" y="60" width="820" height="6" fill="#2A7F71" />
          <foreignObject id="headline" slide:role="shape" slide:shape-type="text" x="80" y="76" width="620" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:48px;font-weight:900;color:#111;line-height:1.1;">去年 400 万营收</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("decorative_line_title_pressure", codes)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_reports_visible_metadata_leak(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="leak" slide:role="shape" slide:shape-type="text" x="80" y="80" width="520" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111;">raw_grid beautiful-feishu-whiteboard /tmp/source.svg prompt:</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("visible_svg_metadata_leak", codes)

    def test_lint_svg_allows_user_visible_slash_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="slash-text" slide:role="shape" slide:shape-type="text" x="80" y="80" width="520" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111;">A/B testing improves DATA/METHOD alignment</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("visible_svg_metadata_leak", codes)

    def test_lint_svg_reports_light_text_without_dark_backing(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="red-panel" slide:role="shape" x="0" y="0" width="300" height="540" fill="#EE1A3B" />
          <foreignObject id="crossing-title" slide:role="shape" slide:shape-type="text" x="60" y="120" width="420" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:36px;font-weight:900;color:#FFFFFF;line-height:1.1;">Crossing title</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("light_text_without_dark_backing", codes)

    def test_lint_svg_accepts_light_text_inside_dark_backing(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="red-panel" slide:role="shape" x="0" y="0" width="420" height="540" fill="#EE1A3B" />
          <foreignObject id="contained-title" slide:role="shape" slide:shape-type="text" x="60" y="120" width="300" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:36px;font-weight:900;color:#FFFFFF;line-height:1.1;">Contained title</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("light_text_without_dark_backing", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_svg_reports_round_node_text_overflow(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <circle id="renew-node" slide:role="shape" cx="640" cy="260" r="34" fill="#EE1A3B" />
          <foreignObject id="renew-note" slide:role="shape" slide:shape-type="text" x="592" y="264" width="96" height="26">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:10px;font-weight:600;color:#FFFFFF;line-height:1.2;text-align:center;">到期前价值提醒</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("node_text_overflow", codes)

    def test_lint_svg_reports_zero_size_text_box(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="empty" slide:role="shape" slide:shape-type="text" x="80" y="80" width="200" height="0">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:400;color:#111;">Hidden</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "non_positive_bbox")

    def test_lint_plan_accepts_diverse_svglide_plan(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 10,
            **style_plan_fields(),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "cover_full_bleed",
                    "density": "low",
                    "title": "Cover",
                    "takeaway": "Start",
                    **recipe_fields("hero_typography", ["typography", "geometric_shape"]),
                },
                {
                    "page": 2,
                    "renderer_id": "agenda_matrix",
                    "density": "medium",
                    "title": "Agenda",
                    "takeaway": "Map",
                    **recipe_fields("geometric_composition", ["geometric_shape", "path"]),
                },
                {
                    "page": 3,
                    "renderer_id": "dashboard_scorecard",
                    "density": "high",
                    "density_structure": "dashboard with four metric cards and trend line",
                    "title": "Signal",
                    "takeaway": "Evidence",
                    **recipe_fields("infographic_scorecard", ["typography", "micro_chart"]),
                },
                {
                    "page": 4,
                    "renderer_id": "comparison_table",
                    "density": "high",
                    "density_structure": "comparison table",
                    "title": "Compare",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                },
                {
                    "page": 5,
                    "renderer_id": "timeline_rail",
                    "density": "medium",
                    "title": "Timeline",
                    **recipe_fields("gradient_depth", ["gradient", "geometric_shape"]),
                },
                {
                    "page": 6,
                    "renderer_id": "process_flow",
                    "density": "high",
                    "density_structure": "five node flow",
                    "title": "Flow",
                    **recipe_fields("technical_texture", ["texture", "path"]),
                },
                {
                    "page": 7,
                    "renderer_id": "case_card_wall",
                    "density": "medium",
                    "title": "Case",
                    **recipe_fields("icon_capability_map", ["icon", "geometric_shape"]),
                },
                {
                    "page": 8,
                    "renderer_id": "source_guard_panel",
                    "density": "medium",
                    "source_status": "attachment_missing",
                    "source_policy": "待从附件补齐；no numeric claims",
                    "title": "Attachment",
                    **recipe_fields("spotlight_annotation", ["spotlight", "annotation"]),
                },
                {
                    "page": 9,
                    "renderer_id": "risk_matrix",
                    "density": "high",
                    "density_structure": "2x2 risk matrix",
                    "title": "Risk",
                    **recipe_fields("fake_ui_dashboard", ["dashboard", "micro_chart"]),
                },
                {
                    "page": 10,
                    "renderer_id": "closing_cta",
                    "density": "low",
                    "page_type": "closing",
                    "title": "Thanks",
                    **recipe_fields("brand_system", ["typography", "geometric_shape"]),
                },
            ],
        }
        result = svg_preflight.lint_plan(plan)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertGreaterEqual(result["distinct_renderer_count"], 5)
        self.assertGreaterEqual(result["distinct_layout_family_count"], 5)

    def test_template_family_leak_catalog_has_34_complete_entries(self) -> None:
        catalog = svg_preflight.STYLE_PRESET_CATALOG
        self.assertEqual(len(catalog), 34)
        tokens = set()
        for style_id, preset in catalog.items():
            self.assertEqual(style_id, preset["style_id"])
            self.assertTrue(preset.get("display_name"))
            self.assertTrue(preset.get("source_token"))
            self.assertTrue(preset["source_token"].endswith("/template.json"))
            tokens.add(preset["source_token"])
        self.assertEqual(len(tokens), 34)

    def test_lint_plan_reports_unknown_template_family(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **style_plan_fields("not_a_real_style"),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_template_family_unknown", codes)

    def test_lint_plan_requires_rule_loading_and_art_direction(self) -> None:
        fields = style_plan_fields()
        fields.pop("loaded_rule_set")
        fields.pop("art_direction")
        fields["quality_gates"] = {"no_text_overflow": True}
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **fields,
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_loaded_rule_set", codes)
        self.assertIn("plan_missing_art_direction", codes)

    def test_lint_plan_requires_design_asset_selection_contract(self) -> None:
        fields = style_plan_fields()
        fields.pop("style_pack_selection")
        fields.pop("style_lock")
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **fields,
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_style_pack_selection", codes)
        self.assertIn("plan_missing_style_lock", codes)

    def test_lint_plan_rejects_random_decoration_policy_in_style_lock(self) -> None:
        fields = style_plan_fields()
        fields["style_lock"]["decoration_policy_id"] = "random_decorations"  # type: ignore[index]
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **fields,
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_disallowed_decoration_policy", codes)

    def test_lint_plan_route_only_svg_still_requires_svg_gates(self) -> None:
        fields = style_plan_fields()
        fields.pop("loaded_rule_set")
        fields.pop("art_direction")
        plan = {
            "route": "svglide-svg",
            "page_count": 1,
            **fields,
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_loaded_rule_set", codes)
        self.assertIn("plan_missing_art_direction", codes)

    def test_lint_plan_requires_new_private_rule_contracts(self) -> None:
        fields = style_plan_fields()
        fields["loaded_rule_set"] = sorted(
            svg_preflight.SVG_PRIVATE_REQUIRED_RULE_FILES
            - {"skills/lark-slides/references/svglide-assets.contract.md"}
        )
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **fields,
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **recipe_fields("path_flow", ["path", "annotation"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        missing = [issue for issue in result["issues"] if issue["code"] == "plan_missing_loaded_rule_set"]
        self.assertEqual(len(missing), 1)
        self.assertIn("svglide-assets.contract.md", missing[0]["hint"])

    def test_lint_plan_requires_business_claim_sources(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **style_plan_fields(),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "revenue_scorecard",
                    "density": "medium",
                    "title": "营收 500 万目标",
                    **recipe_fields("infographic_scorecard", ["typography", "micro_chart"]),
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_business_claims", codes)

        plan["business_claims"] = [
            {"claim": "营收 500 万目标", "source_type": "prompt_provided"},
            {"claim": "增量来自服务包拆分", "source_type": "derived", "derivation": "derived from the prompt target and strategy request"},
        ]
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("plan_missing_business_claims", codes)
        self.assertNotIn("plan_business_claim_missing_derivation", codes)

        plan["business_claims"] = [{"claim": "团队 7 人", "source_type": "prompt_provided"}]
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertIn("plan_business_claim_uncovered", codes)

    def test_lint_plan_accepts_nested_visual_plan(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **style_plan_fields(),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "title": "Route",
                    "visual_plan": {
                        "layout_family": "flow",
                        "density": "medium",
                        **recipe_fields("path_flow", ["path", "annotation"]),
                    },
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_plan_reports_unsafe_svg_effect_without_fallback(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **style_plan_fields(),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "route_story",
                    "density": "medium",
                    "title": "Route",
                    **{
                        **recipe_fields("path_flow", ["path", "annotation"]),
                        "svg_effects": ["stroke_dasharray"],
                    },
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("plan_svg_effect_requires_safe_fallback", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_files_reports_declared_svg_effect_missing_from_source(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Title</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        **{
                            **recipe_fields("path_flow", ["path", "annotation"]),
                            "svg_effects": ["gradient"],
                        },
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_svg_effect_not_found", codes)

    def test_lint_files_route_only_plan_runs_source_alignment(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Route</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = {
                "route": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "title": "Route",
                        **recipe_fields("path_flow", ["path", "annotation"]),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_recipe_required_primitives_not_found", codes)

    def test_lint_files_reports_svg_source_business_claim_uncovered(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">营收 500 万目标</div>
          </foreignObject>
          <path id="trend" slide:role="shape" d="M64 360 L180 330 C260 300 340 340 420 300 Q500 260 580 290" fill="none" stroke="#2563eb" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "business_claims": [{"claim": "团队 7 人", "source_type": "prompt_provided"}],
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "title": "Route",
                        **recipe_fields("path_flow", ["path", "annotation"]),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("source_business_claim_uncovered", codes)

    def test_lint_plan_reports_deck_level_generation_risks(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 10,
            **style_plan_fields(),
            "slides": [
                {"page": 1, "renderer_id": "two_column", "density": "low", "title": "Cover"},
                {"page": 2, "renderer_id": "two_column", "density": "medium", "title": "Agenda"},
                {"page": 3, "renderer_id": "two_column", "density": "medium", "title": "Context"},
                {"page": 4, "renderer_id": "two_column", "density": "high", "title": "Dense"},
                {"page": 5, "renderer_id": "two_column", "density": "medium", "title": "Problem"},
                {
                    "page": 6,
                    "renderer_id": "two_column",
                    "density": "medium",
                    "requires_attachment": True,
                    "source_status": "attachment_missing",
                    "title": "Numbers",
                    "key_message": "Use exact numeric claims",
                },
                {"page": 7, "renderer_id": "two_column", "density": "medium", "title": "Plan"},
                {"page": 8, "renderer_id": "two_column", "density": "medium", "title": "Action"},
                {"page": 9, "renderer_id": "two_column", "density": "medium", "title": "Review"},
                {"page": 10, "renderer_id": "two_column", "density": "medium", "title": "Roadmap"},
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_template_variant", codes)
        self.assertIn("plan_missing_semantic_blocks", codes)
        self.assertIn("plan_missing_component_selection", codes)
        self.assertIn("plan_missing_asset_strategy", codes)
        self.assertIn("plan_renderer_repetition", codes)
        self.assertIn("plan_renderer_diversity_low", codes)
        self.assertIn("plan_high_density_without_structure", codes)
        self.assertIn("plan_missing_source_guard", codes)
        self.assertIn("plan_missing_closing_slide", codes)

    def test_lint_plan_requires_svglide_generation_contract_fields(self) -> None:
        plan = {
            "output_mode": "svglide-svg",
            "page_count": 1,
            **style_plan_fields(),
            "slides": [
                {
                    "page": 1,
                    "renderer_id": "dashboard_scorecard",
                    "density": "high",
                    "density_structure": "dashboard",
                    "visual_recipe": "fake_ui_dashboard",
                    "visual_intent": "show an operating dashboard",
                    "visual_focal_point": "metric cards",
                    "svg_primitives": ["dashboard", "micro_chart"],
                    "xml_like_risk": "would become generic cards",
                }
            ],
        }
        result = svg_preflight.lint_plan(plan)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_missing_template_variant", codes)
        self.assertIn("plan_missing_semantic_blocks", codes)
        self.assertIn("plan_missing_component_selection", codes)
        self.assertIn("plan_missing_asset_strategy", codes)
        self.assertIn("plan_missing_asset_contract", codes)
        self.assertIn("plan_missing_risk_flags", codes)
        self.assertIn("plan_missing_source_policy", codes)
        self.assertIn("plan_missing_content_density_contract", codes)
        self.assertIn("plan_high_density_contract_not_quantified", codes)

    def test_lint_plan_reports_layout_family_diversity_and_repetition(self) -> None:
        slides = []
        recipes = [
            "hero_typography",
            "geometric_composition",
            "infographic_scorecard",
            "path_flow",
            "gradient_depth",
            "technical_texture",
            "icon_capability_map",
            "spotlight_annotation",
            "fake_ui_dashboard",
            "brand_system",
        ]
        for index, recipe in enumerate(recipes, 1):
            slide = {
                "page": index,
                "renderer_id": f"renderer_{index}",
                "layout_family": "two_column",
                "density": "medium",
                "title": "Thanks" if index == 10 else f"Page {index}",
                **recipe_fields(recipe, list(svg_preflight.VISUAL_RECIPE_CATALOG[recipe]["required_primitives"])),
            }
            slide["layout_family"] = "two_column"
            slides.append(slide)
        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 10, **style_plan_fields(), "slides": slides})
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_layout_family_diversity_low", codes)
        self.assertIn("plan_layout_family_repetition", codes)

    def test_lint_files_accepts_recipe_source_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                **style_plan_fields(),
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "visual_recipe": "path_flow",
                        "visual_intent": "show a rising product route",
                        "visual_focal_point": "curved route line",
                        "visual_signature": "curved route path with explicit annotations",
                        "svg_effects": ["path", "connector_flow", "typography"],
                        "required_primitives": ["path", "annotation"],
                        "svg_primitives": ["path", "annotation"],
                        "xml_like_risk": "would become cards plus arrows in XML",
                        "content_density_contract": "flow >= 4 stages",
                        "asset_contract": {
                            "source_type": "procedural",
                            "license": "original generated asset",
                            "local_path": "@./assets/hero.jpg",
                            "usage_page": 1,
                            "generated_by": "unit test",
                        },
                        "risk_flags": [],
                        "source_policy": "Use prompt-provided content only.",
                        "template_variant": "path_flow",
                        "semantic_blocks": [
                            {"block_id": "title", "type": "title", "content": "Unit test title"},
                            {"block_id": "message", "type": "finding", "content": "Use path_flow"},
                        ],
                        "component_selection": [
                            {"component_id": "title_block", "binds": ["title"]},
                            {"component_id": "finding_callout", "binds": ["message"]},
                        ],
                        "asset_strategy": {"strategy_id": "structured_fallback", "expected_asset_count": 0},
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_plan_file_reports_lock_page_path_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir) / "02-plan"
            plan_dir.mkdir()
            plan_path = plan_dir / "slide_plan.json"
            lock_path = plan_dir / "svglide.lock.json"
            plan = {
                "route": "svglide-svg",
                "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
                "svg_files": [{"page": 1, "path": "04-svg/prepared/page-001.svg"}],
                **style_plan_fields(),
                "slides": [],
            }
            lock = {
                "version": "svglide-lock/v1",
                "route": "svglide-svg",
                "pages": [{"page": 1, "path": "04-svg/prepared/page-002.svg"}],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            lock_path.write_text(json.dumps(lock), encoding="utf-8")

            result = svg_preflight.lint_plan_file(str(plan_path))

            codes = [issue["code"] for issue in result["issues"]]
            self.assertIn("plan_lock_conflict", codes)

    def test_lint_files_reports_declared_recipe_without_source_primitives(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Title</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            loaded_rules_json = json.dumps(sorted(svg_preflight.SVG_PRIVATE_REQUIRED_RULE_FILES), indent=20)
            plan_path.write_text(
                """
                {
                  "output_mode": "svglide-svg",
                  "page_count": 1,
                  "template_family_selection": {
                    "enabled": true,
                    "source": "beautiful-html-template-families",
                    "selected_template_id": "raw-grid",
                    "candidate_template_ids": ["raw-grid", "blue-professional", "signal"],
                    "selection_reason": "raw-grid fits technical training pages that need dense but readable visual structure"
                  },
                  "loaded_rule_set": __LOADED_RULE_SET__,
                  "plan_path": ".lark-slides/plan/test/slide_plan.json",
                  "quality_gates": {
                    "no_text_overflow": true,
                    "no_debug_guides": true,
                    "no_xml_like_pages": true
                  },
                  "art_direction": {
                    "cover_treatment": "hero route cover",
                    "section_divider_treatment": "not applicable for this one-page test",
                    "closing_treatment": "not applicable for this one-page test",
                    "deck_motif": "dense grid panels",
                    "svg_native_moments": ["route path", "hero image", "annotation geometry"]
                  },
                  "svg_files": [{"page": 1, "path": "page-001.svg"}],
                  "slides": [{
                    "page": 1,
                    "renderer_id": "route_story",
                    "layout_family": "flow",
                    "density": "medium",
                    "visual_recipe": "path_flow",
                    "visual_intent": "show a rising product route",
                    "visual_focal_point": "curved route line",
                    "visual_signature": "curved route path with explicit annotations",
                    "svg_effects": ["path", "connector_flow", "typography"],
                    "required_primitives": ["path", "annotation"],
                    "svg_primitives": ["path", "annotation"],
                    "xml_like_risk": "would become cards plus arrows in XML",
                    "content_density_contract": "flow >= 4 stages",
                    "asset_contract": "none_required",
                    "risk_flags": [],
                    "source_policy": "Use prompt-provided content only.",
                    "template_variant": "path_flow",
                    "semantic_blocks": [
                      {"block_id": "title", "type": "title", "content": "Unit test title"},
                      {"block_id": "message", "type": "finding", "content": "Use path_flow"}
                    ],
                    "component_selection": [
                      {"component_id": "title_block", "binds": ["title"]},
                      {"component_id": "finding_callout", "binds": ["message"]}
                    ],
                    "asset_strategy": {"strategy_id": "structured_fallback", "expected_asset_count": 0}
                  }]
                }
                """.replace("__LOADED_RULE_SET__", loaded_rules_json),
                encoding="utf-8",
            )
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_recipe_required_primitives_not_found", codes)

    def test_lint_files_warns_image_without_asset_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "visual_recipe": "path_flow",
                        "visual_intent": "show a rising product route",
                        "visual_focal_point": "curved route line",
                        "visual_signature": "curved route path with explicit annotations",
                        "svg_effects": ["path", "connector_flow", "typography"],
                        "required_primitives": ["path", "annotation"],
                        "svg_primitives": ["path", "annotation"],
                        "xml_like_risk": "would become cards plus arrows in XML",
                        "content_density_contract": "flow >= 4 stages",
                        "asset_contract": "none_required",
                        "risk_flags": [],
                        "source_policy": "Use prompt-provided content only.",
                        **template_slide_fields("path_flow"),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_asset_contract_missing_metadata", codes)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_files_accepts_preview_image_asset_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "visual_recipe": "path_flow",
                        "visual_intent": "show a rising product route",
                        "visual_focal_point": "curved route line",
                        "visual_signature": "curved route path with explicit annotations",
                        "svg_effects": ["path", "connector_flow", "typography"],
                        "required_primitives": ["path", "annotation"],
                        "svg_primitives": ["path", "annotation"],
                        "xml_like_risk": "would become cards plus arrows in XML",
                        "content_density_contract": "flow >= 4 stages",
                        "asset_contract": {
                            "mode": "preview",
                            "source_type": "public_url",
                            "retrieval_query": "strategy review product route hero image",
                            "license": "preview_unverified",
                            "href": "https://example.com/hero.jpg",
                            "usage_page": 1,
                            "source_url": "https://example.com/hero.jpg",
                            "replacement_required": True,
                        },
                        "risk_flags": ["image_preview_only"],
                        "source_policy": "Preview image source is marked and will be replaced before production.",
                        **template_slide_fields("path_flow"),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result.get("plan", {}).get("issues", [])]
        self.assertNotIn("plan_asset_contract_missing_metadata", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_files_resolves_top_level_asset_contract_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "asset_contracts": [
                    {
                        "id": "hero-asset",
                        "source_type": "public_url",
                        "retrieval_query": "strategy review product route hero image",
                        "license": "unsplash",
                        "href": "@./assets/hero.jpg",
                        "usage_page": 1,
                        "source_url": "https://images.unsplash.com/photo-1518770660439-4636190af475",
                    }
                ],
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "visual_recipe": "path_flow",
                        "visual_intent": "show a rising product route",
                        "visual_focal_point": "curved route line",
                        "visual_signature": "curved route path with explicit annotations",
                        "svg_effects": ["path", "connector_flow", "typography"],
                        "required_primitives": ["path", "annotation"],
                        "svg_primitives": ["path", "annotation"],
                        "xml_like_risk": "would become cards plus arrows in XML",
                        "content_density_contract": "flow >= 4 stages",
                        "asset_contract": "hero-asset",
                        "risk_flags": [],
                        "source_policy": "Preview image source is marked and will be replaced before production.",
                        **template_slide_fields("path_flow"),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result.get("plan", {}).get("issues", [])]
        self.assertNotIn("plan_asset_contract_missing_metadata", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_files_warns_preview_web_image_without_retrieval_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 1,
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "layout_family": "flow",
                        "density": "medium",
                        "visual_recipe": "path_flow",
                        "visual_intent": "show a rising product route",
                        "visual_focal_point": "curved route line",
                        "visual_signature": "curved route path with explicit annotations",
                        "svg_effects": ["path", "connector_flow", "typography"],
                        "required_primitives": ["path", "annotation"],
                        "svg_primitives": ["path", "annotation"],
                        "xml_like_risk": "would become cards plus arrows in XML",
                        "content_density_contract": "flow >= 4 stages",
                        "asset_contract": {
                            "mode": "preview",
                            "source_type": "public_url",
                            "license": "preview_unverified",
                            "href": "https://example.com/hero.jpg",
                            "usage_page": 1,
                            "source_url": "https://example.com/hero.jpg",
                            "replacement_required": True,
                        },
                        "risk_flags": ["image_preview_only"],
                        "source_policy": "Preview image source is marked and will be replaced before production.",
                        **template_slide_fields("path_flow"),
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_asset_contract_missing_metadata", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_multi_image_slots_cannot_be_partially_filled(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "market_food_grid",
            "layout_family": "showcase",
            "density": "medium",
            **recipe_fields("mask_clip_showcase", ["typography", "image_overlay"]),
            "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 2},
            "image_slots": [
                {"slot_id": "egg-waffle", "required": True, "semantic_subject": "Hong Kong egg waffle", "real_image_required": True},
                {"slot_id": "fish-ball", "required": True, "semantic_subject": "Hong Kong curry fish balls", "real_image_required": True},
            ],
            "asset_contract": [
                {
                    "asset_id": "egg-waffle-photo",
                    "binds_slot": "egg-waffle",
                    "source_type": "web_search_preview",
                    "semantic_subject": "Hong Kong egg waffle",
                    "retrieval_query": "Hong Kong egg waffle street food photo",
                    "license": "preview_unverified",
                    "href": "https://example.com/egg-waffle.jpg",
                    "usage_page": 1,
                    "source_url": "https://example.com/egg-waffle.jpg",
                }
            ],
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("asset_slot_unfilled", codes)
        self.assertIn("asset_slot_count_mismatch", codes)

    def test_lint_files_reports_prepared_svg_missing_required_image_slot(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <path id="route" slide:role="shape" d="M80 320 C180 260 300 360 420 300" fill="none" stroke="#2563eb" />
          <line id="callout" slide:role="shape" x1="420" y1="300" x2="500" y2="260" stroke="#111827" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            slide = {
                "page": 1,
                "renderer_id": "food_route",
                "layout_family": "flow",
                "density": "medium",
                **recipe_fields("path_flow", ["path", "annotation"]),
                "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 1},
                "image_slots": [{"slot_id": "hero-food", "required": True, "semantic_subject": "Hong Kong street food", "real_image_required": True}],
                "asset_contract": [
                    {
                        "asset_id": "hero-food-photo",
                        "binds_slot": "hero-food",
                        "source_type": "web_search_preview",
                        "semantic_subject": "Hong Kong street food",
                        "retrieval_query": "Hong Kong street food dai pai dong photo",
                        "license": "preview_unverified",
                        "href": "https://example.com/hong-kong-food.jpg",
                        "usage_page": 1,
                        "source_url": "https://example.com/hong-kong-food.jpg",
                    }
                ],
            }
            plan_path.write_text(json.dumps({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "svg_files": [{"page": 1, "path": "page-001.svg"}], "slides": [slide]}), encoding="utf-8")

            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))

        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("preview_missing_required_image", codes)

    def test_generated_bitmap_cannot_satisfy_real_image_slot(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "company_cover",
            "layout_family": "showcase",
            "density": "medium",
            **recipe_fields("mask_clip_showcase", ["typography", "image_overlay"]),
            "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 1},
            "image_slots": [{"slot_id": "company", "required": True, "semantic_subject": "Zhipu AI and MiniMax product logos", "real_image_required": True}],
            "asset_contract": {
                "asset_id": "company-ai-art",
                "binds_slot": "company",
                "source_type": "ai_generated_bitmap",
                "semantic_subject": "Zhipu AI and MiniMax product logos",
                "generated_by": "image model",
                "license": "generated_preview",
                "local_path": "@./assets/company.png",
                "usage_page": 1,
            },
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("generated_bitmap_not_real_image", codes)

    def test_image_subject_mismatch_is_reported(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "food_photo",
            "layout_family": "showcase",
            "density": "medium",
            **recipe_fields("mask_clip_showcase", ["typography", "image_overlay"]),
            "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 1},
            "image_slots": [{"slot_id": "hero-food", "required": True, "semantic_subject": "Hong Kong egg waffle street food", "real_image_required": True}],
            "asset_contract": {
                "asset_id": "office-photo",
                "binds_slot": "hero-food",
                "source_type": "web_search_preview",
                "semantic_subject": "corporate office meeting room",
                "retrieval_query": "corporate office meeting room",
                "license": "preview_unverified",
                "href": "https://example.com/office.jpg",
                "usage_page": 1,
                "source_url": "https://example.com/office.jpg",
            },
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("semantic_mismatch", codes)

    def test_public_url_cannot_satisfy_real_image_slot(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "company_cover",
            "layout_family": "showcase",
            "density": "medium",
            **recipe_fields("mask_clip_showcase", ["typography", "image_overlay"]),
            "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 1},
            "image_slots": [{"slot_id": "company", "required": True, "semantic_subject": "Zhipu and MiniMax product identity", "real_image_required": True}],
            "asset_contract": {
                "asset_id": "company-public-url",
                "binds_slot": "company",
                "source_type": "public_url",
                "semantic_subject": "Zhipu and MiniMax product identity",
                "retrieval_query": "Zhipu MiniMax product identity",
                "license": "preview_unverified",
                "href": "https://example.com/company.png",
                "usage_page": 1,
                "source_url": "https://example.com/company.png",
            },
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("asset_source_type_not_allowed", codes)

    def test_live_submit_requires_file_token_for_required_image_slot(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "company_cover",
            "layout_family": "showcase",
            "density": "medium",
            **recipe_fields("mask_clip_showcase", ["typography", "image_overlay"]),
            "asset_strategy": {"strategy_id": "real_image_required", "expected_asset_count": 1, "live_submit_requires_file_token": True},
            "image_slots": [{"slot_id": "company", "required": True, "semantic_subject": "Zhipu and MiniMax product identity", "real_image_required": True}],
            "asset_contract": {
                "asset_id": "company-web-preview",
                "binds_slot": "company",
                "source_type": "web_search_preview",
                "semantic_subject": "Zhipu and MiniMax product identity",
                "retrieval_query": "Zhipu MiniMax product identity",
                "license": "preview_unverified",
                "href": "https://example.com/company.png",
                "usage_page": 1,
                "source_url": "https://example.com/company.png",
            },
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("live_submit_missing_file_token", codes)

    def test_user_requested_no_images_disables_real_image_requirement(self) -> None:
        slide = {
            "page": 1,
            "renderer_id": "typographic_summary",
            "layout_family": "hero",
            "density": "medium",
            **recipe_fields("hero_typography", ["typography", "geometric_shape"]),
            "asset_strategy": {"strategy_id": "none_required", "user_override": True, "expected_asset_count": 0},
            "image_slots": [],
            "asset_contract": "none_required",
        }

        result = svg_preflight.lint_plan({"output_mode": "svglide-svg", "page_count": 1, **style_plan_fields(), "slides": [slide]})

        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("asset_slot_unfilled", codes)
        self.assertNotIn("generated_bitmap_not_real_image", codes)
        self.assertNotIn("semantic_mismatch", codes)

    def test_unowned_decorative_path_is_rejected(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
          <path id="p5-steam-path-one" slide:role="shape" d="M120 420 C180 360 240 450 300 390" fill="none" stroke="#999" />
        </svg>
        """

        result = svg_preflight.lint_svg(svg)

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("unowned_decorative_primitive", codes)

    def test_family_owned_decorative_motif_is_allowed(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
          <path id="family-steam-path-one" slide:role="shape" data-svglide-motif-owner="pin-and-paper" data-svglide-motif-id="steam-ribbon" d="M120 420 C180 360 240 450 300 390" fill="none" stroke="#999" />
        </svg>
        """

        result = svg_preflight.lint_svg(svg)

        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("unowned_decorative_primitive", codes)

    def test_unbound_flow_route_path_is_rejected(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
          <path id="flow-route" slide:role="shape" d="M120 420 C180 360 240 450 300 390" fill="none" stroke="#999" />
        </svg>
        """

        result = svg_preflight.lint_svg(svg)

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("unowned_decorative_primitive", codes)

    def test_semantic_line_primitive_is_allowed(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
          <path id="conversion-trend-line" slide:role="shape" data-svglide-semantic-role="chart-trend-line" d="M120 420 C180 360 240 450 300 390" fill="none" stroke="#2563eb" />
        </svg>
        """

        result = svg_preflight.lint_svg(svg)

        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("unowned_decorative_primitive", codes)

    def test_decorative_primitive_count_respects_family_limits(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
          <path id="steam-one" slide:role="shape" data-svglide-motif-owner="pin-and-paper" data-svglide-motif-id="steam-ribbon" data-svglide-motif-max-count="2" d="M100 420 C160 360 220 450 280 390" fill="none" stroke="#999" />
          <path id="steam-two" slide:role="shape" data-svglide-motif-owner="pin-and-paper" data-svglide-motif-id="steam-ribbon" data-svglide-motif-max-count="2" d="M300 420 C360 360 420 450 480 390" fill="none" stroke="#999" />
          <path id="steam-three" slide:role="shape" data-svglide-motif-owner="pin-and-paper" data-svglide-motif-id="steam-ribbon" data-svglide-motif-max-count="2" d="M500 420 C560 360 620 450 680 390" fill="none" stroke="#999" />
        </svg>
        """

        result = svg_preflight.lint_svg(svg)

        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("decorative_motif_overuse", codes)

    def test_lint_files_reports_density_contract_not_met_by_source(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <rect id="dashboard-card-a" slide:role="shape" x="80" y="120" width="180" height="90" fill="#ffffff" />
          <rect id="dashboard-card-b" slide:role="shape" x="290" y="120" width="180" height="90" fill="#ffffff" />
          <rect id="dashboard-card-c" slide:role="shape" x="500" y="120" width="180" height="90" fill="#ffffff" />
          <rect id="bar-a" slide:role="shape" x="100" y="250" width="120" height="16" fill="#EE1A3B" />
          <rect id="bar-b" slide:role="shape" x="100" y="280" width="90" height="16" fill="#EE1A3B" />
          <rect id="bar-c" slide:role="shape" x="100" y="310" width="140" height="16" fill="#EE1A3B" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan_path.write_text(
                """
                {
                  "output_mode": "svglide-svg",
                  "page_count": 1,
                  "style_preset": "raw_grid",
                  "style_selection_reason": "raw_grid fits technical training pages that need dense but readable visual structure",
                  "style_system": {
                    "palette": {"background": "#F5F5F5", "text": "#0A0A0A", "accent": "#F2D4CF"},
                    "typography": "strong title, readable native text labels",
                    "background_strategy": "muted grid panels",
                    "motif": "dense grid panels"
                  },
                  "svg_files": [{"page": 1, "path": "page-001.svg"}],
                  "slides": [{
                    "page": 1,
                    "renderer_id": "dashboard_scorecard",
                    "layout_family": "dashboard",
                    "density": "high",
                    "density_structure": "dashboard",
                    "visual_recipe": "fake_ui_dashboard",
                    "visual_intent": "show an operating dashboard",
                    "visual_focal_point": "metric cards",
                    "visual_signature": "dashboard cards with bar geometry",
                    "svg_effects": ["chart_geometry"],
                    "required_primitives": ["dashboard", "micro_chart"],
                    "svg_primitives": ["dashboard", "micro_chart"],
                    "xml_like_risk": "would become generic cards",
                    "content_density_contract": "dashboard >= 5 metrics",
                    "asset_contract": "none_required",
                    "risk_flags": [],
                    "source_policy": "Use prompt-provided content only."
                  }]
                }
                """,
                encoding="utf-8",
            )
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_content_density_contract_not_met", codes)

    def test_lint_svg_reports_xml_like_card_layout(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <rect id="card-a" slide:role="shape" x="80" y="150" width="220" height="130" fill="#ffffff" />
          <rect id="card-b" slide:role="shape" x="340" y="150" width="220" height="130" fill="#ffffff" />
          <rect id="card-c" slide:role="shape" x="600" y="150" width="220" height="130" fill="#ffffff" />
          <foreignObject id="a" slide:role="shape" slide:shape-type="text" x="104" y="180" width="160" height="48">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;">A</div>
          </foreignObject>
          <foreignObject id="b" slide:role="shape" slide:shape-type="text" x="364" y="180" width="160" height="48">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;">B</div>
          </foreignObject>
          <foreignObject id="c" slide:role="shape" slide:shape-type="text" x="624" y="180" width="160" height="48">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;">C</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("xml_like_svg_layout", codes)

    def test_lint_files_includes_optional_plan_result(self) -> None:
        result = svg_preflight.lint_files([], None)
        self.assertEqual(result["summary"]["file_count"], 0)


if __name__ == "__main__":
    unittest.main()
