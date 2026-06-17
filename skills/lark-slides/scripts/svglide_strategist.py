#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


CONTRACT_SCHEMA_VERSION = "svglide-strategist-contract/v1"
TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")

CANVAS = {"width": 960, "height": 540, "viewBox": "0 0 960 540"}
SAFE_AREA = {"x": 48, "y": 40, "width": 864, "height": 460}
DEFAULT_GUARDRAILS = [
    "renderer_id must change actual geometry, not only the name",
    "visual_recipe must map to SVGlide-safe primitives present in the SVG source",
    "main text and chart labels stay inside safe area",
    "dense page uses a structured visual carrier, not a long bullet box",
    "avoid XML-like card layout unless the page has real SVG-native visual structure",
]


PAGE_PROFILES: dict[str, dict[str, Any]] = {
    "cover": {
        "seed_id": "cover_hero_statement",
        "page_type": "cover",
        "composition_archetype": "full_bleed_field",
        "required_visual_evidence": ["full_page_archetype", "hero_route", "title_field"],
        "primary_motif": "hero_route",
        "chart_type": "",
        "page_rhythm": "anchor",
        "renderer_id": "cover_hero_statement",
        "main_visual_anchor": {"layout_box_role": "visual", "description": "large thesis text paired with one abstract SVG motif"},
        "svg_effects": ["typography", "path"],
        "asset_id": "chart.vertical_list",
        "density_contract": "one thesis plus one visual motif",
    },
    "agenda": {
        "seed_id": "agenda_numbered_path",
        "page_type": "agenda",
        "composition_archetype": "indexed_path",
        "required_visual_evidence": ["numbered_path", "section_index", "semantic_labels"],
        "primary_motif": "numbered_route",
        "chart_type": "",
        "page_rhythm": "breathing",
        "renderer_id": "agenda_numbered_path",
        "main_visual_anchor": {"layout_box_role": "timeline", "description": "numbered agenda route with compact section labels"},
        "svg_effects": ["typography", "connector_flow", "path"],
        "asset_id": "chart.agenda_list",
        "density_contract": "agenda route >= 4 section labels",
    },
    "section": {
        "seed_id": "section_divider_index",
        "page_type": "section_divider",
        "composition_archetype": "section_signal",
        "required_visual_evidence": ["section_index", "hero_signal", "full_page_archetype"],
        "primary_motif": "section_index",
        "chart_type": "",
        "page_rhythm": "anchor",
        "renderer_id": "section_divider_index",
        "main_visual_anchor": {"layout_box_role": "visual", "description": "oversized chapter index paired with a full-page signal field"},
        "svg_effects": ["typography", "gradient"],
        "asset_id": "chart.numbered_steps",
        "density_contract": "one chapter signal plus one transition sentence",
    },
    "dashboard": {
        "seed_id": "dashboard_kpi_grid",
        "page_type": "kpi_overview",
        "composition_archetype": "data_stage",
        "required_visual_evidence": ["metric_hierarchy", "chart_geometry", "dashboard_grid"],
        "primary_motif": "metric_grid",
        "chart_type": "",
        "page_rhythm": "dense",
        "renderer_id": "dashboard_kpi_grid",
        "main_visual_anchor": {"layout_box_role": "chart", "description": "KPI dashboard grid with hero metrics and micro trends"},
        "svg_effects": ["typography", "chart_geometry"],
        "asset_id": "chart.kpi_cards",
        "density_contract": "dashboard >= 4 metrics",
    },
    "roadmap": {
        "seed_id": "timeline_roadmap",
        "page_type": "roadmap",
        "composition_archetype": "layered_timeline",
        "required_visual_evidence": ["connector_flow", "phase_spine", "full_page_archetype"],
        "primary_motif": "phase_spine",
        "chart_type": "",
        "page_rhythm": "dense",
        "renderer_id": "timeline_roadmap",
        "main_visual_anchor": {"layout_box_role": "timeline", "description": "milestone spine with compact phase labels"},
        "svg_effects": ["typography", "connector_flow", "path"],
        "asset_id": "chart.timeline",
        "density_contract": "timeline >= 3 milestones",
    },
    "process": {
        "seed_id": "process_pipeline",
        "page_type": "process_flow",
        "composition_archetype": "layered_timeline",
        "required_visual_evidence": ["connector_flow", "flow_lanes", "full_page_archetype"],
        "primary_motif": "flow_route",
        "chart_type": "",
        "page_rhythm": "dense",
        "renderer_id": "process_pipeline",
        "main_visual_anchor": {"layout_box_role": "flow", "description": "left-to-right process path with input and output anchors"},
        "svg_effects": ["typography", "connector_flow", "path"],
        "asset_id": "chart.process_flow",
        "density_contract": "process path >= 4 steps",
    },
    "comparison": {
        "seed_id": "comparison_two_column_decision",
        "page_type": "comparison",
        "composition_archetype": "comparison_matrix",
        "required_visual_evidence": ["decision_matrix", "contrast_panels", "semantic_labels"],
        "primary_motif": "decision_axis",
        "chart_type": "",
        "page_rhythm": "dense",
        "renderer_id": "comparison_two_column_decision",
        "main_visual_anchor": {"layout_box_role": "table", "description": "two-column decision matrix with dimension rail"},
        "svg_effects": ["typography", "path"],
        "asset_id": "chart.comparison_table",
        "density_contract": "comparison table >= 4 cells",
    },
    "capability": {
        "seed_id": "capability_icon_map",
        "page_type": "capability_map",
        "composition_archetype": "radial_system",
        "required_visual_evidence": ["hub_spoke", "sector_field", "semantic_labels"],
        "primary_motif": "radial_hub",
        "chart_type": "hub_spoke",
        "page_rhythm": "dense",
        "renderer_id": "capability_icon_map",
        "main_visual_anchor": {"layout_box_role": "visual", "description": "central capability node with surrounding module grid"},
        "svg_effects": ["typography", "connector_flow"],
        "asset_id": "chart.hub_spoke",
        "density_contract": "capability map >= 4 nodes",
    },
    "chart": {
        "seed_id": "single_chart_takeaway",
        "page_type": "chart_takeaway",
        "composition_archetype": "data_stage",
        "required_visual_evidence": ["chart_geometry", "insight_strip", "full_page_archetype"],
        "primary_motif": "takeaway_chart",
        "chart_type": "bar_chart",
        "page_rhythm": "dense",
        "renderer_id": "single_chart_takeaway",
        "main_visual_anchor": {"layout_box_role": "chart", "description": "single chart area with one takeaway annotation"},
        "svg_effects": ["typography", "chart_geometry"],
        "asset_id": "chart.bar_chart",
        "density_contract": "chart >= 3 visible marks",
    },
    "closing": {
        "seed_id": "closing_summary",
        "page_type": "closing",
        "composition_archetype": "closing_manifesto",
        "required_visual_evidence": ["closing_ribbon", "action_cards", "full_page_archetype"],
        "primary_motif": "closing_route",
        "chart_type": "",
        "page_rhythm": "anchor",
        "renderer_id": "closing_summary",
        "main_visual_anchor": {"layout_box_role": "callout", "description": "closing statement plus next-action callout"},
        "svg_effects": ["typography"],
        "asset_id": "chart.numbered_steps",
        "density_contract": "one closing message plus one next action",
    },
    "annotation": {
        "seed_id": "spotlight_diagnosis_callout",
        "page_type": "insight_callout",
        "composition_archetype": "annotated_spotlight",
        "required_visual_evidence": ["spotlight", "annotation", "semantic_labels"],
        "primary_motif": "spotlight_field",
        "chart_type": "",
        "page_rhythm": "breathing",
        "renderer_id": "spotlight_diagnosis_callout",
        "main_visual_anchor": {"layout_box_role": "spotlight", "description": "annotated visual field with one spotlight and side note"},
        "svg_effects": ["typography", "spotlight"],
        "asset_id": "chart.labeled_card",
        "density_contract": "spotlight callout <= 2 targets",
    },
}

