# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import svg_rasterize_effects as rasterize


RICH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns"
  slide:role="slide" width="960" height="540" viewBox="0 0 960 540">
  <defs><filter id="glow"><feGaussianBlur stdDeviation="8" /></filter></defs>
  <rect x="0" y="0" width="960" height="540" fill="#fff" />
  <circle cx="480" cy="270" r="120" fill="#2563eb" filter="url(#glow)" />
</svg>"""


class FakeRenderer:
    def render_full_page(self, svg: str, output_png: Path, scale: int) -> dict[str, object]:
        image = Image.new("RGBA", (960 * scale, 540 * scale), (255, 255, 255, 255))
        output_png.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_png)
        return {
            "output_png": str(output_png),
            "bbox": [0.0, 0.0, 960.0, 540.0],
            "scale": scale,
            "bytes": output_png.stat().st_size,
            "render_ms": 3,
            "alpha_crop": False,
        }


class SvgRasterizeEffectsTest(unittest.TestCase):
    def test_force_page_rasterizes_to_safe_svg_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            output = base_dir / ".lark-slides" / "rasterized" / "run-1" / "page-001.safe.svg"
            report_path = base_dir / ".lark-slides" / "rasterized" / "run-1" / "raster-report.json"

            report = rasterize.rasterize_svg(
                RICH_SVG,
                mode="force-page",
                scale=2,
                input_path=base_dir / "page-001.svg",
                output_path=output,
                asset_dir=output.parent,
                base_dir=base_dir,
                report_path=report_path,
                raster_renderer=FakeRenderer(),
            )

            safe_svg = output.read_text(encoding="utf-8")
            persisted_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "force-page")
            self.assertEqual(persisted_report["raster_images"], 1)
            self.assertEqual(persisted_report["full_page_fallback_count"], 1)
            self.assertIn('href="@./.lark-slides/rasterized/run-1/page-001-island-001.png"', safe_svg)
            self.assertNotIn("<filter", safe_svg)
            self.assertTrue((output.parent / "page-001-island-001.png").exists())

    def test_auto_uses_conservative_full_page_when_effects_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            output = base_dir / ".lark-slides" / "rasterized" / "run-1" / "page-001.safe.svg"
            report_path = output.parent / "raster-report.json"

            report = rasterize.rasterize_svg(
                RICH_SVG,
                mode="auto",
                scale=2,
                input_path=base_dir / "page-001.svg",
                output_path=output,
                asset_dir=output.parent,
                base_dir=base_dir,
                report_path=report_path,
                raster_renderer=FakeRenderer(),
            )

            self.assertEqual(report["full_page_fallback_count"], 1)
            self.assertTrue(str(report["pages"][0]["fallback_reason"]).startswith("conservative_full_page:"))

    def test_scale_below_two_is_rejected_for_raster_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            with self.assertRaises(rasterize.RasterizeError):
                rasterize.rasterize_svg(
                    RICH_SVG,
                    mode="force-page",
                    scale=1,
                    input_path=base_dir / "page.svg",
                    output_path=base_dir / "page.safe.svg",
                    asset_dir=base_dir,
                    base_dir=base_dir,
                    report_path=base_dir / "report.json",
                    raster_renderer=FakeRenderer(),
                )


if __name__ == "__main__":
    unittest.main()
