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


CHECK_VERSION = "svglide-pre-submit-review/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_GUARDRAILS_PATH = SCRIPT_DIR.parent / "references" / "svglide-template-guardrails.json"
PLAN_PATH = Path("02-plan/slide_plan.json")
QUALITY_GATE_PATH = Path("06-check/quality-gate.json")
THEME_ADHERENCE_PATH = Path("06-check/theme-adherence.json")
VISUAL_DISTINCTNESS_PATH = Path("06-check/visual-distinctness.json")
VISUAL_ACCEPTANCE_PATH = Path("06-check/visual-acceptance.json")
VISUAL_ACCEPTANCE_RECEIPT_PATH = Path("receipts/visual_acceptance.json")
PREPARED_SVG_DIR = Path("04-svg/prepared")
CONTACT_SHEET_PATH = Path("05-preview/contact-sheet.png")
PREVIEW_PATH = Path("05-preview/preview.html")
PREVIEW_MANIFEST_PATH = Path("05-preview/preview-manifest.json")
DRY_RUN_PATH = Path("07-create/dry-run.json")
OUTPUT_PATH = Path("06-check/pre-submit-review.json")
RECEIPT_PATH = Path("receipts/pre-submit-review.json")

REQUIRED_HUMAN_CHECKS = [
    "visual_acceptance",
    "intent_acceptance",
    "text_readability",
    "asset_chart_reasonableness",
    "worth_live_submit",
]

ARTIFACT_PATHS = {
    "contact_sheet": CONTACT_SHEET_PATH,
    "preview": PREVIEW_PATH,
    "preview_manifest": PREVIEW_MANIFEST_PATH,
    "quality_gate": QUALITY_GATE_PATH,
    "visual_acceptance": VISUAL_ACCEPTANCE_PATH,
}

PROTECTED_RERUN_BOUNDARIES = [
    "Do not edit runner scripts for this receipt.",
    "Do not weaken quality_gate/theme checks to make review pass.",
    "Do not mutate prepared SVG or preview artifacts after human review; rerun from the named stage instead.",
]


class PreSubmitReviewFatalError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(stage: str, code: str, message: str, *, category: str) -> dict[str, str]:
    return {
        "stage": stage,
        "code": code,
        "category": category,
        "message": message,
    }


