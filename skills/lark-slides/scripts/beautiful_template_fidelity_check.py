#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import json
import struct
import zlib
from collections import Counter
from pathlib import Path
from typing import Any


def default_profile() -> dict[str, Any]:
    return {
        "viewport": {"width": 960, "height": 540, "device_scale_factor": 1},
        "normalization": {"target_size": {"width": 96, "height": 54}, "strip_alpha_to_white": True, "quantize_color_bins": 16},
        "thresholds": {"overall_min": 0.72, "warn_min": 0.62},
        "weights": {
            "color_distribution": 0.25,
            "layout_structure": 0.25,
            "edge_density": 0.2,
            "whitespace": 0.1,
            "dominant_region": 0.2,
        },
    }


def _paeth_predictor(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    pa = abs(estimate - left)
    pb = abs(estimate - up)
    pc = abs(estimate - upper_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return upper_left


def _read_png_rgb(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a PNG file: {path}")
    pos = 8
    width = height = 0
    color_type = None
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        payload = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or color_type not in {2, 6}:
                raise ValueError(f"unsupported PNG format: {path}")
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(bytes(idat))
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    pixels: list[tuple[int, int, int]] = []
    previous = [0] * stride
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        row = list(raw[offset : offset + stride])
        offset += stride
        if filter_type == 1:
            for i in range(stride):
                row[i] = (row[i] + (row[i - channels] if i >= channels else 0)) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                row[i] = (row[i] + previous[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = previous[i]
                row[i] = (row[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = previous[i]
                upper_left = previous[i - channels] if i >= channels else 0
                row[i] = (row[i] + _paeth_predictor(left, up, upper_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"unsupported PNG filter {filter_type}: {path}")
        previous = row
        if color_type == 6:
            for i in range(0, stride, 4):
                alpha = row[i + 3] / 255
                pixels.append(
                    (
                        round(row[i] * alpha + 255 * (1 - alpha)),
                        round(row[i + 1] * alpha + 255 * (1 - alpha)),
                        round(row[i + 2] * alpha + 255 * (1 - alpha)),
                    )
                )
        else:
            pixels.extend((row[i], row[i + 1], row[i + 2]) for i in range(0, stride, 3))
    return width, height, pixels


def _resize_nearest(
    width: int,
    height: int,
    pixels: list[tuple[int, int, int]],
    *,
    target_width: int,
    target_height: int,
) -> tuple[int, int, list[tuple[int, int, int]]]:
    if width == target_width and height == target_height:
        return width, height, pixels
    resized: list[tuple[int, int, int]] = []
    for y in range(target_height):
        source_y = min(height - 1, int(y * height / target_height))
        for x in range(target_width):
            source_x = min(width - 1, int(x * width / target_width))
            resized.append(pixels[source_y * width + source_x])
    return target_width, target_height, resized


def _quantized_histogram(pixels: list[tuple[int, int, int]], bins: int = 16) -> Counter[tuple[int, int, int]]:
    step = max(1, 256 // bins)
    return Counter((r // step, g // step, b // step) for r, g, b in pixels)


def _histogram_similarity(a: Counter, b: Counter) -> float:
    total_a = sum(a.values()) or 1
    total_b = sum(b.values()) or 1
    keys = set(a) | set(b)
    distance = sum(abs(a.get(key, 0) / total_a - b.get(key, 0) / total_b) for key in keys) / 2
    return max(0.0, 1.0 - distance)


def _layout_similarity(a: list[tuple[int, int, int]], b: list[tuple[int, int, int]]) -> float:
    total = min(len(a), len(b)) or 1
    matches = 0
    for left, right in zip(a[:total], b[:total]):
        if sum(abs(left[i] - right[i]) for i in range(3)) <= 36:
            matches += 1
    return matches / total


def _whitespace_ratio(pixels: list[tuple[int, int, int]]) -> float:
    return sum(1 for r, g, b in pixels if r > 238 and g > 238 and b > 238) / (len(pixels) or 1)


def _edge_density(width: int, height: int, pixels: list[tuple[int, int, int]]) -> float:
    if width <= 1 or height <= 1:
        return 0.0
    edges = 0
    checks = 0
    for y in range(height - 1):
        for x in range(width - 1):
            here = pixels[y * width + x]
            right = pixels[y * width + x + 1]
            down = pixels[(y + 1) * width + x]
            if sum(abs(here[i] - right[i]) for i in range(3)) > 90 or sum(abs(here[i] - down[i]) for i in range(3)) > 90:
                edges += 1
            checks += 1
    return edges / (checks or 1)


def _dominant_left_region_ratio(width: int, pixels: list[tuple[int, int, int]]) -> float:
    if not pixels:
        return 0.0
    left_width = max(1, width // 2)
    left_pixels = [pixel for index, pixel in enumerate(pixels) if index % width < left_width]
    dark = sum(1 for r, g, b in left_pixels if r + g + b < 180)
    saturated = sum(1 for r, g, b in left_pixels if max(r, g, b) - min(r, g, b) > 90)
    return (dark + saturated) / (len(left_pixels) or 1)


def _ratio_similarity(a: float, b: float) -> float:
    return max(0.0, 1.0 - abs(a - b))


def select_reference_screenshot(reference_root: Path, *, template_id: str, page_type: str = "default") -> dict[str, Any]:
    exact = reference_root / template_id / f"{page_type}.png"
    if exact.exists():
        return {"path": exact, "rule": "template_page_type"}
    default = reference_root / template_id / "default.png"
    return {"path": default, "rule": "template_default"}


def _failure(template_id: str, reference: Path, render: Path, code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": "svglide-template-fidelity/v1",
        "stage": "template_fidelity",
        "status": "failed",
        "template_id": template_id,
        "page_type": "unknown",
        "reference_screenshot": str(reference),
        "render_screenshot": str(render),
        "reference_selection": {"rule": "explicit", "path": str(reference)},
        "score": 0.0,
        "threshold": default_profile()["thresholds"]["overall_min"],
        "metrics": {},
        "issues": [{"code": code, "message": message}],
    }


def check_template_fidelity(
    *,
    render_screenshot: Path,
    template_id: str,
    page_type: str = "default",
    reference_screenshot: Path | None = None,
    reference_root: Path | None = None,
    min_score: float | None = None,
) -> dict[str, Any]:
    profile = default_profile()
    threshold = min_score if min_score is not None else profile["thresholds"]["overall_min"]
    if reference_screenshot is None:
        if reference_root is None:
            raise ValueError("reference_screenshot or reference_root is required")
        selection = select_reference_screenshot(reference_root, template_id=template_id, page_type=page_type)
        reference_screenshot = Path(selection["path"])
        selection_rule = selection["rule"]
    else:
        selection_rule = "explicit"

    if not reference_screenshot.exists():
        return _failure(template_id, reference_screenshot, render_screenshot, "reference_missing", "reference screenshot is missing")
    if not render_screenshot.exists():
        return _failure(template_id, reference_screenshot, render_screenshot, "render_missing", "render screenshot is missing")

    ref_width, ref_height, ref_pixels = _read_png_rgb(reference_screenshot)
    render_width, render_height, render_pixels = _read_png_rgb(render_screenshot)
    target = profile["normalization"]["target_size"]
    ref_width, ref_height, ref_pixels = _resize_nearest(
        ref_width,
        ref_height,
        ref_pixels,
        target_width=int(target["width"]),
        target_height=int(target["height"]),
    )
    render_width, render_height, render_pixels = _resize_nearest(
        render_width,
        render_height,
        render_pixels,
        target_width=int(target["width"]),
        target_height=int(target["height"]),
    )

    render_hist = _quantized_histogram(render_pixels)
    ref_hist = _quantized_histogram(ref_pixels)
    metrics = {
        "color_distribution": _histogram_similarity(ref_hist, render_hist),
        "layout_structure": _layout_similarity(ref_pixels, render_pixels),
        "edge_density": _ratio_similarity(_edge_density(ref_width, ref_height, ref_pixels), _edge_density(render_width, render_height, render_pixels)),
        "whitespace": _ratio_similarity(_whitespace_ratio(ref_pixels), _whitespace_ratio(render_pixels)),
        "dominant_region": _ratio_similarity(_dominant_left_region_ratio(ref_width, ref_pixels), _dominant_left_region_ratio(render_width, render_pixels)),
    }
    weights = profile["weights"]
    score = sum(metrics[key] * weights[key] for key in weights)
    issues: list[dict[str, str]] = []
    if len(render_hist) <= 1:
        issues.append({"code": "render_blank", "message": "render screenshot is visually blank"})
    if len(render_hist) <= 2 and _whitespace_ratio(render_pixels) > 0.2:
        issues.append({"code": "generic_card_layout", "message": "render resembles a generic card layout, not the reference template"})
    if score < threshold:
        issues.append({"code": "structure_similarity_below_threshold", "message": "template structure is below fidelity threshold"})

    return {
        "schema_version": "svglide-template-fidelity/v1",
        "stage": "template_fidelity",
        "status": "passed" if not issues else "failed",
        "template_id": template_id,
        "page_type": page_type,
        "reference_screenshot": str(reference_screenshot),
        "render_screenshot": str(render_screenshot),
        "reference_selection": {"rule": selection_rule, "path": str(reference_screenshot)},
        "score": round(score, 4),
        "threshold": threshold,
        "metrics": {key: round(value, 4) for key, value in metrics.items()},
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rendered", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--reference-root")
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--page-type", default="default")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    receipt = check_template_fidelity(
        render_screenshot=Path(args.rendered),
        reference_screenshot=Path(args.reference) if args.reference else None,
        reference_root=Path(args.reference_root) if args.reference_root else None,
        template_id=args.template_id,
        page_type=args.page_type,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
