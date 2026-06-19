# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_ppt_master_inventory


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlidePPTMasterInventoryTest(unittest.TestCase):
    def test_inventory_passes_active_native_cleared_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "source/ppt-master-asset-map.json",
                {
                    "schema_version": "svglide-ppt-master-asset-map/v1",
                    "items": [
                        {
                            "source": "ppt-master/layouts/title.json",
                            "kind": "layout",
                            "svglide_target": "svg-seeds:title",
                            "activation_status": "active",
                            "copy_policy": "svglide_native",
                            "license_status": "cleared",
                            "unsupported_features": [],
                        }
                    ],
                },
            )

            result = svglide_ppt_master_inventory.run_inventory(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["active_count"], 1)

    def test_inventory_blocks_active_raw_runtime_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "source/ppt-master-asset-map.json",
                {
                    "schema_version": "svglide-ppt-master-asset-map/v1",
                    "items": [
                        {
                            "source": "ppt-master/raw/template.pptx",
                            "kind": "pptx",
                            "svglide_target": "runtime",
                            "activation_status": "active",
                            "copy_policy": "blocked_raw_runtime",
                            "license_status": "unknown",
                            "unsupported_features": ["pptx-runtime"],
                        }
                    ],
                },
            )

            result = svglide_ppt_master_inventory.run_inventory(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("active_asset_copy_policy_invalid", codes)
            self.assertIn("active_asset_license_not_cleared", codes)
            self.assertIn("raw_runtime_asset_active", codes)


if __name__ == "__main__":
    unittest.main()