def read_json_object(path: Path, issues: list[dict[str, str]], *, stage: str, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            issues.append(issue(stage, f"{stage}_missing", f"required JSON file is missing: {path}", category="missing_input"))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        issues.append(issue(stage, f"{stage}_invalid_json", f"invalid JSON in {path}: {error}", category="invalid_input"))
        return {}
    except OSError as error:
        issues.append(issue(stage, f"{stage}_read_failed", f"could not read {path}: {error}", category="invalid_input"))
        return {}
    if not isinstance(payload, dict):
        issues.append(issue(stage, f"{stage}_not_object", f"expected JSON object: {path}", category="invalid_input"))
        return {}
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def optional_sha256(path: Path) -> str | None:
    return file_sha256(path) if path.exists() and path.is_file() else None


def normalize_hash_records(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    records: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rel = item.get("path") or item.get("prepared")
        sha = item.get("sha256")
        if not isinstance(rel, str) or not isinstance(sha, str):
            return None
        records.append({"path": rel, "sha256": sha})
    return sorted(records, key=lambda item: item["path"])


def normalize_prepared_reviewed_artifact(value: Any) -> list[dict[str, str]] | None:
    if isinstance(value, dict):
        if isinstance(value.get("files"), list):
            return normalize_hash_records(value.get("files"))
        if isinstance(value.get("artifacts"), list):
            return normalize_hash_records(value.get("artifacts"))
        if isinstance(value.get("path"), str) or isinstance(value.get("prepared"), str):
            return normalize_hash_records([value])
    return normalize_hash_records(value)


def sorted_hash_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(records, key=lambda item: item["path"])


def normalize_reviewed_artifacts(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return None
    normalized: dict[str, Any] = {}
    prepared: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            return None
        kind = item.get("kind")
        path = item.get("path")
        sha = item.get("sha256")
        if not isinstance(kind, str) or not isinstance(path, str) or not isinstance(sha, str):
            return None
        record = {"path": path, "sha256": sha}
        if kind == "prepared_svg":
            prepared.append(record)
        elif kind in ARTIFACT_PATHS:
            normalized[kind] = record
        else:
            normalized[kind] = record
    if prepared:
        normalized["prepared_svg"] = prepared
    return normalized


def validate_hash_value(
    issues: list[dict[str, str]],
    *,
    stage: str,
    code: str,
    field: str,
    expected: str | None,
    actual: Any,
    path_label: str,
) -> None:
    if not isinstance(actual, str) or not actual:
        issues.append(issue(stage, f"{code}_missing", f"human review must include {field}", category="missing_input"))
        return
    if expected is None:
        issues.append(issue(stage, f"{code}_target_missing", f"cannot verify {field}; target file is missing: {path_label}", category="missing_input"))
        return
    if actual != expected:
        issues.append(issue(stage, f"{code}_stale", f"{field} does not match current {path_label}", category="stale_hash"))


def validate_human_checks(human: dict[str, Any], issues: list[dict[str, str]]) -> dict[str, Any]:
    approval = human.get("human_approval") if isinstance(human.get("human_approval"), dict) else {}
    if approval.get("approved") is not True:
        issues.append(
            issue(
                "human_review",
                "human_approval_not_approved",
                "human_approval.approved must be true",
                category="human_rejected",
            )
        )

    checks = human.get("checks") if isinstance(human.get("checks"), dict) else {}
    check_statuses: dict[str, Any] = {}
    if not checks:
        issues.append(issue("human_review", "human_checks_missing", "human review must include checks", category="missing_input"))
    for name in REQUIRED_HUMAN_CHECKS:
        check = checks.get(name) if isinstance(checks, dict) else None
        status = check.get("status") if isinstance(check, dict) else None
        check_statuses[name] = status
        if status != "passed":
            issues.append(
                issue(
                    "human_review",
                    f"{name}_not_passed",
                    f"checks.{name}.status must be passed",
                    category="human_rejected" if status == "failed" else "missing_input",
                )
            )
    if isinstance(checks, dict):
        for name, check in checks.items():
            if name in REQUIRED_HUMAN_CHECKS:
                continue
            if not isinstance(name, str) or not isinstance(check, dict) or "status" not in check:
                continue
            status = check.get("status")
            check_statuses[name] = status
            if status != "passed":
                safe_name = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_") or "extra_check"
                issues.append(
                    issue(
                        "human_review",
                        f"{safe_name}_not_passed",
                        f"checks.{name}.status must be passed",
                        category="human_rejected" if status == "failed" else "missing_input",
                    )
                )
    return {
        "approved": approval.get("approved"),
        "checks": check_statuses,
    }


def validate_current_check(
    payload: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    stage: str,
    path: Path,
    project: Path,
    current_plan_sha: str | None,
    current_prepared: list[dict[str, str]],
    require_prepared_when_present: bool = True,
) -> None:
    if not payload:
        return
    if payload.get("status") != "passed":
        issues.append(issue(stage, f"{stage}_not_passed", f"{path.as_posix()} status must be passed", category="check_not_passed"))
    summary = payload.get("summary")
    if isinstance(summary, dict):
        error_count = summary.get("error_count")
        if isinstance(error_count, int) and not isinstance(error_count, bool) and error_count > 0:
            issues.append(issue(stage, f"{stage}_has_errors", f"{path.as_posix()} summary.error_count is {error_count}", category="check_not_passed"))
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
    plan_sha = payload.get("plan_sha256") or inputs.get("plan_sha256")
    if plan_sha is not None and plan_sha != current_plan_sha:
        issues.append(issue(stage, f"{stage}_plan_stale", f"{path.as_posix()} plan_sha256 does not match current slide_plan.json", category="stale_hash"))
    if require_prepared_when_present and "prepared_files" in payload:
        recorded = normalize_hash_records(payload.get("prepared_files"))
        if recorded is None or recorded != sorted_hash_records(current_prepared):
            issues.append(issue(stage, f"{stage}_prepared_stale", f"{path.as_posix()} prepared_files do not match current prepared SVG files", category="stale_hash"))
    output_path = project / path
    if output_path.exists() and not output_path.is_file():
        issues.append(issue(stage, f"{stage}_not_file", f"{path.as_posix()} must be a file", category="invalid_input"))


def validate_quality_gate(
    payload: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    current_prepared: list[dict[str, str]],
) -> None:
    if not payload:
        return
    if payload.get("status") != "passed":
        issues.append(issue("quality_gate", "quality_gate_not_passed", "quality gate status must be passed", category="check_not_passed"))
    recorded = normalize_hash_records(payload.get("prepared_files"))
    if recorded is None or recorded != sorted_hash_records(current_prepared):
        issues.append(
            issue(
                "quality_gate",
                "quality_gate_prepared_stale",
                "quality gate prepared_files do not match current prepared SVG files",
                category="stale_hash",
            )
        )
    checks = payload.get("checks")
    if isinstance(checks, list):
        by_name = {item.get("name"): item for item in checks if isinstance(item, dict)}
        visual = by_name.get("visual-distinctness")
        if visual is None:
            issues.append(issue("quality_gate", "quality_gate_visual_distinctness_missing", "quality gate must include visual-distinctness check", category="missing_input"))
        elif visual.get("status") not in {"passed", "passed_with_waiver"}:
            issues.append(issue("quality_gate", "quality_gate_visual_distinctness_not_passed", "quality gate visual-distinctness check must be passed", category="check_not_passed"))


def validate_preview_manifest(
    manifest: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    project: Path,
    current_prepared: list[dict[str, str]],
) -> None:
    if not manifest:
        return
    expected_paths = [record["path"] for record in current_prepared]
    if manifest.get("page_count") != len(current_prepared):
        issues.append(
            issue(
                "preview",
                "preview_manifest_page_count_stale",
                "preview manifest page_count does not match current prepared SVG count",
                category="stale_hash",
            )
        )
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        issues.append(issue("preview", "preview_manifest_pages_missing", "preview manifest must include pages", category="missing_input"))
        return
    source_paths = [page.get("source_path") for page in pages if isinstance(page, dict)]
    if source_paths != expected_paths:
        issues.append(
            issue(
                "preview",
                "preview_manifest_sources_stale",
                "preview manifest source_path list does not match current prepared SVG files",
                category="stale_hash",
            )
        )
    for page in pages:
        if not isinstance(page, dict):
            issues.append(issue("preview", "preview_manifest_page_invalid", "preview manifest pages must be objects", category="invalid_input"))
            continue
        source_path = page.get("source_path")
        if not isinstance(source_path, str):
            continue
        actual_path = project / source_path
        if not actual_path.exists():
            issues.append(issue("preview", "preview_manifest_source_missing", f"preview source is missing: {source_path}", category="missing_input"))
            continue
        source_bytes = page.get("source_bytes")
        if isinstance(source_bytes, int) and not isinstance(source_bytes, bool) and source_bytes != actual_path.stat().st_size:
            issues.append(
                issue(
                    "preview",
                    "preview_manifest_source_bytes_stale",
                    f"preview source_bytes is stale for {source_path}",
                    category="stale_hash",
                )
            )


def validate_visual_acceptance(
    payload: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    project: Path,
    current_plan_sha: str | None,
    current_artifact_hashes: dict[str, str | None],
) -> None:
    if not payload:
        return
    status = payload.get("status")
    action = payload.get("action")
    if status == "passed":
        if payload.get("deliverable_pass") is not True:
            issues.append(
                issue(
                    "visual_acceptance",
                    "visual_acceptance_deliverable_not_passed",
                    "passed visual acceptance must set deliverable_pass true",
                    category="check_not_passed",
                )
            )
    elif status == "skipped" and action == "engineering_only":
        if payload.get("deliverable_pass") is not False:
            issues.append(
                issue(
                    "visual_acceptance",
                    "visual_acceptance_skip_boundary_invalid",
                    "skipped visual acceptance must set deliverable_pass false",
                    category="invalid_input",
                )
            )
    else:
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_not_passed",
                f"{VISUAL_ACCEPTANCE_PATH.as_posix()} status must be passed, or skipped only for engineering_only output",
                category="check_not_passed",
            )
        )

    summary = payload.get("summary")
    if isinstance(summary, dict):
        error_count = summary.get("error_count")
        if isinstance(error_count, int) and not isinstance(error_count, bool) and error_count > 0:
            issues.append(
                issue(
                    "visual_acceptance",
                    "visual_acceptance_has_errors",
                    f"{VISUAL_ACCEPTANCE_PATH.as_posix()} summary.error_count is {error_count}",
                    category="check_not_passed",
                )
            )

    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
    artboard_required = payload.get("generation_mode") == "artboard_satori" and status == "passed"
    plan_sha = payload.get("plan_sha256") or inputs.get("slide_plan_sha256") or inputs.get("plan_sha256")
    if plan_sha is not None and plan_sha != current_plan_sha:
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_plan_stale",
                "visual acceptance slide_plan_sha256 does not match current slide_plan.json",
                category="stale_hash",
            )
        )

    input_artifact_keys = {
        "quality_gate": "quality_gate_sha256",
        "preview": "preview_sha256",
        "preview_manifest": "preview_manifest_sha256",
        "dry_run": "dry_run_sha256",
    }
    for name, hash_key in input_artifact_keys.items():
        recorded = inputs.get(hash_key)
        if recorded is not None and recorded != current_artifact_hashes.get(name):
            issues.append(
                issue(
                    "visual_acceptance",
                    f"visual_acceptance_{name}_stale",
                    f"visual acceptance {hash_key} does not match current artifact",
                    category="stale_hash",
                )
            )

    guardrails_sha = inputs.get("template_guardrails_sha256")
    current_guardrails_sha = file_sha256(TEMPLATE_GUARDRAILS_PATH) if TEMPLATE_GUARDRAILS_PATH.exists() else None
    if artboard_required and (not isinstance(guardrails_sha, str) or not guardrails_sha):
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_template_guardrails_missing",
                "passed artboard visual acceptance must include template_guardrails_sha256",
                category="missing_input",
            )
        )
    elif guardrails_sha is not None and guardrails_sha != current_guardrails_sha:
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_template_guardrails_stale",
                "visual acceptance template_guardrails_sha256 does not match current guardrail registry",
                category="stale_hash",
            )
        )

    contact = inputs.get("contact_sheet")
    if isinstance(contact, dict):
        if contact.get("sha256") != current_artifact_hashes.get("contact_sheet"):
            issues.append(
                issue(
                    "visual_acceptance",
                    "visual_acceptance_contact_sheet_stale",
                    "visual acceptance contact_sheet.sha256 does not match current contact sheet",
                    category="stale_hash",
                )
            )

    check_path = project / VISUAL_ACCEPTANCE_PATH
    receipt_path = project / VISUAL_ACCEPTANCE_RECEIPT_PATH
    if not receipt_path.exists():
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_receipt_missing",
                f"required visual acceptance receipt is missing: {VISUAL_ACCEPTANCE_RECEIPT_PATH.as_posix()}",
                category="missing_input",
            )
        )
    elif check_path.exists() and file_sha256(receipt_path) != file_sha256(check_path):
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_receipt_disagrees",
                "visual acceptance receipt must match current visual acceptance check",
                category="stale_hash",
            )
        )

    artboard_artifacts = payload.get("artboard_artifacts")
    if artboard_required and not isinstance(artboard_artifacts, list):
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_artboard_artifacts_missing",
                "visual acceptance must record artboard artifact hashes",
                category="missing_input",
            )
        )
        return
    visual_evidence = payload.get("visual_evidence")
    evidence_pages = visual_evidence.get("pages") if isinstance(visual_evidence, dict) else None
    if artboard_required and (not isinstance(evidence_pages, list) or not evidence_pages):
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_visual_evidence_missing",
                "visual acceptance must record page-level visual_evidence.pages",
                category="missing_input",
            )
        )
    elif artboard_required and isinstance(evidence_pages, list):
        for item in evidence_pages:
            if not isinstance(item, dict):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_page_invalid",
                        "visual acceptance visual_evidence.pages entries must be objects",
                        category="invalid_input",
                    )
                )
                continue
            if not isinstance(item.get("page"), int) or not isinstance(item.get("evidence_path"), str) or not item.get("evidence_path"):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_page_target_missing",
                        "visual acceptance visual_evidence.pages entries must include page and evidence_path",
                        category="missing_input",
                    )
                )
            if not isinstance(item.get("preview_anchor"), str) or not item.get("preview_anchor"):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_preview_anchor_missing",
                        "visual acceptance visual_evidence.pages entries must include preview_anchor",
                        category="missing_input",
                    )
                )
            page_preview_sha = item.get("preview_sha256")
            page_preview_manifest_sha = item.get("preview_manifest_sha256")
            if not isinstance(page_preview_sha, str) or not page_preview_sha:
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_preview_hash_missing",
                        "visual acceptance visual_evidence.pages entries must include preview_sha256",
                        category="missing_input",
                    )
                )
            elif isinstance(inputs.get("preview_sha256"), str) and page_preview_sha != inputs.get("preview_sha256"):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_preview_hash_stale",
                        "visual acceptance visual_evidence.pages preview_sha256 does not match current preview evidence",
                        category="stale_hash",
                    )
                )
            if not isinstance(page_preview_manifest_sha, str) or not page_preview_manifest_sha:
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_preview_manifest_hash_missing",
                        "visual acceptance visual_evidence.pages entries must include preview_manifest_sha256",
                        category="missing_input",
                    )
                )
            elif isinstance(inputs.get("preview_manifest_sha256"), str) and page_preview_manifest_sha != inputs.get("preview_manifest_sha256"):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_preview_manifest_hash_stale",
                        "visual acceptance visual_evidence.pages preview_manifest_sha256 does not match current preview manifest evidence",
                        category="stale_hash",
                    )
                )
            if not isinstance(item.get("contact_sheet_tile"), dict):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_visual_evidence_tile_missing",
                        "visual acceptance visual_evidence.pages entries must include contact_sheet_tile",
                        category="missing_input",
                    )
                )
    deck_rhythm = payload.get("deck_rhythm")
    if artboard_required and (not isinstance(deck_rhythm, dict) or deck_rhythm.get("schema_version") != "svglide-deck-rhythm/v1"):
        issues.append(
            issue(
                "visual_acceptance",
                "visual_acceptance_deck_rhythm_missing",
                "passed artboard visual acceptance must include deck_rhythm",
                category="missing_input",
            )
        )
    if isinstance(artboard_artifacts, list):
        for item in artboard_artifacts:
            if not isinstance(item, dict):
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_artboard_artifact_invalid",
                        "visual acceptance artboard_artifacts entries must be objects",
                        category="invalid_input",
                    )
                )
                continue
            rel = item.get("path")
            recorded = item.get("sha256")
            if not isinstance(rel, str) or not rel or not isinstance(recorded, str) or not recorded:
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_artboard_artifact_record_invalid",
                        "visual acceptance artboard artifact records must include path and sha256",
                        category="invalid_input",
                    )
                )
                continue
            target = project / rel
            if not target.exists() or not target.is_file():
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_artboard_artifact_missing",
                        f"visual acceptance artifact is missing: {rel}",
                        category="missing_input",
                    )
                )
                continue
            if file_sha256(target) != recorded:
                issues.append(
                    issue(
                        "visual_acceptance",
                        "visual_acceptance_artboard_artifact_stale",
                        f"visual acceptance artifact hash is stale: {rel}",
                        category="stale_hash",
                    )
                )


