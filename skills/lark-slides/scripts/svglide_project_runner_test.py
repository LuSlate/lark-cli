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
                            "renderer_id": "test-renderer",
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
                            "renderer_id": "test-renderer",
                            "layout_family": "content",
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
                            "renderer_id": "test-renderer",
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

    def write_plan_confirmation(self, project_root: Path) -> None:
        plan = project_root / "02-plan/slide_plan.json"
        (project_root / "02-plan/plan-confirmation.json").write_text(
            json.dumps(
                {
                    "version": "svglide-plan-confirmation/v1",
                    "status": "confirmed",
                    "confirmed_by": "user",
                    "confirmed_at": "2026-06-18T00:00:00+08:00",
                    "plan_path": "02-plan/slide_plan.json",
                    "plan_sha256": runner.file_sha256(plan),
                }
            ),
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
        (project_root / "04-svg/prepared/page-001.svg").write_text("<svg></svg>", encoding="utf-8")
        (project_root / "06-check/quality-gate.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")
        return project_root

    def completed(self, command: list[str], payload: dict[str, object] | None = None, returncode: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode, stdout=json.dumps(payload or {"ok": True}), stderr="")

    def write_ppe_input(self, project_root: Path) -> None:
        (project_root / "07-create/ppe-proof.input.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "environment": {"name": "Pre_release", "x-tt-env": "ppe_pure_svg"},
                    "auth": {"identity": "user"},
                    "proxy": {"mode": "whistle", "rewrite_host": "ppe"},
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
        self.assertEqual(runner.normalize_stage("aesthetic-review"), "aesthetic_review")
        self.assertEqual(runner.normalize_stage("chart-verify"), "chart_verify")
        self.assertEqual(runner.normalize_stage("semantic-review"), "semantic_review")
        self.assertEqual(runner.normalize_stage("runtime-review"), "runtime_review")
        self.assertEqual(runner.normalize_stage("generate"), "generate_svg")
        self.assertEqual(runner.normalize_stage("generate-svg"), "generate_svg")
        self.assertEqual(runner.normalize_stage("quality-gate"), "quality_gate")
        self.assertEqual(runner.normalize_stage("preview-lint"), "preview_lint")
        self.assertEqual(runner.normalize_stage("dry-run"), "dry_run")
        self.assertEqual(runner.normalize_stage("ppe-proof"), "ppe_proof")
        self.assertEqual(runner.normalize_stage("live-create"), "live_create")

    def test_stages_until_uses_normalized_stage_graph(self) -> None:
        dry_run = runner.stages_until("dry_run")
        self.assertIn("source", dry_run)
        self.assertIn("confirm_plan", dry_run)
        self.assertIn("strategy_review", dry_run)
        self.assertIn("assets", dry_run)
        self.assertIn("generate_svg", dry_run)
        self.assertIn("aesthetic_review", dry_run)
        self.assertIn("chart_verify", dry_run)
        self.assertIn("semantic_review", dry_run)
        self.assertIn("runtime_review", dry_run)
        self.assertIn("quality_gate", dry_run)
        self.assertIn("dry_run", dry_run)
        self.assertNotIn("ppe_proof", dry_run)
        self.assertNotIn("live_create", dry_run)
        self.assertNotIn("readback", dry_run)
        self.assertNotIn("export", dry_run)

        readback = runner.stages_until("readback")
        self.assertIn("ppe_proof", readback)
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
            self.assertLess(called_stages.index("chart_verify"), called_stages.index("semantic_review"))
            self.assertLess(called_stages.index("semantic_review"), called_stages.index("quality_gate"))
            self.assertNotIn("dry_run", called_stages)
            self.assertNotIn("ppe_proof", called_stages)
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
            self.assertLess(called_stages.index("dry_run"), called_stages.index("ppe_proof"))
            self.assertLess(called_stages.index("ppe_proof"), called_stages.index("live_create"))
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

    def test_generate_svg_adopts_existing_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
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

    def test_generate_svg_runs_local_generator_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("smoke", "Smoke", plan_root=plan_root)
            project_root = Path(result["project_root"])
            self.write_plan(project_root)
            self.write_plan_confirmation(project_root)
            self.run_source(project_root)
            runner.run_stage(project_root, "confirm-plan")
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
            hashes = runner.prepared_file_hashes(project_root)
            (project_root / "06-check/quality-gate.json").write_text(json.dumps({"status": "passed", "prepared_files": hashes}), encoding="utf-8")
            (project_root / "04-svg/prepared/page-001.svg").write_text("<svg><rect /></svg>", encoding="utf-8")

            with self.assertRaisesRegex(runner.RunnerError, "changed after quality gate"):
                runner.run_create_stage(project_root, runner.load_state(project_root), "dry_run", dry_run=True, command_runner=lambda *a, **k: self.completed(a[0]))

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


if __name__ == "__main__":
    unittest.main()
