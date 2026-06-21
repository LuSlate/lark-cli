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

    def test_node_layout_map_accepts_measured_observation(self) -> None:
        layout_map = json.loads((FIXTURE_DIR / "page-001.node-layout-map.json").read_text(encoding="utf-8"))

        issues = svglide_node_layout_drift.validate_node_layout_map(layout_map)

        self.assertEqual(issues, [])

    def test_node_layout_map_rejects_material_drift(self) -> None:
        layout_map = json.loads((FIXTURE_DIR / "page-001.node-layout-drift.json").read_text(encoding="utf-8"))

        issues = svglide_node_layout_drift.validate_node_layout_map(layout_map)

        self.assertIn("node_layout_drift_exceeds_threshold", {item["code"] for item in issues})


if __name__ == "__main__":
    unittest.main()
