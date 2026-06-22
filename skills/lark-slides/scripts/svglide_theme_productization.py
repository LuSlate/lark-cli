#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_theme
import beautiful_template_runtime


PRODUCTIZATION_VERSION = "svglide-theme-productization/v1"
INPUT_PATH = Path("02-plan/theme-productization.input.json")
THEME_DIR = Path("02-plan/themes")
PROJECT_REGISTRY = Path("02-plan/theme-registry.json")
OUTPUT_PATH = Path("06-check/theme-productization.json")
RECEIPT_PATH = Path("receipts/theme-productization.json")
DEFAULT_MIGRATED_PLAN = Path("02-plan/slide_plan.theme-migrated.json")
CORE_COLOR_ROLES = (
    "background",
    "surface",
    "text",
    "muted",
    "primary",
    "accent",
    "success",
    "warning",
    "danger",
)


class ThemeProductizationError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ThemeProductizationError(f"missing required file: {path}") from err
    except json.JSONDecodeError as err:
        raise ThemeProductizationError(f"invalid JSON in {path}: {err}") from err


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def issue(code: str, message: str, *, path: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if path:
        payload["path"] = path
    return payload


def slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "theme"


def normalize_palette(raw: Any) -> dict[str, str]:
    palette = raw if isinstance(raw, dict) else {}
    colors: dict[str, str] = {}
    colors["background"] = svglide_theme.normalize_hex_color(str(palette.get("background") or "#FFFFFF"))
    colors["surface"] = svglide_theme.normalize_hex_color(str(palette.get("surface") or palette.get("panel") or "#F8FAFC"))
    colors["text"] = svglide_theme.normalize_hex_color(str(palette.get("text") or "#111827"))
    colors["muted"] = svglide_theme.normalize_hex_color(str(palette.get("muted") or "#64748B"))
    colors["primary"] = svglide_theme.normalize_hex_color(str(palette.get("primary") or "#2563EB"))
    colors["accent"] = svglide_theme.normalize_hex_color(str(palette.get("accent") or "#D946EF"))
    colors["success"] = svglide_theme.normalize_hex_color(str(palette.get("success") or "#16A34A"))
    colors["warning"] = svglide_theme.normalize_hex_color(str(palette.get("warning") or "#D97706"))
    colors["danger"] = svglide_theme.normalize_hex_color(str(palette.get("danger") or "#DC2626"))
    for key, value in palette.items():
        if isinstance(key, str) and key not in colors:
            colors[key] = svglide_theme.normalize_hex_color(str(value))
    return colors


def default_tokens(colors: dict[str, str]) -> dict[str, str]:
    return {f"color.{role}": colors[role] for role in CORE_COLOR_ROLES}


def default_semantic_colors(colors: dict[str, str]) -> dict[str, str]:
    return {
        "canvas.background": colors["background"],
        "surface.default": colors["surface"],
        "text.default": colors["text"],
        "text.muted": colors["muted"],
        "brand.primary": colors["primary"],
        "brand.accent": colors["accent"],
        "status.success": colors["success"],
        "status.warning": colors["warning"],
        "status.danger": colors["danger"],
    }


def infer_mode(colors: dict[str, str], requested: Any) -> str:
    if requested in {"light", "dark"}:
        return str(requested)
    return "dark" if svglide_theme.relative_luminance(colors["background"]) < 0.5 else "light"


def complete_theme_spec(raw_theme: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    brand = request.get("brand") if isinstance(request.get("brand"), dict) else {}
    theme_id = str(raw_theme.get("theme_id") or request.get("theme_id") or slug(str(brand.get("name") or "productized-theme")))
    colors = normalize_palette(raw_theme.get("colors") if isinstance(raw_theme.get("colors"), dict) else request.get("palette"))
    semantic_colors = raw_theme.get("semantic_colors") if isinstance(raw_theme.get("semantic_colors"), dict) else default_semantic_colors(colors)
    tokens = raw_theme.get("tokens") if isinstance(raw_theme.get("tokens"), dict) else default_tokens(colors)
    for role in CORE_COLOR_ROLES:
        tokens.setdefault(f"color.{role}", colors[role])
    data_series = raw_theme.get("data_series") if isinstance(raw_theme.get("data_series"), list) else [colors["primary"], colors["accent"], colors["success"], colors["warning"], colors["danger"]]
    spec: dict[str, Any] = {
        **raw_theme,
        "schema_version": "svglide-theme/v1",
        "theme_id": theme_id,
        "mode": infer_mode(colors, raw_theme.get("mode") or brand.get("mode")),
        "colors": colors,
        "semantic_colors": semantic_colors,
        "tokens": tokens,
        "contrast": raw_theme.get("contrast") if isinstance(raw_theme.get("contrast"), dict) else {"min_text_contrast": 4.5},
        "allowed_color_roles": raw_theme.get("allowed_color_roles") if isinstance(raw_theme.get("allowed_color_roles"), list) else list(colors.keys()),
        "data_series": data_series,
        "productization": {
            "source": request.get("source") or "theme-productization.input.json",
            "brand": brand,
            "provider": provider_summary(request),
        },
    }
    return spec


def provider_summary(request: dict[str, Any]) -> dict[str, Any]:
    provider = request.get("provider") if isinstance(request.get("provider"), dict) else {}
    provider_type = provider.get("type") if isinstance(provider.get("type"), str) else "deterministic_rules"
    return {"type": provider_type}


def command_from_provider(provider: dict[str, Any]) -> list[str]:
    raw = provider.get("command")
    if isinstance(raw, list) and raw and all(isinstance(item, str) for item in raw):
        return list(raw)
    if isinstance(raw, str) and raw.strip():
        return shlex.split(raw)
    raise ThemeProductizationError("provider.type=command requires provider.command")


def extract_theme(request: dict[str, Any], project: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = request.get("provider") if isinstance(request.get("provider"), dict) else {}
    provider_type = provider.get("type") if isinstance(provider.get("type"), str) else "deterministic_rules"
    raw_output: str | None = None
    returncode: int | None = None
    if provider_type == "command":
        command = command_from_provider(provider)
        completed = subprocess.run(
            command,
            cwd=project,
            input=json.dumps(request, ensure_ascii=False),
            check=False,
            capture_output=True,
            text=True,
            timeout=int(provider.get("timeout", 60)) if not isinstance(provider.get("timeout"), bool) else 60,
        )
        raw_output = completed.stdout
        returncode = completed.returncode
        if completed.returncode != 0:
            raise ThemeProductizationError(f"theme provider command failed with exit code {completed.returncode}: {completed.stderr}")
        raw_theme = json.loads(completed.stdout)
        if not isinstance(raw_theme, dict):
            raise ThemeProductizationError("theme provider output must be a JSON object")
    elif provider_type in {"deterministic_rules", "fixture"}:
        raw_theme = {
            "theme_id": request.get("theme_id") or slug(str((request.get("brand") or {}).get("name") if isinstance(request.get("brand"), dict) else "productized-theme")),
            "colors": request.get("palette") if isinstance(request.get("palette"), dict) else {},
        }
        raw_output = json.dumps(raw_theme, ensure_ascii=False, sort_keys=True)
        returncode = 0
    else:
        raise ThemeProductizationError(f"unsupported theme provider type: {provider_type}")

    theme = complete_theme_spec(raw_theme, request)
    return theme, {
        "type": provider_type,
        "command": command_from_provider(provider) if provider_type == "command" else None,
        "returncode": returncode,
        "raw_output_sha256": hashlib.sha256((raw_output or "").encode("utf-8")).hexdigest(),
    }


def read_template_ids() -> list[str]:
    payload = beautiful_template_runtime.template_registry()
    templates = payload.get("templates")
    if not isinstance(templates, list):
        return []
    ids: list[str] = []
    for item in templates:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


def registry_record(theme_id: str, theme_path: Path, project: Path, request: dict[str, Any]) -> dict[str, Any]:
    template_binding = request.get("template_binding") if isinstance(request.get("template_binding"), dict) else {}
    supported = template_binding.get("supported_template_ids")
    if not isinstance(supported, list) or not all(isinstance(item, str) for item in supported):
        supported = read_template_ids()
    return {
        "id": theme_id,
        "status": "active",
        "path": theme_path.relative_to(project).as_posix(),
        "template_bindings": {
            "mode": "project_theme_compatible",
            "supported_template_ids": supported,
            "source_theme_id": template_binding.get("source_theme_id") if isinstance(template_binding.get("source_theme_id"), str) else None,
        },
    }


def write_theme_outputs(project: Path, theme: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    theme_id = str(theme["theme_id"])
    theme_path = project / THEME_DIR / f"{slug(theme_id)}.json"
    write_json(theme_path, theme)
    registry = {
        "schema_version": "svglide-theme-registry/v1",
        "themes": [registry_record(theme_id, theme_path, project, request)],
    }
    write_json(project / PROJECT_REGISTRY, registry)
    return {
        "theme_id": theme_id,
        "theme_path": theme_path.relative_to(project).as_posix(),
        "theme_sha256": file_sha256(theme_path),
        "registry_path": PROJECT_REGISTRY.as_posix(),
        "registry_sha256": file_sha256(project / PROJECT_REGISTRY),
    }


def set_path(root: Any, path: list[Any], value: Any) -> None:
    cursor = root
    for item in path[:-1]:
        cursor = cursor[item]
    cursor[path[-1]] = value


def json_pointer(path: list[Any]) -> str:
    return "/" + "/".join(str(item).replace("~", "~0").replace("/", "~1") for item in path)


def migrate_plan(plan: dict[str, Any], target_theme_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    migrated = deepcopy(plan)
    ops: list[dict[str, Any]] = []
    previous: list[str] = []

    def replace(path: list[Any], old: Any) -> None:
        if isinstance(old, str):
            previous.append(old)
        set_path(migrated, path, target_theme_id)
        ops.append({"op": "replace", "path": json_pointer(path), "from": old, "value": target_theme_id})

    if isinstance(migrated.get("theme_id"), str):
        replace(["theme_id"], migrated["theme_id"])
    slides = migrated.get("slides")
    if isinstance(slides, list):
        for index, slide in enumerate(slides):
            if not isinstance(slide, dict):
                continue
            if isinstance(slide.get("theme_id"), str):
                replace(["slides", index, "theme_id"], slide["theme_id"])
            canvas = slide.get("canvas_spec")
            if isinstance(canvas, dict) and isinstance(canvas.get("theme_id"), str):
                replace(["slides", index, "canvas_spec", "theme_id"], canvas["theme_id"])
    return migrated, ops, sorted(set(previous))


def run_migration(project: Path, theme_id: str, request: dict[str, Any]) -> dict[str, Any]:
    migration = request.get("migration") if isinstance(request.get("migration"), dict) else {}
    input_rel = Path(str(migration.get("input_plan") or "02-plan/slide_plan.json"))
    input_path = project / input_rel
    if not input_path.exists():
        return {"status": "skipped", "reason": f"{input_rel.as_posix()} is missing"}
    output_rel = Path(str(migration.get("output_plan") or DEFAULT_MIGRATED_PLAN.as_posix()))
    if migration.get("in_place") is True:
        output_rel = input_rel
    plan = read_json(input_path)
    if not isinstance(plan, dict):
        raise ThemeProductizationError("migration input plan must be a JSON object")
    migrated, ops, previous_theme_ids = migrate_plan(plan, theme_id)
    write_json(project / output_rel, migrated)
    patch_path = project / "02-plan/theme-migration.patch.json"
    write_json(patch_path, {"target_theme_id": theme_id, "ops": ops})
    return {
        "status": "passed",
        "input_plan": input_rel.as_posix(),
        "output_plan": output_rel.as_posix(),
        "patch_path": "02-plan/theme-migration.patch.json",
        "patch_sha256": file_sha256(patch_path),
        "operation_count": len(ops),
        "previous_theme_ids": previous_theme_ids,
        "target_theme_id": theme_id,
        "in_place": output_rel == input_rel,
    }


def run_theme_productization(project: Path, *, input_path: Path = INPUT_PATH) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    request_path = project / input_path
    request = read_json(request_path)
    if not isinstance(request, dict):
        raise ThemeProductizationError("theme productization input must be a JSON object")
    issues: list[dict[str, str]] = []
    try:
        theme, provider = extract_theme(request, project)
    except (svglide_theme.ThemeError, json.JSONDecodeError) as err:
        raise ThemeProductizationError(str(err)) from err
    validation_issues = svglide_theme.validate_theme_spec(theme)
    if validation_issues:
        issues.extend(issue(item["code"], item["message"], path=item.get("path")) for item in validation_issues)
    theme_outputs = write_theme_outputs(project, theme, request)
    migration = run_migration(project, theme_outputs["theme_id"], request)
    status = "passed" if not issues else "failed"
    result = {
        "version": PRODUCTIZATION_VERSION,
        "stage": "theme_productization",
        "status": status,
        "action": "create_live" if status == "passed" else "repair_and_rerun",
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "request": input_path.as_posix(),
            "request_sha256": file_sha256(request_path),
        },
        "provider": provider,
        "theme": theme_outputs,
        "authoring_contract": {
            "status": "passed" if not validation_issues else "failed",
            "schema": "skills/lark-slides/references/svglide-theme-spec.schema.json",
            "registry": PROJECT_REGISTRY.as_posix(),
            "template_binding": "project theme registry template_bindings",
        },
        "migration": migration,
        "boundaries": {
            "authoring_ui": "not_implemented_in_cli_workspace",
            "model_quality_approval": "provider output is validated structurally; true aesthetic judgment needs an external model or human reviewer",
        },
        "summary": {
            "error_count": len(issues),
            "migration_operation_count": migration.get("operation_count", 0) if isinstance(migration, dict) else 0,
        },
        "issues": issues,
    }
    write_json(project / OUTPUT_PATH, result)
    write_json(project / RECEIPT_PATH, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract, author, and migrate SVGlide project themes.")
    parser.add_argument("project")
    parser.add_argument("--input", default=INPUT_PATH.as_posix())
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_theme_productization(Path(args.project), input_path=Path(args.input))
    except (OSError, subprocess.SubprocessError, ThemeProductizationError, svglide_theme.ThemeError, json.JSONDecodeError) as error:
        print(f"svglide_theme_productization: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
