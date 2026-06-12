#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


DEBUG_GUIDE_RE = re.compile(r"\b(?:safe[-_ ]?area|debug|guide|bbox|layout[-_ ]?guide)\b", re.IGNORECASE)
SVG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
FO_RE = re.compile(r"<foreignObject\b([^>]*)>(.*?)</foreignObject>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*([\"'])(.*?)\2", re.DOTALL)
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([0-9.]+)px?", re.IGNORECASE)
LINE_HEIGHT_RE = re.compile(r"line-height\s*:\s*([0-9.]+)", re.IGNORECASE)
BIG_NUMBER_RE = re.compile(r"^[+\-]?\d+(?:\.\d+)?\s*(?:万|亿|%|人)?$")

CLASS_FONT_SIZE = {
    "kicker": 15.0,
    "title": 40.0,
    "title-sm": 29.0,
    "body": 16.0,
    "body-strong": 18.0,
    "small": 13.0,
    "metric": 54.0,
    "metric-light": 42.0,
}
CLASS_LINE_HEIGHT = {
    "title": 1.16,
    "title-sm": 1.18,
    "body": 1.5,
    "body-strong": 1.34,
    "small": 1.38,
    "metric": 1.0,
    "metric-light": 1.0,
}


def parse_attrs(raw: str) -> dict[str, str]:
    return {match.group(1): html.unescape(match.group(3)) for match in ATTR_RE.finditer(raw)}


def number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def issue(level: str, code: str, page: int, message: str, hint: str | None = None, box: dict[str, float] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"level": level, "code": code, "page": page, "message": message}
    if hint:
        out["hint"] = hint
    if box:
        out["box"] = box
    return out


def is_hidden_element(attrs: dict[str, str]) -> bool:
    style = attrs.get("style", "")
    if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0+)?(?:\s|;|$)", style, re.IGNORECASE):
        return True
    if attrs.get("display", "").lower() == "none":
        return True
    if attrs.get("visibility", "").lower() == "hidden":
        return True
    if attrs.get("opacity", "").strip() in {"0", "0.0", "0.00"}:
        return True
    return False


def css_class_value(raw_html: str) -> str:
    match = re.search(r"\bclass\s*=\s*([\"'])(.*?)\1", raw_html, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2)) if match else ""


def style_value(raw_html: str) -> str:
    match = re.search(r"\bstyle\s*=\s*([\"'])(.*?)\1", raw_html, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2)) if match else ""


def font_size_for(raw_html: str) -> float:
    style = style_value(raw_html)
    match = FONT_SIZE_RE.search(style)
    if match:
        return number(match.group(1), 13.0)
    classes = set(css_class_value(raw_html).split())
    for class_name, size in CLASS_FONT_SIZE.items():
        if class_name in classes:
            return size
    return 13.0


def line_height_for(raw_html: str, font_size: float) -> float:
    style = style_value(raw_html)
    match = LINE_HEIGHT_RE.search(style)
    if match:
        return number(match.group(1), 1.35)
    classes = set(css_class_value(raw_html).split())
    for class_name, line_height in CLASS_LINE_HEIGHT.items():
        if class_name in classes:
            return line_height
    return 1.35 if font_size < 18 else 1.25


