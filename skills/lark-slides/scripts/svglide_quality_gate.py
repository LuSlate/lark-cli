#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import svglide_node_layout_drift
import svglide_schema
import svglide_semantic_map_ir


CHECK_DIR = Path("06-check")
QUALITY_GATE_NAME = "quality-gate.json"
PREPARED_SVG_DIR = Path("04-svg/prepared")
SOURCE_SVG_DIR = Path("04-svg")
PLAN_PATH = Path("02-plan/slide_plan.json")
EVIDENCE_PATH = Path("source/evidence.json")
SOURCE_RECEIPT_PATH = Path("source/source-receipt.json")
ASSET_MANIFEST_PATH = Path("03-assets/asset-manifest.json")
GENERATOR_RECEIPT_PATH = Path("receipts/generate_svg.json")
TEMPLATE_FIT_PATH = Path("06-check/template-fit.json")
CANVAS_SPEC_VALIDATE_RECEIPT = Path("receipts/canvas-spec-validate.json")
TEMPLATE_FIT_RECEIPT = Path("receipts/template-fit-check.json")
ARTBOARD_RENDER_RECEIPT = Path("receipts/artboard-render.json")
SATORI_BRIDGE_RECEIPT = Path("receipts/satori-bridge.json")
CONTACT_SHEET = Path("05-preview/contact-sheet.png")
REQUIRED_CHECKS = [
    ("preflight", CHECK_DIR / "preflight.json"),
    ("preview-lint", CHECK_DIR / "preview-lint.json"),
    ("aesthetic-review", CHECK_DIR / "aesthetic-review.json"),
    ("runtime-review", CHECK_DIR / "runtime-review.json"),
    ("semantic-review", CHECK_DIR / "semantic-review.json"),
    ("visual-distinctness", CHECK_DIR / "visual-distinctness.json"),
]
THEME_REQUIRED_CHECKS = [
    ("theme-validate", CHECK_DIR / "theme-validate.json"),
    ("theme-adherence", CHECK_DIR / "theme-adherence.json"),
]
SELECTION_CHECKS = [
    ("palette-review", CHECK_DIR / "palette-review.json"),
    ("theme-template-selection-review", CHECK_DIR / "theme-template-selection-review.json"),
    ("plan-bundle-review", CHECK_DIR / "plan-bundle-review.json"),
]
ARTBOARD_PACKAGE_CHECK = ("artboard-package-check", CHECK_DIR / "artboard-package-check.json")
CHART_VERIFY_CHECK = ("chart-verify", CHECK_DIR / "chart-verify.json")
OPTIONAL_CHECKS = []
PASS_ACTION = "create_live"
FAIL_ACTIONS = {"repair_and_rerun", "failed", "fail"}
PRODUCTION_PROFILE = "production"
REAL_PREVIEW_PROFILE = "local_real_preview"
STRICT_PROFILES = {PRODUCTION_PROFILE, "production_live", REAL_PREVIEW_PROFILE}
USER_VISIBLE_ASSET_PROFILES = STRICT_PROFILES | {"preview_only"}
BLOCKED_ASSET_SOURCE_TYPES = {"local_preview"}
BLOCKED_ASSET_SOURCE_REFS = {"local-generated-preview-asset"}
BLOCKED_ASSET_KINDS = {"generated_image", "ai_image"}
BLOCKED_ASSET_LICENSES = {"preview_unverified"}
INTERNAL_ASSET_SCHEMES = {"internal"}
ASSET_METADATA_KEYS = {
    "asset_id",
    "asset_kind",
    "crop_hint",
    "file",
    "href",
    "license",
    "local_path_or_href",
    "path",
    "placement_role",
    "safe_text_zones",
    "source_ref",
    "source_type",
    "source_url",
    "usage_page",
}


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def has_asset_metadata(value: dict[str, Any]) -> bool:
    return any(key in value for key in ASSET_METADATA_KEYS)


