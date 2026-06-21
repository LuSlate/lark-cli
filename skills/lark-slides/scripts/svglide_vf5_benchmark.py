#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_CASES = [
    {
        "id": "spacex-ipo-analysis",
        "title": "SpaceX IPO Analysis",
        "prompt": "spacex IPO 分析",
        "audience": "投资/战略分析读者",
    },
    {
        "id": "iceland-volcano-research",
        "title": "Iceland Volcano Research",
        "prompt": "冰岛火山研究",
        "audience": "地理/科学研究读者",
    },
    {
        "id": "new-zealand-landscape",
        "title": "New Zealand Landscape",
        "prompt": "新西兰风光",
        "audience": "旅行内容策划读者",
    },
]
REAL_PLANNER_PROVIDERS = {"codex", "claude"}
IMAGE_BACKENDS = {"auto", "openai", "gemini", "qwen", "flux", "stage_command", "none"}
NETWORK_POLICIES = {"auto", "online", "offline", "fixture"}


class BenchmarkError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    raw = value.strip().lower()
    safe = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return safe or "case"


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def command_record(command: list[str], completed: subprocess.CompletedProcess[str], *, started_at: str, ended_at: str) -> dict[str, Any]:
    return {
        "command": command,
        "started_at": started_at,
        "ended_at": ended_at,
        "returncode": completed.returncode,
        "stdout_tail": (completed.stdout or "")[-4000:],
        "stderr_tail": (completed.stderr or "")[-4000:],
    }


