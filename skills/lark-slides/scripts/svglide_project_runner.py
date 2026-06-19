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

import svglide_schema


RUNNER_VERSION = "svglide-project-runner/v0"
PROJECT_VERSION = "svglide-project/v1"
STATE_VERSION = "svglide-state/v1"
STAGE_GRAPH = "svglide-workflow/v1"
ROUTE = "svglide-svg"
DEFAULT_PLAN_ROOT = Path(".lark-slides/plan")
SCRIPT_DIR = Path(__file__).resolve().parent
LARK_CLI_COMMAND_ENV = "SVGLIDE_LARK_CLI_CMD"

STAGES = [
    "init",
    "source",
    "plan",
    "strategy_review",
    "confirm_plan",
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
    "quality_gate",
    "dry_run",
    "ppe_proof",
    "live_create",
    "readback",
    "export",
]

STAGE_ALIASES = {
    "confirm-plan": "confirm_plan",
    "source-review": "source",
    "strategy-review": "strategy_review",
    "aesthetic-review": "aesthetic_review",
    "chart-verify": "chart_verify",
    "semantic-review": "semantic_review",
    "runtime-review": "runtime_review",
    "generate": "generate_svg",
    "generate-svg": "generate_svg",
    "preview-lint": "preview_lint",
    "quality-gate": "quality_gate",
    "dry-run": "dry_run",
    "ppe-proof": "ppe_proof",
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
    "confirm_plan",
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
    "quality_gate",
    "dry_run",
    "ppe_proof",
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
) -> list[str]:
    receipt_paths: list[str] = []
    plan_hash = optional_project_file_hash(project_root, "02-plan/slide_plan.json")
    evidence_hash = optional_project_file_hash(project_root, "source/evidence.json")
    lock_hash = optional_project_file_hash(project_root, "02-plan/svglide.lock.json")
    asset_manifest_hash = optional_project_file_hash(project_root, "03-assets/asset-manifest.json")
    generator_script_hash = file_sha256(Path(command[1])) if len(command) > 1 and Path(command[1]).exists() else None
    for index, item in enumerate(generated_files, 1):
        svg_path = project_root / item["path"]
        page_receipt = svg_path.with_suffix(".receipt.json")
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
            "generator_script_sha256": generator_script_hash,
            "visible_text_policy": "visible SVG text must be traceable to slide_plan.json or source/evidence.json",
            "generated_at": now_iso(),
        }
        write_json(page_receipt, payload)
        receipt_paths.append(page_receipt.relative_to(project_root).as_posix())
    return receipt_paths


def validate_generator_receipt(project_root: Path, receipt: dict[str, Any]) -> list[dict[str, str]]:
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-generator-receipt.schema.json"))
    issues = svglide_schema.validate_json_schema(receipt, schema)
    generated = receipt.get("generated_files")
    page_receipts = receipt.get("page_receipts")
    if isinstance(generated, list) and isinstance(page_receipts, list) and len(generated) != len(page_receipts):
        issues.append({"code": "generator_page_receipt_count_mismatch", "path": "$.page_receipts", "message": "page_receipts count must match generated_files"})
    plan = read_json(plan_path(project_root))
    slides = plan.get("slides")
    if isinstance(slides, list) and isinstance(generated, list) and len(slides) != len(generated):
        issues.append({"code": "generator_slide_count_mismatch", "path": "$.generated_files", "message": "generated SVG count must match slide_plan.slides"})
    if isinstance(page_receipts, list):
        for item in page_receipts:
            if not isinstance(item, str) or not (project_root / item).exists():
                issues.append({"code": "generator_page_receipt_missing", "path": "$.page_receipts", "message": f"missing page receipt: {item}"})
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
    command = svg_generator_command(project_root)
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

    try:
        generated_files = source_file_hashes(project_root)
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

    generator_mode = "script" if command else "external"
    page_receipts = write_page_generation_receipts(project_root, generated_files, generator_mode, command)
    receipt = complete_stage(
        project_root,
        state,
        "generate_svg",
        "passed",
        started_at=started_at,
        inputs=["02-plan/slide_plan.json", "03-assets/assets.json"],
        outputs=[item["path"] for item in generated_files] + page_receipts,
        command=command,
    )
    receipt["generator_mode"] = generator_mode
    receipt["generated_files"] = generated_files
    receipt["page_receipts"] = page_receipts
    receipt["plan_sha256"] = optional_project_file_hash(project_root, "02-plan/slide_plan.json")
    receipt["evidence_sha256"] = optional_project_file_hash(project_root, "source/evidence.json")
    receipt["lock_sha256"] = optional_project_file_hash(project_root, "02-plan/svglide.lock.json")
    receipt["asset_manifest_sha256"] = optional_project_file_hash(project_root, "03-assets/asset-manifest.json")
    receipt["source_receipt_sha256"] = optional_project_file_hash(project_root, "source/source-receipt.json")
    receipt["generator_script_sha256"] = file_sha256(Path(command[1])) if len(command) > 1 and Path(command[1]).exists() else None
    receipt["visible_text_policy"] = "visible SVG text must be traceable to slide_plan.json or source/evidence.json"
    schema_issues = validate_generator_receipt(project_root, receipt)
    if schema_issues:
        receipt["status"] = "failed"
        receipt["error"] = {"code": "generator_receipt_invalid", "issues": schema_issues}
        write_json(receipt_path(project_root, "generate_svg"), receipt)
        record_stage(state, "generate_svg", "failed", receipt_path(project_root, "generate_svg"))
        write_state(project_root, state)
        raise RunnerError("generate_svg receipt validation failed")
    write_json(receipt_path(project_root, "generate_svg"), receipt)
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
    command = receipt.get("command")
    if isinstance(command, list) and len(command) > 1 and isinstance(command[1], str):
        script = Path(command[1])
        if script.exists() and receipt.get("generator_script_sha256") != file_sha256(script):
            raise RunnerError("generator script changed after generate_svg; rerun generate_svg")


