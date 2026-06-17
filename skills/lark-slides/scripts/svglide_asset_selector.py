#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


SELECTION_SCHEMA_VERSION = "svglide-asset-selection/v1"
STRICT_LANES = {"production", "golden"}
DEFAULT_BUDGET = {
    "brand": 1,
    "layout": 3,
    "deck": 1,
    "chart": 6,
    "icon_style": 1,
    "visual_style": 2,
    "image_palette": 1,
    "image_rendering": 1,
    "image_type": 2,
    "narrative_mode": 1,
    "example": 1,
}
DEFAULT_TOTAL_BUDGET = 12
KIND_BUCKETS = {
    "brand_preset": "brand",
    "layout_template": "layout",
    "deck_template": "deck",
    "chart_template": "chart",
    "icon_library": "icon_style",
    "visual_style": "visual_style",
    "image_palette": "image_palette",
    "image_rendering": "image_rendering",
    "image_type_template": "image_type",
    "narrative_mode": "narrative_mode",
    "example_project": "example",
}
ACTIVATION_PRIORITY = {"active": 3, "validated": 2, "candidate": 1, "rejected": 0}
TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)


class SelectorError(ValueError):
    """Raised when selector inputs or policies are invalid."""


def script_path() -> Path:
    return Path(__file__).resolve()


def default_asset_map_path() -> Path:
    return script_path().parents[1] / "references/svglide-design-pattern-map.json"


