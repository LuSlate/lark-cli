#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
MATRIX_PATH = REFERENCES_DIR / "beautiful-template-executable-matrix.json"
DEFAULT_GALLERY_RECEIPT = REFERENCES_DIR / "receipts" / "production-review" / "beautiful-34-gallery.json"
DEFAULT_HUMAN_REVIEW_RECEIPT = REFERENCES_DIR / "receipts" / "production-review" / "beautiful-34-human-review.json"
SCHEMA_VERSION = "svglide-beautiful-human-review/v1"
ALLOWED_HUMAN_STATUS = ["pending", "pass", "needs_fix", "reject"]
ALLOWED_REVIEW_STATUS = set(ALLOWED_HUMAN_STATUS)


def read_json(path: Path) -> dict[str, Any]:
    payload = read_json_value(path)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def read_json_value(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalise_decisions(payload: object | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    raw = payload.get("decisions", payload.get("families", payload)) if isinstance(payload, dict) else payload
    decisions: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for family_id, value in raw.items():
            if isinstance(value, dict):
                decisions[str(family_id)] = value
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict) or not item.get("family_id"):
                continue
            decisions[str(item["family_id"])] = item
    return decisions


def _summary_counts(families: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in ALLOWED_HUMAN_STATUS}
    for family in families:
        status = str(family.get("human_review_status") or "pending")
        counts[status] = counts.get(status, 0) + 1
    return {
        "family_count": len(families),
        "status_counts": counts,
        "pending_count": counts.get("pending", 0),
        "pass_count": counts.get("pass", 0),
        "needs_fix_count": counts.get("needs_fix", 0),
        "reject_count": counts.get("reject", 0),
    }


def _matrix_status_summary() -> dict[str, Any]:
    matrix = read_json(MATRIX_PATH)
    rows = [row for row in _as_list(matrix.get("candidates")) if isinstance(row, dict)]
    production_default_families = [
        str(row.get("family_id"))
        for row in rows
        if row.get("promotion_status") == "production" and row.get("default_selectable") is True
    ]
    return {
        "matrix_candidate_count": len(rows),
        "production_count": sum(1 for row in rows if row.get("promotion_status") == "production"),
        "default_selectable_count": sum(1 for row in rows if row.get("default_selectable") is True),
        "production_default_selectable_count": len(production_default_families),
        "production_default_selectable_families": production_default_families,
    }


def _gallery_url(base_family: dict[str, Any]) -> object:
    if base_family.get("gallery_url"):
        return base_family.get("gallery_url")
    contact_sheet = base_family.get("contact_sheet")
    if isinstance(contact_sheet, dict):
        return contact_sheet.get("html_path")
    return None


def _review_family(base_family: dict[str, Any], decision: dict[str, Any], *, reviewer: str, reviewed_at: str) -> dict[str, Any]:
    status = str(decision.get("human_review_status") or decision.get("status") or base_family.get("human_review_status") or "pending")
    note = str(decision.get("human_review_note") or decision.get("note") or "").strip()
    issue_codes = [str(item) for item in _as_list(decision.get("issue_codes")) if str(item).strip()]
    if status not in ALLOWED_REVIEW_STATUS:
        status = "pending"
        issue_codes.append("invalid_human_review_status")
    validation_issues: list[str] = []
    if status in {"needs_fix", "reject"} and not note and not issue_codes:
        validation_issues.append("human_review_note_or_issue_codes_required")
    auto_gate_status = str(base_family.get("auto_gate_status") or "blocked")
    promotion_eligible = auto_gate_status == "passed" and status == "pass"
    return {
        "family_id": base_family.get("family_id"),
        "runtime_template_id": base_family.get("runtime_template_id"),
        "gallery_url": _gallery_url(base_family),
        "auto_gate_status": auto_gate_status,
        "allowed_human_status": ALLOWED_HUMAN_STATUS,
        "human_review_status": status,
        "human_review_note": note,
        "issue_codes": issue_codes,
        "reviewer": str(decision.get("reviewer") or reviewer),
        "reviewed_at": str(decision.get("reviewed_at") or reviewed_at),
        "promotion_eligible": promotion_eligible,
        "promotion_action": "candidate_for_m9_production_review" if promotion_eligible else "no_change",
        "known_blockers": _as_list(base_family.get("known_blockers")),
        "missing_roles": _as_list(base_family.get("missing_roles")),
        "evidence_hashes": base_family.get("evidence_hashes") if isinstance(base_family.get("evidence_hashes"), dict) else {},
        "validation_issues": validation_issues,
    }


def _promotion_candidates(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family_id": family["family_id"],
            "runtime_template_id": family["runtime_template_id"],
            "action": "create_separate_production_review_receipt",
            "reason": "auto_gate_status=passed and human_review_status=pass",
            "evidence_hashes": family["evidence_hashes"],
        }
        for family in families
        if family["promotion_eligible"]
    ]


def _fix_queue(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family_id": family["family_id"],
            "runtime_template_id": family["runtime_template_id"],
            "action": "fix_and_resubmit_human_review",
            "note": family["human_review_note"],
            "issue_codes": family["issue_codes"] or family["known_blockers"],
        }
        for family in families
        if family["human_review_status"] == "needs_fix"
    ]


