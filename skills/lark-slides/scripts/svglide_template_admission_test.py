# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_template_admission


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideTemplateAdmissionTest(unittest.TestCase):
    def test_template_admission_passes_active_native_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "source/template-admission.json",
                {
                    "schema_version": "svglide-template-admission/v1",
                    "items": [
                        {
                            "id": "seed-title",
                            "source": "svglide/seeds/title.json",
                            "kind": "seed",
                            "activation_status": "active",
                            "copy_policy": "svglide_native",
                            "license_status": "cleared",
                            "compatibility": {"canvas": "960x540"},
                            "usage_proof": {"fixture": "golden/title"},
                            "unsupported_features": [],
                        }
                    ],
                },
            )

            result = svglide_template_admission.run_template_admission(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["active_count"], 1)

    def test_template_admission_blocks_raw_active_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "source/template-admission.json",
                {
                    "schema_version": "svglide-template-admission/v1",
                    "items": [
                        {
                            "id": "raw-pptx",
                            "source": "ppt-master/templates/raw.pptx",
                            "kind": "template",
                            "activation_status": "active",
                            "copy_policy": "blocked_raw_runtime",
                            "license_status": "unknown",
                            "compatibility": {},
                            "usage_proof": {},
                            "unsupported_features": ["pptx"],
                        }
                    ],
                },
            )

            result = svglide_template_admission.run_template_admission(project)

            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("active_template_raw_runtime_source", codes)
            self.assertIn("active_template_copy_policy_invalid", codes)
            self.assertIn("active_template_compatibility_missing", codes)


if __name__ == "__main__":
    unittest.main()
