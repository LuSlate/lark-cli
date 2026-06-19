#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


PLAN_PATH = Path("02-plan/slide_plan.json")
OUTPUT_PATH = Path("06-check/semantic-advisory.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def warning(code: str, message: str, *, page: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    return payload


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON in {path}: expected object")
    return payload


def list_of_strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def run_advisory(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan = read_json_object(project / PLAN_PATH)
    warnings: list[dict[str, Any]] = []
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            continue
        page = slide.get("page") if isinstance(slide.get("page"), int) else index
        title = slide.get("title")
        key_message = slide.get("key_message")
        body_points = list_of_strings(slide.get("body_points") or slide.get("bullets"))
        if isinstance(key_message, str) and len(key_message.strip()) < 8:
            warnings.append(warning("key_message_may_be_weak", "key_message is very short; review insight strength", page=page))
        if title == key_message:
            warnings.append(warning("title_repeats_key_message", "title and key_message are identical; review narrative hierarchy", page=page))
        if slide.get("page_type") == "content" and body_points and all(len(point.strip()) < 10 for point in body_points):
            warnings.append(warning("body_points_may_lack_detail", "content body_points are short; review evidence thickness", page=page))
    result: dict[str, Any] = {
        "schema_version": "svglide-semantic-advisory/v1",
        "status": "passed",
        "generated_at": now_iso(),
        "summary": {"warning_count": len(warnings), "slide_count": len(slides)},
        "warnings": warnings,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-semantic-advisory.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["warnings"].extend(warning(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues)
        result["summary"]["warning_count"] = len(result["warnings"])
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate non-blocking semantic advisory warnings for SVGlide.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_advisory(Path(args.project))
    except (OSError, ValueError) as error:
        print(f"svglide_semantic_advisory: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
