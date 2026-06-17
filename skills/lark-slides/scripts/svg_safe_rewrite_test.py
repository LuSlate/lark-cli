# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import svg_safe_rewrite


SVG_WITH_FILTER = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns"
  slide:role="slide" width="960" height="540" viewBox="0 0 960 540">
  <defs><filter id="glow" /></defs>
  <rect filter="url(#glow)" x="0" y="0" width="960" height="540" />
</svg>"""


class SvgSafeRewriteTest(unittest.TestCase):
    def test_full_page_rewrite_outputs_single_safe_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp)
            png = base_dir / ".lark-slides" / "rasterized" / "run-1" / "page-001-island-001.png"
            png.parent.mkdir(parents=True)
            png.write_bytes(b"placeholder")

            safe_svg = svg_safe_rewrite.full_page_image_svg(SVG_WITH_FILTER, png, base_dir)

            svg_safe_rewrite.validate_safe_subset_lightweight(safe_svg)
            self.assertIn('slide:role="slide"', safe_svg)
            self.assertIn('href="@./.lark-slides/rasterized/run-1/page-001-island-001.png"', safe_svg)
            self.assertIn('x="0" y="0" width="960" height="540"', safe_svg)
            self.assertNotIn("<filter", safe_svg)

    def test_safe_gate_rejects_residual_rich_effects(self) -> None:
        with self.assertRaises(svg_safe_rewrite.SafeRewriteError):
            svg_safe_rewrite.validate_safe_subset_lightweight(SVG_WITH_FILTER)

    def test_asset_href_rejects_paths_outside_base_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base_dir = Path(temp) / "base"
            base_dir.mkdir()
            outside = Path(temp) / "outside.png"
            outside.write_bytes(b"placeholder")

            with self.assertRaises(svg_safe_rewrite.SafeRewriteError):
                svg_safe_rewrite.href_for_asset(outside, base_dir)


if __name__ == "__main__":
    unittest.main()
