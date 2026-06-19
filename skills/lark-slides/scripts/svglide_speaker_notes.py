#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


PLAN_PATH = Path("02-plan/slide_plan.json")
NOTES_DIR = Path("notes")
TOTAL_NOTES = NOTES_DIR / "total.md"
REVIEW_PATH = NOTES_DIR / "notes-review.json"
DELIMITER_RE = re.compile(r"^\s*---+\s*$", re.MULTILINE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON in {path}: expected object")
    return payload


def expected_page_count(project: Path) -> int | None:
    path = project / PLAN_PATH
    if not path.exists():
        return None
    plan = read_json_object(path)
    slides = plan.get("slides")
    if isinstance(slides, list):
        return len(slides)
    page_count = plan.get("page_count")
    return page_count if isinstance(page_count, int) else None


def split_total_notes(project: Path) -> list[Path]:
    total = project / TOTAL_NOTES
    if not total.exists():
        return sorted((project / NOTES_DIR).glob("page-*.md"))
    chunks = [chunk.strip() for chunk in DELIMITER_RE.split(total.read_text(encoding="utf-8")) if chunk.strip()]
    paths: list[Path] = []
    for index, chunk in enumerate(chunks, 1):
        path = project / NOTES_DIR / f"page-{index:03d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(chunk + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def run_speaker_notes(project: Path) -> dict[str, Any]:
    project = project.resolve()
    expected = expected_page_count(project)
    pages = split_total_notes(project)
    issues: list[dict[str, str]] = []
    if expected is not None and len(pages) != expected:
        issues.append(issue("notes_page_count_mismatch", "notes page count must match slide count"))
    for path in pages:
        if not path.read_text(encoding="utf-8").strip():
            issues.append(issue("notes_page_empty", f"speaker note is empty: {path.name}"))
    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-speaker-notes/v1",
        "status": status,
        "generated_at": now_iso(),
        "notes": [path.relative_to(project).as_posix() for path in pages],
        "summary": {"error_count": len(issues), "expected_page_count": expected, "notes_page_count": len(pages)},
        "issues": issues,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-speaker-notes.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["issues"].extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])
    output = project / REVIEW_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split and validate SVGlide speaker notes.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_speaker_notes(Path(args.project))
    except (OSError, ValueError) as error:
        print(f"svglide_speaker_notes: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
