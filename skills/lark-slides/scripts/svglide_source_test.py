# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_source


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideSourceTest(unittest.TestCase):
    def test_source_passes_ready_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "source/evidence.json",
                {
                    "schema_version": "svglide-evidence/v1",
                    "source_status": "ready",
                    "items": [
                        {"id": "item-001", "text": "第一条中文证据内容足够长，用于支撑页面。"},
                        {"id": "item-002", "text": "第二条中文证据内容足够长，用于验证闭环。"},
                        {"id": "item-003", "text": "第三条中文证据内容足够长，用于避免资料过薄。"},
                    ],
                },
            )

            result = svglide_source.run_source(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["error_count"], 0)
            self.assertTrue((project / "source/source-receipt.json").exists())

    def test_source_blocks_thin_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "source").mkdir(parents=True)
            (project / "source/source-notes.md").write_text("- 太薄\n", encoding="utf-8")

            result = svglide_source.run_source(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("source_status_not_ready", codes)
            self.assertTrue((project / "source/evidence.json").exists())

    def test_fixture_policy_generates_ready_evidence_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)

            result = svglide_source.run_source(project, network_policy="fixture")

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["research"]["status"], "fixture")
            self.assertTrue((project / "source/research_queries.json").exists())
            self.assertTrue((project / "source/research.md").exists())
            evidence = json.loads((project / "source/evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["source_status"], "ready")


if __name__ == "__main__":
    unittest.main()
