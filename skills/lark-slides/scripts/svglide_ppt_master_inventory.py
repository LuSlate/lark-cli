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


INPUT_PATH = Path("source/ppt-master-asset-map.json")
OUTPUT_PATH = Path("06-check/ppt-master-inventory.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(code: str, message: str, *, index: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if index is not None:
        payload["index"] = index
    return payload


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON in {path}: expected object")
    return payload


def run_inventory(project: Path) -> dict[str, Any]:
    project = project.resolve()
    path = project / INPUT_PATH
    warnings: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    payload: dict[str, Any] = {"schema_version": "svglide-ppt-master-asset-map/v1", "items": []}
    if path.exists():
        payload = read_json_object(path)
        schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-ppt-master-asset-map.schema.json"))
        issues.extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in svglide_schema.validate_json_schema(payload, schema))
    else:
        warnings.append(issue("asset_map_missing", "source/ppt-master-asset-map.json is not present; inventory is empty"))
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        if item.get("activation_status") == "active":
            if item.get("copy_policy") != "svglide_native":
                issues.append(issue("active_asset_copy_policy_invalid", "active migrated assets must use svglide_native copy_policy", index=index))
            if item.get("license_status") != "cleared":
                issues.append(issue("active_asset_license_not_cleared", "active migrated assets require cleared license_status", index=index))
        if item.get("copy_policy") == "blocked_raw_runtime" and item.get("activation_status") == "active":
            issues.append(issue("raw_runtime_asset_active", "raw ppt-master runtime assets cannot be active CLI runtime dependencies", index=index))
    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-ppt-master-inventory/v1",
        "status": status,
        "generated_at": now_iso(),
        "input": INPUT_PATH.as_posix() if path.exists() else None,
        "summary": {
            "error_count": len(issues),
            "warning_count": len(warnings),
            "asset_count": len(items),
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
    parser = argparse.ArgumentParser(description="Validate ppt-master asset inventory for SVGlide migration.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_inventory(Path(args.project))
    except (OSError, ValueError) as error:
        print(f"svglide_ppt_master_inventory: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
