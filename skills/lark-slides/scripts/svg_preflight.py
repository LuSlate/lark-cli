#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import base64
import binascii
import hashlib
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SLIDE_NS = "https://slides.bytedance.com/ns"
XLINK_NS = "http://www.w3.org/1999/xlink"
SVG_NS = "http://www.w3.org/2000/svg"
SVG_CONTRACT_VERSION = "svglide-authoring-contract/v1"
SVG_CHART_MARKER_VERSION = "svglide-chart-inline/v1"
SVG_CHART_FORMAT = "svglide-chart-spec-v1"
SVG_CHART_SPEC_VERSION = "svglide-chart-spec/v1"
SVG_CHART_ENCODING = "base64url-json"
CANVAS_WIDTH = 960.0
CANVAS_HEIGHT = 540.0
SAFE_AREA = {"x": 48.0, "y": 40.0, "width": 864.0, "height": 460.0}
BADGE_HEADLINE_MIN_GAP = 8.0
TITLE_SURFACE_MIN_GAP = 24.0
DECORATIVE_LINE_HEADLINE_MIN_GAP = 16.0
TEXT_CONTAINER_TOLERANCE = 2.0

NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?:px)?$")
PATH_NUMBER_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SHA256_HASH_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
FONT_SHORTHAND_RE = re.compile(r"(^|;)\s*font\s*:", re.IGNORECASE)
STYLE_IMAGE_OPACITY_RE = re.compile(r"(^|;)\s*opacity\s*:", re.IGNORECASE)
STYLE_STROKE_WIDTH_RE = re.compile(r"(^|;)\s*stroke-width\s*:", re.IGNORECASE)
STYLE_STROKE_DASHARRAY_RE = re.compile(r"(^|;)\s*stroke-dasharray\s*:", re.IGNORECASE)
RGB_RE = re.compile(r"rgba?\(([^)]+)\)", re.IGNORECASE)
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([0-9.]+)px?", re.IGNORECASE)
KEY_PATH_RE = re.compile(r"(critical|flow|journey|loop|main|path|rail|route|spine|timeline)", re.IGNORECASE)
PATH_LIKE_RE = re.compile(
    r"(^|\s)(/Users/|/tmp/|/private/|\.{1,2}/|[A-Za-z]:\\|[A-Za-z0-9._-]+\.(?:json|md|py|go|svg|png|jpe?g))",
    re.IGNORECASE,
)
TOOL_LEAK_RE = re.compile(r"\b(lark-cli|svg_preflight|beautiful-feishu-whiteboard|source_token|source prompt|tool name|file path|prompt:)\b", re.IGNORECASE)

SUPPORTED_SHAPES = {"rect", "ellipse", "circle", "line", "path", "foreignObject"}
RENDERABLE_TAGS = SUPPORTED_SHAPES | {"image", "text", "polygon", "polyline"}
IGNORED_SUBTREES = {"defs", "style"}

def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _normalized_public_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def load_visual_recipe_catalog() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parent.parent / "references" / "svg-recipes.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"failed to load public SVG recipe registry: {path}: {error}") from error
    recipes = data.get("recipes") if isinstance(data, dict) else None
    if not isinstance(recipes, dict):
        raise RuntimeError(f"invalid public SVG recipe registry: {path}: missing recipes object")
    out: dict[str, dict[str, Any]] = {}
    for recipe_id, raw_recipe in recipes.items():
        if not isinstance(raw_recipe, dict):
            raise RuntimeError(f"invalid public SVG recipe registry: {recipe_id} must be an object")
        normalized_id = _normalized_public_id(recipe_id)
        if not normalized_id:
            raise RuntimeError("invalid public SVG recipe registry: recipe id must not be empty")
        out[normalized_id] = {
            "family": str(raw_recipe.get("family") or normalized_id).strip() or normalized_id,
            "required_primitives": _string_set(raw_recipe.get("required_primitives")),
            "required_effects": _string_set(raw_recipe.get("required_effects")),
        }
        if "minimum_visible_area_ratio" in raw_recipe:
            out[normalized_id]["minimum_visible_area_ratio"] = raw_recipe.get("minimum_visible_area_ratio")
    return out


VISUAL_RECIPE_CATALOG: dict[str, dict[str, Any]] = load_visual_recipe_catalog()


def load_svg_seed_catalog() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parent.parent / "references" / "svg-seeds.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"failed to load SVG seed registry: {path}: {error}") from error
    seeds = data.get("seeds") if isinstance(data, dict) else None
    if not isinstance(seeds, dict):
        raise RuntimeError(f"invalid SVG seed registry: {path}: missing seeds object")
    out: dict[str, dict[str, Any]] = {}
    for seed_id, raw_seed in seeds.items():
        if not isinstance(raw_seed, dict):
            raise RuntimeError(f"invalid SVG seed registry: {seed_id} must be an object")
        normalized_id = _normalized_public_id(seed_id)
        if not normalized_id:
            raise RuntimeError("invalid SVG seed registry: seed id must not be empty")
        capacity = raw_seed.get("default_text_capacity")
        layout_boxes = raw_seed.get("layout_boxes")
        required_primitives = _string_set(raw_seed.get("required_primitives"))
        out[normalized_id] = {
            "page_use": str(raw_seed.get("page_use") or "").strip(),
            "family": str(raw_seed.get("family") or normalized_id).strip() or normalized_id,
            "visual_recipe": _normalized_public_id(raw_seed.get("visual_recipe")),
            "layout_family": _normalized_public_id(raw_seed.get("layout_family")),
            "layout_boxes": layout_boxes if isinstance(layout_boxes, list) else [],
            "layout_skeleton": raw_seed.get("layout_skeleton") if isinstance(raw_seed.get("layout_skeleton"), dict) else {},
            "default_text_capacity": capacity if isinstance(capacity, dict) else {},
            "content_budget": raw_seed.get("content_budget") if isinstance(raw_seed.get("content_budget"), dict) else {},
            "text_budget_by_role": raw_seed.get("text_budget_by_role") if isinstance(raw_seed.get("text_budget_by_role"), dict) else {},
            "reserved_bands": raw_seed.get("reserved_bands") if isinstance(raw_seed.get("reserved_bands"), dict) else {},
            "footer_safe_zone": raw_seed.get("footer_safe_zone") if isinstance(raw_seed.get("footer_safe_zone"), dict) else {},
            "vertical_text_policy": raw_seed.get("vertical_text_policy") if isinstance(raw_seed.get("vertical_text_policy"), dict) else {},
            "required_primitives": required_primitives,
            "required_layout_box_roles": _string_set(raw_seed.get("required_layout_box_roles")),
            "quality_rules": raw_seed.get("quality_rules") if isinstance(raw_seed.get("quality_rules"), list) else [],
        }
    return out


SVG_SEED_CATALOG: dict[str, dict[str, Any]] = load_svg_seed_catalog()

PRIMITIVE_ALIASES = {
    "annotation_line": "annotation",
    "annotations": "annotation",
    "bar": "micro_chart",
    "bars": "micro_chart",
    "callout": "annotation",
    "callouts": "annotation",
    "card": "geometric_shape",
    "cards": "geometric_shape",
    "chart": "micro_chart",
    "charts": "micro_chart",
    "circle": "geometric_shape",
    "circles": "geometric_shape",
    "clip": "image_overlay",
    "clip_path": "image_overlay",
    "clipPath": "image_overlay",
    "dashboard_card": "dashboard",
    "data_callout": "annotation",
    "diagram": "geometric_shape",
    "ellipse": "geometric_shape",
    "ellipses": "geometric_shape",
    "flow": "flow",
    "glow": "spotlight",
    "grid": "texture",
    "highlight": "spotlight",
    "hotspot": "spotlight",
    "image": "image",
    "image_mask": "image_overlay",
    "image_overlay": "image_overlay",
    "line": "annotation",
    "lines": "annotation",
    "mask": "image_overlay",
    "metric": "micro_chart",
    "metrics": "micro_chart",
    "path": "path",
    "paths": "path",
    "rect": "geometric_shape",
    "rectangle": "geometric_shape",
    "shape": "geometric_shape",
    "shapes": "geometric_shape",
    "spotlight": "spotlight",
    "text": "typography",
    "texture": "texture",
    "typography": "typography",
    "ui": "dashboard",
    "wireframe": "dashboard",
}

SVG_EFFECT_CATALOG: dict[str, dict[str, Any]] = {
    "chart_geometry": {"safe": True},
    "connector_flow": {"safe": True},
    "filter": {"safe": False, "requires_fallback": True},
    "gradient": {"safe": True},
    "grid_geometry": {"safe": True},
    "image_opacity": {"safe": False, "requires_fallback": True},
    "image_overlay": {"safe": True},
    "mask_clip": {"safe": False, "requires_fallback": True},
    "path": {"safe": True},
    "pattern": {"safe": False, "requires_fallback": True},
    "spotlight": {"safe": True},
    "stroke_dasharray": {"safe": False, "requires_fallback": True},
    "symbol": {"safe": False, "requires_fallback": True},
    "texture": {"safe": True},
    "typography": {"safe": True},
    "watermark_text": {"safe": True},
}

EFFECT_ALIASES = {
    "bar": "chart_geometry",
    "bars": "chart_geometry",
    "chart": "chart_geometry",
    "chart_geometry": "chart_geometry",
    "clip": "mask_clip",
    "clip_path": "mask_clip",
    "clippath": "mask_clip",
    "connector": "connector_flow",
    "connector_flow": "connector_flow",
    "connectors": "connector_flow",
    "drop_shadow": "filter",
    "filter": "filter",
    "grid": "grid_geometry",
    "grid_geometry": "grid_geometry",
    "image_mask": "image_overlay",
    "image_opacity": "image_opacity",
    "image_overlay": "image_overlay",
    "lineargradient": "gradient",
    "linear_gradient": "gradient",
    "mask": "mask_clip",
    "mask_clip": "mask_clip",
    "path": "path",
    "pattern": "pattern",
    "radialgradient": "gradient",
    "radial_gradient": "gradient",
    "shadow": "filter",
    "spotlight": "spotlight",
    "stroke_dasharray": "stroke_dasharray",
    "symbol": "symbol",
    "texture": "texture",
    "typography": "typography",
    "watermark": "watermark_text",
    "watermark_text": "watermark_text",
}

VISIBLE_PLAN_TEXT_KEYS = [
    "title",
    "subtitle",
    "key_message",
    "takeaway",
    "visible_source_note",
    "speaker_intent",
    "visual_signature",
    "visual_intent",
    "visual_focal_point",
]
CAPACITY_PLAN_TEXT_KEYS = [
    "title",
    "subtitle",
    "headline",
    "kicker",
    "key_message",
    "takeaway",
    "body",
    "bullets",
    "callouts",
    "labels",
    "visible_source_note",
]
TEXT_LAYOUT_ROLE_RE = re.compile(r"(title|headline|body|copy|text|label|caption|note|source|footer|callout|chip|metric)", re.IGNORECASE)
TEXT_CLIP_RISK_RATIO = 0.85
CAPACITY_MAX_KEYS = {"max_visible_chars", "max_text_boxes", "title", "body", "footer"}
CAPACITY_MIN_KEYS = {"min_text_boxes"}
INTERNAL_INHERITED_HIDDEN_ATTR = "__svglide_inherited_hidden"
INTERNAL_INHERITED_CLIP_ATTR = "__svglide_inherited_clip"
VERTICAL_WRITING_MODE_RE = re.compile(r"\b(vertical-(?:rl|lr)|sideways-(?:rl|lr)|tb(?:-rl)?)\b", re.IGNORECASE)
ROTATED_TEXT_RE = re.compile(r"rotate\(\s*(?:90|270|-90)(?:deg)?(?:[\s,)]|$)", re.IGNORECASE)


