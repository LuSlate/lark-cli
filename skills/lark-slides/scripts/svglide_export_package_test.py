# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_export_package as export_package


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class SVGlideExportPackageTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(project / "02-plan/slide_plan.json", {"slides": [{"page": 1, "title": "Demo"}]})
        (project / "04-svg/prepared").mkdir(parents=True, exist_ok=True)
        (project / "04-svg/prepared/page-001.svg").write_text("<svg><text>Demo</text></svg>", encoding="utf-8")
        prepared_files = export_package.prepared_file_hashes(project)
        write_json(
            project / "06-check/quality-gate.json",
            {"status": "passed", "prepared_files": prepared_files, "checks": [{"name": "quality", "status": "passed"}]},
        )
        write_json(project / "07-create/live-create.json", {"status": "passed", "prepared_files": prepared_files, "json": {"xml_presentation_id": "xml_1"}})
        write_json(
            project / "08-readback/readback-check.json",
            {
                "version": "svglide-readback/v1",
                "status": "passed",
                "input_binding": {
                    "plan_sha256": export_package.file_sha256(project / "02-plan/slide_plan.json"),
                    "quality_gate_sha256": export_package.file_sha256(project / "06-check/quality-gate.json"),
                    "live_create_sha256": export_package.file_sha256(project / "07-create/live-create.json"),
                },
            },
        )
        return project

    def test_export_package_writes_manifest_archive_and_receipt(self) -> None:
        project = self.make_project()

        result = export_package.run_export_package(project, archive=True)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["action"], "handoff_package")
        self.assertTrue((project / export_package.EXPORT_MANIFEST).exists())
        self.assertTrue((project / export_package.EXPORT_RECEIPT).exists())
        self.assertTrue((project / export_package.EXPORT_ARCHIVE).exists())
        self.assertEqual(result["formats"]["svglide_artifact_package"]["status"], "passed")
        self.assertEqual(result["formats"]["pptx"]["status"], "not_implemented")
        artifact_paths = {item["path"] for item in result["artifacts"]}
        self.assertIn("02-plan/slide_plan.json", artifact_paths)
        self.assertIn("04-svg/prepared/page-001.svg", artifact_paths)

    def test_export_package_blocks_stale_readback_binding(self) -> None:
        project = self.make_project()
        write_json(project / "06-check/quality-gate.json", {"status": "passed", "prepared_files": export_package.prepared_file_hashes(project), "changed": True})

        result = export_package.run_export_package(project)

        self.assertEqual(result["status"], "failed")
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("readback_input_binding_stale", codes)


if __name__ == "__main__":
    unittest.main()
