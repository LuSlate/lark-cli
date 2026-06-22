#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_brand_palette_resolver as brand_resolver
import svglide_semantic_asset_matcher as semantic_matcher


SCHEMA_VERSION = "svglide-palette-selection/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PALETTE_REGISTRY_PATH = SCRIPT_DIR.parent / "references" / "svglide-palette-registry.json"
INSTRUCTION_PATH = Path("00-input/instruction.json")
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
PALETTE_RECEIPT_PATH = Path("receipts/palette_selection.json")


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


def stable_seed(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_palette_registry() -> dict[str, Any]:
    return read_json(PALETTE_REGISTRY_PATH)


def project_brief(project_root: Path, explicit_brief: str | None = None) -> str:
    if explicit_brief:
        return explicit_brief
    instruction_path = project_root / INSTRUCTION_PATH
    if instruction_path.exists():
        instruction = read_json(instruction_path)
        for key in ("raw_prompt", "prompt", "brief"):
            value = instruction.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def palette_metadata(palette: dict[str, Any]) -> dict[str, Any]:
    metadata = palette.get("selection_metadata")
    return metadata if isinstance(metadata, dict) else {}


def lower_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip().lower() for item in values if str(item).strip()]


def signal_values(signals: dict[str, Any], field: str) -> list[str]:
    value = signals.get(field)
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().lower()]
    return []


def score_palette(signals: dict[str, Any], palette: dict[str, Any], brand_resolution: dict[str, Any]) -> dict[str, Any]:
    metadata = palette_metadata(palette)
    palette_id = str(palette.get("palette_id") or palette.get("id") or "")
    matched: list[str] = []
    missed: list[str] = []
    rejection_reasons: list[str] = []
    score = 0

    brands = [str(item).lower() for item in brand_resolution.get("brands", []) if isinstance(item, str)]
    brand_affinity = lower_list(metadata.get("brand_affinity"))
    for brand in brands:
        if brand in brand_affinity:
            score += 18
            matched.append(f"brand_affinity:{brand}")
        elif brand_affinity:
            missed.append(f"brand_affinity:{brand}")
    if brands and palette_id == f"brand.{brands[0]}":
        score += 3
        matched.append(f"brand_primary_entity:{brands[0]}")

    for field, metadata_key, weight in (
        ("tone", "tone_tags", 4),
        ("mood", "tone_tags", 3),
        ("density", "density", 4),
        ("formality", "formality", 4),
        ("industry", "industry_tags", 5),
        ("occasion", "best_for", 3),
        ("content_shape", "best_for", 3),
    ):
        wanted = signal_values(signals, field)
        raw_have = metadata.get(metadata_key)
        have = lower_list(raw_have) if isinstance(raw_have, list) else ([str(raw_have).strip().lower()] if isinstance(raw_have, str) else [])
        for value in wanted:
            if value in have or any(value in item or item in value for item in have):
                score += weight
                matched.append(f"{field}:{value}")
            elif have:
                missed.append(f"{field}:{value}")

    mode = str(palette.get("mode") or "").lower()
    requested_scheme = signals.get("scheme")
    if isinstance(requested_scheme, str) and requested_scheme:
        if requested_scheme == mode or mode == "mixed":
            score += 6
            matched.append(f"scheme:{requested_scheme}")
        else:
            score -= 8
            rejection_reasons.append("style_mismatch:scheme")

    source = brand_resolution.get("source")
    if source == "brand_registry" and brands and not any(item.startswith("brand_affinity:") for item in matched):
        score -= 6
        rejection_reasons.append("brand_palette_not_native_to_palette")
    if source == "stable_fallback":
        fallback_id = brand_resolution.get("palette_id")
        if fallback_id == palette_id:
            score += 10
            matched.append("stable_fallback:selected_palette")

    if not matched:
        rejection_reasons.append("low_semantic_overlap")
    return {
        "palette_id": palette_id,
        "score": score,
        "matched_signals": matched,
        "missed_signals": missed,
        "selection_reason": matched[:5],
        "rejection_reasons": rejection_reasons,
    }


