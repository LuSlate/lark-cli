# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest

import svg_effect_classifier as classifier


SAFE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <defs><linearGradient id="g"><stop offset="0" stop-color="#fff" /></linearGradient></defs>
  <path d="M10 10 L100 10 C120 20 140 20 160 10 Q180 0 200 10 Z" fill="url(#g)" />
</svg>"""


class SvgEffectClassifierTest(unittest.TestCase):
    def reasons(self, svg: str) -> list[str]:
        return [detection.reason for detection in classifier.classify_effects(svg)]

    def test_rejects_unsafe_input_before_render(self) -> None:
        unsafe_inputs = [
            "<!DOCTYPE svg><svg></svg>",
            '<svg><script href="https://example.test/a.js" /></svg>',
            '<svg><rect onload="alert(1)" /></svg>',
            '<svg><image href="javascript:alert(1)" /></svg>',
            '<svg><iframe src="https://example.test" /></svg>',
        ]

        for svg in unsafe_inputs:
            with self.subTest(svg=svg):
                with self.assertRaises(classifier.SvgRasterSafetyError):
                    classifier.sanitize_or_reject(svg)

    def test_detects_rich_svg_effects(self) -> None:
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">
          <defs><filter id="glow" /><mask id="m" /><clipPath id="c" /><symbol id="s"><rect /></symbol></defs>
          <use href="#s" filter="url(#glow)" />
          <path d="M10 10 A40 40 0 0 1 80 80" />
          <text x="10" y="20">Title</text>
          <polygon points="0,0 10,0 10,10" style="mix-blend-mode:multiply" />
        </svg>"""

        reasons = "\n".join(self.reasons(svg))

        self.assertIn("unsupported SVG tag <filter>", reasons)
        self.assertIn("unsupported SVG tag <mask>", reasons)
        self.assertIn("unsupported SVG tag <clipPath>", reasons)
        self.assertIn("unsupported SVG tag <symbol>", reasons)
        self.assertIn("unsupported SVG tag <use>", reasons)
        self.assertIn("path contains unsupported A/S/T commands", reasons)
        self.assertIn("root-level text requires raster or safe rewrite", reasons)
        self.assertIn("unsupported CSS property mix-blend-mode", reasons)

    def test_safe_gradient_path_is_not_flagged(self) -> None:
        self.assertEqual(classifier.classify_effects(SAFE_SVG), [])


if __name__ == "__main__":
    unittest.main()
