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
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_asset_injector
import svglide_schema


RUNNER_VERSION = "svglide-project-runner/v0"
PROJECT_VERSION = "svglide-project/v1"
STATE_VERSION = "svglide-state/v1"
STAGE_GRAPH = "svglide-workflow/v1"
ROUTE = "svglide-svg"
DEFAULT_GENERATION_MODE = "direct_svg"
GENERATION_MODES = {DEFAULT_GENERATION_MODE, "artboard_satori"}
DEFAULT_PLAN_ROOT = Path(".lark-slides/plan")
SCRIPT_DIR = Path(__file__).resolve().parent
LARK_CLI_COMMAND_ENV = "SVGLIDE_LARK_CLI_CMD"

STAGES = [
    "init",
    "source",
    "plan",
    "strategy_review",
    "theme_validate",
    "confirm_plan",
    "package_check",
    "assets",
    "generate_svg",
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
    "dry_run",
    "ppe_proof",
    "pre_submit_review",
    "live_create",
    "readback",
    "export",
]

STAGE_ALIASES = {
    "confirm-plan": "confirm_plan",
    "source-review": "source",
    "strategy-review": "strategy_review",
    "theme-validate": "theme_validate",
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
    "ppe-proof": "ppe_proof",
    "pre-submit-review": "pre_submit_review",
    "pre-submit": "pre_submit_review",
    "live-create": "live_create",
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
    "plan",
    "strategy_review",
    "theme_validate",
    "confirm_plan",
    "package_check",
    "assets",
    "generate_svg",
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
    "dry_run",
    "ppe_proof",
    "pre_submit_review",
    "live_create",
    "readback",
}
FAILURE_STATUSES = {"blocked", "failed", "skipped"}
DECK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PROFILE_TARGETS = {
    "preview_only": "quality_gate",
    "production_live": "readback",
}
QUALITY_GATE_PROFILES = {"preview_only", "production_live", "production", "debug"}
RUNNER_OPTIONS = {
    "network_policy": "auto",
    "offline": False,
    "no_online_research": False,
    "no_image_search": False,
    "no_ai_image": False,
    "refresh_online": False,
    "asset_provider": "auto",
    "image_backend": "auto",
}


class RunnerError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def normalize_stage(stage: str) -> str:
    candidate = STAGE_ALIASES.get(stage, stage.replace("-", "_"))
    if candidate not in STAGES:
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


