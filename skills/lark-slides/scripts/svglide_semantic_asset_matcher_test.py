#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import svglide_semantic_asset_matcher as matcher


def fixture_assets() -> list[dict[str, object]]:
    return [
        {
            "id": "blue-professional",
            "name": "Blue Professional",
            "occasion": ["B2B SaaS pitch", "consulting deliverable", "internal review", "advisory pitch", "investor update"],
            "mood": ["professional", "modern", "calm", "trustworthy"],
            "tone": ["clean", "considered", "polished", "neutral"],
            "formality": "medium-high",
            "density": "medium",
            "scheme": "light",
            "content_shapes": ["metrics", "dashboard", "bar ranking", "diagnosis", "roadmap", "action plan", "owner action"],
            "best_for": "professional business reviews, internal reviews, investor updates, and consulting deliverables",
            "avoid_for": "Contexts where the deck should feel hot, playful, or intentionally informal.",
        },
        {
            "id": "incident-control-room",
            "name": "Incident Control Room",
            "occasion": ["postmortem", "incident review", "internal review", "security review"],
            "mood": ["serious", "trustworthy", "calm", "professional"],
            "tone": ["analytical", "controlled", "structured", "neutral"],
            "formality": "high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["timeline", "root cause", "impact map", "action plan", "owner action", "risk matrix"],
            "best_for": "incident postmortems, root-cause reviews, impact timelines, and owner action plans",
            "avoid_for": "Decks that need to feel playful, casual, hot, or celebratory.",
        },
        {
            "id": "soft-editorial",
            "name": "Soft Editorial",
            "occasion": ["editorial feature", "longform brand story", "gallery or museum", "brand story"],
            "mood": ["literary", "elegant", "quiet", "warm-classical"],
            "tone": ["literary", "considered", "warm", "magazine", "narrative"],
            "formality": "high",
            "density": "low",
            "scheme": "light",
            "content_shapes": ["quote", "essay", "image story", "gallery", "full bleed image story"],
            "best_for": "literary longform stories, quiet editorial decks, and image-led brand narratives",
            "avoid_for": "Decks that need visual heat, punch, dense operational dashboards, or high-density scorecards.",
        },
        {
            "id": "neo-grid-bold",
            "name": "Neo Grid Bold",
            "occasion": ["product launch", "design review", "founder pitch", "brand deck", "conference talk"],
            "mood": ["confident", "punchy", "editorial", "modern", "playful"],
            "tone": ["bold", "minimal", "design-led", "graphic"],
            "formality": "medium",
            "density": "high",
            "scheme": "light",
            "content_shapes": ["stats", "comparisons", "process", "launch narrative", "campaign"],
            "best_for": "confident editorial-graphic product launches, brand decks, and founder talks",
            "avoid_for": "Contexts that need to feel quiet, traditional, serious, formal, executive, or board-ready.",
        },
        {
            "id": "finance-investor-pitch",
            "name": "Finance Investor Pitch",
            "occasion": ["founder pitch", "investor update", "fundraising", "advisory pitch"],
            "mood": ["confident", "professional", "sharp"],
            "tone": ["crisp", "analytical", "polished", "clean"],
            "formality": "medium-high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["market sizing", "traction", "unit economics", "problem solution", "growth curve", "business model"],
            "best_for": "fundraising narratives, investor updates, traction proof, and market sizing",
            "avoid_for": "Academic posters, compliance memos, or purely literary stories.",
        },
        {
            "id": "research-poster-system",
            "name": "Research Poster System",
            "occasion": ["research poster", "academic conference"],
            "mood": ["scholarly", "serious", "professional"],
            "tone": ["structured", "analytical", "clear"],
            "formality": "high",
            "density": "high",
            "scheme": "light",
            "content_shapes": ["research poster", "method", "findings", "references", "affiliation", "two column layout"],
            "best_for": "paper posters, scientific methods, findings, references, and affiliation blocks",
            "avoid_for": "Streetwear launches, playful brand campaigns, or informal workshops.",
        },
        {
            "id": "workshop-playbook",
            "name": "Workshop Playbook",
            "occasion": ["workshop", "onboarding", "training"],
            "mood": ["approachable", "warm", "practical"],
            "tone": ["instructional", "structured", "clear"],
            "formality": "medium",
            "density": "medium",
            "scheme": "light",
            "content_shapes": ["agenda", "checklist", "steps", "exercise", "playbook", "process"],
            "best_for": "training decks, onboarding flows, agendas, exercises, and workshop handbooks",
            "avoid_for": "Board updates, regulatory reports, or investor fundraises.",
        },
        {
            "id": "strategy-roadmap",
            "name": "Strategy Roadmap",
            "occasion": ["strategy offsite", "operating review", "internal review"],
            "mood": ["focused", "professional", "calm"],
            "tone": ["pragmatic", "structured", "analytical", "clean"],
            "formality": "medium-high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["roadmap", "quarterly priorities", "dependency map", "owner action", "milestone"],
            "best_for": "strategy offsites, quarterly priorities, dependency maps, and owner-driven roadmaps",
            "avoid_for": "Playful launch campaigns or low-density editorial essays.",
        },
        {
            "id": "comparison-matrix",
            "name": "Comparison Matrix",
            "occasion": ["competitive analysis", "consulting deliverable", "business review"],
            "mood": ["sharp", "professional", "confident"],
            "tone": ["comparative", "analytical", "structured"],
            "formality": "medium-high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["comparison matrix", "feature matrix", "positioning", "versus", "table"],
            "best_for": "competitive analysis, feature matrices, market positioning, and versus pages",
            "avoid_for": "Literary image stories or academic method posters.",
        },
        {
            "id": "data-dashboard-dark",
            "name": "Data Dashboard Dark",
            "occasion": ["business review", "operating review", "internal review"],
            "mood": ["technical", "focused", "professional"],
            "tone": ["analytical", "controlled", "structured"],
            "formality": "medium-high",
            "density": "high",
            "scheme": "dark",
            "content_shapes": ["dashboard", "metrics", "scorecard", "trend", "funnel", "bar ranking", "kpi"],
            "best_for": "dark high-density KPI dashboards, funnel conversion, trends, and metric scorecards",
            "avoid_for": "Quiet literary narratives, low-density galleries, or warm classical brand stories.",
        },
        {
            "id": "executive-dashboard",
            "name": "Executive Dashboard",
            "occasion": ["operating review", "business review", "internal review", "audit committee"],
            "mood": ["focused", "professional", "serious", "trustworthy"],
            "tone": ["controlled", "analytical", "structured", "clean"],
            "formality": "high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["dashboard", "executive scorecard", "scorecard", "metrics", "trend", "bar ranking", "action plan"],
            "best_for": "executive dashboards, board-ready scorecards, operating reviews, and management KPI briefings",
            "avoid_for": "Playful, retro, streetwear, casual, or hot launch campaigns.",
        },
        {
            "id": "dense-panel-grid",
            "name": "Dense Panel Grid",
            "occasion": ["business review", "operating review", "internal review"],
            "mood": ["technical", "focused", "professional"],
            "tone": ["structured", "analytical", "clean"],
            "formality": "medium-high",
            "density": "high",
            "scheme": "light",
            "content_shapes": ["dense grid", "panel grid", "metrics", "trend", "table", "dashboard", "diagnosis"],
            "best_for": "dense panel grids, information-dense operational dashboards, metric tables, and trend panels",
            "avoid_for": "Low-density editorial essays, quiet galleries, or warm classical story decks.",
        },
        {
            "id": "dark-editorial",
            "name": "Dark Editorial",
            "occasion": ["editorial feature", "longform brand story", "brand story"],
            "mood": ["dramatic", "elegant", "literary", "quiet"],
            "tone": ["magazine", "narrative", "literary", "considered"],
            "formality": "high",
            "density": "low",
            "scheme": "dark",
            "content_shapes": ["quote", "essay", "image story", "full bleed image story"],
            "best_for": "dark editorial stories, cinematic brand essays, image-led narratives, and quote-led magazine pages",
            "avoid_for": "Dense operational dashboards, compliance memos, KPI scorecards, or formal board updates.",
        },
        {
            "id": "playful-retro",
            "name": "Playful Retro",
            "occasion": ["brand deck", "product launch", "campaign"],
            "mood": ["playful", "nostalgic", "punchy", "warm"],
            "tone": ["retro", "graphic", "bold", "design-led"],
            "formality": "medium",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["campaign", "launch narrative", "stats", "process"],
            "best_for": "playful retro launches, arcade-inspired campaigns, Y2K product stories, and pixel-flavored brand decks",
            "avoid_for": "Quiet formal executive, board, regulatory, audit, or serious compliance contexts.",
        },
        {
            "id": "timeline-narrative",
            "name": "Timeline Narrative",
            "occasion": ["retrospective", "product history", "brand story"],
            "mood": ["reflective", "calm", "professional"],
            "tone": ["structured", "narrative", "considered"],
            "formality": "medium-high",
            "density": "medium",
            "scheme": "light",
            "content_shapes": ["timeline", "milestone", "phase", "story arc"],
            "best_for": "product histories, milestone retrospectives, phase narratives, and evolution stories",
            "avoid_for": "High-density dashboards or aggressive streetwear launches.",
        },
        {
            "id": "compliance-memo",
            "name": "Compliance Memo",
            "occasion": ["security review", "regulatory update", "internal review", "audit committee"],
            "mood": ["serious", "trustworthy", "professional"],
            "tone": ["controlled", "analytical", "clean"],
            "formality": "high",
            "density": "medium-high",
            "scheme": "light",
            "content_shapes": ["risk matrix", "controls", "remediation", "action plan", "audit findings"],
            "best_for": "security reviews, compliance updates, audit controls, and remediation plans",
            "avoid_for": "Youthful, playful, casual, hot, or streetwear launch decks.",
        },
    ]


