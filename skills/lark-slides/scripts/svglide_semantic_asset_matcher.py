#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class WeightedSignal:
    field: str
    value: str
    weight: int


PROMPT_RULES: list[tuple[tuple[str, ...], list[WeightedSignal]]] = [
    (
        ("复盘", "回顾", "review"),
        [
            WeightedSignal("occasion", "internal review", 10),
            WeightedSignal("occasion", "business review", 10),
            WeightedSignal("mood", "professional", 5),
            WeightedSignal("mood", "trustworthy", 5),
            WeightedSignal("tone", "analytical", 4),
            WeightedSignal("tone", "polished", 4),
        ],
    ),
    (
        ("内部", "经营", "业务", "管理层", "business review", "operating review", "quarterly review", "qbr", "季度复盘"),
        [
            WeightedSignal("occasion", "internal review", 10),
            WeightedSignal("occasion", "quarterly review", 8),
            WeightedSignal("formality", "medium-high", 4),
            WeightedSignal("tone", "clean", 4),
            WeightedSignal("tone", "neutral", 3),
        ],
    ),
    (
        ("渠道", "健康度", "指标", "数据", "瓶颈"),
        [
            WeightedSignal("content_shape", "metrics", 8),
            WeightedSignal("content_shape", "dashboard", 8),
            WeightedSignal("content_shape", "bar ranking", 7),
            WeightedSignal("content_shape", "diagnosis", 6),
            WeightedSignal("density", "medium", 4),
            WeightedSignal("density", "medium-high", 4),
        ],
    ),
    (
        ("事故", "故障", "根因", "影响范围", "postmortem", "incident", "rca", "root cause"),
        [
            WeightedSignal("occasion", "postmortem", 10),
            WeightedSignal("occasion", "internal review", 6),
            WeightedSignal("mood", "serious", 5),
            WeightedSignal("mood", "trustworthy", 4),
            WeightedSignal("tone", "analytical", 4),
            WeightedSignal("tone", "controlled", 4),
            WeightedSignal("content_shape", "timeline", 8),
            WeightedSignal("content_shape", "root cause", 8),
            WeightedSignal("content_shape", "action plan", 7),
        ],
    ),
    (
        ("行动", "owner", "路线图", "下季度", "优先级", "action plan"),
        [
            WeightedSignal("content_shape", "roadmap", 7),
            WeightedSignal("content_shape", "action plan", 7),
            WeightedSignal("content_shape", "owner action", 6),
        ],
    ),
    (
        ("发布", "品牌发布", "潮流", "街头", "launch", "campaign", "go to market", "gtm"),
        [
            WeightedSignal("occasion", "product launch", 10),
            WeightedSignal("occasion", "brand deck", 10),
            WeightedSignal("mood", "confident", 5),
            WeightedSignal("mood", "punchy", 5),
            WeightedSignal("mood", "playful", 4),
            WeightedSignal("tone", "bold", 5),
            WeightedSignal("tone", "design-led", 5),
            WeightedSignal("tone", "graphic", 4),
            WeightedSignal("density", "high", 3),
        ],
    ),
    (
        ("融资", "路演", "投资人", "founder", "pitch", "traction", "unit economics", "市场规模", "商业模式", "seed round", "series a", "investor memo"),
        [
            WeightedSignal("occasion", "founder pitch", 10),
            WeightedSignal("occasion", "investor update", 9),
            WeightedSignal("mood", "confident", 6),
            WeightedSignal("tone", "crisp", 5),
            WeightedSignal("tone", "analytical", 4),
            WeightedSignal("content_shape", "market sizing", 8),
            WeightedSignal("content_shape", "traction", 8),
            WeightedSignal("content_shape", "unit economics", 7),
            WeightedSignal("content_shape", "problem solution", 6),
            WeightedSignal("density", "medium-high", 4),
        ],
    ),
    (
        ("论文", "研究", "学术", "poster", "海报", "conference", "实验", "方法", "affiliation"),
        [
            WeightedSignal("occasion", "research poster", 10),
            WeightedSignal("occasion", "academic conference", 9),
            WeightedSignal("mood", "scholarly", 6),
            WeightedSignal("tone", "structured", 5),
            WeightedSignal("formality", "high", 5),
            WeightedSignal("density", "high", 5),
            WeightedSignal("content_shape", "research poster", 9),
            WeightedSignal("content_shape", "method", 7),
            WeightedSignal("content_shape", "findings", 7),
            WeightedSignal("content_shape", "references", 5),
            WeightedSignal("content_shape", "affiliation", 5),
        ],
    ),
    (
        ("workshop", "培训", "新人", "onboarding", "教程", "演练", "agenda", "练习", "手册"),
        [
            WeightedSignal("occasion", "workshop", 10),
            WeightedSignal("occasion", "onboarding", 9),
            WeightedSignal("mood", "approachable", 6),
            WeightedSignal("tone", "instructional", 6),
            WeightedSignal("density", "medium", 4),
            WeightedSignal("content_shape", "agenda", 7),
            WeightedSignal("content_shape", "checklist", 7),
            WeightedSignal("content_shape", "steps", 7),
            WeightedSignal("content_shape", "exercise", 6),
        ],
    ),
    (
        ("战略", "路线图", "roadmap", "里程碑", "优先级", "okr", "下季度", "依赖"),
        [
            WeightedSignal("occasion", "strategy offsite", 9),
            WeightedSignal("occasion", "operating review", 7),
            WeightedSignal("mood", "focused", 6),
            WeightedSignal("tone", "pragmatic", 6),
            WeightedSignal("density", "medium-high", 4),
            WeightedSignal("content_shape", "roadmap", 8),
            WeightedSignal("content_shape", "quarterly priorities", 8),
            WeightedSignal("content_shape", "dependency map", 7),
            WeightedSignal("content_shape", "owner action", 6),
        ],
    ),
    (
        (
            "技术架构",
            "系统架构",
            "架构方案",
            "架构图",
            "系统设计",
            "模块",
            "技术链路",
            "调用链路",
            "服务链路",
            "系统链路",
            "架构链路",
            "architecture",
            "system design",
        ),
        [
            WeightedSignal("occasion", "technical architecture", 10),
            WeightedSignal("occasion", "system design", 8),
            WeightedSignal("mood", "technical", 6),
            WeightedSignal("tone", "technical", 6),
            WeightedSignal("tone", "structured", 5),
            WeightedSignal("tone", "precise", 5),
            WeightedSignal("density", "medium-high", 4),
            WeightedSignal("content_shape", "architecture", 9),
            WeightedSignal("content_shape", "dependency map", 8),
            WeightedSignal("content_shape", "nodes", 7),
        ],
    ),
    (
        ("对比", "竞品", "versus", "vs", "feature matrix", "差异", "battlecard"),
        [
            WeightedSignal("occasion", "competitive analysis", 10),
            WeightedSignal("mood", "sharp", 5),
            WeightedSignal("tone", "analytical", 5),
            WeightedSignal("tone", "comparative", 5),
            WeightedSignal("density", "medium-high", 4),
            WeightedSignal("content_shape", "comparison matrix", 8),
            WeightedSignal("content_shape", "feature matrix", 8),
            WeightedSignal("content_shape", "positioning", 7),
            WeightedSignal("content_shape", "versus", 6),
        ],
    ),
    (
        ("时间线", "演进", "历程", "history", "milestone", "timeline", "阶段"),
        [
            WeightedSignal("occasion", "retrospective", 8),
            WeightedSignal("occasion", "product history", 8),
            WeightedSignal("mood", "reflective", 5),
            WeightedSignal("tone", "structured", 5),
            WeightedSignal("tone", "narrative", 4),
            WeightedSignal("content_shape", "timeline", 8),
            WeightedSignal("content_shape", "milestone", 8),
            WeightedSignal("content_shape", "phase", 6),
            WeightedSignal("content_shape", "story arc", 5),
        ],
    ),
    (
        ("故事", "叙事", "人物", "访谈", "品牌故事", "magazine", "editorial", "longform", "图文"),
        [
            WeightedSignal("occasion", "editorial feature", 10),
            WeightedSignal("occasion", "brand story", 8),
            WeightedSignal("mood", "literary", 6),
            WeightedSignal("mood", "elegant", 5),
            WeightedSignal("tone", "magazine", 6),
            WeightedSignal("tone", "narrative", 5),
            WeightedSignal("density", "low", 4),
            WeightedSignal("content_shape", "image story", 7),
            WeightedSignal("content_shape", "essay", 7),
            WeightedSignal("content_shape", "quote", 5),
        ],
    ),
    (
        ("图文报告", "大图", "图片", "配图", "image report", "image feature", "case study", "客户案例"),
        [
            WeightedSignal("occasion", "image story", 10),
            WeightedSignal("occasion", "case study", 8),
            WeightedSignal("occasion", "brand story", 6),
            WeightedSignal("mood", "polished", 5),
            WeightedSignal("tone", "narrative", 5),
            WeightedSignal("content_shape", "image story", 9),
            WeightedSignal("content_shape", "evidence cards", 7),
        ],
    ),
    (
        ("市场格局", "市场分析", "玩家分层", "机会空间", "market landscape", "market map", "landscape"),
        [
            WeightedSignal("occasion", "market analysis", 10),
            WeightedSignal("mood", "focused", 5),
            WeightedSignal("tone", "analytical", 6),
            WeightedSignal("density", "medium-high", 4),
            WeightedSignal("content_shape", "market map", 9),
            WeightedSignal("content_shape", "trend", 8),
            WeightedSignal("content_shape", "bar ranking", 7),
            WeightedSignal("content_shape", "dense grid", 5),
        ],
    ),
    (
        ("最后一页", "总结页", "年度总结", "三个结论", "下一步行动", "closing", "takeaways", "wrap up"),
        [
            WeightedSignal("occasion", "summary", 10),
            WeightedSignal("occasion", "decision review", 7),
            WeightedSignal("tone", "conclusive", 8),
            WeightedSignal("tone", "clear", 6),
            WeightedSignal("tone", "controlled", 4),
            WeightedSignal("content_shape", "takeaways", 9),
            WeightedSignal("content_shape", "action plan", 5),
        ],
    ),
    (
        ("executive dashboard", "executive scorecard", "高管看板", "管理层看板", "董事会看板", "经营驾驶舱", "管理驾驶舱"),
        [
            WeightedSignal("occasion", "operating review", 10),
            WeightedSignal("occasion", "business review", 9),
            WeightedSignal("occasion", "internal review", 8),
            WeightedSignal("mood", "focused", 6),
            WeightedSignal("mood", "professional", 5),
            WeightedSignal("mood", "serious", 4),
            WeightedSignal("tone", "controlled", 6),
            WeightedSignal("tone", "analytical", 5),
            WeightedSignal("tone", "structured", 5),
            WeightedSignal("formality", "high", 6),
            WeightedSignal("density", "medium-high", 5),
            WeightedSignal("content_shape", "dashboard", 8),
            WeightedSignal("content_shape", "executive scorecard", 9),
            WeightedSignal("content_shape", "scorecard", 8),
            WeightedSignal("content_shape", "metrics", 7),
            WeightedSignal("content_shape", "trend", 6),
        ],
    ),
    (
        ("dense grid", "dense panel", "panel grid", "密集网格", "信息网格", "表格网格", "网格看板", "高密度", "密集"),
        [
            WeightedSignal("mood", "technical", 5),
            WeightedSignal("mood", "focused", 4),
            WeightedSignal("tone", "structured", 6),
            WeightedSignal("tone", "analytical", 5),
            WeightedSignal("density", "high", 7),
            WeightedSignal("content_shape", "dense grid", 9),
            WeightedSignal("content_shape", "panel grid", 8),
            WeightedSignal("content_shape", "metrics", 7),
            WeightedSignal("content_shape", "trend", 6),
            WeightedSignal("content_shape", "table", 5),
        ],
    ),
    (
        ("dashboard", "看板", "scorecard", "kpi", "漏斗", "转化", "趋势", "分布", "health score"),
        [
            WeightedSignal("content_shape", "dashboard", 9),
            WeightedSignal("content_shape", "metrics", 8),
            WeightedSignal("content_shape", "scorecard", 8),
            WeightedSignal("content_shape", "trend", 7),
            WeightedSignal("content_shape", "funnel", 6),
            WeightedSignal("density", "high", 5),
            WeightedSignal("tone", "analytical", 4),
        ],
    ),
    (
        ("安全", "合规", "审计", "风险", "治理", "controls", "remediation", "监管"),
        [
            WeightedSignal("occasion", "security review", 10),
            WeightedSignal("occasion", "regulatory update", 8),
            WeightedSignal("mood", "serious", 6),
            WeightedSignal("mood", "trustworthy", 5),
            WeightedSignal("tone", "controlled", 6),
            WeightedSignal("formality", "high", 5),
            WeightedSignal("content_shape", "risk matrix", 8),
            WeightedSignal("content_shape", "controls", 7),
            WeightedSignal("content_shape", "remediation", 7),
            WeightedSignal("content_shape", "action plan", 5),
        ],
    ),
    (
        ("dark editorial", "黑底杂志", "暗黑编辑", "深色叙事", "夜间杂志", "cinematic editorial", "dark magazine"),
        [
            WeightedSignal("occasion", "editorial feature", 10),
            WeightedSignal("occasion", "brand story", 8),
            WeightedSignal("mood", "dramatic", 6),
            WeightedSignal("mood", "elegant", 5),
            WeightedSignal("mood", "literary", 4),
            WeightedSignal("tone", "magazine", 6),
            WeightedSignal("tone", "narrative", 5),
            WeightedSignal("scheme", "dark", 6),
            WeightedSignal("density", "low", 4),
            WeightedSignal("content_shape", "image story", 7),
            WeightedSignal("content_shape", "quote", 6),
            WeightedSignal("content_shape", "essay", 5),
        ],
    ),
    (
        ("复古", "怀旧", "retro", "arcade", "pixel", "像素", "y2k", "playful retro"),
        [
            WeightedSignal("occasion", "brand deck", 8),
            WeightedSignal("occasion", "product launch", 6),
            WeightedSignal("mood", "playful", 7),
            WeightedSignal("mood", "nostalgic", 6),
            WeightedSignal("mood", "punchy", 5),
            WeightedSignal("tone", "retro", 8),
            WeightedSignal("tone", "graphic", 6),
            WeightedSignal("tone", "bold", 5),
            WeightedSignal("density", "medium-high", 4),
            WeightedSignal("content_shape", "campaign", 7),
            WeightedSignal("content_shape", "launch narrative", 6),
            WeightedSignal("content_shape", "stats", 5),
        ],
    ),
    (
        ("暗色", "深色", "dark", "night"),
        [
            WeightedSignal("scheme", "dark", 6),
        ],
    ),
    (
        ("明亮", "浅色", "light"),
        [
            WeightedSignal("scheme", "light", 5),
        ],
    ),
    (
        ("克制", "低饱和", "严肃", "董事会", "管理层", "formal", "executive", "board"),
        [
            WeightedSignal("occasion", "internal review", 12),
            WeightedSignal("mood", "professional", 12),
            WeightedSignal("mood", "trustworthy", 10),
            WeightedSignal("mood", "serious", 10),
            WeightedSignal("tone", "controlled", 12),
            WeightedSignal("tone", "clean", 10),
            WeightedSignal("formality", "high", 10),
            WeightedSignal("density", "medium", 8),
        ],
    ),
    (
        ("冲击力", "视觉冲击", "热烈", "年轻", "赛博", "潮流", "街头", "bold", "vivid"),
        [
            WeightedSignal("mood", "punchy", 8),
            WeightedSignal("mood", "playful", 6),
            WeightedSignal("tone", "bold", 8),
            WeightedSignal("tone", "graphic", 7),
            WeightedSignal("tone", "design-led", 6),
            WeightedSignal("density", "high", 5),
        ],
    ),
]

