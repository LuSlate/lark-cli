#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import svglide_recipe_selector


SCRIPT_DIR = Path(__file__).resolve().parent
LARK_SLIDES_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = LARK_SLIDES_DIR / "references"
FAMILIES_PATH = REFERENCES_DIR / "beautiful-html-template-families.json"
COMPONENT_REGISTRY_PATH = REFERENCES_DIR / "component-registry.json"
ASSET_STRATEGY_PATH = REFERENCES_DIR / "asset-strategy-registry.json"


INTERNAL_REVIEW_RE = re.compile(r"复盘|经营|管理层|指标|问题|原因|后续|review|business", re.IGNORECASE)
CULTURE_EVENT_RE = re.compile(r"艺术|展|活动|海报|文化|青年|poster|exhibition|biennale", re.IGNORECASE)
COMPANY_PRODUCT_RE = re.compile(r"公司|产品|竞品|MiniMax|智谱|brand|company|product|logo|screenshot", re.IGNORECASE)
QUANTIFIED_RE = re.compile(r"\d+|同比|环比|增长|下降|占比|排名|trend|share|%|KPI", re.IGNORECASE)

KEYWORD_FAMILY_BOOSTS: list[tuple[re.Pattern[str], dict[str, float], str]] = [
    (re.compile(r"内部|业务复盘|经营|季度|管理层|review|quarterly|business", re.IGNORECASE), {"blue-professional": 0.3, "signal": 0.22, "emerald-editorial": 0.2, "editorial-forest": 0.16}, "business review semantic fit"),
    (re.compile(r"投资人|投委会|finance|investor|board|董事会", re.IGNORECASE), {"signal": 0.28, "blue-professional": 0.24, "cartesian": 0.2, "emerald-editorial": 0.18}, "finance/institutional fit"),
    (re.compile(r"用户研究|research synthesis|访谈|洞察|定性", re.IGNORECASE), {"monochrome": 0.34, "vellum": 0.24, "pin-and-paper": 0.2}, "research synthesis fit"),
    (re.compile(r"艺术|展览|展|美术馆|museum|exhibition|biennale|curatorial", re.IGNORECASE), {"biennale-yellow": 0.34, "stencil-tablet": 0.24, "studio": 0.2}, "cultural exhibition fit"),
    (re.compile(r"海报|poster|品牌宣言|manifesto|magazine cover|封面", re.IGNORECASE), {"bold-poster": 0.34, "broadside": 0.24, "coral": 0.18}, "poster/editorial fit"),
    (re.compile(r"证据|案例|field|pin|贴纸|手作|crafted|notebook", re.IGNORECASE), {"pin-and-paper": 0.34, "retro-zine": 0.2, "scatterbrain": 0.18}, "crafted evidence fit"),
    (re.compile(r"矩阵|对比|matrix|comparison|table|高密度|dense", re.IGNORECASE), {"raw-grid": 0.32, "cartesian": 0.24, "neo-grid-bold": 0.2, "long-table": 0.18}, "matrix/table fit"),
    (re.compile(r"复古游戏|游戏|arcade|cyberpunk|web3|hackathon|retro gaming", re.IGNORECASE), {"8-bit-orbit": 0.34, "retro-windows": 0.28, "sakura-chroma": 0.16}, "retro digital fit"),
    (re.compile(r"白板|头脑风暴|brainstorm|workshop|工作坊", re.IGNORECASE), {"scatterbrain": 0.3, "daisy-days": 0.22, "pin-and-paper": 0.18}, "workshop/whiteboard fit"),
    (re.compile(r"餐饮|餐厅|小吃|菜单|餐桌|晚餐|programme|food|restaurant|menu", re.IGNORECASE), {"long-table": 0.38, "playful": 0.24, "coral": 0.18, "grove": 0.14}, "food/menu fit"),
    (re.compile(r"时尚|fashion|杂志|magazine|editorial spread", re.IGNORECASE), {"editorial-tri-tone": 0.32, "coral": 0.24, "pink-script": 0.2}, "fashion/editorial fit"),
    (re.compile(r"学术|白皮书|scholarly|policy|研究报告", re.IGNORECASE), {"vellum": 0.32, "cartesian": 0.24, "signal": 0.16}, "scholarly report fit"),
    (re.compile(r"SaaS|产品发布|launch|founder|创业|pitch", re.IGNORECASE), {"block-frame": 0.26, "neo-grid-bold": 0.24, "raw-grid": 0.22, "blue-professional": 0.16}, "product/pitch fit"),
    (re.compile(r"智谱|MiniMax|产品对比|竞品|公司|product comparison|company identity|company comparison", re.IGNORECASE), {"blue-professional": 0.28, "raw-grid": 0.24, "neo-grid-bold": 0.22, "signal": 0.18}, "company/product comparison fit"),
    (re.compile(r"创意机构|creative agency|studio credentials|作品集", re.IGNORECASE), {"creative-mode": 0.3, "studio": 0.26, "neo-grid-bold": 0.16}, "creative studio fit"),
    (re.compile(r"社区|activist|people|campaign|公益|倡议", re.IGNORECASE), {"peoples-platform": 0.34, "broadside": 0.2, "playful": 0.16}, "community campaign fit"),
    (re.compile(r"有机|健康|wellness|organic|生活方式", re.IGNORECASE), {"grove": 0.3, "mat": 0.24, "soft-editorial": 0.18}, "organic lifestyle fit"),
    (re.compile(r"教育|课程|training|lesson|亲和|friendly", re.IGNORECASE), {"daisy-days": 0.3, "playful": 0.24, "scatterbrain": 0.16}, "education/friendly fit"),
    (re.compile(r"档案|archive|archival|历史|文献", re.IGNORECASE), {"stencil-tablet": 0.3, "vellum": 0.24, "cartesian": 0.16}, "archival fit"),
    (re.compile(r"日系|磁带|cassette|vintage japanese|80s", re.IGNORECASE), {"sakura-chroma": 0.34, "retro-zine": 0.18, "retro-windows": 0.16}, "vintage japanese fit"),
    (re.compile(r"夜店|nocturnal|nightlife|夜间|sultry", re.IGNORECASE), {"pink-script": 0.3, "studio": 0.22, "coral": 0.18}, "night editorial fit"),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(path: Path = FAMILIES_PATH) -> dict[str, Any]:
    return load_json(path)


def load_families(path: Path = FAMILIES_PATH) -> list[dict[str, Any]]:
    registry = load_registry(path)
    families = registry.get("families", [])
    if not isinstance(families, list):
        raise ValueError("beautiful-html-template-families.json must contain families[]")
    return [family for family in families if isinstance(family, dict)]


def load_family(template_id: str, path: Path = FAMILIES_PATH) -> dict[str, Any]:
    for family in load_families(path):
        if family.get("template_id") == template_id:
            return family
    raise KeyError(template_id)


def normalize_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(normalize_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(normalize_text(item) for item in value)
    return str(value or "")


def policy_summary(value: Any, keys: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value.get(key) for key in keys if value.get(key) not in (None, "", [])}


def cjk_policy_summary(family: dict[str, Any]) -> dict[str, Any]:
    return policy_summary(
        family.get("cjk_policy"),
        ["strategy", "display_font_cn", "body_font_cn", "runtime_font_policy", "italic_policy", "letter_spacing_policy", "mixed_run_spacing"],
    )


def family_usage_policy_summary(family: dict[str, Any]) -> dict[str, Any]:
    return policy_summary(
        family.get("family_usage_policy"),
        ["closed_visual_system", "cross_family_layout_mix_allowed", "recolor_allowed", "font_substitution_allowed", "decorative_elements_policy"],
    )


def extension_grammar_summary(family: dict[str, Any]) -> dict[str, Any]:
    grammar = family.get("extension_grammar") if isinstance(family.get("extension_grammar"), dict) else {}
    return {
        "layout_rhythm": grammar.get("layout_rhythm"),
        "component_grammar": grammar.get("component_grammar", [])[:6] if isinstance(grammar.get("component_grammar"), list) else grammar.get("component_grammar"),
        "decorative_vocabulary": grammar.get("decorative_vocabulary", [])[:6] if isinstance(grammar.get("decorative_vocabulary"), list) else grammar.get("decorative_vocabulary"),
        "forbidden_mutations": grammar.get("forbidden_mutations", [])[:6] if isinstance(grammar.get("forbidden_mutations"), list) else grammar.get("forbidden_mutations"),
    }


def benchmark_roles(family: dict[str, Any]) -> list[str]:
    visual_dna = family.get("visual_dna") if isinstance(family.get("visual_dna"), dict) else {}
    benchmarks = visual_dna.get("screenshot_benchmarks") if isinstance(visual_dna.get("screenshot_benchmarks"), list) else []
    return [str(item.get("role")) for item in benchmarks if isinstance(item, dict) and item.get("role")]


def query_signals(query: str) -> dict[str, Any]:
    needs: list[str] = []
    tones: list[str] = []
    content_type = "general_presentation"
    density = "medium"
    if INTERNAL_REVIEW_RE.search(query):
        content_type = "internal_review"
        needs.extend(["metrics", "evidence", "action_plan"])
        tones.extend(["formal", "analytical"])
        density = "medium-high"
    if CULTURE_EVENT_RE.search(query):
        content_type = "cultural_event"
        needs.extend(["poster_visual", "event_context"])
        tones.extend(["bold", "editorial"])
    if COMPANY_PRODUCT_RE.search(query):
        needs.extend(["real_image", "identity", "comparison"])
    if QUANTIFIED_RE.search(query):
        needs.append("metrics")
    return {
        "content_type": content_type,
        "tone": sorted(set(tones)) or ["neutral"],
        "density": density,
        "needs": sorted(set(needs)),
    }


def token_overlap_score(query: str, value: Any) -> float:
    query_tokens = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", query.lower()))
    value_tokens = set(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", normalize_text(value).lower()))
    if not query_tokens or not value_tokens:
        return 0.0
    return len(query_tokens & value_tokens) / max(len(query_tokens), 1)


def family_score(query: str, signals: dict[str, Any], family: dict[str, Any]) -> tuple[float, list[str]]:
    semantic_fit = family.get("semantic_fit", {})
    text = normalize_text(semantic_fit)
    score = token_overlap_score(query, semantic_fit) * 0.35
    reasons: list[str] = []
    template_id = str(family.get("template_id") or "")

    if signals["content_type"] == "internal_review":
        if re.search(r"internal review|consulting|investor|finance|B2B|brief|professional|analytical", text, re.IGNORECASE):
            score += 0.38
            reasons.append("business review fit")
        if template_id in {"blue-professional", "emerald-editorial", "signal", "monochrome"}:
            score += 0.18
            reasons.append("preferred analytical family")
    if signals["content_type"] == "cultural_event":
        if re.search(r"art|exhibition|poster|culture|zine|editorial|biennale", text, re.IGNORECASE):
            score += 0.42
            reasons.append("cultural poster fit")
        if template_id in {"biennale-yellow", "bold-poster", "stencil-tablet", "studio"}:
            score += 0.18
            reasons.append("preferred cultural family")
        if template_id == "blue-professional":
            score -= 0.4
            reasons.append("avoid business-first template")
    if "real_image" in signals["needs"]:
        if "image_panel" in family.get("component_candidates", []):
            score += 0.08
            reasons.append("supports image panel")
    if signals["density"] in normalize_text(semantic_fit.get("density")):
        score += 0.05
    for pattern, boosts, reason in KEYWORD_FAMILY_BOOSTS:
        if pattern.search(query) and template_id in boosts:
            score += boosts[template_id]
            reasons.append(reason)
    if family.get("claim_level") == "source_inventory_only":
        score -= 0.03
        reasons.append("source inventory only; requires contract compile before absorbed claim")
    avoid_text = normalize_text(semantic_fit.get("avoid_when"))
    if avoid_text and token_overlap_score(query, avoid_text) > 0:
        score -= 0.3
        reasons.append("avoid_when penalty")
    return max(score, 0.0), reasons or ["semantic metadata overlap"]


def recommended_variants(signals: dict[str, Any], family: dict[str, Any], page_count: int | None = None) -> list[str]:
    available = [str(item.get("variant_id")) for item in family.get("variants", []) if item.get("variant_id")]
    if not available:
        return []
    if signals["content_type"] == "internal_review":
        wanted = [
            "cover",
            "agenda",
            "context_overview",
            "metric_dashboard",
            "problem_analysis",
            "cause_analysis",
            "comparison",
            "case_evidence",
            "action_plan",
            "risk_dependency",
            "closing",
        ]
    elif signals["content_type"] == "cultural_event":
        wanted = ["cover", "section_divider", "context_overview", "case_evidence", "timeline", "closing"]
    else:
        wanted = ["cover", "agenda", "context_overview", "comparison", "action_plan", "closing"]
    variants = [variant for variant in wanted if variant in available]
    if page_count:
        while len(variants) < min(page_count, 6) and len(variants) < len(available):
            for candidate in available:
                if candidate not in variants:
                    variants.append(candidate)
                    break
    return variants


def select_components(semantic_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    component_by_type = {
        "title": "title_block",
        "agenda": "action_list",
        "metric": "metric_card",
        "kpi": "metric_card",
        "finding": "finding_callout",
        "evidence": "evidence_table",
        "comparison": "comparison_matrix",
        "action": "action_list",
        "risk": "risk_matrix",
        "timeline": "timeline",
        "process": "process_flow",
        "company": "image_panel",
        "product": "image_panel",
    }
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for block in semantic_blocks:
        block_id = str(block.get("block_id") or block.get("id") or "")
        component_id = component_by_type.get(str(block.get("type") or "").lower())
        if not block_id or not component_id:
            continue
        key = (component_id, block_id)
        if key in seen:
            continue
        seen.add(key)
        selected.append({"component_id": component_id, "binds": [block_id]})
    return selected


def choose_asset_strategy(semantic_block: dict[str, Any], data_available: bool = False) -> dict[str, Any]:
    text = normalize_text(semantic_block)
    block_type = str(semantic_block.get("type") or "").lower()
    if block_type in {"company", "product", "person", "brand", "case"} or COMPANY_PRODUCT_RE.search(text):
        return {
            "strategy_id": "real_image_required" if data_available else "identity_structured_fallback",
            "fallback_if_missing": "Render a structured identity panel with text badge and product/category labels. Do not leave empty image boxes.",
            "no_fake_data": True,
        }
    if block_type in {"metric", "kpi"} or QUANTIFIED_RE.search(text):
        if data_available and re.search(r"\d+|%", text):
            return {"strategy_id": "chart_when_quantified", "no_fake_data": True}
        return {
            "strategy_id": "structured_fallback",
            "fallback_if_missing": "Use a qualitative comparison table or unlabeled trend skeleton; do not fabricate numbers.",
            "no_fake_data": True,
        }
    return {
        "strategy_id": "structured_fallback",
        "fallback_if_missing": "Use native structured cards when a verifiable image or dataset is not available.",
        "no_fake_data": True,
    }


def semantic_blocks_for_variant(variant: str, page: int, query: str) -> list[dict[str, Any]]:
    title = {"block_id": f"title_{page}", "type": "title", "content": f"{variant} key message"}
    if variant == "cover":
        return [title, {"block_id": f"hero_finding_{page}", "type": "finding", "content": query}]
    if variant == "agenda":
        return [title, {"block_id": f"agenda_{page}", "type": "agenda", "content": "Key sections and decision flow"}]
    if variant == "metric_dashboard":
        return [
            title,
            {"block_id": f"metric_{page}", "type": "metric", "content": "Metric requires provided data"},
            {"block_id": f"kpi_{page}", "type": "kpi", "content": "KPI context without fabricated numbers"},
        ]
    if variant in {"comparison", "case_evidence"}:
        return [
            title,
            {"block_id": f"comparison_{page}", "type": "comparison", "content": "Compare entities, claims, and constraints"},
            {"block_id": f"company_{page}", "type": "company", "content": query},
            {"block_id": f"evidence_{page}", "type": "evidence", "content": "Evidence slot tied to source material"},
        ]
    if variant in {"problem_analysis", "cause_analysis", "context_overview"}:
        return [
            title,
            {"block_id": f"finding_{page}", "type": "finding", "content": f"{variant} finding"},
            {"block_id": f"evidence_{page}", "type": "evidence", "content": "Source-backed evidence table"},
        ]
    if variant == "action_plan":
        return [
            title,
            {"block_id": f"action_{page}", "type": "action", "content": "Owner, next action, and deadline"},
            {"block_id": f"process_{page}", "type": "process", "content": "Execution sequence"},
        ]
    if variant == "risk_dependency":
        return [
            title,
            {"block_id": f"risk_{page}", "type": "risk", "content": "Risk and dependency register"},
            {"block_id": f"action_{page}", "type": "action", "content": "Mitigation owner"},
        ]
    if variant == "timeline":
        return [title, {"block_id": f"timeline_{page}", "type": "timeline", "content": "Milestone sequence"}]
    return [title, {"block_id": f"finding_{page}", "type": "finding", "content": f"{variant} key message"}]


def match_templates(query: str, limit: int = 3, page_count: int | None = None, registry_path: Path = FAMILIES_PATH) -> dict[str, Any]:
    signals = query_signals(query)
    scored = []
    for family in load_families(registry_path):
        score, reasons = family_score(query, signals, family)
        scored.append((score, family, reasons))
    scored.sort(key=lambda item: item[0], reverse=True)
    matches = []
    for score, family, reasons in scored[:limit]:
        variants = recommended_variants(signals, family, page_count)
        matches.append(
            {
                "template_id": family.get("template_id"),
                "status": family.get("status"),
                "claim_level": family.get("claim_level"),
                "score": round(score, 4),
                "reasons": reasons,
                "recommended_variants": variants,
                "component_hints": family.get("component_candidates", [])[:6],
                "asset_strategy_hints": ["chart_when_quantified", "real_image_required", "structured_fallback"],
                "family_usage_policy_summary": family_usage_policy_summary(family),
                "cjk_policy_summary": cjk_policy_summary(family),
                "extension_grammar_summary": extension_grammar_summary(family),
                "benchmark_roles": benchmark_roles(family),
            }
        )
    return {"query_signals": signals, "matches": matches}


def plan_with_template_family(query: str, page_count: int = 10) -> dict[str, Any]:
    result = match_templates(query, limit=3, page_count=page_count)
    design_selection = svglide_recipe_selector.select_design_assets(query)
    preferred_template_id = None
    if design_selection.get("status") == "passed":
        preferred_template_id = (
            design_selection.get("template_family_selection", {}).get("selected_template_id")
            if isinstance(design_selection.get("template_family_selection"), dict)
            else None
        )
    selected_match = result["matches"][0]
    if preferred_template_id:
        selected_match = next(
            (match for match in result["matches"] if match.get("template_id") == preferred_template_id),
            selected_match,
        )
    selected = selected_match["template_id"]
    variants = selected_match["recommended_variants"]
    if not variants:
        variants = ["cover", "agenda", "context_overview", "comparison", "action_plan", "closing"]
    slides = []
    for index in range(page_count):
        variant = variants[index % len(variants)]
        blocks = semantic_blocks_for_variant(variant, index + 1, query)
        slides.append(
            {
                "page": index + 1,
                "template_family_id": selected,
                "template_variant": variant,
                "semantic_blocks": blocks,
                "component_selection": select_components(blocks),
                "asset_strategy": choose_asset_strategy(blocks[-1], data_available=False),
            }
        )
    plan = {
        "version": "beautiful-template-plan/v1",
        "target_slide_count": page_count,
        "template_family_selection": {
            "enabled": True,
            "source": "beautiful-html-template-families",
            "selected_template_id": selected,
            "candidate_template_ids": [item["template_id"] for item in result["matches"]],
            "selection_reason": "; ".join(selected_match["reasons"]),
            "claim_level": selected_match.get("claim_level"),
            "family_usage_policy_summary": selected_match.get("family_usage_policy_summary"),
            "cjk_policy_summary": selected_match.get("cjk_policy_summary"),
            "extension_grammar_summary": selected_match.get("extension_grammar_summary"),
            "benchmark_roles": selected_match.get("benchmark_roles"),
        },
        "slides": slides,
    }
    if design_selection.get("status") == "passed":
        for key in [
            "deck_recipe_selection",
            "style_pack_selection",
            "density_mode_selection",
            "component_variant_selection",
            "image_treatment_selection",
            "style_lock",
        ]:
            plan[key] = design_selection[key]
        plan["selection_metadata"] = design_selection
        plan["style_lock"]["template_family_id"] = selected
        plan["template_family_selection"]["recipe_selected_template_id"] = design_selection["template_family_selection"]["selected_template_id"]
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Match a user query to beautiful-html-template families.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--page-count", type=int, default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    result = match_templates(args.query, args.limit, args.page_count)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
