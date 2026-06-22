from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_plan_bundle_review as review


class PlanBundleReviewTest(unittest.TestCase):
    def write_project(self, root: Path, *, pages: int = 10, baseline: bool = False, local_asset: bool = False) -> None:
        (root / "00-input").mkdir(parents=True)
        (root / "02-plan").mkdir(parents=True)
        (root / "source").mkdir(parents=True)
        (root / "00-input/instruction.json").write_text(json.dumps({"version": "svglide-instruction/v1", "raw_prompt": "智谱和 MiniMax"}), encoding="utf-8")
        palette = {
            "project_palette": {
                "palette_id": "cobalt",
                "source": "fixture",
                "confidence": "high",
                "colors": {
                    "background": "#ffffff",
                    "surface": "#f8fafc",
                    "text": "#0f172a",
                    "muted": "#475569",
                    "primary": "#2563eb",
                    "accent": "#ef4444",
                },
            }
        }
        (root / "02-plan/palette-selection.json").write_text(json.dumps(palette), encoding="utf-8")
        (root / "02-plan/theme-template-selection.json").write_text(
            json.dumps(
                {
                    "selected_template_id": "executive-dashboard",
                    "selected_theme_id": "cobalt-grid",
                    "template_candidates": [{"template_id": "executive-dashboard"}],
                    "theme_candidates": [{"theme_id": "cobalt-grid"}],
                }
            ),
            encoding="utf-8",
        )
        (root / "source/evidence.json").write_text(
            json.dumps({"items": [{"id": f"item-{i:03d}", "text": "evidence"} for i in range(1, 12)]}),
            encoding="utf-8",
        )
        slides = []
        for i in range(1, pages + 1):
            asset_contract = {
                "asset_id": f"asset-{i}",
                "asset_kind": "photo",
                "source_url": "https://example.com/image.png",
                "placement_role": "evidence",
            }
            if local_asset and i == 1:
                asset_contract["source_url"] = "file:///tmp/local.png"
                asset_contract["asset_kind"] = "generated_image"
            slides.append(
                {
                    "page": i,
                    "title": f"Page {i}",
                    "body_points": ["a", "b", "c"],
                    "source_refs": [f"source:item-{i:03d}", "source:item-001"],
                    "visual_recipe": "chart dashboard" if i == 3 else "text-stat",
                    "asset_contract": asset_contract,
                    "canvas_spec": {
                        "template_id": "baseline" if baseline and i == 1 else "executive-dashboard",
                        "theme_id": "cobalt-grid",
                        "selection_trace": {"template_candidate_rank": 1},
                    },
                }
            )
        plan = {
            "generation_mode": "artboard_satori",
            "project_palette": palette["project_palette"],
            "project_theme": {
                "base_theme_id": "cobalt-grid",
                "token_overrides": {
                    "color.background": "#ffffff",
                    "color.surface": "#f8fafc",
                    "color.text": "#0f172a",
                    "color.muted": "#475569",
                    "color.primary": "#2563eb",
                    "color.accent": "#ef4444",
                },
            },
            "slides": slides,
        }
        (root / "02-plan/slide_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def test_passes_complete_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_project(root)
            result = review.run_plan_bundle_review(root, profile="local_real_preview")
            self.assertEqual(result["status"], "passed")
            self.assertTrue((root / "06-check/plan-bundle-review.json").exists())
            self.assertTrue((root / "receipts/plan_bundle_review.json").exists())

    def test_blocks_generation_contract_issues_before_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_project(root, pages=4, baseline=True, local_asset=True)
            result = review.run_plan_bundle_review(root, profile="local_real_preview")
            codes = {item["code"] for item in result["issues"]}
            self.assertEqual(result["status"], "failed")
            self.assertIn("page_count_too_low", codes)
            self.assertIn("baseline_theme_template_forbidden", codes)
            self.assertIn("local_generated_image_forbidden", codes)


if __name__ == "__main__":
    unittest.main()
