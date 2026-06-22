#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_asset_injector
import svglide_schema
import svglide_stage_invalidation


RUNNER_VERSION = "svglide-project-runner/v0"
PROJECT_VERSION = "svglide-project/v1"
STATE_VERSION = "svglide-state/v1"
STAGE_GRAPH = "svglide-workflow/v1"
ROUTE = "svglide-svg"
DEFAULT_GENERATION_MODE = "direct_svg"
GENERATION_MODES = {DEFAULT_GENERATION_MODE, "artboard_satori"}
DEFAULT_PLAN_ROOT = Path(".lark-slides/plan")
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_GUARDRAILS_PATH = SCRIPT_DIR.parent / "references" / "svglide-template-guardrails.json"
LARK_CLI_COMMAND_ENV = "SVGLIDE_LARK_CLI_CMD"
DEFAULT_REPAIR_LOOP_FAILING_RECEIPT = Path("06-check/preflight.json")

STAGES = [
    "init",
    "source",
    "select_style",
    "plan",
    "strategy_review",
    "theme_validate",
    "palette_review",
    "selection_review",
    "plan_bundle_review",
    "package_check",
    "assets",
    "generate_svg",
    "contract_compile",
    "prepare",
    "preview",
    "preflight",
    "preview_lint",
    "aesthetic_review",
    "chart_verify",
    "semantic_review",
    "runtime_review",
    "visual_distinctness_review",
    "theme_adherence",
    "quality_gate",
    "generation_benchmark",
    "dry_run",
    "visual_acceptance",
    "ppe_proof",
    "pre_submit_review",
    "live_create",
    "readback",
    "export",
]
OPTIONAL_STAGES = {
    "confirm_plan",
    "repair_loop",
    "theme_productization",
}

STAGE_ALIASES = {
    "confirm-plan": "confirm_plan",
    "source-review": "source",
    "select-style": "select_style",
    "theme-template-selection": "select_style",
    "palette-selection": "select_style",
    "strategy-review": "strategy_review",
    "theme-validate": "theme_validate",
    "palette-review": "palette_review",
    "selection-review": "selection_review",
    "theme-template-selection-review": "selection_review",
    "plan-bundle-review": "plan_bundle_review",
    "package-check": "package_check",
    "artboard-package-check": "package_check",
    "aesthetic-review": "aesthetic_review",
    "chart-verify": "chart_verify",
    "semantic-review": "semantic_review",
    "runtime-review": "runtime_review",
    "visual-distinctness": "visual_distinctness_review",
    "visual-distinctness-review": "visual_distinctness_review",
    "theme-adherence": "theme_adherence",
    "generate": "generate_svg",
    "generate-svg": "generate_svg",
    "preview-lint": "preview_lint",
    "quality-gate": "quality_gate",
    "dry-run": "dry_run",
    "visual-acceptance": "visual_acceptance",
    "visual-acceptance-gate": "visual_acceptance",
    "deliverable": "visual_acceptance",
    "ppe-proof": "ppe_proof",
    "pre-submit-review": "pre_submit_review",
    "pre-submit": "pre_submit_review",
    "live-create": "live_create",
    "repair-loop": "repair_loop",
    "theme-productization": "theme_productization",
    "theme-productize": "theme_productization",
    "export-package": "export",
    "package-export": "export",
}

PROJECT_DIRS = [
    "00-input",
    "source",
    "01-project",
    "02-plan",
    "03-assets",
    "04-svg",
    "04-svg/prepared",
    "05-preview",
    "06-check",
    "07-create",
    "08-readback",
    "09-export",
    "receipts",
    "logs",
]

IMPLEMENTED_STAGES = {
    "init",
    "source",
    "select_style",
    "plan",
    "strategy_review",
    "theme_validate",
    "palette_review",
    "selection_review",
    "plan_bundle_review",
    "confirm_plan",
    "package_check",
    "assets",
    "generate_svg",
    "contract_compile",
    "prepare",
    "preview",
    "preflight",
    "preview_lint",
    "aesthetic_review",
    "chart_verify",
    "semantic_review",
    "runtime_review",
    "visual_distinctness_review",
    "theme_adherence",
    "quality_gate",
    "generation_benchmark",
    "dry_run",
    "visual_acceptance",
    "ppe_proof",
    "pre_submit_review",
    "live_create",
    "readback",
    "repair_loop",
    "theme_productization",
    "export",
}
FAILURE_STATUSES = {"blocked", "failed", "skipped"}
RERUNNABLE_STAGE_STATUSES = {"blocked", "failed"}
DECK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PROFILE_TARGETS = {
    "preview_only": "quality_gate",
    "local_real_preview": "visual_acceptance",
    "production_live": "readback",
}
QUALITY_GATE_PROFILES = {"preview_only", "local_real_preview", "production_live", "production", "debug"}
RUNNER_OPTIONS = {
    "network_policy": "auto",
    "offline": False,
    "no_online_research": False,
    "no_image_search": False,
    "no_ai_image": False,
    "refresh_online": False,
    "asset_provider": "auto",
    "image_backend": "auto",
    "progress": "none",
    "collect_errors": False,
    "auto_repair": False,
}
PROGRESS_MODES = {"none", "agent"}
COLLECTABLE_VALIDATION_STAGES = {
    "plan",
    "strategy_review",
    "theme_validate",
    "palette_review",
    "selection_review",
    "plan_bundle_review",
}
AUTO_REPAIR_STAGES = {
    "plan",
    "palette_review",
    "selection_review",
    "plan_bundle_review",
    "preview_lint",
}
SLA_TARGET_SECONDS = {
    "local_real_preview": 720,
    "preview_only": 720,
    "production": 720,
    "production_live": 720,
}
ROOT_CAUSE_GROUPS = {
    "project_palette_missing": "palette_adoption",
    "project_palette_mismatch": "palette_adoption",
    "project_theme_token_overrides_missing": "palette_adoption",
    "project_theme_token_override_mismatch": "palette_adoption",
    "asset_contract_metadata_missing": "asset_contract",
    "asset_source_url_missing": "asset_contract",
    "asset_source_url_not_http": "asset_contract",
    "local_generated_image_forbidden": "asset_contract",
    "image_opacity_unsupported": "svg_protocol",
    "unsupported_path_command": "satori_bridge",
    "text_overflow": "preview_layout",
    "chart_rich_content_too_thin": "plan_semantic_evidence",
    "semantic_evidence_missing": "plan_semantic_evidence",
    "page_count_too_low": "deck_scope_contract",
    "baseline_theme_template_forbidden": "template_selection",
    "debug_reference_line_forbidden": "template_selection",
    "unregistered_template_motif": "template_guardrail",
    "unregistered_sharp_decoration": "template_guardrail",
    "decorative_kind_not_allowed": "template_guardrail",
    "decorative_density_too_high": "template_guardrail",
    "text_density_too_high": "preview_layout",
    "page_density_too_high": "preview_layout",
}
PROGRESS_STAGE_MILESTONES = {
    "artboard_satori": [
        ("assets", "主题 plan + 图片资产"),
        ("generate_svg", "Satori-compatible HTML/CSS"),
        ("prepare", "Satori SVG + SVGlide SVG"),
        ("visual_acceptance", "本地预览 + gates"),
    ],
    "direct_svg": [
        ("assets", "素材资产"),
        ("generate_svg", "SVGlide protocol SVG"),
        ("readback", "backend snapshot JSON"),
    ],
}


class RunnerError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def normalize_stage(stage: str) -> str:
    candidate = STAGE_ALIASES.get(stage, stage.replace("-", "_"))
    if candidate not in STAGES and candidate not in OPTIONAL_STAGES:
        raise RunnerError(f"unknown stage '{stage}'", exit_code=2)
    return candidate


def effective_network_policy() -> str:
    if RUNNER_OPTIONS.get("offline"):
        return "offline"
    return str(RUNNER_OPTIONS.get("network_policy") or "auto")


def source_option_args() -> list[str]:
    args = ["--network-policy", effective_network_policy()]
    if RUNNER_OPTIONS.get("no_online_research"):
        args.append("--no-online-research")
    if RUNNER_OPTIONS.get("refresh_online"):
        args.append("--refresh-online")
    return args


def asset_option_args(*, profile: str = "production") -> list[str]:
    args = [
        "--network-policy",
        effective_network_policy(),
        "--asset-provider",
        str(RUNNER_OPTIONS.get("asset_provider") or "auto"),
        "--image-backend",
        str(RUNNER_OPTIONS.get("image_backend") or "auto"),
        "--profile",
        profile,
    ]
    if RUNNER_OPTIONS.get("no_image_search"):
        args.append("--no-image-search")
    if RUNNER_OPTIONS.get("no_ai_image"):
        args.append("--no-ai-image")
    if RUNNER_OPTIONS.get("refresh_online"):
        args.append("--refresh-online")
    return args


def stages_until(stage: str) -> list[str]:
    normalized = normalize_stage(stage)
    return STAGES[: STAGES.index(normalized) + 1]


def resolve_run_target(until: str | None, profile: str | None) -> str:
    if until:
        target = normalize_stage(until)
        if profile in PROFILE_TARGETS:
            profile_target = normalize_stage(PROFILE_TARGETS[profile])
            if STAGES.index(target) > STAGES.index(profile_target):
                raise RunnerError(f"profile '{profile}' can only run until {profile_target}; requested {target}", exit_code=2)
        return target
    if profile in PROFILE_TARGETS:
        return normalize_stage(PROFILE_TARGETS[profile])
    raise RunnerError("--until is required unless --profile is preview_only, local_real_preview, or production_live", exit_code=2)


def stage_required_for_profile(stage: str, profile: str) -> bool:
    if stage == "pre_submit_review":
        return profile == "production_live"
    return True


def validate_deck_id(deck_id: str) -> str:
    if not DECK_ID_RE.fullmatch(deck_id):
        raise RunnerError(
            "deck id must start with an alphanumeric character and contain only letters, numbers, '.', '_' or '-'",
            exit_code=2,
        )
    return deck_id


def project_manifest_path(project_root: Path) -> Path:
    return project_root / "01-project/project_manifest.json"


def state_path(project_root: Path) -> Path:
    return project_root / "01-project/state.json"


def receipt_path(project_root: Path, stage: str) -> Path:
    return project_root / "receipts" / f"{stage}.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise RunnerError(f"missing required file: {path}") from err


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_iso_seconds(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def elapsed_seconds(started_at: str | None, ended_at: str | None) -> float:
    started = parse_iso_seconds(started_at)
    ended = parse_iso_seconds(ended_at)
    if not started or not ended:
        return 0.0
    return max(0.0, (ended - started).total_seconds())


def issue_root_cause(issue: Any) -> str:
    if not isinstance(issue, dict):
        return "unknown"
    group = issue.get("root_cause_group")
    if isinstance(group, str) and group:
        return group
    code = issue.get("code")
    return ROOT_CAUSE_GROUPS.get(code, "unknown") if isinstance(code, str) else "unknown"


def issues_from_payload(payload: Any) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return issues
    raw = payload.get("issues")
    if isinstance(raw, list):
        issues.extend(item for item in raw if isinstance(item, dict))
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("issues"), list):
        issues.extend(item for item in error["issues"] if isinstance(item, dict))
    stages = payload.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if isinstance(stage, dict) and isinstance(stage.get("issues"), list):
                issues.extend(item for item in stage["issues"] if isinstance(item, dict))
    return issues


def failure_summary_path(project_root: Path) -> Path:
    return project_root / "06-check" / "failure-summary.json"


def write_failure_summary(
    project_root: Path,
    *,
    blocking_stage: str,
    issues: list[dict[str, Any]] | None = None,
    message: str | None = None,
    rerun_from: str | None = None,
) -> dict[str, Any]:
    issue_list = issues or []
    primary = issue_list[0] if issue_list else {}
    code = primary.get("code") if isinstance(primary, dict) else None
    root_cause = issue_root_cause(primary) if primary else "unknown"
    repair_hint = primary.get("repair_hint") if isinstance(primary, dict) else None
    payload = {
        "schema_version": "svglide-failure-summary/v1",
        "blocking_stage": blocking_stage,
        "root_cause_group": root_cause,
        "user_visible_summary": message or (primary.get("message") if isinstance(primary.get("message"), str) else f"{blocking_stage} failed"),
        "repair_hint": repair_hint or "inspect the structured issues and rerun from the blocking stage",
        "rerun_from": rerun_from or blocking_stage,
    }
    if code:
        payload["code"] = code
    if issue_list:
        payload["issues"] = issue_list
    write_json(failure_summary_path(project_root), payload)
    return payload


def collected_errors_path(project_root: Path) -> Path:
    return project_root / "06-check" / "collected-errors.json"