def require_existing_stage_current(project_root: Path, stage: str) -> None:
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
    elif stage == "dry_run":
        require_quality_gate_passed(project_root)
    elif stage == "live_create":
        require_quality_gate_passed(project_root)
        require_ppe_proof_current(project_root)
    elif stage == "ppe_proof":
        require_ppe_proof_current(project_root)
    elif stage == "readback":
        require_quality_gate_passed(project_root)


def require_quality_gate_passed(project_root: Path) -> dict[str, Any]:
    gate = read_json(project_root / "06-check" / "quality-gate.json")
    if gate.get("status") != "passed":
        raise RunnerError("quality gate must be passed before create stages")
    gate_hashes = gate.get("prepared_files")
    if isinstance(gate_hashes, list) and gate_hashes and gate_hashes != prepared_file_hashes(project_root):
        raise RunnerError("prepared SVG files changed after quality gate; rerun checks before create")
    return gate


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


def create_command(project_root: Path, *, dry_run: bool) -> list[str]:
    command = lark_cli_command_prefix() + ["slides", "+create-svg", "--as", "user", "--title", project_title(project_root)]
    assets = project_root / "03-assets" / "assets.json"
    if assets.exists():
        command.extend(["--assets", cli_arg_path(assets)])
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
    command_runner=subprocess.run,
) -> dict[str, Any]:
    require_stage_passed(state, "confirm_plan")
    validate_plan_confirmation(project_root)
    require_quality_gate_passed(project_root)
    started_at = now_iso()
    hashes = prepared_file_hashes(project_root)

    if not dry_run:
        require_stage_passed(state, "ppe_proof")
        require_ppe_proof_current(project_root)
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
            ["python3", (SCRIPT_DIR / "svglide_source.py").as_posix(), project_root.as_posix(), "--pretty"],
            output_json=project_root / "source" / "source-receipt.json",
            inputs=["source/source-notes.md", "source/evidence.json"],
            outputs=["source/evidence.json", "source/source-receipt.json", "receipts/source.json"],
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
    if stage == "confirm_plan":
        return run_confirm_plan_stage(project_root, state)
    if stage == "assets":
        require_stage_passed(state, "confirm_plan")
        validate_plan_confirmation(project_root)
        require_source_current(project_root)
        return run_script_stage(
            project_root,
            state,
            stage,
            ["python3", (SCRIPT_DIR / "svglide_assets.py").as_posix(), project_root.as_posix()],
            inputs=["02-plan/slide_plan.json", "02-plan/svglide.lock.json"],
            outputs=["03-assets/assets.json", "03-assets/asset-manifest.json", "receipts/assets.json"],
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
    if stage == "quality_gate":
        require_stage_passed(state, "preflight")
        require_stage_passed(state, "preview_lint")
        require_stage_passed(state, "aesthetic_review")
        require_stage_passed(state, "chart_verify")
        require_stage_passed(state, "semantic_review")
        require_stage_passed(state, "runtime_review")
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
                "receipts/generate_svg.json",
            ],
            outputs=["06-check/quality-gate.json"],
        )
    if stage == "dry_run":
        return run_create_stage(project_root, state, stage, dry_run=True)
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
    if stage == "live_create":
        return run_create_stage(project_root, state, stage, dry_run=False)
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
        require_existing_stage_current(project_root, normalized)
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
        record = state.get("stages", {}).get(stage)
        if record:
            fail_if_existing_stage_failed(stage, record)
            require_existing_stage_current(project_root, stage)
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

    run = subcommands.add_parser("run", help="run until a stage")
    run.add_argument("project_root", type=Path)
    run.add_argument("--until")
    run.add_argument("--profile", choices=sorted(PROFILE_TARGETS))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_project(args.deck_id, args.title, plan_root=args.plan_root, force=args.force)
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
