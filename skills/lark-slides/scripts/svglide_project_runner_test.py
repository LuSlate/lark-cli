# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_project_runner as runner


class SVGlideProjectRunnerTest(unittest.TestCase):
    def write_plan(self, project_root: Path) -> None:
        (project_root / "02-plan").mkdir(parents=True, exist_ok=True)
        (project_root / "02-plan/slide_plan.json").write_text(
            json.dumps(
                {
                    "route": "svglide-svg",
                    "language": "zh-CN",
                    "audience": "企业管理层",
                    "deck_structure": ["cover", "content", "closing"],
                    "style_preset": "safe-native-v1",
                    "style_selection_reason": "用于稳定测试",
                    "style_system": {
                        "palette": ["#111111", "#ffffff"],
                        "typography": "system",
                        "background_strategy": "solid",
                        "motif": "test",
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

    def make_project(self, tmpdir: str) -> Path:
        plan_root = Path(tmpdir) / ".lark-slides/plan"
        result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
        project_root = Path(result["project_root"])
        self.write_plan(project_root)
        self.run_source(project_root)
        self.write_plan_confirmation(project_root)
        runner.run_confirm_plan_stage(project_root, runner.load_state(project_root))
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
        self.assertEqual(runner.normalize_stage("strategy-review"), "strategy_review")
        self.assertEqual(runner.normalize_stage("theme-validate"), "theme_validate")
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
        self.assertEqual(runner.normalize_stage("ppe-proof"), "ppe_proof")
        self.assertEqual(runner.normalize_stage("pre-submit-review"), "pre_submit_review")
        self.assertEqual(runner.normalize_stage("pre-submit"), "pre_submit_review")
        self.assertEqual(runner.normalize_stage("live-create"), "live_create")

    def test_stages_until_uses_normalized_stage_graph(self) -> None:
        dry_run = runner.stages_until("dry_run")
        self.assertIn("source", dry_run)
        self.assertIn("confirm_plan", dry_run)
        self.assertIn("strategy_review", dry_run)
        self.assertIn("theme_validate", dry_run)
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
        self.assertIn("dry_run", dry_run)
        self.assertNotIn("ppe_proof", dry_run)
        self.assertNotIn("live_create", dry_run)
        self.assertNotIn("readback", dry_run)
        self.assertNotIn("export", dry_run)

        readback = runner.stages_until("readback")
        self.assertIn("ppe_proof", readback)
        self.assertIn("pre_submit_review", readback)
        self.assertIn("live_create", readback)
        self.assertIn("readback", readback)

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
            self.assertIn("chart_verify", called_stages)
            self.assertIn("semantic_review", called_stages)
            self.assertIn("runtime_review", called_stages)
            self.assertIn("visual_distinctness_review", called_stages)
            self.assertIn("theme_validate", called_stages)
            self.assertIn("package_check", called_stages)
            self.assertIn("theme_adherence", called_stages)
            self.assertLess(called_stages.index("strategy_review"), called_stages.index("theme_validate"))
            self.assertLess(called_stages.index("theme_validate"), called_stages.index("confirm_plan"))
            self.assertLess(called_stages.index("confirm_plan"), called_stages.index("package_check"))
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
            self.assertIn("pre_submit_review", called_stages)
            self.assertLess(called_stages.index("dry_run"), called_stages.index("ppe_proof"))
            self.assertLess(called_stages.index("ppe_proof"), called_stages.index("pre_submit_review"))
            self.assertLess(called_stages.index("pre_submit_review"), called_stages.index("live_create"))
            self.assertTrue(all(profile == "production_live" for _, profile in calls))

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

            with self.assertRaisesRegex(runner.RunnerError, "plan confirmation required"):
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

    def test_generate_svg_requires_confirm_plan_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)

            with self.assertRaisesRegex(runner.RunnerError, "confirm_plan"):
                runner.run_stage(project_root, "generate-svg")

    def test_assets_requires_confirm_plan_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)

            with self.assertRaisesRegex(runner.RunnerError, "confirm_plan"):
                runner.run_stage(project_root, "assets")

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
            receipt = json.loads((project_root / "receipts/generate_svg.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["generation_mode"], "artboard_satori")
            self.assertEqual(receipt["generator_mode"], "script")
            self.assertEqual(receipt["artboard_receipts"], ["04-svg/artboard/page-001.receipt.json"])
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
            self.assertEqual(receipt["page_receipts"], ["04-svg/page-001.receipt.json"])
            self.assertTrue((project_root / "06-check/template-fit.json").exists())
            self.assertTrue((project_root / "receipts/template-fit-check.json").exists())
            self.assertTrue((project_root / "04-svg/artboard/page-001.png").exists())
            self.assertTrue((project_root / "05-preview/contact-sheet.png").exists())
            page_receipt = json.loads((project_root / "04-svg/page-001.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(page_receipt["generation_mode"], "artboard_satori")
            self.assertEqual(page_receipt["artboard_receipt"], "04-svg/artboard/page-001.receipt.json")

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

    def test_prepare_requires_confirm_plan_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            (project_root / "04-svg/page-001.svg").write_text("<svg></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "confirm_plan"):
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
            source.write_text("<svg><rect /></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after generate_svg"):
                runner.run_stage(project_root, "prepare")

    def test_dry_run_refuses_failed_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = self.make_project(tmpdir)
            (project_root / "06-check/quality-gate.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "quality gate"):
                runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=lambda *a, **k: self.completed(a[0]))

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
