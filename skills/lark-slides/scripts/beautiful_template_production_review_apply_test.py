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

import beautiful_template_production_review_apply as apply


REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class BeautifulTemplateProductionReviewApplyTest(unittest.TestCase):
    def test_seed_human_review_receipt_contains_34_pending_families(self) -> None:
        receipt = apply.build_human_review_receipt()

        self.assertEqual("human_review_receipt", receipt["artifact_kind"])
        self.assertTrue(receipt["not_promotion_receipt"])
        self.assertTrue(receipt["does_not_modify_matrix"])
        self.assertEqual("beautiful-34", receipt["review_batch_id"])
        self.assertEqual(["pending", "pass", "needs_fix", "reject"], receipt["allowed_human_status"])
        self.assertEqual(34, receipt["summary"]["family_count"])
        self.assertEqual({"pending": 34, "pass": 0, "needs_fix": 0, "reject": 0}, receipt["summary"]["status_counts"])
        self.assertEqual(34, receipt["summary"]["pending_count"])
        self.assertEqual(0, receipt["summary"]["promotion_candidate_count"])
        self.assertEqual(["blue-professional"], receipt["summary"]["production_default_selectable_families"])
        self.assertEqual(34, len(receipt["families"]))
        for family in receipt["families"]:
            self.assertEqual(["pending", "pass", "needs_fix", "reject"], family["allowed_human_status"])
            self.assertEqual("pending", family["human_review_status"])
            self.assertEqual("no_change", family["promotion_action"])
            self.assertIn("evidence_hashes", family)

    def test_can_seed_from_gallery_manifest_contact_sheet_fields(self) -> None:
        manifest_path = REFERENCES_DIR / "production-review" / "beautiful" / "manifest.json"

        receipt = apply.build_human_review_receipt(gallery_receipt_path=manifest_path)

        self.assertEqual(34, receipt["summary"]["family_count"])
        blue = next(item for item in receipt["families"] if item["family_id"] == "blue-professional")
        self.assertEqual("families/blue-professional.html", blue["gallery_url"])
        self.assertEqual("passed", blue["auto_gate_status"])

    def test_decisions_route_pass_fix_reject_without_modifying_matrix(self) -> None:
        matrix_path = REFERENCES_DIR / "beautiful-template-executable-matrix.json"
        before = apply.file_sha256(matrix_path)
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = Path(tmp) / "decisions.json"
            output_path = Path(tmp) / "human-review.json"
            write_json(
                decisions_path,
                {
                    "decisions": [
                        {
                            "family_id": "blue-professional",
                            "status": "pass",
                            "note": "整体可用，继续进入逐套 production review。",
                        },
                        {
                            "family_id": "8-bit-orbit",
                            "status": "needs_fix",
                            "note": "缺 page-family smoke，数据页需要复刻。",
                        },
                        {
                            "family_id": "bold-poster",
                            "status": "reject",
                            "note": "当前不适合默认链路。",
                        },
                    ]
                },
            )

            receipt = apply.build_human_review_receipt(decisions_path=decisions_path, reviewed_at="2026-06-24T00:00:00+08:00")
            apply.write_human_review_receipt(receipt, output_path)
            self.assertTrue(output_path.is_file())

        after = apply.file_sha256(matrix_path)
        self.assertEqual(before, after)
        self.assertEqual(1, receipt["summary"]["promotion_candidate_count"])
        self.assertEqual(1, receipt["summary"]["fix_queue_count"])
        self.assertEqual(1, receipt["summary"]["reject_queue_count"])
        self.assertEqual(["blue-professional"], receipt["summary"]["promotion_candidates"])
        self.assertEqual(["8-bit-orbit"], receipt["summary"]["fix_queue"])
        self.assertEqual(["bold-poster"], receipt["summary"]["reject_queue"])
        self.assertEqual(["blue-professional"], [item["family_id"] for item in receipt["promotion_candidates"]])
        self.assertEqual(["8-bit-orbit"], [item["family_id"] for item in receipt["fix_queue"]])
        self.assertEqual(["bold-poster"], [item["family_id"] for item in receipt["reject_queue"]])
        self.assertTrue(receipt["next_actions"])
        for item in receipt["promotion_candidates"] + receipt["next_actions"]:
            self.assertNotIn("promotion_status", item)
            self.assertNotIn("default_selectable", item)

    def test_human_pass_on_blocked_family_does_not_create_promotion_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = Path(tmp) / "decisions.json"
            write_json(
                decisions_path,
                {
                    "families": {
                        "8-bit-orbit": {
                            "human_review_status": "pass",
                            "human_review_note": "人工觉得好看，但自动门禁仍 blocked。",
                        }
                    }
                },
            )

            receipt = apply.build_human_review_receipt(decisions_path=decisions_path)

        family = next(item for item in receipt["families"] if item["family_id"] == "8-bit-orbit")
        self.assertFalse(family["promotion_eligible"])
        self.assertEqual("no_change", family["promotion_action"])
        self.assertEqual([], receipt["promotion_candidates"])
        self.assertEqual(0, receipt["summary"]["invalid_review_count"])
        self.assertIn("human_pass_waiting_for_auto_gate", [item["action"] for item in receipt["next_actions"]])

    def test_needs_fix_and_reject_require_note_or_issue_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            decisions_path = Path(tmp) / "decisions.json"
            write_json(
                decisions_path,
                {
                    "families": {
                        "8-bit-orbit": {"human_review_status": "needs_fix"},
                        "bold-poster": {"human_review_status": "reject", "issue_codes": ["visual_quality_low"]},
                    }
                },
            )

            receipt = apply.build_human_review_receipt(decisions_path=decisions_path)

        bad = next(item for item in receipt["families"] if item["family_id"] == "8-bit-orbit")
        good = next(item for item in receipt["families"] if item["family_id"] == "bold-poster")
        self.assertIn("human_review_note_or_issue_codes_required", bad["validation_issues"])
        self.assertEqual([], good["validation_issues"])


if __name__ == "__main__":
    unittest.main()
