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
        write_json(project / "02-plan/slide_plan.json", {"language": "zh-CN", "theme_id": "dark-clarity", "slides": [{"page": 1, "title": "测试"}]})
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
            "generation_mode": "direct_svg",
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
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
            },
            "signature": {"theme_archetype": "company_ecosystem"},
            "comparisons": [],
            "summary": {"error_count": 0, "warning_count": 0, "comparison_count": 0},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/theme-validate.json",
        {
            "schema_version": "svglide-theme-validate/v1",
            "stage": "theme_validate",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
            },
            "pages": [{"page": 1, "theme_id": "dark-clarity", "status": "passed", "issues": []}],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1, "theme_count": 1},
            "issues": [],
        },
    )
    write_json(
        project / "06-check/theme-adherence.json",
        {
            "schema_version": "svglide-theme-adherence/v1",
            "stage": "theme_adherence",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "theme_validate": "06-check/theme-validate.json",
                "theme_validate_sha256": svglide_quality_gate.file_sha256(project / "06-check/theme-validate.json"),
            },
            "prepared_files": svglide_quality_gate.prepared_file_hashes(project),
            "pages": [{"page": 1, "status": "passed", "issues": []}],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
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


def attach_passing_artboard_receipt(project: Path) -> None:
    artboard_dir = project / "04-svg/artboard"
    artboard_dir.mkdir(parents=True, exist_ok=True)
    (project / "04-svg/artboard/raw").mkdir(parents=True, exist_ok=True)
    (project / "05-preview").mkdir(parents=True, exist_ok=True)
    satori_svg = project / "04-svg/artboard/raw/page-001.satori.svg"
    satori_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540"/></svg>', encoding="utf-8")
    canvas_template_svg = project / "04-svg/artboard/page-001.canvas-template.svg"
    canvas_template_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540"><rect width="960" height="540"/><text x="80" y="120">Title</text></svg>',
        encoding="utf-8",
    )
    (project / "04-svg/page-001.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide">'
        '<foreignObject slide:role="shape" slide:shape-type="text" data-node-id="title" data-source-ref="canvas_spec.content.title" x="80" y="80" width="720" height="72">'
        '<div xmlns="http://www.w3.org/1999/xhtml">Title</div>'
        '</foreignObject>'
        '</svg>',
        encoding="utf-8",
    )
    (project / "04-svg/artboard/page-001.png").write_bytes(b"png")
    write_json(
        project / "04-svg/artboard/page-001.render-metadata.json",
        {"node_version": "v20.0.0", "satori_version": "0.26.0", "resvg_version": "2.6.2", "font_path": "/tmp/font.ttf"},
    )
    write_json(
        project / "04-svg/artboard/page-001.semantic-map.json",
        {
            "version": "svglide-semantic-map/v1",
            "page": 1,
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "semantic_source": "CanvasSpec",
            "content_keys": ["title"],
            "elements": [
                {
                    "element_id": "title",
                    "kind": "text",
                    "role": "title",
                    "source_ref": "canvas_spec.content.title",
                    "text": "Title",
                    "bbox": {"x": 80, "y": 80, "width": 720, "height": 72},
                }
            ],
        },
    )
    write_json(
        project / "04-svg/artboard/page-001.node-layout-map.json",
        {
            "version": "svglide-node-layout-map/v1",
            "page": 1,
            "source": "measured-layout-observation",
            "observation_source": "satori_on_node_detected",
            "threshold_px": 8,
            "drift": {"status": "passed", "max_px": 0, "threshold_px": 8, "missing_count": 0},
            "nodes": [
                {
                    "id": "title",
                    "kind": "text",
                    "x": 80,
                    "y": 80,
                    "width": 720,
                    "height": 72,
                    "text": "Title",
                    "expected_bbox": {"x": 80, "y": 80, "width": 720, "height": 72},
                    "measured_bbox": {"x": 80, "y": 80, "width": 720, "height": 72},
                    "drift_px": 0,
                    "observation_source": "satori_on_node_detected",
                }
            ],
        },
    )
    (project / "05-preview/contact-sheet.png").write_bytes(b"contact")
    source_hash = svglide_quality_gate.file_sha256(project / "04-svg/page-001.svg")
    template_registry_sha256 = "template-registry-hash"
    theme_registry_sha256 = "theme-registry-hash"
    font_hashes = [{"path": "/tmp/font.ttf", "sha256": "font-hash"}]
    semantic_map_sha256 = svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.semantic-map.json")
    write_json(
        project / "04-svg/artboard/page-001.receipt.json",
        {
            "version": "svglide-artboard-receipt/v1",
            "stage": "generate_svg",
            "status": "passed",
            "page": 1,
            "canvas_spec_path": "02-plan/slide_plan.json#/slides/0/canvas_spec",
            "canvas_spec_sha256": "test-canvas-spec",
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "template_registry": "skills/lark-slides/references/svglide-template-registry.json",
            "template_registry_sha256": template_registry_sha256,
            "theme_registry": "skills/lark-slides/scripts/artboard_renderer/themes/registry.json",
            "theme_registry_sha256": theme_registry_sha256,
            "theme_files": ["skills/lark-slides/scripts/artboard_renderer/themes/dark-clarity.json"],
            "node_version": "v20.0.0",
            "satori_version": "0.26.0",
            "resvg_version": "2.6.2",
            "font_hashes": font_hashes,
            "renderer": {"name": "satori-resvg-p0", "engine": "satori-node", "actual_satori_package": True},
            "satori_svg": "04-svg/artboard/raw/page-001.satori.svg",
            "satori_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/raw/page-001.satori.svg"),
            "png": "04-svg/artboard/page-001.png",
            "png_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.png"),
            "render_metadata": "04-svg/artboard/page-001.render-metadata.json",
            "render_metadata_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.render-metadata.json"),
            "canvas_template_svg": "04-svg/artboard/page-001.canvas-template.svg",
            "canvas_template_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.canvas-template.svg"),
            "compiler_input": "04-svg/artboard/page-001.semantic-map.json",
            "compiler_input_sha256": semantic_map_sha256,
            "input_semantic_hash": semantic_map_sha256,
            "semantic_map": "04-svg/artboard/page-001.semantic-map.json",
            "semantic_map_sha256": semantic_map_sha256,
            "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
            "node_layout_map_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.node-layout-map.json"),
            "svglide_svg": "04-svg/page-001.svg",
            "svglide_svg_sha256": source_hash,
            "compiler": {"semantic_source": "CanvasSpec", "compiler_input": "SemanticMapIR", "satori_svg_usage": "preview_only", "input_semantic_hash": semantic_map_sha256},
        },
    )
    receipt = json.loads((project / "receipts/generate_svg.json").read_text(encoding="utf-8"))
    receipt["generation_mode"] = "artboard_satori"
    receipt["artboard_receipts"] = ["04-svg/artboard/page-001.receipt.json"]
    receipt["artboard_additional_receipts"] = [
        "receipts/canvas-spec-validate.json",
        "receipts/artboard-render.json",
        "receipts/satori-bridge.json",
    ]
    receipt["canvas_spec_validate"] = "06-check/canvas-spec-validate.json"
    receipt["artboard_render_receipt"] = "receipts/artboard-render.json"
    receipt["satori_bridge_receipt"] = "receipts/satori-bridge.json"
    receipt["template_fit_check"] = "06-check/template-fit.json"
    receipt["contact_sheet"] = {
        "path": "05-preview/contact-sheet.png",
        "sha256": svglide_quality_gate.file_sha256(project / "05-preview/contact-sheet.png"),
    }
    write_json(project / "receipts/generate_svg.json", receipt)
    write_json(
        project / "06-check/artboard-package-check.json",
        {
            "version": "svglide-artboard-package-check/v1",
            "stage": "package_check",
            "status": "passed",
            "action": "create_live",
            "summary": {"error_count": 0, "warning_count": 0, "runtime_check_count": 0},
            "runtime_checks": [],
            "issues": [],
        },
    )
    write_json(
        project / "06-check/canvas-spec-validate.json",
        {
            "schema_version": "svglide-canvas-spec-validate/v1",
            "stage": "canvas-spec-validate",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "template_registry_sha256": template_registry_sha256,
                "theme_registry_sha256": theme_registry_sha256,
            },
            "pages": [],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
            "issues": [],
        },
    )
    write_json(project / "receipts/canvas-spec-validate.json", json.loads((project / "06-check/canvas-spec-validate.json").read_text(encoding="utf-8")))
    write_json(
        project / "receipts/artboard-render.json",
        {
            "version": "svglide-artboard-render/v1",
            "stage": "artboard-render",
            "status": "passed",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "template_registry_sha256": template_registry_sha256,
                "theme_registry_sha256": theme_registry_sha256,
                "canvas_spec_validate": "receipts/canvas-spec-validate.json",
                "canvas_spec_validate_sha256": svglide_quality_gate.file_sha256(project / "receipts/canvas-spec-validate.json"),
            },
            "pages": [
                {
                    "page": 1,
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                    "satori_version": "0.26.0",
                    "resvg_version": "2.6.2",
                    "font_hashes": font_hashes,
                    "satori_svg": "04-svg/artboard/raw/page-001.satori.svg",
                    "satori_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/raw/page-001.satori.svg"),
                    "png": "04-svg/artboard/page-001.png",
                    "png_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.png"),
                    "render_metadata": "04-svg/artboard/page-001.render-metadata.json",
                    "render_metadata_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.render-metadata.json"),
                    "canvas_template_svg": "04-svg/artboard/page-001.canvas-template.svg",
                    "canvas_template_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.canvas-template.svg"),
                    "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
                    "node_layout_map_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.node-layout-map.json"),
                }
            ],
            "contact_sheet": receipt["contact_sheet"],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
        },
    )
    write_json(
        project / "receipts/satori-bridge.json",
        {
            "version": "svglide-satori-bridge/v1",
            "stage": "satori-bridge",
            "status": "passed",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "artboard_render": "receipts/artboard-render.json",
                "artboard_render_sha256": svglide_quality_gate.file_sha256(project / "receipts/artboard-render.json"),
            },
            "pages": [
                {
                    "page": 1,
                    "semantic_source": "CanvasSpec",
                    "semantic_map": "04-svg/artboard/page-001.semantic-map.json",
                    "semantic_map_sha256": semantic_map_sha256,
                    "input_semantic_hash": semantic_map_sha256,
                    "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
                    "node_layout_map_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.node-layout-map.json"),
                    "canvas_template_svg": "04-svg/artboard/page-001.canvas-template.svg",
                    "canvas_template_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.canvas-template.svg"),
                    "compiler_input": "04-svg/artboard/page-001.semantic-map.json",
                    "compiler_input_sha256": semantic_map_sha256,
                    "compiler_input_type": "SemanticMapIR",
                    "satori_svg_usage": "preview_only",
                    "satori_svg": "04-svg/artboard/raw/page-001.satori.svg",
                    "satori_svg_sha256": svglide_quality_gate.file_sha256(project / "04-svg/artboard/raw/page-001.satori.svg"),
                    "svglide_svg": "04-svg/page-001.svg",
                    "svglide_svg_sha256": source_hash,
                }
            ],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
        },
    )
    write_json(
        project / "06-check/template-fit.json",
        {
            "schema_version": "svglide-template-fit/v1",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": svglide_quality_gate.file_sha256(project / "02-plan/slide_plan.json"),
                "generator_receipt": "receipts/generate_svg.json",
                "generator_receipt_sha256": svglide_quality_gate.file_sha256(project / "receipts/generate_svg.json"),
                "artboard_receipts": ["04-svg/artboard/page-001.receipt.json"],
                "template_registry_sha256": template_registry_sha256,
                "theme_registry_sha256": theme_registry_sha256,
            },
            "pages": [],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
            "issues": [],
        },
    )
    write_json(project / "receipts/template-fit-check.json", json.loads((project / "06-check/template-fit.json").read_text(encoding="utf-8")))