def asset_option_args() -> list[str]:
    args = [
        "--network-policy",
        effective_network_policy(),
        "--asset-provider",
        str(RUNNER_OPTIONS.get("asset_provider") or "auto"),
        "--image-backend",
        str(RUNNER_OPTIONS.get("image_backend") or "auto"),
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
    raise RunnerError("--until is required unless --profile is preview_only or production_live", exit_code=2)


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


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise RunnerError(f"missing required file: {path}") from err


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
        "stage": stage,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at or now_iso(),
        "inputs": inputs or [],
        "outputs": outputs or [],
        "command": command or [],
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
    path = receipt_path(project_root, stage)
    write_json(path, receipt)
    record_stage(state, stage, status, path)
    write_state(project_root, state)
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
    completed = command_runner(command, cwd=repo_root(), check=False, capture_output=True, text=True)
    if output_json is not None:
        write_text(output_json, completed.stdout if completed.stdout.endswith("\n") else completed.stdout + "\n")
    if completed.returncode != 0:
        complete_stage(
            project_root,
            state,
            stage,
            "failed",
            started_at=started_at,
            inputs=inputs,
            outputs=outputs,
            command=command,
            error={
                "code": "stage_command_failed",
                "returncode": completed.returncode,
                "stderr": completed.stderr,
            },
        )
        raise RunnerError(f"stage '{stage}' failed with exit code {completed.returncode}")
    return complete_stage(
        project_root,
        state,
        stage,
        "passed",
        started_at=started_at,
        inputs=inputs,
        outputs=outputs,
        command=command,
    )


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
        visual_identity_added = ensure_visual_identity(payload)
        if visual_identity_added:
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
    receipt["summary"] = {"error_count": len(schema_issues)}
    receipt["issues"] = schema_issues
    write_json(receipt_path(project_root, "plan"), receipt)
    if schema_issues:
        raise RunnerError("plan schema validation failed")
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
            "plan confirmation required before SVG generation; review 02-plan/plan-confirmation.request.json "
            "and write 02-plan/plan-confirmation.json"
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
    root = project_root / "04-svg" / "artboard"
    if not root.exists():
        return []
    return [path.relative_to(project_root).as_posix() for path in sorted(root.glob("page-*.receipt.json")) if path.is_file()]


def refresh_artboard_receipts_after_asset_injection(project_root: Path, generated_files: list[dict[str, str]]) -> None:
    final_hashes = {
        item.get("path"): item.get("sha256")
        for item in generated_files
        if isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str)
    }
    if not final_hashes:
        return

    for receipt_rel in artboard_receipt_paths(project_root):
        receipt_file = project_root / receipt_rel
        payload = read_json(receipt_file)
        svglide_svg = payload.get("svglide_svg")
        final_hash = final_hashes.get(svglide_svg)
        if isinstance(final_hash, str) and payload.get("svglide_svg_sha256") != final_hash:
            payload["svglide_svg_sha256"] = final_hash
            payload["post_asset_injection_refreshed_at"] = now_iso()
            write_json(receipt_file, payload)

    satori_bridge_file = project_root / "receipts" / "satori-bridge.json"
    if not satori_bridge_file.exists():
        return
    satori_bridge = read_json(satori_bridge_file)
    pages = satori_bridge.get("pages")
    changed = False
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            svglide_svg = page.get("svglide_svg")
            final_hash = final_hashes.get(svglide_svg)
            if isinstance(final_hash, str) and page.get("svglide_svg_sha256") != final_hash:
                page["svglide_svg_sha256"] = final_hash
                changed = True
    if changed:
        satori_bridge["post_asset_injection_refreshed_at"] = now_iso()
        write_json(satori_bridge_file, satori_bridge)


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
    require_stage_passed(state, "confirm_plan")
    require_stage_passed(state, "assets")
    validate_plan_confirmation(project_root)
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
        source_file_hashes(project_root)
    except RunnerError as err:
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
                "code": "generated_svg_missing",
                "message": "generate_svg produced no source SVG files under 04-svg",
            },
        )
        raise RunnerError("generate_svg produced no source SVG files under 04-svg") from err

    asset_injection_summary = svglide_asset_injector.inject_project_assets(project_root)
    generated_files = source_file_hashes(project_root)
    if generation_mode == "artboard_satori":
        refresh_artboard_receipts_after_asset_injection(project_root, generated_files)
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
    if isinstance(generated, list) and generated and generated != source_file_hashes(project_root):
        raise RunnerError("source SVG files changed after generate_svg; rerun generate_svg before prepare")
    expected = {
        "plan_sha256": optional_project_file_hash(project_root, "02-plan/slide_plan.json"),
        "evidence_sha256": optional_project_file_hash(project_root, "source/evidence.json"),
        "asset_manifest_sha256": optional_project_file_hash(project_root, "03-assets/asset-manifest.json"),
        "source_receipt_sha256": optional_project_file_hash(project_root, "source/source-receipt.json"),
    }
    for key, current in expected.items():
        if receipt.get(key) != current:
            raise RunnerError(f"generate_svg receipt {key} does not match current project files; rerun generate_svg")
    if receipt.get("generation_mode") == "artboard_satori":
        artboard_receipts = receipt.get("artboard_receipts")
        if not isinstance(artboard_receipts, list) or not artboard_receipts:
            raise RunnerError("generate_svg receipt is missing artboard_receipts; rerun generate_svg")
        for item in artboard_receipts:
            if not isinstance(item, str) or not (project_root / item).exists():
                raise RunnerError(f"artboard receipt is missing: {item}; rerun generate_svg")
    command = receipt.get("command")
    if isinstance(command, list) and len(command) > 1 and isinstance(command[1], str):
        script = Path(command[1])
        if script.exists() and receipt.get("generator_script_sha256") != file_sha256(script):
            raise RunnerError("generator script changed after generate_svg; rerun generate_svg")


