#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import svglide_semantic_asset_matcher


SCRIPT_DIR = Path(__file__).resolve().parent
LARK_SLIDES_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = LARK_SLIDES_DIR / "references"
RECIPE_REGISTRY_PATH = REFERENCES_DIR / "svglide-deck-recipe-registry.json"
STYLE_PACK_REGISTRY_PATH = REFERENCES_DIR / "svglide-style-pack-registry.json"

MATCH_LEVEL_THRESHOLDS = {
    "L1": 32,
    "L2": 16,
    "L3": 8,
}

REQUIRED_RECIPE_METADATA_FIELDS = {"mood", "tone", "best_for", "avoid_for", "density", "formality"}
NOISE_ONLY_RE = re.compile(r"随便|高级感|好看|酷炫|没有主题|灵感合集|whatever|make it nice", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def load_recipe_registry(path: Path = RECIPE_REGISTRY_PATH) -> list[dict[str, Any]]:
    payload = load_json(path)
    recipes = payload.get("recipes")
    if not isinstance(recipes, list):
        raise ValueError(f"{path} must contain recipes[]")
    return [item for item in recipes if isinstance(item, dict)]


def load_style_pack_registry(path: Path = STYLE_PACK_REGISTRY_PATH) -> list[dict[str, Any]]:
    payload = load_json(path)
    packs = payload.get("style_packs")
    if not isinstance(packs, list):
        raise ValueError(f"{path} must contain style_packs[]")
    return [item for item in packs if isinstance(item, dict)]


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def text_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for child in value for item in text_values(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in text_values(child)]
    text = normalize_text(value)
    return [text] if text else []


def prompt_contains(prompt_norm: str, signal: str) -> bool:
    signal_norm = normalize_text(signal)
    if not signal_norm:
        return False
    if re.fullmatch(r"[a-z0-9 ]+", signal_norm):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(signal_norm)}(?![a-z0-9])", prompt_norm))
    return signal_norm in prompt_norm


def matching_values(prompt_norm: str, values: Any) -> list[str]:
    matched: list[str] = []
    for value in text_values(values):
        if prompt_contains(prompt_norm, value):
            matched.append(value)
    return sorted(set(matched))


def registry_text(recipe: dict[str, Any]) -> list[str]:
    fields = [
        "keywords",
        "intent_tags",
        "content_shape",
        "audience",
        "component_slots",
        "image_treatment_candidates",
    ]
    values: list[str] = []
    for field in fields:
        values.extend(text_values(recipe.get(field)))
    metadata = recipe.get("metadata") if isinstance(recipe.get("metadata"), dict) else {}
    values.extend(text_values(metadata.get("best_for")))
    return values


def prompt_specific_enough(prompt: str) -> bool:
    prompt_norm = normalize_text(prompt)
    if len(prompt_norm) < 6:
        return False
    if NOISE_ONLY_RE.search(prompt_norm) and not svglide_semantic_asset_matcher.infer_brief_signals(prompt):
        return False
    return True


def score_recipe(prompt: str, recipe: dict[str, Any]) -> dict[str, Any]:
    prompt_norm = normalize_text(prompt)
    score = 0
    signals: dict[str, list[str]] = {}

    keyword_matches = matching_values(prompt_norm, recipe.get("keywords"))
    score += len(keyword_matches) * 8
    if keyword_matches:
        signals["keywords"] = keyword_matches

    for field, weight in [
        ("intent_tags", 5),
        ("content_shape", 5),
        ("audience", 4),
        ("component_slots", 3),
        ("image_treatment_candidates", 3),
    ]:
        matches = matching_values(prompt_norm, recipe.get(field))
        if matches:
            score += len(matches) * weight
            signals[field] = matches

    metadata = recipe.get("metadata") if isinstance(recipe.get("metadata"), dict) else {}
    for field, weight in [("best_for", 5), ("mood", 2), ("tone", 2)]:
        matches = matching_values(prompt_norm, metadata.get(field))
        if matches:
            score += len(matches) * weight
            signals[f"metadata.{field}"] = matches

    inferred = svglide_semantic_asset_matcher.infer_brief_signals(prompt)
    inferred_values = [value for value in text_values(inferred) if value]
    registry_values = set(registry_text(recipe))
    inferred_matches = sorted({value for value in inferred_values if value in registry_values})
    if inferred_matches:
        score += len(inferred_matches) * 3
        signals["semantic_asset_matcher"] = inferred_matches

    avoid_matches = matching_values(prompt_norm, recipe.get("avoid_when"))
    if avoid_matches:
        score -= len(avoid_matches) * 12
        signals["avoid_when"] = avoid_matches

    return {
        "recipe_id": recipe.get("recipe_id"),
        "score": max(score, 0),
        "signals": signals,
    }


