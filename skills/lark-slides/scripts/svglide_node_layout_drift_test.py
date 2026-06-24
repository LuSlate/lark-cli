#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_node_layout_drift as drift


class NodeLayoutDriftTest(unittest.TestCase):
    def test_observations_from_svg_groups_satori_masked_text_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "page.satori.svg"
            svg_path.write_text(
                '<svg width="960" height="540" viewBox="0 0 960 540" xmlns="http://www.w3.org/2000/svg">'
                '<mask id="satori_om-id-1"><rect x="80" y="226" width="204" height="74" fill="#fff"/></mask>'
                '<text x="90" y="239" font-size="12">Hello</text>'
                '<text x="126" y="239" font-size="12"> </text>'
                '<text x="132" y="239" font-size="12">world</text>'
                '<mask id="satori_om-id-2"><rect x="338" y="100" width="284" height="340" fill="#fff"/></mask>'
                '<path x="338" y="100" width="284" height="340" fill="#D6DD63" d="M338 100 H622 V440 H338 Z"/>'
                "</svg>",
                encoding="utf-8",
            )

            observations = drift.observations_from_svg(svg_path)

        text_observations = [item for item in observations if item["kind"] == "text"]
        self.assertEqual(len(text_observations), 1)
        self.assertEqual(text_observations[0]["text"], "Hello world")
        self.assertEqual(text_observations[0]["bbox"], {"x": 80.0, "y": 226.0, "width": 204.0, "height": 74.0})

    def test_rendered_satori_text_min_height_expansion_does_not_count_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "page.satori.svg"
            svg_path.write_text(
                '<svg width="960" height="540" viewBox="0 0 960 540" xmlns="http://www.w3.org/2000/svg">'
                '<text x="648" y="151" width="34.1" height="14.85" font-size="11" fill="#fff">FIELD</text>'
                "</svg>",
                encoding="utf-8",
            )
            layout_map = drift.build_node_layout_map(
                page=1,
                expected_nodes=[
                    {
                        "id": "satori-text-1",
                        "kind": "text",
                        "x": 648,
                        "y": 140,
                        "width": 34.1,
                        "height": 24,
                        "text": "FIELD",
                    }
                ],
                renderer_observations=[],
                satori_svg_path=svg_path,
            )

        self.assertEqual(layout_map["observation_source"], "rendered_satori_svg_parse")
        self.assertEqual(layout_map["drift"]["status"], "passed")
        self.assertEqual(layout_map["drift"]["max_px"], 0)
        self.assertEqual(layout_map["nodes"][0]["height"], 24)
        self.assertAlmostEqual(layout_map["nodes"][0]["measured_bbox"]["height"], 14.85)


if __name__ == "__main__":
    unittest.main()
