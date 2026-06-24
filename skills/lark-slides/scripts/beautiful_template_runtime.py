#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")
FAMILIES_PATH = REFERENCES_DIR / "beautiful-html-template-families.json"
BRAND_PALETTE_PATH = REFERENCES_DIR / "svglide-brand-palette-registry.json"
EXECUTABLE_MATRIX_PATH = REFERENCES_DIR / "beautiful-template-executable-matrix.json"

LEGACY_THEME_COLORS: dict[str, dict[str, str]] = {
    "acid-studio": {"background": "#1C1C1C", "panel": "#242422", "primary": "#F5D200", "accent": "#F0CC00", "text": "#F5D200", "muted": "#9A860C"},
    "blueprint-technical": {"background": "#071827", "panel": "#0E2A3F", "primary": "#5EEAD4", "accent": "#F97316", "text": "#EAF6FF", "muted": "#93B4C8"},
    "cobalt-grid": {"background": "#081C4A", "panel": "#102C6B", "primary": "#60A5FA", "accent": "#FDE047", "text": "#EEF6FF", "muted": "#B7C8E8"},
    "dark-clarity": {"background": "#0F172A", "panel": "#111827", "primary": "#38BDF8", "accent": "#A78BFA", "text": "#F8FAFC", "muted": "#CBD5E1"},
    "editorial-tritone": {"background": "#F6E7DF", "panel": "#FFF7F0", "primary": "#9F1239", "accent": "#D97706", "text": "#351A24", "muted": "#7C5B62"},
    "field-notebook": {"background": "#F8E8B8", "panel": "#FFF7D6", "primary": "#C2410C", "accent": "#1D4ED8", "text": "#3B2F22", "muted": "#6B5B45"},
    "finance-dark": {"background": "#07110E", "panel": "#10201A", "primary": "#22C55E", "accent": "#F59E0B", "text": "#ECFDF5", "muted": "#A7C4B7"},
    "forest-editorial": {"background": "#EFE7D4", "panel": "#E6DCC4", "primary": "#2E4A2A", "accent": "#E89CB1", "text": "#1A1A17", "muted": "#50634B"},
    "forest-signal": {"background": "#0B1F1A", "panel": "#123329", "primary": "#34D399", "accent": "#FBBF24", "text": "#F7FCEB", "muted": "#B7D3C6"},
    "glass-neon": {"background": "#090B1A", "panel": "#14172E", "primary": "#22D3EE", "accent": "#C084FC", "text": "#F8FAFC", "muted": "#BAC3D9"},
    "ivory-ledger": {"background": "#FAFADF", "panel": "#F5F0E4", "primary": "#1A1A16", "accent": "#5E5E54", "text": "#1A1A16", "muted": "#5E5E54"},
    "magazine-cobalt": {"background": "#F0EBDE", "panel": "#E6E0CE", "primary": "#1F2BE0", "accent": "#5560E5", "text": "#171B2F", "muted": "#4F5AB8"},
    "paper-research": {"background": "#F7F3E8", "panel": "#FFFDF6", "primary": "#1E3A8A", "accent": "#B45309", "text": "#1F2937", "muted": "#4B5563"},
    "raw-grid-mono": {"background": "#F7F2E8", "panel": "#FDE68A", "primary": "#111111", "accent": "#22C55E", "text": "#111111", "muted": "#44403C"},
    "retro-desktop": {"background": "#C0C0C0", "panel": "#D4D0C8", "primary": "#000080", "accent": "#FFFFFF", "text": "#222222", "muted": "#555555"},
    "sakura-catalog": {"background": "#F1E6CB", "panel": "#E54489", "primary": "#E5392A", "accent": "#F09131", "text": "#3A2516", "muted": "#3F8BC4"},
    "signal-navy": {"background": "#1C2644", "panel": "#232F55", "primary": "#C8A870", "accent": "#C8A870", "text": "#E2DCD0", "muted": "#8A96A8"},
    "stone-architect": {"background": "#EFE9DC", "panel": "#F8F4EA", "primary": "#5F5549", "accent": "#A28A6A", "text": "#27221D", "muted": "#756B60"},
    "swiss-red": {"background": "#F8F8F4", "panel": "#FFFFFF", "primary": "#BE123C", "accent": "#111111", "text": "#111111", "muted": "#666666"},
    "terracotta-program": {"background": "#FAF1E2", "panel": "#F2E5CF", "primary": "#B53D2A", "accent": "#8E2D1F", "text": "#3A2516", "muted": "#8E2D1F"},
    "tomato-poster": {"background": "#FFFFFF", "panel": "#F5F2EF", "primary": "#D8000F", "accent": "#1C1410", "text": "#1C1410", "muted": "#5A4036"},
    "warm-editorial": {"background": "#27130F", "panel": "#3A211B", "primary": "#F97316", "accent": "#22D3EE", "text": "#FFF7ED", "muted": "#F4C9A8"},
}

TEMPLATE_IDS = [
    "cover-hero",
    "comparison-cards",
    "summary-final",
    "section-title",
    "agenda-list",
    "timeline-steps",
    "process-flow",
    "metric-dashboard",
    "quote-focus",
    "image-feature",
    "research-poster",
    "data-story",
    "risk-alert",
    "roadmap-lanes",
    "architecture-blueprint",
    "dense-panel-grid",
    "executive-dashboard",
    "editorial-quote-chart",
    "ledger-briefing",
    "intelligence-brief",
    "printed-program",
    "retro-ui-dashboard",
    "product-ribbon",
    "type-mass-poster",
    "brutalist-matrix",
    "annotated-field-board",
    "architectural-spec",
    "trend-grid-report",
    "serif-stat-editorial",
    "poster-stat-punch",
    "coral-magazine-feature",
    "soft-editorial-feature",
    "tritone-editorial-spread",
    "pixel-orbit-console",
    "biennale-programme-poster",
    "block-frame-grid",
    "capsule-card-system",
    "creative-mode-grid",
    "daisy-workshop-playbook",
    "emerald-editorial-cover",
    "grove-organic-brief",
    "mat-midcentury-board",
    "people-platform-manifesto",
    "pink-nocturne-feature",
    "playful-indie-launch",
    "retro-zine-spread",
    "sticky-workshop-board",
    "stencil-field-manual",
    "vellum-scholar-brief",
]

LEGACY_TEMPLATE_IDS = frozenset(
    {
        "cover-hero",
        "comparison-cards",
        "summary-final",
        "section-title",
        "agenda-list",
        "timeline-steps",
        "process-flow",
        "metric-dashboard",
        "quote-focus",
        "image-feature",
        "research-poster",
        "data-story",
        "risk-alert",
        "roadmap-lanes",
        "architecture-blueprint",
    }
)
PRODUCTION_TEMPLATE_IDS = frozenset(set(TEMPLATE_IDS) - set(LEGACY_TEMPLATE_IDS))

