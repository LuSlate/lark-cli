#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_node_layout_drift
import svglide_semantic_map_ir


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures/svglide_artboard/followup_semantic_layout"


class SVGlideSemanticMapIRTest(unittest.TestCase):
    def test_semantic_map_validates_visible_text_and_source_ref(self) -> None:
        semantic_map = json.loads((FIXTURE_DIR / "page-001.semantic-map.json").read_text(encoding="utf-8"))

        issues = svglide_semantic_map_ir.validate_semantic_map_against_svg(semantic_map, FIXTURE_DIR / "page-001.svg")

        self.assertEqual(issues, [])

    def test_semantic_map_rejects_visible_text_drift(self) -> None:
        semantic_map = json.loads((FIXTURE_DIR / "page-001.semantic-map.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "page-001.svg"
            svg_path.write_text((FIXTURE_DIR / "page-001.svg").read_text(encoding="utf-8").replace("Semantic IR Title", "Drifted Title"), encoding="utf-8")

            issues = svglide_semantic_map_ir.validate_semantic_map_against_svg(semantic_map, svg_path)

        self.assertIn("semantic_map_visible_text_mismatch", {item["code"] for item in issues})

    def test_semantic_map_accepts_satori_split_text_without_node_ids(self) -> None:
        semantic_map = {
            "elements": [
                {"element_id": "eyebrow", "kind": "text", "text": "CONSUMER AI", "source_ref": "canvas_spec.content.eyebrow"},
                {"element_id": "title", "kind": "text", "text": "豆包 App：AI 入口", "source_ref": "canvas_spec.content.title"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "satori.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                "<text>CONSUMER</text><text> </text><text>AI</text>"
                "<text>豆</text><text>包</text><text> </text><text>App</text><text>：</text>"
                "<text>AI</text><text> </text><text>入</text><text>口</text>"
                "</svg>",
                encoding="utf-8",
            )

            issues = svglide_semantic_map_ir.validate_semantic_map_against_svg(semantic_map, svg_path)

        self.assertEqual(issues, [])

    def test_semantic_map_accepts_field_label_prefix_for_visible_value(self) -> None:
        semantic_map = {
            "elements": [
                {"element_id": "callout", "kind": "text", "text": "conclusion: 入口越短，频次越高"},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = Path(tmpdir) / "satori.svg"
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                "<text>入口</text><text>越短</text><text>，</text><text>频次越高</text>"
                "</svg>",
                encoding="utf-8",
            )

            issues = svglide_semantic_map_ir.validate_semantic_map_against_svg(semantic_map, svg_path)

        self.assertEqual(issues, [])

    def test_node_layout_map_accepts_measured_observation(self) -> None:
        layout_map = json.loads((FIXTURE_DIR / "page-001.node-layout-map.json").read_text(encoding="utf-8"))

        issues = svglide_node_layout_drift.validate_node_layout_map(layout_map)

        self.assertEqual(issues, [])

    def test_node_layout_map_accepts_canonical_fallback_observation(self) -> None:
        layout_map = json.loads((FIXTURE_DIR / "page-001.node-layout-map.json").read_text(encoding="utf-8"))
        layout_map["drift"]["missing_count"] = 1
        layout_map["drift"]["canonical_fallback_count"] = 1
        layout_map["nodes"][0]["observation_source"] = "missing"
        layout_map["nodes"][0]["measured_bbox"] = layout_map["nodes"][0]["expected_bbox"]
        layout_map["nodes"][0]["drift_px"] = None

        issues = svglide_node_layout_drift.validate_node_layout_map(layout_map)

        self.assertEqual(issues, [])

    def test_node_layout_map_rejects_material_drift(self) -> None:
        layout_map = json.loads((FIXTURE_DIR / "page-001.node-layout-drift.json").read_text(encoding="utf-8"))

        issues = svglide_node_layout_drift.validate_node_layout_map(layout_map)

        self.assertIn("node_layout_drift_exceeds_threshold", {item["code"] for item in issues})


if __name__ == "__main__":
    unittest.main()
