# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import importlib
import hashlib
import json
import tempfile
import unittest
from typing import Any
from pathlib import Path


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def write_png(path: Path, color: tuple[int, int, int] = (255, 255, 255)) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), color).save(path)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def issue_codes(result: dict[str, object]) -> set[str]:
    issues = result.get("issues")
    return {issue["code"] for issue in issues if isinstance(issue, dict) and isinstance(issue.get("code"), str)} if isinstance(issues, list) else set()


def load_fidelity_gate() -> Any:
    try:
        return importlib.import_module("svglide_snapshot_visual_fidelity")
    except ModuleNotFoundError as error:
        raise AssertionError(
            "M8 visual fidelity gate implementation is missing: "
            "skills/lark-slides/scripts/svglide_snapshot_visual_fidelity.py"
        ) from error


def build_minimal_visual_fidelity_project(project: Path, *, page_count: int = 2) -> None:
    baseline_receipts = []
    slide_receipts = []
    visual_receipts = []
    for page in range(1, page_count + 1):
        page_name = f"page-{page:03d}"
        baseline_receipts.append(f"06-check/visual-fidelity/{page_name}.baseline-render-receipt.json")
        slide_receipts.append(f"06-check/visual-fidelity/{page_name}.slide-render-receipt.json")
        visual_receipts.append(f"06-check/visual-fidelity/{page_name}.visual-fidelity-receipt.json")
    write_json(
        project / "06-check/visual-fidelity/manifest.json",
        {
            "schema_version": "svglide-snapshot-visual-fidelity-manifest/v1",
            "prepared_svgs": [f"04-svg/prepared/page-{page:03d}.svg" for page in range(1, page_count + 1)],
            "baseline_render_receipts": baseline_receipts,
            "slide_render_receipts": slide_receipts,
            "visual_fidelity_receipts": visual_receipts,
        },
    )
    for page in range(1, page_count + 1):
        page_name = f"page-{page:03d}"
        write_bytes(project / f"04-svg/prepared/{page_name}.svg", f"<svg>{page}</svg>".encode("utf-8"))
        write_png(project / f"06-check/visual-fidelity/{page_name}.cli-baseline.png", color=(page, page, page))
        write_png(project / f"06-check/visual-fidelity/{page_name}.slide-render.png", color=(page, page, page))
        write_json(project / f"06-check/readback/{page_name}.snapshot.json", {"blocks": [], "page": page})
        write_json(
            project / f"06-check/visual-fidelity/{page_name}.renderer-equivalence-receipt.json",
            {
                "schema_version": "svglide-snapshot-renderer-equivalence/v1",
                "status": "passed",
                "slide_render_model_compatible": True,
                "renderer_scope": "slide_snapshot_renderer",
                "evidence": "unit-test-production-equivalent-renderer",
            },
        )
        write_json(
            project / f"06-check/visual-fidelity/{page_name}.baseline-render-receipt.json",
            {
                "artifact_type": "cli_prepared_svg_baseline",
                "prepared_svg": f"04-svg/prepared/{page_name}.svg",
                "prepared_svg_sha256": file_sha256(project / f"04-svg/prepared/{page_name}.svg"),
                "baseline_png": f"06-check/visual-fidelity/{page_name}.cli-baseline.png",
                "baseline_png_sha256": file_sha256(project / f"06-check/visual-fidelity/{page_name}.cli-baseline.png"),
                "rasterizer": "browser",
                "rasterizer_version": "test",
                "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1},
                "font_manifest_sha256": "sha256:" + "3" * 64,
                "created_at": "2026-06-24T00:00:00Z",
            },
        )
        write_json(
            project / f"06-check/visual-fidelity/{page_name}.slide-render-receipt.json",
            {
                "artifact_type": "slide_snapshot_render",
                "snapshot_json": f"06-check/readback/{page_name}.snapshot.json",
                "snapshot_json_sha256": file_sha256(project / f"06-check/readback/{page_name}.snapshot.json"),
                "slide_render_png": f"06-check/visual-fidelity/{page_name}.slide-render.png",
                "slide_render_png_sha256": file_sha256(project / f"06-check/visual-fidelity/{page_name}.slide-render.png"),
                "render_source": "snapshot_renderer",
                "render_source_version": "test",
                "renderer_equivalence_receipt": f"06-check/visual-fidelity/{page_name}.renderer-equivalence-receipt.json",
                "renderer_equivalence_receipt_sha256": file_sha256(project / f"06-check/visual-fidelity/{page_name}.renderer-equivalence-receipt.json"),
                "capture_method": "automated",
                "capture_command": "python3 render.py",
                "presentation_id": "presentation-fixture",
                "revision_id": "revision-fixture",
                "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1},
                "created_at": "2026-06-24T00:00:00Z",
            },
        )
        write_json(
            project / f"06-check/visual-fidelity/{page_name}.visual-fidelity-receipt.json",
            {
                "status": "passed",
                "visual_fidelity_status": "passed",
                "metrics": {
                    "pixel_diff_ratio": 0.0,
                    "text_region_diff_ratio": 0.0,
                    "bbox_shift_px": 0,
                    "line_count_match": True,
                    "dominant_text_color_match": True,
                    "phash_distance": 0,
                },
                "text_regions": [
                    {
                        "text_style_id": f"txt_{page:03d}",
                        "content_hash": "sha256:" + "6" * 64,
                        "svg_bbox": {"x": 120, "y": 80, "width": 720, "height": 72},
                        "snapshot_bbox": {"x": 120, "y": 80, "width": 720, "height": 72},
                        "text_region_status": "passed",
                    }
                ],
            },
        )