def require_existing_stage_current(project_root: Path, stage: str, *, profile: str = "production") -> None:
    if stage == "source":
        require_source_current(project_root)
    elif stage == "assets":
        require_source_current(project_root)
        require_assets_current(project_root)
    elif stage == "generate_svg":
        require_source_current(project_root)
        require_assets_current(project_root)
        require_generated_svg_current(project_root)
    elif stage == "prepare":
        require_generated_svg_current(project_root)
    elif stage == "quality_gate":
        require_quality_gate_current(project_root)
    elif stage == "dry_run":
        require_quality_gate_current(project_root)
    elif stage == "live_create":
        require_quality_gate_current(project_root)
        require_ppe_proof_current(project_root)
        if profile == "production_live":
            require_pre_submit_review_current(project_root)
    elif stage == "ppe_proof":
        require_ppe_proof_current(project_root)
    elif stage == "pre_submit_review":
        require_pre_submit_review_current(project_root)
    elif stage == "readback":
        require_quality_gate_current(project_root)


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
    if inputs.get("generation_mode") == "artboard_satori":
        if inputs.get("artboard_package_check") != "06-check/artboard-package-check.json":
            raise RunnerError("quality gate is missing artboard_package_check input; rerun package_check and quality_gate")
        if "artboard-package-check" not in check_names:
            raise RunnerError("quality gate is missing artboard-package-check check; rerun quality_gate")
        if input_hashes.get("artboard_package_check") != optional_project_file_hash(project_root, "06-check/artboard-package-check.json"):
            raise RunnerError("quality gate artboard_package_check hash is stale; rerun quality_gate")
    return gate


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
    require_stage_passed(state, "confirm_plan")
    validate_plan_confirmation(project_root)
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
        command.extend(["--assets", cli_arg_path(assets)])
    if not dry_run:
        for header in ppe_live_request_headers(project_root):
            command.extend(["--request-header", header])
    for path in prepared_svg_files(project_root):
        command.extend(["--file", cli_arg_path(path)])
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
    require_stage_passed(state, "confirm_plan")
    validate_plan_confirmation(project_root)
    require_quality_gate_current(project_root)
    started_at = now_iso()
    hashes = prepared_file_hashes(project_root)

    if not dry_run:
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
    completed = command_runner(command, cwd=repo_root(), check=False, capture_output=True, text=True)
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
                "source/research.md",
                "source/research_queries.json",
                "source/source-receipt.json",
                "receipts/source.json",
            ],
        )
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
    if stage == "confirm_plan":
        return run_confirm_plan_stage(project_root, state)
    if stage == "package_check":
        return run_package_check_stage(project_root, state)
    if stage == "assets":
        require_stage_passed(state, "confirm_plan")
        require_stage_passed(state, "package_check")
        validate_plan_confirmation(project_root)
        require_source_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_assets.py").as_posix(), project_root.as_posix(), *asset_option_args()],
            inputs=["02-plan/slide_plan.json", "02-plan/svglide.lock.json"],
            outputs=["03-assets/assets.json", "03-assets/asset-manifest.json", "03-assets/image-jobs.json", "receipts/assets.json"],
        )
    if stage == "generate_svg":
        return run_generate_svg_stage(project_root, state)
    if stage == "prepare":
        require_stage_passed(state, "confirm_plan")
        require_stage_passed(state, "assets")
        require_stage_passed(state, "generate_svg")
        validate_plan_confirmation(project_root)
        require_assets_current(project_root)
        require_generated_svg_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_prepare.py").as_posix(), project_root.as_posix()],
            inputs=["04-svg", "03-assets/assets.json"],
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
                "receipts/generate_svg.json",
            ],
            outputs=["06-check/quality-gate.json"],
        )
    if stage == "dry_run":
        return run_create_stage(project_root, state, stage, dry_run=True, profile=profile)
    if stage == "ppe_proof":
        require_stage_passed(state, "dry_run")
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
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_readback.py").as_posix(), project_root.as_posix(), "--pretty"],
            inputs=["07-create/live-create.json", "02-plan/slide_plan.json"],
            outputs=["08-readback/xml-presentations-get.json", "08-readback/readback-check.json"],
        )
    raise RunnerError(f"stage '{stage}' is not implemented in the P0 runner skeleton")


