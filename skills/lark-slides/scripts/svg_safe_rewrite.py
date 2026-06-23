#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import svg_effect_classifier as classifier


SLIDE_NS = "https://slides.bytedance.com/ns"
SVG_NS = "http://www.w3.org/2000/svg"
SVG_CONTRACT_VERSION = "svglide-authoring-contract/v1"
DEFAULT_WIDTH = 960.0
DEFAULT_HEIGHT = 540.0
HARD_TAGS = classifier.HARD_EFFECT_TAGS
HARD_ATTRS = classifier.HARD_EFFECT_ATTRS
HARD_STYLE_PROPS = classifier.HARD_STYLE_PROPS
NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:px)?$")


class SafeRewriteError(ValueError):
    """Raised when a safe SVG cannot be produced or validated."""


def _number(value: str | None, default: float) -> float:
    if not value:
        return default
    value = value.strip()
    if not NUMBER_RE.match(value):
        return default
    if value.endswith("px"):
        value = value[:-2]
    try:
        return float(value)
    except ValueError:
        return default


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 0.0001:
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def svg_viewport(svg: str) -> tuple[float, float, str]:
    root = classifier.sanitize_or_reject(svg)
    width = _number(root.attrib.get("width"), DEFAULT_WIDTH)
    height = _number(root.attrib.get("height"), DEFAULT_HEIGHT)
    view_box = root.attrib.get("viewBox", "").strip()
    if not view_box:
        view_box = f"0 0 {_format_number(width)} {_format_number(height)}"
    return width, height, view_box


def href_for_asset(asset_path: Path, base_dir: Path) -> str:
    asset_path = asset_path.resolve()
    base_dir = base_dir.resolve()
    try:
        rel = asset_path.relative_to(base_dir)
    except ValueError:
        if not str(asset_path).startswith("/private/tmp/"):
            raise SafeRewriteError(f"raster asset escapes base directory: {asset_path}")
        return str(asset_path)
    rel_text = rel.as_posix()
    if rel_text.startswith("../") or rel_text == "..":
        raise SafeRewriteError(f"raster asset escapes base directory: {asset_path}")
    return f"@./{rel_text}"


def full_page_image_svg(original_svg: str, png_path: Path, base_dir: Path) -> str:
    width, height, view_box = svg_viewport(original_svg)
    href = href_for_asset(png_path, base_dir)
    return "\n".join(
        [
            f'<svg xmlns="{SVG_NS}" xmlns:slide="{SLIDE_NS}" slide:role="slide"',
            f'     slide:contract-version="{SVG_CONTRACT_VERSION}"',
            f'     width="{_format_number(width)}" height="{_format_number(height)}" viewBox="{html.escape(view_box)}">',
            f'  <image slide:role="image" href="{html.escape(href)}" x="0" y="0" width="{_format_number(width)}" height="{_format_number(height)}" />',
            "</svg>",
            "",
        ]
    )


def _style_has_hard_props(style: str) -> bool:
    props = classifier.normalize_style(style)
    return any(classifier.is_hard_style_property(prop) for prop in props)


def validate_safe_subset_lightweight(svg: str) -> None:
    root = classifier.sanitize_or_reject(svg)
    if classifier.local_name(root.tag) != "svg":
        raise SafeRewriteError("safe SVG root must be <svg>")
    for elem in root.iter():
        tag = classifier.local_name(elem.tag)
        if tag in HARD_TAGS:
            raise SafeRewriteError(f"safe SVG still contains unsupported tag <{tag}>")
        if tag in {"text", "polygon", "polyline"}:
            raise SafeRewriteError(f"safe SVG still contains unsupported root-safe tag <{tag}>")
        for raw_attr, value in elem.attrib.items():
            attr = classifier.local_name(raw_attr)
            if attr in HARD_ATTRS:
                raise SafeRewriteError(f"safe SVG still contains unsupported attribute {attr}")
            if attr == "style" and _style_has_hard_props(value):
                raise SafeRewriteError("safe SVG still contains unsupported CSS effect")


def rewrite_svg(svg: str, islands: list[dict[str, object]], rendered_assets: list[dict[str, object]], base_dir: Path) -> str:
    if not islands:
        validate_safe_subset_lightweight(svg)
        return svg
    if len(islands) == 1 and islands[0].get("kind") == "full-page":
        png_path = Path(str(rendered_assets[0]["output_png"]))
        safe_svg = full_page_image_svg(svg, png_path, base_dir)
        validate_safe_subset_lightweight(safe_svg)
        return safe_svg
    raise SafeRewriteError("only full-page safe rewrite is implemented in P0")
