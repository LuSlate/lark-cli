# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import beautiful_template_fidelity_check as fidelity
import svglide_schema


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "beautiful-template-fidelity.schema.json"


def write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in range(height):
        start = y * width
        rows.append(b"\x00" + b"".join(bytes(pixel) for pixel in pixels[start : start + width]))
    raw = b"".join(rows)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def template_reference_pixels(width: int = 96, height: int = 54) -> list[tuple[int, int, int]]:
    pixels: list[tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if x < 42:
                pixels.append((15, 23, 42))
            elif 10 <= y <= 18 and 48 <= x <= 88:
                pixels.append((248, 250, 252))
            elif 48 <= x <= 88 and 24 <= y <= 44:
                pixels.append((56, 189, 248))
            else:
                pixels.append((226, 232, 240))
    return pixels


def generic_card_pixels(width: int = 96, height: int = 54) -> list[tuple[int, int, int]]:
    pixels: list[tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            in_card = (
                (10 <= x <= 30 and 14 <= y <= 34)
                or (38 <= x <= 58 and 14 <= y <= 34)
                or (66 <= x <= 86 and 14 <= y <= 34)
            )
            pixels.append((255, 255, 255) if in_card else (241, 245, 249))
    return pixels


def scale_2x(pixels: list[tuple[int, int, int]], width: int = 96, height: int = 54) -> list[tuple[int, int, int]]:
    scaled: list[tuple[int, int, int]] = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        doubled_row = [pixel for pixel in row for _ in range(2)]
        scaled.extend(doubled_row)
        scaled.extend(doubled_row)
    return scaled


class BeautifulTemplateFidelityCheckTest(unittest.TestCase):
    def test_default_profile_declares_thresholds_weights_viewport_and_normalization(self) -> None:
        profile = fidelity.default_profile()

        self.assertGreaterEqual(profile["thresholds"]["overall_min"], 0.7)
        self.assertEqual(profile["viewport"], {"width": 960, "height": 540, "device_scale_factor": 1})
        self.assertEqual(profile["normalization"]["target_size"], {"width": 96, "height": 54})
        self.assertEqual(sum(profile["weights"].values()), 1.0)
        for key in ["color_distribution", "layout_structure", "edge_density", "whitespace", "dominant_region"]:
            self.assertIn(key, profile["weights"])

    def test_reference_screenshot_selection_prefers_page_type_then_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exact = root / "cover-hero" / "cover.png"
            default = root / "cover-hero" / "default.png"
            write_png(exact, 96, 54, template_reference_pixels())
            write_png(default, 96, 54, generic_card_pixels())

            selection = fidelity.select_reference_screenshot(root, template_id="cover-hero", page_type="cover")

            self.assertEqual(selection["path"], exact)
            self.assertEqual(selection["rule"], "template_page_type")

            exact.unlink()
            fallback = fidelity.select_reference_screenshot(root, template_id="cover-hero", page_type="cover")

            self.assertEqual(fallback["path"], default)
            self.assertEqual(fallback["rule"], "template_default")

    def test_blank_render_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.png"
            render = root / "render.png"
            write_png(reference, 96, 54, template_reference_pixels())
            write_png(render, 96, 54, [(255, 255, 255)] * (96 * 54))

            result = fidelity.check_template_fidelity(reference_screenshot=reference, render_screenshot=render, template_id="cover-hero")

        self.assertEqual(result["status"], "failed")
        self.assertIn("render_blank", {issue["code"] for issue in result["issues"]})
        self.assertIn("score", result)

    def test_generic_cards_fail_even_when_non_blank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.png"
            render = root / "render.png"
            write_png(reference, 96, 54, template_reference_pixels())
            write_png(render, 96, 54, generic_card_pixels())

            result = fidelity.check_template_fidelity(reference_screenshot=reference, render_screenshot=render, template_id="cover-hero")

        self.assertEqual(result["status"], "failed")
        self.assertIn("generic_card_layout", {issue["code"] for issue in result["issues"]})

    def test_reference_screenshot_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = root / "render.png"
            write_png(render, 96, 54, template_reference_pixels())

            result = fidelity.check_template_fidelity(reference_screenshot=root / "missing-reference.png", render_screenshot=render, template_id="cover-hero")

        self.assertEqual(result["status"], "failed")
        self.assertIn("reference_missing", {issue["code"] for issue in result["issues"]})
        self.assertEqual(result["reference_screenshot"], str(root / "missing-reference.png"))

    def test_low_structural_similarity_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.png"
            render = root / "render.png"
            write_png(reference, 96, 54, template_reference_pixels())
            write_png(render, 96, 54, list(reversed(template_reference_pixels())))

            result = fidelity.check_template_fidelity(reference_screenshot=reference, render_screenshot=render, template_id="cover-hero", min_score=0.82)

        self.assertEqual(result["status"], "failed")
        self.assertIn("structure_similarity_below_threshold", {issue["code"] for issue in result["issues"]})
        self.assertLess(result["score"], result["threshold"])

    def test_passed_receipt_matches_schema_and_records_selection_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference_root = root / "references"
            reference = reference_root / "cover-hero" / "cover.png"
            render = root / "render.png"
            write_png(reference, 96, 54, template_reference_pixels())
            write_png(render, 96, 54, template_reference_pixels())

            result = fidelity.check_template_fidelity(
                render_screenshot=render,
                template_id="cover-hero",
                page_type="cover",
                reference_root=reference_root,
            )

        schema = svglide_schema.read_json(SCHEMA_PATH)
        schema_issues = svglide_schema.validate_json_schema(result, schema)
        self.assertEqual(schema_issues, [])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["reference_selection"]["rule"], "template_page_type")
        self.assertGreaterEqual(result["score"], result["threshold"])

    def test_normalizes_different_viewport_sizes_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.png"
            render = root / "render.png"
            write_png(reference, 192, 108, scale_2x(template_reference_pixels()))
            write_png(render, 96, 54, template_reference_pixels())

            result = fidelity.check_template_fidelity(reference_screenshot=reference, render_screenshot=render, template_id="cover-hero")

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertGreaterEqual(result["score"], result["threshold"])


if __name__ == "__main__":
    unittest.main()
