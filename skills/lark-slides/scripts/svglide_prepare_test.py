# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_prepare


SIMPLE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     slide:contract-version="svglide-authoring-contract/v1"
     width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" />
</svg>
"""


class SVGlidePrepareTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        (project / "04-svg").mkdir(parents=True)
        (project / "03-assets").mkdir(parents=True)
        return project

    def test_prepare_copies_source_to_prepared_and_writes_receipt(self) -> None:
        project = self.make_project()
        (project / "04-svg" / "page-001.svg").write_text(SIMPLE_SVG, encoding="utf-8")

        receipt = svglide_prepare.prepare_project(project)

        prepared = project / "04-svg" / "prepared" / "page-001.svg"
        self.assertTrue(prepared.exists())
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["source_files"], ["04-svg/page-001.svg"])
        self.assertEqual(receipt["prepared_files"][0]["prepared"], "04-svg/prepared/page-001.svg")
        self.assertTrue((project / "receipts" / "prepare.json").exists())

    def test_prepare_fails_when_no_source_svg_exists(self) -> None:
        project = self.make_project()

        with self.assertRaisesRegex(svglide_prepare.PrepareError, "no source SVG files"):
            svglide_prepare.prepare_project(project)

    def test_prepare_fails_on_unresolved_local_asset(self) -> None:
        project = self.make_project()
        svg = SIMPLE_SVG.replace(
            "</svg>",
            '<image slide:role="image" href="@./assets/missing.png" x="0" y="0" width="100" height="80" /></svg>',
        )
        (project / "04-svg" / "page-001.svg").write_text(svg, encoding="utf-8")

        with self.assertRaisesRegex(svglide_prepare.PrepareError, "unresolved image placeholder"):
            svglide_prepare.prepare_project(project)

    def test_prepare_accepts_asset_mapping(self) -> None:
        project = self.make_project()
        svg = SIMPLE_SVG.replace(
            "</svg>",
            '<image slide:role="image" href="@./assets/hero.png" x="0" y="0" width="100" height="80" /></svg>',
        )
        (project / "04-svg" / "page-001.svg").write_text(svg, encoding="utf-8")
        (project / "03-assets" / "assets.json").write_text(json.dumps({"@./assets/hero.png": "boxcn_hero"}), encoding="utf-8")

        receipt = svglide_prepare.prepare_project(project)

        self.assertEqual(receipt["asset_refs"][0]["refs"][0]["status"], "mapped")
        self.assertEqual(receipt["asset_refs"][0]["refs"][0]["token"], "boxcn_hero")

    def test_prepare_accepts_existing_local_asset(self) -> None:
        project = self.make_project()
        (project / "assets").mkdir()
        (project / "assets" / "hero.png").write_bytes(b"fake")
        svg = SIMPLE_SVG.replace(
            "</svg>",
            '<image slide:role="image" href="@./assets/hero.png" x="0" y="0" width="100" height="80" /></svg>',
        )
        (project / "04-svg" / "page-001.svg").write_text(svg, encoding="utf-8")

        receipt = svglide_prepare.prepare_project(project)

        self.assertEqual(receipt["asset_refs"][0]["refs"][0]["status"], "local")
        self.assertEqual(receipt["asset_refs"][0]["refs"][0]["path"], "assets/hero.png")


if __name__ == "__main__":
    unittest.main()