TEMPLATE_OVERRIDES: dict[str, dict[str, Any]] = {
    "cover-hero": {"required_content": ["title"], "max_items": {"chips": 4}, "text_budget": {"title": 32, "subtitle": 80, "chips": 16}},
    "comparison-cards": {
        "required_content": ["title", "left_title", "right_title", "left_points", "right_points"],
        "max_items": {"left_points": 3, "right_points": 3},
        "text_budget": {"title": 36, "left_title": 16, "right_title": 16, "left_points": 22, "right_points": 22, "conclusion": 52},
    },
    "agenda-list": {"required_content": ["title", "items"], "max_items": {"items": 6}, "text_budget": {"title": 36, "items": 28}},
    "summary-final": {"required_content": ["title"], "max_items": {"takeaways": 3}, "text_budget": {"title": 34, "subtitle": 76, "takeaways": 24}},
}

FORMALITY_VALUES = {"low", "medium", "medium-high", "high"}
RUNTIME_STATUS_ACTIVE = "active"
ASSET_STATUS_PRODUCTION = "production"
ASSET_STATUS_LEGACY_DEBUG = "legacy_debug"
ASSET_STATUS_DEPRECATED = "deprecated"
QUALITY_TIER_TRUSTED = "trusted"
QUALITY_TIER_FIXTURE_ONLY = "fixture_only"
PRODUCTION_THEME_IDS = frozenset(
    {
        "paper-research",
        "swiss-red",
        "stone-architect",
        "forest-editorial",
        "editorial-tritone",
        "ivory-ledger",
    }
)
LEGACY_THEME_IDS = frozenset(set(LEGACY_THEME_COLORS) - set(PRODUCTION_THEME_IDS))
DARK_BACKGROUND_HEX = {
    "#0F172A",
    "#071827",
    "#081C4A",
    "#07110E",
    "#090B1A",
    "#27130F",
    "#1C2644",
    "#0B1F1A",
    "#1C1C1C",
}
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


@lru_cache(maxsize=8)
def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def family_registry(path: Path = FAMILIES_PATH) -> dict[str, Any]:
    return read_json(path)


