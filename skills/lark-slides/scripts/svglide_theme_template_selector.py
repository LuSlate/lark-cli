#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import svglide_brand_palette_resolver as brand_resolver
import beautiful_template_runtime
import svglide_palette_selector
import svglide_semantic_asset_matcher as semantic_matcher


SCHEMA_VERSION = "svglide-theme-template-selection/v1"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PALETTE_SELECTION_PATH = Path("02-plan/palette-selection.json")
PLAN_PATH = Path("02-plan/slide_plan.json")
SELECTION_PATH = Path("02-plan/theme-template-selection.json")
SELECTION_RECEIPT_PATH = Path("receipts/theme_template_selection.json")
PRODUCTION_ARCHITECTURE_TEMPLATE_IDS = {"architectural-spec"}
PROMOTED_TEMPLATE_REQUIRED_EVIDENCE = "template_token"
PROMOTED_TEMPLATE_FIELD_WEIGHTS = {
    "asset_id": 32,
    "content_shapes": 30,
    "audience_tags": 16,
    "tone_tags": 12,
    "industry_tags": 5,
    "visual_signature": 4,
    "best_for": 8,
}
PROMOTED_TEMPLATE_BOOST_CAP = 96
KEYWORD_TOKEN_RE = re.compile(r"[a-z0-9]+")
PROMOTED_TEMPLATE_STOPWORDS = {
    "about",
    "across",
    "also",
    "and",
    "anything",
    "brand",
    "business",
    "choice",
    "content",
    "deck",
    "decks",
    "feel",
    "for",
    "from",
    "good",
    "including",
    "instead",
    "moment",
    "rather",
    "review",
    "slide",
    "slides",
    "should",
    "that",
    "the",
    "this",
    "to",
    "wants",
    "with",
    "work",
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def normalize_brief(text: str) -> str:
    return semantic_matcher.normalize_text(text)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_seed(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def infer_brief_signals(brief: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    signals = semantic_matcher.infer_brief_signals(brief)
    entities = brand_resolver.extract_brand_entities(brief, evidence)
    if entities:
        signals["brand_entities"] = [entity["brand_id"] for entity in entities]
    if isinstance(evidence, dict) and isinstance(evidence.get("available_assets"), list):
        signals["available_assets"] = [str(item) for item in evidence["available_assets"] if str(item).strip()]
    return signals


def load_palette_selection(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / PALETTE_SELECTION_PATH)


def load_plan_if_present(project_root: Path) -> dict[str, Any]:
    path = project_root / PLAN_PATH
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def load_template_registry(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return beautiful_template_runtime.template_registry()


def load_theme_registry(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return beautiful_template_runtime.theme_registry()


def list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def keyword_tokens(value: Any) -> list[str]:
    return [
        token
        for token in KEYWORD_TOKEN_RE.findall(normalize_brief(str(value)))
        if len(token) >= 3 and token not in PROMOTED_TEMPLATE_STOPWORDS
    ]


def prompt_matches_metadata_term(prompt_norm: str, prompt_tokens: set[str], term: Any) -> bool:
    term_norm = normalize_brief(str(term))
    if not term_norm:
        return False
    if len(term_norm) >= 4 and term_norm in prompt_norm:
        return True
    tokens = keyword_tokens(term_norm)
    if not tokens:
        return False
    if len(tokens) == 1:
        return tokens[0] in prompt_tokens
    if len(tokens) <= 4 and all(token in prompt_tokens for token in tokens):
        return True
    return False


def is_promoted_template_record(template: dict[str, Any]) -> bool:
    gate = template.get("promotion_gate") if isinstance(template.get("promotion_gate"), dict) else {}
    evidence = gate.get("required_evidence") if isinstance(gate.get("required_evidence"), list) else []
    return PROMOTED_TEMPLATE_REQUIRED_EVIDENCE in {str(item) for item in evidence}


def promoted_template_semantic_boost(prompt_norm: str, template: dict[str, Any]) -> tuple[int, list[str]]:
    if not is_promoted_template_record(template):
        return 0, []
    metadata = template.get("selection_metadata") if isinstance(template.get("selection_metadata"), dict) else {}
    prompt_tokens = set(keyword_tokens(prompt_norm))
    matches: list[str] = []
    score = 0
    term_groups: list[tuple[str, list[str]]] = [
        ("asset_id", [str(template.get("id") or ""), str(template.get("source_template_id") or "")]),
    ]
    for field in ["content_shapes", "audience_tags", "tone_tags", "industry_tags", "visual_signature", "best_for"]:
        term_groups.append((field, list_value(metadata.get(field))))
    for field, terms in term_groups:
        weight = PROMOTED_TEMPLATE_FIELD_WEIGHTS[field]
        for term in terms:
            if not prompt_matches_metadata_term(prompt_norm, prompt_tokens, term):
                continue
            normalized = normalize_brief(term).replace(" ", "_")
            score += weight
            matches.append(f"promoted_template_semantic:{field}:{normalized}")
    if not matches:
        return 0, []
    return min(score, PROMOTED_TEMPLATE_BOOST_CAP), matches[:8]


def template_asset(template: dict[str, Any]) -> dict[str, Any]:
    metadata = template.get("selection_metadata") if isinstance(template.get("selection_metadata"), dict) else {}
    return {
        "id": template.get("id"),
        "name": template.get("id"),
        "occasion": list_value(metadata.get("occasion_tags")),
        "mood": list_value(metadata.get("tone_tags")),
        "tone": list_value(metadata.get("tone_tags")),
        "formality": metadata.get("formality"),
        "density": metadata.get("density"),
        "content_shapes": list_value(metadata.get("content_shapes")),
        "best_for": ", ".join(list_value(metadata.get("best_for"))),
        "avoid_for": ", ".join(list_value(metadata.get("avoid_for"))),
    }


def boost_template(
    scored: dict[str, Any],
    template_id: str,
    target_ids: set[str],
    *,
    weight: int,
    signal: str,
    penalty_ids: set[str] | None = None,
    penalty: int = 0,
) -> int:
    delta = 0
    if template_id in target_ids:
        delta += weight
        scored["matched_signals"].append(signal)
    if penalty_ids and template_id in penalty_ids:
        delta -= penalty
        scored["rejection_reasons"].append(f"template_mismatch:{signal}")
    return delta


def theme_asset(theme: dict[str, Any]) -> dict[str, Any]:
    metadata = theme.get("selection_metadata") if isinstance(theme.get("selection_metadata"), dict) else {}
    return {
        "id": theme.get("id"),
        "name": theme.get("id"),
        "occasion": [],
        "mood": list_value(metadata.get("mood_tags")),
        "tone": list_value(metadata.get("mood_tags")),
        "scheme": metadata.get("scheme"),
        "content_shapes": list_value(metadata.get("supported_template_ids")),
        "best_for": ", ".join(list_value(metadata.get("mood_tags")) + list_value(metadata.get("primary_color_bias"))),
        "avoid_for": "",
    }


def score_template(signals: dict[str, Any], template: dict[str, Any], *, brief: str = "") -> dict[str, Any]:
    prompt = brief or json.dumps(signals, ensure_ascii=False)
    scored = semantic_matcher.score_asset(prompt, template_asset(template))
    score = int(scored.get("score") or 0)
    metadata = template.get("selection_metadata") if isinstance(template.get("selection_metadata"), dict) else {}
    template_id = str(template.get("id") or "")
    content_shapes = set(list_value(signals.get("content_shape")))
    occasions = set(list_value(signals.get("occasion")))
    prompt_norm = normalize_brief(brief)
    architecture_intent = bool(
        {"technical architecture", "system design"}.intersection(occasions) or {"architecture", "nodes"}.intersection(content_shapes)
    )
    if template_id in {"executive-dashboard", "metric-dashboard", "trend-grid-report"} and "dashboard" in content_shapes:
        score += 6
        scored["matched_signals"].append("template_capability:dashboard")
    if "internal review" in occasions and "internal" in list_value(metadata.get("audience_tags")):
        score += 4
        scored["matched_signals"].append("audience:internal")
    if template_id in {"timeline-steps", "risk-alert", "process-flow"} and (
        "postmortem" in occasions or {"timeline", "root cause", "action plan"}.intersection(content_shapes)
    ):
        score += 12
        scored["matched_signals"].append("template_capability:postmortem")
    if template_id == "executive-dashboard" and "postmortem" in occasions:
        score -= 10
        scored["rejection_reasons"].append("template_mismatch:postmortem_not_dashboard")
    score += boost_template(
        scored,
        template_id,
        {"intelligence-brief", "ledger-briefing", "serif-stat-editorial"},
        weight=34,
        signal="scenario:postmortem",
        penalty_ids={"executive-dashboard", "metric-dashboard", "trend-grid-report"},
        penalty=30,
    ) if "postmortem" in occasions else 0
    score += boost_template(
        scored,
        template_id,
        {"comparison-cards", "brutalist-matrix", "intelligence-brief"},
        weight=34,
        signal="scenario:comparison",
        penalty_ids={"executive-dashboard", "metric-dashboard"},
        penalty=24,
    ) if "competitive analysis" in occasions or {"comparison matrix", "feature matrix", "versus"}.intersection(content_shapes) else 0
    if template_id in PRODUCTION_ARCHITECTURE_TEMPLATE_IDS and architecture_intent:
        score += 14
        scored["matched_signals"].append("template_capability:architecture")
    if template_id == "risk-alert" and {"technical architecture", "system design"}.intersection(occasions):
        score -= 8
        scored["rejection_reasons"].append("template_mismatch:architecture_not_risk")
    score += boost_template(
        scored,
        template_id,
        PRODUCTION_ARCHITECTURE_TEMPLATE_IDS,
        weight=34,
        signal="scenario:architecture",
        penalty_ids={"executive-dashboard", "metric-dashboard"},
        penalty=28,
    ) if architecture_intent else 0
    score += boost_template(
        scored,
        template_id,
        {"poster-stat-punch", "product-ribbon", "cover-hero"},
        weight=34,
        signal="scenario:product_launch",
        penalty_ids={"brutalist-matrix", "dense-panel-grid"},
        penalty=24,
    ) if "product launch" in occasions or "brand deck" in occasions else 0
    score += boost_template(
        scored,
        template_id,
        {"research-poster", "printed-program"},
        weight=32,
        signal="scenario:research_poster",
    ) if "research" in prompt_norm or "学术" in prompt_norm or "会议研究" in prompt_norm else 0
    score += boost_template(
        scored,
        template_id,
        {"agenda-list", "printed-program", "annotated-field-board"},
        weight=30,
        signal="scenario:workshop",
    ) if "workshop" in prompt_norm or "onboarding" in prompt_norm or "议程" in prompt_norm else 0
    score += boost_template(
        scored,
        template_id,
        {"dense-panel-grid", "ledger-briefing", "trend-grid-report"},
        weight=34,
        signal="scenario:roadmap",
        penalty_ids={"architecture-blueprint", "architectural-spec", "executive-dashboard"},
        penalty=18,
    ) if "roadmap" in prompt_norm or "路线图" in prompt_norm or "swimlane" in prompt_norm or "里程碑" in prompt_norm else 0
    score += boost_template(
        scored,
        template_id,
        {"risk-alert", "intelligence-brief"},
        weight=34,
        signal="scenario:risk_security",
        penalty_ids={"executive-dashboard", "metric-dashboard"},
        penalty=24,
    ) if not architecture_intent and ("security review" in occasions or "风险" in prompt_norm or "合规" in prompt_norm or "审计" in prompt_norm) else 0
    if template_id in {"trend-grid-report", "dense-panel-grid", "intelligence-brief"} and (
        "market analysis" in occasions or {"market map", "trend", "bar ranking"}.intersection(content_shapes)
    ):
        score += 10
        scored["matched_signals"].append("template_capability:market_landscape")
    if template_id == "executive-dashboard" and "market map" in content_shapes and "dashboard" not in content_shapes:
        score -= 8
        scored["rejection_reasons"].append("template_mismatch:market_landscape_not_dashboard")
    if template_id == "image-feature" and (
        {"image story", "evidence cards"}.intersection(content_shapes) or any(token in prompt_norm for token in ("大图", "图片", "配图", "image"))
    ):
        score += 14
        scored["matched_signals"].append("template_capability:image_feature")
    score += boost_template(
        scored,
        template_id,
        {"image-feature", "editorial-quote-chart", "quote-focus"},
        weight=30,
        signal="scenario:image_story",
        penalty_ids={"annotated-field-board"},
        penalty=12,
    ) if any(token in prompt_norm for token in ("客户案例", "quote", "大图", "图片", "品牌图文", "image")) else 0
    score += boost_template(
        scored,
        template_id,
        {"dense-panel-grid", "printed-program", "ledger-briefing"},
        weight=34,
        signal="scenario:dense_table",
        penalty_ids={"intelligence-brief", "executive-dashboard"},
        penalty=18,
    ) if any(token in prompt_norm for token in ("高密度", "排期表", "多个项目", "负责人", "long table")) else 0
    if template_id == "quote-focus" and any(token in prompt_norm for token in ("大图", "图片", "配图", "image report")):
        score -= 8
        scored["rejection_reasons"].append("template_mismatch:image_report_not_quote_only")
    if template_id in {"ledger-briefing", "intelligence-brief", "serif-stat-editorial"} and (
        {"summary", "decision review"}.intersection(occasions) or "takeaways" in content_shapes or any(token in prompt_norm for token in ("最后一页", "总结页", "closing", "takeaways"))
    ):
        score += 18
        scored["matched_signals"].append("template_capability:closing_summary")
    if template_id in {"process-flow", "roadmap-lanes"} and "summary" in occasions:
        score -= 8
        scored["rejection_reasons"].append("template_mismatch:summary_not_process")
    promoted_boost, promoted_matches = promoted_template_semantic_boost(prompt_norm, template)
    if promoted_boost:
        score += promoted_boost
        scored["matched_signals"].extend(promoted_matches)
    required_assets = list_value(metadata.get("required_assets"))
    available_assets = set(list_value(signals.get("available_assets")))
    missing_assets = [item for item in required_assets if item not in available_assets]
    if missing_assets:
        score -= 40 * len(missing_assets)
        for asset in missing_assets:
            scored["rejection_reasons"].append(f"asset_slot_missing:{asset}")
        scored["asset_slot_satisfied"] = "missing"
    else:
        scored["asset_slot_satisfied"] = "satisfied"
    fidelity_gate = template.get("fidelity_gate") if isinstance(template.get("fidelity_gate"), dict) else {}
    if template.get("renderer_executable") is True and fidelity_gate.get("status") == "passed" and isinstance(template.get("visual_contract"), dict):
        score += 10
        scored["matched_signals"].append("runtime_contract:executable_fidelity")
    supported_page_types = list_value(template.get("supported_page_types"))
    scored["page_type_support"] = "supported" if supported_page_types else "unknown"
    if isinstance(fidelity_gate.get("score"), (int, float)):
        scored["fidelity_score"] = fidelity_gate.get("score")
    scored["score"] = score
    scored["template_id"] = template_id
    for key in [
        "asset_status",
        "source_template_id",
        "claim_level",
        "quality_tier",
        "default_selectable",
        "selection_scope",
        "renderer_module",
        "renderer_executable",
        "supported_page_types",
        "visual_contract",
        "fidelity_gate",
        "fidelity_receipt",
        "golden_spec",
        "promotion_gate",
        "source_trace",
        "supported_theme_ids",
        "family_usage_policy_summary",
        "cjk_policy_summary",
        "extension_grammar_summary",
        "benchmark_roles",
    ]:
        if template.get(key) not in (None, "", [], {}):
            scored[key] = template.get(key)
    scored["selection_reason"] = list(scored.get("matched_signals", []))[:6]
    return scored


def selected_palette_mode(palette_selection: dict[str, Any]) -> str | None:
    project_palette = palette_selection.get("project_palette") if isinstance(palette_selection.get("project_palette"), dict) else {}
    colors = project_palette.get("colors") if isinstance(project_palette.get("colors"), dict) else {}
    background = str(colors.get("background") or "")
    if background.startswith("#00") or background.upper() in {"#000000", "#08122D", "#0F172A", "#111111"}:
        return "dark"
    if background.startswith("#"):
        return "light"
    selected = palette_selection.get("selected_palette_id")
    for palette in palette_selection.get("palette_candidates", []):
        if isinstance(palette, dict) and palette.get("palette_id") == selected:
            raw = palette.get("mode")
            return raw if isinstance(raw, str) else None
    return None


def score_theme(
    signals: dict[str, Any],
    theme: dict[str, Any],
    selected_template_ids: list[str],
    palette_selection: dict[str, Any],
    *,
    brief: str = "",
) -> dict[str, Any]:
    prompt = brief or json.dumps(signals, ensure_ascii=False)
    scored = semantic_matcher.score_asset(prompt, theme_asset(theme))
    score = int(scored.get("score") or 0)
    metadata = theme.get("selection_metadata") if isinstance(theme.get("selection_metadata"), dict) else {}
    supported = set(list_value(metadata.get("supported_template_ids")))
    if supported.intersection(selected_template_ids):
        score += 5
        scored["matched_signals"].append("template_support")
    palette_mode = selected_palette_mode(palette_selection)
    theme_scheme = metadata.get("scheme")
    if palette_mode and theme_scheme:
        if theme_scheme in {palette_mode, "mixed"}:
            score += 8
            scored["matched_signals"].append(f"palette_scheme:{palette_mode}")
        else:
            score -= 8
            scored["rejection_reasons"].append("palette_scheme_mismatch")
    brand_resolution = palette_selection.get("brand_resolution") if isinstance(palette_selection.get("brand_resolution"), dict) else {}
    brands = [str(item) for item in brand_resolution.get("brands", []) if isinstance(item, str)]
    affinity = set(list_value(metadata.get("brand_affinity")))
    theme_id = str(theme.get("id") or "")
    if brands and affinity.intersection(brands):
        score += 8
        scored["matched_signals"].append("brand_affinity")
    if brands and {"zhipu", "minimax"}.intersection(brands):
        if theme_id in {"blueprint-technical", "cobalt-grid", "glass-neon", "magazine-cobalt"}:
            score += 14
            scored["matched_signals"].append("brand_context:ai_tech")
        if theme_id in {"acid-studio", "tomato-poster", "sakura-catalog"}:
            score -= 8
            scored["rejection_reasons"].append("brand_context_mismatch:ai_tech")
    if brands and metadata.get("token_override_policy") == "forbidden":
        score -= 10
        scored["rejection_reasons"].append("token_override_policy_forbidden")
    scored["score"] = score
    scored["theme_id"] = theme_id
    scored["selection_reason"] = list(scored.get("matched_signals", []))[:6]
    return scored


def confidence_from_scores(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "low"
    top = int(candidates[0].get("score") or 0)
    second = int(candidates[1].get("score") or 0) if len(candidates) > 1 else 0
    if top >= 24 and top - second >= 5:
        return "high"
    if top >= 15 and not candidates[0].get("hard_rejection"):
        return "medium"
    return "low"


def deterministic_fallback(signals: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    seed = stable_seed({"signals": signals, "candidate_ids": [item.get("id") or item.get("template_id") or item.get("theme_id") for item in candidates]})
    ranked = sorted(candidates, key=lambda item: (stable_seed({"seed": seed, "id": item.get("id") or item.get("template_id") or item.get("theme_id")}), str(item.get("id") or item.get("template_id") or item.get("theme_id"))))
    return {"fallback_seed": seed, "candidate": ranked[0] if ranked else None}


def declared_canvas_ids(plan: dict[str, Any], key: str) -> list[str]:
    ids: list[str] = []
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        spec = slide.get("canvas_spec") if isinstance(slide.get("canvas_spec"), dict) else {}
        value = spec.get(key) or slide.get(key)
        if isinstance(value, str) and value and value not in ids:
            ids.append(value)
    if key == "theme_id":
        project_theme = plan.get("project_theme") if isinstance(plan.get("project_theme"), dict) else {}
        value = project_theme.get("base_theme_id")
        if isinstance(value, str) and value and value not in ids:
            ids.append(value)
    return ids


def include_declared_candidates(candidates: list[dict[str, Any]], *, declared_ids: list[str], id_key: str, top_k: int) -> list[dict[str, Any]]:
    selected = [dict(item) for item in candidates[:top_k]]
    selected_ids = {str(item.get(id_key) or item.get("id")) for item in selected}
    by_id = {str(item.get(id_key) or item.get("id")): item for item in candidates if item.get(id_key) or item.get("id")}
    for declared_id in declared_ids:
        if declared_id in selected_ids:
            continue
        candidate = by_id.get(declared_id)
        if not isinstance(candidate, dict):
            continue
        enriched = dict(candidate)
        matched = list(enriched.get("matched_signals") if isinstance(enriched.get("matched_signals"), list) else [])
        if "plan_declared" not in matched:
            matched.append("plan_declared")
        enriched["matched_signals"] = matched
        reason = list(enriched.get("selection_reason") if isinstance(enriched.get("selection_reason"), list) else [])
        if "plan_declared" not in reason:
            reason.append("plan_declared")
        enriched["selection_reason"] = reason[:6]
        selected.append(enriched)
        selected_ids.add(declared_id)
    return selected


def theme_candidates_for_selected_template(themes: list[dict[str, Any]], selected_template: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(selected_template, dict):
        return themes
    allowed_theme_ids = set(list_value(selected_template.get("supported_theme_ids")))
    if not allowed_theme_ids:
        return themes
    constrained = [
        theme
        for theme in themes
        if str(theme.get("theme_id") or theme.get("id") or "") in allowed_theme_ids
    ]
    return constrained or themes


def select_theme_template(project_root: Path, brief: str, *, top_k: int = 5, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    palette_selection = load_palette_selection(project_root)
    plan = load_plan_if_present(project_root)
    signals = infer_brief_signals(brief, evidence)
    templates = [item for item in load_template_registry().get("templates", []) if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)]
    themes = [item for item in load_theme_registry().get("themes", []) if isinstance(item, dict) and beautiful_template_runtime.is_runtime_selectable(item)]

    template_candidates = [score_template(signals, item, brief=brief) for item in templates]
    template_candidates.sort(key=lambda item: (-int(item.get("score") or 0), str(item.get("template_id") or item.get("id"))))
    selected_template = template_candidates[0] if template_candidates else None
    selected_template_ids = [str(selected_template.get("template_id") or selected_template.get("id"))] if isinstance(selected_template, dict) else []

    constrained_themes = theme_candidates_for_selected_template(themes, selected_template)
    theme_candidates = [score_theme(signals, item, selected_template_ids, palette_selection, brief=brief) for item in constrained_themes]
    theme_candidates.sort(key=lambda item: (-int(item.get("score") or 0), str(item.get("theme_id") or item.get("id"))))

    template_confidence = confidence_from_scores(template_candidates)
    theme_confidence = confidence_from_scores(theme_candidates)
    confidence = "low" if "low" in {template_confidence, theme_confidence} else ("medium" if "medium" in {template_confidence, theme_confidence} else "high")
    fallback_policy = "not_used"
    fallback_seed = stable_seed({"brief": brief, "signals": signals, "palette": palette_selection.get("selected_palette_id")})
    if confidence == "low":
        fallback_policy = "deterministic_ranked_fallback"
    template_candidates_out = include_declared_candidates(
        template_candidates,
        declared_ids=declared_canvas_ids(plan, "template_id"),
        id_key="template_id",
        top_k=top_k,
    )
    theme_candidates_out = include_declared_candidates(
        theme_candidates,
        declared_ids=declared_canvas_ids(plan, "theme_id"),
        id_key="theme_id",
        top_k=top_k,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "theme_template_selection",
        "created_at": now_iso(),
        "palette_selection_ref": PALETTE_SELECTION_PATH.as_posix(),
        "selected_palette_id": palette_selection.get("selected_palette_id"),
        "brief_signals": signals,
        "template_candidates": template_candidates_out,
        "theme_candidates": theme_candidates_out,
        "selected_template_id": template_candidates[0].get("template_id") if template_candidates else None,
        "selected_theme_id": theme_candidates[0].get("theme_id") if theme_candidates else None,
        "confidence": confidence,
        "template_confidence": template_confidence,
        "theme_confidence": theme_confidence,
        "fallback_policy": fallback_policy,
        "deterministic_seed": fallback_seed,
        "brand_resolution": palette_selection.get("brand_resolution"),
    }


def write_selection(project_root: Path, selection: dict[str, Any]) -> Path:
    output = project_root / SELECTION_PATH
    write_json(output, selection)
    write_json(project_root / SELECTION_RECEIPT_PATH, selection)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select deterministic SVGlide template/theme candidates.")
    parser.add_argument("project_root")
    parser.add_argument("--brief")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    brief = svglide_palette_selector.project_brief(project_root, args.brief)
    selection = select_theme_template(project_root, brief, top_k=args.top_k)
    write_selection(project_root, selection)
    print(json.dumps(selection, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