def load_style_preset_catalog() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parent.parent / "references" / "style-presets.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    presets = data.get("presets") if isinstance(data, dict) else None
    if not isinstance(presets, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        raw_style_id = preset.get("style_id")
        style_id = re.sub(r"[^a-z0-9]+", "_", str(raw_style_id or "").strip().lower()).strip("_")
        if style_id:
            out[style_id] = preset
    return out


STYLE_PRESET_CATALOG = load_style_preset_catalog()
CREATE_SVG_ROUTE_ID = "create-svg"
ROUTE_PRIVATE_VISUAL_RECIPE = "route_private"
ROUTE_PRIVATE_RECIPE_REF = "create_svg_curated_recipe"
PUBLIC_REPORT_SCOPE = "public"
INTERNAL_REPORT_SCOPE = "internal"
PRIVATE_MANIFEST_EXPECTED_COUNT = 7
VALID_VISUAL_PRIMITIVES = set(PRIMITIVE_ALIASES.values()) | {
    "annotation",
    "brand_system",
    "dashboard",
    "flow",
    "geometric_shape",
    "gradient",
    "icon",
    "image",
    "image_overlay",
    "micro_chart",
    "path",
    "spotlight",
    "texture",
    "typography",
}


class SvgPreflightError(Exception):
    pass


def fail(message: str) -> None:
    raise SvgPreflightError(message)


def parse_args(argv: list[str]) -> dict[str, Any]:
    inputs: list[str] = []
    plan: str | None = None
    route_manifest: str | None = None
    recipe_selection: str | None = None
    report_scope = PUBLIC_REPORT_SCOPE
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--plan":
            if index + 1 >= len(argv):
                fail("--plan requires a slide_plan.json path")
            plan = argv[index + 1]
            index += 2
            continue
        if token == "--route-manifest":
            if index + 1 >= len(argv):
                fail("--route-manifest requires a route manifest path")
            route_manifest = argv[index + 1]
            index += 2
            continue
        if token == "--recipe-selection":
            if index + 1 >= len(argv):
                fail("--recipe-selection requires a route-private recipe selection sidecar path")
            recipe_selection = argv[index + 1]
            index += 2
            continue
        if token == "--report-scope":
            if index + 1 >= len(argv):
                fail("--report-scope requires public or internal")
            report_scope = argv[index + 1].strip().lower()
            if report_scope not in {PUBLIC_REPORT_SCOPE, INTERNAL_REPORT_SCOPE}:
                fail("--report-scope must be public or internal")
            index += 2
            continue
        if token in {"--input", "-i"}:
            if index + 1 >= len(argv):
                fail(f"{token} requires a file path")
            inputs.append(argv[index + 1])
            index += 2
            continue
        if token.startswith("--"):
            fail(f"unexpected argument: {token}")
        inputs.append(token)
        index += 1
    if not inputs:
        fail("at least one --input <svg-file> is required")
    return {
        "inputs": inputs,
        "plan": plan,
        "route_manifest": route_manifest,
        "recipe_selection": recipe_selection,
        "report_scope": report_scope,
    }


def manifest_error(code: str, message: str) -> None:
    fail(f"{code}: {message}")


def read_json_manifest(path: Path, invalid_code: str, missing_code: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        manifest_error(missing_code, "manifest not found")
    except OSError as error:
        manifest_error(missing_code, error.__class__.__name__)
    except json.JSONDecodeError as error:
        manifest_error(invalid_code, f"manifest is not valid JSON: {error}")
    if not isinstance(data, dict):
        manifest_error(invalid_code, "manifest root must be an object")
    return data


def resolve_manifest_path(path: str, base: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or base is None:
        return candidate
    return base / candidate


def default_preflight_context(report_scope: str = PUBLIC_REPORT_SCOPE) -> dict[str, Any]:
    return {
        "route_id": "",
        "recipe_catalog": VISUAL_RECIPE_CATALOG,
        "public_recipe_catalog": VISUAL_RECIPE_CATALOG,
        "seed_catalog": SVG_SEED_CATALOG,
        "private_recipe_catalog": {},
        "private_id_set": set(),
        "allow_private": False,
        "report_scope": report_scope,
        "route_manifest_path": "",
        "private_manifest_path": "",
        "recipe_selection_path": "",
        "recipe_selection": {},
    }


def validate_private_recipe_manifest(data: dict[str, Any], allowed_ids: set[str] | None = None) -> dict[str, dict[str, Any]]:
    recipes = data.get("recipes")
    if not isinstance(recipes, dict):
        manifest_error("private_route_manifest_invalid", "private recipe manifest must include a recipes object")

    private_ids = set(str(recipe_id) for recipe_id in recipes.keys())
    if len(private_ids) != PRIVATE_MANIFEST_EXPECTED_COUNT:
        manifest_error(
            "private_recipe_catalog_count_mismatch",
            "private recipe manifest must contain exactly 7 entries",
        )
    if allowed_ids is not None and private_ids != allowed_ids:
        manifest_error("private_recipe_catalog_count_mismatch", "private recipe manifest keys must exactly match route allowed_private_recipe_ids")
    public_collisions = sorted(private_ids & set(VISUAL_RECIPE_CATALOG))
    if public_collisions:
        manifest_error("private_recipe_public_id_collision", "private recipes must not collide with public recipe ids")

    validated: dict[str, dict[str, Any]] = {}
    for recipe_id, raw_recipe in recipes.items():
        if not isinstance(raw_recipe, dict):
            manifest_error("private_route_manifest_invalid", "private recipe entries must be objects")
        base_recipe = normalize_name(raw_recipe.get("base_recipe"))
        if base_recipe not in VISUAL_RECIPE_CATALOG:
            manifest_error("private_recipe_unknown_base_recipe", "private recipe references an unknown base_recipe")
        required_primitives = normalize_primitives(raw_recipe.get("required_primitives"))
        unknown_primitives = sorted(required_primitives - VALID_VISUAL_PRIMITIVES)
        if unknown_primitives:
            manifest_error(
                "private_recipe_unknown_primitive",
                "private recipe references unknown primitives",
            )
        required_effects = normalize_effects(raw_recipe.get("required_effects"))
        unknown_effects = sorted(required_effects - set(SVG_EFFECT_CATALOG))
        if unknown_effects:
            manifest_error("private_recipe_unknown_effect", "private recipe references unknown effects")
        try:
            minimum_visible_area_ratio = float(raw_recipe.get("minimum_visible_area_ratio", 0))
        except (TypeError, ValueError):
            manifest_error("private_route_manifest_invalid", "private recipe minimum_visible_area_ratio must be numeric")
        if minimum_visible_area_ratio <= 0:
            manifest_error("private_route_manifest_invalid", "private recipe minimum_visible_area_ratio must be positive")
        if raw_recipe.get("fallback_policy") != "deny":
            manifest_error("private_route_manifest_invalid", 'private recipe fallback_policy must be "deny"')
        if raw_recipe.get("exemption_policy") != "deny":
            manifest_error("private_route_manifest_invalid", 'private recipe exemption_policy must be "deny"')

        recipe = dict(raw_recipe)
        recipe["family"] = recipe_family(base_recipe, default_preflight_context())
        recipe["private"] = True
        recipe["required_primitives"] = required_primitives | set(VISUAL_RECIPE_CATALOG[base_recipe].get("required_primitives", set()))
        recipe["required_effects"] = required_effects
        recipe["minimum_visible_area_ratio"] = minimum_visible_area_ratio
        validated[str(recipe_id)] = recipe
    return validated


def load_recipe_selection(path: str | None, route_id: str, private_catalog: dict[str, dict[str, Any]]) -> dict[str, str]:
    if not path:
        return {}
    selection_path = Path(path)
    data = read_json_manifest(selection_path, "private_route_manifest_invalid", "private_route_manifest_missing")
    if data.get("schema_version") != "1.0.0":
        manifest_error("private_route_manifest_invalid", "recipe selection schema_version must be 1.0.0")
    if textify(data.get("route_id")).strip() != route_id:
        manifest_error("private_route_manifest_invalid", "recipe selection route_id must match the route manifest")
    if textify(data.get("manifest_ref")).strip() != "references/routes/create-svg/private-recipes.manifest.json":
        manifest_error("private_route_manifest_invalid", "recipe selection manifest_ref must target the create-svg private manifest")
    digest = textify(data.get("manifest_digest")).strip()
    if digest and not SHA256_HASH_RE.match(digest):
        manifest_error("private_route_manifest_invalid", "recipe selection manifest_digest must be sha256:<64 hex>")
    selections = data.get("selections")
    if not isinstance(selections, list) or not selections:
        manifest_error("private_route_manifest_invalid", "recipe selection must include a selections array")
    out: dict[str, str] = {}
    for item in selections:
        if not isinstance(item, dict):
            manifest_error("private_route_manifest_invalid", "recipe selection entries must be objects")
        try:
            page_index = int(item.get("page_index"))
        except (TypeError, ValueError):
            manifest_error("private_route_manifest_invalid", "recipe selection page_index must be a positive integer")
        if page_index <= 0:
            manifest_error("private_route_manifest_invalid", "recipe selection page_index must be a positive integer")
        private_recipe_id = textify(item.get("private_recipe_id")).strip()
        if private_recipe_id not in private_catalog:
            manifest_error("private_route_manifest_invalid", "recipe selection references an unknown private recipe")
        recipe = private_catalog[private_recipe_id]
        if normalize_name(item.get("base_recipe")) != normalize_name(recipe.get("base_recipe")):
            manifest_error("private_route_manifest_invalid", "recipe selection base_recipe must match the private manifest")
        if normalize_primitives(item.get("required_primitives")) != set(recipe.get("required_primitives", set())):
            manifest_error("private_route_manifest_invalid", "recipe selection required_primitives must match the private manifest")
        if normalize_effects(item.get("required_effects")) != set(recipe.get("required_effects", set())):
            manifest_error("private_route_manifest_invalid", "recipe selection required_effects must match the private manifest")
        try:
            selected_area_ratio = float(item.get("minimum_visible_area_ratio"))
        except (TypeError, ValueError):
            manifest_error("private_route_manifest_invalid", "recipe selection minimum_visible_area_ratio must be numeric")
        if selected_area_ratio != float(recipe.get("minimum_visible_area_ratio")):
            manifest_error("private_route_manifest_invalid", "recipe selection minimum_visible_area_ratio must match the private manifest")
        evidence = item.get("source_truth_evidence")
        if not isinstance(evidence, list) or not evidence:
            manifest_error("private_route_manifest_invalid", "recipe selection must include source_truth_evidence")
        for evidence_item in evidence:
            if not isinstance(evidence_item, dict) or not textify(evidence_item.get("requirement")).strip() or not textify(evidence_item.get("evidence")).strip():
                manifest_error("private_route_manifest_invalid", "recipe selection source_truth_evidence entries must include requirement and evidence")
        if not textify(item.get("selection_reason")).strip():
            manifest_error("private_route_manifest_invalid", "recipe selection must include selection_reason")
        if item.get("fallback_policy") != "deny":
            manifest_error("private_route_manifest_invalid", 'recipe selection fallback_policy must be "deny"')
        if item.get("exemption_policy") != "deny":
            manifest_error("private_route_manifest_invalid", 'recipe selection exemption_policy must be "deny"')
        page = item.get("page")
        if page is not None:
            out[f"page:{page}"] = private_recipe_id
        out[f"index:{page_index}"] = private_recipe_id
    return out


def build_preflight_context(
    route_manifest: str | None = None,
    recipe_selection: str | None = None,
    report_scope: str = PUBLIC_REPORT_SCOPE,
) -> dict[str, Any]:
    context = default_preflight_context(report_scope)
    if not route_manifest:
        if recipe_selection:
            manifest_error("private_route_not_allowed", "--recipe-selection requires --route-manifest")
        return context

    route_path = Path(route_manifest)
    route = read_json_manifest(route_path, "private_route_manifest_invalid", "private_route_manifest_missing")
    route_id = textify(route.get("route_id")).strip()
    if route_id != CREATE_SVG_ROUTE_ID:
        manifest_error("private_route_not_allowed", f'route manifest route_id must be "{CREATE_SVG_ROUTE_ID}"')
    manifest_ref = textify(route.get("private_recipe_manifest")).strip()
    if not manifest_ref:
        manifest_error("private_route_manifest_invalid", "route manifest must include private_recipe_manifest")
    private_manifest_path = resolve_manifest_path(manifest_ref, route_path.parent)
    private_manifest = read_json_manifest(private_manifest_path, "private_route_manifest_invalid", "private_route_manifest_missing")
    raw_allowed = route.get("allowed_private_recipe_ids")
    allowed_ids: set[str] | None = None
    if raw_allowed is not None:
        if not isinstance(raw_allowed, list) or not raw_allowed:
            manifest_error("private_route_manifest_invalid", "allowed_private_recipe_ids must be a non-empty array when present")
        allowed_ids = {textify(item).strip() for item in raw_allowed if textify(item).strip()}
        if len(allowed_ids) != len(raw_allowed):
            manifest_error("private_recipe_duplicate_id", "allowed_private_recipe_ids must not contain duplicates or empty ids")
    elif textify(route.get("allowed_private_recipe_source")).strip() != "private_recipe_manifest_keys":
        manifest_error("private_route_manifest_invalid", "route manifest must declare allowed_private_recipe_source=private_recipe_manifest_keys")
    private_catalog = validate_private_recipe_manifest(private_manifest, allowed_ids)
    selection = load_recipe_selection(recipe_selection, route_id, private_catalog)

    context.update(
        {
            "route_id": route_id,
            "recipe_catalog": {**VISUAL_RECIPE_CATALOG, **private_catalog},
            "private_recipe_catalog": private_catalog,
            "private_id_set": set(private_catalog),
            "allow_private": True,
            "route_manifest_path": str(route_path),
            "private_manifest_path": str(private_manifest_path),
            "recipe_selection_path": recipe_selection or "",
            "recipe_selection": selection,
        }
    )
    return context


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def get_attr(element: ET.Element, name: str, namespace: str | None = None) -> str | None:
    if namespace:
        value = element.attrib.get(f"{{{namespace}}}{name}")
        if value is not None:
            return value
    value = element.attrib.get(name)
    if value is not None:
        return value
    for key, candidate in element.attrib.items():
        if key.endswith("}" + name):
            return candidate
    return None


def svg_role(element: ET.Element) -> str | None:
    return get_attr(element, "role", SLIDE_NS)


def svg_shape_type(element: ET.Element) -> str | None:
    return get_attr(element, "shape-type", SLIDE_NS)


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not NUMBER_RE.match(value):
        return None
    if value.lower().endswith("px"):
        value = value[:-2]
    try:
        return float(value)
    except ValueError:
        return None


def parse_required_number(element: ET.Element, name: str) -> float | None:
    return parse_number(get_attr(element, name))


def issue(level: str, code: str, message: str, element: ET.Element | None = None, hint: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"level": level, "code": code, "message": message}
    if element is not None:
        elem_id = get_attr(element, "id")
        if elem_id:
            out["element_id"] = elem_id
        out["tag"] = local_name(element.tag)
    if hint:
        out["hint"] = hint
    return out


def parse_viewbox(value: str | None) -> list[float] | None:
    if value is None:
        return None
    parts = [part for part in re.split(r"[\s,]+", value.strip()) if part]
    if len(parts) != 4:
        return None
    try:
        return [float(part) for part in parts]
    except ValueError:
        return None


def is_external_href(value: str | None) -> bool:
    if value is None:
        return False
    lower = value.strip().lower()
    return lower.startswith("http://") or lower.startswith("https://") or lower.startswith("data:")


def href_value(element: ET.Element) -> str | None:
    return get_attr(element, "href") or get_attr(element, "href", XLINK_NS)


def element_self_hidden(element: ET.Element) -> bool:
    props = parse_style_props(get_attr(element, "style"))
    display = textify(get_attr(element, "display") or props.get("display")).strip().lower()
    visibility = textify(get_attr(element, "visibility") or props.get("visibility")).strip().lower()
    opacity = parse_opacity(get_attr(element, "opacity") or props.get("opacity"))
    return display == "none" or visibility in {"hidden", "collapse"} or opacity <= 0.02


def element_self_clip_risk(element: ET.Element) -> bool:
    props = parse_style_props(get_attr(element, "style"))
    overflow = textify(get_attr(element, "overflow") or props.get("overflow")).strip().lower()
    return bool(
        overflow in {"hidden", "clip"}
        or get_attr(element, "clip-path")
        or props.get("clip-path")
        or get_attr(element, "mask")
        or props.get("mask")
    )


def walk_renderable(root: ET.Element) -> list[ET.Element]:
    out: list[ET.Element] = []

    def walk(element: ET.Element, inherited_hidden: bool = False, inherited_clip: bool = False) -> None:
        name = local_name(element.tag)
        if name in IGNORED_SUBTREES:
            return
        current_hidden = inherited_hidden or element_self_hidden(element)
        current_clip = inherited_clip or element_self_clip_risk(element)
        if current_hidden:
            element.set(INTERNAL_INHERITED_HIDDEN_ATTR, "1")
        if current_clip:
            element.set(INTERNAL_INHERITED_CLIP_ATTR, "1")
        if name in RENDERABLE_TAGS or name == "foreignObject" or name == "image":
            out.append(element)
        for child in list(element):
            walk(child, current_hidden, current_clip)

    for child in list(root):
        walk(child)
    return out


def validate_root(root: ET.Element) -> tuple[list[dict[str, Any]], float, float]:
    issues: list[dict[str, Any]] = []
    if local_name(root.tag) != "svg":
        issues.append(issue("error", "root_not_svg", "root element must be <svg>"))
    if svg_role(root) != "slide":
        issues.append(issue("error", "missing_root_role", 'root <svg> must include slide:role="slide"', root))
    contract_version = get_attr(root, "contract-version", SLIDE_NS)
    if contract_version is None:
        issues.append(
            issue(
                "error",
                "root_contract_version_missing",
                f'root <svg> must include slide:contract-version="{SVG_CONTRACT_VERSION}"',
                root,
                "The slide server rejects SVG roots without the SVGlide authoring contract marker.",
            )
        )
    elif contract_version != SVG_CONTRACT_VERSION:
        issues.append(
            issue(
                "error",
                "root_contract_version_mismatch",
                f'root <svg> must use slide:contract-version="{SVG_CONTRACT_VERSION}"',
                root,
            )
        )

    width = parse_number(get_attr(root, "width"))
    height = parse_number(get_attr(root, "height"))
    viewbox = parse_viewbox(get_attr(root, "viewBox"))

    if width != CANVAS_WIDTH or height != CANVAS_HEIGHT:
        issues.append(
            issue(
                "error",
                "root_canvas_mismatch",
                'root must use width="960" height="540"',
                root,
                "Scale coordinates to the Lark Slides 960x540 canvas before calling slides +create-svg.",
            )
        )
    if viewbox != [0.0, 0.0, CANVAS_WIDTH, CANVAS_HEIGHT]:
        issues.append(
            issue(
                "error",
                "root_viewbox_mismatch",
                'root must use viewBox="0 0 960 540"',
                root,
                "Do not submit a 1280x720 viewBox and rely on server-side scaling.",
            )
        )

    return issues, width or CANVAS_WIDTH, height or CANVAS_HEIGHT


def validate_roles_and_attrs(elements: list[ET.Element]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for element in elements:
        name = local_name(element.tag)
        role = svg_role(element)
        if name == "text":
            if is_vertical_text_element(element):
                issues.append(
                    issue(
                        "error",
                        "unsupported_vertical_text",
                        "root-level vertical <text> is not supported by SVGlide authoring",
                        element,
                        "Use seed-declared short vertical labels only, rendered through a supported text surface; do not use root <text writing-mode> for readable content.",
                    )
                )
            issues.append(
                issue(
                    "error",
                    "unsupported_text_element",
                    'root-level <text> is not supported; use foreignObject slide:role="shape" slide:shape-type="text"',
                    element,
                )
            )
            continue
        if name in {"polygon", "polyline"}:
            issues.append(
                issue(
                    "error",
                    "unsupported_shape_element",
                    f"<{name}> is not supported by SVGlide MVP",
                    element,
                    "Use path with M/L/H/V/C/Q/Z commands, or use rect/line/circle/ellipse.",
                )
            )
            continue
        if name not in {"image"} | SUPPORTED_SHAPES:
            continue
        if role is None:
            issues.append(issue("error", "missing_leaf_role", '<%s> must include slide:role="shape" or "image"' % name, element))
            continue
        if role == "shape":
            if name not in SUPPORTED_SHAPES:
                issues.append(issue("error", "unsupported_shape_role", f'<{name} slide:role="shape"> is not supported', element))
                continue
            if name == "foreignObject" and svg_shape_type(element) != "text":
                issues.append(
                    issue(
                        "error",
                        "missing_text_shape_type",
                        '<foreignObject slide:role="shape"> must include slide:shape-type="text"',
                        element,
                    )
                )
        elif role == "image":
            if name != "image":
                issues.append(issue("error", "unsupported_image_role", f'<{name} slide:role="image"> is not supported', element))
            image_href = href_value(element)
            if not image_href:
                issues.append(issue("error", "missing_image_href", '<image slide:role="image"> must include href', element))
            if is_external_href(image_href):
                issues.append(
                    issue(
                        "warning",
                        "external_image_href",
                        "<image> uses an http(s) or data href",
                        element,
                        'MVP preflight allows this, but live conversion is more reliable with href="@./path" auto-upload or a file token.',
                    )
                )
            style = get_attr(element, "style") or ""
            if get_attr(element, "opacity") is not None or STYLE_IMAGE_OPACITY_RE.search(style):
                issues.append(
                    issue(
                        "warning",
                        "image_opacity_unsupported",
                        "<image> opacity is not preserved by the current SVGlide conversion path",
                        element,
                        "MVP preflight allows this, but visual readback may differ; pre-blend opacity or place a semi-transparent rect overlay when fidelity matters.",
                    )
                )
        else:
            issues.append(issue("error", "unsupported_role", f'unsupported slide:role="{role}"', element))
    return issues


def chart_marker_elements(root: ET.Element) -> list[ET.Element]:
    return [child for child in list(root) if local_name(child.tag) == "g" and svg_role(child) == "chart"]


def decode_base64url_payload(payload: str) -> bytes:
    payload = payload.strip()
    if not payload:
        raise ValueError("empty payload")
    if not BASE64URL_RE.match(payload):
        raise ValueError("payload must use unpadded URL-safe base64 characters")
    padding = "=" * ((4 - len(payload) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(payload + padding)
    except (binascii.Error, ValueError) as error:
        raise ValueError(str(error)) from error


def reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON number {value}")


def validate_chart_spec_payload(decoded: bytes) -> None:
    try:
        spec = json.loads(decoded.decode("utf-8"), parse_constant=reject_json_constant)
    except UnicodeDecodeError as error:
        raise ValueError(f"payload must be UTF-8 JSON: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"payload must be JSON: {error}") from error

    if not isinstance(spec, dict):
        raise ValueError("payload root must be a JSON object")
    if spec.get("version") != SVG_CHART_SPEC_VERSION:
        raise ValueError(f'version must be "{SVG_CHART_SPEC_VERSION}"')
    chart_type = spec.get("chartType")
    if chart_type not in {"bar", "line"}:
        raise ValueError('chartType must be one of "bar","line"')
    data = spec.get("data")
    if not isinstance(data, dict):
        raise ValueError("data must be an object")
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("data.categories must be a non-empty array")
    for index, category in enumerate(categories):
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"data.categories[{index}] must be a non-empty string")
    series = data.get("series")
    if not isinstance(series, list) or not series:
        raise ValueError("data.series must be a non-empty array")
    for series_index, item in enumerate(series):
        if not isinstance(item, dict):
            raise ValueError(f"data.series[{series_index}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"data.series[{series_index}].name must be a non-empty string")
        values = item.get("values")
        if not isinstance(values, list):
            raise ValueError(f"data.series[{series_index}].values must be an array")
        if len(values) != len(categories):
            raise ValueError(f"data.series[{series_index}].values length must match data.categories length")
        for value_index, value in enumerate(values):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"data.series[{series_index}].values[{value_index}] must be a finite number")


def validate_chart_markers(root: ET.Element) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    direct_chart_ids = {id(element) for element in chart_marker_elements(root)}

    for element in root.iter():
        if element is root:
            continue
        role = svg_role(element)
        name = local_name(element.tag)
        if role == "whiteboard":
            issues.append(issue("error", "unsupported_whiteboard_role", 'slide:role="whiteboard" is not supported by slides +create-svg', element))
        if role == "chart" and id(element) not in direct_chart_ids:
            issues.append(issue("error", "chart_marker_not_root_child", '<g slide:role="chart"> must be a direct child of root <svg>', element))
        if name == "metadata" and get_attr(element, "data-svglide-whiteboard") is not None:
            issues.append(
                issue(
                    "error",
                    "legacy_whiteboard_marker",
                    "legacy SVGlide whiteboard marker metadata is not supported by slides +create-svg",
                    element,
                )
            )

    seen_refs: set[str] = set()
    for marker in chart_marker_elements(root):
        chart_ref = (get_attr(marker, "chart-ref", SLIDE_NS) or "").strip()
        if not chart_ref:
            issues.append(issue("error", "chart_marker_missing_ref", '<g slide:role="chart"> must include slide:chart-ref', marker))
        elif chart_ref in seen_refs:
            issues.append(issue("error", "chart_marker_duplicate_ref", f'duplicate slide:chart-ref "{chart_ref}" in SVG chart markers', marker))
        else:
            seen_refs.add(chart_ref)
        for attr in ["x", "y", "width", "height"]:
            if parse_number(get_attr(marker, attr)) is None:
                issues.append(issue("error", "chart_marker_bad_bbox", f'<g slide:role="chart"> attribute "{attr}" must be a number or px length', marker))

        children = list(marker)
        if len(children) != 1 or local_name(children[0].tag) != "metadata":
            issues.append(issue("error", "chart_marker_metadata_count", '<g slide:role="chart"> must contain exactly one metadata child', marker))
            continue

        metadata = children[0]
        if get_attr(metadata, "data-svglide-chart") != SVG_CHART_MARKER_VERSION:
            issues.append(
                issue(
                    "error",
                    "chart_marker_metadata_version",
                    f'chart marker metadata must include data-svglide-chart="{SVG_CHART_MARKER_VERSION}"',
                    metadata,
                )
            )
        if get_attr(metadata, "data-format") != SVG_CHART_FORMAT:
            issues.append(issue("error", "chart_marker_metadata_format", f'chart marker metadata must include data-format="{SVG_CHART_FORMAT}"', metadata))
        if get_attr(metadata, "data-encoding") != SVG_CHART_ENCODING:
            issues.append(issue("error", "chart_marker_metadata_encoding", f'chart marker metadata must include data-encoding="{SVG_CHART_ENCODING}"', metadata))

        payload_hash = get_attr(metadata, "data-payload-hash") or ""
        if not SHA256_HASH_RE.match(payload_hash):
            issues.append(issue("error", "chart_marker_payload_hash", 'chart marker metadata must include data-payload-hash="sha256:<64 hex>"', metadata))
            continue
        if list(metadata):
            issues.append(issue("error", "chart_marker_payload_not_text", "chart marker metadata payload must be base64url text", metadata))
            continue
        payload = "".join(metadata.itertext()).strip()
        try:
            decoded = decode_base64url_payload(payload)
        except ValueError as error:
            issues.append(issue("error", "chart_marker_payload_base64url", f"chart marker metadata payload must be base64url: {error}", metadata))
            continue
        actual_hash = "sha256:" + hashlib.sha256(decoded).hexdigest()
        if actual_hash.lower() != payload_hash.lower():
            issues.append(issue("error", "chart_marker_payload_hash_mismatch", "chart marker metadata data-payload-hash does not match decoded payload", metadata))
            continue
        try:
            validate_chart_spec_payload(decoded)
        except ValueError as error:
            issues.append(issue("error", "chart_marker_payload_spec", f"chart marker decoded payload must be valid {SVG_CHART_FORMAT} JSON: {error}", metadata))
            continue

    return issues


def bbox_for_element(element: ET.Element) -> dict[str, float] | None:
    name = local_name(element.tag)
    if name in {"rect", "foreignObject", "image"}:
        x = parse_required_number(element, "x")
        y = parse_required_number(element, "y")
        width = parse_required_number(element, "width")
        height = parse_required_number(element, "height")
        if None in {x, y, width, height}:
            return None
        return {"x": x or 0.0, "y": y or 0.0, "width": width or 0.0, "height": height or 0.0}
    if name == "circle":
        cx = parse_required_number(element, "cx")
        cy = parse_required_number(element, "cy")
        r = parse_required_number(element, "r")
        if None in {cx, cy, r}:
            return None
        return {"x": (cx or 0.0) - (r or 0.0), "y": (cy or 0.0) - (r or 0.0), "width": 2 * (r or 0.0), "height": 2 * (r or 0.0)}
    if name == "ellipse":
        cx = parse_required_number(element, "cx")
        cy = parse_required_number(element, "cy")
        rx = parse_required_number(element, "rx")
        ry = parse_required_number(element, "ry")
        if None in {cx, cy, rx, ry}:
            return None
        return {"x": (cx or 0.0) - (rx or 0.0), "y": (cy or 0.0) - (ry or 0.0), "width": 2 * (rx or 0.0), "height": 2 * (ry or 0.0)}
    if name == "line":
        x1 = parse_required_number(element, "x1")
        y1 = parse_required_number(element, "y1")
        x2 = parse_required_number(element, "x2")
        y2 = parse_required_number(element, "y2")
        if None in {x1, y1, x2, y2}:
            return None
        min_x = min(x1 or 0.0, x2 or 0.0)
        min_y = min(y1 or 0.0, y2 or 0.0)
        return {"x": min_x, "y": min_y, "width": abs((x2 or 0.0) - (x1 or 0.0)), "height": abs((y2 or 0.0) - (y1 or 0.0))}
    if name == "path":
        numbers = [float(match.group(0)) for match in PATH_NUMBER_RE.finditer(get_attr(element, "d") or "")]
        if len(numbers) < 2:
            return None
        xs = numbers[0::2]
        ys = numbers[1::2]
        if not xs or not ys:
            return None
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        return {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y}
    return None


def is_background_bbox(bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    return bbox["x"] <= 0 and bbox["y"] <= 0 and bbox["x"] + bbox["width"] >= canvas_width and bbox["y"] + bbox["height"] >= canvas_height


def is_safe_area_exempt_backing(element: ET.Element, bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    name = local_name(element.tag)
    if name not in {"rect", "image"}:
        return False
    full_height_edge = bbox["y"] <= 0 and bbox["y"] + bbox["height"] >= canvas_height and bbox["width"] >= canvas_width * 0.2
    full_width_edge = bbox["x"] <= 0 and bbox["x"] + bbox["width"] >= canvas_width and bbox["height"] >= canvas_height * 0.2
    if full_height_edge or full_width_edge:
        return True
    if name == "rect":
        has_no_fill = (get_attr(element, "fill") or "").strip().lower() == "none"
        has_stroke = bool(get_attr(element, "stroke") or parse_style_props(get_attr(element, "style")).get("stroke"))
        large_frame = bbox["width"] >= canvas_width * 0.85 and bbox["height"] >= canvas_height * 0.85
        near_canvas_edge = bbox["x"] <= SAFE_AREA["x"] and bbox["y"] <= SAFE_AREA["y"]
        return has_no_fill and has_stroke and large_frame and near_canvas_edge
    return False


def bbox_outside(bbox: dict[str, float], rect: dict[str, float]) -> bool:
    return (
        bbox["x"] < rect["x"]
        or bbox["y"] < rect["y"]
        or bbox["x"] + bbox["width"] > rect["x"] + rect["width"]
        or bbox["y"] + bbox["height"] > rect["y"] + rect["height"]
    )


def intersects(left: dict[str, float], right: dict[str, float]) -> bool:
    return (
        left["x"] < right["x"] + right["width"]
        and left["x"] + left["width"] > right["x"]
        and left["y"] < right["y"] + right["height"]
        and left["y"] + left["height"] > right["y"]
    )


def bbox_contains(outer: dict[str, float], inner: dict[str, float], tolerance: float = 0.5) -> bool:
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance
    )


def bbox_center(bbox: dict[str, float]) -> tuple[float, float]:
    return (bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)


def point_in_bbox(x: float, y: float, bbox: dict[str, float]) -> bool:
    return bbox["x"] <= x <= bbox["x"] + bbox["width"] and bbox["y"] <= y <= bbox["y"] + bbox["height"]


def expand_bbox(bbox: dict[str, float], amount: float) -> dict[str, float]:
    return {
        "x": bbox["x"] - amount,
        "y": bbox["y"] - amount,
        "width": bbox["width"] + amount * 2,
        "height": bbox["height"] + amount * 2,
    }


def parse_style_props(style: str | None) -> dict[str, str]:
    props: dict[str, str] = {}
    if not style:
        return props
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        props[key.strip().lower()] = value.strip()
    return props


def parse_css_number(value: str) -> float | None:
    try:
        value = value.strip()
        if value.endswith("%"):
            return float(value[:-1]) * 2.55
        return float(value)
    except ValueError:
        return None


def parse_color(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    value = value.strip()
    lower = value.lower()
    if lower in {"none", "transparent"}:
        return None
    named = {
        "white": (255.0, 255.0, 255.0, 1.0),
        "black": (0.0, 0.0, 0.0, 1.0),
    }
    if lower in named:
        return named[lower]
    if lower.startswith("#"):
        hex_value = lower[1:]
        if len(hex_value) == 3:
            hex_value = "".join(char * 2 for char in hex_value)
        if len(hex_value) == 6:
            try:
                return (float(int(hex_value[0:2], 16)), float(int(hex_value[2:4], 16)), float(int(hex_value[4:6], 16)), 1.0)
            except ValueError:
                return None
    match = RGB_RE.match(lower)
    if match:
        parts = [part.strip() for part in match.group(1).split(",")]
        if len(parts) in {3, 4}:
            channels = [parse_css_number(part) for part in parts[:3]]
            if any(channel is None for channel in channels):
                return None
            alpha = 1.0
            if len(parts) == 4:
                try:
                    alpha = float(parts[3])
                except ValueError:
                    return None
            return (channels[0] or 0.0, channels[1] or 0.0, channels[2] or 0.0, alpha)
    return None


def parse_opacity(value: str | None) -> float:
    if value is None:
        return 1.0
    try:
        return max(0.0, min(1.0, float(value.strip())))
    except ValueError:
        return 1.0


def relative_luminance(color: tuple[float, float, float, float]) -> float:
    def channel(value: float) -> float:
        value = max(0.0, min(255.0, value)) / 255.0
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    r, g, b, _alpha = color
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def text_color(element: ET.Element) -> tuple[float, float, float, float] | None:
    for child in element.iter():
        props = parse_style_props(get_attr(child, "style"))
        color = parse_color(props.get("color"))
        if color is not None:
            return color
    return None


def fill_color(element: ET.Element) -> tuple[float, float, float, float] | None:
    props = parse_style_props(get_attr(element, "style"))
    color = parse_color(get_attr(element, "fill") or props.get("fill"))
    if color is None:
        return None
    opacity = parse_opacity(get_attr(element, "opacity") or props.get("opacity"))
    return (color[0], color[1], color[2], color[3] * opacity)


def stroke_color(element: ET.Element) -> tuple[float, float, float, float] | None:
    props = parse_style_props(get_attr(element, "style"))
    return parse_color(get_attr(element, "stroke") or props.get("stroke"))


def element_effective_opacity(element: ET.Element) -> float:
    props = parse_style_props(get_attr(element, "style"))
    return parse_opacity(get_attr(element, "opacity") or props.get("opacity"))


def is_light_text_color(color: tuple[float, float, float, float]) -> bool:
    return color[3] >= 0.8 and relative_luminance(color) >= 0.88


def is_dark_backing_color(color: tuple[float, float, float, float]) -> bool:
    return color[3] >= 0.65 and relative_luminance(color) <= 0.45


def validate_geometry(elements: list[ET.Element], canvas_width: float, canvas_height: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    text_boxes: list[dict[str, Any]] = []
    canvas = {"x": 0.0, "y": 0.0, "width": canvas_width, "height": canvas_height}
    for element in elements:
        name = local_name(element.tag)
        bbox = bbox_for_element(element)
        if bbox is None:
            continue
        if name != "line" and (bbox["width"] <= 0 or bbox["height"] <= 0):
            issues.append(
                issue(
                    "error",
                    "non_positive_bbox",
                    f"<{name}> must have positive width and height",
                    element,
                    "Do not submit zero-size text boxes, cards, images, circles, or ellipses; allocate real space or remove the element.",
                )
            )
            continue
        if is_background_bbox(bbox, canvas_width, canvas_height):
            continue
        if bbox_outside(bbox, canvas):
            issues.append(
                issue(
                    "error",
                    "canvas_bounds",
                    f"<{name}> is outside the 960x540 canvas",
                    element,
                    "Non-background elements must fit inside the slide canvas.",
                )
            )
        elif bbox_outside(bbox, SAFE_AREA) and not is_safe_area_exempt_backing(element, bbox, canvas_width, canvas_height):
            issues.append(
                issue(
                    "warning",
                    "safe_area",
                    f"<{name}> is outside the recommended safe area",
                    element,
                    "Keep text, labels, cards, legends, and key visuals within x>=48 y>=40 right<=912 bottom<=500 unless it is an intentional full-bleed background.",
                )
            )
        if name == "foreignObject" and svg_role(element) == "shape" and svg_shape_type(element) == "text":
            text = "".join(element.itertext()).strip()
            if text:
                text_boxes.append(
                    {
                        "element": element,
                        "bbox": bbox,
                        "text": text,
                        "identifier": element_identifier_text(element),
                        "font_size": text_font_size(element),
                        "vertical_text": is_vertical_text_element(element),
                    }
                )
    return issues, text_boxes


def validate_text_overlap(text_boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for left_index, left in enumerate(text_boxes):
        for right in text_boxes[left_index + 1 :]:
            if intersects(left["bbox"], right["bbox"]):
                left_id = get_attr(left["element"], "id") or local_name(left["element"].tag)
                right_id = get_attr(right["element"], "id") or local_name(right["element"].tag)
                issues.append(
                    {
                        "level": "error",
                        "code": "text_bbox_overlap",
                        "message": f"text boxes overlap: {left_id} and {right_id}",
                        "left_element_id": get_attr(left["element"], "id"),
                        "right_element_id": get_attr(right["element"], "id"),
                        "hint": "Move text boxes apart, reduce text density, or split the page into clearer layout boxes.",
                    }
                )
    return issues


def text_line_height(element: ET.Element, font_size: float) -> float:
    for child in element.iter():
        props = parse_style_props(get_attr(child, "style"))
        value = props.get("line-height")
        if not value:
            continue
        lower = value.strip().lower()
        try:
            if lower.endswith("px"):
                return max(font_size, float(lower[:-2]))
            return max(font_size, font_size * float(lower))
        except ValueError:
            continue
    return font_size * 1.25


def text_width_units(text: str) -> float:
    units = 0.0
    for char in text:
        if char.isspace():
            units += 0.35
        elif ord(char) > 127:
            units += 1.0
        elif char in "MW@#%&":
            units += 0.9
        elif char.isupper() or char.isdigit():
            units += 0.66
        elif char in "il.,:;|":
            units += 0.28
        else:
            units += 0.52
    return units


def text_required_size(text: str, font_size: float, max_width: float) -> tuple[float, float, int]:
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    if not lines:
        return (0.0, 0.0, 0)
    longest = max(text_width_units(line) * font_size for line in lines)
    available_width = max(1.0, max_width)
    wrapped_lines = sum(max(1, math.ceil((text_width_units(line) * font_size) / available_width)) for line in lines)
    return (longest, wrapped_lines * font_size * 1.25, wrapped_lines)


def horizontal_overlap(left: dict[str, float], right: dict[str, float], tolerance: float = 0.0) -> bool:
    return left["x"] < right["x"] + right["width"] + tolerance and left["x"] + left["width"] + tolerance > right["x"]


def bbox_right(bbox: dict[str, float]) -> float:
    return bbox["x"] + bbox["width"]


def bbox_bottom(bbox: dict[str, float]) -> float:
    return bbox["y"] + bbox["height"]


def is_top_badge(element: ET.Element, bbox: dict[str, float]) -> bool:
    if local_name(element.tag) != "rect" or svg_role(element) != "shape":
        return False
    return bbox["x"] <= 220 and bbox["y"] <= 90 and 36 <= bbox["width"] <= 190 and 18 <= bbox["height"] <= 56


def is_headline_text(item: dict[str, Any]) -> bool:
    bbox = item["bbox"]
    element = item["element"]
    font_size = text_font_size(element) or 0.0
    return bbox["x"] <= 260 and bbox["y"] <= 155 and (font_size >= 24 or bbox["height"] >= 36) and bbox["width"] >= 140


def is_visible_container_rect(element: ET.Element, bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    if local_name(element.tag) != "rect" or svg_role(element) != "shape":
        return False
    if is_background_bbox(bbox, canvas_width, canvas_height):
        return False
    if is_safe_area_exempt_backing(element, bbox, canvas_width, canvas_height):
        return False
    fill = (get_attr(element, "fill") or parse_style_props(get_attr(element, "style")).get("fill") or "").strip().lower()
    stroke = (get_attr(element, "stroke") or parse_style_props(get_attr(element, "style")).get("stroke") or "").strip().lower()
    if fill in {"none", "transparent"} and not stroke:
        return False
    return bbox["width"] >= 24 and bbox["height"] >= 18


def overlap_area(left: dict[str, float], right: dict[str, float]) -> float:
    x1 = max(left["x"], right["x"])
    y1 = max(left["y"], right["y"])
    x2 = min(bbox_right(left), bbox_right(right))
    y2 = min(bbox_bottom(left), bbox_bottom(right))
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def is_label_or_decor_shape(element: ET.Element, bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    if is_background_bbox(bbox, canvas_width, canvas_height):
        return False
    name = local_name(element.tag)
    if svg_role(element) != "shape" or name not in {"rect", "circle", "ellipse", "path"}:
        return False
    identifier = element_identifier_text(element)
    if re.search(r"(badge|chip|label|tag|pill|marker|stamp|seal|decor|ornament|kicker)", identifier):
        return True
    return bbox["width"] <= 150 and bbox["height"] <= 54 and bbox["width"] * bbox["height"] <= 7200


def is_text_owned_by_shape(text_bbox: dict[str, float], shape_bbox: dict[str, float]) -> bool:
    center_x, center_y = bbox_center(text_bbox)
    return point_in_bbox(center_x, center_y, shape_bbox) and text_bbox["width"] <= shape_bbox["width"] + 6 and text_bbox["height"] <= shape_bbox["height"] + 6


def is_plain_light_panel(element: ET.Element) -> bool:
    color = fill_color(element)
    if color is None or color[3] < 0.85:
        return False
    if relative_luminance(color) < 0.88:
        return False
    stroke = stroke_color(element)
    if stroke is not None and stroke[3] >= 0.2:
        return False
    return True


def has_accent_rail(container_element: ET.Element, container_bbox: dict[str, float], shaped: list[tuple[ET.Element, dict[str, float]]]) -> bool:
    for element, bbox in shaped:
        if element is container_element or local_name(element.tag) != "rect" or svg_role(element) != "shape":
            continue
        color = fill_color(element)
        if color is None or color[3] < 0.7 or relative_luminance(color) >= 0.82:
            continue
        contained = bbox_contains(container_bbox, bbox, tolerance=1.5)
        left_rail = abs(bbox["x"] - container_bbox["x"]) <= 1.5 and bbox["width"] <= 16 and bbox["height"] >= container_bbox["height"] * 0.55
        top_rail = abs(bbox["y"] - container_bbox["y"]) <= 1.5 and bbox["height"] <= 14 and bbox["width"] >= container_bbox["width"] * 0.45
        if contained and (left_rail or top_rail):
            return True
    return False


def is_connector_element(element: ET.Element) -> bool:
    name = local_name(element.tag)
    if svg_role(element) != "shape" or name not in {"line", "path"}:
        return False
    props = parse_style_props(get_attr(element, "style"))
    stroke = get_attr(element, "stroke") or props.get("stroke")
    if not stroke or stroke.strip().lower() in {"none", "transparent"}:
        return False
    opacity = element_effective_opacity(element)
    stroke_opacity = parse_opacity(get_attr(element, "stroke-opacity") or props.get("stroke-opacity"))
    if opacity * stroke_opacity < 0.18:
        return False
    if name == "path":
        fill = (get_attr(element, "fill") or props.get("fill") or "none").strip().lower()
        if fill not in {"none", "transparent"}:
            return False
    return True


def line_segments_for_element(element: ET.Element) -> list[tuple[float, float, float, float]]:
    name = local_name(element.tag)
    if name == "line":
        x1 = parse_required_number(element, "x1")
        y1 = parse_required_number(element, "y1")
        x2 = parse_required_number(element, "x2")
        y2 = parse_required_number(element, "y2")
        if None in {x1, y1, x2, y2}:
            return []
        return [(x1 or 0.0, y1 or 0.0, x2 or 0.0, y2 or 0.0)]
    if name != "path":
        return []
    numbers = [float(match.group(0)) for match in PATH_NUMBER_RE.finditer(get_attr(element, "d") or "")]
    points = list(zip(numbers[0::2], numbers[1::2]))
    return [(a[0], a[1], b[0], b[1]) for a, b in zip(points, points[1:])]


def orientation(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def on_segment(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    return min(ax, bx) - 0.01 <= cx <= max(ax, bx) + 0.01 and min(ay, by) - 0.01 <= cy <= max(ay, by) + 0.01


def segments_intersect(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> bool:
    o1 = orientation(a[0], a[1], b[0], b[1], c[0], c[1])
    o2 = orientation(a[0], a[1], b[0], b[1], d[0], d[1])
    o3 = orientation(c[0], c[1], d[0], d[1], a[0], a[1])
    o4 = orientation(c[0], c[1], d[0], d[1], b[0], b[1])
    if abs(o1) <= 0.01 and on_segment(a[0], a[1], b[0], b[1], c[0], c[1]):
        return True
    if abs(o2) <= 0.01 and on_segment(a[0], a[1], b[0], b[1], d[0], d[1]):
        return True
    if abs(o3) <= 0.01 and on_segment(c[0], c[1], d[0], d[1], a[0], a[1]):
        return True
    if abs(o4) <= 0.01 and on_segment(c[0], c[1], d[0], d[1], b[0], b[1]):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def line_segment_intersects_bbox(segment: tuple[float, float, float, float], bbox: dict[str, float]) -> bool:
    x1, y1, x2, y2 = segment
    segment_bbox = {"x": min(x1, x2), "y": min(y1, y2), "width": abs(x2 - x1), "height": abs(y2 - y1)}
    if not intersects(segment_bbox, bbox):
        return False
    if point_in_bbox(x1, y1, bbox) or point_in_bbox(x2, y2, bbox):
        return True
    left = bbox["x"]
    right = bbox["x"] + bbox["width"]
    top = bbox["y"]
    bottom = bbox["y"] + bbox["height"]
    edges = [
        ((left, top), (right, top)),
        ((right, top), (right, bottom)),
        ((right, bottom), (left, bottom)),
        ((left, bottom), (left, top)),
    ]
    return any(segments_intersect((x1, y1), (x2, y2), start, end) for start, end in edges)


def is_decorative_horizontal_rule(element: ET.Element, bbox: dict[str, float]) -> bool:
    name = local_name(element.tag)
    identifier = element_identifier_text(element)
    if name == "line":
        return bbox["width"] >= 180 and bbox["height"] <= 3
    if name == "rect" and bbox["width"] >= 180 and 1 <= bbox["height"] <= 10:
        return True
    return bool(re.search(r"(divider|rule|line|stripe|bar|decor)", identifier)) and bbox["width"] >= 160 and bbox["height"] <= 14


def validate_layout_pressure(
    elements: list[ET.Element],
    text_boxes: list[dict[str, Any]],
    canvas_width: float,
    canvas_height: float,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    bboxes = [(element, bbox_for_element(element)) for element in elements]
    shaped = [(element, bbox) for element, bbox in bboxes if bbox is not None]
    badges = [(element, bbox) for element, bbox in shaped if is_top_badge(element, bbox)]
    headlines = [item for item in text_boxes if is_headline_text(item)]

    for headline in headlines:
        headline_bbox = headline["bbox"]
        for badge_element, badge_bbox in badges:
            if not horizontal_overlap(badge_bbox, headline_bbox, tolerance=80):
                continue
            gap = headline_bbox["y"] - bbox_bottom(badge_bbox)
            if gap < BADGE_HEADLINE_MIN_GAP:
                issue_item = issue(
                    "error",
                    "badge_headline_overlap",
                    "chapter/status badge is too close to the headline",
                    headline["element"],
                    "Move the headline down or move the badge up; keep at least 8px between badge bottom and headline top, preferably 12px for bold headlines.",
                )
                issue_item["badge_element_id"] = get_attr(badge_element, "id")
                issue_item["gap"] = round(gap, 2)
                issues.append(issue_item)
                break

    containers = [(element, bbox) for element, bbox in shaped if is_visible_container_rect(element, bbox, canvas_width, canvas_height)]
    label_shapes = [(element, bbox) for element, bbox in shaped if is_label_or_decor_shape(element, bbox, canvas_width, canvas_height)]
    for label_element, label_bbox in label_shapes:
        for item in text_boxes:
            text_bbox = item["bbox"]
            if is_text_owned_by_shape(text_bbox, label_bbox):
                continue
            area = overlap_area(label_bbox, expand_bbox(text_bbox, 1.5))
            if area <= 8:
                continue
            label_issue = issue(
                "error",
                "label_text_overlap",
                "label, badge, or decorative shape overlaps readable text",
                label_element,
                "Move labels and decorative marks outside title/body/callout text boxes; do not let style markers cover readable content.",
            )
            label_issue["text_element_id"] = get_attr(item["element"], "id")
            label_issue["overlap_area"] = round(area, 2)
            issues.append(label_issue)
            break

    right_top_text = [
        item
        for item in text_boxes
        if item["bbox"]["x"] >= 600 and item["bbox"]["y"] <= 132 and textify(item.get("text")).strip()
    ]
    if right_top_text:
        total_chars = sum(visible_text_char_count(item.get("text")) for item in right_top_text)
        min_gap = min(
            (
                max(0.0, max(right_top_text[a]["bbox"]["x"], right_top_text[b]["bbox"]["x"]) - min(bbox_right(right_top_text[a]["bbox"]), bbox_right(right_top_text[b]["bbox"])))
                for a in range(len(right_top_text))
                for b in range(a + 1, len(right_top_text))
            ),
            default=999.0,
        )
        if total_chars > 28 or len(right_top_text) > 2 or min_gap < 12:
            crowded_issue = issue(
                "warning",
                "right_title_safe_zone_crowded",
                "right-side title or chip area is crowded",
                right_top_text[0]["element"],
                "Keep the top-right title/chip rail short and separated; move secondary labels into body boxes or reduce text.",
            )
            crowded_issue["text_box_count"] = len(right_top_text)
            crowded_issue["visible_chars"] = total_chars
            crowded_issue["min_gap"] = round(min_gap, 2)
            issues.append(crowded_issue)

    for headline in headlines:
        headline_bbox = headline["bbox"]
        for container_element, container_bbox in containers:
            if container_bbox["y"] <= headline_bbox["y"]:
                continue
            if not horizontal_overlap(container_bbox, headline_bbox, tolerance=8):
                continue
            gap = container_bbox["y"] - bbox_bottom(headline_bbox)
            if gap < TITLE_SURFACE_MIN_GAP:
                pressure_issue = issue(
                    "error",
                    "title_surface_pressure",
                    "text surface or card is too close to the headline",
                    headline["element"],
                    "Move callout cards, labels, badges, and panels outside the title exclusion zone; keep at least 24px between headline bottom and any text surface.",
                )
                pressure_issue["surface_element_id"] = get_attr(container_element, "id")
                pressure_issue["gap"] = round(gap, 2)
                issues.append(pressure_issue)
                break

    for container_element, container_bbox in containers:
        if not is_card_like_rect(container_element, container_bbox, canvas_width, canvas_height):
            continue
        if not is_plain_light_panel(container_element):
            continue
        if has_accent_rail(container_element, container_bbox, shaped):
            continue
        contained_text = [
            item
            for item in text_boxes
            if point_in_bbox(*bbox_center(item["bbox"]), container_bbox) and item["bbox"]["width"] <= container_bbox["width"] + 8
        ]
        if not contained_text:
            continue
        panel_issue = issue(
            "error",
            "plain_white_text_panel",
            "plain white text panel lacks a visible design treatment",
            container_element,
            "Use a style-preset text surface: tinted fill, accent rail, stroke, glass overlay, icon/number marker, or another explicit backing treatment instead of a bare white rectangle.",
        )
        panel_issue["contained_text_count"] = len(contained_text)
        issues.append(panel_issue)

    for item in text_boxes:
        element = item["element"]
        bbox = item["bbox"]
        text = textify(item.get("text")).strip()
        font_size = text_font_size(element) or 14.0
        required_width, required_height, required_lines = text_required_size(text, font_size, bbox["width"])
        if text and (required_width > bbox["width"] + TEXT_CONTAINER_TOLERANCE and required_lines <= 1 or required_height > bbox["height"] + TEXT_CONTAINER_TOLERANCE):
            overflow_issue = issue(
                "error",
                "text_container_overflow",
                "visible text does not fit within its text box",
                element,
                "Increase the text box, shorten the wording, split the sentence into multiple lines, or reduce font size before creating the slide.",
            )
            overflow_issue["required_width"] = round(required_width, 2)
            overflow_issue["required_height"] = round(required_height, 2)
            issues.append(overflow_issue)

        center_x, center_y = bbox_center(bbox)
        containing = [
            (container_element, container_bbox)
            for container_element, container_bbox in containers
            if point_in_bbox(center_x, center_y, container_bbox) and container_bbox["width"] * container_bbox["height"] >= bbox["width"] * bbox["height"]
        ]
        if not containing:
            continue
        container_element, container_bbox = min(containing, key=lambda item_: item_[1]["width"] * item_[1]["height"])
        if not bbox_contains(container_bbox, bbox, tolerance=TEXT_CONTAINER_TOLERANCE):
            overflow_issue = issue(
                "error",
                "text_container_overflow",
                "text box extends beyond its nearest visual container",
                element,
                "Make the card, pill, footer bar, or table band large enough for the visible text, or move the text back inside the container.",
            )
            overflow_issue["container_element_id"] = get_attr(container_element, "id")
            issues.append(overflow_issue)

    decorative_rules = [(element, bbox) for element, bbox in shaped if is_decorative_horizontal_rule(element, bbox)]
    for headline in headlines:
        headline_bbox = headline["bbox"]
        for rule_element, rule_bbox in decorative_rules:
            if bbox_bottom(rule_bbox) > headline_bbox["y"]:
                continue
            if not horizontal_overlap(rule_bbox, headline_bbox, tolerance=12):
                continue
            gap = headline_bbox["y"] - bbox_bottom(rule_bbox)
            if 0 <= gap < DECORATIVE_LINE_HEADLINE_MIN_GAP:
                pressure_issue = issue(
                    "warning",
                    "decorative_line_title_pressure",
                    "decorative horizontal rule is too close to the headline",
                    headline["element"],
                    "Keep decorative line groups at least 16px above headline text, preferably 20-28px for large titles.",
                )
                pressure_issue["rule_element_id"] = get_attr(rule_element, "id")
                pressure_issue["gap"] = round(gap, 2)
                issues.append(pressure_issue)
                break

    connectors = [(element, line_segments_for_element(element)) for element, _bbox in shaped if is_connector_element(element)]
    for connector_element, segments in connectors:
        if not segments:
            continue
        for item in text_boxes:
            text_bbox = expand_bbox(item["bbox"], 2.0)
            if any(line_segment_intersects_bbox(segment, text_bbox) for segment in segments):
                connector_issue = issue(
                    "error",
                    "connector_crosses_text",
                    "connector line/path crosses a visible text box",
                    connector_element,
                    "Route leader lines around text boxes, terminate them at card edges, or shorten them so they do not pass through titles, central labels, or callout copy.",
                )
                connector_issue["text_element_id"] = get_attr(item["element"], "id")
                issues.append(connector_issue)
                break

    return issues


def validate_visible_svg_text_leaks(text_boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    style_terms: list[str] = []
    for preset in STYLE_PRESET_CATALOG.values():
        for value in [preset.get("style_id"), preset.get("display_name"), preset.get("source_token")]:
            term = textify(value).strip()
            if term:
                style_terms.append(term)
    style_terms.append("beautiful-feishu-whiteboard")

    for item in text_boxes:
        text = textify(item.get("text")).strip()
        if not text:
            continue
        lower = text.lower()
        leaked_style_terms = [term for term in style_terms if term.lower() in lower]
        if leaked_style_terms or TOOL_LEAK_RE.search(text) or PATH_LIKE_RE.search(text):
            element = item.get("element")
            issues.append(
                issue(
                    "error",
                    "visible_svg_metadata_leak",
                    "visible SVG text must not expose style preset names, source tokens, prompts, tool names, or local file paths",
                    element if isinstance(element, ET.Element) else None,
                    "Keep preset metadata and generation notes in slide_plan.json; visible SVG text should only contain user-facing deck content.",
                )
            )
    return issues


def element_identifier_text(element: ET.Element) -> str:
    parts = [
        get_attr(element, "id") or "",
        get_attr(element, "class") or "",
        get_attr(element, "aria-label") or "",
    ]
    return " ".join(part for part in parts if part).lower()


def text_font_size(element: ET.Element) -> float | None:
    for child in element.iter():
        style = get_attr(child, "style") or ""
        match = FONT_SIZE_RE.search(style)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def element_writing_mode_text(element: ET.Element) -> str:
    parts: list[str] = []
    for child in element.iter():
        for key in ["writing-mode", "text-orientation", "transform"]:
            value = get_attr(child, key)
            if value:
                parts.append(value)
        style = parse_style_props(get_attr(child, "style"))
        for key in ["writing-mode", "text-orientation", "transform"]:
            value = style.get(key)
            if value:
                parts.append(value)
    return " ".join(parts)


def is_vertical_text_element(element: ET.Element) -> bool:
    mode = element_writing_mode_text(element)
    return bool(VERTICAL_WRITING_MODE_RE.search(mode) or ROTATED_TEXT_RE.search(mode))


def is_card_like_rect(element: ET.Element, bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    if local_name(element.tag) != "rect" or svg_role(element) != "shape":
        return False
    if is_background_bbox(bbox, canvas_width, canvas_height):
        return False
    return 70 <= bbox["width"] <= 420 and 40 <= bbox["height"] <= 240


def element_is_hidden(element: ET.Element) -> bool:
    return get_attr(element, INTERNAL_INHERITED_HIDDEN_ATTR) == "1" or element_self_hidden(element)


def element_has_clip_risk(element: ET.Element) -> bool:
    if get_attr(element, INTERNAL_INHERITED_CLIP_ATTR) == "1":
        return True
    for child in element.iter():
        if element_self_clip_risk(child):
            return True
    return False


def validate_text_visibility_clipping(text_boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in text_boxes:
        element = item.get("element")
        if not isinstance(element, ET.Element):
            continue
        text = textify(item.get("text")).strip()
        if not text:
            continue
        if element_is_hidden(element):
            issues.append(
                issue(
                    "error",
                    "hidden_visible_text",
                    "visible slide text is declared in a hidden or transparent text box",
                    element,
                    "Do not rely on display:none, visibility:hidden, or near-zero opacity for visible content; remove the text or make the box visible.",
                )
            )
            continue
        if not element_has_clip_risk(element):
            continue
        bbox = item["bbox"]
        font_size = text_font_size(element) or 14.0
        required_width, required_height, required_lines = text_required_size(text, font_size, bbox["width"])
        if required_lines > 1 and required_height >= bbox["height"] * TEXT_CLIP_RISK_RATIO or required_width > bbox["width"] + TEXT_CONTAINER_TOLERANCE:
            clipped_issue = issue(
                "error",
                "clipped_visible_text",
                "visible slide text is likely clipped by overflow/clip-path/mask",
                element,
                "Increase the text box, shorten the content, or remove clipping from text-bearing foreignObject nodes.",
            )
            clipped_issue["required_width"] = round(required_width, 2)
            clipped_issue["required_height"] = round(required_height, 2)
            issues.append(clipped_issue)
    return issues


def add_primitive_area(out: dict[str, float], primitive: str, area: float) -> None:
    if area <= 0:
        return
    out[primitive] = out.get(primitive, 0.0) + area


def primitive_signal_area(element: ET.Element, bbox: dict[str, float]) -> float:
    name = local_name(element.tag)
    area = bbox["width"] * bbox["height"]
    if name in {"line", "path"}:
        return max(area, max(bbox["width"], bbox["height"]) * 4.0)
    return area


def summarize_visual_primitives(root: ET.Element, elements: list[ET.Element], text_boxes: list[dict[str, Any]], canvas_width: float, canvas_height: float) -> dict[str, Any]:
    counts = {
        "path": 0,
        "line": 0,
        "rect": 0,
        "circle": 0,
        "ellipse": 0,
        "image": 0,
        "foreignObject": 0,
        "chart_marker": 0,
        "card_like_rect": 0,
        "small_shape": 0,
        "bar_like_rect": 0,
    }
    identifiers: list[str] = []
    semi_transparent_rects: list[dict[str, float]] = []
    primitive_areas: dict[str, float] = {}
    hidden_counts: dict[str, int] = {}

    for element in elements:
        name = local_name(element.tag)
        if name in counts:
            counts[name] += 1
        identifier = element_identifier_text(element)
        if identifier:
            identifiers.append(identifier)
        bbox = bbox_for_element(element)
        if bbox is None:
            if element_is_hidden(element):
                for primitive in ["path"] if name == "path" else []:
                    hidden_counts[primitive] = hidden_counts.get(primitive, 0) + 1
            continue
        area = bbox["width"] * bbox["height"]
        signal_area = primitive_signal_area(element, bbox)
        hidden = element_is_hidden(element)
        element_primitives: set[str] = set()
        if name == "path":
            element_primitives.update({"path", "geometric_shape"})
        elif name == "line":
            element_primitives.update({"annotation", "geometric_shape"})
        elif name in {"rect", "circle", "ellipse"}:
            element_primitives.add("geometric_shape")
        elif name == "image":
            element_primitives.add("image")
        elif name == "foreignObject" and svg_shape_type(element) == "text":
            element_primitives.add("typography")
        if is_card_like_rect(element, bbox, canvas_width, canvas_height):
            counts["card_like_rect"] += 1
        if svg_role(element) == "shape" and name in {"rect", "circle", "ellipse", "line", "path"} and area <= 3600:
            counts["small_shape"] += 1
            element_primitives.add("icon")
        if name == "rect" and 8 <= bbox["width"] <= 240 and 4 <= bbox["height"] <= 70:
            counts["bar_like_rect"] += 1
            element_primitives.add("micro_chart")
        if name == "rect":
            color = fill_color(element)
            if color is not None and 0.05 < color[3] < 0.85:
                semi_transparent_rects.append(bbox)
                element_primitives.add("image_overlay")
        if re.search(r"(texture|grid|dot|scan|pattern)", identifier):
            element_primitives.add("texture")
        if re.search(r"(spotlight|hotspot|highlight|focus)", identifier):
            element_primitives.add("spotlight")
        if re.search(r"(route|journey|flow|loop|path)", identifier):
            element_primitives.add("flow")
        for primitive in element_primitives:
            if hidden:
                hidden_counts[primitive] = hidden_counts.get(primitive, 0) + 1
            else:
                add_primitive_area(primitive_areas, primitive, signal_area)

    root_identifiers = " ".join(identifiers)
    gradients = sum(1 for element in root.iter() if local_name(element.tag) in {"linearGradient", "radialGradient"})
    gradient_refs = sum(
        1
        for element in root.iter()
        if "url(#" in textify(get_attr(element, "fill") or get_attr(element, "stroke") or get_attr(element, "style"))
    )
    patterns = sum(1 for element in root.iter() if local_name(element.tag) == "pattern")
    masks = sum(1 for element in root.iter() if local_name(element.tag) in {"mask", "clipPath"})
    symbols = sum(1 for element in root.iter() if local_name(element.tag) in {"symbol", "use"})
    filters = sum(1 for element in root.iter() if local_name(element.tag) == "filter")
    filter_refs = sum(1 for element in root.iter() if get_attr(element, "filter") or "filter:" in (get_attr(element, "style") or ""))
    mask_refs = sum(1 for element in root.iter() if get_attr(element, "mask") or get_attr(element, "clip-path") or "clip-path:" in (get_attr(element, "style") or ""))
    image_opacity = sum(
        1
        for element in root.iter()
        if local_name(element.tag) == "image"
        and (get_attr(element, "opacity") is not None or STYLE_IMAGE_OPACITY_RE.search(get_attr(element, "style") or ""))
    )
    dasharrays = sum(
        1
        for element in root.iter()
        if get_attr(element, "stroke-dasharray") is not None or STYLE_STROKE_DASHARRAY_RE.search(get_attr(element, "style") or "")
    )
    counts["chart_marker"] = len(chart_marker_elements(root))
    large_text = 0
    for item in text_boxes:
        bbox = item["bbox"]
        font_size = text_font_size(item["element"]) or 0
        if font_size >= 42 or (bbox["width"] >= 300 and bbox["height"] >= 76):
            large_text += 1

    primitives: set[str] = set()
    if counts["path"]:
        primitives.add("path")
        primitives.add("geometric_shape")
    if counts["line"]:
        primitives.add("annotation")
        primitives.add("geometric_shape")
    if counts["rect"] or counts["circle"] or counts["ellipse"]:
        primitives.add("geometric_shape")
    if counts["image"]:
        primitives.add("image")
    if counts["image"] and semi_transparent_rects:
        primitives.add("image_overlay")
    if gradients:
        primitives.add("gradient")
    if gradients and gradient_refs:
        primitive_areas["gradient"] = max(primitive_areas.get("gradient", 0.0), canvas_width * canvas_height * 0.01)
    if filters or filter_refs:
        primitives.add("spotlight")
    if large_text:
        primitives.add("typography")
    if counts["bar_like_rect"] >= 3 or re.search(r"(chart|metric|score|kpi|bar)", root_identifiers):
        primitives.add("micro_chart")
    if counts["chart_marker"]:
        primitives.add("micro_chart")
    if counts["card_like_rect"] >= 3 and (counts["bar_like_rect"] >= 2 or re.search(r"(dashboard|console|panel|metric)", root_identifiers)):
        primitives.add("dashboard")
    if counts["small_shape"] >= 6 or re.search(r"(icon|glyph|capability)", root_identifiers):
        primitives.add("icon")
    if counts["path"] and (counts["circle"] + counts["ellipse"] >= 2 or re.search(r"(route|journey|flow|loop|path)", root_identifiers)):
        primitives.add("flow")
    if counts["small_shape"] >= 10 or re.search(r"(texture|grid|dot|scan|pattern)", root_identifiers):
        primitives.add("texture")
    if counts["line"] or counts["path"] or re.search(r"(annotation|callout|label|legend)", root_identifiers):
        if text_boxes:
            primitives.add("annotation")
    if re.search(r"(spotlight|hotspot|highlight|focus)", root_identifiers):
        primitives.add("spotlight")
    if re.search(r"(brand|system|identity)", root_identifiers):
        primitives.add("brand_system")

    effects: set[str] = set()
    if counts["path"]:
        effects.add("path")
    if counts["line"] or counts["path"]:
        effects.add("connector_flow")
    if counts["bar_like_rect"] >= 3:
        effects.add("chart_geometry")
    if counts["chart_marker"]:
        effects.add("chart_geometry")
    if gradients:
        effects.add("gradient")
    if counts["image"] and semi_transparent_rects:
        effects.add("image_overlay")
    if filters or filter_refs:
        effects.add("filter")
        effects.add("spotlight")
    if patterns:
        effects.add("pattern")
    if masks or mask_refs:
        effects.add("mask_clip")
    if symbols:
        effects.add("symbol")
    if image_opacity:
        effects.add("image_opacity")
    if dasharrays:
        effects.add("stroke_dasharray")
    if counts["small_shape"] >= 10 or re.search(r"(texture|grid|dot|scan|pattern)", root_identifiers):
        effects.add("texture")
    if text_boxes:
        effects.add("typography")
    if re.search(r"(watermark|page-mark|ghost)", root_identifiers):
        effects.add("watermark_text")

    return {
        "present": sorted(primitives),
        "counts": counts,
        "primitive_areas": {key: round(value, 2) for key, value in sorted(primitive_areas.items())},
        "hidden_counts": dict(sorted(hidden_counts.items())),
        "gradient_count": gradients,
        "gradient_ref_count": gradient_refs,
        "filter_count": filters + filter_refs,
        "effects": sorted(effects),
    }


def validate_xml_like_layout(elements: list[ET.Element], text_boxes: list[dict[str, Any]], primitive_summary: dict[str, Any]) -> list[dict[str, Any]]:
    counts = primitive_summary["counts"]
    present = set(primitive_summary["present"])
    svg_native = present & {"path", "gradient", "image", "image_overlay", "annotation", "micro_chart", "dashboard", "icon", "texture", "spotlight", "flow"}
    if counts["card_like_rect"] >= 3 and len(text_boxes) >= 3 and not svg_native:
        return [
            {
                "level": "error",
                "code": "xml_like_svg_layout",
                "message": "SVG page degenerates into card-like rect + text layout without SVG-native visual primitives",
                "hint": "Use a visual_recipe with path, gradient, image overlay, annotation, icon system, micro chart, texture, spotlight, or flow primitives; otherwise prefer the XML/SXSD path.",
            }
        ]
    return []


def validate_visual_quality(elements: list[ET.Element]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    dark_backings: list[dict[str, Any]] = []
    node_containers: list[dict[str, Any]] = []

    for element in elements:
        name = local_name(element.tag)
        role = svg_role(element)
        bbox = bbox_for_element(element)
        if bbox is None:
            continue

        if role == "shape" and name in {"rect", "circle", "ellipse", "path"}:
            color = fill_color(element)
            if color is not None and is_dark_backing_color(color):
                dark_backings.append({"element": element, "bbox": bbox})

        if role == "shape" and name in {"circle", "ellipse"} and 16 <= bbox["width"] <= 140 and 16 <= bbox["height"] <= 140:
            node_containers.append({"element": element, "bbox": bbox})

        if name != "foreignObject" or role != "shape" or svg_shape_type(element) != "text":
            continue
        if not "".join(element.itertext()).strip():
            continue

        color = text_color(element)
        if color is not None and is_light_text_color(color):
            if not any(bbox_contains(backing["bbox"], bbox) for backing in dark_backings):
                issues.append(
                    issue(
                        "error",
                        "light_text_without_dark_backing",
                        "light text must be fully contained by an explicit dark backing shape",
                        element,
                        "Keep white/light text inside a dark rect/card/overlay, or switch to dark text before the text crosses onto a light image or white background.",
                    )
                )

        center_x, center_y = bbox_center(bbox)
        containing_nodes = [container for container in node_containers if point_in_bbox(center_x, center_y, container["bbox"])]
        if containing_nodes:
            container = max(containing_nodes, key=lambda item: item["bbox"]["width"] * item["bbox"]["height"])
            container_bbox = container["bbox"]
            if bbox["width"] > container_bbox["width"] + 1 or bbox["height"] > container_bbox["height"] + 1:
                overflow_issue = issue(
                    "error",
                    "node_text_overflow",
                    "text inside a circle/ellipse node must fit within the node bounds",
                    element,
                    "Put only short labels inside round nodes; move explanations to separate callout cards, legends, or a mechanism table.",
                )
                container_id = get_attr(container["element"], "id")
                if container_id:
                    overflow_issue["container_element_id"] = container_id
                issues.append(overflow_issue)

    return issues


def validate_styles(root: ET.Element) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for element in root.iter():
        style = get_attr(element, "style") or ""
        if FONT_SHORTHAND_RE.search(style):
            issues.append(
                issue(
                    "error",
                    "font_shorthand",
                    'style must not use "font:" shorthand',
                    element,
                    "Use explicit font-size, font-weight, font-family, color, line-height, and text-align properties.",
                )
            )
        name = local_name(element.tag)
        if name in {"circle", "ellipse"} and (get_attr(element, "stroke-width") is not None or STYLE_STROKE_WIDTH_RE.search(style)):
            issues.append(
                issue(
                    "warning",
                    "ellipse_stroke_width_unstable",
                    "<circle>/<ellipse> stroke-width may be downgraded during SVGlide conversion",
                    element,
                    "Use a two-shape ring, or convert the outline to a path/rect when border width is visually important.",
                )
            )
        if get_attr(element, "stroke-dasharray") is not None or STYLE_STROKE_DASHARRAY_RE.search(style):
            identifier = element_identifier_text(element)
            if KEY_PATH_RE.search(identifier):
                issues.append(
                    issue(
                        "error",
                        "stroke_dasharray_key_path",
                        "key routes, loops, flows, timelines, and rails must not rely on stroke-dasharray",
                        element,
                        "Use explicit short line segments or filled dot markers for important routes before calling slides +create-svg.",
                    )
                )
                continue
            issues.append(
                issue(
                    "warning",
                    "stroke_dasharray_unstable",
                    "stroke-dasharray may be downgraded during SVGlide conversion",
                    element,
                    "Use explicit short line segments or filled dot markers when dashed routes are visually important.",
                )
            )
    return issues


def validate_paths(elements: list[ET.Element]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for element in elements:
        if local_name(element.tag) != "path" or svg_role(element) != "shape":
            continue
        data = get_attr(element, "d") or ""
        without_numbers = PATH_NUMBER_RE.sub("", data)
        has_command = False
        for char in without_numbers:
            if char in ", \t\r\n":
                continue
            if char in "MLHVZCQmlhvzcq":
                has_command = True
                continue
            issues.append(
                issue(
                    "error",
                    "unsupported_path_command",
                    f'unsupported path command or character "{char}"',
                    element,
                    "Use only M/L/H/V/C/Q/Z path commands.",
                )
            )
            break
        if not has_command:
            issues.append(issue("error", "missing_path_command", 'path attribute "d" must include M/L/H/V/C/Q/Z commands', element))
    return issues


PLAN_STRUCTURED_RE = re.compile(
    r"(architecture|atlas|board|canvas|cards|chart|cohort|comparison|dashboard|flow|funnel|grid|heatmap|lane|map|matrix|model|network|pipeline|process|pyramid|quadrant|roadmap|route|scorecard|stack|swimlane|system|table|timeline)",
    re.IGNORECASE,
)
CONTENT_DENSITY_KIND_RE = re.compile(r"(architecture|comparison|dashboard|flow|map|matrix|risk[_ -]?grid|scorecard|table|timeline)", re.IGNORECASE)
CONTENT_DENSITY_COUNT_RE = re.compile(r"(?:>=|=>|at\s+least|min(?:imum)?|不少于)\s*([0-9]+)|([0-9]+)\s*(?:\+|or\s+more)", re.IGNORECASE)
PLAN_CLOSING_RE = re.compile(r"(closing|conclusion|q-and-a|q&a|summary|thanks|致谢|总结|展望|下一步|行动号召|启动)", re.IGNORECASE)
PLAN_MISSING_SOURCE_RE = re.compile(r"(missing|unavailable|pending|缺失|待补|待从|未提供|来源不足)", re.IGNORECASE)
PLAN_SOURCE_GUARD_RE = re.compile(r"(no numeric|source guard|pending|待补|待从|缺失|来源|未提供|不编造|不虚构|占位)", re.IGNORECASE)
NO_ASSET_RE = re.compile(r"(none|no[_ -]?asset|no[_ -]?image|not[_ -]?needed|无|不需要)", re.IGNORECASE)


def plan_issue(level: str, code: str, message: str, slide: dict[str, Any] | None = None, hint: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"level": level, "code": code, "message": message}
    if slide is not None and "page" in slide:
        out["page"] = slide.get("page")
    if hint:
        out["hint"] = hint
    return out


def textify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(textify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(textify(item) for item in value.values())
    return str(value)


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", textify(value).strip().lower()).strip("_")


def normalize_primitive(value: Any) -> str:
    name = normalize_name(value)
    return PRIMITIVE_ALIASES.get(name, name)


def normalize_primitives(value: Any) -> set[str]:
    if isinstance(value, list):
        return {normalize_primitive(item) for item in value if normalize_primitive(item)}
    if isinstance(value, str):
        parts = [part for part in re.split(r"[,/|;\s]+", value) if part]
        return {normalize_primitive(part) for part in parts if normalize_primitive(part)}
    return set()


def normalize_effect(value: Any) -> str:
    name = normalize_name(value)
    return EFFECT_ALIASES.get(name, name)


def normalize_effects(value: Any) -> set[str]:
    if isinstance(value, list):
        out: set[str] = set()
        for item in value:
            if isinstance(item, dict):
                effect = normalize_effect(item.get("effect") or item.get("name") or item.get("type"))
            else:
                effect = normalize_effect(item)
            if effect:
                out.add(effect)
        return out
    if isinstance(value, str):
        parts = [part for part in re.split(r"[,/|;\s]+", value) if part]
        return {normalize_effect(part) for part in parts if normalize_effect(part)}
    return set()


def nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def style_preset_id_from(value: Any) -> str:
    if isinstance(value, str):
        return normalize_name(value)
    if not isinstance(value, dict):
        return ""
    for key in ["preset_id", "style_id", "id", "style_preset"]:
        preset_id = normalize_name(value.get(key))
        if preset_id:
            return preset_id
    style_binding = value.get("style_binding")
    if isinstance(style_binding, dict):
        preset_id = style_preset_id_from(style_binding)
        if preset_id:
            return preset_id
    return ""


def deck_style_preset_id(plan: dict[str, Any]) -> str:
    for value in [
        plan.get("style_preset"),
        plan.get("style_binding"),
        nested_dict(plan.get("style_system")).get("style_preset"),
        nested_dict(plan.get("style_system")).get("style_binding"),
        nested_dict(plan.get("theme_system")).get("style_preset"),
        nested_dict(plan.get("theme_system")).get("style_binding"),
    ]:
        preset_id = style_preset_id_from(value)
        if preset_id:
            return preset_id
    return ""


def slide_style_preset_id(slide: dict[str, Any]) -> str:
    for value in [slide.get("style_preset"), slide.get("style_binding"), nested_dict(slide.get("visual_plan")).get("style_binding")]:
        preset_id = style_preset_id_from(value)
        if preset_id:
            return preset_id
    return ""


def style_system(plan: dict[str, Any]) -> dict[str, Any]:
    system = plan.get("style_system")
    if isinstance(system, dict):
        return system
    theme = plan.get("theme_system")
    if isinstance(theme, dict):
        return theme
    return {}


def validation_profile(plan: dict[str, Any]) -> dict[str, Any]:
    profile = plan.get("validation_profile")
    return profile if isinstance(profile, dict) else {}


def seed_gate_level(plan: dict[str, Any]) -> str:
    profile = validation_profile(plan)
    drift_policy = normalize_name(profile.get("drift_policy") or profile.get("seed_policy") or profile.get("mode"))
    if profile.get("strict") is True or drift_policy in {"error", "errors", "strict", "fail", "fail_closed"}:
        return "error"
    return "warning"


def slide_visual_plan(slide: dict[str, Any]) -> dict[str, Any]:
    visual_plan = slide.get("visual_plan")
    if isinstance(visual_plan, dict):
        merged = dict(slide)
        merged.update(visual_plan)
        return merged
    return slide


def has_effect_fallback(slide: dict[str, Any], effect: str) -> bool:
    candidates = [
        slide.get("effect_fallbacks"),
        slide.get("svg_effect_fallbacks"),
        slide.get("safe_rewrite"),
        slide.get("recipe_fallback"),
        slide.get("fallback_policy"),
        nested_dict(slide.get("visual_plan")).get("effect_fallbacks"),
        nested_dict(slide.get("visual_plan")).get("safe_rewrite"),
        nested_dict(slide.get("visual_plan")).get("fallback_policy"),
    ]
    text = " ".join(textify(value) for value in candidates)
    if not text.strip():
        return False
    normalized_text = normalize_name(text)
    return "fallback" in normalized_text or "rewrite" in normalized_text or effect in normalized_text


def has_private_fallback_field(slide: dict[str, Any]) -> bool:
    visual_plan = nested_dict(slide.get("visual_plan"))
    keys = ["effect_fallbacks", "svg_effect_fallbacks", "safe_rewrite", "recipe_fallback", "fallback_policy"]
    return any(textify(slide.get(key)).strip() or textify(visual_plan.get(key)).strip() for key in keys)


def has_private_exemption_field(slide: dict[str, Any]) -> bool:
    visual_plan = nested_dict(slide.get("visual_plan"))
    keys = ["exemption", "exemptions", "exemption_policy", "preflight_exemption", "svg_preflight_exemption"]
    return any(textify(slide.get(key)).strip() or textify(visual_plan.get(key)).strip() for key in keys)


def visible_slide_text(slide: dict[str, Any]) -> str:
    visual_plan = nested_dict(slide.get("visual_plan"))
    parts = [textify(slide.get(key)) for key in VISIBLE_PLAN_TEXT_KEYS]
    parts.extend(textify(visual_plan.get(key)) for key in VISIBLE_PLAN_TEXT_KEYS)
    return " ".join(part for part in parts if part).strip()


def visible_text_char_count(value: Any) -> int:
    return len(re.sub(r"\s+", " ", textify(value)).strip())


def capacity_visible_text(slide: dict[str, Any]) -> str:
    return " ".join(textify(slide.get(key)) for key in CAPACITY_PLAN_TEXT_KEYS if textify(slide.get(key)).strip()).strip()


def slide_seed_id(slide: dict[str, Any]) -> str:
    for key in ["seed_id", "seed", "svg_seed", "template_seed", "layout_seed", "visual_seed"]:
        seed = normalize_name(slide.get(key))
        if seed:
            return seed
    return ""


def slide_text_capacity_value(slide: dict[str, Any]) -> Any:
    for key in ["content_budget", "text_capacity", "text_budget", "text_capacity_contract"]:
        if key in slide:
            return slide.get(key)
    return None


def slide_layout_boxes(slide: dict[str, Any]) -> list[Any]:
    raw = slide.get("layout_boxes")
    if raw is None:
        layout = slide.get("layout")
        if isinstance(layout, dict):
            raw = layout.get("boxes") or layout.get("layout_boxes")
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        boxes = raw.get("boxes")
        if isinstance(boxes, list):
            return boxes
    return []


def slide_layout_skeleton(slide: dict[str, Any]) -> dict[str, Any]:
    raw = slide.get("layout_skeleton") or slide.get("layoutSkeleton")
    return raw if isinstance(raw, dict) else {}


def slide_layout_skeleton_id(slide: dict[str, Any]) -> str:
    for value in [
        slide.get("layout_skeleton_id"),
        slide.get("skeleton_id"),
        nested_dict(slide.get("layout_skeleton")).get("id"),
        nested_dict(slide.get("layoutSkeleton")).get("id"),
    ]:
        skeleton_id = normalize_name(value)
        if skeleton_id:
            return skeleton_id
    return ""


def positive_int_value(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def capacity_limit_from_mapping(data: dict[str, Any], keys: set[str]) -> int | None:
    for key, value in data.items():
        if normalize_name(key) in keys:
            parsed = positive_int_value(value)
            if parsed is not None:
                return parsed
    return None


def parse_capacity_string(value: str) -> dict[str, int]:
    out: dict[str, int] = {}
    pairs = [
        ("max_visible_chars", r"(?:max[_ -]?)?(?:visible[_ -]?)?(?:chars|characters)\s*(?:<=|=|:)?\s*([0-9]+)"),
        ("max_text_boxes", r"max[_ -]?(?:text[_ -]?)?(?:boxes|box_count)\s*(?:<=|=|:)?\s*([0-9]+)"),
        ("min_text_boxes", r"min[_ -]?(?:text[_ -]?)?(?:boxes|box_count)\s*(?:>=|=|:)?\s*([0-9]+)"),
    ]
    lower = value.lower()
    for key, pattern in pairs:
        match = re.search(pattern, lower)
        if not match:
            continue
        parsed = positive_int_value(match.group(1))
        if parsed is not None:
            out[key] = parsed
    return out


def capacity_limits_from_value(capacity: Any) -> dict[str, int]:
    limits: dict[str, int] = {}
    if isinstance(capacity, dict):
        aliases = {
            "max_visible_chars": {"max_visible_chars", "max_chars", "max_characters", "visible_chars"},
            "max_text_boxes": {"max_text_boxes", "max_boxes", "max_box_count"},
            "min_text_boxes": {"min_text_boxes", "min_boxes", "required_text_boxes", "required_boxes"},
            "title": {"title", "max_title_chars", "title_chars"},
            "body": {"body", "max_body_chars", "body_chars"},
            "footer": {"footer", "max_footer_chars", "footer_chars"},
        }
        for target, keys in aliases.items():
            parsed = capacity_limit_from_mapping(capacity, keys)
            if parsed is not None:
                limits[target] = parsed
    elif isinstance(capacity, str):
        limits.update(parse_capacity_string(capacity))
    elif capacity is not None:
        parsed = positive_int_value(capacity)
        if parsed is not None:
            limits["max_visible_chars"] = parsed
    return limits


def text_capacity_limits(capacity: Any, seed_data: dict[str, Any] | None = None) -> dict[str, int]:
    limits: dict[str, int] = {}
    for key in ["content_budget", "default_text_capacity"]:
        default_capacity = seed_data.get(key) if seed_data else None
        if isinstance(default_capacity, dict):
            limits.update(capacity_limits_from_value(default_capacity))
    for key, value in capacity_limits_from_value(capacity).items():
        if key in limits and key in CAPACITY_MAX_KEYS:
            limits[key] = min(limits[key], value)
        elif key in limits and key in CAPACITY_MIN_KEYS:
            limits[key] = max(limits[key], value)
        else:
            limits[key] = value
    return limits


def slide_text_budget_by_role(slide: dict[str, Any]) -> dict[str, Any]:
    raw = slide.get("text_budget_by_role") or slide.get("role_text_budget") or slide.get("roleTextBudget")
    return raw if isinstance(raw, dict) else {}


def role_budget_by_role(budget: dict[str, Any], seed_data: dict[str, Any] | None = None) -> dict[str, dict[str, int]]:
    merged: dict[str, dict[str, int]] = {}
    for source in [seed_data.get("text_budget_by_role") if seed_data else None, budget]:
        if not isinstance(source, dict):
            continue
        for role, raw_limits in source.items():
            normalized_role = normalize_name(role)
            if not normalized_role:
                continue
            raw = raw_limits if isinstance(raw_limits, dict) else {"max_chars": raw_limits}
            limits: dict[str, int] = dict(merged.get(normalized_role, {}))
            aliases = {
                "max_chars": {"max_chars", "chars", "max_visible_chars", "max_characters"},
                "max_lines": {"max_lines", "lines"},
                "max_boxes": {"max_boxes", "max_text_boxes", "boxes"},
                "min_font_px": {"min_font_px", "min_font_size", "min_font"},
            }
            for target, keys in aliases.items():
                parsed = capacity_limit_from_mapping(raw, keys)
                if parsed is None:
                    continue
                if target.startswith("max_") and target in limits:
                    limits[target] = min(limits[target], parsed)
                else:
                    limits[target] = parsed
            merged[normalized_role] = limits
    return merged


def role_budget_loosenings(budget: dict[str, Any], seed_data: dict[str, Any] | None = None) -> list[str]:
    if not seed_data:
        return []
    seed_limits = role_budget_by_role({}, seed_data)
    plan_limits = role_budget_by_role(budget, None)
    loosened: list[str] = []
    for role, limits in plan_limits.items():
        seed_role_limits = seed_limits.get(role)
        if not seed_role_limits:
            continue
        for key, value in limits.items():
            seed_value = seed_role_limits.get(key)
            if seed_value is None:
                continue
            if key.startswith("max_") and value > seed_value:
                loosened.append(f"{role}.{key} {value}>{seed_value}")
            elif key.startswith("min_") and value < seed_value:
                loosened.append(f"{role}.{key} {value}<{seed_value}")
    return loosened


def role_plan_text(slide: dict[str, Any], role: str) -> str:
    keys_by_role = {
        "title": ["title", "headline", "heading", "subtitle"],
        "headline": ["headline", "title"],
        "kicker": ["kicker", "eyebrow", "section"],
        "body": ["body", "bullets", "copy", "paragraphs", "key_message", "takeaway", "one_idea"],
        "callout": ["callout", "callouts", "cta", "takeaway"],
        "label": ["label", "labels", "caption", "captions", "legend", "legends"],
        "caption": ["caption", "captions", "label", "labels"],
        "metric": ["metric", "metrics", "kpi", "kpis"],
        "footer": ["footer", "source_note", "visible_source_note", "legal"],
    }
    keys = keys_by_role.get(role, [role])
    return " ".join(textify(slide.get(key)) for key in keys if textify(slide.get(key)).strip()).strip()


def capacity_budget_loosenings(capacity: Any, seed_data: dict[str, Any] | None = None) -> list[str]:
    if not seed_data:
        return []
    seed_limits = text_capacity_limits(None, seed_data)
    plan_limits = capacity_limits_from_value(capacity)
    loosened: list[str] = []
    for key, value in plan_limits.items():
        seed_value = seed_limits.get(key)
        if seed_value is None:
            continue
        if key in CAPACITY_MAX_KEYS and value > seed_value:
            loosened.append(f"{key} {value}>{seed_value}")
        elif key in CAPACITY_MIN_KEYS and value < seed_value:
            loosened.append(f"{key} {value}<{seed_value}")
    return loosened


def layout_box_role(box: dict[str, Any]) -> str:
    return textify(box.get("role") or box.get("type") or box.get("id") or box.get("name")).strip()


def layout_box_dimension(box: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = box.get(key)
        if isinstance(value, bool) or value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def layout_box_has_positive_bbox(box: dict[str, Any]) -> bool:
    x = layout_box_dimension(box, "x", "left")
    y = layout_box_dimension(box, "y", "top")
    width = layout_box_dimension(box, "width", "w")
    height = layout_box_dimension(box, "height", "h")
    return x is not None and y is not None and width is not None and height is not None and width > 0 and height > 0


def is_text_layout_box(box: dict[str, Any]) -> bool:
    return bool(TEXT_LAYOUT_ROLE_RE.search(layout_box_role(box)))


def layout_box_hidden_clip(box: dict[str, Any]) -> bool:
    if bool(box.get("clip") or box.get("clips") or box.get("hidden_clip")):
        return True
    for key in ["overflow", "clip_path", "clip-path", "mask"]:
        value = normalize_name(box.get(key))
        if value in {"hidden", "clip", "clipped", "mask", "masked", "true", "yes"}:
            return True
    return False


def layout_box_roles(boxes: list[Any]) -> set[str]:
    roles: set[str] = set()
    for box in boxes:
        if isinstance(box, dict):
            role = normalize_name(layout_box_role(box))
            if role:
                roles.add(role)
    return roles


def slide_reserved_bands(slide: dict[str, Any]) -> dict[str, Any]:
    raw = slide.get("reserved_bands") or slide.get("reservedBands")
    if isinstance(raw, dict):
        return raw
    return {}


def slide_footer_safe_zone(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = slide.get("footer_safe_zone") or slide.get("footerSafeZone")
    if isinstance(raw, dict):
        return raw
    seed_raw = seed_data.get("footer_safe_zone") if seed_data else None
    if isinstance(seed_raw, dict):
        return seed_raw
    footer = reserved_footer_band(slide, seed_data)
    return footer or {}


def bbox_from_mapping(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    x = layout_box_dimension(value, "x", "left")
    y = layout_box_dimension(value, "y", "top")
    width = layout_box_dimension(value, "width", "w")
    height = layout_box_dimension(value, "height", "h")
    if None in {x, y, width, height} or width is None or height is None or width <= 0 or height <= 0:
        return None
    return {"x": x or 0.0, "y": y or 0.0, "width": width, "height": height}


def footer_safe_zone_bbox(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> dict[str, float] | None:
    return bbox_from_mapping(slide_footer_safe_zone(slide, seed_data))


def footer_safe_zone_allowed_roles(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> set[str]:
    zone = slide_footer_safe_zone(slide, seed_data)
    allowed = _string_set(zone.get("allowed_roles") or zone.get("allowedRoles"))
    return {normalize_name(role) for role in allowed if normalize_name(role)} or {"footer"}


def footer_safe_zone_min_gap(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> float:
    zone = slide_footer_safe_zone(slide, seed_data)
    gap = layout_box_dimension(zone, "min_gap_above_px", "minGapAbovePx", "body_clearance_px", "bodyClearancePx")
    return gap if gap is not None else 0.0


def reserved_footer_band(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> dict[str, float] | None:
    bands = slide_reserved_bands(slide)
    footer = bbox_from_mapping(bands.get("footer"))
    if footer is not None:
        return footer
    seed_bands = seed_data.get("reserved_bands") if seed_data else None
    if isinstance(seed_bands, dict):
        return bbox_from_mapping(seed_bands.get("footer"))
    return None


def capacity_section_text(slide: dict[str, Any], section: str) -> str:
    keys_by_section = {
        "title": ["title", "headline", "kicker", "subtitle"],
        "body": ["body", "bullets", "callouts", "labels", "key_message", "takeaway", "one_idea"],
        "footer": ["footer", "source_note", "visible_source_note"],
    }
    keys = keys_by_section.get(section, [])
    return " ".join(textify(slide.get(key)) for key in keys if textify(slide.get(key)).strip()).strip()


def slide_vertical_text_policy(slide: dict[str, Any], seed_data: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = slide.get("vertical_text_policy") or slide.get("verticalTextPolicy")
    if isinstance(raw, dict):
        return raw
    seed_raw = seed_data.get("vertical_text_policy") if seed_data else None
    if isinstance(seed_raw, dict):
        return seed_raw
    return {"mode": "deny", "allowed_roles": [], "max_chars": 0, "max_lines": 0}


def vertical_text_policy_allows(policy: dict[str, Any], role: str) -> bool:
    mode = normalize_name(policy.get("mode") or policy.get("status") or "deny")
    enabled = policy.get("enabled")
    if mode in {"deny", "disabled", "forbid", "forbidden", "none"} or enabled is False:
        return False
    allowed_roles = {normalize_name(item) for item in _string_set(policy.get("allowed_roles") or policy.get("allowedRoles")) if normalize_name(item)}
    return bool(role and (role in allowed_roles or "*" in allowed_roles))


def vertical_policy_limit(policy: dict[str, Any], key: str, default: int) -> int:
    parsed = capacity_limit_from_mapping(policy, {key, key.replace("_", ""), f"max_{key}"})
    return parsed if parsed is not None else default


def is_footer_identifier(identifier: str, visible_text: str = "") -> bool:
    combined = f"{identifier} {visible_text}"
    return bool(re.search(r"(footer|source|legal|page[_ -]?num|pagination|来源|资料来源|数据来源|页码|页脚)", combined, re.IGNORECASE))


def layout_box_bboxes_by_role(boxes: list[Any]) -> dict[str, list[dict[str, float]]]:
    out: dict[str, list[dict[str, float]]] = {}
    for box in boxes:
        if not isinstance(box, dict):
            continue
        role = normalize_name(layout_box_role(box))
        bbox = bbox_from_mapping(box)
        if role and bbox is not None:
            out.setdefault(role, []).append(bbox)
    return out


def layout_box_id(box: dict[str, Any]) -> str:
    return normalize_name(box.get("id") or box.get("name") or layout_box_role(box))


def layout_box_bboxes_by_id(boxes: list[Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for box in boxes:
        if not isinstance(box, dict):
            continue
        box_id = layout_box_id(box)
        bbox = bbox_from_mapping(box)
        if box_id and bbox is not None:
            out[box_id] = bbox
    return out


def first_layout_bbox_by_role(boxes: list[Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for box in boxes:
        if not isinstance(box, dict):
            continue
        role = normalize_name(layout_box_role(box))
        bbox = bbox_from_mapping(box)
        if role and bbox is not None and role not in out:
            out[role] = bbox
    return out


def infer_text_box_role_from_layout(text_box: dict[str, Any], layout_bboxes: dict[str, list[dict[str, float]]]) -> str:
    text_bbox = bbox_from_mapping(text_box.get("bbox"))
    if text_bbox is None:
        return ""
    center_x, center_y = bbox_center(text_bbox)
    candidates: list[tuple[float, str]] = []
    for role, boxes in layout_bboxes.items():
        for box in boxes:
            if bbox_contains(box, text_bbox, tolerance=TEXT_CONTAINER_TOLERANCE) or point_in_bbox(center_x, center_y, box):
                candidates.append((box["width"] * box["height"], role))
    if not candidates:
        return ""
    return min(candidates)[1]


def seed_layout_skeleton(seed_data: dict[str, Any] | None) -> dict[str, Any]:
    if not seed_data:
        return {}
    raw = seed_data.get("layout_skeleton")
    return raw if isinstance(raw, dict) else {}


def seed_skeleton_id(seed_id: str, skeleton: dict[str, Any]) -> str:
    return normalize_name(skeleton.get("id") or f"{seed_id}_skeleton")


def skeleton_drift_issues(seed_id: str, seed_data: dict[str, Any], plan_boxes: list[Any]) -> list[str]:
    skeleton = seed_layout_skeleton(seed_data)
    if not skeleton:
        return []
    tolerance_value = layout_box_dimension(skeleton, "drift_tolerance_px", "driftTolerancePx")
    tolerance = tolerance_value if tolerance_value is not None else 24.0
    locked_roles = _string_set(skeleton.get("locked_roles"))
    if not locked_roles:
        locked_roles = {normalize_name(role) for role in seed_data.get("required_layout_box_roles", set()) if normalize_name(role)}
    seed_boxes = first_layout_bbox_by_role(seed_data.get("layout_boxes") if isinstance(seed_data.get("layout_boxes"), list) else [])
    plan_role_boxes = first_layout_bbox_by_role(plan_boxes)
    seed_boxes_by_id = layout_box_bboxes_by_id(seed_data.get("layout_boxes") if isinstance(seed_data.get("layout_boxes"), list) else [])
    plan_boxes_by_id = layout_box_bboxes_by_id(plan_boxes)
    locked_box_ids = _string_set(skeleton.get("locked_boxes") or skeleton.get("locked_box_ids") or skeleton.get("lockedBoxIds"))
    if not locked_box_ids:
        locked_box_ids = set(seed_boxes_by_id)
    drifts: list[str] = []
    for box_id in sorted(locked_box_ids):
        seed_bbox = seed_boxes_by_id.get(box_id)
        plan_bbox = plan_boxes_by_id.get(box_id)
        if seed_bbox is None:
            continue
        if plan_bbox is None:
            drifts.append(f"{seed_id}.{box_id} missing")
            continue
        for key in ["x", "y", "width", "height"]:
            if abs(plan_bbox[key] - seed_bbox[key]) > tolerance:
                drifts.append(f"{seed_id}.{box_id}.{key} {round(plan_bbox[key], 1)} != {round(seed_bbox[key], 1)} +/- {round(tolerance, 1)}")
                break
    for role in sorted(locked_roles):
        seed_bbox = seed_boxes.get(role)
        plan_bbox = plan_role_boxes.get(role)
        if seed_bbox is None or plan_bbox is None:
            continue
        for key in ["x", "y", "width", "height"]:
            if abs(plan_bbox[key] - seed_bbox[key]) > tolerance:
                drifts.append(f"{seed_id}.{role}.{key} {round(plan_bbox[key], 1)} != {round(seed_bbox[key], 1)} +/- {round(tolerance, 1)}")
                break
    return drifts


def infer_text_box_role(text_box: dict[str, Any], available_roles: set[str]) -> str:
    identifier = textify(text_box.get("identifier") or text_box.get("element_id"))
    visible_text = textify(text_box.get("text"))
    normalized = normalize_name(f"{identifier} {visible_text}")
    for role in sorted(available_roles, key=len, reverse=True):
        if role and role in normalized:
            return role
    if is_footer_identifier(identifier, visible_text):
        return "footer"
    if re.search(r"(title|headline|heading|kicker|subtitle|标题|主标题)", normalized):
        return "title"
    if re.search(r"(callout|cta|chip|badge|label|caption|标注|标签)", normalized):
        return "callout" if "callout" in available_roles else "body"
    if re.search(r"(metric|kpi|number|指标)", normalized):
        return "metric" if "metric" in available_roles else "body"
    if re.search(r"(body|copy|text|paragraph|bullet|正文|说明)", normalized):
        return "body"
    return ""


def recipe_family(recipe: str, context: dict[str, Any] | None = None) -> str:
    catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG) if context else VISUAL_RECIPE_CATALOG
    return textify(catalog.get(recipe, {}).get("family") or recipe)


def recipe_required_primitives(recipe: str, context: dict[str, Any]) -> set[str]:
    catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG)
    recipe_data = catalog.get(recipe, {})
    return set(recipe_data.get("required_primitives", set()))


def recipe_required_effects(recipe: str, context: dict[str, Any]) -> set[str]:
    catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG)
    recipe_data = catalog.get(recipe, {})
    return set(recipe_data.get("required_effects", set()))


def recipe_minimum_visible_area_ratio(recipe: str, context: dict[str, Any]) -> float:
    catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG)
    recipe_data = catalog.get(recipe, {})
    try:
        return float(recipe_data.get("minimum_visible_area_ratio", 0.002))
    except (TypeError, ValueError):
        return 0.002


def is_private_recipe(recipe: str, context: dict[str, Any]) -> bool:
    return recipe in context.get("private_id_set", set())


def selected_private_recipe_for_slide(slide: dict[str, Any], slide_index: int, context: dict[str, Any]) -> str:
    selections = context.get("recipe_selection", {})
    page = slide.get("page")
    candidates = []
    if page is not None:
        candidates.append(f"page:{page}")
    candidates.append(f"index:{slide_index}")
    for key in candidates:
        recipe = selections.get(key)
        if recipe:
            return textify(recipe).strip()
    return ""


def plan_slide_text(slide: dict[str, Any], keys: list[str] | None = None) -> str:
    if keys is None:
        return textify(slide)
    return " ".join(textify(slide.get(key)) for key in keys)


def slide_renderer_id(slide: dict[str, Any]) -> str:
    return textify(slide.get("renderer_id") or slide.get("layout_type") or slide.get("visual_structure")).strip()


def slide_layout_family(slide: dict[str, Any]) -> str:
    return textify(slide.get("layout_family")).strip()


def required_plan_primitives(slide: dict[str, Any]) -> set[str]:
    return normalize_primitives(slide.get("required_primitives"))


def density_contract_kind_count(contract: Any) -> tuple[str, int] | None:
    if isinstance(contract, dict):
        kind = normalize_name(contract.get("type") or contract.get("kind") or contract.get("structure"))
        count = None
        for key, value in contract.items():
            normalized_key = normalize_name(key)
            if normalized_key in {"min", "minimum", "min_count", "count"} or normalized_key.startswith("min_"):
                try:
                    count = int(value)
                    break
                except (TypeError, ValueError):
                    continue
        if kind and count is not None:
            return kind, count
        return None
    text = textify(contract)
    kind_match = CONTENT_DENSITY_KIND_RE.search(text)
    count_match = CONTENT_DENSITY_COUNT_RE.search(text)
    if not kind_match or not count_match:
        return None
    count_value = count_match.group(1) or count_match.group(2)
    try:
        return normalize_name(kind_match.group(1)), int(count_value)
    except (TypeError, ValueError):
        return None


def asset_contract_present(contract: Any) -> bool:
    if contract is None:
        return False
    if isinstance(contract, str):
        return bool(contract.strip())
    if isinstance(contract, list):
        return True
    if isinstance(contract, dict):
        return True
    return False


def asset_contract_has_metadata(contract: Any) -> bool:
    if isinstance(contract, list):
        return bool(contract) and all(asset_contract_has_metadata(item) for item in contract)
    if not isinstance(contract, dict):
        return False
    source_type = textify(contract.get("source_type") or contract.get("source")).strip()
    license_text = textify(contract.get("license")).strip()
    local_path = textify(contract.get("local_path") or contract.get("local_path_or_href") or contract.get("href") or contract.get("path")).strip()
    usage_page = textify(contract.get("usage_page") or contract.get("page")).strip()
    source_url = textify(contract.get("source_url") or contract.get("href")).strip()
    generated_by = textify(contract.get("generated_by")).strip()
    retrieval_query = textify(contract.get("retrieval_query") or contract.get("image_search_query") or contract.get("query")).strip()
    no_url_source_types = {"original", "procedural", "ai_generated", "user_provided", "owned", "screenshot", "web_search_preview", "public_url"}
    no_query_source_types = {"original", "procedural", "ai_generated", "user_provided", "owned"}
    normalized_source_type = source_type.lower()
    has_source_reference = source_url or generated_by or normalized_source_type in no_url_source_types
    has_query_reference = retrieval_query or normalized_source_type in no_query_source_types
    return bool(source_type and license_text and local_path and usage_page and has_source_reference and has_query_reference)


def asset_contract_declares_no_asset(contract: Any) -> bool:
    return bool(isinstance(contract, str) and NO_ASSET_RE.search(contract))


def source_density_count(kind: str, primitive_summary: dict[str, Any]) -> int:
    counts = primitive_summary.get("counts", {})
    kind = normalize_name(kind)
    if kind in {"matrix", "table", "comparison", "risk_grid"}:
        return int(counts.get("card_like_rect", 0))
    if kind in {"dashboard", "scorecard"}:
        return max(int(counts.get("card_like_rect", 0)), int(counts.get("bar_like_rect", 0)))
    if kind in {"flow", "timeline"}:
        if int(counts.get("path", 0)) <= 0:
            return 0
        return int(counts.get("circle", 0)) + int(counts.get("ellipse", 0)) + int(counts.get("small_shape", 0))
    if kind in {"map", "architecture"}:
        return int(counts.get("card_like_rect", 0)) + int(counts.get("path", 0))
    return 0


def lint_plan(plan: dict[str, Any], path: str = "<plan>", context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or default_preflight_context()
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        issues.append(plan_issue("error", "plan_missing_slides", "slide_plan.json must include a non-empty slides array"))
        return {
            "path": path,
            "issues": issues,
            "summary": {"slide_count": 0, "error_count": 1, "warning_count": 0},
        }

    page_count = plan.get("page_count") or plan.get("target_slide_count")
    if page_count is not None:
        try:
            expected_count = int(page_count)
            if expected_count != len(slides):
                issues.append(
                    plan_issue(
                        "error",
                        "plan_page_count_mismatch",
                        f"plan page_count is {expected_count}, but slides array has {len(slides)} items",
                    )
                )
        except (TypeError, ValueError):
            issues.append(plan_issue("error", "plan_page_count_invalid", "plan page_count must be an integer when present"))

    is_create_svg_route = context.get("route_id") == CREATE_SVG_ROUTE_ID
    is_svg_plan = plan.get("output_mode") == "svglide-svg" or is_create_svg_route
    seed_level = seed_gate_level(plan)
    deck_preset_id = deck_style_preset_id(plan)
    deck_style_system = style_system(plan)
    if is_svg_plan:
        if plan.get("output_mode") != "svglide-svg":
            issues.append(
                plan_issue(
                    "error",
                    "plan_output_mode_required",
                    'create-svg route plans must include output_mode="svglide-svg"',
                    None,
                    "Do not run create-svg with an untyped plan; output_mode controls SVG seed and recipe gates.",
                )
            )
        if not STYLE_PRESET_CATALOG:
            issues.append(
                plan_issue(
                    "error",
                    "plan_style_preset_catalog_unavailable",
                    "SVGlide style preset catalog is unavailable",
                    None,
                    "Ensure references/style-presets.json exists and contains the 35 beautiful-feishu-whiteboard presets.",
                )
            )
        if not deck_preset_id:
            issues.append(
                plan_issue(
                    "error",
                    "plan_missing_style_preset",
                    "SVGlide plan must include a deck-level style_preset or style_binding.preset_id",
                    None,
                    "Choose one preset from references/style-presets.json before generating SVG.",
                )
            )
        elif deck_preset_id not in STYLE_PRESET_CATALOG:
            issues.append(
                plan_issue(
                    "error",
                    "plan_style_preset_unknown",
                    f'unknown style_preset "{deck_preset_id}"',
                    None,
                    "Use one of: " + ", ".join(sorted(STYLE_PRESET_CATALOG)),
                )
            )
        if not textify(plan.get("style_selection_reason")).strip():
            issues.append(
                plan_issue(
                    "error",
                    "plan_missing_style_selection_reason",
                    "SVGlide plan must explain why the selected style_preset fits this deck",
                    None,
                    "Add style_selection_reason so style choice is auditable and not a random skin.",
                )
            )
        if not deck_style_system:
            issues.append(
                plan_issue(
                    "error",
                    "plan_missing_style_system",
                    "SVGlide plan must include deck-level style_system or theme_system",
                    None,
                    "Translate the selected preset into palette, typography, background_strategy, motif, and shape language.",
                )
            )
        else:
            for field in ["palette", "typography", "background_strategy", "motif"]:
                if not textify(deck_style_system.get(field)).strip():
                    issues.append(
                        plan_issue(
                            "error",
                            f"plan_style_system_missing_{field}",
                            f"SVGlide style_system must include {field}",
                        )
                    )

    renderer_ids: list[str] = []
    layout_families: list[str] = []
    visual_recipes: list[str] = []
    visual_recipe_families: list[str] = []
    recipe_catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG)
    public_recipe_catalog = context.get("public_recipe_catalog", VISUAL_RECIPE_CATALOG)
    private_id_set = context.get("private_id_set", set())
    seed_catalog = context.get("seed_catalog", SVG_SEED_CATALOG)
    for slide_index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            issues.append(plan_issue("error", "plan_slide_invalid", "each slide entry must be an object"))
            continue

        visual_plan = slide_visual_plan(slide)

        renderer_id = slide_renderer_id(visual_plan)
        renderer_ids.append(renderer_id)
        layout_family = slide_layout_family(visual_plan)
        if layout_family:
            layout_families.append(layout_family)
        if is_svg_plan and not textify(visual_plan.get("renderer_id")).strip():
            issues.append(
                plan_issue(
                    "error",
                    "plan_missing_renderer_id",
                    "SVGlide plan slides must include renderer_id so layout diversity is checkable",
                    slide,
                    "Use stable renderer IDs such as cover_full_bleed, agenda_matrix, timeline_rail, comparison_table, or closing_cta.",
                )
            )
        if is_svg_plan:
            if not layout_family:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_layout_family",
                        "SVGlide plan slides must include layout_family so deck-level layout diversity is enforceable",
                        slide,
                        "Use layout families such as hero, agenda_matrix, dashboard, table, timeline, flow, risk_grid, swimlane, or closing.",
                    )
                )

            raw_visual_recipe = normalize_name(visual_plan.get("visual_recipe"))
            visual_recipe = raw_visual_recipe
            route_private_requested = raw_visual_recipe == ROUTE_PRIVATE_VISUAL_RECIPE
            seed_id = slide_seed_id(visual_plan)
            seed_data = None
            if not seed_id:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_seed_id",
                        "SVGlide plan slides must include seed_id",
                        slide,
                        "Choose a seed from references/svg-seeds.json before filling content; do not start from a blank page.",
                    )
                )
            elif seed_id not in seed_catalog:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_unknown_seed",
                        f'unknown seed_id "{seed_id}"',
                        slide,
                        "Use one of: " + ", ".join(sorted(seed_catalog)),
                    )
                )
            else:
                seed_data = seed_catalog[seed_id]
                seed_layout_family = normalize_name(seed_data.get("layout_family"))
                if seed_layout_family and layout_family and normalize_name(layout_family) != seed_layout_family:
                    issues.append(
                        plan_issue(
                            seed_level,
                            "plan_seed_layout_family_mismatch",
                            f'seed "{seed_id}" requires layout_family "{seed_layout_family}"',
                            slide,
                            "Keep the selected seed structure or choose a seed that matches the intended layout family.",
                        )
                    )
                seed_recipe = normalize_name(seed_data.get("visual_recipe"))
                if seed_recipe and raw_visual_recipe and not route_private_requested and raw_visual_recipe != seed_recipe:
                    issues.append(
                        plan_issue(
                            seed_level,
                            "plan_seed_visual_recipe_mismatch",
                            f'seed "{seed_id}" requires visual_recipe "{seed_recipe}"',
                            slide,
                            "Seed and visual_recipe must describe the same structure; choose a different seed or update the recipe.",
                        )
                    )
            layout_boxes = slide_layout_boxes(visual_plan)
            if not layout_boxes:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_layout_boxes",
                        "SVGlide plan slides must declare layout_boxes copied from or adapted from the selected seed",
                        slide,
                        "Declare concrete title/body/visual/footer boxes with x/y/width/height before writing SVG.",
                    )
                )
            else:
                for box in layout_boxes:
                    if not isinstance(box, dict) or not layout_box_role(box) or not layout_box_has_positive_bbox(box):
                        issues.append(
                            plan_issue(
                                seed_level,
                                "plan_layout_box_invalid",
                                "layout_boxes entries must include role plus positive x/y/width/height geometry",
                                slide,
                                "Use boxes such as {role:title,x:64,y:48,width:560,height:58}.",
                            )
                        )
                        break
                if seed_data is not None:
                    required_roles = {normalize_name(role) for role in seed_data.get("required_layout_box_roles", set()) if normalize_name(role)}
                    missing_roles = sorted(required_roles - layout_box_roles(layout_boxes))
                    if missing_roles:
                        issues.append(
                            plan_issue(
                                seed_level,
                                "plan_missing_layout_boxes",
                                f'seed "{seed_id}" requires layout box roles: {", ".join(sorted(required_roles))}',
                                slide,
                                f"Missing layout box roles: {', '.join(missing_roles)}.",
                            )
                        )
                    skeleton = seed_layout_skeleton(seed_data)
                    if skeleton:
                        expected_skeleton_id = seed_skeleton_id(seed_id, skeleton)
                        plan_skeleton = slide_layout_skeleton(visual_plan)
                        plan_skeleton_id = slide_layout_skeleton_id(visual_plan)
                        if not plan_skeleton and not plan_skeleton_id:
                            issues.append(
                                plan_issue(
                                    seed_level,
                                    "plan_seed_layout_skeleton_missing",
                                    "SVGlide plan must declare the selected seed layout_skeleton",
                                    slide,
                                    "Copy layout_skeleton or layout_skeleton_id from svg-seeds.json; seed skeleton is a layout contract, not inspiration.",
                                )
                            )
                        elif plan_skeleton_id and plan_skeleton_id != expected_skeleton_id:
                            issues.append(
                                plan_issue(
                                    seed_level,
                                    "plan_seed_layout_skeleton_mismatch",
                                    f'seed "{seed_id}" requires layout_skeleton_id "{expected_skeleton_id}"',
                                    slide,
                                    "Use the seed skeleton ID unchanged; choose another seed for a different structure.",
                                )
                            )
                        for drift in skeleton_drift_issues(seed_id, seed_data, layout_boxes):
                            issues.append(
                                plan_issue(
                                    seed_level,
                                    "plan_seed_layout_skeleton_drift",
                                    f"layout box drift exceeds selected seed tolerance: {drift}",
                                    slide,
                                    "Keep locked seed roles near their registered boxes, or create a new seed for the new layout.",
                                )
                            )
            capacity_value = slide_text_capacity_value(visual_plan)
            if capacity_value is None:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_content_budget",
                        "SVGlide plan slides must declare content_budget or text_capacity",
                        slide,
                        "Copy the seed budget, then tighten it for the actual title/body/footer copy.",
                    )
                )
            for loosened in capacity_budget_loosenings(capacity_value, seed_data):
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_seed_content_budget_loosened",
                        f"plan content budget widens the selected seed budget: {loosened}",
                        slide,
                        "Seed budgets are upper bounds; shorten content, split the page, or choose a higher-capacity seed instead of increasing the budget.",
                    )
                )
            role_budget = slide_text_budget_by_role(visual_plan)
            if seed_data is not None and seed_data.get("text_budget_by_role") and not role_budget:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_text_budget_by_role",
                        "SVGlide plan must declare text_budget_by_role copied from the selected seed",
                        slide,
                        "Use role-level title/body/callout/label/footer budgets so local overcrowding is caught before SVG rendering.",
                    )
                )
            for loosened in role_budget_loosenings(role_budget, seed_data):
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_seed_text_budget_loosened",
                        f"plan role text budget widens the selected seed budget: {loosened}",
                        slide,
                        "Role text budgets are upper bounds; shorten content, split the page, or choose a higher-capacity seed.",
                    )
                )
            for role, limits in role_budget_by_role(role_budget, seed_data).items():
                max_chars = limits.get("max_chars")
                if not max_chars:
                    continue
                count = visible_text_char_count(role_plan_text(visual_plan, role))
                if count > max_chars:
                    issues.append(
                        plan_issue(
                            seed_level,
                            "plan_text_role_budget_exceeded",
                            f'{role} plan text has {count} chars, above role budget {max_chars}',
                            slide,
                            "Keep each role inside its seed-derived budget; do not solve overflow by shrinking font or rotating text.",
                        )
                    )
            capacity_limits = text_capacity_limits(capacity_value, seed_data)
            text_box_count = sum(1 for box in layout_boxes if isinstance(box, dict) and is_text_layout_box(box))
            max_text_boxes = capacity_limits.get("max_text_boxes")
            min_text_boxes = capacity_limits.get("min_text_boxes")
            if max_text_boxes and text_box_count > max_text_boxes:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_text_box_count_exceeded",
                        f"plan has {text_box_count} text layout boxes, above max_text_boxes {max_text_boxes}",
                        slide,
                        "Reduce visible text surfaces or choose a seed designed for denser content.",
                    )
                )
            if min_text_boxes and text_box_count < min_text_boxes:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_text_box_count_below_seed_minimum",
                        f"plan has {text_box_count} text layout boxes, below min_text_boxes {min_text_boxes}",
                        slide,
                        "Keep the selected seed's required readable text structure, or choose a sparser seed.",
                    )
                )
            visible_chars = visible_text_char_count(capacity_visible_text(visual_plan))
            if capacity_limits.get("max_visible_chars") and visible_chars > capacity_limits["max_visible_chars"]:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_content_budget_exceeded",
                        f"visible plan text has {visible_chars} chars, above max_visible_chars {capacity_limits['max_visible_chars']}",
                        slide,
                        "Shorten content or split the idea into another seeded page before rendering SVG.",
                    )
                )
            for section, code in [
                ("title", "plan_title_capacity_exceeded"),
                ("body", "plan_body_capacity_exceeded"),
                ("footer", "plan_footer_capacity_exceeded"),
            ]:
                limit = capacity_limits.get(section)
                count = visible_text_char_count(capacity_section_text(visual_plan, section))
                if limit and count > limit:
                    issues.append(
                        plan_issue(
                            seed_level,
                            code,
                            f"{section} text has {count} chars, above {section} budget {limit}",
                            slide,
                            f"Keep {section} content within the selected seed's local text capacity.",
                        )
                    )
            if not textify(visual_plan.get("one_idea") or visual_plan.get("key_message")).strip():
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_one_idea",
                        "SVGlide plan slides must declare one_idea or key_message",
                        slide,
                        "Open Design-style authoring starts with one message per seeded page, then fits content into the preserved structure.",
                    )
                )
            reserved_bands = slide_reserved_bands(visual_plan)
            if not reserved_bands or bbox_from_mapping(reserved_bands.get("footer")) is None:
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_reserved_bands",
                        "SVGlide plan slides must declare reserved_bands.footer",
                        slide,
                        "Reserve the footer band explicitly so body text cannot drift into source notes, page marks, or legal copy.",
                    )
                )
            if seed_data is not None and seed_data.get("footer_safe_zone") and not isinstance(visual_plan.get("footer_safe_zone"), dict):
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_missing_footer_safe_zone",
                        "SVGlide plan must declare footer_safe_zone copied from the selected seed",
                        slide,
                        "footer_safe_zone states which roles may enter the footer band and how much clearance body content needs.",
                    )
                )
            if seed_data is not None and seed_data.get("vertical_text_policy") and not isinstance(visual_plan.get("vertical_text_policy"), dict):
                issues.append(
                    plan_issue(
                        seed_level,
                        "plan_vertical_text_policy_missing",
                        "SVGlide plan must declare vertical_text_policy copied from the selected seed",
                        slide,
                        "Default policy is deny; only short seed-approved roles may use vertical or rotated text.",
                    )
                )
            if not visual_recipe:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_visual_recipe",
                        "SVGlide plan slides must include visual_recipe",
                        slide,
                        "Choose one SVG-native recipe such as hero_typography, path_flow, infographic_scorecard, or fake_ui_dashboard.",
                    )
                )
            elif visual_recipe in private_id_set:
                issues.append(
                    plan_issue(
                        "error",
                        "private_recipe_exact_id_in_plan",
                        "slide_plan.json must not contain exact SVG private recipe ids",
                        slide,
                        "Use visual_recipe=route_private with a create-svg route-private recipe selection sidecar instead.",
                    )
                )
            elif route_private_requested and not context.get("allow_private"):
                issues.append(
                    plan_issue(
                        "error",
                        "private_route_not_allowed",
                        "route_private visual_recipe requires the create-svg route manifest",
                        slide,
                        "Run svg_preflight.py with --route-manifest for the create-svg route; non-SVG/XML paths must not load SVG private recipes.",
                    )
                )
            elif route_private_requested:
                selected_recipe = selected_private_recipe_for_slide(visual_plan, slide_index, context)
                if not selected_recipe:
                    issues.append(
                        plan_issue(
                            "error",
                            "private_route_selection_missing",
                            "route_private visual_recipe requires a route-private recipe selection sidecar",
                            slide,
                            "Pass --recipe-selection with create-svg route-private selection data; public slide_plan.json must stay abstract.",
                        )
                    )
                elif selected_recipe not in private_id_set:
                    issues.append(
                        plan_issue(
                            "error",
                            "private_route_selection_invalid",
                            "route-private recipe selection references an unavailable SVG private recipe",
                            slide,
                        )
                    )
                else:
                    visual_recipe = selected_recipe
            elif visual_recipe not in recipe_catalog:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_unknown_visual_recipe",
                        "unknown visual_recipe",
                        slide,
                        "Use one of: " + ", ".join(sorted(public_recipe_catalog)),
                    )
                )
            if visual_recipe in recipe_catalog:
                visual_recipes.append(visual_recipe)
                visual_recipe_families.append(recipe_family(visual_recipe, context))

                declared_primitives = normalize_primitives(visual_plan.get("svg_primitives"))
                plan_required_primitives = required_plan_primitives(visual_plan)
                if not plan_required_primitives:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_missing_required_primitives",
                            "SVGlide plan slides must include required_primitives",
                            slide,
                            "Copy the recipe required primitives, then add any page-specific required primitives the SVG source must expose.",
                        )
                    )
                hard_required_primitives = recipe_required_primitives(visual_recipe, context)
                missing_declared = sorted(hard_required_primitives - declared_primitives)
                if missing_declared:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_recipe_primitives_mismatch",
                            f'{raw_visual_recipe or visual_recipe} requires svg_primitives: {", ".join(sorted(hard_required_primitives))}',
                            slide,
                            "Declare the SVG-native primitives the page will actually draw, not only a renderer_id.",
                        )
                    )
                missing_required_field = sorted(hard_required_primitives - plan_required_primitives)
                if plan_required_primitives and missing_required_field:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_required_primitives_mismatch",
                            f'{raw_visual_recipe or visual_recipe} requires required_primitives: {", ".join(sorted(hard_required_primitives))}',
                            slide,
                            "required_primitives must cover the selected recipe's hard requirements.",
                        )
                    )
                missing_required_declaration = sorted(plan_required_primitives - declared_primitives)
                if plan_required_primitives and missing_required_declaration:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_required_primitives_not_declared",
                            "required_primitives must also appear in svg_primitives",
                            slide,
                            f"Missing from svg_primitives: {', '.join(missing_required_declaration)}.",
                        )
                    )
                if is_private_recipe(visual_recipe, context):
                    if has_private_fallback_field(visual_plan):
                        issues.append(
                            plan_issue(
                                "error",
                                "private_recipe_fallback_not_allowed",
                                "SVG private recipes must not declare fallback or safe rewrite fields",
                                slide,
                                "Fix the SVG source to satisfy the route-private recipe instead of weakening it with a fallback.",
                            )
                        )
                    if has_private_exemption_field(visual_plan):
                        issues.append(
                            plan_issue(
                                "error",
                                "private_recipe_exemption_not_allowed",
                                "SVG private recipes must not declare preflight exemption fields",
                                slide,
                                "Private SVG recipes are fail-closed; remove exemptions and satisfy the source-truth gates.",
                            )
                        )

            for field in ["visual_intent", "visual_focal_point", "visual_signature", "xml_like_risk"]:
                if not textify(visual_plan.get(field)).strip():
                    issues.append(
                        plan_issue(
                            "error",
                            f"plan_missing_{field}",
                            f"SVGlide plan slides must include {field}",
                            slide,
                        )
                    )
            if not normalize_primitives(visual_plan.get("svg_primitives")):
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_svg_primitives",
                        "SVGlide plan slides must include non-empty svg_primitives",
                        slide,
                        "List SVGlide-safe primitives such as path, gradient, typography, annotation, micro_chart, texture, image_overlay, or dashboard.",
                    )
                )
            declared_effects = normalize_effects(visual_plan.get("svg_effects"))
            if not declared_effects:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_svg_effects",
                        "SVGlide plan slides must include svg_effects",
                        slide,
                        "Declare the SVG effects that create the page's visual advantage, such as path, connector_flow, gradient, texture, chart_geometry, or image_overlay.",
                    )
                )
            for effect in sorted(declared_effects):
                if effect not in SVG_EFFECT_CATALOG:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_unknown_svg_effect",
                            f'unknown svg_effect "{effect}"',
                            slide,
                            "Use one of: " + ", ".join(sorted(SVG_EFFECT_CATALOG)),
                        )
                    )
                    continue
                if SVG_EFFECT_CATALOG[effect].get("requires_fallback") and not has_effect_fallback(visual_plan, effect):
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_svg_effect_requires_safe_fallback",
                            f'svg_effect "{effect}" requires an explicit SVGlide-safe fallback or rewrite',
                            slide,
                            "Declare effect_fallbacks, safe_rewrite, recipe_fallback, or fallback_policy before rendering SVG.",
                        )
                    )
            slide_preset_id = slide_style_preset_id(slide)
            effective_preset_id = slide_preset_id or deck_preset_id
            if slide_preset_id and slide_preset_id not in STYLE_PRESET_CATALOG:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_style_preset_unknown",
                        f'unknown slide style_preset "{slide_preset_id}"',
                        slide,
                        "Use one of: " + ", ".join(sorted(STYLE_PRESET_CATALOG)),
                    )
                )
            if slide_preset_id and deck_preset_id and slide_preset_id != deck_preset_id:
                issues.append(
                    plan_issue(
                        "warning",
                        "plan_slide_style_preset_mismatch",
                        f'slide style_preset "{slide_preset_id}" overrides deck style_preset "{deck_preset_id}"',
                        slide,
                        "Only override per page when the visual rhythm explicitly needs a cover, section, or poster treatment.",
                    )
                )
            if effective_preset_id in STYLE_PRESET_CATALOG:
                preset = STYLE_PRESET_CATALOG[effective_preset_id]
                visible = visible_slide_text(visual_plan).lower()
                leaked_terms = [
                    textify(preset.get("style_id")),
                    textify(preset.get("display_name")),
                    textify(preset.get("source_token")),
                ]
                leaked_terms = [term for term in leaked_terms if term and term.lower() in visible]
                if leaked_terms:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_style_preset_visible_leak",
                            "visible slide fields must not expose style preset names, ids, or source tokens",
                            slide,
                            "Keep preset metadata in style_binding/style_system only; visible content should describe the user's topic.",
                        )
                    )
            visible = visible_slide_text(visual_plan)
            if TOOL_LEAK_RE.search(visible) or PATH_LIKE_RE.search(visible):
                issues.append(
                    plan_issue(
                        "error",
                        "plan_visible_tool_or_path_leak",
                        "visible slide fields must not expose prompts, tool names, source tokens, or local file paths",
                        slide,
                    )
                )
            if not asset_contract_present(visual_plan.get("asset_contract")):
                issues.append(
                    plan_issue(
                        "warning",
                        "plan_missing_asset_contract",
                        "SVGlide plan slides must include asset_contract",
                        slide,
                        'MVP preflight allows missing asset_contract, but use "none_required" when the page has no image asset; otherwise provide preview image metadata including retrieval_query/source_url or mark license="preview_unverified".',
                    )
                )
            if "risk_flags" not in visual_plan:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_risk_flags",
                        "SVGlide plan slides must include risk_flags",
                        slide,
                        "Use an empty list when no known generation risk applies; otherwise list risks such as text_overflow, image_preview_only, image_query_mismatch, network_image_fetch_unavailable, image_license, or conversion_dasharray.",
                    )
                )
            if not textify(visual_plan.get("source_policy")).strip():
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_source_policy",
                        "SVGlide plan slides must include source_policy",
                        slide,
                        "State how the generator handles missing data and numeric claims.",
                    )
                )
            density_contract = visual_plan.get("content_density_contract")
            if not textify(density_contract).strip():
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_content_density_contract",
                        "SVGlide plan slides must include content_density_contract",
                        slide,
                        'For high-density pages use a quantified contract such as "dashboard >= 4 metrics" or {"type":"table","min_cells":6}.',
                    )
                )

        density = textify(visual_plan.get("density") or visual_plan.get("text_density")).strip().lower()
        if density == "high":
            structure_text = plan_slide_text(visual_plan, ["density_structure", "visual_structure", "renderer_id", "layout_type"])
            if not PLAN_STRUCTURED_RE.search(structure_text):
                issues.append(
                    plan_issue(
                        "error",
                        "plan_high_density_without_structure",
                        "high-density slides must declare a structured visual carrier",
                        slide,
                        "Use density_structure or renderer_id with matrix, table, timeline, flow, comparison, dashboard, map, or similar structure.",
                    )
                )
            if is_svg_plan and density_contract_kind_count(visual_plan.get("content_density_contract")) is None:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_high_density_contract_not_quantified",
                        "high-density SVG slides must quantify their content_density_contract",
                        slide,
                        'Use a measurable contract such as "matrix >= 6 cells", "timeline >= 4 nodes", "dashboard >= 4 metrics", "flow >= 4 stages", or "risk_grid >= 4 items".',
                    )
                )

        source_status = plan_slide_text(visual_plan, ["source_status", "source_state"])
        requires_attachment = bool(visual_plan.get("requires_attachment"))
        if requires_attachment or PLAN_MISSING_SOURCE_RE.search(source_status):
            guard_text = plan_slide_text(
                visual_plan,
                ["source_policy", "source_guard", "visible_source_note", "key_message", "takeaway", "speaker_intent", "notes"],
            )
            if not PLAN_SOURCE_GUARD_RE.search(guard_text):
                issues.append(
                    plan_issue(
                        "error",
                        "plan_missing_source_guard",
                        "slides with missing attachment/source must explicitly guard against fabricated facts",
                        slide,
                        "Add source_policy/source_guard or visible note such as 待从附件补齐 / 来源缺失 / no numeric claims.",
                    )
                )

    if len(slides) >= 8:
        last_slide = slides[-1] if isinstance(slides[-1], dict) else {}
        closing_plan = slide_visual_plan(last_slide) if isinstance(last_slide, dict) else {}
        closing_text = plan_slide_text(closing_plan, ["page_type", "layout_type", "renderer_id", "title", "key_message", "takeaway"])
        if not PLAN_CLOSING_RE.search(closing_text):
            issues.append(
                plan_issue(
                    "error",
                    "plan_missing_closing_slide",
                    "decks with 8 or more pages must end with an explicit closing/summary/thanks/Q&A page",
                    last_slide if isinstance(last_slide, dict) else None,
                )
            )

    comparable_renderers = [renderer for renderer in renderer_ids if renderer]
    comparable_layout_families = [family for family in layout_families if family]
    if len(slides) >= 10 and len(set(comparable_renderers)) < 5:
        issues.append(
            plan_issue(
                "error",
                "plan_renderer_diversity_low",
                "decks with 10 or more pages must use at least 5 distinct renderer/layout families",
                None,
                "Do not rely on layout_type names only; renderer_id must reflect actual geometry.",
            )
        )
    if is_svg_plan and len(slides) >= 10 and len(set(comparable_layout_families)) < 5:
        issues.append(
            plan_issue(
                "error",
                "plan_layout_family_diversity_low",
                "SVGlide decks with 10 or more pages must use at least 5 distinct layout_family values",
                None,
                "Vary actual reading direction and information structure, not only renderer names.",
            )
        )
    for index in range(len(comparable_renderers) - 2):
        if comparable_renderers[index] == comparable_renderers[index + 1] == comparable_renderers[index + 2]:
            issues.append(
                plan_issue(
                    "error",
                    "plan_renderer_repetition",
                    f"renderer '{comparable_renderers[index]}' repeats for 3 consecutive slides",
                    slides[index + 2] if isinstance(slides[index + 2], dict) else None,
                    "Change geometry, reading direction, image usage, or information structure before generating SVG.",
                )
            )
    for index in range(len(comparable_layout_families) - 2):
        if comparable_layout_families[index] == comparable_layout_families[index + 1] == comparable_layout_families[index + 2]:
            issues.append(
                plan_issue(
                    "error",
                    "plan_layout_family_repetition",
                    f"layout_family '{comparable_layout_families[index]}' repeats for 3 consecutive slides",
                    slides[index + 2] if isinstance(slides[index + 2], dict) else None,
                    "Change the page structure before rendering SVG; recipe names alone are not enough.",
                )
            )
    if is_svg_plan and len(slides) >= 8 and len(set(visual_recipe_families)) < 5:
        issues.append(
            plan_issue(
                "error",
                "plan_visual_recipe_diversity_low",
                "SVGlide decks with 8 or more pages must use at least 5 distinct visual_recipe families",
                None,
                "Mix hero/title, flow/metaphor, data/dashboard, texture/depth, annotation/showcase, icon, geometry, and brand recipes.",
            )
        )

    result: dict[str, Any] = {
        "path": path,
        "slide_count": len(slides),
        "distinct_renderer_count": len(set(comparable_renderers)),
        "distinct_layout_family_count": len(set(comparable_layout_families)),
        "distinct_visual_recipe_count": len(set(visual_recipes)),
        "distinct_visual_recipe_family_count": len(set(visual_recipe_families)),
        "summary": {
            "error_count": sum(1 for item in issues if item["level"] == "error"),
            "warning_count": sum(1 for item in issues if item["level"] == "warning"),
        },
    }
    if issues:
        result["issues"] = issues
    return result