def visible_text(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = TAG_RE.sub("", text)
    return html.unescape(text).strip()


def estimate_text_box(text: str, width: float, font_size: float, line_height: float) -> tuple[float, float, int]:
    if width <= 0:
        return 0.0, 0.0, 0
    lines = [line.strip() for line in text.splitlines() if line.strip()] or [text.strip()]
    estimated_lines = 0
    max_line_width = 0.0
    for line in lines:
        line_width = 0.0
        for char in line:
            line_width += font_size * (0.92 if "\u4e00" <= char <= "\u9fff" else 0.56)
        max_line_width = max(max_line_width, line_width)
        estimated_lines += max(1, int((line_width + width - 1) // width))
    return estimated_lines * font_size * line_height, max_line_width, estimated_lines


def overlap_ratio(a: dict[str, float], b: dict[str, float]) -> float:
    left = max(a["x"], b["x"])
    top = max(a["y"], b["y"])
    right = min(a["x"] + a["width"], b["x"] + b["width"])
    bottom = min(a["y"] + a["height"], b["y"] + b["height"])
    if right <= left or bottom <= top:
        return 0.0
    overlap = (right - left) * (bottom - top)
    smaller = min(a["width"] * a["height"], b["width"] * b["height"])
    return overlap / smaller if smaller > 0 else 0.0


def lint_svg_block(svg: str, page: int) -> tuple[list[dict[str, Any]], list[dict[str, float]]]:
    issues: list[dict[str, Any]] = []
    text_boxes: list[dict[str, float]] = []
    for match in re.finditer(r"<(rect|line|path|circle|ellipse)\b([^>]*)>", svg, re.IGNORECASE):
        element_name = match.group(1).lower()
        attrs = parse_attrs(match.group(2))
        if is_hidden_element(attrs):
            continue
        if (
            element_name == "rect"
            and attrs.get("x") == "48"
            and attrs.get("y") == "40"
            and attrs.get("width") == "864"
            and attrs.get("height") == "460"
            and attrs.get("fill", "").lower() == "none"
            and "stroke" in attrs
        ):
            issues.append(
                issue(
                    "error",
                    "preview_safe_area_debug_rect_visible",
                    page,
                    "preview must not show the 48/40/864/460 safe-area guide rectangle",
                    "Keep safe-area constraints in plan/preflight only; remove visible guide rects from delivered preview.",
                )
            )
        text = " ".join(attrs.get(key, "") for key in ["id", "class", "data-role", "data-debug", "aria-label"])
        if DEBUG_GUIDE_RE.search(text):
            issues.append(
                issue(
                    "error",
                    "preview_debug_guide_visible",
                    page,
                    "preview contains a visible debug/layout guide element",
                    "Remove elements whose id/class/data-* labels mark safe-area, debug, guide, bbox, or layout-guide.",
                )
            )
    for fo in FO_RE.finditer(svg):
        attrs = parse_attrs(fo.group(1))
        box = {
            "x": number(attrs.get("x")),
            "y": number(attrs.get("y")),
            "width": number(attrs.get("width")),
            "height": number(attrs.get("height")),
        }
        raw_inner = fo.group(2)
        text = visible_text(raw_inner)
        if not text:
            continue
        font_size = font_size_for(raw_inner)
        line_height = line_height_for(raw_inner, font_size)
        estimated_height, estimated_width, estimated_lines = estimate_text_box(text, box["width"], font_size, line_height)
        text_boxes.append(box)
        if box["width"] <= 0 or box["height"] <= 0:
            issues.append(issue("error", "preview_text_box_non_positive", page, "foreignObject text box has non-positive size", box=box))
            continue
        if estimated_height + 4 > box["height"]:
            issues.append(
                issue(
                    "error",
                    "preview_text_overflow_risk",
                    page,
                    f'text box is too short for estimated {estimated_lines} line(s): "{text[:48]}"',
                    "Increase foreignObject height or reduce text/font size before delivery.",
                    box,
                )
            )
        if estimated_width > box["width"] * 1.25 and estimated_lines == 1:
            issues.append(
                issue(
                    "warning",
                    "preview_text_width_tight",
                    page,
                    f'text box width is tight and may wrap unexpectedly: "{text[:48]}"',
                    "Reserve width for Chinese text and fallback fonts.",
                    box,
                )
            )
        normalized_text = text.replace(" ", "")
        if font_size >= 36 or BIG_NUMBER_RE.match(normalized_text):
            if estimated_width + 8 > box["width"] or font_size * line_height + 4 > box["height"]:
                issues.append(
                    issue(
                        "error",
                        "preview_big_number_box_tight",
                        page,
                        f'large number/title is in a tight box: "{text[:32]}"',
                        "Large numeric focal points need explicit width/height budget and should not rely on wrapping.",
                        box,
                    )
                )
    for index, current in enumerate(text_boxes):
        for other in text_boxes[index + 1 :]:
            ratio = overlap_ratio(current, other)
            if ratio >= 0.35:
                issues.append(
                    issue(
                        "error",
                        "preview_text_box_overlap",
                        page,
                        "foreignObject text boxes overlap substantially",
                        "Verify this is intentional; otherwise separate the text boxes or reduce their height.",
                        current,
                    )
                )
                break
    return issues, text_boxes


def lint_text(text: str, path: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    svg_blocks = SVG_RE.findall(text)
    if not svg_blocks:
        issues.append(issue("error", "preview_no_svg_pages", 0, "preview contains no SVG pages"))
    page_boxes: list[int] = []
    for index, svg in enumerate(svg_blocks, 1):
        page_issues, boxes = lint_svg_block(svg, index)
        issues.extend(page_issues)
        page_boxes.append(len(boxes))
    return {
        "path": path,
        "rendering_mode": "static_dom_approximation",
        "screenshot_paths": [],
        "page_count": len(svg_blocks),
        "text_box_count": sum(page_boxes),
        "summary": {
            "error_count": sum(1 for item in issues if item["level"] == "error"),
            "warning_count": sum(1 for item in issues if item["level"] == "warning"),
        },
        "page_issues": issues,
        "action": "repair_and_rerun" if any(item["level"] == "error" for item in issues) else "create_live",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint local SVGlide HTML/SVG previews for delivery-blocking visual risks.")
    parser.add_argument("input", help="preview HTML or SVG file")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args(argv)

    path = Path(args.input)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"svg_preview_lint: {error}", file=sys.stderr)
        return 2
    result = lint_text(text, str(path))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 1 if result["summary"]["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
