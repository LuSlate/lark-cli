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

import svglide_pre_submit_review as pre_submit_review


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepared_hashes(project: Path) -> list[dict[str, str]]:
    return pre_submit_review.prepared_file_hashes(project)


def make_project(root: Path) -> Path:
    project = root / "project"
    (project / "02-plan").mkdir(parents=True)
    (project / "04-svg/prepared").mkdir(parents=True)
    (project / "05-preview").mkdir(parents=True)
    (project / "06-check").mkdir(parents=True)
    (project / "receipts").mkdir(parents=True)

    write_json(
        project / "02-plan/slide_plan.json",
        {
            "title": "Theme System P0",
            "slides": [
                {
                    "page": 1,
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                }
            ],
        },
    )
    (project / "04-svg/prepared/page-001.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><text x="80" y="80">Theme System</text></svg>',
        encoding="utf-8",
    )
    (project / "05-preview/preview.html").write_text("<html><body>preview</body></html>", encoding="utf-8")
    (project / "05-preview/contact-sheet.png").write_bytes(b"contact-sheet")
    write_json(
        project / "05-preview/preview-manifest.json",
        {
            "project": str(project),
            "source_dir": "04-svg/prepared",
            "html_path": "05-preview/preview.html",
            "manifest_path": "05-preview/preview-manifest.json",
            "page_count": 1,
            "pages": [
                {
                    "page": 1,
                    "source_path": "04-svg/prepared/page-001.svg",
                    "source_bytes": (project / "04-svg/prepared/page-001.svg").stat().st_size,
                }
            ],
        },
    )

    plan_sha = pre_submit_review.file_sha256(project / "02-plan/slide_plan.json")
    current_prepared = prepared_hashes(project)
    write_json(
        project / "06-check/theme-adherence.json",
        {
            "schema_version": "svglide-theme-adherence/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": plan_sha,
            },
            "prepared_files": current_prepared,
            "summary": {"error_count": 0, "warning_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/visual-distinctness.json",
        {
            "schema_version": "svglide-visual-distinctness/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": plan_sha,
            },
            "summary": {"error_count": 0, "warning_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/quality-gate.json",
        {
            "version": "svglide-quality-gate/v1",
            "status": "passed",
            "profile": "production",
            "inputs": {
                "theme_adherence": "06-check/theme-adherence.json",
                "visual_distinctness": "06-check/visual-distinctness.json",
            },
            "prepared_files": current_prepared,
            "checks": [
                {"name": "visual-distinctness", "status": "passed", "issues": []},
                {"name": "theme-adherence", "status": "passed", "issues": []},
            ],
            "summary": {"failed_check_count": 0, "source_error_count": 0},
        },
    )
    write_human_review(project)
    return project


def human_review_payload(project: Path) -> dict[str, object]:
    current_prepared = prepared_hashes(project)
    return {
        "schema_version": "svglide-pre-submit-human-review/v1",
        "human_approval": {
            "approved": True,
            "reviewer": "unit-test",
        },
        "checks": {
            "visual_acceptance": {"status": "passed"},
            "intent_acceptance": {"status": "passed"},
            "text_readability": {"status": "passed"},
            "asset_chart_reasonableness": {"status": "passed"},
            "worth_live_submit": {"status": "passed"},
        },
        "plan_sha256": pre_submit_review.file_sha256(project / "02-plan/slide_plan.json"),
        "quality_gate_sha256": pre_submit_review.file_sha256(project / "06-check/quality-gate.json"),
        "prepared_files": current_prepared,
        "reviewed_artifacts": {
            "prepared_svg": current_prepared,
            "contact_sheet": {
                "path": "05-preview/contact-sheet.png",
                "sha256": pre_submit_review.file_sha256(project / "05-preview/contact-sheet.png"),
            },
            "preview": {
                "path": "05-preview/preview.html",
                "sha256": pre_submit_review.file_sha256(project / "05-preview/preview.html"),
            },
            "preview_manifest": {
                "path": "05-preview/preview-manifest.json",
                "sha256": pre_submit_review.file_sha256(project / "05-preview/preview-manifest.json"),
            },
            "quality_gate": {
                "path": "06-check/quality-gate.json",
                "sha256": pre_submit_review.file_sha256(project / "06-check/quality-gate.json"),
            },
        },
    }


def human_review_payload_with_artifact_array(project: Path) -> dict[str, object]:
    payload = human_review_payload(project)
    reviewed = payload["reviewed_artifacts"]
    assert isinstance(reviewed, dict)
    current_prepared = reviewed["prepared_svg"]
    assert isinstance(current_prepared, list)
    artifacts: list[dict[str, str]] = [
        {"kind": "prepared_svg", "path": item["path"], "sha256": item["sha256"]}
        for item in current_prepared
        if isinstance(item, dict) and isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str)
    ]
    for kind in ("contact_sheet", "preview", "preview_manifest", "quality_gate"):
        item = reviewed[kind]
        assert isinstance(item, dict)
        artifacts.append({"kind": kind, "path": item["path"], "sha256": item["sha256"]})
    payload["reviewed_artifacts"] = artifacts
    return payload


def write_human_review(project: Path, payload: dict[str, object] | None = None) -> Path:
    path = project / "06-check/pre-submit-human-review.json"
    write_json(path, payload or human_review_payload(project))
    return path


def issue_codes(result: dict[str, object]) -> set[str]:
    issues = result.get("issues")
    self_issues = issues if isinstance(issues, list) else []
    return {item.get("code") for item in self_issues if isinstance(item, dict)}


class PreSubmitReviewTest(unittest.TestCase):
    def test_passed_writes_check_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["issues"], [])
            check = json.loads((project / "06-check/pre-submit-review.json").read_text(encoding="utf-8"))
            receipt = json.loads((project / "receipts/pre-submit-review.json").read_text(encoding="utf-8"))
            self.assertEqual(check["status"], "passed")
            self.assertEqual(check, receipt)

    def test_document_array_reviewed_artifacts_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            write_human_review(project, human_review_payload_with_artifact_array(project))

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "passed", result["issues"])
            self.assertEqual(result["issues"], [])

    def test_missing_human_file_writes_failed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            missing = project / "06-check/missing-human-review.json"
            result = pre_submit_review.run_pre_submit_review(project, missing)

            self.assertEqual(result["status"], "failed")
            self.assertIn("human_review_missing", issue_codes(result))
            self.assertIn("failure_triage", result)
            receipt = json.loads((project / "receipts/pre-submit-review.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            self.assertIn("failure_triage", receipt)

    def test_approval_false_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            payload = human_review_payload(project)
            approval = payload["human_approval"]
            assert isinstance(approval, dict)
            approval["approved"] = False
            write_human_review(project, payload)

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "failed")
            self.assertIn("human_approval_not_approved", issue_codes(result))
            self.assertEqual(result["failure_triage"]["failure_category"], "human_rejected")

    def test_worth_live_submit_failed_blocks_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            payload = human_review_payload(project)
            checks = payload["checks"]
            assert isinstance(checks, dict)
            worth = checks["worth_live_submit"]
            assert isinstance(worth, dict)
            worth["status"] = "failed"
            write_human_review(project, payload)

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "failed")
            self.assertIn("worth_live_submit_not_passed", issue_codes(result))

    def test_reviewed_artifacts_requires_preview_manifest_and_current_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            payload = human_review_payload(project)
            reviewed = payload["reviewed_artifacts"]
            assert isinstance(reviewed, dict)
            reviewed.pop("preview_manifest")
            write_human_review(project, payload)

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")
            self.assertEqual(result["status"], "failed")
            self.assertIn("reviewed_artifact_preview_manifest_missing", issue_codes(result))

            payload = human_review_payload(project)
            reviewed = payload["reviewed_artifacts"]
            assert isinstance(reviewed, dict)
            preview = reviewed["preview"]
            assert isinstance(preview, dict)
            preview["sha256"] = "0" * 64
            write_human_review(project, payload)

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")
            self.assertEqual(result["status"], "failed")
            self.assertIn("reviewed_artifact_preview_stale", issue_codes(result))

    def test_quality_gate_hash_stale_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            quality_gate = json.loads((project / "06-check/quality-gate.json").read_text(encoding="utf-8"))
            quality_gate["note"] = "mutated after human review"
            write_json(project / "06-check/quality-gate.json", quality_gate)

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "failed")
            self.assertIn("human_quality_gate_sha256_stale", issue_codes(result))
            self.assertIn("reviewed_artifact_quality_gate_stale", issue_codes(result))

    def test_prepared_svg_stale_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp))
            (project / "04-svg/prepared/page-001.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><text x="80" y="80">Mutated</text></svg>',
                encoding="utf-8",
            )

            result = pre_submit_review.run_pre_submit_review(project, project / "06-check/pre-submit-human-review.json")

            self.assertEqual(result["status"], "failed")
            codes = issue_codes(result)
            self.assertIn("human_prepared_files_stale", codes)
            self.assertIn("reviewed_artifact_prepared_svg_stale", codes)


if __name__ == "__main__":
    unittest.main()
