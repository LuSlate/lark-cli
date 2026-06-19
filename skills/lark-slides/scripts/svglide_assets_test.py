# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_assets


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideAssetsTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(project / "02-plan/slide_plan.json", {"route": "svglide-svg", "slides": [{"page": 1}]})
        return project

    def test_assets_stage_creates_empty_assets_json_when_no_contracts(self) -> None:
        project = self.make_project()

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "passed")
        self.assertTrue((project / "03-assets/assets.json").exists())
        self.assertTrue((project / "03-assets/asset-manifest.json").exists())
        self.assertEqual(result["manifest"]["summary"]["contract_count"], 0)

    def test_assets_stage_accepts_existing_local_asset(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "href": "@./03-assets/hero.png"}]},
        )
        (project / "03-assets").mkdir(parents=True, exist_ok=True)
        (project / "03-assets/hero.png").write_bytes(b"png")

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["manifest"]["contracts"][0]["status"], "local_file")

    def test_assets_stage_blocks_required_http_asset(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/svglide.lock.json", {"asset_contracts": [{"id": "hero", "href": "https://example.com/hero.png"}]})

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["manifest"]["summary"]["error_count"], 1)
        self.assertEqual(result["manifest"]["issues"][0]["code"], "invalid_asset_href")


if __name__ == "__main__":
    unittest.main()
