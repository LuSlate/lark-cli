# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_vf5_benchmark as benchmark


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def args_for(tmpdir: str, **overrides: object) -> argparse.Namespace:
    values = {
        "run_root": Path(tmpdir) / "vf5-run",
        "project_runner": Path(__file__).resolve().parent / "svglide_project_runner.py",
        "case": None,
        "planner_provider": "codex",
        "planner_command": None,
        "lark_cli_command": None,
        "target_slide_count": 8,
        "language": "zh-CN",
        "audience": "投资/战略分析读者",
        "timeout": 60,
        "no_search": False,
        "network_policy": "auto",
        "asset_provider": "auto",
        "image_backend": "auto",
        "no_online_research": False,
        "no_image_search": False,
        "no_ai_image": False,
        "refresh_online": False,
        "fixture_mode": False,
        "pretty": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class FakeRunner:
    def __init__(self, *, acquired_count: int = 2, visual_deliverable_pass: bool = True) -> None:
        self.acquired_count = acquired_count
        self.visual_deliverable_pass = visual_deliverable_pass
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        self.commands.append(command)
        if "init" in command:
            project = self.init_project(command)
            stdout = json.dumps({"project_root": project.as_posix()})
            return self.completed(command, stdout=stdout), self.record(command, stdout=stdout)
        if "prompt-plan" in command:
            project = Path(command[command.index("prompt-plan") + 1])
            self.write_prompt_plan(project, command)
            return self.completed(command), self.record(command)
        if "run" in command:
            project = Path(command[command.index("run") + 1])
            self.write_visual_acceptance_run(project, command)
            return self.completed(command), self.record(command)
        return self.completed(command, returncode=2, stderr="unsupported"), self.record(command, returncode=2, stderr="unsupported")

    def completed(self, command: list[str], *, stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)

    def record(self, command: list[str], *, stdout: str = "", stderr: str = "", returncode: int = 0) -> dict[str, object]:
        return {
            "command": command,
            "started_at": "2026-06-21T00:00:00+00:00",
            "ended_at": "2026-06-21T00:00:01+00:00",
            "returncode": returncode,
            "stdout_tail": stdout,
            "stderr_tail": stderr,
        }

    def init_project(self, command: list[str]) -> Path:
        deck_id = command[command.index("--deck-id") + 1]
        plan_root = Path(command[command.index("--plan-root") + 1])
        project = plan_root / deck_id
        project.mkdir(parents=True, exist_ok=True)
        write_json(project / "01-project/project_manifest.json", {"deck_id": deck_id, "title": "VF5"})
        write_json(project / "01-project/state.json", {"version": "svglide-state/v1", "stages": {"init": {"status": "passed"}}})
        return project

    def write_prompt_plan(self, project: Path, command: list[str]) -> None:
        prompt = command[command.index("--prompt") + 1]
        write_json(project / "00-input/instruction.json", {"schema_version": "svglide-instruction/v1", "raw_prompt": prompt})
        write_json(project / "02-plan/deck-plan.json", {"schema_version": "svglide-deck-plan/v1", "topic": prompt})
        write_json(project / "02-plan/slide-plan.json", {"schema_version": "svglide-slide-plan/v1", "slides": []})
        write_json(project / "02-plan/slide_plan.json", {"schema_version": "svglide-canvas-plan/v1", "slides": [], "asset_contracts": []})
        write_json(
            project / "receipts/prompt-planner.json",
            {
                "status": "passed",
                "provider": "codex",
                "provider_type": "codex",
                "search_enabled": True,
                "planner_stage_receipt_paths": [
                    "02-plan/planner/source-planner.receipt.json",
                    "02-plan/planner/deck-planner.receipt.json",
                    "02-plan/planner/slide-planner.receipt.json",
                    "02-plan/planner/canvas-planner.receipt.json",
                ],
                "planner_raw_outputs": [],
                "outputs": {"canvas_plan": "02-plan/slide_plan.json"},
                "summary": {"slide_count": 8, "asset_contract_count": 3},
            },
        )

    def write_visual_acceptance_run(self, project: Path, command: list[str]) -> None:
        stages = {
            name: {"status": "passed"}
            for name in [
                "init",
                "source",
                "plan",
                "assets",
                "generate_svg",
                "preview",
                "quality_gate",
                "dry_run",
                "visual_acceptance",
            ]
        }
        write_json(project / "01-project/state.json", {"version": "svglide-state/v1", "stages": stages})
        acquired_assets = [
            {"asset_id": f"asset-{index}", "status": "acquired", "asset_kind": "web_image", "file": f"03-assets/raw/asset-{index}.jpg", "sha256": f"hash-{index}"}
            for index in range(self.acquired_count)
        ]
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "status": "passed",
                "network_policy": "auto",
                "asset_provider": "auto",
                "image_backend": "auto",
                "summary": {
                    "contract_count": 3,
                    "acquired_count": self.acquired_count,
                    "fallback_count": 0,
                    "image_job_count": 0,
                },
                "acquired_assets": acquired_assets,
            },
        )
        write_json(project / "receipts/generate_svg.json", {"asset_injection_summary": {"by_page": [{"page": 1, "asset_id": "asset-0"}]}})
        (project / "05-preview").mkdir(parents=True, exist_ok=True)
        (project / "05-preview/preview.html").write_text("<html></html>", encoding="utf-8")
        write_json(project / "05-preview/preview-manifest.json", {"page_count": 8})
        (project / "05-preview/contact-sheet.png").write_bytes(b"png")
        write_json(project / "06-check/quality-gate.json", {"status": "passed", "summary": {"error_count": 0}})
        write_json(project / "07-create/dry-run.json", {"status": "passed", "returncode": 0, "command": command + ["--dry-run"]})
        issues = [] if self.visual_deliverable_pass else [{"code": "layout_overlap", "message": "text overlaps"}]
        write_json(
            project / "06-check/visual-acceptance.json",
            {
                "status": "passed" if self.visual_deliverable_pass else "failed",
                "deliverable_pass": self.visual_deliverable_pass,
                "action": "deliver" if self.visual_deliverable_pass else "scoped_repair",
                "issues": issues,
                "visual_evidence": {"pages": [{"page": 1, "evidence_path": "05-preview/contact-sheet.png"}]},
                "deck_rhythm": {"schema_version": "svglide-deck-rhythm/v1"},
            },
        )
        write_json(project / "receipts/visual_acceptance.json", {"status": "passed" if self.visual_deliverable_pass else "failed"})


