#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import svglide_theme


SCHEMA_VERSION = "svglide-theme-adherence/v1"
STAGE = "theme_adherence"
PLAN_PATH = Path("02-plan/slide_plan.json")
THEME_VALIDATE_PATH = Path("06-check/theme-validate.json")
CHECK_PATH = Path("06-check/theme-adherence.json")
RECEIPT_PATH = Path("receipts/theme-adherence.json")
PREPARED_DIR = Path("04-svg/prepared")


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path is not None:
        payload["path"] = path
    return payload


def svg_files(project_root: Path) -> list[Path]:
    svg_dir = project_root / PREPARED_DIR
    if not svg_dir.exists():
        return []
    return [path for path in sorted(svg_dir.glob("*.svg")) if path.is_file()]


def style_value(style: str, key: str) -> str | None:
    for item in style.split(";"):
        if ":" not in item:
            continue
        name, value = item.split(":", 1)
        if name.strip().lower() == key:
            return value.strip()
    return None


def first_hex(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])", value)
    return svglide_theme.normalize_hex_color(match.group(0)) if match else None


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1] if "}" in name else name


def element_text_color(element: ElementTree.Element) -> str | None:
    style = element.attrib.get("style")
    for raw in (
        element.attrib.get("color"),
        element.attrib.get("fill"),
        style_value(style or "", "color"),
        style_value(style or "", "fill"),
    ):
        color = first_hex(raw)
        if color:
            return color
    return None


def svg_text_colors(svg_path: Path) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    for element in root.iter():
        if local_name(element.tag).lower() not in {"text", "foreignobject"}:
            continue
        text = "".join(element.itertext()).strip()
        items.append({"tag": local_name(element.tag), "text": text, "color": element_text_color(element)})
    return items


def page_theme_id(validate_receipt: dict[str, Any], page_index: int) -> str | None:
    pages = validate_receipt.get("pages")
    if not isinstance(pages, list):
        return None
    for item in pages:
        if not isinstance(item, dict):
            continue
        if item.get("page") == page_index and isinstance(item.get("theme_id"), str):
            return item["theme_id"]
    if 1 <= page_index <= len(pages):
        item = pages[page_index - 1]
        if isinstance(item, dict) and isinstance(item.get("theme_id"), str):
            return item["theme_id"]
    return None