def normalize_issue(stage: str, issue: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(issue)
    normalized.setdefault("severity", "error")
    normalized.setdefault("stage", stage)
    normalized.setdefault("root_cause_group", issue_root_cause(normalized))
    normalized.setdefault("repairability", "manual")
    return normalized


def write_collected_errors(project_root: Path, state: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    normalized_stages: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    for failure in failures:
        stage = str(failure.get("stage") or "unknown")
        issues = [normalize_issue(stage, issue) for issue in failure.get("issues", []) if isinstance(issue, dict)]
        all_issues.extend(issues)
        normalized_stages.append(
            {
                "stage": stage,
                "status": failure.get("status") or "failed",
                "issues": issues,
                **({"skip_reason": failure["skip_reason"]} if failure.get("skip_reason") else {}),
                **({"upstream_stage": failure["upstream_stage"]} if failure.get("upstream_stage") else {}),
            }
        )
    payload = {
        "schema_version": "svglide-collected-errors/v1",
        "status": "failed" if normalized_stages else "passed",
        "stages": normalized_stages,
        "issues": all_issues,
        "summary": {"error_count": len(all_issues), "stage_count": len(normalized_stages)},
    }
    write_json(collected_errors_path(project_root), payload)
    state["collected_errors"] = project_relpath(collected_errors_path(project_root), project_root)
    write_state(project_root, state)
    if normalized_stages:
        write_failure_summary(
            project_root,
            blocking_stage=normalized_stages[0]["stage"],
            issues=all_issues,
            message="生成前校验聚合到阻断问题",
            rerun_from=normalized_stages[0]["stage"],
        )


def run_auto_repair_command(project_root: Path) -> dict[str, Any]:
    command = ["python3", (SCRIPT_DIR / "svglide_auto_repair.py").as_posix(), project_root.as_posix(), "--pretty"]
    completed = subprocess.run(command, cwd=repo_root(), check=False, capture_output=True, text=True)
    payload = parse_json_or_none(completed.stdout)
    if isinstance(payload, dict):
        return payload
    return {"status": "failed", "stdout": completed.stdout, "stderr": completed.stderr, "returncode": completed.returncode}


def repair_existing_failed_stage(project_root: Path, state: dict[str, Any], stage: str) -> bool:
    record = state.get("stages", {}).get(stage)
    if not isinstance(record, dict) or record.get("status") not in FAILURE_STATUSES:
        return False
    if stage not in AUTO_REPAIR_STAGES or not RUNNER_OPTIONS.get("auto_repair"):
        return False
    result = run_auto_repair_command(project_root)
    if result.get("status") != "patched":
        return False
    state.get("stages", {}).pop(stage, None)
    state.setdefault("auto_repair_history", []).append({"stage": stage, "result": result})
    write_state(project_root, state)
    return True


def prune_stage_and_descendants(state: dict[str, Any], stage: str, target: str) -> list[str]:
    stages = state.get("stages")
    if not isinstance(stages, dict):
        return []
    start = STAGES.index(stage) if stage in STAGES else 0
    end = STAGES.index(target) if target in STAGES else len(STAGES) - 1
    stale = [name for name in STAGES[start : end + 1] if name in stages]
    for name in stale:
        stages.pop(name, None)
    if stale:
        state["stale_pruned"] = stale
    return stale


def is_rerun_required_error(err: RunnerError, stage: str) -> bool:
    message = str(err)
    return "rerun" in message and (stage in message or "current project files" in message or "stale" in message)


def timing_report_path(project_root: Path) -> Path:
    return project_root / "06-check" / "timing-report.json"


def timing_receipt_path(project_root: Path) -> Path:
    return project_root / "receipts" / "timing.json"


def stage_attempt(events: list[dict[str, Any]], stage: str) -> int:
    return sum(1 for event in events if event.get("stage") == stage) + 1


def record_timing_event(
    state: dict[str, Any],
    *,
    stage: str,
    status: str,
    started_at: str,
    ended_at: str,
    wall_time_seconds: float | None = None,
    root_cause_group: str | None = None,
    cache_hit: bool | None = None,
) -> None:
    events = state.setdefault("timing_events", [])
    if not isinstance(events, list):
        events = []
        state["timing_events"] = events
    event: dict[str, Any] = {
        "stage": stage,
        "attempt": stage_attempt(events, stage),
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "wall_time_seconds": round(wall_time_seconds if wall_time_seconds is not None else elapsed_seconds(started_at, ended_at), 3),
    }
    if root_cause_group:
        event["root_cause_group"] = root_cause_group
    if cache_hit is not None:
        event["cache_hit"] = cache_hit
    events.append(event)


def build_stage_input_hashes(project_root: Path, inputs: list[str] | None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in inputs or []:
        if not isinstance(rel, str):
            continue
        path = project_root / rel
        if path.is_file():
            hashes[rel] = file_sha256(path)
    return hashes


def build_script_hashes(command: list[str] | None) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for item in command or []:
        if not isinstance(item, str):
            continue
        path = Path(item)
        if not path.is_absolute():
            path = repo_root() / item
        if path.is_file():
            try:
                hashes[path.resolve().relative_to(repo_root()).as_posix()] = file_sha256(path)
            except ValueError:
                hashes[path.as_posix()] = file_sha256(path)
    return hashes


def write_timing_report(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    events = state.get("timing_events") if isinstance(state.get("timing_events"), list) else []
    stage_runtime: dict[str, float] = {}
    stage_attempts: dict[str, int] = {}
    root_cause_runtime: dict[str, float] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        stage = event.get("stage")
        seconds = event.get("wall_time_seconds")
        if not isinstance(stage, str) or not isinstance(seconds, (int, float)):
            continue
        stage_runtime[stage] = round(stage_runtime.get(stage, 0.0) + float(seconds), 3)
        stage_attempts[stage] = stage_attempts.get(stage, 0) + 1
        group = event.get("root_cause_group")
        if isinstance(group, str) and group:
            root_cause_runtime[group] = round(root_cause_runtime.get(group, 0.0) + float(seconds), 3)
    total = round(sum(stage_runtime.values()), 3)
    profile = str(state.get("profile") or "unknown")
    target_seconds = SLA_TARGET_SECONDS.get(profile, 720)
    slowest_root_cause = None
    if root_cause_runtime:
        slowest_root_cause = max(root_cause_runtime.items(), key=lambda item: item[1])[0]
    payload = {
        "schema_version": "svglide-timing-report/v1",
        "total_wall_time_seconds": total,
        "sla": {
            "profile": profile,
            "target_seconds": target_seconds,
            "passed": total <= target_seconds,
        },
        "stage_runtime_seconds": stage_runtime,
        "stage_attempts": stage_attempts,
        "root_cause_runtime_seconds": root_cause_runtime,
        "slowest_root_cause": slowest_root_cause,
        "events": events,
    }
    benchmark = read_json_optional(project_root / "06-check/generation-benchmark.json")
    cache = benchmark.get("cache") if isinstance(benchmark.get("cache"), dict) else None
    if cache:
        payload["cache"] = cache
    write_json(timing_report_path(project_root), payload)
    write_json(timing_receipt_path(project_root), payload)
    return payload


def read_generation_mode(project_root: Path) -> str:
    plan_path = project_root / "02-plan/slide_plan.json"
    if not plan_path.exists():
        return DEFAULT_GENERATION_MODE
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_GENERATION_MODE
    mode = plan.get("generation_mode")
    return mode if isinstance(mode, str) and mode in GENERATION_MODES else DEFAULT_GENERATION_MODE


def progress_milestones(project_root: Path) -> list[tuple[str, str]]:
    return PROGRESS_STAGE_MILESTONES.get(read_generation_mode(project_root), PROGRESS_STAGE_MILESTONES[DEFAULT_GENERATION_MODE])


def progress_mode_enabled(progress: str | None) -> bool:
    return (progress or RUNNER_OPTIONS.get("progress") or "none") != "none"


def progress_log_path(project_root: Path) -> Path:
    return project_root / "logs/agent-progress.jsonl"


def emit_agent_progress(project_root: Path, *, event: str, message: str, stage: str | None = None, completed: int | None = None, total: int | None = None) -> None:
    payload: dict[str, Any] = {
        "schema_version": "svglide-agent-progress/v1",
        "event": event,
        "message": message,
        "emitted_at": now_iso(),
    }
    if stage:
        payload["stage"] = stage
    if completed is not None:
        payload["completed"] = completed
    if total is not None:
        payload["total"] = total
    append_jsonl(progress_log_path(project_root), payload)
    print(message, file=sys.stderr)


def emit_stage_progress(project_root: Path, stage: str, *, progress: str | None = None) -> None:
    if not progress_mode_enabled(progress):
        return
    milestones = progress_milestones(project_root)
    total = len(milestones)
    for index, (milestone_stage, label) in enumerate(milestones, start=1):
        if milestone_stage == stage:
            emit_agent_progress(
                project_root,
                event="milestone_completed",
                stage=stage,
                completed=index,
                total=total,
                message=f"已完成 {index}/{total} 关键产物: {label}",
            )
            return


def emit_start_progress(project_root: Path, *, progress: str | None = None) -> None:
    if not progress_mode_enabled(progress):
        return
    emit_agent_progress(
        project_root,
        event="started",
        message="正在生成主题 plan 和图片资产",
        completed=0,
        total=len(progress_milestones(project_root)),
    )


def emit_blocked_progress(project_root: Path, error: str, *, progress: str | None = None) -> None:
    if not progress_mode_enabled(progress):
        return
    emit_agent_progress(
        project_root,
        event="blocked",
        message=f"生成已阻断: {error}",
    )


def format_duration(seconds: float | int | None) -> str:
    total = int(round(float(seconds or 0)))
    minutes, secs = divmod(total, 60)
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


def asset_summary(project_root: Path) -> tuple[int | None, int | None]:
    manifest = read_json_optional(project_root / "03-assets/asset-manifest.json")
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    online = summary.get("asset_acquired_count") or summary.get("online_asset_count") or summary.get("real_asset_count")
    fallback = summary.get("fallback_count") or summary.get("asset_fallback_count") or 0
    if not isinstance(online, int):
        contracts = manifest.get("contracts")
        if isinstance(contracts, list):
            online = sum(1 for item in contracts if isinstance(item, dict) and isinstance(item.get("source_url"), str) and item["source_url"].startswith(("http://", "https://")))
    return (online if isinstance(online, int) else None, fallback if isinstance(fallback, int) else None)


def page_count_summary(project_root: Path) -> int | None:
    visual = read_json_optional(project_root / "06-check/visual-acceptance.json")
    summary = visual.get("summary") if isinstance(visual.get("summary"), dict) else {}
    count = summary.get("checked_page_count") or summary.get("page_count")
    if isinstance(count, int):
        return count
    plan = read_json_optional(project_root / "02-plan/slide_plan.json")
    slides = plan.get("slides")
    return len(slides) if isinstance(slides, list) else None


def emit_completion_summary(project_root: Path, state: dict[str, Any], *, progress: str | None = None) -> None:
    if not progress_mode_enabled(progress):
        return
    timing = write_timing_report(project_root, state)
    stage_runtime = timing.get("stage_runtime_seconds") if isinstance(timing.get("stage_runtime_seconds"), dict) else {}
    stage_attempts = timing.get("stage_attempts") if isinstance(timing.get("stage_attempts"), dict) else {}
    slowest_stage = max(stage_runtime.items(), key=lambda item: item[1])[0] if stage_runtime else "unknown"
    max_attempt_stage = max(stage_attempts.items(), key=lambda item: item[1])[0] if stage_attempts else "none"
    max_attempt_count = stage_attempts.get(max_attempt_stage, 0) if isinstance(stage_attempts.get(max_attempt_stage), int) else 0
    sla = timing.get("sla") if isinstance(timing.get("sla"), dict) else {}
    target = format_duration(sla.get("target_seconds") if isinstance(sla.get("target_seconds"), (int, float)) else SLA_TARGET_SECONDS.get(str(state.get("profile") or "local_real_preview"), 720))
    sla_text = f"达到 {target} SLA" if sla.get("passed") is True else f"未达到 {target} SLA"
    page_count = page_count_summary(project_root)
    online_assets, fallback_count = asset_summary(project_root)
    page_text = f"{page_count} 页" if page_count is not None else "页数未知"
    asset_text = f"{online_assets} 个线上图片资产" if online_assets is not None else "线上图片资产数未知"
    fallback_text = f"{fallback_count} 次 fallback" if fallback_count is not None else "fallback 次数未知"
    message = (
        f"生成完成：{page_text}，{asset_text}，{fallback_text}；"
        f"总耗时：{format_duration(timing.get('total_wall_time_seconds'))}，{sla_text}；"
        f"最慢阶段：{slowest_stage} {format_duration(stage_runtime.get(slowest_stage))}；"
        f"最多重跑：{max_attempt_stage} {max_attempt_count} 次；"
        f"最慢 root cause：{timing.get('slowest_root_cause') or 'none'}"
    )
    emit_agent_progress(project_root, event="completed", message=message)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepared_svg_files(project_root: Path) -> list[Path]:
    files = sorted((project_root / "04-svg" / "prepared").glob("*.svg"))
    if not files:
        raise RunnerError(f"no prepared SVG files found under {project_root / '04-svg/prepared'}")
    return files


def source_svg_files(project_root: Path) -> list[Path]:
    files = sorted(path for path in (project_root / "04-svg").glob("*.svg") if path.is_file())
    if not files:
        raise RunnerError(f"no source SVG files found under {project_root / '04-svg'}")
    return files


def svg_file_hashes(files: list[Path], project_root: Path) -> list[dict[str, str]]:
    return [
        {
            "path": path.relative_to(project_root).as_posix(),
            "sha256": file_sha256(path),
        }
        for path in files
    ]


def prepared_file_hashes(project_root: Path) -> list[dict[str, str]]:
    return svg_file_hashes(prepared_svg_files(project_root), project_root)


def source_file_hashes(project_root: Path) -> list[dict[str, str]]:
    return svg_file_hashes(source_svg_files(project_root), project_root)


def raw_visual_manifest_path(project_root: Path) -> Path:
    return project_root / "04-artboard" / "raw" / "manifest.json"


def contract_manifest_path(project_root: Path) -> Path:
    return project_root / "04-svg" / "contract" / "manifest.json"


def raw_visual_file_hashes(project_root: Path) -> list[dict[str, str]]:
    manifest_path = raw_visual_manifest_path(project_root)
    if not manifest_path.exists():
        raise RunnerError(f"missing raw visual manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RunnerError(f"raw visual manifest has no pages: {manifest_path}")
    files: list[Path] = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("source"), str):
            raise RunnerError("raw visual manifest page is missing source")
        files.append(project_root / page["source"])
    return svg_file_hashes(files, project_root)


def contract_output_hashes(project_root: Path) -> list[dict[str, str]]:
    manifest_path = contract_manifest_path(project_root)
    if not manifest_path.exists():
        raise RunnerError(f"missing contract compile manifest: {manifest_path}")
    manifest = read_json(manifest_path)
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RunnerError(f"contract compile manifest has no pages: {manifest_path}")
    files: list[Path] = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("output"), str):
            raise RunnerError("contract compile manifest page is missing output")
        files.append(project_root / page["output"])
    return svg_file_hashes(files, project_root)


def optional_project_file_hash(project_root: Path, rel: str) -> str | None:
    path = project_root / rel
    return file_sha256(path) if path.exists() else None


def project_relpath(path: Path, project_root: Path) -> str:
    return path.relative_to(project_root).as_posix()


def parse_json_or_none(text: str) -> Any:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def build_receipt(
    stage: str,
    status: str,
    *,
    started_at: str,
    ended_at: str | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    command: list[str] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "svglide-stage-receipt/v1",
        "stage": stage,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at or now_iso(),
        "inputs": inputs or [],
        "outputs": outputs or [],
        "command": command or [],
        "tool_versions": {
            "python": sys.version.split()[0],
        },
        "error": error,
    }


def record_stage(state: dict[str, Any], stage: str, status: str, receipt: Path) -> None:
    state.setdefault("stages", {})[stage] = {
        "status": status,
        "receipt": receipt.relative_to(receipt.parents[1]).as_posix(),
    }
    state["current_stage"] = stage
    state["updated_at"] = now_iso()


def load_state(project_root: Path) -> dict[str, Any]:
    state = read_json(state_path(project_root))
    if state.get("version") != STATE_VERSION:
        raise RunnerError(f"unsupported state version in {state_path(project_root)}")
    return state


def write_state(project_root: Path, state: dict[str, Any]) -> None:
    write_json(state_path(project_root), state)


def complete_stage(
    project_root: Path,
    state: dict[str, Any],
    stage: str,
    status: str,
    *,
    started_at: str,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    command: list[str] | None = None,
    error: dict[str, Any] | None = None,
    wall_time_seconds: float | None = None,
) -> dict[str, Any]:
    receipt = build_receipt(
        stage,
        status,
        started_at=started_at,
        inputs=inputs,
        outputs=outputs,
        command=command,
        error=error,
    )
    receipt["profile"] = state.get("profile")
    receipt["input_hashes"] = build_stage_input_hashes(project_root, inputs)
    receipt["script_hashes"] = build_script_hashes(command)
    receipt["wall_time_seconds"] = round(wall_time_seconds if wall_time_seconds is not None else elapsed_seconds(receipt.get("started_at"), receipt.get("ended_at")), 3)
    path = receipt_path(project_root, stage)
    write_json(path, receipt)
    record_stage(state, stage, status, path)
    if status in FAILURE_STATUSES:
        root_cause = None
        if error and isinstance(error.get("issues"), list) and error["issues"]:
            root_cause = issue_root_cause(error["issues"][0])
        record_timing_event(
            state,
            stage=stage,
            status=status,
            started_at=receipt["started_at"],
            ended_at=receipt["ended_at"],
            wall_time_seconds=receipt["wall_time_seconds"],
            root_cause_group=root_cause,
        )
        write_failure_summary(
            project_root,
            blocking_stage=stage,
            issues=error.get("issues") if error and isinstance(error.get("issues"), list) else [],
            message=error.get("message") if error and isinstance(error.get("message"), str) else None,
            rerun_from=stage,
        )
    else:
        record_timing_event(
            state,
            stage=stage,
            status=status,
            started_at=receipt["started_at"],
            ended_at=receipt["ended_at"],
            wall_time_seconds=receipt["wall_time_seconds"],
        )
    svglide_stage_invalidation.update_state_input_hashes(project_root, state)
    write_state(project_root, state)
    write_timing_report(project_root, state)
    return receipt


def run_script_stage(
    project_root: Path,
    state: dict[str, Any],
    stage: str,
    command: list[str],
    *,
    output_json: Path | None = None,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    command_runner=subprocess.run,
) -> dict[str, Any]:
    started_at = now_iso()
    started_perf = time.perf_counter()
    completed = command_runner(command, cwd=repo_root(), check=False, capture_output=True, text=True)
    repair_result: dict[str, Any] | None = None
    if completed.returncode != 0 and RUNNER_OPTIONS.get("auto_repair") and stage in AUTO_REPAIR_STAGES:
        repair_command = ["python3", (SCRIPT_DIR / "svglide_auto_repair.py").as_posix(), project_root.as_posix(), "--pretty"]
        repair_completed = subprocess.run(repair_command, cwd=repo_root(), check=False, capture_output=True, text=True)
        repair_payload = parse_json_or_none(repair_completed.stdout)
        repair_result = repair_payload if isinstance(repair_payload, dict) else {"status": "unknown", "stdout": repair_completed.stdout, "stderr": repair_completed.stderr}
        if repair_completed.returncode == 0 and repair_result.get("status") == "patched":
            completed = command_runner(command, cwd=repo_root(), check=False, capture_output=True, text=True)
    if output_json is not None:
        write_text(output_json, completed.stdout if completed.stdout.endswith("\n") else completed.stdout + "\n")
    if completed.returncode != 0:
        parsed_output = parse_json_or_none(completed.stdout)
        parsed_issues = issues_from_payload(parsed_output)
        error_payload: dict[str, Any] = {
            "code": "stage_command_failed",
            "returncode": completed.returncode,
            "stderr": completed.stderr,
        }
        if parsed_issues:
            error_payload["issues"] = parsed_issues
        if repair_result is not None:
            error_payload["auto_repair"] = repair_result
        complete_stage(
            project_root,
            state,
            stage,
            "failed",
            started_at=started_at,
            inputs=inputs,
            outputs=outputs,
            command=command,
            error=error_payload,
            wall_time_seconds=time.perf_counter() - started_perf,
        )
        raise RunnerError(f"stage '{stage}' failed with exit code {completed.returncode}")
    receipt = complete_stage(
        project_root,
        state,
        stage,
        "passed",
        started_at=started_at,
        inputs=inputs,
        outputs=outputs,
        command=command,
        wall_time_seconds=time.perf_counter() - started_perf,
    )
    if repair_result is not None:
        receipt["auto_repair"] = repair_result
        write_json(receipt_path(project_root, stage), receipt)
    return receipt


def init_project(
    deck_id: str,
    title: str,
    *,
    plan_root: Path = DEFAULT_PLAN_ROOT,
    force: bool = False,
) -> dict[str, Any]:
    deck_id = validate_deck_id(deck_id)
    project_root = plan_root / deck_id
    if project_root.exists():
        if not force:
            raise RunnerError(
                f"project already exists: {project_root}; pass --force to recreate it",
                exit_code=2,
            )
        shutil.rmtree(project_root)

    for directory in PROJECT_DIRS:
        (project_root / directory).mkdir(parents=True, exist_ok=True)

    created_at = now_iso()
    manifest = {
        "version": PROJECT_VERSION,
        "deck_id": deck_id,
        "title": title,
        "route": ROUTE,
        "artifact_root": project_root.as_posix(),
        "stage_graph": STAGE_GRAPH,
        "created_by": "lark-cli",
        "cli_git_commit": current_git_commit(),
        "runner_version": RUNNER_VERSION,
        "created_at": created_at,
    }

    init_receipt_path = receipt_path(project_root, "init")
    init_receipt = build_receipt(
        "init",
        "passed",
        started_at=created_at,
        ended_at=created_at,
        outputs=[
            project_manifest_path(project_root).relative_to(project_root).as_posix(),
            state_path(project_root).relative_to(project_root).as_posix(),
        ],
        command=["init", "--deck-id", deck_id],
    )

    state = {
        "version": STATE_VERSION,
        "current_stage": "init",
        "stages": {
            "init": {
                "status": "passed",
                "receipt": init_receipt_path.relative_to(project_root).as_posix(),
            }
        },
        "runner_version": RUNNER_VERSION,
        "created_at": created_at,
        "updated_at": created_at,
    }

    write_json(project_manifest_path(project_root), manifest)
    write_json(init_receipt_path, init_receipt)
    write_state(project_root, state)
    return {"project_root": project_root.as_posix(), "manifest": manifest, "state": state}


def fail_if_existing_stage_failed(stage: str, record: dict[str, Any]) -> None:
    status = record.get("status")
    if status == "passed":
        return
    if status in FAILURE_STATUSES:
        raise RunnerError(f"required stage '{stage}' is {status}; refusing to continue")
    raise RunnerError(f"required stage '{stage}' has unsupported status '{status}'")


def existing_stage_can_be_retried(record: dict[str, Any]) -> bool:
    return record.get("status") in RERUNNABLE_STAGE_STATUSES


def require_stage_passed(state: dict[str, Any], stage: str) -> None:
    status = state.get("stages", {}).get(stage, {}).get("status")
    if status != "passed":
        raise RunnerError(f"required stage '{stage}' must be passed before continuing")


def block_unimplemented_stage(
    project_root: Path,
    stage: str,
    state: dict[str, Any],
    *,
    command: list[str],
) -> None:
    started_at = now_iso()
    receipt = build_receipt(
        stage,
        "blocked",
        started_at=started_at,
        command=command,
        error={
            "code": "stage_not_implemented",
            "message": f"stage '{stage}' is not implemented in the P0 runner skeleton",
        },
    )
    path = receipt_path(project_root, stage)
    write_json(path, receipt)
    record_stage(state, stage, "blocked", path)
    write_state(project_root, state)
    raise RunnerError(f"stage '{stage}' is not implemented in the P0 runner skeleton")


def plan_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "slide_plan.json"


def palette_selection_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "palette-selection.json"


def theme_template_selection_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "theme-template-selection.json"


def plan_declares_selection(project_root: Path) -> bool:
    path = plan_path(project_root)
    if not path.exists():
        return False
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return bool(
        payload.get("selection_receipt")
        or payload.get("palette_selection_receipt")
        or isinstance(payload.get("project_palette"), dict)
        or isinstance(payload.get("project_theme"), dict)
    )


def selection_gate_required(project_root: Path, state: dict[str, Any]) -> bool:
    stages = state.get("stages") if isinstance(state.get("stages"), dict) else {}
    return bool(
        "select_style" in stages
        or "palette_review" in stages
        or "selection_review" in stages
        or palette_selection_path(project_root).exists()
        or theme_template_selection_path(project_root).exists()
        or plan_declares_selection(project_root)
    )


def apply_selection_receipts_to_plan(project_root: Path, plan: dict[str, Any]) -> bool:
    palette_path = palette_selection_path(project_root)
    selection_path = theme_template_selection_path(project_root)
    if not palette_path.exists() or not selection_path.exists():
        return False
    try:
        palette_selection = read_json(palette_path)
        selection = read_json(selection_path)
    except (OSError, json.JSONDecodeError):
        return False
    changed = False
    project_palette = palette_selection.get("project_palette")
    if isinstance(project_palette, dict) and plan.get("project_palette") != project_palette:
        plan["project_palette"] = project_palette
        changed = True
    if plan.get("palette_selection_receipt") != "02-plan/palette-selection.json":
        plan["palette_selection_receipt"] = "02-plan/palette-selection.json"
        changed = True
    if plan.get("selection_receipt") != "02-plan/theme-template-selection.json":
        plan["selection_receipt"] = "02-plan/theme-template-selection.json"
        changed = True
    if selection.get("confidence") == "low" and not plan.get("fallback_policy"):
        plan["fallback_policy"] = "auto"
        plan["selection_fallback_policy"] = {
            "reason": "low_confidence_theme_template_selection",
            "selection_fallback_policy": selection.get("fallback_policy") or "deterministic_ranked_fallback",
            "palette_fallback_policy": palette_selection.get("fallback_policy") or "not_used",
            "deterministic_seed": selection.get("deterministic_seed") or palette_selection.get("deterministic_seed"),
        }
        changed = True
    if isinstance(project_palette, dict):
        colors = project_palette.get("colors") if isinstance(project_palette.get("colors"), dict) else {}
        token_overrides = {
            f"color.{role}": colors[role]
            for role in ("background", "surface", "text", "muted", "primary", "accent")
            if isinstance(colors.get(role), str)
        }
        project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
        desired_theme = {
            **project_theme,
            "base_theme_id": project_theme.get("base_theme_id") or selection.get("selected_theme_id"),
            "palette_ref": "project_palette",
            "token_overrides": token_overrides,
            "fallback_seed": selection.get("deterministic_seed"),
        }
        if plan.get("project_theme") != desired_theme:
            plan["project_theme"] = desired_theme
            changed = True
    slides = plan.get("slides")
    if isinstance(slides, list):
        template_ids = [item.get("template_id") for item in selection.get("template_candidates", []) if isinstance(item, dict)]
        theme_ids = [item.get("theme_id") for item in selection.get("theme_candidates", []) if isinstance(item, dict)]
        palette_ids = [item.get("palette_id") for item in palette_selection.get("palette_candidates", []) if isinstance(item, dict)]
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            spec = slide.get("canvas_spec")
            if not isinstance(spec, dict):
                continue
            if "template_id" not in spec and selection.get("selected_template_id"):
                spec["template_id"] = selection.get("selected_template_id")
                changed = True
            if "theme_id" not in spec and selection.get("selected_theme_id"):
                spec["theme_id"] = selection.get("selected_theme_id")
                changed = True
            if "palette_id" not in spec and palette_selection.get("selected_palette_id"):
                spec["palette_id"] = palette_selection.get("selected_palette_id")
                changed = True
            if not isinstance(spec.get("selection_trace"), dict):
                template_rank = template_ids.index(spec.get("template_id")) + 1 if spec.get("template_id") in template_ids else None
                theme_rank = theme_ids.index(spec.get("theme_id")) + 1 if spec.get("theme_id") in theme_ids else None
                palette_rank = palette_ids.index(spec.get("palette_id")) + 1 if spec.get("palette_id") in palette_ids else None
                spec["selection_trace"] = {
                    "palette_candidate_rank": palette_rank,
                    "template_candidate_rank": template_rank,
                    "theme_candidate_rank": theme_rank,
                    "selection_reason": ["applied from select_style receipts"],
                }
                changed = True
    return changed


def infer_visual_archetype(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["spacex", "space x", "上市", "ipo", "资本", "估值", "火箭", "星链"]):
        return "space_capital_market"
    if any(token in lowered for token in ["桂林", "山水", "旅游", "旅行", "目的地", "景区"]):
        return "travel_destination"
    if any(token in lowered for token in ["论文", "paper", "研究", "attention", "transformer"]):
        return "academic_paper"
    if any(token in lowered for token in ["字节", "bytedance", "公司", "企业", "产品", "组织"]):
        return "company_ecosystem"
    return "general_explainer"


def visual_identity_defaults(archetype: str) -> dict[str, Any]:
    presets = {
        "company_ecosystem": {
            "palette": "light corporate product ecosystem",
            "layout_motif": "产品生态墙",
            "shape_language": "低圆角 App tile 与组织网络节点",
            "image_treatment": "官网或办公场景图片作为封面/结束页信号，正文保持 SVG 组件",
            "component_bias": "ecosystem_wall, org_network, editorial_profile",
            "theme_visual_anchors": ["产品生态墙", "App tile", "组织网络"],
        },
        "space_capital_market": {
            "palette": "dark orbital capital-market signal",
            "layout_motif": "发射窗口与资本市场信号线",
            "shape_language": "轨道线、窗口卡、风险矩阵",
            "image_treatment": "发射或航天图片配暗色 scrim，文字保持 SVG 覆盖",
            "component_bias": "market_signal, timeline_rail, dashboard_scorecard",
            "theme_visual_anchors": ["发射窗口", "轨道线", "资本信号"],
        },
        "travel_destination": {
            "palette": "bright scenic atlas",
            "layout_motif": "目的地地图与路线",
            "shape_language": "地图块、路线线条、景点卡片",
            "image_treatment": "真实风景图主导封面和结束页，正文用地图/路线组件",
            "component_bias": "destination_atlas, timeline_rail, ecosystem_wall",
            "theme_visual_anchors": ["山水地貌", "旅行路线", "景点地图"],
        },
        "academic_paper": {
            "palette": "clean research whiteboard",
            "layout_motif": "论文机制拆解",
            "shape_language": "模块图、公式框、实验表格",
            "image_treatment": "原论文图作为 inline figure，标注保持 SVG 文本",
            "component_bias": "research_deep_dive, chart, timeline_rail",
            "theme_visual_anchors": ["机制图", "公式框", "实验表格"],
        },
        "general_explainer": {
            "palette": "neutral editorial explainer",
            "layout_motif": "结构化说明路径",
            "shape_language": "信息块、连接线、总结条",
            "image_treatment": "图片只做主题证据信号",
            "component_bias": "editorial_profile, chart, timeline_rail",
            "theme_visual_anchors": ["主题对象", "结构路径", "结论卡片"],
        },
    }
    design_dna = presets.get(archetype, presets["general_explainer"])
    return {
        "theme_archetype": archetype,
        "design_dna": design_dna,
        "forbidden_reuse": {
            "recent_decks": 5,
            "avoid_same_palette": True,
            "avoid_same_cover_structure": True,
            "avoid_default_skeleton": True,
        },
        "distinctness_target": {
            "palette_overlap_max": 0.67,
            "renderer_sequence_similarity_max": 0.75,
            "layout_sequence_similarity_max": 0.75,
        },
    }


def ensure_visual_identity(plan: dict[str, Any]) -> bool:
    if isinstance(plan.get("visual_identity"), dict):
        return False
    text_parts = [str(plan.get(key) or "") for key in ["title", "topic", "scenario", "audience"]]
    slides = plan.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if isinstance(slide, dict):
                text_parts.extend(str(slide.get(key) or "") for key in ["title", "key_message", "section", "role"])
    archetype = infer_visual_archetype(" ".join(text_parts))
    plan["visual_identity"] = visual_identity_defaults(archetype)
    return True


def run_plan_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    started_at = now_iso()
    plan = plan_path(project_root)
    if not plan.exists():
        complete_stage(
            project_root,
            state,
            "plan",
            "failed",
            started_at=started_at,
            inputs=["02-plan/slide_plan.json"],
            outputs=[],
            command=[],
            error={"code": "plan_missing", "message": "missing required plan file"},
        )
        raise RunnerError(f"missing required plan file: {plan}")
    try:
        payload = read_json(plan)
        selection_applied = apply_selection_receipts_to_plan(project_root, payload)
        visual_identity_added = ensure_visual_identity(payload)
        if visual_identity_added or selection_applied:
            write_json(plan, payload)
        schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-plan.schema.json"))
        schema_issues = svglide_schema.validate_json_schema(payload, schema)
    except (OSError, json.JSONDecodeError) as error:
        schema_issues = [{"code": "plan_json_invalid", "message": str(error), "path": "$"}]
    status = "failed" if schema_issues else "passed"
    receipt = complete_stage(
        project_root,
        state,
        "plan",
        status,
        started_at=started_at,
        inputs=["02-plan/slide_plan.json"],
        outputs=["receipts/plan.json"],
        command=[],
        error={"code": "plan_schema_failed", "issues": schema_issues} if schema_issues else None,
    )
    receipt["plan_sha256"] = file_sha256(plan)
    receipt["visual_identity_added"] = bool(locals().get("visual_identity_added", False))
    receipt["selection_receipts_applied"] = bool(locals().get("selection_applied", False))
    receipt["summary"] = {"error_count": len(schema_issues)}
    receipt["issues"] = schema_issues
    write_json(receipt_path(project_root, "plan"), receipt)
    if schema_issues:
        raise RunnerError("plan schema validation failed")
    return receipt


def run_select_style_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    started_at = now_iso()
    commands = [
        ["python3", (SCRIPT_DIR / "svglide_palette_selector.py").as_posix(), project_root.as_posix(), "--pretty"],
        ["python3", (SCRIPT_DIR / "svglide_theme_template_selector.py").as_posix(), project_root.as_posix(), "--pretty"],
    ]
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    for command in commands:
        completed = subprocess.run(command, cwd=repo_root(), check=False, capture_output=True, text=True)
        stdout_parts.append(completed.stdout)
        stderr_parts.append(completed.stderr)
        if completed.returncode != 0:
            complete_stage(
                project_root,
                state,
                "select_style",
                "failed",
                started_at=started_at,
                inputs=["00-input/instruction.json", "source/evidence.json"],
                outputs=["02-plan/palette-selection.json", "02-plan/theme-template-selection.json"],
                command=[" / ".join(shlex.join(item) for item in commands)],
                error={
                    "code": "stage_command_failed",
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                },
            )
            raise RunnerError(f"stage 'select_style' failed with exit code {completed.returncode}")
    receipt = complete_stage(
        project_root,
        state,
        "select_style",
        "passed",
        started_at=started_at,
        inputs=["00-input/instruction.json", "source/evidence.json"],
        outputs=[
            "02-plan/palette-selection.json",
            "02-plan/theme-template-selection.json",
            "receipts/palette_selection.json",
            "receipts/theme_template_selection.json",
        ],
        command=[" / ".join(shlex.join(item) for item in commands)],
    )
    receipt["stdout"] = "\n".join(part.strip() for part in stdout_parts if part.strip())
    receipt["stderr"] = "\n".join(part.strip() for part in stderr_parts if part.strip())
    write_json(receipt_path(project_root, "select_style"), receipt)
    return receipt


def lock_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "svglide.lock.json"


def plan_confirmation_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "plan-confirmation.json"


def plan_confirmation_request_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "plan-confirmation.request.json"


def build_plan_confirmation_request(project_root: Path) -> dict[str, Any]:
    plan = plan_path(project_root)
    if not plan.exists():
        raise RunnerError(f"missing required plan file: {plan}")
    request: dict[str, Any] = {
        "version": "svglide-plan-confirmation-request/v1",
        "status": "pending",
        "requested_at": now_iso(),
        "plan_path": project_relpath(plan, project_root),
        "plan_sha256": file_sha256(plan),
        "required_confirmation_file": project_relpath(plan_confirmation_path(project_root), project_root),
        "confirmation_schema": {
            "version": "svglide-plan-confirmation/v1",
            "status": "confirmed",
            "confirmed_by": "user",
            "plan_path": project_relpath(plan, project_root),
            "plan_sha256": file_sha256(plan),
        },
    }
    lock = lock_path(project_root)
    if lock.exists():
        request["lock_path"] = project_relpath(lock, project_root)
        request["lock_sha256"] = file_sha256(lock)
        request["confirmation_schema"]["lock_path"] = request["lock_path"]
        request["confirmation_schema"]["lock_sha256"] = request["lock_sha256"]
    return request


def validate_plan_confirmation(project_root: Path) -> dict[str, Any]:
    request = build_plan_confirmation_request(project_root)
    confirmation_file = plan_confirmation_path(project_root)
    if not confirmation_file.exists():
        write_json(plan_confirmation_request_path(project_root), request)
        raise RunnerError(
            "optional plan confirmation is missing; review 02-plan/plan-confirmation.request.json "
            "and write 02-plan/plan-confirmation.json before rerunning confirm_plan"
        )
    confirmation = read_json(confirmation_file)
    if confirmation.get("version") != "svglide-plan-confirmation/v1":
        raise RunnerError("plan confirmation version must be svglide-plan-confirmation/v1")
    if confirmation.get("status") != "confirmed":
        raise RunnerError("plan confirmation status must be confirmed")
    if confirmation.get("confirmed_by") != "user":
        raise RunnerError("plan confirmation must be confirmed_by=user")
    for key in ["plan_path", "plan_sha256"]:
        if confirmation.get(key) != request.get(key):
            raise RunnerError(f"plan confirmation {key} does not match current plan")
    if "lock_path" in request:
        for key in ["lock_path", "lock_sha256"]:
            if confirmation.get(key) != request.get(key):
                raise RunnerError(f"plan confirmation {key} does not match current lock")
    return confirmation


def run_confirm_plan_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    started_at = now_iso()
    confirmation = validate_plan_confirmation(project_root)
    inputs = ["02-plan/slide_plan.json", "02-plan/plan-confirmation.json"]
    if lock_path(project_root).exists():
        inputs.append("02-plan/svglide.lock.json")
    receipt = complete_stage(
        project_root,
        state,
        "confirm_plan",
        "passed",
        started_at=started_at,
        inputs=inputs,
        outputs=["receipts/confirm_plan.json"],
        command=[],
    )
    receipt["confirmation"] = {
        "confirmed_by": confirmation.get("confirmed_by"),
        "confirmed_at": confirmation.get("confirmed_at"),
        "plan_sha256": confirmation.get("plan_sha256"),
        "lock_sha256": confirmation.get("lock_sha256"),
    }
    write_json(receipt_path(project_root, "confirm_plan"), receipt)
    return receipt


def project_title(project_root: Path) -> str:
    manifest = read_json(project_manifest_path(project_root))
    return str(manifest.get("title") or "Untitled")


def svg_generator_command(project_root: Path) -> list[str]:
    for candidate in [
        project_root / "04-svg" / "generate_svg.py",
        project_root / "logs" / "generate_svg.py",
        project_root / "logs" / "generate_svgs.py",
    ]:
        if candidate.exists():
            return ["python3", candidate.as_posix()]
    return []


def plan_generation_mode(project_root: Path) -> str:
    plan = read_json(plan_path(project_root))
    raw = plan.get("generation_mode") or DEFAULT_GENERATION_MODE
    if raw not in GENERATION_MODES:
        raise RunnerError(f"unsupported generation_mode '{raw}'")
    return str(raw)


def validate_artboard_plan(project_root: Path) -> None:
    plan = read_json(plan_path(project_root))
    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise RunnerError("generation_mode=artboard_satori requires slide_plan.slides")
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            raise RunnerError(f"generation_mode=artboard_satori slide {index} must be an object")
        spec = slide.get("canvas_spec")
        if not isinstance(spec, dict):
            raise RunnerError(f"generation_mode=artboard_satori slide {index} requires canvas_spec")
        canvas = spec.get("canvas")
        content = spec.get("content")
        if spec.get("version") != "svglide-canvas-spec/v1":
            raise RunnerError(f"generation_mode=artboard_satori slide {index} canvas_spec.version is invalid")
        if not isinstance(canvas, dict) or canvas.get("width") != 960 or canvas.get("height") != 540 or canvas.get("viewBox") != "0 0 960 540":
            raise RunnerError(f"generation_mode=artboard_satori slide {index} canvas_spec.canvas must be 960x540")
        if not isinstance(spec.get("template_id"), str) or not spec.get("template_id"):
            raise RunnerError(f"generation_mode=artboard_satori slide {index} canvas_spec.template_id is required")
        if not isinstance(spec.get("theme"), dict):
            raise RunnerError(f"generation_mode=artboard_satori slide {index} canvas_spec.theme is required")
        if not isinstance(content, dict) or not isinstance(content.get("title"), str) or not content.get("title").strip():
            raise RunnerError(f"generation_mode=artboard_satori slide {index} canvas_spec.content.title is required")


def artboard_generator_command(project_root: Path) -> list[str]:
    return [
        "python3",
        (SCRIPT_DIR / "svglide_artboard_renderer.py").as_posix(),
        project_root.as_posix(),
        "--pretty",
    ]


def artboard_receipt_paths(project_root: Path) -> list[str]:
    root = project_root / "04-artboard" / "raw"
    if not root.exists():
        return []
    return [path.relative_to(project_root).as_posix() for path in sorted(root.glob("page-*.receipt.json")) if path.is_file()]


def require_source_current(project_root: Path) -> None:
    receipt = read_json(project_root / "source" / "source-receipt.json")
    if receipt.get("status") != "passed":
        raise RunnerError("source stage must be passed before continuing")
    inputs = receipt.get("inputs")
    if not isinstance(inputs, dict):
        raise RunnerError("source receipt inputs are missing; rerun source")
    expected = {
        "source_notes_sha256": optional_project_file_hash(project_root, "source/source-notes.md"),
        "evidence_sha256": optional_project_file_hash(project_root, "source/evidence.json"),
    }
    for key, current in expected.items():
        if inputs.get(key) != current:
            raise RunnerError(f"source receipt {key} does not match current source files; rerun source")


def require_assets_current(project_root: Path) -> None:
    manifest = read_json(project_root / "03-assets" / "asset-manifest.json")
    expected = {
        "plan_sha256": optional_project_file_hash(project_root, "02-plan/slide_plan.json"),
        "lock_sha256": optional_project_file_hash(project_root, "02-plan/svglide.lock.json"),
        "assets_json_sha256": optional_project_file_hash(project_root, "03-assets/assets.json"),
    }
    for key, current in expected.items():
        recorded = manifest.get(key)
        if recorded != current:
            raise RunnerError(f"assets manifest {key} does not match current project files; rerun assets")
    if manifest.get("source_receipt_sha256") != optional_project_file_hash(project_root, "source/source-receipt.json"):
        raise RunnerError("assets manifest source_receipt_sha256 does not match current source receipt; rerun assets")
    summary = manifest.get("summary")
    if isinstance(summary, dict) and summary.get("error_count", 0) != 0:
        raise RunnerError("assets manifest contains errors; rerun assets after repair")


def write_page_generation_receipts(
    project_root: Path,
    generated_files: list[dict[str, str]],
    generator_mode: str,
    command: list[str],
    generation_mode: str = DEFAULT_GENERATION_MODE,
    artboard_receipts: list[str] | None = None,
    asset_injection_summary: dict[str, Any] | None = None,
) -> list[str]:
    receipt_paths: list[str] = []
    plan_hash = optional_project_file_hash(project_root, "02-plan/slide_plan.json")
    evidence_hash = optional_project_file_hash(project_root, "source/evidence.json")
    lock_hash = optional_project_file_hash(project_root, "02-plan/svglide.lock.json")
    asset_manifest_hash = optional_project_file_hash(project_root, "03-assets/asset-manifest.json")
    generator_script_hash = file_sha256(Path(command[1])) if len(command) > 1 and Path(command[1]).exists() else None
    plan = read_json(project_root / "02-plan" / "slide_plan.json")
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    visual_identity = plan.get("visual_identity") if isinstance(plan.get("visual_identity"), dict) else {}
    theme_archetype = visual_identity.get("theme_archetype") if isinstance(visual_identity.get("theme_archetype"), str) else None
    injection_events = asset_injection_summary.get("by_page") if isinstance(asset_injection_summary, dict) else []
    if not isinstance(injection_events, list):
        injection_events = []
    for index, item in enumerate(generated_files, 1):
        svg_path = project_root / item["path"]
        page_receipt = svg_path.with_suffix(".receipt.json")
        page_injections = [
            event
            for event in injection_events
            if isinstance(event, dict) and event.get("page") == index
        ]
        asset_refs = [
            {
                "asset_id": event.get("asset_id"),
                "href": event.get("href"),
                "file": event.get("file"),
                "placement_role": event.get("placement_role"),
                "status": event.get("status"),
            }
            for event in page_injections
            if isinstance(event, dict) and event.get("status") in {"injected", "already_present"}
        ]
        slide = slides[index - 1] if index <= len(slides) and isinstance(slides[index - 1], dict) else {}
        identity_fit_reason = slide.get("identity_fit_reason")
        if not isinstance(identity_fit_reason, str) or not identity_fit_reason.strip():
            identity_fit_reason = f"renderer and visual recipe are expected to fit theme_archetype={theme_archetype or 'unspecified'}"
        reuse_risk_score = slide.get("reuse_risk_score")
        if not isinstance(reuse_risk_score, (int, float)):
            reuse_risk_score = 0
        fallback_skeleton_used = bool(slide.get("fallback_skeleton_used") or visual_identity.get("fallback_skeleton_used"))
        payload = {
            "version": "svglide-page-generation/v1",
            "stage": "generate_svg",
            "page": index,
            "source_svg": item["path"],
            "source_sha256": item["sha256"],
            "plan_path": "02-plan/slide_plan.json",
            "plan_sha256": plan_hash,
            "evidence_path": "source/evidence.json" if evidence_hash else None,
            "evidence_sha256": evidence_hash,
            "lock_path": "02-plan/svglide.lock.json" if lock_hash else None,
            "lock_sha256": lock_hash,
            "asset_manifest_path": "03-assets/asset-manifest.json" if asset_manifest_hash else None,
            "asset_manifest_sha256": asset_manifest_hash,
            "generator_mode": generator_mode,
            "generation_mode": generation_mode,
            "artboard_receipt": artboard_receipts[index - 1] if artboard_receipts and index <= len(artboard_receipts) else None,
            "generator_script_sha256": generator_script_hash,
            "asset_refs": asset_refs,
            "asset_injection": page_injections,
            "theme_archetype": theme_archetype,
            "identity_fit_reason": identity_fit_reason,
            "reuse_risk_score": reuse_risk_score,
            "fallback_skeleton_used": fallback_skeleton_used,
            "visible_text_policy": "visible SVG text must be traceable to slide_plan.json or source/evidence.json",
            "generated_at": now_iso(),
        }
        write_json(page_receipt, payload)
        receipt_paths.append(page_receipt.relative_to(project_root).as_posix())
    return receipt_paths


def validate_generator_receipt(project_root: Path, receipt: dict[str, Any]) -> list[dict[str, str]]:
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-generator-receipt.schema.json"))
    issues = svglide_schema.validate_json_schema(receipt, schema)
    generation_mode = receipt.get("generation_mode") or DEFAULT_GENERATION_MODE
    if generation_mode not in GENERATION_MODES:
        issues.append({"code": "generator_generation_mode_invalid", "path": "$.generation_mode", "message": "generation_mode must be direct_svg or artboard_satori"})
    generated = receipt.get("generated_files")
    page_receipts = receipt.get("page_receipts")
    if isinstance(generated, list) and isinstance(page_receipts, list) and len(generated) != len(page_receipts):
        issues.append({"code": "generator_page_receipt_count_mismatch", "path": "$.page_receipts", "message": "page_receipts count must match generated_files"})
    artboard_receipts = receipt.get("artboard_receipts")
    if generation_mode == "artboard_satori":
        if not isinstance(artboard_receipts, list) or not artboard_receipts:
            issues.append({"code": "generator_artboard_receipts_missing", "path": "$.artboard_receipts", "message": "artboard_satori generation must include artboard_receipts"})
        elif isinstance(generated, list) and len(artboard_receipts) != len(generated):
            issues.append({"code": "generator_artboard_receipt_count_mismatch", "path": "$.artboard_receipts", "message": "artboard_receipts count must match generated_files"})
    plan = read_json(plan_path(project_root))
    slides = plan.get("slides")
    if isinstance(slides, list) and isinstance(generated, list) and len(slides) != len(generated):
        issues.append({"code": "generator_slide_count_mismatch", "path": "$.generated_files", "message": "generated SVG count must match slide_plan.slides"})
    if isinstance(page_receipts, list):
        for item in page_receipts:
            if not isinstance(item, str) or not (project_root / item).exists():
                issues.append({"code": "generator_page_receipt_missing", "path": "$.page_receipts", "message": f"missing page receipt: {item}"})
    if isinstance(artboard_receipts, list):
        for item in artboard_receipts:
            if not isinstance(item, str) or not (project_root / item).exists():
                issues.append({"code": "generator_artboard_receipt_missing", "path": "$.artboard_receipts", "message": f"missing artboard receipt: {item}"})
    return issues


def run_generate_svg_stage(
    project_root: Path,
    state: dict[str, Any],
    *,
    command_runner=subprocess.run,
) -> dict[str, Any]:
    require_stage_passed(state, "assets")
    require_source_current(project_root)
    require_assets_current(project_root)
    started_at = now_iso()
    generation_mode = plan_generation_mode(project_root)
    command = svg_generator_command(project_root)
    artboard_result: dict[str, Any] = {}
    if generation_mode == "artboard_satori":
        validate_artboard_plan(project_root)
        if command:
            complete_stage(
                project_root,
                state,
                "generate_svg",
                "failed",
                started_at=started_at,
                inputs=["02-plan/slide_plan.json", "03-assets/assets.json"],
                outputs=[],
                command=command,
                error={
                    "code": "generator_mode_conflict",
                    "message": "generation_mode=artboard_satori cannot be combined with project-local generate_svg.py",
                },
            )
            raise RunnerError("generation_mode=artboard_satori cannot be combined with project-local generate_svg.py")
        command = artboard_generator_command(project_root)
    if command:
        completed = command_runner(command, cwd=repo_root(), check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            complete_stage(
                project_root,
                state,
                "generate_svg",
                "failed",
                started_at=started_at,
                inputs=["02-plan/slide_plan.json", "03-assets/assets.json"],
                outputs=["04-svg"],
                command=command,
                error={
                    "code": "stage_command_failed",
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                },
            )
            raise RunnerError(f"stage 'generate_svg' failed with exit code {completed.returncode}")
        if generation_mode == "artboard_satori":
            parsed = parse_json_or_none(completed.stdout)
            artboard_result = parsed if isinstance(parsed, dict) else {}

    try:
        generated_files = raw_visual_file_hashes(project_root) if generation_mode == "artboard_satori" else source_file_hashes(project_root)
    except RunnerError as err:
        missing_code = "raw_visual_missing" if generation_mode == "artboard_satori" else "generated_svg_missing"
        missing_message = "generate_svg produced no raw visual artifacts under 04-artboard/raw" if generation_mode == "artboard_satori" else "generate_svg produced no source SVG files under 04-svg"
        complete_stage(
            project_root,
            state,
            "generate_svg",
            "failed",
            started_at=started_at,
            inputs=["02-plan/slide_plan.json", "03-assets/assets.json"],
            outputs=[],
            command=command,
            error={
                "code": missing_code,
                "message": missing_message,
            },
        )
        raise RunnerError(missing_message) from err

    asset_injection_summary = {"used_count": 0, "by_page": [], "stage": "contract_compile_pending"} if generation_mode == "artboard_satori" else svglide_asset_injector.inject_project_assets(project_root)
    if generation_mode != "artboard_satori":
        generated_files = source_file_hashes(project_root)
    generator_mode = "script" if command else "external"
    artboard_receipts = artboard_result.get("artboard_receipts") if isinstance(artboard_result.get("artboard_receipts"), list) else artboard_receipt_paths(project_root)
    artboard_additional_receipts = artboard_result.get("additional_receipts") if isinstance(artboard_result.get("additional_receipts"), list) else []
    artboard_output_paths: list[str] = []
    if generation_mode == "artboard_satori":
        for key in ["canvas_spec_validate", "artboard_render_receipt", "satori_bridge_receipt"]:
            value = artboard_result.get(key)
            if isinstance(value, str):
                artboard_output_paths.append(value)
        contact_sheet = artboard_result.get("contact_sheet")
        if isinstance(contact_sheet, dict) and isinstance(contact_sheet.get("path"), str):
            artboard_output_paths.append(contact_sheet["path"])
    page_receipts = write_page_generation_receipts(
        project_root,
        generated_files,
        generator_mode,
        command,
        generation_mode,
        artboard_receipts if generation_mode == "artboard_satori" else None,
        asset_injection_summary,
    )
    receipt = complete_stage(
        project_root,
        state,
        "generate_svg",
        "passed",
        started_at=started_at,
        inputs=["02-plan/slide_plan.json", "03-assets/assets.json"],
        outputs=[item["path"] for item in generated_files]
        + page_receipts
        + (artboard_receipts if generation_mode == "artboard_satori" else [])
        + (artboard_additional_receipts if generation_mode == "artboard_satori" else [])
        + artboard_output_paths,
        command=command,
    )
    receipt["generator_mode"] = generator_mode
    receipt["generation_mode"] = generation_mode
    receipt["generated_files"] = generated_files
    receipt["page_receipts"] = page_receipts
    if generation_mode == "artboard_satori":
        receipt["artboard_receipts"] = artboard_receipts
        receipt["artboard_additional_receipts"] = artboard_additional_receipts
        for key in ["raw_visual_manifest", "raw_visual_files", "semantic_maps"]:
            if key in artboard_result:
                receipt[key] = artboard_result[key]
        for key in ["canvas_spec_validate", "artboard_render_receipt", "satori_bridge_receipt", "contact_sheet"]:
            if key in artboard_result:
                receipt[key] = artboard_result[key]
    receipt["asset_injection_summary"] = asset_injection_summary
    page_receipt_payloads = [read_json(project_root / path) for path in page_receipts]
    receipt["fallback_skeleton_used"] = any(bool(payload.get("fallback_skeleton_used")) for payload in page_receipt_payloads)
    receipt["page_identity_summary"] = [
        {
            "page": payload.get("page"),
            "theme_archetype": payload.get("theme_archetype"),
            "identity_fit_reason": payload.get("identity_fit_reason"),
            "reuse_risk_score": payload.get("reuse_risk_score"),
            "fallback_skeleton_used": payload.get("fallback_skeleton_used"),
        }
        for payload in page_receipt_payloads
    ]
    receipt["plan_sha256"] = optional_project_file_hash(project_root, "02-plan/slide_plan.json")
    receipt["evidence_sha256"] = optional_project_file_hash(project_root, "source/evidence.json")
    receipt["lock_sha256"] = optional_project_file_hash(project_root, "02-plan/svglide.lock.json")
    receipt["asset_manifest_sha256"] = optional_project_file_hash(project_root, "03-assets/asset-manifest.json")
    receipt["source_receipt_sha256"] = optional_project_file_hash(project_root, "source/source-receipt.json")
    receipt["generator_script_sha256"] = file_sha256(Path(command[1])) if len(command) > 1 and Path(command[1]).exists() else None
    receipt["visible_text_policy"] = "visible SVG text must be traceable to slide_plan.json or source/evidence.json"
    if generation_mode == "artboard_satori":
        receipt["template_fit_check"] = "06-check/template-fit.json"
        if "06-check/template-fit.json" not in receipt["outputs"]:
            receipt["outputs"].append("06-check/template-fit.json")
    schema_issues = validate_generator_receipt(project_root, receipt)
    if schema_issues:
        receipt["status"] = "failed"
        receipt["error"] = {"code": "generator_receipt_invalid", "issues": schema_issues}
        write_json(receipt_path(project_root, "generate_svg"), receipt)
        record_stage(state, "generate_svg", "failed", receipt_path(project_root, "generate_svg"))
        write_state(project_root, state)
        raise RunnerError("generate_svg receipt validation failed")
    write_json(receipt_path(project_root, "generate_svg"), receipt)
    if generation_mode == "artboard_satori":
        fit_command = [
            "python3",
            (SCRIPT_DIR / "svglide_template_fit_check.py").as_posix(),
            project_root.as_posix(),
            "--pretty",
        ]
        fit_completed = subprocess.run(fit_command, cwd=repo_root(), check=False, capture_output=True, text=True)
        if fit_completed.returncode != 0:
            receipt["status"] = "failed"
            receipt["error"] = {
                "code": "template_fit_failed",
                "returncode": fit_completed.returncode,
                "stderr": fit_completed.stderr,
            }
            write_json(receipt_path(project_root, "generate_svg"), receipt)
            record_stage(state, "generate_svg", "failed", receipt_path(project_root, "generate_svg"))
            write_state(project_root, state)
            raise RunnerError("artboard template fit check failed")
    return receipt


def require_generated_svg_current(project_root: Path) -> None:
    receipt = read_json(receipt_path(project_root, "generate_svg"))
    generated = receipt.get("generated_files")
    generation_mode = receipt.get("generation_mode") or DEFAULT_GENERATION_MODE
    if isinstance(generated, list) and generated:
        current_generated = raw_visual_file_hashes(project_root) if generation_mode == "artboard_satori" else source_file_hashes(project_root)
        if generated != current_generated:
            raise RunnerError("generated visual files changed after generate_svg; rerun generate_svg before prepare")
    expected = {
        "plan_sha256": optional_project_file_hash(project_root, "02-plan/slide_plan.json"),
        "evidence_sha256": optional_project_file_hash(project_root, "source/evidence.json"),
        "asset_manifest_sha256": optional_project_file_hash(project_root, "03-assets/asset-manifest.json"),
        "source_receipt_sha256": optional_project_file_hash(project_root, "source/source-receipt.json"),
    }
    for key, current in expected.items():
        if receipt.get(key) != current:
            raise RunnerError(f"generate_svg receipt {key} does not match current project files; rerun generate_svg")
    if generation_mode == "artboard_satori":
        artboard_receipts = receipt.get("artboard_receipts")
        if not isinstance(artboard_receipts, list) or not artboard_receipts:
            raise RunnerError("generate_svg receipt is missing artboard_receipts; rerun generate_svg")
        for item in artboard_receipts:
            if not isinstance(item, str) or not (project_root / item).exists():
                raise RunnerError(f"artboard receipt is missing: {item}; rerun generate_svg")
        raw_manifest = receipt.get("raw_visual_manifest")
        if not isinstance(raw_manifest, str) or not (project_root / raw_manifest).exists():
            raise RunnerError("generate_svg receipt is missing raw_visual_manifest; rerun generate_svg")
    command = receipt.get("command")
    if isinstance(command, list) and len(command) > 1 and isinstance(command[1], str):
        script = Path(command[1])
        if script.exists() and receipt.get("generator_script_sha256") != file_sha256(script):
            raise RunnerError("generator script changed after generate_svg; rerun generate_svg")


def require_contract_compile_current(project_root: Path) -> None:
    require_generated_svg_current(project_root)
    receipt = read_json(receipt_path(project_root, "contract_compile"))
    manifest_path = contract_manifest_path(project_root)
    if not manifest_path.exists():
        raise RunnerError("contract compile manifest is missing; rerun contract_compile")
    manifest = read_json(manifest_path)
    if manifest.get("status") == "failed":
        raise RunnerError("contract compile manifest failed; rerun contract_compile after repair")
    if receipt.get("raw_visual_manifest_sha256") != optional_project_file_hash(project_root, "04-artboard/raw/manifest.json"):
        raise RunnerError("contract compile raw manifest hash is stale; rerun contract_compile")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RunnerError("contract compile manifest has no pages; rerun contract_compile")
    current_outputs = contract_output_hashes(project_root)
    expected_outputs = [
        {"path": page.get("output"), "sha256": page.get("output_sha256")}
        for page in pages
        if isinstance(page, dict)
    ]
    if expected_outputs != current_outputs:
        raise RunnerError("contract compiled SVG files changed after contract_compile; rerun contract_compile")


def require_existing_stage_current(project_root: Path, stage: str, *, profile: str = "production") -> None:
    if stage == "source":
        require_source_current(project_root)
    elif stage == "theme_validate":
        check = read_json(project_root / "06-check/theme-validate.json")
        inputs = check.get("inputs")
        if not isinstance(inputs, dict) or inputs.get("plan_sha256") != optional_project_file_hash(project_root, "02-plan/slide_plan.json"):
            raise RunnerError("theme_validate plan hash is stale; rerun theme_validate")
    elif stage == "assets":
        require_source_current(project_root)
        require_assets_current(project_root)
    elif stage == "generate_svg":
        require_source_current(project_root)
        require_assets_current(project_root)
        require_generated_svg_current(project_root)
    elif stage == "contract_compile":
        require_contract_compile_current(project_root)
    elif stage == "prepare":
        require_contract_compile_current(project_root)
    elif stage == "quality_gate":
        require_quality_gate_current(project_root)
    elif stage == "generation_benchmark":
        require_generation_benchmark_current(project_root, profile=profile)
    elif stage == "dry_run":
        require_quality_gate_current(project_root)
        require_generation_benchmark_current(project_root, profile=profile)
    elif stage == "visual_acceptance":
        require_visual_acceptance_current(project_root)
    elif stage == "live_create":
        require_quality_gate_current(project_root)
        require_visual_acceptance_current(project_root)
        require_ppe_proof_current(project_root)
        if profile == "production_live":
            require_pre_submit_review_current(project_root)
    elif stage == "ppe_proof":
        require_visual_acceptance_current(project_root)
        require_ppe_proof_current(project_root)
    elif stage == "pre_submit_review":
        require_visual_acceptance_current(project_root)
        require_pre_submit_review_current(project_root)
    elif stage == "readback":
        require_quality_gate_current(project_root)
        require_visual_acceptance_current(project_root)


def require_quality_gate_passed(project_root: Path) -> dict[str, Any]:
    gate = read_json(project_root / "06-check" / "quality-gate.json")
    if gate.get("status") != "passed":
        raise RunnerError("quality gate must be passed before create stages")
    gate_hashes = gate.get("prepared_files")
    if isinstance(gate_hashes, list) and gate_hashes and gate_hashes != prepared_file_hashes(project_root):
        raise RunnerError("prepared SVG files changed after quality gate; rerun checks before create")
    return gate


def require_quality_gate_current(project_root: Path) -> dict[str, Any]:
    gate = require_quality_gate_passed(project_root)
    inputs = gate.get("inputs")
    if not isinstance(inputs, dict) or inputs.get("visual_distinctness") != "06-check/visual-distinctness.json":
        raise RunnerError("quality gate is missing visual_distinctness input; rerun quality_gate")
    if inputs.get("theme_validate") != "06-check/theme-validate.json":
        raise RunnerError("quality gate is missing theme_validate input; rerun theme_validate and quality_gate")
    if inputs.get("theme_adherence") != "06-check/theme-adherence.json":
        raise RunnerError("quality gate is missing theme_adherence input; rerun theme_adherence and quality_gate")
    checks = gate.get("checks")
    check_names = {item.get("name") for item in checks if isinstance(item, dict)} if isinstance(checks, list) else set()
    if "visual-distinctness" not in check_names:
        raise RunnerError("quality gate is missing visual-distinctness check; rerun quality_gate")
    if "theme-validate" not in check_names:
        raise RunnerError("quality gate is missing theme-validate check; rerun quality_gate")
    if "theme-adherence" not in check_names:
        raise RunnerError("quality gate is missing theme-adherence check; rerun quality_gate")
    if plan_declares_selection(project_root):
        for input_name, rel, check_name in [
            ("palette_review", "06-check/palette-review.json", "palette-review"),
            ("theme_template_selection_review", "06-check/theme-template-selection-review.json", "theme-template-selection-review"),
            ("plan_bundle_review", "06-check/plan-bundle-review.json", "plan-bundle-review"),
        ]:
            if inputs.get(input_name) != rel:
                raise RunnerError(f"quality gate is missing {input_name} input; rerun selection_review and quality_gate")
            if check_name not in check_names:
                raise RunnerError(f"quality gate is missing {check_name} check; rerun quality_gate")
            if not (project_root / rel).exists():
                raise RunnerError(f"{input_name} receipt is missing; rerun selection_review and quality_gate")
    if not (project_root / "06-check/visual-distinctness.json").exists():
        raise RunnerError("visual distinctness receipt is missing; rerun visual_distinctness_review and quality_gate")
    for input_name, rel in [
        ("theme_validate", "06-check/theme-validate.json"),
        ("theme_adherence", "06-check/theme-adherence.json"),
        ("visual_distinctness", "06-check/visual-distinctness.json"),
    ]:
        if not (project_root / rel).exists():
            raise RunnerError(f"{input_name} receipt is missing; rerun {input_name} and quality_gate")
    input_hashes = gate.get("input_hashes")
    if not isinstance(input_hashes, dict):
        raise RunnerError("quality gate is missing input_hashes; rerun quality_gate")
    for input_name, rel in [
        ("theme_validate", "06-check/theme-validate.json"),
        ("theme_adherence", "06-check/theme-adherence.json"),
        ("visual_distinctness", "06-check/visual-distinctness.json"),
        ("generator_receipt", "receipts/generate_svg.json"),
    ]:
        if input_hashes.get(input_name) != optional_project_file_hash(project_root, rel):
            raise RunnerError(f"quality gate {input_name} hash is stale; rerun quality_gate")
    if plan_declares_selection(project_root):
        for input_name, rel in [
            ("palette_review", "06-check/palette-review.json"),
            ("theme_template_selection_review", "06-check/theme-template-selection-review.json"),
            ("plan_bundle_review", "06-check/plan-bundle-review.json"),
        ]:
            if input_hashes.get(input_name) != optional_project_file_hash(project_root, rel):
                raise RunnerError(f"quality gate {input_name} hash is stale; rerun quality_gate")
    if inputs.get("generation_mode") == "artboard_satori":
        if inputs.get("artboard_package_check") != "06-check/artboard-package-check.json":
            raise RunnerError("quality gate is missing artboard_package_check input; rerun package_check and quality_gate")
        if "artboard-package-check" not in check_names:
            raise RunnerError("quality gate is missing artboard-package-check check; rerun quality_gate")
        if input_hashes.get("artboard_package_check") != optional_project_file_hash(project_root, "06-check/artboard-package-check.json"):
            raise RunnerError("quality gate artboard_package_check hash is stale; rerun quality_gate")
    return gate


def require_generation_benchmark_current(project_root: Path, *, profile: str) -> dict[str, Any]:
    benchmark = read_json(project_root / "06-check" / "generation-benchmark.json")
    if benchmark.get("status") != "passed":
        raise RunnerError("generation_benchmark must pass before dry_run")
    if benchmark.get("profile") != profile:
        raise RunnerError("generation_benchmark profile is stale; rerun generation_benchmark")
    quality = benchmark.get("quality")
    if not isinstance(quality, list) or not quality:
        raise RunnerError("generation_benchmark quality report is missing; rerun generation_benchmark")
    if any(not isinstance(item, dict) or item.get("status") != "passed" for item in quality):
        raise RunnerError("generation_benchmark quality report has failures; rerun generation_benchmark")
    cache = benchmark.get("cache")
    if not isinstance(cache, dict) or not isinstance(cache.get("hit_count"), int) or not isinstance(cache.get("miss_count"), int):
        raise RunnerError("generation_benchmark cache telemetry is missing; rerun generation_benchmark")
    timing = read_json_optional(project_root / "06-check" / "timing-report.json")
    timing_cache = timing.get("cache") if isinstance(timing.get("cache"), dict) else None
    if not timing_cache or not isinstance(timing_cache.get("hit_count"), int) or not isinstance(timing_cache.get("miss_count"), int):
        raise RunnerError("timing report cache telemetry is missing; rerun generation_benchmark")
    return benchmark


def require_visual_acceptance_current(project_root: Path) -> dict[str, Any]:
    check_path = project_root / "06-check" / "visual-acceptance.json"
    if not check_path.exists():
        if not artboard_visual_acceptance_required(project_root):
            return {"status": "skipped", "generation_mode": DEFAULT_GENERATION_MODE, "action": "engineering_only"}
        raise RunnerError("visual_acceptance must be run before visual delivery or live submission")
    check = read_json(check_path)
    status = check.get("status")
    mode = check.get("generation_mode")
    if mode == "artboard_satori" and status != "passed":
        raise RunnerError("visual_acceptance must pass for artboard_satori delivery")
    if status not in {"passed", "skipped"}:
        raise RunnerError("visual_acceptance status must be passed or skipped")
    if status == "skipped" and (check.get("action") != "engineering_only" or check.get("deliverable_pass") is not False):
        raise RunnerError("skipped visual_acceptance must be engineering_only with deliverable_pass=false")
    inputs = check.get("inputs")
    if not isinstance(inputs, dict):
        raise RunnerError("visual_acceptance inputs are missing; rerun visual_acceptance")
    expected = {
        "slide_plan_sha256": optional_project_file_hash(project_root, "02-plan/slide_plan.json"),
        "generator_receipt_sha256": optional_project_file_hash(project_root, "receipts/generate_svg.json"),
    }
    if status == "passed":
        expected.update(
            {
                "asset_manifest_sha256": optional_project_file_hash(project_root, "03-assets/asset-manifest.json"),
                "quality_gate_sha256": optional_project_file_hash(project_root, "06-check/quality-gate.json"),
                "dry_run_sha256": optional_project_file_hash(project_root, "07-create/dry-run.json"),
                "preview_sha256": optional_project_file_hash(project_root, "05-preview/preview.html"),
                "preview_manifest_sha256": optional_project_file_hash(project_root, "05-preview/preview-manifest.json"),
                "template_guardrails_sha256": file_sha256(TEMPLATE_GUARDRAILS_PATH) if TEMPLATE_GUARDRAILS_PATH.exists() else None,
            }
        )
        contact_sheet = inputs.get("contact_sheet")
        if not isinstance(contact_sheet, dict) or contact_sheet.get("sha256") != optional_project_file_hash(project_root, "05-preview/contact-sheet.png"):
            raise RunnerError("visual_acceptance contact_sheet hash is stale; rerun visual_acceptance")
        if mode == "artboard_satori":
            require_recorded_artifacts_current(project_root, check.get("artboard_artifacts"), stage="visual_acceptance")
            visual_evidence = check.get("visual_evidence")
            evidence_pages = visual_evidence.get("pages") if isinstance(visual_evidence, dict) else None
            require_visual_evidence_pages_current(
                evidence_pages,
                stage="visual_acceptance",
                preview_sha256=expected.get("preview_sha256"),
                preview_manifest_sha256=expected.get("preview_manifest_sha256"),
            )
            deck_rhythm = check.get("deck_rhythm")
            if not isinstance(deck_rhythm, dict) or deck_rhythm.get("schema_version") != "svglide-deck-rhythm/v1":
                raise RunnerError("visual_acceptance deck_rhythm is missing; rerun visual_acceptance")
    for key, current in expected.items():
        if inputs.get(key) != current:
            raise RunnerError(f"visual_acceptance {key} does not match current project files; rerun visual_acceptance")
    receipt = project_root / "receipts" / "visual_acceptance.json"
    if not receipt.exists():
        raise RunnerError("visual_acceptance receipt is missing; rerun visual_acceptance")
    if file_sha256(receipt) != file_sha256(check_path):
        raise RunnerError("visual_acceptance receipt does not match current check; rerun visual_acceptance")
    return check


def artboard_visual_acceptance_required(project_root: Path) -> bool:
    try:
        return plan_generation_mode(project_root) == "artboard_satori"
    except RunnerError:
        return False


def require_recorded_artifacts_current(project_root: Path, artifacts: Any, *, stage: str) -> None:
    if not isinstance(artifacts, list) or not artifacts:
        raise RunnerError(f"{stage} is missing recorded artifact hashes; rerun {stage}")
    for item in artifacts:
        if not isinstance(item, dict):
            raise RunnerError(f"{stage} recorded artifacts are invalid; rerun {stage}")
        rel = item.get("path")
        recorded = item.get("sha256")
        if not isinstance(rel, str) or not rel or not isinstance(recorded, str) or not recorded:
            raise RunnerError(f"{stage} recorded artifacts must include path and sha256; rerun {stage}")
        current = optional_project_file_hash(project_root, rel)
        if current is None:
            raise RunnerError(f"{stage} artifact is missing: {rel}; rerun {stage}")
        if recorded != current:
            raise RunnerError(f"{stage} artifact hash is stale: {rel}; rerun {stage}")


def require_visual_evidence_pages_current(
    pages: Any,
    *,
    stage: str,
    preview_sha256: str | None = None,
    preview_manifest_sha256: str | None = None,
) -> None:
    if not isinstance(pages, list) or not pages:
        raise RunnerError(f"{stage} visual_evidence.pages is missing; rerun {stage}")
    for item in pages:
        if not isinstance(item, dict):
            raise RunnerError(f"{stage} visual_evidence.pages entries are invalid; rerun {stage}")
        page = item.get("page")
        evidence_path = item.get("evidence_path")
        preview_anchor = item.get("preview_anchor")
        page_preview_sha256 = item.get("preview_sha256")
        page_preview_manifest_sha256 = item.get("preview_manifest_sha256")
        contact_sheet_tile = item.get("contact_sheet_tile")
        if not isinstance(page, int) or not isinstance(evidence_path, str) or not evidence_path:
            raise RunnerError(f"{stage} visual_evidence.pages entries must include page and evidence_path; rerun {stage}")
        if not isinstance(preview_anchor, str) or not preview_anchor:
            raise RunnerError(f"{stage} visual_evidence.pages entries must include preview_anchor; rerun {stage}")
        if not isinstance(page_preview_sha256, str) or not page_preview_sha256:
            raise RunnerError(f"{stage} visual_evidence.pages entries must include preview_sha256; rerun {stage}")
        if not isinstance(page_preview_manifest_sha256, str) or not page_preview_manifest_sha256:
            raise RunnerError(f"{stage} visual_evidence.pages entries must include preview_manifest_sha256; rerun {stage}")
        if preview_sha256 is not None and page_preview_sha256 != preview_sha256:
            raise RunnerError(f"{stage} visual_evidence.pages preview_sha256 is stale; rerun {stage}")
        if preview_manifest_sha256 is not None and page_preview_manifest_sha256 != preview_manifest_sha256:
            raise RunnerError(f"{stage} visual_evidence.pages preview_manifest_sha256 is stale; rerun {stage}")
        if not isinstance(contact_sheet_tile, dict):
            raise RunnerError(f"{stage} visual_evidence.pages entries must include contact_sheet_tile; rerun {stage}")


def require_pre_submit_review_current(project_root: Path) -> dict[str, Any]:
    review_path = project_root / "06-check" / "pre-submit-review.json"
    if not review_path.exists():
        raise RunnerError("pre_submit_review must be passed before production live create")
    review = read_json(review_path)
    if review.get("status") != "passed":
        raise RunnerError("pre_submit_review must be passed before production live create")
    inputs = review.get("inputs")
    if not isinstance(inputs, dict):
        raise RunnerError("pre_submit_review inputs are missing; rerun pre_submit_review")
    expected = {
        "plan_sha256": optional_project_file_hash(project_root, "02-plan/slide_plan.json"),
        "quality_gate_sha256": optional_project_file_hash(project_root, "06-check/quality-gate.json"),
        "theme_adherence_sha256": optional_project_file_hash(project_root, "06-check/theme-adherence.json"),
        "visual_distinctness_sha256": optional_project_file_hash(project_root, "06-check/visual-distinctness.json"),
    }
    for key, current in expected.items():
        if inputs.get(key) != current:
            raise RunnerError(f"pre_submit_review {key} does not match current project files; rerun pre_submit_review")
    if review.get("prepared_files") != prepared_file_hashes(project_root):
        raise RunnerError("prepared SVG files changed after pre_submit_review; rerun pre_submit_review")
    human = review.get("human_approval")
    if not isinstance(human, dict) or human.get("approved") is not True:
        raise RunnerError("pre_submit_review is missing human approval")
    return review


def require_ppe_proof_current(project_root: Path) -> dict[str, Any]:
    proof = read_json(project_root / "07-create" / "ppe-proof.json")
    if proof.get("status") != "passed":
        raise RunnerError("PPE proof must be passed before live create")
    inputs = proof.get("inputs")
    if not isinstance(inputs, dict):
        raise RunnerError("PPE proof inputs are missing; rerun ppe_proof")
    expected = {
        "quality_gate_sha256": optional_project_file_hash(project_root, "06-check/quality-gate.json"),
        "dry_run_sha256": optional_project_file_hash(project_root, "07-create/dry-run.json"),
        "proof_input_sha256": optional_project_file_hash(project_root, "07-create/ppe-proof.input.json"),
    }
    for key, current in expected.items():
        if inputs.get(key) != current:
            raise RunnerError(f"PPE proof {key} does not match current project files; rerun ppe_proof")
    return proof


def write_direct_svg_package_check(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    started_at = now_iso()
    payload = {
        "version": "svglide-artboard-package-check/v1",
        "stage": "package_check",
        "status": "passed",
        "action": "create_live",
        "checked_at": now_iso(),
        "generation_mode": DEFAULT_GENERATION_MODE,
        "summary": {"error_count": 0, "warning_count": 0, "runtime_check_count": 0},
        "runtime_checks": [],
        "issues": [],
        "skip_reason": "generation_mode is direct_svg; artboard package runtime is not required",
    }
    check = project_root / "06-check" / "artboard-package-check.json"
    receipt = project_root / "receipts" / "artboard-package-check.json"
    write_json(check, payload)
    write_json(receipt, payload)
    return complete_stage(
        project_root,
        state,
        "package_check",
        "passed",
        started_at=started_at,
        inputs=["02-plan/slide_plan.json"],
        outputs=[
            "06-check/artboard-package-check.json",
            "receipts/artboard-package-check.json",
        ],
        command=[],
    )


def run_package_check_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    mode = plan_generation_mode(project_root)
    if mode == DEFAULT_GENERATION_MODE:
        return write_direct_svg_package_check(project_root, state)
    return run_script_stage(
        project_root,
        state,
        "package_check",
        [
            "python3",
            (SCRIPT_DIR / "svglide_artboard_package_check.py").as_posix(),
            "--repo-root",
            repo_root().as_posix(),
            "--output-dir",
            project_root.as_posix(),
            "--pretty",
        ],
        inputs=["02-plan/slide_plan.json"],
        outputs=[
            "06-check/artboard-package-check.json",
            "receipts/artboard-package-check.json",
        ],
    )


def repair_loop_input_path(project_root: Path) -> Path:
    return project_root / "02-plan" / "repair-loop.input.json"


def repair_loop_failing_receipt(project_root: Path) -> Path:
    request_path = repair_loop_input_path(project_root)
    if request_path.exists():
        payload = read_json(request_path)
        raw = payload.get("failing_receipt")
        if not isinstance(raw, str) or not raw:
            raise RunnerError("repair-loop.input.json must include failing_receipt")
        return project_root / raw
    fallback = project_root / DEFAULT_REPAIR_LOOP_FAILING_RECEIPT
    if fallback.exists():
        return fallback
    raise RunnerError(
        "repair_loop requires a failing receipt; write 02-plan/repair-loop.input.json "
        "with failing_receipt or run the repair-loop command with --failing-receipt"
    )


def run_repair_loop_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    failing_receipt = repair_loop_failing_receipt(project_root)
    command = [
        "python3",
        (SCRIPT_DIR / "svglide_model_repair_loop.py").as_posix(),
        project_root.as_posix(),
        "--failing-receipt",
        failing_receipt.as_posix(),
        "--pretty",
    ]
    inputs = [
        "02-plan/slide_plan.json",
        "02-plan/repair-plan.json",
        project_relpath(failing_receipt, project_root),
    ]
    if repair_loop_input_path(project_root).exists():
        inputs.append("02-plan/repair-loop.input.json")
    return run_script_stage(
        project_root,
        state,
        "repair_loop",
        command,
        output_json=project_root / "receipts" / "repair-loop.json",
        inputs=inputs,
        outputs=["02-plan/slide_plan.json", "receipts/repair-loop.json", "receipts/repair_loop.json"],
    )


def run_theme_productization_stage(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return run_script_stage(
        project_root,
        state,
        "theme_productization",
        ["python3", (SCRIPT_DIR / "svglide_theme_productization.py").as_posix(), project_root.as_posix(), "--pretty"],
        output_json=project_root / "06-check" / "theme-productization.json",
        inputs=["02-plan/theme-productization.input.json", "02-plan/slide_plan.json"],
        outputs=[
            "02-plan/theme-registry.json",
            "02-plan/themes",
            "02-plan/theme-migration.patch.json",
            "06-check/theme-productization.json",
            "receipts/theme-productization.json",
        ],
    )


def run_visual_acceptance_stage(project_root: Path, state: dict[str, Any], *, profile: str) -> dict[str, Any]:
    started_at = now_iso()
    started_perf = time.perf_counter()
    command = [
        "python3",
        (SCRIPT_DIR / "svglide_visual_acceptance.py").as_posix(),
        project_root.as_posix(),
        "--profile",
        profile,
        "--pretty",
    ]
    completed = subprocess.run(command, cwd=repo_root(), check=False, capture_output=True, text=True)
    check_path = project_root / "06-check" / "visual-acceptance.json"
    receipt = project_root / "receipts" / "visual_acceptance.json"
    status = "failed"
    result: dict[str, Any]
    if check_path.exists():
        result = read_json(check_path)
        ended_at = now_iso()
        result["command"] = command
        result["runner_started_at"] = started_at
        result["runner_ended_at"] = ended_at
        result["stdout"] = completed.stdout
        result["stderr"] = completed.stderr
        write_json(check_path, result)
        write_json(receipt, result)
        if completed.returncode == 0 and result.get("status") in {"passed", "skipped"}:
            status = "passed"
    else:
        ended_at = now_iso()
        result = build_receipt(
            "visual_acceptance",
            "failed",
            started_at=started_at,
            ended_at=ended_at,
            command=command,
            error={
                "code": "visual_acceptance_missing_output",
                "returncode": completed.returncode,
                "stderr": completed.stderr,
            },
        )
        write_json(receipt, result)
    record_stage(state, "visual_acceptance", status, receipt)
    issues = issues_from_payload(result)
    record_timing_event(
        state,
        stage="visual_acceptance",
        status=status,
        started_at=started_at,
        ended_at=result.get("runner_ended_at") or result.get("ended_at") or now_iso(),
        wall_time_seconds=time.perf_counter() - started_perf,
        root_cause_group=issue_root_cause(issues[0]) if status != "passed" and issues else None,
    )
    if status != "passed":
        write_failure_summary(
            project_root,
            blocking_stage="visual_acceptance",
            issues=issues,
            message=issues[0].get("message") if issues and isinstance(issues[0].get("message"), str) else "visual_acceptance failed",
            rerun_from="visual_acceptance",
        )
    write_state(project_root, state)
    write_timing_report(project_root, state)
    if status != "passed":
        raise RunnerError(f"stage 'visual_acceptance' failed with exit code {completed.returncode}")
    return {"stage": "visual_acceptance", "status": status, "receipt": project_relpath(receipt, project_root)}


def lark_cli_command_prefix() -> list[str]:
    raw = os.environ.get(LARK_CLI_COMMAND_ENV, "").strip()
    if not raw:
        return ["lark-cli"]
    parsed = shlex.split(raw)
    if not parsed:
        return ["lark-cli"]
    return parsed


def cli_arg_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root()).as_posix()
    except ValueError:
        return path.as_posix()


def project_cli_arg_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def ppe_live_request_headers(project_root: Path) -> list[str]:
    proof = require_ppe_proof_current(project_root)
    proof_payload = proof.get("proof")
    if not isinstance(proof_payload, dict):
        raise RunnerError("PPE proof payload is missing; rerun ppe_proof")
    headers = proof_payload.get("headers")
    if not isinstance(headers, dict):
        raise RunnerError("PPE proof headers are missing; rerun ppe_proof")
    items: list[str] = []
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise RunnerError("PPE proof headers must be string key/value pairs")
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key != "x-tt-env" or normalized_value != "ppe_pure_svg":
            raise RunnerError("PPE proof currently supports only x-tt-env=ppe_pure_svg")
        items.append(f"{normalized_key}={normalized_value}")
    if not items:
        raise RunnerError("PPE proof headers are empty; rerun ppe_proof")
    return sorted(items)


def create_command(project_root: Path, *, dry_run: bool) -> list[str]:
    command = lark_cli_command_prefix() + ["slides", "+create-svg", "--as", "user", "--title", project_title(project_root)]
    assets = project_root / "03-assets" / "assets.json"
    if assets.exists():
        command.extend(["--assets", project_cli_arg_path(project_root, assets)])
    if not dry_run:
        for header in ppe_live_request_headers(project_root):
            command.extend(["--request-header", header])
    for path in prepared_svg_files(project_root):
        command.extend(["--file", project_cli_arg_path(project_root, path)])
    if dry_run:
        command.append("--dry-run")
    return command


def write_command_trace(project_root: Path, command: list[str]) -> None:
    write_text(project_root / "07-create" / "create-command.txt", " ".join(command) + "\n")


def run_create_stage(
    project_root: Path,
    state: dict[str, Any],
    stage: str,
    *,
    dry_run: bool,
    profile: str = "production",
    command_runner=subprocess.run,
) -> dict[str, Any]:
    require_quality_gate_current(project_root)
    started_at = now_iso()
    hashes = prepared_file_hashes(project_root)

    if not dry_run:
        if artboard_visual_acceptance_required(project_root):
            require_stage_passed(state, "visual_acceptance")
        require_visual_acceptance_current(project_root)
        require_stage_passed(state, "ppe_proof")
        require_ppe_proof_current(project_root)
        if profile == "production_live":
            require_stage_passed(state, "pre_submit_review")
            require_pre_submit_review_current(project_root)
        dry_run_record = read_json(project_root / "07-create" / "dry-run.json")
        if dry_run_record.get("prepared_files") != hashes:
            complete_stage(
                project_root,
                state,
                stage,
                "failed",
                started_at=started_at,
                inputs=["07-create/dry-run.json", "04-svg/prepared"],
                outputs=[],
                command=[],
                error={"code": "prepared_hash_mismatch", "message": "prepared SVG files changed after dry-run"},
            )
            raise RunnerError("prepared SVG files changed after dry-run; rerun dry-run before live create")

    command = create_command(project_root, dry_run=dry_run)
    write_command_trace(project_root, command)
    completed = command_runner(command, cwd=project_root, check=False, capture_output=True, text=True)
    record = {
        "version": "svglide-create-stage/v1",
        "stage": stage,
        "status": "passed" if completed.returncode == 0 else "failed",
        "prepared_files": hashes,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parse_json_or_none(completed.stdout),
    }
    output_path = project_root / "07-create" / ("dry-run.json" if dry_run else "live-create.json")
    write_json(output_path, record)
    outputs = ["07-create/create-command.txt", output_path.relative_to(project_root).as_posix()]
    if completed.returncode != 0:
        complete_stage(
            project_root,
            state,
            stage,
            "failed",
            started_at=started_at,
            inputs=["06-check/quality-gate.json", "04-svg/prepared"],
            outputs=outputs,
            command=command,
            error={"code": "create_command_failed", "returncode": completed.returncode, "stderr": completed.stderr},
        )
        raise RunnerError(f"stage '{stage}' failed with exit code {completed.returncode}")
    return complete_stage(
        project_root,
        state,
        stage,
        "passed",
        started_at=started_at,
        inputs=["06-check/quality-gate.json", "04-svg/prepared"],
        outputs=outputs,
        command=command,
    )


def run_implemented_stage(project_root: Path, stage: str, state: dict[str, Any], *, profile: str = "production") -> dict[str, Any]:
    if stage == "init":
        raise RunnerError("init stage must be created with the init command", exit_code=2)
    if stage == "source":
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_source.py").as_posix(), project_root.as_posix(), *source_option_args(), "--pretty"],
            output_json=project_root / "source" / "source-receipt.json",
            inputs=["source/source-notes.md", "source/evidence.json"],
            outputs=[
                "source/evidence.json",
                "source/research_queries.json",
                "source/source-receipt.json",
                "receipts/source.json",
            ],
        )
    if stage == "select_style":
        require_stage_passed(state, "source")
        return run_select_style_stage(project_root, state)
    if stage == "plan":
        return run_plan_stage(project_root, state)
    if stage == "strategy_review":
        require_stage_passed(state, "source")
        require_source_current(project_root)
        require_stage_passed(state, "plan")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_strategy_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "02-plan" / "strategy-review.json",
            inputs=["02-plan/slide_plan.json"],
            outputs=["02-plan/strategy-review.json"],
        )
    if stage == "theme_validate":
        require_stage_passed(state, "strategy_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_theme_validate.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "theme-validate.json",
            inputs=["02-plan/slide_plan.json"],
            outputs=["06-check/theme-validate.json", "receipts/theme-validate.json"],
        )
    if stage == "palette_review":
        require_stage_passed(state, "theme_validate")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_palette_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "palette-review.json",
            inputs=["02-plan/palette-selection.json", "02-plan/slide_plan.json"],
            outputs=["06-check/palette-review.json", "receipts/palette_review.json"],
        )
    if stage == "selection_review":
        require_stage_passed(state, "palette_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_selection_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "theme-template-selection-review.json",
            inputs=["02-plan/theme-template-selection.json", "02-plan/palette-selection.json", "02-plan/slide_plan.json"],
            outputs=["06-check/theme-template-selection-review.json", "receipts/theme_template_selection_review.json"],
        )
    if stage == "plan_bundle_review":
        require_stage_passed(state, "plan")
        require_stage_passed(state, "palette_review")
        require_stage_passed(state, "selection_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_plan_bundle_review.py").as_posix(), project_root.as_posix(), "--profile", profile, "--pretty"],
            output_json=project_root / "06-check" / "plan-bundle-review.json",
            inputs=[
                "00-input/instruction.json",
                "02-plan/slide_plan.json",
                "02-plan/palette-selection.json",
                "02-plan/theme-template-selection.json",
                "source/evidence.json",
            ],
            outputs=["06-check/plan-bundle-review.json", "receipts/plan_bundle_review.json"],
        )
    if stage == "confirm_plan":
        if selection_gate_required(project_root, state):
            require_stage_passed(state, "selection_review")
            require_stage_passed(state, "plan_bundle_review")
        return run_confirm_plan_stage(project_root, state)
    if stage == "package_check":
        return run_package_check_stage(project_root, state)
    if stage == "assets":
        require_stage_passed(state, "package_check")
        require_source_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_assets.py").as_posix(), project_root.as_posix(), *asset_option_args(profile=profile)],
            inputs=["02-plan/slide_plan.json", "02-plan/svglide.lock.json"],
            outputs=["03-assets/assets.json", "03-assets/asset-manifest.json", "03-assets/image-jobs.json", "receipts/assets.json"],
        )
    if stage == "generate_svg":
        return run_generate_svg_stage(project_root, state)
    if stage == "contract_compile":
        require_stage_passed(state, "generate_svg")
        require_generated_svg_current(project_root)
        generation_mode = plan_generation_mode(project_root)
        command = ["python3", (SCRIPT_DIR / "svglide_contract_compile.py").as_posix(), "--project", project_root.as_posix()]
        if generation_mode != "artboard_satori" or not raw_visual_manifest_path(project_root).exists():
            command.append("--allow-existing-svg")
        return run_script_stage(
            project_root,
            state,
            stage,
            command,
            inputs=["04-artboard/raw/manifest.json", "04-svg", "03-assets/assets.json"],
            outputs=["04-svg", "04-svg/contract/manifest.json", "receipts/contract_compile.json"],
        )
    if stage == "prepare":
        require_stage_passed(state, "assets")
        require_stage_passed(state, "generate_svg")
        require_stage_passed(state, "contract_compile")
        require_assets_current(project_root)
        require_contract_compile_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_prepare.py").as_posix(), project_root.as_posix()],
            inputs=["04-svg", "04-svg/contract/manifest.json", "03-assets/assets.json"],
            outputs=["04-svg/prepared", "receipts/prepare.json"],
        )
    if stage == "preview":
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_preview.py").as_posix(), project_root.as_posix()],
            inputs=["04-svg/prepared"],
            outputs=["05-preview/preview.html", "05-preview/preview-manifest.json"],
        )
    if stage == "preflight":
        plan = project_root / "02-plan" / "slide_plan.json"
        output = project_root / "06-check" / "preflight.json"
        command = ["python3", (SCRIPT_DIR / "svg_preflight.py").as_posix(), "--plan", plan.as_posix()]
        for path in prepared_svg_files(project_root):
            command.extend(["--input", path.as_posix()])
        contract_manifest = contract_manifest_path(project_root)
        if contract_manifest.exists():
            command.extend(["--contract-manifest", contract_manifest.as_posix()])
        return run_script_stage(
            project_root,
            state,
            stage,
            command,
            output_json=output,
            inputs=["02-plan/slide_plan.json", "04-svg/prepared"],
            outputs=["06-check/preflight.json"],
        )
    if stage == "preview_lint":
        preview = project_root / "05-preview" / "preview.html"
        output = project_root / "06-check" / "preview-lint.json"
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svg_preview_lint.py").as_posix(), preview.as_posix(), "--pretty"],
            output_json=output,
            inputs=["05-preview/preview.html"],
            outputs=["06-check/preview-lint.json"],
        )
    if stage == "aesthetic_review":
        require_stage_passed(state, "preview_lint")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_aesthetic_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "aesthetic-review.json",
            inputs=["05-preview/preview.html", "05-preview/preview-manifest.json", "06-check/preview-lint.json"],
            outputs=["06-check/aesthetic-review.json"],
        )
    if stage == "chart_verify":
        require_stage_passed(state, "aesthetic_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_chart_verify.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "chart-verify.json",
            inputs=["02-plan/slide_plan.json", "04-svg/prepared"],
            outputs=["06-check/chart-verify.json"],
        )
    if stage == "semantic_review":
        require_stage_passed(state, "chart_verify")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_semantic_review.py").as_posix(), project_root.as_posix(), "--profile", profile, "--pretty"],
            output_json=project_root / "06-check" / "semantic-review.json",
            inputs=["02-plan/slide_plan.json", "source/evidence.json", "04-svg/prepared"],
            outputs=["06-check/semantic-review.json", "06-check/text-inventory.json"],
        )
    if stage == "runtime_review":
        require_stage_passed(state, "semantic_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_runtime_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "runtime-review.json",
            inputs=["02-plan/slide_plan.json"],
            outputs=["06-check/runtime-review.json"],
        )
    if stage == "visual_distinctness_review":
        require_stage_passed(state, "runtime_review")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_visual_distinctness_review.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "visual-distinctness.json",
            inputs=["02-plan/slide_plan.json"],
            outputs=["06-check/visual-distinctness.json"],
        )
    if stage == "theme_adherence":
        require_stage_passed(state, "visual_distinctness_review")
        require_stage_passed(state, "theme_validate")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_theme_adherence.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "06-check" / "theme-adherence.json",
            inputs=["02-plan/slide_plan.json", "06-check/theme-validate.json", "04-svg/prepared"],
            outputs=["06-check/theme-adherence.json", "receipts/theme-adherence.json"],
        )
    if stage == "quality_gate":
        if selection_gate_required(project_root, state):
            require_stage_passed(state, "palette_review")
            require_stage_passed(state, "selection_review")
        require_stage_passed(state, "preflight")
        require_stage_passed(state, "preview_lint")
        require_stage_passed(state, "aesthetic_review")
        require_stage_passed(state, "chart_verify")
        require_stage_passed(state, "semantic_review")
        require_stage_passed(state, "runtime_review")
        require_stage_passed(state, "visual_distinctness_review")
        require_stage_passed(state, "theme_adherence")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_quality_gate.py").as_posix(), project_root.as_posix(), "--profile", profile, "--pretty"],
            inputs=[
                "06-check/preflight.json",
                "06-check/preview-lint.json",
                "06-check/aesthetic-review.json",
                "06-check/chart-verify.json",
                "06-check/semantic-review.json",
                "06-check/runtime-review.json",
                "06-check/visual-distinctness.json",
                "06-check/theme-validate.json",
                "06-check/theme-adherence.json",
                "06-check/palette-review.json",
                "06-check/theme-template-selection-review.json",
                "06-check/plan-bundle-review.json",
                "receipts/generate_svg.json",
            ],
            outputs=["06-check/quality-gate.json"],
        )
    if stage == "generation_benchmark":
        require_stage_passed(state, "quality_gate")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_generation_benchmark.py").as_posix(), project_root.as_posix(), "--profile", profile, "--pretty"],
            output_json=project_root / "06-check" / "generation-benchmark.json",
            inputs=[
                "02-plan/slide_plan.json",
                "03-assets/asset-manifest.json",
                "06-check/quality-gate.json",
                "06-check/timing-report.json",
            ],
            outputs=["06-check/generation-benchmark.json"],
        )
    if stage == "dry_run":
        require_stage_passed(state, "generation_benchmark")
        require_generation_benchmark_current(project_root, profile=profile)
        return run_create_stage(project_root, state, stage, dry_run=True, profile=profile)
    if stage == "visual_acceptance":
        require_stage_passed(state, "dry_run")
        return run_visual_acceptance_stage(project_root, state, profile=profile)
    if stage == "ppe_proof":
        require_stage_passed(state, "dry_run")
        if artboard_visual_acceptance_required(project_root):
            require_stage_passed(state, "visual_acceptance")
        require_visual_acceptance_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_ppe_proof.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "07-create" / "ppe-proof.json",
            inputs=["06-check/quality-gate.json", "07-create/dry-run.json", "07-create/ppe-proof.input.json"],
            outputs=["07-create/ppe-proof.json"],
        )
    if stage == "pre_submit_review":
        require_stage_passed(state, "ppe_proof")
        if artboard_visual_acceptance_required(project_root):
            require_stage_passed(state, "visual_acceptance")
        require_visual_acceptance_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            [
                "python3",
                (SCRIPT_DIR / "svglide_pre_submit_review.py").as_posix(),
                project_root.as_posix(),
                "--human-review",
                (project_root / "06-check" / "pre-submit-human-review.json").as_posix(),
                "--pretty",
            ],
            output_json=project_root / "06-check" / "pre-submit-review.json",
            inputs=[
                "06-check/pre-submit-human-review.json",
                "06-check/quality-gate.json",
                "06-check/theme-adherence.json",
                "06-check/visual-distinctness.json",
                "04-svg/prepared",
            ],
            outputs=["06-check/pre-submit-review.json", "receipts/pre-submit-review.json"],
        )
    if stage == "live_create":
        return run_create_stage(project_root, state, stage, dry_run=False, profile=profile)
    if stage == "readback":
        if artboard_visual_acceptance_required(project_root):
            require_stage_passed(state, "visual_acceptance")
        require_visual_acceptance_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_readback.py").as_posix(), project_root.as_posix(), "--pretty"],
            inputs=["07-create/live-create.json", "02-plan/slide_plan.json"],
            outputs=["08-readback/xml-presentations-get.json", "08-readback/readback-check.json"],
        )
    if stage == "repair_loop":
        return run_repair_loop_stage(project_root, state)
    if stage == "theme_productization":
        return run_theme_productization_stage(project_root, state)
    if stage == "export":
        require_stage_passed(state, "readback")
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_export_package.py").as_posix(), project_root.as_posix(), "--archive", "--pretty"],
            output_json=project_root / "09-export" / "export-manifest.json",
            inputs=[
                "02-plan/slide_plan.json",
                "06-check/quality-gate.json",
                "07-create/live-create.json",
                "08-readback/readback-check.json",
            ],
            outputs=[
                "09-export/export-manifest.json",
                "09-export/svglide-artifacts.zip",
                "receipts/export.json",
            ],
        )
    raise RunnerError(f"stage '{stage}' is not implemented in the P0 runner skeleton")


