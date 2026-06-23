#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
UNSAFE_TAGS = {"script", "iframe", "object", "embed"}
HARD_EFFECT_TAGS = {
    "filter",
    "mask",
    "clipPath",
    "pattern",
    "symbol",
    "use",
    "marker",
    "animate",
    "animateTransform",
    "animateMotion",
}
HARD_EFFECT_ATTRS = {"filter", "mask", "clip-path"}
HARD_STYLE_PROPS = {
    "filter",
    "backdrop-filter",
    "mix-blend-mode",
    "clip-path",
    "mask",
    "box-shadow",
}
UNSUPPORTED_PATH_COMMAND_RE = re.compile(r"[AaSsTt]")
DOCTYPE_RE = re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE)
JAVASCRIPT_URL_RE = re.compile(r"javascript\s*:", re.IGNORECASE)
CSS_IMPORT_RE = re.compile(r"@import|url\(\s*['\"]?\s*https?://", re.IGNORECASE)
HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
SVG_ROOT_RE = re.compile(r"<svg\b", re.IGNORECASE)


class SvgRasterSafetyError(ValueError):
    """Raised when an SVG is unsafe to parse or render."""


@dataclass(frozen=True)
class EffectDetection:
    kind: str
    reason: str
    element_id: str = ""
    tag: str = ""
    attribute: str = ""

    def as_dict(self) -> dict[str, str]:
        out = {"kind": self.kind, "reason": self.reason}
        if self.element_id:
            out["element_id"] = self.element_id
        if self.tag:
            out["tag"] = self.tag
        if self.attribute:
            out["attribute"] = self.attribute
        return out


def local_name(name: str) -> str:
    if "}" in name:
        return name.rsplit("}", 1)[1]
    return name


def normalize_style(style: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in style.split(";"):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip().lower()
        if key:
            out[key] = value.strip()
    return out


def is_hard_style_property(prop: str) -> bool:
    prop = prop.strip().lower()
    return prop in HARD_STYLE_PROPS or prop.startswith("mask-") or prop.startswith("clip-path")


def parse_svg(svg: str) -> ET.Element:
    if not SVG_ROOT_RE.search(svg):
        raise SvgRasterSafetyError("input is not an SVG document")
    if DOCTYPE_RE.search(svg):
        raise SvgRasterSafetyError("SVG contains DTD or external entity markup")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        raise SvgRasterSafetyError(f"SVG XML parse failed: {error}") from error
    if local_name(root.tag) != "svg":
        raise SvgRasterSafetyError("input root element must be <svg>")
    return root


def _attr_value(attrs: dict[str, str], name: str) -> str:
    for raw_name, value in attrs.items():
        if local_name(raw_name) == name:
            return value
    return ""


def _href_value(attrs: dict[str, str]) -> str:
    for raw_name, value in attrs.items():
        if local_name(raw_name) == "href":
            return value.strip()
    return ""


def _is_external_stylesheet_or_script(tag: str, attrs: dict[str, str]) -> bool:
    href = _href_value(attrs)
    src = attrs.get("src", "").strip()
    rel = attrs.get("rel", "").strip().lower()
    type_value = attrs.get("type", "").strip().lower()
    if tag == "script" and (src or href):
        return True
    if tag == "link" and rel == "stylesheet":
        return True
    if tag == "style" and type_value in {"text/javascript", "application/javascript"}:
        return True
    return False


def sanitize_or_reject(svg: str) -> ET.Element:
    root = parse_svg(svg)
    for elem in root.iter():
        tag = local_name(elem.tag)
        attrs = {local_name(k): v for k, v in elem.attrib.items()}
        if tag in UNSAFE_TAGS:
            raise SvgRasterSafetyError(f"unsafe SVG tag <{tag}> is not allowed")
        if _is_external_stylesheet_or_script(tag, attrs):
            raise SvgRasterSafetyError("external JavaScript or CSS is not allowed")
        if tag == "style" and elem.text and CSS_IMPORT_RE.search(elem.text):
            raise SvgRasterSafetyError("external CSS imports are not allowed")
        for attr_name, value in attrs.items():
            normalized_attr = attr_name.lower()
            normalized_value = value.strip()
            if normalized_attr.startswith("on"):
                raise SvgRasterSafetyError(f"event attribute {attr_name} is not allowed")
            if JAVASCRIPT_URL_RE.search(normalized_value):
                raise SvgRasterSafetyError("javascript: URLs are not allowed")
            if normalized_attr in {"href", "src"} and tag != "image" and HTTP_URL_RE.match(normalized_value):
                raise SvgRasterSafetyError("non-image external resources are not allowed")
    return root


def _detect_element(elem: ET.Element, root: ET.Element, parent: ET.Element | None = None) -> Iterable[EffectDetection]:
    tag = local_name(elem.tag)
    elem_id = elem.attrib.get("id", "")
    if tag in HARD_EFFECT_TAGS:
        yield EffectDetection("tag", f"unsupported SVG tag <{tag}>", elem_id, tag)
    if parent is root and tag == "text":
        yield EffectDetection("text", "root-level text requires raster or safe rewrite", elem_id, tag)
    if tag in {"polygon", "polyline"}:
        yield EffectDetection("shape", f"<{tag}> requires raster or safe rewrite", elem_id, tag)
    if tag == "path" and UNSUPPORTED_PATH_COMMAND_RE.search(elem.attrib.get("d", "")):
        yield EffectDetection("path", "path contains unsupported A/S/T commands", elem_id, tag, "d")
    if tag == "foreignObject":
        style = normalize_style(elem.attrib.get("style", ""))
        rich_props = {"display", "position", "overflow", "transform", "background-image"} & set(style)
        if style.get("display", "").lower() in {"flex", "grid"}:
            yield EffectDetection("foreignObject", "foreignObject uses flex/grid layout", elem_id, tag, "style")
        elif style.get("position", "").lower() in {"absolute", "fixed"}:
            yield EffectDetection("foreignObject", "foreignObject uses absolute/fixed layout", elem_id, tag, "style")
        elif style.get("overflow", "").lower() in {"hidden", "clip"}:
            yield EffectDetection("foreignObject", "foreignObject clips HTML content", elem_id, tag, "style")
        elif rich_props - {"display", "position", "overflow"}:
            yield EffectDetection("foreignObject", "foreignObject uses rich CSS layout effects", elem_id, tag, "style")
    for raw_attr, value in elem.attrib.items():
        attr = local_name(raw_attr)
        if attr in HARD_EFFECT_ATTRS:
            yield EffectDetection("attribute", f"unsupported SVG attribute {attr}", elem_id, tag, attr)
        if attr == "style":
            style = normalize_style(value)
            for prop in sorted(style):
                if is_hard_style_property(prop):
                    yield EffectDetection("style", f"unsupported CSS property {prop}", elem_id, tag, "style")


def classify_effects(svg: str) -> list[EffectDetection]:
    root = sanitize_or_reject(svg)
    parents = {child: parent for parent in root.iter() for child in parent}
    detections: list[EffectDetection] = []
    for elem in root.iter():
        detections.extend(_detect_element(elem, root, parents.get(elem)))
    return detections


def detections_as_dicts(detections: Iterable[EffectDetection]) -> list[dict[str, str]]:
    return [detection.as_dict() for detection in detections]