def validate_single_reviewed_artifact(
    reviewed: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    project: Path,
    name: str,
    expected_rel: Path,
) -> dict[str, Any]:
    record = reviewed.get(name)
    expected_path = expected_rel.as_posix()
    evidence: dict[str, Any] = {"name": name, "expected_path": expected_path, "matched": False}
    if not isinstance(record, dict):
        issues.append(issue("human_review", f"reviewed_artifact_{name}_missing", f"reviewed_artifacts.{name} is required", category="missing_input"))
        return evidence
    rel = record.get("path")
    expected_sha = record.get("sha256")
    evidence["path"] = rel
    evidence["expected_sha256"] = expected_sha
    if rel != expected_path:
        issues.append(issue("human_review", f"reviewed_artifact_{name}_path_invalid", f"reviewed_artifacts.{name}.path must be {expected_path}", category="invalid_input"))
        return evidence
    if not isinstance(expected_sha, str) or not expected_sha:
        issues.append(issue("human_review", f"reviewed_artifact_{name}_sha256_missing", f"reviewed_artifacts.{name}.sha256 is required", category="missing_input"))
        return evidence
    path = project / expected_rel
    if not path.exists():
        issues.append(issue("artifacts", f"{name}_missing", f"artifact is missing: {expected_path}", category="missing_input"))
        return evidence
    actual_sha = file_sha256(path)
    evidence["sha256"] = actual_sha
    evidence["matched"] = expected_sha == actual_sha
    if expected_sha != actual_sha:
        issues.append(issue("human_review", f"reviewed_artifact_{name}_stale", f"reviewed_artifacts.{name}.sha256 does not match current {expected_path}", category="stale_hash"))
    return evidence


