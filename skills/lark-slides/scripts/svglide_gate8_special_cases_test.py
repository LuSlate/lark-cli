# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_gate8_special_cases


class SVGlideGate8SpecialCasesTest(unittest.TestCase):
    def test_gate8_special_cases_all_pass_and_write_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "gate8"

            result = svglide_gate8_special_cases.run_gate8(root)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["summary"]["case_count"], 4)
            cases = {case["name"]: case for case in result["cases"]}
            self.assertEqual(cases["unsupported_feature_fail_fast"]["status"], "passed")
            self.assertTrue(cases["unsupported_feature_fail_fast"]["render_failed_before_live"])
            self.assertTrue(cases["unsupported_feature_fail_fast"]["bridge_failed_before_live"])
            self.assertEqual(cases["chart_marker_svglide_chart_spec_v1"]["chart_verify_status"], "passed")
            self.assertEqual(cases["chart_marker_svglide_chart_spec_v1"]["readback_chart_markers"]["status"], "passed")
            self.assertEqual(cases["image_asset_binding_readback"]["readback_asset_tokens"]["status"], "passed")
            self.assertEqual(cases["image_asset_binding_readback"]["readback_image_assets"]["status"], "passed")
            self.assertEqual(cases["local_raster_fallback_island"]["raster_fallback"]["status"], "passed")

            evidence = json.loads((root / "gate8-special-cases.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "passed")
            self.assertTrue((root / "chart-marker/06-check/chart-verify.json").exists())
            self.assertTrue((root / "image-asset/08-readback/readback-check.json").exists())
            self.assertTrue((root / "raster-fallback/06-check/raster-fallback.json").exists())


if __name__ == "__main__":
    unittest.main()
