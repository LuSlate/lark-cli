#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import svglide_schema


CHECK_DIR = Path("06-check")
QUALITY_GATE_NAME = "quality-gate.json"
PREPARED_SVG_DIR = Path("04-svg/prepared")
SOURCE_SVG_DIR = Path("04-svg")
PLAN_PATH = Path("02-plan/slide_plan.json")
EVIDENCE_PATH = Path("source/evidence.json")
SOURCE_RECEIPT_PATH = Path("source/source-receipt.json")
ASSET_MANIFEST_PATH = Path("03-assets/asset-manifest.json")
GENERATOR_RECEIPT_PATH = Path("receipts/generate_svg.json")
REQUIRED_CHECKS = [
    ("preflight", CHECK_DIR / "preflight.json"),
    ("preview-lint", CHECK_DIR / "preview-lint.json"),
    ("aesthetic-review", CHECK_DIR / "aesthetic-review.json"),
    ("runtime-review", CHECK_DIR / "runtime-review.json"),
    ("semantic-review", CHECK_DIR / "semantic-review.json"),
]
CHART_VERIFY_CHECK = ("chart-verify", CHECK_DIR / "chart-verify.json")
OPTIONAL_CHECKS = []
PASS_ACTION = "create_live"
FAIL_ACTIONS = {"repair_and_rerun", "failed", "fail"}
PRODUCTION_PROFILE = "production"
STRICT_PROFILES = {PRODUCTION_PROFILE, "production_live"}


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepared_file_hashes(project: Path) -> list[dict[str, str]]:
    svg_dir = project / PREPARED_SVG_DIR
    if not svg_dir.exists():
        return []
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "sha256": file_sha256(path),
        }
        for path in sorted(svg_dir.glob("*.svg"))
        if path.is_file()
    ]


def source_file_hashes(project: Path) -> list[dict[str, str]]:
    svg_dir = project / SOURCE_SVG_DIR
    if not svg_dir.exists():
        return []
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "sha256": file_sha256(path),
        }
        for path in sorted(svg_dir.glob("*.svg"))
        if path.is_file()
    ]


def optional_file_sha256(project: Path, rel: Path) -> str | None:
    path = project / rel
    return file_sha256(path) if path.exists() else None