FIELD_ALIASES: dict[str, dict[str, set[str]]] = {
    "occasion": {
        "internal review": {"internal review", "business review", "quarterly review", "operating review", "consulting deliverable"},
        "business review": {"business review", "internal review", "consulting deliverable", "investor update"},
        "quarterly review": {"quarterly review", "business review", "internal review", "operating review"},
        "postmortem": {"postmortem", "internal review", "incident review", "operating review"},
        "product launch": {"product launch", "brand deck", "conference talk"},
        "brand deck": {"brand deck", "product launch", "design review"},
        "founder pitch": {"founder pitch", "investor update", "conference talk"},
        "investor update": {"investor update", "founder pitch", "business review"},
        "research poster": {"research poster", "academic conference"},
        "academic conference": {"academic conference", "research poster"},
        "workshop": {"workshop", "onboarding", "training"},
        "onboarding": {"onboarding", "workshop", "training"},
        "strategy offsite": {"strategy offsite", "operating review", "internal review"},
        "operating review": {"operating review", "business review", "internal review", "strategy offsite"},
        "competitive analysis": {"competitive analysis", "consulting deliverable", "business review"},
        "retrospective": {"retrospective", "product history"},
        "product history": {"product history", "retrospective", "brand story"},
        "editorial feature": {"editorial feature", "longform brand story", "gallery or museum"},
        "brand story": {"brand story", "editorial feature", "longform brand story", "brand deck"},
        "security review": {"security review", "regulatory update", "internal review", "postmortem"},
        "regulatory update": {"regulatory update", "audit committee"},
        "technical architecture": {"technical architecture", "system design", "spec review"},
        "system design": {"system design", "technical architecture", "spec review"},
        "market analysis": {"market analysis", "business review", "operating review"},
        "image story": {"image story", "brand story", "case study", "editorial feature"},
        "case study": {"case study", "image story", "brand story"},
        "summary": {"summary", "decision review", "business review"},
        "decision review": {"decision review", "summary", "business review"},
    },
    "tone": {
        "analytical": {"analytical", "clean", "considered", "polished", "neutral"},
        "controlled": {"controlled", "clean", "considered", "neutral"},
        "clean": {"clean", "considered", "polished", "neutral"},
        "bold": {"bold", "graphic", "design-led"},
        "design-led": {"design-led", "graphic", "bold"},
        "crisp": {"crisp", "clean", "analytical", "polished"},
        "structured": {"structured", "clean", "analytical", "instructional"},
        "instructional": {"instructional", "structured", "clear"},
        "pragmatic": {"pragmatic", "analytical", "structured", "clean"},
        "comparative": {"comparative", "analytical", "sharp"},
        "narrative": {"narrative", "magazine", "literary", "considered"},
        "magazine": {"magazine", "narrative", "literary", "considered"},
        "retro": {"retro"},
        "graphic": {"graphic", "bold", "design-led", "retro"},
        "technical": {"technical", "structured", "precise"},
        "precise": {"precise", "technical", "structured"},
        "conclusive": {"conclusive", "clear", "controlled"},
        "clear": {"clear", "controlled", "instructional"},
    },
    "mood": {
        "professional": {"professional", "modern", "calm", "trustworthy"},
        "trustworthy": {"trustworthy", "professional", "calm"},
        "serious": {"serious", "professional", "trustworthy", "calm"},
        "confident": {"confident", "punchy", "modern", "editorial"},
        "playful": {"playful", "warm", "punchy"},
        "nostalgic": {"nostalgic", "warm"},
        "dramatic": {"dramatic", "elegant", "literary"},
        "technical": {"technical", "focused", "professional"},
        "scholarly": {"scholarly", "serious", "professional"},
        "approachable": {"approachable", "warm", "playful"},
        "focused": {"focused", "professional", "calm"},
        "sharp": {"sharp", "confident", "professional"},
        "reflective": {"reflective", "calm", "literary"},
        "literary": {"literary", "elegant", "quiet"},
        "elegant": {"elegant", "literary", "quiet"},
    },
    "density": {
        "medium-high": {"medium-high", "high", "medium"},
        "medium": {"medium", "medium-high"},
        "high": {"high", "medium-high"},
        "low": {"low", "medium"},
    },
    "formality": {
        "high": {"high", "medium-high"},
        "medium-high": {"medium-high", "high", "medium"},
        "medium": {"medium", "medium-high"},
        "low": {"low", "medium"},
    },
    "content_shape": {
        "dashboard": {"dashboard", "metrics", "scorecard", "data dashboard"},
        "metrics": {"metrics", "dashboard", "scorecard", "kpi"},
        "bar ranking": {"bar ranking", "ranking", "scorecard"},
        "diagnosis": {"diagnosis", "root cause", "analysis"},
        "timeline": {"timeline", "milestone", "phase"},
        "root cause": {"root cause", "diagnosis"},
        "action plan": {"action plan", "owner action", "remediation", "roadmap"},
        "owner action": {"owner action", "action plan", "roadmap"},
        "launch narrative": {"launch narrative", "campaign", "product story"},
        "campaign": {"campaign", "launch narrative"},
        "stats": {"stats", "metrics", "scorecard"},
        "market sizing": {"market sizing", "market map"},
        "traction": {"traction", "metrics", "growth curve"},
        "unit economics": {"unit economics", "business model"},
        "problem solution": {"problem solution", "pitch narrative"},
        "research poster": {"research poster", "scientific poster", "paper poster"},
        "method": {"method", "methods", "experiment design"},
        "findings": {"findings", "results"},
        "references": {"references", "citation"},
        "affiliation": {"affiliation", "logo affiliation"},
        "agenda": {"agenda", "schedule"},
        "checklist": {"checklist", "playbook"},
        "steps": {"steps", "process"},
        "exercise": {"exercise", "workshop activity"},
        "roadmap": {"roadmap", "quarterly priorities", "owner action"},
        "quarterly priorities": {"quarterly priorities", "priority list", "roadmap"},
        "dependency map": {"dependency map", "dependencies"},
        "comparison matrix": {"comparison matrix", "feature matrix", "versus"},
        "feature matrix": {"feature matrix", "comparison matrix", "table"},
        "table": {"table", "feature matrix", "comparison matrix"},
        "positioning": {"positioning", "market map"},
        "versus": {"versus", "comparison matrix"},
        "milestone": {"milestone", "timeline"},
        "phase": {"phase", "timeline"},
        "story arc": {"story arc", "narrative"},
        "image story": {"image story", "gallery", "full bleed image story"},
        "essay": {"essay", "longform"},
        "quote": {"quote", "claim"},
        "scorecard": {"scorecard", "dashboard", "metrics"},
        "executive scorecard": {"executive scorecard"},
        "trend": {"trend", "growth curve", "line chart"},
        "funnel": {"funnel", "conversion funnel"},
        "dense grid": {"dense grid", "panel grid", "grid", "data grid"},
        "panel grid": {"panel grid", "dense grid", "grid"},
        "risk matrix": {"risk matrix", "controls", "remediation"},
        "controls": {"controls", "risk matrix"},
        "remediation": {"remediation", "action plan"},
        "architecture": {"architecture", "dependency map", "nodes"},
        "nodes": {"nodes", "architecture", "dependency map"},
        "market map": {"market map", "positioning", "trend", "bar ranking"},
        "takeaways": {"takeaways", "action plan", "summary"},
        "evidence cards": {"evidence cards", "image story", "case study"},
    },
}

