#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "svglide-auto-repair/v1"
PLAN_PATH = Path("02-plan/slide_plan.json")
INSTRUCTION_PATH = Path("00-input/instruction.json")
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
ASSET_MANIFEST_PATH = Path("03-assets/asset-manifest.json")
CHECK_PATH = Path("06-check/auto-repair.json")
RECEIPT_PATH = Path("receipts/auto_repair.json")
FOREIGN_OBJECT_RE = re.compile(r"<foreignObject\b(?P<attrs>[^>]*)>", re.IGNORECASE)
ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)=\"([^\"]*)\"")


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_record(code: str, file: Path, operation: str, *, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "file": file.as_posix(),
        "operation": operation,
    }
    if path:
        payload["path"] = path
    return payload


def repair_missing_instruction_json(project_root: Path, patches: list[dict[str, Any]]) -> None:
    path = project_root / INSTRUCTION_PATH
    if path.exists():
        return
    manifest = read_json_optional(project_root / "01-project/project_manifest.json")
    raw_prompt = manifest.get("title") if isinstance(manifest.get("title"), str) else "SVGlide generated deck"
    write_json(
        path,
        {
            "version": "svglide-instruction/v1",
            "raw_prompt": raw_prompt,
            "repair_note": "created deterministically by svglide_auto_repair",
        },
    )
    patches.append(patch_record("instruction_missing", INSTRUCTION_PATH, "create_from_project_manifest"))


def palette_token_overrides(project_palette: dict[str, Any]) -> dict[str, str]:
    colors = project_palette.get("colors") if isinstance(project_palette.get("colors"), dict) else {}
    return {
        f"color.{role}": colors[role]
        for role in ("background", "surface", "text", "muted", "primary", "accent")
        if isinstance(colors.get(role), str)
    }


def repair_project_palette_from_selection(project_root: Path, patches: list[dict[str, Any]]) -> dict[str, Any]:
    plan_path = project_root / PLAN_PATH
    selection_path = project_root / PALETTE_SELECTION_PATH
    if not plan_path.exists() or not selection_path.exists():
        return {}
    plan = read_json_optional(plan_path)
    selection = read_json_optional(selection_path)
    project_palette = selection.get("project_palette") if isinstance(selection.get("project_palette"), dict) else {}
    if project_palette and plan.get("project_palette") != project_palette:
        plan["project_palette"] = project_palette
        write_json(plan_path, plan)
        patches.append(patch_record("project_palette_missing", PLAN_PATH, "copy_from_palette_selection", path="project_palette"))
    return plan


def repair_project_theme_token_overrides(project_root: Path, plan: dict[str, Any], patches: list[dict[str, Any]]) -> None:
    plan_path = project_root / PLAN_PATH
    if not plan:
        plan = read_json_optional(plan_path)
    project_palette = plan.get("project_palette") if isinstance(plan.get("project_palette"), dict) else {}
    overrides = palette_token_overrides(project_palette)
    if not overrides:
        return
    project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
    if project_theme.get("token_overrides") == overrides:
        return
    project_theme = dict(project_theme)
    project_theme["palette_ref"] = project_theme.get("palette_ref") or "project_palette"
    project_theme["token_overrides"] = overrides
    plan["project_theme"] = project_theme
    write_json(plan_path, plan)
    patches.append(patch_record("project_theme_token_overrides_missing", PLAN_PATH, "derive_from_project_palette", path="project_theme.token_overrides"))


