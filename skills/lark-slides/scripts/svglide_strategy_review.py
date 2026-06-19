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
OUTPUT_PATH = Path("02-plan/strategy-review.json")
ALLOWED_PAGE_TYPES = {"cover", "section", "content", "closing"}


class StrategyReviewError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StrategyReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StrategyReviewError(f"invalid JSON in {path}: expected object")
    return payload


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path is not None:
        payload["path"] = path
    return payload


def require_chinese(value: Any, code: str, message: str, *, page: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, str) or not value.strip() or not any("\u3400" <= char <= "\u9fff" for char in value):
        return [issue(code, message, page=page)]
    return []


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def run_strategy_review(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan_path = project / PLAN_PATH
    if not plan_path.exists():
        raise StrategyReviewError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_path)
    issues: list[dict[str, Any]] = []

    if plan.get("language") != "zh-CN":
        issues.append(issue("language_not_zh_cn", "slide_plan.language must be zh-CN"))
    if not isinstance(plan.get("audience"), str) or not plan.get("audience", "").strip():
        issues.append(issue("audience_missing", "slide_plan.audience must be a non-empty string"))
    deck_structure = plan.get("deck_structure")
    if not isinstance(deck_structure, list) or not all(isinstance(item, str) for item in deck_structure):
        issues.append(issue("deck_structure_missing", "slide_plan.deck_structure must be a string array"))
        deck_structure = []
    else:
        for page_type in sorted({"cover", "content", "closing"} - set(deck_structure)):
            issues.append(issue("deck_structure_missing_page_type", f"deck_structure must include {page_type}"))

    slides = plan.get("slides")
    slide_receipts: list[dict[str, Any]] = []
    if not isinstance(slides, list) or not slides:
        issues.append(issue("slides_missing", "slide_plan.slides must be a non-empty array"))
        slides = []
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict):
            issues.append(issue("slide_not_object", "slide item must be an object", page=index))
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        page_type = raw_slide.get("page_type")
        body_points = list_of_strings(raw_slide.get("body_points") or raw_slide.get("bullets"))
        source_refs = list_of_strings(raw_slide.get("source_refs") or raw_slide.get("sources"))
        if page_type not in ALLOWED_PAGE_TYPES:
            issues.append(issue("slide_page_type_missing", "slide.page_type must be cover, section, content, or closing", page=page))
        if not isinstance(raw_slide.get("section"), str) or not raw_slide.get("section", "").strip():
            issues.append(issue("slide_section_missing", "slide.section must be a non-empty string", page=page))
        if not isinstance(raw_slide.get("role"), str) or not raw_slide.get("role", "").strip():
            issues.append(issue("slide_role_missing", "slide.role must be a non-empty string", page=page))
        issues.extend(require_chinese(raw_slide.get("title"), "slide_title_not_chinese", "slide.title must be Chinese text", page=page))
        issues.extend(require_chinese(raw_slide.get("key_message"), "slide_key_message_not_chinese", "slide.key_message must be Chinese text", page=page))
        if page_type == "content":
            if len(body_points) < 2:
                issues.append(issue("content_body_points_too_few", "content slides require at least 2 body_points", page=page))
            if not source_refs:
                issues.append(issue("content_source_refs_missing", "content slides require source_refs", page=page))
        slide_receipts.append(
            {
                "page": page,
                "page_type": page_type,
                "section": raw_slide.get("section"),
                "role": raw_slide.get("role"),
                "title": raw_slide.get("title"),
                "key_message": raw_slide.get("key_message"),
                "body_points": body_points,
                "source_refs": source_refs,
            }
        )

    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-strategy-review/v1",
        "status": status,
        "language": plan.get("language"),
        "audience": plan.get("audience"),
        "deck_structure": deck_structure,
        "slides": slide_receipts,
        "summary": {"error_count": len(issues), "warning_count": 0},
        "issues": issues,
        "generated_at": now_iso(),
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-strategy-review.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["issues"].extend(issue(item["code"], item["message"], path=item["path"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])

    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SVGlide strategy fields before confirmation and generation.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_strategy_review(Path(args.project))
    except (OSError, StrategyReviewError) as error:
        print(f"svglide_strategy_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
