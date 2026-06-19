#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PREVIEW_HTML = Path("05-preview/preview.html")
PREVIEW_MANIFEST = Path("05-preview/preview-manifest.json")
PREVIEW_LINT = Path("06-check/preview-lint.json")
ASSET_MANIFEST = Path("03-assets/asset-manifest.json")
AESTHETIC_REVIEW = Path("06-check/aesthetic-review.json")
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"


class AestheticReviewError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AestheticReviewError(f"missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise AestheticReviewError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AestheticReviewError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def expected_page_count(project: Path) -> int | None:
    plan_path = project / "02-plan" / "slide_plan.json"
    if not plan_path.exists():
        return None
    plan = read_json(plan_path)
    for key in ["slides", "svg_files", "pages"]:
        value = plan.get(key)
        if isinstance(value, list):
            return len(value)
    raw = plan.get("page_count") or plan.get("target_slide_count")
    return raw if isinstance(raw, int) and raw > 0 else None


def issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def asset_review(project: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    manifest = read_json_optional(project / ASSET_MANIFEST)
    acquired = manifest.get("acquired_assets") if isinstance(manifest.get("acquired_assets"), list) else []
    real_assets = 0
    fallback_assets = 0
    for item in acquired:
        if not isinstance(item, dict):
            continue
        role = item.get("placement_role")
        status = item.get("status")
        kind = item.get("asset_kind")
        safe_zones = item.get("safe_text_zones")
        if status == "acquired":
            real_assets += 1
        if status == "fallback_used":
            fallback_assets += 1
        if role in {"cover", "background", "closing"} and status == "acquired" and not isinstance(safe_zones, list):
            issues.append(issue("asset_text_zone_unsafe", f"asset {item.get('asset_id')} needs safe_text_zones for {role} placement"))
        if role == "body_visual" and status == "acquired" and kind == "web_image" and item.get("caption_required") is True and not item.get("source_url"):
            issues.append(issue("asset_source_missing", f"body visual asset {item.get('asset_id')} must keep source_url"))
        if role in {"cover", "closing"} and status == "fallback_used":
            warnings.append(issue("asset_fallback_used", f"{role} asset {item.get('asset_id')} fell back to SVG-native rendering"))
        if isinstance(item.get("source_url"), str) and "watermark" in str(item.get("source_url")).lower():
            issues.append(issue("asset_label_baked_into_image", f"asset {item.get('asset_id')} source suggests watermark/text risk"))
    summary = {
        "manifest_status": manifest.get("status") if manifest else "missing",
        "asset_count": len(acquired),
        "real_asset_count": real_assets,
        "fallback_asset_count": fallback_assets,
    }
    return issues, warnings, summary


def run_aesthetic_review(project: Path) -> dict[str, Any]:
    project = project.resolve()
    issues: list[dict[str, str]] = []
    preview = project / PREVIEW_HTML
    manifest_path = project / PREVIEW_MANIFEST
    lint_path = project / PREVIEW_LINT
    if not preview.exists():
        issues.append(issue("missing_preview_html", "preview.html is missing"))
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    if not manifest:
        issues.append(issue("missing_preview_manifest", "preview manifest is missing"))
    lint = read_json(lint_path) if lint_path.exists() else {}
    lint_errors = lint.get("summary", {}).get("error_count") if isinstance(lint.get("summary"), dict) else None
    if lint_errors != 0 or lint.get("action") != PASS_ACTION:
        issues.append(issue("preview_lint_not_clean", "preview lint must be clean before aesthetic review can pass"))

    expected = expected_page_count(project)
    actual = manifest.get("page_count")
    if expected is not None and actual != expected:
        issues.append(issue("preview_page_count_mismatch", f"expected {expected} preview pages, got {actual!r}"))
    for page in manifest.get("pages", []) if isinstance(manifest.get("pages"), list) else []:
        if isinstance(page, dict) and page.get("source_bytes") == 0:
            issues.append(issue("blank_preview_source", f"preview page {page.get('page')} has an empty SVG source"))
    asset_issues, asset_warnings, asset_summary = asset_review(project)
    issues.extend(asset_issues)

    result = {
        "version": "svglide-aesthetic-review/v1",
        "review_mode": "automated_preview_record",
        "reviewed_at": now_iso(),
        "status": "failed" if issues else "passed",
        "preview_path": PREVIEW_HTML.as_posix(),
        "manifest_path": PREVIEW_MANIFEST.as_posix(),
        "page_count": actual,
        "asset_review": asset_summary,
        "summary": {
            "error_count": len(issues),
            "warning_count": len(asset_warnings),
        },
        "issues": issues,
        "warnings": asset_warnings,
        "action": FAIL_ACTION if issues else PASS_ACTION,
    }
    output = project / AESTHETIC_REVIEW
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record automated SVGlide preview aesthetic review gate.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_aesthetic_review(Path(args.project))
    except (OSError, AestheticReviewError) as error:
        print(f"svglide_aesthetic_review: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["action"] == PASS_ACTION else 1


if __name__ == "__main__":
    raise SystemExit(main())
