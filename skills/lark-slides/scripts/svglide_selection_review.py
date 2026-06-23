#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import beautiful_template_runtime


SCHEMA_VERSION = "svglide-selection-review/v1"
STAGE = "theme_template_selection_review"
SELECTION_PATH = Path("02-plan/theme-template-selection.json")
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
PLAN_PATH = Path("02-plan/slide_plan.json")
DESIGN_SELECTION_PATH = Path("02-plan/selection-metadata.json")
RECIPE_ROUTING_RECEIPT_PATH = Path("02-plan/recipe-routing-receipt.json")
CHECK_PATH = Path("06-check/theme-template-selection-review.json")
RECEIPT_PATH = Path("receipts/theme_template_selection_review.json")
REQUIRED_DESIGN_SELECTION_KEYS = [
    "deck_recipe_selection",
    "template_family_selection",
    "style_pack_selection",
    "density_mode_selection",
    "component_variant_selection",
    "image_treatment_selection",
    "style_lock",
]


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


def issue(code: str, message: str, *, path: str | None = None, page: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        payload["path"] = path
    if page is not None:
        payload["page"] = page
    return payload


def load_selection(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / SELECTION_PATH)


def load_palette_selection(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / PALETTE_SELECTION_PATH)


def load_plan(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / PLAN_PATH)


def load_design_selection(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / DESIGN_SELECTION_PATH)


def allowed_template_ids(selection: dict[str, Any]) -> set[str]:
    values = {str(selection.get("selected_template_id"))} if selection.get("selected_template_id") else set()
    for item in selection.get("template_candidates", []):
        if isinstance(item, dict) and item.get("template_id"):
            values.add(str(item["template_id"]))
    return values


def allowed_theme_ids(selection: dict[str, Any]) -> set[str]:
    values = {str(selection.get("selected_theme_id"))} if selection.get("selected_theme_id") else set()
    for item in selection.get("theme_candidates", []):
        if isinstance(item, dict) and item.get("theme_id"):
            values.add(str(item["theme_id"]))
    return values


def allowed_palette_ids(selection: dict[str, Any], palette_selection: dict[str, Any]) -> set[str]:
    values = set()
    if selection.get("selected_palette_id"):
        values.add(str(selection["selected_palette_id"]))
    if palette_selection.get("selected_palette_id"):
        values.add(str(palette_selection["selected_palette_id"]))
    for item in palette_selection.get("palette_candidates", []):
        if isinstance(item, dict) and item.get("palette_id"):
            values.add(str(item["palette_id"]))
    return values


def legacy_status(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return False
    return record.get("status") == "legacy_debug" or record.get("asset_status") == "legacy_debug" or record.get("quality_tier") == "fixture_only"


def production_template_policy_issues(record: dict[str, Any] | None, template_id: str) -> list[dict[str, Any]]:
    if not isinstance(record, dict):
        return []
    issues: list[dict[str, Any]] = []
    is_production_runtime = (
        record.get("asset_status") == beautiful_template_runtime.ASSET_STATUS_PRODUCTION
        and record.get("quality_tier") == beautiful_template_runtime.QUALITY_TIER_TRUSTED
        and record.get("default_selectable") is True
        and record.get("selection_scope") == "production"
    )
    if not is_production_runtime:
        return issues
    if record.get("claim_level") == "source_inventory_only":
        issues.append(
            issue(
                "selected_source_inventory_template",
                f"selected_template_id {template_id!r} claims source_inventory_only",
                path="selected_template_id",
            )
        )
    gate = record.get("promotion_gate")
    if not isinstance(gate, dict) or gate.get("status") != "passed":
        issues.append(
            issue(
                "selected_template_promotion_gate_not_passed",
                f"selected_template_id {template_id!r} does not have promotion_gate.status=passed",
                path="selected_template_id",
            )
        )
    return issues


def candidate_by_id(records: Any, id_key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(records, list):
        return result
    for item in records:
        if not isinstance(item, dict):
            continue
        raw = item.get(id_key) or item.get("id") or item.get("palette_id")
        if isinstance(raw, str) and raw:
            result[raw] = item
    return result


def selected_legacy_issues(selection: dict[str, Any], palette_selection: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    template_id = selection.get("selected_template_id")
    theme_id = selection.get("selected_theme_id")
    palette_id = palette_selection.get("selected_palette_id") or selection.get("selected_palette_id")
    templates = candidate_by_id(selection.get("template_candidates"), "template_id")
    themes = candidate_by_id(selection.get("theme_candidates"), "theme_id")
    palettes = candidate_by_id(palette_selection.get("palette_candidates"), "palette_id")
    if isinstance(template_id, str) and (
        legacy_status(templates.get(template_id)) or template_id in beautiful_template_runtime.LEGACY_TEMPLATE_IDS
    ):
        issues.append(issue("selected_legacy_template", f"selected_template_id {template_id!r} is legacy_debug/fixture_only", path="selected_template_id"))
    if isinstance(template_id, str):
        issues.extend(production_template_policy_issues(templates.get(template_id), template_id))
    if isinstance(theme_id, str) and (
        legacy_status(themes.get(theme_id)) or theme_id in beautiful_template_runtime.LEGACY_THEME_IDS
    ):
        issues.append(issue("selected_legacy_theme", f"selected_theme_id {theme_id!r} is legacy_debug/fixture_only", path="selected_theme_id"))
    if isinstance(palette_id, str):
        legacy_palette_id = palette_id.startswith("family.") and palette_id.removeprefix("family.") in beautiful_template_runtime.LEGACY_THEME_IDS
        if legacy_status(palettes.get(palette_id)) or legacy_palette_id:
            issues.append(issue("selected_legacy_palette", f"selected_palette_id {palette_id!r} is legacy_debug/fixture_only", path="selected_palette_id"))
    return issues


def slide_canvas_spec(slide: dict[str, Any]) -> dict[str, Any]:
    spec = slide.get("canvas_spec")
    return spec if isinstance(spec, dict) else {}


def validate_project_theme(plan: dict[str, Any], selection: dict[str, Any]) -> list[dict[str, Any]]:
    project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
    if not project_theme:
        return [issue("project_theme_missing", "slide_plan must include project_theme", path="project_theme")]
    if project_theme.get("base_theme_id") not in allowed_theme_ids(selection):
        return [issue("project_theme_not_allowed", "project_theme.base_theme_id is not in selector candidates", path="project_theme.base_theme_id")]
    return []


def validate_plan_against_selection(plan: dict[str, Any], selection: dict[str, Any], palette_selection: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    templates = allowed_template_ids(selection)
    themes = allowed_theme_ids(selection)
    palettes = allowed_palette_ids(selection, palette_selection)
    project_palette = plan.get("project_palette") if isinstance(plan.get("project_palette"), dict) else {}
    if not project_palette:
        issues.append(issue("project_palette_missing", "slide_plan must include project_palette", path="project_palette"))
    elif project_palette.get("palette_id") not in palettes:
        issues.append(issue("project_palette_not_allowed", "project_palette.palette_id is not in palette candidates", path="project_palette.palette_id"))
    if plan.get("selection_receipt") != SELECTION_PATH.as_posix():
        issues.append(issue("selection_receipt_missing", f"slide_plan.selection_receipt must be {SELECTION_PATH.as_posix()}", path="selection_receipt"))
    if plan.get("palette_selection_receipt") != PALETTE_SELECTION_PATH.as_posix():
        issues.append(issue("palette_selection_receipt_missing", f"slide_plan.palette_selection_receipt must be {PALETTE_SELECTION_PATH.as_posix()}", path="palette_selection_receipt"))
    if selection.get("confidence") == "low" and not plan.get("fallback_policy"):
        issues.append(issue("low_confidence_fallback_missing", "low confidence selection requires slide_plan.fallback_policy", path="fallback_policy"))

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        issues.append(issue("slides_missing", "slide_plan.slides must be a non-empty array", path="slides"))
        return issues
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            issues.append(issue("slide_invalid", "slide must be an object", page=index))
            continue
        spec = slide_canvas_spec(slide)
        template_id = spec.get("template_id") or slide.get("template_id")
        theme_id = spec.get("theme_id") or slide.get("theme_id")
        palette_id = spec.get("palette_id") or slide.get("palette_id") or project_palette.get("palette_id")
        if template_id not in templates:
            issues.append(issue("template_not_allowed", f"template_id {template_id!r} is not in selector candidates", page=index, path="canvas_spec.template_id"))
        if theme_id not in themes:
            issues.append(issue("theme_not_allowed", f"theme_id {theme_id!r} is not in selector candidates", page=index, path="canvas_spec.theme_id"))
        if palette_id not in palettes:
            issues.append(issue("palette_not_allowed", f"palette_id {palette_id!r} is not in palette candidates", page=index, path="canvas_spec.palette_id"))
        trace = spec.get("selection_trace")
        if not isinstance(trace, dict):
            issues.append(issue("selection_trace_missing", "canvas_spec.selection_trace is required", page=index, path="canvas_spec.selection_trace"))
    return issues


def is_svg_route_plan(plan: dict[str, Any]) -> bool:
    return plan.get("route") == "svglide-svg" or plan.get("output_mode") == "svglide-svg"


def validate_design_asset_selection(plan: dict[str, Any], design_selection: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for key in REQUIRED_DESIGN_SELECTION_KEYS:
        if not isinstance(design_selection.get(key), dict):
            issues.append(issue("design_asset_selection_field_missing", f"selection-metadata.json must include {key}", path=key))
    if issues:
        return issues
    if design_selection.get("status") != "passed":
        issues.append(issue("design_asset_selection_not_passed", "design asset selection must be passed before SVG generation", path="status"))
    recipe = design_selection["deck_recipe_selection"]
    if recipe.get("match_level") == "L4":
        issues.append(issue("design_asset_selection_l4", "L4 recipe selection must fail closed and cannot enter SVG generation", path="deck_recipe_selection.match_level"))
    for key in ["recipe_id", "match_level", "confidence", "signals"]:
        if key not in recipe:
            issues.append(issue("design_asset_recipe_field_missing", f"deck_recipe_selection must include {key}", path=f"deck_recipe_selection.{key}"))
    style_lock = design_selection["style_lock"]
    style_pack = design_selection["style_pack_selection"]
    image_treatment = design_selection["image_treatment_selection"]
    if style_lock.get("deck_level") is not True:
        issues.append(issue("style_lock_not_deck_level", "style_lock must be deck_level=true", path="style_lock.deck_level"))
    if style_lock.get("style_pack_id") != style_pack.get("selected_style_pack_id"):
        issues.append(issue("style_lock_style_pack_mismatch", "style_lock.style_pack_id must match selected_style_pack_id", path="style_lock.style_pack_id"))
    if style_lock.get("image_treatment_id") != image_treatment.get("selected_image_treatment_id"):
        issues.append(issue("style_lock_image_treatment_mismatch", "style_lock.image_treatment_id must match selected image treatment", path="style_lock.image_treatment_id"))
    if style_lock.get("decoration_policy_id") in {"random_decorations", "decorative_noise"}:
        issues.append(issue("style_lock_disallowed_decoration_policy", "random decoration policy is not allowed", path="style_lock.decoration_policy_id"))
    for key in REQUIRED_DESIGN_SELECTION_KEYS:
        if key in plan and plan.get(key) != design_selection.get(key):
            issues.append(issue("design_asset_selection_plan_mismatch", f"slide_plan.{key} must match selection-metadata.json", path=key))
    return issues


def run_review(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    issues: list[dict[str, Any]] = []
    try:
        selection = load_selection(project_root)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        selection = {}
        issues.append(issue("selection_missing", f"could not read {SELECTION_PATH}: {err}", path=SELECTION_PATH.as_posix()))
    try:
        palette_selection = load_palette_selection(project_root)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        palette_selection = {}
        issues.append(issue("palette_selection_missing", f"could not read {PALETTE_SELECTION_PATH}: {err}", path=PALETTE_SELECTION_PATH.as_posix()))
    try:
        plan = load_plan(project_root)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        plan = {}
        issues.append(issue("plan_missing", f"could not read {PLAN_PATH}: {err}", path=PLAN_PATH.as_posix()))
    design_selection: dict[str, Any] = {}
    design_selection_required = is_svg_route_plan(plan) or (project_root / DESIGN_SELECTION_PATH).exists()
    if design_selection_required:
        try:
            design_selection = load_design_selection(project_root)
        except (OSError, json.JSONDecodeError, ValueError) as err:
            issues.append(issue("design_asset_selection_missing", f"could not read {DESIGN_SELECTION_PATH}: {err}", path=DESIGN_SELECTION_PATH.as_posix()))
    if selection and palette_selection and plan:
        issues.extend(selected_legacy_issues(selection, palette_selection))
        issues.extend(validate_project_theme(plan, selection))
        issues.extend(validate_plan_against_selection(plan, selection, palette_selection))
        if design_selection:
            issues.extend(validate_design_asset_selection(plan, design_selection))
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "inputs": {
            "selection": SELECTION_PATH.as_posix(),
            "palette_selection": PALETTE_SELECTION_PATH.as_posix(),
            "plan": PLAN_PATH.as_posix(),
            "design_selection": DESIGN_SELECTION_PATH.as_posix() if design_selection_required else None,
            "recipe_routing_receipt": RECIPE_ROUTING_RECEIPT_PATH.as_posix() if design_selection_required else None,
        },
        "summary": {"error_count": len(issues)},
        "issues": issues,
    }


def write_outputs(project_root: Path, result: dict[str, Any]) -> None:
    write_json(project_root / CHECK_PATH, result)
    write_json(project_root / RECEIPT_PATH, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review SVGlide plan against theme/template selection candidates.")
    parser.add_argument("project_root")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    result = run_review(project_root)
    write_outputs(project_root, result)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