def load_asset_map(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tokenize(*values: object) -> list[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            tokens.update(tokenize(*value))
            continue
        tokens.update(match.group(0).lower() for match in TOKEN_RE.finditer(str(value)))
    return sorted(tokens)


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def kind_bucket(kind: str) -> str:
    return KIND_BUCKETS.get(kind, kind)


def normalize_budget(budget: dict[str, int] | None = None) -> dict[str, int]:
    normalized = dict(DEFAULT_BUDGET)
    if budget:
        for key, value in budget.items():
            if value < 0:
                raise SelectorError(f"budget for {key} must be non-negative")
            normalized[key] = value
    return normalized


def parse_budget_override(raw: str) -> dict[str, int]:
    if not raw:
        return {}
    parsed: dict[str, int] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise SelectorError(f"invalid budget override {item!r}; expected kind=count")
        key, value = item.split("=", 1)
        parsed[key.strip()] = int(value.strip())
    return parsed


def has_normalized_fixture(resource: dict) -> bool:
    if resource.get("normalized_fixture") or resource.get("normalized_fixture_path"):
        return True
    metadata = resource.get("metadata", {})
    return bool(metadata.get("normalized_fixture") or metadata.get("normalized_fixture_path"))


def strict_policy_violation(resource: dict) -> str:
    status = resource.get("activation_status", "")
    if status not in {"validated", "active"}:
        return "activation_status_not_production_ready"
    if resource.get("license_status") in {"unknown", "reference_only", "unknown/reference_only"}:
        return "license_not_production_ready"
    if resource.get("protocol_compatibility") == "needs_normalization" and not has_normalized_fixture(resource):
        return "raw_asset_needs_normalization"
    return ""


def resource_policy_violation(resource: dict, lane: str) -> str:
    if resource.get("activation_status") == "rejected":
        return "rejected_asset"
    if lane in STRICT_LANES:
        return strict_policy_violation(resource)
    return ""


def searchable_tokens(resource: dict) -> set[str]:
    metadata = resource.get("metadata", {})
    return set(
        tokenize(
            resource.get("id", ""),
            resource.get("kind", ""),
            resource.get("source_path", ""),
            resource.get("summary", ""),
            resource.get("selection_tags", []),
            metadata.get("summary", ""),
            metadata.get("page_types", []),
            metadata.get("sample_icons", []),
            metadata.get("page_samples", []),
            metadata.get("media_samples", []),
        )
    )


def score_resource(resource: dict, brief_tokens: set[str], explicit_tags: set[str]) -> tuple[int, list[str]]:
    tokens = searchable_tokens(resource)
    matched_tags = sorted(explicit_tags & tokens)
    matched_brief = sorted(brief_tokens & tokens)
    score = len(matched_tags) * 8 + len(matched_brief) * 2
    if score:
        if resource.get("activation_status") == "active":
            score += 3
        elif resource.get("activation_status") == "validated":
            score += 2
    return score, matched_tags + [token for token in matched_brief if token not in matched_tags]


def slim_asset(resource: dict, *, reason: str, score: int = 0, matched_terms: Iterable[str] = ()) -> dict:
    output = {
        "id": resource["id"],
        "kind": resource["kind"],
        "reason": reason,
        "activation_status": resource.get("activation_status", ""),
    }
    if resource.get("source_path"):
        output["source_path"] = resource["source_path"]
    if score:
        output["score"] = score
    terms = sorted(set(matched_terms))
    if terms:
        output["matched_terms"] = terms[:12]
    return output


def select_assets(
    asset_map: dict,
    *,
    brief: str,
    tags: Iterable[str] = (),
    lane: str = "authoring",
    budget: dict[str, int] | None = None,
    max_total_assets: int = DEFAULT_TOTAL_BUDGET,
) -> dict:
    if lane not in {"authoring", "research", "production", "golden"}:
        raise SelectorError(f"unsupported lane: {lane}")

    normalized_budget = normalize_budget(budget)
    brief_tokens = set(tokenize(brief))
    explicit_tags = set(tokenize(list(tags)))
    selected: list[dict] = []
    excluded: list[dict] = []
    per_kind_counts = {key: 0 for key in normalized_budget}
    candidates: list[tuple[int, int, str, dict, list[str]]] = []

    for resource in asset_map.get("resources", []):
        bucket = kind_bucket(resource.get("kind", ""))
        if bucket not in normalized_budget:
            continue
        score, matched = score_resource(resource, brief_tokens, explicit_tags)
        if score <= 0:
            continue
        violation = resource_policy_violation(resource, lane)
        if violation:
            excluded.append(slim_asset(resource, reason=violation, score=score, matched_terms=matched))
            continue
        priority = ACTIVATION_PRIORITY.get(resource.get("activation_status", ""), 0)
        candidates.append((score, priority, resource["id"], resource, matched))

    for score, _priority, _resource_id, resource, matched in sorted(candidates, key=lambda item: (-item[0], -item[1], item[2])):
        bucket = kind_bucket(resource["kind"])
        if per_kind_counts[bucket] >= normalized_budget[bucket]:
            continue
        if len(selected) >= max_total_assets:
            break
        per_kind_counts[bucket] += 1
        reason = f"matches {', '.join(matched[:5])}" if matched else "matches selector query"
        selected.append(slim_asset(resource, reason=reason, score=score, matched_terms=matched))

    request = {
        "brief": brief,
        "tags": sorted(explicit_tags),
        "lane": lane,
        "budget": normalized_budget,
        "max_total_assets": max_total_assets,
        "asset_map_digest": asset_map.get("summary", {}).get("digests", {}).get("all_source_files", canonical_digest(asset_map)),
    }
    output = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "deck_intent": infer_deck_intent(brief_tokens, explicit_tags),
        "lane": lane,
        "selected_assets": selected,
        "excluded_assets": sorted(excluded, key=lambda item: (-item.get("score", 0), item["id"]))[:50],
        "prompt_budget": {
            "max_assets_per_kind": normalized_budget,
            "max_total_assets": max_total_assets,
            "total_selected": len(selected),
            "selected_per_kind": per_kind_counts,
            "estimated_prompt_tokens": estimate_prompt_tokens(selected),
        },
        "request_digest": canonical_digest(request),
    }
    output["selection_digest"] = canonical_digest({"request_digest": output["request_digest"], "selected_assets": selected})
    return output


def infer_deck_intent(brief_tokens: set[str], tags: set[str]) -> str:
    tokens = brief_tokens | tags
    if {"roadmap", "milestone", "timeline"} & tokens:
        return "roadmap"
    if {"strategy", "business", "market", "growth"} & tokens:
        return "business_strategy"
    if {"architecture", "system", "technical", "engineering", "ops"} & tokens:
        return "technical_architecture"
    if {"academic", "research", "thesis"} & tokens:
        return "academic_report"
    return "general_deck"


def estimate_prompt_tokens(selected_assets: list[dict]) -> int:
    if not selected_assets:
        return 0
    encoded = json.dumps(selected_assets, ensure_ascii=False, sort_keys=True)
    return max(1, len(encoded) // 4)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select a small SVGlide active asset context from svglide-design-pattern-map.json.")
    parser.add_argument("--asset-map", type=Path, default=default_asset_map_path())
    parser.add_argument("--brief", default="", help="User brief or deck topic.")
    parser.add_argument("--tags", default="", help="Comma-separated explicit selector tags.")
    parser.add_argument("--lane", default="authoring", choices=["authoring", "research", "production", "golden"])
    parser.add_argument("--budget", default="", help="Comma-separated per-kind overrides, e.g. chart=3,layout=2.")
    parser.add_argument("--max-total-assets", type=int, default=DEFAULT_TOTAL_BUDGET)
    parser.add_argument("--out-json", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    asset_map = load_asset_map(args.asset_map)
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    selection = select_assets(
        asset_map,
        brief=args.brief,
        tags=tags,
        lane=args.lane,
        budget=parse_budget_override(args.budget),
        max_total_assets=args.max_total_assets,
    )
    encoded = json.dumps(selection, ensure_ascii=False, indent=2) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