def validate_project(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    issues: list[dict[str, Any]] = []
    page_results: list[dict[str, Any]] = []
    unknown_colors: list[dict[str, Any]] = []
    contrast_unresolved: list[dict[str, Any]] = []
    contrast_failures: list[dict[str, Any]] = []

    plan_file = project_root / PLAN_PATH
    validate_file = project_root / THEME_VALIDATE_PATH
    validate_receipt: dict[str, Any] = {}
    try:
        read_json(plan_file)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        issues.append(issue("plan_invalid", f"could not read {PLAN_PATH.as_posix()}: {err}", path=PLAN_PATH.as_posix()))
    try:
        validate_receipt = read_json(validate_file)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        issues.append(issue("theme_validate_invalid", f"could not read {THEME_VALIDATE_PATH.as_posix()}: {err}", path=THEME_VALIDATE_PATH.as_posix()))
    if validate_receipt and validate_receipt.get("status") != "passed":
        issues.append(issue("theme_validate_not_passed", "theme_validate receipt must be passed", path=THEME_VALIDATE_PATH.as_posix()))
    inputs = validate_receipt.get("inputs") if isinstance(validate_receipt.get("inputs"), dict) else {}
    if validate_receipt and inputs.get("plan_sha256") != (svglide_theme.file_sha256(plan_file) if plan_file.exists() else None):
        issues.append(issue("theme_validate_plan_stale", "theme_validate plan_sha256 does not match current slide_plan.json", path=THEME_VALIDATE_PATH.as_posix()))

    prepared_files = svg_files(project_root)
    if not prepared_files:
        issues.append(issue("prepared_svg_missing", "theme_adherence requires 04-svg/prepared/*.svg", path=PREPARED_DIR.as_posix()))

    for index, svg_path in enumerate(prepared_files, start=1):
        rel = svg_path.relative_to(project_root).as_posix()
        page_issues: list[dict[str, Any]] = []
        theme_id = page_theme_id(validate_receipt, index)
        theme: dict[str, Any] | None = None
        if not theme_id:
            page_issues.append(issue("theme_id_missing", "theme_validate receipt must include page theme_id", page=index, path=rel))
        else:
            try:
                theme = svglide_theme.load_theme(theme_id, project_root)
            except (OSError, svglide_theme.ThemeError, json.JSONDecodeError) as err:
                page_issues.append(issue("theme_load_failed", str(err), page=index, path=rel))
        if theme:
            try:
                colors = svglide_theme.extract_svg_colors(svg_path)
            except svglide_theme.ThemeError as err:
                page_issues.append(issue("svg_color_extract_failed", str(err), page=index, path=rel))
                colors = []
            for color in colors:
                classified = svglide_theme.classify_color(color, theme)
                if classified["kind"] == "unknown":
                    entry = {"page": index, "path": rel, "color": color}
                    unknown_colors.append(entry)
                    page_issues.append(issue("theme_unknown_color", f"color {color} is not allowed by theme {theme_id}", page=index, path=rel))
            try:
                text_items = svg_text_colors(svg_path)
            except (OSError, ElementTree.ParseError, svglide_theme.ThemeError) as err:
                page_issues.append(issue("svg_text_parse_failed", str(err), page=index, path=rel))
                text_items = []
            background = theme.get("colors", {}).get("background") if isinstance(theme.get("colors"), dict) else None
            min_ratio = theme.get("contrast", {}).get("min_text_contrast") if isinstance(theme.get("contrast"), dict) else 4.5
            for text_index, item in enumerate(text_items):
                color = item.get("color")
                if not color or not isinstance(background, str):
                    entry = {"page": index, "path": rel, "text_index": text_index, "reason": "text_or_background_color_unresolved"}
                    contrast_unresolved.append(entry)
                    page_issues.append(issue("contrast_unresolved", "text and background colors must be directly inferable in P0", page=index, path=rel))
                    continue
                ratio = svglide_theme.contrast_ratio(color, background)
                if ratio < float(min_ratio):
                    entry = {"page": index, "path": rel, "text_index": text_index, "ratio": round(ratio, 4), "min": min_ratio}
                    contrast_failures.append(entry)
                    page_issues.append(issue("contrast_too_low", f"text contrast {ratio:.2f} is below {min_ratio}", page=index, path=rel))
        page_results.append(
            {
                "page": index,
                "path": rel,
                "theme_id": theme_id,
                "sha256": svglide_theme.file_sha256(svg_path),
                "status": "passed" if not page_issues else "failed",
                "issues": page_issues,
            }
        )
        issues.extend(page_issues)

    status = "passed" if not issues else "failed"
    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "action": "create_live" if status == "passed" else "repair_and_rerun",
        "checked_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": svglide_theme.file_sha256(plan_file) if plan_file.exists() else None,
            "theme_validate": THEME_VALIDATE_PATH.as_posix(),
            "theme_validate_sha256": svglide_theme.file_sha256(validate_file) if validate_file.exists() else None,
        },
        "prepared_files": svglide_theme.prepared_svg_hashes(project_root),
        "pages": page_results,
        "unknown_colors": unknown_colors,
        "contrast_unresolved": contrast_unresolved,
        "contrast_failures": contrast_failures,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "prepared_svg_count": len(prepared_files),
            "unknown_color_count": len(unknown_colors),
            "contrast_unresolved_count": len(contrast_unresolved),
        },
        "issues": issues,
        "output_path": CHECK_PATH.as_posix(),
    }
    return result


def write_outputs(project_root: Path, result: dict[str, Any]) -> None:
    write_json(project_root / CHECK_PATH, result)
    write_json(project_root / RECEIPT_PATH, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate final prepared SVG adherence to ThemeSpec.")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    if not args.project_root.exists() or not args.project_root.is_dir():
        print(f"svglide_theme_adherence: project_root does not exist: {args.project_root}", file=sys.stderr)
        return 2
    try:
        result = validate_project(args.project_root)
        write_outputs(args.project_root, result)
    except OSError as err:
        print(f"svglide_theme_adherence: {err}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
