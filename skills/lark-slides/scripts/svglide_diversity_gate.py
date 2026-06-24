#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import beautiful_template_runtime


PLAN_PATH = Path("02-plan/slide_plan.json")
DESIGN_SELECTION_PATH = Path("02-plan/selection-metadata.json")
CHECK_DIR = Path("06-check")
OUTPUT_PATH = CHECK_DIR / "diversity-gate.json"
PASS_ACTION = "continue_pipeline"
FAIL_ACTION = "repair_and_rerun"
DEFAULT_HISTORY_LIMIT = 8
COMBO_REUSE_FAIL = 0.75


class DiversityGateError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise DiversityGateError(f"missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise DiversityGateError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise DiversityGateError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json_object(path)
    except (OSError, DiversityGateError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str, *, path: str | None = None, compared_project: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if path:
        payload["path"] = path
    if compared_project:
        payload["compared_project"] = compared_project
    return payload


def list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def style_lock_from(plan: dict[str, Any], design_selection: dict[str, Any]) -> dict[str, Any]:
    lock = plan.get("style_lock")
    if isinstance(lock, dict):
        return lock
    lock = design_selection.get("style_lock")
    return lock if isinstance(lock, dict) else {}


def template_family_id(plan: dict[str, Any], lock: dict[str, Any]) -> str:
    raw = lock.get("template_family_id")
    if isinstance(raw, str) and raw:
        return raw
    selection = plan.get("template_family_selection")
    if isinstance(selection, dict):
        raw = selection.get("selected_template_id")
        if isinstance(raw, str) and raw:
            return raw
    return "unknown-template-family"


def style_pack_id(lock: dict[str, Any]) -> str:
    raw = lock.get("style_pack_id")
    return raw if isinstance(raw, str) and raw else "unknown-style-pack"


def component_variant(slide: dict[str, Any], plan: dict[str, Any]) -> str:
    raw = slide.get("component_variant") or slide.get("template_variant")
    if isinstance(raw, str) and raw:
        return raw
    selection = slide.get("component_selection")
    if isinstance(selection, list):
        ids = [str(item.get("component_id")) for item in selection if isinstance(item, dict) and item.get("component_id")]
        if ids:
            return "+".join(ids[:3])
    deck_selection = plan.get("component_variant_selection")
    if isinstance(deck_selection, dict):
        values = list_value(deck_selection.get("selected_component_variants"))
        if values:
            return "+".join(values[:3])
    return "unknown-component"


def layout_variant(slide: dict[str, Any]) -> str:
    for key in ("layout_variant", "layout_family", "renderer_id", "page_type"):
        raw = slide.get(key)
        if isinstance(raw, str) and raw:
            return raw
    return "unknown-layout"


def slide_combo(slide: dict[str, Any], plan: dict[str, Any], lock: dict[str, Any]) -> dict[str, str]:
    spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
    template_id = spec.get("template_id") or template_family_id(plan, lock)
    return {
        "page": str(slide.get("page") or ""),
        "template_id": str(template_id),
        "template_family_id": template_family_id(plan, lock),
        "style_pack_id": style_pack_id(lock),
        "palette_id": str(lock.get("palette_id") or plan.get("project_palette", {}).get("palette_id") or ""),
        "layout_variant": layout_variant(slide),
        "component_variant": component_variant(slide, plan),
    }


def combo_key(combo: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        combo.get("template_id", ""),
        combo.get("style_pack_id", ""),
        combo.get("layout_variant", ""),
        combo.get("component_variant", ""),
    )


def plan_signature(plan: dict[str, Any], design_selection: dict[str, Any]) -> dict[str, Any]:
    lock = style_lock_from(plan, design_selection)
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    combos = [slide_combo(slide, plan, lock) for slide in slides if isinstance(slide, dict)]
    return {
        "style_lock": lock,
        "template_family_id": template_family_id(plan, lock),
        "style_pack_id": style_pack_id(lock),
        "palette_id": str(lock.get("palette_id") or plan.get("project_palette", {}).get("palette_id") or ""),
        "image_treatment_id": str(lock.get("image_treatment_id") or ""),
        "decoration_policy_id": str(lock.get("decoration_policy_id") or ""),
        "combos": combos,
        "combo_keys": ["|".join(combo_key(combo)) for combo in combos],
    }


def validate_current_plan(plan: dict[str, Any], design_selection: dict[str, Any], signature: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    lock = signature.get("style_lock") if isinstance(signature.get("style_lock"), dict) else {}
    if not lock:
        issues.append(issue("style_lock_missing", "SVGlide selection decks must carry a deck-level style_lock", path="style_lock"))
    elif lock.get("deck_level") is not True:
        issues.append(issue("style_lock_not_deck_level", "style_lock.deck_level must be true", path="style_lock.deck_level"))
    if design_selection and design_selection.get("status") == "failed":
        issues.append(issue("recipe_selection_failed", "design asset selection failed closed before diversity gate", path=DESIGN_SELECTION_PATH.as_posix()))
    if not signature.get("combos"):
        issues.append(issue("diversity_combo_missing", "slides must produce at least one diversity combo", path="slides"))
    plan_palette = plan.get("project_palette") if isinstance(plan.get("project_palette"), dict) else {}
    lock_palette = lock.get("palette_id")
    if isinstance(lock_palette, str) and lock_palette and isinstance(plan_palette.get("style_pack_id"), str):
        if plan_palette.get("style_pack_id") != lock.get("style_pack_id"):
            issues.append(issue("style_pack_palette_mismatch", "project_palette.style_pack_id must match style_lock.style_pack_id", path="project_palette.style_pack_id"))
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    for index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        raw_style = slide.get("style_pack_id")
        if isinstance(raw_style, str) and raw_style and raw_style != signature.get("style_pack_id"):
            issues.append(issue("slide_style_pack_drift", "slide-level style_pack_id must not drift from deck style_lock", path=f"slides[{index}].style_pack_id"))
        spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
        raw_palette = spec.get("palette_id")
        project_palette_id = plan_palette.get("palette_id")
        if isinstance(raw_palette, str) and isinstance(project_palette_id, str) and raw_palette and raw_palette != project_palette_id:
            issues.append(issue("slide_palette_drift", "canvas_spec.palette_id must match project_palette.palette_id", path=f"slides[{index}].canvas_spec.palette_id"))
    return issues


def recent_project_dirs(project: Path, limit: int) -> list[Path]:
    root = project.parent
    if not root.exists():
        return []
    candidates = [item for item in root.iterdir() if item.is_dir() and item.resolve() != project.resolve() and (item / PLAN_PATH).exists()]
    candidates.sort(key=lambda item: (item / PLAN_PATH).stat().st_mtime, reverse=True)
    return candidates[:limit]


def combo_reuse_ratio(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_counts = Counter(left)
    right_counts = Counter(right)
    overlap = sum(min(left_counts[key], right_counts[key]) for key in left_counts.keys() & right_counts.keys())
    return overlap / min(len(left), len(right))


def compare_recent(project: Path, signature: dict[str, Any], *, history_limit: int) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    comparisons: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    current_keys = list(signature.get("combo_keys") if isinstance(signature.get("combo_keys"), list) else [])
    for other_project in recent_project_dirs(project, history_limit):
        other_plan = read_json_optional(other_project / PLAN_PATH)
        if not other_plan:
            continue
        other_selection = read_json_optional(other_project / DESIGN_SELECTION_PATH)
        other_signature = plan_signature(other_plan, other_selection)
        other_keys = list(other_signature.get("combo_keys") if isinstance(other_signature.get("combo_keys"), list) else [])
        ratio = combo_reuse_ratio([str(item) for item in current_keys], [str(item) for item in other_keys])
        comparison = {
            "project": relpath(other_project, project.parent),
            "title": other_plan.get("title"),
            "combo_reuse_ratio": round(ratio, 4),
            "style_pack_id": other_signature.get("style_pack_id"),
            "template_family_id": other_signature.get("template_family_id"),
        }
        comparisons.append(comparison)
        if ratio >= COMBO_REUSE_FAIL:
            issues.append(
                issue(
                    "diversity_combo_reuse_too_high",
                    f"template/style/layout/component combo reuse ratio {ratio:.2f} exceeds {COMBO_REUSE_FAIL:.2f}",
                    compared_project=comparison["project"],
                )
            )
    return comparisons, issues


def production_default_template_count() -> int:
    registry = beautiful_template_runtime.template_registry()
    return sum(
        1
        for item in registry.get("templates", [])
        if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)
    )


def run_diversity_gate(project: Path, *, history_limit: int = DEFAULT_HISTORY_LIMIT) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan = read_json_object(project / PLAN_PATH)
    design_selection = read_json_optional(project / DESIGN_SELECTION_PATH)
    signature = plan_signature(plan, design_selection)
    issues = validate_current_plan(plan, design_selection, signature)
    comparisons, comparison_issues = compare_recent(project, signature, history_limit=history_limit)
    warnings: list[dict[str, str]] = []
    single_template_mode = production_default_template_count() <= 1
    if single_template_mode:
        warnings.extend(comparison_issues)
    else:
        issues.extend(comparison_issues)
    status = "passed" if not issues else "failed"
    result = {
        "schema_version": "svglide-diversity-gate/v1",
        "stage": "diversity_gate",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "design_selection": DESIGN_SELECTION_PATH.as_posix() if (project / DESIGN_SELECTION_PATH).exists() else None,
            "history_limit": history_limit,
        },
        "signature": signature,
        "comparisons": comparisons,
        "summary": {
            "error_count": len(issues),
            "warning_count": len(warnings),
            "comparison_count": len(comparisons),
            "combo_count": len(signature.get("combos") if isinstance(signature.get("combos"), list) else []),
        },
        "issues": issues,
        "warnings": warnings,
        "output_path": OUTPUT_PATH.as_posix(),
    }
    if single_template_mode and warnings:
        result["claim_boundary"] = "diversity history reuse was downgraded because the production/default template pool has only one executable fidelity-passed template"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review SVGlide design asset composition diversity.")
    parser.add_argument("project")
    parser.add_argument("--history-limit", type=int, default=DEFAULT_HISTORY_LIMIT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_diversity_gate(Path(args.project), history_limit=args.history_limit)
    except DiversityGateError as error:
        print(f"svglide_diversity_gate: {error}", file=sys.stderr)
        return 2
    write_json(Path(args.project) / OUTPUT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
