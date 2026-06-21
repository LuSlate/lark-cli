#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr

import svglide_node_layout_drift


CANVAS_SPEC_VERSION = "svglide-canvas-spec/v1"
ARTBOARD_RECEIPT_VERSION = "svglide-artboard-receipt/v1"
SEMANTIC_MAP_VERSION = "svglide-semantic-map/v1"
NODE_LAYOUT_MAP_VERSION = "svglide-node-layout-map/v1"
SLIDE_NS = "https://slides.bytedance.com/ns"
SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
CONTRACT_VERSION = "svglide-authoring-contract/v1"
SUPPORTED_TEMPLATES = {
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
SUPPORTED_SATORI_ELEMENTS = {"svg", "g", "mask", "rect", "circle", "ellipse", "line", "path", "text"}
FAIL_FAST_ELEMENTS = {"defs", "filter", "clipPath", "pattern", "foreignObject", "image", "use", "linearGradient", "radialGradient"}
ARTBOARD_RENDERER_DIR = Path(__file__).resolve().parent / "artboard_renderer"
SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
NODE_RENDERER_DIST = ARTBOARD_RENDERER_DIR / "dist" / "render.mjs"
NODE_RENDERER_SOURCE = ARTBOARD_RENDERER_DIR / "render.mjs"
GLOBAL_TEMPLATE_REGISTRY = REFERENCES_DIR / "svglide-template-registry.json"
GLOBAL_THEME_REGISTRY = ARTBOARD_RENDERER_DIR / "themes" / "registry.json"
GLOBAL_THEME_DIR = ARTBOARD_RENDERER_DIR / "themes"
PROJECT_TEMPLATE_REGISTRY = Path("02-plan/template-registry.json")
PROJECT_THEME_REGISTRY = Path("02-plan/theme-registry.json")
CANVAS_SPEC_VALIDATE_CHECK = Path("06-check/canvas-spec-validate.json")
CANVAS_SPEC_VALIDATE_RECEIPT = Path("receipts/canvas-spec-validate.json")
ARTBOARD_RENDER_RECEIPT = Path("receipts/artboard-render.json")
SATORI_BRIDGE_RECEIPT = Path("receipts/satori-bridge.json")
CONTACT_SHEET = Path("05-preview/contact-sheet.png")


class ArtboardError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ArtboardError(f"missing required file: {path}") from err
    except json.JSONDecodeError as err:
        raise ArtboardError(f"invalid JSON: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise ArtboardError(f"expected JSON object: {path}")
    return payload


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha256(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def strings_sha256(values: list[str]) -> str:
    data = "\n".join(values).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def relpath(path: Path, project: Path) -> str:
    return path.relative_to(project).as_posix()


def repo_relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(SCRIPT_DIR.parents[2].resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def optional_project_path(project: Path, rel: Path) -> Path | None:
    path = project / rel
    return path if path.exists() else None


def registry_path(project: Path, rel: Path, fallback: Path) -> Path:
    project_path = optional_project_path(project, rel)
    return project_path if project_path else fallback


def registry_record_by_id(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    records = payload.get(key)
    result: dict[str, dict[str, Any]] = {}
    if isinstance(records, list):
        for item in records:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                result[item["id"]] = item
    return result


def load_template_registry(project: Path) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
    path = registry_path(project, PROJECT_TEMPLATE_REGISTRY, GLOBAL_TEMPLATE_REGISTRY)
    payload = read_json(path)
    return path, payload, registry_record_by_id(payload, "templates")


def load_theme_registry(project: Path) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
    path = registry_path(project, PROJECT_THEME_REGISTRY, GLOBAL_THEME_REGISTRY)
    payload = read_json(path)
    return path, payload, registry_record_by_id(payload, "themes")


def resolve_theme_payload(project: Path, theme_registry_path: Path, theme_record: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    raw_path = theme_record.get("path")
    if isinstance(raw_path, str) and raw_path:
        if theme_registry_path.is_relative_to(project):
            candidate = (project / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path)
        else:
            candidate = (SCRIPT_DIR.parents[2] / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path)
        if candidate.exists():
            return candidate, read_json(candidate)
    return None, theme_record


def template_registry_hash(path: Path) -> str:
    return file_sha256(path)


def theme_registry_hash(path: Path, theme_files: list[Path]) -> str:
    parts = [file_sha256(path)]
    for item in sorted(theme_files):
        parts.append(item.as_posix())
        parts.append(file_sha256(item))
    return strings_sha256(parts)


def validate_registry_bindings(project: Path, spec: dict[str, Any], *, page: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    template_path, template_payload, templates = load_template_registry(project)
    theme_path, theme_payload, themes = load_theme_registry(project)
    template_id = spec.get("template_id")
    theme_id = spec.get("theme_id")
    template_record = templates.get(template_id) if isinstance(template_id, str) else None
    theme_record = themes.get(theme_id) if isinstance(theme_id, str) else None
    theme_file: Path | None = None
    theme_payload_for_id: dict[str, Any] = {}
    if template_record is None:
        issues.append({"code": "canvas_spec_template_unknown", "message": f"page {page} template_id {template_id!r} is not present in Template Registry"})
    elif template_record.get("status") != "active":
        issues.append({"code": "canvas_spec_template_inactive", "message": f"page {page} template_id {template_id!r} is not active"})
    if theme_record is None:
        issues.append({"code": "canvas_spec_theme_unknown", "message": f"page {page} theme_id {theme_id!r} is not present in Theme Registry"})
    elif theme_record.get("status") != "active":
        issues.append({"code": "canvas_spec_theme_inactive", "message": f"page {page} theme_id {theme_id!r} is not active"})
    else:
        theme_file, theme_payload_for_id = resolve_theme_payload(project, theme_path, theme_record)
    if template_record and theme_id:
        allowed = template_record.get("supported_theme_ids")
        if isinstance(allowed, list) and theme_id not in allowed:
            issues.append({"code": "canvas_spec_theme_not_allowed", "message": f"page {page} template_id {template_id!r} does not allow theme_id {theme_id!r}"})
    if template_record:
        content = spec.get("content") if isinstance(spec.get("content"), dict) else {}
        required = template_record.get("required_content")
        if isinstance(required, list):
            for key in required:
                if not isinstance(key, str):
                    continue
                value = content.get(key)
                if value is None or value == "" or value == []:
                    issues.append({"code": "canvas_spec_template_required_content_missing", "message": f"page {page} template {template_id!r} requires content.{key}"})
        max_items = template_record.get("max_items")
        if isinstance(max_items, dict):
            for key, max_count in max_items.items():
                if isinstance(key, str) and isinstance(max_count, int) and isinstance(content.get(key), list) and len(content[key]) > max_count:
                    issues.append({"code": "canvas_spec_template_too_many_items", "message": f"page {page} content.{key} exceeds template max_items {max_count}"})
        text_budget = template_record.get("text_budget")
        if isinstance(text_budget, dict):
            for key, max_chars in text_budget.items():
                if not isinstance(key, str) or not isinstance(max_chars, int):
                    continue
                value = content.get(key)
                values = value if isinstance(value, list) else [value]
                for index, item in enumerate(values):
                    if isinstance(item, str) and len(item.strip()) > max_chars:
                        suffix = f"[{index}]" if isinstance(value, list) else ""
                        issues.append({"code": "canvas_spec_text_budget_exceeded", "message": f"page {page} content.{key}{suffix} exceeds text_budget {max_chars}"})
    registry = {
        "template_registry_path": repo_relpath(template_path) if not template_path.is_relative_to(project) else relpath(template_path, project),
        "template_registry_sha256": template_registry_hash(template_path),
        "theme_registry_path": repo_relpath(theme_path) if not theme_path.is_relative_to(project) else relpath(theme_path, project),
        "theme_files": [repo_relpath(theme_file) if theme_file and not theme_file.is_relative_to(project) else relpath(theme_file, project)] if theme_file else [],
        "theme_registry_sha256": theme_registry_hash(theme_path, [theme_file] if theme_file else []),
        "template_record": template_record,
        "theme_record": theme_record,
        "theme_payload": theme_payload_for_id,
    }
    return issues, registry


def apply_registry_theme(spec: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    theme_payload = registry.get("theme_payload")
    if isinstance(theme_payload, dict) and isinstance(theme_payload.get("colors"), dict):
        merged = json.loads(json.dumps(spec, ensure_ascii=False))
        merged["theme"] = theme_payload
        return merged
    return spec


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def attr(element: ElementTree.Element, name: str) -> str | None:
    value = element.attrib.get(name)
    return value if value is not None and value != "" else None


def number(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace("px", ""))
        except ValueError:
            return default
    return default


def style_attr(style: dict[str, Any]) -> str:
    pairs: list[str] = []
    for key, value in style.items():
        if value is None:
            continue
        pairs.append(f"{key}:{value}")
    return ";".join(pairs)


def svg_attrs(attrs: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in attrs.items():
        if value is None:
            continue
        parts.append(f"{key}={quoteattr(str(value))}")
    return " ".join(parts)


def normalized_box(payload: Any) -> dict[str, float] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "x": number(payload.get("x"), -1),
        "y": number(payload.get("y"), -1),
        "width": number(payload.get("width"), -1),
        "height": number(payload.get("height"), -1),
    }


def box_contains(container: dict[str, float], child: dict[str, float]) -> bool:
    return (
        child["x"] >= container["x"]
        and child["y"] >= container["y"]
        and child["x"] + child["width"] <= container["x"] + container["width"]
        and child["y"] + child["height"] <= container["y"] + container["height"]
    )


def validate_canvas_spec(spec: dict[str, Any], *, page: int) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if spec.get("version") != CANVAS_SPEC_VERSION:
        issues.append({"code": "canvas_spec_version_invalid", "message": f"page {page} canvas_spec.version must be {CANVAS_SPEC_VERSION}"})
    canvas = spec.get("canvas")
    if not isinstance(canvas, dict):
        issues.append({"code": "canvas_spec_canvas_missing", "message": f"page {page} canvas_spec.canvas is required"})
    else:
        if canvas.get("width") != 960 or canvas.get("height") != 540 or canvas.get("viewBox") != "0 0 960 540":
            issues.append({"code": "canvas_spec_canvas_invalid", "message": f"page {page} must use 960x540 canvas and viewBox 0 0 960 540"})
    safe_area = normalized_box(spec.get("safe_area"))
    if safe_area is None or safe_area["width"] <= 0 or safe_area["height"] <= 0:
        issues.append({"code": "canvas_spec_safe_area_missing", "message": f"page {page} canvas_spec.safe_area is required"})
        safe_area = None
    quality_constraints = spec.get("quality_constraints")
    if not isinstance(quality_constraints, dict):
        issues.append({"code": "canvas_spec_quality_constraints_missing", "message": f"page {page} canvas_spec.quality_constraints is required"})
    else:
        quality_safe_area = normalized_box(quality_constraints.get("safe_area"))
        if quality_safe_area is None or quality_safe_area["width"] <= 0 or quality_safe_area["height"] <= 0:
            issues.append({"code": "canvas_spec_quality_safe_area_missing", "message": f"page {page} quality_constraints.safe_area is required"})
        else:
            safe_area = quality_safe_area
        min_font_size = quality_constraints.get("min_font_size")
        if not isinstance(min_font_size, (int, float)) or isinstance(min_font_size, bool) or min_font_size < 1:
            issues.append({"code": "canvas_spec_min_font_size_invalid", "message": f"page {page} quality_constraints.min_font_size must be positive"})
    template_id = spec.get("template_id")
    if template_id not in SUPPORTED_TEMPLATES:
        issues.append({"code": "canvas_spec_template_unsupported", "message": f"page {page} template_id {template_id!r} is not supported by the artboard renderer"})
    if not isinstance(spec.get("theme_id"), str) or not spec.get("theme_id"):
        issues.append({"code": "canvas_spec_theme_id_missing", "message": f"page {page} canvas_spec.theme_id is required"})
    if not isinstance(spec.get("theme"), dict):
        issues.append({"code": "canvas_spec_theme_missing", "message": f"page {page} canvas_spec.theme is required for schema compatibility"})
    content = spec.get("content")
    if not isinstance(content, dict):
        issues.append({"code": "canvas_spec_content_missing", "message": f"page {page} canvas_spec.content is required"})
    else:
        title = content.get("title")
        if not isinstance(title, str) or not title.strip():
            issues.append({"code": "canvas_spec_title_missing", "message": f"page {page} content.title is required"})
    unsupported = spec.get("unsupported_features")
    if isinstance(unsupported, list) and unsupported:
        issues.append({"code": "canvas_spec_unsupported_features", "message": f"page {page} declares unsupported_features: {unsupported}"})
    semantic_elements = spec.get("semantic_elements")
    canvas_box = {"x": 0, "y": 0, "width": 960, "height": 540}
    if not isinstance(semantic_elements, list) or not semantic_elements:
        issues.append({"code": "canvas_spec_semantic_elements_missing", "message": f"page {page} semantic_elements must contain at least one element"})
    else:
        for index, element in enumerate(semantic_elements):
            if not isinstance(element, dict):
                issues.append({"code": "canvas_spec_semantic_element_invalid", "message": f"page {page} semantic_elements[{index}] must be an object"})
                continue
            element_id = element.get("element_id") or f"#{index}"
            bbox = normalized_box(element.get("bbox"))
            if bbox is None or bbox["width"] <= 0 or bbox["height"] <= 0:
                issues.append({"code": "canvas_spec_semantic_bbox_invalid", "message": f"page {page} semantic element {element_id!r} requires positive bbox"})
                continue
            if not box_contains(canvas_box, bbox):
                issues.append({"code": "canvas_spec_bbox_out_of_canvas", "message": f"page {page} semantic element {element_id!r} bbox exceeds 960x540 canvas"})
            role = element.get("role")
            if safe_area and role != "background" and not box_contains(safe_area, bbox):
                issues.append({"code": "canvas_spec_bbox_out_of_safe_area", "message": f"page {page} semantic element {element_id!r} bbox exceeds safe_area"})
    return issues


def normalize_theme(spec: dict[str, Any]) -> dict[str, str]:
    raw = spec.get("theme") if isinstance(spec.get("theme"), dict) else {}
    colors = raw.get("colors") if isinstance(raw.get("colors"), dict) else {}
    return {
        "background": str(colors.get("background") or "#0F172A"),
        "panel": str(colors.get("panel") or "#111827"),
        "primary": str(colors.get("primary") or "#60A5FA"),
        "accent": str(colors.get("accent") or "#A78BFA"),
        "text": str(colors.get("text") or "#F8FAFC"),
        "muted": str(colors.get("muted") or "#CBD5E1"),
    }


def content_text(spec: dict[str, Any], key: str, default: str = "") -> str:
    content = spec.get("content") if isinstance(spec.get("content"), dict) else {}
    value = content.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def content_list(spec: dict[str, Any], key: str) -> list[str]:
    content = spec.get("content") if isinstance(spec.get("content"), dict) else {}
    raw = content.get(key)
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()] if isinstance(raw, list) else []


def content_first_list(spec: dict[str, Any], keys: list[str], default: list[str]) -> list[str]:
    for key in keys:
        values = content_list(spec, key)
        if values:
            return values
    return default


def svg_text(
    parts: list[str],
    nodes: list[dict[str, Any]],
    node_id: str,
    value: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    font_size: float,
    font_weight: int = 700,
) -> None:
    box_height = max(height, 30)
    nodes.append(
        {
            "id": node_id,
            "kind": "text",
            "x": x,
            "y": y,
            "width": width,
            "height": box_height,
            "text": value,
            "fill": fill,
            "font_size": font_size,
            "font_weight": font_weight,
        }
    )
    baseline = y + min(box_height - 4, font_size * 1.18)
    parts.append(
        f'<text data-node-id="{node_id}" data-box-x="{x:g}" data-box-y="{y:g}" '
        f'data-box-width="{width:g}" data-box-height="{box_height:g}" x="{x:g}" y="{baseline:g}" '
        f'fill="{fill}" font-size="{font_size:g}" font-weight="{font_weight}" font-family="Inter">{escape(value)}</text>'
    )


def svg_rect(
    parts: list[str],
    nodes: list[dict[str, Any]],
    node_id: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    opacity: float | None = None,
    stroke: str | None = None,
    stroke_width: float | None = None,
) -> None:
    nodes.append({"id": node_id, "kind": "rect", "x": x, "y": y, "width": width, "height": height, "fill": fill, "opacity": opacity, "stroke": stroke, "stroke_width": stroke_width})
    parts.append(
        f'<rect data-node-id="{node_id}" x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        f'fill="{fill}"'
        + (f' opacity="{opacity:g}"' if opacity is not None else "")
        + (f' stroke="{stroke}"' if stroke else "")
        + (f' stroke-width="{stroke_width:g}"' if stroke_width is not None else "")
        + "/>"
    )


def svg_circle(
    parts: list[str],
    nodes: list[dict[str, Any]],
    node_id: str,
    *,
    cx: float,
    cy: float,
    r: float,
    fill: str,
    opacity: float | None = None,
    stroke: str | None = None,
    stroke_width: float | None = None,
) -> None:
    nodes.append({"id": node_id, "kind": "circle", "x": cx - r, "y": cy - r, "width": r * 2, "height": r * 2, "fill": fill, "opacity": opacity, "stroke": stroke, "stroke_width": stroke_width})
    parts.append(
        f'<circle data-node-id="{node_id}" cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"'
        + (f' opacity="{opacity:g}"' if opacity is not None else "")
        + (f' stroke="{stroke}"' if stroke else "")
        + (f' stroke-width="{stroke_width:g}"' if stroke_width is not None else "")
        + "/>"
    )


def svg_line(
    parts: list[str],
    nodes: list[dict[str, Any]],
    node_id: str,
    *,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    stroke: str,
    stroke_width: float = 2,
    opacity: float | None = None,
) -> None:
    nodes.append(
        {
            "id": node_id,
            "kind": "line",
            "x": min(x1, x2),
            "y": min(y1, y2),
            "width": max(abs(x2 - x1), 1),
            "height": max(abs(y2 - y1), 1),
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "stroke": stroke,
            "stroke_width": stroke_width,
            "opacity": opacity,
        }
    )
    parts.append(
        f'<line data-node-id="{node_id}" x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{stroke}" stroke-width="{stroke_width:g}"'
        + (f' opacity="{opacity:g}"' if opacity is not None else "")
        + "/>"
    )


def svg_path(
    parts: list[str],
    nodes: list[dict[str, Any]],
    node_id: str,
    *,
    d: str,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str = "none",
    stroke: str | None = None,
    stroke_width: float | None = None,
    opacity: float | None = None,
) -> None:
    nodes.append({"id": node_id, "kind": "path", "x": x, "y": y, "width": width, "height": height, "d": d, "fill": fill, "stroke": stroke, "stroke_width": stroke_width, "opacity": opacity})
    parts.append(
        f'<path data-node-id="{node_id}" d="{d}" x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" fill="{fill}"'
        + (f' stroke="{stroke}"' if stroke else "")
        + (f' stroke-width="{stroke_width:g}"' if stroke_width is not None else "")
        + (f' opacity="{opacity:g}"' if opacity is not None else "")
        + "/>"
    )


def begin_template_svg(theme: dict[str, str], nodes: list[dict[str, Any]]) -> list[str]:
    nodes.append({"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540, "fill": theme["background"]})
    return [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
    ]


def add_template_header(parts: list[str], nodes: list[dict[str, Any]], spec: dict[str, Any], theme: dict[str, str], *, title_size: int = 40, title_width: int = 710) -> None:
    eyebrow = content_text(spec, "eyebrow", str(spec.get("template_id") or "ARTBOARD").replace("-", " ").upper())
    title = content_text(spec, "title", "Untitled")
    subtitle = content_text(spec, "subtitle", content_text(spec, "summary", ""))
    svg_text(parts, nodes, "eyebrow", eyebrow.upper(), x=64, y=54, width=380, height=28, fill=theme["primary"], font_size=17, font_weight=850)
    svg_text(parts, nodes, "title", title, x=64, y=91, width=title_width, height=76, fill=theme["text"], font_size=title_size, font_weight=850)
    if subtitle:
        svg_text(parts, nodes, "subtitle", subtitle, x=66, y=168, width=min(title_width, 700), height=58, fill=theme["muted"], font_size=21, font_weight=560)


def semantic_role_for_node(node: dict[str, Any]) -> str:
    node_id = str(node.get("id") or "")
    kind = str(node.get("kind") or "")
    if node_id == "background":
        return "background"
    if kind == "text":
        if node_id.startswith("chip-"):
            return "badge"
        if node_id.startswith("left-point-") or node_id.startswith("right-point-"):
            return "body"
        return node_id or "text"
    if "panel" in node_id or "card" in node_id:
        return "container"
    return "decorative"


def semantic_source_ref_for_node(node: dict[str, Any]) -> str | None:
    node_id = str(node.get("id") or "")
    source_by_id = {
        "eyebrow": "canvas_spec.content.eyebrow",
        "title": "canvas_spec.content.title",
        "subtitle": "canvas_spec.content.subtitle",
        "left-title": "canvas_spec.content.left_title",
        "right-title": "canvas_spec.content.right_title",
        "conclusion": "canvas_spec.content.conclusion",
    }
    if node_id in source_by_id:
        return source_by_id[node_id]
    if node_id.startswith("chip-"):
        return "canvas_spec.content.chips[]"
    if node_id.startswith("left-point-"):
        return "canvas_spec.content.left_points[]"
    if node_id.startswith("right-point-"):
        return "canvas_spec.content.right_points[]"
    if node_id.startswith("takeaway-"):
        return "canvas_spec.content.takeaways[]"
    return None


def semantic_elements_from_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        elements.append(
            {
                "element_id": node_id,
                "kind": str(node.get("kind") or "unknown"),
                "role": semantic_role_for_node(node),
                "source_ref": semantic_source_ref_for_node(node),
                "text": node.get("text") if isinstance(node.get("text"), str) else None,
                "bbox": {
                    "x": number(node.get("x"), 0),
                    "y": number(node.get("y"), 0),
                    "width": number(node.get("width"), 0),
                    "height": number(node.get("height"), 0),
                },
                "style": semantic_style_for_node(node),
            }
        )
    return elements


def semantic_style_for_node(node: dict[str, Any]) -> dict[str, Any]:
    style: dict[str, Any] = {}
    for key in ["fill", "stroke", "stroke_width", "opacity", "font_size", "font_weight", "d", "x1", "y1", "x2", "y2"]:
        value = node.get(key)
        if value is not None:
            style[key] = value
    return style


def template_cover_hero(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    eyebrow = content_text(spec, "eyebrow", "SVGLIDE ARTBOARD")
    title = content_text(spec, "title", "Untitled")
    subtitle = content_text(spec, "subtitle", "")
    chips = content_list(spec, "chips")[:4]
    nodes = [
        {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
        {"id": "accent-orbit", "kind": "circle", "x": 724, "y": 36, "width": 192, "height": 192},
        {"id": "panel", "kind": "rect", "x": 56, "y": 64, "width": 704, "height": 356},
        {"id": "eyebrow", "kind": "text", "x": 84, "y": 98, "width": 420, "height": 32, "text": eyebrow},
        {"id": "title", "kind": "text", "x": 84, "y": 142, "width": 628, "height": 142, "text": title},
        {"id": "subtitle", "kind": "text", "x": 88, "y": 302, "width": 610, "height": 74, "text": subtitle},
    ]
    chip_nodes = []
    chip_x = 84
    for index, chip in enumerate(chips):
        width = min(188, max(92, len(chip) * 13 + 34))
        chip_nodes.append({"id": f"chip-{index + 1}", "kind": "text", "x": chip_x, "y": 444, "width": width, "height": 40, "text": chip})
        chip_x += width + 14
    nodes.extend(chip_nodes)
    text_nodes = {
        "eyebrow": (eyebrow, 18, 700, theme["primary"]),
        "title": (title, 58, 800, theme["text"]),
        "subtitle": (subtitle, 24, 500, theme["muted"]),
    }
    parts = [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
        f'<circle data-node-id="accent-orbit" cx="820" cy="132" r="96" fill="{theme["accent"]}" opacity="0.28"/>',
        f'<circle data-node-id="accent-dot" cx="812" cy="150" r="72" fill="{theme["primary"]}" opacity="0.22"/>',
        f'<rect data-node-id="panel" x="56" y="64" width="704" height="356" fill="{theme["panel"]}" opacity="0.82"/>',
    ]
    for node_id, (text, font_size, font_weight, fill) in text_nodes.items():
        node = next(item for item in nodes if item["id"] == node_id)
        y = node["y"] + font_size
        parts.append(
            f'<text data-node-id="{node_id}" data-box-x="{node["x"]}" data-box-y="{node["y"]}" '
            f'data-box-width="{node["width"]}" data-box-height="{node["height"]}" '
            f'x="{node["x"]}" y="{y}" fill="{fill}" font-size="{font_size}" font-weight="{font_weight}" '
            f'font-family="Inter">{escape(text)}</text>'
        )
    for index, chip in enumerate(chips):
        node_id = f"chip-{index + 1}"
        node = next(item for item in chip_nodes if item["id"] == node_id)
        parts.append(
            f'<rect data-node-id="{node_id}-bg" x="{node["x"]}" y="{node["y"]}" width="{node["width"]}" height="{node["height"]}" '
            f'fill="{theme["primary"]}" opacity="0.16"/>'
        )
        parts.append(
            f'<text data-node-id="{node_id}" data-box-x="{node["x"] + 15}" data-box-y="{node["y"] + 6}" '
            f'data-box-width="{node["width"] - 30}" data-box-height="30" x="{node["x"] + 15}" y="{node["y"] + 27}" '
            f'fill="{theme["text"]}" font-size="17" font-weight="600" font-family="Inter">{escape(chip)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_section_title(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    eyebrow = content_text(spec, "eyebrow", "SECTION")
    title = content_text(spec, "title", "Untitled")
    subtitle = content_text(spec, "subtitle", "")
    nodes = [
        {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
        {"id": "rule", "kind": "rect", "x": 72, "y": 124, "width": 8, "height": 250},
        {"id": "eyebrow", "kind": "text", "x": 104, "y": 126, "width": 420, "height": 32, "text": eyebrow},
        {"id": "title", "kind": "text", "x": 104, "y": 176, "width": 680, "height": 122, "text": title},
        {"id": "subtitle", "kind": "text", "x": 108, "y": 322, "width": 640, "height": 66, "text": subtitle},
    ]
    parts = [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
        f'<rect data-node-id="rule" x="72" y="124" width="8" height="250" fill="{theme["primary"]}"/>',
        f'<circle data-node-id="accent" cx="780" cy="158" r="92" fill="{theme["accent"]}" opacity="0.24"/>',
        f'<text data-node-id="eyebrow" data-box-x="104" data-box-y="126" data-box-width="420" data-box-height="32" x="104" y="144" fill="{theme["primary"]}" font-size="18" font-weight="700" font-family="Inter">{escape(eyebrow)}</text>',
        f'<text data-node-id="title" data-box-x="104" data-box-y="176" data-box-width="680" data-box-height="122" x="104" y="236" fill="{theme["text"]}" font-size="56" font-weight="800" font-family="Inter">{escape(title)}</text>',
        f'<text data-node-id="subtitle" data-box-x="108" data-box-y="322" data-box-width="640" data-box-height="66" x="108" y="350" fill="{theme["muted"]}" font-size="24" font-weight="500" font-family="Inter">{escape(subtitle)}</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n", nodes


def template_summary_final(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    eyebrow = content_text(spec, "eyebrow", "SUMMARY")
    title = content_text(spec, "title", "Summary")
    subtitle = content_text(spec, "subtitle", "")
    takeaways = content_list(spec, "takeaways")[:3]
    nodes = [
        {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
        {"id": "metric-bar-1", "kind": "rect", "x": 712, "y": 322, "width": 18, "height": 30},
        {"id": "metric-bar-2", "kind": "rect", "x": 742, "y": 304, "width": 18, "height": 48},
        {"id": "metric-bar-3", "kind": "rect", "x": 772, "y": 286, "width": 18, "height": 66},
        {"id": "eyebrow", "kind": "text", "x": 72, "y": 64, "width": 420, "height": 32, "text": eyebrow},
        {"id": "title", "kind": "text", "x": 72, "y": 110, "width": 700, "height": 110, "text": title},
        {"id": "subtitle", "kind": "text", "x": 72, "y": 244, "width": 640, "height": 66, "text": subtitle},
    ]
    for index, takeaway in enumerate(takeaways):
        x = 72 + index * 268
        nodes.extend(
            [
                {"id": f"takeaway-card-{index + 1}", "kind": "rect", "x": x, "y": 344, "width": 250, "height": 126},
                {"id": f"takeaway-index-{index + 1}", "kind": "text", "x": x + 22, "y": 366, "width": 64, "height": 30, "text": f"{index + 1:02d}"},
                {"id": f"takeaway-{index + 1}", "kind": "text", "x": x + 22, "y": 404, "width": 202, "height": 54, "text": takeaway},
            ]
        )
    parts = [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
        f'<circle data-node-id="accent" cx="786" cy="136" r="82" fill="{theme["accent"]}" opacity="0.22"/>',
        f'<rect data-node-id="metric-bar-1" x="712" y="322" width="18" height="30" fill="{theme["primary"]}" opacity="0.72"/>',
        f'<rect data-node-id="metric-bar-2" x="742" y="304" width="18" height="48" fill="{theme["primary"]}" opacity="0.86"/>',
        f'<rect data-node-id="metric-bar-3" x="772" y="286" width="18" height="66" fill="{theme["accent"]}" opacity="0.92"/>',
        f'<text data-node-id="eyebrow" data-box-x="72" data-box-y="64" data-box-width="420" data-box-height="32" x="72" y="84" fill="{theme["primary"]}" font-size="18" font-weight="800" font-family="Inter">{escape(eyebrow)}</text>',
        f'<text data-node-id="title" data-box-x="72" data-box-y="110" data-box-width="700" data-box-height="110" x="72" y="164" fill="{theme["text"]}" font-size="50" font-weight="850" font-family="Inter">{escape(title)}</text>',
        f'<text data-node-id="subtitle" data-box-x="72" data-box-y="244" data-box-width="640" data-box-height="66" x="72" y="274" fill="{theme["muted"]}" font-size="23" font-weight="500" font-family="Inter">{escape(subtitle)}</text>',
    ]
    for index, takeaway in enumerate(takeaways):
        x = 72 + index * 268
        parts.append(f'<rect data-node-id="takeaway-card-{index + 1}" x="{x}" y="344" width="250" height="126" fill="{theme["panel"]}"/>')
        parts.append(f'<text data-node-id="takeaway-index-{index + 1}" data-box-x="{x + 22}" data-box-y="366" data-box-width="64" data-box-height="30" x="{x + 22}" y="386" fill="{theme["primary"]}" font-size="18" font-weight="800" font-family="Inter">{index + 1:02d}</text>')
        parts.append(f'<text data-node-id="takeaway-{index + 1}" data-box-x="{x + 22}" data-box-y="404" data-box-width="202" data-box-height="54" x="{x + 22}" y="428" fill="{theme["text"]}" font-size="21" font-weight="700" font-family="Inter">{escape(takeaway)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_comparison(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    title = content_text(spec, "title", "Comparison")
    left_title = content_text(spec, "left_title", "Before")
    right_title = content_text(spec, "right_title", "After")
    left_points = content_list(spec, "left_points")[:3]
    right_points = content_list(spec, "right_points")[:3]
    conclusion = content_text(spec, "conclusion", "")
    nodes = [
        {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
        {"id": "title", "kind": "text", "x": 64, "y": 52, "width": 760, "height": 64, "text": title},
        {"id": "left-card", "kind": "rect", "x": 64, "y": 140, "width": 390, "height": 250},
        {"id": "right-card", "kind": "rect", "x": 506, "y": 140, "width": 390, "height": 250},
        {"id": "comparison-divider", "kind": "path", "x": 480, "y": 144, "width": 1, "height": 246, "d": "M480 144 L480 390", "fill": "none", "stroke": theme["primary"], "stroke_width": 2, "opacity": 0.45},
        {"id": "left-title", "kind": "text", "x": 92, "y": 168, "width": 320, "height": 34, "text": left_title},
        {"id": "left-point-1", "kind": "text", "x": 116, "y": 222, "width": 296, "height": 36, "text": left_points[0] if len(left_points) > 0 else ""},
        {"id": "left-point-2", "kind": "text", "x": 116, "y": 270, "width": 296, "height": 36, "text": left_points[1] if len(left_points) > 1 else ""},
        {"id": "left-point-3", "kind": "text", "x": 116, "y": 318, "width": 296, "height": 36, "text": left_points[2] if len(left_points) > 2 else ""},
        {"id": "right-title", "kind": "text", "x": 534, "y": 168, "width": 320, "height": 34, "text": right_title},
        {"id": "right-point-1", "kind": "text", "x": 558, "y": 222, "width": 296, "height": 36, "text": right_points[0] if len(right_points) > 0 else ""},
        {"id": "right-point-2", "kind": "text", "x": 558, "y": 270, "width": 296, "height": 36, "text": right_points[1] if len(right_points) > 1 else ""},
        {"id": "right-point-3", "kind": "text", "x": 558, "y": 318, "width": 296, "height": 36, "text": right_points[2] if len(right_points) > 2 else ""},
        {"id": "conclusion", "kind": "text", "x": 86, "y": 426, "width": 788, "height": 42, "text": conclusion},
    ]
    parts = [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
        f'<text data-node-id="title" data-box-x="64" data-box-y="52" data-box-width="760" data-box-height="64" x="64" y="96" fill="{theme["text"]}" font-size="40" font-weight="800" font-family="Inter">{escape(title)}</text>',
        f'<rect data-node-id="left-card" x="64" y="140" width="390" height="250" fill="{theme["panel"]}" opacity="0.82"/>',
        f'<rect data-node-id="right-card" x="506" y="140" width="390" height="250" fill="{theme["panel"]}" opacity="0.82"/>',
        f'<path data-node-id="comparison-divider" d="M480 144 L480 390" x="480" y="144" width="1" height="246" fill="none" stroke="{theme["primary"]}" stroke-width="2" opacity="0.45"/>',
        f'<text data-node-id="left-title" data-box-x="92" data-box-y="168" data-box-width="320" data-box-height="34" x="92" y="194" fill="{theme["primary"]}" font-size="24" font-weight="800" font-family="Inter">{escape(left_title)}</text>',
        f'<text data-node-id="right-title" data-box-x="534" data-box-y="168" data-box-width="320" data-box-height="34" x="534" y="194" fill="{theme["accent"]}" font-size="24" font-weight="800" font-family="Inter">{escape(right_title)}</text>',
    ]
    for idx, point in enumerate(left_points):
        y = 248 + idx * 48
        parts.append(f'<circle data-node-id="left-dot-{idx + 1}" cx="98" cy="{y - 7}" r="5" fill="{theme["primary"]}"/>')
        parts.append(f'<text data-node-id="left-point-{idx + 1}" data-box-x="116" data-box-y="{y - 26}" data-box-width="296" data-box-height="36" x="116" y="{y}" fill="{theme["muted"]}" font-size="20" font-weight="500" font-family="Inter">{escape(point)}</text>')
    for idx, point in enumerate(right_points):
        y = 248 + idx * 48
        parts.append(f'<circle data-node-id="right-dot-{idx + 1}" cx="540" cy="{y - 7}" r="5" fill="{theme["accent"]}"/>')
        parts.append(f'<text data-node-id="right-point-{idx + 1}" data-box-x="558" data-box-y="{y - 26}" data-box-width="296" data-box-height="36" x="558" y="{y}" fill="{theme["muted"]}" font-size="20" font-weight="500" font-family="Inter">{escape(point)}</text>')
    parts.extend(
        [
            f'<rect data-node-id="conclusion-bg" x="64" y="414" width="832" height="66" fill="{theme["primary"]}" opacity="0.16"/>',
            f'<text data-node-id="conclusion" data-box-x="86" data-box-y="426" data-box-width="788" data-box-height="42" x="86" y="454" fill="{theme["text"]}" font-size="22" font-weight="700" font-family="Inter">{escape(conclusion)}</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n", nodes


def template_agenda_list(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    items = content_first_list(spec, ["items", "takeaways"], ["Context", "Evidence", "Decision"])[:6]
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    svg_path(parts, nodes, "agenda-trajectory", d="M674 54 L888 54 L842 486 L674 486 Z", x=674, y=54, width=214, height=432, fill=theme["primary"], opacity=0.08)
    svg_line(parts, nodes, "agenda-rail", x1=108, y1=218, x2=108, y2=444, stroke=theme["primary"], stroke_width=3, opacity=0.65)
    add_template_header(parts, nodes, spec, theme, title_size=42, title_width=740)
    start_y = 238
    for index, item in enumerate(items):
        y = start_y + index * 42
        svg_circle(parts, nodes, f"agenda-node-{index + 1}", cx=108, cy=y + 19, r=12, fill=theme["background"], stroke=theme["primary"], stroke_width=3)
        svg_rect(parts, nodes, f"agenda-card-{index + 1}", x=148, y=y, width=586, height=38, fill=theme["panel"], opacity=0.86)
        svg_text(parts, nodes, f"agenda-index-{index + 1}", f"{index + 1:02d}", x=166, y=y + 7, width=54, height=24, fill=theme["primary"], font_size=17, font_weight=850)
        svg_text(parts, nodes, f"agenda-item-{index + 1}", item, x=226, y=y + 6, width=470, height=26, fill=theme["text"], font_size=19, font_weight=720)
    svg_rect(parts, nodes, "agenda-stack-panel", x=780, y=220, width=88, height=214, fill=theme["panel"], opacity=0.7, stroke=theme["primary"], stroke_width=1.5)
    for index, height in enumerate([26, 46, 72, 38]):
        svg_rect(parts, nodes, f"agenda-stack-bar-{index + 1}", x=806 + index * 12, y=394 - height, width=8, height=height, fill=theme["accent"] if index == 2 else theme["primary"], opacity=0.75)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_timeline_steps(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    events = content_first_list(spec, ["events", "steps", "items"], ["Discover", "Design", "Deliver", "Measure"])[:5]
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=40, title_width=740)
    svg_path(parts, nodes, "timeline-orbit", d="M104 296 C260 216 390 408 532 318 C640 246 740 246 856 330", x=104, y=216, width=752, height=192, stroke=theme["accent"], stroke_width=2.5, opacity=0.48)
    svg_line(parts, nodes, "timeline-rail", x1=104, y1=320, x2=856, y2=320, stroke=theme["primary"], stroke_width=3, opacity=0.72)
    count = max(1, len(events))
    for index, event in enumerate(events):
        x = 116 + index * (724 / max(1, count - 1))
        card_y = 368 if index % 2 == 0 else 244
        svg_line(parts, nodes, f"timeline-pin-{index + 1}", x1=x, y1=320, x2=x, y2=card_y + (0 if index % 2 == 0 else 74), stroke=theme["muted"], stroke_width=1.8, opacity=0.5)
        svg_circle(parts, nodes, f"timeline-node-{index + 1}", cx=x, cy=320, r=18, fill=theme["primary"] if index % 2 == 0 else theme["accent"], opacity=0.92)
        svg_text(parts, nodes, f"timeline-index-{index + 1}", f"{index + 1}", x=x - 16, y=306, width=32, height=30, fill=theme["text"], font_size=16, font_weight=850)
        svg_rect(parts, nodes, f"timeline-card-{index + 1}", x=x - 58, y=card_y, width=116, height=74, fill=theme["panel"], opacity=0.88)
        svg_text(parts, nodes, f"timeline-event-{index + 1}", event, x=x - 45, y=card_y + 18, width=90, height=42, fill=theme["text"], font_size=18, font_weight=760)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_process_flow(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    steps = content_first_list(spec, ["steps", "items"], ["Input", "Normalize", "Render", "Verify"])[:5]
    conclusion = content_text(spec, "conclusion", "")
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=40, title_width=720)
    svg_path(parts, nodes, "process-main-flow", d="M98 332 C234 258 350 392 472 318 C594 244 692 394 836 306", x=98, y=244, width=738, height=150, stroke=theme["primary"], stroke_width=3, opacity=0.55)
    for index, step in enumerate(steps):
        x = 76 + index * 168
        y = 272 if index % 2 == 0 else 318
        svg_rect(parts, nodes, f"process-card-{index + 1}", x=x, y=y, width=136, height=118, fill=theme["panel"], opacity=0.9, stroke=theme["primary"] if index % 2 == 0 else theme["accent"], stroke_width=1.5)
        svg_circle(parts, nodes, f"process-node-{index + 1}", cx=x + 34, cy=y + 30, r=16, fill=theme["primary"] if index % 2 == 0 else theme["accent"], opacity=0.9)
        svg_text(parts, nodes, f"process-index-{index + 1}", str(index + 1), x=x + 20, y=y + 16, width=32, height=32, fill=theme["text"], font_size=18, font_weight=900)
        svg_text(parts, nodes, f"process-step-{index + 1}", step, x=x + 16, y=y + 56, width=112, height=52, fill=theme["text"], font_size=19, font_weight=780)
        if index < len(steps) - 1:
            svg_line(parts, nodes, f"process-connector-{index + 1}", x1=x + 138, y1=y + 58, x2=x + 166, y2=(318 if index % 2 == 0 else 272) + 58, stroke=theme["muted"], stroke_width=2, opacity=0.55)
            svg_path(parts, nodes, f"process-arrow-{index + 1}", d=f"M{x + 162:g} {(318 if index % 2 == 0 else 272) + 52:g} L{x + 174:g} {(318 if index % 2 == 0 else 272) + 58:g} L{x + 162:g} {(318 if index % 2 == 0 else 272) + 64:g} Z", x=x + 162, y=(318 if index % 2 == 0 else 272) + 52, width=12, height=12, fill=theme["muted"], opacity=0.7)
    if conclusion:
        svg_rect(parts, nodes, "process-conclusion-bg", x=72, y=458, width=816, height=44, fill=theme["primary"], opacity=0.16)
        svg_text(parts, nodes, "conclusion", conclusion, x=92, y=468, width=760, height=28, fill=theme["text"], font_size=19, font_weight=760)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_metric_dashboard(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    metrics = content_first_list(spec, ["metrics", "items"], ["Velocity", "Cost", "Quality", "Reach"])[:6]
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=38, title_width=690)
    svg_rect(parts, nodes, "dashboard-chart-panel", x=520, y=230, width=340, height=214, fill=theme["panel"], opacity=0.86, stroke=theme["primary"], stroke_width=1.5)
    for index, y in enumerate([398, 358, 318, 278]):
        svg_line(parts, nodes, f"dashboard-grid-{index + 1}", x1=548, y1=y, x2=830, y2=y, stroke=theme["muted"], stroke_width=1, opacity=0.22)
    svg_path(parts, nodes, "dashboard-trend", d="M552 392 C592 370 614 388 652 342 C692 300 724 284 760 314 C786 336 806 278 828 252", x=552, y=252, width=276, height=140, stroke=theme["accent"], stroke_width=4, opacity=0.92)
    for index, (cx, cy) in enumerate([(552, 392), (652, 342), (760, 314), (828, 252)]):
        svg_circle(parts, nodes, f"dashboard-trend-node-{index + 1}", cx=cx, cy=cy, r=7, fill=theme["primary"], stroke=theme["background"], stroke_width=2)
    for index, metric in enumerate(metrics):
        x = 72 + (index % 2) * 214
        y = 246 + (index // 2) * 84
        svg_rect(parts, nodes, f"metric-card-{index + 1}", x=x, y=y, width=188, height=76, fill=theme["panel"], opacity=0.88)
        svg_rect(parts, nodes, f"metric-signal-{index + 1}", x=x + 14, y=y + 60, width=46 + index * 9, height=5, fill=theme["primary"] if index % 2 == 0 else theme["accent"], opacity=0.8)
        svg_text(parts, nodes, f"metric-value-{index + 1}", metric, x=x + 14, y=y + 18, width=158, height=36, fill=theme["text"], font_size=19, font_weight=830)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_risk_alert(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    risks = content_first_list(spec, ["risks", "items"], ["Scope drift", "Dependency delay", "Evidence gap"])[:4]
    severity = content_text(spec, "severity", "L2")
    summary = content_text(spec, "summary", "")
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    svg_path(parts, nodes, "risk-warning-triangle", d="M720 126 L846 344 L594 344 Z", x=594, y=126, width=252, height=218, fill=theme["accent"], opacity=0.16, stroke=theme["accent"], stroke_width=2)
    svg_circle(parts, nodes, "risk-severity-ring", cx=720, cy=276, r=54, fill=theme["background"], opacity=0.92, stroke=theme["accent"], stroke_width=5)
    svg_text(parts, nodes, "risk-severity", severity, x=689, y=256, width=62, height=44, fill=theme["text"], font_size=30, font_weight=900)
    add_template_header(parts, nodes, spec, theme, title_size=40, title_width=650)
    svg_line(parts, nodes, "risk-gauge", x1=104, y1=250, x2=104, y2=444, stroke=theme["accent"], stroke_width=4, opacity=0.7)
    for index, risk in enumerate(risks):
        y = 250 + index * 50
        color = theme["accent"] if index == 0 else theme["primary"]
        svg_circle(parts, nodes, f"risk-node-{index + 1}", cx=104, cy=y + 22, r=10, fill=color)
        svg_rect(parts, nodes, f"risk-card-{index + 1}", x=136, y=y, width=476, height=42, fill=theme["panel"], opacity=0.88)
        svg_text(parts, nodes, f"risk-item-{index + 1}", risk, x=154, y=y + 9, width=408, height=24, fill=theme["text"], font_size=20, font_weight=760)
    if summary:
        svg_text(parts, nodes, "risk-summary", summary, x=640, y=338, width=226, height=70, fill=theme["muted"], font_size=18, font_weight=650)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_roadmap_lanes(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    lanes = content_first_list(spec, ["lanes", "items"], ["Now", "Next", "Later"])[:4]
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=38, title_width=700)
    svg_line(parts, nodes, "roadmap-axis", x1=230, y1=276, x2=842, y2=276, stroke=theme["muted"], stroke_width=2, opacity=0.45)
    for index, label in enumerate(["Q1", "Q2", "Q3", "Q4"]):
        x = 270 + index * 154
        svg_circle(parts, nodes, f"roadmap-quarter-node-{index + 1}", cx=x, cy=276, r=6, fill=theme["primary"], opacity=0.78)
        svg_text(parts, nodes, f"roadmap-quarter-{index + 1}", label, x=x - 13, y=238, width=34, height=30, fill=theme["muted"], font_size=15, font_weight=800)
    for index, lane in enumerate(lanes):
        y = 312 + index * 44
        svg_text(parts, nodes, f"roadmap-lane-label-{index + 1}", lane, x=72, y=y + 7, width=136, height=26, fill=theme["primary"], font_size=20, font_weight=850)
        svg_rect(parts, nodes, f"roadmap-lane-bg-{index + 1}", x=226, y=y, width=620, height=34, fill=theme["panel"], opacity=0.72)
        start = 246 + index * 58
        width = 210 + index * 54
        svg_rect(parts, nodes, f"roadmap-lane-bar-{index + 1}", x=start, y=y + 10, width=width, height=12, fill=theme["accent"] if index % 2 else theme["primary"], opacity=0.7)
        svg_circle(parts, nodes, f"roadmap-milestone-{index + 1}", cx=start + width, cy=y + 16, r=11, fill=theme["background"], stroke=theme["accent"] if index % 2 else theme["primary"], stroke_width=3)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_architecture_blueprint(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    items = content_first_list(spec, ["nodes", "items"], ["Planner", "CanvasSpec", "Renderer", "SVGlide"])[:6]
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=36, title_width=640)
    positions = [(102, 268), (366, 238), (630, 268), (102, 388), (366, 358), (630, 388)]
    centers = [(x + 96, y + 32) for x, y in positions[: len(items)]]
    for index in range(max(0, len(centers) - 1)):
        x1, y1 = centers[index]
        x2, y2 = centers[index + 1]
        svg_line(parts, nodes, f"blueprint-link-{index + 1}", x1=x1, y1=y1, x2=x2, y2=y2, stroke=theme["primary"], stroke_width=2, opacity=0.42)
    if len(centers) >= 6:
        svg_path(parts, nodes, "blueprint-loop", d="M198 300 C326 194 598 194 726 300 C584 452 340 452 198 420 Z", x=198, y=194, width=528, height=258, fill="none", stroke=theme["accent"], stroke_width=2, opacity=0.34)
    for index, item in enumerate(items):
        x, y = positions[index]
        stroke = theme["accent"] if index in {1, 4} else theme["primary"]
        svg_rect(parts, nodes, f"blueprint-node-card-{index + 1}", x=x, y=y, width=192, height=64, fill=theme["panel"], opacity=0.88, stroke=stroke, stroke_width=2)
        svg_circle(parts, nodes, f"blueprint-port-{index + 1}", cx=x + 18, cy=y + 32, r=7, fill=stroke)
        svg_text(parts, nodes, f"blueprint-node-text-{index + 1}", item, x=x + 36, y=y + 18, width=146, height=30, fill=theme["text"], font_size=17, font_weight=780)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_image_feature(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    points = content_first_list(spec, ["points", "items"], ["Evidence", "Signal", "Implication"])[:3]
    caption = content_text(spec, "caption", "")
    image_label = content_text(spec, "image_label", "VISUAL ASSET")
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=38, title_width=512)
    nodes.append({"id": "asset-slot-page", "kind": "rect", "x": 584, "y": 70, "width": 336, "height": 334})
    parts.append(
        f'<rect data-node-id="asset-slot-page" x="584" y="70" width="336" height="334" '
        f'fill="none" stroke="{theme["primary"]}" stroke-width="1.5" opacity="0.72"/>'
    )
    nodes.append({"id": "image-label", "kind": "text", "x": 608, "y": 92, "width": 260, "height": 34, "text": image_label.upper()})
    parts.append(
        f'<text data-node-id="image-label" data-svglide-asset-slot="true" data-box-x="608" data-box-y="92" '
        f'data-box-width="260" data-box-height="34" x="608" y="109" fill="{theme["primary"]}" '
        f'font-size="14" font-weight="820" font-family="Inter">{escape(image_label.upper())}</text>'
    )
    svg_line(parts, nodes, "image-rule", x1=608, y1=336, x2=870, y2=336, stroke=theme["muted"], stroke_width=1, opacity=0.45)
    if caption:
        svg_text(parts, nodes, "caption", caption, x=608, y=346, width=262, height=42, fill=theme["muted"], font_size=16, font_weight=600)
    for index, point in enumerate(points):
        y = 282 + index * 62
        svg_rect(parts, nodes, f"feature-point-bg-{index + 1}", x=72, y=y, width=430, height=44, fill=theme["panel"], opacity=0.82)
        svg_circle(parts, nodes, f"feature-point-dot-{index + 1}", cx=94, cy=y + 22, r=6, fill=theme["primary"] if index != 1 else theme["accent"], opacity=0.9)
        svg_text(parts, nodes, f"feature-point-{index + 1}", point, x=114, y=y + 9, width=360, height=28, fill=theme["text"], font_size=18, font_weight=720)
    svg_path(parts, nodes, "feature-trajectory", d="M88 476 C220 424 310 506 498 448 C602 416 704 454 842 404", x=88, y=404, width=754, height=102, stroke=theme["accent"], stroke_width=3, opacity=0.55)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_data_story(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    metrics = content_first_list(spec, ["metrics", "items"], ["$75B", "$1.77T", "+19%", "4.3%"])[:4]
    callout = content_text(spec, "callout", "")
    nodes: list[dict[str, Any]] = []
    parts = begin_template_svg(theme, nodes)
    add_template_header(parts, nodes, spec, theme, title_size=38, title_width=650)
    svg_rect(parts, nodes, "market-terminal", x=56, y=242, width=848, height=226, fill=theme["panel"], opacity=0.82, stroke=theme["primary"], stroke_width=1.4)
    for index, metric in enumerate(metrics):
        x = 86 + index * 204
        accent = theme["primary"] if index % 2 == 0 else theme["accent"]
        svg_text(parts, nodes, f"data-metric-{index + 1}", metric, x=x, y=268, width=164, height=58, fill=accent, font_size=22, font_weight=900)
        svg_rect(parts, nodes, f"data-bar-track-{index + 1}", x=x, y=334, width=148, height=10, fill=theme["muted"], opacity=0.22)
        svg_rect(parts, nodes, f"data-bar-{index + 1}", x=x, y=334, width=60 + index * 26, height=10, fill=accent, opacity=0.86)
        svg_text(parts, nodes, f"data-label-{index + 1}", ["募资规模", "IPO估值", "首日涨幅", "初始流通"][index], x=x, y=354, width=156, height=28, fill=theme["muted"], font_size=15, font_weight=700)
    svg_line(parts, nodes, "unlock-axis", x1=96, y1=424, x2=826, y2=424, stroke=theme["muted"], stroke_width=2, opacity=0.5)
    for index, label in enumerate(["T+0", "70D", "120D", "180D"]):
        x = 96 + index * 242
        svg_circle(parts, nodes, f"unlock-node-{index + 1}", cx=x, cy=424, r=8, fill=theme["primary"] if index < 2 else theme["accent"], opacity=0.92)
        svg_text(parts, nodes, f"unlock-label-{index + 1}", label, x=x - 24, y=440, width=60, height=24, fill=theme["text"], font_size=14, font_weight=760)
    if callout:
        svg_rect(parts, nodes, "data-callout-bg", x=588, y=392, width=260, height=46, fill=theme["background"], opacity=0.72)
        svg_text(parts, nodes, "data-callout", callout, x=604, y=402, width=228, height=28, fill=theme["text"], font_size=16, font_weight=760)
    svg_path(parts, nodes, "data-price-curve", d="M112 396 C224 370 280 412 382 364 C472 326 544 352 624 306 C692 268 746 286 828 252", x=112, y=252, width=716, height=160, stroke=theme["accent"], stroke_width=3.5, opacity=0.78)
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def template_p1_generic(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    theme = normalize_theme(spec)
    template_id = str(spec.get("template_id") or "generic")
    eyebrow = content_text(spec, "eyebrow", template_id.replace("-", " ").upper())
    title = content_text(spec, "title", "Untitled")
    subtitle = content_text(spec, "subtitle", content_text(spec, "summary", ""))
    quote = content_text(spec, "quote", "")
    attribution = content_text(spec, "attribution", "")
    items = content_first_list(
        spec,
        ["items", "steps", "events", "metrics", "points", "sections", "risks", "lanes", "nodes", "takeaways"],
        ["Context", "Evidence", "Decision"],
    )[:6]
    if quote:
        items = [quote, attribution or "Source"] + items[:3]
    nodes = [
        {"id": "background", "kind": "rect", "x": 0, "y": 0, "width": 960, "height": 540},
        {"id": "accent-rule", "kind": "rect", "x": 64, "y": 72, "width": 8, "height": 344},
        {"id": "eyebrow", "kind": "text", "x": 92, "y": 64, "width": 420, "height": 30, "text": eyebrow},
        {"id": "title", "kind": "text", "x": 92, "y": 108, "width": 700, "height": 96, "text": title},
        {"id": "subtitle", "kind": "text", "x": 94, "y": 212, "width": 660, "height": 54, "text": subtitle},
    ]
    parts = [
        f'<svg xmlns="{SVG_NS}" width="960" height="540" viewBox="0 0 960 540">',
        f'<rect data-node-id="background" x="0" y="0" width="960" height="540" fill="{theme["background"]}"/>',
        f'<rect data-node-id="accent-rule" x="64" y="72" width="8" height="344" fill="{theme["primary"]}"/>',
        f'<rect data-node-id="accent-panel" x="760" y="60" width="120" height="120" fill="{theme["accent"]}" opacity="0.20"/>',
        f'<text data-node-id="eyebrow" data-box-x="92" data-box-y="64" data-box-width="420" data-box-height="30" x="92" y="84" fill="{theme["primary"]}" font-size="18" font-weight="800" font-family="Inter">{escape(eyebrow)}</text>',
        f'<text data-node-id="title" data-box-x="92" data-box-y="108" data-box-width="700" data-box-height="96" x="92" y="158" fill="{theme["text"]}" font-size="46" font-weight="850" font-family="Inter">{escape(title)}</text>',
        f'<text data-node-id="subtitle" data-box-x="94" data-box-y="212" data-box-width="660" data-box-height="54" x="94" y="240" fill="{theme["muted"]}" font-size="22" font-weight="500" font-family="Inter">{escape(subtitle)}</text>',
    ]
    for index, item in enumerate(items):
        x = 92 + (index % 3) * 268
        y = 306 + (index // 3) * 92
        nodes.extend(
            [
                {"id": f"item-card-{index + 1}", "kind": "rect", "x": x, "y": y, "width": 244, "height": 72},
                {"id": f"item-{index + 1}", "kind": "text", "x": x + 16, "y": y + 15, "width": 212, "height": 44, "text": item},
            ]
        )
        parts.append(f'<rect data-node-id="item-card-{index + 1}" x="{x}" y="{y}" width="244" height="72" fill="{theme["panel"]}" opacity="0.84"/>')
        parts.append(f'<text data-node-id="item-{index + 1}" data-box-x="{x + 16}" data-box-y="{y + 15}" data-box-width="212" data-box-height="44" x="{x + 16}" y="{y + 43}" fill="{theme["text"]}" font-size="21" font-weight="720" font-family="Inter">{escape(item)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n", nodes


def render_satori_compatible_svg(spec: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    template_id = spec.get("template_id")
    if template_id in {"cover-hero", "cover_hero"}:
        return template_cover_hero(spec)
    if template_id == "comparison-cards":
        return template_comparison(spec)
    if template_id == "summary-final":
        return template_summary_final(spec)
    if template_id in {"section-title", "section_title"}:
        return template_section_title(spec)
    if template_id == "comparison":
        return template_comparison(spec)
    if template_id == "agenda-list":
        return template_agenda_list(spec)
    if template_id == "timeline-steps":
        return template_timeline_steps(spec)
    if template_id == "process-flow":
        return template_process_flow(spec)
    if template_id == "metric-dashboard":
        return template_metric_dashboard(spec)
    if template_id == "risk-alert":
        return template_risk_alert(spec)
    if template_id == "roadmap-lanes":
        return template_roadmap_lanes(spec)
    if template_id == "architecture-blueprint":
        return template_architecture_blueprint(spec)
    if template_id == "image-feature":
        return template_image_feature(spec)
    if template_id == "data-story":
        return template_data_story(spec)
    if template_id in SUPPORTED_TEMPLATES:
        return template_p1_generic(spec)
    raise ArtboardError(f"unsupported template_id: {template_id}")


def use_node_satori_renderer() -> bool:
    raw = os.environ.get("SVGLIDE_ARTBOARD_USE_NODE_SATORI")
    if raw is None:
        return True
    return raw.lower() not in {"0", "false", "no"}


def resolve_node_renderer() -> Path:
    override = os.environ.get("SVGLIDE_ARTBOARD_RENDERER")
    if override:
        renderer = Path(override).expanduser().resolve()
        if renderer.exists():
            return renderer
        raise ArtboardError(f"SVGLIDE_ARTBOARD_RENDERER points to a missing file: {renderer}")
    if NODE_RENDERER_DIST.exists():
        return NODE_RENDERER_DIST
    if NODE_RENDERER_SOURCE.exists():
        return NODE_RENDERER_SOURCE
    raise ArtboardError(
        "missing node Satori renderer: expected bundled dist/render.mjs in published skills, "
        "or source render.mjs for local development"
    )


def renderer_receipt_path(renderer: Path) -> str:
    try:
        return "skills/lark-slides/scripts/" + renderer.relative_to(Path(__file__).resolve().parent).as_posix()
    except ValueError:
        return renderer.as_posix()


def render_node_satori_svg(spec_path: Path, output_path: Path, png_path: Path, metadata_path: Path, observations_path: Path) -> Path:
    renderer = resolve_node_renderer()
    command = [
        "node",
        renderer.as_posix(),
        spec_path.as_posix(),
        output_path.as_posix(),
        png_path.as_posix(),
        metadata_path.as_posix(),
        observations_path.as_posix(),
    ]
    result = subprocess.run(command, cwd=renderer.parent, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ArtboardError(f"node Satori renderer failed with exit {result.returncode}: {detail}")
    return renderer


def copy_shape(element: ElementTree.Element) -> str:
    name = local_name(element.tag)
    attrs = {key: value for key, value in element.attrib.items() if not key.startswith("data-")}
    attrs["slide:role"] = "shape"
    if name == "path" and "d" in attrs and "a" in str(attrs.get("d", "")) and {"x", "y", "width", "height"}.issubset(attrs):
        x = number(attrs.get("x"), 0)
        y = number(attrs.get("y"), 0)
        width = number(attrs.get("width"), 0)
        height = number(attrs.get("height"), 0)
        replacement_attrs = {key: value for key, value in attrs.items() if key not in {"x", "y", "width", "height", "d"}}
        if width > 0 and height > 0 and abs(width - height) < 0.01:
            replacement_attrs.update({"cx": f"{x + width / 2:g}", "cy": f"{y + height / 2:g}", "r": f"{width / 2:g}"})
            return f"<circle {svg_attrs(replacement_attrs)} />"
        if width > 0 and height > 0:
            replacement_attrs.update({"x": f"{x:g}", "y": f"{y:g}", "width": f"{width:g}", "height": f"{height:g}"})
            return f"<rect {svg_attrs(replacement_attrs)} />"
    return f"<{name} {svg_attrs(attrs)} />"


def text_style_from_element(element: ElementTree.Element) -> dict[str, str]:
    x = number(attr(element, "data-box-x") or attr(element, "x"), 0)
    y = number(attr(element, "data-box-y"), number(attr(element, "y"), 0) - number(attr(element, "font-size"), 18))
    width = number(attr(element, "data-box-width"), 360)
    height = number(attr(element, "data-box-height"), number(attr(element, "font-size"), 18) * 1.35)
    font_size = attr(element, "font-size") or "18"
    font_weight = attr(element, "font-weight") or "400"
    fill = attr(element, "fill") or "#111827"
    family = attr(element, "font-family") or "Inter"
    style = style_attr(
        {
            "font-size": f"{font_size}px" if str(font_size).replace(".", "", 1).isdigit() else font_size,
            "font-weight": font_weight,
            "font-family": family,
            "color": fill,
            "line-height": "1.16",
            "white-space": "normal",
        }
    )
    return {
        "x": f"{x:g}",
        "y": f"{y:g}",
        "width": f"{width:g}",
        "height": f"{height:g}",
        "style": style,
    }


def text_to_foreign_object(element: ElementTree.Element) -> str:
    text = "".join(element.itertext()).strip()
    text_style = text_style_from_element(element)
    attrs = {
        "slide:role": "shape",
        "slide:shape-type": "text",
        "x": text_style["x"],
        "y": text_style["y"],
        "width": text_style["width"],
        "height": text_style["height"],
    }
    node_id = attr(element, "data-node-id")
    if node_id:
        attrs["data-node-id"] = node_id
        source_ref = semantic_source_ref_for_node({"id": node_id})
        if source_ref:
            attrs["data-source-ref"] = source_ref
    return (
        f"<foreignObject {svg_attrs(attrs)}>"
        f'<div xmlns="{XHTML_NS}" style="{escape(text_style["style"])}">{escape(text)}</div>'
        "</foreignObject>"
    )


def text_run_key(element: ElementTree.Element) -> tuple[str, str, str, str]:
    return (
        attr(element, "y") or "",
        attr(element, "font-size") or "18",
        attr(element, "font-weight") or "400",
        attr(element, "fill") or "#111827",
    )


def can_group_satori_text(element: ElementTree.Element) -> bool:
    return not any(attr(element, key) is not None for key in ["data-box-x", "data-box-y", "data-box-width", "data-box-height"])


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def text_run_to_foreign_object(elements: list[ElementTree.Element]) -> str:
    first = elements[0]
    font_size = number(attr(first, "font-size"), 18)
    x_values = [number(attr(item, "x"), 0) for item in elements]
    x = min(x_values) if x_values else 0
    y = number(attr(first, "y"), 0) - font_size
    text_parts: list[str] = []
    max_x = x
    previous_right: float | None = None
    for item in elements:
        item_x = number(attr(item, "x"), x)
        text = "".join(item.itertext())
        measured_width = number(attr(item, "width"), 0)
        estimated_width = max(measured_width, font_size * 0.45, len(text) * font_size * 0.62)
        if previous_right is not None and item_x - previous_right > font_size * 0.35:
            text_parts.append(" ")
        text_parts.append(text)
        previous_right = item_x + estimated_width
        max_x = max(max_x, previous_right)
    text = "".join(text_parts).strip()
    conservative_width = len(text) * font_size if has_cjk(text) else 0
    box_width = min(960 - x, max(max_x - x, conservative_width, font_size * 2))
    box_height = max(number(attr(first, "height"), font_size * 1.35), font_size * 1.35, 45)
    synthetic = ElementTree.Element(first.tag, dict(first.attrib))
    synthetic.text = text
    synthetic.set("data-box-x", f"{x:g}")
    synthetic.set("data-box-y", f"{y:g}")
    synthetic.set("data-box-width", f"{box_width:g}")
    synthetic.set("data-box-height", f"{box_height:g}")
    return text_to_foreign_object(synthetic)


def scan_unsupported(root: ElementTree.Element) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for element in root.iter():
        name = local_name(element.tag)
        if name in FAIL_FAST_ELEMENTS:
            issues.append({"code": "satori_svg_element_fail_fast", "message": f"unsupported Satori SVG element in P0a: {name}"})
        elif name not in SUPPORTED_SATORI_ELEMENTS:
            issues.append({"code": "satori_svg_element_unsupported", "message": f"unsupported Satori SVG element in P0a: {name}"})
        if "filter" in element.attrib or "clip-path" in element.attrib or "mask" in element.attrib:
            issues.append({"code": "satori_svg_effect_fail_fast", "message": f"unsupported effect attribute on {name}"})
    return issues


def compile_svg_markup_to_svglide(
    source_svg: str,
    *,
    semantic_source: str,
    compiler_input: str,
    satori_svg_usage: str,
) -> tuple[str, dict[str, Any]]:
    try:
        root = ElementTree.fromstring(source_svg)
    except ElementTree.ParseError as err:
        raise ArtboardError(f"invalid compiler SVG input: {err}") from err
    issues = scan_unsupported(root)
    if issues:
        raise ArtboardError(json.dumps({"issues": issues}, ensure_ascii=False))
    native_mapped: list[str] = []

    def compile_sequence(elements: list[ElementTree.Element]) -> list[str]:
        output: list[str] = []
        index = 0
        while index < len(elements):
            element = elements[index]
            name = local_name(element.tag)
            if name == "text" and can_group_satori_text(element):
                run = [element]
                index += 1
                while index < len(elements):
                    next_element = elements[index]
                    if local_name(next_element.tag) != "text" or not can_group_satori_text(next_element) or text_run_key(next_element) != text_run_key(element):
                        break
                    run.append(next_element)
                    index += 1
                output.append(text_run_to_foreign_object(run))
                native_mapped.append("text-run->foreignObject")
                continue
            output.extend(compile_element(element))
            index += 1
        return output

    def compile_element(element: ElementTree.Element) -> list[str]:
        name = local_name(element.tag)
        if name == "mask":
            return []
        if name == "g":
            group_children = compile_sequence(list(element))
            if not group_children:
                return []
            attrs = {key: value for key, value in element.attrib.items() if not key.startswith("data-")}
            attr_text = svg_attrs(attrs)
            if attr_text:
                return [f"<g {attr_text}>\n" + "\n".join(f"    {child}" for child in group_children) + "\n  </g>"]
            return group_children
        if name == "text":
            native_mapped.append("text->foreignObject")
            return [text_to_foreign_object(element)]
        if name in {"rect", "circle", "ellipse", "line", "path"}:
            native_mapped.append(name)
            return [copy_shape(element)]
        return []

    children = compile_sequence(list(root))
    if not children:
        raise ArtboardError("compiler produced no SVGlide nodes")
    svg = (
        f'<svg xmlns="{SVG_NS}" xmlns:slide="{SLIDE_NS}" slide:role="slide" '
        f'slide:contract-version="{CONTRACT_VERSION}" width="960" height="540" viewBox="0 0 960 540">\n'
        + "\n".join(f"  {child}" for child in children)
        + "\n</svg>\n"
    )
    return svg, {
        "semantic_source": semantic_source,
        "compiler_input": compiler_input,
        "satori_svg_usage": satori_svg_usage,
        "native_mapped": native_mapped,
        "fail_fast": sorted(FAIL_FAST_ELEMENTS),
    }


def compile_satori_svg_to_svglide(satori_svg: str) -> tuple[str, dict[str, Any]]:
    return compile_svg_markup_to_svglide(
        satori_svg,
        semantic_source="SatoriSVG",
        compiler_input="RawSatoriSVG",
        satori_svg_usage="compiler_input",
    )


def compile_canvas_template_svg_to_svglide(canvas_template_svg: str) -> tuple[str, dict[str, Any]]:
    return compile_svg_markup_to_svglide(
        canvas_template_svg,
        semantic_source="CanvasSpec",
        compiler_input="CanvasSpecTemplateSVG",
        satori_svg_usage="preview_only",
    )


def compile_semantic_map_to_svglide(semantic_map: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    elements = semantic_map.get("elements")
    if not isinstance(elements, list) or not elements:
        raise ArtboardError("semantic-map/v1 has no elements to compile")
    theme = semantic_map.get("theme") if isinstance(semantic_map.get("theme"), dict) else {}
    native_mapped: list[str] = []
    children: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        child = compile_semantic_element(element, theme)
        if child:
            children.append(child)
            native_mapped.append(str(element.get("kind") or "unknown"))
    if not children:
        raise ArtboardError("semantic-map compiler produced no SVGlide nodes")
    svg = (
        f'<svg xmlns="{SVG_NS}" xmlns:slide="{SLIDE_NS}" slide:role="slide" '
        f'slide:contract-version="{CONTRACT_VERSION}" width="960" height="540" viewBox="0 0 960 540">\n'
        + "\n".join(f"  {child}" for child in children)
        + "\n</svg>\n"
    )
    return svg, {
        "semantic_source": str(semantic_map.get("semantic_source") or "semantic-map/v1"),
        "compiler_input": "SemanticMapIR",
        "satori_svg_usage": "preview_only",
        "native_mapped": native_mapped,
        "fail_fast": sorted(FAIL_FAST_ELEMENTS),
    }


def semantic_shape_fill(element_id: str, kind: str, style: dict[str, Any], theme: dict[str, Any]) -> str:
    if style.get("fill"):
        return str(style["fill"])
    if element_id == "background":
        return str(theme.get("background") or "#0F172A")
    if any(token in element_id for token in ["panel", "card", "bg", "terminal"]):
        return str(theme.get("panel") or "#111827")
    if any(token in element_id for token in ["accent", "bar", "node", "dot", "rule", "signal", "port"]):
        return str(theme.get("primary") or "#60A5FA")
    if kind == "path":
        return "none"
    return str(theme.get("panel") or "#111827")


def compile_semantic_element(element: dict[str, Any], theme: dict[str, Any]) -> str | None:
    element_id = str(element.get("element_id") or "")
    kind = str(element.get("kind") or "")
    bbox = element.get("bbox") if isinstance(element.get("bbox"), dict) else {}
    style = element.get("style") if isinstance(element.get("style"), dict) else {}
    x = number(bbox.get("x"), 0)
    y = number(bbox.get("y"), 0)
    width = max(number(bbox.get("width"), 0), 1)
    height = max(number(bbox.get("height"), 0), 1)
    common = {"data-node-id": element_id}
    source_ref = element.get("source_ref")
    if isinstance(source_ref, str) and source_ref:
        common["data-source-ref"] = source_ref
    if kind == "text":
        font_size = number(style.get("font_size"), 18)
        font_weight = int(number(style.get("font_weight"), 700))
        fill = str(style.get("fill") or "#111827")
        text = str(element.get("text") or "")
        attrs = {
            **common,
            "slide:role": "shape",
            "slide:shape-type": "text",
            "x": f"{x:g}",
            "y": f"{y:g}",
            "width": f"{width:g}",
            "height": f"{height:g}",
        }
        css = f"color:{fill};font-size:{font_size:g}px;font-weight:{font_weight};font-family:Inter,Arial,sans-serif;line-height:1.18;"
        return f'<foreignObject {svg_attrs(attrs)}><div xmlns="{XHTML_NS}" style="{escape(css)}">{escape(text)}</div></foreignObject>'
    if kind == "rect":
        attrs = {
            **common,
            "slide:role": "shape",
            "x": f"{x:g}",
            "y": f"{y:g}",
            "width": f"{width:g}",
            "height": f"{height:g}",
            "fill": semantic_shape_fill(element_id, kind, style, theme),
        }
        add_optional_svg_style(attrs, style)
        return f"<rect {svg_attrs(attrs)}/>"
    if kind == "circle":
        attrs = {
            **common,
            "slide:role": "shape",
            "cx": f"{x + width / 2:g}",
            "cy": f"{y + height / 2:g}",
            "r": f"{max(min(width, height) / 2, 1):g}",
            "fill": semantic_shape_fill(element_id, kind, style, theme),
        }
        add_optional_svg_style(attrs, style)
        return f"<circle {svg_attrs(attrs)}/>"
    if kind == "line":
        attrs = {
            **common,
            "slide:role": "shape",
            "x1": f"{number(style.get('x1'), x):g}",
            "y1": f"{number(style.get('y1'), y):g}",
            "x2": f"{number(style.get('x2'), x + width):g}",
            "y2": f"{number(style.get('y2'), y + height):g}",
            "stroke": str(style.get("stroke") or style.get("fill") or theme.get("primary") or "#111827"),
            "stroke-width": f"{number(style.get('stroke_width'), 2):g}",
        }
        add_optional_svg_style(attrs, style)
        return f"<line {svg_attrs(attrs)}/>"
    if kind == "path":
        d = style.get("d")
        if not isinstance(d, str) or not d.strip():
            return None
        attrs = {**common, "slide:role": "shape", "d": d, "fill": semantic_shape_fill(element_id, kind, style, theme)}
        if not style.get("stroke"):
            attrs["stroke"] = str(theme.get("accent") or theme.get("primary") or "#111827")
        add_optional_svg_style(attrs, style)
        return f"<path {svg_attrs(attrs)}/>"
    return None


def add_optional_svg_style(attrs: dict[str, str], style: dict[str, Any]) -> None:
    if style.get("opacity") is not None:
        attrs["opacity"] = f"{number(style.get('opacity'), 1):g}"
    if style.get("stroke"):
        attrs["stroke"] = str(style["stroke"])
    if style.get("stroke_width") is not None:
        attrs["stroke-width"] = f"{number(style.get('stroke_width'), 1):g}"


def normalize_xhtml_foreign_object(svg: str) -> str:
    svg = svg.replace(f' xmlns:html="{XHTML_NS}"', "")
    svg = svg.replace("<html:div ", f'<div xmlns="{XHTML_NS}" ')
    svg = svg.replace("<html:div>", f'<div xmlns="{XHTML_NS}">')
    svg = svg.replace("</html:div>", "</div>")
    return svg


def align_text_boxes_to_node_layout(svglide_svg: str, nodes: list[dict[str, Any]]) -> str:
    text_nodes = [node for node in nodes if node.get("kind") == "text"]
    if not text_nodes:
        return svglide_svg
    ElementTree.register_namespace("", SVG_NS)
    ElementTree.register_namespace("slide", SLIDE_NS)
    try:
        root = ElementTree.fromstring(svglide_svg)
    except ElementTree.ParseError as err:
        raise ArtboardError(f"invalid compiled SVGlide SVG: {err}") from err
    foreign_objects = [element for element in root.iter(f"{{{SVG_NS}}}foreignObject")]
    if not foreign_objects:
        return ElementTree.tostring(root, encoding="unicode") + "\n"
    grouped: list[list[ElementTree.Element]] = [[] for _ in text_nodes]
    for element in foreign_objects:
        best_index = match_text_node_index(element, text_nodes)
        grouped[best_index].append(element)
    parents = {child: parent for parent in root.iter() for child in list(parent)}
    for node, elements in zip(text_nodes, grouped):
        if not elements:
            continue
        element = elements[0]
        for key in ["x", "y", "width", "height"]:
            value = node.get(key)
            if isinstance(value, (int, float)):
                element.set(key, f"{value:g}")
        element.set("data-node-id", str(node.get("id") or ""))
        source_ref = semantic_source_ref_for_node(node)
        if source_ref:
            element.set("data-source-ref", source_ref)
        text = str(node.get("text") or "") or join_text_fragments(["".join(item.itertext()).strip() for item in elements])
        div = next(iter(element), None)
        if div is not None:
            div.text = text
        for extra in elements[1:]:
            parent = parents.get(extra)
            if parent is not None:
                parent.remove(extra)
    return normalize_xhtml_foreign_object(ElementTree.tostring(root, encoding="unicode") + "\n")


def normalize_match_text(value: str) -> str:
    return "".join(value.split()).lower()


def match_text_node_index(element: ElementTree.Element, text_nodes: list[dict[str, Any]]) -> int:
    fragment = normalize_match_text("".join(element.itertext()).strip())
    if fragment:
        for index, node in enumerate(text_nodes):
            target = normalize_match_text(str(node.get("text") or ""))
            if target and fragment == target:
                return index
        for index, node in enumerate(text_nodes):
            target = normalize_match_text(str(node.get("text") or ""))
            if target and target in fragment:
                return index
    x = number(element.get("x"), 0)
    y = number(element.get("y"), 0)
    width = number(element.get("width"), 0)
    height = number(element.get("height"), 0)
    center_x = x + width / 2
    center_y = y + height / 2
    return min(
        range(len(text_nodes)),
        key=lambda idx: (
            center_y - (number(text_nodes[idx].get("y"), 0) + number(text_nodes[idx].get("height"), 0) / 2)
        )
        ** 2
        + (
            (center_x - (number(text_nodes[idx].get("x"), 0) + number(text_nodes[idx].get("width"), 0) / 2)) / 4
        )
        ** 2,
    )


def join_text_fragments(fragments: list[str]) -> str:
    result = ""
    for fragment in [item for item in fragments if item]:
        if result and not result.endswith((" ", "/", "-", "(", "（")) and not fragment.startswith((" ", "/", "-", ")", "）", ".", ",", "。", "，")):
            boundary = result[-1] + fragment[0]
            if not has_cjk(boundary):
                result += " "
        result += fragment
    return result


def validate_satori_preview_svg(satori_svg: str, *, strict: bool = True) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(satori_svg)
    except ElementTree.ParseError as err:
        raise ArtboardError(f"invalid Satori SVG: {err}") from err
    issues = scan_unsupported(root)
    if strict and issues:
        raise ArtboardError(json.dumps({"issues": issues}, ensure_ascii=False))
    element_counts: dict[str, int] = {}
    for element in root.iter():
        name = local_name(element.tag)
        element_counts[name] = element_counts.get(name, 0) + 1
    return {
        "status": "passed" if not issues else "warning",
        "element_counts": element_counts,
        "fail_fast": sorted(FAIL_FAST_ELEMENTS),
        "issues": issues,
        "strict": strict,
    }


def write_contact_sheet(project: Path, png_paths: list[Path]) -> dict[str, Any]:
    if not png_paths:
        raise ArtboardError("cannot create contact sheet without page PNG files")
    try:
        from PIL import Image, ImageDraw
    except Exception as err:  # pragma: no cover - environment dependent
        raise ArtboardError("Pillow is required to compose contact-sheet.png from resvg page PNGs") from err
    thumbs = []
    for index, png in enumerate(png_paths, 1):
        image = Image.open(png).convert("RGB")
        image.thumbnail((320, 180), Image.LANCZOS)
        tile = Image.new("RGB", (320, 180), (10, 14, 18))
        tile.paste(image, ((320 - image.width) // 2, (180 - image.height) // 2))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((8, 8, 46, 30), fill=(15, 23, 42))
        draw.text((16, 13), f"{index:02d}", fill=(248, 250, 252))
        thumbs.append(tile)
    cols = min(3, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    gap = 16
    sheet = Image.new("RGB", (cols * 320 + (cols + 1) * gap, rows * 180 + (rows + 1) * gap), (6, 10, 16))
    for index, tile in enumerate(thumbs):
        x = gap + (index % cols) * (320 + gap)
        y = gap + (index // cols) * (180 + gap)
        sheet.paste(tile, (x, y))
    output = project / CONTACT_SHEET
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return {"path": CONTACT_SHEET.as_posix(), "sha256": file_sha256(output), "source_pngs": [relpath(path, project) for path in png_paths]}


def write_canvas_spec_validate(project: Path, pages: list[dict[str, Any]], issues: list[dict[str, Any]], registry_summary: dict[str, Any]) -> dict[str, Any]:
    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-canvas-spec-validate/v1",
        "stage": "canvas-spec-validate",
        "status": status,
        "action": "create_live" if status == "passed" else "repair_and_rerun",
        "inputs": {
            "slide_plan": "02-plan/slide_plan.json",
            "plan_sha256": file_sha256(project / "02-plan/slide_plan.json"),
            **registry_summary,
        },
        "pages": pages,
        "summary": {"error_count": len(issues), "warning_count": 0, "page_count": len(pages)},
        "issues": issues,
        "output_path": CANVAS_SPEC_VALIDATE_CHECK.as_posix(),
    }
    write_json(project / CANVAS_SPEC_VALIDATE_CHECK, result)
    write_json(project / CANVAS_SPEC_VALIDATE_RECEIPT, result)
    return result


def render_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan = read_json(project / "02-plan/slide_plan.json")
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ArtboardError("slide_plan.slides must contain at least one slide")
    artboard_dir = project / "04-svg/artboard"
    raw_dir = artboard_dir / "raw"
    artboard_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    validation_issues: list[dict[str, Any]] = []
    validation_pages: list[dict[str, Any]] = []
    prepared_specs: list[dict[str, Any]] = []
    registry_summaries: list[dict[str, Any]] = []
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            validation_issues.append({"code": "slide_invalid", "message": f"slide {index} must be an object", "page": index})
            continue
        spec = slide.get("canvas_spec")
        if not isinstance(spec, dict):
            validation_issues.append({"code": "canvas_spec_missing", "message": f"slide {index} is missing canvas_spec for generation_mode=artboard_satori", "page": index})
            continue
        page_issues = validate_canvas_spec(spec, page=index)
        registry_issues, registry_summary = validate_registry_bindings(project, spec, page=index)
        page_issues.extend(registry_issues)
        validation_issues.extend({**item, "page": index} for item in page_issues)
        effective_spec = apply_registry_theme(spec, registry_summary)
        prepared_specs.append({"page": index, "slide": slide, "spec": effective_spec, "registry": registry_summary})
        registry_summaries.append(registry_summary)
        validation_pages.append(
            {
                "page": index,
                "template_id": spec.get("template_id"),
                "theme_id": spec.get("theme_id"),
                "canvas_spec_sha256": json_sha256(spec),
                "template_registry_sha256": registry_summary.get("template_registry_sha256"),
                "theme_registry_sha256": registry_summary.get("theme_registry_sha256"),
                "error_count": len(page_issues),
            }
        )
    registry_summary_for_receipt = {
        "template_registry": registry_summaries[0].get("template_registry_path") if registry_summaries else None,
        "template_registry_sha256": registry_summaries[0].get("template_registry_sha256") if registry_summaries else None,
        "theme_registry": registry_summaries[0].get("theme_registry_path") if registry_summaries else None,
        "theme_registry_sha256": registry_summaries[0].get("theme_registry_sha256") if registry_summaries else None,
        "theme_files": registry_summaries[0].get("theme_files") if registry_summaries else [],
    }
    canvas_validate = write_canvas_spec_validate(project, validation_pages, validation_issues, registry_summary_for_receipt)
    if validation_issues:
        raise ArtboardError(json.dumps({"issues": validation_issues, "receipt": CANVAS_SPEC_VALIDATE_RECEIPT.as_posix()}, ensure_ascii=False))
    max_workers = min(4, len(prepared_specs))

    def render_page_job(prepared: dict[str, Any]) -> dict[str, Any]:
        index = prepared["page"]
        spec = prepared["spec"]
        registry_summary = prepared["registry"]
        page_name = f"page-{index:03d}"
        satori_path = raw_dir / f"{page_name}.satori.svg"
        png_path = artboard_dir / f"{page_name}.png"
        metadata_path = artboard_dir / f"{page_name}.render-metadata.json"
        node_observations_path = artboard_dir / f"{page_name}.node-observations.json"
        canvas_spec_artifact_path = artboard_dir / f"{page_name}.canvas-spec.json"
        canvas_template_path = artboard_dir / f"{page_name}.canvas-template.svg"
        semantic_map_path = artboard_dir / f"{page_name}.semantic-map.json"
        node_layout_path = artboard_dir / f"{page_name}.node-layout-map.json"
        svglide_path = project / "04-svg" / f"{page_name}.svg"
        canvas_template_svg, nodes = render_satori_compatible_svg(spec)
        canvas_template_path.write_text(canvas_template_svg, encoding="utf-8")
        write_json(canvas_spec_artifact_path, spec)
        actual_satori_package = use_node_satori_renderer()
        node_adapter_path: Path | None = None
        renderer_metadata: dict[str, Any] = {}
        if actual_satori_package:
            node_adapter_path = render_node_satori_svg(canvas_spec_artifact_path, satori_path, png_path, metadata_path, node_observations_path)
            satori_svg = satori_path.read_text(encoding="utf-8")
            renderer_metadata = read_json(metadata_path)
            satori_preview = validate_satori_preview_svg(satori_svg, strict=False)
        else:
            satori_svg = canvas_template_svg
            satori_preview = validate_satori_preview_svg(satori_svg, strict=True)
            metadata_path.write_text(json.dumps({"node_version": None, "satori_version": None, "resvg_version": None, "font_path": None}, indent=2) + "\n", encoding="utf-8")
            write_json(node_observations_path, {"version": "svglide-node-observations/v1", "observation_source": "rendered_satori_svg_parse", "nodes": []})
        semantic_map = {
            "version": SEMANTIC_MAP_VERSION,
            "page": index,
            "template_id": spec.get("template_id"),
            "theme_id": spec.get("theme_id"),
            "theme": normalize_theme(spec),
            "semantic_source": "CanvasSpec",
            "content_keys": sorted((spec.get("content") or {}).keys()) if isinstance(spec.get("content"), dict) else [],
            "elements": semantic_elements_from_nodes(nodes),
        }
        write_json(semantic_map_path, semantic_map)
        svglide_svg, compiler = compile_semantic_map_to_svglide(semantic_map)
        satori_path.write_text(satori_svg, encoding="utf-8")
        svglide_path.write_text(svglide_svg, encoding="utf-8")
        if not png_path.exists():
            raise ArtboardError(f"missing resvg PNG output for page {index}: {png_path}")
        font_path = renderer_metadata.get("font_path")
        font_hashes = []
        if isinstance(font_path, str) and Path(font_path).exists():
            font_hashes.append({"path": font_path, "sha256": file_sha256(Path(font_path))})
        renderer_observations = []
        if node_observations_path.exists():
            observations_payload = read_json(node_observations_path)
            raw_observations = observations_payload.get("nodes")
            renderer_observations = raw_observations if isinstance(raw_observations, list) else []
        node_layout_map = svglide_node_layout_drift.build_node_layout_map(
            page=index,
            expected_nodes=nodes,
            renderer_observations=renderer_observations,
            satori_svg_path=satori_path,
        )
        write_json(node_layout_path, node_layout_map)
        input_semantic_hash = file_sha256(semantic_map_path)
        compiler["input_semantic_hash"] = input_semantic_hash
        receipt_path = artboard_dir / f"{page_name}.receipt.json"
        receipt = {
            "version": ARTBOARD_RECEIPT_VERSION,
            "stage": "generate_svg",
            "status": "passed",
            "page": index,
            "canvas_spec_path": f"02-plan/slide_plan.json#/slides/{index - 1}/canvas_spec",
            "canvas_spec_sha256": json_sha256(spec),
            "template_id": spec.get("template_id"),
            "theme_id": spec.get("theme_id"),
            "template_registry": registry_summary.get("template_registry_path"),
            "template_registry_sha256": registry_summary.get("template_registry_sha256"),
            "theme_registry": registry_summary.get("theme_registry_path"),
            "theme_registry_sha256": registry_summary.get("theme_registry_sha256"),
            "theme_files": registry_summary.get("theme_files"),
            "node_version": renderer_metadata.get("node_version"),
            "satori_version": renderer_metadata.get("satori_version"),
            "resvg_version": renderer_metadata.get("resvg_version"),
            "font_hashes": font_hashes,
            "renderer": {
                "name": "satori-resvg-p0",
                "engine": "satori-node" if actual_satori_package else "local-static",
                "actual_satori_package": actual_satori_package,
                "adapter": renderer_receipt_path(node_adapter_path) if node_adapter_path else "skills/lark-slides/scripts/svglide_artboard_renderer.py",
            },
            "satori_svg": relpath(satori_path, project),
            "satori_svg_sha256": file_sha256(satori_path),
            "png": relpath(png_path, project),
            "png_sha256": file_sha256(png_path),
            "render_metadata": relpath(metadata_path, project),
            "render_metadata_sha256": file_sha256(metadata_path),
            "canvas_template_svg": relpath(canvas_template_path, project),
            "canvas_template_svg_sha256": file_sha256(canvas_template_path),
            "compiler_input": relpath(semantic_map_path, project),
            "compiler_input_sha256": file_sha256(semantic_map_path),
            "input_semantic_hash": input_semantic_hash,
            "semantic_map": relpath(semantic_map_path, project),
            "semantic_map_sha256": file_sha256(semantic_map_path),
            "node_layout_map": relpath(node_layout_path, project),
            "node_layout_map_sha256": file_sha256(node_layout_path),
            "svglide_svg": relpath(svglide_path, project),
            "svglide_svg_sha256": file_sha256(svglide_path),
            "compiler": compiler,
            "satori_preview": satori_preview,
            "created_at": now_iso(),
        }
        write_json(receipt_path, receipt)
        receipt["path"] = relpath(receipt_path, project)
        return {
            "page": index,
            "receipt": receipt,
            "png_path": png_path,
            "render_page": {
                "page": index,
                "template_id": spec.get("template_id"),
                "theme_id": spec.get("theme_id"),
                "canvas_spec_sha256": json_sha256(spec),
                "satori_svg": relpath(satori_path, project),
                "satori_svg_sha256": file_sha256(satori_path),
                "png": relpath(png_path, project),
                "png_sha256": file_sha256(png_path),
                "render_metadata": relpath(metadata_path, project),
                "render_metadata_sha256": file_sha256(metadata_path),
                "canvas_template_svg": relpath(canvas_template_path, project),
                "canvas_template_svg_sha256": file_sha256(canvas_template_path),
                "node_observations": relpath(node_observations_path, project),
                "node_observations_sha256": file_sha256(node_observations_path),
                "node_layout_map": relpath(node_layout_path, project),
                "node_layout_map_sha256": file_sha256(node_layout_path),
                "node_version": renderer_metadata.get("node_version"),
                "satori_version": renderer_metadata.get("satori_version"),
                "resvg_version": renderer_metadata.get("resvg_version"),
                "font_hashes": font_hashes,
            },
            "bridge_page": {
                "page": index,
                "semantic_source": "CanvasSpec",
                "canvas_spec_sha256": json_sha256(spec),
                "semantic_map": relpath(semantic_map_path, project),
                "semantic_map_sha256": file_sha256(semantic_map_path),
                "input_semantic_hash": input_semantic_hash,
                "node_layout_map": relpath(node_layout_path, project),
                "node_layout_map_sha256": file_sha256(node_layout_path),
                "canvas_template_svg": relpath(canvas_template_path, project),
                "canvas_template_svg_sha256": file_sha256(canvas_template_path),
                "compiler_input": relpath(semantic_map_path, project),
                "compiler_input_sha256": file_sha256(semantic_map_path),
                "compiler_input_type": compiler.get("compiler_input"),
                "satori_svg_usage": compiler.get("satori_svg_usage"),
                "satori_svg": relpath(satori_path, project),
                "satori_svg_sha256": file_sha256(satori_path),
                "svglide_svg": relpath(svglide_path, project),
                "svglide_svg_sha256": file_sha256(svglide_path),
            },
        }

    if max_workers > 1:
        page_results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(render_page_job, prepared): prepared["page"] for prepared in prepared_specs}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    page_results.append(future.result())
                except Exception as err:
                    raise ArtboardError(f"artboard page job failed for page {page}: {err}") from err
    else:
        page_results = [render_page_job(prepared) for prepared in prepared_specs]
    page_results.sort(key=lambda item: int(item["page"]))
    receipts = [item["receipt"] for item in page_results]
    render_pages = [item["render_page"] for item in page_results]
    bridge_pages = [item["bridge_page"] for item in page_results]
    png_paths = [item["png_path"] for item in page_results]
    contact_sheet = write_contact_sheet(project, png_paths)
    artboard_render_receipt = {
        "version": "svglide-artboard-render/v1",
        "stage": "artboard-render",
        "status": "passed",
        "inputs": {
            "slide_plan": "02-plan/slide_plan.json",
            "plan_sha256": file_sha256(project / "02-plan/slide_plan.json"),
            **registry_summary_for_receipt,
            "canvas_spec_validate": CANVAS_SPEC_VALIDATE_RECEIPT.as_posix(),
            "canvas_spec_validate_sha256": file_sha256(project / CANVAS_SPEC_VALIDATE_RECEIPT),
        },
        "pages": render_pages,
        "contact_sheet": contact_sheet,
        "summary": {"error_count": 0, "warning_count": 0, "page_count": len(render_pages), "max_workers": max_workers},
        "created_at": now_iso(),
    }
    write_json(project / ARTBOARD_RENDER_RECEIPT, artboard_render_receipt)
    satori_bridge_receipt = {
        "version": "svglide-satori-bridge/v1",
        "stage": "satori-bridge",
        "status": "passed",
        "inputs": {
            "slide_plan": "02-plan/slide_plan.json",
            "plan_sha256": file_sha256(project / "02-plan/slide_plan.json"),
            "artboard_render": ARTBOARD_RENDER_RECEIPT.as_posix(),
            "artboard_render_sha256": file_sha256(project / ARTBOARD_RENDER_RECEIPT),
        },
        "pages": bridge_pages,
        "summary": {"error_count": 0, "warning_count": 0, "page_count": len(bridge_pages), "max_workers": max_workers},
        "created_at": now_iso(),
    }
    write_json(project / SATORI_BRIDGE_RECEIPT, satori_bridge_receipt)
    return {
        "version": "svglide-artboard-render/v1",
        "status": "passed",
        "project": str(project),
        "page_count": len(receipts),
        "max_workers": max_workers,
        "artboard_receipts": [receipt["path"] for receipt in receipts],
        "additional_receipts": [
            CANVAS_SPEC_VALIDATE_RECEIPT.as_posix(),
            ARTBOARD_RENDER_RECEIPT.as_posix(),
            SATORI_BRIDGE_RECEIPT.as_posix(),
        ],
        "canvas_spec_validate": CANVAS_SPEC_VALIDATE_CHECK.as_posix(),
        "artboard_render_receipt": ARTBOARD_RENDER_RECEIPT.as_posix(),
        "satori_bridge_receipt": SATORI_BRIDGE_RECEIPT.as_posix(),
        "contact_sheet": contact_sheet,
        "generated_files": [{"path": receipt["svglide_svg"], "sha256": receipt["svglide_svg_sha256"]} for receipt in receipts],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render CanvasSpec artboards into SVGlide protocol SVG.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = render_project(args.project)
    except ArtboardError as error:
        print(f"svglide_artboard_renderer: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