def build_renderable_visual_fidelity_project(project: Path) -> None:
    write_bytes(
        project / "04-svg/prepared/page-001.svg",
        b"""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\" width=\"1280\" height=\"720\">
  <rect x=\"0\" y=\"0\" width=\"1280\" height=\"720\" fill=\"#ffffff\"/>
  <text data-svglide-text-style-id=\"txt_001\" x=\"120\" y=\"160\" width=\"640\" height=\"80\" font-family=\"Arial\" font-size=\"48\" font-weight=\"700\" fill=\"#123456\">SVGLIDE</text>
</svg>""",
    )
    write_json(
        project / "06-check/readback/page-001.snapshot.json",
        {
            "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1},
            "blocks": [
                {
                    "type": "text",
                    "id": "txt_001",
                    "x": 120,
                    "y": 112,
                    "width": 640,
                    "height": 80,
                    "text": "SVGLIDE",
                    "style": {
                        "font_family": "Arial",
                        "text_font_size": "48px",
                        "font_color": "#123456",
                        "bold": "true",
                    },
                }
            ],
        },
    )


class SVGlideSnapshotVisualFidelityTest(unittest.TestCase):
    def test_complete_visual_fidelity_project_passes_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(issue_codes(result), set())
            self.assertEqual(result["summary"]["slide_render_png_available_count"], 2)
            self.assertEqual(result["summary"]["visual_fidelity_passed_count"], 2)

    def test_single_slide_render_png_does_not_close_m8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project, page_count=1)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_png_available_count_lt_2", issue_codes(result))
            self.assertEqual(result["summary"]["slide_render_png_available_count"], 1)

    def test_missing_baseline_render_receipt_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            (project / "06-check/visual-fidelity/page-001.baseline-render-receipt.json").unlink()

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("baseline_render_receipt_missing", issue_codes(result))

    def test_missing_slide_render_receipt_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            (project / "06-check/visual-fidelity/page-001.slide-render-receipt.json").unlink()

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_receipt_missing", issue_codes(result))

    def test_missing_slide_render_png_fails_gate_even_with_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            (project / "06-check/visual-fidelity/page-001.slide-render.png").unlink()

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_png_missing", issue_codes(result))

    def test_empty_manifest_receipt_arrays_do_not_pass_visual_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            write_json(
                project / "06-check/visual-fidelity/manifest.json",
                {
                    "schema_version": "svglide-snapshot-visual-fidelity-manifest/v1",
                    "prepared_svgs": ["04-svg/prepared/page-001.svg"],
                    "baseline_render_receipts": [],
                    "slide_render_receipts": [],
                    "visual_fidelity_receipts": [],
                },
            )

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertTrue(
                {"baseline_render_receipts_empty", "slide_render_receipts_empty", "visual_fidelity_receipts_empty"} <= issue_codes(result)
            )

    def test_status_only_visual_receipt_does_not_pass_visual_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            write_json(
                project / "06-check/visual-fidelity/page-001.visual-fidelity-receipt.json",
                {
                    "status": "passed",
                    "visual_fidelity_status": "passed",
                    "metrics": {},
                    "text_regions": [],
                },
            )

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertTrue({"visual_fidelity_metrics_missing", "text_regions_missing"} <= issue_codes(result))

    def test_artifact_hash_mismatch_fails_visual_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            (project / "06-check/visual-fidelity/page-001.slide-render.png").write_bytes(b"changed-slide-render")

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_png_hash_mismatch", issue_codes(result))

    def test_hash_current_but_invalid_png_fails_visual_fidelity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            png_path = project / "06-check/visual-fidelity/page-001.slide-render.png"
            png_path.write_bytes(b"not-a-decodable-png")
            receipt_path = project / "06-check/visual-fidelity/page-001.slide-render-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["slide_render_png_sha256"] = file_sha256(png_path)
            write_json(receipt_path, receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_png_invalid", issue_codes(result))

    def test_manifest_requires_per_fixture_identity_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            receipt_path = project / "06-check/visual-fidelity/page-002.baseline-render-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["prepared_svg"] = "04-svg/prepared/page-001.svg"
            receipt["prepared_svg_sha256"] = file_sha256(project / "04-svg/prepared/page-001.svg")
            write_json(receipt_path, receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("baseline_prepared_svg_page_mismatch", issue_codes(result))

    def test_manifest_requires_baseline_png_identity_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            receipt_path = project / "06-check/visual-fidelity/page-002.baseline-render-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["baseline_png"] = "06-check/visual-fidelity/page-001.cli-baseline.png"
            receipt["baseline_png_sha256"] = file_sha256(project / "06-check/visual-fidelity/page-001.cli-baseline.png")
            write_json(receipt_path, receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("baseline_png_page_mismatch", issue_codes(result))

    def test_manifest_rejects_duplicate_fixture_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            manifest_path = project / "06-check/visual-fidelity/manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["prepared_svgs"] = ["04-svg/prepared/page-001.svg", "04-svg/prepared/page-001.svg"]
            write_json(manifest_path, manifest)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("prepared_svg_duplicate_page", issue_codes(result))

    def test_not_measured_does_not_pass_visual_fidelity(self) -> None:
        receipt = {
            "visual_fidelity_status": "not_measured",
            "reason": "slide_render_png_unavailable",
            "allowed_claim": "snapshot_structure_fidelity_only",
        }

        result = load_fidelity_gate().evaluate_visual_fidelity_receipt(receipt)

        self.assertEqual(result["status"], "structure_only_partial")
        self.assertFalse(result["visual_fidelity_passed"])
        self.assertIn("slide_render_png_unavailable", result["blocked_reasons"])

    def test_run_gate_rejects_not_measured_visual_fidelity_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            write_json(
                project / "06-check/visual-fidelity/page-001.visual-fidelity-receipt.json",
                {
                    "status": "not_measured",
                    "visual_fidelity_status": "not_measured",
                    "reason": "slide_render_png_unavailable",
                    "allowed_claim": "snapshot_structure_fidelity_only",
                    "metrics": {},
                    "text_regions": [],
                },
            )

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("slide_render_png_unavailable", issue_codes(result))

    def test_requires_two_slide_render_pngs_to_close_m8(self) -> None:
        receipt = {
            "prepared_svg_count": 2,
            "baseline_png_count": 2,
            "snapshot_json_count": 2,
            "visual_fidelity_receipt_count": 2,
            "slide_render_png_available_count": 1,
            "visual_fidelity_passed_count": 1,
            "not_measured_count": 1,
        }

        result = load_fidelity_gate().evaluate_visual_fidelity_receipt(receipt)

        self.assertEqual(result["status"], "structure_only_partial")
        self.assertFalse(result["visual_fidelity_passed"])
        self.assertIn("slide_render_png_available_count_lt_2", result["blocked_reasons"])

    def test_rejects_non_reproducible_slide_render_sources(self) -> None:
        for render_source in ("manual_screenshot", "local_preview"):
            with self.subTest(render_source=render_source):
                render_receipt = {
                    "artifact_type": "slide_snapshot_render",
                    "snapshot_json": "06-check/readback/page-001.snapshot.json",
                    "snapshot_json_sha256": "sha256:" + "1" * 64,
                    "slide_render_png": "06-check/visual-fidelity/page-001.slide-render.png",
                    "slide_render_png_sha256": "sha256:" + "2" * 64,
                    "render_source": render_source,
                    "render_source_version": "test",
                    "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1},
                    "created_at": "2026-06-24T00:00:00Z",
                }

                issues = load_fidelity_gate().validate_slide_render_receipt(render_receipt)

                self.assertIn("render_source_not_allowed", {issue["code"] for issue in issues})

    def test_rejects_editor_screenshot_without_automation_evidence(self) -> None:
        render_receipt = {
            "artifact_type": "slide_snapshot_render",
            "snapshot_json": "06-check/readback/page-001.snapshot.json",
            "snapshot_json_sha256": "sha256:" + "1" * 64,
            "slide_render_png": "06-check/visual-fidelity/page-001.slide-render.png",
            "slide_render_png_sha256": "sha256:" + "2" * 64,
            "render_source": "editor_screenshot",
            "render_source_version": "test",
            "viewport": {"width": 1280, "height": 720, "device_scale_factor": 1},
            "created_at": "2026-06-24T00:00:00Z",
        }

        issues = load_fidelity_gate().validate_slide_render_receipt(render_receipt)

        self.assertTrue({"capture_method_missing", "capture_command_missing", "revision_missing"} <= {issue["code"] for issue in issues})

    def test_baseline_receipt_requires_visual_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            receipt_path = project / "06-check/visual-fidelity/page-001.baseline-render-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt.pop("font_manifest_sha256", None)
            receipt.pop("rasterizer_version", None)
            write_json(receipt_path, receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertTrue({"font_manifest_sha256_missing", "rasterizer_version_missing"} <= issue_codes(result))

    def test_slide_render_receipt_requires_source_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            receipt_path = project / "06-check/visual-fidelity/page-001.slide-render-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for key in ("render_source_version", "capture_command", "presentation_id", "revision_id"):
                receipt.pop(key, None)
            write_json(receipt_path, receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertTrue(
                {"render_source_version_missing", "capture_command_missing", "presentation_id_missing", "revision_missing"}
                <= issue_codes(result)
            )

    def test_snapshot_renderer_without_equivalence_receipt_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            slide_receipt_path = project / "06-check/visual-fidelity/page-001.slide-render-receipt.json"
            slide_receipt = json.loads(slide_receipt_path.read_text(encoding="utf-8"))
            slide_receipt.pop("renderer_equivalence_receipt", None)
            slide_receipt.pop("renderer_equivalence_receipt_sha256", None)
            write_json(slide_receipt_path, slide_receipt)

            result = load_fidelity_gate().run_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("snapshot_renderer_equivalence_receipt_missing", issue_codes(result))

    def test_hard_failures_block_visual_fidelity(self) -> None:
        metrics = {
            "pixel_diff_ratio": 0.01,
            "text_region_diff_ratio": 0.02,
            "phash_distance": 2,
            "line_count_match": False,
            "dominant_text_color_match": True,
            "text_regions": [
                {
                    "text_style_id": "txt_001",
                    "content_hash": "sha256:" + "3" * 64,
                    "bbox_shift_px": 2,
                    "text_region_status": "measured",
                }
            ],
        }

        result = load_fidelity_gate().evaluate_visual_diff_metrics(metrics)

        self.assertFalse(result["visual_fidelity_passed"])
        self.assertIn("line_count_mismatch", result["blocked_reasons"])

    def test_large_pixel_or_text_region_diff_blocks_visual_fidelity(self) -> None:
        metrics = {
            "pixel_diff_ratio": 0.42,
            "text_region_diff_ratio": 0.58,
            "phash_distance": 2,
            "bbox_shift_px": 0,
            "line_count_match": True,
            "dominant_text_color_match": True,
            "text_regions": [
                {
                    "text_style_id": "txt_001",
                    "content_hash": "sha256:" + "3" * 64,
                    "bbox_shift_px": 0,
                    "text_region_status": "passed",
                }
            ],
        }

        result = load_fidelity_gate().evaluate_visual_diff_metrics(metrics)

        self.assertFalse(result["visual_fidelity_passed"])
        self.assertTrue({"pixel_diff_exceeds_threshold", "text_region_diff_exceeds_threshold"} <= set(result["blocked_reasons"]))

    def test_first_tier_visual_thresholds_block_regressions(self) -> None:
        metrics = {
            "pixel_diff_ratio": 0.09,
            "text_region_diff_ratio": 0.13,
            "phash_distance": 2,
            "bbox_shift_px": 0,
            "line_count_match": True,
            "dominant_text_color_match": True,
            "text_regions": [
                {
                    "text_style_id": "txt_001",
                    "content_hash": "sha256:" + "3" * 64,
                    "bbox_shift_px": 0,
                    "text_region_status": "passed",
                }
            ],
        }

        result = load_fidelity_gate().evaluate_visual_diff_metrics(metrics)

        self.assertFalse(result["visual_fidelity_passed"])
        self.assertTrue({"pixel_diff_exceeds_threshold", "text_region_diff_exceeds_threshold"} <= set(result["blocked_reasons"]))

    def test_generate_visual_fidelity_artifacts_writes_hash_bound_receipts_without_closing_m8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_renderable_visual_fidelity_project(project)

            result = load_fidelity_gate().generate_visual_fidelity_artifacts(project)

            self.assertEqual(result["status"], "structure_only_partial")
            manifest = json.loads((project / "06-check/visual-fidelity/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["baseline_render_receipts"], ["06-check/visual-fidelity/page-001.baseline-render-receipt.json"])
            self.assertEqual(manifest["slide_render_receipts"], ["06-check/visual-fidelity/page-001.slide-render-receipt.json"])
            self.assertEqual(manifest["visual_fidelity_receipts"], ["06-check/visual-fidelity/page-001.visual-fidelity-receipt.json"])
            slide_receipt = json.loads((project / "06-check/visual-fidelity/page-001.slide-render-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(slide_receipt["render_source"], "snapshot_renderer")
            self.assertEqual(slide_receipt["capture_method"], "automated")
            self.assertEqual(slide_receipt["snapshot_json_sha256"], file_sha256(project / "06-check/readback/page-001.snapshot.json"))
            self.assertEqual(slide_receipt["slide_render_png_sha256"], file_sha256(project / "06-check/visual-fidelity/page-001.slide-render.png"))
            self.assertEqual(slide_receipt["renderer_equivalence_receipt_sha256"], file_sha256(project / "06-check/visual-fidelity/page-001.renderer-equivalence-receipt.json"))
            gate = load_fidelity_gate().run_visual_fidelity(project)
            self.assertEqual(gate["status"], "failed")
            self.assertIn("snapshot_renderer_equivalence_failed", issue_codes(gate))

    def test_generate_visual_fidelity_artifacts_records_partial_when_snapshot_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            write_bytes(project / "04-svg/prepared/page-001.svg", b"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\"><text x=\"10\" y=\"40\">A</text></svg>")

            result = load_fidelity_gate().generate_visual_fidelity_artifacts(project)

            self.assertEqual(result["status"], "structure_only_partial")
            self.assertIn("snapshot_json_missing", {issue["code"] for issue in result["issues"]})
            gate = load_fidelity_gate().run_visual_fidelity(project)
            self.assertEqual(gate["status"], "failed")
            self.assertIn("snapshot_json_missing", issue_codes(gate))

    def test_precreate_visual_fidelity_allows_partial_without_closing_m8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            write_bytes(project / "04-svg/prepared/page-001.svg", b"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\"><text x=\"10\" y=\"40\">A</text></svg>")
            load_fidelity_gate().generate_visual_fidelity_artifacts(project)

            result = load_fidelity_gate().run_precreate_visual_fidelity(project)

            self.assertEqual(result["status"], "structure_only_partial")
            self.assertFalse(result["visual_fidelity_passed"])
            self.assertEqual(result["allowed_claim"], "snapshot_structure_fidelity_only")
            self.assertIn("snapshot_json_missing", issue_codes(result))

    def test_precreate_visual_fidelity_does_not_allow_empty_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            build_minimal_visual_fidelity_project(project)
            write_json(
                project / "06-check/visual-fidelity/manifest.json",
                {
                    "schema_version": "svglide-snapshot-visual-fidelity-manifest/v1",
                    "prepared_svgs": ["04-svg/prepared/page-001.svg"],
                    "baseline_render_receipts": [],
                    "slide_render_receipts": [],
                    "visual_fidelity_receipts": [],
                },
            )

            result = load_fidelity_gate().run_precreate_visual_fidelity(project)

            self.assertEqual(result["status"], "failed")
            self.assertIn("baseline_render_receipts_empty", issue_codes(result))


if __name__ == "__main__":
    unittest.main()