class SVGlideVF5BenchmarkTest(unittest.TestCase):
    def test_real_mode_blocks_non_real_planner_and_disabled_assets(self) -> None:
        config = args_for(
            tempfile.gettempdir(),
            planner_provider="command",
            network_policy="fixture",
            image_backend="none",
            no_image_search=True,
            no_ai_image=True,
        )

        codes = {item["code"] for item in benchmark.assert_real_mode(config)}

        self.assertIn("planner_provider_not_real", codes)
        self.assertIn("asset_network_not_real", codes)
        self.assertIn("image_search_disabled", codes)
        self.assertIn("ai_image_disabled", codes)
        self.assertIn("image_backend_none", codes)

    def test_benchmark_runs_three_cases_to_visual_acceptance_without_live_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = args_for(tmpdir)
            fake = FakeRunner(acquired_count=2, visual_deliverable_pass=True)

            result = benchmark.run_benchmark(config, command_func=fake)

            self.assertEqual("passed", result["status"])
            self.assertEqual(3, result["summary"]["case_count"])
            self.assertEqual(3, result["summary"]["deliverable_pass_count"])
            self.assertTrue(result["stopped_before_live_create"])
            self.assertTrue((Path(result["run_root"]) / "06-check/vf5-benchmark.json").exists())
            self.assertTrue((Path(result["run_root"]) / "receipts/vf5-benchmark.json").exists())
            self.assertTrue(all(item["stage_statuses"]["live_create"] is None for item in result["cases"]))
            self.assertTrue(all(item["checks"]["visual_acceptance"]["deliverable_pass"] is True for item in result["cases"]))

    def test_real_mode_fails_when_assets_do_not_acquire_real_visuals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = args_for(tmpdir)
            fake = FakeRunner(acquired_count=0, visual_deliverable_pass=True)

            result = benchmark.run_benchmark(config, command_func=fake)

            self.assertEqual("failed", result["status"])
            self.assertEqual(3, result["summary"]["failed_count"])

    def test_fixture_mode_allows_command_provider_but_marks_not_real_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = args_for(
                tmpdir,
                planner_provider="command",
                network_policy="fixture",
                image_backend="none",
                fixture_mode=True,
            )
            fake = FakeRunner(acquired_count=0, visual_deliverable_pass=False)

            result = benchmark.run_benchmark(config, command_func=fake)

            self.assertEqual("passed", result["status"])
            self.assertFalse(result["real_benchmark"])
            self.assertEqual(0, result["summary"]["deliverable_pass_count"])
            self.assertTrue(all(item["checks"]["visual_acceptance"]["issues"] for item in result["cases"]))

    def test_benchmark_sets_local_lark_cli_command_only_for_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            previous = os.environ.get("SVGLIDE_LARK_CLI_CMD")
            os.environ.pop("SVGLIDE_LARK_CLI_CMD", None)
            try:
                config = args_for(tmpdir, lark_cli_command="go run .")
                fake = FakeRunner(acquired_count=2, visual_deliverable_pass=True)

                result = benchmark.run_benchmark(config, command_func=fake)

                self.assertEqual("go run .", result["lark_cli_command"])
                self.assertNotIn("SVGLIDE_LARK_CLI_CMD", os.environ)
            finally:
                if previous is not None:
                    os.environ["SVGLIDE_LARK_CLI_CMD"] = previous


if __name__ == "__main__":
    unittest.main()
