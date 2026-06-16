#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STAGES = [
    "generate",
    "prepare",
    "preview",
    "preflight",
    "preview_lint",
    "quality_gate",
    "dry_run",
    "ppe_proof",
    "live_create",
    "readback",
    "render_contact_sheet",
]
STAGE_ALIASES = {
    "dry-run": "dry_run",
    "dry_run": "dry_run",
    "live-create": "live_create",
    "live_create": "live_create",
    "preview-lint": "preview_lint",
    "preview_lint": "preview_lint",
    "quality-gate": "quality_gate",
    "quality_gate": "quality_gate",
    "ppe-proof": "ppe_proof",
    "ppe_proof": "ppe_proof",
    "render-contact-sheet": "render_contact_sheet",
    "render_contact_sheet": "render_contact_sheet",
}
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STAGE_FINGERPRINT_SCHEMA = "svglide-stage-fingerprint/v1"
QUALITY_GATE_SCHEMA = "svglide-quality-gate/v1"
ENV_PROOF_SCHEMA = "svglide-env-proof/v1"
PREVIEW_LINT_WAIVER_TTL_MS = 30 * 60 * 1000


class RunnerError(RuntimeError):
    pass


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def now_ms() -> int:
    return int(time.time() * 1000)


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_runner_args() -> argparse.Namespace:
    return argparse.Namespace(
        cli="./lark-cli",
        env="",
        env_proof="",
        env_proof_input="",
        proxy="",
        allow_live=False,
        force_live=False,
        allow_missing_preview_lint=False,
        validation_profile="",
        until="dry_run",
        resume=False,
    )


def get_arg(args: argparse.Namespace | None, name: str, default: Any = "") -> Any:
    if args is None:
        args = default_runner_args()
    return getattr(args, name, default)


def text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_stage(value: str) -> str:
    value = STAGE_ALIASES.get(value, value)
    if value not in STAGES:
        raise RunnerError(f"unknown stage: {value}")
    return value


def project_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def project_file(project: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project / path


def rel_to_project(project: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path)


def rel_to_cli_cwd(path: Path) -> str:
    cwd = repo_root().resolve()
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(cwd))
    except ValueError as error:
        raise RunnerError(f"create-svg input must be inside CLI worktree root: {resolved}") from error


def rel_artifact(path: Path) -> str:
    return rel_to_cli_cwd(path)


def safe_existing_file(path: Path, *, suffix: str | None = None, root: Path | None = None) -> Path:
    raw = str(path)
    if not raw.strip() or CONTROL_CHAR_RE.search(raw):
        raise RunnerError(f"unsafe file path: {raw!r}")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise RunnerError(f"not a regular file: {resolved}")
    if suffix and resolved.suffix.lower() != suffix.lower():
        raise RunnerError(f"expected {suffix} file: {resolved}")
    if root is not None:
        root_resolved = root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as error:
            raise RunnerError(f"file escapes allowed root: {resolved}") from error
    return resolved


def safe_output_file(path: Path, *, root: Path, suffix: str | None = None) -> Path:
    raw = str(path)
    if not raw.strip() or CONTROL_CHAR_RE.search(raw):
        raise RunnerError(f"unsafe output path: {raw!r}")
    if suffix and path.suffix.lower() != suffix.lower():
        raise RunnerError(f"expected {suffix} output path: {path}")
    root_resolved = root.resolve()
    candidate = path if path.is_absolute() else root / path
    parent = candidate.parent.resolve(strict=False)
    try:
        parent.relative_to(root_resolved)
    except ValueError as error:
        raise RunnerError(f"output path escapes project root: {candidate}") from error
    return parent / candidate.name


