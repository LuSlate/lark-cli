#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


INVALIDATION_RULES: dict[str, list[str]] = {
    "00-input/instruction.json": ["select_style", "plan", "palette_review", "selection_review", "plan_bundle_review"],
    "02-plan/slide_plan.json": [
        "plan",
        "strategy_review",
        "theme_validate",
        "palette_review",
        "selection_review",
        "plan_bundle_review",
        "confirm_plan",
        "generate_svg",
        "prepare",
        "preview",
        "preflight",
        "preview_lint",
    ],
    "02-plan/palette-selection.json": ["palette_review", "selection_review", "plan_bundle_review", "plan"],
    "02-plan/theme-template-selection.json": ["selection_review", "plan_bundle_review", "plan"],
    "source/evidence.json": ["plan_bundle_review", "semantic_review"],
    "03-assets/asset-manifest.json": ["assets", "prepare", "preflight"],
    "skills/lark-slides/scripts/svglide_artboard_renderer.py": ["generate_svg", "prepare", "preview", "preflight", "preview_lint"],
}
PROFILE_SENSITIVE_STAGES = {
    "assets",
    "quality_gate",
    "generation_benchmark",
    "visual_acceptance",
    "pre_submit_review",
    "live_create",
    "readback",
    "export",
}
SUPPORTED_RECEIPT_SCHEMAS = {
    "svglide-stage-receipt/v1",
    "svglide-visual-acceptance/v1",
    "svglide-timing-report/v1",
}
SCHEMA_OPTIONAL_STAGES = {"init"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def optional_project_file_hash(project_root: Path, rel: str) -> str | None:
    path = project_root / rel
    return file_sha256(path) if path.is_file() else None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def optional_script_file_hash(rel: str) -> str | None:
    path = Path(rel)
    if not path.is_absolute():
        path = repo_root() / rel
    return file_sha256(path) if path.is_file() else None


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def stage_index(stage_order: list[str], stage: str) -> int:
    try:
        return stage_order.index(stage)
    except ValueError:
        return len(stage_order)


def receipt_path(project_root: Path, record: dict[str, Any], stage: str) -> Path:
    raw = record.get("receipt")
    if isinstance(raw, str) and raw:
        return project_root / raw
    return project_root / "receipts" / f"{stage}.json"


def receipt_hashes_stale(project_root: Path, receipt: dict[str, Any], *, stage: str, profile: str) -> bool:
    schema_version = receipt.get("schema_version")
    schema_sensitive = any(key in receipt for key in ("input_hashes", "script_hashes", "outputs", "tool_versions"))
    if schema_version is None and stage not in SCHEMA_OPTIONAL_STAGES and schema_sensitive:
        return True
    if schema_version is not None and schema_version not in SUPPORTED_RECEIPT_SCHEMAS:
        return True
    if schema_version == "svglide-stage-receipt/v1" and not isinstance(receipt.get("tool_versions"), dict):
        return True
    input_hashes = receipt.get("input_hashes")
    if isinstance(input_hashes, dict):
        for rel, recorded in input_hashes.items():
            if isinstance(rel, str) and isinstance(recorded, str):
                current = optional_project_file_hash(project_root, rel)
                if current != recorded:
                    return True
    script_hashes = receipt.get("script_hashes")
    if isinstance(script_hashes, dict):
        for rel, recorded in script_hashes.items():
            if isinstance(rel, str) and isinstance(recorded, str):
                current = optional_script_file_hash(rel)
                if current != recorded:
                    return True
    receipt_profile = receipt.get("profile")
    if stage in PROFILE_SENSITIVE_STAGES and isinstance(receipt_profile, str) and receipt_profile and receipt_profile != profile:
        return True
    outputs = receipt.get("outputs")
    if isinstance(outputs, list):
        for rel in outputs:
            if not isinstance(rel, str) or not rel:
                continue
            path = project_root / rel
            if not path.exists():
                return True
    return False


def stages_affected_by_rule(project_root: Path, state: dict[str, Any]) -> set[str]:
    affected: set[str] = set()
    recorded = state.get("input_hashes")
    if not isinstance(recorded, dict):
        return affected
    for rel, stages in INVALIDATION_RULES.items():
        current = optional_project_file_hash(project_root, rel)
        if recorded.get(rel) != current:
            affected.update(stages)
    return affected


def detect_stale_stages(project_root: Path, state: dict[str, Any], *, target_stage: str, stage_order: list[str], profile: str) -> list[str]:
    stages = state.get("stages") if isinstance(state.get("stages"), dict) else {}
    target_index = stage_index(stage_order, target_stage)
    stale: set[str] = set()
    for stage, record in stages.items():
        if not isinstance(stage, str) or stage_index(stage_order, stage) > target_index:
            continue
        if not isinstance(record, dict):
            stale.add(stage)
            continue
        if record.get("status") != "passed":
            continue
        receipt = read_json_optional(receipt_path(project_root, record, stage))
        if not receipt:
            stale.add(stage)
            continue
        if receipt_hashes_stale(project_root, receipt, stage=stage, profile=profile):
            stale.add(stage)
    ordered = [stage for stage in stage_order if stage in stale and stage_index(stage_order, stage) <= target_index]
    if not ordered:
        return []
    first = stage_index(stage_order, ordered[0])
    return [stage for stage in stage_order[first : target_index + 1] if stage in stages]


def prune_stale_stage_records(state: dict[str, Any], stale: list[str]) -> None:
    stages = state.get("stages")
    if not isinstance(stages, dict):
        return
    for stage in stale:
        stages.pop(stage, None)
    if stale:
        state["stale_pruned"] = stale


def update_state_input_hashes(project_root: Path, state: dict[str, Any]) -> None:
    hashes = state.setdefault("input_hashes", {})
    if not isinstance(hashes, dict):
        hashes = {}
        state["input_hashes"] = hashes
    for rel in INVALIDATION_RULES:
        hashes[rel] = optional_project_file_hash(project_root, rel)