def iter_asset_metadata(value: Any, path: str) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        if has_asset_metadata(value):
            items.append((path, value))
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                items.extend(iter_asset_metadata(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                items.extend(iter_asset_metadata(child, f"{path}[{index}]"))
    return items


def is_allowed_online_source_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return (parsed.scheme in {"http", "https"} and bool(parsed.netloc)) or (parsed.scheme in INTERNAL_ASSET_SCHEMES and bool(parsed.netloc))


def source_url_issue_code(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if value.startswith(("@./", "@/")) or parsed.scheme in {"", "file"}:
        return "asset_source_url_not_http"
    if parsed.scheme in INTERNAL_ASSET_SCHEMES:
        return "asset_source_url_internal_invalid"
    return "asset_source_url_not_http"


def asset_record_requires_online_source(value: dict[str, Any]) -> bool:
    if value.get("status") in {"fallback_used", "planned", "failed", "missing", "missing_optional", "metadata_only"}:
        return False
    return any(key in value for key in {"href", "local_path_or_href", "file", "source_url", "asset_id", "asset_kind"})


def user_visible_asset_issues(project: Path, asset_manifest: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    sources = [
        (PLAN_PATH.as_posix(), read_json_optional(project, PLAN_PATH)),
        (ASSET_MANIFEST_PATH.as_posix(), asset_manifest),
    ]
    seen: set[tuple[str, str, str]] = set()
    for source_name, payload in sources:
        for metadata_path, metadata in iter_asset_metadata(payload, source_name):
            source_type = metadata.get("source_type")
            if isinstance(source_type, str) and source_type in BLOCKED_ASSET_SOURCE_TYPES:
                seen_key = ("asset_source_type_blocked", metadata_path, source_type)
                if seen_key not in seen:
                    issues.append(issue("asset_source_type_blocked", f"{metadata_path} uses blocked source_type={source_type!r}"))
                    seen.add(seen_key)
            source_ref = metadata.get("source_ref")
            if isinstance(source_ref, str) and source_ref in BLOCKED_ASSET_SOURCE_REFS:
                seen_key = ("asset_source_ref_blocked", metadata_path, source_ref)
                if seen_key not in seen:
                    issues.append(issue("asset_source_ref_blocked", f"{metadata_path} uses blocked source_ref={source_ref!r}"))
                    seen.add(seen_key)
            asset_kind = metadata.get("asset_kind")
            if isinstance(asset_kind, str) and asset_kind in BLOCKED_ASSET_KINDS:
                seen_key = ("asset_kind_blocked", metadata_path, asset_kind)
                if seen_key not in seen:
                    issues.append(issue("asset_kind_blocked", f"{metadata_path} uses blocked asset_kind={asset_kind!r}"))
                    seen.add(seen_key)
            license_value = metadata.get("license")
            if isinstance(license_value, str) and license_value in BLOCKED_ASSET_LICENSES:
                seen_key = ("asset_license_blocked", metadata_path, license_value)
                if seen_key not in seen:
                    issues.append(issue("asset_license_blocked", f"{metadata_path} uses blocked license={license_value!r}"))
                    seen.add(seen_key)
            if asset_record_requires_online_source(metadata):
                source_url = metadata.get("source_url")
                if not isinstance(source_url, str) or not source_url.strip():
                    seen_key = ("asset_source_url_missing", metadata_path, "")
                    if seen_key not in seen:
                        issues.append(issue("asset_source_url_missing", f"{metadata_path} must include an http(s) source_url"))
                        seen.add(seen_key)
                elif not is_allowed_online_source_url(source_url):
                    code = source_url_issue_code(source_url)
                    seen_key = (code, metadata_path, source_url)
                    if seen_key not in seen:
                        issues.append(issue(code, f"{metadata_path} has non-online source_url={source_url!r}"))
                        seen.add(seen_key)
    return issues


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


def input_check_hashes(project: Path, checks: list[tuple[str, Path]]) -> dict[str, str | None]:
    return {name.replace("-", "_"): optional_file_sha256(project, rel) for name, rel in checks}


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


def read_json_optional(project: Path, rel: Path) -> dict[str, Any]:
    path = project / rel
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generator_generation_mode(project: Path) -> str | None:
    payload = read_json_optional(project, GENERATOR_RECEIPT_PATH)
    raw = payload.get("generation_mode") if isinstance(payload, dict) else None
    return raw if raw in {"direct_svg", "artboard_satori"} else None


def require_receipt(project: Path, rel: Path, issues: list[dict[str, str]], *, code_prefix: str) -> dict[str, Any]:
    path = project / rel
    if not path.exists():
        issues.append(issue(f"{code_prefix}_missing", f"required receipt is missing: {rel.as_posix()}"))
        return {}
    payload = read_json_optional(project, rel)
    if not payload:
        issues.append(issue(f"{code_prefix}_invalid_json", f"required receipt is not valid JSON: {rel.as_posix()}"))
        return {}
    if payload.get("status") != "passed":
        issues.append(issue(f"{code_prefix}_not_passed", f"receipt status must be passed: {rel.as_posix()}"))
    return payload


def check_recorded_artifact(project: Path, payload: dict[str, Any], path_key: str, hash_key: str, issues: list[dict[str, str]], *, code_prefix: str) -> None:
    rel = payload.get(path_key)
    recorded = payload.get(hash_key)
    if not isinstance(rel, str) or not rel:
        issues.append(issue(f"{code_prefix}_{path_key}_missing", f"receipt must include {path_key}"))
        return
    path = project / rel
    if not path.exists():
        issues.append(issue(f"{code_prefix}_{path_key}_artifact_missing", f"artifact is missing: {rel}"))
        return
    if recorded != file_sha256(path):
        issues.append(issue(f"{code_prefix}_{path_key}_stale", f"artifact hash is stale: {rel}"))


def check_contact_sheet(project: Path, contact_sheet: Any, issues: list[dict[str, str]]) -> None:
    if not isinstance(contact_sheet, dict):
        issues.append(issue("artboard_contact_sheet_missing", "generate_svg receipt must include contact_sheet"))
        return
    rel = contact_sheet.get("path")
    recorded = contact_sheet.get("sha256")
    if rel != CONTACT_SHEET.as_posix():
        issues.append(issue("artboard_contact_sheet_path_invalid", f"contact_sheet.path must be {CONTACT_SHEET.as_posix()}"))
        return
    if not (project / CONTACT_SHEET).exists():
        issues.append(issue("artboard_contact_sheet_file_missing", f"contact sheet is missing: {CONTACT_SHEET.as_posix()}"))
        return
    if recorded != file_sha256(project / CONTACT_SHEET):
        issues.append(issue("artboard_contact_sheet_stale", "contact sheet hash does not match current file"))


def load_online_readiness(project: Path, *, profile: str) -> dict[str, Any]:
    source_receipt = read_json_optional(project, SOURCE_RECEIPT_PATH)
    asset_manifest = read_json_optional(project, ASSET_MANIFEST_PATH)
    research = source_receipt.get("research") if isinstance(source_receipt.get("research"), dict) else {}
    asset_summary = asset_manifest.get("summary") if isinstance(asset_manifest.get("summary"), dict) else {}
    research_status = research.get("status") if isinstance(research, dict) and isinstance(research.get("status"), str) else "legacy"
    asset_status = asset_manifest.get("status") if isinstance(asset_manifest.get("status"), str) else "legacy"
    acquired_count = int(asset_summary.get("acquired_count") or 0)
    local_file_count = int(asset_summary.get("local_file_count") or 0)
    mapped_token_count = int(asset_summary.get("mapped_token_count") or 0)
    image_job_count = int(asset_summary.get("image_job_count") or 0)
    fulfilled_count = acquired_count + mapped_token_count
    issues: list[dict[str, str]] = []
    if profile in STRICT_PROFILES and research_status in {"blocked_by_network", "skipped_by_user"}:
        issues.append(issue("research_missing_for_current_topic", f"research status is {research_status}"))
    if asset_status == "failed":
        issues.append(issue("asset_manifest_failed", "asset manifest status is failed"))
    if profile in USER_VISIBLE_ASSET_PROFILES:
        contract_count = int(asset_summary.get("contract_count") or 0)
        if contract_count > 0 and image_job_count > 0 and fulfilled_count == 0:
            issues.append(
                issue(
                    "visual_asset_contracts_unfulfilled",
                    "asset contracts produced image jobs but no acquired or token-backed online asset",
                )
            )
    if profile in USER_VISIBLE_ASSET_PROFILES:
        issues.extend(user_visible_asset_issues(project, asset_manifest))
    if profile == REAL_PREVIEW_PROFILE:
        contract_count = int(asset_summary.get("contract_count") or 0)
        planned_count = int(asset_summary.get("planned_image_count") or image_job_count or 0)
        if asset_manifest.get("network_policy") == "offline":
            issues.append(issue("real_preview_network_policy_offline", "local_real_preview cannot use offline asset acquisition"))
        if asset_manifest.get("image_backend") == "none":
            issues.append(issue("real_preview_image_backend_none", "local_real_preview cannot use image_backend=none"))
        if contract_count == 0:
            issues.append(issue("real_preview_asset_contracts_empty", "local_real_preview requires non-empty asset contracts"))
        if fulfilled_count + planned_count == 0:
            issues.append(issue("real_preview_visual_assets_missing", "local_real_preview requires acquired or token-backed online visual assets"))
    status = "failed" if issues else "skipped" if not source_receipt and not asset_manifest else "passed"
    return {
        "name": "online-readiness",
        "path": "source/source-receipt.json + 03-assets/asset-manifest.json",
        "required": False,
        "status": status,
        "error_count": len(issues),
        "action": PASS_ACTION if not issues else "repair_and_rerun",
        "waivers": [],
        "issues": issues,
        "research_status": research_status,
        "asset_status": asset_status,
        "asset_real_coverage": fulfilled_count,
        "asset_acquired_count": acquired_count,
        "asset_local_file_count": local_file_count,
        "asset_mapped_token_count": mapped_token_count,
        "asset_fallback_count": asset_summary.get("fallback_count"),
        "image_job_count": image_job_count,
    }


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


def plan_declares_selection(project: Path) -> bool:
    path = project / PLAN_PATH
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if payload.get("selection_receipt") or payload.get("palette_selection_receipt"):
        return True
    if isinstance(payload.get("project_palette"), dict) or isinstance(payload.get("project_theme"), dict):
        return True
    slides = payload.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            spec = slide.get("canvas_spec")
            if isinstance(spec, dict) and (spec.get("palette_id") or spec.get("selection_trace")):
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


def load_generator_receipt(project: Path, *, profile: str) -> dict[str, Any]:
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
    page_identity_summary = payload.get("page_identity_summary")
    if not isinstance(page_identity_summary, list) or not page_identity_summary:
        check["issues"].append(issue("generator_page_identity_summary_missing", "generator receipt must include page_identity_summary"))
    if profile in STRICT_PROFILES and payload.get("fallback_skeleton_used") is True:
        check["issues"].append(issue("fallback_skeleton_used", "production profiles cannot use the generic fallback SVG skeleton"))
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
    generation_mode = payload.get("generation_mode") or "direct_svg"
    if generation_mode not in {"direct_svg", "artboard_satori"}:
        check["issues"].append(issue("generator_generation_mode_invalid", "generation_mode must be direct_svg or artboard_satori"))
    if generation_mode == "artboard_satori":
        if payload.get("canvas_spec_validate") != "06-check/canvas-spec-validate.json":
            check["issues"].append(issue("generator_canvas_spec_validate_missing", "artboard_satori generator receipt must include canvas_spec_validate"))
        if payload.get("artboard_render_receipt") != ARTBOARD_RENDER_RECEIPT.as_posix():
            check["issues"].append(issue("generator_artboard_render_receipt_missing", "artboard_satori generator receipt must include artboard_render_receipt"))
        if payload.get("satori_bridge_receipt") != SATORI_BRIDGE_RECEIPT.as_posix():
            check["issues"].append(issue("generator_satori_bridge_receipt_missing", "artboard_satori generator receipt must include satori_bridge_receipt"))
        additional_receipts = payload.get("artboard_additional_receipts")
        expected_additional_receipts = [
            CANVAS_SPEC_VALIDATE_RECEIPT.as_posix(),
            ARTBOARD_RENDER_RECEIPT.as_posix(),
            SATORI_BRIDGE_RECEIPT.as_posix(),
        ]
        if additional_receipts != expected_additional_receipts:
            check["issues"].append(issue("generator_artboard_additional_receipts_invalid", "artboard_satori generator receipt must include ordered aggregate receipts"))
        check_contact_sheet(project, payload.get("contact_sheet"), check["issues"])
        canvas_validate = require_receipt(project, CANVAS_SPEC_VALIDATE_RECEIPT, check["issues"], code_prefix="canvas_spec_validate")
        if canvas_validate:
            inputs = canvas_validate.get("inputs") if isinstance(canvas_validate.get("inputs"), dict) else {}
            if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
                check["issues"].append(issue("canvas_spec_validate_plan_stale", "canvas-spec-validate plan_sha256 does not match current slide_plan.json"))
            if not inputs.get("template_registry_sha256") or not inputs.get("theme_registry_sha256"):
                check["issues"].append(issue("canvas_spec_validate_registry_hash_missing", "canvas-spec-validate must include template/theme registry hashes"))
        artboard_render = require_receipt(project, ARTBOARD_RENDER_RECEIPT, check["issues"], code_prefix="artboard_render")
        if artboard_render:
            inputs = artboard_render.get("inputs") if isinstance(artboard_render.get("inputs"), dict) else {}
            if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
                check["issues"].append(issue("artboard_render_plan_stale", "artboard-render plan_sha256 does not match current slide_plan.json"))
            if inputs.get("canvas_spec_validate_sha256") != optional_file_sha256(project, CANVAS_SPEC_VALIDATE_RECEIPT):
                check["issues"].append(issue("artboard_render_canvas_validate_stale", "artboard-render canvas_spec_validate_sha256 is stale"))
            if not inputs.get("template_registry_sha256") or not inputs.get("theme_registry_sha256"):
                check["issues"].append(issue("artboard_render_registry_hash_missing", "artboard-render must include template/theme registry hashes"))
            check_contact_sheet(project, artboard_render.get("contact_sheet"), check["issues"])
            pages = artboard_render.get("pages") if isinstance(artboard_render.get("pages"), list) else []
            if not pages:
                check["issues"].append(issue("artboard_render_pages_missing", "artboard-render receipt must include pages"))
            for page in pages:
                if not isinstance(page, dict):
                    check["issues"].append(issue("artboard_render_page_invalid", "artboard-render pages must be objects"))
                    continue
                if not page.get("template_id") or not page.get("theme_id"):
                    check["issues"].append(issue("artboard_render_template_theme_missing", "artboard-render pages must include template_id and theme_id"))
                if not page.get("satori_version") or not page.get("resvg_version"):
                    check["issues"].append(issue("artboard_render_runtime_version_missing", "artboard-render pages must include satori_version and resvg_version"))
                if not isinstance(page.get("font_hashes"), list) or not page.get("font_hashes"):
                    check["issues"].append(issue("artboard_render_font_hash_missing", "artboard-render pages must include font_hashes"))
                for path_key, hash_key in [
                    ("satori_svg", "satori_svg_sha256"),
                    ("png", "png_sha256"),
                    ("render_metadata", "render_metadata_sha256"),
                    ("canvas_template_svg", "canvas_template_svg_sha256"),
                    ("node_layout_map", "node_layout_map_sha256"),
                ]:
                    check_recorded_artifact(project, page, path_key, hash_key, check["issues"], code_prefix="artboard_render")
        satori_bridge = require_receipt(project, SATORI_BRIDGE_RECEIPT, check["issues"], code_prefix="satori_bridge")
        if satori_bridge:
            inputs = satori_bridge.get("inputs") if isinstance(satori_bridge.get("inputs"), dict) else {}
            if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
                check["issues"].append(issue("satori_bridge_plan_stale", "satori-bridge plan_sha256 does not match current slide_plan.json"))
            if inputs.get("artboard_render_sha256") != optional_file_sha256(project, ARTBOARD_RENDER_RECEIPT):
                check["issues"].append(issue("satori_bridge_artboard_render_stale", "satori-bridge artboard_render_sha256 is stale"))
            pages = satori_bridge.get("pages") if isinstance(satori_bridge.get("pages"), list) else []
            if not pages:
                check["issues"].append(issue("satori_bridge_pages_missing", "satori-bridge receipt must include pages"))
            for page in pages:
                if not isinstance(page, dict):
                    check["issues"].append(issue("satori_bridge_page_invalid", "satori-bridge pages must be objects"))
                    continue
                if page.get("semantic_source") != "SatoriSVG":
                    check["issues"].append(issue("satori_bridge_semantic_source_invalid", "satori-bridge semantic_source must be SatoriSVG"))
                if page.get("input_semantic_hash") != page.get("satori_svg_sha256"):
                    check["issues"].append(issue("satori_bridge_input_semantic_hash_mismatch", "satori-bridge input_semantic_hash must match satori_svg_sha256"))
                if page.get("compiler_input_type") != "RawSatoriSVG":
                    check["issues"].append(issue("satori_bridge_compiler_input_type_invalid", "satori-bridge compiler_input_type must be RawSatoriSVG"))
                if page.get("satori_svg_usage") != "compiler_input":
                    check["issues"].append(issue("satori_bridge_satori_usage_invalid", "satori-bridge satori_svg_usage must be compiler_input"))
                if page.get("compiler_input") != page.get("satori_svg"):
                    check["issues"].append(issue("satori_bridge_compiler_input_path_invalid", "satori-bridge compiler_input must point to satori_svg"))
                if page.get("compiler_input_sha256") != page.get("satori_svg_sha256"):
                    check["issues"].append(issue("satori_bridge_compiler_input_hash_mismatch", "satori-bridge compiler_input_sha256 must match satori_svg_sha256"))
                for path_key, hash_key in [
                    ("semantic_map", "semantic_map_sha256"),
                    ("node_layout_map", "node_layout_map_sha256"),
                    ("canvas_template_svg", "canvas_template_svg_sha256"),
                    ("compiler_input", "compiler_input_sha256"),
                    ("satori_svg", "satori_svg_sha256"),
                    ("svglide_svg", "svglide_svg_sha256"),
                ]:
                    check_recorded_artifact(project, page, path_key, hash_key, check["issues"], code_prefix="satori_bridge")
        template_fit_receipt = require_receipt(project, TEMPLATE_FIT_RECEIPT, check["issues"], code_prefix="template_fit_receipt")
        if template_fit_receipt:
            inputs = template_fit_receipt.get("inputs") if isinstance(template_fit_receipt.get("inputs"), dict) else {}
            if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
                check["issues"].append(issue("template_fit_receipt_plan_stale", "template-fit receipt plan_sha256 does not match current slide_plan.json"))
            if inputs.get("generator_receipt_sha256") != optional_file_sha256(project, GENERATOR_RECEIPT_PATH):
                check["issues"].append(issue("template_fit_receipt_generator_stale", "template-fit receipt generator_receipt_sha256 is stale"))
            if not inputs.get("template_registry_sha256") or not inputs.get("theme_registry_sha256"):
                check["issues"].append(issue("template_fit_receipt_registry_hash_missing", "template-fit receipt must include template/theme registry hashes"))
        template_fit = read_json_optional(project, TEMPLATE_FIT_PATH)
        if not template_fit:
            check["issues"].append(issue("template_fit_missing", "artboard_satori generation requires 06-check/template-fit.json"))
        else:
            if template_fit.get("status") != "passed":
                check["issues"].append(issue("template_fit_not_passed", "template fit status must be passed"))
            inputs = template_fit.get("inputs") if isinstance(template_fit.get("inputs"), dict) else {}
            if inputs.get("plan_sha256") != optional_file_sha256(project, PLAN_PATH):
                check["issues"].append(issue("template_fit_plan_stale", "template fit plan_sha256 does not match current slide_plan.json"))
            if inputs.get("generator_receipt_sha256") != optional_file_sha256(project, GENERATOR_RECEIPT_PATH):
                check["issues"].append(issue("template_fit_generator_stale", "template fit generator_receipt_sha256 does not match current generate_svg receipt"))
        artboard_receipts = payload.get("artboard_receipts")
        if not isinstance(artboard_receipts, list) or not artboard_receipts:
            check["issues"].append(issue("generator_artboard_receipts_missing", "artboard_satori generation must include artboard_receipts"))
        elif isinstance(generated, list) and len(artboard_receipts) != len(generated):
            check["issues"].append(issue("generator_artboard_receipt_count_mismatch", "artboard_receipts count must match generated_files"))
        if isinstance(artboard_receipts, list):
            artboard_schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-artboard-receipt.schema.json"))
            semantic_map_schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-semantic-map.schema.json"))
            node_layout_schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-node-layout-map.schema.json"))
            by_svg = {item.get("path"): item.get("sha256") for item in generated if isinstance(item, dict)} if isinstance(generated, list) else {}
            for item in artboard_receipts:
                if not isinstance(item, str):
                    check["issues"].append(issue("generator_artboard_receipt_invalid", "artboard_receipts must be string paths"))
                    continue
                artboard_receipt_path = project / item
                if not artboard_receipt_path.exists():
                    check["issues"].append(issue("generator_artboard_receipt_missing", f"artboard receipt is missing: {item}"))
                    continue
                try:
                    artboard_receipt = json.loads(artboard_receipt_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    check["issues"].append(issue("generator_artboard_receipt_invalid_json", f"could not read artboard receipt JSON: {error}"))
                    continue
                schema_issues = svglide_schema.validate_json_schema(artboard_receipt, artboard_schema)
                if schema_issues:
                    check["issues"].extend(issue("generator_artboard_receipt_schema_invalid", f"{item} {schema_issue['path']}: {schema_issue['message']}") for schema_issue in schema_issues)
                    continue
                if not isinstance(artboard_receipt, dict) or artboard_receipt.get("status") != "passed":
                    check["issues"].append(issue("generator_artboard_receipt_not_passed", f"artboard receipt status must be passed: {item}"))
                    continue
                svglide_svg = artboard_receipt.get("svglide_svg")
                svglide_svg_sha256 = artboard_receipt.get("svglide_svg_sha256")
                if not isinstance(svglide_svg, str) or by_svg.get(svglide_svg) != svglide_svg_sha256:
                    check["issues"].append(issue("generator_artboard_output_stale", f"artboard receipt output does not match generated_files: {item}"))
                for path_key, hash_key in [
                    ("satori_svg", "satori_svg_sha256"),
                    ("png", "png_sha256"),
                    ("render_metadata", "render_metadata_sha256"),
                    ("canvas_template_svg", "canvas_template_svg_sha256"),
                    ("compiler_input", "compiler_input_sha256"),
                    ("semantic_map", "semantic_map_sha256"),
                    ("node_layout_map", "node_layout_map_sha256"),
                    ("svglide_svg", "svglide_svg_sha256"),
                ]:
                    rel = artboard_receipt.get(path_key)
                    recorded = artboard_receipt.get(hash_key)
                    if not isinstance(rel, str) or not (project / rel).exists():
                        check["issues"].append(issue("generator_artboard_artifact_missing", f"artboard artifact is missing: {path_key} in {item}"))
                        continue
                    if recorded != file_sha256(project / rel):
                        check["issues"].append(issue("generator_artboard_artifact_stale", f"artboard artifact hash is stale: {path_key} in {item}"))
                if not artboard_receipt.get("template_id") or not artboard_receipt.get("theme_id"):
                    check["issues"].append(issue("generator_artboard_template_theme_missing", f"artboard receipt must include template_id and theme_id: {item}"))
                if not artboard_receipt.get("template_registry_sha256") or not artboard_receipt.get("theme_registry_sha256"):
                    check["issues"].append(issue("generator_artboard_registry_hash_missing", f"artboard receipt must include template/theme registry hashes: {item}"))
                if not artboard_receipt.get("satori_version") or not artboard_receipt.get("resvg_version"):
                    check["issues"].append(issue("generator_artboard_runtime_version_missing", f"artboard receipt must include satori_version and resvg_version: {item}"))
                if not isinstance(artboard_receipt.get("font_hashes"), list) or not artboard_receipt.get("font_hashes"):
                    check["issues"].append(issue("generator_artboard_font_hash_missing", f"artboard receipt must include font_hashes: {item}"))
                compiler = artboard_receipt.get("compiler") if isinstance(artboard_receipt.get("compiler"), dict) else {}
                if compiler.get("semantic_source") != "SatoriSVG":
                    check["issues"].append(issue("generator_artboard_compiler_semantic_source_invalid", f"artboard compiler semantic_source must be SatoriSVG: {item}"))
                if compiler.get("compiler_input") != "RawSatoriSVG":
                    check["issues"].append(issue("generator_artboard_compiler_input_invalid", f"artboard compiler_input must be RawSatoriSVG: {item}"))
                if compiler.get("satori_svg_usage") != "compiler_input":
                    check["issues"].append(issue("generator_artboard_compiler_satori_usage_invalid", f"artboard compiler satori_svg_usage must be compiler_input: {item}"))
                if artboard_receipt.get("compiler_input") != artboard_receipt.get("satori_svg"):
                    check["issues"].append(issue("generator_artboard_compiler_input_path_invalid", f"artboard compiler_input must point to satori_svg: {item}"))
                input_semantic_hash = artboard_receipt.get("input_semantic_hash")
                satori_svg_sha256 = artboard_receipt.get("satori_svg_sha256")
                if not isinstance(input_semantic_hash, str) or not input_semantic_hash:
                    check["issues"].append(issue("generator_artboard_input_semantic_hash_missing", f"artboard receipt must include input_semantic_hash: {item}"))
                elif input_semantic_hash != satori_svg_sha256:
                    check["issues"].append(issue("generator_artboard_input_semantic_hash_mismatch", f"artboard input_semantic_hash must match satori_svg_sha256: {item}"))
                if artboard_receipt.get("compiler_input_sha256") != satori_svg_sha256:
                    check["issues"].append(issue("generator_artboard_compiler_input_hash_mismatch", f"artboard compiler_input_sha256 must match satori_svg_sha256: {item}"))
                if compiler.get("input_semantic_hash") != satori_svg_sha256:
                    check["issues"].append(issue("generator_artboard_compiler_input_semantic_hash_mismatch", f"artboard compiler input_semantic_hash must match satori_svg_sha256: {item}"))
                for path_key, artifact_schema, code in [
                    ("semantic_map", semantic_map_schema, "generator_artboard_semantic_map_schema_invalid"),
                    ("node_layout_map", node_layout_schema, "generator_artboard_node_layout_schema_invalid"),
                ]:
                    rel = artboard_receipt.get(path_key)
                    if not isinstance(rel, str) or not (project / rel).exists():
                        continue
                    try:
                        artifact = json.loads((project / rel).read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as error:
                        check["issues"].append(issue(code, f"could not read {path_key} JSON in {item}: {error}"))
                        continue
                    schema_issues = svglide_schema.validate_json_schema(artifact, artifact_schema)
                    check["issues"].extend(issue(code, f"{rel} {schema_issue['path']}: {schema_issue['message']}") for schema_issue in schema_issues)
                    if path_key == "semantic_map" and artifact.get("semantic_source") == "CanvasSpec":
                        svglide_rel = artboard_receipt.get("svglide_svg")
                        if isinstance(svglide_rel, str) and (project / svglide_rel).exists():
                            semantic_issues = svglide_semantic_map_ir.validate_semantic_map_against_svg(artifact, project / svglide_rel)
                            check["issues"].extend(issue(f"generator_artboard_{semantic_issue['code']}", f"{rel}: {semantic_issue['message']}") for semantic_issue in semantic_issues)
                    if path_key == "node_layout_map":
                        drift_issues = svglide_node_layout_drift.validate_node_layout_map(artifact)
                        check["issues"].extend(issue(f"generator_artboard_{drift_issue['code']}", f"{rel}: {drift_issue['message']}") for drift_issue in drift_issues)
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

    if name == "theme-validate" and isinstance(payload, dict):
        freshness = plan_bound_check_freshness_issues(project, payload, "theme_validate", prepared=False)
        if freshness:
            check["issues"].extend(freshness)
            return check

    if name == "theme-adherence" and isinstance(payload, dict):
        freshness = plan_bound_check_freshness_issues(project, payload, "theme_adherence", prepared=True)
        if freshness:
            check["issues"].extend(freshness)
            return check
        inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
        if inputs.get("theme_validate_sha256") != optional_file_sha256(project, CHECK_DIR / "theme-validate.json"):
            check["issues"].append(issue("theme_adherence_theme_validate_stale", "theme adherence theme_validate_sha256 does not match current theme-validate receipt"))
            return check

    if name == "artboard-package-check" and isinstance(payload, dict):
        if payload.get("stage") not in {"package_check", "artboard_package_check"}:
            check["issues"].append(issue("artboard_package_check_stage_invalid", "artboard package check stage must be package_check"))
            return check

    if name in {"chart-verify", "runtime-review", "semantic-review", "theme-validate", "theme-adherence", "artboard-package-check"} and action not in {PASS_ACTION, "passed"}:
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
    checks = [load_generator_receipt(project, profile=profile)]
    checks.append(load_online_readiness(project, profile=profile))
    checks.extend(load_check(project, name, rel, required=True, profile=profile) for name, rel in REQUIRED_CHECKS)
    checks.extend(load_check(project, name, rel, required=True, profile=profile) for name, rel in THEME_REQUIRED_CHECKS)
    selection_checks_required = plan_declares_selection(project) or any((project / rel).exists() for _, rel in SELECTION_CHECKS)
    checks.extend(load_check(project, name, rel, required=selection_checks_required, profile=profile) for name, rel in SELECTION_CHECKS)
    generation_mode = generator_generation_mode(project)
    conditional_checks: list[tuple[str, Path]] = []
    if generation_mode == "artboard_satori":
        conditional_checks.append(ARTBOARD_PACKAGE_CHECK)
        checks.append(load_check(project, *ARTBOARD_PACKAGE_CHECK, required=True, profile=profile))
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
    active_selection_checks = [
        item
        for item in SELECTION_CHECKS
        if selection_checks_required or (project / item[1]).exists()
    ]
    input_checks = REQUIRED_CHECKS + THEME_REQUIRED_CHECKS + active_selection_checks + conditional_checks + ([CHART_VERIFY_CHECK] if chart_required else []) + OPTIONAL_CHECKS
    required_input_names = {item[0] for item in REQUIRED_CHECKS + THEME_REQUIRED_CHECKS + conditional_checks}
    if selection_checks_required:
        required_input_names.update(item[0] for item in SELECTION_CHECKS)
    result = {
        "version": "svglide-quality-gate/v1",
        "project": str(project),
        "profile": profile,
        "status": status,
        "inputs": {
            name.replace("-", "_"): rel.as_posix()
            for name, rel in input_checks
            if (project / rel).exists() or name in required_input_names
        },
        "input_hashes": input_check_hashes(project, input_checks + [("generator-receipt", GENERATOR_RECEIPT_PATH)]),
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
            "research_status": next((check.get("research_status") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_status": next((check.get("asset_status") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_real_coverage": next((check.get("asset_real_coverage") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_acquired_count": next((check.get("asset_acquired_count") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_local_file_count": next((check.get("asset_local_file_count") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_mapped_token_count": next((check.get("asset_mapped_token_count") for check in checks if check.get("name") == "online-readiness"), None),
            "asset_fallback_count": next((check.get("asset_fallback_count") for check in checks if check.get("name") == "online-readiness"), None),
            "image_job_count": next((check.get("image_job_count") for check in checks if check.get("name") == "online-readiness"), None),
        },
        "checks": checks,
        "output_path": relpath(output_path, project),
    }
    result["inputs"]["generator_receipt"] = GENERATOR_RECEIPT_PATH.as_posix()
    result["inputs"]["generation_mode"] = generation_mode or "unknown"
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
    parser.add_argument("--profile", default=PRODUCTION_PROFILE, choices=["production", "debug", "fixture", "preview_only", "local_real_preview", "production_live"])
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