def validate_reviewed_artifacts(
    human: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    project: Path,
    current_prepared: list[dict[str, str]],
) -> list[dict[str, Any]]:
    reviewed = normalize_reviewed_artifacts(human.get("reviewed_artifacts"))
    evidence: list[dict[str, Any]] = []
    if not reviewed:
        issues.append(issue("human_review", "reviewed_artifacts_missing", "human review must include reviewed_artifacts", category="missing_input"))
        return evidence

    prepared_record = normalize_prepared_reviewed_artifact(reviewed.get("prepared_svg"))
    expected_prepared = sorted_hash_records(current_prepared)
    evidence.append({"name": "prepared_svg", "expected_files": expected_prepared, "files": prepared_record, "matched": prepared_record == expected_prepared})
    if prepared_record is None:
        issues.append(issue("human_review", "reviewed_artifact_prepared_svg_invalid", "reviewed_artifacts.prepared_svg must include path/sha256 records", category="invalid_input"))
    elif prepared_record != expected_prepared:
        issues.append(issue("human_review", "reviewed_artifact_prepared_svg_stale", "reviewed_artifacts.prepared_svg does not match current prepared SVG files", category="stale_hash"))

    for name, expected_rel in ARTIFACT_PATHS.items():
        evidence.append(
            validate_single_reviewed_artifact(
                reviewed,
                issues,
                project=project,
                name=name,
                expected_rel=expected_rel,
            )
        )
    return evidence


