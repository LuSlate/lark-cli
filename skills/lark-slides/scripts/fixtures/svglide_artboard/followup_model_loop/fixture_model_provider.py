#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


THEME = {
    "colors": {
        "background": "#F8F8F4",
        "panel": "#FFFFFF",
        "primary": "#BE123C",
        "accent": "#111111",
        "text": "#111111",
        "muted": "#666666",
    }
}

LOADED_RULE_SET = [
    "skills/lark-slides/references/lark-slides-create-svg.md",
    "skills/lark-slides/references/beautiful-html-template-families.json",
    "skills/lark-slides/references/component-registry.json",
    "skills/lark-slides/references/asset-strategy-registry.json",
    "skills/lark-slides/references/svg-aesthetic-review.md",
    "skills/lark-slides/references/svg-protocol.md",
    "skills/lark-slides/references/svglide-artifacts.spec.md",
    "skills/lark-slides/references/svglide-assets.contract.md",
    "skills/lark-slides/references/svglide-checks.checklist.md",
    "skills/lark-slides/references/svglide-create-svg.contract.md",
    "skills/lark-slides/references/svglide-generate-svg.contract.md",
    "skills/lark-slides/references/svglide-lock.contract.md",
    "skills/lark-slides/references/svglide-plan.contract.md",
    "skills/lark-slides/references/svglide-planning-layer.md",
    "skills/lark-slides/references/svglide-ppt-master-migration.matrix.md",
    "skills/lark-slides/references/svglide-preview.spec.md",
    "skills/lark-slides/references/svglide-readback.contract.md",
    "skills/lark-slides/references/svglide-route-admission.md",
    "skills/lark-slides/references/svglide-svg-private.rules.json",
    "skills/lark-slides/references/svglide-validation-checklist.md",
    "skills/lark-slides/references/svglide-visual-planning.md",
    "skills/lark-slides/references/svglide-workflow.spec.md",
]


def canvas_spec_for(
    template_id: str,
    content: dict[str, object],
    semantic_role: str = "title",
    theme: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "version": "svglide-canvas-spec/v1",
        "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
        "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
        "template_id": template_id,
        "theme_id": "swiss-red",
        "theme": theme or THEME,
        "content": content,
        "semantic_elements": [
            {
                "element_id": "title",
                "kind": "text",
                "role": semantic_role,
                "source_ref": "canvas_spec.content.title",
                "bbox": {"x": 84, "y": 96, "width": 700, "height": 96},
            }
        ],
        "quality_constraints": {
            "max_title_lines": 2,
            "min_font_size": 18,
            "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
        },
    }


