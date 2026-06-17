#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import base64
import html
import json
import math
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "svglide-preview-lint/v1"
DEFAULT_CANVAS_WIDTH = 960.0
DEFAULT_CANVAS_HEIGHT = 540.0
MIN_BODY_ELEMENTS = 2
MIN_VARIETY_PAGE_COUNT = 4
DEFAULT_VALIDATION_PROFILE = "authoring"
VISUAL_SCORE_THRESHOLDS = {
    "authoring": 75,
    "production": 85,
    "golden": 90,
}

SVG_BLOCK_RE = re.compile(r"<svg\b[\s\S]*?</svg>", re.IGNORECASE)
NUMBER_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
STYLE_DECL_RE = re.compile(r"\s*([A-Za-z-]+)\s*:\s*([^;]+)")
RGB_RE = re.compile(r"rgba?\(([^)]+)\)", re.IGNORECASE)
TRANSFORM_RE = re.compile(r"(translate|scale)\s*\(([^)]*)\)", re.IGNORECASE)
PLACEHOLDER_COPY_RE = re.compile(
    r"\b(contract renderer|placeholder|lorem ipsum|todo|draft only|smoke deck)\b|SVGlide\s+contract\s+renderer",
    re.IGNORECASE,
)
LOCAL_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
RENDERABLE_TAGS = {"rect", "circle", "ellipse", "line", "path", "polygon", "polyline", "image", "text", "foreignobject"}
PRESENTATION_ATTRS = {
    "color",
    "display",
    "fill",
    "fill-opacity",
    "font-size",
    "opacity",
    "stroke",
    "stroke-opacity",
    "stroke-width",
    "visibility",
}


@dataclass(frozen=True)
class SvgSource:
    page: int
    label: str
    root: ET.Element
    base_dir: Path
    path: Path | None = None


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def as_list(self) -> list[float]:
        return [round(self.x, 2), round(self.y, 2), round(self.width, 2), round(self.height, 2)]


@dataclass(frozen=True)
class Transform:
    sx: float = 1.0
    sy: float = 1.0
    tx: float = 0.0
    ty: float = 0.0

    def apply(self, box: Box) -> Box:
        x1 = box.x * self.sx + self.tx
        y1 = box.y * self.sy + self.ty
        x2 = (box.x + box.width) * self.sx + self.tx
        y2 = (box.y + box.height) * self.sy + self.ty
        return Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))


@dataclass(frozen=True)
class RenderElement:
    element_id: str
    tag: str
    box: Box
    page: int
    label: str
    text: str = ""
    href: str = ""
    fill: str = ""
    color: str = ""
    font_size: float = 16.0
    background: bool = False


class PreviewSvgCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.svg_refs: list[str] = []
        self.svg_data_uris: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        for attr_name in ("src", "data", "href"):
            value = attr_map.get(attr_name)
            if not value:
                continue
            if is_svg_data_uri(value):
                self.svg_data_uris.append(value)
            elif is_svg_reference(value):
                self.svg_refs.append(value)


def local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def attr_value(element: ET.Element, name: str, default: str = "") -> str:
    for key, value in element.attrib.items():
        if local_name(key) == name.lower():
            return value
    return default


def parse_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    match = NUMBER_RE.search(str(value))
    if not match:
        return default
    try:
        number = float(match.group(0))
    except ValueError:
        return default
    if not math.isfinite(number):
        return default
    return number


