# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import contextlib
import html
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svg_preflight
import svglide_project_runner as runner


class SVGlideProjectRunnerTest(unittest.TestCase):
    def test_local_real_preview_profile_targets_visual_acceptance(self) -> None:
        self.assertEqual(runner.resolve_run_target(None, "local_real_preview"), "visual_acceptance")

    def test_local_real_preview_assets_args_preserve_explicit_disable_flags(self) -> None:
        saved_options = dict(runner.RUNNER_OPTIONS)
        try:
            runner.RUNNER_OPTIONS.update(
                {
                    "network_policy": "online",
                    "offline": False,
                    "no_image_search": True,
                    "no_ai_image": True,
                    "asset_provider": "auto",
                    "image_backend": "auto",
                }
            )

            args = runner.asset_option_args(profile="local_real_preview")

            self.assertIn("--profile", args)
            self.assertEqual(args[args.index("--profile") + 1], "local_real_preview")
            self.assertIn("--no-image-search", args)
            self.assertIn("--no-ai-image", args)
            self.assertIn("--network-policy", args)
            self.assertEqual(args[args.index("--network-policy") + 1], "online")
        finally:
            runner.RUNNER_OPTIONS.clear()
            runner.RUNNER_OPTIONS.update(saved_options)

    def write_plan(self, project_root: Path) -> None:
        (project_root / "02-plan").mkdir(parents=True, exist_ok=True)
        (project_root / "02-plan/slide_plan.json").write_text(
            json.dumps(
                {
                    "route": "svglide-svg",
                    "deck_intent": "smoke",
                    "language": "zh-CN",
                    "audience": "企业管理层",
                    "deck_structure": ["cover", "content", "closing"],
                    "template_family_selection": {
                        "enabled": True,
                        "source": "beautiful-html-template-families",
                        "selected_template_id": "blue-professional",
                        "candidate_template_ids": ["blue-professional", "signal", "raw-grid"],
                        "selection_reason": "用于稳定测试",
                    },
                    "loaded_rule_set": ["skills/lark-slides/references/svglide-svg-private.rules.json"],
                    "plan_path": "02-plan/slide_plan.json",
                    "quality_gates": {
                        "no_text_overflow": True,
                        "no_debug_guides": True,
                        "no_xml_like_pages": True,
                    },
                    "art_direction": {
                        "cover_treatment": "中文封面",
                        "section_divider_treatment": "章节过渡",
                        "closing_treatment": "中文总结",
                        "deck_motif": "测试母题",
                        "svg_native_moments": ["结构化开场", "信息图正文", "总结强调"],
                    },
                    "visual_identity": {
                        "theme_archetype": "company_ecosystem",
                        "design_dna": {
                            "palette": "light neutral test palette",
                            "layout_motif": "测试生态墙",
                            "shape_language": "低圆角信息块",
                            "image_treatment": "图片只做背景信号",
                            "component_bias": "生态墙、结构卡片、总结条",
                            "theme_visual_anchors": ["测试产品墙", "测试组织网络", "测试结论条"],
                        },
                        "forbidden_reuse": {"recent_decks": 5, "avoid_default_skeleton": True},
                        "distinctness_target": {"palette_overlap_max": 0.67, "renderer_sequence_similarity_max": 0.75},
                    },
                    "slides": [
                        {
                            "page": 1,
                            "page_type": "cover",
                            "section": "开场",
                            "role": "thesis",
                            "title": "测试标题",
                            "key_message": "测试主结论",
                            "body_points": ["测试要点一", "测试要点二"],
                            "source_refs": ["source:item-001"],
                            "renderer_id": "cover_full_bleed",
                            "layout_family": "cover",
                            "visual_recipe": "test-recipe",
                            "visual_intent": "验证 runner",
                            "visual_focal_point": "标题",
                            "visual_signature": "稳定结构",
                            "svg_effects": ["text"],
                            "required_primitives": ["text"],
                            "svg_primitives": ["text"],
                            "xml_like_risk": "low",
                            "content_density_contract": "medium",
                            "risk_flags": [],
                            "source_policy": "source-backed",
                            "template_variant": "cover",
                            "semantic_blocks": [
                                {"block_id": "title", "type": "title", "content": "测试标题"},
                                {"block_id": "message", "type": "finding", "content": "测试主结论"},
                            ],
                            "component_selection": [
                                {"component_id": "title_block", "binds": ["title"]},
                                {"component_id": "finding_callout", "binds": ["message"]},
                            ],
                            "asset_strategy": {"strategy_id": "structured_fallback", "no_fake_data": True},
                        },
                        {
                            "page": 2,
                            "page_type": "content",
                            "section": "正文",
                            "role": "evidence",
                            "title": "测试正文",
                            "key_message": "正文主结论",
                            "body_points": ["测试证据一", "测试证据二"],
                            "source_refs": ["source:item-001"],
                            "renderer_id": "ecosystem_wall",
                            "layout_family": "ecosystem",
                            "visual_recipe": "test-recipe",
                            "visual_intent": "验证 runner",
                            "visual_focal_point": "正文",
                            "visual_signature": "稳定结构",
                            "svg_effects": ["text"],
                            "required_primitives": ["text"],
                            "svg_primitives": ["text"],
                            "xml_like_risk": "low",
                            "content_density_contract": "medium",
                            "risk_flags": [],
                            "source_policy": "source-backed",
                            "template_variant": "case_evidence",
                            "semantic_blocks": [
                                {"block_id": "title", "type": "title", "content": "测试正文"},
                                {"block_id": "evidence", "type": "evidence", "content": "正文主结论"},
                            ],
                            "component_selection": [
                                {"component_id": "title_block", "binds": ["title"]},
                                {"component_id": "evidence_table", "binds": ["evidence"]},
                            ],
                            "asset_strategy": {"strategy_id": "structured_fallback", "no_fake_data": True},
                        },
                        {
                            "page": 3,
                            "page_type": "closing",
                            "section": "结尾",
                            "role": "takeaway",
                            "title": "测试结论",
                            "key_message": "结论主线",
                            "body_points": ["后续动作一", "后续动作二"],
                            "source_refs": ["source:item-001"],
                            "renderer_id": "closing_cta",
                            "layout_family": "closing",
                            "visual_recipe": "test-recipe",
                            "visual_intent": "验证 runner",
                            "visual_focal_point": "结论",
                            "visual_signature": "稳定结构",
                            "svg_effects": ["text"],
                            "required_primitives": ["text"],
                            "svg_primitives": ["text"],
                            "xml_like_risk": "low",
                            "content_density_contract": "medium",
                            "risk_flags": [],
                            "source_policy": "source-backed",
                            "template_variant": "closing",
                            "semantic_blocks": [
                                {"block_id": "title", "type": "title", "content": "测试结论"},
                                {"block_id": "action", "type": "action", "content": "结论主线"},
                            ],
                            "component_selection": [
                                {"component_id": "title_block", "binds": ["title"]},
                                {"component_id": "action_list", "binds": ["action"]},
                            ],
                            "asset_strategy": {"strategy_id": "structured_fallback", "no_fake_data": True},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def write_artboard_plan(self, project_root: Path) -> None:
        self.write_plan(project_root)
        plan = json.loads((project_root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
        plan["generation_mode"] = "artboard_satori"
        first_slide = plan["slides"][0]
        first_slide["renderer_id"] = "artboard_satori.cover-hero"
        first_slide["layout_family"] = "cover"
        first_slide["visual_recipe"] = "artboard-cover-hero"
        first_slide["required_primitives"] = ["text", "rect", "circle"]
        first_slide["svg_primitives"] = ["foreignObject", "rect", "circle"]
        first_slide["canvas_spec"] = {
            "version": "svglide-canvas-spec/v1",
            "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
            "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
            "template_id": "cover-hero",
            "theme_id": "dark-clarity",
            "theme": {
                "colors": {
                    "background": "#0F172A",
                    "panel": "#111827",
                    "primary": "#38BDF8",
                    "accent": "#A78BFA",
                    "text": "#F8FAFC",
                    "muted": "#CBD5E1",
                }
            },
            "content": {
                "eyebrow": "ARTBOARD P0A",
                "title": "受控画板生成",
                "subtitle": "CanvasSpec 驱动模板，输出可进入 SVGlide 后续链路的协议 SVG。",
                "chips": ["CanvasSpec", "Satori Preview", "SVGlide SVG"],
            },
            "semantic_elements": [
                {
                    "element_id": "title",
                    "kind": "text",
                    "role": "title",
                    "source_ref": "canvas_spec.content.title",
                    "bbox": {"x": 84, "y": 142, "width": 628, "height": 142},
                }
            ],
            "quality_constraints": {
                "max_title_lines": 2,
                "min_font_size": 18,
                "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
            },
        }
        plan["slides"] = [first_slide]
        (project_root / "02-plan/slide_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def write_selection_ready_plan(self, project_root: Path, brief: str) -> None:
        self.write_plan(project_root)
        plan = json.loads((project_root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
        plan["title"] = brief
        plan["topic"] = brief
        plan["style_preset"] = "cobalt_bloom"
        plan["loaded_rule_set"] = sorted(svg_preflight.SVG_PRIVATE_REQUIRED_RULE_FILES)
        for slide in plan["slides"]:
            slide["canvas_spec"] = {}
            slide["visual_recipe"] = "geometric_composition"
            slide["svg_effects"] = ["path"]
            slide["required_primitives"] = ["geometric_shape", "path"]
            slide["svg_primitives"] = ["geometric_shape", "path"]
            slide["asset_contract"] = "none_required"
        (project_root / "02-plan/slide_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False),
            encoding="utf-8",
        )

    def write_instruction(self, project_root: Path, brief: str) -> None:
        (project_root / "00-input/instruction.json").write_text(
            json.dumps(
                {
                    "version": "svglide-instruction/v1",
                    "raw_prompt": brief,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def write_plan_confirmation(self, project_root: Path) -> None:
        plan = project_root / "02-plan/slide_plan.json"
        payload = {
            "version": "svglide-plan-confirmation/v1",
            "status": "confirmed",
            "confirmed_by": "user",
            "confirmed_at": "2026-06-18T00:00:00+08:00",
            "plan_path": "02-plan/slide_plan.json",
            "plan_sha256": runner.file_sha256(plan),
        }
        lock = project_root / "02-plan/svglide.lock.json"
        if lock.exists():
            payload["lock_path"] = "02-plan/svglide.lock.json"
            payload["lock_sha256"] = runner.file_sha256(lock)
        (project_root / "02-plan/plan-confirmation.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def write_evidence(self, project_root: Path) -> None:
        (project_root / "source").mkdir(parents=True, exist_ok=True)
        (project_root / "source/evidence.json").write_text(
            json.dumps(
                {
                    "schema_version": "svglide-evidence/v1",
                    "source_status": "ready",
                    "items": [
                        {"id": "item-001", "text": "第一条中文证据内容足够长，用于支撑测试页面。"},
                        {"id": "item-002", "text": "第二条中文证据内容足够长，用于验证来源闭环。"},
                        {"id": "item-003", "text": "第三条中文证据内容足够长，用于避免资料过薄。"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def run_source(self, project_root: Path) -> None:
        self.write_evidence(project_root)
        runner.run_stage(project_root, "source")

    def make_selection_project(self, tmpdir: str, deck_id: str, brief: str) -> Path:
        plan_root = Path(tmpdir) / ".lark-slides/plan"
        result = runner.init_project(deck_id, brief[:40] or deck_id, plan_root=plan_root)
        project_root = Path(result["project_root"])
        self.write_instruction(project_root, brief)
        self.write_selection_ready_plan(project_root, brief)
        return project_root

    def write_protocol_fixture_svgs(self, project_root: Path) -> None:
        plan = json.loads((project_root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
        colors = plan["project_palette"]["colors"]
        background = colors["background"]
        surface = colors["surface"]
        text = colors["text"]
        primary = colors["primary"]
        accent = colors["accent"]
        muted = colors["muted"]
        for slide in plan["slides"]:
            page = int(slide["page"])
            title = html.escape(slide["title"])
            key_message = html.escape(slide["key_message"])
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" slide:role="slide" slide:contract-version="svglide-authoring-contract/v1" width="960" height="540" viewBox="0 0 960 540">
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="{background}"/>
  <rect slide:role="shape" x="48" y="48" width="864" height="444" fill="{surface}"/>
  <path slide:role="shape" d="M72 248 L836 248 L796 288 L112 288 Z" fill="{primary}" opacity="0.10"/>
  <foreignObject id="title" data-source-ref="slide_plan.slides[{page}].title" slide:role="shape" slide:shape-type="text" x="72" y="82" width="760" height="70"><div xmlns="http://www.w3.org/1999/xhtml" style="font-size:34px;font-weight:700;color:{text};line-height:1.2">{title}</div></foreignObject>
  <foreignObject id="message" data-source-ref="slide_plan.slides[{page}].key_message" slide:role="shape" slide:shape-type="text" x="72" y="168" width="740" height="60"><div xmlns="http://www.w3.org/1999/xhtml" style="font-size:22px;font-weight:500;color:{text};line-height:1.35">{key_message}</div></foreignObject>
  <rect slide:role="shape" x="72" y="310" width="210" height="96" fill="{primary}" opacity="0.14"/>
  <rect slide:role="shape" x="306" y="310" width="210" height="96" fill="{accent}" opacity="0.16"/>
  <rect slide:role="shape" x="540" y="310" width="210" height="96" fill="{muted}" opacity="0.14"/>
</svg>'''
            (project_root / f"04-svg/page-{page:03d}.svg").write_text(svg, encoding="utf-8")

    def make_project(self, tmpdir: str) -> Path:
        plan_root = Path(tmpdir) / ".lark-slides/plan"
        result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
        project_root = Path(result["project_root"])
        self.write_plan(project_root)
        self.run_source(project_root)
        (project_root / "03-assets/asset-manifest.json").write_text(
            json.dumps(
                {
                    "version": "svglide-assets/v1",
                    "status": "passed",
                    "source_receipt_sha256": runner.file_sha256(project_root / "source/source-receipt.json"),
                    "summary": {"error_count": 0},
                }
            ),
            encoding="utf-8",
        )
        (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
        (project_root / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
        source_files = runner.source_file_hashes(project_root)
        (project_root / "04-svg/page-001.receipt.json").write_text(
            json.dumps(
                {
                    "version": "svglide-page-generation/v1",
                    "stage": "generate_svg",
                    "page": 1,
                    "source_svg": source_files[0]["path"],
                    "source_sha256": source_files[0]["sha256"],
                    "plan_sha256": runner.file_sha256(project_root / "02-plan/slide_plan.json"),
                    "evidence_sha256": runner.file_sha256(project_root / "source/evidence.json"),
                }
            ),
            encoding="utf-8",
        )
        (project_root / "receipts/generate_svg.json").write_text(
            json.dumps(
                {
                    "stage": "generate_svg",
                    "status": "passed",
                    "generator_mode": "external",
                    "generation_mode": "direct_svg",
                    "generated_files": source_files,
                    "page_receipts": ["04-svg/page-001.receipt.json"],
                    "plan_sha256": runner.file_sha256(project_root / "02-plan/slide_plan.json"),
                    "evidence_sha256": runner.file_sha256(project_root / "source/evidence.json"),
                    "asset_manifest_sha256": runner.file_sha256(project_root / "03-assets/asset-manifest.json"),
                    "source_receipt_sha256": runner.file_sha256(project_root / "source/source-receipt.json"),
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
                }
            ),
            encoding="utf-8",
        )
        theme_validate = {
            "schema_version": "svglide-theme-validate/v1",
            "stage": "theme_validate",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": runner.file_sha256(project_root / "02-plan/slide_plan.json"),
            },
            "pages": [{"page": 1, "theme_id": "dark-clarity", "status": "passed", "issues": []}],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1, "theme_count": 1},
            "issues": [],
        }
        (project_root / "06-check/theme-validate.json").write_text(json.dumps(theme_validate), encoding="utf-8")
        theme_adherence = {
            "schema_version": "svglide-theme-adherence/v1",
            "stage": "theme_adherence",
            "status": "passed",
            "action": "create_live",
            "inputs": {
                "slide_plan": "02-plan/slide_plan.json",
                "plan_sha256": runner.file_sha256(project_root / "02-plan/slide_plan.json"),
                "theme_validate": "06-check/theme-validate.json",
                "theme_validate_sha256": runner.file_sha256(project_root / "06-check/theme-validate.json"),
            },
            "prepared_files": runner.prepared_file_hashes(project_root),
            "pages": [{"page": 1, "status": "passed", "issues": []}],
            "summary": {"error_count": 0, "warning_count": 0, "page_count": 1},
            "issues": [],
        }
        (project_root / "06-check/theme-adherence.json").write_text(json.dumps(theme_adherence), encoding="utf-8")
        (project_root / "06-check/visual-distinctness.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "action": "create_live",
                    "inputs": {
                        "slide_plan": "02-plan/slide_plan.json",
                        "plan_sha256": runner.file_sha256(project_root / "02-plan/slide_plan.json"),
                    },
                    "summary": {"error_count": 0},
                    "issues": [],
                }
            ),
            encoding="utf-8",
        )
        (project_root / "06-check/quality-gate.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "inputs": {
                        "generation_mode": "direct_svg",
                        "generator_receipt": "receipts/generate_svg.json",
                        "visual_distinctness": "06-check/visual-distinctness.json",
                        "theme_validate": "06-check/theme-validate.json",
                        "theme_adherence": "06-check/theme-adherence.json",
                    },
                    "input_hashes": {
                        "generator_receipt": runner.file_sha256(project_root / "receipts/generate_svg.json"),
                        "visual_distinctness": runner.file_sha256(project_root / "06-check/visual-distinctness.json"),
                        "theme_validate": runner.file_sha256(project_root / "06-check/theme-validate.json"),
                        "theme_adherence": runner.file_sha256(project_root / "06-check/theme-adherence.json"),
                    },
                    "prepared_files": runner.prepared_file_hashes(project_root),
                    "checks": [
                        {"name": "visual-distinctness", "status": "passed"},
                        {"name": "theme-validate", "status": "passed"},
                        {"name": "theme-adherence", "status": "passed"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return project_root

    def test_selection_pipeline_runs_three_fixture_briefs_to_quality_gate(self) -> None:
        briefs = [
            ("selection_internal_review", "生成一份内部业务复盘，高管经营看板，包含指标、趋势和行动项"),
            ("selection_brand_ai", "生成一份主题为智谱和 MiniMax 的 slide，从头走到本地预览"),
            ("selection_unknown_topic", "一个不存在于模板库的主题：量子陶瓷供应链"),
        ]
        saved_options = dict(runner.RUNNER_OPTIONS)
        try:
            runner.RUNNER_OPTIONS.update(
                {
                    "network_policy": "fixture",
                    "offline": False,
                    "no_online_research": False,
                    "no_image_search": True,
                    "no_ai_image": True,
                    "refresh_online": False,
                    "asset_provider": "auto",
                    "image_backend": "none",
                }
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                for deck_id, brief in briefs:
                    project_root = self.make_selection_project(tmpdir, deck_id, brief)
                    for stage in [
                        "source",
                        "select_style",
                        "plan",
                        "strategy_review",
                        "theme_validate",
                        "palette_review",
                        "selection_review",
                        "plan_bundle_review",
                    ]:
                        runner.run_stage(project_root, stage, profile="preview_only")
                    runner.run_stage(project_root, "package_check", profile="preview_only")
                    runner.run_stage(project_root, "assets", profile="preview_only")
                    self.write_protocol_fixture_svgs(project_root)
                    for stage in [
                        "generate_svg",
                        "contract_compile",
                        "prepare",
                        "preview",
                        "preflight",
                        "preview_lint",
                        "aesthetic_review",
                        "chart_verify",
                        "semantic_review",
                        "runtime_review",
                        "visual_distinctness_review",
                        "theme_adherence",
                        "quality_gate",
                    ]:
                        runner.run_stage(project_root, stage, profile="preview_only")

                    plan = json.loads((project_root / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
                    palette = json.loads((project_root / "02-plan/palette-selection.json").read_text(encoding="utf-8"))
                    selection = json.loads((project_root / "02-plan/theme-template-selection.json").read_text(encoding="utf-8"))
                    self.assertEqual(plan["project_palette"], palette["project_palette"])
                    self.assertEqual(plan["project_theme"]["base_theme_id"], selection["selected_theme_id"])
                    template_candidates = {item["template_id"] for item in selection["template_candidates"]}
                    theme_candidates = {item["theme_id"] for item in selection["theme_candidates"]}
                    for slide in plan["slides"]:
                        spec = slide["canvas_spec"]
                        self.assertIn(spec["template_id"], template_candidates)
                        self.assertIn(spec["theme_id"], theme_candidates)
                        self.assertIn("selection_trace", spec)
                    self.assertEqual(
                        json.loads((project_root / "06-check/palette-review.json").read_text(encoding="utf-8"))["status"],
                        "passed",
                    )
                    self.assertEqual(
                        json.loads((project_root / "06-check/theme-template-selection-review.json").read_text(encoding="utf-8"))["status"],
                        "passed",
                    )
                    self.assertEqual(
                        json.loads((project_root / "06-check/plan-bundle-review.json").read_text(encoding="utf-8"))["status"],
                        "passed",
                    )
                    self.assertNotIn("confirm_plan", runner.load_state(project_root)["stages"])
                    self.assertEqual(
                        json.loads((project_root / "06-check/quality-gate.json").read_text(encoding="utf-8"))["status"],
                        "passed",
                    )
        finally:
            runner.RUNNER_OPTIONS.clear()
            runner.RUNNER_OPTIONS.update(saved_options)

    def make_artboard_visual_project(self, tmpdir: str) -> Path:
        project_root = self.make_project(tmpdir)
        self.write_artboard_plan(project_root)
        artboard_dir = project_root / "04-svg/artboard"
        artboard_dir.mkdir(parents=True, exist_ok=True)
        (project_root / "05-preview").mkdir(parents=True, exist_ok=True)
        (artboard_dir / "page-001.png").write_bytes(b"page-png")
        (project_root / "05-preview/contact-sheet.png").write_bytes(b"contact-sheet")
        (project_root / "05-preview/preview.html").write_text('<html><body><section id="page-1">preview</section></body></html>', encoding="utf-8")
        (project_root / "05-preview/preview-manifest.json").write_text(
            json.dumps({"page_count": 1, "pages": [{"page": 1, "source_path": "04-svg/prepared/page-001.svg", "source_bytes": (project_root / "04-svg/prepared/page-001.svg").stat().st_size}]}),
            encoding="utf-8",
        )
        (artboard_dir / "page-001.semantic-map.json").write_text(
            json.dumps(
                {
                    "version": "svglide-semantic-map/v1",
                    "page": 1,
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                    "elements": [
                        {
                            "element_id": "title",
                            "kind": "text",
                            "role": "title",
                            "text": "受控画板生成",
                            "bbox": {"x": 84, "y": 142, "width": 628, "height": 142},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (artboard_dir / "page-001.node-layout-map.json").write_text(
            json.dumps(
                {
                    "version": "svglide-node-layout-map/v1",
                    "page": 1,
                    "nodes": [{"id": "title", "kind": "text", "x": 84, "y": 142, "width": 628, "height": 142}],
                }
            ),
            encoding="utf-8",
        )
        (artboard_dir / "page-001.receipt.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "page": 1,
                    "template_id": "cover-hero",
                    "theme_id": "dark-clarity",
                    "semantic_map": "04-svg/artboard/page-001.semantic-map.json",
                    "semantic_map_sha256": runner.file_sha256(artboard_dir / "page-001.semantic-map.json"),
                    "node_layout_map": "04-svg/artboard/page-001.node-layout-map.json",
                    "node_layout_map_sha256": runner.file_sha256(artboard_dir / "page-001.node-layout-map.json"),
                    "png": "04-svg/artboard/page-001.png",
                    "png_sha256": runner.file_sha256(artboard_dir / "page-001.png"),
                }
            ),
            encoding="utf-8",
        )
        generator_path = project_root / "receipts/generate_svg.json"
        generator = json.loads(generator_path.read_text(encoding="utf-8"))
        generator["generation_mode"] = "artboard_satori"
        generator["artboard_receipts"] = ["04-svg/artboard/page-001.receipt.json"]
        generator["contact_sheet"] = {
            "path": "05-preview/contact-sheet.png",
            "sha256": runner.file_sha256(project_root / "05-preview/contact-sheet.png"),
        }
        generator_path.write_text(json.dumps(generator), encoding="utf-8")
        gate_path = project_root / "06-check/quality-gate.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        gate["input_hashes"]["generator_receipt"] = runner.file_sha256(generator_path)
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        return project_root

    def completed(self, command: list[str], payload: dict[str, object] | None = None, returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=json.dumps(payload or {"ok": True}), stderr="")

    def write_ppe_input(self, project_root: Path) -> None:
        rule_file = "skills/lark-slides/references/ppe-pure-svg.whistle.js"
        rule_path = runner.repo_root() / rule_file
        (project_root / "07-create/ppe-proof.input.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "environment": {"name": "Pre_release", "x-tt-env": "ppe_pure_svg"},
                    "auth": {"identity": "user"},
                    "proxy": {
                        "mode": "whistle",
                        "capture": True,
                        "http_proxy": "http://127.0.0.1:8899",
                        "https_proxy": "http://127.0.0.1:8899",
                        "rewrite_host": "open.feishu-pre.cn",
                        "rule_file": rule_file,
                        "rule_sha256": runner.file_sha256(rule_path),
                        "inject_headers": {"Env": "Pre_release", "x-tt-env": "ppe_pure_svg"},
                    },
                    "headers": {"x-tt-env": "ppe_pure_svg"},
                    "route": {"name": "slides +create-svg", "lane": "pure-svg"},
                }
            ),
            encoding="utf-8",
        )

    def test_normalize_stage_accepts_aliases(self) -> None:
        self.assertEqual(runner.normalize_stage("confirm-plan"), "confirm_plan")
        self.assertEqual(runner.normalize_stage("source-review"), "source")
        self.assertEqual(runner.normalize_stage("select-style"), "select_style")
        self.assertEqual(runner.normalize_stage("theme-template-selection"), "select_style")
        self.assertEqual(runner.normalize_stage("palette-selection"), "select_style")
        self.assertEqual(runner.normalize_stage("strategy-review"), "strategy_review")
        self.assertEqual(runner.normalize_stage("theme-validate"), "theme_validate")
        self.assertEqual(runner.normalize_stage("palette-review"), "palette_review")
        self.assertEqual(runner.normalize_stage("selection-review"), "selection_review")
        self.assertEqual(runner.normalize_stage("theme-template-selection-review"), "selection_review")
        self.assertEqual(runner.normalize_stage("plan-bundle-review"), "plan_bundle_review")
        self.assertEqual(runner.normalize_stage("package-check"), "package_check")
        self.assertEqual(runner.normalize_stage("artboard-package-check"), "package_check")
        self.assertEqual(runner.normalize_stage("aesthetic-review"), "aesthetic_review")
        self.assertEqual(runner.normalize_stage("chart-verify"), "chart_verify")
        self.assertEqual(runner.normalize_stage("semantic-review"), "semantic_review")
        self.assertEqual(runner.normalize_stage("runtime-review"), "runtime_review")
        self.assertEqual(runner.normalize_stage("visual-distinctness"), "visual_distinctness_review")
        self.assertEqual(runner.normalize_stage("visual-distinctness-review"), "visual_distinctness_review")
        self.assertEqual(runner.normalize_stage("theme-adherence"), "theme_adherence")
        self.assertEqual(runner.normalize_stage("generate"), "generate_svg")
        self.assertEqual(runner.normalize_stage("generate-svg"), "generate_svg")
        self.assertEqual(runner.normalize_stage("quality-gate"), "quality_gate")
        self.assertEqual(runner.normalize_stage("preview-lint"), "preview_lint")
        self.assertEqual(runner.normalize_stage("dry-run"), "dry_run")
        self.assertEqual(runner.normalize_stage("visual-acceptance"), "visual_acceptance")
        self.assertEqual(runner.normalize_stage("visual-acceptance-gate"), "visual_acceptance")
        self.assertEqual(runner.normalize_stage("deliverable"), "visual_acceptance")
        self.assertEqual(runner.normalize_stage("ppe-proof"), "ppe_proof")
        self.assertEqual(runner.normalize_stage("pre-submit-review"), "pre_submit_review")
        self.assertEqual(runner.normalize_stage("pre-submit"), "pre_submit_review")
        self.assertEqual(runner.normalize_stage("live-create"), "live_create")
        self.assertEqual(runner.normalize_stage("theme-productization"), "theme_productization")
        self.assertEqual(runner.normalize_stage("theme-productize"), "theme_productization")
        self.assertEqual(runner.normalize_stage("export-package"), "export")
        self.assertEqual(runner.normalize_stage("package-export"), "export")

    def test_stages_until_uses_normalized_stage_graph(self) -> None:
        dry_run = runner.stages_until("dry_run")
        self.assertIn("source", dry_run)
        self.assertIn("select_style", dry_run)
        self.assertNotIn("confirm_plan", dry_run)
        self.assertIn("strategy_review", dry_run)
        self.assertIn("theme_validate", dry_run)
        self.assertIn("palette_review", dry_run)
        self.assertIn("selection_review", dry_run)
        self.assertIn("plan_bundle_review", dry_run)
        self.assertIn("package_check", dry_run)
        self.assertIn("assets", dry_run)
        self.assertIn("generate_svg", dry_run)
        self.assertIn("aesthetic_review", dry_run)
        self.assertIn("chart_verify", dry_run)
        self.assertIn("semantic_review", dry_run)
        self.assertIn("runtime_review", dry_run)
        self.assertIn("visual_distinctness_review", dry_run)
        self.assertIn("theme_adherence", dry_run)
        self.assertIn("quality_gate", dry_run)
        self.assertIn("generation_benchmark", dry_run)
        self.assertIn("dry_run", dry_run)
        self.assertLess(dry_run.index("quality_gate"), dry_run.index("generation_benchmark"))
        self.assertLess(dry_run.index("generation_benchmark"), dry_run.index("dry_run"))
        self.assertNotIn("visual_acceptance", dry_run)
        self.assertNotIn("ppe_proof", dry_run)
        self.assertNotIn("live_create", dry_run)
        self.assertNotIn("readback", dry_run)
        self.assertNotIn("export", dry_run)

        visual_acceptance = runner.stages_until("visual_acceptance")
        self.assertIn("dry_run", visual_acceptance)
        self.assertIn("visual_acceptance", visual_acceptance)
        self.assertLess(visual_acceptance.index("dry_run"), visual_acceptance.index("visual_acceptance"))
        self.assertNotIn("ppe_proof", visual_acceptance)

        readback = runner.stages_until("readback")
        self.assertIn("visual_acceptance", readback)
        self.assertIn("ppe_proof", readback)
        self.assertIn("pre_submit_review", readback)
        self.assertIn("live_create", readback)
        self.assertIn("readback", readback)
        self.assertNotIn("export", readback)

        export = runner.stages_until("export")
        self.assertIn("readback", export)
        self.assertIn("export", export)

    def test_resolve_run_target_accepts_preview_only_profile(self) -> None:
        self.assertEqual(runner.resolve_run_target(None, "preview_only"), "quality_gate")
        self.assertEqual(runner.resolve_run_target("preview_lint", "preview_only"), "preview_lint")
        with self.assertRaisesRegex(runner.RunnerError, "preview_only"):
            runner.resolve_run_target("dry_run", "preview_only")

    def test_preview_only_profile_runs_to_quality_gate_without_create_stages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            calls: list[tuple[str, str]] = []
            original_run_implemented_stage = runner.run_implemented_stage
            original_implemented_stages = runner.IMPLEMENTED_STAGES

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                calls.append((stage, profile))
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            try:
                runner.IMPLEMENTED_STAGES = set(runner.IMPLEMENTED_STAGES) | set(runner.stages_until("quality_gate"))
                runner.run_implemented_stage = fake_run_implemented_stage
                runner.run_until(project_root, runner.resolve_run_target(None, "preview_only"), profile="preview_only")
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.IMPLEMENTED_STAGES = original_implemented_stages

            called_stages = [stage for stage, _ in calls]
            self.assertIn("source", called_stages)
            self.assertIn("select_style", called_stages)
            self.assertIn("chart_verify", called_stages)
            self.assertIn("semantic_review", called_stages)
            self.assertIn("runtime_review", called_stages)
            self.assertIn("visual_distinctness_review", called_stages)
            self.assertIn("theme_validate", called_stages)
            self.assertIn("package_check", called_stages)
            self.assertIn("theme_adherence", called_stages)
            self.assertLess(called_stages.index("source"), called_stages.index("select_style"))
            self.assertLess(called_stages.index("select_style"), called_stages.index("plan"))
            self.assertLess(called_stages.index("strategy_review"), called_stages.index("theme_validate"))
            self.assertLess(called_stages.index("theme_validate"), called_stages.index("palette_review"))
            self.assertLess(called_stages.index("palette_review"), called_stages.index("selection_review"))
            self.assertLess(called_stages.index("selection_review"), called_stages.index("plan_bundle_review"))
            self.assertNotIn("confirm_plan", called_stages)
            self.assertLess(called_stages.index("plan_bundle_review"), called_stages.index("package_check"))
            self.assertLess(called_stages.index("chart_verify"), called_stages.index("semantic_review"))
            self.assertLess(called_stages.index("semantic_review"), called_stages.index("quality_gate"))
            self.assertLess(called_stages.index("runtime_review"), called_stages.index("visual_distinctness_review"))
            self.assertLess(called_stages.index("visual_distinctness_review"), called_stages.index("theme_adherence"))
            self.assertLess(called_stages.index("theme_adherence"), called_stages.index("quality_gate"))
            self.assertLess(called_stages.index("visual_distinctness_review"), called_stages.index("quality_gate"))
            self.assertNotIn("dry_run", called_stages)
            self.assertNotIn("ppe_proof", called_stages)
            self.assertNotIn("pre_submit_review", called_stages)
            self.assertNotIn("live_create", called_stages)
            self.assertNotIn("readback", called_stages)
            self.assertTrue(all(profile == "preview_only" for _, profile in calls))

    def test_complete_stage_writes_timing_report_with_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            (project_root / "02-plan/slide_plan.json").write_text("{}", encoding="utf-8")
            state = runner.load_state(project_root)
            state["profile"] = "preview_only"
            runner.complete_stage(
                project_root,
                state,
                "plan",
                "passed",
                started_at=runner.now_iso(),
                inputs=["02-plan/slide_plan.json"],
                outputs=["receipts/plan.json"],
            )
            receipt = json.loads((project_root / "receipts/plan.json").read_text(encoding="utf-8"))
            report = json.loads((project_root / "06-check/timing-report.json").read_text(encoding="utf-8"))
            self.assertIn("02-plan/slide_plan.json", receipt["input_hashes"])
            self.assertEqual(report["schema_version"], "svglide-timing-report/v1")
            self.assertEqual(report["stage_attempts"]["plan"], 1)
            self.assertEqual(report["sla"]["profile"], "preview_only")

    def test_collect_errors_stops_before_render_and_writes_structured_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            original_run_implemented_stage = runner.run_implemented_stage

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                if stage == "plan_bundle_review":
                    runner.complete_stage(
                        project_root,
                        state,
                        stage,
                        "failed",
                        started_at=runner.now_iso(),
                        error={
                            "code": "stage_command_failed",
                            "issues": [
                                {
                                    "code": "project_palette_missing",
                                    "message": "missing palette",
                                    "root_cause_group": "palette_adoption",
                                }
                            ],
                        },
                    )
                    raise runner.RunnerError("plan bundle failed")
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            try:
                runner.run_implemented_stage = fake_run_implemented_stage
                with self.assertRaisesRegex(runner.RunnerError, "pre-render validation errors"):
                    runner.run_until(project_root, "package_check", profile="preview_only", collect_errors=True)
            finally:
                runner.run_implemented_stage = original_run_implemented_stage

            collected = json.loads((project_root / "06-check/collected-errors.json").read_text(encoding="utf-8"))
            self.assertEqual(collected["status"], "failed")
            self.assertEqual(collected["issues"][0]["root_cause_group"], "palette_adoption")
            self.assertNotIn("confirm_plan", runner.load_state(project_root)["stages"])

    def test_production_live_profile_runs_ppe_before_live_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            calls: list[tuple[str, str]] = []
            original_run_implemented_stage = runner.run_implemented_stage
            original_implemented_stages = runner.IMPLEMENTED_STAGES

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                calls.append((stage, profile))
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            try:
                runner.IMPLEMENTED_STAGES = set(runner.IMPLEMENTED_STAGES) | set(runner.stages_until("readback"))
                runner.run_implemented_stage = fake_run_implemented_stage
                runner.run_until(project_root, runner.resolve_run_target(None, "production_live"), profile="production_live")
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.IMPLEMENTED_STAGES = original_implemented_stages

            called_stages = [stage for stage, _ in calls]
            self.assertIn("ppe_proof", called_stages)
            self.assertIn("visual_acceptance", called_stages)
            self.assertIn("pre_submit_review", called_stages)
            self.assertLess(called_stages.index("dry_run"), called_stages.index("ppe_proof"))
            self.assertLess(called_stages.index("dry_run"), called_stages.index("visual_acceptance"))
            self.assertLess(called_stages.index("visual_acceptance"), called_stages.index("ppe_proof"))
            self.assertLess(called_stages.index("ppe_proof"), called_stages.index("pre_submit_review"))
            self.assertLess(called_stages.index("pre_submit_review"), called_stages.index("live_create"))
            self.assertTrue(all(profile == "production_live" for _, profile in calls))

    def test_agent_progress_reports_four_artboard_milestones_to_stderr_and_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_artboard_plan(project_root)
            calls: list[str] = []
            original_run_implemented_stage = runner.run_implemented_stage
            original_implemented_stages = runner.IMPLEMENTED_STAGES

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                calls.append(stage)
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            stderr = io.StringIO()
            try:
                runner.IMPLEMENTED_STAGES = set(runner.IMPLEMENTED_STAGES) | set(runner.stages_until("readback"))
                runner.run_implemented_stage = fake_run_implemented_stage
                with contextlib.redirect_stderr(stderr):
                    runner.run_until(
                        project_root,
                        runner.resolve_run_target(None, "production_live"),
                        profile="production_live",
                        progress="agent",
                    )
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.IMPLEMENTED_STAGES = original_implemented_stages

            output = stderr.getvalue()
            self.assertIn("正在生成主题 plan 和图片资产", output)
            self.assertIn("已完成 1/4 关键产物: 主题 plan + 图片资产", output)
            self.assertIn("已完成 2/4 关键产物: Satori-compatible HTML/CSS", output)
            self.assertIn("已完成 3/4 关键产物: Satori SVG + SVGlide SVG", output)
            self.assertIn("已完成 4/4 关键产物: 本地预览 + gates", output)
            self.assertIn("生成完成：", output)
            self.assertIn("assets", calls)
            self.assertIn("visual_acceptance", calls)
            events = [
                json.loads(line)
                for line in (project_root / "logs/agent-progress.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            milestones = [event for event in events if event["event"] == "milestone_completed"]
            self.assertEqual(milestones[-1]["completed"], 4)
            self.assertEqual(milestones[-1]["total"], 4)
            self.assertEqual(events[-1]["event"], "completed")

    def test_agent_progress_reports_direct_svg_denominator_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            original_run_implemented_stage = runner.run_implemented_stage
            original_implemented_stages = runner.IMPLEMENTED_STAGES

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            stderr = io.StringIO()
            try:
                runner.IMPLEMENTED_STAGES = set(runner.IMPLEMENTED_STAGES) | set(runner.stages_until("readback"))
                runner.run_implemented_stage = fake_run_implemented_stage
                with contextlib.redirect_stderr(stderr):
                    runner.run_until(project_root, "readback", progress="agent")
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.IMPLEMENTED_STAGES = original_implemented_stages

            output = stderr.getvalue()
            self.assertIn("已完成 1/3 关键产物: 素材资产", output)
            self.assertIn("已完成 2/3 关键产物: SVGlide protocol SVG", output)
            self.assertIn("已完成 3/3 关键产物: backend snapshot JSON", output)
            self.assertNotIn("4/4", output)

    def test_agent_progress_failure_is_concise_and_stdout_json_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_artboard_plan(project_root)
            original_run_implemented_stage = runner.run_implemented_stage
            original_implemented_stages = runner.IMPLEMENTED_STAGES

            def fake_run_implemented_stage(project_root: Path, stage: str, state: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                if stage == "assets":
                    raise runner.RunnerError("asset stage missing trusted image materializer")
                return runner.complete_stage(project_root, state, stage, "passed", started_at=runner.now_iso())

            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                runner.IMPLEMENTED_STAGES = set(runner.IMPLEMENTED_STAGES) | set(runner.stages_until("readback"))
                runner.run_implemented_stage = fake_run_implemented_stage
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = runner.main(
                        [
                            "run",
                            project_root.as_posix(),
                            "--profile",
                            "production_live",
                            "--progress",
                            "agent",
                        ]
                    )
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.IMPLEMENTED_STAGES = original_implemented_stages

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            error_output = stderr.getvalue()
            self.assertEqual(error_output.count("生成已阻断:"), 1)
            self.assertNotIn("\nasset stage missing trusted image materializer\n", error_output)
            self.assertNotIn("Traceback", error_output)

    def test_pre_submit_review_uses_documented_human_review_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            state = runner.load_state(project_root)
            state.setdefault("stages", {})["ppe_proof"] = {"status": "passed"}
            captured: dict[str, object] = {}
            original_run_script_stage = runner.run_script_stage

            def fake_run_script_stage(
                project_root: Path,
                state: dict[str, object],
                stage: str,
                command: list[str],
                *,
                output_json: Path | None = None,
                inputs: list[str] | None = None,
                outputs: list[str] | None = None,
                command_runner=runner.subprocess.run,
            ) -> dict[str, object]:
                captured["command"] = command
                captured["inputs"] = inputs
                return runner.complete_stage(
                    project_root,
                    state,
                    stage,
                    "passed",
                    started_at=runner.now_iso(),
                    inputs=inputs,
                    outputs=outputs,
                    command=command,
                )

            try:
                runner.run_script_stage = fake_run_script_stage
                runner.run_implemented_stage(project_root, "pre_submit_review", state, profile="production_live")
            finally:
                runner.run_script_stage = original_run_script_stage

            command = captured["command"]
            inputs = captured["inputs"]
            self.assertIsInstance(command, list)
            self.assertIsInstance(inputs, list)
            self.assertIn((project_root / "06-check/pre-submit-human-review.json").as_posix(), command)
            self.assertIn("06-check/pre-submit-human-review.json", inputs)

    def test_export_stage_invokes_package_script_after_readback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            (project_root / "receipts/readback.json").write_text(
                json.dumps({"stage": "readback", "status": "passed", "profile": "production"}),
                encoding="utf-8",
            )
            state = runner.load_state(project_root)
            state.setdefault("stages", {})["readback"] = {"status": "passed", "receipt": "receipts/readback.json"}
            runner.write_state(project_root, state)
            captured: dict[str, object] = {}
            original_run_script_stage = runner.run_script_stage

            def fake_run_script_stage(
                project_root: Path,
                state: dict[str, object],
                stage: str,
                command: list[str],
                **_: object,
            ) -> dict[str, object]:
                captured["stage"] = stage
                captured["command"] = command
                return runner.complete_stage(
                    project_root,
                    state,
                    stage,
                    "passed",
                    started_at=runner.now_iso(),
                    command=command,
                )

            try:
                runner.run_script_stage = fake_run_script_stage
                runner.run_stage(project_root, "export-package")
            finally:
                runner.run_script_stage = original_run_script_stage

            self.assertEqual(captured["stage"], "export")
            command = captured["command"]
            self.assertIsInstance(command, list)
            self.assertIn("svglide_export_package.py", " ".join(command))
            self.assertIn("--archive", command)

    def test_theme_productization_stage_invokes_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            captured: dict[str, object] = {}
            original_run_script_stage = runner.run_script_stage

            def fake_run_script_stage(
                project_root: Path,
                state: dict[str, object],
                stage: str,
                command: list[str],
                **_: object,
            ) -> dict[str, object]:
                captured["stage"] = stage
                captured["command"] = command
                return runner.complete_stage(
                    project_root,
                    state,
                    stage,
                    "passed",
                    started_at=runner.now_iso(),
                    command=command,
                )

            try:
                runner.run_script_stage = fake_run_script_stage
                runner.run_stage(project_root, "theme-productize")
            finally:
                runner.run_script_stage = original_run_script_stage

            self.assertEqual(captured["stage"], "theme_productization")
            command = captured["command"]
            self.assertIsInstance(command, list)
            self.assertIn("svglide_theme_productization.py", " ".join(command))

    def test_init_creates_project_directories_manifest_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])

            for directory in runner.PROJECT_DIRS:
                self.assertTrue((project_root / directory).is_dir(), directory)

            manifest = json.loads((project_root / "01-project/project_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], runner.PROJECT_VERSION)
            self.assertEqual(manifest["deck_id"], "smoke")
            self.assertEqual(manifest["title"], "Smoke")
            self.assertEqual(manifest["route"], runner.ROUTE)
            self.assertEqual(manifest["stage_graph"], runner.STAGE_GRAPH)
            self.assertEqual(manifest["artifact_root"], project_root.as_posix())

            state = json.loads((project_root / "01-project/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["version"], runner.STATE_VERSION)
            self.assertEqual(state["current_stage"], "init")
            self.assertEqual(state["stages"]["init"]["status"], "passed")
            self.assertEqual(state["stages"]["init"]["receipt"], "receipts/init.json")

            init_receipt = json.loads((project_root / "receipts/init.json").read_text(encoding="utf-8"))
            self.assertEqual(init_receipt["stage"], "init")
            self.assertEqual(init_receipt["status"], "passed")

    def test_repeated_init_rejects_existing_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            runner.init_project("smoke", "Smoke", plan_root=plan_root)

            with self.assertRaises(runner.RunnerError) as err:
                runner.init_project("smoke", "Smoke", plan_root=plan_root)

            self.assertEqual(err.exception.exit_code, 2)
            self.assertIn("already exists", str(err.exception))

    def test_run_until_fails_on_skipped_required_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.run_source(project_root)
            state_path = project_root / "01-project/state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["stages"]["plan"] = {"status": "skipped", "receipt": "receipts/plan.json"}
            state_path.write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaises(runner.RunnerError) as err:
                runner.run_until(project_root, "dry_run")

            self.assertIn("required stage 'plan' is skipped", str(err.exception))

    def test_run_until_retries_existing_failed_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            state = runner.load_state(project_root)
            for stage in runner.stages_until("dry_run"):
                receipt = project_root / "receipts" / f"{stage}.json"
                receipt.write_text(json.dumps({"stage": stage, "status": "failed" if stage == "dry_run" else "passed"}), encoding="utf-8")
                runner.record_stage(state, stage, "failed" if stage == "dry_run" else "passed", receipt)
            runner.write_state(project_root, state)

            called: list[str] = []
            original_run_implemented_stage = runner.run_implemented_stage
            original_require_existing_stage_current = runner.require_existing_stage_current
            original_detect_stale_stages = runner.svglide_stage_invalidation.detect_stale_stages

            def fake_run_implemented_stage(project_root_arg: Path, stage: str, state_arg: dict[str, object], *, profile: str = "production") -> dict[str, object]:
                called.append(stage)
                return runner.complete_stage(
                    project_root_arg,
                    state_arg,
                    stage,
                    "passed",
                    started_at=runner.now_iso(),
                    command=["fake", stage],
                )

            try:
                runner.run_implemented_stage = fake_run_implemented_stage
                runner.require_existing_stage_current = lambda *_args, **_kwargs: None
                runner.svglide_stage_invalidation.detect_stale_stages = lambda *_args, **_kwargs: []
                runner.run_until(project_root, "dry_run", profile="preview_only")
            finally:
                runner.run_implemented_stage = original_run_implemented_stage
                runner.require_existing_stage_current = original_require_existing_stage_current
                runner.svglide_stage_invalidation.detect_stale_stages = original_detect_stale_stages

            updated = runner.load_state(project_root)
            self.assertEqual(called, ["dry_run"])
            self.assertEqual(updated["stages"]["dry_run"]["status"], "passed")
            self.assertIn("dry_run", updated["stale_pruned"])

    def test_plan_stage_validates_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)

            result = runner.run_stage(project_root, "plan")

            receipt = json.loads((project_root / "receipts/plan.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["stage"], "plan")
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(result["status"], "passed")

            state = json.loads((project_root / "01-project/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["plan"]["status"], "passed")

    def test_plan_stage_rejects_artboard_mode_without_canvas_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            plan_path = project_root / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["generation_mode"] = "artboard_satori"
            for slide in plan["slides"]:
                slide.pop("canvas_spec", None)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "plan schema validation failed"):
                runner.run_stage(project_root, "plan")

            receipt = json.loads((project_root / "receipts/plan.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            paths = {item["path"] for item in receipt["error"]["issues"]}
            self.assertIn("$.slides[0].canvas_spec", paths)

    def test_plan_stage_adds_visual_identity_before_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("bytedance", "字节跳动", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            plan_path = project_root / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan.pop("visual_identity")
            plan["title"] = "字节跳动"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            result = runner.run_stage(project_root, "plan")

            updated = json.loads(plan_path.read_text(encoding="utf-8"))
            receipt = json.loads((project_root / "receipts/plan.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertTrue(receipt["visual_identity_added"])
            self.assertEqual(updated["visual_identity"]["theme_archetype"], "company_ecosystem")

    def test_strategy_review_stage_validates_plan_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "plan")

            result = runner.run_stage(project_root, "strategy-review")

            self.assertEqual(result["status"], "passed")
            review = json.loads((project_root / "02-plan/strategy-review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "passed")

    def test_confirm_plan_writes_request_and_does_not_block_state_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)

            with self.assertRaisesRegex(runner.RunnerError, "optional plan confirmation is missing"):
                runner.run_stage(project_root, "confirm-plan")

            request = json.loads((project_root / "02-plan/plan-confirmation.request.json").read_text(encoding="utf-8"))
            self.assertEqual(request["status"], "pending")
            self.assertEqual(request["plan_path"], "02-plan/slide_plan.json")

            state = json.loads((project_root / "01-project/state.json").read_text(encoding="utf-8"))
            self.assertNotIn("confirm_plan", state["stages"])

    def test_confirm_plan_passes_with_matching_user_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)

            result = runner.run_stage(project_root, "confirm-plan")

            self.assertEqual(result["status"], "passed")
            receipt = json.loads((project_root / "receipts/confirm_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["confirmation"]["confirmed_by"], "user")

    def test_generate_svg_requires_assets_stage_without_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "package-check")

            with self.assertRaisesRegex(runner.RunnerError, "assets"):
                runner.run_stage(project_root, "generate-svg")

    def test_assets_runs_after_package_check_without_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "package-check")

            result = runner.run_stage(project_root, "assets")

            self.assertEqual(result["status"], "passed")

    def test_generate_svg_requires_assets_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            runner.run_stage(project_root, "confirm-plan")
            self.run_source(project_root)
            (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "assets"):
                runner.run_stage(project_root, "generate-svg")

    def test_package_check_writes_noop_receipt_for_direct_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            runner.run_stage(project_root, "confirm-plan")

            result = runner.run_stage(project_root, "package-check")

            self.assertEqual(result["status"], "passed")
            check = json.loads((project_root / "06-check/artboard-package-check.json").read_text(encoding="utf-8"))
            self.assertEqual(check["stage"], "package_check")
            self.assertEqual(check["status"], "passed")
            self.assertEqual(check["generation_mode"], "direct_svg")
            self.assertEqual(check["summary"]["error_count"], 0)
            state = runner.load_state(project_root)
            self.assertEqual(state["stages"]["package_check"]["status"], "passed")

    def test_generate_svg_adopts_existing_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            for page in range(1, 4):
                (project_root / f"04-svg/page-{page:03d}.svg").write_text("<svg></svg>", encoding="utf-8")

            result = runner.run_stage(project_root, "generate-svg")

            self.assertEqual(result["status"], "passed")
            receipt = json.loads((project_root / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["generator_mode"], "external")
            self.assertEqual(receipt["generated_files"][0]["path"], "04-svg/page-001.svg")
            self.assertEqual(receipt["page_receipts"][0], "04-svg/page-001.receipt.json")
            self.assertTrue((project_root / "04-svg/page-001.receipt.json").exists())

    def test_generate_svg_injects_file_backed_cover_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            (project_root / "03-assets/raw").mkdir(parents=True, exist_ok=True)
            (project_root / "03-assets/raw/hero.png").write_bytes(b"png")
            (project_root / "02-plan/svglide.lock.json").write_text(
                json.dumps(
                    {
                        "asset_contracts": [
                            {
                                "id": "hero",
                                "href": "@./03-assets/raw/hero.png",
                                "usage_page": 1,
                                "placement_role": "cover",
                                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            for page in range(1, 4):
                (project_root / f"04-svg/page-{page:03d}.svg").write_text(
                    '<svg width="960" height="540" viewBox="0 0 960 540"><text>测试标题</text></svg>',
                    encoding="utf-8",
                )

            result = runner.run_stage(project_root, "generate-svg")

            self.assertEqual(result["status"], "passed")
            svg = (project_root / "04-svg/page-001.svg").read_text(encoding="utf-8")
            self.assertIn('href="@./03-assets/raw/hero.png"', svg)
            receipt = json.loads((project_root / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["asset_injection_summary"]["used_count"], 1)
            self.assertEqual(receipt["generated_files"][0]["sha256"], runner.file_sha256(project_root / "04-svg/page-001.svg"))
            page_receipt = json.loads((project_root / "04-svg/page-001.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(page_receipt["asset_refs"][0]["asset_id"], "hero")
            self.assertEqual(page_receipt["asset_injection"][0]["status"], "injected")
            runner.run_stage(project_root, "contract_compile")
            runner.run_stage(project_root, "prepare")
            runner.run_stage(project_root, "preview")
            preview_html = (project_root / "05-preview/preview.html").read_text(encoding="utf-8")
            self.assertIn('href="data:image/png;base64,', preview_html)

    def test_generate_svg_runs_local_generator_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            generator = project_root / "logs/generate_svgs.py"
            generator.write_text(
                "\n".join(
                    [
                        "from pathlib import Path",
                        "project = Path(__file__).resolve().parents[1]",
                        "for page in range(1, 4):",
                        "    (project / f'04-svg/page-{page:03d}.svg').write_text('<svg></svg>', encoding='utf-8')",
                    ]
                ),
                encoding="utf-8",
            )

            result = runner.run_stage(project_root, "generate-svg")

            self.assertEqual(result["status"], "passed")
            self.assertTrue((project_root / "04-svg/page-001.svg").exists())
            receipt = json.loads((project_root / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["generator_mode"], "script")
            self.assertIn("logs/generate_svgs.py", receipt["command"][1])

    def test_generate_svg_runs_artboard_satori_dispatcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_artboard_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")

            result = runner.run_stage(project_root, "generate-svg")

            self.assertEqual(result["status"], "passed")
            source = project_root / "04-svg/page-001.svg"
            self.assertTrue(source.exists())
            self.assertIn('slide:role="slide"', source.read_text(encoding="utf-8"))
            raw_source = project_root / "04-artboard/raw/page-001.visual.svg"
            self.assertTrue(raw_source.exists())
            self.assertNotIn("slide:role", raw_source.read_text(encoding="utf-8"))
            receipt = json.loads((project_root / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["generation_mode"], "artboard_satori")
            self.assertEqual(receipt["generator_mode"], "script")
            self.assertEqual(receipt["artboard_receipts"], ["04-artboard/raw/page-001.receipt.json"])
            self.assertEqual(receipt["raw_visual_manifest"], "04-artboard/raw/manifest.json")
            self.assertEqual(receipt["raw_visual_files"][0]["path"], "04-artboard/raw/page-001.visual.svg")
            self.assertEqual(
                receipt["artboard_additional_receipts"],
                [
                    "receipts/canvas-spec-validate.json",
                    "receipts/artboard-render.json",
                    "receipts/satori-bridge.json",
                ],
            )
            self.assertEqual(receipt["canvas_spec_validate"], "06-check/canvas-spec-validate.json")
            self.assertEqual(receipt["artboard_render_receipt"], "receipts/artboard-render.json")
            self.assertEqual(receipt["satori_bridge_receipt"], "receipts/satori-bridge.json")
            self.assertEqual(receipt["contact_sheet"]["path"], "05-preview/contact-sheet.png")
            self.assertEqual(receipt["template_fit_check"], "06-check/template-fit.json")
            self.assertEqual(receipt["page_receipts"], ["04-artboard/raw/page-001.visual.receipt.json"])
            self.assertTrue((project_root / "06-check/template-fit.json").exists())
            self.assertTrue((project_root / "receipts/template-fit-check.json").exists())
            compile_result = runner.run_stage(project_root, "contract_compile")
            self.assertEqual(compile_result["status"], "passed")
            self.assertTrue((project_root / "04-svg/page-001.svg").exists())
            self.assertIn('slide:role="slide"', (project_root / "04-svg/page-001.svg").read_text(encoding="utf-8"))
            self.assertTrue((project_root / "04-artboard/raw/page-001.visual.png").exists())
            self.assertTrue((project_root / "05-preview/contact-sheet.png").exists())
            contract_manifest = json.loads((project_root / "04-svg/contract/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(contract_manifest["stage"], "contract_compile")
            self.assertEqual(contract_manifest["pages"][0]["output"], "04-svg/page-001.svg")

    def test_generate_svg_rejects_artboard_plan_without_canvas_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_artboard_plan(project_root)
            plan_path = project_root / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["slides"][0].pop("canvas_spec")
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")

            with self.assertRaisesRegex(runner.RunnerError, "requires canvas_spec"):
                runner.run_stage(project_root, "generate-svg")

    def test_prepare_requires_generate_svg_stage_without_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "generate_svg"):
                runner.run_stage(project_root, "prepare")

    def test_prepare_requires_generate_svg_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "generate_svg"):
                runner.run_stage(project_root, "prepare")

    def test_prepare_requires_assets_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            runner.run_stage(project_root, "confirm-plan")
            (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "assets"):
                runner.run_stage(project_root, "prepare")

    def test_prepare_refuses_changed_sources_after_generate_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
            runner.run_stage(project_root, "package-check")
            runner.run_stage(project_root, "assets")
            source = project_root / "04-svg/page-001.svg"
            for page in range(1, 4):
                (project_root / f"04-svg/page-{page:03d}.svg").write_text("<svg></svg>", encoding="utf-8")
            runner.run_stage(project_root, "generate-svg")
            runner.run_stage(project_root, "contract_compile")
            source.write_text("<svg><rect /></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after generate_svg|changed after contract_compile|compiled SVG files changed"):
                runner.run_stage(project_root, "prepare")

    def test_dry_run_refuses_failed_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            (project_root / "06-check/quality-gate.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "quality gate"):
                runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=lambda *a, **k: self.completed(a[0]))

    def test_dry_run_stage_requires_generation_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)

            with self.assertRaisesRegex(runner.RunnerError, "generation_benchmark"):
                runner.run_stage(project_root, "dry-run")

    def test_dry_run_refuses_changed_prepared_hashes_after_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            (project_root / "04-svg/prepared/page-001.svg").write_text("<svg><rect /></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after quality gate"):
                runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=lambda *a, **k: self.completed(a[0]))

    def test_existing_quality_gate_without_visual_distinctness_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            old_gate = {
                "status": "passed",
                "inputs": {},
                "checks": [],
                "prepared_files": runner.prepared_file_hashes(project_root),
            }
            (project_root / "06-check/quality-gate.json").write_text(json.dumps(old_gate), encoding="utf-8")
            state = runner.load_state(project_root)
            receipt = project_root / "receipts/quality_gate.json"
            receipt.write_text(json.dumps({"stage": "quality_gate", "status": "passed"}), encoding="utf-8")
            runner.record_stage(state, "quality_gate", "passed", receipt)
            runner.write_state(project_root, state)

            with self.assertRaisesRegex(runner.RunnerError, "visual_distinctness"):
                runner.run_stage(project_root, "quality_gate")

    def test_existing_quality_gate_missing_selection_inputs_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            plan_path = project_root / "02-plan/slide_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["selection_receipt"] = "02-plan/theme-template-selection.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "palette_review"):
                runner.require_quality_gate_current(project_root)

    def test_dry_run_command_includes_assets_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            (project_root / "03-assets/assets.json").write_text(json.dumps({"@./hero.png": "boxcn_hero"}), encoding="utf-8")
            captured: list[list[str]] = []

            def fake(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                captured.append(command)
                return self.completed(command)

            runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=fake)

            self.assertIn("--assets", captured[0])
            self.assertEqual(captured[0][captured[0].index("--assets") + 1], "03-assets/assets.json")
            self.assertEqual(captured[0][captured[0].index("--file") + 1], "04-svg/prepared/page-001.svg")
            self.assertIn("--dry-run", captured[0])
            dry_run = json.loads((project_root / "07-create/dry-run.json").read_text(encoding="utf-8"))
            self.assertEqual(dry_run["prepared_files"][0]["path"], "04-svg/prepared/page-001.svg")

    def test_dry_run_command_omits_assets_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            captured: list[list[str]] = []

            def fake(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                captured.append(command)
                return self.completed(command)

            runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=fake)

            self.assertNotIn("--assets", captured[0])

    def test_create_command_allows_local_cli_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            previous = os.environ.get(runner.LARK_CLI_COMMAND_ENV)
            os.environ[runner.LARK_CLI_COMMAND_ENV] = "env GOCACHE=/private/tmp/svglide-gocache go run ."
            try:
                command = runner.create_command(project_root, dry_run=True)
            finally:
                if previous is None:
                    os.environ.pop(runner.LARK_CLI_COMMAND_ENV, None)
                else:
                    os.environ[runner.LARK_CLI_COMMAND_ENV] = previous

            self.assertEqual(command[:5], ["env", "GOCACHE=/private/tmp/svglide-gocache", "go", "run", "."])
            self.assertIn("+create-svg", command)
            self.assertIn("--dry-run", command)

    def test_live_create_command_includes_ppe_request_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            captured: list[list[str]] = []

            def fake(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                captured.append(command)
                return self.completed(command, {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]})

            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            self.write_ppe_input(project_root)
            runner.run_stage(project_root, "ppe-proof")
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "live_create",
                dry_run=False,
                command_runner=fake,
            )

            self.assertEqual(captured[0][captured[0].index("--request-header") + 1], "x-tt-env=ppe_pure_svg")
            self.assertNotIn("--dry-run", captured[0])
            command_text = (project_root / "07-create/create-command.txt").read_text(encoding="utf-8")
            self.assertIn("--request-header x-tt-env=ppe_pure_svg", command_text)

    def test_ppe_proof_refuses_visual_acceptance_receipt_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            runner.run_stage(project_root, "visual-acceptance")
            self.write_ppe_input(project_root)
            (project_root / "receipts/visual_acceptance.json").write_text(
                json.dumps({"status": "skipped", "mutated": True}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(runner.RunnerError, "receipt does not match"):
                runner.run_stage(project_root, "ppe-proof")

    def test_ppe_proof_refuses_skipped_visual_acceptance_delivery_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            runner.run_stage(project_root, "visual-acceptance")
            self.write_ppe_input(project_root)
            check_path = project_root / "06-check/visual-acceptance.json"
            check = json.loads(check_path.read_text(encoding="utf-8"))
            check["action"] = "deliverable_pass"
            check["deliverable_pass"] = True
            check_path.write_text(json.dumps(check), encoding="utf-8")
            (project_root / "receipts/visual_acceptance.json").write_text(json.dumps(check), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "skipped visual_acceptance"):
                runner.run_stage(project_root, "ppe-proof")

    def test_ppe_proof_refuses_stale_visual_acceptance_artboard_artifacts(self) -> None:
        for rel in ["04-svg/artboard/page-001.receipt.json", "04-svg/artboard/page-001.png"]:
            with self.subTest(rel=rel), tempfile.TemporaryDirectory() as tmpdir:
                project_root = self.make_artboard_visual_project(tmpdir)
                runner.run_create_stage(
                    project_root,
                    runner.load_state(project_root),
                    "dry_run",
                    dry_run=True,
                    command_runner=lambda command, **_: self.completed(command),
                )
                runner.run_stage(project_root, "visual-acceptance")
                self.write_ppe_input(project_root)
                target = project_root / rel
                if rel.endswith(".json"):
                    payload = json.loads(target.read_text(encoding="utf-8"))
                    payload["mutated_after_visual_acceptance"] = True
                    target.write_text(json.dumps(payload), encoding="utf-8")
                else:
                    target.write_bytes(b"mutated-after-visual-acceptance")

                with self.assertRaisesRegex(runner.RunnerError, "artifact hash is stale"):
                    runner.run_stage(project_root, "ppe-proof")

    def test_ppe_proof_refuses_missing_visual_evidence_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_artboard_visual_project(tmpdir)
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            runner.run_stage(project_root, "visual-acceptance")
            self.write_ppe_input(project_root)
            check_path = project_root / "06-check/visual-acceptance.json"
            check = json.loads(check_path.read_text(encoding="utf-8"))
            check.pop("visual_evidence", None)
            check_path.write_text(json.dumps(check), encoding="utf-8")
            (project_root / "receipts/visual_acceptance.json").write_text(json.dumps(check), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "visual_evidence.pages"):
                runner.run_stage(project_root, "ppe-proof")

    def test_ppe_proof_refuses_visual_evidence_pages_without_preview_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_artboard_visual_project(tmpdir)
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            runner.run_stage(project_root, "visual-acceptance")
            self.write_ppe_input(project_root)
            check_path = project_root / "06-check/visual-acceptance.json"
            check = json.loads(check_path.read_text(encoding="utf-8"))
            page = check["visual_evidence"]["pages"][0]
            page.pop("preview_sha256", None)
            page.pop("preview_manifest_sha256", None)
            check_path.write_text(json.dumps(check), encoding="utf-8")
            (project_root / "receipts/visual_acceptance.json").write_text(json.dumps(check), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "preview_sha256"):
                runner.run_stage(project_root, "ppe-proof")

    def test_ppe_proof_refuses_missing_deck_rhythm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_artboard_visual_project(tmpdir)
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            runner.run_stage(project_root, "visual-acceptance")
            self.write_ppe_input(project_root)
            check_path = project_root / "06-check/visual-acceptance.json"
            check = json.loads(check_path.read_text(encoding="utf-8"))
            check.pop("deck_rhythm", None)
            check_path.write_text(json.dumps(check), encoding="utf-8")
            (project_root / "receipts/visual_acceptance.json").write_text(json.dumps(check), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "deck_rhythm"):
                runner.run_stage(project_root, "ppe-proof")

    def test_cli_arg_path_uses_repo_relative_paths(self) -> None:
        repo_file = runner.repo_root() / "skills/lark-slides/scripts/svglide_project_runner.py"

        self.assertEqual(runner.cli_arg_path(repo_file), "skills/lark-slides/scripts/svglide_project_runner.py")

    def test_live_create_refuses_changed_prepared_hashes_after_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)

            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            self.write_ppe_input(project_root)
            runner.run_stage(project_root, "ppe-proof")
            (project_root / "04-svg/prepared/page-001.svg").write_text("<svg><rect /></svg>", encoding="utf-8")
            theme_adherence_path = project_root / "06-check/theme-adherence.json"
            theme_adherence = json.loads(theme_adherence_path.read_text(encoding="utf-8"))
            theme_adherence["prepared_files"] = runner.prepared_file_hashes(project_root)
            theme_adherence_path.write_text(json.dumps(theme_adherence), encoding="utf-8")
            gate_path = project_root / "06-check/quality-gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["prepared_files"] = runner.prepared_file_hashes(project_root)
            gate["input_hashes"]["theme_adherence"] = runner.file_sha256(theme_adherence_path)
            gate_path.write_text(json.dumps(gate), encoding="utf-8")
            proof_path = project_root / "07-create/ppe-proof.json"
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            proof["inputs"]["quality_gate_sha256"] = runner.file_sha256(gate_path)
            proof_path.write_text(json.dumps(proof), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after dry-run"):
                runner.run_create_stage(
                    project_root,
                    runner.load_state(project_root),
                    "live_create",
                    dry_run=False,
                    command_runner=lambda command, **_: self.completed(command, {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]}),
                )

            receipt = json.loads((project_root / "receipts/live_create.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["error"]["code"], "prepared_hash_mismatch")

    def test_live_create_requires_ppe_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)

            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )

            with self.assertRaisesRegex(runner.RunnerError, "ppe_proof"):
                runner.run_create_stage(
                    project_root,
                    runner.load_state(project_root),
                    "live_create",
                    dry_run=False,
                    command_runner=lambda command, **_: self.completed(command, {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]}),
                )

    def test_production_live_create_requires_pre_submit_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)

            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            self.write_ppe_input(project_root)
            runner.run_stage(project_root, "ppe-proof")

            with self.assertRaisesRegex(runner.RunnerError, "pre_submit_review"):
                runner.run_create_stage(
                    project_root,
                    runner.load_state(project_root),
                    "live_create",
                    dry_run=False,
                    profile="production_live",
                    command_runner=lambda command, **_: self.completed(command, {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]}),
                )

    def test_existing_live_create_record_requires_pre_submit_for_production_live_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)

            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "dry_run",
                dry_run=True,
                command_runner=lambda command, **_: self.completed(command),
            )
            self.write_ppe_input(project_root)
            runner.run_stage(project_root, "ppe-proof")
            runner.run_create_stage(
                project_root,
                runner.load_state(project_root),
                "live_create",
                dry_run=False,
                command_runner=lambda command, **_: self.completed(command, {"xml_presentation_id": "xml_1", "slide_ids": ["s1"]}),
            )

            with self.assertRaisesRegex(runner.RunnerError, "pre_submit_review"):
                runner.run_stage(project_root, "live-create", profile="production_live")


if __name__ == "__main__":
    unittest.main()
