#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import svglide_schema


INPUT_PATH = Path("05-preview/preview-annotations.json")
OUTPUT_PATH = Path("06-check/preview-annotations-review.json")
REPAIR_LIST_PATH = Path("06-check/preview-repair-list.json")


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON in {path}: expected object")
    return payload


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def run_preview_annotations(project: Path) -> dict[str, Any]:
    project = project.resolve()
    path = project / INPUT_PATH
    issues: list[dict[str, str]] = []
    payload: dict[str, Any] = {"schema_version": "svglide-preview-annotations/v1", "annotations": []}
    if path.exists():
        payload = read_json_object(path)
        schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-preview-annotations.schema.json"))
        issues.extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in svglide_schema.validate_json_schema(payload, schema))
    annotations = payload.get("annotations") if isinstance(payload.get("annotations"), list) else []
    open_items = [
        item for item in annotations
        if isinstance(item, dict) and item.get("status", "open") == "open" and item.get("severity") in {"warning", "error"}
    ]
    result = {
        "schema_version": "svglide-preview-annotations-review/v1",
        "status": "failed" if issues else "passed",
        "input": INPUT_PATH.as_posix() if path.exists() else None,
        "repair_list": REPAIR_LIST_PATH.as_posix(),
        "summary": {
            "error_count": len(issues),
            "annotation_count": len(annotations),
            "open_repair_count": len(open_items),
        },
        "issues": issues,
    }
    repair = {"schema_version": "svglide-preview-repair-list/v1", "items": open_items}
    for output, data in [(project / OUTPUT_PATH, result), (project / REPAIR_LIST_PATH, repair)]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate preview annotations and write a repair list.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_preview_annotations(Path(args.project))
    except (OSError, ValueError) as error:
        print(f"svglide_preview_annotations: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
