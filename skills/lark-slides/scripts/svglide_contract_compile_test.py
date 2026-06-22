# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_schema
import svglide_contract_compile


def valid_report() -> dict[str, object]:
    decision = {
        "element_id": "title",
        "source_ref": "canvas_spec.content.title",
        "importance": "semantic_required",
        "source_tag": "text",
        "decision": "compiled",
        "reason": "compiled to foreignObject text shape",
        "output_ref": "title",
    }
    return {
        "version": "svglide-contract-compile/v1",
        "source": "04-artboard/raw/page-001.visual.svg",
        "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
        "output": "04-svg/page-001.svg",
        "status": "passed",
        "summary": {
            "semantic_required": 1,
            "visual_required": 0,
            "decorative_optional": 0,
            "compiled_elements": 1,
            "degraded_elements": 0,
            "rasterized_regions": 0,
            "dropped_decorations": 0,
            "blocking_issues": 0,
        },
        "compiled": [decision],
        "degraded": [],
        "rasterized": [],
        "dropped": [],
        "blocking_issues": [],
        "input_sha256": "abc",
        "semantic_map_sha256": "def",
        "output_sha256": "123",
    }


def valid_manifest() -> dict[str, object]:
    return {
        "version": "svglide-contract-compile-manifest/v1",
        "stage": "contract_compile",
        "status": "passed",
        "pages": [
            {
                "page": 1,
                "source": "04-artboard/raw/page-001.visual.svg",
                "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                "output": "04-svg/page-001.svg",
                "report": "04-svg/contract/page-001.report.json",
                "status": "passed",
                "input_sha256": "abc",
                "semantic_map_sha256": "def",
                "output_sha256": "123",
            }
        ],
        "summary": {
            "pages": 1,
            "blocking_issues": 0,
            "degraded_elements": 0,
            "rasterized_regions": 0,
            "dropped_decorations": 0,
        },
    }


class SVGlideContractCompileSchemaTest(unittest.TestCase):
    def report_schema(self) -> dict[str, object]:
        return svglide_schema.read_json(svglide_schema.schema_path("svglide-contract-compile-report.schema.json"))

    def manifest_schema(self) -> dict[str, object]:
        return svglide_schema.read_json(svglide_schema.schema_path("svglide-contract-compile-manifest.schema.json"))

    def test_page_report_schema_accepts_element_level_decisions(self) -> None:
        self.assertEqual(svglide_schema.validate_json_schema(valid_report(), self.report_schema()), [])

    def test_page_report_schema_rejects_missing_decision_arrays(self) -> None:
        payload = valid_report()
        payload.pop("compiled")

        issues = svglide_schema.validate_json_schema(payload, self.report_schema())

        self.assertIn("$.compiled", {issue["path"] for issue in issues})

    def test_page_report_schema_rejects_decision_without_reason(self) -> None:
        payload = valid_report()
        compiled = copy.deepcopy(payload["compiled"])
        compiled[0].pop("reason")
        payload["compiled"] = compiled

        issues = svglide_schema.validate_json_schema(payload, self.report_schema())

        self.assertIn("$.compiled[0].reason", {issue["path"] for issue in issues})

    def test_manifest_schema_accepts_page_source_report_output_mapping(self) -> None:
        self.assertEqual(svglide_schema.validate_json_schema(valid_manifest(), self.manifest_schema()), [])

    def test_manifest_schema_rejects_missing_output_sha256(self) -> None:
        payload = valid_manifest()
        pages = copy.deepcopy(payload["pages"])
        pages[0].pop("output_sha256")
        payload["pages"] = pages

        issues = svglide_schema.validate_json_schema(payload, self.manifest_schema())

        self.assertIn("$.pages[0].output_sha256", {issue["path"] for issue in issues})


