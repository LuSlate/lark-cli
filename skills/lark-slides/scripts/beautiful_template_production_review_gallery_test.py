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
    "smoke_deck",
    "pages",
    "contact_sheet",
    "not_promotion_receipt",
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
            self.assertEqual("production_review_family_smoke_deck", family["artifact_kind"])
            self.assertTrue(family["not_promotion_receipt"])
            self.assertTrue(family["family_id"])
            self.assertTrue(family["runtime_template_id"])
            self.assertTrue(family["visual_contract_path"])
            self.assertTrue(family["reference_screenshot"])
            self.assertIsInstance(family["default_selectable"], bool)
            self.assertIsInstance(family["page_variant_count"], int)
            self.assertGreater(family["page_variant_count"], 0)
            self.assertIsInstance(family["implemented_page_variants"], list)
            self.assertIn(family["smoke_status"], {"passed", "failed", "missing"})
            self.assertEqual("smoke_deck_review_data", family["smoke_deck"]["artifact_kind"])
            self.assertIn(family["smoke_deck"]["status"], {"passed", "failed", "missing"})
            self.assertIsInstance(family["pages"], list)
            self.assertGreater(len(family["pages"]), 0)
            self.assertGreaterEqual(len(family["pages"]), family["page_variant_count"])
            self.assertEqual("smoke_deck_contact_sheet_review_model", family["contact_sheet"]["artifact_kind"])
            self.assertIn(family["contact_sheet"]["render_status"], {"passed", "failed", "missing_smoke"})
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
        self.assertEqual("passed", blue["smoke_deck"]["status"])
        self.assertEqual(10, blue["smoke_deck"]["page_count"])
        self.assertEqual(10, len(blue["pages"]))
        self.assertEqual("passed", blue["contact_sheet"]["render_status"])
        self.assertEqual([], blue["missing_roles"])
        split_page = next(page for page in blue["pages"] if page["page_variant_id"] == "split")
        self.assertEqual("comparison_or_split", split_page["role_group"])
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
        self.assertEqual("missing", candidate["smoke_deck"]["status"])
        self.assertEqual("missing_smoke", candidate["contact_sheet"]["render_status"])
        self.assertTrue(all(page["render_status"] == "missing_smoke" for page in candidate["pages"]))
        self.assertIn("missing_smoke", candidate["known_blockers"])
        self.assertIn("production_review_pending", candidate["known_blockers"])

    def test_write_artifacts_keeps_production_default_counts_unchanged(self) -> None:
        before = gallery.matrix_status_counts()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gallery.write_gallery_artifacts(Path(tmpdir), Path(tmpdir) / "receipt.json")
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

    def test_rendered_html_is_human_review_entrypoint_not_promotion_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gallery.write_gallery_artifacts(Path(tmpdir), Path(tmpdir) / "receipt.json")
            output_dir = Path(tmpdir)

            index_html = Path(result["html_path"]).read_text(encoding="utf-8")
            family_html = (output_dir / "families" / "blue-professional.html").read_text(encoding="utf-8")

        for page_html in (index_html, family_html):
            self.assertIn('data-review-status="pass"', page_html)
            self.assertIn('data-review-status="needs_fix"', page_html)
            self.assertIn('data-review-status="reject"', page_html)
            self.assertIn("human_review_status=pending", page_html)
            self.assertIn("promotion_action=no_change_until_human_pass", page_html)
            self.assertIn("beautiful-production-review-decisions-v1", page_html)
            self.assertIn("review-decisions-json", page_html)
            self.assertIn("does not automatically modify production/default", page_html)
            self.assertIn("skills/lark-slides/references/receipts/production-review/beautiful-34-gallery.json", page_html)
            self.assertIn("apply script", page_html)


if __name__ == "__main__":
    unittest.main()
