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


INPUT_PATH = Path("source/template-admission.json")
OUTPUT_PATH = Path("06-check/template-admission.json")
RAW_RUNTIME_EXTENSIONS = {".pptx", ".potx", ".key", ".svg", ".xml"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(code: str, message: str, *, item_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if item_id is not None:
        payload["id"] = item_id
    return payload


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON in {path}: expected object")
    return payload


def non_empty_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def raw_runtime_source(source: str) -> bool:
    suffix = Path(source).suffix.lower()
    if suffix in RAW_RUNTIME_EXTENSIONS:
        return True
    lowered = source.lower()
    return any(token in lowered for token in ["raw-runtime", "runtime-asset", "pptx"])


def run_template_admission(project: Path) -> dict[str, Any]:
    project = project.resolve()
    path = project / INPUT_PATH
    warnings: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    payload: dict[str, Any] = {"schema_version": "svglide-template-admission/v1", "items": []}
    if path.exists():
        payload = read_json_object(path)
        schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-template-admission.schema.json"))
        issues.extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in svglide_schema.validate_json_schema(payload, schema))
    else:
        warnings.append(issue("template_admission_missing", "source/template-admission.json is not present; no external seed/template is active"))
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id") if isinstance(item.get("id"), str) else "<unknown>"
        if item_id in seen:
            issues.append(issue("template_admission_duplicate_id", f"duplicate admission id: {item_id}", item_id=item_id))
        seen.add(item_id)
        source = item.get("source") if isinstance(item.get("source"), str) else ""
        active = item.get("activation_status") == "active"
        if active:
            if item.get("copy_policy") != "svglide_native":
                issues.append(issue("active_template_copy_policy_invalid", "active template/seed must be svglide_native", item_id=item_id))
            if item.get("license_status") != "cleared":
                issues.append(issue("active_template_license_not_cleared", "active template/seed requires cleared license_status", item_id=item_id))
            if not non_empty_object(item.get("compatibility")):
                issues.append(issue("active_template_compatibility_missing", "active template/seed requires compatibility proof", item_id=item_id))
            if not non_empty_object(item.get("usage_proof")):
                issues.append(issue("active_template_usage_proof_missing", "active template/seed requires usage proof", item_id=item_id))
            if raw_runtime_source(source):
                issues.append(issue("active_template_raw_runtime_source", "raw PPTX/XML/SVG runtime assets cannot be active SVGlide runtime templates", item_id=item_id))
    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-template-admission-review/v1",
        "status": status,
        "generated_at": now_iso(),
        "input": INPUT_PATH.as_posix() if path.exists() else None,
        "summary": {
            "error_count": len(issues),
            "warning_count": len(warnings),
            "item_count": len(items),
            "active_count": sum(1 for item in items if isinstance(item, dict) and item.get("activation_status") == "active"),
        },
        "issues": issues,
        "warnings": warnings,
        "items": items,
    }
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SVGlide seed/template admission.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_template_admission(Path(args.project))
    except (OSError, ValueError) as error:
        print(f"svglide_template_admission: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