def error_count_from_payload(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return None
    raw = summary.get("error_count")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def list_waivers(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("waivers")
    return raw if isinstance(raw, list) else []


def action_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("action") or payload.get("status")
    return raw if isinstance(raw, str) else None


def plan_requires_chart_verify(project: Path) -> bool | None:
    path = project / PLAN_PATH
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    slides = payload.get("slides") if isinstance(payload, dict) else None
    if not isinstance(slides, list):
        return None
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        contract = slide.get("chart_contract")
        if isinstance(contract, dict) and (contract.get("verify") == "required" or contract.get("precision") == "exact"):
            return True
    return False


def semantic_review_freshness_issues(project: Path, payload: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if payload.get("status") != "passed":
        issues.append(issue("semantic_review_not_passed", "semantic review status must be passed"))
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        issues.append(issue("semantic_review_inputs_missing", "semantic review must include inputs"))
        return issues
    if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
        issues.append(issue("semantic_review_plan_stale", "semantic review plan_sha256 does not match current slide_plan.json"))
    evidence_hash = optional_file_sha256(project, EVIDENCE_PATH)
    if inputs.get("evidence_sha256") != evidence_hash:
        issues.append(issue("semantic_review_evidence_stale", "semantic review evidence_sha256 does not match current source/evidence.json"))
    if payload.get("prepared_files") != prepared_file_hashes(project):
        issues.append(issue("semantic_review_prepared_stale", "semantic review prepared_files do not match current prepared SVG files"))
    inventory = payload.get("text_inventory")
    if not isinstance(inventory, str) or not (project / inventory).exists():
        issues.append(issue("semantic_review_text_inventory_missing", "semantic review must point to an existing text inventory"))
    return issues


def plan_bound_check_freshness_issues(project: Path, payload: dict[str, Any], name: str, *, prepared: bool) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if payload.get("status") != "passed":
        issues.append(issue(f"{name}_not_passed", f"{name} status must be passed"))
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        issues.append(issue(f"{name}_inputs_missing", f"{name} must include inputs"))
        return issues
    if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
        issues.append(issue(f"{name}_plan_stale", f"{name} plan_sha256 does not match current slide_plan.json"))
    if prepared and payload.get("prepared_files") != prepared_file_hashes(project):
        issues.append(issue(f"{name}_prepared_stale", f"{name} prepared_files do not match current prepared SVG files"))
    return issues


def load_generator_receipt(project: Path) -> dict[str, Any]:
    rel = GENERATOR_RECEIPT_PATH
    path = project / rel
    check: dict[str, Any] = {
        "name": "generator-receipt",
        "path": rel.as_posix(),
        "required": True,
        "status": "missing" if not path.exists() else "failed",
        "error_count": None,
        "action": None,
        "waivers": [],
        "issues": [],
    }
    if not path.exists():
        check["issues"].append(issue("missing_generator_receipt", "generator receipt is required"))
        return check
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        check["issues"].append(issue("invalid_generator_receipt_json", f"could not read generator receipt JSON: {error}"))
        return check
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-generator-receipt.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(payload, schema)
    check["issues"].extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues)
    if payload.get("status") != "passed":
        check["issues"].append(issue("generator_receipt_not_passed", "generator receipt status must be passed"))
    if payload.get("generated_files") != source_file_hashes(project):
        check["issues"].append(issue("generator_source_stale", "generator receipt generated_files do not match current source SVG files"))
    expected = {
        "plan_sha256": optional_file_sha256(project, PLAN_PATH),
        "evidence_sha256": optional_file_sha256(project, EVIDENCE_PATH),
        "asset_manifest_sha256": optional_file_sha256(project, ASSET_MANIFEST_PATH),
        "source_receipt_sha256": optional_file_sha256(project, SOURCE_RECEIPT_PATH),
    }
    for key, current in expected.items():
        if payload.get(key) != current:
            check["issues"].append(issue(f"generator_{key}_stale", f"generator receipt {key} does not match current project files"))
    generated = payload.get("generated_files")
    page_receipts = payload.get("page_receipts")
    if not isinstance(generated, list) or not generated:
        check["issues"].append(issue("generator_generated_files_missing", "generator receipt must include generated_files"))
    if not isinstance(page_receipts, list) or not page_receipts:
        check["issues"].append(issue("generator_page_receipts_missing", "generator receipt must include page_receipts"))
    elif isinstance(generated, list) and len(page_receipts) != len(generated):
        check["issues"].append(issue("generator_page_receipt_count_mismatch", "page_receipts count must match generated_files"))
    if isinstance(page_receipts, list):
        for item in page_receipts:
            if not isinstance(item, str):
                check["issues"].append(issue("generator_page_receipt_invalid", "page_receipts must be string paths"))
                continue
            page_receipt = project / item
            if not page_receipt.exists():
                check["issues"].append(issue("generator_page_receipt_missing", f"page receipt is missing: {item}"))
    check["error_count"] = len(check["issues"])
    check["status"] = "failed" if check["issues"] else "passed"
    return check


def load_check(project: Path, name: str, rel: Path, *, required: bool, profile: str) -> dict[str, Any]:
    path = project / rel
    check: dict[str, Any] = {
        "name": name,
        "path": relpath(path, project),
        "required": required,
        "status": "missing" if not path.exists() else "failed",
        "error_count": None,
        "action": None,
        "waivers": [],
        "issues": [],
    }
    if not path.exists():
        if required:
            check["issues"].append(issue("missing_check_file", f"required check file is missing: {rel.as_posix()}"))
        else:
            check["status"] = "skipped"
        return check
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        check["issues"].append(issue("invalid_check_json", f"could not read check JSON: {error}"))
        return check

    schema_names = {
        "semantic-review": "svglide-semantic-review.schema.json",
        "chart-verify": "svglide-chart-verify.schema.json",
        "runtime-review": "svglide-runtime-review.schema.json",
    }
    if name in schema_names:
        schema = svglide_schema.read_json(svglide_schema.schema_path(schema_names[name]))
        schema_issues = svglide_schema.validate_json_schema(payload, schema)
        if schema_issues:
            check["issues"].extend(issue(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues)
            return check

    error_count = error_count_from_payload(payload)
    if error_count is None:
        check["issues"].append(issue("missing_error_count", "check JSON must contain integer summary.error_count"))
        return check

    waivers = list_waivers(payload)
    action = action_from_payload(payload)
    check["error_count"] = error_count
    check["action"] = action
    check["waivers"] = waivers
    if error_count > 0:
        check["issues"].append(issue("check_has_errors", f"summary.error_count is {error_count}"))
        return check

    if name == "preview-lint" and action != PASS_ACTION:
        check["issues"].append(issue("preview_lint_action_not_create_live", f"preview lint action is {action!r}; expected {PASS_ACTION!r}"))
        return check

    if name == "aesthetic-review":
        if action in FAIL_ACTIONS:
            check["issues"].append(issue("aesthetic_review_blocks_create", f"aesthetic review action is {action!r}"))
            return check
        if action is not None and action != PASS_ACTION:
            check["issues"].append(issue("aesthetic_review_action_unknown", f"aesthetic review action is {action!r}; expected {PASS_ACTION!r} or repair action"))
            return check

    if name == "semantic-review" and isinstance(payload, dict):
        freshness = semantic_review_freshness_issues(project, payload)
        if freshness:
            check["issues"].extend(freshness)
            return check

    if name == "runtime-review" and isinstance(payload, dict):
        freshness = plan_bound_check_freshness_issues(project, payload, "runtime_review", prepared=False)
        if freshness:
            check["issues"].extend(freshness)
            return check

    if name == "chart-verify" and isinstance(payload, dict):
        freshness = plan_bound_check_freshness_issues(project, payload, "chart_verify", prepared=True)
        if freshness:
            check["issues"].extend(freshness)
            return check

    if name in {"chart-verify", "runtime-review", "semantic-review"} and action not in {PASS_ACTION, "passed"}:
        check["issues"].append(issue(f"{name.replace('-', '_')}_action_not_create_live", f"{name} action is {action!r}; expected {PASS_ACTION!r}"))
        return check

    if waivers:
        if name == "preflight":
            check["issues"].append(issue("preflight_waiver_not_allowed", "preflight waivers are not allowed"))
            return check
        if profile in STRICT_PROFILES:
            check["issues"].append(issue("production_waiver_not_allowed", "production profile does not accept waivers"))
            return check
        check["status"] = "passed_with_waiver"
        return check

    check["status"] = "passed"
    return check


def run_quality_gate(project: Path, *, profile: str = PRODUCTION_PROFILE) -> dict[str, Any]:
    project = project.resolve()
    checks = [load_generator_receipt(project)]
    checks.extend(load_check(project, name, rel, required=True, profile=profile) for name, rel in REQUIRED_CHECKS)
    chart_required = plan_requires_chart_verify(project)
    if chart_required is None:
        checks.append(
            {
                "name": "chart-verify-admission",
                "path": PLAN_PATH.as_posix(),
                "required": True,
                "status": "failed",
                "error_count": 1,
                "action": None,
                "waivers": [],
                "issues": [issue("chart_verify_requirement_unknown", "could not determine whether chart verification is required")],
            }
        )
    else:
        checks.append(load_check(project, *CHART_VERIFY_CHECK, required=chart_required, profile=profile))
    checks.extend(load_check(project, name, rel, required=False, profile=profile) for name, rel in OPTIONAL_CHECKS)
    failed_checks = [check for check in checks if check["status"] not in {"passed", "passed_with_waiver", "skipped"}]
    waiver_checks = [check for check in checks if check["status"] == "passed_with_waiver"]
    source_error_count = sum(check["error_count"] or 0 for check in checks)
    status = "failed" if failed_checks else "passed_with_waiver" if waiver_checks else "passed"
    output_path = project / CHECK_DIR / QUALITY_GATE_NAME
    result = {
        "version": "svglide-quality-gate/v1",
        "project": str(project),
        "profile": profile,
        "status": status,
        "inputs": {
            name.replace("-", "_"): rel.as_posix()
            for name, rel in REQUIRED_CHECKS + ([CHART_VERIFY_CHECK] if chart_required else []) + OPTIONAL_CHECKS
            if (project / rel).exists() or name in {item[0] for item in REQUIRED_CHECKS}
        },
        "prepared_files": prepared_file_hashes(project),
        "waivers": [
            {"check": check["name"], "waivers": check["waivers"]}
            for check in checks
            if check["waivers"]
        ],
        "summary": {
            "check_count": len(checks),
            "failed_check_count": len(failed_checks),
            "waiver_check_count": len(waiver_checks),
            "source_error_count": source_error_count,
        },
        "checks": checks,
        "output_path": relpath(output_path, project),
    }
    result["inputs"]["generator_receipt"] = GENERATOR_RECEIPT_PATH.as_posix()
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-quality-gate.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["summary"]["failed_check_count"] += 1
        result["checks"].append(
            {
                "name": "quality-gate-schema",
                "path": "06-check/quality-gate.json",
                "required": True,
                "status": "failed",
                "error_count": len(schema_issues),
                "action": None,
                "waivers": [],
                "issues": [issue(item["code"], f"{item['path']}: {item['message']}") for item in schema_issues],
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate SVGlide preflight and preview lint outputs.")
    parser.add_argument("project", help="SVGlide project directory containing 06-check/preflight.json and preview-lint.json")
    parser.add_argument("--profile", default=PRODUCTION_PROFILE, choices=["production", "debug", "preview_only", "production_live"])
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        result = run_quality_gate(Path(args.project), profile=args.profile)
    except OSError as error:
        print(f"svglide_quality_gate: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