METADATA_FIELDS = {
    "occasion": ("occasion",),
    "mood": ("mood",),
    "tone": ("tone",),
    "formality": ("formality",),
    "density": ("density",),
    "scheme": ("scheme",),
    "content_shape": ("content_shape", "content_shapes", "layout_archetypes", "supported_content_shapes"),
}


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def prompt_matches_keywords(prompt_norm: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        keyword_norm = normalize_text(keyword)
        if re.fullmatch(r"[a-z0-9 ]+", keyword_norm):
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword_norm)}(?![a-z0-9])", prompt_norm):
                return True
        elif keyword_norm in prompt_norm:
            return True
    return False


def list_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    if isinstance(value, str):
        text = normalize_text(value)
        return [text] if text else []
    return []


def asset_values(asset: dict[str, Any], field: str) -> set[str]:
    values: set[str] = set()
    for key in METADATA_FIELDS.get(field, (field,)):
        values.update(list_values(asset.get(key)))
    return values


def infer_brief_signals(prompt: str) -> dict[str, Any]:
    prompt_norm = normalize_text(prompt)
    weighted: list[WeightedSignal] = []
    for keywords, signals in PROMPT_RULES:
        if prompt_matches_keywords(prompt_norm, keywords):
            weighted.extend(signals)

    grouped: dict[str, list[str]] = {
        "occasion": [],
        "mood": [],
        "tone": [],
        "content_shape": [],
    }
    scalar_scores: dict[str, dict[str, int]] = {"formality": {}, "density": {}, "scheme": {}}
    for signal in weighted:
        if signal.field in grouped and signal.value not in grouped[signal.field]:
            grouped[signal.field].append(signal.value)
        elif signal.field in scalar_scores:
            scalar_scores[signal.field][signal.value] = scalar_scores[signal.field].get(signal.value, 0) + signal.weight

    result: dict[str, Any] = {key: values for key, values in grouped.items() if values}
    for field, scores in scalar_scores.items():
        if scores:
            result[field] = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return result


