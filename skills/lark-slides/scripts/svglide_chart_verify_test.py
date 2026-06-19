# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_chart_verify


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideChartVerifyTest(unittest.TestCase):
    def test_chart_verify_passes_when_no_required_chart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "title": "普通页"}]})
            (project / "04-svg/prepared").mkdir(parents=True)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg><text>普通页</text></svg>", encoding="utf-8")

            result = svglide_chart_verify.run_chart_verify(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["required_chart_count"], 0)

    def test_chart_verify_blocks_required_chart_without_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/slide_plan.json",
                {"slides": [{"page": 1, "title": "图表页", "chart_contract": {"verify": "required"}}]},
            )
            (project / "04-svg/prepared").mkdir(parents=True)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg><text>图表页</text></svg>", encoding="utf-8")

            result = svglide_chart_verify.run_chart_verify(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("chart_contract_data_missing", codes)
            self.assertIn("chart_marks_missing", codes)


if __name__ == "__main__":
    unittest.main()
