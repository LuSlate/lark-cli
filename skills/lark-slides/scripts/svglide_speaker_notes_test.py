# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_speaker_notes


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideSpeakerNotesTest(unittest.TestCase):
    def test_speaker_notes_split_total_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}, {"page": 2}]})
            (project / "notes").mkdir(parents=True)
            (project / "notes/total.md").write_text("第一页讲稿\n---\n第二页讲稿\n", encoding="utf-8")

            result = svglide_speaker_notes.run_speaker_notes(project)

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project / "notes/page-001.md").exists())
            self.assertTrue((project / "notes/page-002.md").exists())

    def test_speaker_notes_blocks_page_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1}, {"page": 2}]})
            (project / "notes").mkdir(parents=True)
            (project / "notes/total.md").write_text("只有一页讲稿\n", encoding="utf-8")

            result = svglide_speaker_notes.run_speaker_notes(project)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["issues"][0]["code"], "notes_page_count_mismatch")


if __name__ == "__main__":
    unittest.main()