def load_plan_json(path: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return None, {
            "path": path,
            "issues": [
                {
                    "level": "error",
                    "code": "plan_json_invalid",
                    "message": f"slide_plan.json is not valid JSON: {error}",
                    "hint": "Fix the plan before generating SVG or calling slides +create-svg.",
                }
            ],
            "summary": {"error_count": 1, "warning_count": 0},
        }
    if not isinstance(plan, dict):
        return None, {
            "path": path,
            "issues": [
                {
                    "level": "error",
                    "code": "plan_root_invalid",
                    "message": "slide_plan.json root must be an object",
                }
            ],
            "summary": {"error_count": 1, "warning_count": 0},
        }
    return plan, None


def lint_plan_file(path: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    plan, load_error = load_plan_json(path)
    if load_error:
        return load_error
    return lint_plan(plan or {}, path, context)


def planned_svg_path(slide: dict[str, Any], plan: dict[str, Any]) -> str:
    direct = textify(slide.get("svg_path") or slide.get("path") or slide.get("file"))
    if direct:
        return direct
    page = slide.get("page")
    svg_files = plan.get("svg_files")
    if isinstance(svg_files, list):
        for item in svg_files:
            if not isinstance(item, dict):
                continue
            if item.get("page") == page and textify(item.get("path")):
                return textify(item.get("path"))
    return ""


def resolved_visual_recipe_for_slide(slide: dict[str, Any], slide_index: int, context: dict[str, Any]) -> str:
    visual_plan = slide_visual_plan(slide)
    recipe = normalize_name(visual_plan.get("visual_recipe"))
    if recipe == ROUTE_PRIVATE_VISUAL_RECIPE:
        return selected_private_recipe_for_slide(visual_plan, slide_index, context)
    return recipe


def lint_plan_svg_alignment(plan: dict[str, Any], files: list[dict[str, Any]], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or default_preflight_context()
    if plan.get("output_mode") != "svglide-svg":
        return []
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        return []

    files_by_name = {Path(textify(file.get("path"))).name: file for file in files if textify(file.get("path"))}
    alignments: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        svg_path = planned_svg_path(slide, plan)
        if svg_path:
            file = files_by_name.get(Path(svg_path).name)
            if file is not None:
                alignments.append((index + 1, slide, file))
                continue
        if len(files) == len(slides):
            alignments.append((index + 1, slide, files[index]))

    issues: list[dict[str, Any]] = []
    recipe_catalog = context.get("recipe_catalog", VISUAL_RECIPE_CATALOG)
    seed_catalog = context.get("seed_catalog", SVG_SEED_CATALOG)
    for slide_index, slide, file in alignments:
        visual_plan = slide_visual_plan(slide)
        recipe = resolved_visual_recipe_for_slide(visual_plan, slide_index, context)
        seed_id = slide_seed_id(visual_plan)
        seed_data = seed_catalog.get(seed_id) if seed_id in seed_catalog else None
        if recipe not in recipe_catalog:
            continue
        visual_primitives = file.get("visual_primitives", {})
        source_primitives = set(visual_primitives.get("present", []))
        source_effects = set(visual_primitives.get("effects", []))
        source_areas = visual_primitives.get("primitive_areas", {}) if isinstance(visual_primitives.get("primitive_areas"), dict) else {}
        hidden_counts = visual_primitives.get("hidden_counts", {}) if isinstance(visual_primitives.get("hidden_counts"), dict) else {}
        declared_primitives = normalize_primitives(visual_plan.get("svg_primitives"))
        required_primitives = recipe_required_primitives(recipe, context) | required_plan_primitives(visual_plan)
        missing_required = sorted(required_primitives - source_primitives)
        if missing_required:
            issues.append(
                plan_issue(
                    "error",
                    "private_recipe_required_primitives_not_found" if is_private_recipe(recipe, context) else "plan_recipe_required_primitives_not_found",
                    f'{recipe} required primitives not found in SVG source: {", ".join(missing_required)}',
                    slide,
                    f"SVG file {file.get('path')} exposes primitives {sorted(source_primitives)}; adjust SVG source or choose a more accurate visual_recipe.",
                )
            )
        if is_private_recipe(recipe, context):
            minimum_area = CANVAS_WIDTH * CANVAS_HEIGHT * recipe_minimum_visible_area_ratio(recipe, context)
            for primitive in sorted(required_primitives):
                if int(hidden_counts.get(primitive, 0)) > 0 and float(source_areas.get(primitive, 0.0)) <= 0:
                    issues.append(
                        plan_issue(
                            "error",
                            "private_recipe_required_primitive_not_visible",
                            "SVG private recipe required primitive is hidden or transparent in the source",
                            slide,
                            "Private recipes must be proven by visible SVG geometry; remove display:none/visibility:hidden/zero opacity or choose another recipe.",
                        )
                    )
                    continue
                if primitive in source_primitives and float(source_areas.get(primitive, 0.0)) < minimum_area:
                    issues.append(
                        plan_issue(
                            "error",
                            "private_recipe_required_primitive_too_small",
                            "SVG private recipe required primitive is too small to substantiate the recipe",
                            slide,
                            "Increase the actual SVG geometry; private recipes cannot be satisfied by tiny hidden markers or metadata-only declarations.",
                        )
                    )
        if declared_primitives and not (declared_primitives & source_primitives):
            issues.append(
                plan_issue(
                    "error",
                    "plan_svg_primitives_not_found",
                    "slide svg_primitives do not match any detected SVG source primitive",
                    slide,
                    f"Declared {sorted(declared_primitives)}, detected {sorted(source_primitives)} in {file.get('path')}.",
                )
            )
        declared_effects = normalize_effects(visual_plan.get("svg_effects"))
        required_effects = declared_effects | recipe_required_effects(recipe, context)
        missing_effects = sorted(effect for effect in required_effects if effect in SVG_EFFECT_CATALOG and effect not in source_effects)
        if missing_effects:
            issues.append(
                plan_issue(
                    "error",
                    "private_recipe_required_effect_not_found" if is_private_recipe(recipe, context) else "plan_svg_effect_not_found",
                    f'declared svg_effects not found in SVG source: {", ".join(missing_effects)}',
                    slide,
                    f"SVG file {file.get('path')} exposes effects {sorted(source_effects)}; adjust SVG source or remove inaccurate effects.",
                )
            )
        if is_private_recipe(recipe, context):
            file_warnings = [item for item in file.get("issues", []) if item.get("level") == "warning"]
            if file_warnings:
                issues.append(
                    plan_issue(
                        "error",
                        "private_recipe_unclassified_warning",
                        "SVG private recipe pages must not carry unresolved SVG preflight warnings",
                        slide,
                        "Classify and fix warnings before using route-private SVG recipes.",
                    )
                )
        contract = density_contract_kind_count(visual_plan.get("content_density_contract"))
        density = textify(visual_plan.get("density") or visual_plan.get("text_density")).strip().lower()
        if density == "high" and contract is not None:
            kind, minimum = contract
            source_count = source_density_count(kind, file.get("visual_primitives", {}))
            if source_count < minimum:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_content_density_contract_not_met",
                        f'content_density_contract "{kind} >= {minimum}" is not met by SVG source',
                        slide,
                        f"Detected count is {source_count} in {file.get('path')}; add real cells/nodes/metrics/stages/items before rendering.",
                    )
                )
        if "image" in source_primitives:
            contract_value = visual_plan.get("asset_contract")
            if asset_contract_declares_no_asset(contract_value) or not asset_contract_has_metadata(contract_value):
                issues.append(
                    plan_issue(
                        "warning",
                        "plan_asset_contract_missing_metadata",
                        "SVG source uses image primitives, but asset_contract lacks required source/license metadata",
                        slide,
                        'MVP preflight allows incomplete image metadata; for preview add retrieval_query, source_type, license="preview_unverified", local_path_or_href, usage_page, and source_url/href when available.',
                    )
                )
        footer_band = reserved_footer_band(visual_plan)
        footer_zone = footer_safe_zone_bbox(visual_plan, seed_data) or footer_band
        footer_allowed_roles = footer_safe_zone_allowed_roles(visual_plan, seed_data)
        footer_min_gap = footer_safe_zone_min_gap(visual_plan, seed_data)
        vertical_policy = slide_vertical_text_policy(visual_plan, seed_data)
        text_box_reports = file.get("text_boxes")
        layout_boxes = slide_layout_boxes(visual_plan)
        layout_bboxes = layout_box_bboxes_by_role(layout_boxes)
        capacity_limits = text_capacity_limits(slide_text_capacity_value(visual_plan), seed_data)
        role_budgets = role_budget_by_role(slide_text_budget_by_role(visual_plan), seed_data)
        if footer_band is not None and isinstance(text_box_reports, list):
            source_text_box_count = len(text_box_reports)
            max_text_boxes = capacity_limits.get("max_text_boxes")
            min_text_boxes = capacity_limits.get("min_text_boxes")
            if max_text_boxes and source_text_box_count > max_text_boxes:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_source_text_box_count_exceeded",
                        f"SVG source has {source_text_box_count} text boxes, above max_text_boxes {max_text_boxes}",
                        slide,
                        "Reduce rendered text surfaces or choose a higher-capacity seed.",
                    )
                )
            if min_text_boxes and source_text_box_count < min_text_boxes:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_source_text_box_count_below_seed_minimum",
                        f"SVG source has {source_text_box_count} text boxes, below min_text_boxes {min_text_boxes}",
                        slide,
                        "The final SVG should preserve the selected seed's readable text structure.",
                    )
                )
            source_visible_chars = sum(int(text_box.get("text_chars", 0)) for text_box in text_box_reports if isinstance(text_box, dict))
            if capacity_limits.get("max_visible_chars") and source_visible_chars > capacity_limits["max_visible_chars"]:
                issues.append(
                    plan_issue(
                        "error",
                        "plan_source_content_budget_exceeded",
                        f"SVG source has {source_visible_chars} visible text chars, above max_visible_chars {capacity_limits['max_visible_chars']}",
                        slide,
                        "Shorten rendered copy or split the page before live create.",
                    )
                )
            source_role_chars: dict[str, int] = {}
            source_role_boxes: dict[str, int] = {}
            role_line_counts: dict[str, int] = {}
            role_min_fonts: dict[str, float] = {}
            for text_box in text_box_reports:
                if not isinstance(text_box, dict):
                    continue
                text_bbox = bbox_from_mapping(text_box.get("bbox"))
                if text_bbox is None:
                    continue
                identifier = textify(text_box.get("identifier") or text_box.get("element_id"))
                visible_text = textify(text_box.get("text"))
                role = infer_text_box_role(text_box, set(layout_bboxes)) or infer_text_box_role_from_layout(text_box, layout_bboxes)
                is_footer = role == "footer" or (is_footer_identifier(identifier, visible_text) and role not in {"source", "caption"})
                if not role and is_footer:
                    role = "footer"
                budget_role = role
                if not budget_role and not is_footer and "body" in role_budgets:
                    budget_role = "body"
                elif budget_role not in role_budgets and not is_footer and "body" in role_budgets:
                    budget_role = "body"
                if budget_role:
                    source_role_chars[budget_role] = source_role_chars.get(budget_role, 0) + visible_text_char_count(visible_text)
                    source_role_boxes[budget_role] = source_role_boxes.get(budget_role, 0) + 1
                    font_size = float(text_box.get("font_size") or 0.0)
                    role_min_fonts[budget_role] = min(role_min_fonts.get(budget_role, font_size or 999.0), font_size or 999.0)
                    _, _required_height, required_lines = text_required_size(visible_text, font_size or 14.0, text_bbox["width"])
                    role_line_counts[budget_role] = max(role_line_counts.get(budget_role, 0), required_lines)
                if bool(text_box.get("vertical_text")):
                    if not role:
                        role = budget_role or "body"
                    if not vertical_text_policy_allows(vertical_policy, role):
                        issues.append(
                            plan_issue(
                                "error",
                                "vertical_text_disallowed_role",
                                f'SVG source uses vertical text in role "{role}" but the selected seed policy does not allow it',
                                slide,
                                "Do not use writing-mode/text-orientation/rotated long text unless the seed explicitly allows this role.",
                            )
                        )
                        break
                    max_vertical_chars = vertical_policy_limit(vertical_policy, "max_chars", 8)
                    if visible_text_char_count(visible_text) > max_vertical_chars:
                        issues.append(
                            plan_issue(
                                "error",
                                "vertical_text_budget_exceeded",
                                f'vertical text has {visible_text_char_count(visible_text)} chars, above policy max_chars {max_vertical_chars}',
                                slide,
                                "Use vertical text only for short decorative labels; move explanations into horizontal body boxes.",
                            )
                        )
                        break
                if is_footer and not bbox_contains(footer_band, text_bbox, tolerance=TEXT_CONTAINER_TOLERANCE):
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_footer_reserved_band_violation",
                            "footer/source/note text is outside reserved_bands.footer",
                            slide,
                            f"Keep footer-like text inside the declared footer band in {file.get('path')}.",
                        )
                    )
                    break
                if not is_footer and intersects(text_bbox, footer_band):
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_footer_reserved_band_violation",
                            "non-footer text intrudes into reserved_bands.footer",
                            slide,
                            "Move body/callout text above the reserved footer band or shrink the body box.",
                        )
                    )
                    issues.append(
                        plan_issue(
                            "error",
                            "footer_safe_zone_intrusion",
                            "non-footer text intrudes into footer_safe_zone",
                            slide,
                            "Only footer/source/legal/page mark roles may enter the footer safe zone; move body, labels, and chart legends above it.",
                        )
                    )
                    break
                if footer_zone is not None:
                    zone_role = role or ("footer" if is_footer else "body")
                    gap_above = footer_zone["y"] - bbox_bottom(text_bbox)
                    if intersects(text_bbox, footer_zone) and zone_role not in footer_allowed_roles:
                        issues.append(
                            plan_issue(
                                "error",
                                "footer_safe_zone_intrusion",
                                f'SVG text role "{zone_role}" intrudes into footer_safe_zone',
                                slide,
                                "Only footer/source/legal/page mark roles may enter the footer safe zone; move body, labels, and chart legends above it.",
                            )
                        )
                        break
                    if zone_role not in footer_allowed_roles and 0 <= gap_above < footer_min_gap:
                        issues.append(
                            plan_issue(
                                "error",
                                "footer_safe_zone_intrusion",
                                f'SVG text role "{zone_role}" is too close to footer_safe_zone',
                                slide,
                                f"Keep non-footer content at least {round(footer_min_gap, 1)}px above the footer safe zone.",
                            )
                        )
                        break
                if role and role in layout_bboxes and not any(bbox_contains(box, text_bbox, tolerance=TEXT_CONTAINER_TOLERANCE) for box in layout_bboxes[role]):
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_text_box_outside_seed_layout_box",
                            f'SVG text box inferred as "{role}" is outside the matching layout box',
                            slide,
                            "Keep final SVG text inside the seed-derived layout box, or update the plan boxes before rendering.",
                        )
                    )
                    break
            for role, limits in role_budgets.items():
                max_chars = limits.get("max_chars")
                if max_chars and source_role_chars.get(role, 0) > max_chars:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_source_role_text_budget_exceeded",
                            f'SVG source role "{role}" has {source_role_chars.get(role, 0)} chars, above role budget {max_chars}',
                            slide,
                            "Shorten rendered copy, split the page, or choose a seed with a higher role budget.",
                        )
                    )
                    break
                max_boxes = limits.get("max_boxes")
                if max_boxes and source_role_boxes.get(role, 0) > max_boxes:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_source_role_text_budget_exceeded",
                            f'SVG source role "{role}" has {source_role_boxes.get(role, 0)} text boxes, above role budget {max_boxes}',
                            slide,
                            "Reduce role text surfaces or use a seed designed for denser content.",
                        )
                    )
                    break
                max_lines = limits.get("max_lines")
                if max_lines and role_line_counts.get(role, 0) > max_lines:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_source_role_text_budget_exceeded",
                            f'SVG source role "{role}" needs {role_line_counts.get(role, 0)} lines, above role budget {max_lines}',
                            slide,
                            "Increase the seed text box only by creating/updating a seed, or shorten the wording.",
                        )
                    )
                    break
                min_font = limits.get("min_font_px")
                if min_font and role_min_fonts.get(role, 999.0) < min_font:
                    issues.append(
                        plan_issue(
                            "error",
                            "plan_source_role_text_budget_exceeded",
                            f'SVG source role "{role}" font size is below min_font_px {min_font}',
                            slide,
                            "Do not hide overflow by shrinking text below the seed minimum.",
                        )
                    )
                    break
    return issues


