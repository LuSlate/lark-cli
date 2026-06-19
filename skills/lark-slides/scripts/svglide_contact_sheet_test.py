# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_contact_sheet


class SVGlideContactSheetTest(unittest.TestCase):
    def test_contact_sheet_writes_html_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "04-svg/prepared").mkdir(parents=True)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            result = svglide_contact_sheet.run_contact_sheet(project)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project / "05-preview/contact-sheet.html").exists())
            self.assertTrue((project / "05-preview/contact-sheet.json").exists())


if __name__ == "__main__":
    unittest.main()
