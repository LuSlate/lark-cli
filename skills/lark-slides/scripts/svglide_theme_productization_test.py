# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_theme_productization as productization
import svglide_theme_validate


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class SVGlideThemeProductizationTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(
            project / "02-plan/slide_plan.json",
            {
                "generation_mode": "artboard_satori",
                "theme_id": "dark-clarity",
                "slides": [
                    {
                        "page": 1,
                        "title": "Theme Migration",
                        "theme_id": "dark-clarity",
                        "canvas_spec": {"template_id": "cover-hero", "theme_id": "dark-clarity"},
                    }
                ],
            },
        )
        write_json(
            project / productization.INPUT_PATH,
            {
                "theme_id": "acme-signal",
                "brand": {"name": "ACME Signal"},
                "provider": {"type": "deterministic_rules"},
                "palette": {
                    "background": "#FFFFFF",
                    "surface": "#F4F7FB",
                    "text": "#102033",
                    "muted": "#667085",
                    "primary": "#1363DF",
                    "accent": "#F04438",
                },
                "template_binding": {"supported_template_ids": ["cover-hero"]},
                "migration": {"output_plan": "02-plan/slide_plan.acme.json"},
            },
        )
        return project

    def test_theme_productization_extracts_registry_and_migrates_plan(self) -> None:
        project = self.make_project()

        result = productization.run_theme_productization(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["theme"]["theme_id"], "acme-signal")
        self.assertTrue((project / "02-plan/themes/acme-signal.json").exists())
        self.assertTrue((project / "02-plan/theme-registry.json").exists())
        self.assertTrue((project / "02-plan/slide_plan.acme.json").exists())
        self.assertTrue((project / "02-plan/theme-migration.patch.json").exists())
        self.assertEqual(result["migration"]["operation_count"], 3)
        migrated = json.loads((project / "02-plan/slide_plan.acme.json").read_text(encoding="utf-8"))
        self.assertEqual(migrated["theme_id"], "acme-signal")
        self.assertEqual(migrated["slides"][0]["canvas_spec"]["theme_id"], "acme-signal")
        registry = json.loads((project / "02-plan/theme-registry.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["themes"][0]["template_bindings"]["supported_template_ids"], ["cover-hero"])

    def test_theme_validate_accepts_productized_project_theme_binding(self) -> None:
        project = self.make_project()
        productization.run_theme_productization(project)
        migrated = json.loads((project / "02-plan/slide_plan.acme.json").read_text(encoding="utf-8"))
        write_json(project / "02-plan/slide_plan.json", migrated)

        result = svglide_theme_validate.validate_project(project)

        self.assertEqual(result["status"], "passed", result["issues"])
        self.assertEqual(result["inputs"]["theme_registry"], "02-plan/theme-registry.json")
        self.assertEqual(result["pages"][0]["theme_id"], "acme-signal")

    def test_theme_productization_rejects_invalid_palette(self) -> None:
        project = self.make_project()
        request = json.loads((project / productization.INPUT_PATH).read_text(encoding="utf-8"))
        request["palette"]["primary"] = "#12GGGG"
        write_json(project / productization.INPUT_PATH, request)

        with self.assertRaises(productization.ThemeProductizationError):
            productization.run_theme_productization(project)


if __name__ == "__main__":
    unittest.main()
