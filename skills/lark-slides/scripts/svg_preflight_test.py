# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest

import svg_preflight


VALID_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#f8fafc" />
  <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
    <div xmlns="http://www.w3.org/1999/xhtml"
         style="font-size:32px;font-weight:800;font-family:Arial;color:#111827;line-height:1.15;text-align:left;">
      Strategy review
    </div>
  </foreignObject>
  <image id="hero" slide:role="image" href="@./assets/hero.jpg" x="560" y="96" width="320" height="220" />
  <path id="trend" slide:role="shape" d="M64 360 L180 330 C260 300 340 340 420 300 Q500 260 580 290" fill="none" stroke="#2563eb" />
</svg>
"""


class SvgPreflightTest(unittest.TestCase):
    def test_lint_svg_accepts_valid_svglide(self) -> None:
        result = svg_preflight.lint_svg(VALID_SVG)
        self.assertEqual(result["summary"]["error_count"], 0)
        self.assertEqual(result["summary"]["warning_count"], 0)

    def test_lint_svg_reports_canvas_mismatch(self) -> None:
        result = svg_preflight.lint_svg(
            VALID_SVG.replace('width="960" height="540" viewBox="0 0 960 540"', 'width="1280" height="720" viewBox="0 0 1280 720"')
        )
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("root_canvas_mismatch", codes)
        self.assertIn("root_viewbox_mismatch", codes)
        self.assertEqual(result["summary"]["error_count"], 2)

    def test_lint_svg_reports_external_image_and_font_shorthand(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="title" slide:role="shape" slide:shape-type="text" x="64" y="56" width="420" height="72">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font: 700 24px Arial;color:#111827;">Title</div>
          </foreignObject>
          <image id="hero" slide:role="image" href="https://example.com/hero.jpg" x="560" y="96" width="320" height="220" />
        </svg>
        """
        result = svg_preflight.lint_svg(svg)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("external_image_href", codes)
        self.assertIn("font_shorthand", codes)

    def test_lint_svg_reports_canvas_error_and_safe_area_warning(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <rect id="badge" slide:role="shape" x="12" y="20" width="80" height="40" />
          <rect id="overflow" slide:role="shape" x="920" y="500" width="120" height="80" />
        </svg>
        """
        result = svg_preflight.lint_svg(svg)
        codes = [issue["code"] for issue in result["issues"]]
        self.assertIn("safe_area", codes)
        self.assertIn("canvas_bounds", codes)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["summary"]["warning_count"], 1)

    def test_lint_svg_reports_text_bbox_overlap(self) -> None:
        svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:slide="https://slides.bytedance.com/ns"
             slide:role="slide"
             width="960" height="540" viewBox="0 0 960 540">
          <foreignObject id="a" slide:role="shape" slide:shape-type="text" x="80" y="80" width="240" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:24px;font-weight:700;color:#111;">A</div>
          </foreignObject>
          <foreignObject id="b" slide:role="shape" slide:shape-type="text" x="120" y="100" width="240" height="80">
            <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:18px;font-weight:400;color:#111;">B</div>
          </foreignObject>
        </svg>
        """
        result = svg_preflight.lint_svg(svg)
        self.assertEqual(result["summary"]["error_count"], 1)
        self.assertEqual(result["issues"][0]["code"], "text_bbox_overlap")


if __name__ == "__main__":
    unittest.main()