CASE_PROFILES: dict[str, dict[str, object]] = {
    "spacex": {
        "triggers": ["spacex", "space x", "ipo"],
        "topic": "spacex IPO 分析",
        "audience": "投资/战略分析读者",
        "objective": "用三页说明 SpaceX IPO 分析的核心判断框架。",
        "narrative_arc": ["提出问题", "建立框架", "收束判断"],
        "visual_identity": "深色航天资本市场信号",
        "tone": "审慎、分析型、可追溯",
        "source_policy": "不编造 IPO 日期或估值事实。",
        "style_preset": "raw_grid",
        "theme": THEME,
        "theme_reason": "SpaceX IPO 分析适合深色资本市场信号主题。",
        "style_system": {
            "palette": {"background": "#F8F8F4", "text": "#111111", "accent": "#BE123C"},
            "typography": "Satori-compatible static hierarchy",
            "background_strategy": "dark market terminal",
            "motif": "orbital capital signal",
        },
        "visual_dna": {
            "theme_archetype": "space_capital_market",
            "palette": "orbital capital-market signal",
            "layout_motif": "发射窗口与资本市场信号线",
            "shape_language": "轨道线、窗口卡、风险矩阵",
            "image_treatment": "发射或航天图片配暗色 scrim，文字保持 SVG 覆盖",
            "component_bias": "market_signal, timeline_rail, dashboard_scorecard",
            "theme_visual_anchors": ["发射窗口", "轨道线", "资本信号"],
        },
        "art_direction": {
            "cover_treatment": "深色发射资产封面叠加资本市场信号。",
            "section_divider_treatment": "用轨道线条做节奏分隔。",
            "closing_treatment": "以投资问题清单收束。",
            "deck_motif": "发射窗口与资本信号线",
            "svg_native_moments": ["封面 chips", "轨道线", "风险折价卡"],
        },
        "source_notes_markdown": "# Source Notes\n\n- SpaceX is a private aerospace company.\n- IPO timing is not confirmed.\n- Analysis separates Starlink, launch services, and risk discount.\n",
        "evidence_items": [
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
        "slides": [
            {
                "page": 1,
                "page_type": "cover",
                "section": "开场",
                "role": "thesis",
                "title": "SpaceX IPO 分析框架",
                "key_message": "IPO 价值判断取决于 Starlink、发射业务与风险折价。",
                "template_id": "executive-dashboard",
                "content_goal": "建立分析框架。",
                "visual_goal": "使用深色金融航天封面。",
                "content_requirements": {
                    "eyebrow": "SPACE CAPITAL MARKET",
                    "subtitle": "把未确认 IPO 传闻转成可审查的投资分析框架。",
                    "chips": ["Starlink", "Launch", "Risk"],
                },
                "visual_role": "investment thesis cover",
                "body_points": ["Starlink 规模", "发射业务韧性", "风险折价"],
                "renderer_id": "artboard_satori.executive-dashboard",
                "layout_family": "cover",
                "visual_recipe": "hero_typography",
                "visual_intent": "建立投资分析框架。",
                "visual_focal_point": "标题和 Starlink/Launch/Risk 标签。",
                "visual_signature": "dark orbital market cover",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect", "circle"],
                "svg_primitives": ["typography", "rect", "circle"],
                "xml_like_risk": "普通 bullets 会弱化投资框架。",
                "content_density_contract": "cover title plus 3 chips",
            },
            {
                "page": 2,
                "page_type": "content",
                "section": "价值驱动",
                "role": "evidence",
                "title": "三条价值驱动线",
                "key_message": "Starlink、发射服务和资本开支共同决定估值弹性。",
                "template_id": "trend-grid-report",
                "content_goal": "拆解核心价值驱动。",
                "visual_goal": "用数据故事卡说明驱动因素。",
                "content_requirements": {
                    "eyebrow": "DATA STORY",
                    "subtitle": "把 IPO 价值拆成收入规模、发射韧性和资本效率。",
                    "metrics": ["Starlink 规模", "Launch 履约", "Capex 现金"],
                    "metric_labels": ["收入规模", "发射韧性", "资本效率"],
                    "milestones": ["规模", "发射", "现金", "风险"],
                    "callout": "增长上行，风险折价。",
                },
                "visual_role": "data story",
                "body_points": ["Starlink 规模影响收入弹性", "发射服务验证履约能力", "资本开支影响现金折价"],
                "renderer_id": "artboard_satori.trend-grid-report",
                "layout_family": "data_story",
                "visual_recipe": "infographic_scorecard",
                "visual_intent": "拆解 IPO 价值驱动。",
                "visual_focal_point": "三张指标卡和结论条。",
                "visual_signature": "dark data story cards",
                "svg_effects": ["typography", "chart_geometry"],
                "required_primitives": ["typography", "micro_chart"],
                "svg_primitives": ["typography", "micro_chart", "rect"],
                "xml_like_risk": "简单列表会损失价值拆解层次。",
                "content_density_contract": "3 metrics plus callout",
                "chart_contract": {
                    "type": "micro_chart",
                    "source_refs": ["item-002", "item-003"],
                    "encoding": "qualitative comparison bars and decision timeline",
                    "claims": ["Starlink 规模", "Launch 履约", "Capex 现金"],
                },
            },
            {
                "page": 3,
                "page_type": "closing",
                "section": "判断边界",
                "role": "takeaway",
                "title": "投资判断边界",
                "key_message": "没有确认 IPO 时间前，应输出条件判断而非确定结论。",
                "template_id": "ledger-briefing",
                "content_goal": "收束风险和后续观察点。",
                "visual_goal": "用总结页给出审慎结论。",
                "content_requirements": {
                    "eyebrow": "INVESTOR CHECKLIST",
                    "subtitle": "将市场传闻转为可复核的跟踪清单。",
                    "takeaways": ["确认上市时间", "拆分业务假设", "跟踪监管与现金流风险"],
                },
                "visual_role": "closing checklist",
                "body_points": ["确认上市时间", "拆分业务假设", "跟踪监管与现金流风险"],
                "renderer_id": "artboard_satori.ledger-briefing",
                "layout_family": "closing",
                "visual_recipe": "brand_system",
                "visual_intent": "收束风险和后续观察点。",
                "visual_focal_point": "三条投资检查项。",
                "visual_signature": "dark closing checklist",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect"],
                "svg_primitives": ["typography", "rect"],
                "xml_like_risk": "结论过度确定会误导投资判断。",
                "content_density_contract": "3 takeaways",
            },
        ],
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
                "page": 2,
                "placement_role": "body_visual",
                "query": "Starlink satellites orbit public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "space network background",
            },
            {
                "id": "rocket-stage",
                "page": 3,
                "placement_role": "closing",
                "query": "rocket launch pad night public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "launch infrastructure",
            },
        ],
    },
    "iceland": {
        "triggers": ["冰岛", "iceland", "volcano", "火山"],
        "topic": "冰岛火山研究",
        "audience": "地理/科学研究读者",
        "objective": "用三页说明冰岛火山研究的观测框架与风险判断。",
        "narrative_arc": ["地质背景", "监测信号", "风险边界"],
        "visual_identity": "黑色火山岩与热成像研究信号",
        "tone": "科学、冷静、证据优先",
        "source_policy": "不编造喷发时间、震级或实时预警。",
        "style_preset": "editorial_forest",
        "theme": {
            "colors": {
                "background": "#111827",
                "panel": "#1F2937",
                "primary": "#F97316",
                "accent": "#FACC15",
                "text": "#F9FAFB",
                "muted": "#CBD5E1",
            }
        },
        "theme_reason": "冰岛火山研究适合暗色地质观测和高对比热信号主题。",
        "style_system": {
            "palette": {"background": "#111827", "text": "#F9FAFB", "accent": "#F97316"},
            "typography": "Satori-compatible scientific hierarchy",
            "background_strategy": "basalt field with thermal signal",
            "motif": "seismic and geothermal trace",
        },
        "visual_dna": {
            "theme_archetype": "volcanic_research_lab",
            "palette": "basalt green with thermal amber and moss accents",
            "layout_motif": "地震波形与熔岩剖面",
            "shape_language": "等值线、震波轨迹、观测卡片",
            "image_treatment": "火山地貌图片配暗色 scrim，保留科学标注区",
            "component_bias": "field_note, signal_card, risk_matrix",
            "theme_visual_anchors": ["火山岩", "地震波形", "热信号"],
        },
        "art_direction": {
            "cover_treatment": "玄武岩暗背景叠加热信号标题。",
            "section_divider_treatment": "用地震波线和等值线做节奏分隔。",
            "closing_treatment": "以风险观察清单收束。",
            "deck_motif": "地震波形与热信号",
            "svg_native_moments": ["热信号 chips", "观测波形", "风险边界卡"],
        },
        "source_notes_markdown": "# Source Notes\n\n- Iceland sits on an active volcanic and rift system.\n- Volcano research combines seismicity, deformation, gas, and field observations.\n- Risk interpretation must separate observed signals from eruption prediction.\n",
        "evidence_items": [
            {
                "id": "item-001",
                "text": "Icelandic volcanic systems are monitored through seismic activity, deformation, gas output, and field observations.",
            },
            {
                "id": "item-002",
                "text": "Scientific interpretation should distinguish measured unrest signals from deterministic eruption prediction.",
            },
            {
                "id": "item-003",
                "text": "A clear research deck should connect tectonic setting, monitoring signals, and risk communication boundaries.",
            },
        ],
        "slides": [
            {
                "page": 1,
                "page_type": "cover",
                "section": "开场",
                "role": "thesis",
                "title": "冰岛火山研究框架",
                "key_message": "研究重点是把地质背景、监测信号和风险解释分开。",
                "template_id": "executive-dashboard",
                "content_goal": "建立研究问题。",
                "visual_goal": "使用火山岩与热信号封面。",
                "content_requirements": {
                    "eyebrow": "VOLCANIC RESEARCH",
                    "subtitle": "从地震、形变和气体信号建立可复核的火山研究框架。",
                    "chips": ["Seismic", "Deformation", "Gas"],
                },
                "visual_role": "research thesis cover",
                "body_points": ["地质背景", "监测信号", "风险解释"],
                "renderer_id": "artboard_satori.executive-dashboard",
                "layout_family": "cover",
                "visual_recipe": "hero_typography",
                "visual_intent": "建立火山研究框架。",
                "visual_focal_point": "标题和 Seismic/Deformation/Gas 标签。",
                "visual_signature": "basalt thermal research cover",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect", "circle"],
                "svg_primitives": ["typography", "rect", "circle"],
                "xml_like_risk": "普通列表会削弱科学研究层次。",
                "content_density_contract": "cover title plus 3 chips",
            },
            {
                "page": 2,
                "page_type": "content",
                "section": "监测信号",
                "role": "evidence",
                "title": "三类核心监测信号",
                "key_message": "地震活动、地表形变和气体变化共同构成研究证据链。",
                "template_id": "trend-grid-report",
                "content_goal": "拆解核心观测信号。",
                "visual_goal": "用科学数据故事卡说明观测链路。",
                "content_requirements": {
                    "eyebrow": "SIGNAL STORY",
                    "subtitle": "把火山活动拆成地震、形变和气体三类可观测信号。",
                    "metrics": ["地震活动", "地表形变", "气体变化"],
                    "metric_labels": ["震群频率", "形变趋势", "挥发物线索"],
                    "milestones": ["背景", "震动", "形变", "解释"],
                    "callout": "信号增强，不等于确定喷发。",
                },
                "visual_role": "scientific data story",
                "body_points": ["地震活动提示岩浆移动", "地表形变反映压力变化", "气体变化补充地下过程线索"],
                "renderer_id": "artboard_satori.trend-grid-report",
                "layout_family": "data_story",
                "visual_recipe": "infographic_scorecard",
                "visual_intent": "拆解火山监测证据链。",
                "visual_focal_point": "三张监测信号卡和解释边界。",
                "visual_signature": "dark seismic signal cards",
                "svg_effects": ["typography", "chart_geometry"],
                "required_primitives": ["typography", "micro_chart"],
                "svg_primitives": ["typography", "micro_chart", "rect"],
                "xml_like_risk": "简单列表会损失监测链路层次。",
                "content_density_contract": "3 metrics plus callout",
                "chart_contract": {
                    "type": "micro_chart",
                    "source_refs": ["item-001", "item-002"],
                    "encoding": "qualitative monitoring signal comparison and interpretation timeline",
                    "claims": ["地震活动", "地表形变", "气体变化"],
                },
            },
            {
                "page": 3,
                "page_type": "closing",
                "section": "风险边界",
                "role": "takeaway",
                "title": "风险解释边界",
                "key_message": "研究结论应说明信号强弱、证据缺口和不确定性。",
                "template_id": "ledger-briefing",
                "content_goal": "收束研究边界。",
                "visual_goal": "用总结页给出风险解释清单。",
                "content_requirements": {
                    "eyebrow": "RESEARCH CHECKLIST",
                    "subtitle": "把观测信号转成可沟通、可复核的研究判断。",
                    "takeaways": ["区分信号与预测", "标注证据缺口", "持续跟踪多源观测"],
                },
                "visual_role": "research checklist",
                "body_points": ["区分信号与预测", "标注证据缺口", "持续跟踪多源观测"],
                "renderer_id": "artboard_satori.ledger-briefing",
                "layout_family": "closing",
                "visual_recipe": "brand_system",
                "visual_intent": "收束风险解释边界。",
                "visual_focal_point": "三条研究检查项。",
                "visual_signature": "dark research checklist",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect"],
                "svg_primitives": ["typography", "rect"],
                "xml_like_risk": "把信号等同预测会误导风险沟通。",
                "content_density_contract": "3 takeaways",
            },
        ],
        "asset_contracts": [
            {
                "id": "iceland-volcano-cover",
                "page": 1,
                "placement_role": "cover",
                "query": "Iceland volcano landscape public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "volcanic landscape with dark basalt negative space",
            },
            {
                "id": "seismic-monitoring",
                "page": 2,
                "placement_role": "body_visual",
                "query": "volcano monitoring seismic station Iceland public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "scientific monitoring environment",
            },
            {
                "id": "lava-field",
                "page": 3,
                "placement_role": "closing",
                "query": "Iceland lava field geothermal public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "lava field or geothermal terrain",
            },
        ],
    },
    "new_zealand": {
        "triggers": ["新西兰", "new zealand", "zealand", "landscape", "风光"],
        "topic": "新西兰风光",
        "audience": "旅行内容策划读者",
        "objective": "用三页呈现新西兰风光的视觉叙事和路线策划重点。",
        "narrative_arc": ["建立印象", "拆解景观层次", "形成路线建议"],
        "visual_identity": "高山湖泊与海岸光线的旅行画板",
        "tone": "清爽、克制、沉浸式",
        "source_policy": "不编造实时天气、门票价格或交通状态。",
        "style_preset": "cobalt_bloom",
        "theme": {
            "colors": {
                "background": "#0B3B34",
                "panel": "#12564C",
                "primary": "#38BDF8",
                "accent": "#FBBF24",
                "text": "#F8FAFC",
                "muted": "#BAE6FD",
            }
        },
        "theme_reason": "新西兰风光适合以深绿底色承载高山湖泊和海岸光线。",
        "style_system": {
            "palette": {"background": "#0B3B34", "text": "#F8FAFC", "accent": "#38BDF8"},
            "typography": "Satori-compatible travel editorial hierarchy",
            "background_strategy": "alpine lake with restrained overlay",
            "motif": "route ribbon and landscape layers",
        },
        "visual_dna": {
            "theme_archetype": "alpine_coast_travel_board",
            "palette": "fern green with lake mist and sunrise amber",
            "layout_motif": "山脉层叠与路线丝带",
            "shape_language": "地形层、路线轨迹、目的地卡片",
            "image_treatment": "自然风光图片配轻度暗色 scrim，保留远景层次",
            "component_bias": "destination_card, route_strip, editorial_caption",
            "theme_visual_anchors": ["南岛山脉", "湖泊光线", "海岸路线"],
        },
        "art_direction": {
            "cover_treatment": "高山湖泊大图叠加旅行标题。",
            "section_divider_treatment": "用路线丝带和地形层做节奏分隔。",
            "closing_treatment": "以路线策划清单收束。",
            "deck_motif": "山脉层叠与路线丝带",
            "svg_native_moments": ["目的地 chips", "路线轨迹", "行程建议卡"],
        },
        "source_notes_markdown": "# Source Notes\n\n- New Zealand landscape storytelling often combines alpine, lake, fjord, and coastal scenes.\n- Travel planning should distinguish visual appeal from real-time weather and access status.\n- A compact deck can organize scenic value, route rhythm, and planning cautions.\n",
        "evidence_items": [
            {
                "id": "item-001",
                "text": "New Zealand scenic storytelling commonly combines alpine terrain, lakes, fjords, and coastlines.",
            },
            {
                "id": "item-002",
                "text": "Travel content should separate evergreen route framing from real-time weather or access claims.",
            },
            {
                "id": "item-003",
                "text": "A visual route deck should balance destination appeal, route rhythm, and planning cautions.",
            },
        ],
        "slides": [
            {
                "page": 1,
                "page_type": "cover",
                "section": "开场",
                "role": "thesis",
                "title": "新西兰风光路线",
                "key_message": "风光叙事应串联高山、湖泊和海岸三类视觉记忆点。",
                "template_id": "executive-dashboard",
                "content_goal": "建立旅行视觉印象。",
                "visual_goal": "使用高山湖泊旅行封面。",
                "content_requirements": {
                    "eyebrow": "LANDSCAPE ROUTE",
                    "subtitle": "把南岛山脉、湖泊光线和海岸路线组织成一条视觉叙事。",
                    "chips": ["Alpine", "Lake", "Coast"],
                },
                "visual_role": "travel editorial cover",
                "body_points": ["高山层次", "湖泊光线", "海岸路线"],
                "renderer_id": "artboard_satori.executive-dashboard",
                "layout_family": "cover",
                "visual_recipe": "hero_typography",
                "visual_intent": "建立旅行视觉叙事。",
                "visual_focal_point": "标题和 Alpine/Lake/Coast 标签。",
                "visual_signature": "alpine lake route cover",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect", "circle"],
                "svg_primitives": ["typography", "rect", "circle"],
                "xml_like_risk": "普通景点列表会削弱路线叙事。",
                "content_density_contract": "cover title plus 3 chips",
            },
            {
                "page": 2,
                "page_type": "content",
                "section": "景观层次",
                "role": "evidence",
                "title": "三层风光记忆点",
                "key_message": "高山、湖泊和海岸形成互补的视觉节奏。",
                "template_id": "trend-grid-report",
                "content_goal": "拆解风光层次。",
                "visual_goal": "用旅行数据故事卡说明路线价值。",
                "content_requirements": {
                    "eyebrow": "SCENIC STORY",
                    "subtitle": "把风光路线拆成地貌层次、光线窗口和移动节奏。",
                    "metrics": ["高山层次", "湖泊光线", "海岸路线"],
                    "metric_labels": ["地貌层次", "日照窗口", "移动节奏"],
                    "milestones": ["山脉", "湖泊", "海岸", "行程"],
                    "callout": "视觉强度，要配合季节和路况。",
                },
                "visual_role": "travel data story",
                "body_points": ["高山提供空间纵深", "湖泊形成光线记忆点", "海岸路线增强移动节奏"],
                "renderer_id": "artboard_satori.trend-grid-report",
                "layout_family": "data_story",
                "visual_recipe": "infographic_scorecard",
                "visual_intent": "拆解风光路线价值。",
                "visual_focal_point": "三张风光记忆点卡和路线结论。",
                "visual_signature": "dark alpine scenic cards",
                "svg_effects": ["typography", "chart_geometry"],
                "required_primitives": ["typography", "micro_chart"],
                "svg_primitives": ["typography", "micro_chart", "rect"],
                "xml_like_risk": "简单景点罗列会损失路线层次。",
                "content_density_contract": "3 metrics plus callout",
                "chart_contract": {
                    "type": "micro_chart",
                    "source_refs": ["item-001", "item-003"],
                    "encoding": "qualitative landscape layer comparison and route rhythm",
                    "claims": ["高山层次", "湖泊光线", "海岸路线"],
                },
            },
            {
                "page": 3,
                "page_type": "closing",
                "section": "路线建议",
                "role": "takeaway",
                "title": "路线策划边界",
                "key_message": "最终路线应同时考虑季节、天气和交通可达性。",
                "template_id": "ledger-briefing",
                "content_goal": "收束路线策划建议。",
                "visual_goal": "用总结页给出行程检查项。",
                "content_requirements": {
                    "eyebrow": "ROUTE CHECKLIST",
                    "subtitle": "把漂亮画面转成可执行的旅行内容策划。",
                    "takeaways": ["按季节选择光线", "预留天气弹性", "核对道路与步道状态"],
                },
                "visual_role": "route checklist",
                "body_points": ["按季节选择光线", "预留天气弹性", "核对道路与步道状态"],
                "renderer_id": "artboard_satori.ledger-briefing",
                "layout_family": "closing",
                "visual_recipe": "brand_system",
                "visual_intent": "收束路线策划边界。",
                "visual_focal_point": "三条行程检查项。",
                "visual_signature": "dark route checklist",
                "svg_effects": ["typography"],
                "required_primitives": ["typography", "rect"],
                "svg_primitives": ["typography", "rect"],
                "xml_like_risk": "忽略天气和交通会误导旅行计划。",
                "content_density_contract": "3 takeaways",
            },
        ],
        "asset_contracts": [
            {
                "id": "new-zealand-alpine-cover",
                "page": 1,
                "placement_role": "cover",
                "query": "New Zealand alpine lake landscape public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "alpine lake with calm negative space",
            },
            {
                "id": "southern-alps-route",
                "page": 2,
                "placement_role": "body_visual",
                "query": "New Zealand Southern Alps travel landscape public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "mountain route scenery",
            },
            {
                "id": "new-zealand-coast",
                "page": 3,
                "placement_role": "closing",
                "query": "New Zealand coastline scenic road public domain",
                "required": True,
                "safe_text_zones": [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                "crop_hint": "coastal road or fjord travel scene",
            },
        ],
    },
}