def lint_svg(svg: str, path: str = "<svg>") -> dict[str, Any]:
    result: dict[str, Any] = {"path": path, "issues": []}
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        result["issues"].append(
            {
                "level": "error",
                "code": "xml_not_well_formed",
                "message": f"SVG is not well-formed: {error}",
                "hint": "Fix tag closure, attribute quotes, namespaces, and XML escaping before calling slides +create-svg.",
            }
        )
        result["summary"] = {"error_count": 1, "warning_count": 0}
        return result

    root_issues, width, height = validate_root(root)
    elements = walk_renderable(root)
    role_issues = validate_roles_and_attrs(elements)
    marker_issues = validate_chart_markers(root)
    geometry_issues, text_boxes = validate_geometry(elements, width, height)
    primitive_summary = summarize_visual_primitives(root, elements, text_boxes, width, height)
    issues = (
        root_issues
        + role_issues
        + marker_issues
        + validate_styles(root)
        + validate_paths(elements)
        + geometry_issues
        + validate_text_overlap(text_boxes)
        + validate_layout_pressure(elements, text_boxes, width, height)
        + validate_visible_svg_text_leaks(text_boxes)
        + validate_text_visibility_clipping(text_boxes)
        + validate_visual_quality(elements)
        + validate_xml_like_layout(elements, text_boxes, primitive_summary)
    )

    result["width"] = width
    result["height"] = height
    result["element_count"] = len(elements)
    result["text_box_count"] = len(text_boxes)
    result["text_boxes"] = [
        {
            "element_id": get_attr(item["element"], "id"),
            "identifier": element_identifier_text(item["element"]),
            "bbox": {key: round(value, 2) for key, value in item["bbox"].items()},
            "text": textify(item.get("text")).strip()[:160],
            "text_chars": visible_text_char_count(item.get("text")),
            "font_size": round(float(item.get("font_size") or 0.0), 2),
            "vertical_text": bool(item.get("vertical_text")),
        }
        for item in text_boxes
    ]
    result["visual_primitives"] = primitive_summary
    result["issues"] = issues
    result["summary"] = {
        "error_count": sum(1 for item in issues if item["level"] == "error"),
        "warning_count": sum(1 for item in issues if item["level"] == "warning"),
    }
    if not issues:
        result.pop("issues")
    return result


