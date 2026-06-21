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

import svglide_template_fit_check as template_fit


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_project(project: Path, nodes: list[dict[str, object]]) -> None:
    write_json(project / "02-plan/slide_plan.json", {"generation_mode": "artboard_satori", "slides": [{"page": 1}]})
    write_json(
        project / "04-svg/artboard/page-001.node-layout-map.json",
        {"version": "svglide-node-layout-map/v1", "page": 1, "nodes": nodes},
    )
    write_json(
        project / "04-svg/artboard/page-001.receipt.json",
        {
            "version": "svglide-artboard-receipt/v1",
            "status": "passed",
            "page": 1,
            "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
        },
    )
    write_json(
        project / "receipts/generate_svg.json",
        {
            "stage": "generate_svg",
            "status": "passed",
            "generation_mode": "artboard_satori",
            "artboard_receipts": ["04-svg/artboard/page-001.receipt.json"],
        },
    )


class SVGlideTemplateFitCheckTest(unittest.TestCase):
    def test_template_fit_passes_for_nodes_inside_canvas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_project(
                project,
                [
                    {"id": "title", "kind": "text", "x": 80, "y": 80, "width": 720, "height": 72},
                    {"id": "panel", "kind": "shape", "x": 64, "y": 220, "width": 320, "height": 180},
                ],
            )

            result = template_fit.run_template_fit(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["page_count"], 1)
            self.assertEqual(result["pages"][0]["node_count"], 2)
            self.assertEqual(result["inputs"]["generator_receipt"], "receipts/generate_svg.json")
            self.assertEqual(
                result["pages"][0]["node_layout_map_sha256"],
                template_fit.file_sha256(project / "04-svg/artboard/page-001.node-layout-map.json"),
            )
            self.assertTrue((project / "06-check/template-fit.json").exists())
            self.assertTrue((project / "receipts/template-fit-check.json").exists())

    def test_template_fit_fails_for_out_of_canvas_and_short_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_project(
                project,
                [
                    {"id": "title", "kind": "text", "x": 40, "y": 40, "width": 320, "height": 24},
                    {"id": "footer", "kind": "shape", "x": 920, "y": 500, "width": 80, "height": 60},
                ],
            )

            result = template_fit.run_template_fit(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("text_box_too_short", codes)
            self.assertIn("node_out_of_canvas", codes)
            self.assertEqual(result["action"], "repair_and_rerun")


if __name__ == "__main__":
    unittest.main()
