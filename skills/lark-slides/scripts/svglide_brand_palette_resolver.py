#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BRAND_REGISTRY_PATH = SCRIPT_DIR.parent / "references" / "svglide-brand-palette-registry.json"
PALETTE_REGISTRY_PATH = SCRIPT_DIR.parent / "references" / "svglide-palette-registry.json"
HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def normalize_hex(value: str) -> str:
    raw = value.strip()
    digits = raw[1:]
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits.upper()}"


def stable_seed(parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def extract_brand_entities(brief: str, evidence: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = load_brand_registry()
    brief_norm = normalize_text(brief)
    evidence_text = normalize_text(json.dumps(evidence or {}, ensure_ascii=False))
    haystack = f"{brief_norm} {evidence_text}".strip()
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in registry.get("brands", []):
        if not isinstance(record, dict):
            continue
        brand_id = record.get("brand_id")
        aliases = record.get("aliases")
        if not isinstance(brand_id, str) or not isinstance(aliases, list):
            continue
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm and alias_norm in haystack and brand_id not in seen:
                seen.add(brand_id)
                entities.append({"brand_id": brand_id, "display_name": record.get("display_name") or brand_id, "matched_alias": alias})
                break
    return entities


def resolve_user_provided_palette(brief: str, evidence: dict[str, Any] | None = None) -> dict[str, Any] | None:
    text = f"{brief}\n{json.dumps(evidence or {}, ensure_ascii=False)}"
    colors = [normalize_hex(match.group(0)) for match in HEX_RE.finditer(text)]
    unique: list[str] = []
    for color in colors:
        if color not in unique:
            unique.append(color)
    if not unique:
        return None
    primary = unique[0]
    accent = unique[1] if len(unique) > 1 else primary
    return {
        "source": "user_provided",
        "palette_source": "user_provided",
        "confidence": "high",
        "colors": {
            "primary": primary,
            "accent": accent,
        },
        "evidence": [
            {
                "type": "user_provided",
                "source": "brief_or_evidence_hex_color",
                "matched_colors": unique,
            }
        ],
    }


def load_brand_registry(path: Path | None = None) -> dict[str, Any]:
    return read_json(path or BRAND_REGISTRY_PATH)


def load_palette_registry(path: Path | None = None) -> dict[str, Any]:
    return read_json(path or PALETTE_REGISTRY_PATH)


def resolve_brand_registry_palette(entities: list[dict[str, Any]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {record.get("brand_id"): record for record in registry.get("brands", []) if isinstance(record, dict)}
    resolutions: list[dict[str, Any]] = []
    for entity in entities:
        brand_id = entity.get("brand_id")
        record = by_id.get(brand_id)
        if not isinstance(record, dict):
            continue
        resolutions.append(
            {
                "brand_id": brand_id,
                "display_name": record.get("display_name") or brand_id,
                "source": "brand_registry",
                "palette_source": "brand_registry",
                "confidence": record.get("confidence") or "low",
                "colors": record.get("palette") if isinstance(record.get("palette"), dict) else {},
                "evidence": [
                    {
                        "type": "brand_registry",
                        "source_trace": f"svglide-brand-palette-registry.json:{brand_id}",
                        "matched_alias": entity.get("matched_alias"),
                        "record_confidence": record.get("confidence") or "low",
                    }
                ],
            }
        )
    return resolutions


def resolve_asset_extracted_palette(project_root: Path, evidence: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    evidence_obj = evidence or {}
    for key in ("dominant_colors", "visual_identity_palette_candidates", "palette_candidates"):
        raw = evidence_obj.get(key)
        if isinstance(raw, list):
            colors = [normalize_hex(item) for item in raw if isinstance(item, str) and HEX_RE.fullmatch(item.strip())]
            if len(colors) >= 2:
                candidates.append(
                    {
                        "source": "source_asset_extract",
                        "palette_source": "source_asset_extract",
                        "confidence": "medium",
                        "colors": {"primary": colors[0], "accent": colors[1]},
                        "evidence": [{"type": "source_asset_extract", "source": key, "matched_colors": colors}],
                    }
                )
    return candidates


def stable_palette_fallback(signals: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    active = [item for item in registry.get("palettes", []) if isinstance(item, dict) and item.get("status") == "active"]
    if not active:
        raise ValueError("palette registry has no active palettes")
    seed = stable_seed({"signals": signals, "registry_version": registry.get("schema_version"), "strategy": "stable_palette_fallback"})
    ranked = sorted(active, key=lambda item: (stable_seed({"seed": seed, "palette_id": item.get("palette_id")}), str(item.get("palette_id"))))
    selected = ranked[0]
    colors = selected.get("colors") if isinstance(selected.get("colors"), dict) else {}
    return {
        "source": "stable_fallback",
        "palette_source": "stable_fallback",
        "confidence": "low",
        "palette_id": selected.get("palette_id"),
        "fallback_seed": seed,
        "colors": {
            "primary": colors.get("primary"),
            "accent": colors.get("accent"),
            "background": colors.get("background"),
            "text": colors.get("text"),
        },
        "evidence": [{"type": "stable_fallback", "source": "svglide-palette-registry.json", "fallback_seed": seed}],
    }


def merge_brand_resolutions(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    first = resolutions[0]
    second = resolutions[1] if len(resolutions) > 1 else first
    first_colors = first.get("colors") if isinstance(first.get("colors"), dict) else {}
    second_colors = second.get("colors") if isinstance(second.get("colors"), dict) else {}
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    confidence = min(
        (str(item.get("confidence") or "low") for item in resolutions),
        key=lambda value: confidence_order.get(value, 0),
    )
    return {
        "source": "brand_registry",
        "palette_source": "brand_registry",
        "confidence": confidence,
        "brands": [item.get("brand_id") for item in resolutions],
        "colors": {
            "primary": first_colors.get("primary"),
            "accent": second_colors.get("accent") or first_colors.get("accent") or first_colors.get("primary"),
            "background": first_colors.get("background"),
            "text": first_colors.get("text"),
        },
        "evidence": [evidence for item in resolutions for evidence in item.get("evidence", []) if isinstance(evidence, dict)],
    }


def resolve_brand_palette(project_root: Path, brief: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    user_palette = resolve_user_provided_palette(brief, evidence)
    if user_palette is not None:
        return user_palette

    brand_registry = load_brand_registry()
    entities = extract_brand_entities(brief, evidence)
    registry_resolutions = resolve_brand_registry_palette(entities, brand_registry)
    if registry_resolutions:
        return merge_brand_resolutions(registry_resolutions)

    asset_resolutions = resolve_asset_extracted_palette(project_root, evidence)
    if asset_resolutions:
        return asset_resolutions[0]

    palette_registry = load_palette_registry()
    return stable_palette_fallback({"brief": brief, "entities": entities}, palette_registry)
