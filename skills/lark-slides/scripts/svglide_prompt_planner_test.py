#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_project_runner as runner
import svglide_prompt_planner as prompt_planner


class SVGlidePromptPlannerTest(unittest.TestCase):
    def fixture_dir(self) -> Path:
        return Path(__file__).resolve().parent / "fixtures/svglide_artboard/followup_model_loop"

    def fixture_provider_command(self) -> str:
        provider = self.fixture_dir() / "fixture_model_provider.py"
        return f"{sys.executable} {provider} --stage {{stage}} --raw-output {{raw_output}}"

    def fixture_topic(self) -> dict[str, object]:
        return json.loads((self.fixture_dir() / "topic.json").read_text(encoding="utf-8"))

    def test_prompt_builders_do_not_inject_spacex_rules_for_other_topics(self) -> None:
        instruction = prompt_planner.instruction_payload(
            prompt="新西兰风光",
            language="zh-CN",
            target_slide_count=3,
            audience="旅行内容策划读者",
        )
        context = prompt_planner.load_context()
        context["selection"] = {
            "palette_selection": {"selected_palette_id": "brand.zhipu"},
            "theme_template_selection": {
                "template_candidates": [{"template_id": "executive-dashboard"}],
                "theme_candidates": [{"theme_id": "glass-neon"}],
            },
        }
        deck_plan = {
            "schema_version": "svglide-deck-plan/v1",
            "topic": "新西兰风光",
            "audience": "旅行内容策划读者",
            "target_slide_count": 3,
            "slides": [],
        }
        slide_plan = {"schema_version": "svglide-slide-plan/v1", "slides": []}

        prompts = [
            prompt_planner.build_source_prompt(instruction),
            prompt_planner.build_deck_prompt(instruction, context),
            prompt_planner.build_slide_prompt(instruction, deck_plan, context, "deck-sha"),
            prompt_planner.build_canvas_prompt(instruction, deck_plan, slide_plan, context),
        ]

        for planner_prompt in prompts:
            self.assertNotIn("SpaceX", planner_prompt)
            self.assertNotIn("confirmed IPO", planner_prompt)
            self.assertNotIn("investment-analysis", planner_prompt)
        self.assertIn("selection_context", prompts[2])
        self.assertIn("selection_context", prompts[3])
        self.assertIn("template_id/theme_id/palette_id must come from its candidates", prompts[3])

    def test_load_context_filters_legacy_layout_archetypes_from_production_prompt(self) -> None:
        context = prompt_planner.load_context()
        layout_records = context["layout_archetypes"]["archetypes"]

        self.assertEqual([], [item for item in layout_records if item.get("status") == "legacy_debug"])
        self.assertNotIn("architecture-blueprint", {item.get("id") for item in layout_records})

    def fake_provider(self, tmpdir: str) -> Path:
        provider = Path(tmpdir) / "fake_provider.py"
        provider.write_text(
            textwrap.dedent(
                r'''
                #!/usr/bin/env python3
                import argparse
                import json
                from pathlib import Path

                def source_plan():
                    return {
                        "schema_version": "svglide-source-plan/v1",
                        "source_notes_markdown": "# Source Notes\n\n- SpaceX is a private launch and satellite company.\n- IPO timing is not confirmed.\n- Analysis should separate Starlink and launch-service drivers.\n",
                        "evidence": {
                            "schema_version": "svglide-evidence/v1",
                            "source_status": "ready",
                            "generated_from": "fake_provider",
                            "research_status": "fixture",
                            "items": [
                                {"id": "item-001", "text": "SpaceX remains a private aerospace company, so IPO timing must be treated as unconfirmed."},
                                {"id": "item-002", "text": "Starlink scale and launch cadence are central inputs for any SpaceX IPO narrative."},
                                {"id": "item-003", "text": "A useful IPO analysis separates valuation drivers, risk factors, and investor questions."},
                            ],
                        },
                    }

                def deck_plan():
                    return {
                        "schema_version": "svglide-deck-plan/v1",
                        "topic": "spacex IPO 分析",
                        "audience": "投资/战略分析读者",
                        "objective": "用一页说明 SpaceX IPO 分析的核心判断框架。",
                        "target_slide_count": 1,
                        "narrative_arc": ["提出问题", "建立框架", "收束判断"],
                        "theme_direction": {
                            "preferred_theme_ids": ["swiss-red"],
                            "visual_identity": "深色航天资本市场信号",
                            "tone": "审慎、分析型、可追溯",
                        },
                        "constraints": {
                            "generation_mode": "artboard_satori",
                            "source_policy": "不编造 IPO 日期或估值事实。",
                            "forbidden_outputs": ["free_html", "free_css", "free_svg", "markdown_fence"],
                        },
                        "slides": [
                            {
                                "page": 1,
                                "title": "SpaceX IPO 分析框架",
                                "role": "cover",
                                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                                "content_goal": "建立分析框架。",
                                "visual_goal": "使用深色金融航天封面。",
                                "allowed_template_ids": ["executive-dashboard"],
                            }
                        ],
                    }

                def slide_plan():
                    return {
                        "schema_version": "svglide-slide-plan/v1",
                        "deck_plan_ref": {"path": "02-plan/deck-plan.json"},
                        "generation_mode": "artboard_satori",
                        "slides": [
                            {
                                "page": 1,
                                "title": "SpaceX IPO 分析框架",
                                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                                "template_id": "executive-dashboard",
                                "theme_id": "swiss-red",
                                "content_requirements": {
                                    "eyebrow": "SPACE CAPITAL MARKET",
                                    "subtitle": "把未确认 IPO 传闻转成可审查的投资分析框架。",
                                    "chips": ["Starlink", "Launch", "Risk"],
                                },
                                "visual_role": "investment thesis cover",
                                "source_policy": "不编造 IPO 日期或估值事实。",
                            }
                        ],
                    }

                def canvas_plan():
                    canvas_spec = {
                        "version": "svglide-canvas-spec/v1",
                        "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
                        "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
                        "template_id": "executive-dashboard",
                        "theme_id": "swiss-red",
                        "theme": {"colors": {"background": "#F8F8F4", "panel": "#FFFFFF", "primary": "#BE123C", "accent": "#111111", "text": "#111111", "muted": "#666666"}},
                        "content": {"eyebrow": "SPACE CAPITAL MARKET", "title": "SpaceX IPO 分析框架", "subtitle": "把未确认 IPO 传闻转成可审查的投资分析框架。", "chips": ["Starlink", "Launch", "Risk"]},
                        "semantic_elements": [
                            {"element_id": "title", "kind": "text", "role": "title", "source_ref": "canvas_spec.content.title", "bbox": {"x": 84, "y": 142, "width": 628, "height": 142}}
                        ],
                        "quality_constraints": {"max_title_lines": 2, "min_font_size": 18, "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460}},
                    }
                    return {
                        "schema_version": "svglide-canvas-plan/v1",
                        "route": "svglide-svg",
                        "generation_mode": "artboard_satori",
                        "page_count": 1,
                        "target_slide_count": 1,
                        "plan_path": "02-plan/slide_plan.json",
                        "template_family_selection": {
                            "enabled": True,
                            "source": "beautiful-html-template-families",
                            "selected_template_id": "blue-professional",
                            "candidate_template_ids": ["blue-professional", "signal", "cobalt-grid"],
                            "selection_reason": "SpaceX IPO 分析适合正式分析型 family。",
                        },
                        "loaded_rule_set": [
                            "skills/lark-slides/references/svglide-canvas-spec.schema.json",
                            "skills/lark-slides/references/beautiful-html-template-families.json",
                        ],
                        "quality_gates": {"no_text_overflow": True, "no_debug_guides": True, "no_xml_like_pages": True},
                        "art_direction": {
                            "cover_treatment": "深色发射资产封面叠加资本市场信号。",
                            "section_divider_treatment": "用轨道线条做节奏分隔。",
                            "closing_treatment": "以投资问题清单收束。",
                            "deck_motif": "发射窗口与资本信号线",
                            "svg_native_moments": ["封面 chips", "轨道线", "风险折价卡"],
                        },
                        "asset_contracts": [
                            {"id": "spacex-launch-cover", "page": 1, "placement_role": "cover", "query": "SpaceX Falcon 9 launch public domain", "required": True, "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}], "crop_hint": "rocket launch with dark negative space"},
                            {"id": "starlink-orbit", "page": 1, "placement_role": "cover", "query": "Starlink satellites orbit public domain", "required": True, "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}], "crop_hint": "space network background"},
                            {"id": "rocket-stage", "page": 1, "placement_role": "cover", "query": "rocket launch pad night public domain", "required": True, "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}], "crop_hint": "launch infrastructure"},
                        ],
                        "slides": [
                            {
                                "page": 1,
                                "title": "SpaceX IPO 分析框架",
                                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                                "renderer_id": "artboard_satori.executive-dashboard",
                                "layout_family": "cover",
                                "template_variant": "cover",
                                "semantic_blocks": [{"block_id": "title", "type": "title", "content": "SpaceX IPO 分析框架"}],
                                "component_selection": [{"component_id": "title_block", "binds": ["title"]}],
                                "asset_strategy": {"strategy_id": "real_image_required", "decision": "use cover image slot"},
                                "content_density_contract": "cover title plus 3 chips",
                                "risk_flags": [],
                                "source_policy": "不编造 IPO 日期或估值事实。",
                                "canvas_spec": canvas_spec,
                            }
                        ],
                    }

                parser = argparse.ArgumentParser()
                parser.add_argument("--stage", required=True)
                parser.add_argument("--raw-output", required=True)
                args = parser.parse_args()
                mapping = {
                    "source-planner": source_plan,
                    "deck-planner": deck_plan,
                    "slide-planner": slide_plan,
                    "canvas-planner": canvas_plan,
                }
                Path(args.raw_output).write_text(json.dumps(mapping[args.stage](), ensure_ascii=False), encoding="utf-8")
                '''
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return provider

    def test_prompt_plan_writes_instruction_receipts_and_planner_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("spacex-auto", "SpaceX Auto", plan_root=plan_root)
            project = Path(result["project_root"])
            topic = self.fixture_topic()

            receipt = prompt_planner.run_prompt_plan(
                project,
                prompt=str(topic["prompt"]),
                target_slide_count=int(topic["target_slide_count"]),
                language=str(topic["language"]),
                audience=str(topic["audience"]),
                provider="command",
                planner_command=self.fixture_provider_command(),
                trusted_provider_id="fixture-model-provider",
            )

            self.assertEqual("passed", receipt["status"])
            self.assertEqual("command", receipt["provider_type"])
            self.assertEqual("fixture-model-provider", receipt["trusted_provider_evidence"]["trusted_provider_id"])
            self.assertEqual(4, len(receipt["planner_raw_outputs"]))
            self.assertTrue(all(item["sha256"] for item in receipt["planner_raw_outputs"]))
            self.assertTrue((project / "00-input/instruction.json").exists())
            self.assertEqual("spacex IPO 分析", json.loads((project / "00-input/instruction.json").read_text(encoding="utf-8"))["raw_prompt"])
            self.assertTrue((project / "02-plan/deck-plan.json").exists())
            self.assertTrue((project / "02-plan/slide-plan.json").exists())
            self.assertTrue((project / "02-plan/slide_plan.json").exists())
            self.assertTrue((project / "02-plan/planner/deck-planner.input.txt").exists())
            self.assertTrue((project / "02-plan/planner/canvas-planner.raw.txt").exists())
            self.assertTrue((project / "02-plan/plan-confirmation.json").exists())
            self.assertTrue((project / "source/evidence.json").exists())
            self.assertTrue((project / "receipts/prompt-planner.json").exists())
            self.assertEqual("passed", json.loads((project / "06-check/planner-contract-check.json").read_text(encoding="utf-8"))["status"])
            canvas = json.loads((project / "02-plan/slide_plan.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(canvas["asset_contracts"]), 3)
            self.assertEqual("command", canvas["model_loop_fixture"]["provider"])

    def test_prompt_plan_refuses_to_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("spacex-auto", "SpaceX Auto", plan_root=plan_root)
            project = Path(result["project_root"])
            command = self.fixture_provider_command()
            prompt_planner.run_prompt_plan(
                project,
                prompt="spacex IPO 分析",
                target_slide_count=1,
                provider="command",
                planner_command=command,
                trusted_provider_id="fixture-model-provider",
            )

            with self.assertRaisesRegex(prompt_planner.PromptPlannerError, "already exist"):
                prompt_planner.run_prompt_plan(
                    project,
                    prompt="spacex IPO 分析",
                    target_slide_count=1,
                    provider="command",
                    planner_command=command,
                    trusted_provider_id="fixture-model-provider",
                )

    def test_external_planner_requires_trusted_provider_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_root = Path(tmpdir) / ".lark-slides/plan"
            result = runner.init_project("spacex-auto", "SpaceX Auto", plan_root=plan_root)
            project = Path(result["project_root"])

            with self.assertRaisesRegex(prompt_planner.PromptPlannerError, "trusted_provider_id"):
                prompt_planner.run_prompt_plan(
                    project,
                    prompt="spacex IPO 分析",
                    target_slide_count=1,
                    provider="command",
                    planner_command=self.fixture_provider_command(),
                )


if __name__ == "__main__":
    unittest.main()
