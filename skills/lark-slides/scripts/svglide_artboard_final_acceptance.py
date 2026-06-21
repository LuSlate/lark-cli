#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CHECK_VERSION = "svglide-artboard-final-acceptance/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
DEFAULT_PLAN = Path("/Users/bytedance/Downloads/PLAN.md")
FINAL_CHECK = Path("06-check/final-acceptance-check.json")
FINAL_RECEIPT = Path("receipts/final-acceptance-check.json")
ACTION_GUIDE = REFERENCES_DIR / "svglide-artboard-full-plan-action.md"
SCOPE_DEFERRALS = REFERENCES_DIR / "svglide-artboard-gate12-scope.md"
PACKAGE_RECEIPT = SCRIPT_DIR / "fixtures/svglide_artboard/gate11_package/receipts/artboard-package-check.json"
INSTRUCTION_PROJECT = REPO_ROOT / ".tmp/svglide-p0c-gate7-live6"
INSTRUCTION_ADHERENCE_CHECK = INSTRUCTION_PROJECT / "06-check/instruction-adherence.json"
INSTRUCTION_ADHERENCE_RECEIPT = INSTRUCTION_PROJECT / "receipts/instruction-adherence.json"

REQUIRED_GATE_EVIDENCE = {
    "0": "svglide-artboard-gate0-gate1-evidence.md",
    "1": "svglide-artboard-gate0-gate1-evidence.md",
    "2": "svglide-artboard-gate2-evidence.md",
    "3": "svglide-artboard-gate3-evidence.md",
    "4": "svglide-artboard-gate4-evidence.md",
    "5": "svglide-artboard-gate5-evidence.md",
    "6": "svglide-artboard-gate6-evidence.md",
    "7": "svglide-artboard-gate7-evidence.md",
    "8": "svglide-artboard-gate8-evidence.md",
    "9": "svglide-artboard-gate9-evidence.md",
    "10": "svglide-artboard-gate10-evidence.md",
    "11": "svglide-artboard-gate11-evidence.md",
    "12a": "svglide-artboard-gate12a-evidence.md",
}


