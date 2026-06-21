#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPORT_VERSION = "svglide-export-package/v1"
EXPORT_MANIFEST = Path("09-export/export-manifest.json")
EXPORT_ARCHIVE = Path("09-export/svglide-artifacts.zip")
EXPORT_RECEIPT = Path("receipts/export.json")
MANDATORY_INPUTS = [
    "02-plan/slide_plan.json",
    "06-check/quality-gate.json",
    "07-create/live-create.json",
    "08-readback/readback-check.json",
]
OPTIONAL_ARTIFACTS = [
    "00-input/instruction.json",
    "source/evidence.json",
    "source/research.md",
    "02-plan/deck-plan.json",
    "02-plan/canvas-plan.json",
    "02-plan/plan-confirmation.json",
    "02-plan/svglide.lock.json",
    "03-assets/assets.json",
    "03-assets/asset-manifest.json",
    "05-preview/preview.html",
    "05-preview/preview-manifest.json",
    "06-check/preflight.json",
    "06-check/preview-lint.json",
    "06-check/aesthetic-review.json",
    "06-check/chart-verify.json",
    "06-check/semantic-review.json",
    "06-check/runtime-review.json",
    "06-check/visual-distinctness.json",
    "06-check/theme-validate.json",
    "06-check/theme-adherence.json",
    "07-create/dry-run.json",
    "07-create/ppe-proof.json",
    "08-readback/xml-presentations-get.json",
]


class ExportPackageError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ExportPackageError(f"missing required file: {path}") from err
    except json.JSONDecodeError as err:
        raise ExportPackageError(f"invalid JSON in {path}: {err}") from err


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def optional_sha256(path: Path) -> str | None:
    return file_sha256(path) if path.exists() else None


