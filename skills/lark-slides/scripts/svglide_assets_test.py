# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_assets


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC"
)


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

    def test_assets_stage_downloads_source_url_to_local_href(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {
                "asset_contracts": [
                    {
                        "id": "hero",
                        "href": "@./03-assets/raw/hero.png",
                        "source_url": "https://example.com/hero.png",
                        "license": "cc0",
                        "usage_page": 1,
                        "placement_role": "cover",
                        "safe_text_zones": [{"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.7}],
                    }
                ]
            },
        )
        requested_urls: list[str] = []
        previous_http_get = svglide_assets.http_get

        def fake_http_get(url: str, timeout: float = 10.0) -> tuple[bytes, str]:
            requested_urls.append(url)
            return PNG_1X1, "image/png"

        svglide_assets.http_get = fake_http_get
        try:
            result = svglide_assets.run_assets(
                project,
                network_policy="online",
                image_backend="auto",
                no_ai_image=True,
                profile="local_real_preview",
            )
        finally:
            svglide_assets.http_get = previous_http_get

        self.assertEqual(result["status"], "failed")
        # One acquired image is valid but below the default local_real_preview minimum of 3.
        self.assertEqual(result["manifest"]["summary"]["acquired_count"], 1)
        asset = result["manifest"]["acquired_assets"][0]
        self.assertEqual(asset["status"], "acquired")
        self.assertEqual(asset["asset_kind"], "web_image")
        self.assertEqual(asset["file"], "03-assets/raw/hero.png")
        self.assertEqual(asset["source_url"], "https://example.com/hero.png")
        self.assertIsNone(asset["fallback_reason"])
        self.assertEqual(requested_urls, ["https://example.com/hero.png"])
        self.assertTrue((project / "03-assets/raw/hero.png").exists())

    def test_no_image_search_still_downloads_explicit_source_url(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {
                "asset_contracts": [
                    {
                        "id": "hero",
                        "href": "@./03-assets/raw/hero.png",
                        "source_url": "https://example.com/hero.png",
                        "license": "cc0",
                        "usage_page": 1,
                        "placement_role": "cover",
                        "safe_text_zones": [{"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.7}],
                    }
                ]
            },
        )
        previous_http_get = svglide_assets.http_get
        svglide_assets.http_get = lambda url, timeout=10.0: (PNG_1X1, "image/png")
        try:
            result = svglide_assets.run_assets(
                project,
                network_policy="online",
                image_backend="auto",
                no_image_search=True,
                no_ai_image=True,
                profile="local_real_preview",
            )
        finally:
            svglide_assets.http_get = previous_http_get

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["manifest"]["summary"]["acquired_count"], 1)
        asset = result["manifest"]["acquired_assets"][0]
        self.assertEqual(asset["status"], "acquired")
        self.assertEqual(asset["asset_kind"], "web_image")
        self.assertEqual(asset["file"], "03-assets/raw/hero.png")
        self.assertEqual(asset["source_url"], "https://example.com/hero.png")
        self.assertTrue((project / "03-assets/raw/hero.png").exists())

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
                    "import base64",
                    f"output.write_bytes(base64.b64decode('{base64.b64encode(PNG_1X1).decode('ascii')}'))",
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
        self.assertEqual(jobs["jobs"][0]["image_meta"]["width"], 1)

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

    def test_stage_command_backend_rejects_invalid_image_bytes(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "query": "rocket launch", "usage_page": 1, "placement_role": "cover"}]},
        )
        command = project / "make_invalid_image.py"
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

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["manifest"]["summary"]["acquired_count"], 0)
        self.assertIn("image_file_too_small", result["manifest"]["acquired_assets"][0]["fallback_reason"])

    def test_local_real_preview_fails_empty_assets(self) -> None:
        project = self.make_project()

        result = svglide_assets.run_assets(project, network_policy="auto", image_backend="auto", profile="local_real_preview")

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["manifest"]["issues"]}
        self.assertIn("real_preview_asset_contracts_empty", codes)
        self.assertIn("real_preview_visual_asset_count_too_low", codes)

    def test_local_real_preview_fails_image_backend_none(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {"asset_contracts": [{"id": "hero", "query": "company product visual", "usage_page": 1, "placement_role": "cover"}]},
        )

        result = svglide_assets.run_assets(
            project,
            network_policy="auto",
            image_backend="none",
            profile="local_real_preview",
            no_image_search=True,
        )

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["manifest"]["issues"]}
        self.assertIn("real_preview_image_backend_none", codes)

    def test_local_real_preview_rejects_three_local_only_visual_assets(self) -> None:
        project = self.make_project()
        (project / "03-assets").mkdir(parents=True, exist_ok=True)
        for index in range(1, 4):
            (project / f"03-assets/hero-{index}.png").write_bytes(PNG_1X1)
        write_json(
            project / "02-plan/svglide.lock.json",
            {
                "asset_contracts": [
                    {"id": "hero-1", "href": "@./03-assets/hero-1.png", "usage_page": 1, "placement_role": "cover"},
                    {"id": "hero-2", "href": "@./03-assets/hero-2.png", "usage_page": 2, "placement_role": "body_visual"},
                    {"id": "hero-3", "href": "@./03-assets/hero-3.png", "usage_page": 3, "placement_role": "closing"},
                ]
            },
        )

        result = svglide_assets.run_assets(project, network_policy="auto", image_backend="auto", profile="local_real_preview")

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["manifest"]["issues"]}
        self.assertIn("real_preview_visual_asset_count_too_low", codes)
        self.assertEqual(result["manifest"]["summary"]["contract_count"], 3)
        self.assertEqual(result["manifest"]["summary"]["real_visual_asset_count"], 0)

    def test_local_real_preview_accepts_three_token_backed_visual_assets(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/svglide.lock.json",
            {
                "asset_contracts": [
                    {"id": "hero-1", "href": "@./03-assets/hero-1.png", "usage_page": 1, "placement_role": "cover"},
                    {"id": "hero-2", "href": "@./03-assets/hero-2.png", "usage_page": 2, "placement_role": "body_visual"},
                    {"id": "hero-3", "href": "@./03-assets/hero-3.png", "usage_page": 3, "placement_role": "closing"},
                ]
            },
        )
        write_json(
            project / "03-assets/assets.json",
            {
                "@./03-assets/hero-1.png": "boxcn_hero_1",
                "@./03-assets/hero-2.png": "boxcn_hero_2",
                "@./03-assets/hero-3.png": "boxcn_hero_3",
            },
        )

        result = svglide_assets.run_assets(project, network_policy="auto", image_backend="auto", profile="local_real_preview")

        self.assertEqual(result["status"], "passed", result["manifest"]["issues"])
        self.assertEqual(result["manifest"]["summary"]["contract_count"], 3)
        self.assertGreaterEqual(result["manifest"]["summary"]["real_visual_asset_count"], 3)

    def test_local_real_preview_rejects_stage_command_generated_asset(self) -> None:
        project = self.make_project()
        write_json(
            project / "02-plan/slide_plan.json",
            {
                "route": "svglide-svg",
                "asset_policy": {"required": True, "minimum_visual_asset_count": 1},
                "slides": [{"page": 1}],
            },
        )
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
                    "import base64",
                    f"output.write_bytes(base64.b64decode('{base64.b64encode(PNG_1X1).decode('ascii')}'))",
                    "print(json.dumps({'source_url': 'internal://image/hero', 'license': 'internal_test'}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        previous = os.environ.get(svglide_assets.STAGE_COMMAND_ENV)
        os.environ[svglide_assets.STAGE_COMMAND_ENV] = f"{sys.executable} {command}"
        try:
            result = svglide_assets.run_assets(
                project,
                network_policy="online",
                asset_provider="trusted:test",
                image_backend="stage_command",
                profile="local_real_preview",
            )
        finally:
            if previous is None:
                os.environ.pop(svglide_assets.STAGE_COMMAND_ENV, None)
            else:
                os.environ[svglide_assets.STAGE_COMMAND_ENV] = previous

        self.assertEqual(result["status"], "failed")
        codes = {item["code"] for item in result["manifest"]["issues"]}
        self.assertIn("real_preview_generated_asset_blocked", codes)


if __name__ == "__main__":
    unittest.main()
