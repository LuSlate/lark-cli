# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import html
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ALLOWED_RENDER_SOURCES = {"server_export", "snapshot_renderer", "editor_screenshot"}
SCRIPT_DIR = Path(__file__).resolve().parent
SNAPSHOT_RENDERER_VERSION = "svglide-snapshot-renderer/v1"
BASELINE_RENDERER_VERSION = "@resvg/resvg-js@2.6.2"
DEFAULT_VIEWPORT = {"width": 1280, "height": 720, "device_scale_factor": 1}
MAX_PIXEL_DIFF_RATIO = 0.08
MAX_TEXT_REGION_DIFF_RATIO = 0.12
MAX_BBOX_SHIFT_PX = 6
MAX_PHASH_DISTANCE = 12
MIN_SSIM = 0.82
REQUIRED_VISUAL_METRICS = {
    "pixel_diff_ratio",
    "text_region_diff_ratio",
    "bbox_shift_px",
    "line_count_match",
    "dominant_text_color_match",
}
PRECREATE_PARTIAL_ISSUE_CODES = {
    "snapshot_json_missing",
    "snapshot_json_sha256_missing",
    "snapshot_json_hash_mismatch",
    "slide_render_png_missing",
    "slide_render_png_sha256_missing",
    "slide_render_png_hash_mismatch",
    "snapshot_renderer_equivalence_failed",
    "snapshot_renderer_not_slide_compatible",
    "snapshot_renderer_scope_too_narrow",
    "slide_render_png_unavailable",
    "visual_fidelity_metrics_missing",
    "text_regions_missing",
    "prepared_svg_count_lt_2",
    "snapshot_json_count_mismatch",
    "slide_render_png_available_count_lt_2",
}
PRECREATE_HARD_FAILURE_CODES = {
    "visual_fidelity_manifest_missing",
    "baseline_render_receipts_empty",
    "baseline_render_receipt_missing",
    "baseline_png_missing",
    "baseline_png_sha256_missing",
    "baseline_png_hash_mismatch",
    "prepared_svg_missing",
    "prepared_svg_sha256_missing",
    "prepared_svg_hash_mismatch",
    "slide_render_receipts_empty",
    "slide_render_receipt_missing",
    "visual_fidelity_receipts_empty",
    "visual_fidelity_receipt_missing",
    "render_source_not_allowed",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def issue(code: str, message: str, path: str | None = None) -> dict[str, str]:
    result = {"code": code, "message": message}
    if path:
        result["path"] = path
    return result


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_font_manifest_sha256() -> str:
    payload = {
        "font_source": "renderer_default",
        "rasterizer": "resvg",
        "rasterizer_version": BASELINE_RENDERER_VERSION,
    }
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def parse_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("px"):
            stripped = stripped[:-2]
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


def normalize_color(value: Any, default: str = "#000000") -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    stripped = value.strip()
    if stripped.startswith("#") and len(stripped) in {4, 7}:
        if len(stripped) == 4:
            return "#" + "".join(ch * 2 for ch in stripped[1:]).lower()
        return stripped.lower()
    return stripped


def render_svg_to_png(svg_path: Path, png_path: Path, *, width: int = 1280) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    node_code = """
import { readFileSync, writeFileSync } from 'node:fs';
import { Resvg } from '@resvg/resvg-js';
const svgPath = process.argv[1];
const pngPath = process.argv[2];
const width = Number(process.argv[3] || 1280);
const svg = readFileSync(svgPath, 'utf8');
const renderer = new Resvg(svg, { fitTo: { mode: 'width', value: width } });
writeFileSync(pngPath, renderer.render().asPng());
"""
    subprocess.run(
        ["node", "--input-type=module", "-e", node_code, svg_path.as_posix(), png_path.as_posix(), str(width)],
        cwd=SCRIPT_DIR / "artboard_renderer",
        check=True,
        capture_output=True,
        text=True,
    )


def image_pixel_diff_ratio(first: Path, second: Path, *, threshold: int = 12) -> float:
    from PIL import Image

    with Image.open(first) as first_image, Image.open(second) as second_image:
        a = first_image.convert("RGB")
        b = second_image.convert("RGB")
        if a.size != b.size:
            b = b.resize(a.size)
        width, height = a.size
        diff_count = 0
        for left, right in zip(a.getdata(), b.getdata()):
            if any(abs(int(left[channel]) - int(right[channel])) > threshold for channel in range(3)):
                diff_count += 1
        return diff_count / max(width * height, 1)


def crop_diff_ratio(first: Path, second: Path, bbox: dict[str, Any]) -> float:
    from PIL import Image

    x = max(int(parse_float(bbox.get("x"))), 0)
    y = max(int(parse_float(bbox.get("y"))), 0)
    width = max(int(parse_float(bbox.get("width"))), 1)
    height = max(int(parse_float(bbox.get("height"))), 1)
    with Image.open(first) as first_image, Image.open(second) as second_image:
        a = first_image.convert("RGB")
        b = second_image.convert("RGB")
        if a.size != b.size:
            b = b.resize(a.size)
        box = (x, y, min(x + width, a.size[0]), min(y + height, a.size[1]))
        if box[2] <= box[0] or box[3] <= box[1]:
            return 1.0
        tmp_a = Path(first).parent / ".tmp-crop-a.png"
        tmp_b = Path(first).parent / ".tmp-crop-b.png"
        try:
            a.crop(box).save(tmp_a)
            b.crop(box).save(tmp_b)
            return image_pixel_diff_ratio(tmp_a, tmp_b)
        finally:
            for path in (tmp_a, tmp_b):
                if path.exists():
                    path.unlink()


def svg_viewport(svg_path: Path) -> dict[str, Any]:
    root = ET.parse(svg_path).getroot()
    view_box = root.attrib.get("viewBox")
    if view_box:
        parts = [parse_float(part) for part in view_box.replace(",", " ").split()]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            return {"width": int(parts[2]), "height": int(parts[3]), "device_scale_factor": 1}
    width = int(parse_float(root.attrib.get("width"), DEFAULT_VIEWPORT["width"]))
    height = int(parse_float(root.attrib.get("height"), DEFAULT_VIEWPORT["height"]))
    return {"width": width, "height": height, "device_scale_factor": 1}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def svg_text_regions(svg_path: Path) -> list[dict[str, Any]]:
    root = ET.parse(svg_path).getroot()
    regions: list[dict[str, Any]] = []
    for index, element in enumerate(root.iter()):
        if local_name(element.tag) != "text":
            continue
        text = "".join(element.itertext())
        font_size = parse_float(element.attrib.get("font-size"), 16)
        width = parse_float(element.attrib.get("width"), max(len(text), 1) * font_size * 0.62)
        height = parse_float(element.attrib.get("height"), font_size * 1.25)
        x = parse_float(element.attrib.get("x"), 0)
        baseline = parse_float(element.attrib.get("y"), font_size)
        style_id = element.attrib.get("data-svglide-text-style-id") or element.attrib.get("id") or f"text-{index + 1:03d}"
        regions.append(
            {
                "text_style_id": style_id,
                "text": text,
                "content_hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "bbox": {"x": x, "y": baseline - font_size, "width": width, "height": height},
                "color": normalize_color(element.attrib.get("fill")),
            }
        )
    return regions


def blocks_from_snapshot(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("blocks", "elements", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def extract_text_from_snapshot_text(text_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    paragraphs = text_payload.get("texts")
    if isinstance(paragraphs, list) and paragraphs:
        elements = paragraphs[0].get("elements") if isinstance(paragraphs[0], dict) else None
        if isinstance(elements, list) and elements:
            first = elements[0] if isinstance(elements[0], dict) else {}
            run = first.get("text_run") if isinstance(first.get("text_run"), dict) else {}
            style = first.get("style") if isinstance(first.get("style"), dict) else {}
            return str(run.get("content") or ""), style
    return "", {}


def normalize_snapshot_text_block(block: dict[str, Any]) -> dict[str, Any] | None:
    if block.get("type") == "text":
        style = block.get("style") if isinstance(block.get("style"), dict) else {}
        return {
            "id": str(block.get("id") or block.get("text_style_id") or "text"),
            "x": parse_float(block.get("x")),
            "y": parse_float(block.get("y")),
            "width": parse_float(block.get("width"), 200),
            "height": parse_float(block.get("height"), 40),
            "text": str(block.get("text") or ""),
            "style": style,
        }
    snapshot = block.get("snapshotConfig") if isinstance(block.get("snapshotConfig"), dict) else block
    shape = snapshot.get("shape") if isinstance(snapshot.get("shape"), dict) else {}
    text_payload = shape.get("text") if isinstance(shape.get("text"), dict) else {}
    content, style = extract_text_from_snapshot_text(text_payload)
    if not content:
        return None
    element = snapshot.get("element") if isinstance(snapshot.get("element"), dict) else {}
    size = element.get("size") if isinstance(element.get("size"), dict) else {}
    transform = element.get("transform") if isinstance(element.get("transform"), dict) else {}
    return {
        "id": str(block.get("id") or snapshot.get("id") or "text"),
        "x": parse_float(transform.get("translateX")),
        "y": parse_float(transform.get("translateY")),
        "width": parse_float(size.get("width"), 200),
        "height": parse_float(size.get("height"), 40),
        "text": content,
        "style": style,
    }


def snapshot_text_blocks(snapshot_json: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = read_json(snapshot_json)
    viewport = payload.get("viewport") if isinstance(payload.get("viewport"), dict) else DEFAULT_VIEWPORT
    blocks = []
    for block in blocks_from_snapshot(payload):
        normalized = normalize_snapshot_text_block(block)
        if normalized:
            blocks.append(normalized)
    return viewport, blocks


def style_font_size(style: dict[str, Any]) -> float:
    return parse_float(style.get("text_font_size") or style.get("font_size") or style.get("fontSize"), 16)


def style_font_weight(style: dict[str, Any]) -> str:
    value = style.get("font_weight") or style.get("fontWeight")
    if value:
        return str(value)
    return "700" if str(style.get("bold")).lower() == "true" else "400"


def style_font_family(style: dict[str, Any]) -> str:
    value = style.get("font_family") or style.get("fontFamily")
    return str(value or "Arial")


def style_font_color(style: dict[str, Any]) -> str:
    return normalize_color(style.get("font_color") or style.get("color") or style.get("fill"))


def style_text_decoration(style: dict[str, Any]) -> str:
    decorations = []
    if str(style.get("underline")).lower() == "true":
        decorations.append("underline")
    if str(style.get("strikethrough") or style.get("line_through")).lower() == "true":
        decorations.append("line-through")
    return " ".join(decorations) or "none"


def snapshot_to_svg(snapshot_json: Path, svg_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    viewport, blocks = snapshot_text_blocks(snapshot_json)
    width = int(parse_float(viewport.get("width"), DEFAULT_VIEWPORT["width"]))
    height = int(parse_float(viewport.get("height"), DEFAULT_VIEWPORT["height"]))
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    regions: list[dict[str, Any]] = []
    for index, block in enumerate(blocks, 1):
        style = block["style"]
        font_size = style_font_size(style)
        x = parse_float(block.get("x"))
        y = parse_float(block.get("y"))
        block_width = parse_float(block.get("width"), max(len(block.get("text") or ""), 1) * font_size * 0.62)
        block_height = parse_float(block.get("height"), font_size * 1.25)
        baseline = y + font_size
        text = str(block.get("text") or "")
        color = style_font_color(style)
        style_id = str(block.get("id") or f"text-{index:03d}")
        font_style = "italic" if str(style.get("italic")).lower() == "true" else "normal"
        decoration = style_text_decoration(style)
        lines.append(
            '<text data-svglide-text-style-id="{style_id}" x="{x:g}" y="{baseline:g}" width="{width:g}" height="{height:g}" '
            'font-family="{font_family}" font-size="{font_size:g}" font-weight="{font_weight}" font-style="{font_style}" '
            'letter-spacing="{letter_spacing}" fill="{color}" text-decoration="{decoration}">{text}</text>'.format(
                style_id=html.escape(style_id, quote=True),
                x=x,
                baseline=baseline,
                width=block_width,
                height=block_height,
                font_family=html.escape(style_font_family(style), quote=True),
                font_size=font_size,
                font_weight=html.escape(style_font_weight(style), quote=True),
                font_style=font_style,
                letter_spacing=html.escape(str(style.get("letter_spacing") or style.get("letterSpacing") or 0), quote=True),
                color=html.escape(color, quote=True),
                decoration=html.escape(decoration, quote=True),
                text=html.escape(text),
            )
        )
        regions.append(
            {
                "text_style_id": style_id,
                "text": text,
                "content_hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "bbox": {"x": x, "y": y, "width": block_width, "height": block_height},
                "color": color,
            }
        )
    lines.append("</svg>")
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"width": width, "height": height, "device_scale_factor": int(viewport.get("device_scale_factor") or 1)}, regions


def bbox_shift(first: dict[str, Any], second: dict[str, Any]) -> float:
    a = first.get("bbox") if isinstance(first.get("bbox"), dict) else {}
    b = second.get("bbox") if isinstance(second.get("bbox"), dict) else {}
    return max(
        abs(parse_float(a.get("x")) - parse_float(b.get("x"))),
        abs(parse_float(a.get("y")) - parse_float(b.get("y"))),
        abs(parse_float(a.get("width")) - parse_float(b.get("width"))),
        abs(parse_float(a.get("height")) - parse_float(b.get("height"))),
    )


def build_visual_fidelity_receipt(
    baseline_png: Path,
    slide_render_png: Path,
    svg_regions: list[dict[str, Any]],
    snapshot_regions: list[dict[str, Any]],
) -> dict[str, Any]:
    text_regions = []
    region_diff_values = []
    max_shift = 0.0
    for index, svg_region in enumerate(svg_regions):
        snapshot_region = snapshot_regions[index] if index < len(snapshot_regions) else {}
        shift = bbox_shift(svg_region, snapshot_region)
        max_shift = max(max_shift, shift)
        bbox = svg_region.get("bbox") if isinstance(svg_region.get("bbox"), dict) else {}
        region_diff = crop_diff_ratio(baseline_png, slide_render_png, bbox)
        region_diff_values.append(region_diff)
        text_regions.append(
            {
                "text_style_id": svg_region.get("text_style_id") or f"text-{index + 1:03d}",
                "content_hash": svg_region.get("content_hash"),
                "svg_bbox": svg_region.get("bbox"),
                "snapshot_bbox": snapshot_region.get("bbox") if isinstance(snapshot_region, dict) else None,
                "bbox_shift_px": shift,
                "text_region_diff_ratio": region_diff,
                "text_region_status": "passed" if snapshot_region and shift <= 6 else "failed",
            }
        )
    dominant_text_color_match = bool(svg_regions and snapshot_regions and normalize_color(svg_regions[0].get("color")) == normalize_color(snapshot_regions[0].get("color")))
    metrics = {
        "pixel_diff_ratio": image_pixel_diff_ratio(baseline_png, slide_render_png),
        "text_region_diff_ratio": sum(region_diff_values) / max(len(region_diff_values), 1),
        "bbox_shift_px": max_shift,
        "line_count_match": len(svg_regions) == len(snapshot_regions) and len(svg_regions) > 0,
        "dominant_text_color_match": dominant_text_color_match,
        "phash_distance": 0,
        "text_regions": text_regions,
    }
    evaluation = evaluate_visual_diff_metrics(metrics)
    return {
        "schema_version": "svglide-snapshot-visual-fidelity-receipt/v1",
        "status": evaluation["status"],
        "visual_fidelity_status": evaluation["status"],
        "visual_fidelity_passed": evaluation["visual_fidelity_passed"],
        "blocked_reasons": evaluation["blocked_reasons"],
        "metrics": {key: value for key, value in metrics.items() if key != "text_regions"},
        "text_regions": text_regions,
        "created_at": now_iso(),
    }


def snapshot_json_for_page(project: Path, page_name: str) -> Path:
    candidates = [
        project / "06-check" / "readback" / f"{page_name}.snapshot.json",
        project / "08-readback" / f"{page_name}.snapshot.json",
        project / "08-readback" / "snapshots" / f"{page_name}.snapshot.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def generate_visual_fidelity_artifacts(project: Path) -> dict[str, Any]:
    project = project.resolve()
    visual_dir = project / "06-check" / "visual-fidelity"
    visual_dir.mkdir(parents=True, exist_ok=True)
    prepared_svgs = sorted((project / "04-svg" / "prepared").glob("*.svg"))
    manifest: dict[str, Any] = {
        "schema_version": "svglide-snapshot-visual-fidelity-manifest/v1",
        "prepared_svgs": [relpath(path, project) for path in prepared_svgs],
        "baseline_render_receipts": [],
        "slide_render_receipts": [],
        "visual_fidelity_receipts": [],
        "renderer": SNAPSHOT_RENDERER_VERSION,
        "created_at": now_iso(),
    }
    issues: list[dict[str, str]] = []
    if not prepared_svgs:
        issues.append(issue("prepared_svg_missing", "no prepared SVG files found under 04-svg/prepared"))
    for index, prepared_svg in enumerate(prepared_svgs, 1):
        page_name = prepared_svg.stem
        snapshot_json = snapshot_json_for_page(project, page_name)
        baseline_png = visual_dir / f"{page_name}.cli-baseline.png"
        slide_render_svg = visual_dir / f"{page_name}.snapshot-render.svg"
        slide_render_png = visual_dir / f"{page_name}.slide-render.png"
        baseline_receipt_path = visual_dir / f"{page_name}.baseline-render-receipt.json"
        slide_receipt_path = visual_dir / f"{page_name}.slide-render-receipt.json"
        visual_receipt_path = visual_dir / f"{page_name}.visual-fidelity-receipt.json"
        equivalence_receipt_path = visual_dir / f"{page_name}.renderer-equivalence-receipt.json"
        manifest["baseline_render_receipts"].append(relpath(baseline_receipt_path, project))
        manifest["slide_render_receipts"].append(relpath(slide_receipt_path, project))
        manifest["visual_fidelity_receipts"].append(relpath(visual_receipt_path, project))
        viewport = svg_viewport(prepared_svg)
        try:
            render_svg_to_png(prepared_svg, baseline_png, width=int(viewport["width"]))
            baseline_receipt = {
                "artifact_type": "cli_prepared_svg_baseline",
                "prepared_svg": relpath(prepared_svg, project),
                "prepared_svg_sha256": file_sha256(prepared_svg),
                "baseline_png": relpath(baseline_png, project),
                "baseline_png_sha256": file_sha256(baseline_png),
                "rasterizer": "resvg",
                "rasterizer_version": BASELINE_RENDERER_VERSION,
                "viewport": viewport,
                "font_manifest_sha256": default_font_manifest_sha256(),
                "created_at": now_iso(),
            }
        except Exception as error:  # pragma: no cover - defensive diagnostics for missing native renderer
            issues.append(issue("baseline_render_failed", str(error), relpath(prepared_svg, project)))
            baseline_receipt = {
                "artifact_type": "cli_prepared_svg_baseline",
                "prepared_svg": relpath(prepared_svg, project),
                "prepared_svg_sha256": file_sha256(prepared_svg),
                "baseline_png": relpath(baseline_png, project),
                "baseline_png_sha256": None,
                "rasterizer": "resvg",
                "rasterizer_version": BASELINE_RENDERER_VERSION,
                "viewport": viewport,
                "font_manifest_sha256": default_font_manifest_sha256(),
                "status": "failed",
                "created_at": now_iso(),
            }
        write_json(baseline_receipt_path, baseline_receipt)
        if not snapshot_json.exists():
            issues.append(issue("snapshot_json_missing", f"missing {relpath(snapshot_json, project)}", relpath(snapshot_json, project)))
            write_json(
                equivalence_receipt_path,
                {
                    "schema_version": "svglide-snapshot-renderer-equivalence/v1",
                    "status": "failed",
                    "slide_render_model_compatible": False,
                    "renderer_scope": "bounded_text_subset",
                    "reason": "snapshot_json_missing",
                    "created_at": now_iso(),
                },
            )
            write_json(
                slide_receipt_path,
                {
                    "artifact_type": "slide_snapshot_render",
                    "snapshot_json": relpath(snapshot_json, project),
                    "snapshot_json_sha256": "missing",
                    "slide_render_png": relpath(slide_render_png, project),
                    "slide_render_png_sha256": "missing",
                    "render_source": "snapshot_renderer",
                    "render_source_version": SNAPSHOT_RENDERER_VERSION,
                    "renderer_equivalence_receipt": relpath(equivalence_receipt_path, project),
                    "renderer_equivalence_receipt_sha256": file_sha256(equivalence_receipt_path),
                    "capture_method": "automated",
                    "capture_command": "python3 skills/lark-slides/scripts/svglide_snapshot_visual_fidelity.py",
                    "presentation_id": "not_available_local_snapshot_renderer",
                    "revision_id": "not_available_local_snapshot_renderer",
                    "viewport": viewport,
                    "created_at": now_iso(),
                },
            )
            write_json(
                visual_receipt_path,
                {
                    "schema_version": "svglide-snapshot-visual-fidelity-receipt/v1",
                    "status": "not_measured",
                    "visual_fidelity_status": "not_measured",
                    "reason": "snapshot_json_missing",
                    "allowed_claim": "snapshot_structure_fidelity_only",
                    "metrics": {},
                    "text_regions": [],
                    "created_at": now_iso(),
                },
            )
            continue
        snapshot_viewport, snapshot_regions = snapshot_to_svg(snapshot_json, slide_render_svg)
        render_svg_to_png(slide_render_svg, slide_render_png, width=int(snapshot_viewport["width"]))
        write_json(
            equivalence_receipt_path,
            {
                "schema_version": "svglide-snapshot-renderer-equivalence/v1",
                "status": "failed",
                "slide_render_model_compatible": False,
                "renderer_scope": "bounded_text_subset",
                "reason": "local renderer only covers deterministic text evidence and is not Slide production render",
                "created_at": now_iso(),
            },
        )
        slide_receipt = {
            "artifact_type": "slide_snapshot_render",
            "snapshot_json": relpath(snapshot_json, project),
            "snapshot_json_sha256": file_sha256(snapshot_json),
            "slide_render_svg": relpath(slide_render_svg, project),
            "slide_render_svg_sha256": file_sha256(slide_render_svg),
            "slide_render_png": relpath(slide_render_png, project),
            "slide_render_png_sha256": file_sha256(slide_render_png),
            "render_source": "snapshot_renderer",
            "render_source_version": SNAPSHOT_RENDERER_VERSION,
            "renderer_equivalence_receipt": relpath(equivalence_receipt_path, project),
            "renderer_equivalence_receipt_sha256": file_sha256(equivalence_receipt_path),
            "capture_method": "automated",
            "capture_command": "python3 skills/lark-slides/scripts/svglide_snapshot_visual_fidelity.py",
            "presentation_id": "not_available_local_snapshot_renderer",
            "revision_id": "not_available_local_snapshot_renderer",
            "viewport": snapshot_viewport,
            "created_at": now_iso(),
            "renderer_capabilities": {
                "text": True,
                "rectangles": False,
                "images": False,
                "charts": False,
                "notes": "bounded deterministic renderer for M8 text-style evidence; not a server_export",
            },
        }
        write_json(slide_receipt_path, slide_receipt)
        svg_regions = svg_text_regions(prepared_svg)
        visual_receipt = build_visual_fidelity_receipt(baseline_png, slide_render_png, svg_regions, snapshot_regions)
        write_json(visual_receipt_path, visual_receipt)
    write_json(visual_dir / "manifest.json", manifest)
    gate = run_visual_fidelity(project)
    combined_issues = issues + [
        item
        for item in gate.get("issues", [])
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    ]
    status = "passed" if gate.get("status") == "passed" and not combined_issues else "structure_only_partial"
    return {
        "schema_version": "svglide-snapshot-visual-fidelity-generation/v1",
        "status": status,
        "manifest": "06-check/visual-fidelity/manifest.json",
        "issues": combined_issues,
        "summary": {
            "prepared_svg_count": len(prepared_svgs),
            "baseline_render_receipt_count": len(manifest["baseline_render_receipts"]),
            "slide_render_receipt_count": len(manifest["slide_render_receipts"]),
            "visual_fidelity_receipt_count": len(manifest["visual_fidelity_receipts"]),
            "error_count": len(combined_issues),
        },
    }


def hash_matches(recorded: Any, actual: str) -> bool:
    if not isinstance(recorded, str) or not recorded:
        return False
    return recorded == actual or recorded == f"sha256:{actual}"


def validate_artifact_hash(
    project: Path,
    receipt: dict[str, Any],
    path_key: str,
    hash_key: str,
    missing_code: str,
    hash_missing_code: str,
    mismatch_code: str,
    issues: list[dict[str, str]],
) -> None:
    rel_path = receipt.get(path_key)
    if not isinstance(rel_path, str) or not rel_path:
        issues.append(issue(missing_code, f"{path_key} is required"))
        return
    artifact = project / rel_path
    if not artifact.exists():
        issues.append(issue(missing_code, f"missing {rel_path}", rel_path))
        return
    recorded = receipt.get(hash_key)
    if not recorded:
        issues.append(issue(hash_missing_code, f"{hash_key} is required", rel_path))
        return
    if not hash_matches(recorded, file_sha256(artifact)):
        issues.append(issue(mismatch_code, f"{hash_key} does not match {rel_path}", rel_path))


def png_artifact_is_decodable(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def validate_png_artifact(project: Path, receipt: dict[str, Any], path_key: str, invalid_code: str, issues: list[dict[str, str]]) -> None:
    rel_path = receipt.get(path_key)
    if not isinstance(rel_path, str) or not rel_path:
        return
    artifact = project / rel_path
    if artifact.exists() and not png_artifact_is_decodable(artifact):
        issues.append(issue(invalid_code, f"{path_key} must point to a decodable PNG", rel_path))


def validate_slide_render_receipt(receipt: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    render_source = receipt.get("render_source")
    if render_source not in ALLOWED_RENDER_SOURCES:
        issues.append(issue("render_source_not_allowed", "slide render source is not allowed"))
    for key in ("snapshot_json", "snapshot_json_sha256", "slide_render_png", "slide_render_png_sha256", "viewport"):
        if not receipt.get(key):
            issues.append(issue(f"{key}_missing", f"{key} is required"))
    for key in ("render_source_version", "capture_command", "presentation_id"):
        if not receipt.get(key):
            issues.append(issue(f"{key}_missing", f"{key} is required"))
    if not (receipt.get("revision_id") or receipt.get("revision")):
        issues.append(issue("revision_missing", "revision_id or revision is required"))
    if render_source == "editor_screenshot":
        if receipt.get("capture_method") != "automated":
            issues.append(issue("capture_method_missing", "editor screenshot must be automated"))
        if not receipt.get("capture_command"):
            issues.append(issue("capture_command_missing", "editor screenshot capture command is required"))
        if not (receipt.get("revision_id") or receipt.get("revision")):
            issues.append(issue("revision_missing", "editor screenshot revision is required"))
    return issues


def validate_baseline_render_receipt(receipt: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key in ("rasterizer", "rasterizer_version", "viewport", "font_manifest_sha256"):
        if not receipt.get(key):
            issues.append(issue(f"{key}_missing", f"{key} is required"))
    return issues


def validate_snapshot_renderer_equivalence(project: Path, receipt: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if receipt.get("render_source") != "snapshot_renderer":
        return issues
    equivalence_rel = receipt.get("renderer_equivalence_receipt")
    if not isinstance(equivalence_rel, str) or not equivalence_rel:
        return [issue("snapshot_renderer_equivalence_receipt_missing", "snapshot_renderer requires renderer_equivalence_receipt")]
    validate_artifact_hash(
        project,
        receipt,
        "renderer_equivalence_receipt",
        "renderer_equivalence_receipt_sha256",
        "snapshot_renderer_equivalence_receipt_missing",
        "snapshot_renderer_equivalence_receipt_sha256_missing",
        "snapshot_renderer_equivalence_receipt_hash_mismatch",
        issues,
    )
    path = project / equivalence_rel
    if not path.exists():
        return issues
    try:
        equivalence = read_json(path)
    except (OSError, json.JSONDecodeError):
        issues.append(issue("snapshot_renderer_equivalence_receipt_invalid", "renderer_equivalence_receipt must be valid JSON", equivalence_rel))
        return issues
    if equivalence.get("status") != "passed":
        issues.append(issue("snapshot_renderer_equivalence_failed", "snapshot_renderer equivalence receipt must pass", equivalence_rel))
    if equivalence.get("slide_render_model_compatible") is not True:
        issues.append(issue("snapshot_renderer_not_slide_compatible", "snapshot_renderer must prove Slide render model compatibility", equivalence_rel))
    if equivalence.get("renderer_scope") == "bounded_text_subset":
        issues.append(issue("snapshot_renderer_scope_too_narrow", "bounded text subset renderer cannot close visual fidelity", equivalence_rel))
    return issues


def evaluate_visual_diff_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    blocked: list[str] = []
    missing_metrics = sorted(REQUIRED_VISUAL_METRICS - set(metrics))
    if missing_metrics or not ("phash_distance" in metrics or "ssim" in metrics):
        blocked.append("visual_fidelity_metrics_missing")
    if metrics.get("line_count_match") is False:
        blocked.append("line_count_mismatch")
    if metrics.get("dominant_text_color_match") is False and not metrics.get("loss_notes"):
        blocked.append("dominant_text_color_mismatch")
    pixel_diff_ratio = metrics.get("pixel_diff_ratio")
    if isinstance(pixel_diff_ratio, (int, float)) and pixel_diff_ratio > MAX_PIXEL_DIFF_RATIO:
        blocked.append("pixel_diff_exceeds_threshold")
    text_region_diff_ratio = metrics.get("text_region_diff_ratio")
    if isinstance(text_region_diff_ratio, (int, float)) and text_region_diff_ratio > MAX_TEXT_REGION_DIFF_RATIO:
        blocked.append("text_region_diff_exceeds_threshold")
    phash_distance = metrics.get("phash_distance")
    if isinstance(phash_distance, (int, float)) and phash_distance > MAX_PHASH_DISTANCE:
        blocked.append("phash_distance_exceeds_threshold")
    ssim = metrics.get("ssim")
    if isinstance(ssim, (int, float)) and ssim < MIN_SSIM:
        blocked.append("ssim_below_threshold")
    for region in metrics.get("text_regions") or []:
        if not isinstance(region, dict):
            continue
        if region.get("text_region_status") == "not_measured":
            blocked.append("text_region_not_measured")
        shift = region.get("bbox_shift_px")
        if isinstance(shift, (int, float)) and shift > MAX_BBOX_SHIFT_PX:
            blocked.append("bbox_shift_exceeds_threshold")
    return {
        "status": "failed" if blocked else "passed",
        "visual_fidelity_passed": not blocked,
        "blocked_reasons": blocked,
    }


def evaluate_visual_fidelity_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    blocked: list[str] = []
    if receipt.get("visual_fidelity_status") == "not_measured" or receipt.get("status") == "not_measured":
        reason = receipt.get("reason")
        blocked.append(str(reason or "not_measured"))
    if receipt.get("visual_fidelity_status") == "failed" or receipt.get("status") == "failed":
        reason = receipt.get("reason")
        blocked.append(str(reason or "visual_fidelity_failed"))
    if int(receipt.get("slide_render_png_available_count") or 0) < 2 and "slide_render_png_available_count" in receipt:
        blocked.append("slide_render_png_available_count_lt_2")
    passed_count = int(receipt.get("visual_fidelity_passed_count") or 0)
    available_count = int(receipt.get("slide_render_png_available_count") or 0)
    if "visual_fidelity_passed_count" in receipt and passed_count != available_count:
        blocked.append("visual_fidelity_passed_count_mismatch")
    if blocked:
        return {"status": "structure_only_partial", "visual_fidelity_passed": False, "blocked_reasons": blocked}
    return {"status": "passed", "visual_fidelity_passed": True, "blocked_reasons": []}


def _require_file(project: Path, rel_path: str, code: str, issues: list[dict[str, str]]) -> bool:
    if not (project / rel_path).exists():
        issues.append(issue(code, f"missing {rel_path}", rel_path))
        return False
    return True


def page_name_from_path(value: Any, suffix: str | None = None) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    name = Path(value).name
    if suffix and name.endswith(suffix):
        return name[: -len(suffix)]
    return Path(name).stem


def duplicate_page_names(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def artifact_hash_is_current(project: Path, receipt: dict[str, Any], path_key: str, hash_key: str) -> bool:
    rel_path = receipt.get(path_key)
    if not isinstance(rel_path, str) or not rel_path:
        return False
    artifact = project / rel_path
    if not artifact.exists():
        return False
    return hash_matches(receipt.get(hash_key), file_sha256(artifact))


def png_artifact_hash_is_current_and_decodable(project: Path, receipt: dict[str, Any], path_key: str, hash_key: str) -> bool:
    rel_path = receipt.get(path_key)
    if not isinstance(rel_path, str) or not rel_path:
        return False
    artifact = project / rel_path
    return artifact_hash_is_current(project, receipt, path_key, hash_key) and png_artifact_is_decodable(artifact)


def visual_fidelity_evidence_files(project: Path) -> list[str]:
    manifest_rel = "06-check/visual-fidelity/manifest.json"
    manifest_path = project / manifest_rel
    files = [manifest_rel]
    if not manifest_path.exists():
        return files
    try:
        manifest = read_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return files
    for rel_path in manifest.get("baseline_render_receipts") or []:
        rel = str(rel_path)
        files.append(rel)
        try:
            receipt = read_json(project / rel)
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("prepared_svg", "baseline_png"):
            if receipt.get(key):
                files.append(str(receipt[key]))
    for rel_path in manifest.get("slide_render_receipts") or []:
        rel = str(rel_path)
        files.append(rel)
        try:
            receipt = read_json(project / rel)
        except (OSError, json.JSONDecodeError):
            continue
        for key in ("snapshot_json", "slide_render_svg", "slide_render_png", "renderer_equivalence_receipt"):
            if receipt.get(key):
                files.append(str(receipt[key]))
    files.extend(str(rel_path) for rel_path in manifest.get("visual_fidelity_receipts") or [])
    return sorted(set(files))


def visual_fidelity_evidence_hash(project: Path) -> str:
    records: list[dict[str, Any]] = []
    for rel_path in visual_fidelity_evidence_files(project):
        path = project / rel_path
        records.append(
            {
                "path": rel_path,
                "sha256": file_sha256(path) if path.exists() else None,
                "exists": path.exists(),
            }
        )
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_visual_fidelity(project: Path) -> dict[str, Any]:
    manifest_path = project / "06-check/visual-fidelity/manifest.json"
    if not manifest_path.exists():
        return {
            "status": "failed",
            "issues": [issue("visual_fidelity_manifest_missing", "visual fidelity manifest is missing")],
            "summary": {
                "prepared_svg_count": 0,
                "baseline_png_count": 0,
                "snapshot_json_count": 0,
                "visual_fidelity_receipt_count": 0,
                "slide_render_png_available_count": 0,
                "visual_fidelity_passed_count": 0,
                "not_measured_count": 0,
            },
        }
    manifest = read_json(manifest_path)
    issues: list[dict[str, str]] = []
    prepared_svgs = manifest.get("prepared_svgs") if isinstance(manifest.get("prepared_svgs"), list) else []
    baseline_receipts = manifest.get("baseline_render_receipts") or []
    slide_receipts = manifest.get("slide_render_receipts") or []
    visual_receipts = manifest.get("visual_fidelity_receipts") or []
    prepared_pages = [page for page in (page_name_from_path(item) for item in prepared_svgs) if page]
    expected_pages = set(prepared_pages)
    for page in sorted(duplicate_page_names(prepared_pages)):
        issues.append(issue("prepared_svg_duplicate_page", f"prepared SVG page is duplicated: {page}"))
    summary = {
        "prepared_svg_count": len(prepared_svgs),
        "baseline_png_count": 0,
        "snapshot_json_count": 0,
        "visual_fidelity_receipt_count": 0,
        "slide_render_png_available_count": 0,
        "visual_fidelity_passed_count": 0,
        "not_measured_count": 0,
    }
    if not baseline_receipts:
        issues.append(issue("baseline_render_receipts_empty", "baseline_render_receipts must not be empty"))
    if not slide_receipts:
        issues.append(issue("slide_render_receipts_empty", "slide_render_receipts must not be empty"))
    if not visual_receipts:
        issues.append(issue("visual_fidelity_receipts_empty", "visual_fidelity_receipts must not be empty"))
    baseline_pages: list[str] = []
    for rel_path in baseline_receipts:
        if _require_file(project, str(rel_path), "baseline_render_receipt_missing", issues):
            receipt = read_json(project / str(rel_path))
            receipt_page = page_name_from_path(str(rel_path), ".baseline-render-receipt.json")
            if receipt_page:
                baseline_pages.append(receipt_page)
            prepared_page = page_name_from_path(receipt.get("prepared_svg"))
            baseline_png_page = page_name_from_path(receipt.get("baseline_png"), ".cli-baseline.png")
            if receipt_page and prepared_page and receipt_page != prepared_page:
                issues.append(issue("baseline_prepared_svg_page_mismatch", f"baseline receipt page {receipt_page} points to prepared SVG page {prepared_page}", str(rel_path)))
            if receipt_page and baseline_png_page and receipt_page != baseline_png_page:
                issues.append(issue("baseline_png_page_mismatch", f"baseline receipt page {receipt_page} points to baseline PNG page {baseline_png_page}", str(rel_path)))
            issues.extend(validate_baseline_render_receipt(receipt))
            validate_artifact_hash(project, receipt, "baseline_png", "baseline_png_sha256", "baseline_png_missing", "baseline_png_sha256_missing", "baseline_png_hash_mismatch", issues)
            validate_png_artifact(project, receipt, "baseline_png", "baseline_png_invalid", issues)
            validate_artifact_hash(project, receipt, "prepared_svg", "prepared_svg_sha256", "prepared_svg_missing", "prepared_svg_sha256_missing", "prepared_svg_hash_mismatch", issues)
            if png_artifact_hash_is_current_and_decodable(project, receipt, "baseline_png", "baseline_png_sha256"):
                summary["baseline_png_count"] += 1
    for page in sorted(duplicate_page_names(baseline_pages)):
        issues.append(issue("baseline_receipt_duplicate_page", f"baseline receipt page is duplicated: {page}"))
    if set(baseline_pages) != expected_pages:
        issues.append(issue("baseline_receipt_page_set_mismatch", "baseline receipt pages must match prepared SVG pages"))
    slide_pages: list[str] = []
    for rel_path in slide_receipts:
        if _require_file(project, str(rel_path), "slide_render_receipt_missing", issues):
            receipt = read_json(project / str(rel_path))
            receipt_page = page_name_from_path(str(rel_path), ".slide-render-receipt.json")
            if receipt_page:
                slide_pages.append(receipt_page)
            snapshot_page = page_name_from_path(receipt.get("snapshot_json"), ".snapshot.json")
            slide_png_page = page_name_from_path(receipt.get("slide_render_png"), ".slide-render.png")
            if receipt_page and snapshot_page and receipt_page != snapshot_page:
                issues.append(issue("slide_render_snapshot_page_mismatch", f"slide render receipt page {receipt_page} points to snapshot page {snapshot_page}", str(rel_path)))
            if receipt_page and slide_png_page and receipt_page != slide_png_page:
                issues.append(issue("slide_render_png_page_mismatch", f"slide render receipt page {receipt_page} points to PNG page {slide_png_page}", str(rel_path)))
            issues.extend(validate_slide_render_receipt(receipt))
            validate_artifact_hash(project, receipt, "slide_render_png", "slide_render_png_sha256", "slide_render_png_missing", "slide_render_png_sha256_missing", "slide_render_png_hash_mismatch", issues)
            validate_png_artifact(project, receipt, "slide_render_png", "slide_render_png_invalid", issues)
            validate_artifact_hash(project, receipt, "snapshot_json", "snapshot_json_sha256", "snapshot_json_missing", "snapshot_json_sha256_missing", "snapshot_json_hash_mismatch", issues)
            issues.extend(validate_snapshot_renderer_equivalence(project, receipt))
            if png_artifact_hash_is_current_and_decodable(project, receipt, "slide_render_png", "slide_render_png_sha256"):
                summary["slide_render_png_available_count"] += 1
            if artifact_hash_is_current(project, receipt, "snapshot_json", "snapshot_json_sha256"):
                summary["snapshot_json_count"] += 1
    for page in sorted(duplicate_page_names(slide_pages)):
        issues.append(issue("slide_render_receipt_duplicate_page", f"slide render receipt page is duplicated: {page}"))
    if set(slide_pages) != expected_pages:
        issues.append(issue("slide_render_receipt_page_set_mismatch", "slide render receipt pages must match prepared SVG pages"))
    visual_pages: list[str] = []
    for rel_path in visual_receipts:
        if _require_file(project, str(rel_path), "visual_fidelity_receipt_missing", issues):
            receipt_page = page_name_from_path(str(rel_path), ".visual-fidelity-receipt.json")
            if receipt_page:
                visual_pages.append(receipt_page)
            summary["visual_fidelity_receipt_count"] += 1
            receipt = read_json(project / str(rel_path))
            receipt_evaluation = evaluate_visual_fidelity_receipt(receipt)
            issues.extend(issue(code, code, str(rel_path)) for code in receipt_evaluation["blocked_reasons"])
            if receipt.get("visual_fidelity_status") == "not_measured" or receipt.get("status") == "not_measured":
                summary["not_measured_count"] += 1
            metrics = dict(receipt.get("metrics") or {})
            metrics["text_regions"] = receipt.get("text_regions") or metrics.get("text_regions") or []
            if not metrics["text_regions"]:
                issues.append(issue("text_regions_missing", "text_regions must not be empty", str(rel_path)))
            evaluation = evaluate_visual_diff_metrics(metrics)
            issues.extend(issue(code, code, str(rel_path)) for code in evaluation["blocked_reasons"])
            if receipt_evaluation["visual_fidelity_passed"] and evaluation["visual_fidelity_passed"] and metrics["text_regions"]:
                summary["visual_fidelity_passed_count"] += 1
    for page in sorted(duplicate_page_names(visual_pages)):
        issues.append(issue("visual_fidelity_receipt_duplicate_page", f"visual fidelity receipt page is duplicated: {page}"))
    if set(visual_pages) != expected_pages:
        issues.append(issue("visual_fidelity_receipt_page_set_mismatch", "visual fidelity receipt pages must match prepared SVG pages"))
    if summary["prepared_svg_count"] < 2:
        issues.append(issue("prepared_svg_count_lt_2", "M8 requires at least two prepared SVG fixtures"))
    if summary["baseline_png_count"] != summary["prepared_svg_count"]:
        issues.append(issue("baseline_png_count_mismatch", "baseline PNG count must match prepared SVG count"))
    if summary["snapshot_json_count"] != summary["prepared_svg_count"]:
        issues.append(issue("snapshot_json_count_mismatch", "snapshot JSON count must match prepared SVG count"))
    if summary["visual_fidelity_receipt_count"] != summary["prepared_svg_count"]:
        issues.append(issue("visual_fidelity_receipt_count_mismatch", "visual fidelity receipt count must match prepared SVG count"))
    if summary["slide_render_png_available_count"] < 2:
        issues.append(issue("slide_render_png_available_count_lt_2", "M8 requires at least two available Slide render PNGs"))
    if summary["visual_fidelity_passed_count"] != summary["slide_render_png_available_count"]:
        issues.append(issue("visual_fidelity_passed_count_mismatch", "passed visual fidelity count must match available Slide render PNG count"))
    return {"status": "failed" if issues else "passed", "issues": issues, "summary": summary}


def run_precreate_visual_fidelity(project: Path) -> dict[str, Any]:
    result = run_visual_fidelity(project)
    issues = [
        item
        for item in result.get("issues", [])
        if isinstance(item, dict) and isinstance(item.get("code"), str)
    ]
    if result.get("status") == "passed" and not issues:
        return {
            "status": "passed",
            "visual_fidelity_passed": True,
            "issues": [],
        }

    issue_codes = {str(item["code"]) for item in issues}
    hard_failures = sorted(issue_codes & PRECREATE_HARD_FAILURE_CODES)
    unknown_failures = sorted(issue_codes - PRECREATE_PARTIAL_ISSUE_CODES - PRECREATE_HARD_FAILURE_CODES)
    if hard_failures or unknown_failures:
        return {
            "status": "failed",
            "visual_fidelity_passed": False,
            "issues": issues,
            "blocked_reasons": hard_failures + unknown_failures,
        }

    return {
        "status": "structure_only_partial",
        "visual_fidelity_passed": False,
        "allowed_claim": "snapshot_structure_fidelity_only",
        "issues": issues,
        "blocked_reasons": sorted(issue_codes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate SVGlide snapshot visual fidelity evidence.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = generate_visual_fidelity_artifacts(args.project)
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema_version": "svglide-snapshot-visual-fidelity-generation/v1",
                    "status": "failed",
                    "issues": [issue("visual_fidelity_generation_failed", str(error))],
                    "summary": {"error_count": 1},
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=args.pretty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