def select_profile(prompt_text: str) -> dict[str, object]:
    raw_prompt = instruction_raw_prompt(prompt_text)
    haystack = (raw_prompt or prompt_text).lower()
    for profile in CASE_PROFILES.values():
        if any(str(trigger).lower() in haystack for trigger in profile["triggers"]):
            return profile
    return CASE_PROFILES["spacex"]


def instruction_raw_prompt(prompt_text: str) -> str | None:
    marker = "Instruction:"
    if marker in prompt_text:
        candidate = prompt_text.split(marker, 1)[1].lstrip()
        try:
            instruction, _ = json.JSONDecoder().raw_decode(candidate)
            raw_prompt = instruction.get("raw_prompt")
            if isinstance(raw_prompt, str) and raw_prompt.strip():
                return raw_prompt
        except json.JSONDecodeError:
            pass
    return None


def slide_source_refs() -> list[str]:
    return ["item-001", "item-002", "item-003"]


def source_plan(profile: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "svglide-source-plan/v1",
        "source_notes_markdown": profile["source_notes_markdown"],
        "evidence": {
            "schema_version": "svglide-evidence/v1",
            "source_status": "ready",
            "generated_from": "followup_model_loop_fixture_provider",
            "research_status": "fixture_command_provider",
            "items": profile["evidence_items"],
        },
    }


