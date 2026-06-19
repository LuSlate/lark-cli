#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


PLAN_PATH = Path("02-plan/slide_plan.json")
PROJECT_REGISTRY_PATH = Path("02-plan/renderer-registry.json")
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "svglide-renderer-registry.json"
OUTPUT_PATH = Path("06-check/runtime-review.json")
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"


class RuntimeReviewError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeReviewError(f"invalid JSON in {path}: expected object")
    return payload


def issue(code: str, message: str, *, page: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    return payload


def registry_path_for(project: Path) -> Path:
    project_registry = project / PROJECT_REGISTRY_PATH
    return project_registry if project_registry.exists() else DEFAULT_REGISTRY_PATH


def load_registry(project: Path) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    path = registry_path_for(project)
    registry = read_json_object(path)
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-renderer-registry.schema.json"))
    issues = [issue(item["code"], f"{item['path']}: {item['message']}") for item in svglide_schema.validate_json_schema(registry, schema)]
    by_id: dict[str, dict[str, Any]] = {}
    renderers = registry.get("renderers")
    if isinstance(renderers, list):
        for item in renderers:
            if not isinstance(item, dict):
                continue
            renderer_id = item.get("id")
            if isinstance(renderer_id, str):
                if renderer_id in by_id:
                    issues.append(issue("renderer_registry_duplicate_id", f"duplicate renderer id: {renderer_id}"))
                by_id[renderer_id] = item
    return path, registry, by_id, issues


def style_preset_allowed(style_preset: Any, renderer: dict[str, Any]) -> bool:
    allowed = renderer.get("allowed_style_presets")
    if not isinstance(allowed, list) or "*" in allowed:
        return True
    if not isinstance(style_preset, str) or not style_preset:
        return True
    return style_preset in allowed


def run_runtime_review(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan_file = project / PLAN_PATH
    if not plan_file.exists():
        raise RuntimeReviewError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_file)
    registry_path, _registry, registry, issues = load_registry(project)
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    renderers: list[str] = []
    families: list[str] = []
    pages: list[dict[str, Any]] = []
    style_preset = plan.get("style_preset")
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict):
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        renderer = raw_slide.get("renderer_id")
        family = raw_slide.get("layout_family")
        renderer_record = registry.get(renderer) if isinstance(renderer, str) else None
        page_status = "passed"
        if not isinstance(renderer, str) or not renderer.strip():
            issues.append(issue("renderer_id_missing", "each slide must declare renderer_id", page=page))
            page_status = "failed"
        else:
            renderers.append(renderer)
            if renderer_record is None:
                issues.append(issue("renderer_unknown", f"renderer_id is not present in registry: {renderer}", page=page))
                page_status = "failed"
            else:
                status = renderer_record.get("status")
                if status != "active":
                    issues.append(issue("renderer_not_active", f"renderer_id {renderer} status is {status}", page=page))
                    page_status = "failed"
                if not style_preset_allowed(style_preset, renderer_record):
                    issues.append(issue("renderer_style_preset_not_allowed", f"renderer_id {renderer} does not allow style_preset {style_preset}", page=page))
                    page_status = "failed"
        if not isinstance(family, str) or not family.strip():
            issues.append(issue("layout_family_missing", "each slide must declare layout_family", page=page))
            page_status = "failed"
        else:
            families.append(family)
            if isinstance(renderer_record, dict) and isinstance(renderer_record.get("family"), str) and family != renderer_record.get("family"):
                issues.append(issue("renderer_family_mismatch", f"layout_family {family} does not match registry family {renderer_record.get('family')}", page=page))
                page_status = "failed"
        pages.append(
            {
                "page": page,
                "renderer_id": renderer,
                "registry_status": renderer_record.get("status") if isinstance(renderer_record, dict) else "unknown",
                "layout_family": family,
                "registry_family": renderer_record.get("family") if isinstance(renderer_record, dict) else None,
                "status": page_status,
            }
        )
    renderer_count = len(set(renderers))
    family_count = len(set(families))
    if len(slides) >= 4 and renderer_count <= 1:
        issues.append(issue("renderer_monoculture", "decks with at least 4 slides need more than one renderer_id"))
    if len(slides) >= 4 and family_count <= 1:
        issues.append(issue("layout_family_monoculture", "decks with at least 4 slides need more than one layout_family"))
    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-runtime-review/v1",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": file_sha256(plan_file),
            "style_preset": style_preset,
        },
        "registry": {
            "path": str(registry_path if registry_path.is_absolute() else registry_path.as_posix()),
            "sha256": file_sha256(registry_path),
        },
        "pages": pages,
        "renderers": sorted(set(renderers)),
        "layout_families": sorted(set(families)),
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "slide_count": len(slides),
            "renderer_count": renderer_count,
            "layout_family_count": family_count,
        },
        "issues": issues,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-runtime-review.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["action"] = FAIL_ACTION
        result["issues"].extend(issue(item["code"], item["message"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review SVGlide runtime renderer and visual diversity contracts.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_runtime_review(Path(args.project))
    except (OSError, RuntimeReviewError) as error:
        print(f"svglide_runtime_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
