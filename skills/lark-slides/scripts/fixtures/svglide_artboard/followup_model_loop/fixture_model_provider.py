#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def source_plan() -> dict[str, object]:
    return {
        "schema_version": "svglide-source-plan/v1",
        "source_notes_markdown": "# Source Notes\n\n- SpaceX is a private aerospace company.\n- IPO timing is not confirmed.\n- Analysis separates Starlink, launch services, and risk discount.\n",
        "evidence": {
            "schema_version": "svglide-evidence/v1",
            "source_status": "ready",
            "generated_from": "followup_model_loop_fixture_provider",
            "research_status": "fixture_command_provider",
            "items": [
                {
                    "id": "item-001",
                    "text": "SpaceX remains privately held, so any IPO date must be treated as unconfirmed analysis context.",
                },
                {
                    "id": "item-002",
                    "text": "Starlink scale, launch cadence, and capital expenditure are core drivers in a SpaceX IPO framing.",
                },
                {
                    "id": "item-003",
                    "text": "Investor-facing analysis should separate valuation upside, execution risk, and market timing.",
                },
            ],
        },
    }


def deck_plan() -> dict[str, object]:
    return {
        "schema_version": "svglide-deck-plan/v1",
        "topic": "spacex IPO 分析",
        "audience": "投资/战略分析读者",
        "objective": "用一页说明 SpaceX IPO 分析的核心判断框架。",
        "target_slide_count": 1,
        "narrative_arc": ["提出问题", "建立框架", "收束判断"],
        "theme_direction": {
            "preferred_theme_ids": ["finance-dark"],
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
                "allowed_template_ids": ["cover-hero"],
            }
        ],
    }


def slide_plan() -> dict[str, object]:
    return {
        "schema_version": "svglide-slide-plan/v1",
        "deck_plan_ref": {"path": "02-plan/deck-plan.json"},
        "generation_mode": "artboard_satori",
        "slides": [
            {
                "page": 1,
                "title": "SpaceX IPO 分析框架",
                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                "template_id": "cover-hero",
                "theme_id": "finance-dark",
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


def canvas_plan() -> dict[str, object]:
    canvas_spec = {
        "version": "svglide-canvas-spec/v1",
        "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
        "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
        "template_id": "cover-hero",
        "theme_id": "finance-dark",
        "theme": {
            "colors": {
                "background": "#07110E",
                "panel": "#10201A",
                "primary": "#22C55E",
                "accent": "#F59E0B",
                "text": "#ECFDF5",
                "muted": "#A7C4B7",
            }
        },
        "content": {
            "eyebrow": "SPACE CAPITAL MARKET",
            "title": "SpaceX IPO 分析框架",
            "subtitle": "把未确认 IPO 传闻转成可审查的投资分析框架。",
            "chips": ["Starlink", "Launch", "Risk"],
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
    return {
        "schema_version": "svglide-canvas-plan/v1",
        "route": "svglide-svg",
        "generation_mode": "artboard_satori",
        "page_count": 1,
        "target_slide_count": 1,
        "plan_path": "02-plan/slide_plan.json",
        "style_preset": "finance-dark",
        "style_selection_reason": "SpaceX IPO 分析适合深色资本市场信号主题。",
        "style_system": {
            "palette": {"background": "#07110E", "text": "#ECFDF5", "accent": "#F59E0B"},
            "typography": "Satori-compatible static hierarchy",
            "background_strategy": "dark market terminal",
            "motif": "orbital capital signal",
        },
        "loaded_rule_set": [
            "skills/lark-slides/references/svglide-canvas-spec.schema.json",
            "skills/lark-slides/references/svglide-template-registry.json",
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
            {
                "id": "spacex-launch-cover",
                "page": 1,
                "placement_role": "cover",
                "query": "SpaceX Falcon 9 launch public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "rocket launch with dark negative space",
            },
            {
                "id": "starlink-orbit",
                "page": 1,
                "placement_role": "cover",
                "query": "Starlink satellites orbit public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "space network background",
            },
            {
                "id": "rocket-stage",
                "page": 1,
                "placement_role": "cover",
                "query": "rocket launch pad night public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "launch infrastructure",
            },
        ],
        "model_loop_fixture": {
            "provider": "command",
            "source": "skills/lark-slides/scripts/fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py",
        },
        "slides": [
            {
                "page": 1,
                "title": "SpaceX IPO 分析框架",
                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                "renderer_id": "artboard_satori.cover-hero",
                "layout_family": "cover",
                "visual_recipe": "hero_typography",
                "visual_intent": "建立投资分析框架。",
                "visual_focal_point": "标题和 Starlink/Launch/Risk 标签。",
                "visual_signature": "dark orbital market cover",
                "svg_effects": ["typography", "asset_scrim"],
                "required_primitives": ["typography", "rect", "circle"],
                "svg_primitives": ["typography", "rect", "circle"],
                "xml_like_risk": "普通 bullets 会弱化投资框架。",
                "content_density_contract": "cover title plus 3 chips",
                "risk_flags": [],
                "source_policy": "不编造 IPO 日期或估值事实。",
                "canvas_spec": canvas_spec,
            }
        ],
    }


def main() -> int:
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
    if args.stage not in mapping:
        raise SystemExit(f"unsupported stage: {args.stage}")
    Path(args.raw_output).write_text(json.dumps(mapping[args.stage](), ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