def issue(code: str, message: str, *, path: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if path:
        payload["path"] = path
    return payload


def prepared_svg_files(project: Path) -> list[Path]:
    return sorted(path for path in (project / "04-svg" / "prepared").glob("*.svg") if path.is_file())


def prepared_file_hashes(project: Path) -> list[dict[str, str]]:
    return [{"path": relpath(path, project), "sha256": file_sha256(path)} for path in prepared_svg_files(project)]


def relpath(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def artifact_record(project: Path, rel: str) -> dict[str, Any] | None:
    path = project / rel
    if not path.is_file():
        return None
    return {"path": rel, "sha256": file_sha256(path), "bytes": path.stat().st_size}


def collect_artifacts(project: Path) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for rel in [*MANDATORY_INPUTS, *OPTIONAL_ARTIFACTS]:
        record = artifact_record(project, rel)
        if record is not None:
            records[rel] = record
    for directory in ["04-svg/prepared", "04-svg/artboard", "receipts"]:
        root = project / directory
        if root.exists():
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                rel = relpath(path, project)
                records[rel] = {"path": rel, "sha256": file_sha256(path), "bytes": path.stat().st_size}
    return [records[key] for key in sorted(records)]


def validate_inputs(project: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    for rel in MANDATORY_INPUTS:
        if not (project / rel).exists():
            issues.append(issue("export_input_missing", f"missing required export input {rel}", path=rel))
    if issues:
        return issues, {}

    quality_gate = read_json(project / "06-check/quality-gate.json")
    live_create = read_json(project / "07-create/live-create.json")
    readback = read_json(project / "08-readback/readback-check.json")

    if quality_gate.get("status") != "passed":
        issues.append(issue("quality_gate_not_passed", "quality gate must pass before export", path="06-check/quality-gate.json"))
    if live_create.get("status") != "passed":
        issues.append(issue("live_create_not_passed", "live create must pass before export", path="07-create/live-create.json"))
    if readback.get("status") != "passed":
        issues.append(issue("readback_not_passed", "readback must pass before export", path="08-readback/readback-check.json"))

    prepared_hashes = prepared_file_hashes(project)
    if not prepared_hashes:
        issues.append(issue("prepared_svg_missing", "export requires at least one prepared SVG", path="04-svg/prepared"))

    if isinstance(quality_gate.get("prepared_files"), list) and quality_gate.get("prepared_files") != prepared_hashes:
        issues.append(issue("quality_gate_prepared_files_stale", "prepared SVG files changed after quality gate", path="06-check/quality-gate.json"))
    if isinstance(live_create.get("prepared_files"), list) and live_create.get("prepared_files") != prepared_hashes:
        issues.append(issue("live_create_prepared_files_stale", "prepared SVG files changed after live create", path="07-create/live-create.json"))

    binding = readback.get("input_binding")
    if isinstance(binding, dict):
        expected = {
            "plan_sha256": optional_sha256(project / "02-plan/slide_plan.json"),
            "quality_gate_sha256": optional_sha256(project / "06-check/quality-gate.json"),
            "live_create_sha256": optional_sha256(project / "07-create/live-create.json"),
        }
        for key, value in expected.items():
            if binding.get(key) != value:
                issues.append(issue("readback_input_binding_stale", f"readback {key} does not match current export inputs", path="08-readback/readback-check.json"))
    else:
        issues.append(issue("readback_input_binding_missing", "readback check must include input_binding", path="08-readback/readback-check.json"))

    return issues, {
        "quality_gate": quality_gate,
        "live_create": live_create,
        "readback": readback,
        "prepared_files": prepared_hashes,
    }


def create_archive(project: Path, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    archive = project / EXPORT_ARCHIVE
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for record in artifacts:
            rel = record["path"]
            if rel.startswith("09-export/"):
                continue
            info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, (project / rel).read_bytes())
    return {"path": EXPORT_ARCHIVE.as_posix(), "sha256": file_sha256(archive), "bytes": archive.stat().st_size}


def run_export_package(project: Path, *, archive: bool = False) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    issues, validated = validate_inputs(project)
    artifacts = collect_artifacts(project)
    archive_record = create_archive(project, artifacts) if archive and not issues else None

    status = "passed" if not issues else "failed"
    result: dict[str, Any] = {
        "version": EXPORT_VERSION,
        "stage": "export",
        "status": status,
        "action": "handoff_package" if status == "passed" else "repair_and_rerun",
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan_sha256": optional_sha256(project / "02-plan/slide_plan.json"),
            "quality_gate_sha256": optional_sha256(project / "06-check/quality-gate.json"),
            "live_create_sha256": optional_sha256(project / "07-create/live-create.json"),
            "readback_check_sha256": optional_sha256(project / "08-readback/readback-check.json"),
        },
        "prepared_files": validated.get("prepared_files", prepared_file_hashes(project)),
        "artifacts": artifacts,
        "formats": {
            "svglide_artifact_package": {
                "status": "passed" if status == "passed" else "failed",
                "manifest": EXPORT_MANIFEST.as_posix(),
                "archive": archive_record,
            },
            "pptx": {
                "status": "not_implemented",
                "reason": "SVGlide export currently packages verified source artifacts; no local PPTX serializer is wired to this runner.",
            },
            "animated_deck": {
                "status": "not_implemented",
                "reason": "SVGlide SVG/readback pipeline has no animation timeline export contract.",
            },
            "narrated_deck": {
                "status": "not_implemented",
                "reason": "SVGlide SVG/readback pipeline has no speaker-audio or narration export contract.",
            },
        },
        "summary": {
            "error_count": len(issues),
            "artifact_count": len(artifacts),
            "prepared_svg_count": len(validated.get("prepared_files", prepared_file_hashes(project))),
            "archive_created": archive_record is not None,
        },
        "issues": issues,
    }
    write_json(project / EXPORT_MANIFEST, result)
    write_json(project / EXPORT_RECEIPT, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Package verified SVGlide project artifacts after live readback.")
    parser.add_argument("project")
    parser.add_argument("--archive", action="store_true", help="create a deterministic zip package under 09-export")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_export_package(Path(args.project), archive=args.archive)
    except (OSError, ExportPackageError) as error:
        print(f"svglide_export_package: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
