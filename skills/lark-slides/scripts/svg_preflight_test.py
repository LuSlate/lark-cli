# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import svg_private_docs_lint
import svg_preflight


VALID_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     slide:contract-version="svglide-authoring-contract/v1"
     width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
  <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="46" width="500" height="46">
    <div xmlns="http://www.w3.org/1999/xhtml"
         style="font-size:28px;font-weight:800;font-family:Arial;color:#111827;line-height:1.15;text-align:left;">
      Strategy review
    </div>
  </foreignObject>
  <image id="hero" slide:role="image" href="@./assets/hero.jpg" x="560" y="96" width="320" height="220" />
  <foreignObject id="body-input" slide:role="shape" slide:shape-type="text" x="76" y="226" width="96" height="30">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:700;color:#111827;line-height:1.2;text-align:center;">Input</div>
  </foreignObject>
  <foreignObject id="body-output" slide:role="shape" slide:shape-type="text" x="780" y="226" width="96" height="30">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:700;color:#111827;line-height:1.2;text-align:center;">Output</div>
  </foreignObject>
  <foreignObject id="callout-note" slide:role="shape" slide:shape-type="text" x="170" y="392" width="420" height="28">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:13px;font-weight:600;color:#334155;line-height:1.2;text-align:left;">Pipeline stays inside seed boxes</div>
  </foreignObject>
  <path id="trend-flow-path" slide:role="shape" d="M210 260 C360 190 520 330 750 260" fill="none" stroke="#2563eb" />
