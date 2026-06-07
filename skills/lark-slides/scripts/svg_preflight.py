#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SLIDE_NS = "https://slides.bytedance.com/ns"
XLINK_NS = "http://www.w3.org/1999/xlink"
SVG_NS = "http://www.w3.org/2000/svg"
CANVAS_WIDTH = 960.0
CANVAS_HEIGHT = 540.0
SAFE_AREA = {"x": 48.0, "y": 40.0, "width": 864.0, "height": 460.0}

NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?:px)?$")
PATH_NUMBER_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
FONT_SHORTHAND_RE = re.compile(r"(^|;)\s*font\s*:", re.IGNORECASE)

SUPPORTED_SHAPES = {"rect", "ellipse", "circle", "line", "path", "foreignObject"}
RENDERABLE_TAGS = SUPPORTED_SHAPES | {"image", "text", "polygon", "polyline"}
IGNORED_SUBTREES = {"defs", "style"}


class SvgPreflightError(Exception):
    pass


def fail(message: str) -> None:
    raise SvgPreflightError(message)


def parse_args(argv: list[str]) -> dict[str, Any]:
    inputs: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
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
    return {"inputs": inputs}


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


def walk_renderable(root: ET.Element) -> list[ET.Element]:
    out: list[ET.Element] = []

    def walk(element: ET.Element) -> None:
        name = local_name(element.tag)
        if name in IGNORED_SUBTREES:
            return
        if name in RENDERABLE_TAGS or name == "foreignObject" or name == "image":
            out.append(element)
        for child in list(element):
            walk(child)

    for child in list(root):
        walk(child)
    return out


def validate_root(root: ET.Element) -> tuple[list[dict[str, Any]], float, float]:
    issues: list[dict[str, Any]] = []
    if local_name(root.tag) != "svg":
        issues.append(issue("error", "root_not_svg", "root element must be <svg>"))
    if svg_role(root) != "slide":
        issues.append(issue("error", "missing_root_role", 'root <svg> must include slide:role="slide"', root))

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
                        "error",
                        "external_image_href",
                        "<image> must not use http(s) or data href",
                        element,
                        'Download or generate the image locally and use href="@./path", or provide a file token.',
                    )
                )
        else:
            issues.append(issue("error", "unsupported_role", f'unsupported slide:role="{role}"', element))
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
    return None


def is_background_bbox(bbox: dict[str, float], canvas_width: float, canvas_height: float) -> bool:
    return bbox["x"] <= 0 and bbox["y"] <= 0 and bbox["x"] + bbox["width"] >= canvas_width and bbox["y"] + bbox["height"] >= canvas_height


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


def validate_geometry(elements: list[ET.Element], canvas_width: float, canvas_height: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    text_boxes: list[dict[str, Any]] = []
    canvas = {"x": 0.0, "y": 0.0, "width": canvas_width, "height": canvas_height}
    for element in elements:
        name = local_name(element.tag)
        bbox = bbox_for_element(element)
        if bbox is None:
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
        elif bbox_outside(bbox, SAFE_AREA):
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
                text_boxes.append({"element": element, "bbox": bbox, "text": text})
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
    geometry_issues, text_boxes = validate_geometry(elements, width, height)
    issues = root_issues + role_issues + validate_styles(root) + validate_paths(elements) + geometry_issues + validate_text_overlap(text_boxes)

    result["width"] = width
    result["height"] = height
    result["element_count"] = len(elements)
    result["text_box_count"] = len(text_boxes)
    result["issues"] = issues
    result["summary"] = {
        "error_count": sum(1 for item in issues if item["level"] == "error"),
        "warning_count": sum(1 for item in issues if item["level"] == "warning"),
    }
    if not issues:
        result.pop("issues")
    return result


def lint_files(paths: list[str]) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in paths:
        svg = Path(path).read_text(encoding="utf-8")
        files.append(lint_svg(svg, path))
    return {
        "summary": {
            "file_count": len(files),
            "error_count": sum(file["summary"]["error_count"] for file in files),
            "warning_count": sum(file["summary"]["warning_count"] for file in files),
        },
        "files": files,
    }


def main(argv: list[str]) -> int:
    try:
        options = parse_args(argv)
        result = lint_files(options["inputs"])
    except SvgPreflightError as error:
        print(f"svg_preflight: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"svg_preflight: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["summary"]["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
