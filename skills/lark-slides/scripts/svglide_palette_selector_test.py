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

import svglide_palette_selector as selector


class PaletteSelectorTest(unittest.TestCase):
    def test_ai_brand_brief_uses_brand_resolution_and_outputs_project_palette(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = selector.select_palette(Path(tmpdir), "生成一份主题为智谱和 MiniMax 的 slide", top_k=5)

        self.assertEqual("brand_registry", result["brand_resolution"]["source"])
        self.assertEqual(["zhipu", "minimax"], result["brand_resolution"]["brands"])
        self.assertEqual("brand.zhipu", result["selected_palette_id"])
        self.assertEqual(result["project_palette"]["colors"]["primary"], "#315CFF")
        self.assertEqual(result["project_palette"]["colors"]["accent"], "#06B6D4")

    def test_user_provided_palette_wins_over_brand_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = selector.select_palette(Path(tmpdir), "NVIDIA 复盘，主色 #123456，强调色 #ABCDEF", top_k=3)

        self.assertEqual("user_provided", result["brand_resolution"]["source"])
        self.assertEqual("#123456", result["project_palette"]["colors"]["primary"])
        self.assertEqual("#ABCDEF", result["project_palette"]["colors"]["accent"])

    def test_unknown_topic_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = selector.select_palette(root, "一个不存在于模板库的主题：量子陶瓷供应链", top_k=5)
            second = selector.select_palette(root, "一个不存在于模板库的主题：量子陶瓷供应链", top_k=5)

        self.assertEqual(first["selected_palette_id"], second["selected_palette_id"])
        self.assertEqual(first["deterministic_seed"], second["deterministic_seed"])

    def test_write_palette_selection_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = selector.select_palette(root, "内部业务复盘", top_k=3)
            output = selector.write_palette_selection(root, result)

            written = json.loads(output.read_text(encoding="utf-8"))
            receipt = json.loads((root / "receipts/palette_selection.json").read_text(encoding="utf-8"))

        self.assertEqual(written["schema_version"], "svglide-palette-selection/v1")
        self.assertEqual(receipt["selected_palette_id"], written["selected_palette_id"])


if __name__ == "__main__":
    unittest.main()
