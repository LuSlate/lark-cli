# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree


SVG_NS = "http://www.w3.org/2000/svg"
SLIDE_NS = "https://slides.bytedance.com/ns"
XHTML_NS = "http://www.w3.org/1999/xhtml"
TEXT_STYLE_MANIFEST_ID = "svglide-text-style-manifest"
TEXT_STYLE_MANIFEST_VERSION = "svglide-satori-text-style/v1"

ElementTree.register_namespace("", SVG_NS)
ElementTree.register_namespace("slide", SLIDE_NS)
ElementTree.register_namespace("html", XHTML_NS)


@dataclass
class TextStyleManifestResult:
    svg_text: str
    item_count: int
    bound_count: int
    loss_count: int
    losses: list[dict[str, Any]]


def _style_declarations(style: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not style:
        return result
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _attr(element: ElementTree.Element, name: str) -> str | None:
    value = element.attrib.get(name)
    return value if isinstance(value, str) else None


def _slide_attr(name: str) -> str:
    return f"{{{SLIDE_NS}}}{name}"


def _text_content(element: ElementTree.Element) -> str:
    return "".join(element.itertext()).strip()


def _first_xhtml_style(element: ElementTree.Element) -> dict[str, str]:
    style = _style_declarations(_attr(element, "style"))
    if style:
        return style
    for child in element.iter():
        style = _style_declarations(_attr(child, "style"))
        if style:
            return style
    return {}


def _is_managed_text(element: ElementTree.Element) -> bool:
    tag = element.tag.split("}", 1)[-1]
    role = element.attrib.get(_slide_attr("role"))
    shape_type = element.attrib.get(_slide_attr("shape-type"))
    return tag == "text" or role == "text" or (tag == "foreignObject" and shape_type == "text")


def _parse_number(value: str | None, fallback: int | float) -> int | float:
    if not value:
        return fallback
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return fallback
    number = float(match.group(0))
    return int(number) if number.is_integer() else number


def _role_for_index(index: int) -> str:
    return ["display", "body", "label", "metric"][min(index, 3)]


def _manifest_item(element: ElementTree.Element, item_id: str, index: int) -> dict[str, Any]:
    tag = element.tag.split("}", 1)[-1]
    style = _first_xhtml_style(element) if tag == "foreignObject" else _style_declarations(_attr(element, "style"))
    role = _role_for_index(index)
    font_family = _attr(element, "font-family") or style.get("font-family") or "Source Sans Pro"
    font_size = _parse_number(_attr(element, "font-size") or style.get("font-size"), 16)
    font_weight = _parse_number(_attr(element, "font-weight") or style.get("font-weight"), 400)
    line_height = _parse_number(_attr(element, "line-height") or style.get("line-height"), 1.2)
    letter_spacing = _parse_number(_attr(element, "letter-spacing") or style.get("letter-spacing"), 0)
    color = _attr(element, "fill") or _attr(element, "color") or style.get("color") or "#111827"
    decoration_line = _attr(element, "text-decoration") or style.get("text-decoration") or "none"
    return {
        "role": role,
        "content_hash": f"sha256:pending-{item_id}",
        "font_family": font_family,
        "font_size": font_size,
        "font_weight": font_weight,
        "font_style": _attr(element, "font-style") or style.get("font-style") or "normal",
        "line_height": line_height,
        "letter_spacing": letter_spacing,
        "text_transform": style.get("text-transform", "none"),
        "color": color,
        "decoration": {"line": decoration_line, "style": "solid", "color": "currentColor", "thickness": "1px"},
        "wrap": "nowrap" if style.get("white-space") == "nowrap" else "wrap",
        "source_contract": {"strategy": f"theme.typography.{role}"},
        "loss_notes": [],
        "text": _text_content(element),
    }


def inject_text_style_manifest(svg_text: str) -> TextStyleManifestResult:
    root = ElementTree.fromstring(svg_text)
    managed = [element for element in root.iter() if _is_managed_text(element)]
    items: dict[str, dict[str, Any]] = {}
    losses: list[dict[str, Any]] = []
    for index, element in enumerate(managed):
        item_id = f"txt_{index + 1:03d}"
        element.set("data-svglide-text-style-id", item_id)
        items[item_id] = _manifest_item(element, item_id, index)
    metadata = ElementTree.Element(f"{{{SVG_NS}}}metadata", {"id": TEXT_STYLE_MANIFEST_ID, "type": "application/json"})
    metadata.text = json.dumps(
        {"version": TEXT_STYLE_MANIFEST_VERSION, "source": "cli-artboard-satori", "items": items},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    root.insert(0, metadata)
    output = ElementTree.tostring(root, encoding="unicode")
    return TextStyleManifestResult(
        svg_text=output,
        item_count=len(items),
        bound_count=len(items),
        loss_count=len(losses),
        losses=losses,
    )
