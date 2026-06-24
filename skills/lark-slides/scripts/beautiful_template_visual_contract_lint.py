#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")
MATRIX_PATH = REFERENCES_DIR / "beautiful-template-executable-matrix.json"
FAMILIES_PATH = REFERENCES_DIR / "beautiful-html-template-families.json"

REQUIRED_MATRIX_FIELDS = {
    "family_id",
    "source_template_html",
    "source_design_md",
    "source_template_json",
    "reference_screenshot",
    "runtime_template_id",
    "visual_contract",
    "visual_contract_path",
    "promotion_status",
    "font_strategy",
    "typography_strategy",
    "text_style_strategy",
}
PLANNED_OR_ACTUAL_EVIDENCE_FIELDS = {
    "renderer_module": "planned_renderer_module",
    "golden_spec": "planned_golden_spec",
    "fidelity_receipt": "planned_fidelity_receipt",
}
REQUIRED_SOURCE_FIELDS = {
    "source_template_html",
    "source_design_md",
    "source_template_json",
    "reference_screenshot",
}
REQUIRED_CONTRACT_SECTIONS = {
    "layout",
    "typography",
    "palette",
    "decorative",
    "image",
    "component",
    "page_type",
    "satori",
    "font_strategy",
    "typography_strategy",
    "text_style_strategy",
    "do_not_simplify",
}
REQUIRED_STRATEGY_FIELDS = {
    "font_strategy": {
        "source_fonts",
        "slide_native_preferred",
        "adobe_or_embedded_fallback",
        "cjk_fallback",
        "role_mapping",
        "forbidden",
        "mapping_reason",
    },
    "typography_strategy": {
        "source_typography_tokens",
        "role_mapping",
        "font_size_scale",
        "font_weight_scale",
        "line_height_scale",
        "letter_spacing_scale",
        "word_spacing",
        "paragraph_spacing",
        "text_transform_policy",
        "hierarchy_ratio",
        "max_lines",
        "measure",
        "alignment",
        "wrapping_policy",
        "text_direction",
        "writing_mode",
        "cjk_typography_adjustment",
        "mapping_reason",
        "extraction_confidence",
        "source_refs",
    },
    "text_style_strategy": {
        "bold",
        "italic",
        "underline",
        "line_through",
        "emphasis",
        "text_decoration_policy",
        "forbidden",
        "extraction_confidence",
        "source_refs",
    },
}
REQUIRED_FONT_ROLES = {"display", "body", "label", "metric"}
EXTRACTION_CONFIDENCE_VALUES = {
    "direct_from_design_md",
    "css_extracted_from_template_html",
    "inferred_from_layout",
    "absent_use_default",
}
STRATEGY_EVIDENCE_FIELDS = {
    "font_strategy": {
        "source_fonts",
        "slide_native_preferred",
        "adobe_or_embedded_fallback",
        "cjk_fallback",
        "role_mapping.display",
        "role_mapping.body",
        "role_mapping.label",
        "role_mapping.metric",
        "forbidden",
        "mapping_reason",
    },
    "typography_strategy": {
        "source_typography_tokens",
        "role_mapping.display",
        "role_mapping.body",
        "role_mapping.label",
        "role_mapping.metric",
        "font_size_scale",
        "font_weight_scale",
        "line_height_scale",
        "letter_spacing_scale",
        "word_spacing",
        "paragraph_spacing",
        "text_transform_policy",
        "hierarchy_ratio",
        "max_lines",
        "measure",
        "alignment",
        "wrapping_policy",
        "text_direction",
        "writing_mode",
        "cjk_typography_adjustment",
        "mapping_reason",
    },
    "text_style_strategy": {
        "bold",
        "italic",
        "underline",
        "line_through",
        "emphasis",
        "text_decoration_policy.underline.style",
        "text_decoration_policy.underline.color",
        "text_decoration_policy.underline.thickness",
        "text_decoration_policy.line_through.style",
        "text_decoration_policy.line_through.color",
        "text_decoration_policy.line_through.thickness",
        "forbidden",
    },
}
ALLOWED_RUNTIME_FONTS = {
    "system-sans-cjk",
    "system-sans-cjk-regular",
    "system-sans-cjk-medium",
    "system-sans-cjk-heavy",
    "system-serif-cjk",
    "system-serif-cjk-regular",
    "system-serif-cjk-medium",
    "system-serif-cjk-heavy",
    "system-mono",
    "system-mono-cjk",
    "Source Sans Pro",
    "Source Serif Pro",
    "Source Code Pro",
    "思源黑体",
    "思源宋体",
    "思源等宽",
    "Noto Sans SC",
    "Noto Serif SC",
    "Noto Sans Mono CJK SC",
    "Feishu Sans",
    "Feishu Serif",
    "Feishu Mono",
}
PRODUCTION_STATUSES = {"production"}
NON_PRODUCTION_STATUSES = {"needs_review", "experimental", "legacy_debug"}
PAGE_FAMILY_REQUIRED_FIELDS = {
    "source_slide_count",
    "core_page_roles",
    "production_minimum_roles",
}
PAGE_VARIANT_REQUIRED_FIELDS = {
    "source_class",
    "page_role",
    "required_slots",
    "source_refs",
    "extraction_confidence",
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def resolve_path(value: object) -> Path:
    raw = str(value or "")
    path = Path(raw)
    if path.is_absolute():
        return path
    if raw.startswith(f"{SOURCE_ROOT.name}/"):
        return SOURCE_ROOT.parent / raw
    if raw.startswith("screenshots/") or raw.startswith("templates/"):
        return SOURCE_ROOT / raw
    return REPO_ROOT / raw


def is_non_empty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return value is not None


def source_paths_for_family(family: dict[str, Any]) -> dict[str, str]:
    source = family.get("source") if isinstance(family.get("source"), dict) else {}
    return {
        "source_template_html": str(source.get("source_template_html") or ""),
        "source_design_md": str(source.get("source_design_md") or ""),
        "source_template_json": str(source.get("source_template_json") or ""),
        "reference_screenshot": str(source.get("reference_screenshot") or ""),
    }


def matrix_rows(path: Path = MATRIX_PATH) -> list[dict[str, Any]]:
    payload = read_json(path)
    rows = payload.get("candidates")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def family_rows(path: Path = FAMILIES_PATH) -> list[dict[str, Any]]:
    payload = read_json(path)
    rows = payload.get("families")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def load_contract(value: object) -> tuple[Path | None, dict[str, Any] | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None
    path = resolve_path(value)
    if not path.is_file():
        return path, None
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return path, None
    return path, payload


def issue(code: str, message: str, *, family_id: str = "", path: str = "") -> dict[str, str]:
    result = {"code": code, "message": message}
    if family_id:
        result["family_id"] = family_id
    if path:
        result["path"] = path
    return result


def validate_production_role_consumption(row: dict[str, Any]) -> list[dict[str, str]]:
    family_id = str(row.get("family_id") or "")
    receipt_path = resolve_path(row.get("fidelity_receipt"))
    if not receipt_path.is_file():
        return []
    try:
        receipt = read_json(receipt_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return [
            issue(
                "candidate_production_fidelity_receipt_unreadable",
                "production candidate.fidelity_receipt must be readable JSON",
                family_id=family_id,
                path="fidelity_receipt",
            )
        ]
    role_consumption = receipt.get("role_consumption") if isinstance(receipt.get("role_consumption"), dict) else {}
    if not role_consumption:
        return [
            issue(
                "candidate_production_fidelity_role_consumption_missing",
                "production fidelity receipt must prove font_roles, typography_roles, and text_style_roles were consumed",
                family_id=family_id,
                path="fidelity_receipt.role_consumption",
            )
        ]
    issues: list[dict[str, str]] = []
    if not is_non_empty(role_consumption.get("source")):
        issues.append(
            issue(
                "candidate_production_fidelity_role_consumption_source_missing",
                "production fidelity receipt role_consumption.source is required",
                family_id=family_id,
                path="fidelity_receipt.role_consumption.source",
            )
        )
    for key in ("font_roles", "typography_roles"):
        roles = role_consumption.get(key) if isinstance(role_consumption.get(key), dict) else {}
        for role in sorted(REQUIRED_FONT_ROLES):
            if not is_non_empty(roles.get(role)):
                issues.append(
                    issue(
                        "candidate_production_fidelity_role_consumption_incomplete",
                        f"production fidelity receipt role_consumption.{key}.{role} is required",
                        family_id=family_id,
                        path=f"fidelity_receipt.role_consumption.{key}.{role}",
                    )
                )
    text_style_roles = role_consumption.get("text_style_roles") if isinstance(role_consumption.get("text_style_roles"), dict) else {}
    for key in ("bold", "italic", "underline", "line_through", "emphasis", "text_decoration_policy"):
        if not is_non_empty(text_style_roles.get(key)):
            issues.append(
                issue(
                    "candidate_production_fidelity_role_consumption_incomplete",
                    f"production fidelity receipt role_consumption.text_style_roles.{key} is required",
                    family_id=family_id,
                    path=f"fidelity_receipt.role_consumption.text_style_roles.{key}",
                )
            )
    return issues


def validate_contract(contract: dict[str, Any], row: dict[str, Any]) -> list[dict[str, str]]:
    family_id = str(row.get("family_id") or "")
    issues: list[dict[str, str]] = []
    if contract.get("family_id") != family_id:
        issues.append(issue("contract_family_id_mismatch", "contract.family_id must match matrix family_id", family_id=family_id, path="family_id"))
    if contract.get("runtime_template_id") != row.get("runtime_template_id"):
        issues.append(
            issue(
                "contract_runtime_template_id_mismatch",
                "contract.runtime_template_id must match matrix runtime_template_id",
                family_id=family_id,
                path="runtime_template_id",
            )
        )
    source = contract.get("source") if isinstance(contract.get("source"), dict) else {}
    for key in REQUIRED_SOURCE_FIELDS:
        if source.get(key) != row.get(key):
            issues.append(issue("contract_source_mismatch", f"contract.source.{key} must match matrix row", family_id=family_id, path=f"source.{key}"))
        elif not resolve_path(source.get(key)).is_file():
            issues.append(issue("contract_source_missing_file", f"contract.source.{key} must point to an existing file", family_id=family_id, path=f"source.{key}"))
    for section in sorted(REQUIRED_CONTRACT_SECTIONS):
        value = contract.get(section)
        if not is_non_empty(value):
            issues.append(issue("contract_required_section_missing", f"contract.{section} is required", family_id=family_id, path=section))
    issues.extend(validate_strategies(contract, family_id=family_id, path_prefix="contract"))
    return issues


def validate_page_family_contract(contract: dict[str, Any], *, family_id: str = "") -> list[dict[str, str]]:
    family = family_id or str(contract.get("family_id") or "")
    issues: list[dict[str, str]] = []
    page_family = contract.get("page_family")
    if not isinstance(page_family, dict) or not page_family:
        issues.append(issue("contract_page_family_missing", "contract.page_family is required", family_id=family, path="page_family"))
        page_family = {}
    for key in sorted(PAGE_FAMILY_REQUIRED_FIELDS):
        if not is_non_empty(page_family.get(key)):
            issues.append(
                issue(
                    "page_family_required_field_missing",
                    f"contract.page_family.{key} is required",
                    family_id=family,
                    path=f"page_family.{key}",
                )
            )
    if page_family.get("source_slide_count") is not None and not isinstance(page_family.get("source_slide_count"), int):
        issues.append(issue("page_family_source_slide_count_invalid", "page_family.source_slide_count must be an integer", family_id=family, path="page_family.source_slide_count"))
    for key in ("core_page_roles", "production_minimum_roles"):
        value = page_family.get(key)
        if value is not None and (not isinstance(value, list) or not all(is_non_empty(item) for item in value)):
            issues.append(issue("page_family_roles_invalid", f"page_family.{key} must be a non-empty string array", family_id=family, path=f"page_family.{key}"))

    page_variants = contract.get("page_variants")
    if not isinstance(page_variants, dict) or not page_variants:
        issues.append(issue("contract_page_variants_missing", "contract.page_variants is required", family_id=family, path="page_variants"))
        return issues
    for variant_id, variant in sorted(page_variants.items()):
        path_prefix = f"page_variants.{variant_id}"
        if not isinstance(variant, dict):
            issues.append(issue("page_variant_invalid", "page variant must be an object", family_id=family, path=path_prefix))
            continue
        for key in sorted(PAGE_VARIANT_REQUIRED_FIELDS):
            if not is_non_empty(variant.get(key)):
                issues.append(
                    issue(
                        "page_variant_required_field_missing",
                        f"{path_prefix}.{key} is required",
                        family_id=family,
                        path=f"{path_prefix}.{key}",
                    )
                )
        required_slots = variant.get("required_slots")
        if required_slots is not None and (not isinstance(required_slots, list) or not all(is_non_empty(item) for item in required_slots)):
            issues.append(issue("page_variant_required_slots_invalid", "required_slots must be a non-empty string array", family_id=family, path=f"{path_prefix}.required_slots"))
        confidence = variant.get("extraction_confidence")
        if confidence is not None and confidence not in EXTRACTION_CONFIDENCE_VALUES:
            issues.append(issue("page_variant_extraction_confidence_invalid", "page variant extraction_confidence is invalid", family_id=family, path=f"{path_prefix}.extraction_confidence"))
        refs = variant.get("source_refs")
        if refs is not None:
            if not isinstance(refs, list) or not refs:
                issues.append(issue("page_variant_source_refs_invalid", "source_refs must be a non-empty array", family_id=family, path=f"{path_prefix}.source_refs"))
            else:
                for index, ref in enumerate(refs):
                    ref_path = f"{path_prefix}.source_refs[{index}]"
                    if not isinstance(ref, dict):
                        issues.append(issue("page_variant_source_ref_invalid", "source_refs entries must be objects", family_id=family, path=ref_path))
                        continue
                    for key in ("path", "selector_or_token", "raw_value"):
                        if not is_non_empty(ref.get(key)):
                            issues.append(issue("page_variant_source_ref_field_missing", f"source_refs entries must include {key}", family_id=family, path=f"{ref_path}.{key}"))
                    if is_non_empty(ref.get("path")) and not resolve_path(ref.get("path")).is_file():
                        issues.append(issue("page_variant_source_ref_missing_file", "source_refs.path must point to an existing source file", family_id=family, path=f"{ref_path}.path"))
    declared_count = page_family.get("source_slide_count")
    if isinstance(declared_count, int) and declared_count != len(page_variants):
        issues.append(
            issue(
                "page_family_variant_count_mismatch",
                "page_family.source_slide_count must match extracted page_variants count",
                family_id=family,
                path="page_family.source_slide_count",
            )
        )
    return issues


def validate_page_family_candidate(row: dict[str, Any]) -> list[dict[str, str]]:
    family_id = str(row.get("family_id") or "")
    issues: list[dict[str, str]] = []
    status = str(row.get("promotion_status") or "")
    is_default = row.get("default_selectable") is True
    gate = row.get("page_family_promotion_gate") if isinstance(row.get("page_family_promotion_gate"), dict) else {}
    migration_block = row.get("migration_block") if isinstance(row.get("migration_block"), dict) else {}
    smoke_receipt = row.get("page_family_smoke_receipt")
    smoke_deck = row.get("page_family_smoke_deck")
    golden_specs = row.get("page_variant_golden_specs")
    has_smoke_receipt = is_non_empty(smoke_receipt)
    has_smoke_deck = is_non_empty(smoke_deck)

    if has_smoke_deck and not resolve_path(smoke_deck).is_file():
        issues.append(
            issue(
                "page_family_smoke_deck_missing_file",
                "page_family_smoke_deck must point to an existing smoke deck",
                family_id=family_id,
                path="page_family_smoke_deck",
            )
        )
    if has_smoke_receipt and not resolve_path(smoke_receipt).is_file():
        issues.append(
            issue(
                "page_family_smoke_receipt_missing_file",
                "page_family_smoke_receipt must point to an existing receipt",
                family_id=family_id,
                path="page_family_smoke_receipt",
            )
        )
    elif has_smoke_receipt:
        receipt = read_json_or_empty(resolve_path(smoke_receipt))
        if not isinstance(receipt.get("input_hashes"), dict) or not receipt.get("input_hashes"):
            issues.append(issue("page_family_smoke_receipt_input_hashes_missing", "page_family_smoke_receipt must include non-empty input_hashes", family_id=family_id, path="page_family_smoke_receipt.input_hashes"))
        if not isinstance(receipt.get("provenance"), dict) or not receipt.get("provenance"):
            issues.append(issue("page_family_smoke_receipt_provenance_missing", "page_family_smoke_receipt must include provenance", family_id=family_id, path="page_family_smoke_receipt.provenance"))
    if isinstance(golden_specs, dict):
        for variant_id, raw_path in sorted(golden_specs.items()):
            if not is_non_empty(raw_path) or not resolve_path(raw_path).is_file():
                issues.append(issue("page_variant_golden_spec_missing_file", "page_variant_golden_specs entries must point to existing golden specs", family_id=family_id, path=f"page_variant_golden_specs.{variant_id}"))
    if gate.get("status") == "passed":
        if not has_smoke_receipt:
            issues.append(issue("page_family_gate_passed_without_smoke", "passed page_family_promotion_gate requires page_family_smoke_receipt", family_id=family_id, path="page_family_smoke_receipt"))
        if not has_smoke_deck:
            issues.append(issue("page_family_gate_passed_without_smoke_deck", "passed page_family_promotion_gate requires page_family_smoke_deck", family_id=family_id, path="page_family_smoke_deck"))
        if not is_non_empty(row.get("implemented_page_variants")):
            issues.append(issue("page_family_gate_passed_without_implemented_variants", "passed page_family_promotion_gate requires implemented_page_variants", family_id=family_id, path="implemented_page_variants"))
        if not isinstance(golden_specs, dict) or not golden_specs:
            issues.append(issue("page_family_gate_passed_without_golden_specs", "passed page_family_promotion_gate requires page_variant_golden_specs", family_id=family_id, path="page_variant_golden_specs"))
        else:
            for variant_id in row.get("implemented_page_variants", []) if isinstance(row.get("implemented_page_variants"), list) else []:
                if variant_id not in golden_specs:
                    issues.append(issue("page_family_gate_passed_variant_without_golden_spec", "every implemented page variant must have a golden spec", family_id=family_id, path=f"page_variant_golden_specs.{variant_id}"))

    if status in PRODUCTION_STATUSES or is_default:
        is_migration_blocked = gate.get("status") == "migration_blocked" or migration_block.get("page_family_smoke_missing") is True
        if not has_smoke_receipt and not is_migration_blocked:
            issues.append(
                issue(
                    "production_page_family_smoke_missing",
                    "production/default selectable beautiful family must have page-family smoke evidence or an explicit migration block",
                    family_id=family_id,
                    path="page_family_smoke_receipt",
                )
            )
    return issues


def _role_font_name(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("slide_font", "font", "family", "alias"):
            raw = value.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return ""


def _role_is_source_only_or_download(value: object) -> bool:
    return isinstance(value, dict) and (value.get("source_only") is True or value.get("requires_download") is True)


def _strategy_signature(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _value_at_path(value: object, field_path: str) -> object:
    current = value
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current.get(part)
    return current


def _validate_source_refs(refs: object, *, family_id: str, strategy_name: str, field_path: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(refs, list) or not refs:
        return [
            issue(
                "strategy_source_refs_missing",
                "non-default extracted or inferred strategy field must include source_refs",
                family_id=family_id,
                path=f"{strategy_name}.source_refs.{field_path}",
            )
        ]
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            issues.append(
                issue(
                    "strategy_source_ref_invalid",
                    "source_refs entries must be objects",
                    family_id=family_id,
                    path=f"{strategy_name}.source_refs.{field_path}[{index}]",
                )
            )
            continue
        for key in ("path", "selector_or_token", "raw_value"):
            if not is_non_empty(ref.get(key)):
                issues.append(
                    issue(
                        "strategy_source_ref_field_missing",
                        "source_refs entries must include path, selector_or_token, and raw_value",
                        family_id=family_id,
                        path=f"{strategy_name}.source_refs.{field_path}[{index}].{key}",
                    )
                )
        if is_non_empty(ref.get("path")) and not resolve_path(ref.get("path")).is_file():
            issues.append(
                issue(
                    "strategy_source_ref_missing_file",
                    "source_refs.path must point to an existing source file",
                    family_id=family_id,
                    path=f"{strategy_name}.source_refs.{field_path}[{index}].path",
                )
            )
    return issues


def _source_style_flags(row: dict[str, Any]) -> dict[str, bool]:
    chunks: list[str] = []
    for key in ("source_template_html", "source_design_md", "source_template_json"):
        path = resolve_path(row.get(key))
        if path.is_file():
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    blob = "\n".join(chunks).lower()
    return {
        "italic": "italic" in blob or "font-style" in blob or "<em" in blob,
        "underline": "underline" in blob or "text-decoration" in blob,
        "line_through": "line-through" in blob,
        "text_transform": "text-transform" in blob or "uppercase" in blob or "lowercase" in blob,
        "letter_spacing": "letter-spacing" in blob or "letterspacing" in blob,
    }


def validate_strategies(container: dict[str, Any], *, family_id: str, path_prefix: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for section, required_fields in REQUIRED_STRATEGY_FIELDS.items():
        strategy = container.get(section)
        if not isinstance(strategy, dict) or not strategy:
            issues.append(issue("strategy_required_section_missing", f"{path_prefix}.{section} is required", family_id=family_id, path=section))
            continue
        for key in sorted(required_fields):
            if not is_non_empty(strategy.get(key)):
                issues.append(
                    issue(
                        "strategy_required_field_missing",
                        f"{path_prefix}.{section}.{key} is required",
                        family_id=family_id,
                        path=f"{section}.{key}",
                    )
                )
        confidence = strategy.get("extraction_confidence")
        source_refs = strategy.get("source_refs")
        if not isinstance(confidence, dict) or not confidence:
            issues.append(issue("strategy_extraction_confidence_missing", f"{path_prefix}.{section}.extraction_confidence is required", family_id=family_id, path=f"{section}.extraction_confidence"))
            confidence = {}
        if not isinstance(source_refs, dict):
            issues.append(issue("strategy_source_refs_invalid", f"{path_prefix}.{section}.source_refs must be an object", family_id=family_id, path=f"{section}.source_refs"))
            source_refs = {}
        for field_path in sorted(STRATEGY_EVIDENCE_FIELDS.get(section, set())):
            if not is_non_empty(_value_at_path(strategy, field_path)):
                issues.append(
                    issue(
                        "strategy_required_field_missing",
                        f"{path_prefix}.{section}.{field_path} is required",
                        family_id=family_id,
                        path=f"{section}.{field_path}",
                    )
                )
            field_confidence = confidence.get(field_path) if isinstance(confidence, dict) else None
            if field_confidence not in EXTRACTION_CONFIDENCE_VALUES:
                issues.append(
                    issue(
                        "strategy_extraction_confidence_invalid",
                        "each strategy field must have a valid extraction_confidence",
                        family_id=family_id,
                        path=f"{section}.extraction_confidence.{field_path}",
                    )
                )
                continue
            if field_confidence != "absent_use_default":
                issues.extend(
                    _validate_source_refs(
                        source_refs.get(field_path) if isinstance(source_refs, dict) else None,
                        family_id=family_id,
                        strategy_name=section,
                        field_path=field_path,
                    )
                )
    font_strategy = container.get("font_strategy") if isinstance(container.get("font_strategy"), dict) else {}
    source_fonts = font_strategy.get("source_fonts") if isinstance(font_strategy.get("source_fonts"), list) else []
    for index, raw_font in enumerate(source_fonts):
        font = str(raw_font or "")
        if len(font) > 48 or "`" in font or "\n" in font:
            issues.append(
                issue(
                    "font_strategy_source_font_invalid",
                    "source_fonts must contain font family names, not prose fragments",
                    family_id=family_id,
                    path=f"font_strategy.source_fonts[{index}]",
                )
            )
    font_roles = font_strategy.get("role_mapping") if isinstance(font_strategy.get("role_mapping"), dict) else {}
    missing_roles = REQUIRED_FONT_ROLES - set(font_roles)
    for role in sorted(missing_roles):
        issues.append(issue("font_strategy_role_missing", f"font_strategy.role_mapping.{role} is required", family_id=family_id, path=f"font_strategy.role_mapping.{role}"))
    for role in sorted(REQUIRED_FONT_ROLES & set(font_roles)):
        role_value = font_roles.get(role)
        runtime_font = _role_font_name(role_value)
        if runtime_font not in ALLOWED_RUNTIME_FONTS and not _role_is_source_only_or_download(role_value):
            issues.append(
                issue(
                    "font_strategy_role_font_not_allowed",
                    "role font must use Slide/system/embedded allowlist, or be marked source_only/requires_download",
                    family_id=family_id,
                    path=f"font_strategy.role_mapping.{role}",
                )
            )
        if isinstance(role_value, dict) and not is_non_empty(role_value.get("source_font")):
            issues.append(
                issue(
                    "font_strategy_role_source_font_missing",
                    "role mapping must retain source font evidence",
                    family_id=family_id,
                    path=f"font_strategy.role_mapping.{role}.source_font",
                )
            )
    role_fonts = [_role_font_name(font_roles.get(role)) for role in sorted(REQUIRED_FONT_ROLES)]
    if len({font for font in role_fonts if font}) == 1 and not is_non_empty(font_strategy.get("same_role_font_justification")):
        issues.append(
            issue(
                "font_strategy_same_role_font_missing_justification",
                "families mapping all four roles to one runtime font must explain why",
                family_id=family_id,
                path="font_strategy.same_role_font_justification",
            )
        )
    typography = container.get("typography_strategy") if isinstance(container.get("typography_strategy"), dict) else {}
    typography_roles = typography.get("role_mapping") if isinstance(typography.get("role_mapping"), dict) else {}
    for role in sorted(REQUIRED_FONT_ROLES - set(typography_roles)):
        issues.append(
            issue(
                "typography_strategy_role_missing",
                f"typography_strategy.role_mapping.{role} is required",
                family_id=family_id,
                path=f"typography_strategy.role_mapping.{role}",
            )
        )
    text_style = container.get("text_style_strategy") if isinstance(container.get("text_style_strategy"), dict) else {}
    for key in ("bold", "italic", "underline", "line_through"):
        value = text_style.get(key)
        if not isinstance(value, dict):
            issues.append(issue("text_style_strategy_section_invalid", f"text_style_strategy.{key} must be an object", family_id=family_id, path=f"text_style_strategy.{key}"))
    emphasis = text_style.get("emphasis")
    if isinstance(emphasis, dict):
        for key in ("color_shift", "font_family_switch", "weight_shift", "style_shift"):
            if key not in emphasis:
                issues.append(issue("text_style_emphasis_field_missing", f"text_style_strategy.emphasis.{key} is required", family_id=family_id, path=f"text_style_strategy.emphasis.{key}"))
    decoration_policy = text_style.get("text_decoration_policy") if isinstance(text_style.get("text_decoration_policy"), dict) else {}
    for group in ("underline", "line_through"):
        group_value = decoration_policy.get(group) if isinstance(decoration_policy.get(group), dict) else {}
        for key in ("style", "color", "thickness"):
            if not is_non_empty(group_value.get(key)):
                issues.append(
                    issue(
                        "text_decoration_policy_field_missing",
                        f"text_style_strategy.text_decoration_policy.{group}.{key} is required",
                        family_id=family_id,
                        path=f"text_style_strategy.text_decoration_policy.{group}.{key}",
                    )
                )
    return issues


def validate_candidate_matrix(
    *,
    matrix_path: Path = MATRIX_PATH,
    families_path: Path = FAMILIES_PATH,
    page_family_mode: str = "deferred",
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    rows = matrix_rows(matrix_path)
    families = {str(family.get("template_id") or ""): family for family in family_rows(families_path)}
    row_by_family = {str(row.get("family_id") or ""): row for row in rows}

    if len(rows) != 34:
        issues.append(issue("candidate_count_not_34", "beautiful candidate matrix must contain 34 rows"))
    if set(row_by_family) != set(families):
        issues.append(issue("candidate_family_set_mismatch", "candidate matrix families must match beautiful family registry"))

    for family_id, family in sorted(families.items()):
        row = row_by_family.get(family_id)
        if row is None:
            issues.append(issue("candidate_missing_family", "candidate row is missing", family_id=family_id))
            continue
        missing = REQUIRED_MATRIX_FIELDS - set(row)
        for key in sorted(missing):
            issues.append(issue("candidate_required_field_missing", f"candidate.{key} is required", family_id=family_id, path=key))
        for key in sorted(REQUIRED_MATRIX_FIELDS & set(row)):
            if not is_non_empty(row.get(key)):
                issues.append(issue("candidate_required_field_empty", f"candidate.{key} must be non-empty", family_id=family_id, path=key))
        issues.extend(validate_strategies(row, family_id=family_id, path_prefix="candidate"))
        has_actual_renderer = is_non_empty(row.get("renderer_module"))
        if not has_actual_renderer:
            for actual_key in ("renderer_id", "golden_spec", "fidelity_receipt"):
                if is_non_empty(row.get(actual_key)):
                    issues.append(
                        issue(
                            "candidate_unfinished_actual_evidence_present",
                            f"unfinished renderer candidate must not fill actual {actual_key}; use planned_* fields until renderer/fidelity exists",
                            family_id=family_id,
                            path=actual_key,
                        )
                    )
            fidelity_gate = row.get("fidelity_gate") if isinstance(row.get("fidelity_gate"), dict) else {}
            if fidelity_gate.get("status") not in {None, "", "not_run"}:
                issues.append(
                    issue(
                        "candidate_unfinished_fidelity_status_invalid",
                        "unfinished renderer candidate fidelity_gate.status must be not_run",
                        family_id=family_id,
                        path="fidelity_gate.status",
                    )
                )
        for actual_key, planned_key in PLANNED_OR_ACTUAL_EVIDENCE_FIELDS.items():
            actual = row.get(actual_key)
            planned = row.get(planned_key)
            if not is_non_empty(actual) and not is_non_empty(planned):
                issues.append(
                    issue(
                        "candidate_evidence_or_plan_missing",
                        f"candidate must include either {actual_key} or {planned_key}",
                        family_id=family_id,
                        path=actual_key,
                    )
                )
            if is_non_empty(actual) and not resolve_path(actual).is_file():
                issues.append(
                    issue(
                        "candidate_actual_evidence_missing_file",
                        f"candidate.{actual_key} is an actual evidence field and must point to an existing file",
                        family_id=family_id,
                        path=actual_key,
                    )
                )
        if row.get("template_id") and row.get("runtime_template_id") and row.get("template_id") != row.get("runtime_template_id"):
            issues.append(issue("candidate_template_id_mismatch", "template_id and runtime_template_id must match", family_id=family_id, path="runtime_template_id"))
        expected_sources = source_paths_for_family(family)
        for key, expected in expected_sources.items():
            actual = row.get(key)
            if actual != expected:
                issues.append(issue("candidate_source_mismatch", f"candidate.{key} must match family source", family_id=family_id, path=key))
            if actual and not resolve_path(actual).is_file():
                issues.append(issue("candidate_source_missing_file", f"candidate.{key} must point to an existing file", family_id=family_id, path=key))
        status = str(row.get("promotion_status") or "")
        is_default = row.get("default_selectable") is True
        if status in PRODUCTION_STATUSES or is_default:
            for key in ("renderer_module", "golden_spec", "fidelity_receipt"):
                if not resolve_path(row.get(key)).is_file():
                    issues.append(issue("candidate_production_evidence_missing_file", f"production candidate.{key} must exist", family_id=family_id, path=key))
            issues.extend(validate_production_role_consumption(row))
            if status not in PRODUCTION_STATUSES or not is_default:
                issues.append(issue("candidate_production_status_inconsistent", "production candidates must be default selectable and vice versa", family_id=family_id))
        elif status not in NON_PRODUCTION_STATUSES:
            issues.append(issue("candidate_promotion_status_invalid", "promotion_status must be production, needs_review, experimental, or legacy_debug", family_id=family_id, path="promotion_status"))

        contract_ref = row.get("visual_contract_path") or row.get("visual_contract")
        contract_path, contract = load_contract(contract_ref)
        if contract is None:
            issues.append(
                issue(
                    "candidate_visual_contract_missing_file",
                    f"visual_contract_path must point to a readable JSON file: {contract_path or contract_ref}",
                    family_id=family_id,
                    path="visual_contract_path",
                )
            )
        else:
            issues.extend(validate_contract(contract, row))
            if page_family_mode == "strict" or is_non_empty(contract.get("page_family")) or is_non_empty(contract.get("page_variants")):
                issues.extend(validate_page_family_contract(contract, family_id=family_id))
            for strategy_key in ("font_strategy", "typography_strategy", "text_style_strategy"):
                if row.get(strategy_key) != contract.get(strategy_key):
                    issues.append(
                        issue(
                            "candidate_contract_strategy_mismatch",
                            f"candidate.{strategy_key} must match visual contract",
                            family_id=family_id,
                            path=strategy_key,
                        )
                    )
        flags = _source_style_flags(row)
        typography = row.get("typography_strategy") if isinstance(row.get("typography_strategy"), dict) else {}
        text_style = row.get("text_style_strategy") if isinstance(row.get("text_style_strategy"), dict) else {}
        if flags["italic"] and not is_non_empty((text_style.get("italic") if isinstance(text_style.get("italic"), dict) else {}).get("source_usage")):
            issues.append(issue("source_italic_mapping_missing", "source italic usage must be recorded or mapped as loss", family_id=family_id, path="text_style_strategy.italic.source_usage"))
        if flags["underline"] and not is_non_empty((text_style.get("underline") if isinstance(text_style.get("underline"), dict) else {}).get("source_usage")):
            issues.append(issue("source_underline_mapping_missing", "source underline/text-decoration usage must be recorded or mapped as loss", family_id=family_id, path="text_style_strategy.underline.source_usage"))
        if flags["line_through"] and not is_non_empty((text_style.get("line_through") if isinstance(text_style.get("line_through"), dict) else {}).get("source_usage")):
            issues.append(issue("source_line_through_mapping_missing", "source line-through usage must be recorded or mapped as loss", family_id=family_id, path="text_style_strategy.line_through.source_usage"))
        if flags["text_transform"] and not is_non_empty(typography.get("text_transform_policy")):
            issues.append(issue("source_text_transform_mapping_missing", "source text-transform usage must be recorded", family_id=family_id, path="typography_strategy.text_transform_policy"))
        if flags["letter_spacing"] and not is_non_empty(typography.get("letter_spacing_scale")):
            issues.append(issue("source_letter_spacing_mapping_missing", "source letter-spacing usage must be recorded", family_id=family_id, path="typography_strategy.letter_spacing_scale"))
        if page_family_mode == "strict" or any(is_non_empty(row.get(key)) for key in ("page_family_smoke_receipt", "page_family_promotion_gate", "migration_block", "implemented_page_variants")):
            issues.extend(validate_page_family_candidate(row))
    font_signatures = {_strategy_signature(row.get("font_strategy", {}).get("role_mapping", {})) for row in rows if isinstance(row.get("font_strategy"), dict)}
    typography_signatures = {_strategy_signature(row.get("typography_strategy", {})) for row in rows if isinstance(row.get("typography_strategy"), dict)}
    if len(rows) == 34 and len(font_signatures) <= 1:
        issues.append(issue("font_strategy_all_families_identical", "34 families must not share one identical font role mapping"))
    if len(rows) == 34 and len(typography_signatures) <= 1:
        issues.append(issue("typography_strategy_all_families_identical", "34 families must not share one identical typography strategy"))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint beautiful template visual contracts and executable matrix.")
    parser.add_argument("--page-family-strict", action="store_true", help="also require page-family contract and production smoke evidence")
    args = parser.parse_args()
    issues = validate_candidate_matrix(page_family_mode="strict" if args.page_family_strict else "deferred")
    print(json.dumps({"status": "passed" if not issues else "failed", "issues": issues}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
