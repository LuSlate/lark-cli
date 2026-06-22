#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_VERSION = "svglide-visual-acceptance/v1"
TEMPLATE_GUARDRAILS_PATH = SCRIPT_DIR.parent / "references" / "svglide-template-guardrails.json"
CHECK_PATH = Path("06-check/visual-acceptance.json")
RECEIPT_PATH = Path("receipts/visual_acceptance.json")
INSTRUCTION_PATH = Path("00-input/instruction.json")
PLAN_PATH = Path("02-plan/slide_plan.json")
ASSET_MANIFEST_PATH = Path("03-assets/asset-manifest.json")
GENERATOR_RECEIPT_PATH = Path("receipts/generate_svg.json")
QUALITY_GATE_PATH = Path("06-check/quality-gate.json")
DRY_RUN_PATH = Path("07-create/dry-run.json")
PREVIEW_PATH = Path("05-preview/preview.html")
PREVIEW_MANIFEST_PATH = Path("05-preview/preview-manifest.json")
CONTACT_SHEET_PATH = Path("05-preview/contact-sheet.png")
PASS_ACTION = "deliverable_pass"
FAIL_ACTION = "repair_and_rerun"
SKIP_ACTION = "engineering_only"
TEXT_ROLES = {"title", "subtitle", "body", "body_point", "paragraph", "key_message", "eyebrow", "label", "badge"}
HIGH_PRIORITY_TEXT_ROLES = {"title", "subtitle", "body", "body_point", "paragraph", "key_message"}
SHARP_DECORATION_KINDS = {"path", "polygon", "polyline"}
CONTACT_SHEET_TILE_WIDTH = 320
CONTACT_SHEET_TILE_HEIGHT = 180
CONTACT_SHEET_GAP = 16
CONTACT_SHEET_MAX_COLS = 3


