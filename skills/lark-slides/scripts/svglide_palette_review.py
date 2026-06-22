#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_theme


SCHEMA_VERSION = "svglide-palette-review/v1"
STAGE = "palette_review"
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
PLAN_PATH = Path("02-plan/slide_plan.json")
CHECK_PATH = Path("06-check/palette-review.json")
RECEIPT_PATH = Path("receipts/palette_review.json")


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


def issue(code: str, message: str, *, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        payload["path"] = path
    return payload


def load_palette_selection(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / PALETTE_SELECTION_PATH)


def load_plan(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / PLAN_PATH)


def validate_brand_resolution(selection: dict[str, Any]) -> list[dict[str, Any]]:
    resolution = selection.get("brand_resolution")
    if not isinstance(resolution, dict):
        return [issue("brand_resolution_missing", "palette selection must include brand_resolution", path="brand_resolution")]
    issues: list[dict[str, Any]] = []
    if resolution.get("source") not in {"user_provided", "brand_registry", "source_asset_extract", "official_lookup", "stable_fallback"}:
        issues.append(issue("brand_resolution_source_invalid", "brand_resolution.source is invalid", path="brand_resolution.source"))
    if resolution.get("confidence") not in {"high", "medium", "low"}:
        issues.append(issue("brand_resolution_confidence_invalid", "brand_resolution.confidence is invalid", path="brand_resolution.confidence"))
    evidence = resolution.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        issues.append(issue("brand_resolution_evidence_missing", "brand_resolution.evidence must be non-empty", path="brand_resolution.evidence"))
    return issues


def validate_palette_contrast(selection: dict[str, Any]) -> list[dict[str, Any]]:
    project_palette = selection.get("project_palette") if isinstance(selection.get("project_palette"), dict) else {}
    colors = project_palette.get("colors") if isinstance(project_palette.get("colors"), dict) else {}
    text = colors.get("text")
    background = colors.get("background")
    if not isinstance(text, str) or not isinstance(background, str):
        return [issue("palette_contrast_colors_missing", "project_palette.colors.text/background are required", path="project_palette.colors")]
    try:
        ratio = svglide_theme.contrast_ratio(text, background)
    except svglide_theme.ThemeError as err:
        return [issue("palette_contrast_color_invalid", str(err), path="project_palette.colors")]
    if ratio < 4.5:
        return [issue("palette_contrast_too_low", f"text/background contrast {ratio:.2f} is below 4.5", path="project_palette.colors")]
    return []


def required_series_count(payload: Any) -> int:
    max_count = 0
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"required_series_count", "series_count", "min_series_count"} and isinstance(value, int):
                max_count = max(max_count, value)
            else:
                max_count = max(max_count, required_series_count(value))
    elif isinstance(payload, list):
        for item in payload:
            max_count = max(max_count, required_series_count(item))
    return max_count


def validate_data_series(selection: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    required = required_series_count(plan)
    if required <= 0:
        return []
    project_palette = selection.get("project_palette") if isinstance(selection.get("project_palette"), dict) else {}
    data_series = project_palette.get("data_series")
    if not isinstance(data_series, list) or len(data_series) < required:
        return [issue("palette_data_series_insufficient", f"plan requires {required} data series colors", path="project_palette.data_series")]
    return []


def validate_project_palette(plan: dict[str, Any], selection: dict[str, Any]) -> list[dict[str, Any]]:
    expected = selection.get("project_palette") if isinstance(selection.get("project_palette"), dict) else {}
    actual = plan.get("project_palette") if isinstance(plan.get("project_palette"), dict) else {}
    if not actual:
        return [issue("project_palette_missing", "slide_plan must include project_palette", path="project_palette")]
    issues: list[dict[str, Any]] = []
    for key in ("palette_id", "source", "confidence"):
        if actual.get(key) != expected.get(key):
            issues.append(issue("project_palette_mismatch", f"project_palette.{key} does not match palette selection", path=f"project_palette.{key}"))
    expected_colors = expected.get("colors") if isinstance(expected.get("colors"), dict) else {}
    actual_colors = actual.get("colors") if isinstance(actual.get("colors"), dict) else {}
    for key in ("background", "text", "primary", "accent"):
        if actual_colors.get(key) != expected_colors.get(key):
            issues.append(issue("project_palette_color_mismatch", f"project_palette.colors.{key} does not match palette selection", path=f"project_palette.colors.{key}"))
    return issues


def validate_theme_token_override(plan: dict[str, Any], selection: dict[str, Any]) -> list[dict[str, Any]]:
    expected = selection.get("project_palette") if isinstance(selection.get("project_palette"), dict) else {}
    expected_colors = expected.get("colors") if isinstance(expected.get("colors"), dict) else {}
    project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
    overrides = project_theme.get("token_overrides") if isinstance(project_theme.get("token_overrides"), dict) else {}
    if not overrides:
        return [issue("project_theme_token_overrides_missing", "slide_plan.project_theme.token_overrides is required", path="project_theme.token_overrides")]
    issues: list[dict[str, Any]] = []
    for role in ("background", "surface", "text", "muted", "primary", "accent"):
        token = f"color.{role}"
        if expected_colors.get(role) and overrides.get(token) != expected_colors.get(role):
            issues.append(issue("project_theme_token_override_mismatch", f"{token} must use selected project palette color", path=f"project_theme.token_overrides.{token}"))
    return issues


def run_palette_review(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    issues: list[dict[str, Any]] = []
    try:
        selection = load_palette_selection(project_root)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        selection = {}
        issues.append(issue("palette_selection_missing", f"could not read {PALETTE_SELECTION_PATH}: {err}", path=PALETTE_SELECTION_PATH.as_posix()))
    try:
        plan = load_plan(project_root)
    except (OSError, json.JSONDecodeError, ValueError) as err:
        plan = {}
        issues.append(issue("plan_missing", f"could not read {PLAN_PATH}: {err}", path=PLAN_PATH.as_posix()))

    if selection:
        issues.extend(validate_brand_resolution(selection))
        issues.extend(validate_palette_contrast(selection))
    if selection and plan:
        issues.extend(validate_data_series(selection, plan))
        issues.extend(validate_project_palette(plan, selection))
        issues.extend(validate_theme_token_override(plan, selection))

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "inputs": {
            "palette_selection": PALETTE_SELECTION_PATH.as_posix(),
            "plan": PLAN_PATH.as_posix(),
        },
        "summary": {"error_count": len(issues)},
        "issues": issues,
    }


def write_outputs(project_root: Path, result: dict[str, Any]) -> None:
    write_json(project_root / CHECK_PATH, result)
    write_json(project_root / RECEIPT_PATH, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review SVGlide palette selection and project palette adoption.")
    parser.add_argument("project_root")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    result = run_palette_review(project_root)
    write_outputs(project_root, result)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