KEYWORD_PROFILES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("agenda", ("agenda", "contents", "table of contents", "toc", "目录", "议程")),
    ("section", ("section", "chapter", "section divider", "divider", "transition", "章节", "过渡", "转场", "第1章", "第2章", "第3章", "01 ", "02 ", "03 ")),
    ("dashboard", ("dashboard", "kpi", "metric", "metrics", "status", "scorecard", "health", "看板", "指标", "状态")),
    ("roadmap", ("roadmap", "timeline", "milestone", "phase", "plan", "规划", "里程碑", "阶段")),
    ("process", ("process", "pipeline", "workflow", "flow", "funnel", "步骤", "流程", "链路")),
    ("comparison", ("compare", "comparison", "versus", "vs", "matrix", "table", "decision", "对比", "比较", "矩阵")),
    ("capability", ("capability", "module", "architecture", "system", "hub", "spoke", "能力", "模块", "架构")),
    ("chart", ("chart", "bar", "line", "trend", "data", "evidence", "数据", "图表", "趋势")),
    ("closing", ("closing", "summary", "next", "thanks", "q&a", "结尾", "总结", "下一步")),
    ("cover", ("cover", "opening", "title", "thesis", "封面", "开场", "标题")),
)

STYLE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("raw_grid", ("dashboard", "kpi", "metric", "technical", "dense", "status", "ops", "operation", "看板", "指标")),
    ("long_table", ("process", "pipeline", "responsibility", "plan", "workflow", "流程", "责任")),
    ("riptide_cobalt", ("technology", "architecture", "flow", "system", "tech", "技术", "架构")),
    ("data_journalism_editorial", ("financial", "market", "report", "data", "analysis", "finance", "数据", "分析")),
    ("monochrome", ("serious", "formal", "minimal", "decision", "compare", "正式", "决策")),
)