def deck_plan(profile: dict[str, object]) -> dict[str, object]:
    slides = profile["slides"]
    return {
        "schema_version": "svglide-deck-plan/v1",
        "topic": profile["topic"],
        "audience": profile["audience"],
        "objective": profile["objective"],
        "target_slide_count": 3,
        "narrative_arc": profile["narrative_arc"],
        "theme_direction": {
            "preferred_theme_ids": ["swiss-red"],
            "visual_identity": profile["visual_identity"],
            "tone": profile["tone"],
        },
        "constraints": {
            "generation_mode": "artboard_satori",
            "source_policy": profile["source_policy"],
            "forbidden_outputs": ["free_html", "free_css", "free_svg", "markdown_fence"],
        },
        "slides": [
            {
                "page": slide["page"],
                "title": slide["title"],
                "role": slide["role"],
                "key_message": slide["key_message"],
                "content_goal": slide["content_goal"],
                "visual_goal": slide["visual_goal"],
                "allowed_template_ids": [slide["template_id"]],
            }
            for slide in slides
        ],
    }


def slide_plan(profile: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "svglide-slide-plan/v1",
        "deck_plan_ref": {"path": "02-plan/deck-plan.json"},
        "generation_mode": "artboard_satori",
        "slides": [
            {
                "page": slide["page"],
                "title": slide["title"],
                "key_message": slide["key_message"],
                "template_id": slide["template_id"],
                "theme_id": "swiss-red",
                "content_requirements": {
                    **slide["content_requirements"],
                    "title": slide["title"],
                },
                "visual_role": slide["visual_role"],
                "source_policy": profile["source_policy"],
            }
            for slide in profile["slides"]
        ],
    }


