#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_brand_palette_resolver as resolver


class BrandPaletteResolverTest(unittest.TestCase):
    def test_user_provided_hex_takes_precedence(self) -> None:
        result = resolver.resolve_user_provided_palette("用 #76B900 和 #111111 做一份 NVIDIA 复盘")

        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "user_provided")
        self.assertEqual(result["colors"]["primary"], "#76B900")

    def test_extracts_zhipu_and_minimax_entities(self) -> None:
        entities = resolver.extract_brand_entities("生成一份主题为智谱和 MiniMax 的 slide")

        self.assertEqual(["zhipu", "minimax"], [item["brand_id"] for item in entities])

    def test_registry_resolution_records_evidence_and_confidence(self) -> None:
        entities = resolver.extract_brand_entities("NVIDIA 与 AMD 生态对比")
        registry = resolver.load_brand_registry()

        results = resolver.resolve_brand_registry_palette(entities, registry)

        self.assertEqual(["nvidia", "amd"], [item["brand_id"] for item in results])
        self.assertEqual("brand_registry", results[0]["source"])
        self.assertTrue(results[0]["evidence"])

    def test_unknown_brand_uses_stable_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = resolver.resolve_brand_palette(Path(tmpdir), "未知品牌 AlphaOmega 内部复盘")
            second = resolver.resolve_brand_palette(Path(tmpdir), "未知品牌 AlphaOmega 内部复盘")

        self.assertEqual("stable_fallback", first["source"])
        self.assertEqual(first["fallback_seed"], second["fallback_seed"])


if __name__ == "__main__":
    unittest.main()