@dataclass(frozen=True)
class SemanticCase:
    case_id: str
    category: str
    capability: str
    prompt: str
    expected_top: str
    expected_signals: dict[str, tuple[str, ...] | str]
    rejected: dict[str, tuple[str, ...]]
    expected_rank_prefix: tuple[str, ...] = ()
    rewrite_prompt: str | None = None
    baseline_prompt: str | None = None
    expected_baseline_top: str | None = None


POSITIVE_CASES: tuple[SemanticCase, ...] = (
    SemanticCase(
        "internal_review_unknown_topic",
        "positive",
        "Unknown business topic decomposes into review, metrics, ranking, and action-plan signals.",
        "我要一份霍洛图生态渠道健康度复盘，包含指标、瓶颈排序和下季度行动",
        "blue-professional",
        {"occasion": ("internal review",), "content_shape": ("dashboard", "bar ranking", "action plan")},
        {"soft-editorial": ("missing_content_shape_match", "style_mismatch:density")},
    ),
    SemanticCase(
        "incident_postmortem",
        "positive",
        "Incident terms route to timeline, root-cause, and owner-action assets.",
        "我要一份 AI Agent 事故复盘，包含影响范围、根因、时间线和 owner action",
        "incident-control-room",
        {"occasion": ("postmortem",), "content_shape": ("timeline", "root cause", "action plan")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "brand_launch",
        "positive",
        "Streetwear launch and punchy visual direction select the bold launch asset.",
        "我要一份街头潮流品牌发布会 deck，要有冲击力和发布叙事",
        "neo-grid-bold",
        {"occasion": ("product launch", "brand deck"), "tone": ("bold", "graphic"), "density": "high"},
        {"blue-professional": ("avoid_for:playful_or_informal", "avoid_penalty")},
    ),
    SemanticCase(
        "investor_pitch",
        "positive",
        "Fundraising language maps to market sizing, traction, and unit economics.",
        "准备一份 AI infra 创业公司融资路演，讲市场规模、traction 和 unit economics",
        "finance-investor-pitch",
        {"occasion": ("founder pitch", "investor update"), "content_shape": ("market sizing", "traction", "unit economics")},
        {"research-poster-system": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "research_poster",
        "positive",
        "Academic poster requests select method, findings, references, and affiliation layout.",
        "做一张多模态检索论文的学术 poster，包含实验方法、findings、references 和 affiliation",
        "research-poster-system",
        {"occasion": ("research poster", "academic conference"), "content_shape": ("method", "findings", "references")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "workshop_playbook",
        "positive",
        "Training and onboarding terms select agenda, checklist, step, and exercise assets.",
        "我要新人 onboarding 培训 workshop 手册，包含 agenda、步骤、练习和 checklist",
        "workshop-playbook",
        {"occasion": ("workshop", "onboarding"), "content_shape": ("agenda", "checklist", "steps")},
        {"finance-investor-pitch": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "strategy_roadmap",
        "positive",
        "Strategy prompts select roadmap, quarterly priorities, dependencies, and owners.",
        "下季度 OKR 战略路线图，列优先级、依赖关系和 owner action",
        "strategy-roadmap",
        {"occasion": ("strategy offsite",), "content_shape": ("roadmap", "quarterly priorities", "dependency map")},
        {"soft-editorial": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "competitive_matrix",
        "positive",
        "Competitive prompts select comparison matrix and positioning assets.",
        "做一份竞品对比 battlecard，用 feature matrix 讲差异和定位",
        "comparison-matrix",
        {"occasion": ("competitive analysis",), "content_shape": ("comparison matrix", "feature matrix", "positioning")},
        {"research-poster-system": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dark_dashboard",
        "positive",
        "Dark dashboard style selects dense KPI scorecard assets instead of light review defaults.",
        "暗色增长 KPI 看板，展示漏斗转化、趋势、分布和高密度 scorecard",
        "data-dashboard-dark",
        {"scheme": "dark", "density": "high", "content_shape": ("dashboard", "scorecard", "funnel")},
        {"soft-editorial": ("avoid_for:dense_or_operational", "style_mismatch:scheme")},
    ),
    SemanticCase(
        "editorial_story",
        "positive",
        "Narrative and longform story terms select a low-density editorial asset.",
        "做一个品牌故事 longform editorial 图文叙事，偏人物访谈和 quote",
        "soft-editorial",
        {"occasion": ("editorial feature", "brand story"), "density": "low", "content_shape": ("image story", "quote")},
        {"data-dashboard-dark": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "timeline_history",
        "positive",
        "Product evolution requests select timeline and milestone narrative assets.",
        "讲产品十年演进历程，用时间线、里程碑和阶段故事串起来",
        "timeline-narrative",
        {"occasion": ("retrospective", "product history"), "content_shape": ("timeline", "milestone", "phase")},
        {"workshop-playbook": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "compliance_memo",
        "positive",
        "Risk and audit language selects compliance, control, and remediation assets.",
        "安全合规审计汇报，包含风险矩阵、controls、remediation 和 action plan",
        "compliance-memo",
        {"occasion": ("security review",), "content_shape": ("risk matrix", "controls", "remediation")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "executive_dashboard_scorecard",
        "positive",
        "Executive dashboard language selects the board-ready KPI scorecard asset.",
        "管理层看板 executive dashboard：QBR scorecard 展示收入、留存趋势、核心 KPI 和 action plan，克制正式",
        "executive-dashboard",
        {"occasion": ("operating review", "business review"), "formality": "high", "content_shape": ("dashboard", "scorecard", "trend")},
        {"playful-retro": ("avoid_for:quiet_or_formal", "avoid_penalty")},
    ),
    SemanticCase(
        "board_kpi_briefing",
        "positive",
        "Board dashboard prompts select a controlled executive briefing asset.",
        "董事会看板：经营驾驶舱、核心指标、趋势 scorecard 和管理层 action plan",
        "executive-dashboard",
        {"occasion": ("operating review", "internal review"), "mood": ("focused", "professional"), "tone": ("controlled", "structured")},
        {"neo-grid-bold": ("avoid_for:quiet_or_formal", "avoid_penalty")},
    ),
    SemanticCase(
        "dense_panel_grid",
        "positive",
        "Dense grid requests select panel-grid layouts instead of generic dashboards.",
        "高密度 dense panel grid，用密集网格同时放指标、趋势、小表格和诊断",
        "dense-panel-grid",
        {"density": "high", "content_shape": ("dense grid", "panel grid", "table")},
        {"soft-editorial": ("avoid_for:dense_or_operational", "style_mismatch:density")},
    ),
    SemanticCase(
        "ops_information_grid",
        "positive",
        "Operational information grids select dense panel assets.",
        "运营信息网格：网格看板里放 metrics、趋势、table 和瓶颈诊断",
        "dense-panel-grid",
        {"density": "high", "content_shape": ("dense grid", "metrics", "table")},
        {"dark-editorial": ("avoid_for:dense_or_operational", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dark_editorial_feature",
        "positive",
        "Dark editorial signals select cinematic magazine-style story assets.",
        "黑底 dark editorial 品牌长文故事，像夜间杂志，有 quote、人物访谈和 image story",
        "dark-editorial",
        {"scheme": "dark", "occasion": ("editorial feature", "brand story"), "content_shape": ("image story", "quote")},
        {"data-dashboard-dark": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dark_magazine_quote_story",
        "positive",
        "Dark magazine rewrite selects the dark editorial template.",
        "深色叙事 deck：夜间杂志感、人物故事、essay、quote 和 full bleed image story",
        "dark-editorial",
        {"scheme": "dark", "mood": ("dramatic", "elegant"), "tone": ("magazine", "narrative")},
        {"executive-dashboard": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "playful_retro_campaign",
        "positive",
        "Retro campaign language selects playful retro over generic launch styles.",
        "复古 arcade 风品牌活动 deck，playful retro，有像素感、campaign 和 launch narrative",
        "playful-retro",
        {"occasion": ("brand deck", "product launch"), "mood": ("playful", "nostalgic"), "tone": ("retro", "graphic")},
        {"compliance-memo": ("avoid_for:playful_or_informal", "avoid_penalty")},
    ),
    SemanticCase(
        "y2k_product_launch",
        "positive",
        "Y2K launch prompts select retro launch assets.",
        "Y2K 怀旧产品 launch，像素视觉、stats、campaign 节奏，要年轻 playful",
        "playful-retro",
        {"mood": ("playful", "nostalgic"), "content_shape": ("campaign", "stats"), "density": "high"},
        {"blue-professional": ("avoid_for:playful_or_informal", "avoid_penalty")},
    ),
    SemanticCase(
        "monthly_business_review",
        "positive",
        "Routine business-review prompts stay on professional review assets.",
        "月度业务复盘：渠道指标、bar ranking、瓶颈诊断和下季度行动计划",
        "blue-professional",
        {"occasion": ("internal review", "business review"), "content_shape": ("metrics", "bar ranking", "diagnosis")},
        {"soft-editorial": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "security_incident_rca",
        "positive",
        "Security incident RCA prompts route to incident timelines and root-cause assets.",
        "安全事件 RCA postmortem，讲影响范围、root cause、timeline 和 owner action",
        "incident-control-room",
        {"occasion": ("postmortem",), "mood": ("serious", "trustworthy"), "content_shape": ("timeline", "root cause", "action plan")},
        {"playful-retro": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "series_a_investor_memo",
        "positive",
        "Series A investor memos select market, traction, and unit-economic assets.",
        "Series A investor memo：市场规模、traction、business model、unit economics 和增长曲线",
        "finance-investor-pitch",
        {"occasion": ("founder pitch", "investor update"), "content_shape": ("market sizing", "traction", "unit economics")},
        {"compliance-memo": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "paper_methods_poster",
        "positive",
        "Research poster prompts select academic methods and findings layout.",
        "Conference paper poster：method、findings、references、affiliation 和 two column layout",
        "research-poster-system",
        {"occasion": ("research poster", "academic conference"), "formality": "high", "content_shape": ("method", "findings", "references")},
        {"playful-retro": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "onboarding_exercise_agenda",
        "positive",
        "Onboarding agendas select instructional workshop assets.",
        "新人教程 onboarding workshop：agenda、checklist、steps、exercise 和演练手册",
        "workshop-playbook",
        {"occasion": ("workshop", "onboarding"), "tone": ("instructional",), "content_shape": ("agenda", "checklist", "exercise")},
        {"executive-dashboard": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "competitive_positioning_table",
        "positive",
        "Feature tables and positioning prompts select comparison matrices.",
        "竞品 versus 分析：feature matrix、table、定位、差异和 battlecard",
        "comparison-matrix",
        {"occasion": ("competitive analysis",), "tone": ("comparative",), "content_shape": ("comparison matrix", "feature matrix", "positioning")},
        {"timeline-narrative": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "roadmap_dependency_review",
        "positive",
        "Roadmap dependency prompts select strategy assets.",
        "战略 offsite roadmap：季度优先级、dependency map、里程碑和 owner action",
        "strategy-roadmap",
        {"occasion": ("strategy offsite",), "content_shape": ("roadmap", "quarterly priorities", "dependency map")},
        {"dark-editorial": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "milestone_retrospective",
        "positive",
        "Milestone retrospectives select the timeline narrative template.",
        "产品 history retrospective：timeline、milestone、phase 和 story arc",
        "timeline-narrative",
        {"occasion": ("retrospective", "product history"), "tone": ("structured", "narrative"), "content_shape": ("timeline", "milestone", "phase")},
        {"dense-panel-grid": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "audit_controls_update",
        "positive",
        "Audit-control updates select compliance memo assets.",
        "审计委员会 security review：risk matrix、controls、audit findings 和 remediation",
        "compliance-memo",
        {"occasion": ("security review",), "formality": "high", "content_shape": ("risk matrix", "controls", "remediation")},
        {"playful-retro": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dark_growth_dashboard",
        "positive",
        "Dark growth dashboards select dark data scorecard assets.",
        "dark 增长 dashboard：KPI scorecard、funnel、trend、conversion funnel 和 metrics",
        "data-dashboard-dark",
        {"scheme": "dark", "density": "high", "content_shape": ("dashboard", "scorecard", "funnel")},
        {"dense-panel-grid": ("style_mismatch:scheme",)},
    ),
)

NEGATIVE_CASES: tuple[SemanticCase, ...] = (
    SemanticCase(
        "launch_rejects_business_default",
        "negative",
        "Playful launch style must reject the sober business review default.",
        "街头潮流新品发布，年轻、热烈、冲击力强",
        "neo-grid-bold",
        {"mood": ("punchy", "playful"), "tone": ("bold", "graphic")},
        {"blue-professional": ("avoid_for:playful_or_informal", "avoid_penalty")},
    ),
    SemanticCase(
        "postmortem_rejects_launch",
        "negative",
        "Incident postmortems must not overmatch launch or brand templates.",
        "线上故障 postmortem，要讲影响范围、根因、时间线和整改 owner",
        "incident-control-room",
        {"occasion": ("postmortem",), "content_shape": ("timeline", "root cause")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "academic_rejects_editorial_story",
        "negative",
        "Academic poster structure must not be confused with a quiet editorial story.",
        "学术会议 poster，需要方法、实验 findings、references、affiliation",
        "research-poster-system",
        {"occasion": ("research poster", "academic conference"), "content_shape": ("method", "findings")},
        {"soft-editorial": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dense_dashboard_rejects_editorial",
        "negative",
        "High-density KPI dashboards must reject low-density editorial assets.",
        "高密度 dashboard scorecard，看漏斗转化趋势和核心 KPI",
        "dense-panel-grid",
        {"density": "high", "content_shape": ("dense grid", "dashboard", "scorecard", "funnel")},
        {"soft-editorial": ("avoid_for:dense_or_operational", "style_mismatch:density")},
    ),
    SemanticCase(
        "fundraise_rejects_compliance",
        "negative",
        "Investor pitches must not match governance or remediation templates.",
        "Founder pitch 给投资人，强调市场规模、traction、商业模式和 unit economics",
        "finance-investor-pitch",
        {"occasion": ("founder pitch", "investor update"), "content_shape": ("market sizing", "traction")},
        {"compliance-memo": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "compliance_rejects_launch",
        "negative",
        "Regulatory updates must reject playful launch styles.",
        "监管合规治理更新，讲 controls、风险矩阵和 remediation",
        "compliance-memo",
        {"occasion": ("regulatory update",), "content_shape": ("risk matrix", "controls")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "executive_dashboard_rejects_retro",
        "negative",
        "Board scorecards must reject playful retro campaign assets.",
        "董事会看板 executive scorecard，正式克制，展示经营指标、趋势和 action plan",
        "executive-dashboard",
        {"formality": "high", "tone": ("controlled",), "content_shape": ("dashboard", "scorecard", "trend")},
        {"playful-retro": ("avoid_for:quiet_or_formal", "avoid_penalty")},
    ),
    SemanticCase(
        "dense_grid_rejects_dark_editorial",
        "negative",
        "Dense operational grids must reject dark editorial story assets.",
        "高密度 panel grid dashboard，密集网格放 metrics、trend、table 和 scorecard",
        "dense-panel-grid",
        {"density": "high", "content_shape": ("dense grid", "panel grid", "table")},
        {"dark-editorial": ("avoid_for:dense_or_operational", "missing_content_shape_match")},
    ),
    SemanticCase(
        "dark_editorial_rejects_data_dashboard",
        "negative",
        "Dark editorial stories must not be mistaken for dark KPI dashboards.",
        "dark editorial 夜间杂志品牌故事，quote、essay、人物叙事和 image story",
        "dark-editorial",
        {"scheme": "dark", "occasion": ("editorial feature", "brand story"), "content_shape": ("image story", "quote")},
        {"data-dashboard-dark": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "retro_rejects_compliance",
        "negative",
        "Retro launches must reject serious compliance templates.",
        "复古像素 product launch，playful retro campaign，要年轻、热烈、stats 强",
        "playful-retro",
        {"mood": ("playful", "nostalgic"), "tone": ("retro", "graphic"), "content_shape": ("campaign", "stats")},
        {"compliance-memo": ("avoid_for:playful_or_informal", "avoid_penalty")},
    ),
    SemanticCase(
        "executive_dashboard_rejects_founder_pitch",
        "negative",
        "Executive KPI scorecards must not route to investor pitch assets.",
        "管理层看板 QBR：经营驾驶舱、核心 KPI、趋势 scorecard 和 owner action",
        "executive-dashboard",
        {"occasion": ("operating review", "business review"), "content_shape": ("dashboard", "scorecard", "trend")},
        {"playful-retro": ("avoid_for:quiet_or_formal", "missing_content_shape_match")},
    ),
    SemanticCase(
        "comparison_rejects_timeline",
        "negative",
        "Competitive matrices must reject timeline narrative assets.",
        "竞品 vs battlecard：feature matrix、comparison matrix、table 和 positioning",
        "comparison-matrix",
        {"occasion": ("competitive analysis",), "content_shape": ("comparison matrix", "feature matrix", "positioning")},
        {"timeline-narrative": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "timeline_rejects_dense_grid",
        "negative",
        "Timeline narratives must reject dense operational grid layouts.",
        "产品演进 history timeline，按 phase、milestone 和 story arc 展开",
        "timeline-narrative",
        {"occasion": ("retrospective", "product history"), "content_shape": ("timeline", "milestone", "phase")},
        {"dense-panel-grid": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "workshop_rejects_investor_pitch",
        "negative",
        "Training playbooks must not match investor pitch assets.",
        "onboarding training workshop：agenda、steps、exercise、checklist 和教程手册",
        "workshop-playbook",
        {"occasion": ("workshop", "onboarding"), "content_shape": ("agenda", "checklist", "steps")},
        {"finance-investor-pitch": ("missing_occasion_match", "missing_content_shape_match")},
    ),
    SemanticCase(
        "security_review_rejects_dark_editorial",
        "negative",
        "Security reviews must reject dark editorial story assets.",
        "security review 审计汇报：risk matrix、controls、remediation、治理和监管风险",
        "compliance-memo",
        {"occasion": ("security review", "regulatory update"), "content_shape": ("risk matrix", "controls", "remediation")},
        {"dark-editorial": ("missing_occasion_match", "missing_content_shape_match")},
    ),
)

BOUNDARY_CASES: tuple[SemanticCase, ...] = (
    SemanticCase(
        "unknown_topic_decomposition",
        "boundary",
        "Unknown nouns should not block decomposition into known business-review signals.",
        "量子供应链飞轮健康度回顾：指标、瓶颈排序、owner action",
        "blue-professional",
        {"occasion": ("internal review",), "content_shape": ("dashboard", "bar ranking", "owner action")},
        {"neo-grid-bold": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "style_override_changes_launch_ranking",
        "boundary",
        "Executive low-saturation style override must change launch ranking away from bold launch.",
        "品牌发布会 deck，但给董事会看，要克制、严肃、低饱和",
        "blue-professional",
        {"occasion": ("product launch", "brand deck", "internal review"), "mood": ("professional", "serious"), "tone": ("controlled",)},
        {"neo-grid-bold": ("avoid_for:quiet_or_formal", "avoid_penalty")},
        baseline_prompt="品牌发布会 deck，潮流街头，要视觉冲击力",
        expected_baseline_top="neo-grid-bold",
    ),
    SemanticCase(
        "business_review_synonym_rewrite",
        "boundary",
        "Chinese and English business-review rewrites keep the same selected template.",
        "经营复盘：渠道指标、瓶颈诊断、下季度行动",
        "blue-professional",
        {"occasion": ("internal review", "business review"), "content_shape": ("metrics", "diagnosis", "action plan")},
        {"soft-editorial": ("missing_content_shape_match",)},
        rewrite_prompt="Quarterly operating review for channel KPIs, bottleneck diagnosis, and next-quarter actions",
    ),
    SemanticCase(
        "research_poster_synonym_rewrite",
        "boundary",
        "Chinese and English academic-poster rewrites keep the same selected template.",
        "论文海报：方法、实验结果、引用和机构署名",
        "research-poster-system",
        {"occasion": ("research poster",), "content_shape": ("method", "references", "affiliation")},
        {"workshop-playbook": ("missing_occasion_match", "missing_content_shape_match")},
        rewrite_prompt="Academic conference poster with methods, findings, references, and affiliation blocks",
    ),
    SemanticCase(
        "unknown_competitor_topic",
        "boundary",
        "Unknown product nouns plus comparison wording should route to matrix assets.",
        "火星配送平台竞品差异矩阵，讲 feature matrix、定位和 vs",
        "comparison-matrix",
        {"occasion": ("competitive analysis",), "content_shape": ("comparison matrix", "feature matrix", "positioning")},
        {"soft-editorial": ("missing_content_shape_match",)},
    ),
    SemanticCase(
        "timeline_rewrite_stability",
        "boundary",
        "Timeline, milestone, and evolution synonyms should stay on the narrative timeline asset.",
        "产品演进时间线：阶段、里程碑和故事弧线",
        "timeline-narrative",
        {"occasion": ("retrospective", "product history"), "content_shape": ("timeline", "milestone", "phase")},
        {"data-dashboard-dark": ("missing_content_shape_match",)},
        rewrite_prompt="Product history timeline with phases, milestones, and a narrative story arc",
    ),
    SemanticCase(
        "dark_editorial_style_override",
        "boundary",
        "Adding a dark magazine style changes a generic editorial story to dark editorial.",
        "品牌故事 editorial，但做成黑底杂志和 cinematic editorial，有 quote 与 image story",
        "dark-editorial",
        {"scheme": "dark", "occasion": ("editorial feature", "brand story"), "tone": ("magazine", "narrative")},
        {"soft-editorial": ("style_mismatch:scheme",)},
        baseline_prompt="品牌故事 longform editorial，有人物访谈、quote 和 image story",
        expected_baseline_top="soft-editorial",
    ),
    SemanticCase(
        "dark_dashboard_style_override",
        "boundary",
        "Dark style override moves high-density dashboards from light dense grids to dark dashboards.",
        "暗色高密度 dashboard，用 scorecard、trend、funnel 和 KPI 展示增长健康度",
        "data-dashboard-dark",
        {"scheme": "dark", "density": "high", "content_shape": ("dashboard", "scorecard", "funnel")},
        {"dense-panel-grid": ("style_mismatch:scheme",)},
        baseline_prompt="高密度 panel grid dashboard，用 scorecard、trend、table 和 KPI 展示增长健康度",
        expected_baseline_top="dense-panel-grid",
    ),
    SemanticCase(
        "executive_override_for_retro_launch",
        "boundary",
        "Executive style and scorecard content override playful launch styling.",
        "复古 campaign launch 但给董事会看，要正式克制，用 KPI scorecard 和 action plan",
        "executive-dashboard",
        {"occasion": ("product launch", "brand deck", "internal review"), "formality": "high", "content_shape": ("dashboard", "scorecard", "action plan")},
        {"playful-retro": ("avoid_for:quiet_or_formal", "avoid_penalty")},
        baseline_prompt="复古 campaign launch，像素 arcade，年轻 playful，强调 stats",
        expected_baseline_top="playful-retro",
    ),
    SemanticCase(
        "retro_synonym_rewrite",
        "boundary",
        "Chinese and English retro campaign rewrites keep the playful retro asset.",
        "Y2K 复古品牌 campaign：像素视觉、launch narrative 和 stats",
        "playful-retro",
        {"mood": ("playful", "nostalgic"), "tone": ("retro", "graphic"), "content_shape": ("campaign", "launch narrative")},
        {"compliance-memo": ("avoid_for:playful_or_informal", "avoid_penalty")},
        rewrite_prompt="Playful retro arcade brand deck with pixel visuals, campaign stats, and launch narrative",
    ),
    SemanticCase(
        "dense_grid_synonym_rewrite",
        "boundary",
        "Dense grid and information-grid rewrites keep the dense panel asset.",
        "密集信息网格：指标、趋势、小表格、诊断和 panel grid",
        "dense-panel-grid",
        {"density": "high", "content_shape": ("dense grid", "panel grid", "table")},
        {"soft-editorial": ("avoid_for:dense_or_operational", "style_mismatch:density")},
        rewrite_prompt="Dense panel grid for metrics, trend panels, diagnosis, and compact tables",
    ),
    SemanticCase(
        "executive_dashboard_synonym_rewrite",
        "boundary",
        "Executive dashboard synonyms keep the executive dashboard asset.",
        "高管经营驾驶舱：scorecard、核心指标、趋势和 action plan",
        "executive-dashboard",
        {"occasion": ("operating review", "business review"), "content_shape": ("dashboard", "scorecard", "trend")},
        {"playful-retro": ("avoid_for:quiet_or_formal", "avoid_penalty")},
        rewrite_prompt="Executive scorecard for board operating review with KPI trends and management action plan",
    ),
    SemanticCase(
        "security_review_synonym_rewrite",
        "boundary",
        "Security, audit, controls, and remediation rewrites stay on compliance assets.",
        "治理审计更新：controls、风险矩阵、整改 remediation 和监管风险",
        "compliance-memo",
        {"occasion": ("security review", "regulatory update"), "content_shape": ("risk matrix", "controls", "remediation")},
        {"neo-grid-bold": ("missing_occasion_match", "missing_content_shape_match")},
        rewrite_prompt="Security review for audit controls, risk matrix, regulatory exposure, and remediation plan",
    ),
    SemanticCase(
        "founder_pitch_synonym_rewrite",
        "boundary",
        "Founder pitch and investor memo rewrites keep finance pitch assets.",
        "融资路演：市场规模、商业模式、traction 和 unit economics",
        "finance-investor-pitch",
        {"occasion": ("founder pitch", "investor update"), "content_shape": ("market sizing", "traction", "unit economics")},
        {"research-poster-system": ("missing_content_shape_match",)},
        rewrite_prompt="Series A investor memo covering market sizing, traction, business model, and unit economics",
    ),
    SemanticCase(
        "workshop_synonym_rewrite",
        "boundary",
        "Workshop and training rewrites keep instructional playbook assets.",
        "新人培训手册：agenda、steps、exercise、checklist 和演练",
        "workshop-playbook",
        {"occasion": ("workshop", "onboarding"), "tone": ("instructional",), "content_shape": ("agenda", "checklist", "steps")},
        {"finance-investor-pitch": ("missing_occasion_match", "missing_content_shape_match")},
        rewrite_prompt="Onboarding training workshop playbook with agenda, steps, checklist, and exercises",
    ),
)


ALL_CASES = POSITIVE_CASES + NEGATIVE_CASES + BOUNDARY_CASES


def clone_case(base: SemanticCase, suffix: str, prompt_prefix: str) -> SemanticCase:
    return SemanticCase(
        case_id=f"{base.case_id}_{suffix}",
        category=base.category,
        capability=f"{base.capability} Variant topic: {prompt_prefix}",
        prompt=f"{prompt_prefix}：{base.prompt}",
        expected_top=base.expected_top,
        expected_signals=base.expected_signals,
        rejected=base.rejected,
        expected_rank_prefix=base.expected_rank_prefix,
        rewrite_prompt=base.rewrite_prompt,
        baseline_prompt=base.baseline_prompt,
        expected_baseline_top=base.expected_baseline_top,
    )


CASE_BY_ID = {case.case_id: case for case in ALL_CASES}


def generated_variants(base_ids: tuple[str, ...], topics: tuple[str, ...]) -> tuple[SemanticCase, ...]:
    return tuple(
        clone_case(CASE_BY_ID[base_id], f"variant_{topic_index + 1}", topic)
        for base_id in base_ids
        for topic_index, topic in enumerate(topics)
    )


POSITIVE_VARIANT_CASES = generated_variants(
    (
        "internal_review_unknown_topic",
        "incident_postmortem",
        "brand_launch",
        "investor_pitch",
        "research_poster",
        "workshop_playbook",
        "strategy_roadmap",
        "competitive_matrix",
        "dark_dashboard",
        "editorial_story",
        "executive_dashboard_scorecard",
    ),
    ("零售增长", "AI 搜索", "跨境支付", "云端协作", "客户成功"),
)

NEGATIVE_VARIANT_CASES = generated_variants(
    (
        "launch_rejects_business_default",
        "postmortem_rejects_launch",
        "academic_rejects_editorial_story",
        "dense_dashboard_rejects_editorial",
        "compliance_rejects_launch",
    ),
    ("医疗 SaaS", "金融风控", "教育增长", "企业平台", "内容社区"),
)

BOUNDARY_VARIANT_CASES = generated_variants(
    (
        "unknown_topic_decomposition",
        "style_override_changes_launch_ranking",
        "dark_editorial_style_override",
        "executive_override_for_retro_launch",
    ),
    ("火星物流", "量子供应链", "无人门店", "低空经济", "智能客服"),
)


ALL_CASES = ALL_CASES + POSITIVE_VARIANT_CASES + NEGATIVE_VARIANT_CASES + BOUNDARY_VARIANT_CASES


def validate_case_catalog() -> None:
    counts = {category: len([case for case in ALL_CASES if case.category == category]) for category in ("positive", "negative", "boundary")}
    assert counts == {"positive": 85, "negative": 40, "boundary": 35}, counts
    assert len(ALL_CASES) == 160, len(ALL_CASES)
    assert len([case for case in ALL_CASES if case.category in {"positive", "boundary"}]) >= 120
    positive_top_ids = {case.expected_top for case in POSITIVE_CASES}
    assert len(positive_top_ids) >= 14, positive_top_ids
    all_top_ids = {case.expected_top for case in ALL_CASES}
    assert len(all_top_ids) >= 14, all_top_ids
    for case in ALL_CASES:
        assert case.capability
        assert case.expected_signals
        assert case.rejected


validate_case_catalog()


class SVGlideSemanticAssetMatcherTest(unittest.TestCase):
    maxDiff = None

    def assert_signal(self, signals: dict[str, Any], field: str, expected: tuple[str, ...] | str) -> None:
        self.assertIn(field, signals)
        actual = signals[field]
        if isinstance(expected, tuple):
            self.assertIsInstance(actual, list)
            for value in expected:
                self.assertIn(value, actual)
        else:
            self.assertEqual(expected, actual)

    def assert_rejection_reasons(self, result: dict[str, Any], expected: dict[str, tuple[str, ...]]) -> None:
        rejection_reasons = result["candidate_rejection_reasons"]
        for candidate_id, reason_parts in expected.items():
            self.assertIn(candidate_id, rejection_reasons)
            reasons = rejection_reasons[candidate_id]
            self.assertTrue(reasons, candidate_id)
            for reason_part in reason_parts:
                self.assertTrue(
                    any(reason_part in reason for reason in reasons),
                    f"{candidate_id} reasons {reasons!r} did not contain {reason_part!r}",
                )

    def assert_semantic_case(self, case: SemanticCase) -> None:
        result = matcher.rank_assets(case.prompt, fixture_assets())

        self.assertIn("brief_signals", result)
        self.assertIn("selected_template_id", result)
        self.assertIn("candidate_templates_considered", result)
        self.assertIn("candidate_rejection_reasons", result)
        self.assertIn("candidates", result)
        self.assertGreaterEqual(len(result["candidate_templates_considered"]), 3)

        self.assertEqual(case.expected_top, result["selected_template_id"])
        self.assertEqual(case.expected_top, result["candidates"][0]["id"])
        self.assertEqual(case.expected_top, result["candidate_templates_considered"][0])
        self.assertEqual(
            [candidate["id"] for candidate in result["candidates"]],
            result["candidate_templates_considered"][: len(result["candidates"])],
        )
        self.assertGreater(int(result["candidates"][0]["score"]), int(result["candidates"][1]["score"]))

        for field, expected in case.expected_signals.items():
            self.assert_signal(result["brief_signals"], field, expected)
        self.assert_rejection_reasons(result, case.rejected)

        if case.expected_rank_prefix:
            self.assertEqual(list(case.expected_rank_prefix), result["candidate_templates_considered"][: len(case.expected_rank_prefix)])

        if case.rewrite_prompt:
            rewritten = matcher.rank_assets(case.rewrite_prompt, fixture_assets())
            self.assertEqual(case.expected_top, rewritten["selected_template_id"])
            self.assertEqual(case.expected_top, rewritten["candidate_templates_considered"][0])
            self.assertIn("brief_signals", rewritten)
            self.assertIn("candidate_templates_considered", rewritten)
            self.assertIn("candidate_rejection_reasons", rewritten)

        if case.baseline_prompt:
            baseline = matcher.rank_assets(case.baseline_prompt, fixture_assets())
            self.assertEqual(case.expected_baseline_top, baseline["selected_template_id"])
            self.assertNotEqual(baseline["selected_template_id"], result["selected_template_id"])


def make_case_test(case: SemanticCase):
    def test(self: SVGlideSemanticAssetMatcherTest) -> None:
        self.assert_semantic_case(case)

    test.__name__ = f"test_{case.category}_{case.case_id}"
    test.__doc__ = case.capability
    return test


for semantic_case in ALL_CASES:
    setattr(SVGlideSemanticAssetMatcherTest, f"test_{semantic_case.category}_{semantic_case.case_id}", make_case_test(semantic_case))


if __name__ == "__main__":
    unittest.main()