def run_stage(project_root: Path, stage: str, *, command: list[str] | None = None, profile: str = "production") -> dict[str, Any]:
    normalized = normalize_stage(stage)
    if profile not in QUALITY_GATE_PROFILES:
        raise RunnerError(f"unknown profile '{profile}'", exit_code=2)
    state = load_state(project_root)
    record = state.get("stages", {}).get(normalized)
    if record:
        fail_if_existing_stage_failed(normalized, record)
        require_existing_stage_current(project_root, normalized, profile=profile)
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


def run_until(project_root: Path, until: str, *, profile: str = "production") -> dict[str, Any]:
    if profile not in QUALITY_GATE_PROFILES:
        raise RunnerError(f"unknown profile '{profile}'", exit_code=2)
    target = normalize_stage(until)
    state = load_state(project_root)
    for stage in stages_until(target):
        if not stage_required_for_profile(stage, profile):
            continue
        record = state.get("stages", {}).get(stage)
        if record:
            fail_if_existing_stage_failed(stage, record)
            require_existing_stage_current(project_root, stage, profile=profile)
            continue

        if stage not in IMPLEMENTED_STAGES:
            block_unimplemented_stage(
                project_root,
                stage,
                state,
                command=["run", project_root.as_posix(), "--until", target],
            )
        run_implemented_stage(project_root, stage, state, profile=profile)
        state = load_state(project_root)

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
    add_network_args(stage)

    run = subcommands.add_parser("run", help="run until a stage")
    run.add_argument("project_root", type=Path)
    run.add_argument("--until")
    run.add_argument("--profile", choices=sorted(PROFILE_TARGETS))
    add_network_args(run)

    prompt_plan = subcommands.add_parser("prompt-plan", help="generate source and plan artifacts from a raw prompt")
    prompt_plan.add_argument("project_root", type=Path)
    prompt_plan.add_argument("--prompt", required=True)
    prompt_plan.add_argument("--target-slide-count", type=int, default=8)
    prompt_plan.add_argument("--language", default="zh-CN")
    prompt_plan.add_argument("--audience", default="投资/战略分析读者")
    prompt_plan.add_argument("--provider", default="codex", choices=["codex", "claude", "command"])
    prompt_plan.add_argument("--planner-command")
    prompt_plan.add_argument("--no-search", action="store_true")
    prompt_plan.add_argument("--timeout", type=int, default=300)
    prompt_plan.add_argument("--force", action="store_true")

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
    try:
        apply_cli_runner_options(args)
        if args.command == "init":
            result = init_project(args.deck_id, args.title, plan_root=args.plan_root, force=args.force)
        elif args.command == "prompt-plan":
            import svglide_prompt_planner

            result = svglide_prompt_planner.run_prompt_plan(
                args.project_root,
                prompt=args.prompt,
                target_slide_count=args.target_slide_count,
                language=args.language,
                audience=args.audience,
                provider=args.provider,
                planner_command=args.planner_command,
                search=not args.no_search,
                timeout=args.timeout,
                force=args.force,
            )
        elif args.command == "stage":
            result = run_stage(args.project_root, args.stage, profile=args.profile)
        elif args.command == "run":
            result = run_until(args.project_root, resolve_run_target(args.until, args.profile), profile=args.profile or "production")
        else:
            parser.error(f"unsupported command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except RunnerError as err:
        print(str(err), file=sys.stderr)
        return err.exit_code


if __name__ == "__main__":
    sys.exit(main())
