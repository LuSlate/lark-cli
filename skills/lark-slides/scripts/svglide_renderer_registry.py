#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REGISTRY_SCHEMA_VERSION = "svglide-renderer-registry/v1"
ACTIVE_STATUSES = {"active", "candidate", "blocked", "deprecated"}


def script_path() -> Path:
    return Path(__file__).resolve()


def references_dir() -> Path:
    return script_path().parents[1] / "references"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def registry_path(ref_dir: Path | None = None) -> Path:
    return (ref_dir or references_dir()) / "svglide-renderer-registry.json"


def load_registry(ref_dir: Path | None = None) -> dict[str, Any]:
    data = read_json(registry_path(ref_dir))
    if not isinstance(data, dict):
        raise ValueError("renderer registry must contain a JSON object")
    return data


def load_catalog_ids(ref_dir: Path | None = None) -> dict[str, set[str]]:
    root = ref_dir or references_dir()
    seeds = read_json(root / "svg-seeds.json")
    recipes = read_json(root / "svg-recipes.json")
    if not isinstance(seeds, dict) or not isinstance(recipes, dict):
        raise ValueError("seed and recipe catalogs must contain JSON objects")
    seed_ids = set((seeds.get("seeds") or {}).keys()) if isinstance(seeds.get("seeds"), dict) else set()
    recipe_ids = set((recipes.get("recipes") or {}).keys()) if isinstance(recipes.get("recipes"), dict) else set()
    chart_type_ids = (
        set((recipes.get("chart_type_contracts") or {}).keys())
        if isinstance(recipes.get("chart_type_contracts"), dict)
        else set()
    )
    return {"seeds": seed_ids, "recipes": recipe_ids, "chart_types": chart_type_ids}


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def list_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text(item) for item in value if text(item)]


def validate_registry(data: dict[str, Any], catalog_ids: dict[str, set[str]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if data.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        issues.append({"level": "error", "code": "invalid_schema_version"})
    renderers = data.get("renderers")
    if not isinstance(renderers, list) or not renderers:
        issues.append({"level": "error", "code": "missing_renderers"})
        renderers = []

    seen: set[str] = set()
    active_count = 0
    candidate_count = 0
    active_seed_ids: set[str] = set()
    active_recipe_ids: set[str] = set()
    active_page_kinds: set[str] = set()
    for index, item in enumerate(renderers, 1):
        if not isinstance(item, dict):
            issues.append({"level": "error", "code": "renderer_not_object", "index": index})
            continue
        renderer_id = text(item.get("id"))
        status = text(item.get("status")) or "candidate"
        seed_id = text(item.get("layout_seed_id"))
        recipe_id = text(item.get("visual_recipe_id"))
        page_kind = text(item.get("page_kind"))
        if not renderer_id:
            issues.append({"level": "error", "code": "missing_renderer_id", "index": index})
            continue
        if renderer_id in seen:
            issues.append({"level": "error", "code": "duplicate_renderer_id", "renderer_id": renderer_id})
        seen.add(renderer_id)
        if status not in ACTIVE_STATUSES:
            issues.append({"level": "error", "code": "invalid_status", "renderer_id": renderer_id, "status": status})
        if status == "active":
            active_count += 1
            active_seed_ids.add(seed_id)
            active_recipe_ids.add(recipe_id)
            active_page_kinds.add(page_kind)
            required = {
                "page_kind": page_kind,
                "runtime_renderer_family": text(item.get("runtime_renderer_family")),
                "layout_seed_id": seed_id,
                "visual_recipe_id": recipe_id,
            }
            for field, value in required.items():
                if not value:
                    issues.append({"level": "error", "code": f"active_renderer_missing_{field}", "renderer_id": renderer_id})
            if seed_id and seed_id not in catalog_ids["seeds"]:
                issues.append({"level": "error", "code": "unknown_layout_seed", "renderer_id": renderer_id, "layout_seed_id": seed_id})
            if recipe_id and recipe_id not in catalog_ids["recipes"]:
                issues.append({"level": "error", "code": "unknown_visual_recipe", "renderer_id": renderer_id, "visual_recipe_id": recipe_id})
            for chart_type in list_text(item.get("chart_types")):
                if chart_type not in catalog_ids["chart_types"]:
                    issues.append({"level": "error", "code": "unknown_chart_type", "renderer_id": renderer_id, "chart_type": chart_type})
            if not list_text(item.get("style_reskin_hooks")):
                issues.append({"level": "warning", "code": "missing_style_reskin_hooks", "renderer_id": renderer_id})
            if not list_text(item.get("required_primitives")):
                issues.append({"level": "warning", "code": "missing_required_primitives", "renderer_id": renderer_id})
        elif status == "candidate":
            candidate_count += 1

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "status": "passed" if not any(issue["level"] == "error" for issue in issues) else "failed",
        "summary": {
            "renderer_count": len(renderers),
            "active_count": active_count,
            "candidate_count": candidate_count,
            "active_seed_count": len({item for item in active_seed_ids if item}),
            "active_recipe_count": len({item for item in active_recipe_ids if item}),
            "active_page_kind_count": len({item for item in active_page_kinds if item}),
            "error_count": sum(1 for issue in issues if issue["level"] == "error"),
            "warning_count": sum(1 for issue in issues if issue["level"] == "warning"),
        },
        "issues": issues,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the SVGlide renderer registry.")
    parser.add_argument("--references-dir", default="", help="Override references directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ref_dir = Path(args.references_dir).expanduser() if args.references_dir else references_dir()
    report = validate_registry(load_registry(ref_dir), load_catalog_ids(ref_dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(
            "renderer registry: "
            f"{report['status']} "
            f"({summary['active_count']} active, {summary['candidate_count']} candidate, "
            f"{summary['error_count']} errors, {summary['warning_count']} warnings)"
        )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
