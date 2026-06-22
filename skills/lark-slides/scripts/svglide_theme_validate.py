#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_theme


SCHEMA_VERSION = "svglide-theme-validate/v1"
STAGE = "theme_validate"
PLAN_PATH = Path("02-plan/slide_plan.json")
CHECK_PATH = Path("06-check/theme-validate.json")
RECEIPT_PATH = Path("receipts/theme-validate.json")
TEMPLATE_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "svglide-template-registry.json"


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


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return relpath(path, svglide_theme.REPO_ROOT)


def template_records() -> dict[str, dict[str, Any]]:
    payload = read_json(TEMPLATE_REGISTRY_PATH)
    templates = payload.get("templates") if isinstance(payload.get("templates"), list) else []
    return {item["id"]: item for item in templates if isinstance(item, dict) and isinstance(item.get("id"), str)}


def theme_record_paths(registry: dict[str, Any]) -> dict[str, str]:
    themes = registry.get("themes") if isinstance(registry.get("themes"), list) else []
    result: dict[str, str] = {}
    for item in themes:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("path"), str):
            result[item["id"]] = item["path"]
    return result


def theme_records_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    themes = registry.get("themes") if isinstance(registry.get("themes"), list) else []
    return {item["id"]: item for item in themes if isinstance(item, dict) and isinstance(item.get("id"), str)}


def project_theme_allows_template(registry: dict[str, Any], theme_id: str, template_id: str) -> bool:
    record = theme_records_by_id(registry).get(theme_id)
    if not isinstance(record, dict):
        return False
    bindings = record.get("template_bindings")
    if not isinstance(bindings, dict):
        return False
    supported = bindings.get("supported_template_ids")
    return isinstance(supported, list) and template_id in supported


def slide_canvas_spec(slide: dict[str, Any]) -> dict[str, Any]:
    spec = slide.get("canvas_spec")
    return spec if isinstance(spec, dict) else {}


def slide_theme_id(slide: dict[str, Any], plan: dict[str, Any]) -> str | None:
    spec = slide_canvas_spec(slide)
    raw = spec.get("theme_id")
    if isinstance(raw, str) and raw:
        return raw
    theme = spec.get("theme")
    if isinstance(theme, str) and theme:
        return theme
    if isinstance(theme, dict) and isinstance(theme.get("theme_id"), str):
        return theme["theme_id"]
    for key in ("theme_id", "theme"):
        raw_slide = slide.get(key)
        if isinstance(raw_slide, str) and raw_slide:
            return raw_slide
    for key in ("theme_id", "theme"):
        raw_plan = plan.get(key)
        if isinstance(raw_plan, str) and raw_plan:
            return raw_plan
    return None


def slide_template_id(slide: dict[str, Any]) -> str | None:
    spec = slide_canvas_spec(slide)
    raw = spec.get("template_id")
    if isinstance(raw, str) and raw:
        return raw
    raw = slide.get("template_id")
    return raw if isinstance(raw, str) and raw else None


def theme_policy_allows_multi_theme(plan: dict[str, Any]) -> bool:
    policy = plan.get("theme_policy")
    if not isinstance(policy, dict):
        return False
    return policy.get("allow_multi_theme") is True


def theme_policy_scope(plan: dict[str, Any]) -> str:
    policy = plan.get("theme_policy")
    if not isinstance(policy, dict):
        return "deck"
    raw = policy.get("scope")
    return raw if isinstance(raw, str) and raw else "deck"