def refresh_artboard_node_layout_hashes(project: Path) -> None:
    node_layout_sha = svglide_quality_gate.file_sha256(project / "04-svg/artboard/page-001.node-layout-map.json")
    for receipt_rel in [
        "04-svg/artboard/page-001.receipt.json",
        "receipts/artboard-render.json",
        "receipts/satori-bridge.json",
    ]:
        receipt_path = project / receipt_rel
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if "node_layout_map_sha256" in receipt:
            receipt["node_layout_map_sha256"] = node_layout_sha
        for page in receipt.get("pages", []) if isinstance(receipt.get("pages"), list) else []:
            if isinstance(page, dict) and page.get("node_layout_map") == "04-svg/artboard/page-001.node-layout-map.json":
                page["node_layout_map_sha256"] = node_layout_sha
        write_json(receipt_path, receipt)
    satori_bridge = project / "receipts/satori-bridge.json"
    render_receipt = project / "receipts/artboard-render.json"
    payload = json.loads(satori_bridge.read_text(encoding="utf-8"))
    payload["inputs"]["artboard_render_sha256"] = svglide_quality_gate.file_sha256(render_receipt)
    write_json(satori_bridge, payload)


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

    def test_quality_gate_is_independent_from_visual_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            (project / "04-svg/prepared").mkdir(parents=True)
            (project / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
            write_passing_semantic_review(project)
            write_json(
                project / "06-check/visual-acceptance.json",
                {
                    "schema_version": "svglide-visual-acceptance/v1",
                    "status": "failed",
                    "issues": [{"code": "layout_overlap"}],
                },
            )

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "passed")
            self.assertNotIn("visual_acceptance", result["inputs"])
            self.assertNotIn("visual-acceptance", {check["name"] for check in result["checks"]})

    def test_quality_gate_requires_theme_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            (project / "06-check/theme-adherence.json").unlink()

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            missing = [check for check in result["checks"] if check["name"] == "theme-adherence"][0]
            self.assertEqual(missing["status"], "missing")
            self.assertIn("theme_adherence", result["inputs"])

    def test_quality_gate_fails_when_theme_adherence_theme_validate_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            theme_validate = json.loads((project / "06-check/theme-validate.json").read_text(encoding="utf-8"))
            theme_validate["checked_at"] = "2026-06-21T00:00:00+08:00"
            write_json(project / "06-check/theme-validate.json", theme_validate)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("theme_adherence_theme_validate_stale", failed_codes)

    def test_quality_gate_direct_svg_ignores_artboard_package_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            write_json(
                project / "06-check/artboard-package-check.json",
                {
                    "version": "svglide-artboard-package-check/v1",
                    "stage": "package_check",
                    "status": "failed",
                    "action": "repair_and_rerun",
                    "summary": {"error_count": 1, "warning_count": 0, "runtime_check_count": 0},
                    "issues": [{"code": "should_be_ignored", "message": "direct_svg does not require artboard package"}],
                },
            )

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "passed")
            self.assertNotIn("artboard_package_check", result["inputs"])
            self.assertNotIn("artboard-package-check", {check["name"] for check in result["checks"]})

    def test_quality_gate_artboard_satori_requires_package_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0, "warning_count": 1}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0, "warning_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            (project / "06-check/artboard-package-check.json").unlink()

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            missing = [check for check in result["checks"] if check["name"] == "artboard-package-check"][0]
            self.assertEqual(missing["status"], "missing")
            self.assertEqual(result["inputs"]["generation_mode"], "artboard_satori")
            self.assertIn("artboard_package_check", result["inputs"])

    def test_online_readiness_counts_local_file_assets_as_real_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(
                project / "03-assets/asset-manifest.json",
                {
                    "status": "passed",
                    "summary": {
                        "acquired_count": 1,
                        "local_file_count": 3,
                        "mapped_token_count": 2,
                        "fallback_count": 0,
                    },
                },
            )

            result = svglide_quality_gate.load_online_readiness(project, profile="production")

            self.assertEqual(result["asset_real_coverage"], 6)
            self.assertEqual(result["asset_acquired_count"], 1)
            self.assertEqual(result["asset_local_file_count"], 3)
            self.assertEqual(result["asset_mapped_token_count"], 2)

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

    def test_quality_gate_requires_artboard_receipts_for_artboard_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            receipt = json.loads((project / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            receipt["generation_mode"] = "artboard_satori"
            write_json(project / "receipts/generate_svg.json", receipt)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_receipts_missing", failed_codes)

    def test_quality_gate_fails_when_artboard_receipt_artifact_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            (project / "04-svg/artboard/raw/page-001.satori.svg").write_text("<svg changed='true'/>", encoding="utf-8")

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_artifact_stale", failed_codes)

    def test_quality_gate_rejects_raw_satori_as_artboard_compiler_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            receipt_path = project / "04-svg/artboard/page-001.receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["compiler"]["compiler_input"] = "RawSatoriSVG"
            receipt["compiler"]["satori_svg_usage"] = "compiler_input"
            write_json(receipt_path, receipt)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_compiler_input_invalid", failed_codes)
            self.assertIn("generator_artboard_compiler_satori_usage_invalid", failed_codes)

    def test_quality_gate_fails_when_artboard_compiler_input_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            semantic_map = json.loads((project / "04-svg/artboard/page-001.semantic-map.json").read_text(encoding="utf-8"))
            semantic_map["elements"][0]["text"] = "Changed semantic input"
            write_json(project / "04-svg/artboard/page-001.semantic-map.json", semantic_map)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_artifact_stale", failed_codes)
            self.assertIn("satori_bridge_compiler_input_stale", failed_codes)

    def test_quality_gate_fails_when_node_layout_drift_exceeds_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            node_layout_path = project / "04-svg/artboard/page-001.node-layout-map.json"
            node_layout = json.loads(node_layout_path.read_text(encoding="utf-8"))
            node_layout["drift"] = {"status": "failed", "max_px": 48, "threshold_px": 8, "missing_count": 0}
            node_layout["nodes"][0]["x"] = 128
            node_layout["nodes"][0]["measured_bbox"]["x"] = 128
            node_layout["nodes"][0]["drift_px"] = 48
            write_json(node_layout_path, node_layout)
            refresh_artboard_node_layout_hashes(project)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_node_layout_drift_exceeds_threshold", failed_codes)

    def test_quality_gate_validates_artboard_receipt_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_passing_semantic_review(project)
            attach_passing_artboard_receipt(project)
            receipt_path = project / "04-svg/artboard/page-001.receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt.pop("version")
            write_json(receipt_path, receipt)

            result = svglide_quality_gate.run_quality_gate(project)

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("generator_artboard_receipt_schema_invalid", failed_codes)

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

    def test_quality_gate_blocks_strict_profile_when_image_jobs_have_no_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(
                project / "03-assets/asset-manifest.json",
                {
                    "version": "svglide-assets/v1",
                    "status": "passed",
                    "summary": {
                        "contract_count": 1,
                        "error_count": 0,
                        "mapped_token_count": 0,
                        "local_file_count": 0,
                        "acquired_count": 0,
                        "fallback_count": 0,
                        "image_job_count": 1,
                    },
                },
            )
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project, profile="production")

            self.assertEqual(result["status"], "failed")
            failed_codes = {
                issue["code"]
                for check in result["checks"]
                for issue in check["issues"]
            }
            self.assertIn("visual_asset_contracts_unfulfilled", failed_codes)

    def test_quality_gate_allows_unfulfilled_image_jobs_in_preview_only_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            write_json(project / "06-check/preflight.json", {"summary": {"error_count": 0}})
            write_json(project / "06-check/preview-lint.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(project / "06-check/aesthetic-review.json", {"summary": {"error_count": 0}, "action": "create_live"})
            write_json(
                project / "03-assets/asset-manifest.json",
                {
                    "version": "svglide-assets/v1",
                    "status": "passed",
                    "summary": {
                        "contract_count": 1,
                        "error_count": 0,
                        "mapped_token_count": 0,
                        "local_file_count": 0,
                        "acquired_count": 0,
                        "fallback_count": 0,
                        "image_job_count": 1,
                    },
                },
            )
            write_passing_semantic_review(project)

            result = svglide_quality_gate.run_quality_gate(project, profile="preview_only")

            self.assertEqual(result["status"], "passed")

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