class FinalAcceptanceError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise FinalAcceptanceError(f"missing JSON file: {path}") from err
    except json.JSONDecodeError as err:
        raise FinalAcceptanceError(f"invalid JSON file: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise FinalAcceptanceError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_rel(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def extract_gate_statuses(action_text: str) -> dict[str, dict[str, str]]:
    statuses: dict[str, dict[str, str]] = {}
    pattern = re.compile(r"^\| (?P<gate>\d+[a-z]?) [^|]* \| (?P<status>[^|]+) \| (?P<owner>[^|]+) \| (?P<verdict>[^|]+) \|", re.MULTILINE)
    for match in pattern.finditer(action_text):
        gate = match.group("gate")
        statuses[gate] = {
            "status": match.group("status").strip(),
            "owner": match.group("owner").strip(),
            "reviewer_verdict": match.group("verdict").strip(),
        }
    return statuses


def verify_hashed_file(
    issues: list[dict[str, str]],
    project: Path,
    label: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    rel = record.get("path")
    expected_sha = record.get("sha256")
    evidence = {"label": label, "path": rel, "matched": False}
    if not isinstance(rel, str) or not isinstance(expected_sha, str):
        issues.append({"code": "instruction_adherence_hash_record_invalid", "message": f"{label} hash record is incomplete"})
        return evidence
    path = project / rel
    evidence["exists"] = path.exists()
    if not path.exists():
        issues.append({"code": "instruction_adherence_hashed_file_missing", "message": f"{label} file missing: {rel}"})
        return evidence
    actual_sha = file_sha256(path)
    evidence["sha256"] = actual_sha
    evidence["matched"] = actual_sha == expected_sha
    if actual_sha != expected_sha:
        issues.append({"code": "instruction_adherence_hash_stale", "message": f"{label} hash is stale for {rel}"})
    return evidence


def validate_instruction_adherence_current(issues: list[dict[str, str]]) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "project": repo_rel(INSTRUCTION_PROJECT),
        "check_path": repo_rel(INSTRUCTION_ADHERENCE_CHECK),
        "receipt_path": repo_rel(INSTRUCTION_ADHERENCE_RECEIPT),
        "hash_checks": [],
    }
    if not INSTRUCTION_ADHERENCE_CHECK.exists():
        issues.append({"code": "instruction_adherence_check_missing", "message": f"missing {repo_rel(INSTRUCTION_ADHERENCE_CHECK)}"})
        return evidence
    if not INSTRUCTION_ADHERENCE_RECEIPT.exists():
        issues.append({"code": "instruction_adherence_receipt_missing", "message": f"missing {repo_rel(INSTRUCTION_ADHERENCE_RECEIPT)}"})
        return evidence

    check = read_json(INSTRUCTION_ADHERENCE_CHECK)
    receipt = read_json(INSTRUCTION_ADHERENCE_RECEIPT)
    evidence["status"] = check.get("status")
    evidence["receipt_status"] = receipt.get("status")
    if check.get("status") != "passed":
        issues.append({"code": "instruction_adherence_not_passed", "message": "instruction adherence check must have status=passed"})
    if receipt.get("status") != "passed":
        issues.append({"code": "instruction_adherence_receipt_not_passed", "message": "instruction adherence receipt must have status=passed"})
    if file_sha256(INSTRUCTION_ADHERENCE_CHECK) != file_sha256(INSTRUCTION_ADHERENCE_RECEIPT):
        issues.append({"code": "instruction_adherence_check_receipt_mismatch", "message": "instruction adherence check and receipt must match"})

    for label, key in (
        ("instruction", "instruction"),
        ("deck_plan", "deck_plan"),
        ("slide_plan", "slide_plan"),
        ("final_plan", "plan"),
    ):
        record = check.get(key)
        if isinstance(record, dict):
            evidence["hash_checks"].append(verify_hashed_file(issues, INSTRUCTION_PROJECT, label, record))
        else:
            issues.append({"code": "instruction_adherence_hash_record_missing", "message": f"missing {key} hash record"})

    for index, record in enumerate(check.get("output_pages") or []):
        if isinstance(record, dict):
            evidence["hash_checks"].append(verify_hashed_file(issues, INSTRUCTION_PROJECT, f"output_page_{index + 1}", record))
    readback = check.get("readback") if isinstance(check.get("readback"), dict) else {}
    for label, path_key, sha_key in (
        ("readback_check", "check_path", "check_sha256"),
        ("readback_raw", "raw_path", "raw_sha256"),
    ):
        evidence["hash_checks"].append(verify_hashed_file(issues, INSTRUCTION_PROJECT, label, {"path": readback.get(path_key), "sha256": readback.get(sha_key)}))
    binding_checks = readback.get("binding_checks")
    evidence["readback_binding_checks"] = binding_checks
    if not isinstance(binding_checks, list) or not binding_checks:
        issues.append({"code": "instruction_adherence_binding_missing", "message": "readback binding checks are missing from instruction adherence"})
    else:
        for item in binding_checks:
            if not isinstance(item, dict) or item.get("matched") is not True:
                issues.append({"code": "instruction_adherence_binding_stale", "message": "all readback binding checks must be matched=true"})
                break
    if check.get("issues"):
        issues.append({"code": "instruction_adherence_has_issues", "message": "instruction adherence issues must be empty"})
    return evidence


def validate_final_acceptance(plan_path: Path = DEFAULT_PLAN) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    evidence: list[dict[str, Any]] = []

    action_text = ACTION_GUIDE.read_text(encoding="utf-8") if ACTION_GUIDE.exists() else ""
    if not action_text:
        issues.append({"code": "action_guide_missing", "message": f"missing {repo_rel(ACTION_GUIDE)}"})
    statuses = extract_gate_statuses(action_text)
    gate_statuses: dict[str, Any] = {}
    for gate in [*(str(value) for value in range(0, 12)), "12a"]:
        status = statuses.get(gate)
        gate_statuses[gate] = status
        if status is None:
            issues.append({"code": "gate_status_missing", "message": f"Gate {gate} status is missing from action guide"})
            continue
        if status.get("status") != "DONE" or status.get("reviewer_verdict") != "PASS":
            issues.append({"code": "gate_not_passed", "message": f"Gate {gate} must be DONE/PASS before Gate 12 final acceptance"})

    seen_evidence: set[str] = set()
    for gate, name in REQUIRED_GATE_EVIDENCE.items():
        path = REFERENCES_DIR / name
        key = path.as_posix()
        if key not in seen_evidence:
            seen_evidence.add(key)
            evidence.append({"path": repo_rel(path), "exists": path.exists()})
        if not path.exists():
            issues.append({"code": "gate_evidence_missing", "message": f"Gate {gate} evidence file missing: {repo_rel(path)}"})

    if not PACKAGE_RECEIPT.exists():
        issues.append({"code": "package_receipt_missing", "message": f"missing {repo_rel(PACKAGE_RECEIPT)}"})
        package_status = None
    else:
        package_payload = read_json(PACKAGE_RECEIPT)
        package_status = package_payload.get("status")
        if package_status != "passed":
            issues.append({"code": "package_receipt_not_passed", "message": "Gate 11 package receipt must have status=passed"})

    if not SCOPE_DEFERRALS.exists():
        issues.append({"code": "scope_deferrals_missing", "message": f"missing {repo_rel(SCOPE_DEFERRALS)}"})
        deferral_text = ""
    else:
        deferral_text = SCOPE_DEFERRALS.read_text(encoding="utf-8")
        for marker in ("Owner:", "Target date:", "Not claimed:"):
            if marker not in deferral_text:
                issues.append({"code": "scope_deferrals_incomplete", "message": f"scope deferrals must include {marker}"})

    if not plan_path.exists():
        issues.append({"code": "plan_missing", "message": f"missing PLAN.md: {plan_path}"})
        plan_text = ""
    else:
        plan_text = plan_path.read_text(encoding="utf-8")
        if "Gate 12 Final Acceptance" not in plan_text and "Gate 12b Final Acceptance" not in plan_text:
            issues.append({"code": "plan_gate12_missing", "message": "PLAN.md must mention Gate 12/Gate 12b Final Acceptance"})
        if "不声称完整高质量 PPT 生成系统已完成" not in plan_text:
            issues.append({"code": "plan_scope_claim_missing", "message": "PLAN.md must explicitly avoid claiming full high-quality PPT generation completion"})
        if "svglide-artboard-gate12-scope.md" not in plan_text:
            issues.append({"code": "plan_deferral_reference_missing", "message": "PLAN.md must reference the Gate 12 explicit scope file"})
        if "Gate 12a reviewer PASS" not in plan_text and "Gate 12a Instruction/Plan/Output Adherence 已获得 reviewer PASS" not in plan_text:
            issues.append({"code": "plan_gate12a_pass_missing", "message": "PLAN.md must declare Gate 12a reviewer PASS before Gate 12b acceptance"})

    instruction_adherence = validate_instruction_adherence_current(issues)

    return {
        "version": CHECK_VERSION,
        "stage": "final_acceptance",
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "plan_path": plan_path.as_posix(),
        "gate_statuses": gate_statuses,
        "evidence_files": evidence,
        "package_receipt": {
            "path": repo_rel(PACKAGE_RECEIPT),
            "status": package_status,
        },
        "instruction_adherence": instruction_adherence,
        "scope": {
            "accepted_milestone": "P0/P1 artboard_satori implementation through Gate 12a reviewer PASS",
            "not_claimed": "complete high-quality PPT generation system with actual model-driven topic-to-deck loop",
            "deferrals_path": repo_rel(SCOPE_DEFERRALS),
        },
        "issues": issues,
    }


def write_check_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    write_json(output_dir / FINAL_CHECK, payload)
    write_json(output_dir / FINAL_RECEIPT, payload)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SVGlide artboard Gate 12 final acceptance evidence.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        payload = validate_final_acceptance(args.plan)
        if args.output_dir:
            write_check_outputs(args.output_dir, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    except FinalAcceptanceError as err:
        payload = {
            "version": CHECK_VERSION,
            "stage": "final_acceptance",
            "status": "failed",
            "checked_at": now_iso(),
            "issues": [{"code": "final_acceptance_error", "message": str(err)}],
        }
        if args.output_dir:
            write_check_outputs(args.output_dir, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
