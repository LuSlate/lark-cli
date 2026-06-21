#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ASSET_MANIFEST = Path("03-assets/asset-manifest.json")
SVG_DIR = Path("04-svg")
INJECTABLE_ROLES = {"cover", "closing", "body_visual", "inline_figure"}
FILE_BACKED_STATUSES = {"acquired", "local_file", "generated"}
FILE_BACKED_KINDS = {"web_image", "user_file", "ai_image"}
SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE | re.DOTALL)
VIEWBOX_RE = re.compile(r"""viewBox\s*=\s*["']\s*([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s+([0-9.-]+)\s*["']""", re.IGNORECASE)
NUMBER_ATTR_RE = re.compile(r"""{name}\s*=\s*["']([0-9.]+)(?:px)?["']""")
PAGE_RE = re.compile(r"page-(\d+)\.svg$")
FULL_SLIDE_RECT_RE = re.compile(r"<rect\b[^>]*>", re.IGNORECASE | re.DOTALL)


class AssetInjectionError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_object(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise AssetInjectionError(f"missing required file: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AssetInjectionError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AssetInjectionError(f"invalid JSON in {path}: expected object")
    return payload


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed
    return None


def safe_id(value: Any) -> str:
    raw = str(value or "asset").strip().lower()
    out = "".join(ch if ch.isalnum() else "-" for ch in raw).strip("-")
    return out or "asset"


def source_svg_files(project: Path) -> list[Path]:
    svg_dir = project / SVG_DIR
    if not svg_dir.exists():
        return []
    return sorted(path for path in svg_dir.glob("*.svg") if path.is_file())


def page_number(path: Path, fallback: int) -> int:
    match = PAGE_RE.search(path.name)
    if match:
        return int(match.group(1))
    return fallback


def slide_count(project: Path, fallback: int) -> int:
    plan = read_json_object(project / "02-plan" / "slide_plan.json", required=False)
    slides = plan.get("slides")
    if isinstance(slides, list) and slides:
        return len(slides)
    count = as_int(plan.get("page_count") or plan.get("target_slide_count"))
    return count if count and count > 0 else fallback


def normalize_asset_file(project: Path, raw: Any) -> tuple[Path | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, None
    value = raw.strip()
    if value.startswith("@./"):
        rel = value[3:]
    elif value.startswith("@/"):
        rel = value[2:]
    else:
        rel = value
    path = (project / rel).resolve()
    root = project.resolve()
    if path != root and root not in path.parents:
        return None, None
    return path, f"@./{rel}"


def has_safe_text_zone(asset: dict[str, Any]) -> bool:
    zones = asset.get("safe_text_zones")
    return isinstance(zones, list) and bool(zones)


def candidate_page(asset: dict[str, Any], *, page_count: int) -> int | None:
    page = as_int(asset.get("page") or asset.get("usage_page"))
    role = asset.get("placement_role")
    if page and page > 0:
        return page
    if role == "cover":
        return 1
    if role == "closing":
        return page_count if page_count > 0 else None
    return None


def merged_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ["acquired_assets", "contracts"]:
        values = manifest.get(key)
        if not isinstance(values, list):
            continue
        for raw in values:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            asset_id = item.get("asset_id") or item.get("id")
            if not isinstance(asset_id, str) or not asset_id.strip():
                continue
            item["asset_id"] = asset_id
            dedupe_key = f"{asset_id}:{item.get('page') or item.get('usage_page')}:{item.get('placement_role')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            merged.append(item)
    return merged


def geometry(svg_text: str) -> tuple[float, float]:
    open_match = SVG_OPEN_RE.search(svg_text)
    if not open_match:
        return 960.0, 540.0
    tag = open_match.group(0)
    viewbox = VIEWBOX_RE.search(tag)
    if viewbox:
        return float(viewbox.group(3)), float(viewbox.group(4))
    width_re = re.compile(NUMBER_ATTR_RE.pattern.format(name="width"), re.IGNORECASE)
    height_re = re.compile(NUMBER_ATTR_RE.pattern.format(name="height"), re.IGNORECASE)
    width = width_re.search(tag)
    height = height_re.search(tag)
    if width and height:
        return float(width.group(1)), float(height.group(1))
    return 960.0, 540.0


def has_body_slot(svg_text: str, asset: dict[str, Any], page: int) -> bool:
    asset_id = safe_id(asset.get("asset_id"))
    tokens = [
        "data-svglide-asset-slot",
        f'id="asset-slot-{asset_id}"',
        f"id='asset-slot-{asset_id}'",
        f'id="asset-slot-page-{page:03d}"',
        f"id='asset-slot-page-{page:03d}'",
        'data-node-id="image-label"',
        "data-node-id='image-label'",
        "<!-- svglide:asset-slot",
    ]
    return any(token in svg_text for token in tokens)


def already_injected(svg_text: str, asset_id: str) -> bool:
    escaped = html.escape(asset_id, quote=True)
    safe = safe_id(asset_id)
    return f'data-svglide-asset-id="{escaped}"' in svg_text or f'id="svglide-asset-{safe}"' in svg_text


def cover_or_closing_layer(asset: dict[str, Any], *, href: str, width: float, height: float) -> str:
    role = str(asset.get("placement_role") or "")
    asset_id = html.escape(str(asset.get("asset_id")), quote=True)
    safe = safe_id(asset.get("asset_id"))
    scrim_opacity = "0.40" if role == "cover" else "0.30"
    return f"""
  <g id="svglide-asset-{safe}" data-svglide-asset-layer="true" data-svglide-asset-id="{asset_id}" data-svglide-placement-role="{html.escape(role, quote=True)}">
    <image slide:role="image" id="svglide-asset-image-{safe}" href="{html.escape(href, quote=True)}" x="0" y="0" width="{width:g}" height="{height:g}" preserveAspectRatio="xMidYMid slice" />
    <rect slide:role="shape" id="svglide-asset-scrim-{safe}" x="0" y="0" width="{width:g}" height="{height:g}" fill="#06111F" opacity="{scrim_opacity}" />
  </g>"""


def text_layer(id_: str, *, x: float, y: float, width: float, height: float, text: str, color: str = "#1F2937", size: int = 12) -> str:
    safe_id = html.escape(id_, quote=True)
    safe_text = html.escape(text, quote=True)
    style = (
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;"
        f"font-size:{size}px;font-weight:600;line-height:1.2;color:{color};"
        "white-space:pre-wrap;overflow:hidden;"
    )
    return (
        f'<foreignObject slide:role="shape" slide:shape-type="text" id="{safe_id}" '
        f'x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="{html.escape(style, quote=True)}">{safe_text}</div>'
        "</foreignObject>"
    )


def figure_layer(asset: dict[str, Any], *, href: str, width: float, height: float) -> str:
    asset_id = html.escape(str(asset.get("asset_id")), quote=True)
    safe = safe_id(asset.get("asset_id"))
    return f"""
  <g id="svglide-asset-{safe}" data-svglide-asset-layer="true" data-svglide-asset-id="{asset_id}" data-svglide-placement-role="{html.escape(str(asset.get("placement_role") or ""), quote=True)}">
    <rect slide:role="shape" x="{width - 368:g}" y="78" width="320" height="276" rx="8" fill="#FFFFFF" opacity="0.92" />
    <image slide:role="image" id="svglide-asset-image-{safe}" href="{html.escape(href, quote=True)}" x="{width - 352:g}" y="94" width="288" height="216" preserveAspectRatio="xMidYMid slice" />
  </g>"""


def ambient_layer(asset: dict[str, Any], *, href: str, width: float, height: float) -> str:
    asset_id = html.escape(str(asset.get("asset_id")), quote=True)
    safe = safe_id(asset.get("asset_id"))
    return f"""
  <g id="svglide-asset-{safe}" data-svglide-asset-layer="true" data-svglide-asset-id="{asset_id}" data-svglide-placement-role="{html.escape(str(asset.get("placement_role") or ""), quote=True)}" data-svglide-slot-strategy="ambient_fallback">
    <image slide:role="image" id="svglide-asset-image-{safe}" href="{html.escape(href, quote=True)}" x="0" y="0" width="{width:g}" height="{height:g}" preserveAspectRatio="xMidYMid slice" opacity="0.22" />
    <rect slide:role="shape" id="svglide-asset-ambient-scrim-{safe}" x="0" y="0" width="{width:g}" height="{height:g}" fill="#06111F" opacity="0.52" />
  </g>"""


def inject_layer(svg_text: str, layer: str) -> str:
    match = SVG_OPEN_RE.search(svg_text)
    if not match:
        raise AssetInjectionError("source SVG has no <svg> root")
    insert_at = match.end()
    tail = svg_text[insert_at:]
    rect_match = FULL_SLIDE_RECT_RE.match(tail.lstrip())
    if rect_match:
        leading_ws = len(tail) - len(tail.lstrip())
        rect = rect_match.group(0)
        attrs = {
            name: value
            for name, value in re.findall(r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*["']([^"']+)["']""", rect)
        }
        if attrs.get("x", "0") == "0" and attrs.get("y", "0") == "0" and attrs.get("width") in {"960", "960.0"} and attrs.get("height") in {"540", "540.0"}:
            insert_at += leading_ws + rect_match.end()
    return svg_text[:insert_at] + layer + svg_text[insert_at:]


def injection_for_asset(project: Path, svg_text: str, asset: dict[str, Any], *, page: int) -> tuple[str, dict[str, Any]]:
    role = asset.get("placement_role")
    asset_id = str(asset.get("asset_id"))
    result: dict[str, Any] = {
        "page": page,
        "asset_id": asset_id,
        "placement_role": role,
        "status": "skipped",
    }
    if role not in INJECTABLE_ROLES:
        result["reason"] = "placement_role_not_injectable"
        return svg_text, result
    status = asset.get("status")
    kind = asset.get("asset_kind")
    if status not in FILE_BACKED_STATUSES or kind not in FILE_BACKED_KINDS:
        result["reason"] = "asset_has_no_local_file"
        return svg_text, result
    asset_path, href = normalize_asset_file(project, asset.get("file") or asset.get("href") or asset.get("path"))
    if asset_path is None or href is None or not asset_path.exists() or not asset_path.is_file():
        result["reason"] = "asset_file_missing"
        result["file"] = asset.get("file")
        return svg_text, result
    if role in {"cover", "closing"} and not has_safe_text_zone(asset):
        result["reason"] = "safe_text_zones_missing"
        result["file"] = relpath(asset_path, project)
        return svg_text, result
    if role == "inline_figure" and not asset.get("source_url"):
        result["reason"] = "inline_figure_source_missing"
        result["file"] = relpath(asset_path, project)
        return svg_text, result
    if already_injected(svg_text, asset_id):
        result.update(
            {
                "status": "already_present",
                "href": href,
                "file": relpath(asset_path, project),
                "asset_kind": kind,
                "source_url": asset.get("source_url"),
                "license": asset.get("license"),
            }
        )
        return svg_text, result
    width, height = geometry(svg_text)
    slot_strategy = "declared_slot"
    if role in {"cover", "closing"}:
        layer = cover_or_closing_layer(asset, href=href, width=width, height=height)
        renderer_id = "editorial_image_cover" if role == "cover" else "image_closing_takeaway"
        slot_strategy = "full_bleed"
    else:
        if has_body_slot(svg_text, asset, page):
            layer = figure_layer(asset, href=href, width=width, height=height)
            renderer_id = "figure_panel_asset"
        else:
            layer = ambient_layer(asset, href=href, width=width, height=height)
            renderer_id = "ambient_asset_background"
            slot_strategy = "ambient_fallback"
    injected = inject_layer(svg_text, layer)
    result.update(
        {
            "status": "injected",
            "href": href,
            "file": relpath(asset_path, project),
            "asset_kind": kind,
            "source_url": asset.get("source_url"),
            "license": asset.get("license"),
            "renderer_id": renderer_id,
            "slot_strategy": slot_strategy,
            "asset_fit_reason": f"{role} page has local file-backed {kind} asset",
        }
    )
    return injected, result


def inject_project_assets(project: Path) -> dict[str, Any]:
    project = project.resolve()
    manifest = read_json_object(project / ASSET_MANIFEST, required=False)
    svg_files = source_svg_files(project)
    pages = {page_number(path, index): path for index, path in enumerate(svg_files, 1)}
    page_count = slide_count(project, len(svg_files))
    by_page: dict[int, list[dict[str, Any]]] = {}
    for asset in merged_assets(manifest):
        page = candidate_page(asset, page_count=page_count)
        if page is None:
            continue
        by_page.setdefault(page, []).append(asset)

    results: list[dict[str, Any]] = []
    for page, assets in sorted(by_page.items()):
        svg_path = pages.get(page)
        if svg_path is None:
            for asset in assets:
                results.append(
                    {
                        "page": page,
                        "asset_id": asset.get("asset_id"),
                        "placement_role": asset.get("placement_role"),
                        "status": "skipped",
                        "reason": "page_svg_missing",
                    }
                )
            continue
        svg_text = svg_path.read_text(encoding="utf-8")
        page_results: list[dict[str, Any]] = []
        for asset in sorted(assets, key=lambda item: str(item.get("asset_id"))):
            updated, result = injection_for_asset(project, svg_text, asset, page=page)
            svg_text = updated
            page_results.append(result)
        if any(item.get("status") == "injected" for item in page_results):
            svg_path.write_text(svg_text, encoding="utf-8")
        results.extend(page_results)

    injected = [item for item in results if item.get("status") == "injected"]
    already = [item for item in results if item.get("status") == "already_present"]
    skipped = [item for item in results if item.get("status") == "skipped"]
    return {
        "version": "svglide-asset-injection/v1",
        "status": "passed",
        "generated_at": now_iso(),
        "manifest_path": ASSET_MANIFEST.as_posix() if manifest else None,
        "used_count": len(injected) + len(already),
        "injected_count": len(injected),
        "already_present_count": len(already),
        "skipped_count": len(skipped),
        "by_page": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inject file-backed SVGlide assets into generated SVG pages.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = inject_project_assets(Path(args.project))
    except (OSError, AssetInjectionError) as error:
        print(f"svglide_asset_injector: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
