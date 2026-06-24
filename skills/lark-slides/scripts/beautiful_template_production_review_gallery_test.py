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

import beautiful_template_production_review_gallery as gallery


REQUIRED_FAMILY_FIELDS = {
    "family_id",
    "runtime_template_id",
    "visual_contract_path",
    "reference_screenshot",
    "promotion_status",
    "default_selectable",
    "page_variant_count",
    "implemented_page_variants",
    "smoke_status",
}


class BeautifulTemplateProductionReviewGalleryTest(unittest.TestCase):
    def test_gallery_manifest_contains_all_34_candidates_with_review_fields(self) -> None:
        manifest = gallery.build_gallery_manifest()

        self.assertEqual("production_review_gallery", manifest["artifact_kind"])
        self.assertTrue(manifest["not_promotion_receipt"])
        self.assertEqual(34, manifest["summary"]["candidate_count"])
        self.assertEqual(34, len(manifest["families"]))

        family_ids = set()
        for family in manifest["families"]:
            self.assertTrue(REQUIRED_FAMILY_FIELDS.issubset(family), family)
            self.assertTrue(family["family_id"])
            self.assertTrue(family["runtime_template_id"])
            self.assertTrue(family["visual_contract_path"])
            self.assertTrue(family["reference_screenshot"])
            self.assertIsInstance(family["default_selectable"], bool)
            self.assertIsInstance(family["page_variant_count"], int)
            self.assertGreater(family["page_variant_count"], 0)
            self.assertIsInstance(family["implemented_page_variants"], list)
            self.assertIn(family["smoke_status"], {"passed", "failed", "missing"})
            self.assertIn(family["review_decision"], {"pending_review"})
            family_ids.add(family["family_id"])

        self.assertEqual(34, len(family_ids))

    def test_blue_professional_smoke_is_evidence_not_promotion_receipt(self) -> None:
        manifest = gallery.build_gallery_manifest()
        blue = next(item for item in manifest["families"] if item["family_id"] == "blue-professional")

        self.assertEqual("executive-dashboard", blue["runtime_template_id"])
        self.assertEqual("production", blue["promotion_status"])
        self.assertTrue(blue["default_selectable"])
        self.assertEqual("passed", blue["smoke_status"])
        self.assertEqual("page-family-smoke", blue["smoke"]["artifact_kind"])
        self.assertTrue(blue["smoke"]["receipt_path"])
        self.assertTrue(blue["smoke"]["receipt_sha256"])
        self.assertGreaterEqual(blue["page_variant_count"], 10)
        self.assertEqual("production_review_gallery", manifest["artifact_kind"])
        self.assertNotEqual("promotion_receipt", blue.get("artifact_kind"))

    def test_non_smoke_families_remain_needs_review_and_missing_smoke(self) -> None:
        manifest = gallery.build_gallery_manifest()
        candidate = next(item for item in manifest["families"] if item["family_id"] == "8-bit-orbit")

        self.assertEqual("needs_review", candidate["promotion_status"])
        self.assertFalse(candidate["default_selectable"])
        self.assertEqual("missing", candidate["smoke_status"])
        self.assertIn("production_review_pending", candidate["known_blockers"])

    def test_write_artifacts_keeps_production_default_counts_unchanged(self) -> None:
        before = gallery.matrix_status_counts()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gallery.write_gallery_artifacts(Path(tmpdir))
            manifest_path = Path(result["manifest_path"])
            html_path = Path(result["html_path"])

            self.assertTrue(manifest_path.is_file())
            self.assertTrue(html_path.is_file())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        after = gallery.matrix_status_counts()
        self.assertEqual(before, after)
        self.assertEqual(before["production_default_selectable_count"], manifest["summary"]["production_default_selectable_count"])
        self.assertEqual(before["default_selectable_count"], manifest["summary"]["default_selectable_count"])
        self.assertEqual(34, manifest["summary"]["candidate_count"])
        self.assertTrue(manifest["not_promotion_receipt"])


if __name__ == "__main__":
    unittest.main()