NARRATIVE_MODES = {"briefing", "instructional", "narrative", "pyramid", "showcase"}

MODE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("instructional", ("training", "tutorial", "course", "lesson", "how-to", "playbook", "教学", "培训", "教程")),
    ("pyramid", ("decision", "board", "strategy", "proposal", "investment", "consulting", "决策", "战略", "提案", "投资")),
    ("showcase", ("launch", "showcase", "portfolio", "brand", "event", "product reveal", "发布", "展示", "作品集", "品牌")),
    ("narrative", ("story", "journey", "case", "vision", "future", "体验", "旅程", "故事", "案例", "愿景")),
    ("briefing", ("briefing", "review", "report", "status", "operations", "weekly", "汇报", "报告", "复盘", "经营", "周报")),
)


def script_path() -> Path:
    return Path(__file__).resolve()


def references_dir() -> Path:
    return script_path().parents[1] / "references"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clone_json(value: Any) -> Any:
    return copy.deepcopy(value)


def tokenize(*values: object) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            tokens.update(tokenize(*value.values()))
            continue
        if isinstance(value, (list, tuple, set)):
            tokens.update(tokenize(*value))
            continue
        tokens.update(match.group(0).lower() for match in TOKEN_RE.finditer(str(value)))
    return tokens


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(compact_text(item) for item in value.values() if compact_text(item))
    if isinstance(value, (list, tuple, set)):
        return " ".join(compact_text(item) for item in value if compact_text(item))
    return str(value).strip()


def load_catalogs(ref_dir: Path | None = None) -> dict[str, Any]:
    root = ref_dir or references_dir()
    style_data = read_json(root / "style-presets.json")
    seed_data = read_json(root / "svg-seeds.json")
    recipe_data = read_json(root / "svg-recipes.json")
    pattern_data = read_json(root / "svglide-design-pattern-map.json")
    return {
        "style_presets": {item["style_id"]: item for item in style_data.get("presets", []) if isinstance(item, dict) and item.get("style_id")},
        "seeds": seed_data.get("seeds", {}),
        "recipes": recipe_data.get("recipes", {}),
        "chart_type_contracts": recipe_data.get("chart_type_contracts", {}),
        "pattern_ids": {item.get("id") for item in pattern_data.get("resources", []) if isinstance(item, dict) and item.get("id")},
    }


