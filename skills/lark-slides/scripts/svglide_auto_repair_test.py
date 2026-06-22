from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_auto_repair as repair


class AutoRepairTest(unittest.TestCase):
    def test_repairs_deterministic_plan_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01-project").mkdir(parents=True)
            (root / "02-plan").mkdir(parents=True)
            (root / "03-assets").mkdir(parents=True)
            (root / "01-project/project_manifest.json").write_text(json.dumps({"title": "内部业务复盘"}), encoding="utf-8")
            palette = {
                "project_palette": {
                    "palette_id": "blue",
                    "source": "fixture",
                    "confidence": "high",
                    "colors": {
                        "background": "#ffffff",
                        "surface": "#f8fafc",
                        "text": "#0f172a",
                        "muted": "#64748b",
                        "primary": "#2563eb",
                        "accent": "#ef4444",
                    },
                }
            }
            (root / "02-plan/palette-selection.json").write_text(json.dumps(palette), encoding="utf-8")
            (root / "02-plan/slide_plan.json").write_text(
                json.dumps({"slides": [{"asset_contract": "hero-image"}]}),
                encoding="utf-8",
            )
            (root / "03-assets/asset-manifest.json").write_text(
                json.dumps(
                    {
                        "contracts": [
                            {
                                "asset_id": "hero-image",
                                "source_url": "https://example.com/hero.jpg",
                                "file": "03-assets/raw/hero.jpg",
                                "asset_kind": "web_image",
                                "placement_role": "cover",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = repair.run_auto_repair(root)
            self.assertEqual(result["status"], "patched")
            plan = json.loads((root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["project_palette"]["palette_id"], "blue")
            self.assertEqual(plan["project_theme"]["token_overrides"]["color.primary"], "#2563eb")
            self.assertEqual(plan["slides"][0]["asset_contract"]["asset_id"], "hero-image")
            self.assertEqual(plan["slides"][0]["asset_contract"]["source_url"], "https://example.com/hero.jpg")
            self.assertTrue((root / "00-input/instruction.json").exists())

    def test_chart_rich_thin_is_suggestion_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-input").mkdir(parents=True)
            (root / "06-check").mkdir(parents=True)
            (root / "00-input/instruction.json").write_text(json.dumps({"raw_prompt": "x"}), encoding="utf-8")
            (root / "06-check/plan-bundle-review.json").write_text(
                json.dumps({"issues": [{"code": "chart_rich_content_too_thin"}]}),
                encoding="utf-8",
            )
            result = repair.run_auto_repair(root)
            suggestions = result["suggestions"]
            self.assertEqual(suggestions[0]["repairability"], "suggestion_only")
            self.assertEqual(result["status"], "noop")

    def test_repairs_minor_text_overflow_by_increasing_text_box_height(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00-input").mkdir(parents=True)
            (root / "04-svg/prepared").mkdir(parents=True)
            (root / "05-preview").mkdir(parents=True)
            (root / "06-check").mkdir(parents=True)
            (root / "00-input/instruction.json").write_text(json.dumps({"raw_prompt": "x"}), encoding="utf-8")
            svg = '<svg><foreignObject x="10" y="20" width="120" height="24"><div>很长的文字</div></foreignObject></svg>'
            (root / "04-svg/prepared/page-001.svg").write_text(svg, encoding="utf-8")
            (root / "05-preview/preview.html").write_text(svg, encoding="utf-8")
            (root / "06-check/preview-lint.json").write_text(
                json.dumps(
                    {
                        "page_issues": [
                            {
                                "code": "preview_text_overflow_risk",
                                "page": 1,
                                "box": {"x": 10, "y": 20, "width": 120, "height": 24},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = repair.run_auto_repair(root)

            self.assertEqual(result["status"], "patched")
            updated = (root / "04-svg/prepared/page-001.svg").read_text(encoding="utf-8")
            self.assertIn('height="38"', updated)
            self.assertTrue(any(item["operation"] == "increase_foreign_object_height_from_preview_lint" for item in result["patches"]))


if __name__ == "__main__":
    unittest.main()
