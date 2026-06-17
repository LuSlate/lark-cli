# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import svglide_golden_suite as golden_suite


class SVGlideGoldenSuiteTest(unittest.TestCase):
    def test_list_json_outputs_manifest_with_required_cases(self) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = golden_suite.main(["list", "--json"])

        self.assertEqual(exit_code, 0)
        manifest = json.loads(stdout.getvalue())
        self.assertEqual(manifest["schema_version"], "svglide-golden-suite-manifest/v1")
        self.assertEqual(manifest["case_count"], len(manifest["cases"]))
        self.assertGreaterEqual(manifest["case_count"], 3)
        case_ids = {case["case_id"] for case in manifest["cases"]}
        self.assertTrue(
            {
                "ai-capital-editorial",
                "aksu-oasis-planning",
                "runtime-smoke",
            }.issubset(case_ids)
        )

        for case in manifest["cases"]:
            for key in ["case_id", "theme_domain", "prompt_summary", "expected_archetypes", "required_evidence"]:
                self.assertIn(key, case)
            self.assertIsInstance(case["expected_archetypes"], list)
            self.assertTrue(case["expected_archetypes"])

    def test_manifest_has_no_external_reference_project_words(self) -> None:
        encoded = json.dumps(golden_suite.build_manifest(), ensure_ascii=False).lower()
        banned_tokens = [
            "ppt" + "-master",
            "ppt" + "_master",
            "ppt" + " master",
            "hugo" + "he3",
            "ppt" + "169",
        ]

        for token in banned_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, encoded)

    def test_each_case_declares_required_evidence(self) -> None:
        for case in golden_suite.list_cases():
            with self.subTest(case_id=case["case_id"]):
                evidence = case["required_evidence"]
                self.assertIsInstance(evidence, list)
                self.assertTrue(evidence)
                self.assertTrue(all(isinstance(item, str) and item for item in evidence))

    def test_aksu_case_locks_agenda_and_section_regression(self) -> None:
        cases = {case["case_id"]: case for case in golden_suite.list_cases()}
        aksu = cases["aksu-oasis-planning"]

        self.assertIn("agenda", aksu["expected_archetypes"])
        self.assertIn("section", aksu["expected_archetypes"])
        self.assertIn("agenda_numbered_path", aksu["required_evidence"])
        self.assertIn("section_signal", aksu["required_evidence"])


if __name__ == "__main__":
    unittest.main()
