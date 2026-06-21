# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_assets


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideAssetsTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(project / "02-plan/slide_plan.json", {"route": "svglide-svg", "slides": [{"page": 1}]})
        return project

    def test_assets_stage_creates_empty_assets_json_when_no_contracts(self) -> None:
        project = self.make_project()

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "passed")
        self.assertTrue((project / "03-assets/assets.json").exists())
        self.assertTrue((project / "03-assets/asset-manifest.json").exists())
        self.assertEqual(result["manifest"]["summary"]["contract_count"], 0)

    def test_assets_stage_accepts_existing_local_asset(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "href": "@./03-assets/hero.png"}]},
        )
        (project / "03-assets").mkdir(parents=True, exist_ok=True)
        (project / "03-assets/hero.png").write_bytes(b"png")

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["manifest"]["contracts"][0]["status"], "local_file")

    def test_assets_stage_accepts_existing_local_path_asset(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "local_path": "@./03-assets/hero.png"}]},
        )
        (project / "03-assets").mkdir(parents=True, exist_ok=True)
        (project / "03-assets/hero.png").write_bytes(b"png")

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["manifest"]["contracts"][0]["status"], "local_file")
        self.assertEqual(result["manifest"]["acquired_assets"][0]["status"], "local_file")

    def test_assets_stage_blocks_required_http_asset(self) -> None:
        project = self.make_project()
        write_json(project / "02-plan/svglide.lock.json", {"asset_contracts": [{"id": "hero", "href": "https://example.com/hero.png"}]})

        result = svglide_assets.run_assets(project)

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["manifest"]["summary"]["error_count"], 1)
        self.assertEqual(result["manifest"]["issues"][0]["code"], "invalid_asset_href")

    def test_fixture_policy_writes_fallback_manifest_and_image_jobs(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "query": "rocket launch", "usage_page": 1, "placement_role": "cover"}]},
        )

        result = svglide_assets.run_assets(project, network_policy="fixture", image_backend="openai")

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["manifest"]["summary"]["image_job_count"], 1)
        self.assertEqual(result["manifest"]["acquired_assets"][0]["status"], "planned")
        self.assertEqual(result["manifest"]["acquired_assets"][0]["asset_kind"], "ai_image")
        self.assertTrue((project / "03-assets/image-jobs.json").exists())

    def test_stage_command_backend_acquires_generated_asset(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "query": "rocket launch", "usage_page": 1, "placement_role": "cover"}]},
        )
        command = project / "make_image.py"
        command.write_text(
            "\n".join(
                [
                    "import json",
                    "import pathlib",
                    "import sys",
                    "payload = json.loads(sys.stdin.read())",
                    "output = pathlib.Path(payload['output_path'])",
                    "output.parent.mkdir(parents=True, exist_ok=True)",
                    "output.write_bytes(b'png')",
                    "print(json.dumps({'source_url': 'internal://image/hero', 'license': 'internal_test'}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        previous = os.environ.get(svglide_assets.STAGE_COMMAND_ENV)
        os.environ[svglide_assets.STAGE_COMMAND_ENV] = f"{sys.executable} {command}"
        try:
            result = svglide_assets.run_assets(project, network_policy="online", asset_provider="trusted:test", image_backend="stage_command")
        finally:
            if previous is None:
                os.environ.pop(svglide_assets.STAGE_COMMAND_ENV, None)
            else:
                os.environ[svglide_assets.STAGE_COMMAND_ENV] = previous

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["manifest"]["summary"]["acquired_count"], 1)
        self.assertEqual(result["manifest"]["summary"]["fallback_count"], 0)
        self.assertEqual(result["manifest"]["summary"]["image_job_count"], 1)
        asset = result["manifest"]["acquired_assets"][0]
        self.assertEqual(asset["status"], "acquired")
        self.assertEqual(asset["asset_kind"], "generated_image")
        self.assertEqual(asset["provider"], "trusted:test")
        self.assertTrue((project / asset["file"]).exists())
        jobs = json.loads((project / "03-assets/image-jobs.json").read_text(encoding="utf-8"))
        self.assertEqual(jobs["jobs"][0]["status"], "acquired")

    def test_stage_command_backend_fails_without_command(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "query": "rocket launch", "usage_page": 1, "placement_role": "cover"}]},
        )
        previous = os.environ.pop(svglide_assets.STAGE_COMMAND_ENV, None)
        try:
            result = svglide_assets.run_assets(project, network_policy="online", asset_provider="trusted:test", image_backend="stage_command")
        finally:
            if previous is not None:
                os.environ[svglide_assets.STAGE_COMMAND_ENV] = previous

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["manifest"]["summary"]["acquired_count"], 0)
        self.assertEqual(result["manifest"]["summary"]["image_job_count"], 1)
        self.assertEqual(result["manifest"]["issues"][0]["code"], "asset_acquisition_failed")


if __name__ == "__main__":
    unittest.main()