class VisualAcceptanceError(Exception):
    pass


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.lower() == "id" and value:
                self.ids.add(value)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise VisualAcceptanceError(f"missing required JSON file: {path}") from error
    except json.JSONDecodeError as error:
        raise VisualAcceptanceError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise VisualAcceptanceError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_optional(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        return read_json_object(path)
    except (OSError, VisualAcceptanceError):
        return {}


def load_template_guardrails() -> dict[str, Any]:
    return read_json_optional(TEMPLATE_GUARDRAILS_PATH)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def optional_sha256(path: Path) -> str | None:
    return file_sha256(path) if path.exists() and path.is_file() else None


def relpath(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None, bbox: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path is not None:
        payload["path"] = path
    if bbox is not None:
        payload["bbox"] = bbox
    return payload


def contact_sheet_tile_bbox(page: int, page_count: int) -> dict[str, int] | None:
    if page <= 0 or page_count <= 0:
        return None
    cols = min(CONTACT_SHEET_MAX_COLS, page_count)
    if cols <= 0:
        return None
    index = page - 1
    return {
        "x": CONTACT_SHEET_GAP + (index % cols) * (CONTACT_SHEET_TILE_WIDTH + CONTACT_SHEET_GAP),
        "y": CONTACT_SHEET_GAP + (index // cols) * (CONTACT_SHEET_TILE_HEIGHT + CONTACT_SHEET_GAP),
        "width": CONTACT_SHEET_TILE_WIDTH,
        "height": CONTACT_SHEET_TILE_HEIGHT,
    }


def html_ids(path: Path) -> set[str]:
    parser = IdCollector()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.ids


def check_preview_anchor_targets(project: Path, page_results: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    preview_path = project / PREVIEW_PATH
    if not preview_path.exists() or not preview_path.is_file():
        return
    ids = html_ids(preview_path)
    for page_result in page_results:
        page = page_result.get("page")
        if not isinstance(page, int):
            continue
        anchor = f"page-{page}"
        if anchor not in ids:
            issues.append(
                issue(
                    "preview_anchor_missing",
                    f"preview.html must include id=\"{anchor}\" for page {page}",
                    page=page,
                    path=PREVIEW_PATH.as_posix(),
                )
            )


def expected_page_count(instruction: dict[str, Any], plan: dict[str, Any]) -> int | None:
    for raw in [
        instruction.get("target_slide_count"),
        instruction.get("page_count"),
        plan.get("target_slide_count"),
        plan.get("page_count"),
    ]:
        if isinstance(raw, int) and raw > 0:
            return raw
    slides = plan.get("slides")
    return len(slides) if isinstance(slides, list) and slides else None


def generation_mode(plan: dict[str, Any], generator: dict[str, Any]) -> str:
    raw = generator.get("generation_mode") or plan.get("generation_mode") or "direct_svg"
    return raw if raw in {"direct_svg", "artboard_satori"} else "unknown"


def path_record(path: Path, project: Path) -> dict[str, str] | None:
    if not path.exists() or not path.is_file():
        return None
    return {"path": relpath(path, project), "sha256": file_sha256(path)}


def artifact_record(project: Path, rel: Any, *, kind: str) -> dict[str, str] | None:
    if not isinstance(rel, str) or not rel:
        return None
    record = path_record(project / rel, project)
    if record is None:
        return None
    record["kind"] = kind
    return record


def bbox_from(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        x = float(value["x"])
        y = float(value["y"])
        width = float(value["width"])
        height = float(value["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def node_bbox(node: dict[str, Any]) -> dict[str, float] | None:
    return bbox_from(node.get("bbox")) or bbox_from(node)


def bbox_inside(inner: dict[str, float], outer: dict[str, float], *, tolerance: float = 0.5) -> bool:
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance
    )


def intersection_area(left: dict[str, float], right: dict[str, float]) -> float:
    x1 = max(left["x"], right["x"])
    y1 = max(left["y"], right["y"])
    x2 = min(left["x"] + left["width"], right["x"] + right["width"])
    y2 = min(left["y"] + left["height"], right["y"] + right["height"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def overlap_ratio(left: dict[str, float], right: dict[str, float]) -> float:
    area = intersection_area(left, right)
    if area <= 0:
        return 0.0
    left_area = left["width"] * left["height"]
    right_area = right["width"] * right["height"]
    return area / min(left_area, right_area)


def slide_by_page(plan: dict[str, Any], page: int) -> dict[str, Any]:
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    for item in slides:
        if isinstance(item, dict) and item.get("page") == page:
            return item
    if 1 <= page <= len(slides) and isinstance(slides[page - 1], dict):
        return slides[page - 1]
    return {}


def canvas_from_slide(slide: dict[str, Any]) -> dict[str, float]:
    spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
    canvas = spec.get("canvas") if isinstance(spec.get("canvas"), dict) else {}
    return {
        "x": 0.0,
        "y": 0.0,
        "width": float(canvas.get("width") or 960),
        "height": float(canvas.get("height") or 540),
    }


def safe_area_from_slide(slide: dict[str, Any], canvas: dict[str, float]) -> dict[str, float]:
    spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
    raw = spec.get("safe_area") or (spec.get("quality_constraints", {}) if isinstance(spec.get("quality_constraints"), dict) else {}).get("safe_area")
    return bbox_from(raw) or {"x": 48.0, "y": 40.0, "width": max(0.0, canvas["width"] - 96), "height": max(0.0, canvas["height"] - 80)}


def template_guardrail(template_id: str, guardrails: dict[str, Any]) -> dict[str, Any]:
    defaults = guardrails.get("defaults") if isinstance(guardrails.get("defaults"), dict) else {}
    templates = guardrails.get("templates") if isinstance(guardrails.get("templates"), dict) else {}
    template = templates.get(template_id) if isinstance(templates.get(template_id), dict) else {}
    merged: dict[str, Any] = dict(defaults)
    for key, value in template.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            child = dict(merged[key])
            child.update(value)
            merged[key] = child
        else:
            merged[key] = value
    return merged


def template_origin_matches(element: dict[str, Any], template_id: str) -> bool:
    origin = element.get("origin")
    if not isinstance(origin, dict):
        return False
    return origin.get("type") == "template" and origin.get("id") == template_id


def motif_registered(element_id: str, element: dict[str, Any], decorative_rules: dict[str, Any], *, template_id: str = "") -> bool:
    if template_id and template_origin_matches(element, template_id):
        return True
    motifs = decorative_rules.get("admitted_motifs")
    motif_tokens = [str(item).lower() for item in motifs] if isinstance(motifs, list) else []
    explicit = element.get("motif_id") or element.get("template_motif")
    if isinstance(explicit, str) and explicit.lower() in motif_tokens:
        return True
    return any(token and token in element_id for token in motif_tokens)


def text_line_group_count(elements: list[dict[str, Any]]) -> int:
    rows: list[dict[str, float]] = []
    for element in sorted(elements, key=lambda item: ((bbox_from(item.get("bbox")) or {}).get("y", 0), (bbox_from(item.get("bbox")) or {}).get("x", 0))):
        bbox = bbox_from(element.get("bbox"))
        if bbox is None:
            continue
        matched = False
        for row in rows:
            tolerance = max(3.0, min(row["height"], bbox["height"]) * 0.35)
            if abs(row["y"] - bbox["y"]) <= tolerance:
                row["height"] = max(row["height"], bbox["height"])
                matched = True
                break
        if not matched:
            rows.append({"y": bbox["y"], "height": bbox["height"]})
    return len(rows)


def logical_density_counts(elements: list[dict[str, Any]], *, template_id: str) -> dict[str, int]:
    text_elements = [element for element in elements if isinstance(element, dict) and str(element.get("kind") or "") == "text"]
    text_count = text_line_group_count(text_elements)
    non_template_decorative = 0
    template_decorative_present = False
    other_nodes = 0
    for element in elements:
        if not isinstance(element, dict):
            continue
        kind = str(element.get("kind") or "")
        role = str(element.get("role") or "")
        if kind == "text":
            continue
        if role == "decorative":
            if template_origin_matches(element, template_id):
                template_decorative_present = True
            else:
                non_template_decorative += 1
        else:
            other_nodes += 1
    total = text_count + non_template_decorative + other_nodes + (1 if template_decorative_present else 0)
    return {
        "total_nodes": total,
        "text_nodes": text_count,
        "decorative_nodes": non_template_decorative,
    }


def slide_declares_image_slot(slide: dict[str, Any], image_rules: dict[str, Any]) -> bool:
    spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
    content = spec.get("content") if isinstance(spec.get("content"), dict) else {}
    fields = image_rules.get("allowed_slot_fields")
    slot_fields = [str(item) for item in fields] if isinstance(fields, list) else ["asset_slots", "image_slots", "assets"]
    for field in slot_fields:
        value = spec.get(field)
        if value:
            return True
        if content.get(field):
            return True
    for field in ["image", "image_asset", "key_visual", "hero_image"]:
        if content.get(field) or spec.get(field):
            return True
    return False


def check_status_file(project: Path, rel: Path, issues: list[dict[str, Any]], *, code_prefix: str) -> dict[str, Any]:
    path = project / rel
    if not path.exists():
        issues.append(issue(f"{code_prefix}_missing", f"required file is missing: {rel.as_posix()}", path=rel.as_posix()))
        return {}
    payload = read_json_object(path)
    if payload.get("status") != "passed":
        issues.append(issue(f"{code_prefix}_not_passed", f"{rel.as_posix()} status must be passed", path=rel.as_posix()))
    return payload


def check_recorded_hash(
    project: Path,
    record: dict[str, Any],
    *,
    path_key: str,
    hash_key: str,
    code_prefix: str,
    issues: list[dict[str, Any]],
    page: int | None = None,
) -> None:
    rel = record.get(path_key)
    recorded = record.get(hash_key)
    if not isinstance(rel, str) or not rel:
        issues.append(issue(f"{code_prefix}_{path_key}_missing", f"receipt must include {path_key}", page=page))
        return
    target = project / rel
    if not target.exists():
        issues.append(issue(f"{code_prefix}_{path_key}_file_missing", f"artifact is missing: {rel}", page=page, path=rel))
        return
    if recorded != file_sha256(target):
        issues.append(issue(f"{code_prefix}_{path_key}_stale", f"artifact hash is stale: {rel}", page=page, path=rel))


def check_contact_sheet(project: Path, generator: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, str] | None:
    if not (project / CONTACT_SHEET_PATH).exists():
        issues.append(issue("contact_sheet_missing", f"visual acceptance requires {CONTACT_SHEET_PATH.as_posix()}", path=CONTACT_SHEET_PATH.as_posix()))
        return None
    contact_record = path_record(project / CONTACT_SHEET_PATH, project)
    generated = generator.get("contact_sheet")
    if isinstance(generated, dict):
        rel = generated.get("path")
        sha = generated.get("sha256")
        if rel != CONTACT_SHEET_PATH.as_posix():
            issues.append(issue("contact_sheet_path_invalid", f"contact_sheet.path must be {CONTACT_SHEET_PATH.as_posix()}"))
        if sha != contact_record["sha256"]:
            issues.append(issue("contact_sheet_stale", "contact sheet hash does not match generator receipt", path=CONTACT_SHEET_PATH.as_posix()))
    else:
        issues.append(issue("contact_sheet_receipt_missing", "generate_svg receipt must include contact_sheet"))
    return contact_record


def check_page_layout(project: Path, plan: dict[str, Any], receipt_path: str, issues: list[dict[str, Any]], guardrails: dict[str, Any]) -> dict[str, Any]:
    receipt_file = project / receipt_path
    if not receipt_file.exists():
        issues.append(issue("artboard_receipt_missing", f"artboard receipt is missing: {receipt_path}", path=receipt_path))
        return {"page": None, "status": "failed", "issues": []}
    receipt = read_json_object(receipt_file)
    page = int(receipt.get("page") or 0)
    template_id = str(receipt.get("template_id") or "")
    rules = template_guardrail(template_id, guardrails)
    decorative_rules = rules.get("decorative") if isinstance(rules.get("decorative"), dict) else {}
    density_rules = rules.get("density") if isinstance(rules.get("density"), dict) else {}
    image_rules = rules.get("image") if isinstance(rules.get("image"), dict) else {}
    page_issues: list[dict[str, Any]] = []
    if receipt.get("status") != "passed":
        page_issues.append(issue("artboard_receipt_not_passed", "artboard receipt status must be passed", page=page, path=receipt_path))
    artifacts: list[dict[str, str]] = []
    receipt_record = path_record(receipt_file, project)
    if receipt_record is not None:
        receipt_record["kind"] = "artboard_receipt"
        artifacts.append(receipt_record)
    for path_key, hash_key, code_prefix in [
        ("semantic_map", "semantic_map_sha256", "semantic_map"),
        ("node_layout_map", "node_layout_map_sha256", "node_layout_map"),
        ("png", "png_sha256", "page_png"),
    ]:
        check_recorded_hash(project, receipt, path_key=path_key, hash_key=hash_key, code_prefix=code_prefix, issues=page_issues, page=page)
        record = artifact_record(project, receipt.get(path_key), kind=code_prefix)
        if record is not None:
            artifacts.append(record)

    semantic_map = read_json_optional(project / str(receipt.get("semantic_map") or ""))
    node_map = read_json_optional(project / str(receipt.get("node_layout_map") or ""))
    slide = slide_by_page(plan, page)
    canvas = canvas_from_slide(slide)
    safe_area = safe_area_from_slide(slide, canvas)

    text_elements: list[dict[str, Any]] = []
    semantic_elements = semantic_map.get("elements") if isinstance(semantic_map.get("elements"), list) else []
    for element in semantic_elements:
        if not isinstance(element, dict):
            continue
        role = str(element.get("role") or "")
        kind = str(element.get("kind") or "")
        bbox = bbox_from(element.get("bbox"))
        element_id = str(element.get("element_id") or "").lower()
        if bbox is None:
            page_issues.append(issue("element_bbox_invalid", "semantic element bbox must be positive", page=page, path=receipt.get("semantic_map"), bbox=element.get("bbox") if isinstance(element.get("bbox"), dict) else None))
            continue
        if not bbox_inside(bbox, canvas):
            page_issues.append(issue("element_outside_canvas", f"element {element.get('element_id')} is outside canvas", page=page, path=receipt.get("semantic_map"), bbox=bbox))
        if role in TEXT_ROLES or kind == "text":
            text_elements.append({"id": element.get("element_id"), "role": role, "bbox": bbox})
            if role in HIGH_PRIORITY_TEXT_ROLES and not bbox_inside(bbox, safe_area):
                page_issues.append(issue("text_outside_safe_area", f"text element {element.get('element_id')} is outside safe area", page=page, path=receipt.get("semantic_map"), bbox=bbox))
        if role == "decorative":
            allowed_kinds = decorative_rules.get("allowed_kinds")
            allowed = {str(item) for item in allowed_kinds} if isinstance(allowed_kinds, list) else set()
            if allowed and kind not in allowed:
                page_issues.append(issue("decorative_kind_not_allowed", f"template {template_id} does not allow decorative {kind}", page=page, path=receipt.get("semantic_map"), bbox=bbox))
            registered_motif = motif_registered(element_id, element, decorative_rules, template_id=template_id)
            if not registered_motif:
                page_issues.append(issue("unregistered_template_motif", f"decorative element {element.get('element_id')} is not an admitted template motif", page=page, path=receipt.get("semantic_map"), bbox=bbox))
            if kind in SHARP_DECORATION_KINDS and (kind not in allowed or not registered_motif):
                page_issues.append(issue("unregistered_sharp_decoration", f"decorative {kind} requires an admitted template motif", page=page, path=receipt.get("semantic_map"), bbox=bbox))
        if ("chart" in element_id or role in {"chart", "data_chart"}) and not isinstance(slide.get("chart_contract"), dict):
            page_issues.append(issue("chart_like_mark_without_contract", f"chart-like element {element.get('element_id')} requires chart_contract", page=page, path=receipt.get("semantic_map"), bbox=bbox))
        if kind in {"image", "raster", "bitmap"} or role in {"image", "key_visual", "hero_image"}:
            if image_rules.get("requires_canvas_slot", True) and not slide_declares_image_slot(slide, image_rules):
                page_issues.append(issue("image_without_canvas_slot", f"image element {element.get('element_id')} requires a CanvasSpec image slot", page=page, path=receipt.get("semantic_map"), bbox=bbox))
            source_ref = element.get("source_ref")
            if not isinstance(source_ref, str) or not source_ref.startswith("canvas_spec."):
                page_issues.append(issue("image_without_canvas_source_ref", f"image element {element.get('element_id')} must be sourced from CanvasSpec", page=page, path=receipt.get("semantic_map"), bbox=bbox))

    for index, left in enumerate(text_elements):
        if left["role"] not in HIGH_PRIORITY_TEXT_ROLES:
            continue
        for right in text_elements[index + 1 :]:
            if right["role"] not in HIGH_PRIORITY_TEXT_ROLES:
                continue
            ratio = overlap_ratio(left["bbox"], right["bbox"])
            if ratio > 0.08:
                page_issues.append(
                    issue(
                        "high_priority_text_overlap",
                        f"text elements {left['id']} and {right['id']} overlap by {ratio:.2f}",
                        page=page,
                        path=receipt.get("semantic_map"),
                        bbox=left["bbox"],
                    )
                )

    nodes = node_map.get("nodes") if isinstance(node_map.get("nodes"), list) else []
    density_counts = logical_density_counts([element for element in semantic_elements if isinstance(element, dict)], template_id=template_id)
    max_nodes = density_rules.get("max_nodes") if isinstance(density_rules.get("max_nodes"), int) else 90
    max_text_nodes = density_rules.get("max_text_nodes") if isinstance(density_rules.get("max_text_nodes"), int) else 34
    max_decorative = decorative_rules.get("max_count") if isinstance(decorative_rules.get("max_count"), int) else 8
    if density_counts["total_nodes"] > max_nodes:
        page_issues.append(issue("page_density_too_high", f"page has {density_counts['total_nodes']} logical layout nodes; template limit is {max_nodes}", page=page, path=receipt.get("node_layout_map")))
    if density_counts["text_nodes"] > max_text_nodes:
        page_issues.append(issue("text_density_too_high", f"page has {density_counts['text_nodes']} logical text nodes; template limit is {max_text_nodes}", page=page, path=receipt.get("node_layout_map")))
    if density_counts["decorative_nodes"] > max_decorative:
        page_issues.append(issue("decorative_density_too_high", f"page has {density_counts['decorative_nodes']} non-template decorative elements; template limit is {max_decorative}", page=page, path=receipt.get("semantic_map")))

    issues.extend(page_issues)
    return {
        "page": page,
        "path": receipt_path,
        "template_id": receipt.get("template_id"),
        "template_guardrail": {
            "path": str(TEMPLATE_GUARDRAILS_PATH),
            "schema_version": guardrails.get("schema_version"),
        },
        "theme_id": receipt.get("theme_id"),
        "semantic_map": receipt.get("semantic_map"),
        "node_layout_map": receipt.get("node_layout_map"),
        "png": receipt.get("png"),
        "artifacts": artifacts,
        "status": "failed" if page_issues else "passed",
        "issue_count": len(page_issues),
        "issues": page_issues,
    }


def check_deck_rhythm(plan: dict[str, Any], page_results: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    build_deck_rhythm(plan, page_results, issues)


def longest_run(sequence: list[str]) -> dict[str, Any]:
    if not sequence:
        return {"value": None, "length": 0}
    best_value = sequence[0]
    best_len = 1
    current_value = sequence[0]
    current_len = 1
    for value in sequence[1:]:
        if value == current_value:
            current_len += 1
        else:
            if current_len > best_len:
                best_value = current_value
                best_len = current_len
            current_value = value
            current_len = 1
    if current_len > best_len:
        best_value = current_value
        best_len = current_len
    return {"value": best_value, "length": best_len}


def build_deck_rhythm(plan: dict[str, Any], page_results: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    slide_count = len(slides)
    layout_sequence = [slide.get("layout_family") for slide in slides if isinstance(slide, dict) and isinstance(slide.get("layout_family"), str)]
    renderer_sequence = [slide.get("renderer_id") for slide in slides if isinstance(slide, dict) and isinstance(slide.get("renderer_id"), str)]
    visual_recipe_sequence = [slide.get("visual_recipe") for slide in slides if isinstance(slide, dict) and isinstance(slide.get("visual_recipe"), str)]
    theme_ids = [item.get("theme_id") for item in page_results if isinstance(item.get("theme_id"), str)]
    layout_run = longest_run(layout_sequence)
    renderer_run = longest_run(renderer_sequence)
    visual_recipe_run = longest_run(visual_recipe_sequence)
    thresholds = {
        "min_unique_layout_families_for_4plus": 2,
        "min_unique_renderers_for_4plus": 2,
        "min_unique_visual_recipes_for_4plus": 2,
        "max_consecutive_renderer_repeat": 3,
        "max_theme_ids": 2,
    }
    if slide_count >= 3 and layout_sequence and len(set(layout_sequence)) == 1:
        issues.append(issue("layout_rhythm_collapsed", "all slides use the same layout_family; deck rhythm is not planned"))
    if slide_count >= 3 and renderer_sequence and len(set(renderer_sequence)) == 1:
        issues.append(issue("renderer_sequence_collapsed", "all slides use the same renderer_id; deck rhythm is not planned"))
    if slide_count >= 4 and layout_sequence and len(set(layout_sequence)) < thresholds["min_unique_layout_families_for_4plus"]:
        issues.append(issue("layout_family_variety_too_low", "deck with four or more slides needs at least two layout families"))
    if slide_count >= 4 and renderer_sequence and len(set(renderer_sequence)) < thresholds["min_unique_renderers_for_4plus"]:
        issues.append(issue("renderer_variety_too_low", "deck with four or more slides needs at least two renderers"))
    if slide_count >= 4 and visual_recipe_sequence and len(set(visual_recipe_sequence)) < thresholds["min_unique_visual_recipes_for_4plus"]:
        issues.append(issue("visual_recipe_collapsed", "deck visual_recipe sequence collapsed to one generic look"))
    if renderer_run["length"] > thresholds["max_consecutive_renderer_repeat"]:
        issues.append(issue("renderer_sequence_repetition_too_long", f"renderer {renderer_run['value']} repeats {renderer_run['length']} consecutive pages"))
    theme_policy = plan.get("theme_policy") if isinstance(plan.get("theme_policy"), dict) else {}
    allow_multi_theme = theme_policy.get("allow_multi_theme") is True
    if theme_ids and len(set(theme_ids)) > thresholds["max_theme_ids"] and not allow_multi_theme:
        issues.append(issue("theme_palette_too_fragmented", "too many theme_ids for one deck; theme token budget is fragmented"))
    return {
        "schema_version": "svglide-deck-rhythm/v1",
        "slide_count": slide_count,
        "layout_family_sequence": layout_sequence,
        "renderer_sequence": renderer_sequence,
        "visual_recipe_sequence": visual_recipe_sequence,
        "theme_ids": theme_ids,
        "unique_layout_family_count": len(set(layout_sequence)),
        "unique_renderer_count": len(set(renderer_sequence)),
        "unique_visual_recipe_count": len(set(visual_recipe_sequence)),
        "unique_theme_id_count": len(set(theme_ids)),
        "longest_layout_run": layout_run,
        "longest_renderer_run": renderer_run,
        "longest_visual_recipe_run": visual_recipe_run,
        "thresholds": thresholds,
        "theme_policy": theme_policy,
    }


def build_visual_evidence(
    project: Path,
    *,
    preview_manifest: dict[str, Any],
    page_results: list[dict[str, Any]],
    contact_sheet: dict[str, str] | None,
) -> dict[str, Any]:
    page_count = len(page_results) or (preview_manifest.get("page_count") if isinstance(preview_manifest.get("page_count"), int) else 0)
    preview_record = path_record(project / PREVIEW_PATH, project)
    preview_manifest_record = path_record(project / PREVIEW_MANIFEST_PATH, project)
    manifest_pages = {
        item.get("page"): item
        for item in preview_manifest.get("pages", [])
        if isinstance(item, dict) and isinstance(item.get("page"), int)
    } if isinstance(preview_manifest.get("pages"), list) else {}
    evidence_pages: list[dict[str, Any]] = []
    for page_result in page_results:
        page = page_result.get("page")
        if not isinstance(page, int):
            continue
        manifest_page = manifest_pages.get(page) if isinstance(manifest_pages.get(page), dict) else {}
        page_png = page_result.get("png")
        page_evidence = {
            "page": page,
            "evidence_path": CONTACT_SHEET_PATH.as_posix() if contact_sheet else page_png,
            "contact_sheet": CONTACT_SHEET_PATH.as_posix() if contact_sheet else None,
            "contact_sheet_sha256": contact_sheet.get("sha256") if isinstance(contact_sheet, dict) else None,
            "contact_sheet_tile": contact_sheet_tile_bbox(page, page_count),
            "contact_sheet_crop_source": "artboard_renderer_fixed_grid_v1",
            "preview": PREVIEW_PATH.as_posix() if (project / PREVIEW_PATH).exists() else None,
            "preview_sha256": preview_record.get("sha256") if isinstance(preview_record, dict) else None,
            "preview_anchor": f"{PREVIEW_PATH.as_posix()}#page-{page}",
            "preview_manifest_sha256": preview_manifest_record.get("sha256") if isinstance(preview_manifest_record, dict) else None,
            "preview_source_path": manifest_page.get("source_path") if isinstance(manifest_page, dict) else None,
            "page_png": page_png,
            "page_png_sha256": optional_sha256(project / page_png) if isinstance(page_png, str) else None,
            "semantic_map": page_result.get("semantic_map"),
            "node_layout_map": page_result.get("node_layout_map"),
        }
        evidence_pages.append(page_evidence)
        page_result["visual_evidence"] = page_evidence
    return {
        "schema_version": "svglide-visual-evidence/v1",
        "contact_sheet": contact_sheet,
        "contact_sheet_grid": {
            "tile_width": CONTACT_SHEET_TILE_WIDTH,
            "tile_height": CONTACT_SHEET_TILE_HEIGHT,
            "gap": CONTACT_SHEET_GAP,
            "max_cols": CONTACT_SHEET_MAX_COLS,
            "page_count": page_count,
        },
        "preview": preview_record,
        "preview_manifest": preview_manifest_record,
        "pages": evidence_pages,
    }


def attach_issue_evidence(issues: list[dict[str, Any]], visual_evidence: dict[str, Any]) -> None:
    pages = visual_evidence.get("pages")
    by_page = {
        item.get("page"): item
        for item in pages
        if isinstance(item, dict) and isinstance(item.get("page"), int)
    } if isinstance(pages, list) else {}
    for item in issues:
        page = item.get("page")
        page_evidence = by_page.get(page)
        if not isinstance(page_evidence, dict):
            continue
        item.setdefault("evidence_path", page_evidence.get("evidence_path"))
        item.setdefault("preview_anchor", page_evidence.get("preview_anchor"))
        if isinstance(page_evidence.get("contact_sheet_tile"), dict):
            item.setdefault("contact_sheet_tile", page_evidence.get("contact_sheet_tile"))


def run_visual_acceptance(project: Path, *, profile: str = "production") -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    instruction = read_json_optional(project / INSTRUCTION_PATH)
    plan = read_json_object(project / PLAN_PATH)
    generator = read_json_optional(project / GENERATOR_RECEIPT_PATH)
    guardrails = load_template_guardrails()
    mode = generation_mode(plan, generator)

    if mode != "artboard_satori":
        result = {
            "schema_version": SCHEMA_VERSION,
            "stage": "visual_acceptance",
            "status": "skipped",
            "action": SKIP_ACTION,
            "profile": profile,
            "generation_mode": mode,
            "started_at": started_at,
            "ended_at": now_iso(),
            "deliverable_pass": False,
            "claim_boundary": "engineering_only; skipped visual acceptance cannot support high-quality visual claims",
            "inputs": {
                "instruction": INSTRUCTION_PATH.as_posix() if (project / INSTRUCTION_PATH).exists() else None,
                "instruction_sha256": optional_sha256(project / INSTRUCTION_PATH),
                "slide_plan": PLAN_PATH.as_posix(),
                "slide_plan_sha256": file_sha256(project / PLAN_PATH),
                "generator_receipt": GENERATOR_RECEIPT_PATH.as_posix() if (project / GENERATOR_RECEIPT_PATH).exists() else None,
                "generator_receipt_sha256": optional_sha256(project / GENERATOR_RECEIPT_PATH),
                "template_guardrails": str(TEMPLATE_GUARDRAILS_PATH),
                "template_guardrails_sha256": optional_sha256(TEMPLATE_GUARDRAILS_PATH),
            },
            "summary": {"error_count": 0, "warning_count": 1, "checked_page_count": 0},
            "issues": [],
            "warnings": [issue("non_artboard_visual_acceptance_skipped", "visual acceptance is implemented for artboard_satori output only")],
            "repair_scope": "none",
            "output_path": CHECK_PATH.as_posix(),
        }
        write_json(project / CHECK_PATH, result)
        write_json(project / RECEIPT_PATH, result)
        return result

    quality_gate = check_status_file(project, QUALITY_GATE_PATH, issues, code_prefix="quality_gate")
    dry_run = check_status_file(project, DRY_RUN_PATH, issues, code_prefix="dry_run")
    preview_manifest = read_json_optional(project / PREVIEW_MANIFEST_PATH)
    if not (project / PREVIEW_PATH).exists():
        issues.append(issue("preview_html_missing", f"required preview is missing: {PREVIEW_PATH.as_posix()}", path=PREVIEW_PATH.as_posix()))
    if not preview_manifest:
        issues.append(issue("preview_manifest_missing", f"required preview manifest is missing: {PREVIEW_MANIFEST_PATH.as_posix()}", path=PREVIEW_MANIFEST_PATH.as_posix()))
    contact_sheet = check_contact_sheet(project, generator, issues)

    expected_count = expected_page_count(instruction, plan)
    actual_count = preview_manifest.get("page_count") if isinstance(preview_manifest.get("page_count"), int) else None
    if expected_count is not None and actual_count is not None and expected_count != actual_count:
        issues.append(issue("preview_page_count_mismatch", f"expected {expected_count} pages, got {actual_count}"))
    artboard_receipts = generator.get("artboard_receipts") if isinstance(generator.get("artboard_receipts"), list) else []
    if expected_count is not None and artboard_receipts and len(artboard_receipts) != expected_count:
        issues.append(issue("artboard_receipt_count_mismatch", f"expected {expected_count} artboard receipts, got {len(artboard_receipts)}"))
    if not artboard_receipts:
        issues.append(issue("artboard_receipts_missing", "visual acceptance requires generate_svg artboard_receipts"))

    page_results = [
        check_page_layout(project, plan, receipt, issues, guardrails)
        for receipt in artboard_receipts
        if isinstance(receipt, str)
    ]
    artboard_artifacts = [
        artifact
        for page_result in page_results
        for artifact in page_result.get("artifacts", [])
        if isinstance(artifact, dict)
    ]
    visual_evidence = build_visual_evidence(project, preview_manifest=preview_manifest, page_results=page_results, contact_sheet=contact_sheet)
    check_preview_anchor_targets(project, page_results, issues)
    attach_issue_evidence(issues, visual_evidence)
    deck_rhythm = build_deck_rhythm(plan, page_results, issues)

    if quality_gate and dry_run:
        if dry_run.get("prepared_files") != quality_gate.get("prepared_files"):
            issues.append(issue("engineering_prepared_hash_mismatch", "dry_run prepared_files must match quality_gate prepared_files"))
    failed_pages = sorted({item.get("page") for item in issues if isinstance(item.get("page"), int)})
    status = "failed" if issues else "passed"
    repair_scope = "none"
    if issues:
        repair_scope = "scoped_template_theme_canvas_or_asset_repair"

    result = {
        "schema_version": SCHEMA_VERSION,
        "stage": "visual_acceptance",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "profile": profile,
        "generation_mode": mode,
        "started_at": started_at,
        "ended_at": now_iso(),
        "engineering_pass": {
            "quality_gate_status": quality_gate.get("status"),
            "dry_run_status": dry_run.get("status"),
        },
        "deliverable_pass": status == "passed",
        "claim_boundary": "passed visual_acceptance is required before high-quality or upper-bound visual claims",
        "inputs": {
            "instruction": INSTRUCTION_PATH.as_posix() if (project / INSTRUCTION_PATH).exists() else None,
            "instruction_sha256": optional_sha256(project / INSTRUCTION_PATH),
            "slide_plan": PLAN_PATH.as_posix(),
            "slide_plan_sha256": file_sha256(project / PLAN_PATH),
            "asset_manifest": ASSET_MANIFEST_PATH.as_posix() if (project / ASSET_MANIFEST_PATH).exists() else None,
            "asset_manifest_sha256": optional_sha256(project / ASSET_MANIFEST_PATH),
            "generator_receipt": GENERATOR_RECEIPT_PATH.as_posix() if (project / GENERATOR_RECEIPT_PATH).exists() else None,
            "generator_receipt_sha256": optional_sha256(project / GENERATOR_RECEIPT_PATH),
            "quality_gate": QUALITY_GATE_PATH.as_posix(),
            "quality_gate_sha256": optional_sha256(project / QUALITY_GATE_PATH),
            "dry_run": DRY_RUN_PATH.as_posix(),
            "dry_run_sha256": optional_sha256(project / DRY_RUN_PATH),
            "preview": PREVIEW_PATH.as_posix() if (project / PREVIEW_PATH).exists() else None,
            "preview_sha256": optional_sha256(project / PREVIEW_PATH),
            "preview_manifest": PREVIEW_MANIFEST_PATH.as_posix() if (project / PREVIEW_MANIFEST_PATH).exists() else None,
            "preview_manifest_sha256": optional_sha256(project / PREVIEW_MANIFEST_PATH),
            "contact_sheet": contact_sheet,
            "template_guardrails": str(TEMPLATE_GUARDRAILS_PATH),
            "template_guardrails_sha256": optional_sha256(TEMPLATE_GUARDRAILS_PATH),
        },
        "summary": {
            "error_count": len(issues),
            "warning_count": len(warnings),
            "expected_page_count": expected_count,
            "checked_page_count": len(page_results),
            "failed_page_count": len(failed_pages),
        },
        "failed_pages": failed_pages,
        "pages": page_results,
        "artboard_artifacts": artboard_artifacts,
        "visual_evidence": visual_evidence,
        "deck_rhythm": deck_rhythm,
        "issues": issues,
        "warnings": warnings,
        "repair_scope": repair_scope,
        "output_path": CHECK_PATH.as_posix(),
    }
    write_json(project / CHECK_PATH, result)
    write_json(project / RECEIPT_PATH, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate rendered SVGlide preview before visual delivery claims.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--profile", default="production", choices=["production", "production_live", "preview_only", "local_real_preview", "debug"])
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_visual_acceptance(args.project, profile=args.profile)
    except (OSError, VisualAcceptanceError) as error:
        print(f"svglide_visual_acceptance: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] in {"passed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