def run_stage(project_root: Path, stage: str, *, command: list[str] | None = None, profile: str = "production") -> dict[str, Any]:
    normalized = normalize_stage(stage)
    if profile not in QUALITY_GATE_PROFILES:
        raise RunnerError(f"unknown profile '{profile}'", exit_code=2)
    state = load_state(project_root)
    state["profile"] = profile
    stale = svglide_stage_invalidation.detect_stale_stages(project_root, state, target_stage=normalized, stage_order=STAGES, profile=profile)
    if stale:
        svglide_stage_invalidation.prune_stale_stage_records(state, stale)
        write_state(project_root, state)
    record = state.get("stages", {}).get(normalized)
    if record and repair_existing_failed_stage(project_root, state, normalized):
        state = load_state(project_root)
        record = state.get("stages", {}).get(normalized)
    if record:
        fail_if_existing_stage_failed(normalized, record)
        require_existing_stage_current(project_root, normalized, profile=profile)
        write_timing_report(project_root, state)
        return {"stage": normalized, "status": "passed", "state": state}

    if normalized not in IMPLEMENTED_STAGES:
        block_unimplemented_stage(
            project_root,
            normalized,
            state,
            command=command or ["stage", project_root.as_posix(), stage],
        )

    receipt = run_implemented_stage(project_root, normalized, state, profile=profile)
    return {"stage": normalized, "status": receipt["status"], "state": load_state(project_root)}


