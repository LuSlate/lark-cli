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

import beautiful_template_runtime


SCHEMA_VERSION = "svglide-selection-metadata-lint/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
REFERENCE_DIR = SCRIPT_DIR.parent / "references"
BRAND_PALETTE_REGISTRY = REFERENCE_DIR / "svglide-brand-palette-registry.json"
CHECK_PATH = Path("06-check/selection-metadata-lint.json")
RECEIPT_PATH = Path("receipts/selection_metadata_lint.json")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
DENSITY_VALUES = {"low", "medium", "medium-high", "high"}
FORMALITY_VALUES = {"low", "medium", "medium-high", "high"}
SCHEME_VALUES = {"light", "dark", "mixed"}
TOKEN_OVERRIDE_VALUES = {"allowed", "restricted", "forbidden"}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def active_templates(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in registry.get("templates", []) if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)]


def active_themes(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in registry.get("themes", []) if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)]


def active_palettes(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in registry.get("palettes", []) if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)]


def brand_records(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in registry.get("brands", []) if isinstance(item, dict)]


def issue(code: str, message: str, *, item_id: str | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if item_id is not None:
        payload["id"] = item_id
    if path is not None:
        payload["path"] = path
    return payload


def non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def valid_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX_RE.fullmatch(value))


def validate_template_metadata(template: dict[str, Any]) -> list[dict[str, Any]]:
    template_id = str(template.get("id") or "<unknown-template>")
    metadata = template.get("selection_metadata")
    issues: list[dict[str, Any]] = []
    is_production_runtime = (
        template.get("asset_status") == beautiful_template_runtime.ASSET_STATUS_PRODUCTION
        and template.get("quality_tier") == beautiful_template_runtime.QUALITY_TIER_TRUSTED
        and template.get("default_selectable") is True
        and template.get("selection_scope") == "production"
    )
    if is_production_runtime:
        if template.get("claim_level") == "source_inventory_only":
            issues.append(
                issue(
                    "source_inventory_only_production_template",
                    "production/default-selectable template cannot claim source_inventory_only",
                    item_id=template_id,
                    path="claim_level",
                )
            )
        gate = template.get("promotion_gate")
        if not isinstance(gate, dict) or gate.get("status") != "passed":
            issues.append(
                issue(
                    "template_promotion_gate_not_passed",
                    "production/default-selectable template requires promotion_gate.status=passed",
                    item_id=template_id,
                    path="promotion_gate.status",
                )
            )
    if not isinstance(metadata, dict):
        issues.append(issue("selection_metadata_missing", "active template requires selection_metadata", item_id=template_id))
        return issues
    list_required = (
        "best_for",
        "industry_tags",
        "occasion_tags",
        "audience_tags",
        "tone_tags",
        "content_shapes",
        "visual_signature",
    )
    for key in list_required:
        if not non_empty_string_list(metadata.get(key)):
            issues.append(issue("selection_metadata_list_empty", f"selection_metadata.{key} must be a non-empty string array", item_id=template_id, path=f"selection_metadata.{key}"))
    for key in ("avoid_for", "required_assets", "decorative_elements"):
        if not string_list(metadata.get(key)):
            issues.append(issue("selection_metadata_list_invalid", f"selection_metadata.{key} must be a string array", item_id=template_id, path=f"selection_metadata.{key}"))
    if metadata.get("density") not in DENSITY_VALUES:
        issues.append(issue("selection_metadata_density_invalid", "selection_metadata.density is invalid", item_id=template_id, path="selection_metadata.density"))
    if metadata.get("formality") not in FORMALITY_VALUES:
        issues.append(issue("selection_metadata_formality_invalid", "selection_metadata.formality is invalid", item_id=template_id, path="selection_metadata.formality"))
    return issues


def validate_theme_metadata(theme: dict[str, Any]) -> list[dict[str, Any]]:
    theme_id = str(theme.get("id") or "<unknown-theme>")
    metadata = theme.get("selection_metadata")
    if not isinstance(metadata, dict):
        return [issue("selection_metadata_missing", "active theme requires selection_metadata", item_id=theme_id)]
    issues: list[dict[str, Any]] = []
    if metadata.get("scheme") not in SCHEME_VALUES:
        issues.append(issue("selection_metadata_scheme_invalid", "selection_metadata.scheme is invalid", item_id=theme_id, path="selection_metadata.scheme"))
    for key in ("mood_tags", "primary_color_bias", "supported_template_ids"):
        if not non_empty_string_list(metadata.get(key)):
            issues.append(issue("selection_metadata_list_empty", f"selection_metadata.{key} must be a non-empty string array", item_id=theme_id, path=f"selection_metadata.{key}"))
    if not string_list(metadata.get("brand_affinity")):
        issues.append(issue("selection_metadata_list_invalid", "selection_metadata.brand_affinity must be a string array", item_id=theme_id, path="selection_metadata.brand_affinity"))
    if not isinstance(metadata.get("contrast_profile"), str) or not metadata.get("contrast_profile").strip():
        issues.append(issue("selection_metadata_contrast_profile_invalid", "selection_metadata.contrast_profile must be a non-empty string", item_id=theme_id, path="selection_metadata.contrast_profile"))
    if metadata.get("token_override_policy") not in TOKEN_OVERRIDE_VALUES:
        issues.append(issue("selection_metadata_token_override_policy_invalid", "selection_metadata.token_override_policy is invalid", item_id=theme_id, path="selection_metadata.token_override_policy"))
    return issues