def match_level(score: int) -> str:
    if score >= MATCH_LEVEL_THRESHOLDS["L1"]:
        return "L1"
    if score >= MATCH_LEVEL_THRESHOLDS["L2"]:
        return "L2"
    if score >= MATCH_LEVEL_THRESHOLDS["L3"]:
        return "L3"
    return "L4"


def confidence_for(score: int, level: str) -> float:
    if level == "L4":
        return 0.0
    if level == "L3":
        return round(min(0.49, 0.32 + score / 80), 2)
    if level == "L2":
        return round(min(0.74, 0.5 + score / 100), 2)
    return round(min(0.95, 0.72 + score / 180), 2)


def missing_signals_for(prompt: str, scored: list[dict[str, Any]]) -> list[str]:
    prompt_norm = normalize_text(prompt)
    missing = ["intent", "content_shape", "audience"]
    if not prompt_norm:
        missing.append("prompt")
    if scored and scored[0]["score"] > 0:
        missing.append("sufficient_recipe_confidence")
    if NOISE_ONLY_RE.search(prompt_norm):
        missing.append("specific_subject")
    return sorted(set(missing))


def style_pack_score(prompt: str, recipe: dict[str, Any], pack: dict[str, Any]) -> int:
    prompt_norm = normalize_text(prompt)
    score = 0
    metadata = pack.get("metadata") if isinstance(pack.get("metadata"), dict) else {}
    for field, weight in [("best_for", 7), ("mood", 3), ("tone", 3)]:
        score += len(matching_values(prompt_norm, metadata.get(field))) * weight
    if pack.get("style_pack_id") in recipe.get("style_pack_candidates", []):
        score += 20
    if pack.get("image_treatment_id") in recipe.get("image_treatment_candidates", []):
        score += 4
    avoid = matching_values(prompt_norm, metadata.get("avoid_for"))
    score -= len(avoid) * 10
    return score