def first_present(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = compact_text(data.get(key))
        if value:
            return value
    visual_plan = data.get("visual_plan")
    if isinstance(visual_plan, dict):
        for key in keys:
            value = compact_text(visual_plan.get(key))
            if value:
                return value
    return ""


def classify_profile(text: str, *, index: int, total: int) -> str:
    lowered = text.lower()
    if index == 0 and any(keyword in lowered for keyword in ("cover", "opening", "title", "thesis", "封面", "开场")):
        return "cover"
    if total > 1 and index == total - 1 and any(keyword in lowered for keyword in ("closing", "summary", "next", "thanks", "q&a", "结尾", "总结", "下一步")):
        return "closing"
    for profile, keywords in KEYWORD_PROFILES:
        if any(keyword in lowered for keyword in keywords):
            return profile
    if index == 0:
        return "cover"
    if total > 1 and index == total - 1:
        return "closing"
    return "annotation"


def style_preset_from_brief(brief: str, catalogs: dict[str, Any]) -> str:
    lowered = brief.lower()
    for style_id, keywords in STYLE_HINTS:
        if style_id in catalogs["style_presets"] and any(keyword in lowered for keyword in keywords):
            return style_id
    return "raw_grid" if "raw_grid" in catalogs["style_presets"] else sorted(catalogs["style_presets"])[0]


def narrative_mode_from_brief(brief: str, slide_plan: dict[str, Any] | None = None) -> str:
    lowered = " ".join([brief, compact_text(slide_plan or {})]).lower()
    tokens = tokenize(lowered)
    for mode, keywords in MODE_HINTS:
        if any((keyword in tokens if re.fullmatch(r"[a-z0-9-]+", keyword) else keyword in lowered) for keyword in keywords):
            return mode
    return "briefing"


def style_system_from_preset(style_id: str, catalogs: dict[str, Any]) -> dict[str, Any]:
    preset = catalogs["style_presets"].get(style_id, {})
    palette = preset.get("palette") if isinstance(preset.get("palette"), dict) else {}
    shape_language = preset.get("shape_language") if isinstance(preset.get("shape_language"), dict) else {}
    density = preset.get("density") if isinstance(preset.get("density"), dict) else {}
    return {
        "palette": {
            "background": palette.get("background", "#F5F5F5"),
            "text": palette.get("text", "#0A0A0A"),
            "accent": palette.get("accent", "#2563EB"),
            "support": clone_json(palette.get("support", [])),
        },
        "typography": "strong title, readable native text labels",
        "background_strategy": shape_language.get("panel_treatment", "structured panels with explicit text surfaces"),
        "motif": shape_language.get("texture", "local SVG motif derived from selected page recipe"),
        "density": {
            "text_density": density.get("text_density", "medium"),
            "label_density": density.get("label_density", "medium"),
            "connector_density": density.get("connector_density", "medium"),
        },
    }


def apply_brief_palette(style_system: dict[str, Any], brief: str) -> dict[str, Any]:
    colors: list[str] = []
    for match in HEX_COLOR_RE.finditer(brief):
        color = match.group(0).upper()
        if color not in colors:
            colors.append(color)
    if not colors:
        return style_system
    output = clone_json(style_system)
    palette = output.setdefault("palette", {})
    if isinstance(palette, dict):
        palette["accent"] = colors[0]
        if len(colors) > 1:
            palette["support"] = colors[1:]
    output["palette_source"] = "brief_hex_colors"
    return output


def slide_text(slide: dict[str, Any], fallback_description: str) -> str:
    parts = [
        first_present(slide, ("title", "headline", "name")),
        first_present(slide, ("description", "summary", "body", "key_message", "page_type", "chart_type", "visual_recipe")),
        fallback_description,
    ]
    return " ".join(part for part in parts if part)


def seed_for_profile(profile: str, catalogs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    seed_id = PAGE_PROFILES[profile]["seed_id"]
    seeds = catalogs["seeds"]
    if seed_id not in seeds:
        raise ValueError(f"missing SVG seed: {seed_id}")
    return seed_id, seeds[seed_id]


def seed_for_slide(slide: dict[str, Any], profile: str, catalogs: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    explicit_seed = compact_text(slide.get("seed_id"))
    seeds = catalogs["seeds"]
    if explicit_seed and explicit_seed in seeds:
        seed = seeds[explicit_seed]
        profile_data = dict(PAGE_PROFILES[profile])
        profile_data["seed_id"] = explicit_seed
        return explicit_seed, seed, profile_data

    chart_type = compact_text(slide.get("chart_type")).replace("-", "_").lower()
    visual_recipe = compact_text(slide.get("visual_recipe")).replace("-", "_").lower()
    for candidate, data in PAGE_PROFILES.items():
        if chart_type and chart_type == data["chart_type"]:
            seed_id, seed = seed_for_profile(candidate, catalogs)
            return seed_id, seed, data
        if visual_recipe and seeds.get(data["seed_id"], {}).get("visual_recipe") == visual_recipe:
            seed_id, seed = seed_for_profile(candidate, catalogs)
            return seed_id, seed, data

    seed_id, seed = seed_for_profile(profile, catalogs)
    return seed_id, seed, PAGE_PROFILES[profile]


def list_union(*values: Any) -> list[str]:
    out: list[str] = []
    for value in values:
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, (list, tuple, set)):
            candidates = [str(item) for item in value if str(item).strip()]
        else:
            candidates = []
        for item in candidates:
            if item not in out:
                out.append(item)
    return out


def setdefault_clone(target: dict[str, Any], key: str, value: Any) -> None:
    if key not in target or target[key] in (None, "", []):
        target[key] = clone_json(value)


def normalize_empty_chart_type(value: Any) -> str:
    normalized = compact_text(value).replace("-", "_").lower()
    return "" if normalized in {"none", "na", "n_a", "not_applicable", "no_chart", "no"} else normalized


def known_profile_evidence() -> set[str]:
    evidence: set[str] = set()
    for profile in PAGE_PROFILES.values():
        raw = profile.get("required_visual_evidence")
        if isinstance(raw, list):
            evidence.update(str(item) for item in raw if str(item).strip())
    return evidence


def complete_visual_design_contract(completed: dict[str, Any], profile_data: dict[str, Any]) -> dict[str, Any]:
    existing = completed.get("visual_design_contract")
    contract = clone_json(existing) if isinstance(existing, dict) else {}
    thesis = first_present(completed, ("visual_thesis", "key_message", "one_idea", "title", "headline", "description"))
    existing_required = list_union(contract.get("required_visual_evidence"))
    manual_required = [item for item in existing_required if item not in known_profile_evidence()]
    required = list_union(manual_required, profile_data.get("required_visual_evidence"))
    pattern_bundle = list_union(contract.get("pattern_bundle"), profile_data.get("asset_id"))
    setdefault_clone(contract, "schema_version", "svglide-visual-design-contract/v1")
    setdefault_clone(contract, "page_kind", profile_data["page_type"])
    setdefault_clone(contract, "visual_thesis", thesis)
    setdefault_clone(contract, "composition_archetype", profile_data["composition_archetype"])
    contract["pattern_bundle"] = pattern_bundle
    setdefault_clone(contract, "density", profile_data["page_rhythm"])
    setdefault_clone(contract, "primary_motif", profile_data["primary_motif"])
    contract["required_visual_evidence"] = required
    setdefault_clone(contract, "renderer_id", profile_data["renderer_id"])
    setdefault_clone(contract, "layout_seed_id", completed.get("seed_id"))
    setdefault_clone(contract, "visual_recipe", completed.get("visual_recipe"))
    return contract


def complete_slide(slide: dict[str, Any], *, brief: str, fallback_description: str, index: int, total: int, catalogs: dict[str, Any]) -> dict[str, Any]:
    completed = clone_json(slide)
    if "chart_type" in completed:
        completed["chart_type"] = normalize_empty_chart_type(completed.get("chart_type"))
    text = slide_text(completed, fallback_description) or brief
    profile = classify_profile(text, index=index, total=total)
    seed_id, seed, profile_data = seed_for_slide(completed, profile, catalogs)
    recipe = compact_text(completed.get("visual_recipe")) or compact_text(seed.get("visual_recipe"))
    recipe_contract = catalogs["recipes"].get(recipe, {})
    required_primitives = list_union(recipe_contract.get("required_primitives"), seed.get("required_primitives"), completed.get("required_primitives"))
    svg_primitives = list_union(completed.get("svg_primitives"), required_primitives, ["typography", "geometric_shape"])

    setdefault_clone(completed, "page", index + 1)
    setdefault_clone(completed, "key_message", first_present(completed, ("key_message", "one_idea", "title", "headline", "description")) or text)
    setdefault_clone(completed, "renderer_id", profile_data["renderer_id"])
    setdefault_clone(completed, "page_rhythm", profile_data["page_rhythm"])
    setdefault_clone(completed, "page_type", profile_data["page_type"])
    setdefault_clone(completed, "chart_type", profile_data["chart_type"])
    setdefault_clone(completed, "main_visual_anchor", profile_data["main_visual_anchor"])
    setdefault_clone(completed, "seed_id", seed_id)
    completed["layout_skeleton_id"] = clone_json(seed.get("layout_skeleton", {}).get("id", f"{seed_id}_skeleton"))
    completed["layout_family"] = clone_json(seed.get("layout_family", profile))
    setdefault_clone(completed, "visual_recipe", recipe)
    setdefault_clone(completed, "visual_signature", f"{profile_data['page_type']} / {profile_data['renderer_id']} / {profile_data['asset_id']}")
    completed["svg_effects"] = clone_json(profile_data["svg_effects"])
    completed["layout_boxes"] = clone_json(seed.get("layout_boxes", []))
    completed["content_budget"] = clone_json(seed.get("content_budget", {}))
    completed["text_capacity"] = clone_json(seed.get("default_text_capacity") or seed.get("content_budget", {}))
    completed["text_budget_by_role"] = clone_json(seed.get("text_budget_by_role", {}))
    completed["reserved_bands"] = clone_json(seed.get("reserved_bands", {}))
    completed["footer_safe_zone"] = clone_json(seed.get("footer_safe_zone", {}))
    completed["vertical_text_policy"] = clone_json(seed.get("vertical_text_policy", {"mode": "deny", "allowed_roles": [], "max_chars": 0, "max_lines": 0}))
    setdefault_clone(
        completed,
        "reference_asset",
        {
            "source": "svglide_design_pattern",
            "asset_id": profile_data["asset_id"],
            "usage": "page-type geometry only; do not copy raw SVG paths",
        },
    )
    setdefault_clone(completed, "visual_intent", f"use {recipe.replace('_', ' ')} structure to make the page readable as SVG-native content")
    setdefault_clone(completed, "visual_focal_point", profile_data["main_visual_anchor"])
    setdefault_clone(completed, "required_primitives", required_primitives)
    setdefault_clone(completed, "svg_primitives", svg_primitives)
    setdefault_clone(completed, "xml_like_risk", "without the declared SVG primitives this page would degrade into ordinary text boxes")
    setdefault_clone(completed, "content_density_contract", profile_data["density_contract"])
    setdefault_clone(completed, "asset_contract", "none_required")
    setdefault_clone(completed, "risk_flags", [])
    setdefault_clone(completed, "source_status", "user_prompt_only")
    setdefault_clone(completed, "source_policy", "when source material is missing, mark missing evidence and avoid numeric claims")
    setdefault_clone(completed, "layout_guardrails", DEFAULT_GUARDRAILS)
    completed["visual_design_contract"] = complete_visual_design_contract(completed, profile_data)
    return completed


def normalize_slide_inputs(slide_plan: dict[str, Any] | None, page_descriptions: list[str]) -> list[dict[str, Any]]:
    plan = slide_plan or {}
    raw_slides = plan.get("slides")
    if isinstance(raw_slides, list) and raw_slides:
        slides = [clone_json(item) for item in raw_slides if isinstance(item, dict)]
    else:
        pages = plan.get("pages")
        slides = [clone_json(item) for item in pages if isinstance(item, dict)] if isinstance(pages, list) and pages else []
    if not slides:
        slides = [{"description": description} for description in page_descriptions]
    if not slides:
        slides = [{"description": "Cover: core message"}, {"description": "Closing: next steps"}]
    for index, description in enumerate(page_descriptions):
        if index >= len(slides):
            slides.append({"description": description})
        elif description and not compact_text(slides[index].get("description")):
            slides[index]["description"] = description
    return slides


def selected_asset_id(slide: dict[str, Any]) -> str:
    reference = slide.get("reference_asset")
    if isinstance(reference, dict):
        asset_id = compact_text(reference.get("asset_id") or reference.get("id"))
        if asset_id:
            return asset_id
    asset_id = compact_text(slide.get("asset_id") or slide.get("design_pattern_id"))
    return asset_id


def deck_rhythm_from_slides(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rhythm: list[dict[str, Any]] = []
    for index, slide in enumerate(slides, 1):
        item = {
            "page": slide.get("page", index),
            "rhythm": compact_text(slide.get("page_rhythm")) or "breathing",
            "page_type": compact_text(slide.get("page_type")) or "content",
        }
        rhythm.append(item)
    return rhythm


def build_design_pattern_selection(slides: list[dict[str, Any]], existing: Any, catalogs: dict[str, Any]) -> dict[str, Any]:
    selection = clone_json(existing) if isinstance(existing, dict) else {}
    raw_assets = selection.get("selected_assets")
    selected_assets: list[dict[str, Any]] = [clone_json(item) for item in raw_assets if isinstance(item, dict)] if isinstance(raw_assets, list) else []
    seen = {compact_text(asset.get("id") or asset.get("asset_id")) for asset in selected_assets}
    pattern_ids = catalogs.get("pattern_ids", set())
    for slide in slides:
        asset_id = selected_asset_id(slide)
        if not asset_id or asset_id in seen or (pattern_ids and asset_id not in pattern_ids):
            continue
        selected_assets.append(
            {
                "id": asset_id,
                "kind": "chart_template",
                "usage": "geometry_contract",
                "copy_policy": "derive_contract_only",
            }
        )
        seen.add(asset_id)
    setdefault_clone(selection, "schema_version", "svglide-design-pattern-selection/v1")
    setdefault_clone(selection, "mode", "local_contract")
    setdefault_clone(selection, "selected_assets", selected_assets)
    setdefault_clone(selection, "proof_status", "pending_component_report")
    return selection


def build_contract(
    *,
    brief: str = "",
    slide_plan: dict[str, Any] | None = None,
    page_descriptions: list[str] | None = None,
    ref_dir: Path | None = None,
) -> dict[str, Any]:
    catalogs = load_catalogs(ref_dir)
    descriptions = page_descriptions or []
    source_plan = clone_json(slide_plan) if isinstance(slide_plan, dict) else {}
    output = source_plan
    slides = normalize_slide_inputs(source_plan, descriptions)
    completed_slides = [
        complete_slide(slide, brief=brief, fallback_description=descriptions[index] if index < len(descriptions) else "", index=index, total=len(slides), catalogs=catalogs)
        for index, slide in enumerate(slides)
    ]

    style_id = compact_text(output.get("style_preset")) or style_preset_from_brief(brief or compact_text(output), catalogs)
    if style_id not in catalogs["style_presets"]:
        style_id = style_preset_from_brief(brief or compact_text(output), catalogs)
    explicit_mode = compact_text(output.get("narrative_mode") or output.get("mode"))
    narrative_mode = explicit_mode if explicit_mode in NARRATIVE_MODES else narrative_mode_from_brief(brief, output)

    setdefault_clone(output, "schema_version", CONTRACT_SCHEMA_VERSION)
    setdefault_clone(output, "output_mode", "svglide-svg")
    output["mode"] = narrative_mode
    setdefault_clone(output, "narrative_mode", narrative_mode)
    setdefault_clone(output, "canvas", CANVAS)
    setdefault_clone(output, "safe_area", SAFE_AREA)
    output["style_preset"] = style_id
    setdefault_clone(output, "style_selection_reason", f"{style_id} matches the brief and the selected SVG page recipes")
    output["style_system"] = apply_brief_palette(style_system_from_preset(style_id, catalogs), brief)
    for slide in completed_slides:
        contract = slide.get("visual_design_contract")
        if isinstance(contract, dict):
            setdefault_clone(contract, "style_preset", style_id)
    output["slides"] = completed_slides
    output["page_count"] = len(completed_slides)
    setdefault_clone(output, "page_rhythm", deck_rhythm_from_slides(completed_slides))
    output["design_pattern_selection"] = build_design_pattern_selection(completed_slides, output.get("design_pattern_selection"), catalogs)
    return output


def read_text_arg(path: str | None, inline: str | None) -> str:
    parts: list[str] = []
    if inline:
        parts.append(inline)
    if path:
        parts.append(Path(path).expanduser().read_text(encoding="utf-8"))
    return "\n".join(part.strip() for part in parts if part.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or complete a conservative SVGlide plan contract.")
    parser.add_argument("--brief", help="path to a brief text file")
    parser.add_argument("--brief-text", help="inline brief text")
    parser.add_argument("--plan", help="existing slide_plan.json to complete")
    parser.add_argument("--page-description", action="append", default=[], help="simple page description; may be repeated")
    parser.add_argument("--output", help="output JSON path; defaults to stdout")
    parser.add_argument("--in-place", action="store_true", help="write the completed contract back to --plan")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.in_place and not args.plan:
        parser.error("--in-place requires --plan")

    brief = read_text_arg(args.brief, args.brief_text)
    slide_plan = read_json(Path(args.plan).expanduser()) if args.plan else None
    if slide_plan is not None and not isinstance(slide_plan, dict):
        raise ValueError("--plan must point to a JSON object")

    result = build_contract(brief=brief, slide_plan=slide_plan, page_descriptions=args.page_description)
    output_path = Path(args.output).expanduser() if args.output else (Path(args.plan).expanduser() if args.in_place else None)
    if output_path:
        write_json(output_path, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
