# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest

import iconpark_tool


class IconParkToolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index_data = iconpark_tool.load_index()

    def test_search_icons_finds_growth_trend(self) -> None:
        results = iconpark_tool.search_icons(self.index_data, {"query": "增长趋势", "limit": 5})
        self.assertTrue(results)
        self.assertTrue(
            any(entry["iconType"] == "iconpark/Charts/positive-dynamics.svg" for entry in results)
        )

    def test_search_icons_supports_english_query(self) -> None:
        results = iconpark_tool.search_icons(self.index_data, {"query": "security protect", "limit": 3})
        self.assertTrue(results)
        self.assertEqual(results[0]["iconType"], "iconpark/Safe/protect.svg")

    def test_search_icons_supports_category_filter(self) -> None:
        results = iconpark_tool.search_icons(
            self.index_data,
            {"query": "data", "category": "Charts", "limit": 10},
        )
        self.assertTrue(results)
        self.assertTrue(all(entry["category"] == "Charts" for entry in results))

    def test_search_icons_does_not_expand_ai_inside_words(self) -> None:
        mail_results = iconpark_tool.search_icons(self.index_data, {"query": "mail", "limit": 5})
        self.assertEqual(mail_results[0]["iconType"], "iconpark/Office/envelope-one.svg")
        self.assertNotEqual(mail_results[0]["iconType"], "iconpark/Others/magic.svg")

        fail_results = iconpark_tool.search_icons(self.index_data, {"query": "fail", "limit": 5})
        self.assertNotEqual(fail_results[0]["iconType"], "iconpark/Others/magic.svg")

    def test_search_icons_supports_template_icon_queries(self) -> None:
        cases = [
            ("arrow", "iconpark/Arrows/arrow-right.svg"),
            ("right", "iconpark/Arrows/right.svg"),
            ("PPT", "iconpark/Music/ppt.svg"),
            ("table", "iconpark/Office/table.svg"),
            ("会议", "iconpark/Office/schedule.svg"),
            ("飞书", "iconpark/Brand/bydesign.svg"),
        ]
        for query, icon_type in cases:
            with self.subTest(query=query):
                results = iconpark_tool.search_icons(self.index_data, {"query": query, "limit": 5})
                self.assertTrue(
                    any(entry["iconType"] == icon_type for entry in results),
                    f"{icon_type} not found in {results}",
                )

    def test_search_icons_defaults_to_wider_candidate_set(self) -> None:
        results = iconpark_tool.search_icons(self.index_data, {"query": "data"})
        self.assertEqual(len(results), 8)

    def test_search_icons_boosts_common_slide_terms(self) -> None:
        results = iconpark_tool.search_icons(self.index_data, {"query": "会议", "limit": 3})
        self.assertTrue(
            any(entry["iconType"] == "iconpark/Office/schedule.svg" for entry in results),
            f"iconpark/Office/schedule.svg not found in {results}",
        )

    def test_search_icons_requires_query(self) -> None:
        with self.assertRaises(iconpark_tool.IconParkToolError):
            iconpark_tool.search_icons(self.index_data, {"limit": 5})

    def test_search_icons_rejects_invalid_limit(self) -> None:
        with self.assertRaises(iconpark_tool.IconParkToolError):
            iconpark_tool.search_icons(self.index_data, {"query": "data", "limit": "abc"})

    def test_resolve_icon_accepts_name_and_icon_type(self) -> None:
        by_name = iconpark_tool.resolve_icon(self.index_data, "chart-line")
        by_type = iconpark_tool.resolve_icon(self.index_data, "iconpark/Charts/chart-line.svg")
        self.assertEqual(by_name["iconType"], "iconpark/Charts/chart-line.svg")
        self.assertEqual(by_name, by_type)

    def test_resolve_icon_accepts_template_icon_type(self) -> None:
        result = iconpark_tool.resolve_icon(self.index_data, "iconpark/Arrows/arrow-right.svg")
        self.assertEqual(result["iconType"], "iconpark/Arrows/arrow-right.svg")

    def test_resolve_icon_rejects_unknown_name(self) -> None:
        with self.assertRaises(iconpark_tool.IconParkToolError):
            iconpark_tool.resolve_icon(self.index_data, "not-a-real-icon")

    def test_list_categories_counts_index(self) -> None:
        categories = iconpark_tool.list_categories(self.index_data)
        self.assertTrue(any(entry["category"] == "Charts" and entry["count"] > 0 for entry in categories))


if __name__ == "__main__":
    unittest.main()
