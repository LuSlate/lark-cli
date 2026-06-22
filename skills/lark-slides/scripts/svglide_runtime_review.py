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


PLAN_PATH = Path("02-plan/slide_plan.json")
PROJECT_REGISTRY_PATH = Path("02-plan/renderer-registry.json")
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "svglide-renderer-registry.json"
ASSET_MANIFEST_PATH = Path("03-assets/asset-manifest.json")
ARTBOARD_DIR = Path("04-svg/artboard")
OUTPUT_PATH = Path("06-check/runtime-review.json")
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"
FAMILY_ALIASES = {
    "annotation_board": {"annotated-field-board"},
    "architectural_spec": {"architectural-spec", "architecture"},
    "briefing": {"intelligence-brief", "cover"},
    "catalog": {"product-ribbon"},
    "dashboard": {"executive-dashboard", "metric-dashboard"},
    "ledger": {"ledger-briefing"},
    "matrix": {"brutalist-matrix", "comparison"},
    "poster_stat": {"poster-stat-punch", "closing"},
    "serif_stat": {"serif-stat-editorial"},
    "trend_grid": {"trend-grid-report"},
}


class RuntimeReviewError(Exception):
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
        raise RuntimeReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeReviewError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_object_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_object(path)


def issue(code: str, message: str, *, page: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    return payload


def assets_by_page(project: Path) -> dict[int, list[dict[str, Any]]]:
    manifest = read_json_object_optional(project / ASSET_MANIFEST_PATH)
    raw_items = manifest.get("acquired_assets")
    if not isinstance(raw_items, list):
        return {}
    by_page: dict[int, list[dict[str, Any]]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_page = item.get("page") or item.get("usage_page")
        if isinstance(raw_page, int):
            by_page.setdefault(raw_page, []).append(item)
    return by_page


def decorative_trace_issues(project: Path) -> list[dict[str, Any]]:
    artboard_dir = project / ARTBOARD_DIR
    if not artboard_dir.exists():
        return []
    issues: list[dict[str, Any]] = []
    for path in sorted(artboard_dir.glob("page-*.semantic-map.json")):
        try:
            payload = read_json_object(path)
        except RuntimeReviewError as err:
            issues.append(issue("semantic_map_invalid", str(err)))
            continue
        page = payload.get("page") if isinstance(payload.get("page"), int) else None
        elements = payload.get("elements")
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            role = element.get("role")
            if role not in {"background", "container", "decorative"}:
                continue
            origin = element.get("origin")
            if not isinstance(origin, dict):
                issues.append(
                    issue(
                        "decorative_origin_missing",
                        f"semantic element {element.get('element_id')!r} requires machine-readable origin",
                        page=page,
                    )
                )
                continue
            if origin.get("type") not in {"template", "theme", "canvas_spec", "semantic_map", "guardrail"}:
                issues.append(
                    issue(
                        "decorative_origin_type_invalid",
                        f"semantic element {element.get('element_id')!r} has invalid origin.type",
                        page=page,
                    )
                )
            element_type = str(element.get("element_type") or "")
            kind = str(element.get("kind") or "")
            if role == "decorative" and (element_type in {"decorative_line", "decorative_path"} or kind in {"line", "path"}):
                purpose = element.get("semantic_purpose") or element.get("purpose")
                if not isinstance(purpose, str) or not purpose.strip():
                    issues.append(
                        issue(
                            "decorative_semantic_purpose_missing",
                            f"decorative {kind or element_type} {element.get('element_id')!r} requires semantic_purpose",
                            page=page,
                        )
                    )
    return issues


def registry_path_for(project: Path) -> Path:
    project_registry = project / PROJECT_REGISTRY_PATH
    return project_registry if project_registry.exists() else DEFAULT_REGISTRY_PATH


def load_registry(project: Path) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    path = registry_path_for(project)
    registry = read_json_object(path)
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-renderer-registry.schema.json"))
    issues = [issue(item["code"], f"{item['path']}: {item['message']}") for item in svglide_schema.validate_json_schema(registry, schema)]
    by_id: dict[str, dict[str, Any]] = {}
    renderers = registry.get("renderers")
    if isinstance(renderers, list):
        for item in renderers:
            if not isinstance(item, dict):
                continue
            renderer_id = item.get("id")
            if isinstance(renderer_id, str):
                if renderer_id in by_id:
                    issues.append(issue("renderer_registry_duplicate_id", f"duplicate renderer id: {renderer_id}"))
                by_id[renderer_id] = item
    return path, registry, by_id, issues


def style_preset_allowed(style_preset: Any, renderer: dict[str, Any]) -> bool:
    allowed = renderer.get("allowed_style_presets")
    if not isinstance(allowed, list) or "*" in allowed:
        return True
    if not isinstance(style_preset, str) or not style_preset:
        return True
    return style_preset in allowed


def normalize_family(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def renderer_suffix(renderer_id: Any) -> str | None:
    if not isinstance(renderer_id, str) or not renderer_id:
        return None
    return renderer_id.rsplit(".", 1)[-1]


def family_matches(plan_family: str, registry_family: str, renderer_id: Any) -> bool:
    plan_norm = normalize_family(plan_family)
    registry_norm = normalize_family(registry_family)
    if plan_norm == registry_norm:
        return True
    aliases = {normalize_family(item) for item in FAMILY_ALIASES.get(plan_norm, set())}
    suffix = renderer_suffix(renderer_id)
    suffix_norm = normalize_family(suffix) if suffix else None
    return registry_norm in aliases or (suffix_norm is not None and suffix_norm in aliases)


def accepts_cover_asset(slide: dict[str, Any], renderer: Any, family: Any) -> bool:
    if slide.get("page_type") == "cover":
        return True
    if isinstance(family, str) and family_matches(family, "cover", renderer):
        return True
    return isinstance(renderer, str) and "cover" in renderer


def accepts_closing_asset(slide: dict[str, Any], renderer: Any, family: Any) -> bool:
    if slide.get("page_type") == "closing":
        return True
    if isinstance(family, str) and family_matches(family, "closing", renderer):
        return True
    return isinstance(renderer, str) and "closing" in renderer


def run_runtime_review(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan_file = project / PLAN_PATH
    if not plan_file.exists():
        raise RuntimeReviewError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_file)
    registry_path, _registry, registry, issues = load_registry(project)
    page_assets = assets_by_page(project)
    issues.extend(decorative_trace_issues(project))
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    renderers: list[str] = []
    families: list[str] = []
    pages: list[dict[str, Any]] = []
    style_preset = plan.get("style_preset")
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict):
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        renderer = raw_slide.get("renderer_id")
        family = raw_slide.get("layout_family")
        current_assets = page_assets.get(page, [])
        renderer_record = registry.get(renderer) if isinstance(renderer, str) else None
        page_status = "passed"
        if not isinstance(renderer, str) or not renderer.strip():
            issues.append(issue("renderer_id_missing", "each slide must declare renderer_id", page=page))
            page_status = "failed"
        else:
            renderers.append(renderer)
            if renderer_record is None:
                issues.append(issue("renderer_unknown", f"renderer_id is not present in registry: {renderer}", page=page))
                page_status = "failed"
            else:
                status = renderer_record.get("status")
                if status != "active":
                    issues.append(issue("renderer_not_active", f"renderer_id {renderer} status is {status}", page=page))
                    page_status = "failed"
                if not style_preset_allowed(style_preset, renderer_record):
                    issues.append(issue("renderer_style_preset_not_allowed", f"renderer_id {renderer} does not allow style_preset {style_preset}", page=page))
                    page_status = "failed"
        if not isinstance(family, str) or not family.strip():
            issues.append(issue("layout_family_missing", "each slide must declare layout_family", page=page))
            page_status = "failed"
        else:
            families.append(family)
            if (
                isinstance(renderer_record, dict)
                and isinstance(renderer_record.get("family"), str)
                and not family_matches(family, renderer_record["family"], renderer)
            ):
                issues.append(issue("renderer_family_mismatch", f"layout_family {family} does not match registry family {renderer_record.get('family')}", page=page))
                page_status = "failed"
        for asset in current_assets:
            role = asset.get("placement_role")
            status = asset.get("status")
            if role == "cover" and status in {"acquired", "planned"} and not accepts_cover_asset(raw_slide, renderer, family):
                issues.append(issue("asset_renderer_mismatch", "cover asset should use a cover renderer", page=page))
                page_status = "failed"
            if role == "closing" and status in {"acquired", "planned"} and not accepts_closing_asset(raw_slide, renderer, family):
                issues.append(issue("asset_renderer_mismatch", "closing asset should use a closing layout family", page=page))
                page_status = "failed"
        pages.append(
            {
                "page": page,
                "renderer_id": renderer,
                "registry_status": renderer_record.get("status") if isinstance(renderer_record, dict) else "unknown",
                "layout_family": family,
                "registry_family": renderer_record.get("family") if isinstance(renderer_record, dict) else None,
                "asset_count": len(current_assets),
                "asset_roles": [item.get("placement_role") for item in current_assets if isinstance(item, dict)],
                "status": page_status,
            }
        )
    renderer_count = len(set(renderers))
    family_count = len(set(families))
    if len(slides) >= 4 and renderer_count <= 1:
        issues.append(issue("renderer_monoculture", "decks with at least 4 slides need more than one renderer_id"))
    if len(slides) >= 4 and family_count <= 1:
        issues.append(issue("layout_family_monoculture", "decks with at least 4 slides need more than one layout_family"))
    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-runtime-review/v1",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": file_sha256(plan_file),
            "style_preset": style_preset,
        },
        "registry": {
            "path": str(registry_path if registry_path.is_absolute() else registry_path.as_posix()),
            "sha256": file_sha256(registry_path),
        },
        "pages": pages,
        "renderers": sorted(set(renderers)),
        "layout_families": sorted(set(families)),
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "slide_count": len(slides),
            "renderer_count": renderer_count,
            "layout_family_count": family_count,
            "asset_page_count": len(page_assets),
        },
        "issues": issues,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-runtime-review.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["action"] = FAIL_ACTION
        result["issues"].extend(issue(item["code"], item["message"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review SVGlide runtime renderer and visual diversity contracts.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_runtime_review(Path(args.project))
    except (OSError, RuntimeReviewError) as error:
        print(f"svglide_runtime_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