def private_redaction_terms(context: dict[str, Any]) -> list[str]:
    terms = [textify(item) for item in sorted(context.get("private_id_set", set()))]
    for key in ["route_manifest_path", "private_manifest_path", "recipe_selection_path"]:
        value = textify(context.get(key)).strip()
        if value:
            terms.append(value)
            terms.append(Path(value).name)
    return [term for term in terms if term]


def redact_text(text: str, context: dict[str, Any]) -> str:
    out = text
    for term in private_redaction_terms(context):
        out = out.replace(term, "[redacted-private]")
    out = re.sub(r"Use one of:\s*([^.\n]+)", "Use one of: [public catalog]", out)
    return out


def redact_private_metadata(value: Any, context: dict[str, Any]) -> Any:
    if context.get("report_scope") == INTERNAL_REPORT_SCOPE:
        return value
    if isinstance(value, str):
        return redact_text(value, context)
    if isinstance(value, list):
        return [redact_private_metadata(item, context) for item in value]
    if isinstance(value, dict):
        return {key: redact_private_metadata(item, context) for key, item in value.items()}
    return value


def lint_files(paths: list[str], plan_path: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or default_preflight_context()
    files: list[dict[str, Any]] = []
    for path in paths:
        svg = Path(path).read_text(encoding="utf-8")
        files.append(lint_svg(svg, path))
    plan_result = None
    if plan_path:
        plan, load_error = load_plan_json(plan_path)
        plan_result = load_error or lint_plan(plan or {}, plan_path, context)
        if plan is not None:
            alignment_issues = lint_plan_svg_alignment(plan, files, context)
            if alignment_issues:
                plan_result.setdefault("issues", []).extend(alignment_issues)
                plan_result["summary"]["error_count"] = sum(1 for item in plan_result["issues"] if item["level"] == "error")
                plan_result["summary"]["warning_count"] = sum(1 for item in plan_result["issues"] if item["level"] == "warning")
    elif context.get("route_id") == CREATE_SVG_ROUTE_ID:
        plan_result = {
            "path": "<missing-plan>",
            "issues": [
                {
                    "level": "error",
                    "code": "plan_required_for_create_svg_route",
                    "message": "create-svg route preflight requires --plan so seed, recipe, layout, and content-budget gates cannot be bypassed",
                    "hint": "Pass --plan .lark-slides/plan/<deck-id>/slide_plan.json together with SVG inputs before live create.",
                }
            ],
            "summary": {"error_count": 1, "warning_count": 0},
        }
    summary = {
        "file_count": len(files),
        "error_count": sum(file["summary"]["error_count"] for file in files),
        "warning_count": sum(file["summary"]["warning_count"] for file in files),
    }
    if plan_result:
        summary["plan_count"] = 1
        summary["error_count"] += plan_result["summary"]["error_count"]
        summary["warning_count"] += plan_result["summary"]["warning_count"]
    result: dict[str, Any] = {
        "summary": {
            **summary,
        },
        "files": files,
    }
    if plan_result:
        result["plan"] = plan_result
    return result


def main(argv: list[str]) -> int:
    context = default_preflight_context()
    try:
        options = parse_args(argv)
        context = build_preflight_context(options["route_manifest"], options["recipe_selection"], options["report_scope"])
        result = lint_files(options["inputs"], options["plan"], context)
    except SvgPreflightError as error:
        print(f"svg_preflight: {redact_text(str(error), context)}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"svg_preflight: {redact_text(str(error), context)}", file=sys.stderr)
        return 2

    print(json.dumps(redact_private_metadata(result, context), ensure_ascii=False, indent=2))
    return 1 if result["summary"]["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