def signal_matches_asset(signal: WeightedSignal, asset: dict[str, Any]) -> bool:
    values = asset_values(asset, signal.field)
    signal_value = normalize_text(signal.value)
    if signal_value in values:
        return True
    aliases = {
        normalize_text(alias)
        for alias in FIELD_ALIASES.get(signal.field, {}).get(signal.value, {signal.value})
    }
    return bool(values.intersection(aliases))


def avoid_penalty(prompt: str, asset: dict[str, Any]) -> tuple[int, list[str]]:
    prompt_norm = normalize_text(prompt)
    avoid_text = normalize_text(asset.get("avoid_for"))
    if not avoid_text:
        return 0, []
    penalties: list[str] = []
    formal_override = any(
        token in prompt_norm
        for token in ("克制", "低饱和", "严肃", "董事会", "管理层", "高管", "正式", "formal", "executive", "board")
    )
    avoid_checks = (
        (
            ("playful", "informal", "hot", "casual", "warm", "潮流", "街头", "热烈", "年轻", "冲击", "retro", "复古", "y2k", "pixel", "像素"),
            ("playful", "informal", "hot", "casual", "warm", "heat", "punch"),
            "avoid_for:playful_or_informal",
        ),
        (
            ("quiet", "克制", "低饱和", "严肃", "董事会", "管理层", "高管", "驾驶舱", "formal", "executive", "board"),
            ("quiet", "traditional", "serious", "board", "executive"),
            "avoid_for:quiet_or_formal",
        ),
        (
            ("dense", "高密度", "密集", "dashboard", "看板", "scorecard"),
            ("dense", "high density", "operational"),
            "avoid_for:dense_or_operational",
        ),
    )
    for prompt_tokens, avoid_tokens, reason in avoid_checks:
        if reason == "avoid_for:playful_or_informal" and formal_override:
            continue
        if any(token in prompt_norm for token in prompt_tokens) and any(token in avoid_text for token in avoid_tokens):
            penalties.append(reason)
    for token in ("playful", "潮流", "街头", "热烈", "年轻", "冲击", "retro", "复古", "y2k", "pixel", "像素"):
        if (
            not formal_override
            and token in prompt_norm
            and ("playful" in avoid_text or "informal" in avoid_text or "heat" in avoid_text)
        ):
            penalties.append("avoid_for:playful_or_informal")
            break
    return len(penalties) * 12, penalties


