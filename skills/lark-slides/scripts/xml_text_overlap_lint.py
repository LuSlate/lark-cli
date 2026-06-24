#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


class XmlTextOverlapLintError(Exception):
    pass


TITLE_LIKE_TEXT_TYPES = {"title", "headline", "sub-headline", "card_title", "callout"}
CENTER_ALLOWED_TEXT_TYPES = {"title", "quote", "hero"}


def fail(message: str) -> None:
    raise XmlTextOverlapLintError(message)


def read_file(file_path: str | Path) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def parse_args(argv: list[str]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if not token.startswith("--"):
            fail(f"unexpected argument: {token}")
        key = token[2:]
        next_token = argv[index + 1] if index + 1 < len(argv) else None
        if next_token is None or next_token.startswith("--"):
            options[key] = True
            index += 1
            continue
        options[key] = next_token
        index += 2
    return options


def extract_attribute(tag_source: str, name: str) -> str | None:
    match = re.search(fr'{re.escape(name)}="([^"]+)"', tag_source)
    return match.group(1) if match else None


def extract_numeric_attribute(tag_source: str, name: str) -> int | float | None:
    raw = extract_attribute(tag_source, name)
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return int(value) if value.is_integer() else value


def strip_xml(value: str) -> str:
    stripped = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", value)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    stripped = stripped.replace("&nbsp;", " ")
    stripped = stripped.replace("&amp;", "&")
    stripped = stripped.replace("&lt;", "<")
    stripped = stripped.replace("&gt;", ">")
    stripped = stripped.replace("&quot;", '"')
    stripped = stripped.replace("&#39;", "'")
    return re.sub(r"\s+", " ", stripped).strip()


def collapse_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def chinese_char_count(value: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", value))


def chinese_text(value: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fff]", value))


def xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def extract_content_lines(content_xml: str) -> list[str]:
    try:
        root = ET.fromstring(f"<root>{content_xml}</root>")
    except ET.ParseError:
        text = strip_xml(content_xml)
        return [text] if text else []

    lines: list[str] = []
    for content_node in root.iter():
        if xml_local_name(content_node.tag) != "content":
            continue
        paragraph_lines: list[str] = []
        for node in content_node.iter():
            if xml_local_name(node.tag) != "p":
                continue
            line = collapse_space("".join(node.itertext()))
            if line:
                paragraph_lines.append(line)
        if paragraph_lines:
            lines.extend(paragraph_lines)
        else:
            line = collapse_space("".join(content_node.itertext()))
            if line:
                lines.append(line)
    return lines


def extract_error_context(xml: str, line: int | None, column: int | None, radius: int = 40) -> str | None:
    if line is None or column is None:
        return None
    lines = xml.splitlines()
    if line < 1 or line > len(lines):
        return None
    source_line = lines[line - 1]
    start = max(column - radius, 0)
    end = min(column + radius, len(source_line))
    return source_line[start:end].strip()


def build_xml_error_issue(error: ET.ParseError, xml: str) -> dict[str, Any]:
    line, column = getattr(error, "position", (None, None))
    return {
        "level": "error",
        "code": "xml_not_well_formed",
        "message": f"XML is not well-formed: {error}",
        "line": line,
        "column": column,
        "context": extract_error_context(xml, line, column),
        "hint": (
            "Escape raw user text before placing it in XML. In text nodes and attribute values, bare & must be "
            "written as &amp;. In text nodes, write < as &lt; and > as &gt;. For attribute URLs, use a=1&amp;b=2."
        ),
    }


def validate_xml_well_formed(xml: str) -> dict[str, Any] | None:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        return build_xml_error_issue(error, xml)

    root_name = xml_local_name(root.tag)
    if root_name not in {"presentation", "slide"}:
        fail("input must contain a <presentation> or <slide> root")
    return None


def parse_presentation(xml: str) -> dict[str, Any]:
    presentation_match = re.search(r"<presentation\b([^>]*)>", xml)
    if presentation_match:
        return {
            "width": int(float(extract_attribute(presentation_match.group(1), "width") or 960)),
            "height": int(float(extract_attribute(presentation_match.group(1), "height") or 540)),
            "slides": re.findall(r"<slide\b[\s\S]*?</slide>", xml),
        }
    slide_match = re.findall(r"<slide\b[\s\S]*?</slide>", xml)
    if slide_match:
        return {"width": 960, "height": 540, "slides": slide_match}
    fail("input must contain a <presentation> or <slide> root")


def extract_elements(slide_xml: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for match in re.finditer(r"<shape\b([^>]*)>([\s\S]*?)</shape>", slide_xml):
        attrs, content = match.group(1), match.group(2)
        x = extract_numeric_attribute(attrs, "topLeftX")
        y = extract_numeric_attribute(attrs, "topLeftY")
        width = extract_numeric_attribute(attrs, "width")
        height = extract_numeric_attribute(attrs, "height")
        if all(value is not None for value in [x, y, width, height]):
            font_size = float(extract_attribute(content, "fontSize") or extract_attribute(attrs, "fontSize") or 16)
            lines = extract_content_lines(content)
            raw_text = "\n".join(lines)
            elements.append(
                {
                    "id": f"shape-{len(elements) + 1}",
                    "kind": "shape",
                    "type": extract_attribute(attrs, "type") or "shape",
                    "textType": extract_attribute(content, "textType"),
                    "textAlign": extract_attribute(content, "textAlign") or extract_attribute(attrs, "textAlign"),
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "fontSize": font_size,
                    "text": strip_xml(content),
                    "rawText": raw_text,
                    "lines": lines,
                }
            )

    for match in re.finditer(r"<(img|table|chart)\b([^>]*)/?>", slide_xml):
        attrs = match.group(2)
        x = extract_numeric_attribute(attrs, "topLeftX")
        y = extract_numeric_attribute(attrs, "topLeftY")
        width = extract_numeric_attribute(attrs, "width")
        height = extract_numeric_attribute(attrs, "height")
        if all(value is not None for value in [x, y, width, height]):
            elements.append(
                {
                    "id": f"{match.group(1)}-{len(elements) + 1}",
                    "kind": match.group(1),
                    "type": match.group(1),
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                }
            )
    return elements


def intersects(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["x"] < right["x"] + right["width"]
        and left["x"] + left["width"] > right["x"]
        and left["y"] < right["y"] + right["height"]
        and left["y"] + left["height"] > right["y"]
    )


def is_text_element(element: dict[str, Any]) -> bool:
    return element["kind"] == "shape" and element["type"] == "text"


def has_text_content(element: dict[str, Any]) -> bool:
    return bool(element.get("text"))


def is_decorative_text(element: dict[str, Any]) -> bool:
    text = element.get("text") or ""
    return bool(text) and re.search(r"[A-Za-z0-9\u4e00-\u9fff]", text) is None


def normalize_text_for_overlap(text: str) -> str:
    return re.sub(r"\s+", "", text)


def is_similar_text_overlay(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_text = normalize_text_for_overlap(left.get("text") or "")
    right_text = normalize_text_for_overlap(right.get("text") or "")
    if not left_text or not right_text:
        return False
    if left_text == right_text or left_text in right_text or right_text in left_text:
        return True
    return SequenceMatcher(None, left_text, right_text).ratio() >= 0.75


def estimate_text_line_count(element: dict[str, Any]) -> int:
    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    chars_per_line = max(1, int(element["width"] // max(font_size * 0.55, 1)))
    paragraphs = [paragraph for paragraph in re.split(r"\n+", element["text"]) if paragraph]
    line_count = 0
    for paragraph in paragraphs:
        logical_length = max(len(paragraph), 1)
        line_count += max(1, -(-logical_length // chars_per_line))
    return max(line_count, 1)


def estimate_text_visual_bbox(element: dict[str, Any]) -> dict[str, int | float] | None:
    if not is_text_element(element) or not has_text_content(element) or is_decorative_text(element):
        return None

    font_size = element["fontSize"] if isinstance(element["fontSize"], (int, float)) else 16
    char_width = max(font_size * 0.55, 1)
    line_count = estimate_text_line_count(element)
    visual_width = min(element["width"], max(1, len(element["text"]) * char_width))
    visual_height = min(element["height"], max(1, line_count * font_size * 1.2))
    return {
        "x": element["x"],
        "y": element["y"],
        "width": visual_width,
        "height": visual_height,
    }


def intersection_area(left: dict[str, Any], right: dict[str, Any]) -> int | float:
    width = min(left["x"] + left["width"], right["x"] + right["width"]) - max(left["x"], right["x"])
    height = min(left["y"] + left["height"], right["y"] + right["height"]) - max(left["y"], right["y"])
    if width <= 0 or height <= 0:
        return 0
    return width * height


def is_template_text_stack(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if not (is_text_element(left) and is_text_element(right)):
        return False
    if not (has_text_content(left) and has_text_content(right)):
        return True
    top, bottom = sorted([left, right], key=lambda element: element["y"])
    top_type = top.get("textType")
    bottom_type = bottom.get("textType")
    allowed_pairs = {
        ("title", "sub-headline"),
        ("title", None),
        ("headline", "headline"),
        ("headline", None),
    }
    if (top_type, bottom_type) not in allowed_pairs:
        return False
    same_column = abs(top["x"] - bottom["x"]) <= 4
    vertical_offset = bottom["y"] - top["y"]
    top_font_size = float(top.get("fontSize", 16))
    return same_column and vertical_offset >= top_font_size * 0.75


def should_flag_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if is_text_element(left) and not has_text_content(left):
        return False
    if is_text_element(right) and not has_text_content(right):
        return False
    if is_template_text_stack(left, right):
        return False
    if is_text_element(left) and is_text_element(right):
        if is_similar_text_overlay(left, right):
            return False
        left_visual = estimate_text_visual_bbox(left)
        right_visual = estimate_text_visual_bbox(right)
        if left_visual is None or right_visual is None:
            return False
        overlap_area = intersection_area(left_visual, right_visual)
        if overlap_area <= 0:
            return False
        smaller_area = min(
            left_visual["width"] * left_visual["height"],
            right_visual["width"] * right_visual["height"],
        )
        return smaller_area > 0 and overlap_area / smaller_area >= 0.30
    return False


def estimate_text_width(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        if re.match(r"[\u4e00-\u9fff]", char):
            width += font_size
        elif char.isspace():
            width += font_size * 0.32
        else:
            width += font_size * 0.55
    return width


def estimated_rendered_line_count(element: dict[str, Any]) -> int:
    return len(estimate_rendered_lines(element))


def estimate_rendered_lines(element: dict[str, Any]) -> list[str]:
    lines = [line for line in element.get("lines", []) if line]
    if not lines:
        return []
    font_size = float(element.get("fontSize") or 16)
    usable_width = max(float(element["width"]) - 6, 1)
    rendered_lines: list[str] = []
    for line in lines:
        current = ""
        current_width = 0.0
        for char in line:
            char_width = estimate_text_width(char, font_size)
            if current and current_width + char_width > usable_width:
                rendered_lines.append(current)
                current = char
                current_width = char_width
                continue
            current += char
            current_width += char_width
        if current:
            rendered_lines.append(current)
    return rendered_lines


def has_insufficient_height_for_estimated_wrap(element: dict[str, Any], estimated_line_count: int) -> bool:
    if estimated_line_count < 2:
        return False
    font_size = float(element.get("fontSize") or 16)
    required_height = estimated_line_count * font_size * 1.12
    return float(element["height"]) < required_height


def has_too_short_text_box(element: dict[str, Any]) -> bool:
    text = element.get("text") or ""
    if chinese_char_count(text) < 6:
        return False
    font_size = float(element.get("fontSize") or 16)
    return float(element["height"]) < font_size * 0.95


def is_slash_separated_short_label(text: str) -> bool:
    if "/" not in text:
        return False
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if len(parts) < 2:
        return False
    return chinese_char_count(text) <= 14 and all(chinese_char_count(part) <= 4 for part in parts)


def is_short_display_text_auto_wrapped(element: dict[str, Any], rendered_lines: list[str]) -> bool:
    if len(element.get("lines", [])) != 1 or len(rendered_lines) != 2:
        return False
    if element.get("textType") in {"title", "caption"}:
        return False
    text = element.get("text") or ""
    chinese_count = chinese_char_count(text)
    if not (4 <= chinese_count <= 20):
        return False
    font_size = float(element.get("fontSize") or 16)
    if font_size < 20:
        return False
    if not has_insufficient_height_for_estimated_wrap(element, len(rendered_lines)):
        return False
    return chinese_count / max(len(text), 1) >= 0.6


def build_wrap_issue(
    code: str,
    element: dict[str, Any],
    message: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "level": "warning",
        "code": code,
        "element": element["id"],
        "message": message,
        "reason": reason,
        "repair": {
            "prefer_single_line": True,
            "allow_font_shrink": True,
            "max_shrink_ratio": 0.9,
            "avoid_center_align": True,
        },
    }


def is_probable_cover_center_title(element: dict[str, Any]) -> bool:
    text_type = element.get("textType")
    if text_type == "quote":
        return True
    if text_type not in CENTER_ALLOWED_TEXT_TYPES:
        return False
    return element["x"] >= 120 and element["y"] >= 150 and element["width"] >= 300 and element["height"] >= 80


def lint_wrap_quality(element: dict[str, Any]) -> list[dict[str, Any]]:
    if not is_text_element(element) or not has_text_content(element):
        return []

    lines = [line for line in element.get("lines", []) if line]
    rendered_lines = estimate_rendered_lines(element)
    estimated_line_count = len(rendered_lines)
    if len(lines) < 2 and estimated_line_count < 2 and not has_too_short_text_box(element):
        return []

    issues: list[dict[str, Any]] = []
    raw_text = element.get("rawText") or "\n".join(lines)
    joined_chinese = chinese_text("".join(lines))
    joined_chinese_count = chinese_char_count(joined_chinese)
    font_size = float(element.get("fontSize") or 16)

    last_line_chinese_count = chinese_char_count(lines[-1])
    previous_text_chinese_count = chinese_char_count("".join(lines[:-1]))
    if (
        len(lines) == 2
        and 1 <= last_line_chinese_count <= 3
        and previous_text_chinese_count >= 10
    ):
        issues.append(
            build_wrap_issue(
                "text_orphan_line",
                element,
                f"Last line is very short: {lines[-1]}",
                "最后一行是过短尾行",
            )
        )

    if has_too_short_text_box(element):
        issues.append(
            build_wrap_issue(
                "text_box_too_short",
                element,
                f"Text box height is too short for font size: height={element['height']}, fontSize={font_size:g}",
                "文本框高度低于字号所需高度，渲染后容易截断或压缩显示",
            )
        )

    text_type = element.get("textType")
    estimated_single_line_width = joined_chinese_count * font_size * 0.62
    if (
        text_type in TITLE_LIKE_TEXT_TYPES
        and len(lines) >= 2
        and 1 <= joined_chinese_count <= 20
        and font_size >= 20
        and font_size < 40
        and chinese_char_count("".join(lines)) == len("".join(lines))
        and element["width"] >= estimated_single_line_width
    ):
        issues.append(
            build_wrap_issue(
                "text_unnecessary_wrap",
                element,
                f"Short title-like text wraps unnecessarily: {joined_chinese}",
                "短标题或强调文本不超过 20 个中文字符却出现换行",
            )
        )

    if is_short_display_text_auto_wrapped(element, rendered_lines):
        issues.append(
            build_wrap_issue(
                "text_unnecessary_wrap",
                element,
                f"Short display text is likely to wrap in a one-line box: {strip_xml(raw_text)}",
                "短展示文本被放入过窄且只够一行高度的文本框，渲染后容易异常换行",
            )
        )

    if (
        (element.get("textAlign") or "").lower() == "center"
        and (
            (len(lines) >= 2 and font_size >= 22)
            or (
                len(lines) == 1
                and joined_chinese_count >= 8
                and has_insufficient_height_for_estimated_wrap(element, estimated_line_count)
            )
        )
        and text_type not in {"title", "sub-headline", "quote", "hero"}
        and not is_probable_cover_center_title(element)
        and not is_slash_separated_short_label(raw_text)
    ):
        issues.append(
            build_wrap_issue(
                "text_center_wrapped",
                element,
                f"Centered multi-line text is hard to scan: {strip_xml(raw_text)}",
                "非封面、非金句场景的多行文本使用居中对齐",
            )
        )

    return issues


def lint_slide(slide_xml: str, slide_number: int) -> dict[str, Any]:
    elements = extract_elements(slide_xml)
    issues: list[dict[str, Any]] = []

    for element in elements:
        issues.extend(lint_wrap_quality(element))

    for index, left in enumerate(elements):
        for right in elements[index + 1 :]:
            if not intersects(left, right) or not should_flag_overlap(left, right):
                continue
            issues.append(
                {
                    "level": "error",
                    "code": "bbox_overlap",
                    "elements": [left["id"], right["id"]],
                    "message": f'{left["id"]} overlaps {right["id"]}',
                }
            )

    return {"slide_number": slide_number, "element_count": len(elements), "issues": issues}


def lint_xml(xml: str, source_path: str | None = None) -> dict[str, Any]:
    xml_error = validate_xml_well_formed(xml)
    if xml_error:
        return {
            "file": source_path,
            "slide_size": {"width": 960, "height": 540},
            "summary": {"slide_count": 0, "error_count": 1, "warning_count": 0},
            "issues": [xml_error],
            "slides": [],
        }

    presentation = parse_presentation(xml)
    slides = [
        lint_slide(slide_xml, index + 1)
        for index, slide_xml in enumerate(presentation["slides"])
    ]
    error_count = sum(1 for slide in slides for issue in slide["issues"] if issue["level"] == "error")
    warning_count = sum(1 for slide in slides for issue in slide["issues"] if issue["level"] == "warning")
    return {
        "file": source_path,
        "slide_size": {"width": presentation["width"], "height": presentation["height"]},
        "summary": {"slide_count": len(slides), "error_count": error_count, "warning_count": warning_count},
        "slides": slides,
    }


def print_usage() -> None:
    print("Usage:\n  python3 xml_text_overlap_lint.py --input <presentation.xml>", file=sys.stderr)


def run_cli(argv: list[str] | None = None) -> None:
    options = parse_args(argv or sys.argv[1:])
    if options.get("help") or options.get("--help"):
        print_usage()
        raise SystemExit(0)
    if not options.get("input"):
        print_usage()
        fail("--input is required")
    input_path = Path(options["input"]).resolve()
    result = lint_xml(read_file(input_path), str(input_path))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["summary"]["error_count"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        run_cli()
    except XmlTextOverlapLintError as error:
        print(f"xml-text-overlap-lint error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
