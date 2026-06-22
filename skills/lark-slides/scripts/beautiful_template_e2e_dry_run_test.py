# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import beautiful_template_e2e_dry_run


class BeautifulTemplateE2EDryRunTest(unittest.TestCase):
    def test_internal_review_and_zhipu_minimax_dry_runs_pass_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = beautiful_template_e2e_dry_run.run_all(Path(tmpdir))

        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["receipt_count"], 2)
        receipts = {item["case_id"]: item for item in summary["receipts"]}
        self.assertEqual(receipts["internal-review"]["selected_template_id"], "blue-professional")
        self.assertGreaterEqual(receipts["internal-review"]["template_variant_count"], 6)
        self.assertGreaterEqual(receipts["internal-review"]["component_count"], 5)
        self.assertEqual(receipts["internal-review"]["unowned_decorative_primitive_count"], 0)
        self.assertEqual(receipts["zhipu-minimax"]["selected_template_id"], "blue-professional")
        self.assertGreaterEqual(receipts["zhipu-minimax"]["component_count"], 5)
        self.assertEqual(receipts["zhipu-minimax"]["required_image_fill_rate"], 1.0)
        self.assertEqual(receipts["zhipu-minimax"]["unowned_decorative_primitive_count"], 0)
        for receipt in receipts.values():
            self.assertEqual(receipt["preflight_summary"]["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