class SVGlideContractCompileTest(unittest.TestCase):
    def make_project(self, elements: list[dict[str, object]]) -> Path:
        root = Path(tempfile.mkdtemp())
        project = root / ".lark-slides" / "plan" / "demo"
        raw_dir = project / "04-artboard" / "raw"
        raw_dir.mkdir(parents=True)
        (project / "03-assets").mkdir(parents=True)
        visual = raw_dir / "page-001.visual.svg"
        semantic_map = raw_dir / "page-001.semantic-map.json"
        visual.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="960" height="540" fill="#fff"/></svg>', encoding="utf-8")
        semantic_map.write_text(
            json.dumps(
                {
                    "version": "svglide-semantic-map/v1",
                    "page": 1,
                    "theme": {"background": "#ffffff", "text": "#111111", "primary": "#2563eb"},
                    "elements": elements,
                }
            ),
            encoding="utf-8",
        )
        (raw_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "version": "svglide-raw-visual-manifest/v1",
                    "stage": "generate_svg",
                    "pages": [
                        {
                            "page": 1,
                            "source": "04-artboard/raw/page-001.visual.svg",
                            "semantic_map": "04-artboard/raw/page-001.semantic-map.json",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (project / "03-assets" / "assets.json").write_text("{}", encoding="utf-8")
        return project

    def test_compile_project_requires_raw_manifest(self) -> None:
        project = Path(tempfile.mkdtemp()) / ".lark-slides" / "plan" / "demo"

        with self.assertRaisesRegex(svglide_contract_compile.ContractCompileError, "raw visual manifest"):
            svglide_contract_compile.compile_project(project)

    def test_compile_semantic_text_to_foreign_object_text_shape(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "title",
                    "kind": "text",
                    "importance": "semantic_required",
                    "text": "Quarterly Review",
                    "bbox": {"x": 80, "y": 64, "width": 640, "height": 72},
                    "style": {"font_size": 32, "font_weight": 800, "fill": "#111111"},
                }
            ]
        )

        result = svglide_contract_compile.compile_project(project)

        svg = (project / "04-svg" / "page-001.svg").read_text(encoding="utf-8")
        self.assertEqual(result["status"], "passed")
        self.assertIn('slide:role="slide"', svg)
        self.assertIn('slide:role="shape"', svg)
        self.assertIn('slide:shape-type="text"', svg)
        self.assertIn("Quarterly Review", svg)

    def test_compile_semantic_rect_circle_line_path_to_shape_role(self) -> None:
        project = self.make_project(
            [
                {"element_id": "panel", "kind": "rect", "bbox": {"x": 0, "y": 0, "width": 960, "height": 540}, "style": {"fill": "#f8fafc"}},
                {"element_id": "dot", "kind": "circle", "bbox": {"x": 100, "y": 120, "width": 30, "height": 30}, "style": {"fill": "#2563eb"}},
                {"element_id": "rule", "kind": "line", "bbox": {"x": 80, "y": 260, "width": 300, "height": 0}, "style": {"stroke": "#111111"}},
                {"element_id": "wave", "kind": "path", "bbox": {"x": 80, "y": 320, "width": 300, "height": 90}, "style": {"d": "M80 360 C160 300 240 420 380 330", "stroke": "#2563eb"}},
            ]
        )

        svglide_contract_compile.compile_project(project)

        svg = (project / "04-svg" / "page-001.svg").read_text(encoding="utf-8")
        self.assertGreaterEqual(svg.count('slide:role="shape"'), 4)
        self.assertIn("<path", svg)

    def test_compile_preserves_decorative_motif_owner_attrs(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "steam-one",
                    "kind": "path",
                    "importance": "decorative_optional",
                    "bbox": {"x": 80, "y": 320, "width": 300, "height": 90},
                    "style": {"d": "M80 360 C160 300 240 420 380 330", "stroke": "#2563eb"},
                    "data-svglide-role": "decorative_motif",
                    "data-svglide-motif-owner": "pin-and-paper",
                    "data-svglide-motif-id": "steam-ribbon",
                    "data-svglide-origin-template": "pin-and-paper",
                }
            ]
        )

        svglide_contract_compile.compile_project(project)

        svg = (project / "04-svg" / "page-001.svg").read_text(encoding="utf-8")
        self.assertIn('data-svglide-role="decorative_motif"', svg)
        self.assertIn('data-svglide-motif-owner="pin-and-paper"', svg)
        self.assertIn('data-svglide-motif-id="steam-ribbon"', svg)
        self.assertIn('data-svglide-origin-template="pin-and-paper"', svg)

    def test_compile_semantic_image_to_image_role(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "hero",
                    "kind": "image",
                    "importance": "semantic_required",
                    "href": "@./assets/hero.png",
                    "bbox": {"x": 560, "y": 96, "width": 320, "height": 220},
                }
            ]
        )

        svglide_contract_compile.compile_project(project)

        svg = (project / "04-svg" / "page-001.svg").read_text(encoding="utf-8")
        self.assertIn('slide:role="image"', svg)
        self.assertIn('href="@./assets/hero.png"', svg)

    def test_compile_injects_assets_and_refreshes_contract_hashes(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "background",
                    "kind": "rect",
                    "importance": "visual_required",
                    "bbox": {"x": 0, "y": 0, "width": 960, "height": 540},
                    "style": {"fill": "#07110E"},
                },
                {
                    "element_id": "title",
                    "kind": "text",
                    "importance": "semantic_required",
                    "text": "Asset backed cover",
                    "bbox": {"x": 80, "y": 80, "width": 560, "height": 80},
                },
            ]
        )
        raw_asset = project / "03-assets" / "raw" / "hero.png"
        raw_asset.parent.mkdir(parents=True, exist_ok=True)
        raw_asset.write_bytes(b"fake-png")
        (project / "03-assets" / "asset-manifest.json").write_text(
            json.dumps(
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
                            "file": "03-assets/raw/hero.png",
                            "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = svglide_contract_compile.compile_project(project)

        svg_path = project / "04-svg" / "page-001.svg"
        current_hash = svglide_contract_compile.file_sha256(svg_path)
        report = json.loads((project / "04-svg" / "contract" / "page-001.report.json").read_text(encoding="utf-8"))
        receipt = json.loads((project / "receipts" / "contract_compile.json").read_text(encoding="utf-8"))
        svg = svg_path.read_text(encoding="utf-8")
        self.assertIn('data-svglide-asset-id="hero"', svg)
        self.assertEqual(result["pages"][0]["output_sha256"], current_hash)
        self.assertEqual(report["output_sha256"], current_hash)
        self.assertEqual(receipt["pages"][0]["output_sha256"], current_hash)
        self.assertEqual(receipt["asset_injection_summary"]["used_count"], 1)

    def test_decorative_optional_unknown_can_drop_with_report(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "noise",
                    "kind": "mesh-gradient",
                    "importance": "decorative_optional",
                    "bbox": {"x": 0, "y": 0, "width": 960, "height": 540},
                }
            ]
        )

        result = svglide_contract_compile.compile_project(project)

        report = json.loads((project / "04-svg" / "contract" / "page-001.report.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "passed_with_warnings")
        self.assertEqual(report["dropped"][0]["element_id"], "noise")
        self.assertEqual(report["dropped"][0]["importance"], "decorative_optional")

    def test_semantic_required_unknown_blocks(self) -> None:
        project = self.make_project(
            [
                {
                    "element_id": "main_claim",
                    "kind": "unsupported-widget",
                    "importance": "semantic_required",
                    "bbox": {"x": 80, "y": 80, "width": 640, "height": 120},
                }
            ]
        )

        result = svglide_contract_compile.compile_project(project)

        self.assertEqual(result["status"], "failed")
        report = json.loads((project / "04-svg" / "contract" / "page-001.report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["blocking_issues"][0]["decision"], "blocked")

    def test_contract_manifest_hashes_match_outputs(self) -> None:
        project = self.make_project(
            [{"element_id": "title", "kind": "text", "text": "Hash check", "bbox": {"x": 80, "y": 80, "width": 300, "height": 50}}]
        )

        svglide_contract_compile.compile_project(project)

        manifest = json.loads((project / "04-svg" / "contract" / "manifest.json").read_text(encoding="utf-8"))
        page = manifest["pages"][0]
        self.assertEqual(page["output_sha256"], svglide_contract_compile.file_sha256(project / page["output"]))


if __name__ == "__main__":
    unittest.main()