</svg>
"""

ROUTE_DIR = Path(__file__).resolve().parent.parent / "references" / "routes" / "create-svg"
ROUTE_MANIFEST_PATH = ROUTE_DIR / "route.manifest.json"
PRIVATE_RECIPE_MANIFEST_PATH = ROUTE_DIR / "private-recipes.manifest.json"
PUBLIC_RECIPE_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "svg-recipes.json"
PUBLIC_SEED_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "svg-seeds.json"
SEED_BY_RECIPE = {
    "hero_typography": "cover_hero_statement",
    "geometric_composition": "comparison_two_column_decision",
    "path_flow": "process_pipeline",
    "infographic_scorecard": "single_chart_takeaway",
    "icon_capability_map": "capability_icon_map",
    "gradient_depth": "section_divider_index",
    "mask_clip_showcase": "image_story_showcase",
    "technical_texture": "architecture_layered_system",
    "metaphor_loop": "loop_flywheel",
    "spotlight_annotation": "spotlight_diagnosis_callout",
    "fake_ui_dashboard": "dashboard_kpi_grid",
    "brand_system": "closing_summary",
}


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def private_recipe_manifest() -> dict[str, object]:
    return read_json(PRIVATE_RECIPE_MANIFEST_PATH)


def private_recipe_ids() -> list[str]:
    recipes = private_recipe_manifest().get("recipes")
    if not isinstance(recipes, dict):
        raise AssertionError("private recipe manifest must include recipes object")
    return list(recipes)


def private_recipe_with_primitive(primitive: str) -> str:
    recipes = private_recipe_manifest().get("recipes")
    if not isinstance(recipes, dict):
        raise AssertionError("private recipe manifest must include recipes object")
    for recipe_id, recipe in recipes.items():
        if not isinstance(recipe, dict):
            continue
        primitives = svg_preflight.normalize_primitives(recipe.get("required_primitives"))
        if primitive in primitives:
            return str(recipe_id)
    raise AssertionError(f"no private recipe requires {primitive}")


def write_recipe_selection(directory: Path, recipe_id: str) -> Path:
    recipes = private_recipe_manifest().get("recipes")
    if not isinstance(recipes, dict) or not isinstance(recipes.get(recipe_id), dict):
        raise AssertionError("private recipe must exist in manifest")
    recipe = recipes[recipe_id]
    path = directory / "recipe-selection.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "route_id": "create-svg",
                "manifest_ref": "references/routes/create-svg/private-recipes.manifest.json",
                "manifest_digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
                "selections": [
                    {
                        "page_index": 1,
                        "page": 1,
                        "private_recipe_id": recipe_id,
                        "base_recipe": recipe["base_recipe"],
                        "required_primitives": recipe["required_primitives"],
                        "required_effects": recipe["required_effects"],
                        "minimum_visible_area_ratio": recipe["minimum_visible_area_ratio"],
                        "source_truth_evidence": [
                            {
                                "requirement": "unit test route-private evidence",
                                "evidence": "unit test SVG source and plan alignment",
                                "source_ref": "slide_plan.json#/slides/0",
                            }
                        ],
                        "selection_reason": "unit test validates route-private selection gates",
                        "fallback_policy": "deny",
                        "exemption_policy": "deny",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def private_context(selection_path: Path | None = None) -> dict[str, object]:
    return svg_preflight.build_preflight_context(
        str(ROUTE_MANIFEST_PATH),
        str(selection_path) if selection_path else None,
    )


def private_route_plan(primitives: set[str] | list[str], **slide_overrides: object) -> dict[str, object]:
    primitive_list = sorted(primitives)
    slide = {
        "page": 1,
        "renderer_id": "route_private_story",
        "density": "medium",
        **seed_fields("process_pipeline"),
        "visual_recipe": "route_private",
        "visual_intent": "use the route-private SVG recipe selected by the create-svg sidecar",
        "visual_focal_point": "route-private visual structure",
        "visual_signature": "route-private SVG structure is proven by source primitives",
        "svg_effects": effects_for_primitives(primitive_list),
        "required_primitives": primitive_list,
        "svg_primitives": primitive_list,
        "xml_like_risk": "would collapse into generic XML cards without the SVG route-private recipe",
        "content_density_contract": "flow >= 4 stages",
        "asset_contract": "none_required",
        "risk_flags": [],
        "source_policy": "Use prompt-provided content only.",
    }
    slide.update(slide_overrides)
    return {
        "output_mode": "svglide-svg",
        "page_count": 1,
        **style_plan_fields(),
        "svg_files": [{"page": 1, "path": "page-001.svg"}],
        "slides": [slide],
    }


def private_route_plan_for_context(context: dict[str, object], recipe_id: str, **slide_overrides: object) -> dict[str, object]:
    primitives = svg_preflight.recipe_required_primitives(recipe_id, context)
    return private_route_plan(primitives, **slide_overrides)


def issue_codes(result: dict[str, object]) -> list[str]:
    return [str(issue.get("code")) for issue in result.get("issues", []) if isinstance(issue, dict)]


def issue_levels(result: dict[str, object], code: str) -> list[str]:
    return [str(issue.get("level")) for issue in result.get("issues", []) if isinstance(issue, dict) and issue.get("code") == code]


def plan_issue_codes(result: dict[str, object]) -> list[str]:
    plan = result.get("plan")
    if not isinstance(plan, dict):
        return []
    return issue_codes(plan)


def with_contract(svg: str) -> str:
    if "slide:contract-version=" in svg:
        return svg
    return svg.replace(
        'slide:role="slide"',
        f'slide:role="slide"\n             slide:contract-version="{svg_preflight.SVG_CONTRACT_VERSION}"',
        1,
    )


def style_plan_fields(preset_id: str = "raw_grid") -> dict[str, object]:
    return {
        "style_preset": preset_id,
        "style_selection_reason": "raw_grid fits technical training pages that need dense but readable visual structure",
        "style_system": {
            "palette": {
                "background": "#F5F5F5",
                "text": "#0A0A0A",
                "accent": "#F2D4CF",
            },
            "typography": "strong title, readable native text labels",
            "background_strategy": "muted grid panels with one stable background family",
            "motif": "dense grid panels with restrained accent labels",
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


def recipe_fields(recipe: str, primitives: list[str]) -> dict[str, object]:
    seed = seed_fields(SEED_BY_RECIPE.get(recipe, "process_pipeline"))
    return {
        **seed,
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
    }


def seed_fields(seed_id: str = "process_pipeline") -> dict[str, object]:
    seed = svg_preflight.SVG_SEED_CATALOG[seed_id]
    key_message = "One seeded idea"
    return {
        "seed_id": seed_id,
        "layout_family": seed["layout_family"],
        "layout_skeleton_id": seed["layout_skeleton"]["id"],
        "layout_boxes": seed["layout_boxes"],
        "content_budget": seed["content_budget"],
        "text_capacity": seed["default_text_capacity"],
        "text_budget_by_role": seed["text_budget_by_role"],
        "one_idea": key_message,
        "key_message": key_message,
        "reserved_bands": seed["reserved_bands"],
        "footer_safe_zone": seed["footer_safe_zone"],
        "vertical_text_policy": seed["vertical_text_policy"],
    }


def single_slide_plan(recipe: str = "path_flow", primitives: list[str] | None = None, **slide_overrides: object) -> dict[str, object]:
    primitive_list = primitives or list(svg_preflight.VISUAL_RECIPE_CATALOG[recipe]["required_primitives"])
    slide = {
        "page": 1,
        "renderer_id": "route_story",
        "density": "medium",
        "title": "Route",
        **recipe_fields(recipe, primitive_list),
        "asset_contract": "none_required",
    }
    slide.update(slide_overrides)
    return {
        "output_mode": "svglide-svg",
        "page_count": 1,
        **style_plan_fields(),
        "slides": [slide],
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

    def test_visual_primitives_count_vertical_bars_as_bar_geometry(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             slide:contract-version="svglide-authoring-contract/v1"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <rect id="bar-a" slide:role="shape" x="120" y="220" width="56" height="190" fill="#e63946" />
          <rect id="bar-b" slide:role="shape" x="220" y="260" width="56" height="150" fill="#f4a261" />
          <rect id="bar-c" slide:role="shape" x="320" y="310" width="56" height="100" fill="#52b788" />
        </svg>
        """
        result = svg_preflight.lint_svg(svg)
        primitives = result["visual_primitives"]
        self.assertGreaterEqual(primitives["counts"]["bar_like_rect"], 3)
        self.assertIn("micro_chart", primitives["present"])

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

    def test_lint_svg_counts_regular_foreign_object_text_as_typography(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="small-label" slide:role="shape" slide:shape-type="text" x="120" y="160" width="180" height="28">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:700;color:#111827;">Regular label</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertIn("typography", result["visual_primitives"]["present"])
        self.assertIn("typography", result["visual_primitives"]["effects"])

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
          <path id="decorative-divider" slide:role="shape" d="M80 80 L220 160" fill="none" stroke="#EE1A3B" stroke-width="2" stroke-dasharray="8 8" />
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
          <path id="conversion-flow-route" slide:role="shape" d="M80 80 L220 160" fill="none" stroke="#EE1A3B" stroke-width="2" stroke-dasharray="8 8" />
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

    def test_lint_svg_reports_hidden_visible_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="hidden-copy" slide:role="shape" slide:shape-type="text" x="80" y="120" width="360" height="80" display="none">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;">This copy is part of the visible plan but hidden in SVG.</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("hidden_visible_text", codes)

    def test_lint_svg_reports_parent_hidden_visible_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <g display="none">
            <foreignObject id="hidden-copy" slide:role="shape" slide:shape-type="text" x="80" y="120" width="360" height="80">
              <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;">This visible copy is hidden by its parent group.</div>
            </foreignObject>
          </g>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("hidden_visible_text", codes)

    def test_lint_svg_reports_clipped_visible_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="clipped-copy" slide:role="shape" slide:shape-type="text" x="80" y="120" width="120" height="24" style="overflow:hidden;">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;line-height:1.2;">This sentence will wrap into multiple hidden lines.</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("clipped_visible_text", codes)

    def test_lint_svg_reports_parent_clipped_visible_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <g style="overflow:hidden;">
            <foreignObject id="clipped-copy" slide:role="shape" slide:shape-type="text" x="80" y="120" width="120" height="24">
              <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:700;color:#111827;line-height:1.2;">This sentence will wrap into multiple hidden lines.</div>
            </foreignObject>
          </g>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("clipped_visible_text", codes)

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

    def test_lint_svg_reports_title_surface_pressure(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="headline" slide:role="shape" slide:shape-type="text" x="64" y="56" width="380" height="94">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:38px;font-weight:900;color:#111;line-height:1.1;">挑战不是单点问题</div>
          </foreignObject>
          <rect id="too-close-card" slide:role="shape" x="98" y="126" width="244" height="82" fill="#ffffff" />
          <foreignObject id="card-text" slide:role="shape" slide:shape-type="text" x="124" y="150" width="170" height="30">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:800;color:#111;line-height:1.2;">客户结构集中</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("title_surface_pressure", codes)

    def test_lint_svg_reports_plain_white_text_panel(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="plain-card" slide:role="shape" x="120" y="190" width="260" height="82" fill="#ffffff" />
          <foreignObject id="card-text" slide:role="shape" slide:shape-type="text" x="144" y="214" width="190" height="32">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:800;color:#111;line-height:1.2;">服务品类偏窄</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plain_white_text_panel", codes)

    def test_lint_svg_accepts_accent_rail_text_panel(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="treated-card" slide:role="shape" x="120" y="190" width="260" height="82" fill="#ffffff" />
          <rect id="accent-rail" slide:role="shape" x="120" y="190" width="8" height="82" fill="#57c9a7" />
          <foreignObject id="card-text" slide:role="shape" slide:shape-type="text" x="144" y="214" width="190" height="32">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:800;color:#111;line-height:1.2;">服务品类偏窄</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result.get("issues", [])]
        self.assertNotIn("plain_white_text_panel", codes)

    def test_lint_svg_reports_connector_crosses_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <line id="bad-leader" slide:role="shape" x1="200" y1="292" x2="700" y2="292" stroke="#94A3B8" stroke-width="3" />
          <foreignObject id="center-text" slide:role="shape" slide:shape-type="text" x="400" y="250" width="160" height="84">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:800;color:#111;line-height:1.3;text-align:center;">今年必须从交付升级为增长服务</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("connector_crosses_text", codes)

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
        self.assertGreaterEqual(result["distinct_visual_recipe_family_count"], 5)

    def test_style_preset_catalog_has_36_complete_entries(self) -> None:
        catalog = svg_preflight.STYLE_PRESET_CATALOG
        self.assertEqual(len(catalog), 36)
        group_counts: dict[str, int] = {}
        tokens = set()
        for style_id, preset in catalog.items():
            self.assertEqual(style_id, preset["style_id"])
            self.assertIn(preset["group"], {"Restrained", "Balanced", "Bold"})
            group_counts[preset["group"]] = group_counts.get(preset["group"], 0) + 1
            self.assertTrue(preset.get("display_name"))
            self.assertTrue(preset.get("source_token"))
            tokens.add(preset["source_token"])
            self.assertIn("palette", preset)
            self.assertRegex(preset["palette"]["background"], r"^#[0-9A-Fa-f]{6}$")
            self.assertRegex(preset["palette"]["text"], r"^#[0-9A-Fa-f]{6}$")
            self.assertRegex(preset["palette"]["accent"], r"^#[0-9A-Fa-f]{6}$")
            self.assertIn("shape_language", preset)
            self.assertIn("density", preset)
            self.assertIn("slide_translation", preset)
            self.assertIn("quality_oracle", preset)
        self.assertEqual(group_counts, {"Restrained": 10, "Balanced": 15, "Bold": 11})
        self.assertEqual(len(tokens), 36)
        self.assertIn("data_journalism_editorial", catalog)

    def test_chart_type_contracts_are_runtime_catalog_source(self) -> None:
        registry = read_json(PUBLIC_RECIPE_REGISTRY_PATH)
        contracts = registry.get("chart_type_contracts")
        self.assertIsInstance(contracts, dict)
        assert isinstance(contracts, dict)
        self.assertEqual(set(contracts), set(svg_preflight.CHART_TYPE_CONTRACTS))
        for chart_type, contract in contracts.items():
            self.assertIsInstance(chart_type, str)
            self.assertIsInstance(contract, dict)
            assert isinstance(contract, dict)
            recommended_recipe = contract.get("recommended_visual_recipe")
            if recommended_recipe:
                self.assertIn(recommended_recipe, svg_preflight.VISUAL_RECIPE_CATALOG)
            minimum_keys = [key for key in contract if key.startswith("min_")]
            self.assertTrue(minimum_keys)
            for key in minimum_keys:
                self.assertIsInstance(contract[key], int)
                self.assertGreater(contract[key], 0)

    def test_lint_plan_reports_unknown_chart_type(self) -> None:
        plan = single_slide_plan(
            "infographic_scorecard",
            ["typography", "micro_chart"],
            chart_type="spider_radar",
        )
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_unknown_chart_type", issue_codes(result))

    def test_lint_plan_respects_explicit_empty_chart_type(self) -> None:
        plan = single_slide_plan(
            "geometric_composition",
            ["geometric_shape", "path"],
            chart_type="",
            reference_asset={"source": "ppt-master", "asset_id": "chart.agenda_list"},
        )
        result = svg_preflight.lint_plan(plan)
        self.assertNotIn("plan_unknown_chart_type", issue_codes(result))

    def test_public_recipe_registry_is_runtime_catalog_source(self) -> None:
        registry = read_json(PUBLIC_RECIPE_REGISTRY_PATH)
        recipes = registry.get("recipes")
        self.assertIsInstance(recipes, dict)
        assert isinstance(recipes, dict)
        self.assertEqual(set(recipes), set(svg_preflight.VISUAL_RECIPE_CATALOG))
        for recipe_id, recipe in recipes.items():
            self.assertIsInstance(recipe_id, str)
            self.assertIsInstance(recipe, dict)
            assert isinstance(recipe, dict)
            self.assertNotIn(".", recipe_id)
            self.assertEqual(recipe_id, recipe_id.lower())
            self.assertIn("family", recipe)
            primitives = svg_preflight.normalize_primitives(recipe.get("required_primitives"))
            effects = svg_preflight.normalize_effects(recipe.get("required_effects"))
            self.assertTrue(primitives)
            self.assertFalse(primitives - svg_preflight.VALID_VISUAL_PRIMITIVES)
            self.assertFalse(effects - set(svg_preflight.SVG_EFFECT_CATALOG))
            self.assertEqual(primitives, svg_preflight.VISUAL_RECIPE_CATALOG[recipe_id]["required_primitives"])

    def test_public_seed_registry_is_runtime_catalog_source(self) -> None:
        registry = read_json(PUBLIC_SEED_REGISTRY_PATH)
        seeds = registry.get("seeds")
        self.assertIsInstance(seeds, dict)
        assert isinstance(seeds, dict)
        self.assertEqual(len(seeds), 16)
        self.assertEqual(set(seeds), set(svg_preflight.SVG_SEED_CATALOG))
        self.assertEqual({seed["visual_recipe"] for seed in svg_preflight.SVG_SEED_CATALOG.values()}, set(svg_preflight.VISUAL_RECIPE_CATALOG))
        for seed_id, seed in seeds.items():
            self.assertEqual(seed_id, seed_id.lower())
            self.assertIn(seed.get("visual_recipe"), svg_preflight.VISUAL_RECIPE_CATALOG)
            self.assertIsInstance(seed.get("layout_boxes"), list)
            self.assertTrue(seed.get("layout_boxes"))
            self.assertIsInstance(seed.get("content_budget"), dict)
            self.assertIsInstance(seed.get("default_text_capacity"), dict)
            self.assertIn("footer", seed.get("reserved_bands", {}))
            self.assertIsInstance(seed.get("layout_skeleton"), dict)
            self.assertTrue(seed["layout_skeleton"].get("id"))
            self.assertIsInstance(seed["layout_skeleton"].get("locked_roles"), list)
            self.assertIsInstance(seed.get("text_budget_by_role"), dict)
            self.assertTrue(seed["text_budget_by_role"])
            self.assertIsInstance(seed.get("footer_safe_zone"), dict)
            self.assertIn("allowed_roles", seed["footer_safe_zone"])
            self.assertIsInstance(seed.get("vertical_text_policy"), dict)
            self.assertIn(seed["vertical_text_policy"].get("mode"), {"deny", "allow", "restricted"})
            primitives = svg_preflight.normalize_primitives(seed.get("required_primitives"))
            self.assertTrue(primitives)
            self.assertFalse(primitives - svg_preflight.VALID_VISUAL_PRIMITIVES)

    def test_private_recipe_manifest_catalog_has_valid_route_scoped_schema(self) -> None:
        route = read_json(ROUTE_MANIFEST_PATH)
        manifest = private_recipe_manifest()
        recipes = manifest.get("recipes")
        self.assertIsInstance(recipes, dict)
        assert isinstance(recipes, dict)
        private_ids = set(recipes)

        self.assertEqual(len(private_ids), 7)
        allowed_ids = route.get("allowed_private_recipe_ids")
        if allowed_ids is not None:
            self.assertEqual(private_ids, set(allowed_ids))
        else:
            self.assertEqual(route.get("allowed_private_recipe_source"), "private_recipe_manifest_keys")
        self.assertFalse(private_ids & set(svg_preflight.VISUAL_RECIPE_CATALOG))

        for recipe_id, recipe in recipes.items():
            self.assertIsInstance(recipe_id, str)
            self.assertIsInstance(recipe, dict)
            assert isinstance(recipe, dict)
            self.assertIn(recipe.get("base_recipe"), svg_preflight.VISUAL_RECIPE_CATALOG)
            primitives = svg_preflight.normalize_primitives(recipe.get("required_primitives"))
            effects = svg_preflight.normalize_effects(recipe.get("required_effects"))
            self.assertTrue(primitives)
            self.assertTrue(effects)
            self.assertFalse(primitives - svg_preflight.VALID_VISUAL_PRIMITIVES)
            self.assertFalse(effects - set(svg_preflight.SVG_EFFECT_CATALOG))

        context = private_context()
        self.assertEqual(set(context["private_recipe_catalog"]), private_ids)

    def test_route_private_fails_closed_without_manifest_or_selection(self) -> None:
        public_result = svg_preflight.lint_plan(private_route_plan(["path", "annotation"]))
        self.assertIn("private_route_not_allowed", issue_codes(public_result))

        manifest_only_result = svg_preflight.lint_plan(
            private_route_plan(["path", "annotation"]),
            context=private_context(),
        )
        self.assertIn("private_route_selection_missing", issue_codes(manifest_only_result))

    def test_route_private_rejects_minimal_selection_sidecar(self) -> None:
        recipe_id = private_recipe_ids()[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "minimal-selection.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "route_id": "create-svg",
                        "selections": [{"page": 1, "private_recipe_id": recipe_id}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(svg_preflight.SvgPreflightError) as raised:
                private_context(path)
        self.assertIn("private_route_manifest_invalid", str(raised.exception))

    def test_lint_plan_rejects_exact_private_recipe_id_in_public_plan(self) -> None:
        recipe_id = private_recipe_ids()[0]
        context = private_context()
        plan = private_route_plan_for_context(
            context,
            recipe_id,
            visual_recipe=recipe_id,
        )
        result = svg_preflight.lint_plan(plan, context=context)
        self.assertIn("private_recipe_exact_id_in_plan", issue_codes(result))

    def test_lint_files_rejects_route_private_field_spoofing_without_source_primitives(self) -> None:
        recipe_id = private_recipe_ids()[0]
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:32px;font-weight:800;color:#111827;">Title</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            selection_path = write_recipe_selection(tmp, recipe_id)
            context = private_context(selection_path)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan_path.write_text(json.dumps(private_route_plan_for_context(context, recipe_id)), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path), context=context)
        self.assertIn("private_recipe_required_primitives_not_found", plan_issue_codes(result))

    def test_lint_files_rejects_hidden_or_tiny_private_required_primitive(self) -> None:
        recipe_id = private_recipe_with_primitive("path")
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <defs>
            <linearGradient id="private-gradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#0ea5e9" />
              <stop offset="100%" stop-color="#f43f5e" />
            </linearGradient>
          </defs>
          <rect id="gradient-field" slide:role="shape" x="0" y="0" width="960" height="540" fill="url(#private-gradient)" />
          <path id="route-path-hidden" slide:role="shape" display="none" d="M120 360 C260 240 460 420 720 180" fill="none" stroke="#111827" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            selection_path = write_recipe_selection(tmp, recipe_id)
            context = private_context(selection_path)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan_path.write_text(json.dumps(private_route_plan_for_context(context, recipe_id)), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path), context=context)
        codes = plan_issue_codes(result)
        self.assertIn("private_recipe_required_primitive_not_visible", codes)
        self.assertIn("private_recipe_required_primitive_too_small", codes)

    def test_lint_plan_rejects_private_route_fallback_and_exemption_fields(self) -> None:
        recipe_id = private_recipe_ids()[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            selection_path = write_recipe_selection(Path(tmpdir), recipe_id)
            context = private_context(selection_path)
            plan = private_route_plan_for_context(
                context,
                recipe_id,
                fallback_policy="safe_rewrite_allowed",
                exemption_policy="allow_preflight_exemption",
            )
            result = svg_preflight.lint_plan(plan, context=context)
        codes = issue_codes(result)
        self.assertIn("private_recipe_fallback_not_allowed", codes)
        self.assertIn("private_recipe_exemption_not_allowed", codes)

    def test_public_redaction_removes_private_recipe_ids_and_private_enums(self) -> None:
        context = private_context()
        private_ids = private_recipe_ids()
        raw = {
            "issue": {
                "message": private_ids[0],
                "hint": "Use one of: " + ", ".join(private_ids),
            }
        }
        redacted = svg_preflight.redact_private_metadata(raw, context)
        encoded = json.dumps(redacted)
        for recipe_id in private_ids:
            self.assertNotIn(recipe_id, encoded)
        self.assertIn("Use one of: [public catalog]", encoded)

    def test_public_main_redacts_private_manifest_errors(self) -> None:
        recipe_id = private_recipe_ids()[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            selection_path = write_recipe_selection(tmp, recipe_id)
            context = private_context(selection_path)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan_path.write_text(
                json.dumps(private_route_plan_for_context(context, recipe_id, visual_recipe=recipe_id)),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = svg_preflight.main(
                    [
                        "--route-manifest",
                        str(ROUTE_MANIFEST_PATH),
                        "--recipe-selection",
                        str(selection_path),
                        "--plan",
                        str(plan_path),
                        str(svg_path),
                    ]
                )
        self.assertEqual(exit_code, 1)
        output = stdout.getvalue()
        for private_id in private_recipe_ids():
            self.assertNotIn(private_id, output)
        self.assertNotIn("Use one of: " + ", ".join(private_recipe_ids()), output)

    def test_private_docs_lint_reports_public_private_id_leak(self) -> None:
        recipe_id = private_recipe_ids()[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            public_doc = repo_root / "README.md"
            public_doc.write_text(f"Do not publish {recipe_id} in public docs.", encoding="utf-8")
            issues = svg_private_docs_lint.lint_file(
                public_doc,
                repo_root,
                [recipe_id],
                [],
                [],
            )
        self.assertEqual([issue.code for issue in issues], ["private_recipe_id_leak"])

    def test_private_docs_lint_output_redacts_leaked_token(self) -> None:
        recipe_id = private_recipe_ids()[0]
        issue = svg_private_docs_lint.Issue("README.md", 1, 1, "private_recipe_id_leak", recipe_id)
        encoded = json.dumps(svg_private_docs_lint.issue_to_dict(issue))
        self.assertNotIn(recipe_id, encoded)
        self.assertIn("token_hash", encoded)

    def test_lint_plan_reports_unknown_style_preset(self) -> None:
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
        self.assertIn("plan_style_preset_unknown", codes)

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

    def test_lint_plan_accepts_declared_seed_controls(self) -> None:
        result = svg_preflight.lint_plan(single_slide_plan())
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_plan_reports_unknown_seed(self) -> None:
        plan = single_slide_plan(seed_id="missing_seed")
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_unknown_seed", issue_codes(result))

    def test_lint_plan_reports_seed_visual_recipe_mismatch(self) -> None:
        plan = single_slide_plan(seed_id="cover_hero_statement")
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_seed_visual_recipe_mismatch", issue_codes(result))

    def test_lint_plan_reports_missing_layout_boxes(self) -> None:
        plan = single_slide_plan(layout_boxes=[])
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_missing_layout_boxes", issue_codes(result))
        self.assertEqual(issue_levels(result, "plan_missing_layout_boxes"), ["warning"])
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_plan_can_promote_seed_controls_to_errors_with_strict_profile(self) -> None:
        plan = single_slide_plan(layout_boxes=[])
        plan["validation_profile"] = {"mode": "svglide_project_pipeline", "strict": True}
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_missing_layout_boxes", issue_codes(result))
        self.assertEqual(issue_levels(result, "plan_missing_layout_boxes"), ["error"])

    def test_lint_plan_reports_missing_seed_skeleton_controls(self) -> None:
        plan = single_slide_plan()
        slide = plan["slides"][0]
        assert isinstance(slide, dict)
        slide.pop("layout_skeleton_id", None)
        slide.pop("layout_skeleton", None)
        slide.pop("text_budget_by_role", None)
        slide.pop("footer_safe_zone", None)
        slide.pop("vertical_text_policy", None)
        result = svg_preflight.lint_plan(plan)
        codes = issue_codes(result)
        self.assertIn("plan_seed_layout_skeleton_missing", codes)
        self.assertIn("plan_missing_text_budget_by_role", codes)
        self.assertIn("plan_missing_footer_safe_zone", codes)
        self.assertIn("plan_vertical_text_policy_missing", codes)

    def test_lint_plan_reports_seed_layout_skeleton_drift(self) -> None:
        plan = single_slide_plan()
        slide = plan["slides"][0]
        assert isinstance(slide, dict)
        layout_boxes = json.loads(json.dumps(slide["layout_boxes"]))
        layout_boxes[0]["x"] = layout_boxes[0]["x"] + 120
        slide["layout_boxes"] = layout_boxes
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_seed_layout_skeleton_drift", issue_codes(result))

    def test_lint_plan_reports_missing_duplicate_role_seed_box(self) -> None:
        plan = single_slide_plan("geometric_composition")
        slide = plan["slides"][0]
        assert isinstance(slide, dict)
        slide["layout_boxes"] = [box for box in slide["layout_boxes"] if isinstance(box, dict) and box.get("id") != "right-panel"]
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_seed_layout_skeleton_drift", issue_codes(result))

    def test_lint_plan_reports_role_text_budget_exceeded(self) -> None:
        plan = single_slide_plan(
            body="这是一段明显超过局部正文预算的长文本，用来验证 role 级别预算不会被总预算掩盖。",
            text_budget_by_role={
                "body": {"max_chars": 8, "max_lines": 1, "max_boxes": 3, "min_font_px": 12},
                "title": {"max_chars": 36, "max_lines": 2, "max_boxes": 1, "min_font_px": 22},
                "footer": {"max_chars": 34, "max_lines": 1, "max_boxes": 1, "min_font_px": 9},
            },
        )
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_text_role_budget_exceeded", issue_codes(result))

    def test_lint_plan_reports_title_body_footer_budget_exceeded(self) -> None:
        plan = single_slide_plan(
            title="This title is too long",
            body="This body has too much detail for the selected seed.",
            footer="Footer source note is also too long",
            content_budget={"max_visible_chars": 30, "title": 6, "body": 10, "footer": 8},
        )
        result = svg_preflight.lint_plan(plan)
        codes = issue_codes(result)
        self.assertIn("plan_content_budget_exceeded", codes)
        self.assertIn("plan_title_capacity_exceeded", codes)
        self.assertIn("plan_body_capacity_exceeded", codes)
        self.assertIn("plan_footer_capacity_exceeded", codes)

    def test_lint_plan_rejects_seed_budget_loosened_by_plan(self) -> None:
        plan = single_slide_plan(content_budget={"max_visible_chars": 9999, "title": 999, "body": 999, "footer": 999})
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_seed_content_budget_loosened", issue_codes(result))

    def test_lint_plan_reports_layout_box_missing_coordinates(self) -> None:
        plan = single_slide_plan(layout_boxes=[{"role": "title", "width": 500, "height": 60}])
        result = svg_preflight.lint_plan(plan)
        self.assertIn("plan_layout_box_invalid", issue_codes(result))

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
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("plan_svg_effect_requires_safe_fallback", codes)

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

    def test_lint_files_reports_source_role_budget_and_vertical_text(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="46" width="640" height="52">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Route</div>
          </foreignObject>
          <foreignObject id="body-copy" slide:role="shape" slide:shape-type="text" x="68" y="214" width="120" height="84">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;color:#111827;">正文超出局部预算</div>
          </foreignObject>
          <foreignObject id="body-vertical" slide:role="shape" slide:shape-type="text" x="772" y="214" width="120" height="84">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;writing-mode:vertical-rl;color:#111827;">竖排正文</div>
          </foreignObject>
          <foreignObject id="callout-note" slide:role="shape" slide:shape-type="text" x="150" y="382" width="660" height="48">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:13px;color:#334155;">Note</div>
          </foreignObject>
          <path id="trend-flow-path" slide:role="shape" d="M210 260 C360 190 520 330 750 260" fill="none" stroke="#2563eb" />
          <line id="annotation-line" slide:role="shape" x1="210" y1="300" x2="750" y2="300" stroke="#2563eb" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan(
                text_budget_by_role={
                    **seed_fields("process_pipeline")["text_budget_by_role"],
                    "body": {"max_chars": 4, "max_lines": 2, "max_boxes": 3, "min_font_px": 12},
                },
                svg_files=[{"page": 1, "path": "page-001.svg"}],
            )
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = plan_issue_codes(result)
        self.assertIn("plan_source_role_text_budget_exceeded", codes)
        self.assertIn("vertical_text_disallowed_role", codes)

    def test_lint_files_reports_neutral_text_id_against_role_budget(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="alpha" slide:role="shape" slide:shape-type="text" x="300" y="184" width="220" height="64">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;color:#111827;">中性 ID 也不能绕过正文预算</div>
          </foreignObject>
          <path id="trend-flow-path" slide:role="shape" d="M210 260 C360 190 520 330 750 260" fill="none" stroke="#2563eb" />
          <line id="annotation-line" slide:role="shape" x1="210" y1="300" x2="750" y2="300" stroke="#2563eb" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan(
                text_budget_by_role={
                    **seed_fields("process_pipeline")["text_budget_by_role"],
                    "body": {"max_chars": 4, "max_lines": 2, "max_boxes": 4, "min_font_px": 12},
                },
                svg_files=[{"page": 1, "path": "page-001.svg"}],
            )
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_source_role_text_budget_exceeded", plan_issue_codes(result))

    def test_lint_files_reports_footer_safe_zone_intrusion(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="46" width="640" height="52">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Route</div>
          </foreignObject>
          <foreignObject id="body-copy" slide:role="shape" slide:shape-type="text" x="68" y="492" width="400" height="28">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;color:#111827;">Body should stay above the bottom band.</div>
          </foreignObject>
          <path id="trend-flow-path" slide:role="shape" d="M210 260 C360 190 520 330 750 260" fill="none" stroke="#2563eb" />
          <line id="annotation-line" slide:role="shape" x1="210" y1="300" x2="750" y2="300" stroke="#2563eb" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan(svg_files=[{"page": 1, "path": "page-001.svg"}])
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("footer_safe_zone_intrusion", plan_issue_codes(result))

    def test_lint_svg_reports_label_text_overlap(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="body-copy" slide:role="shape" slide:shape-type="text" x="320" y="180" width="220" height="60">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;color:#111827;">Readable body copy</div>
          </foreignObject>
          <rect id="label-chip" slide:role="shape" x="420" y="190" width="120" height="30" fill="#ef4444" />
        </svg>
        """
        result = svg_preflight.lint_svg(with_contract(svg))
        self.assertIn("label_text_overlap", issue_codes(result))

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
        self.assertIn("plan_missing_visual_recipe", codes)
        self.assertIn("plan_renderer_repetition", codes)
        self.assertIn("plan_renderer_diversity_low", codes)
        self.assertIn("plan_visual_recipe_diversity_low", codes)
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
        self.assertIn("plan_missing_layout_family", codes)
        self.assertIn("plan_missing_required_primitives", codes)
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
                **style_plan_fields(),
                "svg_files": [{"page": 1, "path": "page-001.svg"}],
                "slides": [
                    {
                        "page": 1,
                        "renderer_id": "route_story",
                        "density": "medium",
                        **recipe_fields("path_flow", ["path", "annotation"]),
                        "asset_contract": {
                            "source_type": "procedural",
                            "license": "original generated asset",
                            "local_path": "@./assets/hero.jpg",
                            "usage_page": 1,
                            "generated_by": "unit test",
                        },
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_files_reports_chart_type_contract_not_met_by_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = single_slide_plan(
                "infographic_scorecard",
                ["typography", "micro_chart"],
                chart_type="bar_chart",
            )
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_chart_type_contract_not_met", plan_issue_codes(result))

    def test_lint_files_reports_svg_input_count_mismatch_with_plan_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            plan = single_slide_plan()
            second_slide = dict(plan["slides"][0])
            second_slide["page"] = 2
            second_slide["title"] = "Route 2"
            plan["page_count"] = 2
            plan["slides"] = [plan["slides"][0], second_slide]
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}, {"page": 2, "path": "page-002.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))

        self.assertIn("plan_svg_file_count_mismatch", plan_issue_codes(result))

    def test_lint_files_rejects_ai_capital_p07_p08_archetype_degradation(self) -> None:
        plain_card_svg = with_contract(
            """
            <svg xmlns="http://www.w3.org/2000/svg"
                 xmlns:slide="https://slides.bytedance.com/ns"
                 slide:role="slide"
                 width="960" height="540" viewBox="0 0 960 540">
              <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#111827" />
              <rect slide:role="shape" x="80" y="150" width="260" height="170" fill="#1f2937" />
              <rect slide:role="shape" x="360" y="150" width="260" height="170" fill="#1f2937" />
              <foreignObject slide:role="shape" slide:shape-type="text" x="80" y="72" width="560" height="48">
                <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;color:#f9fafb;">AI capital card summary</div>
              </foreignObject>
              <foreignObject slide:role="shape" slide:shape-type="text" x="100" y="182" width="220" height="60">
                <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:16px;color:#e5e7eb;">Generic card, not the declared chart geometry.</div>
              </foreignObject>
              <foreignObject slide:role="shape" slide:shape-type="text" x="380" y="182" width="220" height="60">
                <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:16px;color:#e5e7eb;">Generic card, not the declared chart geometry.</div>
              </foreignObject>
            </svg>
            """
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            page7 = tmp / "page-007.svg"
            page8 = tmp / "page-008.svg"
            plan_path = tmp / "slide_plan.json"
            page7.write_text(plain_card_svg, encoding="utf-8")
            page8.write_text(plain_card_svg, encoding="utf-8")
            bubble_plan = single_slide_plan(
                "geometric_composition",
                list(svg_preflight.VISUAL_RECIPE_CATALOG["geometric_composition"]["required_primitives"]),
                chart_type="bubble_chart",
                ppt_master_reference_assets=[{"asset_id": "chart.bubble_chart", "source": "ppt-master"}],
            )
            donut_plan = single_slide_plan(
                "infographic_scorecard",
                ["typography", "micro_chart"],
                chart_type="donut_chart",
                ppt_master_reference_assets=[{"asset_id": "chart.donut_chart", "source": "ppt-master"}],
            )
            slide7 = bubble_plan["slides"][0]
            slide8 = donut_plan["slides"][0]
            slide7["page"] = 7
            slide8["page"] = 8
            plan = {
                "output_mode": "svglide-svg",
                "page_count": 2,
                **style_plan_fields(),
                "slides": [slide7, slide8],
                "svg_files": [{"page": 7, "path": "page-007.svg"}, {"page": 8, "path": "page-008.svg"}],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(page7), str(page8)], str(plan_path))

        messages = [
            str(issue.get("message"))
            for issue in result.get("plan", {}).get("issues", [])
            if isinstance(issue, dict) and issue.get("code") == "plan_chart_type_contract_not_met"
        ]
        self.assertGreaterEqual(len(messages), 2)
        self.assertTrue(any("round_nodes 0 < 3" in message for message in messages))
        self.assertTrue(any("round_nodes 0 < 2" in message for message in messages))

    def test_lint_files_accepts_chart_type_contract_geometry(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="42" width="520" height="42">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:26px;font-weight:800;color:#111827;line-height:1.1;">Market concentration</div>
          </foreignObject>
          <foreignObject id="body-takeaway" slide:role="shape" slide:shape-type="text" x="66" y="94" width="620" height="30">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:15px;font-weight:700;color:#334155;line-height:1.15;">Top cohorts drive the majority of adoption</div>
          </foreignObject>
          <rect id="chart-frame" slide:role="shape" x="86" y="154" width="650" height="296" fill="#ffffff" stroke="#cbd5e1" />
          <rect id="bar-a" slide:role="shape" x="120" y="214" width="224" height="24" fill="#e63946" />
          <rect id="bar-b" slide:role="shape" x="120" y="266" width="176" height="24" fill="#f4a261" />
          <rect id="bar-c" slide:role="shape" x="120" y="318" width="132" height="24" fill="#52b788" />
          <foreignObject id="annotation" slide:role="shape" slide:shape-type="text" x="748" y="168" width="150" height="58">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:13px;font-weight:700;color:#334155;line-height:1.2;">Visible bars prove the declared type.</div>
          </foreignObject>
          <foreignObject id="footer" slide:role="shape" slide:shape-type="text" x="64" y="500" width="300" height="18">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:10px;color:#64748b;line-height:1.1;">Source: unit test</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan(
                "infographic_scorecard",
                ["typography", "micro_chart"],
                chart_type="bar_chart",
            )
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertNotIn("plan_chart_type_contract_not_met", plan_issue_codes(result))
        self.assertEqual(result["summary"]["error_count"], 0)

    def test_lint_files_reports_footer_reserved_band_violation(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="46" width="500" height="46">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Route</div>
          </foreignObject>
          <foreignObject id="body-input" slide:role="shape" slide:shape-type="text" x="76" y="226" width="96" height="30">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:700;color:#111827;text-align:center;">Input</div>
          </foreignObject>
          <foreignObject id="body-output" slide:role="shape" slide:shape-type="text" x="780" y="226" width="96" height="30">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:14px;font-weight:700;color:#111827;text-align:center;">Output</div>
          </foreignObject>
          <foreignObject id="callout-note" slide:role="shape" slide:shape-type="text" x="170" y="392" width="420" height="28">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:13px;font-weight:600;color:#334155;">Pipeline note</div>
          </foreignObject>
          <path id="flow-path" slide:role="shape" d="M80 270 C220 190 420 340 620 220" fill="none" stroke="#2563eb" />
          <line id="annotation-line" slide:role="shape" x1="620" y1="220" x2="720" y2="190" stroke="#111827" />
          <foreignObject id="footer-source" slide:role="shape" slide:shape-type="text" x="64" y="462" width="520" height="24">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:12px;font-weight:500;color:#374151;">Source: unit test</div>
          </foreignObject>
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan()
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_footer_reserved_band_violation", plan_issue_codes(result))

    def test_lint_files_reports_body_text_inside_footer_band(self) -> None:
        svg = VALID_SVG.replace(
            "</svg>",
            """
  <foreignObject id="body-bottom-copy" slide:role="shape" slide:shape-type="text" x="80" y="500" width="260" height="20">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:12px;font-weight:600;color:#111827;">Body copy should stay with the main content</div>
  </foreignObject>
</svg>
""",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(svg, encoding="utf-8")
            plan = single_slide_plan()
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_footer_reserved_band_violation", plan_issue_codes(result))

    def test_lint_files_reports_source_text_box_count_exceeded(self) -> None:
        svg = VALID_SVG.replace(
            "</svg>",
            """
  <foreignObject id="extra" slide:role="shape" slide:shape-type="text" x="300" y="320" width="120" height="24">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:12px;font-weight:600;color:#111827;">Extra</div>
  </foreignObject>
</svg>
""",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(svg, encoding="utf-8")
            plan = single_slide_plan(content_budget={"max_text_boxes": 4})
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_source_text_box_count_exceeded", plan_issue_codes(result))

    def test_lint_files_reports_source_text_box_count_below_seed_minimum(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="46" width="500" height="46">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:28px;font-weight:800;color:#111827;">Route</div>
          </foreignObject>
          <path id="flow-path" slide:role="shape" d="M210 260 C360 190 520 330 750 260" fill="none" stroke="#2563eb" />
        </svg>
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(with_contract(svg), encoding="utf-8")
            plan = single_slide_plan()
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_source_text_box_count_below_seed_minimum", plan_issue_codes(result))

    def test_lint_files_reports_text_box_outside_seed_layout_box(self) -> None:
        svg = VALID_SVG.replace('id="title" slide:role="shape" slide:shape-type="text" x="64" y="46"', 'id="title" slide:role="shape" slide:shape-type="text" x="64" y="130"')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            svg_path = tmp / "page-001.svg"
            plan_path = tmp / "slide_plan.json"
            svg_path.write_text(svg, encoding="utf-8")
            plan = single_slide_plan()
            plan["svg_files"] = [{"page": 1, "path": "page-001.svg"}]
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        self.assertIn("plan_text_box_outside_seed_layout_box", plan_issue_codes(result))

    def test_lint_files_requires_plan_for_create_svg_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "page-001.svg"
            svg_path.write_text(VALID_SVG, encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], context=private_context())
        self.assertIn("plan_required_for_create_svg_route", plan_issue_codes(result))

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
                    "source_policy": "Use prompt-provided content only."
                  }]
                }
                """,
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
                        "density": "medium",
                        **recipe_fields("path_flow", ["path", "annotation"]),
                        "asset_contract": "none_required",
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
                        "density": "medium",
                        **recipe_fields("path_flow", ["path", "annotation"]),
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
                        "density": "medium",
                        **recipe_fields("path_flow", ["path", "annotation"]),
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
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            result = svg_preflight.lint_files([str(svg_path)], str(plan_path))
        codes = [issue["code"] for issue in result["plan"]["issues"]]
        self.assertIn("plan_asset_contract_missing_metadata", codes)
        self.assertEqual(result["summary"]["error_count"], 0)

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
