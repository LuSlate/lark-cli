#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import svg_effect_classifier as classifier
import svg_raster_renderer as renderer_mod
import svg_safe_rewrite


VERSION = "1"
MODES = {"off", "auto", "strict", "force-page"}


class RasterizeError(RuntimeError):
    """Raised when SVG rasterization cannot produce a safe output."""


def load_svg(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RasterizeError(f"failed to read SVG input {path}: {error}") from error
    if not text.strip():
        raise RasterizeError(f"SVG input is empty: {path}")
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def whole_page_island(reason: str) -> dict[str, object]:
    return {
        "id": "page-001-island-001",
        "kind": "full-page",
        "reason": reason,
        "bbox": [0.0, 0.0, 960.0, 540.0],
    }


def plan_raster_islands(mode: str, detections: list[classifier.EffectDetection]) -> list[dict[str, object]]:
    if mode == "off":
        return []
    if mode == "force-page":
        return [whole_page_island("force-page")]
    if not detections:
        return []
    reasons = sorted({detection.reason for detection in detections})
    return [whole_page_island("conservative_full_page:" + "; ".join(reasons[:4]))]


def _asset_rel(path: str, base_dir: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def build_report(
    *,
    mode: str,
    input_path: Path,
    output_path: Path,
    base_dir: Path,
    detections: list[classifier.EffectDetection],
    islands: list[dict[str, object]],
    rendered_assets: list[dict[str, object]],
    render_started: float,
) -> dict[str, object]:
    generated_assets = [_asset_rel(str(asset["output_png"]), base_dir) for asset in rendered_assets]
    island_reports: list[dict[str, object]] = []
    for island, asset in zip(islands, rendered_assets):
        island_reports.append(
            {
                "id": island.get("id", "page-001-island-001"),
                "reason": island.get("reason", ""),
                "source_node_ids": island.get("source_node_ids", []),
                "bbox": asset.get("bbox", island.get("bbox", [0.0, 0.0, 960.0, 540.0])),
                "output_png": _asset_rel(str(asset["output_png"]), base_dir),
                "scale": asset.get("scale", 2),
                "bytes": asset.get("bytes", 0),
                "render_ms": asset.get("render_ms", 0),
                "alpha_crop": asset.get("alpha_crop", False),
            }
        )
    total_bytes = sum(int(asset.get("bytes", 0)) for asset in rendered_assets)
    total_ms = sum(int(asset.get("render_ms", 0)) for asset in rendered_assets)
    full_page_count = sum(1 for island in islands if island.get("kind") == "full-page")
    return {
        "version": VERSION,
        "mode": mode,
        "run_id": Path(output_path).parent.name,
        "base_dir": str(base_dir.resolve()),
        "native_text_blocks": 0,
        "rasterized_text_blocks": 0,
        "raster_images": len(rendered_assets),
        "raster_total_bytes": total_bytes,
        "raster_total_ms": total_ms or int((time.monotonic() - render_started) * 1000),
        "full_page_fallback_count": full_page_count,
        "generated_assets": generated_assets,
        "detections": classifier.detections_as_dicts(detections),
        "visual_artifacts": {},
        "quality": {"gate_passed": True},
        "pages": [
            {
                "source_path": str(input_path),
                "safe_path": str(output_path),
                "mode": mode,
                "fallback_reason": islands[0].get("reason", "") if islands else "",
                "runtime_gate_ok": True,
                "pngs": generated_assets,
                "islands": island_reports,
            }
        ],
    }


def rasterize_svg(
    svg: str,
    *,
    mode: str,
    scale: int,
    input_path: Path,
    output_path: Path,
    asset_dir: Path,
    base_dir: Path,
    report_path: Path,
    raster_renderer: renderer_mod.RasterRenderer | None = None,
) -> dict[str, object]:
    if mode not in MODES:
        raise RasterizeError(f"invalid rasterization mode: {mode}")
    if mode != "off" and scale < 2:
        raise RasterizeError("svg raster scale must be >= 2")
    classifier.sanitize_or_reject(svg)
    detections = classifier.classify_effects(svg)
    islands = plan_raster_islands(mode, detections)
    started = time.monotonic()
    rendered_assets = renderer_mod.render_islands(svg, islands, asset_dir, scale, raster_renderer) if islands else []
    safe_svg = svg_safe_rewrite.rewrite_svg(svg, islands, rendered_assets, base_dir)
    svg_safe_rewrite.validate_safe_subset_lightweight(safe_svg)
    write_text(output_path, safe_svg)
    report = build_report(
        mode=mode,
        input_path=input_path,
        output_path=output_path,
        base_dir=base_dir,
        detections=detections,
        islands=islands,
        rendered_assets=rendered_assets,
        render_started=started,
    )
    write_text(report_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rasterize rich SVG effects into safe SVGlide SVG image assets.")
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--preview-html", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        rasterize_svg(
            load_svg(Path(args.input)),
            mode=args.mode,
            scale=args.scale,
            input_path=Path(args.input),
            output_path=Path(args.output),
            asset_dir=Path(args.asset_dir),
            base_dir=Path(args.base_dir),
            report_path=Path(args.report),
        )
    except (RasterizeError, classifier.SvgRasterSafetyError, svg_safe_rewrite.SafeRewriteError, renderer_mod.RasterRenderError) as error:
        print(f"svg_rasterize_effects: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
