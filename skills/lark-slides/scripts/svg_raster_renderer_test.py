# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

import svg_raster_renderer as renderer


SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540" fill="#fff"/></svg>'


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
            "render_ms": 1,
            "alpha_crop": False,
        }


class SvgRasterRendererTest(unittest.TestCase):
    def test_render_islands_validates_nonempty_nontransparent_png(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            rendered = renderer.render_islands(
                SVG,
                [{"kind": "full-page"}],
                Path(temp),
                2,
                FakeRenderer(),
            )

            output_png = Path(str(rendered[0]["output_png"]))
            self.assertTrue(output_png.exists())
            self.assertEqual(renderer.png_dimensions(output_png), (1920, 1080))

    def test_validate_png_rejects_fully_transparent_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "transparent.png"
            Image.new("RGBA", (10, 10), (255, 255, 255, 0)).save(path)

            with self.assertRaises(renderer.RasterRenderError):
                renderer.validate_png(path, require_nontransparent=True)


if __name__ == "__main__":
    unittest.main()
