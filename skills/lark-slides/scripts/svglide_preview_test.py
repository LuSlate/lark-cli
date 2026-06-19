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

import svglide_preview


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SVGlidePreviewTest(unittest.TestCase):
    def test_build_preview_inlines_prepared_svgs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write(
                project / "04-svg/prepared/002.svg",
                '<svg width="960" height="540" viewBox="0 0 960 540"><text>Second</text></svg>',
            )
            write(
                project / "04-svg/prepared/001.svg",
                '<?xml version="1.0" encoding="UTF-8"?><svg width="960" height="540" viewBox="0 0 960 540"><text>First</text></svg>',
            )

            manifest = svglide_preview.build_preview(project)

            html_path = project / "05-preview/preview.html"
            manifest_path = project / "05-preview/preview-manifest.json"
            self.assertTrue(html_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest["page_count"], 2)
            self.assertEqual(
                [page["source_path"] for page in manifest["pages"]],
                ["04-svg/prepared/001.svg", "04-svg/prepared/002.svg"],
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn("<svg", html)
            self.assertIn("Page 1 of 2", html)
            self.assertIn("Source path: 04-svg/prepared/001.svg", html)
            self.assertIn('href="#page-2"', html)
            self.assertNotIn("<?xml", html)

            saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["page_count"], 2)

    def test_build_preview_fails_without_prepared_svgs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(svglide_preview.SVGlidePreviewError):
                svglide_preview.build_preview(Path(tmpdir))


if __name__ == "__main__":
    unittest.main()
