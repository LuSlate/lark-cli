from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_stage_invalidation as invalidation


class StageInvalidationTest(unittest.TestCase):
    def test_hash_unchanged_does_not_prune(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "02-plan").mkdir(parents=True)
            (root / "receipts").mkdir(parents=True)
            plan = root / "02-plan/slide_plan.json"
            plan.write_text("{}", encoding="utf-8")
            receipt = {
                "schema_version": "svglide-stage-receipt/v1",
                "stage": "plan",
                "status": "passed",
                "inputs": ["02-plan/slide_plan.json"],
                "outputs": [],
                "input_hashes": {"02-plan/slide_plan.json": invalidation.file_sha256(plan)},
                "profile": "preview_only",
                "tool_versions": {"python": "3.x"},
            }
            (root / "receipts/plan.json").write_text(json.dumps(receipt), encoding="utf-8")
            state = {"stages": {"plan": {"status": "passed", "receipt": "receipts/plan.json"}}}
            stale = invalidation.detect_stale_stages(root, state, target_stage="plan", stage_order=["plan"], profile="preview_only")
            self.assertEqual(stale, [])

    def test_hash_change_prunes_stage_and_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "02-plan").mkdir(parents=True)
            (root / "receipts").mkdir(parents=True)
            plan = root / "02-plan/slide_plan.json"
            plan.write_text("{}", encoding="utf-8")
            (root / "receipts/plan.json").write_text(
                json.dumps(
                    {
                        "schema_version": "svglide-stage-receipt/v1",
                        "stage": "plan",
                        "status": "passed",
                        "input_hashes": {"02-plan/slide_plan.json": "stale"},
                        "profile": "preview_only",
                        "tool_versions": {"python": "3.x"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "receipts/preview.json").write_text(
                json.dumps({"schema_version": "svglide-stage-receipt/v1", "stage": "preview", "status": "passed", "profile": "preview_only", "tool_versions": {"python": "3.x"}}),
                encoding="utf-8",
            )
            state = {
                "stages": {
                    "plan": {"status": "passed", "receipt": "receipts/plan.json"},
                    "preview": {"status": "passed", "receipt": "receipts/preview.json"},
                }
            }
            order = ["plan", "generate_svg", "prepare", "preview"]
            stale = invalidation.detect_stale_stages(root, state, target_stage="preview", stage_order=order, profile="preview_only")
            self.assertEqual(stale, ["plan", "preview"])
            invalidation.prune_stale_stage_records(state, stale)
            self.assertNotIn("plan", state["stages"])
            self.assertNotIn("preview", state["stages"])

    def test_profile_change_invalidates_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "receipts").mkdir(parents=True)
            (root / "receipts/quality_gate.json").write_text(
                json.dumps({"schema_version": "svglide-stage-receipt/v1", "stage": "quality_gate", "status": "passed", "profile": "preview_only", "tool_versions": {"python": "3.x"}}),
                encoding="utf-8",
            )
            state = {"stages": {"quality_gate": {"status": "passed", "receipt": "receipts/quality_gate.json"}}}
            stale = invalidation.detect_stale_stages(root, state, target_stage="quality_gate", stage_order=["quality_gate"], profile="local_real_preview")
            self.assertEqual(stale, ["quality_gate"])

    def test_missing_output_invalidates_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "receipts").mkdir(parents=True)
            (root / "receipts/preview.json").write_text(
                json.dumps(
                    {
                        "schema_version": "svglide-stage-receipt/v1",
                        "stage": "preview",
                        "status": "passed",
                        "outputs": ["05-preview/preview.html"],
                        "tool_versions": {"python": "3.x"},
                    }
                ),
                encoding="utf-8",
            )
            state = {"stages": {"preview": {"status": "passed", "receipt": "receipts/preview.json"}}}
            stale = invalidation.detect_stale_stages(root, state, target_stage="preview", stage_order=["preview"], profile="preview_only")
            self.assertEqual(stale, ["preview"])

    def test_unsupported_or_missing_schema_invalidates_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "receipts").mkdir(parents=True)
            state = {"stages": {"plan": {"status": "passed", "receipt": "receipts/plan.json"}}}
            for payload in [
                {"stage": "plan", "status": "passed", "tool_versions": {"python": "3.x"}},
                {"schema_version": "unsupported/v1", "stage": "plan", "status": "passed", "tool_versions": {"python": "3.x"}},
                {"schema_version": "svglide-stage-receipt/v1", "stage": "plan", "status": "passed"},
            ]:
                (root / "receipts/plan.json").write_text(json.dumps(payload), encoding="utf-8")
                stale = invalidation.detect_stale_stages(root, state, target_stage="plan", stage_order=["plan"], profile="preview_only")
                self.assertEqual(stale, ["plan"])


if __name__ == "__main__":
    unittest.main()
