# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_preview_annotations


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlidePreviewAnnotationsTest(unittest.TestCase):
    def test_preview_annotations_write_repair_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "05-preview/preview-annotations.json",
                {
                    "schema_version": "svglide-preview-annotations/v1",
                    "annotations": [
                        {"page": 1, "severity": "warning", "message": "标题太挤", "status": "open"},
                        {"page": 2, "severity": "info", "message": "仅备注", "status": "open"},
                        {"page": 3, "severity": "error", "message": "文本重叠", "status": "resolved"},
                    ],
                },
            )

            result = svglide_preview_annotations.run_preview_annotations(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["open_repair_count"], 1)
            repair = json.loads((project / "06-check/preview-repair-list.json").read_text(encoding="utf-8"))
            self.assertEqual(len(repair["items"]), 1)


if __name__ == "__main__":
    unittest.main()