def select_style_pack(prompt: str, recipe: dict[str, Any], packs: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_ids = set(recipe.get("style_pack_candidates", []))
    candidates = [pack for pack in packs if pack.get("style_pack_id") in candidate_ids]
    if not candidates:
        candidates = packs
    ranked = sorted(
        candidates,
        key=lambda pack: (-style_pack_score(prompt, recipe, pack), str(pack.get("style_pack_id"))),
    )
    return ranked[0]


def build_failed_selection(prompt: str, scored: list[dict[str, Any]]) -> dict[str, Any]:
    best = scored[0] if scored else {"recipe_id": None, "score": 0, "signals": {}}
    return {
        "schema_version": "svglide-design-asset-selection/v1",
        "status": "failed",
        "action": "fail_closed",
        "prompt": prompt,
        "deck_recipe_selection": {
            "recipe_id": best.get("recipe_id"),
            "match_level": "L4",
            "confidence": 0.0,
            "signals": best.get("signals") or {},
            "missing_signals": missing_signals_for(prompt, scored),
            "candidate_recipe_ids": [str(item["recipe_id"]) for item in scored[:5] if item.get("recipe_id")],
            "selection_reason": "No recipe reached the minimum confidence required to generate.",
        },
    }


def build_success_selection(
    prompt: str,
    recipe: dict[str, Any],
    recipe_score: dict[str, Any],
    style_pack: dict[str, Any],
    scored: list[dict[str, Any]],
) -> dict[str, Any]:
    level = match_level(int(recipe_score["score"]))
    template_candidates = [str(item) for item in recipe.get("template_family_candidates", [])]
    style_pack_id = str(style_pack["style_pack_id"])
    image_treatment_id = str(style_pack["image_treatment_id"])
    density_modes = [str(item) for item in recipe.get("density_modes", [])]
    component_slots = [str(item) for item in recipe.get("component_slots", [])]
    decoration_policy_id = str(style_pack["decoration_policy_id"])
    return {
        "schema_version": "svglide-design-asset-selection/v1",
        "status": "passed",
        "action": "generate",
        "prompt": prompt,
        "deck_recipe_selection": {
            "recipe_id": recipe["recipe_id"],
            "display_name": recipe.get("display_name"),
            "match_level": level,
            "confidence": confidence_for(int(recipe_score["score"]), level),
            "signals": recipe_score["signals"],
            "missing_signals": [],
            "candidate_recipe_ids": [str(item["recipe_id"]) for item in scored[:5] if item.get("recipe_id")],
            "selection_reason": "Matched recipe metadata from prompt intent, content shape, audience, and asset signals.",
        },
        "template_family_selection": {
            "enabled": True,
            "source": "beautiful-html-template-families",
            "selected_template_id": template_candidates[0],
            "candidate_template_ids": template_candidates,
            "selection_reason": f"Recipe {recipe['recipe_id']} prefers this template family for structure; final visual skin comes from style_pack.",
        },
        "style_pack_selection": {
            "selected_style_pack_id": style_pack_id,
            "candidate_style_pack_ids": [str(item) for item in recipe.get("style_pack_candidates", [])],
            "selection_reason": f"Selected {style_pack_id} because it matches the recipe tone and image treatment requirements.",
            "palette_id": style_pack["palette_id"],
            "typography_id": style_pack["typography_id"],
            "background_system_id": style_pack["background_system_id"],
            "chart_palette_id": style_pack["chart_palette_id"],
            "image_treatment_id": image_treatment_id,
            "decoration_policy_id": decoration_policy_id,
            "component_variant_bias": style_pack["component_variant_bias"],
        },
        "density_mode_selection": {
            "selected_density_mode": density_modes[0],
            "candidate_density_modes": density_modes,
            "selection_reason": "Density mode follows the matched deck recipe rather than per-page reinvention.",
        },
        "component_variant_selection": {
            "selected_component_variants": component_slots[:6],
            "candidate_component_variants": component_slots,
            "selection_reason": "Component variants are constrained by recipe slots and style_pack bias.",
        },
        "image_treatment_selection": {
            "selected_image_treatment_id": image_treatment_id,
            "candidate_image_treatment_ids": [str(item) for item in recipe.get("image_treatment_candidates", [])],
            "selection_reason": "Image treatment is locked at deck level; local preview and live create must consume the same metadata.",
        },
        "style_lock": {
            "template_family_id": template_candidates[0],
            "style_pack_id": style_pack_id,
            "palette_id": style_pack["palette_id"],
            "typography_id": style_pack["typography_id"],
            "background_system_id": style_pack["background_system_id"],
            "chart_palette_id": style_pack["chart_palette_id"],
            "image_treatment_id": image_treatment_id,
            "decoration_policy_id": decoration_policy_id,
            "component_variant_bias": style_pack["component_variant_bias"],
            "deck_level": True,
        },
    }


def validate_registry_contracts(recipes: list[dict[str, Any]], packs: list[dict[str, Any]]) -> None:
    style_pack_ids = {pack.get("style_pack_id") for pack in packs}
    for recipe in recipes:
        metadata = recipe.get("metadata") if isinstance(recipe.get("metadata"), dict) else {}
        missing = REQUIRED_RECIPE_METADATA_FIELDS - set(metadata)
        if missing:
            raise ValueError(f"recipe {recipe.get('recipe_id')} missing metadata fields: {sorted(missing)}")
        if not set(recipe.get("style_pack_candidates", [])) & style_pack_ids:
            raise ValueError(f"recipe {recipe.get('recipe_id')} has no valid style_pack_candidates")


def select_design_assets(prompt: str) -> dict[str, Any]:
    recipes = load_recipe_registry()
    packs = load_style_pack_registry()
    validate_registry_contracts(recipes, packs)
    scored = sorted(
        [score_recipe(prompt, recipe) for recipe in recipes],
        key=lambda item: (-int(item["score"]), str(item.get("recipe_id"))),
    )
    if not prompt_specific_enough(prompt) or not scored:
        return build_failed_selection(prompt, scored)
    best = scored[0]
    level = match_level(int(best["score"]))
    if level == "L4":
        return build_failed_selection(prompt, scored)
    recipes_by_id = {recipe["recipe_id"]: recipe for recipe in recipes}
    recipe = recipes_by_id[str(best["recipe_id"])]
    style_pack = select_style_pack(prompt, recipe, packs)
    return build_success_selection(prompt, recipe, best, style_pack, scored)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select SVGlide deck recipe and composable design assets.")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    result = select_design_assets(args.prompt)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