def collected_failure_from_stage(project_root: Path, stage: str, err: RunnerError) -> dict[str, Any]:
    candidates = [
        project_root / "06-check" / f"{stage.replace('_', '-')}.json",
        receipt_path(project_root, stage),
    ]
    if stage == "selection_review":
        candidates.insert(0, project_root / "06-check/theme-template-selection-review.json")
    if stage == "plan_bundle_review":
        candidates.insert(0, project_root / "06-check/plan-bundle-review.json")
    payload: dict[str, Any] = {}
    for candidate in candidates:
        payload = read_json_optional(candidate)
        if payload:
            break
    issues = issues_from_payload(payload)
    if not issues:
        issues = [{"code": "stage_failed", "message": str(err), "stage": stage, "root_cause_group": "unknown"}]
    return {"stage": stage, "status": "failed", "issues": issues}


def run_until(
    project_root: Path,
    until: str,
    *,
    profile: str = "production",
    progress: str | None = None,
    collect_errors: bool | None = None,
) -> dict[str, Any]:
    if profile not in QUALITY_GATE_PROFILES:
        raise RunnerError(f"unknown profile '{profile}'", exit_code=2)
    target = normalize_stage(until)
    state = load_state(project_root)
    state["profile"] = profile
    stale = svglide_stage_invalidation.detect_stale_stages(project_root, state, target_stage=target, stage_order=STAGES, profile=profile)
    if stale:
        svglide_stage_invalidation.prune_stale_stage_records(state, stale)
        write_state(project_root, state)
    emit_start_progress(project_root, progress=progress)
    collected_failures: list[dict[str, Any]] = []
    should_collect = bool(collect_errors if collect_errors is not None else RUNNER_OPTIONS.get("collect_errors"))
    for stage in stages_until(target):
        if not stage_required_for_profile(stage, profile):
            continue
        if collected_failures and stage not in COLLECTABLE_VALIDATION_STAGES:
            write_collected_errors(project_root, state, collected_failures)
            raise RunnerError("pre-render validation errors collected; render stages were not executed")
        record = state.get("stages", {}).get(stage)
        if record and repair_existing_failed_stage(project_root, state, stage):
            state = load_state(project_root)
            record = state.get("stages", {}).get(stage)
        if record:
            if existing_stage_can_be_retried(record):
                prune_stage_and_descendants(state, stage, target)
                write_state(project_root, state)
                state = load_state(project_root)
                record = None
            else:
                try:
                    fail_if_existing_stage_failed(stage, record)
                    require_existing_stage_current(project_root, stage, profile=profile)
                except RunnerError as err:
                    if should_collect and stage in COLLECTABLE_VALIDATION_STAGES:
                        collected_failures.append(collected_failure_from_stage(project_root, stage, err))
                        continue
                    if is_rerun_required_error(err, stage):
                        prune_stage_and_descendants(state, stage, target)
                        write_state(project_root, state)
                        state = load_state(project_root)
                        record = None
                    else:
                        raise
            if record is None:
                pass
            else:
                continue

        if stage not in IMPLEMENTED_STAGES:
            block_unimplemented_stage(
                project_root,
                stage,
                state,
                command=["run", project_root.as_posix(), "--until", target],
            )
        try:
            run_implemented_stage(project_root, stage, state, profile=profile)
        except RunnerError as err:
            if should_collect and stage in COLLECTABLE_VALIDATION_STAGES:
                if "required stage" in str(err):
                    upstream_stage = str(err).split("'")[1] if "'" in str(err) else None
                    collected_failures.append(
                        {
                            "stage": stage,
                            "status": "skipped",
                            "skip_reason": "upstream_required_output_invalid",
                            "upstream_stage": upstream_stage,
                            "issues": [
                                {
                                    "code": "upstream_required_output_invalid",
                                    "message": str(err),
                                    "stage": stage,
                                    "root_cause_group": "upstream_validation",
                                }
                            ],
                        }
                    )
                else:
                    collected_failures.append(collected_failure_from_stage(project_root, stage, err))
                state = load_state(project_root)
                continue
            raise
        state = load_state(project_root)
        emit_stage_progress(project_root, stage, progress=progress)

    if collected_failures:
        write_collected_errors(project_root, state, collected_failures)
        raise RunnerError("pre-render validation errors collected; render stages were not executed")
    write_timing_report(project_root, state)
    emit_completion_summary(project_root, state, progress=progress)
    return {"project_root": project_root.as_posix(), "until": target, "state": state}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SVGlide project runner skeleton")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser("init", help="create a SVGlide project directory")
    init.add_argument("--deck-id", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--plan-root", type=Path, default=DEFAULT_PLAN_ROOT)
    init.add_argument("--force", action="store_true")

    stage = subcommands.add_parser("stage", help="run one stage")
    stage.add_argument("project_root", type=Path)
    stage.add_argument("stage")
    stage.add_argument("--profile", default="production", choices=sorted(QUALITY_GATE_PROFILES))
    stage.add_argument("--collect-errors", action="store_true")
    stage.add_argument("--auto-repair", action="store_true")
    add_network_args(stage)

    run = subcommands.add_parser("run", help="run until a stage")
    run.add_argument("project_root", type=Path)
    run.add_argument("--until")
    run.add_argument("--profile", choices=sorted(PROFILE_TARGETS))
    run.add_argument("--progress", default="none", choices=sorted(PROGRESS_MODES))
    run.add_argument("--collect-errors", action="store_true")
    run.add_argument("--auto-repair", action="store_true")
    add_network_args(run)

    for command_name in ["prompt-plan", "model-plan"]:
        prompt_plan = subcommands.add_parser(command_name, help="generate source and plan artifacts from a raw prompt")
        prompt_plan.add_argument("project_root", type=Path)
        prompt_plan.add_argument("--prompt", required=True)
        prompt_plan.add_argument("--target-slide-count", type=int, default=10)
        prompt_plan.add_argument("--language", default="zh-CN")
        prompt_plan.add_argument("--audience", default="投资/战略分析读者")
        prompt_plan.add_argument("--provider", default="codex", choices=["codex", "claude", "command"])
        prompt_plan.add_argument("--planner-command")
        prompt_plan.add_argument("--trusted-provider-id")
        prompt_plan.add_argument("--no-search", action="store_true")
        prompt_plan.add_argument("--timeout", type=int, default=300)
        prompt_plan.add_argument("--force", action="store_true")

    repair_loop = subcommands.add_parser("repair-loop", help="apply a scoped repair-plan JSON Patch to slide_plan.json")
    repair_loop.add_argument("project_root", type=Path)
    repair_loop.add_argument("--failing-receipt", type=Path, required=True)
    repair_loop.add_argument("--repair-plan", type=Path, default=Path("02-plan/repair-plan.json"))
    repair_loop.add_argument("--plan", type=Path, default=Path("02-plan/slide_plan.json"))

    theme_productize = subcommands.add_parser("theme-productize", help="extract a project theme and migrate a slide plan to it")
    theme_productize.add_argument("project_root", type=Path)
    theme_productize.add_argument("--input", type=Path, default=Path("02-plan/theme-productization.input.json"))

    return parser


def add_network_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--no-online-research", action="store_true")
    parser.add_argument("--no-image-search", action="store_true")
    parser.add_argument("--no-ai-image", action="store_true")
    parser.add_argument("--refresh-online", action="store_true")
    parser.add_argument("--network-policy", default="auto", choices=["auto", "online", "offline", "fixture"])
    parser.add_argument("--asset-provider", default="auto")
    parser.add_argument("--image-backend", default="auto", choices=["auto", "openai", "gemini", "qwen", "flux", "stage_command", "none"])


def apply_cli_runner_options(args: argparse.Namespace) -> None:
    for key in RUNNER_OPTIONS:
        if hasattr(args, key):
            RUNNER_OPTIONS[key] = getattr(args, key)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    saved_runner_options = dict(RUNNER_OPTIONS)
    try:
        apply_cli_runner_options(args)
        if args.command == "init":
            result = init_project(args.deck_id, args.title, plan_root=args.plan_root, force=args.force)
        elif args.command in {"prompt-plan", "model-plan"}:
            import svglide_prompt_planner

            result = svglide_prompt_planner.run_prompt_plan(
                args.project_root,
                prompt=args.prompt,
                target_slide_count=args.target_slide_count,
                language=args.language,
                audience=args.audience,
                provider=args.provider,
                planner_command=args.planner_command,
                trusted_provider_id=args.trusted_provider_id,
                search=not args.no_search,
                timeout=args.timeout,
                force=args.force,
            )
        elif args.command == "repair-loop":
            import svglide_model_repair_loop

            try:
                result = svglide_model_repair_loop.run_repair_loop(
                    args.project_root,
                    failing_receipt=args.failing_receipt,
                    repair_plan=args.repair_plan,
                    plan=args.plan,
                )
            except svglide_model_repair_loop.RepairLoopError as err:
                raise RunnerError(str(err)) from err
        elif args.command == "theme-productize":
            import svglide_theme_productization

            try:
                result = svglide_theme_productization.run_theme_productization(args.project_root, input_path=args.input)
            except (svglide_theme_productization.ThemeProductizationError, OSError, json.JSONDecodeError) as err:
                raise RunnerError(str(err)) from err
        elif args.command == "stage":
            result = run_stage(args.project_root, args.stage, profile=args.profile)
        elif args.command == "run":
            result = run_until(
                args.project_root,
                resolve_run_target(args.until, args.profile),
                profile=args.profile or "production",
                progress=args.progress,
                collect_errors=args.collect_errors,
            )
        else:
            parser.error(f"unsupported command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RunnerError as err:
        progress = getattr(args, "progress", "none") if "args" in locals() else "none"
        emitted_progress_block = False
        if "args" in locals() and getattr(args, "command", None) == "run" and hasattr(args, "project_root"):
            emit_blocked_progress(args.project_root, str(err), progress=progress)
            emitted_progress_block = progress_mode_enabled(progress)
        if not emitted_progress_block:
            print(str(err), file=sys.stderr)
        return err.exit_code
    finally:
        RUNNER_OPTIONS.update(saved_runner_options)


if __name__ == "__main__":
    sys.exit(main())
