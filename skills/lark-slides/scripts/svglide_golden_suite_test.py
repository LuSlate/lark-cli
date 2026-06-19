# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_golden_suite


class SVGlideGoldenSuiteTest(unittest.TestCase):
    def test_golden_suite_passes_positive_and_negative_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = svglide_golden_suite.run_suite(Path(tmpdir))

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["positive_case_count"], 3)
            self.assertEqual(result["summary"]["failed_case_count"], 0)
            self.assertTrue((Path(tmpdir) / "golden-suite.json").exists())
            negative = next(case for case in result["cases"] if case["name"] == "negative_english")
            self.assertEqual(negative["expected_status"], "failed")
            self.assertIn("language_not_zh_cn", negative["issue_codes"])


if __name__ == "__main__":
    unittest.main()
