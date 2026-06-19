# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_asset_injector


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class SVGlideAssetInjectorTest(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        write_json(
            project / "02-plan/slide_plan.json",
            {
                "route": "svglide-svg",
                "slides": [
                    {"page": 1, "page_type": "cover"},
                    {"page": 2, "page_type": "closing"},
                ],
            },
        )
        (project / "04-svg").mkdir(parents=True)
        return project

    def write_svg(self, project: Path, page: int, body: str = "<text>Title</text>") -> None:
        (project / f"04-svg/page-{page:03d}.svg").write_text(
            f'<svg width="960" height="540" viewBox="0 0 960 540">{body}</svg>',
            encoding="utf-8",
        )

    def write_asset(self, project: Path, name: str = "hero.png") -> str:
        asset = project / "03-assets" / "raw" / name
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(PNG_1X1)
        return asset.relative_to(project).as_posix()

    def test_injects_cover_asset_with_scrim_and_editable_overlay_preserved(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1)
        self.write_svg(project, 2)
        asset_file = self.write_asset(project)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "hero",
                        "page": 1,
                        "placement_role": "cover",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": asset_file,
                        "source_url": "https://example.com/hero",
                        "license": "preview_unverified",
                        "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                ],
            },
        )

        result = svglide_asset_injector.inject_project_assets(project)

        svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")
        self.assertEqual(result["used_count"], 1)
        self.assertIn('data-svglide-asset-id="hero"', svg)
        self.assertIn('href="@./03-assets/raw/hero.png"', svg)
        self.assertIn("svglide-asset-scrim-hero", svg)
        self.assertIn("<text>Title</text>", svg)

    def test_injection_is_idempotent(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1)
        asset_file = self.write_asset(project)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "hero",
                        "page": 1,
                        "placement_role": "cover",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": asset_file,
                        "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                ],
            },
        )

        first = svglide_asset_injector.inject_project_assets(project)
        second = svglide_asset_injector.inject_project_assets(project)
        svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")

        self.assertEqual(first["injected_count"], 1)
        self.assertEqual(second["already_present_count"], 1)
        self.assertEqual(svg.count('data-svglide-asset-id="hero"'), 1)

    def test_injects_after_full_slide_background_rect(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1, '<rect x="0" y="0" width="960" height="540" fill="#fff"/><text>Title</text>')
        asset_file = self.write_asset(project)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "hero",
                        "page": 1,
                        "placement_role": "cover",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": asset_file,
                        "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                ],
            },
        )

        svglide_asset_injector.inject_project_assets(project)
        svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")

        self.assertLess(svg.index("<rect"), svg.index('data-svglide-asset-id="hero"'))
        self.assertLess(svg.index('data-svglide-asset-id="hero"'), svg.index("<text>Title</text>"))

    def test_missing_file_is_skipped_without_empty_image(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "hero",
                        "page": 1,
                        "placement_role": "cover",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": "03-assets/raw/missing.png",
                        "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                ],
            },
        )

        result = svglide_asset_injector.inject_project_assets(project)
        svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")

        self.assertEqual(result["used_count"], 0)
        self.assertEqual(result["by_page"][0]["reason"], "asset_file_missing")
        self.assertNotIn("<image", svg)

    def test_cover_without_safe_text_zone_is_skipped(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1)
        asset_file = self.write_asset(project)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "hero",
                        "page": 1,
                        "placement_role": "cover",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": asset_file,
                    }
                ],
            },
        )

        result = svglide_asset_injector.inject_project_assets(project)

        self.assertEqual(result["used_count"], 0)
        self.assertEqual(result["by_page"][0]["reason"], "safe_text_zones_missing")

    def test_body_visual_asset_uses_svg_text_contract_for_caption(self) -> None:
        project = self.make_project()
        self.write_svg(project, 1, '<rect x="0" y="0" width="960" height="540" fill="#fff"/><!-- svglide:asset-slot -->')
        asset_file = self.write_asset(project)
        write_json(
            project / "03-assets/asset-manifest.json",
            {
                "version": "svglide-assets/v1",
                "status": "passed",
                "acquired_assets": [
                    {
                        "asset_id": "figure",
                        "page": 1,
                        "placement_role": "body_visual",
                        "asset_kind": "user_file",
                        "status": "local_file",
                        "file": asset_file,
                        "source_url": "https://example.com/source",
                        "license": "preview_unverified",
                    }
                ],
            },
        )

        result = svglide_asset_injector.inject_project_assets(project)
        svg = (project / "04-svg/page-001.svg").read_text(encoding="utf-8")

        self.assertEqual(result["used_count"], 1)
        self.assertIn('slide:shape-type="text"', svg)
        self.assertIn("Visual evidence", svg)
        self.assertIn("Source: https://example.com/source", svg)
        self.assertNotIn("<text", svg)


if __name__ == "__main__":
    unittest.main()