def validate_human_bindings(
    human: dict[str, Any],
    issues: list[dict[str, str]],
    *,
    project: Path,
    current_plan_sha: str | None,
    current_quality_gate_sha: str | None,
    current_prepared: list[dict[str, str]],
) -> None:
    validate_hash_value(
        issues,
        stage="human_review",
        code="human_plan_sha256",
        field="plan_sha256",
        expected=current_plan_sha,
        actual=human.get("plan_sha256"),
        path_label=PLAN_PATH.as_posix(),
    )
    validate_hash_value(
        issues,
        stage="human_review",
        code="human_quality_gate_sha256",
        field="quality_gate_sha256",
        expected=current_quality_gate_sha,
        actual=human.get("quality_gate_sha256"),
        path_label=QUALITY_GATE_PATH.as_posix(),
    )
    recorded_prepared = normalize_hash_records(human.get("prepared_files"))
    if recorded_prepared is None:
        issues.append(issue("human_review", "human_prepared_files_missing", "human review must include prepared_files path/sha256 records", category="missing_input"))
    elif recorded_prepared != sorted_hash_records(current_prepared):
        issues.append(issue("human_review", "human_prepared_files_stale", "human review prepared_files do not match current prepared SVG files", category="stale_hash"))

    reviewed_artifacts = normalize_reviewed_artifacts(human.get("reviewed_artifacts")) or {}
    quality_gate_review = reviewed_artifacts.get("quality_gate") if isinstance(reviewed_artifacts, dict) else None
    if isinstance(quality_gate_review, dict) and quality_gate_review.get("sha256") != human.get("quality_gate_sha256"):
        issues.append(issue("human_review", "human_quality_gate_hash_disagrees", "quality_gate_sha256 must match reviewed_artifacts.quality_gate.sha256", category="stale_hash"))

    if current_prepared and not (project / PREPARED_SVG_DIR).exists():
        issues.append(issue("prepared_svg", "prepared_svg_dir_missing", f"missing {PREPARED_SVG_DIR.as_posix()}", category="missing_input"))


