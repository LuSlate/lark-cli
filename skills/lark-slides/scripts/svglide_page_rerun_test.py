# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_page_rerun


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlidePageRerunTest(unittest.TestCase):
    def test_page_rerun_marks_dirty_pages_against_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "04-svg/prepared").mkdir(parents=True)
            page = project / "04-svg/prepared/page-001.svg"
            page.write_text("<svg></svg>", encoding="utf-8")
            current = svglide_page_rerun.current_prepared(project)
            write_json(project / "06-check/quality-gate.json", {"prepared_files": current})
            page.write_text("<svg><rect /></svg>", encoding="utf-8")

            result = svglide_page_rerun.run_page_rerun(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["dirty_page_count"], 1)
            self.assertEqual(result["pages"][0]["status"], "dirty")


if __name__ == "__main__":
    unittest.main()