def project_artifact_path(project: Path, value: str, *, must_exist: bool, suffix: str | None = None) -> Path:
    raw = value.strip()
    if not raw or CONTROL_CHAR_RE.search(raw):
        raise RunnerError(f"unsafe artifact path: {value!r}")
    path = Path(raw).expanduser()
    root = repo_root().resolve()
    candidates: list[Path]
    if path.is_absolute():
        candidates = [path]
    elif raw.startswith(".lark-slides/") or raw.startswith("skills/lark-slides/"):
        candidates = [root / path]
    else:
        candidates = [project / path, root / path]
    selected = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RunnerError(f"artifact path escapes CLI worktree root: {resolved}") from error
    if suffix and resolved.suffix.lower() != suffix.lower():
        raise RunnerError(f"expected {suffix} artifact path: {resolved}")
    if must_exist:
        return safe_existing_file(resolved, suffix=suffix, root=root)
    parent = resolved.parent.resolve(strict=False)
    try:
        parent.relative_to(root)
    except ValueError as error:
        raise RunnerError(f"artifact output escapes CLI worktree root: {resolved}") from error
    return parent / resolved.name


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or not header.startswith(PNG_SIGNATURE) or header[12:16] != b"IHDR":
        raise RunnerError(f"expected PNG image: {path}")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise RunnerError(f"PNG has invalid dimensions: {path}")
    return width, height


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_fallback_contact_sheet(path: Path, panels: list[tuple[str, Path]]) -> None:
    width = 960
    height = 360
    panel_width = width // max(1, len(panels))
    colors = [(40, 96, 168), (46, 125, 88), (96, 96, 104)]
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            index = min(x // panel_width, len(panels) - 1)
            base = colors[index % len(colors)]
            border = x % panel_width in {0, panel_width - 1} or y in {0, height - 1}
            shade = 35 if border else 0
            row.extend((max(0, base[0] - shade), max(0, base[1] - shade), max(0, base[2] - shade), 255))
        rows.append(bytes(row))
    raw = b"".join(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    png = [
        PNG_SIGNATURE,
        png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
        png_chunk(b"IDAT", zlib.compress(raw)),
        png_chunk(b"IEND", b""),
    ]
    path.write_bytes(b"".join(png))


def render_contact_sheet_png(output: Path, panels: list[tuple[str, Path]]) -> None:
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        write_fallback_contact_sheet(output, panels)
        return

    thumb_width = 360
    thumb_height = 204
    label_height = 28
    padding = 16
    sheet_width = padding + len(panels) * (thumb_width + padding)
    sheet_height = padding + label_height + thumb_height + padding
    sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image_path) in enumerate(panels):
        left = padding + index * (thumb_width + padding)
        draw.text((left, padding), label, fill=(24, 24, 24))
        with Image.open(image_path) as image:
            image = ImageOps.contain(image.convert("RGBA"), (thumb_width, thumb_height))
            frame = Image.new("RGBA", (thumb_width, thumb_height), (248, 248, 248, 255))
            frame.alpha_composite(image, ((thumb_width - image.width) // 2, (thumb_height - image.height) // 2))
            sheet.paste(frame.convert("RGB"), (left, padding + label_height))
        draw.rectangle(
            [left, padding + label_height, left + thumb_width - 1, padding + label_height + thumb_height - 1],
            outline=(180, 180, 180),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")


def ensure_project_dirs(project: Path) -> None:
    for name in ["logs", "receipts", "prepared"]:
        (project / name).mkdir(parents=True, exist_ok=True)


def manifest_path(project: Path) -> Path:
    return project / "project_manifest.json"


def state_path(project: Path) -> Path:
    return project / "state.json"


def manifest(project: Path) -> dict[str, Any]:
    path = manifest_path(project)
    if not path.exists():
        raise RunnerError(f"missing project_manifest.json: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise RunnerError("project_manifest.json must contain an object")
    return data


def receipt_path(project: Path, stage: str, data: dict[str, Any]) -> Path:
    receipts = data.get("receipts")
    if isinstance(receipts, dict) and isinstance(receipts.get(stage), str):
        return safe_output_file(project_file(project, receipts[stage]), root=project, suffix=".json")
    return project / "receipts" / f"{stage.replace('_', '-')}.json"


def log_path(project: Path, stage: str) -> Path:
    return project / "logs" / f"{stage.replace('_', '-')}.log"


def project_pages(project: Path, data: dict[str, Any], *, prepared: bool) -> list[Path]:
    pages = data.get("pages")
    out: list[Path] = []
    if isinstance(pages, list):
        key = "prepared_svg" if prepared else "source_svg"
        for page in pages:
            if isinstance(page, dict) and isinstance(page.get(key), str):
                out.append(project_file(project, page[key]))
    if out:
        return out
    folder = project / ("prepared" if prepared else "pages")
    return sorted(folder.glob("page-*.svg"))


def plan_file(project: Path, data: dict[str, Any]) -> Path:
    value = data.get("plan")
    if isinstance(value, str) and value.strip():
        return project_file(project, value)
    return project / "slide_plan.json"


def deck_title(project: Path, data: dict[str, Any]) -> str:
    for key in ["title", "deck_title", "name"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    plan = read_json(plan_file(project, data), {})
    if isinstance(plan, dict):
        for key in ["title", "deck_title", "theme_name", "deck_id"]:
            value = plan.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    deck_id = data.get("deck_id")
    return str(deck_id or project.name)


def stage_command(data: dict[str, Any], stage: str) -> str:
    commands = data.get("stage_commands")
    if isinstance(commands, dict) and isinstance(commands.get(stage), str):
        return commands[stage]
    return ""


def command_cwd(args: list[str], project: Path) -> Path:
    if any(part.startswith("skills/lark-slides/") for part in args):
        return repo_root()
    return project


def run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, stdin: str | None = None) -> CommandResult:
    process = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(process.returncode, process.stdout, process.stderr)


def run_manifest_command(project: Path, data: dict[str, Any], stage: str) -> dict[str, Any]:
    command = stage_command(data, stage)
    if not command:
        if stage == "generate" and data.get("generated") is True:
            return {"status": "skipped", "reason": "generated=true"}
        if stage == "preview" and data.get("preview") == "skipped":
            return {"status": "skipped", "reason": "preview=skipped"}
        raise RunnerError(f"missing stage_commands.{stage}")
    optional = False
    if command.startswith("optional:"):
        optional = True
        command = command.removeprefix("optional:").strip()
    if command.startswith("builtin:"):
        raise RunnerError(f"stage {stage} cannot use builtin command {command}")
    args = shlex.split(command)
    if not args:
        raise RunnerError(f"empty command for stage {stage}")
    executable = args[0]
    if optional and shutil.which(executable) is None:
        return {"status": "skipped", "reason": f"missing executable: {executable}"}
    result = run_command(args, cwd=command_cwd(args, project))
    log_path(project, stage).write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        if optional:
            return {"status": "skipped", "reason": "optional command failed", "returncode": result.returncode}
        raise RunnerError(f"{stage} command failed: {result.returncode}; see {log_path(project, stage)}")
    return {"status": "passed", "command": args, "log": str(log_path(project, stage).relative_to(project))}


def current_input_digest(project: Path, data: dict[str, Any], *, prepared: bool) -> str:
    pieces: list[str] = []
    plan = plan_file(project, data)
    if plan.exists():
        pieces.append(f"{plan.relative_to(project)}={file_digest(plan)}")
    for page in project_pages(project, data, prepared=prepared):
        if page.exists():
            pieces.append(f"{page.relative_to(project)}={file_digest(page)}")
    return text_digest("\n".join(pieces))


def json_digest(data: Any) -> str:
    return text_digest(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def fingerprint_path(project: Path, path: Path) -> str:
    resolved = path.resolve(strict=False)
    for root in [project.resolve(), repo_root().resolve()]:
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            continue
    return str(resolved)


def add_file_fingerprint(inputs: list[dict[str, Any]], project: Path, kind: str, path: Path) -> None:
    item: dict[str, Any] = {"kind": kind, "path": fingerprint_path(project, path)}
    if path.exists() and path.is_file():
        item["digest"] = file_digest(path)
    else:
        item["digest"] = "missing"
    inputs.append(item)


def add_value_fingerprint(inputs: list[dict[str, Any]], kind: str, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    inputs.append({"kind": kind, "value": value, "digest": text_digest(text)})


def resolve_cli_for_command(cli: str) -> str:
    cli_path = Path(cli)
    if not cli_path.is_absolute():
        candidate = repo_root() / cli_path
        if candidate.exists():
            return str(safe_existing_file(candidate, root=repo_root()))
    return cli


def cli_version_from_command(cli: str) -> str | None:
    try:
        result = run_command([resolve_cli_for_command(cli), "--version"], cwd=repo_root())
    except OSError:
        return None
    if result.returncode != 0:
        return None
    version = (result.stdout or result.stderr).strip().splitlines()
    return version[0].strip() if version and version[0].strip() else None


def cli_version_from_receipt(project: Path, cli: str) -> str | None:
    candidates = [
        project / "receipts" / "lark-cli-version.json",
        project / "receipts" / "cli-version.json",
    ]
    for candidate in candidates:
        data = read_json(candidate, {})
        if not isinstance(data, dict):
            continue
        proof_cli = text_from_any(nested(data, ["cli", "path"]) or data.get("cli_path"))
        if proof_cli and not same_cli_path(proof_cli, cli):
            continue
        version = text_from_any(nested(data, ["cli", "version"]) or data.get("cli_version") or data.get("version"))
        if version:
            return version
    return None


def read_cli_version(project: Path, cli: str) -> str:
    version = cli_version_from_command(cli) or cli_version_from_receipt(project, cli)
    if not version:
        raise RunnerError(f"failed to resolve lark-cli version for {cli}")
    return version


def cli_version_for_fingerprint(project: Path, cli: str) -> str:
    try:
        return read_cli_version(project, cli)
    except RunnerError:
        return "unavailable"


def normalized_env_proof_path(project: Path, data: dict[str, Any], args: argparse.Namespace | None) -> Path:
    value = text_from_any(get_arg(args, "env_proof", ""))
    if value:
        return safe_output_file(project_file(project, value), root=project, suffix=".json")
    return project / "receipts" / "env-proof.json"


def env_proof_input_path(args: argparse.Namespace | None) -> Path | None:
    value = text_from_any(get_arg(args, "env_proof_input", ""))
    return Path(value).expanduser().resolve() if value else None


def stage_input_fingerprint(stage: str, project: Path, args: argparse.Namespace) -> dict[str, Any]:
    stage = normalize_stage(stage)
    data = manifest(project)
    cli = text_from_any(get_arg(args, "cli", "./lark-cli")) or "./lark-cli"
    inputs: list[dict[str, Any]] = []
    add_file_fingerprint(inputs, project, "manifest", manifest_path(project))
    add_value_fingerprint(inputs, "stage_command", stage_command(data, stage))

    if stage in {"generate", "prepare"}:
        for page in project_pages(project, data, prepared=False):
            add_file_fingerprint(inputs, project, "source_svg", page)
    if stage not in {"generate", "prepare"}:
        for page in project_pages(project, data, prepared=True):
            add_file_fingerprint(inputs, project, "prepared_svg", page)
    if stage != "generate":
        add_file_fingerprint(inputs, project, "plan", plan_file(project, data))

    scripts = repo_root() / "skills" / "lark-slides" / "scripts"
    if stage == "preflight":
        add_file_fingerprint(inputs, project, "script", scripts / "svg_preflight.py")
        add_file_fingerprint(
            inputs,
            project,
            "route_manifest",
            repo_root() / "skills" / "lark-slides" / "references" / "routes" / "create-svg" / "route.manifest.json",
        )
        for catalog in ["svg-seeds.json", "svg-recipes.json", "style-presets.json"]:
            add_file_fingerprint(inputs, project, "catalog", repo_root() / "skills" / "lark-slides" / "references" / catalog)
    if stage == "preview_lint":
        add_file_fingerprint(inputs, project, "preview_html", project / "preview" / "preview.html")
        add_file_fingerprint(inputs, project, "script", scripts / "svg_preview_lint.py")
        add_value_fingerprint(inputs, "allow_missing_preview_lint", bool(get_arg(args, "allow_missing_preview_lint", False)))
    if stage == "quality_gate":
        for dependency in ["preflight", "preview_lint"]:
            add_file_fingerprint(inputs, project, f"{dependency}_receipt", receipt_path(project, dependency, data))
        add_file_fingerprint(inputs, project, "component_report", project / "receipts" / "emitted_components.json")
        add_file_fingerprint(inputs, project, "component_waiver", project / "receipts" / "emitted-components-waiver.json")
        add_file_fingerprint(inputs, project, "allowlist_receipt", project / "receipts" / "allowlist.json")
        try:
            add_file_fingerprint(inputs, project, "raster_report", raster_report_path(project, data))
        except RunnerError:
            pass
        add_value_fingerprint(inputs, "validation_profile", resolved_validation_profile(data, args))
    if stage in {"dry_run", "live_create"}:
        add_file_fingerprint(inputs, project, "quality_gate_receipt", receipt_path(project, "quality_gate", data))
    if stage in {"dry_run", "ppe_proof", "live_create", "readback"}:
        add_value_fingerprint(inputs, "cli", {"path": cli, "version": cli_version_for_fingerprint(project, cli)})
    if stage == "dry_run":
        add_value_fingerprint(inputs, "raster_config", create_svg_raster_config(data))
    if stage == "ppe_proof":
        raw = env_proof_input_path(args)
        if raw is not None:
            add_file_fingerprint(inputs, project, "env_proof_input", raw)
        else:
            add_value_fingerprint(inputs, "env_proof_input", "")
        add_value_fingerprint(
            inputs,
            "proof_config",
            {
                "env": get_arg(args, "env", ""),
                "env_proof": text_from_any(get_arg(args, "env_proof", "")),
                "proxy": text_from_any(get_arg(args, "proxy", "")),
            },
        )
    if stage == "live_create":
        add_file_fingerprint(inputs, project, "dry_run_receipt", receipt_path(project, "dry_run", data))
        add_file_fingerprint(inputs, project, "ppe_proof_receipt", receipt_path(project, "ppe_proof", data))
        add_file_fingerprint(inputs, project, "env_proof", normalized_env_proof_path(project, data, args))
    if stage == "readback":
        add_file_fingerprint(inputs, project, "live_create_receipt", receipt_path(project, "live_create", data))
    if stage == "render_contact_sheet":
        try:
            add_file_fingerprint(inputs, project, "raster_report", raster_report_path(project, data))
        except RunnerError:
            pass
        add_file_fingerprint(inputs, project, "readback_receipt", receipt_path(project, "readback", data))

    payload = {"stage": stage, "schema_version": STAGE_FINGERPRINT_SCHEMA, "inputs": inputs}
    return {**payload, "digest": json_digest(payload)}


def update_state(project: Path, stage: str, receipt: dict[str, Any]) -> None:
    state = read_json(state_path(project), {})
    if not isinstance(state, dict):
        state = {}
    stages = state.setdefault("stages", {})
    stages[stage] = {
        "status": receipt.get("status"),
        "elapsed_ms": receipt.get("elapsed_ms"),
        "input_digest": receipt.get("input_digest"),
        "input_fingerprint_digest": nested(receipt, ["input_fingerprint", "digest"]),
        "receipt": str(receipt_path(project, stage, manifest(project)).relative_to(project)),
        "updated_at_ms": now_ms(),
    }
    if receipt.get("status") == "passed":
        state["last_successful_stage"] = stage
    write_json(state_path(project), state)


def update_timings(project: Path, stage: str, receipt: dict[str, Any]) -> None:
    path = project / "receipts" / "timings.json"
    timings = read_json(path, {"stages": []})
    if not isinstance(timings, dict):
        timings = {"stages": []}
    stages = [
        item
        for item in timings.get("stages", [])
        if isinstance(item, dict) and item.get("name") != stage and item.get("stage") != stage
    ]
    fingerprint = receipt.get("input_fingerprint") if isinstance(receipt.get("input_fingerprint"), dict) else {}
    stages.append(
        {
            "name": stage,
            "stage": stage,
            "status": receipt.get("status"),
            "elapsed_ms": receipt.get("elapsed_ms", 0),
            "cache_hit": bool(receipt.get("cache_hit")),
            "input_count": len(fingerprint.get("inputs", [])) if isinstance(fingerprint.get("inputs"), list) else 0,
            "output_count": receipt_output_count(receipt),
            "error_count": receipt_count(receipt, "error_count"),
            "warning_count": receipt_count(receipt, "warning_count"),
        }
    )
    order = {name: index for index, name in enumerate(STAGES)}
    stages.sort(key=lambda item: order.get(str(item.get("stage") or item.get("name")), 999))
    timings["deck_id"] = manifest(project).get("deck_id", project.name)
    timings["stages"] = stages
    timings["total_elapsed_ms"] = sum(int(item.get("elapsed_ms") or 0) for item in stages)
    write_json(path, timings)


def receipt_count(receipt: dict[str, Any], key: str) -> int:
    value = receipt.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    summary = receipt.get("summary")
    if isinstance(summary, dict):
        nested_value = summary.get(key)
        if isinstance(nested_value, int) and not isinstance(nested_value, bool):
            return nested_value
        nested_summary = summary.get("summary")
        if isinstance(nested_summary, dict):
            nested_value = nested_summary.get(key)
            if isinstance(nested_value, int) and not isinstance(nested_value, bool):
                return nested_value
    return 0


def receipt_output_count(receipt: dict[str, Any]) -> int:
    outputs = receipt.get("outputs")
    if isinstance(outputs, list):
        return len(outputs)
    operations = receipt.get("operations")
    if isinstance(operations, list):
        return len(operations)
    if receipt.get("xml_presentation_id"):
        return 1
    return 0


def write_stage_receipt(
    project: Path,
    data: dict[str, Any],
    stage: str,
    started_ms: int,
    body: dict[str, Any],
    *,
    prepared_digest: bool = True,
    args: argparse.Namespace | None = None,
) -> dict[str, Any]:
    if args is None:
        args = default_runner_args()
    fingerprint = stage_input_fingerprint(stage, project, args)
    receipt = {
        "stage": stage,
        "status": body.get("status", "passed"),
        "elapsed_ms": now_ms() - started_ms,
        "input_digest": fingerprint["digest"],
        "input_fingerprint": fingerprint,
        **body,
    }
    write_json(receipt_path(project, stage, data), receipt)
    update_state(project, stage, receipt)
    update_timings(project, stage, receipt)
    return receipt


def stage_uses_prepared_digest(stage: str) -> bool:
    return stage not in {"generate", "prepare"}


def builtin_prepare(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    source_pages = project_pages(project, data, prepared=False)
    if not source_pages:
        raise RunnerError("prepare found no pages/*.svg source files")
    prepared_pages = project_pages(project, data, prepared=True)
    if not prepared_pages or len(prepared_pages) != len(source_pages):
        prepared_pages = [project / "prepared" / page.name for page in source_pages]
    operations = []
    for source, target in zip(source_pages, prepared_pages):
        source = safe_existing_file(source, suffix=".svg", root=project)
        target = safe_output_file(target, root=project, suffix=".svg")
        before = file_digest(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target = safe_existing_file(target, suffix=".svg", root=project)
        after = file_digest(target)
        operations.append(
            {
                "source": rel_to_project(project, source),
                "target": rel_to_project(project, target),
                "source_digest": before,
                "prepared_digest": after,
                "mutation": "copy",
            }
        )
    return {"status": "passed", "operations": operations}


def run_prepare(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    command = stage_command(data, "prepare")
    if not command or command == "builtin:copy_and_normalize_svg":
        return builtin_prepare(project, data)
    if command.startswith("builtin:"):
        raise RunnerError(f"unknown prepare builtin: {command}")
    return run_manifest_command(project, data, "prepare")


def run_preflight(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    require_latest_prepare(project, data)
    inputs = project_pages(project, data, prepared=True)
    if not inputs:
        raise RunnerError("preflight found no prepared SVG files")
    route_manifest = repo_root() / "skills" / "lark-slides" / "references" / "routes" / "create-svg" / "route.manifest.json"
    args = [
        sys.executable,
        "skills/lark-slides/scripts/svg_preflight.py",
        "--plan",
        str(plan_file(project, data)),
    ]
    if route_manifest.exists():
        args[2:2] = ["--route-manifest", str(route_manifest), "--report-scope", "public"]
    for path in inputs:
        args.extend(["--input", str(safe_existing_file(path, suffix=".svg", root=project))])
    result = run_command(args, cwd=repo_root())
    log_path(project, "preflight").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    if result.returncode != 0:
        raise RunnerError(f"preflight failed: {result.returncode}; see {log_path(project, 'preflight')}")
    return {
        "status": "passed",
        "command": args,
        "log": str(log_path(project, "preflight").relative_to(project)),
        "summary": parsed,
    }


def parse_json_output(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def build_create_svg_command(project: Path, data: dict[str, Any], cli: str, *, dry_run: bool) -> list[str]:
    inputs = project_pages(project, data, prepared=True)
    if not inputs:
        raise RunnerError("create-svg command found no prepared SVG files")
    cli_path = Path(cli)
    if not cli_path.is_absolute():
        cli_path = repo_root() / cli_path
    if cli_path.exists():
        cli = str(safe_existing_file(cli_path, root=repo_root()))
    args = [cli, "slides", "+create-svg", "--as", "user", "--title", deck_title(project, data)]
    for path in inputs:
        safe_path = safe_existing_file(path, suffix=".svg", root=project)
        args.extend(["--file", rel_to_cli_cwd(safe_path)])
    args.extend(create_svg_raster_flags(project, data))
    if dry_run:
        args.append("--dry-run")
    args.extend(["--format", "json"])
    return args


def create_svg_raster_config(data: dict[str, Any]) -> dict[str, Any]:
    for key in ["rasterize", "svg_rasterize", "svg_rasterization"]:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def create_svg_raster_flags(project: Path, data: dict[str, Any]) -> list[str]:
    config = create_svg_raster_config(data)
    mode = text_from_any(
        config.get("effects")
        or config.get("mode")
        or data.get("svg_rasterize_effects")
        or data.get("rasterize_effects")
    )
    if not mode or mode == "off":
        return []
    flags = ["--svg-rasterize-effects", mode]
    scale = config.get("scale") or data.get("svg_rasterize_scale") or data.get("rasterize_scale")
    if scale is not None and text_from_any(scale):
        flags.extend(["--svg-rasterize-scale", text_from_any(scale)])
    report = (
        config.get("report")
        or config.get("report_path")
        or data.get("svg_rasterize_report")
        or data.get("raster_report")
        or data.get("rasterization_report")
    )
    if isinstance(report, str) and report.strip():
        report_path = project_artifact_path(project, report, must_exist=False, suffix=".json")
        flags.extend(["--svg-rasterize-report", rel_to_cli_cwd(report_path)])
    return flags


def required_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RunnerError(f"{field} must be an integer")
    return value


def extract_stage_counts(stage: str, receipt: dict[str, Any], *, allow_waived: bool = False) -> dict[str, Any]:
    status = text_from_any(receipt.get("status"))
    if status == "waived" and stage == "preview_lint" and allow_waived:
        if not preview_lint_waiver_active(receipt):
            raise RunnerError("preview_lint waiver expired")
        return {"status": "waived", "error_count": 0, "warning_count": 0}
    if status != "passed":
        raise RunnerError(f"{stage} receipt status must be passed")
    if stage == "preflight":
        summary = nested(receipt, ["summary", "summary"])
        if not isinstance(summary, dict):
            raise RunnerError("preflight receipt missing summary.summary")
        return {
            "status": "passed",
            "error_count": required_int(summary.get("error_count"), "preflight.summary.summary.error_count"),
            "warning_count": required_int(summary.get("warning_count"), "preflight.summary.summary.warning_count"),
        }
    if stage == "preview_lint":
        summary = receipt.get("summary")
        if not isinstance(summary, dict):
            raise RunnerError("preview_lint receipt missing summary")
        return {
            "status": "passed",
            "error_count": required_int(summary.get("error_count"), "preview_lint.summary.error_count"),
            "warning_count": required_int(summary.get("warning_count"), "preview_lint.summary.warning_count"),
        }
    raise RunnerError(f"cannot extract counts for stage: {stage}")


def dry_run_waiver_allowed(data: dict[str, Any], args: argparse.Namespace | None = None) -> bool:
    until = normalize_stage(text_from_any(get_arg(args, "until", "dry_run")) or "dry_run")
    return is_authoring_or_debug_lane(data, args) and STAGES.index(until) <= STAGES.index("dry_run")


def component_report_summary(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> dict[str, Any]:
    report_path = project / "receipts" / "emitted_components.json"
    if report_path.exists():
        report = read_json(report_path)
        if not isinstance(report, dict):
            raise RunnerError("emitted_components.json must contain an object")
        status = text_from_any(report.get("status") or "passed")
        if status not in {"passed", "verified", "ok"}:
            raise RunnerError(f"component report status must be passed: {status}")
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        error_count = report.get("error_count", summary.get("error_count", 0))
        warning_count = report.get("warning_count", summary.get("warning_count", 0))
        return {
            "status": "passed",
            "error_count": required_int(error_count, "component_report.error_count"),
            "warning_count": required_int(warning_count, "component_report.warning_count"),
            "path": rel_to_project(project, report_path),
        }

    waiver_path = project / "receipts" / "emitted-components-waiver.json"
    waiver = validate_legacy_waiver(read_json(waiver_path, {}) if waiver_path.exists() else {})
    if waiver.get("active") and dry_run_waiver_allowed(data, args):
        return {
            "status": "waived",
            "error_count": 0,
            "warning_count": 0,
            "waiver": {"type": "legacy_component_report", **waiver},
            "path": rel_to_project(project, waiver_path),
        }
    if is_production_lane(data, args):
        raise RunnerError("production quality gate requires receipts/emitted_components.json")
    raise RunnerError("quality gate requires receipts/emitted_components.json or active legacy component waiver")


def allowlist_entries(project: Path, data: dict[str, Any]) -> list[Any]:
    profile = data.get("validation_profile")
    if isinstance(profile, dict) and isinstance(profile.get("allowlist"), list):
        return profile["allowlist"]
    receipt = read_json(project / "receipts" / "allowlist.json", {})
    if isinstance(receipt, dict) and isinstance(receipt.get("allowlist"), list):
        return receipt["allowlist"]
    if isinstance(receipt, list):
        return receipt
    return []


def allowlist_summary(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    active_count = 0
    expired_count = 0
    for index, entry in enumerate(allowlist_entries(project, data)):
        validation = validate_legacy_waiver(entry, require_codes=True)
        if not validation.get("active"):
            if "missing required fields" in text_from_any(validation.get("reason")):
                raise RunnerError(f"allowlist entry {index} is invalid: {validation.get('reason')}")
            expired_count += 1
        else:
            active_count += 1
    return {"active_count": active_count, "expired_count": expired_count}


def raster_summary(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    try:
        path = raster_report_path(project, data)
    except RunnerError:
        return {"error_count": 0, "warning_count": 0, "status": "not_configured"}
    report = read_json(path, {})
    if not isinstance(report, dict):
        raise RunnerError("raster report must contain an object")
    quality = report.get("quality") if isinstance(report.get("quality"), dict) else {}
    error_count = report.get("error_count", quality.get("error_count", 0))
    warning_count = report.get("warning_count", quality.get("warning_count", 0))
    return {
        "status": "passed",
        "error_count": required_int(error_count, "raster.error_count"),
        "warning_count": required_int(warning_count, "raster.warning_count"),
        "path": rel_artifact(path),
    }


def run_quality_gate(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> dict[str, Any]:
    preflight = require_fresh_receipt(project, data, "preflight", {"passed"}, args)
    preview_lint = require_fresh_receipt(project, data, "preview_lint", {"passed", "waived"}, args)
    preview_waiver_allowed = allow_preview_lint_waiver(data, args) and dry_run_waiver_allowed(data, args)
    preflight_counts = extract_stage_counts("preflight", preflight)
    preview_counts = extract_stage_counts("preview_lint", preview_lint, allow_waived=preview_waiver_allowed)
    component_counts = component_report_summary(project, data, args)
    raster_counts = raster_summary(project, data)
    allowlist = allowlist_summary(project, data)
    production = is_production_lane(data, args)
    waivers: list[dict[str, Any]] = []
    if preview_counts["status"] == "waived":
        waivers.append({"type": "preview_lint", **preview_lint.get("waiver", {})})
    if component_counts["status"] == "waived" and isinstance(component_counts.get("waiver"), dict):
        waivers.append(component_counts["waiver"])

    failures: list[str] = []
    if preflight_counts["error_count"] != 0:
        failures.append("preflight.error_count must be 0")
    if preview_counts["error_count"] != 0:
        failures.append("preview_lint.error_count must be 0")
    if component_counts["error_count"] != 0:
        failures.append("component_report.error_count must be 0")
    if raster_counts["error_count"] != 0:
        failures.append("raster.error_count must be 0")
    if production:
        total_warnings = (
            preflight_counts["warning_count"]
            + preview_counts["warning_count"]
            + component_counts["warning_count"]
            + raster_counts["warning_count"]
        )
        if total_warnings != 0:
            failures.append("production warning_budget must be 0")
        if waivers:
            failures.append("production quality gate does not allow waivers")
    if waivers and not dry_run_waiver_allowed(data, args):
        failures.append("quality gate waivers are only allowed for authoring/debug dry_run")
    if failures:
        raise RunnerError("quality gate failed: " + "; ".join(failures))

    status = "passed_with_waiver" if waivers else "passed"
    return {
        "schema_version": QUALITY_GATE_SCHEMA,
        "status": status,
        "preflight": preflight_counts,
        "preview_lint": preview_counts,
        "component_report": component_counts,
        "raster": raster_counts,
        "allowlist": allowlist,
        "visual_score": None,
        "visual_score_mode": "advisory",
        "waivers": waivers,
    }


def run_dry_run(project: Path, data: dict[str, Any], cli: str, args: argparse.Namespace | None = None) -> dict[str, Any]:
    if args is None:
        args = default_runner_args()
        args.cli = cli
    require_latest_quality_gate(project, data, args)
    args = build_create_svg_command(project, data, cli, dry_run=True)
    result = run_command(args, cwd=repo_root())
    log_path(project, "dry_run").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    if result.returncode != 0:
        raise RunnerError(f"dry-run failed: {result.returncode}; see {log_path(project, 'dry_run')}")
    return {
        "status": "passed",
        "command": args,
        "log": str(log_path(project, "dry_run").relative_to(project)),
        "summary": parsed,
    }


def command_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    if getattr(args, "proxy", ""):
        env["HTTP_PROXY"] = args.proxy
        env["HTTPS_PROXY"] = args.proxy
    return env


def proxy_status(env: dict[str, str]) -> dict[str, Any]:
    proxy = env.get("HTTPS_PROXY") or env.get("HTTP_PROXY") or env.get("https_proxy") or env.get("http_proxy")
    return {
        "status": "configured_not_observed" if proxy else "missing",
        "proxy": proxy or "",
        "headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
        "verification": "best_effort_proxy_presence",
    }


def load_env_proof(path: str) -> dict[str, Any]:
    if not path:
        return {"verified": False, "reason": "missing --env-proof"}
    proof_path = Path(path).expanduser()
    try:
        data = read_json(proof_path)
    except Exception as error:  # noqa: BLE001 - surface malformed proof as runner error text.
        return {"verified": False, "reason": f"failed to read env proof: {error}", "path": str(proof_path)}
    if not isinstance(data, dict):
        return {"verified": False, "reason": "env proof must be a JSON object", "path": str(proof_path)}

    target_env = text_from_any(data.get("target_env") or data.get("env"))
    headers = data.get("headers") if isinstance(data.get("headers"), dict) else {}
    env_header = text_from_any(headers.get("Env") or headers.get("env"))
    tt_env_header = text_from_any(headers.get("x-tt-env") or headers.get("X-Tt-Env") or headers.get("X-TT-ENV"))
    host_text = " ".join(
        text_from_any(data.get(key))
        for key in ["openapi_host", "rewritten_host", "target_host", "url", "endpoint", "host"]
    )
    checks = {
        "target_env": target_env == "ppe_pure_svg",
        "env_header": env_header == "Pre_release",
        "tt_env_header": tt_env_header == "ppe_pure_svg",
        "pre_release_host": "open.feishu-pre.cn" in host_text,
    }
    verified = all(checks.values()) and text_from_any(data.get("status") or "verified") in {"verified", "passed", "ok"}
    return {
        "verified": verified,
        "path": str(proof_path),
        "checks": checks,
        "summary": {
            "target_env": target_env,
            "Env": env_header,
            "x-tt-env": tt_env_header,
            "host": host_text,
            "status": text_from_any(data.get("status")),
        },
    }


def text_from_any(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def verify_auth(project: Path, cli: str, env: dict[str, str]) -> dict[str, Any]:
    args = [cli, "auth", "status", "--verify"]
    result = run_command(args, cwd=repo_root(), env=env)
    (project / "logs" / "auth-status.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    verified = result.returncode == 0 and (not isinstance(parsed, dict) or parsed.get("verified") is not False)
    return {"verified": verified, "returncode": result.returncode, "summary": parsed, "log": "logs/auth-status.log"}


def write_env_receipt(project: Path, data: dict[str, Any], args: argparse.Namespace, env: dict[str, str], auth: dict[str, Any]) -> None:
    proof_path = normalized_env_proof_path(project, data, args)
    proof = load_env_proof(str(proof_path)) if proof_path.exists() else {"verified": False, "reason": "missing normalized env proof"}
    receipt = {
        "target_env": args.env,
        "allow_live": bool(args.allow_live),
        "auth_verified": bool(auth.get("verified")),
        "cli_path": args.cli,
        "proxy": proxy_status(env),
        "env_proof": proof,
        "auth": auth,
    }
    path = receipt_path(project, "env", data)
    write_json(path, receipt)


def proof_status(value: Any) -> str:
    return text_from_any(value).lower()


def proof_headers(data: dict[str, Any]) -> dict[str, Any]:
    headers = data.get("headers") if isinstance(data.get("headers"), dict) else {}
    return {
        "Env": text_from_any(headers.get("Env") or headers.get("env")),
        "x-tt-env": text_from_any(headers.get("x-tt-env") or headers.get("X-Tt-Env") or headers.get("X-TT-ENV")),
    }


def proof_host(data: dict[str, Any]) -> str:
    values = [
        data.get("target_host"),
        data.get("openapi_host"),
        data.get("rewritten_host"),
        data.get("host"),
        data.get("url"),
        data.get("endpoint"),
    ]
    host_summary = data.get("host_summary") if isinstance(data.get("host_summary"), dict) else {}
    values.extend(host_summary.values())
    return " ".join(text_from_any(value) for value in values if text_from_any(value))


def required_smoke_lane(data: dict[str, Any], args: argparse.Namespace | None = None) -> str:
    env = text_from_any(get_arg(args, "env", ""))
    lane = text_from_any(data.get("smoke_lane") or data.get("lane"))
    if lane:
        return lane
    if env == "ppe_pure_svg" or not env:
        return "pure_svg"
    return env


def smoke_covers_lane(smoke_type: str, required_lane: str) -> bool:
    if required_lane == "pure_svg":
        return smoke_type in {"pure_svg_minimal", "mixed_deck_smoke"}
    if required_lane in {"image_token", "image_token_minimal"}:
        return smoke_type in {"image_token_minimal", "mixed_deck_smoke"}
    return smoke_type == required_lane or smoke_type == "mixed_deck_smoke"


def int_ms(value: Any, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise RunnerError(f"env proof {field} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise RunnerError(f"env proof {field} must be an integer") from error


def validate_env_proof(
    data: dict[str, Any],
    *,
    now_ms: int,
    required_lane: str,
    cli_path: str,
    cli_version: str,
    auth_subject: str | None,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise RunnerError("env proof must be a JSON object")
    target_env = text_from_any(data.get("target_env") or data.get("env"))
    headers = proof_headers(data)
    target_host = proof_host(data)
    observed_at_ms = int_ms(data.get("observed_at_ms"), "observed_at_ms")
    expires_at_value = data.get("expires_at_ms")
    ttl_ms = data.get("ttl_ms")
    expires_at_ms = int_ms(expires_at_value, "expires_at_ms") if expires_at_value is not None else observed_at_ms + int_ms(ttl_ms, "ttl_ms")
    cli_data = data.get("cli") if isinstance(data.get("cli"), dict) else {}
    proof_cli_path = text_from_any(cli_data.get("path") or data.get("cli_path"))
    proof_cli_version = text_from_any(cli_data.get("version") or data.get("cli_version"))
    auth = data.get("auth") if isinstance(data.get("auth"), dict) else {}
    smoke = data.get("smoke") if isinstance(data.get("smoke"), dict) else {}
    subject = text_from_any(auth_subject or auth.get("subject") or data.get("auth_subject"))
    smoke_type = text_from_any(smoke.get("type") or data.get("smoke_type"))
    smoke_status = proof_status(smoke.get("status") or data.get("smoke_status"))
    status = proof_status(data.get("status") or data.get("verification_status") or smoke_status or auth.get("status"))
    proxy = data.get("proxy") if isinstance(data.get("proxy"), dict) else {}

    failures: list[str] = []
    if target_env != "ppe_pure_svg":
        failures.append("target_env must be ppe_pure_svg")
    if "open.feishu-pre.cn" not in target_host:
        failures.append("target_host must include open.feishu-pre.cn")
    if headers["Env"] != "Pre_release":
        failures.append("headers.Env must be Pre_release")
    if headers["x-tt-env"] != "ppe_pure_svg":
        failures.append("headers.x-tt-env must be ppe_pure_svg")
    if expires_at_ms <= now_ms:
        failures.append("env proof is expired")
    if not proof_cli_path:
        failures.append("cli.path is required")
    elif not same_cli_path(proof_cli_path, cli_path):
        failures.append("cli.path does not match --cli")
    if not proof_cli_version:
        failures.append("cli.version is required")
    elif proof_cli_version != cli_version:
        failures.append("cli.version does not match current --cli --version")
    if not subject:
        failures.append("auth.subject is required")
    if not smoke_type or not smoke_covers_lane(smoke_type, required_lane):
        failures.append(f"smoke.type does not cover lane {required_lane}")
    if smoke_status and smoke_status not in {"passed", "verified", "ok"}:
        failures.append("smoke.status must be passed/verified/ok")
    if status and status not in {"passed", "verified", "ok"}:
        failures.append("proof status must be passed/verified/ok")
    if failures:
        raise RunnerError("env proof failed: " + "; ".join(failures))

    return {
        "schema_version": ENV_PROOF_SCHEMA,
        "status": "verified",
        "target_env": target_env,
        "target_host": target_host,
        "headers": headers,
        "observed_at_ms": observed_at_ms,
        "ttl_ms": expires_at_ms - observed_at_ms,
        "expires_at_ms": expires_at_ms,
        "cli_path": cli_path,
        "cli_version": cli_version,
        "cli": {"path": cli_path, "version": cli_version, "version_source": f"{cli_path} --version"},
        "auth_subject": subject,
        "auth": {"status": "verified", "subject": subject},
        "proxy_url": text_from_any(proxy.get("url") or data.get("proxy_url")),
        "proxy": proxy,
        "smoke": {
            "type": smoke_type,
            "status": smoke_status or "passed",
            "presentation_id": smoke.get("presentation_id") or data.get("presentation_id"),
        },
        "lane": required_lane,
    }


def run_ppe_proof(project: Path, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if args.env and args.env != "ppe_pure_svg":
        raise RunnerError("ppe_proof only supports --env ppe_pure_svg")
    raw_path = env_proof_input_path(args)
    if raw_path is None:
        raise RunnerError("ppe_proof requires --env-proof-input")
    raw = read_json(raw_path)
    if not isinstance(raw, dict):
        raise RunnerError("env proof input must contain a JSON object")
    cli_version = read_cli_version(project, args.cli)
    auth = raw.get("auth") if isinstance(raw.get("auth"), dict) else {}
    normalized = validate_env_proof(
        raw,
        now_ms=now_ms(),
        required_lane=required_smoke_lane(data, args),
        cli_path=args.cli,
        cli_version=cli_version,
        auth_subject=text_from_any(auth.get("subject") or raw.get("auth_subject")),
    )
    output = normalized_env_proof_path(project, data, args)
    write_json(output, normalized)
    return {
        "status": "passed",
        "normalized_env_proof": rel_to_project(project, output),
        "summary": {
            "target_env": normalized["target_env"],
            "target_host": normalized["target_host"],
            "expires_at_ms": normalized["expires_at_ms"],
            "cli_version": normalized["cli_version"],
            "auth_subject": normalized["auth_subject"],
            "lane": normalized["lane"],
            "smoke_type": normalized["smoke"]["type"],
        },
    }


def require_latest_ppe_proof(project: Path, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    receipt = require_fresh_receipt(project, data, "ppe_proof", {"passed"}, args)
    value = text_from_any(receipt.get("normalized_env_proof"))
    proof_path = project_file(project, value) if value else normalized_env_proof_path(project, data, args)
    proof = read_json(proof_path)
    if not isinstance(proof, dict):
        raise RunnerError("normalized env proof must contain a JSON object")
    cli_version = read_cli_version(project, args.cli)
    validate_env_proof(
        proof,
        now_ms=now_ms(),
        required_lane=required_smoke_lane(data, args),
        cli_path=args.cli,
        cli_version=cli_version,
        auth_subject=text_from_any(proof.get("auth_subject")),
    )
    return receipt


def last_receipt(project: Path, data: dict[str, Any], stage: str) -> dict[str, Any]:
    return read_json(receipt_path(project, stage, data), {})


def same_cli_path(left: str, right: str) -> bool:
    if left == right:
        return True
    left_path = Path(left).expanduser()
    right_path = Path(right).expanduser()
    if not left_path.is_absolute():
        left_path = repo_root() / left_path
    if not right_path.is_absolute():
        right_path = repo_root() / right_path
    return left_path.resolve(strict=False) == right_path.resolve(strict=False)


def receipt_matches_current_fingerprint(
    project: Path, data: dict[str, Any], stage: str, args: argparse.Namespace | None = None
) -> bool:
    if args is None:
        args = default_runner_args()
    receipt = last_receipt(project, data, stage)
    fingerprint = receipt.get("input_fingerprint")
    if not isinstance(fingerprint, dict):
        return False
    if fingerprint.get("schema_version") != STAGE_FINGERPRINT_SCHEMA:
        return False
    current = stage_input_fingerprint(stage, project, args)
    return fingerprint.get("digest") == current.get("digest")


def require_fresh_receipt(
    project: Path,
    data: dict[str, Any],
    stage: str,
    allowed_statuses: set[str],
    args: argparse.Namespace | None = None,
) -> dict[str, Any]:
    receipt = last_receipt(project, data, stage)
    status = text_from_any(receipt.get("status"))
    if status not in allowed_statuses:
        allowed = "/".join(sorted(allowed_statuses))
        raise RunnerError(f"stage requires a {allowed} {stage} receipt")
    if not receipt_matches_current_fingerprint(project, data, stage, args):
        raise RunnerError(f"{stage} receipt is stale")
    return receipt


def parse_expiry_ms(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = int(value)
        return numeric * 1000 if 0 < numeric < 10_000_000_000 else numeric
    text = text_from_any(value)
    if not text:
        return None
    if text.isdigit():
        return parse_expiry_ms(int(text))
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except ValueError:
        return None


def validate_legacy_waiver(waiver: Any, *, now: int | None = None, require_codes: bool = False) -> dict[str, Any]:
    if now is None:
        now = now_ms()
    if not isinstance(waiver, dict):
        return {"active": False, "reason": "waiver must be a JSON object"}
    missing = [key for key in ["owner", "reason", "expires_at"] if not text_from_any(waiver.get(key))]
    if require_codes and not isinstance(waiver.get("codes"), list):
        missing.append("codes")
    if missing:
        return {"active": False, "reason": f"waiver missing required fields: {', '.join(missing)}"}
    expires_at_ms = parse_expiry_ms(waiver.get("expires_at"))
    if expires_at_ms is None:
        return {"active": False, "reason": "waiver expires_at is invalid"}
    if expires_at_ms <= now:
        return {"active": False, "reason": "waiver expired", "expires_at_ms": expires_at_ms}
    return {
        "active": True,
        "owner": text_from_any(waiver.get("owner")),
        "reason": text_from_any(waiver.get("reason")),
        "expires_at": waiver.get("expires_at"),
        "expires_at_ms": expires_at_ms,
        "codes": waiver.get("codes") if isinstance(waiver.get("codes"), list) else [],
    }


def resolved_validation_profile(data: dict[str, Any], args: argparse.Namespace | None = None) -> str:
    explicit = text_from_any(get_arg(args, "validation_profile", ""))
    if explicit:
        return explicit
    profile = data.get("validation_profile")
    if isinstance(profile, dict):
        return text_from_any(profile.get("profile") or profile.get("mode")) or "authoring"
    if isinstance(profile, str):
        return profile.strip() or "authoring"
    return "authoring"


def is_production_lane(data: dict[str, Any], args: argparse.Namespace | None = None) -> bool:
    if resolved_validation_profile(data, args) == "production":
        return True
    strategy = data.get("asset_strategy")
    if isinstance(strategy, dict) and strategy.get("mode") == "production_asset_strict":
        return True
    pages = data.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            mode = nested(page, ["visual_plan", "asset_contract", "mode"])
            if mode == "production_asset_strict":
                return True
    return False


def is_authoring_or_debug_lane(data: dict[str, Any], args: argparse.Namespace | None = None) -> bool:
    return not is_production_lane(data, args) and resolved_validation_profile(data, args) in {
        "authoring",
        "debug",
        "dev",
        "development",
        "local",
        "",
    }


def allow_preview_lint_waiver(data: dict[str, Any], args: argparse.Namespace | None = None) -> bool:
    if is_production_lane(data, args):
        return False
    return bool(get_arg(args, "allow_missing_preview_lint", False)) or resolved_validation_profile(data, args) == "debug"


def preview_lint_waiver_receipt(reason: str) -> dict[str, Any]:
    started = now_ms()
    return {
        "status": "waived",
        "reason": reason,
        "waiver": {
            "type": "missing_preview_lint",
            "owner": "svglide_project_runner",
            "reason": reason,
            "expires_at_ms": started + PREVIEW_LINT_WAIVER_TTL_MS,
        },
        "summary": {"error_count": 0, "warning_count": 0},
    }


def preview_lint_waiver_active(receipt: dict[str, Any]) -> bool:
    waiver = receipt.get("waiver")
    if not isinstance(waiver, dict):
        return False
    expires_at_ms = waiver.get("expires_at_ms")
    if not isinstance(expires_at_ms, int) or isinstance(expires_at_ms, bool):
        return False
    return expires_at_ms > now_ms()


def quality_gate_waivers_active(receipt: dict[str, Any]) -> bool:
    waivers = receipt.get("waivers")
    if not isinstance(waivers, list):
        return False
    for waiver in waivers:
        if not isinstance(waiver, dict):
            return False
        expires_at_ms = waiver.get("expires_at_ms")
        if not isinstance(expires_at_ms, int) or isinstance(expires_at_ms, bool) or expires_at_ms <= now_ms():
            return False
    return True


def require_latest_prepare(project: Path, data: dict[str, Any]) -> None:
    prepare = last_receipt(project, data, "prepare")
    if prepare.get("status") != "passed":
        raise RunnerError("stage requires a passed prepare receipt")
    if not receipt_matches_current_fingerprint(project, data, "prepare"):
        raise RunnerError("prepare receipt is stale after source SVG changes")


def require_latest_quality_gate(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> dict[str, Any]:
    quality = require_fresh_receipt(project, data, "quality_gate", {"passed", "passed_with_waiver"}, args)
    if quality.get("status") == "passed_with_waiver":
        if is_production_lane(data, args) or not quality_gate_waivers_active(quality):
            raise RunnerError("quality_gate waiver is not reusable")
    return quality


def require_strict_quality_gate(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> dict[str, Any]:
    return require_fresh_receipt(project, data, "quality_gate", {"passed"}, args)


def require_latest_dry_run(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> None:
    require_latest_quality_gate(project, data, args)
    require_fresh_receipt(project, data, "dry_run", {"passed"}, args)


def run_live_create(project: Path, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_live:
        raise RunnerError("live-create requires --allow-live")
    if args.env != "ppe_pure_svg":
        raise RunnerError("this rollout only allows --env ppe_pure_svg")
    previous = last_receipt(project, data, "live_create")
    if previous.get("status") == "passed" and previous.get("xml_presentation_id") and not args.force_live:
        raise RunnerError("live-create already succeeded; use readback or pass --force-live to create another document")
    require_latest_dry_run(project, data, args)
    require_strict_quality_gate(project, data, args)
    require_latest_ppe_proof(project, data, args)
    env = command_env(args)
    auth = {"verified": True, "source": "ppe_proof", "summary": last_receipt(project, data, "ppe_proof").get("summary")}
    write_env_receipt(project, data, args, env, auth)
    if proxy_status(env)["status"] == "missing":
        raise RunnerError("ppe_pure_svg live-create requires HTTP_PROXY/HTTPS_PROXY or --proxy")
    proof = load_env_proof(str(normalized_env_proof_path(project, data, args)))
    if not proof.get("verified"):
        raise RunnerError(f"ppe_pure_svg live-create requires verified normalized --env-proof: {proof.get('reason') or proof.get('checks')}")
    pending = {"stage": "live_create", "status": "pending", "input_digest": current_input_digest(project, data, prepared=True)}
    write_json(receipt_path(project, "live_create", data), pending)
    create_args = build_create_svg_command(project, data, args.cli, dry_run=False)
    result = run_command(create_args, cwd=repo_root(), env=env)
    log_path(project, "live_create").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    if result.returncode != 0:
        raise RunnerError(f"live-create failed: {result.returncode}; see {log_path(project, 'live_create')}")
    fields = live_create_fields(parsed)
    return {
        "status": "passed",
        "command": create_args,
        "log": str(log_path(project, "live_create").relative_to(project)),
        "summary": parsed,
        **fields,
    }


def run_readback(project: Path, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    live = last_receipt(project, data, "live_create")
    xml_presentation_id = live.get("xml_presentation_id")
    if not xml_presentation_id:
        raise RunnerError("readback requires live-create receipt with xml_presentation_id")
    env = command_env(args)
    params = json.dumps({"xml_presentation_id": xml_presentation_id}, ensure_ascii=False)
    readback_args = [args.cli, "slides", "xml_presentations", "get", "--as", "user", "--params", params, "--format", "json"]
    result = run_command(readback_args, cwd=repo_root(), env=env)
    log_path(project, "readback").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    if result.returncode != 0:
        raise RunnerError(f"readback failed: {result.returncode}; see {log_path(project, 'readback')}")
    slide_count = None
    revision_id = None
    if isinstance(parsed, dict):
        presentation = nested(parsed, ["data", "xml_presentation"])
        if isinstance(presentation, dict):
            content = presentation.get("content")
            revision_id = presentation.get("revision_id")
            if isinstance(content, str):
                slide_count = content.count("<slide id=")
    body = {
        "status": "passed",
        "command": readback_args,
        "log": str(log_path(project, "readback").relative_to(project)),
        "summary": parsed,
        "xml_presentation_id": xml_presentation_id,
        "url": live.get("url"),
        "revision_id": revision_id or live.get("revision_id"),
        "slide_count": slide_count,
    }
    maybe_update_readback_snapshot(project, data, body)
    return body


def raster_report_path(project: Path, data: dict[str, Any]) -> Path:
    for key in ["raster_report", "rasterization_report"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return project_artifact_path(project, value, must_exist=True, suffix=".json")
    artifacts = data.get("visual_artifacts")
    if isinstance(artifacts, dict) and isinstance(artifacts.get("raster_report"), str):
        return project_artifact_path(project, artifacts["raster_report"], must_exist=True, suffix=".json")
    candidates = sorted(project.glob("**/raster-report.json"))
    if not candidates:
        candidates = sorted((repo_root() / ".lark-slides" / "rasterized").glob("*/raster-report.json"))
    if len(candidates) == 1:
        return safe_existing_file(candidates[0], suffix=".json", root=repo_root())
    if not candidates:
        raise RunnerError("render-contact-sheet requires raster-report.json; set project_manifest.raster_report")
    raise RunnerError("render-contact-sheet found multiple raster-report.json files; set project_manifest.raster_report")


def report_artifact(project: Path, report: dict[str, Any], key: str, *, suffix: str) -> Path:
    artifacts = report.get("visual_artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get(key), str) or not artifacts[key].strip():
        raise RunnerError(f"raster-report.json missing visual_artifacts.{key}")
    return project_artifact_path(project, artifacts[key], must_exist=True, suffix=suffix)


def first_generated_png(project: Path, report: dict[str, Any]) -> Path | None:
    candidates: list[str] = []
    generated = report.get("generated_assets")
    if isinstance(generated, list):
        candidates.extend(item for item in generated if isinstance(item, str))
    pages = report.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict) and isinstance(page.get("pngs"), list):
                candidates.extend(item for item in page["pngs"] if isinstance(item, str))
    for value in candidates:
        try:
            return project_artifact_path(project, value.lstrip("@"), must_exist=True, suffix=".png")
        except RunnerError:
            continue
    return None


def ensure_preview_artifact(project: Path, report_path: Path, report: dict[str, Any], key: str) -> Path:
    artifacts = report.setdefault("visual_artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        report["visual_artifacts"] = artifacts
    value = artifacts.get(key)
    if isinstance(value, str) and value.strip():
        return project_artifact_path(project, value, must_exist=True, suffix=".png")
    fallback = first_generated_png(project, report)
    if fallback is None:
        raise RunnerError(f"raster-report.json missing visual_artifacts.{key}")
    artifacts[key] = rel_artifact(fallback)
    write_json(report_path, report)
    return fallback


def ensure_readback_snapshot_artifact(project: Path, data: dict[str, Any], report_path: Path, report: dict[str, Any]) -> Path:
    artifacts = report.setdefault("visual_artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        report["visual_artifacts"] = artifacts
    value = artifacts.get("readback_snapshot")
    if isinstance(value, str) and value.strip():
        return project_artifact_path(project, value, must_exist=True, suffix=".json")
    readback = last_receipt(project, data, "readback")
    if readback.get("status") != "passed":
        raise RunnerError("raster-report.json missing visual_artifacts.readback_snapshot")
    output = report_path.parent / "readback-snapshot.json"
    write_json(output, readback)
    artifacts["readback_snapshot"] = rel_artifact(output)
    write_json(report_path, report)
    return output


def maybe_update_readback_snapshot(project: Path, data: dict[str, Any], readback_body: dict[str, Any]) -> None:
    try:
        report_path = raster_report_path(project, data)
    except RunnerError:
        return
    report = read_json(report_path, {})
    if not isinstance(report, dict):
        return
    artifacts = report.setdefault("visual_artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        report["visual_artifacts"] = artifacts
    output = report_path.parent / "readback-snapshot.json"
    write_json(output, readback_body)
    artifacts["readback_snapshot"] = rel_artifact(output)
    write_json(report_path, report)


def contact_sheet_output_path(project: Path, data: dict[str, Any], report: dict[str, Any], report_path: Path) -> Path:
    artifacts = report.get("visual_artifacts")
    if isinstance(artifacts, dict) and isinstance(artifacts.get("contact_sheet"), str) and artifacts["contact_sheet"].strip():
        return project_artifact_path(project, artifacts["contact_sheet"], must_exist=False, suffix=".png")
    manifest_artifacts = data.get("visual_artifacts")
    if isinstance(manifest_artifacts, dict) and isinstance(manifest_artifacts.get("contact_sheet"), str):
        return project_artifact_path(project, manifest_artifacts["contact_sheet"], must_exist=False, suffix=".png")
    value = data.get("contact_sheet")
    if isinstance(value, str) and value.strip():
        return project_artifact_path(project, value, must_exist=False, suffix=".png")
    return report_path.parent / "contact-sheet.png"


def update_report_contact_sheet(project: Path, report_path: Path, report: dict[str, Any], output: Path) -> None:
    artifacts = report.setdefault("visual_artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        report["visual_artifacts"] = artifacts
    artifacts["contact_sheet"] = rel_artifact(output)
    write_json(report_path, report)


def run_render_contact_sheet(project: Path, data: dict[str, Any]) -> dict[str, Any]:
    report_path = raster_report_path(project, data)
    report = read_json(report_path)
    if not isinstance(report, dict):
        raise RunnerError(f"raster-report.json must contain an object: {report_path}")
    quality = report.get("quality")
    if isinstance(quality, dict) and quality.get("gate_passed") is False:
        raise RunnerError("render-contact-sheet blocked because raster-report.json quality.gate_passed=false")

    rich_preview = ensure_preview_artifact(project, report_path, report, "rich_preview")
    safe_preview = ensure_preview_artifact(project, report_path, report, "safe_preview")
    readback_snapshot = ensure_readback_snapshot_artifact(project, data, report_path, report)
    readback_data = read_json(readback_snapshot)
    if not isinstance(readback_data, dict):
        raise RunnerError(f"readback snapshot must contain a JSON object: {readback_snapshot}")

    rich_dimensions = png_dimensions(rich_preview)
    safe_dimensions = png_dimensions(safe_preview)
    output = contact_sheet_output_path(project, data, report, report_path)
    render_contact_sheet_png(output, [("rich preview", rich_preview), ("safe preview", safe_preview)])
    output = safe_existing_file(output, suffix=".png", root=repo_root())
    contact_dimensions = png_dimensions(output)
    update_report_contact_sheet(project, report_path, report, output)
    return {
        "status": "passed",
        "raster_report": rel_artifact(report_path),
        "rich_preview": rel_artifact(rich_preview),
        "safe_preview": rel_artifact(safe_preview),
        "readback_snapshot": rel_artifact(readback_snapshot),
        "contact_sheet": rel_artifact(output),
        "dimensions": {
            "rich_preview": rich_dimensions,
            "safe_preview": safe_dimensions,
            "contact_sheet": contact_dimensions,
        },
    }


def nested(data: dict[str, Any], path: list[str]) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def live_create_fields(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {"xml_presentation_id": None, "url": None, "revision_id": None, "slide_ids": None}
    data = parsed.get("data")
    if not isinstance(data, dict):
        data = {}
    return {
        "xml_presentation_id": parsed.get("xml_presentation_id")
        or parsed.get("presentation_id")
        or data.get("xml_presentation_id")
        or data.get("presentation_id"),
        "url": parsed.get("url") or data.get("url"),
        "revision_id": parsed.get("revision_id") or data.get("revision_id"),
        "slide_ids": parsed.get("slide_ids") or data.get("slide_ids"),
    }


def run_preview_lint(project: Path, data: dict[str, Any], args: argparse.Namespace | None = None) -> dict[str, Any]:
    require_latest_prepare(project, data)
    command = stage_command(data, "preview_lint")
    if command:
        raise RunnerError("stage_commands.preview_lint is not supported; preview_lint is runner-owned")
    script = repo_root() / "skills" / "lark-slides" / "scripts" / "svg_preview_lint.py"
    if not script.exists():
        if allow_preview_lint_waiver(data, args):
            return preview_lint_waiver_receipt("skipped_missing_tool")
        raise RunnerError("preview_lint requires bundled svg_preview_lint.py")
    preview = project / "preview" / "preview.html"
    if not preview.exists():
        if allow_preview_lint_waiver(data, args):
            return preview_lint_waiver_receipt("missing preview/preview.html")
        raise RunnerError("preview_lint requires preview/preview.html")
    result = run_command(
        [sys.executable, str(script), "--project", str(project), "--preview", str(preview), "--plan", str(plan_file(project, data))],
        cwd=repo_root(),
    )
    log_path(project, "preview_lint").write_text(result.stdout + result.stderr, encoding="utf-8")
    parsed = parse_json_output(result.stdout)
    if result.returncode != 0:
        raise RunnerError(f"preview_lint failed: {result.returncode}; see {log_path(project, 'preview_lint')}")
    return {"status": "passed", "log": str(log_path(project, "preview_lint").relative_to(project)), "summary": parsed}


def execute_stage(stage: str, project: Path, data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    started = now_ms()
    ensure_project_dirs(project)
    if stage == "generate":
        body = run_manifest_command(project, data, "generate")
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=False, args=args)
    if stage == "prepare":
        body = run_prepare(project, data)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=False, args=args)
    if stage == "preview":
        require_latest_prepare(project, data)
        body = run_manifest_command(project, data, "preview")
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "preflight":
        body = run_preflight(project, data)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "preview_lint":
        body = run_preview_lint(project, data, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "quality_gate":
        body = run_quality_gate(project, data, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "dry_run":
        body = run_dry_run(project, data, args.cli, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "ppe_proof":
        body = run_ppe_proof(project, data, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "live_create":
        body = run_live_create(project, data, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "readback":
        body = run_readback(project, data, args)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    if stage == "render_contact_sheet":
        body = run_render_contact_sheet(project, data)
        return write_stage_receipt(project, data, stage, started, body, prepared_digest=True, args=args)
    raise RunnerError(f"unimplemented stage: {stage}")


def stages_until(until: str) -> list[str]:
    until = normalize_stage(until)
    return STAGES[: STAGES.index(until) + 1]


def should_skip_existing(project: Path, data: dict[str, Any], stage: str, args: argparse.Namespace | None = None) -> bool:
    receipt = last_receipt(project, data, stage)
    status = text_from_any(receipt.get("status"))
    if status == "skipped":
        return False
    if status == "waived":
        if stage != "preview_lint" or not allow_preview_lint_waiver(data, args) or not preview_lint_waiver_active(receipt):
            return False
    elif status == "passed_with_waiver":
        if stage != "quality_gate" or is_production_lane(data, args) or not quality_gate_waivers_active(receipt):
            return False
    elif status != "passed":
        return False
    if not receipt_matches_current_fingerprint(project, data, stage, args):
        return False
    if stage == "ppe_proof":
        try:
            require_latest_ppe_proof(project, data, args or default_runner_args())
        except RunnerError:
            return False
    return True


def record_cache_hit(project: Path, stage: str, receipt: dict[str, Any]) -> None:
    cached = dict(receipt)
    cached["elapsed_ms"] = 0
    cached["cache_hit"] = True
    update_timings(project, stage, cached)


def run_pipeline(args: argparse.Namespace) -> int:
    project = project_path(args.project)
    data = manifest(project)
    for stage in stages_until(args.until):
        if args.resume and should_skip_existing(project, data, stage, args):
            record_cache_hit(project, stage, last_receipt(project, data, stage))
            print(f"{stage}: skipped existing receipt")
            continue
        receipt = execute_stage(stage, project, data, args)
        print(f"{stage}: {receipt.get('status')} ({receipt.get('elapsed_ms')} ms)")
        if receipt.get("status") == "skipped":
            raise RunnerError(f"required stage skipped: {stage}: {receipt.get('reason')}")
    return 0


def run_single_stage(args: argparse.Namespace, stage: str) -> int:
    project = project_path(args.project)
    data = manifest(project)
    receipt = execute_stage(stage, project, data, args)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", required=True, help="Path to .lark-slides/plan/<deck-id>")
    parser.add_argument("--cli", default="./lark-cli", help="Path to lark-cli binary")
    parser.add_argument("--env", default="", help="Target environment, e.g. ppe_pure_svg")
    parser.add_argument("--env-proof-input", default="", help="Raw JSON proof that PPE routing and headers were verified")
    parser.add_argument("--env-proof", default="", help="Normalized env-proof receipt path; defaults to receipts/env-proof.json")
    parser.add_argument("--proxy", default="", help="Optional HTTP(S) proxy for live/readback commands")
    parser.add_argument("--allow-live", action="store_true", help="Allow live-create stage to call online APIs")
    parser.add_argument("--force-live", action="store_true", help="Allow live-create even when a successful live receipt exists")
    parser.add_argument("--allow-missing-preview-lint", action="store_true", help="Allow preview_lint to emit a temporary waiver")
    parser.add_argument("--validation-profile", default="", help="Override project validation profile, e.g. authoring/debug/production")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SVGlide project pipeline with receipts and timings.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run stages through --until")
    add_common_args(run)
    run.add_argument("--until", default="dry_run", help="Last stage to run")
    run.add_argument("--resume", action="store_true", help="Reuse passed receipts when input digests match")

    for stage in STAGES:
        stage_parser = sub.add_parser(stage.replace("_", "-"), help=f"Run only {stage}")
        add_common_args(stage_parser)
        stage_parser.set_defaults(single_stage=stage)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run_pipeline(args)
        stage = getattr(args, "single_stage", None)
        if stage:
            return run_single_stage(args, stage)
        parser.error("unknown command")
        return 2
    except RunnerError as error:
        print(f"svglide_project_runner: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