def canvas_plan(profile: dict[str, object]) -> dict[str, object]:
    slides = profile["slides"]
    return {
        "schema_version": "svglide-canvas-plan/v1",
        "route": "svglide-svg",
        "generation_mode": "artboard_satori",
        "language": "zh-CN",
        "audience": profile["audience"],
        "deck_structure": ["cover", "content", "closing"],
        "page_count": 3,
        "target_slide_count": 3,
        "plan_path": "02-plan/slide_plan.json",
        "template_family_selection": {
            "enabled": True,
            "source": "beautiful-html-template-families",
            "selected_template_id": "blue-professional",
            "candidate_template_ids": ["blue-professional", "signal", "cobalt-grid"],
            "selection_reason": profile["theme_reason"],
        },
        "visual_identity": {
            "theme_archetype": profile["visual_dna"]["theme_archetype"],
            "design_dna": {
                "palette": profile["visual_dna"]["palette"],
                "layout_motif": profile["visual_dna"]["layout_motif"],
                "shape_language": profile["visual_dna"]["shape_language"],
                "image_treatment": profile["visual_dna"]["image_treatment"],
                "component_bias": profile["visual_dna"]["component_bias"],
                "theme_visual_anchors": profile["visual_dna"]["theme_visual_anchors"],
            },
            "forbidden_reuse": {"recent_decks": 5, "avoid_same_palette": True, "avoid_default_skeleton": True},
            "distinctness_target": {"palette_overlap_max": 0.67, "renderer_sequence_similarity_max": 0.75},
        },
        "loaded_rule_set": LOADED_RULE_SET,
        "quality_gates": {"no_text_overflow": True, "no_debug_guides": True, "no_xml_like_pages": True},
        "art_direction": profile["art_direction"],
        "asset_contracts": profile["asset_contracts"],
        "business_claims": [
            {
                "claim": "+19%",
                "source_type": "assumption",
                "assumption": "Fixture template micro-chart placeholder; not a factual claim.",
            },
            {
                "claim": "4.3%",
                "source_type": "assumption",
                "assumption": "Fixture template micro-chart placeholder; not a factual claim.",
            },
        ],
        "model_loop_fixture": {
            "provider": "command",
            "source": "skills/lark-slides/scripts/fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py",
        },
        "slides": [canvas_slide(slide, profile) for slide in slides],
    }


