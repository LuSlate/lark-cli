# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_semantic_advisory


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideSemanticAdvisoryTest(unittest.TestCase):
    def test_advisory_warns_but_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/slide_plan.json",
                {
                    "slides": [
                        {
                            "page": 1,
                            "page_type": "content",
                            "title": "增长",
                            "key_message": "增长",
                            "body_points": ["高", "快"],
                        }
                    ]
                },
            )

            result = svglide_semantic_advisory.run_advisory(project)

            self.assertEqual(result["status"], "passed")
            self.assertGreater(result["summary"]["warning_count"], 0)


if __name__ == "__main__":
    unittest.main()
