# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import ppt_master_asset_inventory as inventory


REFERENCE_DIR = SCRIPT_DIR.parent / "references"


def ppt_master_source() -> Path:
    return inventory.default_source_root()


class PptMasterAssetInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = ppt_master_source()
        cls.asset_map = inventory.build_asset_map(cls.source)

    def test_schema_and_counts_cover_required_categories(self) -> None:
        inventory.validate_asset_map(self.asset_map)
        resources = self.asset_map["resources"]
        counts = Counter(resource["kind"] for resource in resources)

        self.assertEqual(self.asset_map["schema_version"], inventory.SCHEMA_VERSION)
        self.assertEqual(counts["brand_preset"], 2)
        self.assertEqual(counts["layout_template"], 7)
        self.assertEqual(counts["deck_template"], 8)
        self.assertEqual(counts["chart_template"], 71)
        self.assertEqual(counts["icon_library"], 5)
        self.assertEqual(counts["example_project"], 21)
        self.assertEqual(counts["visual_style"], 18)
        self.assertEqual(counts["image_palette"], 14)
        self.assertEqual(counts["image_rendering"], 20)
        self.assertEqual(counts["image_type_template"], 11)
        self.assertEqual(counts["narrative_mode"], 5)
        self.assertGreaterEqual(counts["workflow_reference"], 6)

        for resource in resources:
            missing = inventory.REQUIRED_FIELDS - set(resource)
            self.assertEqual(missing, set(), resource["id"])

    def test_checked_in_asset_map_matches_source_counts_and_digests(self) -> None:
        checked_in = json.loads((REFERENCE_DIR / "ppt-master-asset-map.json").read_text(encoding="utf-8"))

        self.assertEqual(checked_in["schema_version"], inventory.SCHEMA_VERSION)
        self.assertEqual(checked_in["summary"]["counts"], self.asset_map["summary"]["counts"])
        self.assertEqual(checked_in["summary"]["digests"], self.asset_map["summary"]["digests"])

    def test_raw_svg_resources_are_never_active(self) -> None:
        raw_resources = [
            resource
            for resource in self.asset_map["resources"]
            if resource["protocol_compatibility"] == "needs_normalization"
        ]
        self.assertGreater(len(raw_resources), 0)

        for resource in raw_resources:
            self.assertEqual(resource["copy_policy"], "derive_contract_only", resource["id"])
            self.assertEqual(resource["license_status"], "reference_only", resource["id"])
            self.assertNotIn(resource["activation_status"], {"validated", "active"}, resource["id"])

    def test_icons_and_examples_are_summarized_not_expanded(self) -> None:
        icon_resources = [resource for resource in self.asset_map["resources"] if resource["kind"] == "icon_library"]
        icon_file_count = self.asset_map["summary"]["counts"]["icon_svg_files"]

        self.assertEqual(len(icon_resources), 5)
        self.assertGreater(icon_file_count, 11000)
        self.assertLess(len(self.asset_map["resources"]), icon_file_count)
        for resource in icon_resources:
            self.assertEqual(resource["granularity"], "library_summary")
            self.assertEqual(resource["metadata"]["index_policy"], "library_summary_only")
            self.assertIn("sample_icons", resource["metadata"])

        examples = [resource for resource in self.asset_map["resources"] if resource["kind"] == "example_project"]
        self.assertEqual(len(examples), 21)
        for resource in examples:
            self.assertEqual(resource["granularity"], "project_page_media_summary")
            self.assertIn("page_count", resource["metadata"])
            self.assertIn("media_count", resource["metadata"])
            self.assertIn("base64_count", resource["metadata"])
            self.assertIn("project_digest", resource["metadata"])


if __name__ == "__main__":
    unittest.main()
