#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "svglide-plan-bundle-review/v1"
STAGE = "plan_bundle_review"
PLAN_PATH = Path("02-plan/slide_plan.json")
INSTRUCTION_PATH = Path("00-input/instruction.json")
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
THEME_SELECTION_PATH = Path("02-plan/theme-template-selection.json")
EVIDENCE_PATH = Path("source/evidence.json")
CHECK_PATH = Path("06-check/plan-bundle-review.json")
RECEIPT_PATH = Path("receipts/plan_bundle_review.json")
STRICT_PROFILES = {"local_real_preview", "production", "production_live"}
BASELINE_IDS = {
    "baseline",
    "baseline-theme",
    "baseline-template",
    "svglide-baseline",
    "safe-native-v1",
    "default",
}
ASSET_METADATA_KEYS = {
    "asset_id",
    "asset_kind",
    "href",
    "file",
    "local_path_or_href",
    "path",
    "placement_role",
    "source_ref",
    "source_type",
    "source_url",
    "usage_page",
}
ROOT_CAUSE_BY_CODE = {
    "project_palette_missing": "palette_adoption",
    "project_palette_mismatch": "palette_adoption",
    "project_theme_token_overrides_missing": "palette_adoption",
    "project_theme_token_override_mismatch": "palette_adoption",
    "asset_contract_metadata_missing": "asset_contract",
    "asset_source_url_missing": "asset_contract",
    "asset_source_url_not_http": "asset_contract",
    "local_generated_image_forbidden": "asset_contract",
    "page_count_too_low": "deck_scope_contract",
    "visual_asset_role_missing": "asset_contract",
    "chart_rich_content_too_thin": "plan_semantic_evidence",
    "semantic_evidence_missing": "plan_semantic_evidence",
    "baseline_theme_template_forbidden": "template_selection",
    "debug_reference_line_forbidden": "template_selection",
    "template_theme_incompatible": "template_selection",
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json_optional(project_root: Path, rel: Path) -> tuple[dict[str, Any], str | None]:
    path = project_root / rel
    if not path.exists():
        return {}, f"missing required file: {rel.as_posix()}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return {}, f"could not read {rel.as_posix()}: {err}"
    if not isinstance(payload, dict):
        return {}, f"expected JSON object: {rel.as_posix()}"
    return payload, None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def issue(
    code: str,
    message: str,
    *,
    path: str | None = None,
    page: int | None = None,
    repair_hint: str | None = None,
    repairability: str = "manual",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "severity": "error",
        "stage": STAGE,
        "root_cause_group": ROOT_CAUSE_BY_CODE.get(code, "plan_bundle"),
        "message": message,
        "repairability": repairability,
    }
    if path is not None:
        payload["path"] = path
    if page is not None:
        payload["page"] = page
    if repair_hint is not None:
        payload["repair_hint"] = repair_hint
    return payload


def is_online_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def iter_asset_metadata(value: Any, path: str) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        if any(key in value for key in ASSET_METADATA_KEYS):
            found.append((path, value))
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                found.extend(iter_asset_metadata(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(iter_asset_metadata(child, f"{path}[{index}]"))
    return found


def evidence_ids(evidence: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    items = evidence.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                ids.add(item["id"])
    return ids


def source_ref_id(source_ref: str) -> str:
    if source_ref.startswith("source:"):
        return source_ref.split(":", 1)[1]
    return source_ref


def validate_instruction_exists(instruction_error: str | None) -> list[dict[str, Any]]:
    if instruction_error:
        return [
            issue(
                "instruction_missing",
                instruction_error,
                path=INSTRUCTION_PATH.as_posix(),
                repair_hint="write 00-input/instruction.json before running pre-render review",
                repairability="deterministic",
            )
        ]
    return []


def validate_deck_scope_contract(plan: dict[str, Any], instruction: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    slide_count = len(slides) if isinstance(slides, list) else 0
    contract = plan.get("deck_scope_contract") if isinstance(plan.get("deck_scope_contract"), dict) else {}
    minimum = contract.get("min_page_count")
    if not isinstance(minimum, int):
        minimum = 8 if profile in STRICT_PROFILES else 0
    if minimum and slide_count < minimum:
        issues.append(
            issue(
                "page_count_too_low",
                f"complex preview needs at least {minimum} pages before SVG generation; found {slide_count}",
                path="slides",
                repair_hint="expand slide_plan.slides or lower deck_scope_contract.min_page_count explicitly",
            )
        )
    return issues


def validate_project_palette_adopted(plan: dict[str, Any], palette_selection: dict[str, Any]) -> list[dict[str, Any]]:
    expected = palette_selection.get("project_palette") if isinstance(palette_selection.get("project_palette"), dict) else {}
    actual = plan.get("project_palette") if isinstance(plan.get("project_palette"), dict) else {}
    if not actual:
        return [
            issue(
                "project_palette_missing",
                "slide_plan.project_palette is required before SVG generation",
                path="project_palette",
                repair_hint="copy project_palette from 02-plan/palette-selection.json",
                repairability="deterministic",
            )
        ]
    issues: list[dict[str, Any]] = []
    if expected:
        for key in ("palette_id", "source", "confidence"):
            if expected.get(key) != actual.get(key):
                issues.append(
                    issue(
                        "project_palette_mismatch",
                        f"project_palette.{key} does not match palette selection",
                        path=f"project_palette.{key}",
                        repair_hint="rerun plan or copy selected palette into slide_plan.project_palette",
                        repairability="deterministic",
                    )
                )
    return issues


def validate_project_theme_token_overrides(plan: dict[str, Any], palette_selection: dict[str, Any]) -> list[dict[str, Any]]:
    project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
    overrides = project_theme.get("token_overrides") if isinstance(project_theme.get("token_overrides"), dict) else {}
    if not overrides:
        return [
            issue(
                "project_theme_token_overrides_missing",
                "slide_plan.project_theme.token_overrides is required before SVG generation",
                path="project_theme.token_overrides",
                repair_hint="derive color.* token overrides from selected project_palette",
                repairability="deterministic",
            )
        ]
    expected = palette_selection.get("project_palette") if isinstance(palette_selection.get("project_palette"), dict) else {}
    colors = expected.get("colors") if isinstance(expected.get("colors"), dict) else {}
    issues: list[dict[str, Any]] = []
    for role in ("background", "surface", "text", "muted", "primary", "accent"):
        expected_color = colors.get(role)
        if isinstance(expected_color, str) and overrides.get(f"color.{role}") != expected_color:
            issues.append(
                issue(
                    "project_theme_token_override_mismatch",
                    f"project_theme.token_overrides.color.{role} must match selected palette",
                    path=f"project_theme.token_overrides.color.{role}",
                    repair_hint="refresh token_overrides from 02-plan/palette-selection.json",
                    repairability="deterministic",
                )
            )
    return issues


def validate_asset_contracts_online_only(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for metadata_path, metadata in iter_asset_metadata(plan, "slide_plan"):
        asset_kind = metadata.get("asset_kind")
        if asset_kind in {"generated_image", "ai_image"}:
            issues.append(
                issue(
                    "local_generated_image_forbidden",
                    f"{metadata_path} uses forbidden asset_kind={asset_kind!r}",
                    path=metadata_path,
                    repair_hint="replace generated/local image with an online source-backed asset",
                )
            )
        source_url = metadata.get("source_url")
        source_type = metadata.get("source_type")
        if source_type in {"local_preview", "local_generated"}:
            issues.append(
                issue(
                    "local_generated_image_forbidden",
                    f"{metadata_path} uses forbidden source_type={source_type!r}",
                    path=metadata_path,
                    repair_hint="use an http(s) source_url for visible images",
                )
            )
        if any(key in metadata for key in {"href", "file", "local_path_or_href", "asset_id", "asset_kind"}):
            if not isinstance(source_url, str) or not source_url.strip():
                issues.append(
                    issue(
                        "asset_source_url_missing",
                        f"{metadata_path} must include an online source_url",
                        path=f"{metadata_path}.source_url",
                        repair_hint="attach source_url from asset manifest or online search result",
                    )
                )
            elif not is_online_url(source_url):
                issues.append(
                    issue(
                        "asset_source_url_not_http",
                        f"{metadata_path}.source_url must be http(s), got {source_url!r}",
                        path=f"{metadata_path}.source_url",
                        repair_hint="replace local/file/internal preview URL with http(s) source_url",
                    )
                )
    return issues


def validate_asset_contract_resolution(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        contract = slide.get("asset_contract")
        if isinstance(contract, str) and contract not in {"none", "none_required"}:
            issues.append(
                issue(
                    "asset_contract_metadata_missing",
                    "asset_contract string must be resolved to metadata before SVG generation",
                    page=index,
                    path=f"slides[{index - 1}].asset_contract",
                    repair_hint="replace asset_contract id with metadata including source_url and placement_role",
                    repairability="deterministic",
                )
            )
        if contract is None or (isinstance(contract, str) and contract in {"none", "none_required"}):
            continue
        metadata = contract if isinstance(contract, dict) else {}
        if isinstance(metadata, dict) and metadata and not metadata.get("placement_role"):
            issues.append(
                issue(
                    "visual_asset_role_missing",
                    "asset_contract.placement_role is required for visible asset planning",
                    page=index,
                    path=f"slides[{index - 1}].asset_contract.placement_role",
                    repair_hint="set placement_role such as hero, evidence, logo, or texture",
                    repairability="deterministic",
                )
            )
    return issues


def validate_semantic_evidence_before_render(plan: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    ids = evidence_ids(evidence)
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        refs = slide.get("source_refs")
        if not isinstance(refs, list) or not refs:
            issues.append(
                issue(
                    "semantic_evidence_missing",
                    "each slide needs source_refs before render",
                    page=index,
                    path=f"slides[{index - 1}].source_refs",
                    repair_hint="add source_refs or mark the slide as explicit user-authored narrative",
                )
            )
            continue
        missing = [ref for ref in refs if isinstance(ref, str) and ids and source_ref_id(ref) not in ids]
        if missing:
            issues.append(
                issue(
                    "semantic_evidence_missing",
                    f"source_refs not found in evidence: {', '.join(missing)}",
                    page=index,
                    path=f"slides[{index - 1}].source_refs",
                    repair_hint="align source_refs with source/evidence.json item ids",
                )
            )
    return issues


def validate_chart_rich_evidence(plan: dict[str, Any], evidence: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    if profile not in STRICT_PROFILES:
        return []
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        recipe = " ".join(str(slide.get(key) or "") for key in ["visual_recipe", "layout_family", "renderer_id"]).lower()
        if not any(token in recipe for token in ["chart", "dashboard", "metric", "trend", "data"]):
            continue
        refs = slide.get("source_refs")
        ref_count = len([ref for ref in refs if isinstance(ref, str)]) if isinstance(refs, list) else 0
        body_points = slide.get("body_points")
        body_count = len(body_points) if isinstance(body_points, list) else 0
        if ref_count < 2 and body_count < 3:
            issues.append(
                issue(
                    "chart_rich_content_too_thin",
                    "chart-rich slide needs stronger evidence before SVG generation",
                    page=index,
                    path=f"slides[{index - 1}].source_refs",
                    repair_hint="add source_refs or downgrade visual_recipe",
                    repairability="suggestion_only",
                )
            )
    return issues


def validate_template_theme_compatibility(plan: dict[str, Any], selection: dict[str, Any]) -> list[dict[str, Any]]:
    selected_template = selection.get("selected_template_id")
    selected_theme = selection.get("selected_theme_id")
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
        template_id = spec.get("template_id") or slide.get("template_id")
        theme_id = spec.get("theme_id") or slide.get("theme_id")
        if selected_template and template_id and template_id != selected_template:
            trace = spec.get("selection_trace")
            if not isinstance(trace, dict):
                issues.append(
                    issue(
                        "template_theme_incompatible",
                        "template differs from selected template without selection_trace",
                        page=index,
                        path=f"slides[{index - 1}].canvas_spec.selection_trace",
                        repair_hint="add selection_trace or regenerate template selection",
                    )
                )
        if selected_theme and theme_id and theme_id != selected_theme and not isinstance(spec.get("selection_trace"), dict):
            issues.append(
                issue(
                    "template_theme_incompatible",
                    "theme differs from selected theme without selection_trace",
                    page=index,
                    path=f"slides[{index - 1}].canvas_spec.selection_trace",
                    repair_hint="add selection_trace or regenerate theme selection",
                )
            )
    return issues


def validate_satori_static_risks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for metadata_path, metadata in iter_asset_metadata(plan, "slide_plan"):
        opacity = metadata.get("opacity")
        if metadata.get("kind") == "image" and isinstance(opacity, (int, float)) and opacity < 1:
            issues.append(
                issue(
                    "image_opacity_unsupported",
                    f"{metadata_path} uses image opacity that may not survive Satori/SVG conversion",
                    path=f"{metadata_path}.opacity",
                    repair_hint="apply opacity through a separate overlay instead of the image node",
                )
            )
    return issues


def validate_no_baseline_theme_template(plan: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    values: list[tuple[str, Any, int | None]] = [
        ("style_preset", plan.get("style_preset"), None),
        ("project_theme.base_theme_id", (plan.get("project_theme") or {}).get("base_theme_id") if isinstance(plan.get("project_theme"), dict) else None, None),
    ]
    slides = plan.get("slides")
    if isinstance(slides, list):
        for index, slide in enumerate(slides, start=1):
            if not isinstance(slide, dict):
                continue
            spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
            values.extend(
                [
                    (f"slides[{index - 1}].template_id", slide.get("template_id") or spec.get("template_id"), index),
                    (f"slides[{index - 1}].theme_id", slide.get("theme_id") or spec.get("theme_id"), index),
                ]
            )
            text = json.dumps(slide, ensure_ascii=False).lower()
            if any(token in text for token in ["debug guide", "reference line", "参考线", "辅助线"]):
                issues.append(
                    issue(
                        "debug_reference_line_forbidden",
                        "debug/reference lines must not enter template or SVG plan",
                        page=index,
                        path=f"slides[{index - 1}]",
                        repair_hint="remove debug guide/reference line elements from canvas_spec",
                    )
                )
    for path, value, page in values:
        if isinstance(value, str) and value.lower() in BASELINE_IDS:
            issues.append(
                issue(
                    "baseline_theme_template_forbidden",
                    f"{path} uses forbidden baseline id {value!r}",
                    page=page,
                    path=path,
                    repair_hint="select a non-baseline template/theme from the registry",
                )
            )
    return issues


def run_plan_bundle_review(project_root: Path, *, profile: str) -> dict[str, Any]:
    project_root = project_root.resolve()
    issues: list[dict[str, Any]] = []
    instruction, instruction_error = read_json_optional(project_root, INSTRUCTION_PATH)
    plan, plan_error = read_json_optional(project_root, PLAN_PATH)
    palette_selection, palette_error = read_json_optional(project_root, PALETTE_SELECTION_PATH)
    selection, selection_error = read_json_optional(project_root, THEME_SELECTION_PATH)
    evidence, evidence_error = read_json_optional(project_root, EVIDENCE_PATH)

    issues.extend(validate_instruction_exists(instruction_error))
    for rel, error_value, code in [
        (PLAN_PATH, plan_error, "plan_missing"),
        (PALETTE_SELECTION_PATH, palette_error, "palette_selection_missing"),
        (THEME_SELECTION_PATH, selection_error, "selection_missing"),
        (EVIDENCE_PATH, evidence_error, "evidence_missing"),
    ]:
        if error_value:
            issues.append(issue(code, error_value, path=rel.as_posix()))

    if plan:
        issues.extend(validate_deck_scope_contract(plan, instruction, profile))
        issues.extend(validate_asset_contracts_online_only(plan))
        issues.extend(validate_asset_contract_resolution(plan))
        issues.extend(validate_no_baseline_theme_template(plan))
        issues.extend(validate_satori_static_risks(plan))
    if plan and palette_selection:
        issues.extend(validate_project_palette_adopted(plan, palette_selection))
        issues.extend(validate_project_theme_token_overrides(plan, palette_selection))
    if plan and evidence:
        issues.extend(validate_semantic_evidence_before_render(plan, evidence))
        issues.extend(validate_chart_rich_evidence(plan, evidence, profile))
    if plan and selection:
        issues.extend(validate_template_theme_compatibility(plan, selection))

    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "profile": profile,
        "inputs": {
            "instruction": INSTRUCTION_PATH.as_posix(),
            "plan": PLAN_PATH.as_posix(),
            "palette_selection": PALETTE_SELECTION_PATH.as_posix(),
            "theme_template_selection": THEME_SELECTION_PATH.as_posix(),
            "evidence": EVIDENCE_PATH.as_posix(),
        },
        "summary": {"error_count": len(issues), "warning_count": 0},
        "issues": issues,
    }
    write_json(project_root / CHECK_PATH, result)
    write_json(project_root / RECEIPT_PATH, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review SVGlide pre-render plan bundle.")
    parser.add_argument("project_root")
    parser.add_argument("--profile", default="production")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    result = run_plan_bundle_review(Path(args.project_root), profile=args.profile)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
