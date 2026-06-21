#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_theme_adherence
import svglide_theme_validate


SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE_ROOT = SCRIPT_DIR / "fixtures" / "svglide_artboard"
EVIDENCE_PATH = SCRIPT_DIR.parent / "references" / "svglide-theme-system-p0-evidence.md"


def copy_fixture(relative: str, tmpdir: str) -> Path:
    source = FIXTURE_ROOT / relative
    target = Path(tmpdir) / relative.replace("/", "-")
    shutil.copytree(source, target)
    return target


def issue_codes(payload: dict[str, object]) -> set[str]:
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return set()
    return {item.get("code") for item in issues if isinstance(item, dict) and isinstance(item.get("code"), str)}


class SVGlideThemeSystemP0FixtureTest(unittest.TestCase):
    def test_evidence_file_exists_and_keeps_p0_scope(self) -> None:
        self.assertTrue(EVIDENCE_PATH.exists(), f"missing evidence file: {EVIDENCE_PATH}")
        text = EVIDENCE_PATH.read_text(encoding="utf-8")
        for required in ["P0-0", "P0-8", "theme_validate", "theme_adherence", "pre_submit_review", "direct_svg"]:
            self.assertIn(required, text)
        for forbidden in ["自动审美已通过", "已支持完整主题系统", "PPTX export 已完成"]:
            self.assertNotIn(forbidden, text)

    def test_positive_artboard_fixture_validates_theme_and_final_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = copy_fixture("theme-system-p0/artboard-satori", tmpdir)

            validation = svglide_theme_validate.validate_project(project)
            svglide_theme_validate.write_outputs(project, validation)
            adherence = svglide_theme_adherence.validate_project(project)

        self.assertEqual(validation["status"], "passed", validation["issues"])
        self.assertEqual(adherence["status"], "passed", adherence["issues"])
        self.assertEqual(adherence["summary"]["prepared_svg_count"], 3)

    def test_positive_direct_svg_fixture_validates_without_canvas_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = copy_fixture("theme-system-p0/direct-svg", tmpdir)

            validation = svglide_theme_validate.validate_project(project)
            svglide_theme_validate.write_outputs(project, validation)
            adherence = svglide_theme_adherence.validate_project(project)

        self.assertEqual(validation["status"], "passed", validation["issues"])
        self.assertEqual(adherence["status"], "passed", adherence["issues"])

    def test_negative_fixtures_fail_for_unknown_color_low_contrast_and_stale_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            unknown = copy_fixture("theme-system-invalid/unknown-color", tmpdir)
            validation = svglide_theme_validate.validate_project(unknown)
            svglide_theme_validate.write_outputs(unknown, validation)
            unknown_result = svglide_theme_adherence.validate_project(unknown)

            low_contrast = copy_fixture("theme-system-invalid/low-contrast", tmpdir)
            validation = svglide_theme_validate.validate_project(low_contrast)
            svglide_theme_validate.write_outputs(low_contrast, validation)
            low_contrast_result = svglide_theme_adherence.validate_project(low_contrast)

            stale = copy_fixture("theme-system-invalid/stale-theme-validate", tmpdir)
            stale_result = svglide_theme_adherence.validate_project(stale)

        self.assertEqual(unknown_result["status"], "failed")
        self.assertIn("theme_unknown_color", issue_codes(unknown_result))
        self.assertEqual(low_contrast_result["status"], "failed")
        self.assertIn("contrast_too_low", issue_codes(low_contrast_result))
        self.assertEqual(stale_result["status"], "failed")
        self.assertIn("theme_validate_plan_stale", issue_codes(stale_result))


if __name__ == "__main__":
    unittest.main()