def scheme_boundary_penalty(prompt: str, asset: dict[str, Any]) -> tuple[int, list[str]]:
    scheme_values = asset_values(asset, "scheme")
    prompt_norm = normalize_text(prompt)
    dark_tokens = ("dark", "night", "暗色", "深色", "黑底", "暗黑", "夜间", "黑色")
    prompt_requests_dark = any(token in prompt_norm for token in dark_tokens)
    if prompt_requests_dark and "dark" not in scheme_values:
        return 8, ["style_mismatch:scheme"]
    if not prompt_requests_dark and "dark" in scheme_values:
        return 8, ["style_mismatch:scheme"]
    return 0, []


def weighted_signals_for_prompt(prompt: str) -> list[WeightedSignal]:
    prompt_norm = normalize_text(prompt)
    weighted: list[WeightedSignal] = []
    for keywords, signals in PROMPT_RULES:
        if prompt_matches_keywords(prompt_norm, keywords):
            weighted.extend(signals)
    return weighted


def score_asset(prompt: str, asset: dict[str, Any]) -> dict[str, Any]:
    matched: list[str] = []
    missed: list[str] = []
    matched_fields: set[str] = set()
    missed_fields: set[str] = set()
    score = 0
    weighted_signals = weighted_signals_for_prompt(prompt)
    for signal in weighted_signals:
        label = f"{signal.field}:{signal.value}"
        if signal_matches_asset(signal, asset):
            score += signal.weight
            matched.append(label)
            matched_fields.add(signal.field)
        else:
            missed.append(label)
            missed_fields.add(signal.field)

    best_for = normalize_text(asset.get("best_for"))
    for signal in weighted_signals:
        if normalize_text(signal.value) in best_for:
            score += 2
            matched.append(f"best_for:{signal.value}")

    penalty, rejection_reasons = avoid_penalty(prompt, asset)
    scheme_penalty, scheme_reasons = scheme_boundary_penalty(prompt, asset)
    score -= penalty + scheme_penalty
    rejection_reasons.extend(scheme_reasons)
    if weighted_signals:
        for field in ("occasion", "content_shape"):
            if field in missed_fields and field not in matched_fields:
                rejection_reasons.append(f"missing_{field}_match")
        for field in ("mood", "tone", "formality", "density", "scheme"):
            if field in missed_fields and field not in matched_fields:
                rejection_reasons.append(f"style_mismatch:{field}")
    if not matched:
        rejection_reasons.append("low_semantic_overlap")
    if penalty:
        rejection_reasons.append(f"avoid_penalty:{penalty}")

    return {
        "id": asset.get("id") or asset.get("slug") or asset.get("name"),
        "name": asset.get("name"),
        "score": score,
        "matched_signals": matched,
        "missed_signals": missed,
        "rejection_reasons": rejection_reasons,
    }


def rank_assets(prompt: str, assets: list[dict[str, Any]], *, top_k: int = 3) -> dict[str, Any]:
    scored = [score_asset(prompt, asset) for asset in assets]
    scored.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    considered = [str(item["id"]) for item in scored]
    rejection_reasons = {
        str(item["id"]): item["rejection_reasons"]
        for item in scored
        if item["rejection_reasons"] or item not in scored[:top_k]
    }
    return {
        "brief_signals": infer_brief_signals(prompt),
        "selected_template_id": str(scored[0]["id"]) if scored else None,
        "candidate_templates_considered": considered,
        "candidate_rejection_reasons": rejection_reasons,
        "candidates": scored[:top_k],
    }