def confidence_from_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "low"
    top = int(candidates[0].get("score") or 0)
    second = int(candidates[1].get("score") or 0) if len(candidates) > 1 else 0
    if top >= 24 and top - second >= 5:
        return "high"
    if top >= 15:
        return "medium"
    return "low"


def project_palette_from_selection(palette: dict[str, Any], brand_resolution: dict[str, Any], confidence: str) -> dict[str, Any]:
    colors = dict(palette.get("colors") if isinstance(palette.get("colors"), dict) else {})
    brand_colors = brand_resolution.get("colors") if isinstance(brand_resolution.get("colors"), dict) else {}
    for key in ("primary", "accent", "background", "text"):
        value = brand_colors.get(key)
        if isinstance(value, str) and value:
            colors[key] = value
    return {
        "palette_id": palette.get("palette_id"),
        "source": brand_resolution.get("source"),
        "confidence": confidence,
        "selection_receipt": PALETTE_SELECTION_PATH.as_posix(),
        "colors": colors,
        "data_series": palette.get("data_series") if isinstance(palette.get("data_series"), list) else [],
    }


def select_palette(project_root: Path, brief: str, *, top_k: int = 5, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = load_palette_registry()
    signals = semantic_matcher.infer_brief_signals(brief)
    brand_resolution = brand_resolver.resolve_brand_palette(project_root, brief, evidence)
    scored = [
        score_palette(signals, palette, brand_resolution)
        for palette in registry.get("palettes", [])
        if isinstance(palette, dict) and palette.get("status") == "active"
    ]
    scored.sort(key=lambda item: (-int(item["score"]), str(item["palette_id"])))
    confidence = confidence_from_candidates(scored)
    if confidence == "low" and brand_resolution.get("source") not in {"stable_fallback", "user_provided"}:
        fallback = brand_resolver.stable_palette_fallback(signals, registry)
        brand_resolution = {**fallback, "previous_resolution": brand_resolution}
        scored = [
            score_palette(signals, palette, brand_resolution)
            for palette in registry.get("palettes", [])
            if isinstance(palette, dict) and palette.get("status") == "active"
        ]
        scored.sort(key=lambda item: (-int(item["score"]), str(item["palette_id"])))
        confidence = confidence_from_candidates(scored)

    selected_id = scored[0]["palette_id"] if scored else None
    palette_by_id = {item.get("palette_id"): item for item in registry.get("palettes", []) if isinstance(item, dict)}
    selected_palette = palette_by_id.get(selected_id, {})
    seed = stable_seed({"brief": brief, "signals": signals, "registry_version": registry.get("schema_version")})
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "palette_selection",
        "created_at": now_iso(),
        "brief_signals": signals,
        "selected_palette_id": selected_id,
        "confidence": confidence,
        "fallback_policy": "stable_palette_fallback" if brand_resolution.get("source") == "stable_fallback" else "not_used",
        "deterministic_seed": seed,
        "brand_resolution": brand_resolution,
        "palette_candidates": scored[:top_k],
        "candidate_palette_ids_considered": [item["palette_id"] for item in scored],
        "project_palette": project_palette_from_selection(selected_palette, brand_resolution, confidence) if selected_palette else None,
    }


def write_palette_selection(project_root: Path, selection: dict[str, Any]) -> Path:
    output = project_root / PALETTE_SELECTION_PATH
    write_json(output, selection)
    write_json(project_root / PALETTE_RECEIPT_PATH, selection)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select a deterministic SVGlide project palette.")
    parser.add_argument("project_root")
    parser.add_argument("--brief")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    brief = project_brief(project_root, args.brief)
    selection = select_palette(project_root, brief, top_k=args.top_k)
    write_palette_selection(project_root, selection)
    print(json.dumps(selection, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