def iter_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            if isinstance(child, (dict, list)):
                found.extend(iter_dicts(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                found.extend(iter_dicts(child))
    return found


def repair_asset_contract_id_metadata(project_root: Path, patches: list[dict[str, Any]]) -> None:
    plan_path = project_root / PLAN_PATH
    plan = read_json_optional(plan_path)
    manifest = read_json_optional(project_root / ASSET_MANIFEST_PATH)
    manifest_contracts = {
        item.get("asset_id") or item.get("id"): item
        for item in manifest.get("contracts", [])
        if isinstance(item, dict) and (item.get("asset_id") or item.get("id"))
    } if isinstance(manifest.get("contracts"), list) else {}
    slides = plan.get("slides")
    if not isinstance(slides, list):
        return
    changed = False
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        contract = slide.get("asset_contract")
        if not isinstance(contract, str) or contract in {"none", "none_required"}:
            if isinstance(contract, dict):
                asset_id = contract.get("asset_id") or contract.get("id")
                manifest_contract = manifest_contracts.get(asset_id)
                if isinstance(asset_id, str) and isinstance(manifest_contract, dict):
                    copied = False
                    for key in ["source_url", "href", "file", "path", "asset_kind", "license", "safe_text_zones", "placement_role"]:
                        if key not in contract and key in manifest_contract:
                            contract[key] = manifest_contract[key]
                            copied = True
                    if copied:
                        contract["status"] = manifest_contract.get("status") or contract.get("status")
                        patches.append(patch_record("asset_contract_metadata_missing", PLAN_PATH, "copy_asset_contract_metadata_from_manifest", path=f"slides[{index - 1}].asset_contract"))
                        changed = True
            continue
        metadata = {
            "asset_id": contract,
            "placement_role": slide.get("visual_asset_role") or "evidence",
            "status": "metadata_only",
        }
        manifest_contract = manifest_contracts.get(contract)
        if isinstance(manifest_contract, dict):
            for key in ["source_url", "href", "file", "path", "asset_kind", "license", "safe_text_zones", "placement_role", "status"]:
                if key in manifest_contract:
                    metadata[key] = manifest_contract[key]
        slide["asset_contract"] = metadata
        patches.append(patch_record("asset_contract_metadata_missing", PLAN_PATH, "wrap_asset_contract_id", path=f"slides[{index - 1}].asset_contract"))
        changed = True
    if changed:
        write_json(plan_path, plan)


def repair_cached_web_image_asset_manifest(project_root: Path, patches: list[dict[str, Any]]) -> None:
    manifest_path = project_root / ASSET_MANIFEST_PATH
    manifest = read_json_optional(manifest_path)
    if not manifest:
        return
    changed = False
    for item in iter_dicts(manifest):
        source_url = item.get("source_url")
        cached_from = item.get("cached_from") or item.get("original_url")
        if isinstance(source_url, str) and source_url.startswith(("http://", "https://")):
            continue
        if isinstance(cached_from, str) and cached_from.startswith(("http://", "https://")):
            item["source_url"] = cached_from
            patches.append(patch_record("asset_source_url_missing", ASSET_MANIFEST_PATH, "restore_source_url_from_cache_metadata"))
            changed = True
    if changed:
        write_json(manifest_path, manifest)


def parse_attrs(raw: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in ATTR_RE.finditer(raw)}


def number_close(left: Any, right: Any, *, tolerance: float = 0.5) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def foreign_object_matches_box(attrs: dict[str, str], box: dict[str, Any]) -> bool:
    return all(number_close(attrs.get(key), box.get(key)) for key in ["x", "y", "width", "height"])


def repair_text_box_height(text: str, box: dict[str, Any]) -> tuple[str, bool]:
    changed = False

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        attrs = parse_attrs(match.group("attrs"))
        if not foreign_object_matches_box(attrs, box):
            return match.group(0)
        try:
            current_height = float(attrs["height"])
        except (KeyError, ValueError):
            return match.group(0)
        new_height = round(current_height * 1.25 + 8, 3)
        raw_attrs = match.group("attrs")
        updated_attrs = re.sub(r'height="[^"]*"', f'height="{new_height:g}"', raw_attrs, count=1)
        if updated_attrs != raw_attrs:
            changed = True
        return f"<foreignObject{updated_attrs}>"

    return FOREIGN_OBJECT_RE.sub(replace, text), changed


def repair_minor_text_overflow(project_root: Path, patches: list[dict[str, Any]]) -> None:
    lint = read_json_optional(project_root / "06-check/preview-lint.json")
    issues = lint.get("issues") if isinstance(lint.get("issues"), list) else lint.get("page_issues")
    issues = issues if isinstance(issues, list) else []
    minor = [
        item
        for item in issues
        if isinstance(item, dict)
        and item.get("code") in {"text_overflow", "preview_text_overflow_risk"}
        and isinstance(item.get("box"), dict)
        and isinstance(item.get("page"), int)
    ]
    changed_paths: set[str] = set()
    for item in minor:
        page = int(item["page"])
        box = item["box"]
        candidates = [
            Path(f"04-svg/prepared/page-{page:03d}.svg"),
            Path(f"04-svg/page-{page:03d}.svg"),
            Path("05-preview/preview.html"),
        ]
        for rel in candidates:
            path = project_root / rel
            if not path.exists() or not path.is_file():
                continue
            original = path.read_text(encoding="utf-8")
            repaired, changed = repair_text_box_height(original, box)
            if changed:
                path.write_text(repaired, encoding="utf-8")
                changed_paths.add(rel.as_posix())
    for rel in sorted(changed_paths):
        patches.append(patch_record("text_overflow", Path(rel), "increase_foreign_object_height_from_preview_lint"))


def suggestion_only_repairs(project_root: Path) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for rel in [Path("06-check/plan-bundle-review.json"), Path("06-check/collected-errors.json")]:
        payload = read_json_optional(project_root / rel)
        issues = payload.get("issues")
        if not isinstance(issues, list):
            for stage in payload.get("stages", []) if isinstance(payload.get("stages"), list) else []:
                if isinstance(stage, dict) and isinstance(stage.get("issues"), list):
                    issues = (issues or []) + stage["issues"]
        if not isinstance(issues, list):
            continue
        for item in issues:
            if not isinstance(item, dict):
                continue
            if item.get("code") in {"chart_rich_content_too_thin", "semantic_evidence_missing", "template_theme_incompatible"}:
                suggestions.append(
                    {
                        "code": item.get("code"),
                        "repairability": "suggestion_only",
                        "safe_actions": [
                            "add source_refs",
                            "downgrade visual_recipe from chart-rich to text-stat",
                            "ask model to regenerate evidence-backed page plan",
                        ],
                    }
                )
    return suggestions


def run_auto_repair(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    patches: list[dict[str, Any]] = []
    repair_missing_instruction_json(project_root, patches)
    plan = repair_project_palette_from_selection(project_root, patches)
    repair_project_theme_token_overrides(project_root, plan, patches)
    repair_asset_contract_id_metadata(project_root, patches)
    repair_cached_web_image_asset_manifest(project_root, patches)
    repair_minor_text_overflow(project_root, patches)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": "auto_repair",
        "status": "patched" if patches else "noop",
        "patched_at": now_iso(),
        "patches": patches,
        "suggestions": suggestion_only_repairs(project_root),
    }
    write_json(project_root / CHECK_PATH, payload)
    write_json(project_root / RECEIPT_PATH, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply deterministic SVGlide plan repairs.")
    parser.add_argument("project_root")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    result = run_auto_repair(Path(args.project_root))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
