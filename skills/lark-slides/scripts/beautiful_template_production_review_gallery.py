#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")
MATRIX_PATH = REFERENCES_DIR / "beautiful-template-executable-matrix.json"
DEFAULT_OUTPUT_DIR = REFERENCES_DIR / "production-review" / "beautiful"
DEFAULT_RECEIPT_PATH = REFERENCES_DIR / "receipts" / "production-review" / "beautiful-34-gallery.json"
GENERATOR_VERSION = "svglide-beautiful-production-review-gallery/v2"
REVIEW_BATCH_ID = "beautiful-34"
HUMAN_REVIEW_STATUS = "pending"
PROMOTION_ACTION = "no_change_until_human_pass"
REVIEW_STATUSES = ("pass", "needs_fix", "reject")
REVIEW_STORAGE_KEY = "beautiful-production-review-decisions-v1"
REVIEW_DECISIONS_SCHEMA_VERSION = "svglide-beautiful-human-review-decisions/v1"

CORE_REVIEW_ROLES = [
    "cover",
    "agenda",
    "content",
    "data_or_structured",
    "comparison_or_split",
    "quote_or_emphasis",
    "process_or_timeline",
    "closing",
]

ROLE_GROUP_ALIASES = {
    "cover": {"cover", "hero", "opening", "title"},
    "agenda": {"agenda", "toc", "outline", "chapter", "section"},
    "content": {"content", "body", "detail", "deep_dive", "case", "context", "overview", "evidence"},
    "data_or_structured": {
        "data",
        "metric",
        "metrics",
        "dashboard",
        "chart",
        "table",
        "grid",
        "financial",
        "statement",
        "structured",
        "stat",
    },
    "comparison_or_split": {"comparison", "compare", "split", "vs", "matrix"},
    "quote_or_emphasis": {"quote", "emphasis", "callout", "manifesto", "statement"},
    "process_or_timeline": {"process", "timeline", "roadmap", "steps", "flow", "plan"},
    "closing": {"closing", "close", "summary", "takeaway", "colophon", "cta", "final"},
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def read_json_optional(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def optional_sha256(path: Path | None) -> str | None:
    return file_sha256(path) if path is not None and path.is_file() else None


def resolve_path(value: object) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    if raw.startswith(f"{SOURCE_ROOT.name}/"):
        return SOURCE_ROOT.parent / raw
    if raw.startswith("screenshots/") or raw.startswith("templates/"):
        return SOURCE_ROOT / raw
    return REPO_ROOT / raw


def relpath(path: Path | None, base: Path = REPO_ROOT) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_uri(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return path.resolve().as_uri()


def matrix_rows() -> list[dict[str, Any]]:
    payload = read_json(MATRIX_PATH)
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("beautiful-template-executable-matrix.json must contain candidates[]")
    return [row for row in rows if isinstance(row, dict)]


def matrix_status_counts() -> dict[str, int]:
    rows = matrix_rows()
    return {
        "candidate_count": len(rows),
        "default_selectable_count": sum(1 for row in rows if row.get("default_selectable") is True),
        "production_count": sum(1 for row in rows if row.get("promotion_status") == "production"),
        "production_default_selectable_count": sum(
            1
            for row in rows
            if row.get("promotion_status") == "production" and row.get("default_selectable") is True
        ),
    }


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _visual_contract(row: dict[str, Any]) -> tuple[dict[str, Any], Path | None]:
    path = resolve_path(row.get("visual_contract_path") or _as_dict(row.get("visual_contract")).get("path"))
    return read_json_optional(path), path


def _role_group(page_role: object, variant_id: object) -> str | None:
    raw_tokens = f"{page_role or ''} {variant_id or ''}".lower().replace("-", "_").replace("/", "_")
    tokens = {token for token in raw_tokens.split("_") if token}
    tokens.add(str(page_role or "").lower())
    tokens.add(str(variant_id or "").lower())
    if {"split", "compare", "comparison", "vs", "matrix"}.intersection(tokens):
        return "comparison_or_split"
    for group, aliases in ROLE_GROUP_ALIASES.items():
        if aliases.intersection(tokens):
            return group
    return None


def _variant_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    index = item.get("source_slide_index")
    if isinstance(index, int):
        return index, str(item.get("page_variant_id") or "")
    return 10_000, str(item.get("page_variant_id") or "")


def _variant_records(contract: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    variants = contract.get("page_variants")
    if isinstance(variants, dict):
        for variant_id, value in variants.items():
            if not isinstance(value, dict):
                continue
            role = value.get("page_role")
            records.append(
                {
                    "page_variant_id": str(variant_id),
                    "page_role": role,
                    "role_group": _role_group(role, variant_id),
                    "source_class": value.get("source_class"),
                    "source_slide_index": value.get("source_slide_index"),
                    "required_slots": _as_list(value.get("required_slots")),
                    "optional_slots": _as_list(value.get("optional_slots")),
                    "source_refs": _as_list(value.get("source_refs")),
                    "extraction_confidence": value.get("extraction_confidence"),
                }
            )
        return sorted(records, key=_variant_sort_key)

    source_variants = row.get("source_page_variants")
    if isinstance(source_variants, list):
        for index, item in enumerate(source_variants, start=1):
            if isinstance(item, dict):
                variant_id = str(item.get("variant_id") or item.get("page_variant_id") or item.get("source_class") or f"page-{index}")
                role = item.get("page_role")
                records.append(
                    {
                        "page_variant_id": variant_id,
                        "page_role": role,
                        "role_group": _role_group(role, variant_id),
                        "source_class": item.get("source_class"),
                        "source_slide_index": item.get("source_slide_index") or index,
                        "required_slots": _as_list(item.get("required_slots")),
                        "optional_slots": _as_list(item.get("optional_slots")),
                        "source_refs": _as_list(item.get("source_refs")),
                        "extraction_confidence": item.get("extraction_confidence"),
                    }
                )
            elif isinstance(item, str):
                records.append(
                    {
                        "page_variant_id": item,
                        "page_role": item,
                        "role_group": _role_group(item, item),
                        "source_class": None,
                        "source_slide_index": index,
                        "required_slots": [],
                        "optional_slots": [],
                        "source_refs": [],
                        "extraction_confidence": "matrix_source_page_variants",
                    }
                )
        return sorted(records, key=_variant_sort_key)

    page_type = contract.get("page_type")
    layout_variants = page_type.get("layout_variants") if isinstance(page_type, dict) else None
    if isinstance(layout_variants, list):
        for index, item in enumerate(layout_variants, start=1):
            if not isinstance(item, dict):
                continue
            variant_id = str(item.get("variant_id") or item.get("source_class") or f"page-{index}")
            roles = _as_list(item.get("page_roles"))
            role = roles[0] if roles else variant_id
            records.append(
                {
                    "page_variant_id": variant_id,
                    "page_role": role,
                    "role_group": _role_group(role, variant_id),
                    "source_class": item.get("source_class"),
                    "source_slide_index": item.get("source_slide_index") or index,
                    "required_slots": _as_list(item.get("required_slots")),
                    "optional_slots": _as_list(item.get("optional_slots")),
                    "source_refs": _as_list(item.get("source_refs")),
                    "extraction_confidence": item.get("extraction_confidence"),
                }
            )
    return sorted(records, key=_variant_sort_key)


def _smoke_summary(row: dict[str, Any]) -> dict[str, Any]:
    deck_path = resolve_path(row.get("page_family_smoke_deck"))
    receipt_path = resolve_path(row.get("page_family_smoke_receipt"))
    receipt = read_json_optional(receipt_path)
    status = str(receipt.get("status") or "missing")
    if not receipt_path or not receipt_path.is_file():
        status = "missing"
    return {
        "artifact_kind": "page-family-smoke",
        "status": status,
        "deck_path": row.get("page_family_smoke_deck"),
        "deck_sha256": optional_sha256(deck_path),
        "receipt_path": row.get("page_family_smoke_receipt"),
        "receipt_sha256": optional_sha256(receipt_path),
        "degraded": bool(receipt.get("degraded")) if receipt else None,
        "rendered_pages": receipt.get("rendered_pages"),
        "page_variant_coverage": receipt.get("page_variant_coverage") if isinstance(receipt.get("page_variant_coverage"), dict) else {},
        "missing_required_roles": _as_list(receipt.get("missing_required_roles")),
        "implemented_page_variants": _as_list(receipt.get("implemented_page_variants")),
        "covered_implemented_page_variants": _as_list(receipt.get("covered_implemented_page_variants")),
        "missing_implemented_page_variants": _as_list(receipt.get("missing_implemented_page_variants")),
        "input_hashes": _as_dict(receipt.get("input_hashes")),
    }


def _fidelity_summary(row: dict[str, Any]) -> dict[str, Any]:
    gate = _as_dict(row.get("fidelity_gate"))
    receipt_path = resolve_path(row.get("fidelity_receipt") or gate.get("receipt_path"))
    receipt = read_json_optional(receipt_path)
    return {
        "status": gate.get("status") or receipt.get("status") or "missing",
        "score": gate.get("score") if gate.get("score") is not None else receipt.get("score"),
        "threshold": gate.get("threshold") if gate.get("threshold") is not None else receipt.get("threshold"),
        "receipt_path": row.get("fidelity_receipt") or gate.get("receipt_path"),
        "receipt_sha256": optional_sha256(receipt_path),
    }


def _promotion_gate_summary(row: dict[str, Any]) -> dict[str, Any]:
    gate = _as_dict(row.get("page_family_promotion_gate"))
    return {
        "status": gate.get("status") or "missing",
        "required_evidence": _as_list(gate.get("required_evidence")),
        "claim_boundary": gate.get("claim_boundary"),
    }


def _source_screenshot_for_page(family_id: str, slide_index: object, fallback: object) -> dict[str, Any]:
    reference = resolve_path(fallback)
    if isinstance(slide_index, int):
        candidate = SOURCE_ROOT / "screenshots" / f"{family_id}-{slide_index}.png"
        if candidate.is_file():
            return {
                "status": "exact",
                "path": relpath(candidate),
                "uri": file_uri(candidate),
                "sha256": optional_sha256(candidate),
                "expected_path": relpath(candidate),
                "reference_screenshot": relpath(reference),
                "fallback_used": False,
            }
        expected_path = candidate
        reason = "source_screenshot_missing_for_slide"
    else:
        expected_path = None
        reason = "source_slide_index_missing"
    return {
        "status": "missing",
        "path": None,
        "uri": None,
        "sha256": None,
        "expected_path": relpath(expected_path),
        "reference_screenshot": relpath(reference),
        "missing_reason": reason,
        "fallback_used": False,
    }


def _page_render_evidence(row: dict[str, Any], variant_id: str, smoke: dict[str, Any]) -> dict[str, Any]:
    variant_golden = row.get("page_variant_golden_specs")
    golden_path = None
    if isinstance(variant_golden, dict):
        golden_path = resolve_path(variant_golden.get(variant_id))
    smoke_status = str(smoke.get("status") or "missing")
    if smoke_status == "passed":
        status = "passed" if golden_path and golden_path.is_file() else "smoke_passed_without_variant_golden"
    else:
        status = "missing_smoke"
    return {
        "render_status": status,
        "golden_spec": relpath(golden_path),
        "golden_spec_sha256": optional_sha256(golden_path),
        "smoke_receipt": smoke.get("receipt_path"),
        "smoke_receipt_sha256": smoke.get("receipt_sha256"),
    }


def _coverage_from_pages(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    for role in CORE_REVIEW_ROLES:
        matching = [page for page in pages if page.get("role_group") == role]
        coverage[role] = {
            "covered": bool(matching),
            "page_variant_ids": [str(page.get("page_variant_id")) for page in matching],
            "pages": [page.get("page") for page in matching],
            "missing_reason": None if matching else "source_page_variant_not_extracted_for_role",
        }
    return coverage


def _source_smoke_deck(row: dict[str, Any], variants: list[dict[str, Any]], smoke: dict[str, Any]) -> dict[str, Any]:
    family_id = str(row.get("family_id") or "")
    pages: list[dict[str, Any]] = []
    for page_number, variant in enumerate(variants, start=1):
        variant_id = str(variant.get("page_variant_id") or f"page-{page_number}")
        evidence = _page_render_evidence(row, variant_id, smoke)
        screenshot = _source_screenshot_for_page(family_id, variant.get("source_slide_index"), row.get("reference_screenshot"))
        pages.append(
            {
                "page": page_number,
                "page_variant_id": variant_id,
                "page_role": variant.get("page_role"),
                "role_group": variant.get("role_group"),
                "source_class": variant.get("source_class"),
                "source_slide_index": variant.get("source_slide_index"),
                "required_slots": _as_list(variant.get("required_slots")),
                "optional_slots": _as_list(variant.get("optional_slots")),
                "source_refs": _as_list(variant.get("source_refs")),
                "source_screenshot": screenshot,
                "render_status": evidence["render_status"],
                "render_evidence": evidence,
            }
        )
    coverage = _coverage_from_pages(pages)
    missing_roles = [role for role, value in coverage.items() if not value["covered"]]
    return {
        "artifact_kind": "smoke_deck_review_data",
        "status": smoke.get("status") or "missing",
        "source": "visual_contract.page_variants",
        "source_page_count": len(variants),
        "page_count": len(pages),
        "pages": pages,
        "page_variant_coverage": coverage,
        "missing_roles": missing_roles,
        "claim_boundary": "source-derived review deck; only passed smoke/fidelity/review receipt can promote a family",
    }


def _auto_gate_status(row: dict[str, Any], smoke: dict[str, Any], fidelity: dict[str, Any], promotion_gate: dict[str, Any]) -> str:
    if (
        smoke.get("status") == "passed"
        and fidelity.get("status") == "passed"
        and promotion_gate.get("status") == "passed"
        and bool(row.get("production_review_receipt"))
    ):
        return "passed"
    return "blocked"


def _known_blockers(
    row: dict[str, Any],
    smoke: dict[str, Any],
    variant_count: int,
    missing_roles: list[str],
    auto_gate_status: str,
) -> list[str]:
    blockers = [str(item) for item in _as_list(row.get("blocking_issues")) if str(item)]
    if variant_count <= 0:
        blockers.append("page_variants_missing")
    if smoke.get("status") != "passed":
        blockers.extend(["missing_smoke", "page_family_smoke_missing_or_failed"])
    if missing_roles:
        blockers.append("source_core_roles_missing")
    if auto_gate_status != "passed":
        blockers.append("auto_gate_blocked")
    if row.get("promotion_status") != "production":
        blockers.append("production_review_pending")
    return sorted(set(blockers))


def _family_review(row: dict[str, Any]) -> dict[str, Any]:
    contract, contract_path = _visual_contract(row)
    variant_records = _variant_records(contract, row)
    smoke = _smoke_summary(row)
    fidelity = _fidelity_summary(row)
    promotion_gate = _promotion_gate_summary(row)
    smoke_deck = _source_smoke_deck(row, variant_records, smoke)
    coverage = smoke_deck["page_variant_coverage"]
    missing_roles = smoke_deck["missing_roles"]
    implemented_variants = [str(item) for item in _as_list(row.get("implemented_page_variants")) if str(item)]
    family_id = str(row.get("family_id") or "")
    runtime_template_id = str(row.get("runtime_template_id") or row.get("template_id") or "")
    auto_gate_status = _auto_gate_status(row, smoke, fidelity, promotion_gate)
    blockers = _known_blockers(row, smoke, len(variant_records), missing_roles, auto_gate_status)
    contact_sheet_status = "passed" if smoke.get("status") == "passed" else "missing_smoke"
    evidence_hashes = {
        "visual_contract": optional_sha256(contract_path),
        "reference_screenshot": optional_sha256(resolve_path(row.get("reference_screenshot"))),
        "smoke_receipt": smoke.get("receipt_sha256"),
        "fidelity_receipt": fidelity.get("receipt_sha256"),
    }
    return {
        "artifact_kind": "production_review_family_smoke_deck",
        "not_promotion_receipt": True,
        "family_id": family_id,
        "runtime_template_id": runtime_template_id,
        "template_id": row.get("template_id"),
        "visual_contract_path": row.get("visual_contract_path") or _as_dict(row.get("visual_contract")).get("path"),
        "visual_contract_sha256": optional_sha256(contract_path),
        "reference_screenshot": row.get("reference_screenshot"),
        "reference_screenshot_sha256": optional_sha256(resolve_path(row.get("reference_screenshot"))),
        "promotion_status": row.get("promotion_status"),
        "default_selectable": row.get("default_selectable") is True,
        "page_variant_count": len(variant_records),
        "page_variants": variant_records,
        "implemented_page_variants": implemented_variants,
        "implemented_page_variant_count": len(implemented_variants),
        "pages": smoke_deck["pages"],
        "smoke_deck": smoke_deck,
        "page_variant_coverage": coverage,
        "missing_roles": missing_roles,
        "smoke_status": smoke["status"],
        "smoke": smoke,
        "fidelity_status": fidelity["status"],
        "fidelity": fidelity,
        "page_family_promotion_gate_status": promotion_gate["status"],
        "page_family_promotion_gate": promotion_gate,
        "auto_gate_status": auto_gate_status,
        "human_review_status": HUMAN_REVIEW_STATUS,
        "allowed_human_status": list(REVIEW_STATUSES),
        "promotion_action": PROMOTION_ACTION,
        "evidence_hashes": evidence_hashes,
        "contact_sheet": {
            "artifact_kind": "smoke_deck_contact_sheet_review_model",
            "render_status": contact_sheet_status,
            "html_path": f"families/{family_id}.html",
            "sha256": None,
        },
        "known_blockers": blockers,
        "review_decision": "pending_review",
        "review_claim_boundary": "gallery_input_only_not_promotion_receipt",
    }


def build_gallery_manifest() -> dict[str, Any]:
    rows = sorted(matrix_rows(), key=lambda row: str(row.get("family_id") or ""))
    families = [_family_review(row) for row in rows]
    counts = matrix_status_counts()
    smoke_status_counts: dict[str, int] = {}
    auto_gate_counts: dict[str, int] = {}
    for family in families:
        smoke_status = str(family.get("smoke_status") or "missing")
        smoke_status_counts[smoke_status] = smoke_status_counts.get(smoke_status, 0) + 1
        auto_status = str(family.get("auto_gate_status") or "blocked")
        auto_gate_counts[auto_status] = auto_gate_counts.get(auto_status, 0) + 1
    return {
        "schema_version": GENERATOR_VERSION,
        "artifact_kind": "production_review_gallery",
        "review_batch_id": REVIEW_BATCH_ID,
        "not_promotion_receipt": True,
        "generated_by": "beautiful_template_production_review_gallery.py",
        "source_matrix": relpath(MATRIX_PATH),
        "source_matrix_sha256": file_sha256(MATRIX_PATH),
        "summary": {
            **counts,
            "smoke_status_counts": smoke_status_counts,
            "auto_gate_status_counts": auto_gate_counts,
            "auto_gate_passed_count": auto_gate_counts.get("passed", 0),
            "auto_gate_blocked_count": auto_gate_counts.get("blocked", 0),
            "review_pending_count": len(families),
            "families_with_implemented_page_variants": sum(
                1 for family in families if family["implemented_page_variant_count"] > 0
            ),
            "family_contact_sheet_count": len(families),
        },
        "policy": {
            "gallery_is_review_input_only": True,
            "does_not_modify_matrix": True,
            "does_not_promote_family": True,
            "promotion_requires_separate_review_receipt": True,
            "human_review_pass_does_not_promote_without_auto_gate": True,
            "auto_gate_pass_without_human_pass_does_not_promote": True,
        },
        "families": families,
    }


def build_gallery_receipt(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or build_gallery_manifest()
    families = []
    for family in manifest["families"]:
        families.append(
            {
                "family_id": family["family_id"],
                "runtime_template_id": family["runtime_template_id"],
                "gallery_url": family["contact_sheet"]["html_path"],
                "page_variant_coverage": [
                    role for role, coverage in family["page_variant_coverage"].items() if coverage.get("covered")
                ],
                "missing_roles": family["missing_roles"],
                "auto_gate_status": family["auto_gate_status"],
                "human_review_status": family["human_review_status"],
                "allowed_human_status": family["allowed_human_status"],
                "promotion_action": family["promotion_action"],
                "review_decision": family["review_decision"],
                "known_blockers": family["known_blockers"],
                "evidence_hashes": family["evidence_hashes"],
            }
        )
    return {
        "schema_version": GENERATOR_VERSION,
        "artifact_kind": "production_review_gallery_receipt",
        "review_batch_id": REVIEW_BATCH_ID,
        "not_promotion_receipt": True,
        "family_count": len(families),
        "source_manifest_sha256": None,
        "summary": manifest["summary"],
        "policy": manifest["policy"],
        "families": families,
    }


def _badge(value: object) -> str:
    text = html.escape(str(value))
    css = "ok" if str(value) == "passed" else "warn" if str(value) in {"pending", "pending_review"} else "bad"
    return f'<span class="badge {css}">{text}</span>'


def _review_receipt_relpath() -> str:
    return relpath(DEFAULT_RECEIPT_PATH) or DEFAULT_RECEIPT_PATH.as_posix()


def _review_decision_template(family: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_id": family["family_id"],
        "runtime_template_id": family["runtime_template_id"],
        "review_status": "pass | needs_fix | reject",
        "human_review_status_before_selection": HUMAN_REVIEW_STATUS,
        "promotion_action": PROMOTION_ACTION,
        "source_gallery_receipt_path": _review_receipt_relpath(),
        "notes": "",
    }


def _review_controls_html(family: dict[str, Any], *, include_snippet: bool = False) -> str:
    family_id = str(family["family_id"])
    safe_family_id = html.escape(family_id, quote=True)
    buttons = "".join(
        f'<button type="button" data-family-id="{safe_family_id}" data-review-status="{html.escape(status, quote=True)}">{html.escape(status)}</button>'
        for status in REVIEW_STATUSES
    )
    snippet = ""
    if include_snippet:
        template = json.dumps(_review_decision_template(family), ensure_ascii=False, indent=2, sort_keys=True)
        snippet = (
            '<details class="decision-template">'
            "<summary>Copyable decision JSON fragment</summary>"
            f"<pre>{html.escape(template)}</pre>"
            "</details>"
        )
    return (
        f'<div class="review-control" data-review-control-for="{safe_family_id}">'
        f'<div class="decision-buttons">{buttons}</div>'
        f'<div class="review-current">Selected: <strong data-review-current-for="{safe_family_id}">pending</strong></div>'
        f'<label class="notes-label">Notes <input type="text" data-review-notes-for="{safe_family_id}" placeholder="optional apply-script context" /></label>'
        f"{snippet}"
        "</div>"
    )


def _review_handoff_html() -> str:
    receipt_path = _review_receipt_relpath()
    command = f"python <apply-script> --gallery-receipt {receipt_path} --decisions <exported-decisions.json>"
    return f"""<section class="review-handoff">
    <h2>Human Review Export</h2>
    <div class="warning">This local UI does not automatically modify production/default. It only stores browser-local decisions and exports JSON for a separate apply script.</div>
    <p><code>human_review_status={html.escape(HUMAN_REVIEW_STATUS)}</code> <code>promotion_action={html.escape(PROMOTION_ACTION)}</code></p>
    <p>Machine-readable gallery receipt: <code>{html.escape(receipt_path)}</code></p>
    <p>Apply script input: save this textarea as decisions JSON, then pass it to the apply script, for example <code>{html.escape(command)}</code>.</p>
    <textarea id="review-decisions-json" readonly spellcheck="false"></textarea>
  </section>
"""


def _review_script_html() -> str:
    receipt_path = _review_receipt_relpath()
    return """  <script>
    (function () {
      var storageKey = %(storage_key)s;
      var schemaVersion = %(schema_version)s;
      var reviewBatchId = %(review_batch_id)s;
      var receiptPath = %(receipt_path)s;
      var pendingHumanReviewStatus = %(pending_status)s;
      var promotionAction = %(promotion_action)s;

      function readState() {
        try {
          var parsed = JSON.parse(localStorage.getItem(storageKey) || "{}");
          if (parsed && typeof parsed === "object" && parsed.decisions && typeof parsed.decisions === "object") {
            return parsed;
          }
        } catch (error) {
          // Ignore malformed local state and rebuild below.
        }
        return { decisions: {} };
      }

      function writeState(state) {
        localStorage.setItem(storageKey, JSON.stringify(state));
      }

      function buildExport(state) {
        var decisions = Object.keys(state.decisions || {}).sort().map(function (familyId) {
          return state.decisions[familyId];
        });
        return {
          schema_version: schemaVersion,
          artifact_kind: "beautiful_template_human_review_decisions",
          review_batch_id: reviewBatchId,
          source_gallery_receipt_path: receiptPath,
          not_promotion_receipt: true,
          policy: {
            does_not_automatically_modify_production_default: true,
            apply_script_must_validate_gallery_receipt: true
          },
          decisions: decisions
        };
      }

      function render(state) {
        document.querySelectorAll("[data-review-current-for]").forEach(function (node) {
          var familyId = node.getAttribute("data-review-current-for");
          var decision = state.decisions[familyId];
          node.textContent = decision ? decision.review_status : "pending";
        });
        document.querySelectorAll("[data-review-status]").forEach(function (button) {
          var familyId = button.getAttribute("data-family-id");
          var status = button.getAttribute("data-review-status");
          var decision = state.decisions[familyId];
          button.classList.toggle("selected", Boolean(decision && decision.review_status === status));
        });
        document.querySelectorAll("[data-review-notes-for]").forEach(function (input) {
          var familyId = input.getAttribute("data-review-notes-for");
          var decision = state.decisions[familyId];
          if (decision && input.value !== decision.notes) {
            input.value = decision.notes || "";
          }
        });
        var textarea = document.getElementById("review-decisions-json");
        if (textarea) {
          textarea.value = JSON.stringify(buildExport(state), null, 2);
        }
      }

      document.addEventListener("click", function (event) {
        var button = event.target.closest("[data-review-status]");
        if (!button) {
          return;
        }
        var state = readState();
        var familyId = button.getAttribute("data-family-id");
        var status = button.getAttribute("data-review-status");
        var existing = state.decisions[familyId] || {};
        state.decisions[familyId] = {
          family_id: familyId,
          review_status: status,
          human_review_status_before_selection: pendingHumanReviewStatus,
          promotion_action: promotionAction,
          source_gallery_receipt_path: receiptPath,
          notes: existing.notes || "",
          updated_at: new Date().toISOString()
        };
        writeState(state);
        render(state);
      });

      document.addEventListener("input", function (event) {
        var input = event.target.closest("[data-review-notes-for]");
        if (!input) {
          return;
        }
        var state = readState();
        var familyId = input.getAttribute("data-review-notes-for");
        var existing = state.decisions[familyId] || {
          family_id: familyId,
          review_status: "needs_fix",
          human_review_status_before_selection: pendingHumanReviewStatus,
          promotion_action: promotionAction,
          source_gallery_receipt_path: receiptPath,
          updated_at: new Date().toISOString()
        };
        existing.notes = input.value;
        existing.updated_at = new Date().toISOString();
        state.decisions[familyId] = existing;
        writeState(state);
        render(state);
      });

      render(readState());
    })();
  </script>
""" % {
        "storage_key": json.dumps(REVIEW_STORAGE_KEY),
        "schema_version": json.dumps(REVIEW_DECISIONS_SCHEMA_VERSION),
        "review_batch_id": json.dumps(REVIEW_BATCH_ID),
        "receipt_path": json.dumps(receipt_path),
        "pending_status": json.dumps(HUMAN_REVIEW_STATUS),
        "promotion_action": json.dumps(PROMOTION_ACTION),
    }


def _render_family_html(family: dict[str, Any]) -> str:
    pages = []
    for page in family["pages"]:
        screenshot = page.get("source_screenshot") if isinstance(page.get("source_screenshot"), dict) else {}
        img = ""
        if screenshot.get("uri"):
            img = f'<img src="{html.escape(str(screenshot["uri"]))}" alt="{html.escape(str(page["page_variant_id"]))}" />'
        else:
            expected = screenshot.get("expected_path") or "unknown"
            img = (
                '<div class="missing-thumb">'
                "<strong>source screenshot missing</strong>"
                f"<small>{html.escape(str(expected))}</small>"
                "</div>"
            )
        pages.append(
            "<section class=\"page\">"
            f"<div class=\"thumb\">{img}</div>"
            f"<h2>{html.escape(str(page['page']))}. {html.escape(str(page['page_variant_id']))}</h2>"
            f"<p>{html.escape(str(page.get('page_role') or 'unknown'))} / {html.escape(str(page.get('role_group') or 'unmapped'))}</p>"
            f"<p>{_badge(page.get('render_status'))}</p>"
            f"<p>source screenshot: {html.escape(str(screenshot.get('status') or 'missing'))}</p>"
            f"<p><code>{html.escape(str(page.get('source_class') or ''))}</code></p>"
            "</section>"
        )
    blockers = ", ".join(family["known_blockers"]) or "none"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(family['family_id'])} - SVGlide Production Review</title>
  <style>
    body {{ margin: 28px; background: #f6f7f9; color: #172033; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    a {{ color: #1d4ed8; }}
    header {{ max-width: 1200px; margin-bottom: 20px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .warning {{ padding: 10px 12px; border: 1px solid #d9b51d; background: #fff8d6; border-radius: 8px; }}
    .meta {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 10px; margin: 16px 0; }}
    .metric {{ background: #fff; border: 1px solid #dfe5ee; border-radius: 8px; padding: 10px; }}
    .metric strong {{ display: block; font-size: 20px; }}
    .deck {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }}
    .page {{ background: #fff; border: 1px solid #dfe5ee; border-radius: 8px; padding: 10px; }}
    .thumb {{ background: #eef2f7; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; overflow: hidden; border-radius: 6px; border: 1px solid #d8dee9; }}
    .thumb img {{ width: 100%; height: 100%; object-fit: contain; }}
    .missing-thumb {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; color: #7c2d12; background: #ffedd5; width: 100%; height: 100%; text-align: center; padding: 12px; box-sizing: border-box; }}
    .missing-thumb small {{ color: #9a3412; word-break: break-all; }}
    h2 {{ margin: 10px 0 4px; font-size: 15px; }}
    p {{ margin: 5px 0; font-size: 12px; color: #536071; }}
    code {{ word-break: break-all; font-size: 11px; }}
    button {{ cursor: pointer; border: 1px solid #b8c2d2; background: #fff; color: #172033; border-radius: 6px; padding: 6px 9px; font-weight: 700; }}
    button.selected {{ border-color: #1d4ed8; background: #dbeafe; color: #1e3a8a; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 2px 7px; font-size: 11px; font-weight: 700; }}
    .ok {{ color: #065f46; background: #d1fae5; }}
    .warn {{ color: #92400e; background: #fef3c7; }}
    .bad {{ color: #991b1b; background: #fee2e2; }}
    .review-panel, .review-handoff {{ background: #fff; border: 1px solid #dfe5ee; border-radius: 8px; padding: 14px; margin: 16px 0; }}
    .decision-buttons {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }}
    .review-current {{ font-size: 12px; color: #536071; margin-bottom: 8px; }}
    .notes-label {{ display: block; color: #536071; font-size: 12px; }}
    .notes-label input {{ margin-left: 8px; min-width: min(520px, 80vw); padding: 6px 8px; border: 1px solid #c7d0df; border-radius: 6px; }}
    .decision-template {{ margin-top: 10px; }}
    pre, textarea {{ width: 100%; box-sizing: border-box; border: 1px solid #c7d0df; border-radius: 6px; background: #f8fafc; color: #172033; }}
    pre {{ overflow: auto; padding: 10px; font-size: 12px; }}
    textarea {{ min-height: 180px; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <p><a href="../index.html">Back to gallery</a></p>
    <h1>{html.escape(family['family_id'])}</h1>
    <div class="warning">Review input only. This contact sheet is not a production promotion receipt and does not automatically modify production/default.</div>
    <div class="meta">
      <div class="metric"><strong>{html.escape(str(family['page_variant_count']))}</strong>source pages</div>
      <div class="metric"><strong>{html.escape(str(family['auto_gate_status']))}</strong>auto gate</div>
      <div class="metric"><strong>{html.escape(str(family['smoke_status']))}</strong>smoke</div>
      <div class="metric"><strong>{html.escape(str(family['fidelity_status']))}</strong>fidelity</div>
    </div>
    <div class="review-panel">
      <h2>Human decision</h2>
      {_review_controls_html(family, include_snippet=True)}
    </div>
    <p><strong>Known blockers:</strong> {html.escape(blockers)}</p>
  </header>
  {_review_handoff_html()}
  <main class="deck">
    {"".join(pages)}
  </main>
{_review_script_html()}
</body>
</html>
"""


def _render_html(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    rows = []
    for family in manifest["families"]:
        blocker_text = ", ".join(family["known_blockers"]) or "none"
        contact = family["contact_sheet"]["html_path"]
        rows.append(
            "<tr>"
            f"<td><strong><a href=\"{html.escape(contact)}\">{html.escape(family['family_id'])}</a></strong><br><small>{html.escape(family['runtime_template_id'])}</small></td>"
            f"<td>{html.escape(str(family['promotion_status']))}<br><small>default={html.escape(str(family['default_selectable']).lower())}</small></td>"
            f"<td>{family['page_variant_count']} source<br><small>{family['implemented_page_variant_count']} implemented</small></td>"
            f"<td>{_badge(family['auto_gate_status'])}<br><small>human_review_status={html.escape(str(family['human_review_status']))}</small><br><small>promotion_action={html.escape(str(family['promotion_action']))}</small></td>"
            f"<td>{html.escape(str(family['smoke_status']))}<br><small>{html.escape(str(family['smoke'].get('rendered_pages') or ''))} rendered</small></td>"
            f"<td>{html.escape(str(family['fidelity_status']))}</td>"
            f"<td>{html.escape(blocker_text)}</td>"
            f"<td>{_review_controls_html(family)}</td>"
            f"<td><code>{html.escape(str(family['visual_contract_path']))}</code><br><code>{html.escape(str(family['reference_screenshot']))}</code></td>"
            "</tr>"
        )
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>SVGlide Beautiful Production Review Gallery</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #172033; background: #f7f8fb; }
    header { max-width: 1180px; margin-bottom: 24px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    a { color: #1d4ed8; text-decoration: none; }
    .warning { background: #fff6d6; border: 1px solid #e7c95b; padding: 12px 14px; border-radius: 8px; }
    .summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }
    .metric { background: #fff; border: 1px solid #dbe1ea; border-radius: 8px; padding: 10px 12px; min-width: 150px; }
    .metric strong { display: block; font-size: 22px; }
    button { cursor: pointer; border: 1px solid #b8c2d2; background: #fff; color: #172033; border-radius: 6px; padding: 6px 9px; font-weight: 700; }
    button.selected { border-color: #1d4ed8; background: #dbeafe; color: #1e3a8a; }
    table { border-collapse: collapse; width: 100%%; background: #fff; border: 1px solid #dbe1ea; }
    th, td { border-bottom: 1px solid #e5e9f0; padding: 10px; text-align: left; vertical-align: top; font-size: 13px; }
    th { background: #eef2f7; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    code { font-size: 11px; color: #4a5870; word-break: break-all; }
    small { color: #65728a; }
    .decision-buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
    .review-current { font-size: 12px; color: #536071; margin-bottom: 8px; }
    .notes-label { display: block; color: #536071; font-size: 12px; }
    .notes-label input { width: min(220px, 80vw); padding: 6px 8px; border: 1px solid #c7d0df; border-radius: 6px; }
    .review-handoff { background: #fff; border: 1px solid #dbe1ea; border-radius: 8px; padding: 14px; margin: 18px 0; max-width: 1180px; }
    textarea { width: 100%%; min-height: 180px; box-sizing: border-box; border: 1px solid #c7d0df; border-radius: 6px; background: #f8fafc; color: #172033; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
    .badge { display: inline-block; border-radius: 999px; padding: 2px 7px; font-size: 11px; font-weight: 700; }
    .ok { color: #065f46; background: #d1fae5; }
    .warn { color: #92400e; background: #fef3c7; }
    .bad { color: #991b1b; background: #fee2e2; }
  </style>
</head>
<body>
  <header>
    <h1>SVGlide Beautiful Production Review Gallery</h1>
    <div class="warning">This gallery is review input only. It is not a promotion receipt, does not change production/default_selectable status, and does not automatically modify production/default.</div>
    <div class="summary">
      <div class="metric"><strong>%(candidate_count)s</strong>candidates</div>
      <div class="metric"><strong>%(production_default)s</strong>production + default</div>
      <div class="metric"><strong>%(auto_passed)s</strong>auto gate passed</div>
      <div class="metric"><strong>%(smoke_counts)s</strong>smoke status counts</div>
    </div>
  </header>
  %(handoff)s
  <table>
    <thead>
      <tr>
        <th>Family</th>
        <th>Status</th>
        <th>Variants</th>
        <th>Review Gate</th>
        <th>Smoke</th>
        <th>Fidelity</th>
        <th>Known Blockers</th>
        <th>Human Decision</th>
        <th>Evidence</th>
      </tr>
    </thead>
    <tbody>
      %(rows)s
    </tbody>
  </table>
%(script)s
</body>
</html>
""" % {
        "candidate_count": html.escape(str(summary["candidate_count"])),
        "production_default": html.escape(str(summary["production_default_selectable_count"])),
        "auto_passed": html.escape(str(summary["auto_gate_passed_count"])),
        "smoke_counts": html.escape(json.dumps(summary["smoke_status_counts"], sort_keys=True)),
        "handoff": _review_handoff_html(),
        "rows": "\n".join(rows),
        "script": _review_script_html(),
    }


def write_gallery_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR, receipt_path: Path = DEFAULT_RECEIPT_PATH) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    families_dir = output_dir / "families"
    families_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_gallery_manifest()
    for family in manifest["families"]:
        family_html_path = families_dir / f"{family['family_id']}.html"
        family_html_path.write_text(_render_family_html(family), encoding="utf-8")
        family["contact_sheet"]["html_path"] = relpath(family_html_path, output_dir)
        family["contact_sheet"]["sha256"] = file_sha256(family_html_path)
        family["evidence_hashes"]["contact_sheet"] = family["contact_sheet"]["sha256"]
        family_path = families_dir / f"{family['family_id']}.json"
        family["review_artifact_path"] = relpath(family_path, output_dir)
        family_path.write_text(json.dumps(family, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    html_path = output_dir / "index.html"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(_render_html(manifest), encoding="utf-8")
    receipt = build_gallery_receipt(manifest)
    receipt["source_manifest_sha256"] = file_sha256(manifest_path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "manifest_path": str(manifest_path),
        "html_path": str(html_path),
        "receipt_path": str(receipt_path),
        "candidate_count": manifest["summary"]["candidate_count"],
        "production_default_selectable_count": manifest["summary"]["production_default_selectable_count"],
        "default_selectable_count": manifest["summary"]["default_selectable_count"],
        "auto_gate_passed_count": manifest["summary"]["auto_gate_passed_count"],
    }


def write_gallery_html_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    families_dir = output_dir / "families"
    families_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_gallery_manifest()
    for family in manifest["families"]:
        family_html_path = families_dir / f"{family['family_id']}.html"
        family_html_path.write_text(_render_family_html(family), encoding="utf-8")
    html_path = output_dir / "index.html"
    html_path.write_text(_render_html(manifest), encoding="utf-8")
    return {
        "html_path": str(html_path),
        "family_html_count": len(manifest["families"]),
        "candidate_count": manifest["summary"]["candidate_count"],
        "production_default_selectable_count": manifest["summary"]["production_default_selectable_count"],
        "default_selectable_count": manifest["summary"]["default_selectable_count"],
        "auto_gate_passed_count": manifest["summary"]["auto_gate_passed_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH))
    parser.add_argument("--stdout", action="store_true", help="print manifest only and do not write artifacts")
    parser.add_argument("--receipt-stdout", action="store_true", help="print gallery receipt only and do not write artifacts")
    parser.add_argument("--html-only", action="store_true", help="write index/family HTML only and leave manifest/receipt JSON unchanged")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.stdout:
        manifest = build_gallery_manifest()
        print(json.dumps(manifest, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0
    if args.receipt_stdout:
        receipt = build_gallery_receipt()
        print(json.dumps(receipt, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0
    if args.html_only:
        result = write_gallery_html_artifacts(Path(args.output_dir))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0
    result = write_gallery_artifacts(Path(args.output_dir), Path(args.receipt_path))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