def families(path: Path = FAMILIES_PATH) -> list[dict[str, Any]]:
    raw = family_registry(path).get("families")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def executable_matrix_candidates(path: Path = EXECUTABLE_MATRIX_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = read_json(path)
    raw = payload.get("candidates") or payload.get("templates")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def executable_matrix_by_runtime_template_id(path: Path = EXECUTABLE_MATRIX_PATH) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in executable_matrix_candidates(path):
        template_id = str(row.get("runtime_template_id") or row.get("template_id") or "").strip()
        if template_id:
            records[template_id] = row
    return records


def _copy_if_present(target: dict[str, Any], source: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if value not in (None, "", [], {}):
        target[key] = value


def _matrix_execution_metadata(row: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in (
        "family_id",
        "renderer_id",
        "renderer_module",
        "golden_spec",
        "reference_screenshot",
        "fidelity_receipt",
        "fidelity_gate",
        "visual_contract",
        "visual_contract_path",
        "font_strategy",
        "typography_strategy",
        "text_style_strategy",
        "source_trace",
        "planned_renderer_module",
        "planned_golden_spec",
        "page_family",
        "page_variants",
        "implemented_page_variants",
        "supported_page_variants",
        "page_family_smoke_deck",
        "page_family_smoke_receipt",
        "page_family_promotion_gate",
    ):
        _copy_if_present(metadata, row, key)
    family_id = row.get("family_id")
    if isinstance(family_id, str) and family_id.strip():
        metadata.setdefault("source_family", family_id.strip())
        metadata.setdefault("source_template_id", family_id.strip())
    visual_contract = metadata.get("visual_contract")
    if isinstance(visual_contract, dict) and visual_contract.get("path") and not metadata.get("visual_contract_path"):
        metadata["visual_contract_path"] = visual_contract["path"]
    return metadata


def merge_executable_matrix_metadata(record: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return record
    for key, value in _matrix_execution_metadata(row).items():
        if key == "source_trace" and record.get("source_trace"):
            continue
        record[key] = value
    return record


def runtime_asset_metadata(asset_status: str) -> dict[str, Any]:
    if asset_status == ASSET_STATUS_PRODUCTION:
        return {
            "status": RUNTIME_STATUS_ACTIVE,
            "asset_status": ASSET_STATUS_PRODUCTION,
            "quality_tier": QUALITY_TIER_TRUSTED,
            "default_selectable": True,
            "selection_scope": "production",
        }
    if asset_status == ASSET_STATUS_LEGACY_DEBUG:
        return {
            "status": ASSET_STATUS_LEGACY_DEBUG,
            "asset_status": ASSET_STATUS_LEGACY_DEBUG,
            "quality_tier": QUALITY_TIER_FIXTURE_ONLY,
            "default_selectable": False,
            "selection_scope": "debug",
            "legacy_reason": "legacy theme retained for explicit fixture/debug compatibility",
        }
    return {
        "status": ASSET_STATUS_DEPRECATED,
        "asset_status": ASSET_STATUS_DEPRECATED,
        "quality_tier": QUALITY_TIER_FIXTURE_ONLY,
        "default_selectable": False,
        "selection_scope": "fixture",
    }


def mapping_asset_ids(family: dict[str, Any]) -> list[str]:
    mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
    raw = mapping.get("svglide_asset_ids")
    return [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []


def mapped_runtime_theme_id(family: dict[str, Any]) -> str | None:
    known_theme_ids = set(LEGACY_THEME_COLORS) | set(promoted_theme_ids())
    for item in mapping_asset_ids(family):
        if not item.startswith("theme."):
            continue
        candidate = item.removeprefix("theme.").replace("_", "-")
        if candidate in known_theme_ids:
            return candidate
    return None


def promoted_theme_ids() -> list[str]:
    return [record["theme_id"] for record in promoted_theme_records()]


def promoted_template_ids() -> list[str]:
    return [record["template_id"] for record in promoted_template_records()]


def family_theme_ids() -> list[str]:
    return sorted({str(family.get("template_id")) for family in families() if str(family.get("template_id") or "").strip()})


def all_theme_ids(include_legacy: bool = False) -> list[str]:
    theme_ids = set(PRODUCTION_THEME_IDS)
    theme_ids.update(promoted_theme_ids())
    if include_legacy:
        theme_ids.update(LEGACY_THEME_IDS)
        theme_ids.update(family_theme_ids())
    return sorted(theme_ids)


def all_template_ids(include_legacy: bool = False) -> list[str]:
    template_ids = set(promoted_template_ids())
    if include_legacy:
        template_ids.update(PRODUCTION_TEMPLATE_IDS)
        template_ids.update(LEGACY_TEMPLATE_IDS)
    return sorted(template_ids)


def is_runtime_selectable(record: dict[str, Any], *, include_legacy_debug: bool = False) -> bool:
    if record.get("claim_level") == "source_inventory_only":
        return False
    gate = record.get("promotion_gate")
    if isinstance(gate, dict) and gate.get("status") != "passed":
        return False
    if (
        record.get("asset_status") == ASSET_STATUS_PRODUCTION
        and record.get("quality_tier") == QUALITY_TIER_TRUSTED
        and record.get("selection_scope") == "production"
        and record.get("default_selectable") is True
    ):
        if _record_kind(record) == "template":
            return _has_template_runtime_contract(record)
        return True
    if _record_kind(record) == "template" and (
        record.get("asset_status") == ASSET_STATUS_PRODUCTION
        or record.get("quality_tier") == QUALITY_TIER_TRUSTED
        or record.get("selection_scope") == "production"
    ):
        return False
    status = record.get("status")
    if status == ASSET_STATUS_LEGACY_DEBUG:
        return include_legacy_debug
    return status == "active" and record.get("default_selectable") is not False


def non_empty_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if cleaned:
            return cleaned
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def normalized_formality(value: Any) -> str:
    raw = str(value or "").strip()
    return raw if raw in FORMALITY_VALUES else "medium"


def policy_summary(value: Any, keys: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value.get(key) for key in keys if value.get(key) not in (None, "", [])}


def family_usage_policy_summary(family: dict[str, Any]) -> dict[str, Any]:
    return policy_summary(
        family.get("family_usage_policy"),
        ["closed_visual_system", "cross_family_layout_mix_allowed", "recolor_allowed", "font_substitution_allowed", "decorative_elements_policy"],
    )


def cjk_policy_summary(family: dict[str, Any]) -> dict[str, Any]:
    return policy_summary(
        family.get("cjk_policy"),
        ["strategy", "display_font_cn", "body_font_cn", "runtime_font_policy", "italic_policy", "letter_spacing_policy", "mixed_run_spacing"],
    )


def extension_grammar_summary(family: dict[str, Any]) -> dict[str, Any]:
    grammar = family.get("extension_grammar") if isinstance(family.get("extension_grammar"), dict) else {}
    return {
        "layout_rhythm": grammar.get("layout_rhythm"),
        "component_grammar": grammar.get("component_grammar", [])[:6] if isinstance(grammar.get("component_grammar"), list) else grammar.get("component_grammar"),
        "decorative_vocabulary": grammar.get("decorative_vocabulary", [])[:6] if isinstance(grammar.get("decorative_vocabulary"), list) else grammar.get("decorative_vocabulary"),
        "forbidden_mutations": grammar.get("forbidden_mutations", [])[:6] if isinstance(grammar.get("forbidden_mutations"), list) else grammar.get("forbidden_mutations"),
    }


def benchmark_roles(family: dict[str, Any]) -> list[str]:
    visual_dna = family.get("visual_dna") if isinstance(family.get("visual_dna"), dict) else {}
    benchmarks = visual_dna.get("screenshot_benchmarks") if isinstance(visual_dna.get("screenshot_benchmarks"), list) else []
    return [str(item.get("role")) for item in benchmarks if isinstance(item, dict) and item.get("role")]


def _non_empty_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) and value else {}


def _non_empty_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) and value else []


def _runtime_path(value: Any) -> Path:
    raw = str(value or "")
    path = Path(raw)
    if path.is_absolute():
        return path
    if raw.startswith(f"{SOURCE_ROOT.name}/"):
        return SOURCE_ROOT.parent / raw
    if raw.startswith("screenshots/") or raw.startswith("templates/"):
        return SOURCE_ROOT / raw
    return REPO_ROOT / raw


def _existing_file(value: Any) -> bool:
    return _runtime_path(value).is_file()


def _file_sha256(value: Any) -> str | None:
    path = _runtime_path(value)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_hashes_match(receipt_payload: dict[str, Any]) -> bool:
    reference_screenshot = receipt_payload.get("reference_screenshot")
    render_screenshot = receipt_payload.get("render_screenshot") or receipt_payload.get("rendered")
    return (
        receipt_payload.get("generated_by") == "beautiful_template_fidelity_check.py"
        and isinstance(receipt_payload.get("generator_version"), str)
        and bool(receipt_payload.get("generator_version"))
        and isinstance(receipt_payload.get("command"), list)
        and bool(receipt_payload.get("command"))
        and isinstance(receipt_payload.get("reference_sha256"), str)
        and receipt_payload.get("reference_sha256") == _file_sha256(reference_screenshot)
        and isinstance(receipt_payload.get("render_sha256"), str)
        and receipt_payload.get("render_sha256") == _file_sha256(render_screenshot)
    )


def _read_optional_json_file(value: Any) -> dict[str, Any]:
    path = _runtime_path(value)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _record_kind(record: dict[str, Any]) -> str:
    if "palette_id" in record:
        return "palette"
    if "theme_id" in record and "colors" in record:
        return "theme"
    return "template"


def _has_template_runtime_contract(record: dict[str, Any]) -> bool:
    fidelity_gate = record.get("fidelity_gate")
    receipt = record.get("fidelity_receipt")
    if isinstance(fidelity_gate, dict) and not receipt:
        receipt = fidelity_gate.get("receipt_path")
    receipt_payload = _read_optional_json_file(receipt)
    receipt_template_id = receipt_payload.get("selected_template_id") or receipt_payload.get("template_id")
    score = receipt_payload.get("score")
    threshold = receipt_payload.get("threshold", 0.72)
    return (
        isinstance(record.get("renderer_module"), str)
        and bool(str(record.get("renderer_module")).strip())
        and _existing_file(record.get("renderer_module"))
        and record.get("renderer_executable") is True
        and isinstance(record.get("golden_spec"), str)
        and bool(str(record.get("golden_spec")).strip())
        and _existing_file(record.get("golden_spec"))
        and _existing_file(receipt)
        and receipt_payload.get("status") == "passed"
        and receipt_template_id == record.get("id")
        and isinstance(score, (int, float))
        and isinstance(threshold, (int, float))
        and score >= threshold
        and _existing_file(receipt_payload.get("reference_screenshot"))
        and _existing_file(receipt_payload.get("render_screenshot") or receipt_payload.get("rendered"))
        and _receipt_hashes_match(receipt_payload)
        and _non_empty_list(record.get("supported_page_types"))
        and isinstance(record.get("visual_contract"), dict)
        and bool(record.get("visual_contract"))
        and isinstance(fidelity_gate, dict)
        and fidelity_gate.get("status") == "passed"
    )


def _theme_source_trace(family: dict[str, Any], theme_token: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = theme_token.get("source_trace")
    if isinstance(explicit, list) and explicit:
        return [item for item in explicit if isinstance(item, dict)]
    source = family.get("source") if isinstance(family.get("source"), dict) else {}
    records: list[dict[str, Any]] = []
    for key in ("source_design_md", "reference_screenshot"):
        value = source.get(key)
        if isinstance(value, str) and value:
            records.append({"source": value, "evidence": key})
    screenshots = source.get("source_screenshots")
    if isinstance(screenshots, list):
        records.extend({"source": item, "evidence": "source_screenshot"} for item in screenshots if isinstance(item, str) and item)
    return records


def _source_trace(family: dict[str, Any], token: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = token.get("source_trace")
    if isinstance(explicit, list) and explicit:
        return [item for item in explicit if isinstance(item, dict)]
    return _theme_source_trace(family, token)


def theme_promotion_candidate(family: dict[str, Any]) -> dict[str, Any]:
    family_id = str(family.get("template_id") or "")
    theme_id = family_id
    theme_token = family.get("theme_token") if isinstance(family.get("theme_token"), dict) else {}
    semantic_fit = _non_empty_dict(family.get("semantic_fit"))
    visual_dna = _non_empty_dict(family.get("visual_dna"))
    cjk_policy = _non_empty_dict(family.get("cjk_policy"))
    usage_policy = _non_empty_dict(family.get("family_usage_policy"))
    asset_ids = mapping_asset_ids(family)
    source = family.get("source") if isinstance(family.get("source"), dict) else {}
    source_trace = _theme_source_trace(family, theme_token)
    issues: list[dict[str, str]] = []

    def block(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    if family.get("claim_level") == "source_inventory_only" or family.get("status") == "source_inventoried":
        block("source_inventory_only_family", "source inventory only families cannot promote to runtime themes")
    if family.get("status") != "absorbed":
        block("family_not_absorbed", "theme promotion requires an absorbed family")
    if family.get("claim_level") != "svglide_absorbed":
        block("claim_not_absorbed", "theme promotion requires svglide_absorbed claim level")
    if f"theme.{theme_id}" not in asset_ids:
        block("missing_theme_mapping", "svglide_mapping.svglide_asset_ids must include theme.<family>")
    if not theme_token:
        block("missing_theme_token", "promoted themes require a theme_token")
    elif theme_token.get("theme_id") != theme_id:
        block("theme_token_id_mismatch", "theme_token.theme_id must match the source family")
    for key in ("colors", "semantic_colors", "typography", "spacing", "motif_budget", "template_bindings"):
        if not theme_token.get(key):
            block(f"missing_theme_token_{key}", f"theme_token.{key} is required")
    if theme_token.get("status") != ASSET_STATUS_PRODUCTION:
        block("theme_token_not_production", "theme_token.status must be production")
    if theme_token.get("quality_tier") != QUALITY_TIER_TRUSTED:
        block("theme_token_not_trusted", "theme_token.quality_tier must be trusted")
    if theme_token.get("default_selectable") is not True:
        block("theme_token_not_default_selectable", "theme_token.default_selectable must be true")
    for key, value in (
        ("semantic_fit", semantic_fit),
        ("visual_dna", visual_dna),
        ("cjk_policy", cjk_policy),
        ("family_usage_policy", usage_policy),
    ):
        if not value:
            block(f"missing_{key}", f"{key} is required for theme promotion")
    if not _non_empty_list(semantic_fit.get("best_for")) or not _non_empty_list(semantic_fit.get("avoid_when")):
        block("missing_semantic_fit_scope", "semantic_fit.best_for and avoid_when are required")
    if not _non_empty_list(visual_dna.get("screenshot_benchmarks")) and not source.get("reference_screenshot"):
        block("missing_visual_evidence", "screenshot_benchmarks or reference_screenshot is required")
    if not source_trace:
        block("missing_source_trace", "source evidence is required")

    gate_status = "passed" if not issues else "blocked"
    return {
        "id": theme_id,
        "source_family": family_id,
        "theme_id": theme_id,
        "status": ASSET_STATUS_PRODUCTION if gate_status == "passed" else ASSET_STATUS_LEGACY_DEBUG,
        "asset_status": ASSET_STATUS_PRODUCTION if gate_status == "passed" else ASSET_STATUS_LEGACY_DEBUG,
        "quality_tier": QUALITY_TIER_TRUSTED if gate_status == "passed" else QUALITY_TIER_FIXTURE_ONLY,
        "default_selectable": gate_status == "passed",
        "selection_scope": "production" if gate_status == "passed" else "debug",
        "promotion_status": "has_theme_mapping" if gate_status == "passed" else "blocked",
        "promotion_gate": {
            "status": gate_status,
            "issues": issues,
            "required_evidence": [
                "theme_token",
                "theme_mapping",
                "source_trace",
                "semantic_fit",
                "visual_dna",
                "cjk_policy",
                "family_usage_policy",
            ],
        },
        "theme_token": theme_token,
        "source_trace": source_trace,
        "semantic_fit": semantic_fit,
        "visual_dna": visual_dna,
        "cjk_policy": cjk_policy,
        "family_usage_policy": usage_policy,
    }


def template_promotion_candidate(family: dict[str, Any]) -> dict[str, Any]:
    family_id = str(family.get("template_id") or "")
    template_token = family.get("template_token") if isinstance(family.get("template_token"), dict) else {}
    template_id = str(template_token.get("template_id") or family_id)
    theme_token = family.get("theme_token") if isinstance(family.get("theme_token"), dict) else {}
    semantic_fit = _non_empty_dict(family.get("semantic_fit"))
    visual_dna = _non_empty_dict(family.get("visual_dna"))
    cjk_policy = _non_empty_dict(family.get("cjk_policy"))
    usage_policy = _non_empty_dict(family.get("family_usage_policy"))
    asset_ids = mapping_asset_ids(family)
    source = family.get("source") if isinstance(family.get("source"), dict) else {}
    source_trace = _source_trace(family, template_token)
    issues: list[dict[str, str]] = []

    def block(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    if family.get("claim_level") == "source_inventory_only" or family.get("status") == "source_inventoried":
        block("source_inventory_only_family", "source inventory only families cannot promote to runtime templates")
    if family.get("status") != "absorbed":
        block("family_not_absorbed", "template promotion requires an absorbed family")
    if family.get("claim_level") != "svglide_absorbed":
        block("claim_not_absorbed", "template promotion requires svglide_absorbed claim level")
    if f"template.{template_id}" not in asset_ids:
        block("missing_template_mapping", "svglide_mapping.svglide_asset_ids must include template.<template_id>")
    if f"theme.{family_id}" not in asset_ids:
        block("missing_theme_mapping", "promoted templates must bind to a family theme")
    if not template_token:
        block("missing_template_token", "promoted templates require a template_token")
    elif template_token.get("template_id") != template_id:
        block("template_token_id_mismatch", "template_token.template_id must match the promoted template id")
    for key in ("renderer_id", "layout_family", "required_content", "content_shapes", "max_items", "text_budget", "source_trace"):
        if not template_token.get(key):
            block(f"missing_template_token_{key}", f"template_token.{key} is required")
    if not template_token.get("renderer_module"):
        block("missing_template_token_renderer_module", "template_token.renderer_module is required")
    elif not _existing_file(template_token.get("renderer_module")):
        block("template_token_renderer_module_missing_file", "template_token.renderer_module must point to an existing file")
    if template_token.get("renderer_executable") is not True:
        block("template_token_renderer_not_executable", "template_token.renderer_executable must be true")
    if not template_token.get("golden_spec"):
        block("missing_template_token_golden_spec", "template_token.golden_spec is required")
    elif not _existing_file(template_token.get("golden_spec")):
        block("template_token_golden_spec_missing_file", "template_token.golden_spec must point to an existing file")
    if not _non_empty_list(template_token.get("supported_page_types")):
        block("missing_template_token_supported_page_types", "template_token.supported_page_types is required")
    if not isinstance(template_token.get("visual_contract"), dict) or not template_token.get("visual_contract"):
        block("missing_template_token_visual_contract", "template_token.visual_contract is required")
    fidelity_gate = template_token.get("fidelity_gate")
    fidelity_receipt = template_token.get("fidelity_receipt")
    if isinstance(fidelity_gate, dict) and not fidelity_receipt:
        fidelity_receipt = fidelity_gate.get("receipt_path")
    if not isinstance(fidelity_gate, dict) or fidelity_gate.get("status") != "passed":
        block("template_token_fidelity_gate_not_passed", "template_token.fidelity_gate.status must be passed")
    if not fidelity_receipt:
        block("missing_template_token_fidelity_receipt", "template_token fidelity receipt is required")
    elif not _existing_file(fidelity_receipt):
        block("template_token_fidelity_receipt_missing_file", "template_token fidelity receipt must point to an existing file")
    else:
        receipt_payload = _read_optional_json_file(fidelity_receipt)
        receipt_template_id = receipt_payload.get("selected_template_id") or receipt_payload.get("template_id")
        score = receipt_payload.get("score")
        threshold = receipt_payload.get("threshold", 0.72)
        if receipt_payload.get("status") != "passed":
            block("template_token_fidelity_receipt_not_passed", "template fidelity receipt status must be passed")
        if receipt_template_id != template_id:
            block("template_token_fidelity_receipt_template_mismatch", "template fidelity receipt template_id must match template_token.template_id")
        if not isinstance(score, (int, float)) or not isinstance(threshold, (int, float)) or score < threshold:
            block("template_token_fidelity_receipt_score_below_threshold", "template fidelity receipt score must meet threshold")
        if not _existing_file(receipt_payload.get("reference_screenshot")):
            block("template_token_fidelity_receipt_reference_missing_file", "template fidelity receipt reference_screenshot must exist")
        if not _existing_file(receipt_payload.get("render_screenshot") or receipt_payload.get("rendered")):
            block("template_token_fidelity_receipt_render_missing_file", "template fidelity receipt render_screenshot must exist")
        if not _receipt_hashes_match(receipt_payload):
            block("template_token_fidelity_receipt_hash_mismatch", "template fidelity receipt provenance and hashes must match current files")
    if template_token.get("status") != ASSET_STATUS_PRODUCTION:
        block("template_token_not_production", "template_token.status must be production")
    if template_token.get("quality_tier") != QUALITY_TIER_TRUSTED:
        block("template_token_not_trusted", "template_token.quality_tier must be trusted")
    if template_token.get("default_selectable") is not True:
        block("template_token_not_default_selectable", "template_token.default_selectable must be true")
    if template_token.get("selection_scope") != "production":
        block("template_token_not_production_scope", "template_token.selection_scope must be production")
    if not theme_token:
        block("missing_theme_token", "promoted templates require a paired family theme_token")
    elif theme_token.get("theme_id") != family_id:
        block("theme_token_id_mismatch", "theme_token.theme_id must match the source family")
    for key, value in (
        ("semantic_fit", semantic_fit),
        ("visual_dna", visual_dna),
        ("cjk_policy", cjk_policy),
        ("family_usage_policy", usage_policy),
    ):
        if not value:
            block(f"missing_{key}", f"{key} is required for template promotion")
    if not _non_empty_list(semantic_fit.get("best_for")) or not _non_empty_list(semantic_fit.get("avoid_when")):
        block("missing_semantic_fit_scope", "semantic_fit.best_for and avoid_when are required")
    if not _non_empty_list(visual_dna.get("screenshot_benchmarks")) and not source.get("reference_screenshot"):
        block("missing_visual_evidence", "screenshot_benchmarks or reference_screenshot is required")
    if not source_trace:
        block("missing_source_trace", "source evidence is required")

    gate_status = "passed" if not issues else "blocked"
    return {
        "id": template_id,
        "source_family": family_id,
        "template_id": template_id,
        "theme_id": family_id,
        "status": ASSET_STATUS_PRODUCTION if gate_status == "passed" else ASSET_STATUS_LEGACY_DEBUG,
        "asset_status": ASSET_STATUS_PRODUCTION if gate_status == "passed" else ASSET_STATUS_LEGACY_DEBUG,
        "quality_tier": QUALITY_TIER_TRUSTED if gate_status == "passed" else QUALITY_TIER_FIXTURE_ONLY,
        "default_selectable": gate_status == "passed",
        "selection_scope": "production" if gate_status == "passed" else "debug",
        "promotion_status": "has_template_mapping" if gate_status == "passed" else "blocked",
        "promotion_gate": {
            "status": gate_status,
            "issues": issues,
            "required_evidence": [
                "template_token",
                "template_mapping",
                "paired_theme_token",
                "source_trace",
                "semantic_fit",
                "visual_dna",
                "cjk_policy",
                "family_usage_policy",
            ],
        },
        "template_token": template_token,
        "source_trace": source_trace,
        "semantic_fit": semantic_fit,
        "visual_dna": visual_dna,
        "cjk_policy": cjk_policy,
        "family_usage_policy": usage_policy,
    }


def promoted_theme_records(path: Path = FAMILIES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for family in families(path):
        candidate = theme_promotion_candidate(family)
        if candidate["promotion_gate"]["status"] == "passed":
            records.append(candidate)
    return records


def promoted_template_records(path: Path = FAMILIES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for family in families(path):
        candidate = template_promotion_candidate(family)
        if candidate["promotion_gate"]["status"] == "passed":
            records.append(candidate)
    return records


def family_policy_context(limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for family in families()[: limit or None]:
        template_id = family.get("template_id")
        if not isinstance(template_id, str) or not template_id:
            continue
        records.append(
            {
                "source_template_id": template_id,
                "status": family.get("status"),
                "claim_level": family.get("claim_level"),
                "family_usage_policy_summary": family_usage_policy_summary(family),
                "cjk_policy_summary": cjk_policy_summary(family),
                "extension_grammar_summary": extension_grammar_summary(family),
                "benchmark_roles": benchmark_roles(family),
            }
        )
    return records


def _static_template_promotion_gate(family: dict[str, Any] | None, template_id: str) -> dict[str, Any] | None:
    if not isinstance(family, dict):
        return None
    issues: list[dict[str, str]] = []
    if family.get("status") != "absorbed":
        issues.append({"code": "family_not_absorbed", "message": "static production template source family must be absorbed"})
    if family.get("claim_level") != "svglide_absorbed":
        issues.append({"code": "claim_not_absorbed", "message": "static production template source family must claim svglide_absorbed"})
    if f"template.{template_id}" not in mapping_asset_ids(family):
        issues.append({"code": "missing_template_mapping", "message": "source family must map to this production template"})
    return {
        "status": "passed" if not issues else "blocked",
        "issues": issues,
        "required_evidence": [
            "static_absorption_record",
            "template_mapping",
            "source_trace",
            "semantic_fit",
            "visual_dna",
            "cjk_policy",
            "family_usage_policy",
        ],
    }


def _promoted_template_payload(record: dict[str, Any]) -> dict[str, Any]:
    token = record["template_token"]
    semantic_fit = record.get("semantic_fit") if isinstance(record.get("semantic_fit"), dict) else {}
    visual_dna = record.get("visual_dna") if isinstance(record.get("visual_dna"), dict) else {}
    template_id = record["template_id"]
    return {
        "id": template_id,
        "renderer_id": str(token.get("renderer_id") or f"artboard_satori.{template_id}"),
        "renderer_module": token.get("renderer_module"),
        "renderer_executable": token.get("renderer_executable") is True,
        "golden_spec": token.get("golden_spec"),
        "fidelity_receipt": token.get("fidelity_receipt") or (token.get("fidelity_gate") or {}).get("receipt_path"),
        "fidelity_gate": token.get("fidelity_gate") if isinstance(token.get("fidelity_gate"), dict) else {},
        "supported_page_types": non_empty_string_list(token.get("supported_page_types"), []),
        "visual_contract": token.get("visual_contract") if isinstance(token.get("visual_contract"), dict) else {},
        "visual_contract_path": record.get("visual_contract_path")
        or ((token.get("visual_contract") if isinstance(token.get("visual_contract"), dict) else {}).get("path")),
        "layout_family": str(token.get("layout_family") or template_id.replace("-", "_")),
        "required_content": non_empty_string_list(token.get("required_content"), ["title"]),
        "optional_content": non_empty_string_list(token.get("optional_content"), ["eyebrow", "subtitle"]),
        "max_items": token.get("max_items") if isinstance(token.get("max_items"), dict) else {},
        "text_budget": token.get("text_budget") if isinstance(token.get("text_budget"), dict) else {"title": 60, "subtitle": 120},
        "supported_theme_ids": [record["theme_id"]],
        "selection_metadata": {
            "best_for": non_empty_string_list(semantic_fit.get("best_for"), [template_id.replace("-", " ")]),
            "avoid_for": non_empty_string_list(semantic_fit.get("avoid_when"), []),
            "occasion_tags": non_empty_string_list(semantic_fit.get("best_for"), [template_id.replace("-", " ")]),
            "tone_tags": non_empty_string_list(semantic_fit.get("tones"), ["structured"]),
            "industry_tags": non_empty_string_list(semantic_fit.get("industries"), ["general"]),
            "density": visual_dna.get("density") or "medium",
            "formality": normalized_formality(semantic_fit.get("formality")),
            "content_shapes": non_empty_string_list(token.get("content_shapes"), [template_id.replace("-", " ")]),
            "audience_tags": non_empty_string_list(token.get("audience_tags"), ["general"]),
            "visual_signature": non_empty_string_list(visual_dna.get("motifs") or visual_dna.get("decorative_motifs"), [template_id.replace("-", " ")]),
            "required_assets": non_empty_string_list(token.get("required_assets"), []),
            "decorative_elements": non_empty_string_list(visual_dna.get("decorative_motifs") or visual_dna.get("motifs"), []),
        },
        "source_template_id": record["source_family"],
        "claim_level": "svglide_absorbed",
        "source_trace": record["source_trace"],
        "promotion_gate": record["promotion_gate"],
        "family_usage_policy_summary": family_usage_policy_summary({"family_usage_policy": record.get("family_usage_policy")}),
        "cjk_policy_summary": cjk_policy_summary({"cjk_policy": record.get("cjk_policy")}),
        "extension_grammar_summary": extension_grammar_summary({"extension_grammar": token.get("extension_grammar")}),
        "benchmark_roles": benchmark_roles({"visual_dna": visual_dna}),
        "template_token": token,
        **runtime_asset_metadata(ASSET_STATUS_PRODUCTION),
    }


def template_registry(include_legacy: bool = False) -> dict[str, Any]:
    theme_ids = all_theme_ids(include_legacy=include_legacy)
    records: list[dict[str, Any]] = []
    family_by_asset: dict[str, dict[str, Any]] = {}
    for family in families():
        mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
        for raw in mapping.get("svglide_asset_ids", []) if isinstance(mapping.get("svglide_asset_ids"), list) else []:
            if isinstance(raw, str) and raw.startswith("template."):
                family_by_asset[raw.removeprefix("template.")] = family
    promoted_by_id = {record["template_id"]: record for record in promoted_template_records()}
    matrix_by_template_id = executable_matrix_by_runtime_template_id()
    for template_id in all_template_ids(include_legacy=include_legacy):
        if template_id in promoted_by_id:
            record = _promoted_template_payload(promoted_by_id[template_id])
            records.append(merge_executable_matrix_metadata(record, matrix_by_template_id.get(template_id)))
            continue
        family = family_by_asset.get(template_id)
        asset_status = ASSET_STATUS_LEGACY_DEBUG
        semantic_fit = family.get("semantic_fit") if isinstance(family, dict) and isinstance(family.get("semantic_fit"), dict) else {}
        visual_dna = family.get("visual_dna") if isinstance(family, dict) and isinstance(family.get("visual_dna"), dict) else {}
        best_for = non_empty_string_list(semantic_fit.get("best_for"), [template_id.replace("-", " ")])
        tone_tags = non_empty_string_list(semantic_fit.get("tones"), ["structured"])
        industry_tags = non_empty_string_list(semantic_fit.get("industries"), ["general"])
        audience_tags = ["internal"] if template_id in {"executive-dashboard", "metric-dashboard", "trend-grid-report"} else ["general"]
        record = {
            "id": template_id,
            "renderer_id": f"artboard_satori.{template_id}",
            "layout_family": template_id.replace("-", "_"),
            "required_content": ["title"],
            "optional_content": ["eyebrow", "subtitle"],
            "max_items": {},
            "text_budget": {"title": 60, "subtitle": 120},
            "supported_theme_ids": theme_ids,
            "selection_metadata": {
                "best_for": best_for,
                "avoid_for": semantic_fit.get("avoid_when", []),
                "occasion_tags": best_for,
                "tone_tags": tone_tags,
                "industry_tags": industry_tags,
                "density": visual_dna.get("density") or "medium",
                "formality": normalized_formality(semantic_fit.get("formality")),
                "content_shapes": [template_id.replace("-", " ")],
                "audience_tags": audience_tags,
                "visual_signature": visual_dna.get("motifs") or visual_dna.get("decorative_motifs") or [template_id.replace("-", " ")],
                "required_assets": [],
                "decorative_elements": visual_dna.get("decorative_motifs") or visual_dna.get("motifs") or [],
            },
            **runtime_asset_metadata(asset_status),
        }
        if family:
            record.update(
                {
                    "source_template_id": family.get("template_id"),
                    "claim_level": family.get("claim_level"),
                    "source_trace": _source_trace(family, {}),
                    "promotion_gate": _static_template_promotion_gate(family, template_id),
                    "family_usage_policy_summary": family_usage_policy_summary(family),
                    "cjk_policy_summary": cjk_policy_summary(family),
                    "extension_grammar_summary": extension_grammar_summary(family),
                    "benchmark_roles": benchmark_roles(family),
                }
            )
        record.update(TEMPLATE_OVERRIDES.get(template_id, {}))
        merge_executable_matrix_metadata(record, matrix_by_template_id.get(template_id))
        records.append(record)
    return {"version": "svglide-template-registry/generated-from-beautiful-family-v1", "include_legacy_debug": include_legacy, "templates": records}


def theme_mode(colors: dict[str, str]) -> str:
    return "dark" if colors["background"].upper() in DARK_BACKGROUND_HEX else "light"


def hex_rgb(value: str) -> tuple[int, int, int] | None:
    text = value.strip()
    if not text.startswith("#"):
        return None
    text = text[1:]
    if len(text) == 3:
        text = "".join(part * 2 for part in text)
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def relative_luminance_hex(value: str) -> float | None:
    rgb = hex_rgb(value)
    if rgb is None:
        return None

    def channel(raw: int) -> float:
        normalized = raw / 255.0
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(part) for part in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio_hex(foreground: str, background: str) -> float:
    foreground_luminance = relative_luminance_hex(foreground)
    background_luminance = relative_luminance_hex(background)
    if foreground_luminance is None or background_luminance is None:
        return 0.0
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def readable_against(background: str, *, min_ratio: float = 4.5) -> str:
    dark = "#111827"
    light = "#F8FAFC"
    return dark if contrast_ratio_hex(dark, background) >= min_ratio else light


def ensure_readable_runtime_colors(colors: dict[str, str]) -> dict[str, str]:
    fixed = dict(colors)
    text_backing = fixed.get("panel") or fixed.get("surface") or fixed.get("background") or "#F8FAFC"
    text_color = fixed.get("text") or readable_against(text_backing)
    if contrast_ratio_hex(text_color, text_backing) < 4.5:
        text_color = readable_against(text_backing)
    fixed["text"] = text_color
    for role in ("muted", "primary", "accent"):
        role_color = fixed.get(role) or text_color
        if contrast_ratio_hex(role_color, text_backing) < 3.0:
            role_color = text_color
        fixed[role] = role_color
    return fixed


def _theme_token_colors(theme_token: dict[str, Any]) -> dict[str, str]:
    raw = theme_token.get("colors") if isinstance(theme_token.get("colors"), dict) else {}
    colors = {
        "background": str(raw.get("background") or "#FFFFFF"),
        "surface": str(raw.get("surface") or raw.get("panel") or "#F8FAFC"),
        "panel": str(raw.get("panel") or raw.get("surface") or "#F8FAFC"),
        "primary": str(raw.get("primary") or "#2563EB"),
        "accent": str(raw.get("accent") or raw.get("primary") or "#2563EB"),
        "text": str(raw.get("text") or "#111827"),
        "muted": str(raw.get("muted") or "#64748B"),
        "success": str(raw.get("success") or "#22C55E"),
        "warning": str(raw.get("warning") or "#F59E0B"),
        "danger": str(raw.get("danger") or "#EF4444"),
    }
    for role, value in raw.items():
        if isinstance(role, str) and role not in colors and isinstance(value, str) and value.startswith("#"):
            colors[role] = value
    return colors


def _promoted_theme_payload(record: dict[str, Any]) -> dict[str, Any]:
    theme_token = record["theme_token"]
    theme_id = record["theme_id"]
    colors = _theme_token_colors(theme_token)
    template_ids = [
        item
        for item in non_empty_string_list(theme_token.get("template_bindings"), all_template_ids())
        if item in set(all_template_ids())
    ]
    if not template_ids:
        template_ids = all_template_ids()
    semantic_fit = record.get("semantic_fit") if isinstance(record.get("semantic_fit"), dict) else {}
    semantic_colors = theme_token.get("semantic_colors") if isinstance(theme_token.get("semantic_colors"), dict) else {}
    return {
        "schema_version": "svglide-theme/v1",
        "theme_id": theme_id,
        "mode": str(theme_token.get("mode") or theme_mode(colors)),
        "colors": colors,
        "semantic_colors": semantic_colors,
        "tokens": {f"color.{role}": colors[role] for role in CORE_COLOR_ROLES if role in colors},
        "contrast": {"min_text_contrast": 4.5},
        "allowed_color_roles": list(CORE_COLOR_ROLES),
        "data_series": [colors["primary"], colors["accent"], colors["success"], colors["warning"], colors["danger"]],
        "selection_metadata": {
            "scheme": str(theme_token.get("mode") or theme_mode(colors)),
            "mood_tags": non_empty_string_list(semantic_fit.get("tones"), [theme_id.replace("-", " ")]),
            "primary_color_bias": [colors["primary"]],
            "supported_template_ids": template_ids,
            "brand_affinity": [],
            "contrast_profile": "high readability",
            "token_override_policy": "restricted",
        },
        "template_bindings": {"supported_template_ids": template_ids},
        "theme_token": theme_token,
        "source_family": record["source_family"],
        "source_trace": record["source_trace"],
        "promotion_gate": record["promotion_gate"],
        **runtime_asset_metadata(ASSET_STATUS_PRODUCTION),
    }


def theme_payload(theme_id: str) -> dict[str, Any]:
    promoted_by_id = {record["theme_id"]: record for record in promoted_theme_records()}
    if theme_id in promoted_by_id:
        return _promoted_theme_payload(promoted_by_id[theme_id])
    if theme_id in LEGACY_THEME_COLORS:
        colors = LEGACY_THEME_COLORS[theme_id]
        supported_template_ids = all_template_ids(include_legacy=theme_id in LEGACY_THEME_IDS)
        return {
            "schema_version": "svglide-theme/v1",
            "theme_id": theme_id,
            "mode": theme_mode(colors),
            "colors": {
                "background": colors["background"],
                "surface": colors["panel"],
                "panel": colors["panel"],
                "primary": colors["primary"],
                "accent": colors["accent"],
                "text": colors["text"],
                "muted": colors["muted"],
                "success": "#22C55E",
                "warning": "#F59E0B",
                "danger": "#EF4444",
            },
            "selection_metadata": {
                "scheme": theme_mode(colors),
                "mood_tags": [theme_id.replace("-", " ")],
                "primary_color_bias": [colors["primary"]],
                "supported_template_ids": supported_template_ids,
                "brand_affinity": [],
                "contrast_profile": "normal",
                "token_override_policy": "restricted",
            },
            "template_bindings": {"supported_template_ids": supported_template_ids},
        }
    family_by_id = {str(family.get("template_id")): family for family in families() if str(family.get("template_id") or "").strip()}
    family = family_by_id.get(theme_id)
    if not family:
        raise KeyError(theme_id)
    mapped_theme_id = mapped_runtime_theme_id(family)
    colors: dict[str, str] = {}
    if mapped_theme_id:
        mapped_payload = theme_payload(mapped_theme_id)
        colors = dict(mapped_payload["colors"])
    visual_dna = family.get("visual_dna") if isinstance(family.get("visual_dna"), dict) else {}
    palette_roles = visual_dna.get("palette_roles") if isinstance(visual_dna.get("palette_roles"), dict) else {}

    def color(role: str, fallback: str) -> str:
        value = palette_roles.get(role)
        return value if isinstance(value, str) and value.startswith("#") else fallback

    if not colors:
        colors = {
            "background": color("background", "#F8FAFC"),
            "surface": color("surface", color("background", "#F8FAFC")),
            "panel": color("surface", color("background", "#F8FAFC")),
            "primary": color("primary", color("accent", "#2563EB")),
            "accent": color("accent", color("primary", "#2563EB")),
            "text": color("text", "#111827"),
            "muted": color("muted", "#64748B"),
            "success": "#22C55E",
            "warning": "#F59E0B",
            "danger": "#EF4444",
        }
    colors = ensure_readable_runtime_colors(colors)
    mapped_templates = [item.removeprefix("template.") for item in mapping_asset_ids(family) if item.startswith("template.")]
    supported_template_ids = [item for item in mapped_templates if item in set(all_template_ids(include_legacy=True))]
    if not supported_template_ids:
        supported_template_ids = all_template_ids(include_legacy=True)
    return {
        "schema_version": "svglide-theme/v1",
        "theme_id": theme_id,
        "mode": theme_mode(colors),
        "colors": {
            "background": colors["background"],
            "surface": colors["surface"],
            "panel": colors["panel"],
            "primary": colors["primary"],
            "accent": colors["accent"],
            "text": colors["text"],
            "muted": colors["muted"],
            "success": colors["success"],
            "warning": colors["warning"],
            "danger": colors["danger"],
        },
        "selection_metadata": {
            "scheme": theme_mode(colors),
            "mood_tags": non_empty_string_list(family.get("semantic_fit", {}).get("tones") if isinstance(family.get("semantic_fit"), dict) else None, [theme_id.replace("-", " ")]),
            "primary_color_bias": [colors["primary"]],
            "supported_template_ids": supported_template_ids,
            "brand_affinity": [],
            "contrast_profile": "normal",
            "token_override_policy": "restricted",
        },
        "template_bindings": {"supported_template_ids": supported_template_ids},
        "source_family": theme_id,
        "source_trace": _theme_source_trace(family, {}),
        "asset_status": ASSET_STATUS_LEGACY_DEBUG,
    }


def _asset_status_for_theme(theme_id: str, payload: dict[str, Any]) -> str:
    if payload.get("asset_status") == ASSET_STATUS_PRODUCTION:
        return ASSET_STATUS_PRODUCTION
    return ASSET_STATUS_LEGACY_DEBUG if theme_id in LEGACY_THEME_IDS else ASSET_STATUS_PRODUCTION


def theme_registry(include_legacy: bool = False) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for theme_id in all_theme_ids(include_legacy=include_legacy):
        payload = theme_payload(theme_id)
        asset_status = _asset_status_for_theme(theme_id, payload)
        record = {
            "id": theme_id,
            "theme_id": theme_id,
            "colors": payload["colors"],
            "selection_metadata": payload["selection_metadata"],
            "template_bindings": payload["template_bindings"],
            **runtime_asset_metadata(asset_status),
        }
        for key in ("theme_token", "source_family", "source_trace", "promotion_gate"):
            if payload.get(key):
                record[key] = payload[key]
        records.append(record)
    return {
        "version": "svglide-theme-registry/generated-from-beautiful-family-v1",
        "include_legacy_debug": include_legacy,
        "themes": records,
    }


def palette_registry(include_legacy: bool = False) -> dict[str, Any]:
    palettes: list[dict[str, Any]] = []
    for theme_id in all_theme_ids(include_legacy=include_legacy):
        theme = theme_payload(theme_id)
        colors = theme["colors"]
        asset_status = _asset_status_for_theme(theme_id, theme)
        source_trace = theme.get("source_trace") if isinstance(theme.get("source_trace"), list) else [{"source": FAMILIES_PATH.as_posix(), "theme_id": theme_id}]
        palettes.append(
            {
                "palette_id": f"family.{theme_id}",
                "mode": theme["mode"],
                "colors": colors,
                "data_series": [colors["primary"], colors["accent"], colors["success"], colors["warning"], colors["danger"]],
                "source_trace": source_trace,
                "source_family": theme.get("source_family") or theme_id,
                "selection_metadata": {
                    "tone_tags": non_empty_string_list(theme.get("selection_metadata", {}).get("mood_tags") if isinstance(theme.get("selection_metadata"), dict) else None, [theme_id.replace("-", " ")]),
                    "density": "medium",
                    "formality": "medium",
                    "industry_tags": ["general"],
                    "best_for": non_empty_string_list(theme.get("selection_metadata", {}).get("mood_tags") if isinstance(theme.get("selection_metadata"), dict) else None, [theme_id.replace("-", " ")]),
                    "avoid_for": [],
                    "brand_affinity": [],
                },
                **runtime_asset_metadata(asset_status),
            }
        )
    brand_registry = read_json(BRAND_PALETTE_PATH)
    for brand in brand_registry.get("brands", []) if isinstance(brand_registry.get("brands"), list) else []:
        if not isinstance(brand, dict) or not isinstance(brand.get("brand_id"), str):
            continue
        palette = brand.get("palette") if isinstance(brand.get("palette"), dict) else {}
        colors = {
            "background": str(palette.get("background") or "#FFFFFF"),
            "surface": str(palette.get("surface") or palette.get("background") or "#F8FAFC"),
            "text": str(palette.get("text") or "#111827"),
            "muted": str(palette.get("muted") or "#64748B"),
            "primary": str(palette.get("primary") or "#2563EB"),
            "accent": str(palette.get("accent") or palette.get("primary") or "#2563EB"),
        }
        palettes.append(
            {
                "palette_id": f"brand.{brand['brand_id']}",
                "mode": "mixed",
                "colors": colors,
                "data_series": [colors["primary"], colors["accent"], colors["muted"]],
                "source_trace": brand.get("source_trace") if isinstance(brand.get("source_trace"), list) else [{"source": BRAND_PALETTE_PATH.as_posix(), "brand_id": brand["brand_id"]}],
                "selection_metadata": {
                    "brand_affinity": [brand["brand_id"]],
                    "tone_tags": ["brand"],
                    "density": "medium",
                    "formality": "medium",
                    "industry_tags": ["general"],
                    "avoid_for": [],
                    "best_for": [str(brand.get("display_name") or brand["brand_id"])],
                },
                **runtime_asset_metadata(ASSET_STATUS_PRODUCTION),
            }
        )
    return {"schema_version": "svglide-palette-registry/generated-from-beautiful-family-v1", "palettes": palettes}


def component_registry() -> dict[str, Any]:
    existing_path = REFERENCES_DIR / "component-registry.json"
    if existing_path.exists():
        return read_json(existing_path)
    return {"version": "svglide-component-registry/v1", "components": []}
