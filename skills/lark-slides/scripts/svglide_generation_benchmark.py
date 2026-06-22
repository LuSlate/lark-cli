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


SCHEMA_VERSION = "svglide-generation-benchmark/v1"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "svglide_benchmark" / "topics.json"
CACHE_ROOT = Path(".svglide-cache")


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_topics(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"expected topic array: {path}")
    return [item for item in payload if isinstance(item, dict)]


def cache_key(prompt: str, *, profile: str, template_library_version: str, asset_policy_version: str) -> dict[str, str]:
    return {
        "prompt_semantic_hash": f"sha256:{sha256_text(prompt.strip().lower())}",
        "profile": profile,
        "template_library_version": template_library_version,
        "asset_policy_version": asset_policy_version,
    }


def cache_path(project_root: Path, kind: str, key: dict[str, str]) -> Path:
    digest = sha256_text(json.dumps(key, ensure_ascii=False, sort_keys=True))
    return project_root / CACHE_ROOT / kind / f"{digest}.json"


def lookup_cache(project_root: Path, kind: str, key: dict[str, str]) -> dict[str, Any]:
    path = cache_path(project_root, kind, key)
    if not path.exists():
        return {"kind": kind, "hit": False, "path": path.relative_to(project_root).as_posix()}
    payload = read_json(path)
    return {"kind": kind, "hit": True, "path": path.relative_to(project_root).as_posix(), "payload": payload}


def write_cache(project_root: Path, kind: str, key: dict[str, str], payload: dict[str, Any]) -> Path:
    path = cache_path(project_root, kind, key)
    write_json(
        path,
        {
            "schema_version": "svglide-generation-cache/v1",
            "kind": kind,
            "key": key,
            "created_at": now_iso(),
            "payload": payload,
        },
    )
    return path


def evaluate_project_against_topic(project_root: Path, topic: dict[str, Any]) -> dict[str, Any]:
    plan_path = project_root / "02-plan/slide_plan.json"
    plan = read_json(plan_path) if plan_path.exists() else {}
    quality_gate = read_json_optional(project_root / "06-check/quality-gate.json")
    gate_summary = quality_gate.get("summary") if isinstance(quality_gate.get("summary"), dict) else {}
    asset_manifest = read_json_optional(project_root / "03-assets/asset-manifest.json")
    asset_summary = asset_manifest.get("summary") if isinstance(asset_manifest.get("summary"), dict) else {}
    slides = plan.get("slides") if isinstance(plan, dict) else []
    slide_count = len(slides) if isinstance(slides, list) else 0
    min_pages, max_pages = topic.get("expected_page_count_range", [0, 999])
    page_count_ok = isinstance(min_pages, int) and isinstance(max_pages, int) and min_pages <= slide_count <= max_pages
    project_palette = plan.get("project_palette") if isinstance(plan, dict) and isinstance(plan.get("project_palette"), dict) else {}
    project_theme = plan.get("project_theme") if isinstance(plan, dict) and isinstance(plan.get("project_theme"), dict) else {}
    base_theme = project_theme.get("base_theme_id")
    baseline_ok = base_theme not in {"baseline", "baseline-theme", "safe-native-v1", "default"}
    token_overrides = project_theme.get("token_overrides") if isinstance(project_theme.get("token_overrides"), dict) else {}
    palette_consistency_ok = bool(project_palette and token_overrides)
    real_assets = gate_summary.get("asset_real_coverage") or gate_summary.get("asset_acquired_count") or asset_summary.get("asset_acquired_count") or 0
    fallback_count = gate_summary.get("asset_fallback_count") or asset_summary.get("asset_fallback_count") or asset_summary.get("fallback_count") or 0
    online_image_policy_ok = not topic.get("requires_online_images") or (isinstance(real_assets, int) and real_assets > 0)
    fallback_ok = isinstance(fallback_count, int) and fallback_count == 0
    chart_rich_pages = [
        slide
        for slide in slides
        if isinstance(slide, dict)
        and (
            any(term in str(slide.get("visual_recipe") or "").lower() for term in ["chart", "dashboard", "trend", "stat", "data"])
            or isinstance(slide.get("chart_contract"), dict)
            or any(term in str(slide.get("renderer_id") or "").lower() for term in ["chart", "dashboard", "trend", "stat", "data"])
        )
    ]
    chart_rich_ok = not topic.get("requires_chart_rich_pages") or bool(chart_rich_pages)
    checks = {
        "page_count_ok": page_count_ok,
        "baseline_ok": baseline_ok,
        "palette_consistency_ok": palette_consistency_ok,
        "online_image_policy_ok": online_image_policy_ok,
        "fallback_ok": fallback_ok,
        "chart_rich_ok": chart_rich_ok,
    }
    return {
        "topic_id": topic.get("id"),
        "prompt": topic.get("prompt"),
        "slide_count": slide_count,
        "expected_page_count_range": topic.get("expected_page_count_range"),
        "base_theme_id": base_theme,
        "fallback_count": fallback_count,
        "online_asset_count": real_assets,
        "checks": checks,
        "status": "passed" if all(checks.values()) else "failed",
    }


def run_benchmark(project_root: Path, *, profile: str = "local_real_preview") -> dict[str, Any]:
    project_root = project_root.resolve()
    topics = load_topics()
    template_version = sha256_text("template-registry")
    asset_policy_version = sha256_text("asset-policy")
    cache_results: list[dict[str, Any]] = []
    for topic in topics:
        prompt = str(topic.get("prompt") or topic.get("id") or "")
        key = cache_key(prompt, profile=profile, template_library_version=f"sha256:{template_version}", asset_policy_version=f"sha256:{asset_policy_version}")
        for kind in ["theme-match", "asset-search", "template-score"]:
            result = lookup_cache(project_root, kind, key)
            cache_results.append(result)
            if not result["hit"]:
                write_cache(project_root, kind, key, {"topic_id": topic.get("id"), "prompt": prompt, "profile": profile})
    evaluated = [evaluate_project_against_topic(project_root, topic) for topic in topics]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if all(item.get("status") == "passed" for item in evaluated) else "failed",
        "profile": profile,
        "checked_at": now_iso(),
        "topics": topics,
        "cache": {
            "results": cache_results,
            "hit_count": sum(1 for item in cache_results if item.get("hit")),
            "miss_count": sum(1 for item in cache_results if not item.get("hit")),
        },
        "quality": evaluated,
    }
    write_json(project_root / "06-check/generation-benchmark.json", payload)
    timing_path = project_root / "06-check/timing-report.json"
    timing = read_json_optional(timing_path)
    if timing:
        timing["cache"] = payload["cache"]
        write_json(timing_path, timing)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SVGlide generation benchmark/cache telemetry.")
    parser.add_argument("project_root")
    parser.add_argument("--profile", default="local_real_preview")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    result = run_benchmark(Path(args.project_root), profile=args.profile)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