def validate_palette_metadata(palette: dict[str, Any]) -> list[dict[str, Any]]:
    palette_id = str(palette.get("palette_id") or palette.get("id") or "<unknown-palette>")
    issues: list[dict[str, Any]] = []
    colors = palette.get("colors")
    if not isinstance(colors, dict):
        return [issue("palette_colors_missing", "active palette requires colors", item_id=palette_id, path="colors")]
    for key in ("background", "surface", "text", "muted", "primary", "accent"):
        if not valid_hex(colors.get(key)):
            issues.append(issue("palette_color_invalid", f"colors.{key} must be #RRGGBB", item_id=palette_id, path=f"colors.{key}"))
    data_series = palette.get("data_series")
    if not isinstance(data_series, list) or len(data_series) < 2 or not all(valid_hex(item) for item in data_series):
        issues.append(issue("palette_data_series_invalid", "data_series must contain at least two #RRGGBB colors", item_id=palette_id, path="data_series"))
    metadata = palette.get("selection_metadata")
    if not isinstance(metadata, dict):
        issues.append(issue("selection_metadata_missing", "active palette requires selection_metadata", item_id=palette_id, path="selection_metadata"))
    else:
        for key in ("best_for", "industry_tags", "tone_tags"):
            if not non_empty_string_list(metadata.get(key)):
                issues.append(issue("selection_metadata_list_empty", f"selection_metadata.{key} must be a non-empty string array", item_id=palette_id, path=f"selection_metadata.{key}"))
        if not string_list(metadata.get("avoid_for")):
            issues.append(issue("selection_metadata_list_invalid", "selection_metadata.avoid_for must be a string array", item_id=palette_id, path="selection_metadata.avoid_for"))
        if not string_list(metadata.get("brand_affinity")):
            issues.append(issue("selection_metadata_list_invalid", "selection_metadata.brand_affinity must be a string array", item_id=palette_id, path="selection_metadata.brand_affinity"))
        if metadata.get("density") not in DENSITY_VALUES:
            issues.append(issue("selection_metadata_density_invalid", "selection_metadata.density is invalid", item_id=palette_id, path="selection_metadata.density"))
        if metadata.get("formality") not in FORMALITY_VALUES:
            issues.append(issue("selection_metadata_formality_invalid", "selection_metadata.formality is invalid", item_id=palette_id, path="selection_metadata.formality"))
    source_trace = palette.get("source_trace")
    if not isinstance(source_trace, list) or not source_trace:
        issues.append(issue("palette_source_trace_missing", "active palette requires source_trace", item_id=palette_id, path="source_trace"))
    return issues


def validate_brand_palette_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    brand_id = str(record.get("brand_id") or "<unknown-brand>")
    issues: list[dict[str, Any]] = []
    if not non_empty_string_list(record.get("aliases")):
        issues.append(issue("brand_aliases_missing", "brand record requires aliases", item_id=brand_id, path="aliases"))
    palette = record.get("palette")
    if not isinstance(palette, dict):
        issues.append(issue("brand_palette_missing", "brand record requires palette", item_id=brand_id, path="palette"))
    else:
        for key in ("primary", "accent", "background", "text"):
            if not valid_hex(palette.get(key)):
                issues.append(issue("brand_palette_color_invalid", f"palette.{key} must be #RRGGBB", item_id=brand_id, path=f"palette.{key}"))
    if record.get("confidence") not in {"high", "medium", "low"}:
        issues.append(issue("brand_confidence_invalid", "confidence must be high, medium, or low", item_id=brand_id, path="confidence"))
    if not isinstance(record.get("source_trace"), list) or not record.get("source_trace"):
        issues.append(issue("brand_source_trace_missing", "brand record requires source_trace", item_id=brand_id, path="source_trace"))
    if not isinstance(record.get("updated_at"), str) or not record.get("updated_at"):
        issues.append(issue("brand_updated_at_missing", "brand record requires updated_at", item_id=brand_id, path="updated_at"))
    return issues


def resolve_repo_root(path: Path) -> Path:
    path = path.resolve()
    if (path / "skills/lark-slides").exists():
        return path
    return REPO_ROOT


def run_lint(repo_root: Path) -> dict[str, Any]:
    repo_root = resolve_repo_root(repo_root)
    references = repo_root / "skills" / "lark-slides" / "references"
    issues: list[dict[str, Any]] = []
    template_registry = beautiful_template_runtime.template_registry()
    theme_registry = beautiful_template_runtime.theme_registry()
    palette_registry = beautiful_template_runtime.palette_registry()
    brand_registry = load_json(references / "svglide-brand-palette-registry.json")

    templates = active_templates(template_registry)
    themes = active_themes(theme_registry)
    palettes = active_palettes(palette_registry)
    brands = brand_records(brand_registry)

    for template in templates:
        issues.extend(validate_template_metadata(template))
    for theme in themes:
        issues.extend(validate_theme_metadata(theme))
    for palette in palettes:
        issues.extend(validate_palette_metadata(palette))
    for record in brands:
        issues.extend(validate_brand_palette_record(record))

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "selection_metadata_lint",
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "summary": {
            "active_template_count": len(templates),
            "active_theme_count": len(themes),
            "active_palette_count": len(palettes),
            "brand_palette_count": len(brands),
            "error_count": len(issues),
        },
        "issues": issues,
    }


def write_outputs(root: Path, result: dict[str, Any]) -> None:
    for rel in (CHECK_PATH, RECEIPT_PATH):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint SVGlide selection metadata.")
    parser.add_argument("repo_root", nargs="?", default=REPO_ROOT.as_posix())
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    result = run_lint(root)
    if args.write:
        write_outputs(root, result)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