def run_command(command: list[str], *, cwd: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    started_at = now_iso()
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    ended_at = now_iso()
    return completed, command_record(command, completed, started_at=started_at, ended_at=ended_at)


def parse_init_project_root(stdout: str) -> Path:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise BenchmarkError(f"init did not return JSON: {error}") from error
    project_root = payload.get("project_root") if isinstance(payload, dict) else None
    if not isinstance(project_root, str) or not project_root:
        raise BenchmarkError("init output is missing project_root")
    return Path(project_root)


def selected_cases(case_ids: list[str] | None) -> list[dict[str, str]]:
    cases = [{key: str(value) for key, value in item.items()} for item in DEFAULT_CASES]
    if not case_ids:
        return cases
    requested = set(case_ids)
    selected = [case for case in cases if case["id"] in requested]
    missing = sorted(requested - {case["id"] for case in selected})
    if missing:
        raise BenchmarkError(f"unknown benchmark case id(s): {missing}")
    return selected


def assert_real_mode(args: argparse.Namespace) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if args.fixture_mode:
        return issues
    if args.planner_provider not in REAL_PLANNER_PROVIDERS:
        issues.append({"code": "planner_provider_not_real", "message": "real VF5 runs must use codex or claude planner provider"})
    if args.network_policy in {"offline", "fixture"}:
        issues.append({"code": "asset_network_not_real", "message": "real VF5 runs must use auto or online network policy"})
    if args.no_image_search:
        issues.append({"code": "image_search_disabled", "message": "real VF5 runs must not disable image search"})
    if args.no_ai_image:
        issues.append({"code": "ai_image_disabled", "message": "real VF5 runs must not disable AI image planning"})
    if args.image_backend == "none":
        issues.append({"code": "image_backend_none", "message": "real VF5 runs must not use image-backend none"})
    return issues


def command_project_runner(args: argparse.Namespace) -> Path:
    path = Path(args.project_runner) if args.project_runner else SCRIPT_DIR / "svglide_project_runner.py"
    if not path.exists():
        raise BenchmarkError(f"project runner not found: {path}")
    return path


def planner_command_args(args: argparse.Namespace) -> list[str]:
    values = [
        "--provider",
        args.planner_provider,
        "--target-slide-count",
        str(args.target_slide_count),
        "--language",
        args.language,
        "--timeout",
        str(args.timeout),
        "--force",
    ]
    if args.planner_command:
        values.extend(["--planner-command", args.planner_command])
    if args.no_search:
        values.append("--no-search")
    return values


def run_args(args: argparse.Namespace) -> list[str]:
    values = [
        "--network-policy",
        args.network_policy,
        "--asset-provider",
        args.asset_provider,
        "--image-backend",
        args.image_backend,
    ]
    if args.no_image_search:
        values.append("--no-image-search")
    if args.no_ai_image:
        values.append("--no-ai-image")
    if args.no_online_research:
        values.append("--no-online-research")
    if args.refresh_online:
        values.append("--refresh-online")
    return values


def asset_summary(project_root: Path) -> dict[str, Any]:
    manifest = read_json(project_root / "03-assets/asset-manifest.json") or {}
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    acquired_assets = manifest.get("acquired_assets") if isinstance(manifest.get("acquired_assets"), list) else []
    injection = read_json(project_root / "receipts/generate_svg.json") or {}
    injection_summary = injection.get("asset_injection_summary") if isinstance(injection.get("asset_injection_summary"), dict) else {}
    return {
        "manifest_path": "03-assets/asset-manifest.json" if manifest else None,
        "manifest_sha256": file_sha256(project_root / "03-assets/asset-manifest.json"),
        "status": manifest.get("status"),
        "network_policy": manifest.get("network_policy"),
        "asset_provider": manifest.get("asset_provider"),
        "image_backend": manifest.get("image_backend"),
        "contract_count": summary.get("contract_count"),
        "acquired_count": summary.get("acquired_count"),
        "fallback_count": summary.get("fallback_count"),
        "image_job_count": summary.get("image_job_count"),
        "acquired_assets": [
            {
                "asset_id": item.get("asset_id"),
                "status": item.get("status"),
                "asset_kind": item.get("asset_kind"),
                "file": item.get("file"),
                "sha256": item.get("sha256"),
                "source_url": item.get("source_url"),
            }
            for item in acquired_assets
            if isinstance(item, dict)
        ],
        "asset_injection_summary": injection_summary,
    }


def stage_status(project_root: Path, stage: str) -> str | None:
    state = read_json(project_root / "01-project/state.json") or {}
    record = state.get("stages", {}).get(stage) if isinstance(state.get("stages"), dict) else None
    return record.get("status") if isinstance(record, dict) else None


def planner_summary(project_root: Path) -> dict[str, Any]:
    receipt = read_json(project_root / "receipts/prompt-planner.json") or {}
    return {
        "receipt_path": "receipts/prompt-planner.json" if receipt else None,
        "receipt_sha256": file_sha256(project_root / "receipts/prompt-planner.json"),
        "status": receipt.get("status"),
        "provider": receipt.get("provider"),
        "provider_type": receipt.get("provider_type"),
        "search_enabled": receipt.get("search_enabled"),
        "outputs": receipt.get("outputs"),
        "planner_stage_receipt_paths": receipt.get("planner_stage_receipt_paths"),
        "planner_raw_outputs": receipt.get("planner_raw_outputs"),
        "summary": receipt.get("summary"),
    }


def check_summary(project_root: Path) -> dict[str, Any]:
    quality_gate = read_json(project_root / "06-check/quality-gate.json") or {}
    dry_run = read_json(project_root / "07-create/dry-run.json") or {}
    visual_acceptance = read_json(project_root / "06-check/visual-acceptance.json") or {}
    return {
        "quality_gate": {
            "path": "06-check/quality-gate.json" if quality_gate else None,
            "sha256": file_sha256(project_root / "06-check/quality-gate.json"),
            "status": quality_gate.get("status"),
            "summary": quality_gate.get("summary"),
        },
        "dry_run": {
            "path": "07-create/dry-run.json" if dry_run else None,
            "sha256": file_sha256(project_root / "07-create/dry-run.json"),
            "status": dry_run.get("status"),
            "returncode": dry_run.get("returncode"),
            "command": dry_run.get("command"),
        },
        "visual_acceptance": {
            "path": "06-check/visual-acceptance.json" if visual_acceptance else None,
            "sha256": file_sha256(project_root / "06-check/visual-acceptance.json"),
            "receipt_sha256": file_sha256(project_root / "receipts/visual_acceptance.json"),
            "status": visual_acceptance.get("status"),
            "deliverable_pass": visual_acceptance.get("deliverable_pass"),
            "action": visual_acceptance.get("action"),
            "issues": visual_acceptance.get("issues"),
            "visual_evidence": visual_acceptance.get("visual_evidence"),
            "deck_rhythm": visual_acceptance.get("deck_rhythm"),
        },
    }


def preview_summary(project_root: Path) -> dict[str, Any]:
    return {
        "preview_html": {
            "path": "05-preview/preview.html",
            "sha256": file_sha256(project_root / "05-preview/preview.html"),
        },
        "preview_manifest": {
            "path": "05-preview/preview-manifest.json",
            "sha256": file_sha256(project_root / "05-preview/preview-manifest.json"),
        },
        "contact_sheet": {
            "path": "05-preview/contact-sheet.png",
            "sha256": file_sha256(project_root / "05-preview/contact-sheet.png"),
        },
    }


def actionable_visual_outcome(checks: dict[str, Any]) -> bool:
    va = checks["visual_acceptance"]
    if va.get("deliverable_pass") is True:
        return True
    issues = va.get("issues")
    return isinstance(issues, list) and any(isinstance(item, dict) and item.get("code") for item in issues)


def real_assets_satisfied(assets: dict[str, Any], *, fixture_mode: bool) -> bool:
    if fixture_mode:
        return True
    acquired = assets.get("acquired_count")
    if isinstance(acquired, int) and acquired > 0:
        return True
    acquired_assets = assets.get("acquired_assets")
    return isinstance(acquired_assets, list) and any(
        isinstance(item, dict) and item.get("status") == "acquired" and item.get("file") and item.get("sha256")
        for item in acquired_assets
    )


def case_status(case_result: dict[str, Any], *, fixture_mode: bool) -> str:
    if case_result.get("command_failed"):
        return "failed"
    checks = case_result["checks"]
    if checks["quality_gate"].get("status") != "passed":
        return "failed"
    if checks["dry_run"].get("status") != "passed":
        return "failed"
    if checks["visual_acceptance"].get("status") not in {"passed", "failed"}:
        return "failed"
    if not actionable_visual_outcome(checks):
        return "failed"
    if not real_assets_satisfied(case_result["assets"], fixture_mode=fixture_mode):
        return "failed"
    return "passed"


def run_case(
    case: dict[str, str],
    args: argparse.Namespace,
    *,
    project_runner: Path,
    run_root: Path,
    command_func: Callable[[list[str], Path], tuple[subprocess.CompletedProcess[str], dict[str, Any]]],
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    plan_root = run_root / "projects"
    deck_id = f"vf5-{slugify(case['id'])}"
    init_command = [
        sys.executable,
        project_runner.as_posix(),
        "init",
        "--deck-id",
        deck_id,
        "--title",
        case["title"],
        "--plan-root",
        plan_root.as_posix(),
        "--force",
    ]
    init_completed, init_record = command_func(init_command, REPO_ROOT)
    commands.append(init_record)
    project_root: Path | None = None
    command_failed = init_completed.returncode != 0
    if not command_failed:
        try:
            project_root = parse_init_project_root(init_completed.stdout)
        except BenchmarkError:
            command_failed = True
    if project_root is None:
        project_root = plan_root / deck_id
    prompt_command = [
        sys.executable,
        project_runner.as_posix(),
        "prompt-plan",
        project_root.as_posix(),
        "--prompt",
        case["prompt"],
        "--audience",
        case.get("audience") or args.audience,
        *planner_command_args(args),
    ]
    if not command_failed:
        prompt_completed, prompt_record = command_func(prompt_command, REPO_ROOT)
        commands.append(prompt_record)
        command_failed = prompt_completed.returncode != 0
    run_command_line = [
        sys.executable,
        project_runner.as_posix(),
        "run",
        project_root.as_posix(),
        "--until",
        "visual_acceptance",
        *run_args(args),
    ]
    if not command_failed:
        run_completed, run_record = command_func(run_command_line, REPO_ROOT)
        commands.append(run_record)
        command_failed = run_completed.returncode != 0

    result = {
        "case_id": case["id"],
        "prompt": case["prompt"],
        "title": case["title"],
        "project_root": project_root.as_posix(),
        "project_root_sha256": None,
        "command_failed": command_failed,
        "commands": commands,
        "stage_statuses": {
            "source": stage_status(project_root, "source"),
            "plan": stage_status(project_root, "plan"),
            "assets": stage_status(project_root, "assets"),
            "generate_svg": stage_status(project_root, "generate_svg"),
            "preview": stage_status(project_root, "preview"),
            "quality_gate": stage_status(project_root, "quality_gate"),
            "dry_run": stage_status(project_root, "dry_run"),
            "visual_acceptance": stage_status(project_root, "visual_acceptance"),
            "live_create": stage_status(project_root, "live_create"),
        },
        "instruction": {
            "path": "00-input/instruction.json",
            "sha256": file_sha256(project_root / "00-input/instruction.json"),
        },
        "planner": planner_summary(project_root),
        "assets": asset_summary(project_root),
        "preview": preview_summary(project_root),
        "checks": check_summary(project_root),
        "live_submission_blocked": stage_status(project_root, "live_create") is None,
    }
    result["status"] = case_status(result, fixture_mode=args.fixture_mode)
    result["project_root_sha256"] = file_sha256(project_root / "01-project/project_manifest.json")
    return result


def run_benchmark(
    args: argparse.Namespace,
    *,
    command_func: Callable[[list[str], Path], tuple[subprocess.CompletedProcess[str], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    run_root = (Path(args.run_root) if args.run_root else REPO_ROOT / ".tmp" / f"svglide-vf5-benchmark-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}").resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    project_runner = command_project_runner(args)
    mode_issues = assert_real_mode(args)
    cases = selected_cases(args.case)
    command_func = command_func or (lambda command, cwd: run_command(command, cwd=cwd))
    previous_lark_cli_command = os.environ.get("SVGLIDE_LARK_CLI_CMD")
    if args.lark_cli_command:
        os.environ["SVGLIDE_LARK_CLI_CMD"] = args.lark_cli_command
    try:
        case_results = [
            run_case(case, args, project_runner=project_runner, run_root=run_root, command_func=command_func)
            for case in cases
        ]
    finally:
        if args.lark_cli_command:
            if previous_lark_cli_command is None:
                os.environ.pop("SVGLIDE_LARK_CLI_CMD", None)
            else:
                os.environ["SVGLIDE_LARK_CLI_CMD"] = previous_lark_cli_command
    passed_count = sum(1 for item in case_results if item["status"] == "passed")
    deliverable_pass_count = sum(
        1
        for item in case_results
        if item["checks"]["visual_acceptance"].get("deliverable_pass") is True
    )
    failed_count = len(case_results) - passed_count
    status = "passed" if not mode_issues and failed_count == 0 else "failed"
    payload = {
        "schema_version": "svglide-vf5-benchmark/v1",
        "status": status,
        "run_root": run_root.as_posix(),
        "created_at": now_iso(),
        "fixture_mode": bool(args.fixture_mode),
        "real_benchmark": not bool(args.fixture_mode),
        "planner_provider": args.planner_provider,
        "planner_search_enabled": not args.no_search,
        "network_policy": args.network_policy,
        "asset_provider": args.asset_provider,
        "image_backend": args.image_backend,
        "lark_cli_command": args.lark_cli_command or os.environ.get("SVGLIDE_LARK_CLI_CMD") or "lark-cli",
        "no_image_search": bool(args.no_image_search),
        "no_ai_image": bool(args.no_ai_image),
        "target_stage": "visual_acceptance",
        "stopped_before_live_create": all(item.get("live_submission_blocked") for item in case_results),
        "mode_issues": mode_issues,
        "summary": {
            "case_count": len(case_results),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "deliverable_pass_count": deliverable_pass_count,
        },
        "cases": case_results,
    }
    write_json(run_root / "06-check/vf5-benchmark.json", payload)
    receipt = {
        "schema_version": "svglide-vf5-benchmark-receipt/v1",
        "stage": "vf5_benchmark",
        "status": status,
        "created_at": payload["created_at"],
        "run_root": run_root.as_posix(),
        "check_path": "06-check/vf5-benchmark.json",
        "check_sha256": file_sha256(run_root / "06-check/vf5-benchmark.json"),
        "case_project_roots": [item["project_root"] for item in case_results],
        "summary": payload["summary"],
        "mode_issues": mode_issues,
    }
    write_json(run_root / "receipts/vf5-benchmark.json", receipt)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VF5 real prompt-to-visual-acceptance benchmark suite.")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--project-runner", type=Path)
    parser.add_argument("--case", action="append", help="case id to run; defaults to all VF5 benchmark prompts")
    parser.add_argument("--planner-provider", default="codex", choices=["codex", "claude", "command"])
    parser.add_argument("--planner-command")
    parser.add_argument("--lark-cli-command", help="local CLI command used by svglide_project_runner via SVGLIDE_LARK_CLI_CMD")
    parser.add_argument("--target-slide-count", type=int, default=8)
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--audience", default="投资/战略分析读者")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-search", action="store_true")
    parser.add_argument("--network-policy", default="auto", choices=sorted(NETWORK_POLICIES))
    parser.add_argument("--asset-provider", default="auto")
    parser.add_argument("--image-backend", default="auto", choices=sorted(IMAGE_BACKENDS))
    parser.add_argument("--no-online-research", action="store_true")
    parser.add_argument("--no-image-search", action="store_true")
    parser.add_argument("--no-ai-image", action="store_true")
    parser.add_argument("--refresh-online", action="store_true")
    parser.add_argument("--fixture-mode", action="store_true", help="allow fixture providers/assets for deterministic tests; never claim real benchmark")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(args)
    except (BenchmarkError, OSError) as error:
        print(f"svglide_vf5_benchmark: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
