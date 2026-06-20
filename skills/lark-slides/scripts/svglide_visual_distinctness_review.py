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


PLAN_PATH = Path("02-plan/slide_plan.json")
CHECK_DIR = Path("06-check")
OUTPUT_PATH = CHECK_DIR / "visual-distinctness.json"
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"
DEFAULT_HISTORY_LIMIT = 5
PALETTE_OVERLAP_FAIL = 0.67
SEQUENCE_OVERLAP_FAIL = 0.75
DEFAULT_RENDERERS = {
    "cover",
    "cover_full_bleed",
    "chart",
    "dashboard_scorecard",
    "timeline",
    "timeline_rail",
    "closing",
    "closing_cta",
    "test-renderer",
}


class VisualDistinctnessError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise VisualDistinctnessError(f"missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise VisualDistinctnessError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise VisualDistinctnessError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json_object(path)
    except (OSError, VisualDistinctnessError):
        return {}


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str, *, compared_project: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if compared_project:
        payload["compared_project"] = compared_project
    return payload


def normalize_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if len(raw) == 4 and raw.startswith("#"):
        return "#" + "".join(ch * 2 for ch in raw[1:])
    if len(raw) == 7 and raw.startswith("#"):
        return raw
    return None


def colors_from(value: Any) -> list[str]:
    colors: list[str] = []
    if isinstance(value, list):
        for item in value:
            color = normalize_color(item)
            if color and color not in colors:
                colors.append(color)
    elif isinstance(value, dict):
        for item in value.values():
            if isinstance(item, list):
                for nested in item:
                    color = normalize_color(nested)
                    if color and color not in colors:
                        colors.append(color)
            else:
                color = normalize_color(item)
                if color and color not in colors:
                    colors.append(color)
    return colors


def plan_signature(plan: dict[str, Any]) -> dict[str, Any]:
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    style_system = plan.get("style_system") if isinstance(plan.get("style_system"), dict) else {}
    visual_identity = plan.get("visual_identity") if isinstance(plan.get("visual_identity"), dict) else {}
    design_dna = visual_identity.get("design_dna") if isinstance(visual_identity.get("design_dna"), dict) else {}
    art_direction = plan.get("art_direction") if isinstance(plan.get("art_direction"), dict) else {}
    palette = colors_from(style_system.get("palette"))
    if not palette:
        palette = colors_from(design_dna.get("palette"))
    return {
        "title": plan.get("title"),
        "style_preset": plan.get("style_preset"),
        "theme_archetype": visual_identity.get("theme_archetype"),
        "palette": palette,
        "renderer_sequence": [item.get("renderer_id") for item in slides if isinstance(item, dict)],
        "layout_sequence": [item.get("layout_family") for item in slides if isinstance(item, dict)],
        "recipe_sequence": [item.get("visual_recipe") for item in slides if isinstance(item, dict)],
        "cover_treatment": art_direction.get("cover_treatment") or design_dna.get("cover_treatment"),
    }


def sequence_similarity(left: list[Any], right: list[Any]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    if size <= 0:
        return 0.0
    matches = sum(1 for index in range(size) if left[index] == right[index])
    return matches / size


def palette_overlap(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    return len(left_set & right_set) / min(len(left_set), len(right_set))


def recent_project_dirs(project: Path, limit: int) -> list[Path]:
    root = project.parent
    if not root.exists():
        return []
    candidates = [
        item
        for item in root.iterdir()
        if item.is_dir() and item.resolve() != project.resolve() and (item / PLAN_PATH).exists()
    ]
    candidates.sort(key=lambda item: (item / PLAN_PATH).stat().st_mtime, reverse=True)
    return candidates[:limit]


def is_default_renderer_sequence(renderers: list[Any]) -> bool:
    return bool(renderers) and all(isinstance(item, str) and item in DEFAULT_RENDERERS for item in renderers)


def compare_signatures(current: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    renderer_similarity = sequence_similarity(current.get("renderer_sequence", []), other.get("renderer_sequence", []))
    layout_similarity = sequence_similarity(current.get("layout_sequence", []), other.get("layout_sequence", []))
    recipe_similarity = sequence_similarity(current.get("recipe_sequence", []), other.get("recipe_sequence", []))
    palette_similarity = palette_overlap(current.get("palette", []), other.get("palette", []))
    same_style = current.get("style_preset") == other.get("style_preset") and bool(current.get("style_preset"))
    same_cover = current.get("cover_treatment") == other.get("cover_treatment") and bool(current.get("cover_treatment"))
    return {
        "style_preset_match": same_style,
        "cover_treatment_match": same_cover,
        "palette_overlap": round(palette_similarity, 4),
        "renderer_sequence_similarity": round(renderer_similarity, 4),
        "layout_sequence_similarity": round(layout_similarity, 4),
        "recipe_sequence_similarity": round(recipe_similarity, 4),
        "same_theme_archetype": current.get("theme_archetype") == other.get("theme_archetype") and bool(current.get("theme_archetype")),
    }


def high_similarity(comparison: dict[str, Any]) -> bool:
    if comparison.get("same_theme_archetype"):
        return False
    palette_high = comparison.get("palette_overlap", 0) >= PALETTE_OVERLAP_FAIL
    renderer_high = comparison.get("renderer_sequence_similarity", 0) >= SEQUENCE_OVERLAP_FAIL
    layout_high = comparison.get("layout_sequence_similarity", 0) >= SEQUENCE_OVERLAP_FAIL
    return bool(comparison.get("style_preset_match") and palette_high and (renderer_high or layout_high))


def run_visual_distinctness_review(
    project: Path,
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    allow_style_reuse: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan = read_json_object(project / PLAN_PATH)
    signature = plan_signature(plan)
    issues: list[dict[str, str]] = []
    comparisons: list[dict[str, Any]] = []

    if not signature.get("theme_archetype"):
        issues.append(issue("visual_identity_theme_missing", "visual_identity.theme_archetype is required for distinctness review"))
    if is_default_renderer_sequence(signature.get("renderer_sequence", [])):
        issues.append(issue("renderer_sequence_default_only", "renderer sequence uses only default generic renderers"))

    for other_project in recent_project_dirs(project, history_limit):
        other_plan = read_json_optional(other_project / PLAN_PATH)
        if not other_plan:
            continue
        other_signature = plan_signature(other_plan)
        comparison = compare_signatures(signature, other_signature)
        comparison["project"] = relpath(other_project, project.parent)
        comparison["title"] = other_signature.get("title")
        comparison["style_preset"] = other_signature.get("style_preset")
        comparison["theme_archetype"] = other_signature.get("theme_archetype")
        comparisons.append(comparison)
        if not allow_style_reuse and high_similarity(comparison):
            issues.append(
                issue(
                    "visual_identity_too_similar_to_recent_deck",
                    "different theme reuses style preset, palette, and renderer/layout sequence from a recent deck",
                    compared_project=comparison["project"],
                )
            )

    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-visual-distinctness/v1",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "history_limit": history_limit,
            "allow_style_reuse": allow_style_reuse,
        },
        "signature": signature,
        "comparisons": comparisons,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "comparison_count": len(comparisons),
        },
        "issues": issues,
        "output_path": OUTPUT_PATH.as_posix(),
    }
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review SVGlide visual distinctness against recent local projects.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--history-limit", type=int, default=DEFAULT_HISTORY_LIMIT)
    parser.add_argument("--allow-style-reuse", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_visual_distinctness_review(
            Path(args.project),
            history_limit=max(0, args.history_limit),
            allow_style_reuse=args.allow_style_reuse,
        )
    except (OSError, VisualDistinctnessError) as error:
        print(f"svglide_visual_distinctness_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
