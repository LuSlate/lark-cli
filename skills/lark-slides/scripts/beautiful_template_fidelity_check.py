#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
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
            "color_distribution": 0.18,
            "layout_structure": 0.18,
            "edge_density": 0.12,
            "whitespace": 0.08,
            "dominant_region": 0.12,
            "color_complexity": 0.08,
            "primary_color_alignment": 0.10,
            "layout_region": 0.08,
            "decorative_density": 0.03,
            "typographic_hierarchy": 0.03,
        },
    }


REQUIRED_METRIC_KEYS = tuple(default_profile()["weights"].keys())
GENERATOR_VERSION = "svglide-template-fidelity-check/v2"


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _bin_distance(a: tuple[int, int, int], b: tuple[int, int, int], bins: int = 16) -> float:
    return (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) / (3 * max(1, bins - 1))


def _dominant_palette_similarity(a: Counter, b: Counter, *, limit: int = 5, bins: int = 16) -> float:
    total_a = sum(a.values()) or 1
    total_b = sum(b.values()) or 1
    top_a = a.most_common(limit)
    top_b = b.most_common(limit)
    if not top_a or not top_b:
        return 0.0
    weighted = 0.0
    weight_total = 0.0
    for color_a, count_a in top_a:
        weight = count_a / total_a
        nearest = max(0.0, 1.0 - min(_bin_distance(color_a, color_b, bins) for color_b, _ in top_b))
        weighted += nearest * weight
        weight_total += weight
    coverage = sum(count for _, count in top_b) / total_b
    return max(0.0, min(1.0, (weighted / (weight_total or 1)) * min(1.0, coverage + 0.15)))


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


def _region_class(pixel: tuple[int, int, int]) -> int:
    r, g, b = pixel
    total = r + g + b
    if r > 238 and g > 238 and b > 238:
        return 0
    if total < 190:
        return 1
    if max(r, g, b) - min(r, g, b) > 70:
        return 2
    return 3


