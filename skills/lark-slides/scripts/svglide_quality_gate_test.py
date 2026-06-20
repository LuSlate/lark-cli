#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_quality_gate


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_passing_semantic_review(project: Path) -> None:
    (project / "02-plan").mkdir(parents=True, exist_ok=True)
    (project / "source").mkdir(parents=True, exist_ok=True)
    (project / "03-assets").mkdir(parents=True, exist_ok=True)
    (project / "04-svg").mkdir(parents=True, exist_ok=True)
    (project / "04-svg/prepared").mkdir(parents=True, exist_ok=True)
    if not (project / "02-plan/slide_plan.json").exists():
        write_json(project / "02-plan/slide_plan.json", {"language": "zh-CN", "slides": []})
    if not (project / "source/evidence.json").exists():
        write_json(project / "source/evidence.json", {"schema_version": "svglide-evidence/v1", "source_status": "ready", "items": [{"id": "item-001", "text": "这是一条足够长的中文证据内容，用于质量门禁测试。"}]})
    if not (project / "source/source-receipt.json").exists():
        write_json(
            project / "source/source-receipt.json",
            {
                "schema_version": "svglide-source-receipt/v1",
                "stage": "source",
                "status": "passed",
                "inputs": {"evidence_sha256": svglide_quality_gate.file_sha256(project / "source/evidence.json"), "source_notes_sha256": None},
                "outputs": {"evidence": "source/evidence.json", "source_receipt": "source/source-receipt.json"},
                "summary": {"error_count": 0, "evidence_item_count": 1},
                "issues": [],
            },
        )
    if not (project / "03-assets/asset-manifest.json").exists():
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "source_receipt_sha256": svglide_quality_gate.file_sha256(project / "source/source-receipt.json"),
                "summary": {"error_count": 0},
            },
        )
    if not (project / "04-svg/page-001.svg").exists():
        (project / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
    if not any((project / "04-svg/prepared").glob("*.svg")):
        (project / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
    source_files = svglide_quality_gate.source_file_hashes(project)
    page_receipt = project / "04-svg/page-001.receipt.json"
    write_json(
        page_receipt,
        {
            "version": "svglide-page-generation/v1",
            "stage": "generate_svg",
            "page": 1,
            "source_svg": source_files[0]["path"],
            "source_sha256": source_files[0]["sha256"],
            "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
            "evidence_sha256": svglide_quality_gate.file_sha256(project / "source/evidence.json"),
        },
    )
    write_json(
        project / "receipts/generate_svg.json",
        {
            "stage": "generate_svg",
            "status": "passed",
            "generator_mode": "external",
            "generated_files": source_files,
            "page_receipts": ["04-svg/page-001.receipt.json"],
            "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
            "evidence_sha256": svglide_quality_gate.file_sha256(project / "source/evidence.json"),
            "asset_manifest_sha256": svglide_quality_gate.file_sha256(project / "03-assets/asset-manifest.json"),
            "source_receipt_sha256": svglide_quality_gate.file_sha256(project / "source/source-receipt.json"),
            "lock_sha256": None,
            "generator_script_sha256": None,
            "fallback_skeleton_used": False,
            "page_identity_summary": [
                {
                    "page": 1,
                    "theme_archetype": "company_ecosystem",
                    "identity_fit_reason": "测试页符合视觉身份",
                    "reuse_risk_score": 0,
                    "fallback_skeleton_used": False,
                }
            ],
        },
    )
    write_json(project / "06-check/text-inventory.json", {"schema_version": "svglide-text-inventory/v1", "slides": []})
    write_json(
        project / "06-check/runtime-review.json",
        {
            "schema_version": "svglide-runtime-review/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
            },
            "registry": {
                "path": "skills/lark-slides/references/svglide-renderer-registry.json",
                "sha256": svglide_quality_gate.file_sha256(Path(__file__).resolve().parent.parent / "references" / "svglide-renderer-registry.json"),
            },
            "pages": [],
            "summary": {"error_count": 0, "warning_count": 0, "slide_count": 0, "renderer_count": 0, "layout_family_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/visual-distinctness.json",
        {
            "schema_version": "svglide-visual-distinctness/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {"slide_plan": "02-plan/slide_plan.json"},
            "signature": {"theme_archetype": "company_ecosystem"},
            "comparisons": [],
            "summary": {"error_count": 0, "warning_count": 0, "comparison_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/chart-verify.json",
        {
            "schema_version": "svglide-chart-verify/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "svg_dir": "04-svg/prepared",
            },
            "prepared_files": svglide_quality_gate.prepared_file_hashes(project),
            "summary": {"error_count": 0, "warning_count": 0, "required_chart_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/semantic-review.json",
        {
            "schema_version": "svglide-semantic-review/v1",
            "status": "passed",
            "action": "create_live",
            "profile": "preview_only",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "evidence": "source/evidence.json",
                "evidence_sha256": svglide_quality_gate.file_sha256(project / "source/evidence.json"),
                "svg_dir": "04-svg/prepared",
            },
            "prepared_files": svglide_quality_gate.prepared_file_hashes(project),
            "text_inventory": "06-check/text-inventory.json",
            "summary": {"error_count": 0, "warning_count": 0, "slide_count": 1, "prepared_svg_count": 1, "unmatched_text_count": 0},
            "issues": [],
        },
    )


class SVGlideQualityGateTest(unittest.TestCase):
    def test_quality_gate_passes_when_required_checks_have_zero_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            (project / "04-svg/prepared").mkdir(parents=True)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["version"], "svglide-quality-gate/v1")
            self.assertEqual(result["inputs"]["preflight"], "06-check/preflight.json")
            self.assertEqual(result["inputs"]["preview_lint"], "06-check/preview-lint.json")
            self.assertEqual(result["inputs"]["aesthetic_review"], "06-check/aesthetic-review.json")
            self.assertEqual(result["inputs"]["semantic_review"], "06-check/semantic-review.json")
            self.assertEqual(result["inputs"]["visual_distinctness"], "06-check/visual-distinctness.json")
            self.assertEqual(result["prepared_files"][0]["path"], "04-svg/prepared/page-001.svg")
            self.assertEqual(result["summary"]["failed_check_count"], 0)
            self.assertTrue((project / "06-check/quality-gate.json").exists())

    def test_quality_gate_fails_when_required_check_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("missing_check_file", failed_codes)

    def test_quality_gate_fails_when_any_check_has_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 2}, "action": "repair_and_rerun"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["source_error_count"], 2)
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("check_has_errors", failed_codes)

    def test_quality_gate_fails_when_preview_lint_action_blocks_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "repair_and_rerun"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("preview_lint_action_not_create_live", failed_codes)

    def test_quality_gate_fails_when_aesthetic_review_blocks_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "repair_and_rerun"})
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("aesthetic_review_blocks_create", failed_codes)

    def test_quality_gate_rejects_production_waivers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live", "waivers": [{"id": "w1"}]})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("production_waiver_not_allowed", failed_codes)

    def test_quality_gate_rejects_production_live_waivers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live", "waivers": [{"id": "w1"}]})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project, profile="production_live")

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("production_waiver_not_allowed", failed_codes)

    def test_quality_gate_fails_when_semantic_review_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg><rect /></svg>", encoding="utf-8")

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("semantic_review_prepared_stale", failed_codes)

    def test_quality_gate_fails_when_semantic_review_plan_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            write_json(project / "02-plan/slide_plan.json", {"language": "zh-CN", "slides": [{"page": 1}]})

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("semantic_review_plan_stale", failed_codes)

    def test_quality_gate_fails_when_semantic_review_evidence_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            write_json(project / "source/evidence.json", {"schema_version": "svglide-evidence/v1", "source_status": "ready", "items": [{"id": "item-001", "text": "新的证据内容足够长，应该让旧 semantic receipt 失效"}]})

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("semantic_review_evidence_stale", failed_codes)

    def test_quality_gate_fails_when_semantic_review_text_inventory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "06-check/text-inventory.json").unlink()

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("semantic_review_text_inventory_missing", failed_codes)

    def test_quality_gate_fails_when_semantic_review_status_is_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            semantic = json.loads((project / "06-check/semantic-review.json").read_text(encoding="utf-8"))
            semantic["status"] = "failed"
            write_json(project / "06-check/semantic-review.json", semantic)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("semantic_review_not_passed", failed_codes)

    def test_quality_gate_fails_when_generator_receipt_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "receipts/generate_svg.json").unlink()

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("missing_generator_receipt", failed_codes)

    def test_quality_gate_fails_when_generator_receipt_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "04-svg/page-001.svg").write_text("<svg><rect /></svg>", encoding="utf-8")

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_source_stale", failed_codes)

    def test_quality_gate_requires_chart_verify_when_plan_requires_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "02-plan/slide_plan.json",
                {"language": "zh-CN", "slides": [{"page": 1, "chart_contract": {"verify": "required", "data": [1, 2]}}]},
            )
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "06-check/chart-verify.json").unlink()

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("missing_check_file", failed_codes)

    def test_quality_gate_fails_when_runtime_review_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            write_json(project / "02-plan/slide_plan.json", {"language": "zh-CN", "slides": [{"page": 1, "title": "新计划"}]})

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("runtime_review_plan_stale", failed_codes)

    def test_quality_gate_blocks_strict_profile_when_research_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            receipt = json.loads((project / "source/source-receipt.json").read_text(encoding="utf-8"))
            receipt["research"] = {"status": "blocked_by_network"}
            write_json(project / "source/source-receipt.json", receipt)

            result = svglide_quality_gate.run_quality_gate(project, profile="production")

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("research_missing_for_current_topic", failed_codes)

    def test_quality_gate_blocks_strict_profile_when_fallback_skeleton_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            receipt = json.loads((project / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            receipt["fallback_skeleton_used"] = True
            write_json(project / "receipts/generate_svg.json", receipt)

            result = svglide_quality_gate.run_quality_gate(project, profile="production")

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("fallback_skeleton_used", failed_codes)


if __name__ == "__main__":
    unittest.main()