def parse_style(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in style.split(";"):
        match = STYLE_DECL_RE.match(part)
        if match:
            out[match.group(1).strip().lower()] = match.group(2).strip()
    return out


def merged_style(element: ET.Element, inherited: dict[str, str]) -> dict[str, str]:
    style = dict(inherited)
    for key, value in element.attrib.items():
        name = local_name(key)
        if name in PRESENTATION_ATTRS and value.strip():
            style[name] = value.strip()
    style.update(parse_style(attr_value(element, "style")))
    return style


def parse_transform(value: str, current: Transform) -> Transform:
    sx, sy, tx, ty = current.sx, current.sy, current.tx, current.ty
    for name, raw_args in TRANSFORM_RE.findall(value or ""):
        args = [float(part) for part in NUMBER_RE.findall(raw_args)]
        if name.lower() == "translate" and args:
            tx += args[0] * sx
            ty += (args[1] if len(args) > 1 else 0.0) * sy
        elif name.lower() == "scale" and args:
            sx *= args[0]
            sy *= args[1] if len(args) > 1 else args[0]
    return Transform(sx=sx, sy=sy, tx=tx, ty=ty)


def canvas_size(root: ET.Element) -> tuple[float, float]:
    view_box = attr_value(root, "viewBox")
    numbers = [float(part) for part in NUMBER_RE.findall(view_box)]
    if len(numbers) == 4 and numbers[2] > 0 and numbers[3] > 0:
        return numbers[2], numbers[3]
    width = parse_number(attr_value(root, "width"), DEFAULT_CANVAS_WIDTH)
    height = parse_number(attr_value(root, "height"), DEFAULT_CANVAS_HEIGHT)
    if width <= 0 or height <= 0:
        return DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT
    return width, height


def check(
    code: str,
    level: str,
    confidence: str,
    message: str,
    *,
    page: int | None = None,
    bbox: Box | None = None,
    path: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "code": code,
        "level": level,
        "confidence": confidence,
        "message": message,
    }
    if page is not None:
        item["page"] = page
    if bbox is not None:
        item["bbox"] = bbox.as_list()
    if path:
        item["path"] = path
    if source:
        item["source"] = source
    return item


def safe_rel(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return str(path)


def is_svg_data_uri(value: str) -> bool:
    return value.strip().lower().startswith("data:image/svg+xml")


def is_svg_reference(value: str) -> bool:
    parsed = urllib.parse.urlsplit(html.unescape(value.strip()))
    if parsed.scheme in {"http", "https", "data", "javascript", "about", "mailto"}:
        return False
    path = urllib.parse.unquote(parsed.path).lower()
    return path.endswith(".svg")


def data_uri_svg(value: str) -> str:
    header, _, payload = value.partition(",")
    if not payload:
        raise ValueError("missing data URI payload")
    if ";base64" in header.lower():
        return base64.b64decode(payload).decode("utf-8")
    return urllib.parse.unquote(payload)


def normalize_ref(value: str) -> str:
    value = html.unescape(value.strip())
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme == "file":
        return urllib.parse.unquote(parsed.path)
    if parsed.scheme:
        return value
    return urllib.parse.unquote(parsed.path)


def candidate_paths(value: str, base_dir: Path, project: Path, *, svg_ref: bool = False) -> list[Path]:
    raw = normalize_ref(value)
    if raw.startswith("@"):
        raw = raw[1:]
    if not raw:
        return []
    path = Path(raw)
    if path.is_absolute():
        return [path]
    candidates = [base_dir / path, project / path]
    if svg_ref and len(path.parts) == 1:
        candidates.extend([project / "prepared" / path, project / "pages" / path])
    return candidates


def resolve_existing_ref(value: str, base_dir: Path, project: Path, *, svg_ref: bool = False) -> tuple[Path | None, Path | None]:
    candidates = candidate_paths(value, base_dir, project, svg_ref=svg_ref)
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidate
    return None, candidates[0] if candidates else None


def is_remote_or_data(value: str) -> bool:
    parsed = urllib.parse.urlsplit(value.strip())
    return parsed.scheme in {"http", "https", "data", "mailto", "javascript", "about"}


def is_local_image_href(value: str) -> bool:
    if not value or value.startswith("#") or is_remote_or_data(value):
        return False
    raw = normalize_ref(value)
    if raw.startswith("@"):
        raw = raw[1:]
    lower = raw.lower()
    return "/" in raw or "." in Path(raw).name or lower.endswith(LOCAL_IMAGE_EXTENSIONS)


def read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        return None, str(error)
    except json.JSONDecodeError as error:
        return None, f"{error.msg} at line {error.lineno} column {error.colno}"
    if not isinstance(data, dict):
        return None, "plan root must be a JSON object"
    return data, ""


def text_from_any(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def normalize_validation_profile(value: Any) -> str:
    raw = ""
    if isinstance(value, dict):
        for key in ("profile", "lane", "level", "mode"):
            raw = text_from_any(value.get(key)).lower()
            if raw:
                break
    else:
        raw = text_from_any(value).lower()
    raw = raw.replace("-", "_")
    if raw in {"prod", "production_asset_strict"}:
        return "production"
    if raw in {"gold", "golden_regression"}:
        return "golden"
    if raw in VISUAL_SCORE_THRESHOLDS:
        return raw
    return DEFAULT_VALIDATION_PROFILE


def validation_profile_from_plan(plan: Path) -> str:
    data, _ = read_json(plan)
    if not isinstance(data, dict):
        return DEFAULT_VALIDATION_PROFILE
    return normalize_validation_profile(data.get("validation_profile"))


def resolve_validation_profile(plan: Path, override: str = "") -> str:
    explicit = normalize_validation_profile(override) if override else ""
    return explicit or validation_profile_from_plan(plan)


def visual_score_threshold(profile: str) -> int:
    return VISUAL_SCORE_THRESHOLDS.get(normalize_validation_profile(profile), VISUAL_SCORE_THRESHOLDS[DEFAULT_VALIDATION_PROFILE])


def visual_score_enforced(profile: str) -> bool:
    return normalize_validation_profile(profile) in {"production", "golden"}


def extract_plan_svg_refs(data: dict[str, Any]) -> list[tuple[int, str]]:
    refs: list[tuple[int, str]] = []

    def add_from_entry(entry: Any, default_page: int) -> None:
        if not isinstance(entry, dict):
            return
        page = int(parse_number(entry.get("page") or entry.get("page_index"), default_page))
        for key in ("prepared_svg", "source_svg", "path", "svg", "svg_path", "file"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip().lower().split("?", 1)[0].endswith(".svg"):
                refs.append((page, value.strip()))
                return

    for index, entry in enumerate(data.get("svg_files") if isinstance(data.get("svg_files"), list) else []):
        add_from_entry(entry, index + 1)
    for index, entry in enumerate(data.get("pages") if isinstance(data.get("pages"), list) else []):
        add_from_entry(entry, index + 1)
    for index, entry in enumerate(data.get("slides") if isinstance(data.get("slides"), list) else []):
        add_from_entry(entry, index + 1)
    return refs


def parse_svg_text(text: str, label: str, checks: list[dict[str, Any]], *, page: int, path: Path | None = None) -> ET.Element | None:
    try:
        return ET.fromstring(text)
    except ET.ParseError as error:
        checks.append(
            check(
                "svg_parse_failed",
                "error",
                "high",
                f"SVG is not well formed: {error}",
                page=page,
                path=str(path) if path else label,
                source=label,
            )
        )
        return None


def collect_preview_sources(project: Path, preview: Path, plan: Path, checks: list[dict[str, Any]]) -> list[SvgSource]:
    sources: list[SvgSource] = []
    if not preview.exists():
        checks.append(
            check(
                "preview_missing",
                "error",
                "high",
                "preview HTML does not exist",
                path=safe_rel(preview, project),
            )
        )
        return sources

    try:
        preview_text = preview.read_text(encoding="utf-8")
    except OSError as error:
        checks.append(
            check(
                "preview_read_failed",
                "error",
                "high",
                f"preview HTML could not be read: {error}",
                path=safe_rel(preview, project),
            )
        )
        return sources

    collector = PreviewSvgCollector()
    try:
        collector.feed(preview_text)
        collector.close()
    except Exception as error:
        checks.append(
            check(
                "preview_parse_failed",
                "error",
                "high",
                f"preview HTML could not be parsed: {error}",
                path=safe_rel(preview, project),
            )
        )
        return sources

    inline_blocks = SVG_BLOCK_RE.findall(preview_text)
    if not collector.svg_refs and not collector.svg_data_uris and not inline_blocks:
        checks.append(
            check(
                "preview_svg_missing",
                "error",
                "high",
                "preview HTML does not reference or embed any SVG",
                path=safe_rel(preview, project),
                source="preview",
            )
        )

    seen_paths: set[Path] = set()
    for index, ref in enumerate(collector.svg_refs, start=1):
        path, display = resolve_existing_ref(ref, preview.parent, project, svg_ref=True)
        if path is None:
            checks.append(
                check(
                    "svg_file_missing",
                    "error",
                    "high",
                    "preview references an SVG file that does not exist",
                    page=index,
                    path=safe_rel(display, project) if display else ref,
                    source="preview",
                )
            )
            continue
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        try:
            svg_text = path.read_text(encoding="utf-8")
        except OSError as error:
            checks.append(
                check(
                    "svg_read_failed",
                    "error",
                    "high",
                    f"referenced SVG could not be read: {error}",
                    page=index,
                    path=safe_rel(path, project),
                    source="preview",
                )
            )
            continue
        root = parse_svg_text(svg_text, safe_rel(path, project), checks, page=index, path=path)
        if root is not None:
            sources.append(SvgSource(page=index, label=safe_rel(path, project), root=root, base_dir=path.parent, path=path))

    for index, value in enumerate(collector.svg_data_uris, start=len(sources) + 1):
        try:
            svg_text = data_uri_svg(value)
        except (ValueError, UnicodeDecodeError) as error:
            checks.append(
                check(
                    "svg_data_uri_parse_failed",
                    "error",
                    "high",
                    f"embedded SVG data URI could not be decoded: {error}",
                    page=index,
                    source="preview",
                )
            )
            continue
        root = parse_svg_text(svg_text, f"preview:data-uri:{index}", checks, page=index)
        if root is not None:
            sources.append(SvgSource(page=index, label=f"preview:data-uri:{index}", root=root, base_dir=preview.parent))

    for index, svg_text in enumerate(inline_blocks, start=len(sources) + 1):
        root = parse_svg_text(svg_text, f"preview:inline-svg:{index}", checks, page=index)
        if root is not None:
            sources.append(SvgSource(page=index, label=f"preview:inline-svg:{index}", root=root, base_dir=preview.parent))

    plan_data, plan_error = read_json(plan)
    if plan_data is None:
        checks.append(
            check(
                "plan_parse_failed" if plan.exists() else "plan_missing",
                "error",
                "high",
                f"slide plan is required and could not be read: {plan_error}",
                path=safe_rel(plan, project),
                source="plan",
            )
        )
        plan_refs: list[tuple[int, str]] = []
    else:
        plan_refs = extract_plan_svg_refs(plan_data)

    for page, ref in plan_refs:
        path, display = resolve_existing_ref(ref, project, project, svg_ref=True)
        if path is None:
            checks.append(
                check(
                    "svg_file_missing",
                    "error",
                    "high",
                    "slide plan references an SVG file that does not exist",
                    page=page,
                    path=safe_rel(display, project) if display else ref,
                    source="plan",
                )
            )
            continue
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        try:
            svg_text = path.read_text(encoding="utf-8")
        except OSError as error:
            checks.append(
                check(
                    "svg_read_failed",
                    "error",
                    "high",
                    f"planned SVG could not be read: {error}",
                    page=page,
                    path=safe_rel(path, project),
                    source="plan",
                )
            )
            continue
        root = parse_svg_text(svg_text, safe_rel(path, project), checks, page=page, path=path)
        if root is not None:
            sources.append(SvgSource(page=page, label=safe_rel(path, project), root=root, base_dir=path.parent, path=path))

    if not sources and not any(str(item["code"]).startswith("svg_") or item["code"] == "preview_svg_missing" for item in checks):
        checks.append(
            check(
                "preview_svg_missing",
                "error",
                "high",
                "preview HTML does not reference or embed any SVG",
                path=safe_rel(preview, project),
                source="preview",
            )
        )
    return sources


def parse_color(value: str) -> tuple[int, int, int, float] | None:
    value = value.strip().lower()
    if not value or value in {"none", "transparent", "currentcolor", "inherit"}:
        return None
    named = {
        "black": "#000000",
        "white": "#ffffff",
        "red": "#ff0000",
        "green": "#008000",
        "blue": "#0000ff",
        "gray": "#808080",
        "grey": "#808080",
    }
    value = named.get(value, value)
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) == 3:
            raw = "".join(part * 2 for part in raw)
        if len(raw) == 6:
            try:
                return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), 1.0
            except ValueError:
                return None
    match = RGB_RE.match(value)
    if match:
        parts = [part.strip() for part in match.group(1).split(",")]
        if len(parts) >= 3:
            channels: list[int] = []
            for part in parts[:3]:
                if part.endswith("%"):
                    channels.append(round(float(part[:-1]) * 2.55))
                else:
                    channels.append(round(float(part)))
            alpha = float(parts[3]) if len(parts) >= 4 else 1.0
            return max(0, min(255, channels[0])), max(0, min(255, channels[1])), max(0, min(255, channels[2])), alpha
    return None


def luminance(color: tuple[int, int, int, float]) -> float:
    r, g, b, alpha = color
    if alpha <= 0:
        return 1.0
    values = []
    for channel in (r, g, b):
        raw = channel / 255.0
        values.append(raw / 12.92 if raw <= 0.03928 else ((raw + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def is_light_color(value: str) -> bool:
    parsed = parse_color(value)
    return parsed is not None and luminance(parsed) >= 0.78


def is_dark_color(value: str) -> bool:
    parsed = parse_color(value)
    return parsed is not None and luminance(parsed) <= 0.28


def style_opacity(style: dict[str, str]) -> float:
    opacity = parse_number(style.get("opacity"), 1.0)
    fill_opacity = parse_number(style.get("fill-opacity"), 1.0)
    return opacity * fill_opacity


def visible_element(element: ET.Element, style: dict[str, str]) -> bool:
    if style.get("display", "").lower() == "none":
        return False
    if style.get("visibility", "").lower() in {"hidden", "collapse"}:
        return False
    if style_opacity(style) <= 0.01:
        return False
    tag = local_name(element.tag)
    if tag in {"rect", "circle", "ellipse", "polygon", "path"}:
        fill = style.get("fill", "")
        stroke = style.get("stroke", "")
        if fill.lower() in {"none", "transparent"} and stroke.lower() in {"", "none", "transparent"}:
            return False
    if tag == "line":
        stroke = style.get("stroke", "")
        return stroke.lower() not in {"", "none", "transparent"}
    return True


def text_from_element(element: ET.Element) -> str:
    return " ".join(part.strip() for part in element.itertext() if part.strip())


def descendant_text_color(element: ET.Element, style: dict[str, str]) -> str:
    if style.get("color"):
        return style["color"]
    if style.get("fill"):
        return style["fill"]
    for child in element.iter():
        child_style = parse_style(attr_value(child, "style"))
        if child_style.get("color"):
            return child_style["color"]
        if child_style.get("fill"):
            return child_style["fill"]
        fill = attr_value(child, "fill")
        if fill:
            return fill
    return ""


def points_bbox(value: str) -> Box | None:
    numbers = [float(part) for part in NUMBER_RE.findall(value or "")]
    if len(numbers) < 4:
        return None
    xs = numbers[0::2]
    ys = numbers[1::2]
    if not xs or not ys:
        return None
    return Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def element_bbox(element: ET.Element, tag: str, style: dict[str, str]) -> Box | None:
    if tag in {"rect", "foreignobject", "image"}:
        return Box(
            parse_number(attr_value(element, "x")),
            parse_number(attr_value(element, "y")),
            parse_number(attr_value(element, "width")),
            parse_number(attr_value(element, "height")),
        )
    if tag == "circle":
        radius = parse_number(attr_value(element, "r"))
        return Box(parse_number(attr_value(element, "cx")) - radius, parse_number(attr_value(element, "cy")) - radius, radius * 2, radius * 2)
    if tag == "ellipse":
        rx = parse_number(attr_value(element, "rx"))
        ry = parse_number(attr_value(element, "ry"))
        return Box(parse_number(attr_value(element, "cx")) - rx, parse_number(attr_value(element, "cy")) - ry, rx * 2, ry * 2)
    if tag == "line":
        x1 = parse_number(attr_value(element, "x1"))
        y1 = parse_number(attr_value(element, "y1"))
        x2 = parse_number(attr_value(element, "x2"))
        y2 = parse_number(attr_value(element, "y2"))
        stroke = max(1.0, parse_number(style.get("stroke-width"), 1.0))
        return Box(min(x1, x2) - stroke / 2, min(y1, y2) - stroke / 2, abs(x2 - x1) + stroke, abs(y2 - y1) + stroke)
    if tag in {"path", "polygon", "polyline"}:
        return points_bbox(attr_value(element, "d") or attr_value(element, "points"))
    if tag == "text":
        text = text_from_element(element)
        font_size = parse_number(style.get("font-size") or attr_value(element, "font-size"), 16.0)
        x = parse_number(attr_value(element, "x"))
        y = parse_number(attr_value(element, "y"))
        width = parse_number(attr_value(element, "textLength"), max(font_size * 0.55 * len(text), font_size * 0.6 if text else 0.0))
        height = font_size * 1.25 if text else 0.0
        return Box(x, y - font_size, width, height)
    return None


def is_background_rect(tag: str, box: Box, fill: str, canvas_width: float, canvas_height: float) -> bool:
    if tag != "rect" or not fill or box.area <= 0:
        return False
    covers_width = box.x <= 2 and box.x + box.width >= canvas_width - 2
    covers_height = box.y <= 2 and box.y + box.height >= canvas_height - 2
    return covers_width and covers_height


def collect_render_elements(source: SvgSource) -> list[RenderElement]:
    canvas_width, canvas_height = canvas_size(source.root)
    elements: list[RenderElement] = []

    def walk(element: ET.Element, inherited: dict[str, str], transform: Transform) -> None:
        tag = local_name(element.tag)
        style = merged_style(element, inherited)
        next_transform = parse_transform(attr_value(element, "transform"), transform)
        if tag in RENDERABLE_TAGS and visible_element(element, style):
            box = element_bbox(element, tag, style)
            if box is not None:
                box = next_transform.apply(box)
                fill = style.get("fill", "")
                color = descendant_text_color(element, style) if tag in {"text", "foreignobject"} else style.get("color", "")
                text = text_from_element(element) if tag in {"text", "foreignobject"} else ""
                elements.append(
                    RenderElement(
                        element_id=attr_value(element, "id"),
                        tag=tag,
                        box=box,
                        page=source.page,
                        label=source.label,
                        text=text,
                        href=attr_value(element, "href"),
                        fill=fill,
                        color=color,
                        font_size=parse_number(style.get("font-size"), 16.0),
                        background=is_background_rect(tag, box, fill, canvas_width, canvas_height),
                    )
                )
        if tag in {"defs", "style", "script", "title", "desc"}:
            return
        for child in list(element):
            walk(child, style, next_transform)

    walk(source.root, {}, Transform())
    return elements


def quantize(value: float, total: float, buckets: int = 8) -> int:
    if total <= 0:
        return 0
    return max(0, min(buckets - 1, int((value / total) * buckets)))


def color_tone(value: str) -> str:
    parsed = parse_color(value)
    if parsed is None:
        return "none"
    if luminance(parsed) <= 0.28:
        return "dark"
    if luminance(parsed) >= 0.78:
        return "light"
    return "mid"


def visual_fingerprint(source: SvgSource) -> str:
    canvas_width, canvas_height = canvas_size(source.root)
    elements = [element for element in collect_render_elements(source) if not element.background and element.box.area > 16]
    tokens: list[str] = []
    for element in elements:
        center_x = element.box.x + element.box.width / 2
        center_y = element.box.y + element.box.height / 2
        width_bucket = quantize(element.box.width, canvas_width, 6)
        height_bucket = quantize(element.box.height, canvas_height, 6)
        x_bucket = quantize(center_x, canvas_width)
        y_bucket = quantize(center_y, canvas_height)
        tone = color_tone(element.fill or element.color)
        tokens.append(f"{element.tag}:{x_bucket}:{y_bucket}:{width_bucket}:{height_bucket}:{tone}")
    return "|".join(sorted(tokens))


def intersection(a: Box, b: Box) -> Box:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)
    return Box(x1, y1, max(0.0, x2 - x1), max(0.0, y2 - y1))


def inside_canvas_ratio(box: Box, canvas_width: float, canvas_height: float) -> float:
    if box.area <= 0:
        return 0.0
    inside = intersection(box, Box(0, 0, canvas_width, canvas_height))
    return inside.area / box.area


def box_covers(backing: Box, target: Box, threshold: float = 0.78) -> bool:
    if target.area <= 0:
        return False
    return intersection(backing, target).area / target.area >= threshold


def is_label_backing(element: RenderElement) -> bool:
    ident = element.element_id.lower()
    if element.tag != "rect" or element.box.area <= 0:
        return False
    if element.background:
        return False
    if element.box.width > 260 or element.box.height > 96:
        return False
    return any(token in ident for token in ["name-plate", "label-back", "label-bg", "badge", "pill"])


def is_label_text(element: RenderElement) -> bool:
    ident = element.element_id.lower()
    return any(token in ident for token in ["label", "name", "title", "badge", "pill"])


def is_page_chrome(element: RenderElement, canvas_height: float) -> bool:
    ident = element.element_id.lower()
    if element.background:
        return True
    if ident in {"top-rule", "bottom-rule", "page-rule"}:
        return True
    if "footer" in ident:
        return True
    if element.tag in {"text", "foreignobject"} and element.box.y >= canvas_height - 52 and element.font_size <= 12:
        return True
    if element.tag in {"rect", "line"} and element.box.height <= 6 and element.box.width >= 0.5 * DEFAULT_CANVAS_WIDTH:
        return True
    return False


def semantic_label_token_count(elements: list[RenderElement]) -> int:
    text = " ".join(element.text for element in elements if element.text.strip())
    parts = re.split(r"[/、,，;；|·\n]+", text)
    return sum(1 for part in parts if len(part.strip()) >= 2)


def element_path(project: Path, source: SvgSource) -> str:
    if source.path:
        return safe_rel(source.path, project)
    return source.label


def lint_svg_source(project: Path, source: SvgSource) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    canvas_width, canvas_height = canvas_size(source.root)
    elements = collect_render_elements(source)
    body_elements = [element for element in elements if not element.background and element.box.area > 4]
    text_elements = [element for element in elements if element.tag in {"text", "foreignobject"} and element.text.strip()]
    semantic_text_elements = [element for element in text_elements if not is_page_chrome(element, canvas_height)]
    dark_backings = [element for element in elements if element.tag in {"rect", "path", "polygon"} and is_dark_color(element.fill)]
    label_backings = [element for element in elements if is_label_backing(element)]
    image_elements = [element for element in elements if element.tag == "image" and element.box.area > 0]
    meaningful_visual_elements = [
        element
        for element in body_elements
        if element.tag not in {"text", "foreignobject"}
        and not is_page_chrome(element, canvas_height)
        and element.box.area > 80
    ]
    path = element_path(project, source)

    if body_elements:
        body_count = len(body_elements)
    else:
        body_count = 0
    if body_count < MIN_BODY_ELEMENTS:
        checks.append(
            check(
                "page_body_too_sparse",
                "error",
                "high",
                f"page has {body_count} visible body elements; expected at least {MIN_BODY_ELEMENTS}",
                page=source.page,
                path=path,
                source=source.label,
            )
        )
    elif not image_elements and len(text_elements) <= 2 and body_count <= 4:
        checks.append(
            check(
                "low_information_density",
                "warning",
                "medium",
                "page has only a thin visual idea; add data, structure, image, or a stronger SVG focal system",
                page=source.page,
                path=path,
                source=source.label,
            )
        )
    if any(PLACEHOLDER_COPY_RE.search(element.text) for element in text_elements):
        checks.append(
            check(
                "placeholder_renderer_copy",
                "warning",
                "high",
                "page exposes implementation, placeholder, or smoke-test copy",
                page=source.page,
                path=path,
                source=source.label,
            )
        )
    if (
        not image_elements
        and len(meaningful_visual_elements) >= 5
        and len(semantic_text_elements) <= 2
        and semantic_label_token_count(semantic_text_elements) < 4
    ):
        checks.append(
            check(
                "unlabeled_visual_system",
                "warning",
                "medium",
                "page has many visual marks but too few semantic labels or annotations",
                page=source.page,
                path=path,
                source=source.label,
            )
        )

    for element in elements:
        if element.tag in {"text", "foreignobject"} and element.box.area <= 0:
            checks.append(
                check(
                    "text_bbox_zero",
                    "error",
                    "high",
                    "text element has zero width or height",
                    page=source.page,
                    bbox=element.box,
                    path=path,
                    source=source.label,
                )
            )
        if element.tag == "image":
            if element.box.area <= 0:
                checks.append(
                    check(
                        "image_bbox_zero",
                        "error",
                        "high",
                        "image element has zero width or height",
                        page=source.page,
                        bbox=element.box,
                        path=path,
                        source=source.label,
                    )
                )
            if not element.href.strip():
                checks.append(
                    check(
                        "image_href_missing",
                        "error",
                        "high",
                        "image element is missing href",
                        page=source.page,
                        bbox=element.box,
                        path=path,
                        source=source.label,
                    )
                )
            elif is_local_image_href(element.href):
                resolved, display = resolve_existing_ref(element.href, source.base_dir, project)
                if resolved is None:
                    checks.append(
                        check(
                            "local_image_missing",
                            "error",
                            "high",
                            "local image href does not resolve to an existing asset",
                            page=source.page,
                            bbox=element.box,
                            path=safe_rel(display, project) if display else element.href,
                            source=source.label,
                        )
                    )

        ratio = inside_canvas_ratio(element.box, canvas_width, canvas_height)
        bleed_x = max(canvas_width * 0.15, 96.0)
        bleed_y = max(canvas_height * 0.15, 54.0)
        beyond_bleed = (
            element.box.x < -bleed_x
            or element.box.y < -bleed_y
            or element.box.x + element.box.width > canvas_width + bleed_x
            or element.box.y + element.box.height > canvas_height + bleed_y
        )
        if element.box.area > 0 and (ratio < 0.5 or beyond_bleed):
            checks.append(
                check(
                    "bbox_out_of_bounds",
                    "error",
                    "high",
                    "visible element bbox is mostly or obviously outside the slide canvas",
                    page=source.page,
                    bbox=element.box,
                    path=path,
                    source=source.label,
                )
            )

    for index, left in enumerate(text_elements):
        for right in text_elements[index + 1 :]:
            overlap = intersection(left.box, right.box)
            if overlap.area <= 0:
                continue
            smaller = min(left.box.area, right.box.area)
            if smaller > 0 and overlap.area / smaller >= 0.45 and overlap.width >= 6 and overlap.height >= 6:
                checks.append(
                    check(
                        "text_overlap",
                        "error",
                        "high",
                        "text boxes have a high-overlap static bbox",
                        page=source.page,
                        bbox=overlap,
                        path=path,
                        source=source.label,
                    )
                )

    for backing in label_backings:
        for element in text_elements:
            if is_label_text(element) and box_covers(backing.box, element.box, threshold=0.55):
                continue
            overlap = intersection(backing.box, element.box)
            if overlap.area <= 0:
                continue
            smaller = min(backing.box.area, element.box.area)
            if smaller > 0 and overlap.area / smaller >= 0.2 and overlap.width >= 8 and overlap.height >= 8:
                checks.append(
                    check(
                        "shape_text_overlap",
                        "error",
                        "high",
                        "label backing shape overlaps a separate text block",
                        page=source.page,
                        bbox=overlap,
                        path=path,
                        source=source.label,
                    )
                )

    for element in text_elements:
        color = element.color or element.fill
        if not is_light_color(color):
            continue
        if not any(box_covers(backing.box, element.box) for backing in dark_backings):
            checks.append(
                check(
                    "light_text_without_dark_backing",
                    "error",
                    "high",
                    "light text has no detectable dark backing shape behind it",
                    page=source.page,
                    bbox=element.box,
                    path=path,
                    source=source.label,
                )
            )

    return checks


def lint_visual_variety(project: Path, sources: list[SvgSource]) -> list[dict[str, Any]]:
    if len(sources) < MIN_VARIETY_PAGE_COUNT:
        return []
    groups: dict[str, list[SvgSource]] = {}
    for source in sources:
        fingerprint = visual_fingerprint(source)
        if not fingerprint:
            continue
        groups.setdefault(fingerprint, []).append(source)
    repeated = max((items for items in groups.values()), key=len, default=[])
    if len(repeated) < math.ceil(len(sources) * 0.75):
        return []
    pages = [source.page for source in repeated]
    return [
        check(
            "low_visual_variety",
            "warning",
            "medium",
            f"{len(repeated)} of {len(sources)} pages share the same coarse visual fingerprint",
            page=pages[0] if pages else None,
            path=safe_rel(repeated[0].path, project) if repeated and repeated[0].path else None,
            source="preview",
        )
    ]


def visual_score(checks: list[dict[str, Any]]) -> int:
    errors = sum(1 for item in checks if item.get("level") == "error")
    warnings = sum(1 for item in checks if item.get("level") == "warning")
    return max(0, min(100, 100 - errors * 22 - warnings * 7))


def lint_project(project: Path, preview: Path, plan: Path, validation_profile: str = "") -> dict[str, Any]:
    project = project.resolve()
    preview = preview.resolve()
    plan = plan.resolve()
    profile = resolve_validation_profile(plan, validation_profile)
    threshold = visual_score_threshold(profile)
    checks: list[dict[str, Any]] = []
    sources = collect_preview_sources(project, preview, plan, checks)
    for source in sources:
        checks.extend(lint_svg_source(project, source))
    checks.extend(lint_visual_variety(project, sources))
    error_count = sum(1 for item in checks if item.get("level") == "error")
    warning_count = sum(1 for item in checks if item.get("level") == "warning")
    score = visual_score(checks)
    score_passed = score >= threshold
    score_enforced = visual_score_enforced(profile)
    warning_gate_passed = profile != "golden" or warning_count == 0
    status = "passed" if error_count == 0 and (score_passed or not score_enforced) and warning_gate_passed else "failed"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "error_count": error_count,
        "warning_count": warning_count,
        "checks": checks,
        "visual_score": score,
        "visual_score_threshold": threshold,
        "visual_score_passed": score_passed,
        "visual_score_mode": "enforced" if score_enforced else "advisory",
        "validation_profile": profile,
        "warning_gate_passed": warning_gate_passed,
        "project": str(project),
        "preview": safe_rel(preview, project),
        "plan": safe_rel(plan, project),
        "page_count": len(sources),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint an SVGlide preview HTML artifact without browser dependencies.")
    parser.add_argument("legacy_preview", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--project", help="SVGlide project root.")
    parser.add_argument("--preview", help="Preview HTML file, usually preview/preview.html.")
    parser.add_argument("--plan", help="Slide plan JSON file, usually slide_plan.json.")
    parser.add_argument("--validation-profile", default="", help="Quality profile: authoring, production, or golden.")
    args = parser.parse_args(argv)
    if args.legacy_preview and not args.preview:
        args.preview = args.legacy_preview
    if not args.preview:
        parser.error("--preview is required")
    preview = Path(args.preview)
    if args.project:
        project = Path(args.project)
    elif preview.parent.name == "preview":
        project = preview.parent.parent
    else:
        project = Path.cwd()
    args.project = str(project)
    if not args.plan:
        args.plan = str(project / "slide_plan.json")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = lint_project(Path(args.project), Path(args.preview), Path(args.plan), args.validation_profile)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