def _coarse_region_signature(
    width: int,
    height: int,
    pixels: list[tuple[int, int, int]],
    *,
    columns: int = 12,
    rows: int = 6,
) -> list[int]:
    signature: list[int] = []
    for row in range(rows):
        y0 = row * height // rows
        y1 = max(y0 + 1, (row + 1) * height // rows)
        for column in range(columns):
            x0 = column * width // columns
            x1 = max(x0 + 1, (column + 1) * width // columns)
            classes: Counter[int] = Counter()
            for y in range(y0, y1):
                for x in range(x0, x1):
                    classes[_region_class(pixels[y * width + x])] += 1
            signature.append(classes.most_common(1)[0][0] if classes else 3)
    return signature


def _signature_similarity(a: list[int], b: list[int]) -> float:
    total = min(len(a), len(b)) or 1
    return sum(1 for left, right in zip(a[:total], b[:total]) if left == right) / total


def _decorative_density_similarity(reference_edge_density: float, render_edge_density: float) -> float:
    if reference_edge_density <= 0.015:
        return 1.0
    return max(0.0, min(1.0, render_edge_density / reference_edge_density))


def _active_text_band_heights(width: int, height: int, pixels: list[tuple[int, int, int]]) -> list[int]:
    active_rows: list[bool] = []
    for y in range(height):
        active = 0
        for x in range(width):
            r, g, b = pixels[y * width + x]
            saturation = max(r, g, b) - min(r, g, b)
            if r + g + b < 390 or (saturation > 70 and r + g + b < 650):
                active += 1
        active_rows.append(active / max(1, width) >= 0.08)
    bands: list[int] = []
    current = 0
    for active in active_rows:
        if active:
            current += 1
        elif current:
            bands.append(current)
            current = 0
    if current:
        bands.append(current)
    return bands


def _typographic_hierarchy_value(width: int, height: int, pixels: list[tuple[int, int, int]]) -> float:
    bands = _active_text_band_heights(width, height, pixels)
    if len(bands) < 2:
        return 1.0 if bands else 0.0
    sorted_bands = sorted(bands)
    middle = sorted_bands[len(sorted_bands) // 2]
    return max(bands) / max(1, middle)


def _typographic_hierarchy_similarity(reference_value: float, render_value: float) -> float:
    if reference_value <= 1.2:
        return 1.0
    return max(0.0, min(1.0, render_value / reference_value))


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


def _receipt_provenance(reference: Path, render: Path, command: list[str] | None = None) -> dict[str, Any]:
    return {
        "generated_by": "beautiful_template_fidelity_check.py",
        "generator_version": GENERATOR_VERSION,
        "command": command or [],
        "reference_sha256": _file_sha256(reference),
        "render_sha256": _file_sha256(render),
    }


def role_consumption_from_canvas_spec_payload(payload: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    typography = payload.get("theme", {}).get("typography", {}) if isinstance(payload.get("theme"), dict) else {}
    if not isinstance(typography, dict):
        return None
    font_roles = typography.get("font_roles") if isinstance(typography.get("font_roles"), dict) else {}
    typography_roles = typography.get("role_tokens") if isinstance(typography.get("role_tokens"), dict) else {}
    text_style_roles = typography.get("text_style_roles") if isinstance(typography.get("text_style_roles"), dict) else {}
    if not font_roles and not typography_roles and not text_style_roles:
        return None
    return {
        "source": source,
        "font_roles": font_roles,
        "typography_roles": typography_roles,
        "text_style_roles": text_style_roles,
    }


def role_consumption_from_canvas_spec(path: Path) -> dict[str, Any] | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return role_consumption_from_canvas_spec_payload(payload, source=str(path))


def _failure(template_id: str, reference: Path, render: Path, code: str, message: str, command: list[str] | None = None) -> dict[str, Any]:
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
        **_receipt_provenance(reference, render, command),
    }


def check_template_fidelity(
    *,
    render_screenshot: Path,
    template_id: str,
    page_type: str = "default",
    reference_screenshot: Path | None = None,
    reference_root: Path | None = None,
    min_score: float | None = None,
    command: list[str] | None = None,
    role_consumption: dict[str, Any] | None = None,
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
        return _failure(template_id, reference_screenshot, render_screenshot, "reference_missing", "reference screenshot is missing", command)
    if not render_screenshot.exists():
        return _failure(template_id, reference_screenshot, render_screenshot, "render_missing", "render screenshot is missing", command)

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
    ref_edge_density = _edge_density(ref_width, ref_height, ref_pixels)
    render_edge_density = _edge_density(render_width, render_height, render_pixels)
    ref_hierarchy = _typographic_hierarchy_value(ref_width, ref_height, ref_pixels)
    render_hierarchy = _typographic_hierarchy_value(render_width, render_height, render_pixels)
    metrics = {
        "color_distribution": _histogram_similarity(ref_hist, render_hist),
        "layout_structure": _layout_similarity(ref_pixels, render_pixels),
        "edge_density": _ratio_similarity(ref_edge_density, render_edge_density),
        "whitespace": _ratio_similarity(_whitespace_ratio(ref_pixels), _whitespace_ratio(render_pixels)),
        "dominant_region": _ratio_similarity(_dominant_left_region_ratio(ref_width, ref_pixels), _dominant_left_region_ratio(render_width, render_pixels)),
        "color_complexity": min(1.0, max(0.0, (len(render_hist) - 1) / 5)),
        "primary_color_alignment": _dominant_palette_similarity(ref_hist, render_hist, bins=int(profile["normalization"]["quantize_color_bins"])),
        "layout_region": _signature_similarity(
            _coarse_region_signature(ref_width, ref_height, ref_pixels),
            _coarse_region_signature(render_width, render_height, render_pixels),
        ),
        "decorative_density": _decorative_density_similarity(ref_edge_density, render_edge_density),
        "typographic_hierarchy": _typographic_hierarchy_similarity(ref_hierarchy, render_hierarchy),
    }
    weights = profile["weights"]
    score = sum(metrics[key] * weights[key] for key in weights)
    issues: list[dict[str, str]] = []
    if len(render_hist) <= 1:
        issues.append({"code": "single_color_render", "message": "render collapsed to a single color block"})
    if len(render_hist) <= 1 and _whitespace_ratio(render_pixels) > 0.95:
        issues.append({"code": "render_blank", "message": "render screenshot is visually blank"})
    if len(render_hist) <= 2 and _whitespace_ratio(render_pixels) > 0.2:
        issues.append({"code": "generic_card_layout", "message": "render resembles a generic card layout, not the reference template"})
    if metrics["primary_color_alignment"] < 0.58 and metrics["color_distribution"] < 0.62:
        issues.append({"code": "primary_color_drift", "message": "render dominant palette drifted from the reference template"})
    if metrics["layout_region"] < 0.68:
        issues.append({"code": "layout_main_region_misaligned", "message": "render main layout regions do not align with the reference template"})
    decorative_density_tolerated = score >= threshold + 0.08 and metrics["decorative_density"] >= 0.32
    if ref_edge_density >= 0.045 and render_edge_density < ref_edge_density * 0.58 and not decorative_density_tolerated:
        issues.append({"code": "decorative_density_missing", "message": "render dropped decorative line or detail density from the reference template"})
    if ref_hierarchy >= 2.0 and render_hierarchy < ref_hierarchy * 0.65:
        issues.append({"code": "typographic_hierarchy_missing", "message": "render dropped the reference template typography hierarchy"})
    if score < threshold:
        issues.append({"code": "structure_similarity_below_threshold", "message": "template structure is below fidelity threshold"})

    receipt = {
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
        **_receipt_provenance(reference_screenshot, render_screenshot, command),
    }
    if role_consumption:
        receipt["role_consumption"] = role_consumption
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rendered", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--reference-root")
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--page-type", default="default")
    parser.add_argument("--canvas-spec")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    role_consumption = role_consumption_from_canvas_spec(Path(args.canvas_spec)) if args.canvas_spec else None
    receipt = check_template_fidelity(
        render_screenshot=Path(args.rendered),
        reference_screenshot=Path(args.reference) if args.reference else None,
        reference_root=Path(args.reference_root) if args.reference_root else None,
        template_id=args.template_id,
        page_type=args.page_type,
        command=[Path(sys.argv[0]).name, *sys.argv[1:]],
        role_consumption=role_consumption,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
