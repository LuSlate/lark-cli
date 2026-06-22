from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_generation_benchmark as benchmark


class GenerationBenchmarkTest(unittest.TestCase):
    def write_plan(self, root: Path) -> None:
        (root / "02-plan").mkdir(parents=True)
        (root / "02-plan/slide_plan.json").write_text(
            json.dumps(
                {
                    "project_palette": {
                        "colors": {
                            "background": "#101827",
                            "surface": "#17233a",
                            "text": "#f8fafc",
                            "muted": "#94a3b8",
                            "primary": "#60a5fa",
                            "accent": "#fbbf24",
                        }
                    },
                    "project_theme": {
                        "base_theme_id": "cobalt-grid",
                        "token_overrides": {
                            "color.background": "#101827",
                            "color.primary": "#60a5fa",
                        },
                    },
                    "slides": [
                        {"page": i, "title": f"Page {i}", "renderer_id": "executive-dashboard" if i == 2 else "content-stat"}
                        for i in range(1, 11)
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_cache_key_is_versioned(self) -> None:
        key = benchmark.cache_key("内部业务复盘", profile="local_real_preview", template_library_version="sha256:a", asset_policy_version="sha256:b")
        self.assertEqual(key["profile"], "local_real_preview")
        self.assertTrue(key["prompt_semantic_hash"].startswith("sha256:"))
        self.assertEqual(key["template_library_version"], "sha256:a")

    def test_benchmark_writes_cache_and_reports_second_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_plan(root)
            (root / "06-check").mkdir(parents=True)
            (root / "03-assets").mkdir(parents=True)
            (root / "03-assets/asset-manifest.json").write_text(
                json.dumps({"summary": {"asset_acquired_count": 4, "asset_fallback_count": 0}}),
                encoding="utf-8",
            )
            (root / "06-check/quality-gate.json").write_text(
                json.dumps({"summary": {"asset_real_coverage": 4, "asset_fallback_count": 0}}),
                encoding="utf-8",
            )
            (root / "06-check/timing-report.json").write_text(
                json.dumps({"schema_version": "svglide-timing-report/v1"}),
                encoding="utf-8",
            )
            first = benchmark.run_benchmark(root, profile="local_real_preview")
            second = benchmark.run_benchmark(root, profile="local_real_preview")
            self.assertEqual(first["cache"]["hit_count"], 0)
            self.assertGreater(second["cache"]["hit_count"], 0)
            self.assertEqual(len(second["quality"]), 4)
            self.assertTrue(all(item["status"] == "passed" for item in second["quality"]))
            self.assertTrue(all("palette_consistency_ok" in item["checks"] for item in second["quality"]))
            timing = json.loads((root / "06-check/timing-report.json").read_text(encoding="utf-8"))
            self.assertEqual(timing["cache"]["hit_count"], 12)
            self.assertTrue((root / "06-check/generation-benchmark.json").exists())


if __name__ == "__main__":
    unittest.main()