def validate_required_artifacts(project: Path, issues: list[dict[str, str]], *, current_prepared: list[dict[str, str]]) -> None:
    if not (project / PREPARED_SVG_DIR).exists():
        issues.append(issue("prepared_svg", "prepared_svg_dir_missing", f"missing {PREPARED_SVG_DIR.as_posix()}", category="missing_input"))
    elif not current_prepared:
        issues.append(issue("prepared_svg", "prepared_svg_missing", f"no prepared SVG files found under {PREPARED_SVG_DIR.as_posix()}", category="missing_input"))

    for name, rel in ARTIFACT_PATHS.items():
        path = project / rel
        if not path.exists():
            issues.append(issue("artifacts", f"{name}_missing", f"required artifact is missing: {rel.as_posix()}", category="missing_input"))
        elif not path.is_file():
            issues.append(issue("artifacts", f"{name}_not_file", f"required artifact must be a file: {rel.as_posix()}", category="invalid_input"))


def minimal_rerun_from(issues: list[dict[str, str]]) -> str:
    if not issues:
        return "none"
    codes = {item.get("code") for item in issues}
    stages = {item.get("stage") for item in issues}
    if any(code in codes for code in {"human_review_missing", "human_approval_not_approved"}) or "human_review" in stages and not any(item.get("category") == "stale_hash" for item in issues):
        return "collect_pre_submit_human_review"
    if any(code and "prepared" in code for code in codes):
        return "prepare_svg_then_preview_quality_gate_and_human_review"
    if any(code and "preview" in code for code in codes):
        return "preview_then_human_review"
    if any(code and "visual_acceptance" in code for code in codes) or "visual_acceptance" in stages:
        return "scoped_visual_repair_then_visual_acceptance_and_human_review"
    if any(code and "quality_gate" in code for code in codes) or "quality_gate" in stages:
        return "quality_gate_then_human_review"
    if "theme_adherence" in stages:
        return "theme_adherence_then_quality_gate_and_human_review"
    if "visual_distinctness" in stages:
        return "visual_distinctness_then_quality_gate_and_human_review"
    return "rerun_from_first_failed_stage"


