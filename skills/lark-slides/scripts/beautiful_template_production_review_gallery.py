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
GENERATOR_VERSION = "svglide-beautiful-production-review-gallery/v1"


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


def _variant_records(contract: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    variants = contract.get("page_variants")
    if isinstance(variants, dict):
        return [
            {
                "page_variant_id": str(variant_id),
                "page_role": value.get("page_role") if isinstance(value, dict) else None,
                "source_class": value.get("source_class") if isinstance(value, dict) else None,
                "source_slide_index": value.get("source_slide_index") if isinstance(value, dict) else None,
            }
            for variant_id, value in sorted(variants.items())
        ]
    source_variants = row.get("source_page_variants")
    if isinstance(source_variants, list):
        return [
            {
                "page_variant_id": str(item.get("variant_id") or item.get("page_variant_id") or item.get("source_class")),
                "page_role": item.get("page_role"),
                "source_class": item.get("source_class"),
                "source_slide_index": item.get("source_slide_index"),
            }
            for item in source_variants
            if isinstance(item, dict)
        ]
    page_type = contract.get("page_type")
    layout_variants = page_type.get("layout_variants") if isinstance(page_type, dict) else None
    if isinstance(layout_variants, list):
        return [
            {
                "page_variant_id": str(item.get("variant_id") or item.get("source_class")),
                "page_role": None,
                "source_class": item.get("source_class"),
                "source_slide_index": item.get("source_slide_index"),
            }
            for item in layout_variants
            if isinstance(item, dict)
        ]
    return []


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


def _known_blockers(row: dict[str, Any], smoke: dict[str, Any], variant_count: int) -> list[str]:
    blockers = [str(item) for item in _as_list(row.get("blocking_issues")) if str(item)]
    if variant_count <= 0:
        blockers.append("page_variants_missing")
    if smoke.get("status") != "passed":
        blockers.append("page_family_smoke_missing_or_failed")
    if row.get("promotion_status") != "production":
        blockers.append("production_review_pending")
    return sorted(set(blockers))


def _family_review(row: dict[str, Any]) -> dict[str, Any]:
    contract, contract_path = _visual_contract(row)
    variant_records = _variant_records(contract, row)
    smoke = _smoke_summary(row)
    fidelity = _fidelity_summary(row)
    promotion_gate = _promotion_gate_summary(row)
    implemented_variants = [str(item) for item in _as_list(row.get("implemented_page_variants")) if str(item)]
    family_id = str(row.get("family_id") or "")
    runtime_template_id = str(row.get("runtime_template_id") or row.get("template_id") or "")
    blockers = _known_blockers(row, smoke, len(variant_records))
    return {
        "artifact_kind": "production_review_family_card",
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
        "smoke_status": smoke["status"],
        "smoke": smoke,
        "fidelity_status": fidelity["status"],
        "fidelity": fidelity,
        "page_family_promotion_gate_status": promotion_gate["status"],
        "page_family_promotion_gate": promotion_gate,
        "known_blockers": blockers,
        "review_decision": "pending_review",
        "review_claim_boundary": "gallery_input_only_not_promotion_receipt",
    }


def build_gallery_manifest() -> dict[str, Any]:
    rows = sorted(matrix_rows(), key=lambda row: str(row.get("family_id") or ""))
    families = [_family_review(row) for row in rows]
    counts = matrix_status_counts()
    smoke_status_counts: dict[str, int] = {}
    for family in families:
        status = str(family.get("smoke_status") or "missing")
        smoke_status_counts[status] = smoke_status_counts.get(status, 0) + 1
    return {
        "schema_version": GENERATOR_VERSION,
        "artifact_kind": "production_review_gallery",
        "not_promotion_receipt": True,
        "generated_by": "beautiful_template_production_review_gallery.py",
        "source_matrix": relpath(MATRIX_PATH),
        "source_matrix_sha256": file_sha256(MATRIX_PATH),
        "summary": {
            **counts,
            "smoke_status_counts": smoke_status_counts,
            "review_pending_count": len(families),
            "families_with_implemented_page_variants": sum(
                1 for family in families if family["implemented_page_variant_count"] > 0
            ),
        },
        "policy": {
            "gallery_is_review_input_only": True,
            "does_not_modify_matrix": True,
            "does_not_promote_family": True,
            "promotion_requires_separate_review_receipt": True,
        },
        "families": families,
    }


def _render_html(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    rows = []
    for family in manifest["families"]:
        blocker_text = ", ".join(family["known_blockers"]) or "none"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(family['family_id'])}</strong><br><small>{html.escape(family['runtime_template_id'])}</small></td>"
            f"<td>{html.escape(str(family['promotion_status']))}<br><small>default={html.escape(str(family['default_selectable']).lower())}</small></td>"
            f"<td>{family['page_variant_count']} source<br><small>{family['implemented_page_variant_count']} implemented</small></td>"
            f"<td>{html.escape(str(family['smoke_status']))}<br><small>{html.escape(str(family['smoke'].get('rendered_pages') or ''))} pages</small></td>"
            f"<td>{html.escape(str(family['fidelity_status']))}</td>"
            f"<td>{html.escape(str(family['page_family_promotion_gate_status']))}</td>"
            f"<td>{html.escape(blocker_text)}</td>"
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
    .warning { background: #fff6d6; border: 1px solid #e7c95b; padding: 12px 14px; border-radius: 8px; }
    .summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }
    .metric { background: #fff; border: 1px solid #dbe1ea; border-radius: 8px; padding: 10px 12px; min-width: 150px; }
    .metric strong { display: block; font-size: 22px; }
    table { border-collapse: collapse; width: 100%%; background: #fff; border: 1px solid #dbe1ea; }
    th, td { border-bottom: 1px solid #e5e9f0; padding: 10px; text-align: left; vertical-align: top; font-size: 13px; }
    th { background: #eef2f7; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    code { font-size: 11px; color: #4a5870; word-break: break-all; }
    small { color: #65728a; }
  </style>
</head>
<body>
  <header>
    <h1>SVGlide Beautiful Production Review Gallery</h1>
    <div class="warning">This gallery is review input only. It is not a promotion receipt and does not change production/default_selectable status.</div>
    <div class="summary">
      <div class="metric"><strong>%(candidate_count)s</strong>candidates</div>
      <div class="metric"><strong>%(production_default)s</strong>production + default</div>
      <div class="metric"><strong>%(default_count)s</strong>default selectable</div>
      <div class="metric"><strong>%(smoke_counts)s</strong>smoke status counts</div>
    </div>
  </header>
  <table>
    <thead>
      <tr>
        <th>Family</th>
        <th>Status</th>
        <th>Variants</th>
        <th>Smoke</th>
        <th>Fidelity</th>
        <th>Gate</th>
        <th>Known Blockers</th>
        <th>Evidence</th>
      </tr>
    </thead>
    <tbody>
      %(rows)s
    </tbody>
  </table>
</body>
</html>
""" % {
        "candidate_count": html.escape(str(summary["candidate_count"])),
        "production_default": html.escape(str(summary["production_default_selectable_count"])),
        "default_count": html.escape(str(summary["default_selectable_count"])),
        "smoke_counts": html.escape(json.dumps(summary["smoke_status_counts"], sort_keys=True)),
        "rows": "\n".join(rows),
    }


def write_gallery_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    families_dir = output_dir / "families"
    families_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_gallery_manifest()
    for family in manifest["families"]:
        family_path = families_dir / f"{family['family_id']}.json"
        family["review_artifact_path"] = relpath(family_path, output_dir)
        family_path.write_text(json.dumps(family, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    html_path = output_dir / "index.html"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(_render_html(manifest), encoding="utf-8")
    return {
        "manifest_path": str(manifest_path),
        "html_path": str(html_path),
        "candidate_count": manifest["summary"]["candidate_count"],
        "production_default_selectable_count": manifest["summary"]["production_default_selectable_count"],
        "default_selectable_count": manifest["summary"]["default_selectable_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stdout", action="store_true", help="print manifest only and do not write artifacts")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.stdout:
        manifest = build_gallery_manifest()
        print(json.dumps(manifest, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0
    result = write_gallery_artifacts(Path(args.output_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