def validate_project(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    plan_file = project_root / PLAN_PATH
    issues: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    theme_files: list[dict[str, str]] = []
    theme_file_seen: set[str] = set()
    theme_ids_seen: set[str] = set()
    plan: dict[str, Any] = {}
    registry: dict[str, Any] = {}
    registry_path = svglide_theme.GLOBAL_THEME_REGISTRY
    registry_paths: dict[str, str] = {}
    templates: dict[str, dict[str, Any]] = {}

    try:
        plan = read_json(plan_file)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        issues.append(issue("plan_invalid", f"could not read {PLAN_PATH.as_posix()}: {err}", path=PLAN_PATH.as_posix()))

    try:
        registry_path = svglide_theme.theme_registry_path(project_root)
        registry = svglide_theme.load_registry(project_root)
        registry_paths = theme_record_paths(registry)
    except (OSError, svglide_theme.ThemeError, json.JSONDecodeError) as err:
        issues.append(issue("theme_registry_invalid", str(err), path=svglide_theme.GLOBAL_THEME_REGISTRY.as_posix()))

    try:
        templates = template_records()
    except (OSError, json.JSONDecodeError, ValueError) as err:
        issues.append(issue("template_registry_invalid", str(err), path=TEMPLATE_REGISTRY_PATH.as_posix()))

    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    if not slides:
        issues.append(issue("slides_missing", "slide_plan.slides must be a non-empty array", path=PLAN_PATH.as_posix()))

    for index, slide in enumerate(slides, start=1):
        page_issues: list[dict[str, Any]] = []
        if not isinstance(slide, dict):
            page_issues.append(issue("slide_invalid", "slide item must be an object", page=index))
            pages.append({"page": index, "status": "failed", "issues": page_issues})
            issues.extend(page_issues)
            continue
        theme_id = slide_theme_id(slide, plan)
        template_id = slide_template_id(slide)
        theme_hash: str | None = None
        if not theme_id:
            page_issues.append(issue("theme_id_missing", "slide or canvas_spec must declare theme_id", page=index))
        else:
            theme_ids_seen.add(theme_id)
            try:
                theme = svglide_theme.load_theme(theme_id, project_root)
                theme_hash = svglide_theme.theme_sha256(theme)
                raw_theme_path = registry_paths.get(theme_id)
                if raw_theme_path and raw_theme_path not in theme_file_seen:
                    theme_file_seen.add(raw_theme_path)
                    theme_path = svglide_theme.theme_file_path(theme_id, project_root)
                    if theme_path is not None:
                        theme_files.append({"path": display_path(theme_path, project_root), "sha256": svglide_theme.file_sha256(theme_path)})
            except (OSError, svglide_theme.ThemeError, json.JSONDecodeError) as err:
                page_issues.append(issue("theme_invalid", str(err), page=index))
        if template_id:
            template = templates.get(template_id)
            if not template:
                page_issues.append(issue("template_unknown", f"template_id {template_id!r} is not present in template registry", page=index))
            elif theme_id:
                allowed = template.get("supported_theme_ids")
                if isinstance(allowed, list) and theme_id not in allowed and not project_theme_allows_template(registry, theme_id, template_id):
                    page_issues.append(issue("template_theme_not_allowed", f"template_id {template_id!r} does not allow theme_id {theme_id!r}", page=index))
        pages.append(
            {
                "page": slide.get("page") if isinstance(slide.get("page"), int) else index,
                "theme_id": theme_id,
                "template_id": template_id,
                "theme_sha256": theme_hash,
                "status": "passed" if not page_issues else "failed",
                "issues": page_issues,
            }
        )
        issues.extend(page_issues)

    if len(theme_ids_seen) > 1 and not theme_policy_allows_multi_theme(plan):
        issues.append(
            issue(
                "deck_theme_not_unified",
                "deck-level generation defaults to one unified theme; set theme_policy.allow_multi_theme=true only for an intentional multi-theme deck",
                path="$.theme_policy.allow_multi_theme",
            )
        )
    if len(theme_ids_seen) > 1 and theme_policy_scope(plan) == "deck" and theme_policy_allows_multi_theme(plan):
        issues.append(
            issue(
                "deck_theme_scope_conflict",
                "theme_policy.scope=deck conflicts with allow_multi_theme=true",
                path="$.theme_policy.scope",
            )
        )

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
            "theme_registry": display_path(registry_path, project_root),
            "theme_registry_sha256": svglide_theme.file_sha256(registry_path)
            if registry_path.exists()
            else None,
            "template_registry": relpath(TEMPLATE_REGISTRY_PATH, svglide_theme.REPO_ROOT),
            "template_registry_sha256": svglide_theme.file_sha256(TEMPLATE_REGISTRY_PATH) if TEMPLATE_REGISTRY_PATH.exists() else None,
        },
        "theme_files": theme_files,
        "pages": pages,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "page_count": len(pages),
            "theme_count": len(theme_ids_seen),
        },
        "issues": issues,
        "output_path": CHECK_PATH.as_posix(),
    }
    return result


def write_outputs(project_root: Path, result: dict[str, Any]) -> None:
    write_json(project_root / CHECK_PATH, result)
    write_json(project_root / RECEIPT_PATH, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SVGlide ThemeSpec usage in a project plan.")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    if not args.project_root.exists() or not args.project_root.is_dir():
        print(f"svglide_theme_validate: project_root does not exist: {args.project_root}", file=sys.stderr)
        return 2
    try:
        result = validate_project(args.project_root)
        write_outputs(args.project_root, result)
    except OSError as err:
        print(f"svglide_theme_validate: {err}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
