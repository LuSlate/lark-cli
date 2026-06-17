# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import svglide_project_runner as runner


SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" width="960" height="540" viewBox="0 0 960 540"><rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#fff" /></svg>"""


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_png(path: Path) -> None:
    runner.write_fallback_contact_sheet(path, [("fixture", path)])


class SVGlideProjectRunnerTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(dir=runner.repo_root()))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        project = root / "demo"
        (project / "pages").mkdir(parents=True)
        (project / "pages" / "page-001.svg").write_text(SVG, encoding="utf-8")
        write_json(
            project / "project_manifest.json",
            {
                "deck_id": "demo",
                "title": "Demo Deck",
                "plan": "slide_plan.json",
                "pages": [{"page": 1, "source_svg": "pages/page-001.svg", "prepared_svg": "prepared/page-001.svg"}],
                "stage_commands": {"prepare": "builtin:copy_and_normalize_svg"},
            },
        )
        write_json(project / "slide_plan.json", {"output_mode": "svglide-svg", "title": "Demo Deck"})
        return project

    def args(self, project: Path, **overrides: object) -> Namespace:
        values = {
            "project": str(project),
            "cli": "./lark-cli",
            "env": "",
            "env_proof": "",
            "env_proof_input": "",
            "proxy": "",
            "allow_live": False,
            "force_live": False,
            "allow_missing_preview_lint": False,
            "validation_profile": "",
            "until": "dry_run",
            "resume": False,
        }
        values.update(overrides)
        return Namespace(**values)

    def write_prepare_receipt(self, project: Path, data: dict[str, object]) -> None:
        body = runner.builtin_prepare(project, data)
        runner.write_stage_receipt(project, data, "prepare", runner.now_ms(), body, prepared_digest=False, args=self.args(project))

    def write_gate_inputs(
        self,
        project: Path,
        data: dict[str, object],
        args: Namespace,
        *,
        preview_warning_count: int = 0,
        visual_score: int = 100,
        validation_profile: str | None = None,
    ) -> None:
        profile = validation_profile or runner.quality_validation_profile(
            runner.resolved_validation_profile(data, args, project=project)
        )
        self.write_prepare_receipt(project, data)
        runner.write_stage_receipt(
            project,
            data,
            "preflight",
            runner.now_ms(),
            {"status": "passed", "summary": {"summary": {"error_count": 0, "warning_count": 0}}},
            args=args,
        )
        runner.write_stage_receipt(
            project,
            data,
            "preview_lint",
            runner.now_ms(),
            {
                "status": "passed",
                "summary": {
                    "error_count": 0,
                    "warning_count": preview_warning_count,
                    "visual_score": visual_score,
                    "visual_score_threshold": runner.visual_score_threshold(profile),
                    "visual_score_mode": "enforced" if runner.visual_score_enforced(profile) else "advisory",
                    "validation_profile": profile,
                },
            },
            args=args,
        )

    def write_component_waiver(self, project: Path) -> None:
        write_json(
            project / "receipts" / "emitted-components-waiver.json",
            {"owner": "test", "reason": "legacy fixture", "expires_at": runner.now_ms() + 60_000},
        )

    def write_component_report(self, project: Path) -> None:
        write_json(
            project / "receipts" / "emitted_components.json",
            {"status": "passed", "summary": {"error_count": 0, "warning_count": 0}},
        )

    def write_structured_component_report(self, project: Path) -> None:
        write_json(
            project / "receipts" / "emitted_components.json",
            {
                "schema_version": "svglide-component-report/v1",
                "status": "passed",
                "pages": [
                    {
                        "page": 1,
                        "components": [
                            {
                                "id": "page-1.title",
                                "renderer_id": "demo.cover",
                                "bbox": {"x": 80, "y": 80, "width": 420, "height": 48},
                                "primitives": ["typography"],
                            }
                        ],
                    }
                ],
                "summary": {"error_count": 0, "warning_count": 0},
            },
        )

    def write_fake_cli(self, project: Path, version: str = "lark-cli 1.2.3") -> Path:
        cli = project / "fake-lark-cli"
        cli.write_text(f"#!/bin/sh\necho {version!r}\n", encoding="utf-8")
        cli.chmod(cli.stat().st_mode | 0o111)
        return cli

    def test_builtin_prepare_copies_source_svg_to_prepared(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)

        receipt = runner.builtin_prepare(project, data)

        prepared = project / "prepared" / "page-001.svg"
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(prepared.exists())
        self.assertEqual(prepared.read_text(encoding="utf-8"), SVG)
        self.assertEqual(receipt["operations"][0]["mutation"], "copy")

    def test_build_create_svg_command_uses_prepared_files(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        runner.builtin_prepare(project, data)

        command = runner.build_create_svg_command(project, data, "./lark-cli", dry_run=True)

        self.assertTrue(command[0].endswith("lark-cli"))
        self.assertEqual(command[1:3], ["slides", "+create-svg"])
        self.assertIn("--dry-run", command)
        self.assertIn(runner.rel_to_cli_cwd(project / "prepared" / "page-001.svg"), command)
        self.assertNotIn(str((project / "prepared" / "page-001.svg").resolve()), command)
        self.assertNotIn(str((project / "pages" / "page-001.svg").resolve()), command)

    def test_build_create_svg_command_passes_raster_flags(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["rasterize"] = {"effects": "force-page", "scale": 2, "report": "raster/raster-report.json"}
        runner.builtin_prepare(project, data)

        command = runner.build_create_svg_command(project, data, "./lark-cli", dry_run=True)

        self.assertIn("--svg-rasterize-effects", command)
        self.assertIn("force-page", command)
        self.assertIn("--svg-rasterize-scale", command)
        self.assertIn("2", command)
        self.assertIn("--svg-rasterize-report", command)
        report_index = command.index("--svg-rasterize-report") + 1
        self.assertEqual(command[report_index], runner.rel_to_cli_cwd(project / "raster" / "raster-report.json"))

    def test_live_create_requires_allow_live(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        args = Namespace(allow_live=False, env="ppe_pure_svg", env_proof="", force_live=False, cli="./lark-cli", proxy="")

        with self.assertRaisesRegex(runner.RunnerError, "--allow-live"):
            runner.run_live_create(project, data, args)

    def test_prepare_resume_is_invalidated_by_source_svg_changes(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        body = runner.builtin_prepare(project, data)
        runner.write_stage_receipt(project, data, "prepare", runner.now_ms(), body, prepared_digest=False)

        self.assertTrue(runner.should_skip_existing(project, data, "prepare"))

        (project / "pages" / "page-001.svg").write_text(SVG.replace("#fff", "#eee"), encoding="utf-8")

        self.assertFalse(runner.should_skip_existing(project, data, "prepare"))
        with self.assertRaisesRegex(runner.RunnerError, "stale"):
            runner.require_latest_prepare(project, data)

    def test_timing_receipt_records_v2_fields(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        body = runner.builtin_prepare(project, data)

        runner.write_stage_receipt(project, data, "prepare", runner.now_ms(), body, prepared_digest=False)

        timings = json.loads((project / "receipts" / "timings.json").read_text(encoding="utf-8"))
        stage = next(item for item in timings["stages"] if item["stage"] == "prepare")
        self.assertIn("started_at_ms", stage)
        self.assertIn("ended_at_ms", stage)
        self.assertIn("target_ms", stage)
        self.assertIn("over_budget", stage)
        self.assertIn("next_command", stage)
        self.assertGreater(stage["target_ms"], 0)
        self.assertIn("svglide_project_runner.py", stage["next_command"])

    def test_prepare_rejects_prepared_svg_outside_project_before_copy(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["pages"][0]["prepared_svg"] = "../escape.svg"
        outside = project.parent / "escape.svg"

        with self.assertRaisesRegex(runner.RunnerError, "escapes project root"):
            runner.builtin_prepare(project, data)

        self.assertFalse(outside.exists())

    def test_prepare_rejects_manifest_page_count_drift_from_slide_plan(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "page_count": 2,
                "slides": [{"page": 1}, {"page": 2}],
                "svg_files": [{"page": 1}, {"page": 2}],
            },
        )

        with self.assertRaisesRegex(runner.RunnerError, "project_manifest.pages count 1.*slide_plan.page_count 2"):
            runner.builtin_prepare(project, data)

    def test_prepare_resume_is_invalidated_by_slide_plan_page_count_changes(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "page_count": 1,
                "slides": [{"page": 1}],
                "svg_files": [{"page": 1}],
            },
        )
        args = self.args(project)
        self.write_prepare_receipt(project, data)

        self.assertTrue(runner.should_skip_existing(project, data, "prepare", args))

        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "page_count": 2,
                "slides": [{"page": 1}, {"page": 2}],
                "svg_files": [{"page": 1}, {"page": 2}],
            },
        )

        self.assertFalse(runner.should_skip_existing(project, data, "prepare", args))
        with self.assertRaisesRegex(runner.RunnerError, "project_manifest.pages count 1.*slide_plan.page_count 2"):
            runner.require_latest_prepare(project, data)

    def test_preflight_rejects_manifest_page_count_drift_after_existing_prepare_receipt(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "page_count": 1,
                "slides": [{"page": 1}],
                "svg_files": [{"page": 1}],
            },
        )
        self.write_prepare_receipt(project, data)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "page_count": 2,
                "slides": [{"page": 1}, {"page": 2}],
                "svg_files": [{"page": 1}, {"page": 2}],
            },
        )

        with self.assertRaisesRegex(runner.RunnerError, "project_manifest.pages count 1.*slide_plan.page_count 2"):
            runner.run_preflight(project, data)

    def test_receipt_path_rejects_paths_outside_project(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["receipts"] = {"dry_run": "../dry-run.json"}

        with self.assertRaisesRegex(runner.RunnerError, "escapes project root"):
            runner.receipt_path(project, "dry_run", data)

    def test_proxy_status_is_configured_not_observed(self) -> None:
        status = runner.proxy_status({"HTTPS_PROXY": "http://127.0.0.1:8899"})

        self.assertEqual(status["status"], "configured_not_observed")

    def test_env_proof_requires_ppe_headers_and_prerelease_host(self) -> None:
        project = self.make_project()
        proof = project / "env-proof.json"
        write_json(
            proof,
            {
                "status": "verified",
                "target_env": "ppe_pure_svg",
                "openapi_host": "open.feishu-pre.cn",
                "headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
            },
        )

        self.assertTrue(runner.load_env_proof(str(proof))["verified"])

        write_json(
            proof,
            {
                "status": "verified",
                "target_env": "ppe_pure_svg",
                "openapi_host": "open.feishu.cn",
                "headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
            },
        )

        self.assertFalse(runner.load_env_proof(str(proof))["verified"])

    def test_stage_aliases_accept_cli_names(self) -> None:
        self.assertEqual(runner.normalize_stage("dry-run"), "dry_run")
        self.assertEqual(runner.normalize_stage("live-create"), "live_create")
        self.assertEqual(runner.normalize_stage("preview-lint"), "preview_lint")
        self.assertEqual(runner.normalize_stage("quality-gate"), "quality_gate")
        self.assertEqual(runner.normalize_stage("ppe-proof"), "ppe_proof")
        self.assertEqual(runner.normalize_stage("render-contact-sheet"), "render_contact_sheet")

    def test_stage_graph_includes_quality_gate_and_ppe_proof(self) -> None:
        dry_run_stages = runner.stages_until("dry_run")
        readback_stages = runner.stages_until("readback")

        self.assertIn("quality_gate", dry_run_stages)
        self.assertNotIn("ppe_proof", dry_run_stages)
        self.assertNotIn("live_create", dry_run_stages)
        self.assertEqual(readback_stages[-3:], ["ppe_proof", "live_create", "readback"])
        parser = runner.build_parser()
        self.assertEqual(parser.parse_args(["quality-gate", "--project", "/tmp/p"]).single_stage, "quality_gate")
        self.assertEqual(parser.parse_args(["ppe-proof", "--project", "/tmp/p"]).single_stage, "ppe_proof")

    def test_skipped_preview_lint_receipt_is_not_reused(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        args = self.args(project)
        self.write_prepare_receipt(project, data)
        runner.write_stage_receipt(
            project,
            data,
            "preview_lint",
            runner.now_ms(),
            {"status": "skipped", "reason": "missing preview/preview.html"},
            args=args,
        )

        self.assertFalse(runner.should_skip_existing(project, data, "preview_lint", args))

    def test_allow_missing_preview_lint_generates_waiver(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        args = self.args(project, allow_missing_preview_lint=True)
        self.write_prepare_receipt(project, data)

        receipt = runner.run_preview_lint(project, data, args)

        self.assertEqual(receipt["status"], "waived")
        self.assertEqual(receipt["summary"]["error_count"], 0)

    def test_preview_lint_manifest_command_is_rejected(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["stage_commands"]["preview_lint"] = "python3 project_lint.py"
        write_json(project / "project_manifest.json", data)
        self.write_prepare_receipt(project, data)

        with self.assertRaisesRegex(runner.RunnerError, "preview_lint is runner-owned"):
            runner.run_preview_lint(project, data, self.args(project))

    def test_quality_gate_allows_authoring_component_waiver_for_dry_run(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        args = self.args(project, allow_missing_preview_lint=True)
        self.write_gate_inputs(project, data, args)
        self.write_component_waiver(project)

        body = runner.run_quality_gate(project, data, args)
        receipt = runner.write_stage_receipt(project, data, "quality_gate", runner.now_ms(), body, args=args)

        self.assertEqual(body["status"], "passed_with_waiver")
        self.assertEqual(receipt["input_fingerprint"]["schema_version"], "svglide-stage-fingerprint/v1")
        self.assertTrue(runner.should_skip_existing(project, data, "quality_gate", args))
        with self.assertRaisesRegex(runner.RunnerError, "passed quality_gate"):
            runner.require_strict_quality_gate(project, data, args)

    def test_quality_gate_rejects_component_waiver_for_production(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["validation_profile"] = {"profile": "production"}
        write_json(project / "project_manifest.json", data)
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_waiver(project)

        with self.assertRaisesRegex(runner.RunnerError, "production"):
            runner.run_quality_gate(project, data, args)

    def test_resolved_validation_profile_reads_slide_plan(self) -> None:
        project = self.make_project()
        write_json(
            project / "slide_plan.json",
            {"output_mode": "svglide-svg", "title": "Demo Deck", "validation_profile": {"profile": "golden"}},
        )
        data = runner.manifest(project)

        self.assertEqual(runner.resolved_validation_profile(data, self.args(project), project=project), "golden")

    def test_quality_gate_accepts_authoring_score_below_threshold_as_advisory(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        args = self.args(project)
        self.write_gate_inputs(project, data, args, visual_score=72)
        self.write_component_report(project)

        body = runner.run_quality_gate(project, data, args)

        self.assertEqual(body["status"], "passed")
        self.assertEqual(body["validation_profile"], "authoring")
        self.assertEqual(body["visual_score"], 72)
        self.assertEqual(body["visual_score_threshold"], 75)
        self.assertEqual(body["visual_score_mode"], "advisory")

    def test_quality_gate_rejects_production_score_below_threshold(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["validation_profile"] = {"profile": "production"}
        write_json(project / "project_manifest.json", data)
        args = self.args(project)
        self.write_gate_inputs(project, data, args, visual_score=84)
        self.write_structured_component_report(project)

        with self.assertRaisesRegex(runner.RunnerError, "visual_score must be >= 85"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_rejects_golden_preview_warnings(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["validation_profile"] = {"profile": "golden"}
        write_json(project / "project_manifest.json", data)
        args = self.args(project)
        self.write_gate_inputs(project, data, args, preview_warning_count=1, visual_score=93)
        self.write_structured_component_report(project)

        with self.assertRaisesRegex(runner.RunnerError, "golden warning_budget must be 0"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_rejects_unproven_ppt_master_asset_selection(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "ppt_master_asset_selection": {
                    "selected_assets": [
                        {"id": "chart.timeline", "kind": "chart_template"},
                    ],
                },
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)

        with self.assertRaisesRegex(runner.RunnerError, "ppt-master asset usage"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_accepts_proven_ppt_master_asset_selection(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "ppt_master_asset_selection": {
                    "selected_assets": [
                        {"id": "chart.timeline", "kind": "chart_template"},
                    ],
                },
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)
        write_json(
            project / "receipts" / "ppt-master-asset-usage.json",
            {
                "schema_version": "svglide-ppt-master-asset-usage/v1",
                "status": "passed",
                "used_asset_ids": ["chart.timeline"],
                "page_usages": [
                    {
                        "page": 1,
                        "asset_id": "chart.timeline",
                        "component_ids": ["component.timeline.1"],
                        "source_trace": "derived_renderer_contract",
                    }
                ],
                "error_count": 0,
                "warning_count": 0,
            },
        )

        body = runner.run_quality_gate(project, data, args)

        self.assertEqual(body["status"], "passed")
        self.assertEqual(body["ppt_master_asset_usage"]["used_count"], 1)

    def test_quality_gate_rejects_selected_assets_not_used_by_receipt(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "ppt_master_asset_selection": {
                    "selected_assets": [
                        {"id": "chart.bubble_chart", "kind": "chart_template"},
                        {"id": "chart.hub_spoke", "kind": "chart_template"},
                    ],
                },
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)
        write_json(
            project / "receipts" / "ppt-master-asset-usage.json",
            {
                "schema_version": "svglide-ppt-master-asset-usage/v1",
                "status": "passed",
                "page_usages": [
                    {
                        "page": 1,
                        "asset_id": "chart.bubble_chart",
                        "component_ids": ["bubble-chart"],
                        "source_trace": "chart.bubble_chart",
                    }
                ],
                "error_count": 0,
                "warning_count": 0,
            },
        )

        with self.assertRaisesRegex(runner.RunnerError, "ppt-master asset usage"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_ignores_disabled_ppt_master_selected_assets(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "ppt_master_asset_selection": {
                    "selected_assets": [
                        {"id": "chart.bubble_chart", "kind": "chart_template", "enabled": True},
                        {"id": "chart.hub_spoke", "kind": "chart_template", "enabled": False},
                    ],
                },
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)
        write_json(
            project / "receipts" / "ppt-master-asset-usage.json",
            {
                "schema_version": "svglide-ppt-master-asset-usage/v1",
                "status": "passed",
                "page_usages": [
                    {
                        "page": 1,
                        "asset_id": "chart.bubble_chart",
                        "component_ids": ["bubble-chart"],
                        "source_trace": "chart.bubble_chart",
                    }
                ],
                "error_count": 0,
                "warning_count": 0,
            },
        )

        body = runner.run_quality_gate(project, data, args)

        self.assertEqual(body["status"], "passed")
        self.assertEqual(body["ppt_master_asset_usage"]["selected_count"], 1)
        self.assertNotIn("chart.hub_spoke", body["ppt_master_asset_usage"]["missing_asset_ids"])

    def test_quality_gate_rejects_shallow_component_report_for_golden(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["validation_profile"] = {"profile": "golden"}
        write_json(project / "project_manifest.json", data)
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)

        with self.assertRaisesRegex(runner.RunnerError, "component report schema_version"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_accepts_structured_component_report_for_golden(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        data["validation_profile"] = {"profile": "golden"}
        write_json(project / "project_manifest.json", data)
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        write_json(
            project / "receipts" / "emitted_components.json",
            {
                "schema_version": "svglide-component-report/v1",
                "status": "passed",
                "pages": [
                    {
                        "page": 1,
                        "components": [
                            {
                                "id": "page-1.title",
                                "renderer_id": "demo.cover",
                                "bbox": {"x": 80, "y": 80, "width": 420, "height": 48},
                                "primitives": ["typography"],
                                "effects": ["text_hierarchy"],
                            }
                        ],
                    }
                ],
                "summary": {"error_count": 0, "warning_count": 0},
            },
        )

        body = runner.run_quality_gate(project, data, args)

        self.assertEqual(body["status"], "passed")
        self.assertEqual(body["component_report"]["status"], "passed")

    def test_quality_gate_rejects_ppt_master_usage_without_page_trace(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "ppt_master_asset_selection": {
                    "selected_assets": [
                        {"id": "chart.timeline", "kind": "chart_template"},
                    ],
                },
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)
        write_json(
            project / "receipts" / "ppt-master-asset-usage.json",
            {
                "schema_version": "svglide-ppt-master-asset-usage/v1",
                "status": "passed",
                "used_asset_ids": ["chart.timeline"],
                "error_count": 0,
                "warning_count": 0,
            },
        )

        with self.assertRaisesRegex(runner.RunnerError, "ppt-master asset usage"):
            runner.run_quality_gate(project, data, args)

    def test_quality_gate_rejects_unproven_slide_level_ppt_master_reference(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        write_json(
            project / "slide_plan.json",
            {
                "output_mode": "svglide-svg",
                "title": "Demo Deck",
                "slides": [
                    {
                        "page": 1,
                        "visual_plan": {
                            "ppt_master_reference_assets": [
                                {"id": "layout.government_blue", "kind": "layout_template"},
                            ],
                        },
                    }
                ],
            },
        )
        args = self.args(project)
        self.write_gate_inputs(project, data, args)
        self.write_component_report(project)

        with self.assertRaisesRegex(runner.RunnerError, "ppt-master asset usage"):
            runner.run_quality_gate(project, data, args)

    def test_dry_run_requires_latest_quality_gate(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)

        with self.assertRaisesRegex(runner.RunnerError, "quality_gate"):
            runner.run_dry_run(project, data, "./lark-cli", self.args(project))

    def test_ppe_proof_normalizes_raw_env_proof(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        cli = self.write_fake_cli(project)
        observed = runner.now_ms()
        raw = project / "raw-env-proof.json"
        write_json(
            raw,
            {
                "schema_version": "svglide-env-proof-raw/v1",
                "observed_at_ms": observed,
                "ttl_ms": 60_000,
                "target_env": "ppe_pure_svg",
                "target_host": "open.feishu-pre.cn",
                "headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
                "auth": {"status": "verified", "subject": "user:fixture"},
                "cli": {"path": str(cli), "version": "lark-cli 1.2.3"},
                "smoke": {"type": "pure_svg_minimal", "status": "passed", "presentation_id": "pres_1"},
            },
        )
        args = self.args(project, cli=str(cli), env="ppe_pure_svg", env_proof_input=str(raw))

        body = runner.run_ppe_proof(project, data, args)
        runner.write_stage_receipt(project, data, "ppe_proof", runner.now_ms(), body, args=args)

        normalized = json.loads((project / "receipts" / "env-proof.json").read_text(encoding="utf-8"))
        self.assertEqual(normalized["schema_version"], "svglide-env-proof/v1")
        self.assertEqual(normalized["expires_at_ms"], observed + 60_000)
        self.assertEqual(normalized["auth_subject"], "user:fixture")
        self.assertTrue(runner.should_skip_existing(project, data, "ppe_proof", args))
        runner.require_latest_ppe_proof(project, data, args)

    def test_live_create_rejects_quality_gate_waiver(self) -> None:
        project = self.make_project()
        data = runner.manifest(project)
        cli = self.write_fake_cli(project)
        args = self.args(project, cli=str(cli), env="ppe_pure_svg", allow_live=True, proxy="http://127.0.0.1:8899")
        self.write_gate_inputs(project, data, args)
        self.write_component_waiver(project)
        quality = runner.run_quality_gate(project, data, args)
        runner.write_stage_receipt(project, data, "quality_gate", runner.now_ms(), quality, args=args)
        runner.write_stage_receipt(
            project,
            data,
            "dry_run",
            runner.now_ms(),
            {"status": "passed", "summary": {"ok": True}},
            args=args,
        )

        with self.assertRaisesRegex(runner.RunnerError, "passed quality_gate"):
            runner.run_live_create(project, data, args)

    def test_live_create_fields_accept_nested_cli_data(self) -> None:
        parsed = {
            "ok": True,
            "data": {
                "xml_presentation_id": "pres_123",
                "url": "https://example.test/slides/pres_123",
                "revision_id": 3,
                "slide_ids": ["s1", "s2"],
            },
        }

        fields = runner.live_create_fields(parsed)

        self.assertEqual(fields["xml_presentation_id"], "pres_123")
        self.assertEqual(fields["url"], "https://example.test/slides/pres_123")
        self.assertEqual(fields["revision_id"], 3)
        self.assertEqual(fields["slide_ids"], ["s1", "s2"])

    def test_render_contact_sheet_writes_png_and_updates_report(self) -> None:
        project = self.make_project()
        raster_dir = project / "raster"
        write_png(raster_dir / "rich-preview.png")
        write_png(raster_dir / "safe-preview.png")
        write_json(raster_dir / "readback-snapshot.json", {"xml_presentation_id": "pres_123", "slide_count": 1})
        write_json(
            raster_dir / "raster-report.json",
            {
                "quality": {"gate_passed": True},
                "visual_artifacts": {
                    "rich_preview": "raster/rich-preview.png",
                    "safe_preview": "raster/safe-preview.png",
                    "readback_snapshot": "raster/readback-snapshot.json",
                },
            },
        )
        data = runner.manifest(project)
        data["raster_report"] = "raster/raster-report.json"
        write_json(project / "project_manifest.json", data)

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = runner.main(["render-contact-sheet", "--project", str(project)])

        contact_sheet = raster_dir / "contact-sheet.png"
        self.assertEqual(exit_code, 0)
        self.assertTrue(contact_sheet.exists())
        self.assertGreater(contact_sheet.stat().st_size, 0)
        receipt = runner.last_receipt(project, data, "render_contact_sheet")
        self.assertEqual(receipt["status"], "passed")
        updated_report = json.loads((raster_dir / "raster-report.json").read_text(encoding="utf-8"))
        self.assertEqual(updated_report["visual_artifacts"]["contact_sheet"], runner.rel_to_cli_cwd(contact_sheet))

    def test_render_contact_sheet_rejects_failed_quality_gate(self) -> None:
        project = self.make_project()
        raster_dir = project / "raster"
        write_png(raster_dir / "rich-preview.png")
        write_png(raster_dir / "safe-preview.png")
        write_json(raster_dir / "readback-snapshot.json", {})
        write_json(
            raster_dir / "raster-report.json",
            {
                "quality": {"gate_passed": False},
                "visual_artifacts": {
                    "rich_preview": "raster/rich-preview.png",
                    "safe_preview": "raster/safe-preview.png",
                    "readback_snapshot": "raster/readback-snapshot.json",
                },
            },
        )
        data = runner.manifest(project)
        data["raster_report"] = "raster/raster-report.json"

        with self.assertRaisesRegex(runner.RunnerError, "gate_passed=false"):
            runner.run_render_contact_sheet(project, data)

    def test_render_contact_sheet_can_use_generated_png_and_readback_receipt(self) -> None:
        project = self.make_project()
        raster_dir = project / "raster"
        generated = raster_dir / "page-full.png"
        write_png(generated)
        write_json(
            raster_dir / "raster-report.json",
            {
                "quality": {"gate_passed": True},
                "generated_assets": [runner.rel_to_cli_cwd(generated)],
                "visual_artifacts": {},
            },
        )
        data = runner.manifest(project)
        data["raster_report"] = "raster/raster-report.json"
        write_json(project / "project_manifest.json", data)
        write_json(
            runner.receipt_path(project, "readback", data),
            {"status": "passed", "xml_presentation_id": "pres_123", "slide_count": 1},
        )

        body = runner.run_render_contact_sheet(project, data)

        self.assertEqual(body["status"], "passed")
        report = json.loads((raster_dir / "raster-report.json").read_text(encoding="utf-8"))
        artifacts = report["visual_artifacts"]
        self.assertEqual(artifacts["rich_preview"], runner.rel_to_cli_cwd(generated))
        self.assertEqual(artifacts["safe_preview"], runner.rel_to_cli_cwd(generated))
        self.assertTrue((raster_dir / "readback-snapshot.json").exists())
        self.assertTrue((raster_dir / "contact-sheet.png").exists())


if __name__ == "__main__":
    unittest.main()
