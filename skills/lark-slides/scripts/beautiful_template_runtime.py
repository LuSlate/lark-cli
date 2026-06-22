#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
FAMILIES_PATH = REFERENCES_DIR / "beautiful-html-template-families.json"
BRAND_PALETTE_PATH = REFERENCES_DIR / "svglide-brand-palette-registry.json"

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
]

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


def all_theme_ids() -> list[str]:
    return sorted(LEGACY_THEME_COLORS)


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


def template_registry() -> dict[str, Any]:
    theme_ids = all_theme_ids()
    records: list[dict[str, Any]] = []
    family_by_asset: dict[str, dict[str, Any]] = {}
    for family in families():
        mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
        for raw in mapping.get("svglide_asset_ids", []) if isinstance(mapping.get("svglide_asset_ids"), list) else []:
            if isinstance(raw, str) and raw.startswith("template."):
                family_by_asset[raw.removeprefix("template.")] = family
    for template_id in TEMPLATE_IDS:
        family = family_by_asset.get(template_id)
        semantic_fit = family.get("semantic_fit") if isinstance(family, dict) and isinstance(family.get("semantic_fit"), dict) else {}
        visual_dna = family.get("visual_dna") if isinstance(family, dict) and isinstance(family.get("visual_dna"), dict) else {}
        best_for = non_empty_string_list(semantic_fit.get("best_for"), [template_id.replace("-", " ")])
        tone_tags = non_empty_string_list(semantic_fit.get("tones"), ["structured"])
        industry_tags = non_empty_string_list(semantic_fit.get("industries"), ["general"])
        audience_tags = ["internal"] if template_id in {"executive-dashboard", "metric-dashboard", "trend-grid-report"} else ["general"]
        record = {
            "id": template_id,
            "status": "active",
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
        }
        record.update(TEMPLATE_OVERRIDES.get(template_id, {}))
        records.append(record)
    return {"version": "svglide-template-registry/generated-from-beautiful-family-v1", "templates": records}


def theme_payload(theme_id: str) -> dict[str, Any]:
    colors = LEGACY_THEME_COLORS[theme_id]
    return {
        "schema_version": "svglide-theme/v1",
        "theme_id": theme_id,
        "mode": "dark" if colors["background"].upper() in {"#0F172A", "#071827", "#081C4A", "#07110E", "#090B1A", "#27130F", "#1C2644", "#0B1F1A", "#1C1C1C"} else "light",
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
            "scheme": "dark" if colors["background"].upper() in {"#0F172A", "#071827", "#081C4A", "#07110E", "#090B1A", "#27130F", "#1C2644", "#0B1F1A", "#1C1C1C"} else "light",
            "mood_tags": [theme_id.replace("-", " ")],
            "primary_color_bias": [colors["primary"]],
            "supported_template_ids": TEMPLATE_IDS,
            "brand_affinity": [],
            "contrast_profile": "normal",
            "token_override_policy": "restricted",
        },
        "template_bindings": {"supported_template_ids": TEMPLATE_IDS},
    }


def theme_registry() -> dict[str, Any]:
    return {
        "version": "svglide-theme-registry/generated-from-beautiful-family-v1",
        "themes": [
            {
                "id": theme_id,
                "status": "active",
                "colors": theme_payload(theme_id)["colors"],
                "selection_metadata": theme_payload(theme_id)["selection_metadata"],
                "template_bindings": theme_payload(theme_id)["template_bindings"],
            }
            for theme_id in all_theme_ids()
        ],
    }


def palette_registry() -> dict[str, Any]:
    palettes: list[dict[str, Any]] = []
    for theme_id in all_theme_ids():
        theme = theme_payload(theme_id)
        colors = theme["colors"]
        palettes.append(
            {
                "palette_id": f"family.{theme_id}",
                "status": "active",
                "mode": theme["mode"],
                "colors": colors,
                "data_series": [colors["primary"], colors["accent"], colors["success"], colors["warning"], colors["danger"]],
                "source_trace": [{"source": FAMILIES_PATH.as_posix(), "theme_id": theme_id}],
                "selection_metadata": {
                    "tone_tags": [theme_id.replace("-", " ")],
                    "density": "medium",
                    "formality": "medium",
                    "industry_tags": ["general"],
                    "best_for": [theme_id.replace("-", " ")],
                    "avoid_for": [],
                    "brand_affinity": [],
                },
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
                "status": "active",
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
            }
        )
    return {"schema_version": "svglide-palette-registry/generated-from-beautiful-family-v1", "palettes": palettes}


def component_registry() -> dict[str, Any]:
    existing_path = REFERENCES_DIR / "component-registry.json"
    if existing_path.exists():
        return read_json(existing_path)
    return {"version": "svglide-component-registry/v1", "components": []}
