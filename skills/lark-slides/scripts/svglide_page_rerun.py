#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import svglide_schema


PREPARED_DIR = Path("04-svg/prepared")
QUALITY_GATE = Path("06-check/quality-gate.json")
OUTPUT_PATH = Path("receipts/page-rerun.json")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def current_prepared(project: Path) -> list[dict[str, Any]]:
    root = project / PREPARED_DIR
    files = sorted(root.glob("*.svg")) if root.exists() else []
    return [{"page": index, "path": path.relative_to(project).as_posix(), "sha256": file_sha256(path)} for index, path in enumerate(files, 1)]


def previous_hashes(project: Path) -> dict[str, str]:
    path = project / QUALITY_GATE
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    files = payload.get("prepared_files") if isinstance(payload, dict) else None
    if not isinstance(files, list):
        return {}
    return {item.get("path"): item.get("sha256") for item in files if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str)}


def run_page_rerun(project: Path) -> dict[str, Any]:
    project = project.resolve()
    current = current_prepared(project)
    previous = previous_hashes(project)
    pages = []
    for item in current:
        old_hash = previous.get(item["path"])
        status = "dirty" if old_hash != item["sha256"] else "clean"
        pages.append({**item, "previous_sha256": old_hash, "status": status})
    result: dict[str, Any] = {
        "schema_version": "svglide-page-rerun/v1",
        "status": "passed",
        "pages": pages,
        "summary": {
            "page_count": len(pages),
            "dirty_page_count": sum(1 for item in pages if item["status"] == "dirty"),
        },
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-page-rerun.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["issues"] = schema_issues
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize page-level dirty set for SVGlide reruns.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_page_rerun(Path(args.project))
    except OSError as error:
        print(f"svglide_page_rerun: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
