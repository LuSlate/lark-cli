#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


QUALITY_GATE = Path("06-check/quality-gate.json")
DRY_RUN = Path("07-create/dry-run.json")
PROOF_INPUT = Path("07-create/ppe-proof.input.json")
PROOF_OUTPUT = Path("07-create/ppe-proof.json")


class PPEProofError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PPEProofError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PPEProofError(f"invalid JSON in {path}: expected object")
    return payload


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def proof_issues(proof: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if proof.get("status") != "passed":
        issues.append(issue("ppe_status_not_passed", "ppe proof input status must be passed"))
    for key in ["environment", "auth", "proxy", "headers", "route"]:
        value = proof.get(key)
        if not isinstance(value, dict) or not value:
            issues.append(issue(f"ppe_{key}_missing", f"ppe proof input requires non-empty {key} object"))
    environment = proof.get("environment")
    if isinstance(environment, dict) and environment.get("name") != "Pre_release":
        issues.append(issue("ppe_environment_not_pre_release", "ppe proof environment.name must be Pre_release"))
    headers = proof.get("headers")
    if isinstance(headers, dict) and headers.get("x-tt-env") != "ppe_pure_svg":
        issues.append(issue("ppe_header_missing_x_tt_env", "ppe proof headers.x-tt-env must be ppe_pure_svg"))
    return issues


def run_ppe_proof(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    issues: list[dict[str, str]] = []
    quality_gate = project / QUALITY_GATE
    dry_run = project / DRY_RUN
    proof_file = project / PROOF_INPUT
    if not quality_gate.exists():
        issues.append(issue("quality_gate_missing", "quality gate must exist before PPE proof"))
    if not dry_run.exists():
        issues.append(issue("dry_run_missing", "dry-run receipt must exist before PPE proof"))
    proof: dict[str, Any] = {}
    if proof_file.exists():
        proof = read_json_object(proof_file)
        issues.extend(proof_issues(proof))
    else:
        issues.append(issue("ppe_proof_input_missing", "07-create/ppe-proof.input.json is required before live create"))
    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-ppe-proof/v1",
        "status": status,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "quality_gate": QUALITY_GATE.as_posix() if quality_gate.exists() else None,
            "quality_gate_sha256": file_sha256(quality_gate) if quality_gate.exists() else None,
            "dry_run": DRY_RUN.as_posix() if dry_run.exists() else None,
            "dry_run_sha256": file_sha256(dry_run) if dry_run.exists() else None,
            "proof_input": PROOF_INPUT.as_posix() if proof_file.exists() else None,
            "proof_input_sha256": file_sha256(proof_file) if proof_file.exists() else None,
        },
        "proof": proof,
        "summary": {"error_count": len(issues)},
        "issues": issues,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-ppe-proof.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["issues"].extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])
    output = project / PROOF_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate PPE/auth/proxy/header proof before SVGlide live create.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_ppe_proof(Path(args.project))
    except (OSError, PPEProofError) as error:
        print(f"svglide_ppe_proof: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