def _reject_queue(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family_id": family["family_id"],
            "runtime_template_id": family["runtime_template_id"],
            "action": "keep_out_of_promotion_pool",
            "note": family["human_review_note"],
            "issue_codes": family["issue_codes"] or family["known_blockers"],
        }
        for family in families
        if family["human_review_status"] == "reject"
    ]


def _next_actions(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for family in families:
        status = family["human_review_status"]
        if status == "pending":
            actions.append(
                {
                    "family_id": family["family_id"],
                    "runtime_template_id": family["runtime_template_id"],
                    "action": "await_human_review",
                    "reason": "human_review_status=pending",
                }
            )
        elif status == "pass" and not family["promotion_eligible"]:
            actions.append(
                {
                    "family_id": family["family_id"],
                    "runtime_template_id": family["runtime_template_id"],
                    "action": "human_pass_waiting_for_auto_gate",
                    "reason": f"auto_gate_status={family['auto_gate_status']}",
                }
            )
        elif status == "needs_fix":
            actions.append(
                {
                    "family_id": family["family_id"],
                    "runtime_template_id": family["runtime_template_id"],
                    "action": "fix_and_resubmit_human_review",
                    "reason": family["human_review_note"] or "needs_fix",
                }
            )
        elif status == "reject":
            actions.append(
                {
                    "family_id": family["family_id"],
                    "runtime_template_id": family["runtime_template_id"],
                    "action": "keep_out_of_promotion_pool",
                    "reason": family["human_review_note"] or "reject",
                }
            )
    return actions


def build_human_review_receipt(
    *,
    gallery_receipt_path: Path = DEFAULT_GALLERY_RECEIPT,
    decisions_path: Path | None = None,
    reviewer: str = "user",
    reviewed_at: str = "pending",
) -> dict[str, Any]:
    gallery_receipt = read_json(gallery_receipt_path)
    if gallery_receipt.get("not_promotion_receipt") is not True:
        raise ValueError("gallery receipt must be marked not_promotion_receipt")
    decisions = _normalise_decisions(read_json_value(decisions_path) if decisions_path else None)
    families = []
    for family in _as_list(gallery_receipt.get("families")):
        if not isinstance(family, dict) or not family.get("family_id"):
            continue
        decision = decisions.get(str(family["family_id"]), {})
        families.append(_review_family(family, decision, reviewer=reviewer, reviewed_at=reviewed_at))
    promotion_candidates = _promotion_candidates(families)
    fix_queue = _fix_queue(families)
    reject_queue = _reject_queue(families)
    next_actions = _next_actions(families)
    invalid_reviews = [
        {
            "family_id": family["family_id"],
            "runtime_template_id": family["runtime_template_id"],
            "validation_issues": family["validation_issues"],
        }
        for family in families
        if family["validation_issues"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "human_review_receipt",
        "review_batch_id": gallery_receipt.get("review_batch_id"),
        "review_surface": "local_html_gallery",
        "not_promotion_receipt": True,
        "does_not_modify_matrix": True,
        "allowed_human_status": ALLOWED_HUMAN_STATUS,
        "source_gallery_receipt": str(gallery_receipt_path),
        "source_gallery": str(gallery_receipt_path),
        "source_gallery_receipt_sha256": file_sha256(gallery_receipt_path),
        "source_manifest_sha256": gallery_receipt.get("source_manifest_sha256"),
        "summary": {
            **_summary_counts(families),
            **_matrix_status_summary(),
            "promotion_candidates": [item["family_id"] for item in promotion_candidates],
            "fix_queue": [item["family_id"] for item in fix_queue],
            "reject_queue": [item["family_id"] for item in reject_queue],
            "promotion_candidate_count": len(promotion_candidates),
            "fix_queue_count": len(fix_queue),
            "reject_queue_count": len(reject_queue),
            "next_action_count": len(next_actions),
            "invalid_review_count": len(invalid_reviews),
        },
        "policy": {
            "human_review_pass_does_not_promote_without_auto_gate": True,
            "human_review_pass_does_not_modify_matrix": True,
            "apply_does_not_write_matrix": True,
            "apply_outputs_candidates_or_next_actions_only": True,
            "promotion_requires_separate_production_review_receipt": True,
        },
        "families": families,
        "promotion_candidates": promotion_candidates,
        "fix_queue": fix_queue,
        "reject_queue": reject_queue,
        "next_actions": next_actions,
        "invalid_reviews": invalid_reviews,
    }


def write_human_review_receipt(receipt: dict[str, Any], output_path: Path = DEFAULT_HUMAN_REVIEW_RECEIPT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=["seed", "apply"], default="seed")
    parser.add_argument("--gallery-receipt", "--gallery-source", dest="gallery_receipt", default=str(DEFAULT_GALLERY_RECEIPT))
    parser.add_argument("--decisions")
    parser.add_argument("--output", default=str(DEFAULT_HUMAN_REVIEW_RECEIPT))
    parser.add_argument("--reviewer", default="user")
    parser.add_argument("--reviewed-at", default="pending")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    receipt = build_human_review_receipt(
        gallery_receipt_path=Path(args.gallery_receipt),
        decisions_path=Path(args.decisions) if args.decisions else None,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
    )
    if args.stdout:
        print(json.dumps(receipt, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if not receipt["invalid_reviews"] else 1
    output_path = write_human_review_receipt(receipt, Path(args.output))
    print(json.dumps({"output_path": str(output_path), **receipt["summary"]}, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if not receipt["invalid_reviews"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
