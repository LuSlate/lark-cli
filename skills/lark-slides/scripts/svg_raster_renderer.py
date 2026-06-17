#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Protocol

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised in minimal Python installs.
    Image = None  # type: ignore[assignment]


CANVAS_WIDTH = 960
CANVAS_HEIGHT = 540
MAX_PNG_BYTES = 20 * 1024 * 1024
TRANSPARENT_1X1_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lM6c3QAAAABJRU5ErkJggg=="
)


class RasterRenderError(RuntimeError):
    """Raised when Chromium rasterization or PNG validation fails."""


class RasterRenderer(Protocol):
    def render_full_page(self, svg: str, output_png: Path, scale: int) -> dict[str, object]:
        ...


def viewport_size_from_svg(svg: str) -> tuple[int, int]:
    # P0 keeps the SVGlide root contract fixed. Go-side validation enforces the
    # full contract later, so the renderer defaults to the canonical canvas.
    return CANVAS_WIDTH, CANVAS_HEIGHT


class PlaywrightRasterRenderer:
    def render_full_page(self, svg: str, output_png: Path, scale: int) -> dict[str, object]:
        if scale < 2:
            raise RasterRenderError("svg raster scale must be >= 2")
        started = time.monotonic()
        output_png.parent.mkdir(parents=True, exist_ok=True)
        width, height = viewport_size_from_svg(svg)
        html = self._preview_html(svg, width, height)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RasterRenderError(
                "python package playwright is required for SVG rasterization; install it and run `python3 -m playwright install chromium`"
            ) from error

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=scale,
                    java_script_enabled=False,
                    bypass_csp=False,
                )
                page = context.new_page()
                page.route("**/*", lambda route: route.abort())
                page.set_content(html, wait_until="load")
                page.screenshot(path=str(output_png), clip={"x": 0, "y": 0, "width": width, "height": height}, omit_background=False)
                browser.close()
        except Exception as error:  # pragma: no cover - depends on local Chromium.
            raise RasterRenderError(f"Chromium SVG rasterization failed: {error}") from error

        validate_png(output_png, require_nontransparent=True)
        return {
            "output_png": str(output_png),
            "bbox": [0.0, 0.0, float(width), float(height)],
            "scale": scale,
            "bytes": output_png.stat().st_size,
            "render_ms": int((time.monotonic() - started) * 1000),
            "alpha_crop": False,
        }

    @staticmethod
    def _preview_html(svg: str, width: int, height: int) -> str:
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<style>html,body{margin:0;width:%dpx;height:%dpx;background:#fff;overflow:hidden;}svg{display:block;}</style>"
            "</head><body>%s</body></html>"
        ) % (width, height, svg)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RasterRenderError(f"not a PNG file: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def validate_png(path: Path, require_nontransparent: bool = True) -> None:
    if not path.exists():
        raise RasterRenderError(f"raster PNG does not exist: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise RasterRenderError(f"raster PNG is empty: {path}")
    if size > MAX_PNG_BYTES:
        raise RasterRenderError(f"raster PNG exceeds {MAX_PNG_BYTES} bytes: {path}")
    width, height = png_dimensions(path)
    if width <= 0 or height <= 0:
        raise RasterRenderError(f"raster PNG has invalid dimensions: {path}")
    if require_nontransparent and Image is not None:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            if not any(pixel[3] > 0 for pixel in rgba.getdata()):
                raise RasterRenderError(f"raster PNG is fully transparent: {path}")


def render_islands(
    svg: str,
    islands: list[dict[str, object]],
    asset_dir: Path,
    scale: int,
    renderer: RasterRenderer | None = None,
) -> list[dict[str, object]]:
    renderer = renderer or PlaywrightRasterRenderer()
    rendered: list[dict[str, object]] = []
    for index, island in enumerate(islands, start=1):
        if island.get("kind") != "full-page":
            raise RasterRenderError("only full-page raster islands are implemented in P0")
        output_png = asset_dir / f"page-001-island-{index:03d}.png"
        result = dict(renderer.render_full_page(svg, output_png, scale))
        validate_png(Path(str(result["output_png"])), require_nontransparent=True)
        rendered.append(result)
    return rendered
