#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beautiful_template_page_family_extract as extract


SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")


class BeautifulTemplatePageFamilyExtractTest(unittest.TestCase):
    def test_blue_professional_extracts_10_source_layout_variants(self) -> None:
        report = extract.extract_family("blue-professional", source_root=SOURCE_ROOT)

        variants = report["page_variants"]
        self.assertEqual(10, len(variants))
        self.assertEqual(
            [
                "cover",
                "agenda",
                "metrics",
                "dashboard",
                "split",
                "bars",
                "quote",
                "timeline",
                "detail",
                "closing",
            ],
            list(variants),
        )
        self.assertEqual("layout-cover", variants["cover"]["source_class"])

    def test_blue_professional_role_mapping_uses_runtime_roles(self) -> None:
        report = extract.extract_family("blue-professional", source_root=SOURCE_ROOT)
        variants = report["page_variants"]

        self.assertEqual("cover", variants["cover"]["page_role"])
        self.assertEqual("agenda", variants["agenda"]["page_role"])
        self.assertEqual("data_dashboard", variants["dashboard"]["page_role"])
        self.assertEqual("process_or_timeline", variants["timeline"]["page_role"])
        self.assertEqual("closing", variants["closing"]["page_role"])

    def test_each_variant_has_traceable_source_refs_and_confidence(self) -> None:
        report = extract.extract_family("blue-professional", source_root=SOURCE_ROOT)

        for variant_id, variant in report["page_variants"].items():
            with self.subTest(variant=variant_id):
                self.assertTrue(variant["required_slots"])
                self.assertTrue(variant["source_refs"])
                self.assertEqual("css_extracted_from_template_html", variant["extraction_confidence"])
                for ref in variant["source_refs"]:
                    self.assertTrue((SOURCE_ROOT.parent / ref["path"]).is_file(), ref)
                    self.assertTrue(ref["selector_or_token"])
                    self.assertTrue(ref["raw_value"])

    def test_all_34_families_generate_extraction_report_without_production_claims(self) -> None:
        report = extract.extract_all(source_root=SOURCE_ROOT)

        self.assertEqual(34, report["summary"]["family_count"])
        self.assertEqual(34, report["summary"]["families_with_page_variants"])
        self.assertNotIn("default_selectable", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("promotion_status", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
