#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr

import svglide_node_layout_drift
import beautiful_template_runtime


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
    "dense-panel-grid",
    "executive-dashboard",
    "editorial-quote-chart",
    "ledger-briefing",
    "intelligence-brief",
    "printed-program",
    "retro-ui-dashboard",
    "product-ribbon",
    "type-mass-poster",
    "brutalist-matrix",
    "annotated-field-board",
    "architectural-spec",
    "trend-grid-report",
    "serif-stat-editorial",
    "poster-stat-punch",
}
PYTHON_TEMPLATE_IDS = {
    "cover-hero",
    "cover_hero",
    "comparison-cards",
    "summary-final",
    "section-title",
    "section_title",
    "comparison",
    "agenda-list",
    "timeline-steps",
    "process-flow",
    "metric-dashboard",
    "risk-alert",
    "roadmap-lanes",
    "architecture-blueprint",
    "image-feature",
    "data-story",
}
SATORI_INTERNAL_ELEMENTS = {"defs", "clipPath", "mask"}
SUPPORTED_SATORI_ELEMENTS = {"svg", "g", "defs", "clipPath", "mask", "rect", "circle", "ellipse", "line", "path", "text"}
FAIL_FAST_ELEMENTS = {"filter", "pattern", "foreignObject", "image", "use", "linearGradient", "radialGradient"}
STRIPPED_SATORI_ATTRS = {"clip-path", "mask"}
PATH_TOKEN_RE = re.compile(r"[AaCcHhLlMmQqVvZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
ARTBOARD_RENDERER_DIR = Path(__file__).resolve().parent / "artboard_renderer"
SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
NODE_RENDERER_DIST = ARTBOARD_RENDERER_DIR / "dist" / "render.mjs"
NODE_RENDERER_SOURCE = ARTBOARD_RENDERER_DIR / "render.mjs"
GLOBAL_TEMPLATE_REGISTRY = beautiful_template_runtime.FAMILIES_PATH
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
    project_path = optional_project_path(project, PROJECT_TEMPLATE_REGISTRY)
    if project_path:
        path = project_path
        payload = read_json(path)
    else:
        path = beautiful_template_runtime.FAMILIES_PATH
        payload = beautiful_template_runtime.template_registry()
    return path, payload, registry_record_by_id(payload, "templates")


def load_theme_registry(project: Path) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
    project_path = optional_project_path(project, PROJECT_THEME_REGISTRY)
    if project_path:
        path = project_path
        payload = read_json(path)
    else:
        path = beautiful_template_runtime.FAMILIES_PATH
        payload = beautiful_template_runtime.theme_registry()
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
    if isinstance(theme_record.get("colors"), dict):
        theme_id = str(theme_record.get("id") or theme_record.get("theme_id") or "")
        if theme_id in beautiful_template_runtime.LEGACY_THEME_COLORS:
            return None, beautiful_template_runtime.theme_payload(theme_id)
        return None, theme_record
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
    elif not beautiful_template_runtime.is_runtime_selectable(template_record, include_legacy_debug=template_payload.get("include_legacy_debug") is True):
        issues.append({"code": "canvas_spec_template_inactive", "message": f"page {page} template_id {template_id!r} is not active"})
    if theme_record is None:
        issues.append({"code": "canvas_spec_theme_unknown", "message": f"page {page} theme_id {theme_id!r} is not present in Theme Registry"})
    elif not beautiful_template_runtime.is_runtime_selectable(theme_record, include_legacy_debug=theme_payload.get("include_legacy_debug") is True):
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


def compact_semantic_text(value: str, *, max_chars: int = 54) -> str:
    text = " ".join(value.split())
    return text if len(text) <= max_chars else text[: max_chars - 3].rstrip() + "..."


def content_compiler_items(spec: dict[str, Any]) -> list[tuple[str, str]]:
    content = spec.get("content") if isinstance(spec.get("content"), dict) else {}
    items: list[tuple[str, str]] = []
    skip = {"eyebrow", "title", "subtitle"}
    for key, value in content.items():
        if key in skip:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    items.append((key, compact_semantic_text(item)))
        elif isinstance(value, str) and value.strip():
            label = key.replace("_", " ").strip()
            items.append((key, compact_semantic_text(f"{label}: {value.strip()}")))
    return items


def add_compiler_text_node(
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
    font_weight: int,
    role: str,
    source_ref: str | None = None,
) -> None:
    if not value:
        return
    nodes.append(
        {
            "id": node_id,
            "kind": "text",
            "role": role,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "text": value,
            "fill": fill,
            "font_size": font_size,
            "font_weight": font_weight,
            "source_ref": source_ref,
        }
    )


def compiler_nodes_from_canvas_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    theme = normalize_theme(spec)
    template_id = str(spec.get("template_id") or "unknown-template")
    theme_id = str(spec.get("theme_id") or "unknown-theme")
    nodes: list[dict[str, Any]] = [
        {
            "id": "background",
            "kind": "rect",
            "role": "background",
            "x": 0,
            "y": 0,
            "width": 960,
            "height": 540,
            "fill": theme["background"],
            "origin": {"type": "theme", "id": theme_id, "reason": "canvas background"},
        },
        {
            "id": "content-panel",
            "kind": "rect",
            "role": "container",
            "x": 48,
            "y": 40,
            "width": 864,
            "height": 460,
            "fill": theme["panel"],
            "origin": {"type": "template", "id": template_id, "reason": "contract compile semantic panel"},
        },
    ]
    add_compiler_text_node(
        nodes,
        "eyebrow",
        content_text(spec, "eyebrow", "").upper(),
        x=64,
        y=58,
        width=360,
        height=28,
        fill=theme["primary"],
        font_size=15,
        font_weight=800,
        role="eyebrow",
        source_ref="canvas_spec.content.eyebrow",
    )
    add_compiler_text_node(
        nodes,
        "title",
        compact_semantic_text(content_text(spec, "title", "Untitled"), max_chars=40),
        x=64,
        y=96,
        width=700,
        height=92,
        fill=theme["text"],
        font_size=36,
        font_weight=850,
        role="title",
        source_ref="canvas_spec.content.title",
    )
    subtitle = compact_semantic_text(content_text(spec, "subtitle", content_text(spec, "summary", "")), max_chars=64)
    add_compiler_text_node(
        nodes,
        "subtitle",
        subtitle,
        x=66,
        y=196,
        width=700,
        height=52,
        fill=theme["muted"],
        font_size=18,
        font_weight=560,
        role="subtitle",
        source_ref="canvas_spec.content.subtitle" if subtitle else None,
    )
    for index, (key, value) in enumerate(content_compiler_items(spec)[:6], 1):
        col = (index - 1) % 2
        row = (index - 1) // 2
        x = 64 + col * 424
        y = 276 + row * 70
        nodes.append(
            {
                "id": f"content-card-{index}",
                "kind": "rect",
                "role": "container",
                "x": x,
                "y": y,
                "width": 390,
                "height": 56,
                "fill": theme["panel"],
                "origin": {"type": "template", "id": template_id, "reason": "contract compile content card"},
            }
        )
        add_compiler_text_node(
            nodes,
            f"content-{index}",
            value,
            x=x + 16,
            y=y + 13,
            width=358,
            height=34,
            fill=theme["text"],
            font_size=16,
            font_weight=650,
            role="body",
            source_ref=f"canvas_spec.content.{key}",
        )
    return nodes


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
    explicit = node.get("role")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    node_id = str(node.get("id") or "")
    kind = str(node.get("kind") or "")
    if node_id == "background":
        return "background"
    if node_id.startswith(("data-bar", "unlock-", "data-price-curve")):
        return "data_chart"
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
    explicit = node.get("source_ref")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
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


def semantic_element_type_for_node(node: dict[str, Any], role: str) -> str:
    kind = str(node.get("kind") or "unknown")
    if role == "decorative" and kind == "line":
        return "decorative_line"
    if role == "decorative" and kind == "path":
        return "decorative_path"
    if role == "background":
        return "background"
    if role == "container":
        return "layout_container"
    return kind


def semantic_purpose_for_node(node: dict[str, Any], role: str) -> str | None:
    explicit = node.get("semantic_purpose") or node.get("purpose")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if role != "decorative":
        return None
    node_id = str(node.get("id") or "").lower()
    kind = str(node.get("kind") or "").lower()
    if kind not in {"line", "path"}:
        return None
    if any(token in node_id for token in ("connector", "flow", "arrow", "link")):
        return "connector"
    if any(token in node_id for token in ("timeline", "milestone", "rail", "lane")):
        return "timeline or lane structure"
    if any(token in node_id for token in ("divider", "rule", "separator")):
        return "section divider"
    if "annotation" in node_id or "callout" in node_id:
        return "annotation pointer"
    return None


def origin_for_semantic_node(node: dict[str, Any], role: str, spec: dict[str, Any] | None) -> dict[str, Any] | None:
    explicit = node.get("origin")
    if isinstance(explicit, dict):
        return explicit
    node_id = str(node.get("id") or "")
    if role == "background":
        return {"type": "theme", "id": str((spec or {}).get("theme_id") or "unknown-theme"), "reason": "canvas background"}
    if semantic_source_ref_for_node(node):
        return None
    if role in {"decorative", "container", "data_chart"}:
        template_id = str((spec or {}).get("template_id") or "unknown-template")
        reason = "template visual structure"
        if role == "data_chart":
            reason = "template data visualization scaffold"
        elif "line" in node_id or str(node.get("kind")) == "line":
            reason = "template decorative rule"
        elif "grid" in node_id:
            reason = "template grid decoration"
        elif "panel" in node_id or "card" in node_id:
            reason = "template layout container"
        return {"type": "template", "id": template_id, "reason": reason}
    return None


def semantic_elements_from_nodes(nodes: list[dict[str, Any]], spec: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        role = semantic_role_for_node(node)
        source_ref = semantic_source_ref_for_node(node)
        origin = origin_for_semantic_node(node, role, spec)
        element: dict[str, Any] = {
            "element_id": node_id,
            "kind": str(node.get("kind") or "unknown"),
            "role": role,
            "element_type": semantic_element_type_for_node(node, role),
            "source_ref": source_ref,
            "text": node.get("text") if isinstance(node.get("text"), str) else None,
            "bbox": {
                "x": number(node.get("x"), 0),
                "y": number(node.get("y"), 0),
                "width": number(node.get("width"), 0),
                "height": number(node.get("height"), 0),
            },
            "style": semantic_style_for_node(node),
        }
        if origin is not None:
            element["origin"] = origin
        semantic_purpose = semantic_purpose_for_node(node, role)
        if semantic_purpose:
            element["semantic_purpose"] = semantic_purpose
        elements.append(element)
    return elements


def decorative_trace_summary(elements: list[dict[str, Any]]) -> dict[str, Any]:
    required_roles = {"background", "container", "decorative"}
    required = [
        item
        for item in elements
        if isinstance(item, dict) and item.get("role") in required_roles
    ]
    missing = [
        str(item.get("element_id"))
        for item in required
        if not isinstance(item.get("origin"), dict)
    ]
    by_origin_type: dict[str, int] = {}
    for item in required:
        origin = item.get("origin")
        if isinstance(origin, dict):
            origin_type = str(origin.get("type") or "unknown")
            by_origin_type[origin_type] = by_origin_type.get(origin_type, 0) + 1
    return {
        "schema_version": "svglide-decorative-trace-summary/v1",
        "required_origin_count": len(required),
        "missing_origin_count": len(missing),
        "missing_origin_element_ids": missing,
        "by_origin_type": by_origin_type,
    }


def semantic_style_for_node(node: dict[str, Any]) -> dict[str, Any]:
    style: dict[str, Any] = {}
    for key in ["fill", "stroke", "stroke_width", "opacity", "font_size", "font_weight", "d", "x1", "y1", "x2", "y2"]:
        value = node.get(key)
        if value is not None:
            style[key] = value
    return style


def nodes_from_satori_svg(satori_svg_path: Path) -> list[dict[str, Any]]:
    observations = svglide_node_layout_drift.observations_from_svg(satori_svg_path)
    nodes: list[dict[str, Any]] = []
    counters: dict[str, int] = {}
    for observation in observations:
        bbox = observation.get("bbox") if isinstance(observation.get("bbox"), dict) else {}
        kind = str(observation.get("kind") or "node")
        raw_id = observation.get("id")
        node_id = str(raw_id) if isinstance(raw_id, str) and raw_id else ""
        if not node_id:
            counters[kind] = counters.get(kind, 0) + 1
            node_id = f"satori-{kind}-{counters[kind]}"
        height = number(bbox.get("height"), 0)
        if kind == "text":
            height = max(height, 24)
        nodes.append(
            {
                "id": node_id,
                "kind": "text" if kind == "text" else kind,
                "x": number(bbox.get("x"), 0),
                "y": number(bbox.get("y"), 0),
                "width": number(bbox.get("width"), 0),
                "height": height,
                "text": observation.get("text") if isinstance(observation.get("text"), str) else None,
            }
        )
    return nodes


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
    labels = content_first_list(spec, ["metric_labels", "labels"], ["运营口径", "用户口径", "单客口径", "现金口径"])[:4]
    milestones = content_first_list(spec, ["milestones", "unlock_labels"], ["口径", "来源", "区间", "敏感项"])[:4]
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
        label = labels[index] if index < len(labels) else ""
        svg_text(parts, nodes, f"data-label-{index + 1}", label, x=x, y=354, width=156, height=28, fill=theme["muted"], font_size=15, font_weight=700)
    svg_line(parts, nodes, "unlock-axis", x1=96, y1=424, x2=826, y2=424, stroke=theme["muted"], stroke_width=2, opacity=0.5)
    for index, label in enumerate(milestones):
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
        [
            "items",
            "steps",
            "events",
            "metrics",
            "points",
            "sections",
            "risks",
            "lanes",
            "nodes",
            "takeaways",
            "rows",
            "trends",
            "cards",
            "pillars",
            "notes",
            "panels",
            "bars",
            "cells",
            "tags",
        ],
        ["背景", "证据", "判断"],
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
        f'<text data-node-id="eyebrow" data-box-x="92" data-box-y="64" data-box-width="420" data-box-height="30" x="92" y="84" fill="{theme["primary"]}" font-size="18" font-weight="800" font-family="Inter">{escape(eyebrow)}</text>',
        f'<text data-node-id="title" data-box-x="92" data-box-y="108" data-box-width="700" data-box-height="96" x="92" y="158" fill="{theme["text"]}" font-size="46" font-weight="850" font-family="Inter">{escape(title)}</text>',
        f'<text data-node-id="subtitle" data-box-x="94" data-box-y="212" data-box-width="660" data-box-height="54" x="94" y="240" fill="{theme["muted"]}" font-size="22" font-weight="500" font-family="Inter">{escape(subtitle)}</text>',
    ]
    for index, item in enumerate(items):
        x = 92 + (index % 3) * 268
        y = 306 + (index // 3) * 92
        nodes.extend(
            [
                {"id": f"item-card-{index + 1}", "kind": "rect", "x": x, "y": y, "width": 244, "height": 86},
                {"id": f"item-{index + 1}", "kind": "text", "x": x + 16, "y": y + 13, "width": 212, "height": 62, "text": item},
            ]
        )
        parts.append(f'<rect data-node-id="item-card-{index + 1}" x="{x}" y="{y}" width="244" height="86" fill="{theme["panel"]}" opacity="0.84"/>')
        parts.append(f'<text data-node-id="item-{index + 1}" data-box-x="{x + 16}" data-box-y="{y + 13}" data-box-width="212" data-box-height="62" x="{x + 16}" y="{y + 41}" fill="{theme["text"]}" font-size="19" font-weight="720" font-family="Inter">{escape(item)}</text>')
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
        raise ArtboardError(f"template_id {template_id} requires the Node/Satori renderer; Python generic fallback is not allowed")
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


def fmt_path_number(value: float) -> str:
    return f"{value:g}"


def is_path_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def read_path_number(tokens: list[str], index: int) -> tuple[float, int] | None:
    if index >= len(tokens) or is_path_command(tokens[index]):
        return None
    try:
        return float(tokens[index]), index + 1
    except ValueError:
        return None


def read_path_numbers(tokens: list[str], index: int, count: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    next_index = index
    for _ in range(count):
        read = read_path_number(tokens, next_index)
        if read is None:
            return None
        value, next_index = read
        values.append(value)
    return values, next_index


def normalize_satori_path_d(d: str) -> str | None:
    tokens = PATH_TOKEN_RE.findall(d)
    if not tokens:
        return None
    index = 0
    command: str | None = None
    x = 0.0
    y = 0.0
    start_x = 0.0
    start_y = 0.0
    parts: list[str] = []

    while index < len(tokens):
        if is_path_command(tokens[index]):
            command = tokens[index]
            index += 1
        if command is None:
            return None
        lower = command.lower()
        relative = command.islower()

        if lower == "m":
            read = read_path_numbers(tokens, index, 2)
            if read is None:
                return None
            values, index = read
            x = x + values[0] if relative else values[0]
            y = y + values[1] if relative else values[1]
            start_x = x
            start_y = y
            parts.append(f"M{fmt_path_number(x)} {fmt_path_number(y)}")
            command = "l" if relative else "L"
            continue

        if lower == "l":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_numbers(tokens, index, 2)
                if read is None:
                    return None
                values, index = read
                x = x + values[0] if relative else values[0]
                y = y + values[1] if relative else values[1]
                parts.append(f"L{fmt_path_number(x)} {fmt_path_number(y)}")
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "h":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_number(tokens, index)
                if read is None:
                    return None
                value, index = read
                x = x + value if relative else value
                parts.append(f"L{fmt_path_number(x)} {fmt_path_number(y)}")
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "v":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_number(tokens, index)
                if read is None:
                    return None
                value, index = read
                y = y + value if relative else value
                parts.append(f"L{fmt_path_number(x)} {fmt_path_number(y)}")
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "a":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_numbers(tokens, index, 7)
                if read is None:
                    return None
                values, index = read
                end_x = x + values[5] if relative else values[5]
                end_y = y + values[6] if relative else values[6]
                if abs(end_x - x) > 0.001 or abs(end_y - y) > 0.001:
                    parts.append(f"L{fmt_path_number(end_x)} {fmt_path_number(end_y)}")
                x = end_x
                y = end_y
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "c":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_numbers(tokens, index, 6)
                if read is None:
                    return None
                values, index = read
                if relative:
                    x1, y1 = x + values[0], y + values[1]
                    x2, y2 = x + values[2], y + values[3]
                    end_x, end_y = x + values[4], y + values[5]
                else:
                    x1, y1, x2, y2, end_x, end_y = values
                parts.append(
                    f"C{fmt_path_number(x1)} {fmt_path_number(y1)} "
                    f"{fmt_path_number(x2)} {fmt_path_number(y2)} "
                    f"{fmt_path_number(end_x)} {fmt_path_number(end_y)}"
                )
                x = end_x
                y = end_y
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "q":
            consumed = False
            while index < len(tokens) and not is_path_command(tokens[index]):
                read = read_path_numbers(tokens, index, 4)
                if read is None:
                    return None
                values, index = read
                if relative:
                    x1, y1 = x + values[0], y + values[1]
                    end_x, end_y = x + values[2], y + values[3]
                else:
                    x1, y1, end_x, end_y = values
                parts.append(f"Q{fmt_path_number(x1)} {fmt_path_number(y1)} {fmt_path_number(end_x)} {fmt_path_number(end_y)}")
                x = end_x
                y = end_y
                consumed = True
            if not consumed:
                return None
            continue

        if lower == "z":
            x = start_x
            y = start_y
            parts.append("Z")
            command = None
            continue

        return None

    return " ".join(parts) if parts else None


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def estimated_run_width(text: str, font_size: float, measured_span: float) -> float:
    if text.strip().isdigit() and measured_span > 0:
        return measured_span
    total = 0.0
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            total += font_size
        elif char.isspace():
            total += font_size * 0.35
        elif char.isascii() and (char.isalnum() or char in "-_/"):
            total += font_size * 0.62
        else:
            total += font_size * 0.72
    if not text:
        total = measured_span
    factor = 1.04 if has_cjk(text) else 1.12
    return max(measured_span, total * factor)


def parse_css_number(style: str, key: str, fallback: float) -> float:
    for part in style.split(";"):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        if name.strip().lower() != key:
            continue
        raw = value.strip().lower().removesuffix("px")
        try:
            return float(raw)
        except ValueError:
            return fallback
    return fallback


def foreign_object_font_size(element: ElementTree.Element) -> float:
    for child in list(element):
        style = child.attrib.get("style")
        if isinstance(style, str):
            return parse_css_number(style, "font-size", 18.0)
    return 18.0


def foreign_object_text(element: ElementTree.Element) -> str:
    return "".join(element.itertext()).strip()


def preview_estimated_text_width(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        width += font_size * (0.92 if "\u4e00" <= char <= "\u9fff" else 0.56)
    return width


def foreign_object_bbox(element: ElementTree.Element) -> dict[str, float] | None:
    try:
        return {
            "x": float(element.attrib.get("x", "0")),
            "y": float(element.attrib.get("y", "0")),
            "width": float(element.attrib.get("width", "0")),
            "height": float(element.attrib.get("height", "0")),
        }
    except ValueError:
        return None


def bbox_right(bbox: dict[str, float]) -> float:
    return bbox["x"] + bbox["width"]


def bbox_bottom(bbox: dict[str, float]) -> float:
    return bbox["y"] + bbox["height"]


def bbox_intersects(left: dict[str, float], right: dict[str, float]) -> bool:
    return not (
        bbox_right(left) <= right["x"]
        or bbox_right(right) <= left["x"]
        or bbox_bottom(left) <= right["y"]
        or bbox_bottom(right) <= left["y"]
    )


def set_svg_number_attr(element: ElementTree.Element, key: str, value: float) -> None:
    element.set(key, f"{value:g}")


def repair_foreign_object_layout(svg_text: str) -> str:
    try:
        root = ElementTree.fromstring(svg_text)
    except ElementTree.ParseError:
        return svg_text
    changed = False
    text_elements = [element for element in root.iter() if local_name(element.tag) == "foreignObject"]

    for element in text_elements:
        text_value = foreign_object_text(element)
        if text_value.isdigit() and len(text_value) >= 2:
            font_size = foreign_object_font_size(element)
            bbox = foreign_object_bbox(element)
            if bbox:
                min_width = min(960.0 - bbox["x"], preview_estimated_text_width(text_value, font_size) + 10)
                if bbox["width"] < min_width:
                    set_svg_number_attr(element, "width", min_width)
                    changed = True
                if bbox["height"] < font_size * 2.5:
                    set_svg_number_attr(element, "height", font_size * 2.5)
                    changed = True

    for _ in range(12):
        moved = False
        items: list[tuple[ElementTree.Element, dict[str, float]]] = []
        for element in text_elements:
            bbox = foreign_object_bbox(element)
            if bbox:
                items.append((element, bbox))
        items.sort(key=lambda item: (item[1]["y"], item[1]["x"]))
        for left_index, (left_element, left_bbox) in enumerate(items):
            for right_element, right_bbox in items[left_index + 1 :]:
                if not bbox_intersects(left_bbox, right_bbox):
                    continue
                same_row = abs(left_bbox["y"] - right_bbox["y"]) <= min(left_bbox["height"], right_bbox["height"]) * 0.65
                if same_row and left_bbox["x"] <= right_bbox["x"]:
                    left_text = foreign_object_text(left_element)
                    right_text = foreign_object_text(right_element)
                    if right_text.isdigit() and not left_text.isdigit():
                        new_left_x = max(48.0, right_bbox["x"] - left_bbox["width"] - 4)
                        if new_left_x < left_bbox["x"]:
                            set_svg_number_attr(left_element, "x", new_left_x)
                            moved = True
                            changed = True
                            break
                    new_x = bbox_right(left_bbox) + 4
                    if new_x + right_bbox["width"] <= 920:
                        set_svg_number_attr(right_element, "x", new_x)
                        moved = True
                        changed = True
                        break
                lower_element, upper_bbox = (right_element, left_bbox) if right_bbox["y"] >= left_bbox["y"] else (left_element, right_bbox)
                lower_bbox = right_bbox if lower_element is right_element else left_bbox
                new_y = bbox_bottom(upper_bbox) + 2
                if new_y + lower_bbox["height"] <= 512:
                    set_svg_number_attr(lower_element, "y", new_y)
                    moved = True
                    changed = True
                    break
            if moved:
                break
        if not moved:
            break

    if not changed:
        return svg_text
    ElementTree.register_namespace("", SVG_NS)
    ElementTree.register_namespace("slide", SLIDE_NS)
    return ElementTree.tostring(root, encoding="unicode") + "\n"


def scan_unsupported(root: ElementTree.Element) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for element in root.iter():
        name = local_name(element.tag)
        if name in SATORI_INTERNAL_ELEMENTS:
            continue
        if name in FAIL_FAST_ELEMENTS:
            issues.append({"code": "satori_svg_element_fail_fast", "message": f"unsupported Satori SVG element in P0a: {name}"})
        elif name not in SUPPORTED_SATORI_ELEMENTS:
            issues.append({"code": "satori_svg_element_unsupported", "message": f"unsupported Satori SVG element in P0a: {name}"})
        if "filter" in element.attrib:
            issues.append({"code": "satori_svg_effect_fail_fast", "message": f"unsupported effect attribute on {name}"})
    return issues


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


def compile_satori_svg_to_svglide(satori_svg: str) -> dict[str, Any]:
    try:
        validate_satori_preview_svg(satori_svg, strict=True)
    except ArtboardError as error:
        raise ArtboardError(f"satori_svg_effect_fail_fast: {error}") from error
    return {"status": "passed", "satori_svg_usage": "compiler_input"}


def write_contact_sheet(project: Path, png_paths: list[Path]) -> dict[str, Any]:
    if not png_paths:
        raise ArtboardError("cannot create contact sheet without page PNG files")
    try:
        from PIL import Image, ImageDraw
    except Exception as err:  # pragma: no cover - environment dependent
        raise ArtboardError("Pillow is required to compose contact-sheet.png from resvg page PNGs") from err
    thumbs = []
    thumb_meta: list[dict[str, Any]] = []
    for index, png in enumerate(png_paths, 1):
        image = Image.open(png).convert("RGB")
        source_width, source_height = image.size
        image.thumbnail((320, 180), Image.LANCZOS)
        tile = Image.new("RGB", (320, 180), (10, 14, 18))
        image_x = (320 - image.width) // 2
        image_y = (180 - image.height) // 2
        tile.paste(image, (image_x, image_y))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((8, 8, 46, 30), fill=(15, 23, 42))
        draw.text((16, 13), f"{index:02d}", fill=(248, 250, 252))
        thumbs.append(tile)
        thumb_meta.append(
            {
                "page": index,
                "source_png": relpath(png, project),
                "source_width": source_width,
                "source_height": source_height,
                "image_in_tile": {"x": image_x, "y": image_y, "width": image.width, "height": image.height},
                "label_in_tile": {"x": 8, "y": 8, "width": 38, "height": 22},
            }
        )
    cols = min(3, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    gap = 16
    sheet = Image.new("RGB", (cols * 320 + (cols + 1) * gap, rows * 180 + (rows + 1) * gap), (6, 10, 16))
    for index, tile in enumerate(thumbs):
        x = gap + (index % cols) * (320 + gap)
        y = gap + (index // cols) * (180 + gap)
        sheet.paste(tile, (x, y))
        thumb_meta[index]["tile_bbox"] = {"x": x, "y": y, "width": 320, "height": 180}
        image_in_tile = thumb_meta[index]["image_in_tile"]
        thumb_meta[index]["image_bbox"] = {
            "x": x + image_in_tile["x"],
            "y": y + image_in_tile["y"],
            "width": image_in_tile["width"],
            "height": image_in_tile["height"],
        }
    output = project / CONTACT_SHEET
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return {
        "path": CONTACT_SHEET.as_posix(),
        "sha256": file_sha256(output),
        "source_pngs": [relpath(path, project) for path in png_paths],
        "grid": {"tile_width": 320, "tile_height": 180, "gap": gap, "cols": cols, "rows": rows},
        "pages": thumb_meta,
    }


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
    artboard_dir = project / "04-artboard" / "raw"
    raw_dir = artboard_dir
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
        satori_path = raw_dir / f"{page_name}.visual.svg"
        png_path = artboard_dir / f"{page_name}.visual.png"
        metadata_path = artboard_dir / f"{page_name}.render-metadata.json"
        node_observations_path = artboard_dir / f"{page_name}.node-observations.json"
        canvas_spec_artifact_path = artboard_dir / f"{page_name}.canvas-spec.json"
        canvas_template_path = artboard_dir / f"{page_name}.canvas-template.svg"
        semantic_map_path = artboard_dir / f"{page_name}.semantic-map.json"
        node_layout_path = artboard_dir / f"{page_name}.node-layout-map.json"
        write_json(canvas_spec_artifact_path, spec)
        actual_satori_package = use_node_satori_renderer()
        node_adapter_path: Path | None = None
        renderer_metadata: dict[str, Any] = {}
        if actual_satori_package:
            node_adapter_path = render_node_satori_svg(canvas_spec_artifact_path, satori_path, png_path, metadata_path, node_observations_path)
            satori_svg = satori_path.read_text(encoding="utf-8")
            canvas_template_svg = satori_svg
            canvas_template_path.write_text(canvas_template_svg, encoding="utf-8")
            layout_nodes = nodes_from_satori_svg(satori_path)
            semantic_nodes = compiler_nodes_from_canvas_spec(spec)
            renderer_metadata = read_json(metadata_path)
            satori_preview = validate_satori_preview_svg(satori_svg, strict=False)
            semantic_source = "SatoriSVG"
            extraction_strategy = "canvas_spec_compiler_nodes_with_satori_preview"
            compiler_input_path = satori_path
            compiler = {
                "semantic_source": semantic_source,
                "compiler_input": "RawSatoriSVG",
                "satori_svg_usage": "compiler_input",
                "native_mapped": [],
                "fail_fast": sorted(FAIL_FAST_ELEMENTS),
            }
        else:
            canvas_template_svg, nodes = render_satori_compatible_svg(spec)
            canvas_template_path.write_text(canvas_template_svg, encoding="utf-8")
            satori_svg = canvas_template_svg
            satori_preview = validate_satori_preview_svg(satori_svg, strict=True)
            metadata_path.write_text(json.dumps({"node_version": None, "satori_version": None, "resvg_version": None, "font_path": None}, indent=2) + "\n", encoding="utf-8")
            write_json(node_observations_path, {"version": "svglide-node-observations/v1", "observation_source": "rendered_satori_svg_parse", "nodes": []})
            layout_nodes = nodes
            semantic_nodes = nodes
            semantic_source = "CanvasSpec"
            extraction_strategy = "python_template_nodes"
            compiler_input_path = satori_path
            compiler = {
                "semantic_source": semantic_source,
                "compiler_input": "CanvasSpecTemplateSVG",
                "satori_svg_usage": "preview_only",
                "native_mapped": [],
                "fail_fast": sorted(FAIL_FAST_ELEMENTS),
            }
        semantic_elements = semantic_elements_from_nodes(semantic_nodes, spec)
        trace_summary = decorative_trace_summary(semantic_elements)
        semantic_map = {
            "version": SEMANTIC_MAP_VERSION,
            "page": index,
            "template_id": spec.get("template_id"),
            "theme_id": spec.get("theme_id"),
            "theme": normalize_theme(spec),
            "semantic_source": semantic_source,
            "extraction_strategy": extraction_strategy,
            "content_keys": sorted((spec.get("content") or {}).keys()) if isinstance(spec.get("content"), dict) else [],
            "elements": semantic_elements,
            "trace_summary": trace_summary,
        }
        write_json(semantic_map_path, semantic_map)
        satori_path.write_text(satori_svg, encoding="utf-8")
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
        layout_observations = renderer_observations
        if semantic_source == "SatoriSVG":
            # Layout nodes are parsed from the final raw Satori SVG. Renderer
            # hook observations are useful audit evidence, but they describe
            # intermediate flex nodes and must not be matched against final SVG
            # element boxes for drift gating.
            layout_observations = []
        node_layout_map = svglide_node_layout_drift.build_node_layout_map(
            page=index,
            expected_nodes=layout_nodes,
            renderer_observations=layout_observations,
            satori_svg_path=satori_path,
        )
        write_json(node_layout_path, node_layout_map)
        input_semantic_hash = file_sha256(compiler_input_path)
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
            "compiler_input": relpath(compiler_input_path, project),
            "compiler_input_sha256": file_sha256(compiler_input_path),
            "input_semantic_hash": input_semantic_hash,
            "semantic_map": relpath(semantic_map_path, project),
            "semantic_map_sha256": file_sha256(semantic_map_path),
            "node_layout_map": relpath(node_layout_path, project),
            "node_layout_map_sha256": file_sha256(node_layout_path),
            "compiler": compiler,
            "decorative_trace_summary": trace_summary,
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
                "semantic_source": compiler.get("semantic_source"),
                "canvas_spec_sha256": json_sha256(spec),
                "semantic_map": relpath(semantic_map_path, project),
                "semantic_map_sha256": file_sha256(semantic_map_path),
                "input_semantic_hash": input_semantic_hash,
                "node_layout_map": relpath(node_layout_path, project),
                "node_layout_map_sha256": file_sha256(node_layout_path),
                "canvas_template_svg": relpath(canvas_template_path, project),
                "canvas_template_svg_sha256": file_sha256(canvas_template_path),
                "compiler_input": relpath(compiler_input_path, project),
                "compiler_input_sha256": file_sha256(compiler_input_path),
                "compiler_input_type": compiler.get("compiler_input"),
                "satori_svg_usage": compiler.get("satori_svg_usage"),
                "satori_svg": relpath(satori_path, project),
                "satori_svg_sha256": file_sha256(satori_path),
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
    raw_visual_manifest = {
        "version": "svglide-raw-visual-manifest/v1",
        "stage": "generate_svg",
        "status": "passed",
        "pages": [
            {
                "page": receipt["page"],
                "source": receipt["satori_svg"],
                "source_sha256": receipt["satori_svg_sha256"],
                "semantic_map": receipt["semantic_map"],
                "semantic_map_sha256": receipt["semantic_map_sha256"],
                "node_layout_map": receipt["node_layout_map"],
                "node_layout_map_sha256": receipt["node_layout_map_sha256"],
                "png": receipt["png"],
                "png_sha256": receipt["png_sha256"],
                "receipt": receipt["path"],
            }
            for receipt in receipts
        ],
        "summary": {"page_count": len(receipts), "max_workers": max_workers},
        "created_at": now_iso(),
    }
    raw_visual_manifest_path = raw_dir / "manifest.json"
    write_json(raw_visual_manifest_path, raw_visual_manifest)
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
    compat_artboard_dir = project / "04-svg" / "artboard"
    compat_raw_dir = compat_artboard_dir / "raw"
    compat_raw_dir.mkdir(parents=True, exist_ok=True)
    for receipt in receipts:
        page = int(receipt["page"])
        page_name = f"page-{page:03d}"
        source_path = project / str(receipt["satori_svg"])
        compat_raw_path = compat_raw_dir / f"{page_name}.satori.svg"
        compat_raw_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        compat_receipt = dict(receipt)
        compat_receipt["compiler_input"] = relpath(compat_raw_path, project)
        compat_receipt["satori_svg"] = relpath(compat_raw_path, project)
        compat_receipt["satori_svg_sha256"] = file_sha256(compat_raw_path)
        write_json(compat_artboard_dir / f"{page_name}.receipt.json", compat_receipt)
    try:
        import svglide_contract_compile

        svglide_contract_compile.compile_project(project)
    except Exception as err:
        raise ArtboardError(f"contract compile failed after artboard render: {err}") from err
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
        "raw_visual_manifest": relpath(raw_visual_manifest_path, project),
        "raw_visual_files": [{"path": receipt["satori_svg"], "sha256": receipt["satori_svg_sha256"]} for receipt in receipts],
        "semantic_maps": [{"path": receipt["semantic_map"], "sha256": receipt["semantic_map_sha256"]} for receipt in receipts],
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