def canvas_slide(slide: dict[str, object], profile: dict[str, object]) -> dict[str, object]:
    content = {
        **slide["content_requirements"],
        "title": slide["title"],
    }
    payload: dict[str, object] = {
        "page": slide["page"],
        "page_type": slide["page_type"],
        "section": slide["section"],
        "role": slide["role"],
        "title": slide["title"],
        "key_message": slide["key_message"],
        "body_points": slide["body_points"],
        "source_refs": slide_source_refs(),
        "renderer_id": slide["renderer_id"],
        "layout_family": slide["layout_family"],
        "template_variant": str(slide["template_id"]).replace("-", "_"),
        "semantic_blocks": [
            {"block_id": "title", "type": "title", "content": slide["title"]},
            {"block_id": "message", "type": "finding", "content": slide["key_message"]},
        ],
        "component_selection": [
            {"component_id": "title_block", "binds": ["title"]},
            {"component_id": "finding_callout", "binds": ["message"]},
        ],
        "asset_strategy": {"strategy_id": "structured_fallback", "decision": "none_required"},
        "asset_contract": "none_required",
        "content_density_contract": slide["content_density_contract"],
        "risk_flags": [],
        "source_policy": profile["source_policy"],
        "canvas_spec": canvas_spec_for(slide["template_id"], content, theme=profile["theme"]),
    }
    if "chart_contract" in slide:
        payload["chart_contract"] = slide["chart_contract"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--raw-output", required=True)
    args = parser.parse_args()
    profile = select_profile(sys.stdin.read())
    mapping = {
        "source-planner": source_plan,
        "deck-planner": deck_plan,
        "slide-planner": slide_plan,
        "canvas-planner": canvas_plan,
    }
    if args.stage not in mapping:
        raise SystemExit(f"unsupported stage: {args.stage}")
    Path(args.raw_output).write_text(json.dumps(mapping[args.stage](profile), ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