def build_failure_triage(issues: list[dict[str, str]]) -> dict[str, Any]:
    primary = issues[0] if issues else {}
    return {
        "primary_failure_stage": primary.get("stage", "unknown"),
        "failure_category": primary.get("category", "unknown"),
        "minimal_rerun_from": minimal_rerun_from(issues),
        "do_not_touch": PROTECTED_RERUN_BOUNDARIES,
        "blocking_issue_codes": [item.get("code") for item in issues[:10]],
    }


def run_pre_submit_review(project: Path, human_review: Path) -> dict[str, Any]:
    project = project.resolve()
    if not project.exists() or not project.is_dir():
        raise PreSubmitReviewFatalError(f"project_root does not exist or is not a directory: {project}")

    issues: list[dict[str, str]] = []
    current_prepared = prepared_file_hashes(project)
    current_plan_sha = optional_sha256(project / PLAN_PATH)
    current_quality_gate_sha = optional_sha256(project / QUALITY_GATE_PATH)
    current_theme_sha = optional_sha256(project / THEME_ADHERENCE_PATH)
    current_visual_sha = optional_sha256(project / VISUAL_DISTINCTNESS_PATH)
    current_visual_acceptance_sha = optional_sha256(project / VISUAL_ACCEPTANCE_PATH)
    current_artifact_hashes = {
        name: optional_sha256(project / rel)
        for name, rel in ARTIFACT_PATHS.items()
    }
    current_artifact_hashes["dry_run"] = optional_sha256(project / DRY_RUN_PATH)

    plan = read_json_object(project / PLAN_PATH, issues, stage="plan")
    quality_gate = read_json_object(project / QUALITY_GATE_PATH, issues, stage="quality_gate")
    theme_adherence = read_json_object(project / THEME_ADHERENCE_PATH, issues, stage="theme_adherence")
    visual_distinctness = read_json_object(project / VISUAL_DISTINCTNESS_PATH, issues, stage="visual_distinctness")
    visual_acceptance = read_json_object(project / VISUAL_ACCEPTANCE_PATH, issues, stage="visual_acceptance")
    preview_manifest = read_json_object(project / PREVIEW_MANIFEST_PATH, issues, stage="preview")
    human = read_json_object(human_review, issues, stage="human_review")

    validate_required_artifacts(project, issues, current_prepared=current_prepared)
    validate_quality_gate(quality_gate, issues, current_prepared=current_prepared)
    validate_current_check(
        theme_adherence,
        issues,
        stage="theme_adherence",
        path=THEME_ADHERENCE_PATH,
        project=project,
        current_plan_sha=current_plan_sha,
        current_prepared=current_prepared,
    )
    validate_current_check(
        visual_distinctness,
        issues,
        stage="visual_distinctness",
        path=VISUAL_DISTINCTNESS_PATH,
        project=project,
        current_plan_sha=current_plan_sha,
        current_prepared=current_prepared,
        require_prepared_when_present=False,
    )
    validate_visual_acceptance(
        visual_acceptance,
        issues,
        project=project,
        current_plan_sha=current_plan_sha,
        current_artifact_hashes=current_artifact_hashes,
    )
    validate_preview_manifest(preview_manifest, issues, project=project, current_prepared=current_prepared)

    human_summary: dict[str, Any] = {"approved": None, "checks": {}}
    reviewed_evidence: list[dict[str, Any]] = []
    human_sha = optional_sha256(human_review)
    if human:
        human_summary = validate_human_checks(human, issues)
        validate_human_bindings(
            human,
            issues,
            project=project,
            current_plan_sha=current_plan_sha,
            current_quality_gate_sha=current_quality_gate_sha,
            current_prepared=current_prepared,
        )
        reviewed_evidence = validate_reviewed_artifacts(human, issues, project=project, current_prepared=current_prepared)

    result: dict[str, Any] = {
        "version": CHECK_VERSION,
        "stage": "pre_submit_review",
        "status": "failed" if issues else "passed",
        "checked_at": now_iso(),
        "project": str(project),
        "human_review": {
            "path": relpath(human_review, project),
            "sha256": human_sha,
        },
        "inputs": {
            "plan": PLAN_PATH.as_posix(),
            "plan_sha256": current_plan_sha,
            "quality_gate": QUALITY_GATE_PATH.as_posix(),
            "quality_gate_sha256": current_quality_gate_sha,
            "theme_adherence": THEME_ADHERENCE_PATH.as_posix(),
            "theme_adherence_sha256": current_theme_sha,
            "visual_distinctness": VISUAL_DISTINCTNESS_PATH.as_posix(),
            "visual_distinctness_sha256": current_visual_sha,
            "visual_acceptance": VISUAL_ACCEPTANCE_PATH.as_posix(),
            "visual_acceptance_sha256": current_visual_acceptance_sha,
            "prepared_svg_dir": PREPARED_SVG_DIR.as_posix(),
            "contact_sheet": CONTACT_SHEET_PATH.as_posix(),
            "contact_sheet_sha256": current_artifact_hashes["contact_sheet"],
            "preview": PREVIEW_PATH.as_posix(),
            "preview_sha256": current_artifact_hashes["preview"],
            "preview_manifest": PREVIEW_MANIFEST_PATH.as_posix(),
            "preview_manifest_sha256": current_artifact_hashes["preview_manifest"],
        },
        "plan_title": plan.get("title"),
        "human_approval": human_summary,
        "prepared_files": current_prepared,
        "reviewed_artifacts": reviewed_evidence,
        "summary": {
            "issue_count": len(issues),
            "prepared_svg_count": len(current_prepared),
        },
        "issues": issues,
        "outputs": {
            "check": OUTPUT_PATH.as_posix(),
            "receipt": RECEIPT_PATH.as_posix(),
        },
    }
    if issues:
        result["failure_triage"] = build_failure_triage(issues)

    write_json(project / OUTPUT_PATH, result)
    write_json(project / RECEIPT_PATH, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate structured human pre-submit review receipt freshness.")
    parser.add_argument("project_root", help="SVGlide project root")
    parser.add_argument("--human-review", required=True, type=Path, help="human review JSON path")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        result = run_pre_submit_review(Path(args.project_root), args.human_review)
    except (OSError, PreSubmitReviewFatalError) as error:
        print(f"svglide_pre_submit_review: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=args.pretty))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
