#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema
import beautiful_template_runtime


PLAN_PATH = Path("02-plan/slide_plan.json")
OUTPUT_PATH = Path("02-plan/strategy-review.json")
ALLOWED_PAGE_TYPES = {"cover", "section", "content", "closing"}
DEFAULT_FULL_DECK_MIN_SLIDES = 10
SAMPLE_DECK_INTENTS = {"sample", "quick_preview", "single_page", "one_page", "fixture", "smoke", "test"}
DEFAULT_RENDERERS = {
    "cover",
    "cover_full_bleed",
    "chart",
    "dashboard_scorecard",
    "timeline",
    "timeline_rail",
    "closing",
    "closing_cta",
    "test-renderer",
}
THEME_ARCHETYPE_KEYWORDS = {
    "company_ecosystem": ["字节", "bytedance", "公司", "企业", "产品矩阵", "生态"],
    "space_capital_market": ["spacex", "space x", "上市", "ipo", "资本", "估值", "火箭", "星链"],
    "volcanic_research_lab": ["冰岛", "火山", "地震", "岩浆", "形变", "volcano", "seismic", "iceland"],
    "alpine_coast_travel_board": ["新西兰", "高山", "湖泊", "海岸", "new zealand", "alpine", "coast"],
    "travel_destination": ["桂林", "山水", "旅游", "旅行", "目的地", "景区", "城市"],
    "academic_paper": ["论文", "paper", "研究", "attention", "transformer", "机制"],
}


class StrategyReviewError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StrategyReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StrategyReviewError(f"invalid JSON in {path}: expected object")
    return payload


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path is not None:
        payload["path"] = path
    return payload


def require_chinese(value: Any, code: str, message: str, *, page: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(value, str) or not value.strip() or not any("\u3400" <= char <= "\u9fff" for char in value):
        return [issue(code, message, page=page)]
    return []


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def first_positive_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and value > 0:
            return value
    return None


def collect_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        if value.strip():
            strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(collect_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(collect_strings(item))
    return strings


def plan_deck_intent(plan: dict[str, Any]) -> str:
    raw = plan.get("deck_intent") or plan.get("generation_intent") or plan.get("intent")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return "full_deck"


def is_sample_deck(plan: dict[str, Any]) -> bool:
    intent = plan_deck_intent(plan)
    if intent in SAMPLE_DECK_INTENTS:
        return True
    target = first_positive_int(plan.get("target_slide_count"), plan.get("page_count"))
    return target == 1


def text_haystack(values: Any) -> str:
    return " ".join(collect_strings(values)).lower()


def contains_any(haystack: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in haystack for keyword in keywords)


def validate_full_deck_strategy(plan: dict[str, Any], slides: list[Any], deck_structure: list[str]) -> list[dict[str, Any]]:
    if is_sample_deck(plan):
        return []

    issues: list[dict[str, Any]] = []
    slide_count = len([slide for slide in slides if isinstance(slide, dict)])
    target_count = first_positive_int(plan.get("target_slide_count"), plan.get("page_count"))
    required_count = max(DEFAULT_FULL_DECK_MIN_SLIDES, target_count or DEFAULT_FULL_DECK_MIN_SLIDES)
    content_count = sum(1 for slide in slides if isinstance(slide, dict) and slide.get("page_type") == "content")
    page_types = [slide.get("page_type") for slide in slides if isinstance(slide, dict)]

    if target_count is None:
        issues.append(
            issue(
                "full_deck_target_slide_count_missing",
                "full deck plans must declare target_slide_count or page_count; default user decks should target 10 slides",
                path="$.target_slide_count",
            )
        )
    elif target_count < DEFAULT_FULL_DECK_MIN_SLIDES:
        issues.append(
            issue(
                "full_deck_target_slide_count_too_low",
                f"full deck target_slide_count/page_count must be at least {DEFAULT_FULL_DECK_MIN_SLIDES}; use deck_intent=sample for short samples",
                path="$.target_slide_count",
            )
        )
    if slide_count < required_count:
        issues.append(
            issue(
                "full_deck_slide_count_too_low",
                f"full deck requires at least {required_count} slides; use deck_intent=sample for a short preview",
                path="$.slides",
            )
        )
    if page_types == ["cover", "content", "content", "closing"]:
        issues.append(
            issue(
                "full_deck_minimal_sample_structure",
                "cover + two content pages + closing is a sample structure, not a complete presentation",
                path="$.slides",
            )
        )
    if content_count < 6:
        issues.append(
            issue(
                "full_deck_content_pages_too_few",
                "full deck plans need at least 6 content pages to support a complete narrative",
                path="$.slides",
            )
        )
    if "cover" not in deck_structure or "content" not in deck_structure or "closing" not in deck_structure:
        issues.append(issue("full_deck_structure_incomplete", "full deck deck_structure must include cover, content, and closing"))

    haystack = text_haystack({"slides": slides, "deck_structure": deck_structure, "title": plan.get("title"), "topic": plan.get("topic")})
    required_signals = [
        ("full_deck_missing_core_conclusion", ["核心结论", "关键结论", "结论先行", "executive summary", "insight", "洞察"]),
        ("full_deck_missing_positioning", ["定位", "背景", "公司", "格局", "context", "positioning"]),
        ("full_deck_missing_comparison", ["对比", "比较", "差异", "矩阵", "comparison", "matrix"]),
        ("full_deck_missing_risk_or_next_steps", ["风险", "治理", "合规", "安全", "后续", "观察", "next"]),
    ]
    for code, keywords in required_signals:
        if not contains_any(haystack, keywords):
            issues.append(issue(code, f"full deck narrative is missing signal: {', '.join(keywords[:3])}"))
    return issues


def infer_theme_archetype(plan: dict[str, Any]) -> str | None:
    haystack = " ".join(collect_strings({key: plan.get(key) for key in ["title", "topic", "scenario", "audience", "business_claims"]}))
    slides = plan.get("slides")
    if isinstance(slides, list):
        haystack += " " + " ".join(collect_strings(slides))
    lowered = haystack.lower()
    for archetype, keywords in THEME_ARCHETYPE_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return archetype
    return None


def style_presets_by_id() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for theme in beautiful_template_runtime.theme_registry().get("themes", []):
        if not isinstance(theme, dict):
            continue
        theme_id = theme.get("id")
        if isinstance(theme_id, str) and theme_id:
            result[theme_id] = {"style_id": theme_id, "palette": theme.get("colors") if isinstance(theme.get("colors"), dict) else {}}
    return result


def normalize_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if len(raw) == 4 and raw.startswith("#"):
        return "#" + "".join(ch * 2 for ch in raw[1:])
    if len(raw) == 7 and raw.startswith("#"):
        return raw
    return None


def color_luminance(color: str) -> float:
    r = int(color[1:3], 16) / 255
    g = int(color[3:5], 16) / 255
    b = int(color[5:7], 16) / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def style_background_is_dark(style_preset: str | None) -> bool | None:
    if not style_preset:
        return None
    preset = style_presets_by_id().get(style_preset)
    if not preset:
        return None
    palette = preset.get("palette") if isinstance(preset.get("palette"), dict) else {}
    bg = normalize_color(palette.get("background"))
    return color_luminance(bg) < 0.42 if bg else None


def design_palette_intent(design_dna: dict[str, Any]) -> str:
    raw = design_dna.get("palette_intent") or design_dna.get("palette") or design_dna.get("color_intent")
    return " ".join(collect_strings(raw)).lower()


def visual_anchors(visual_identity: dict[str, Any], design_dna: dict[str, Any]) -> list[str]:
    for key in ["theme_visual_anchors", "visual_anchors", "subject_visual_anchors"]:
        anchors = list_of_strings(visual_identity.get(key))
        if anchors:
            return anchors
    for key in ["theme_visual_anchors", "visual_anchors", "subject_visual_anchors"]:
        anchors = list_of_strings(design_dna.get(key))
        if anchors:
            return anchors
    return []


def validate_visual_identity(plan: dict[str, Any], slides: list[Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    visual_identity = plan.get("visual_identity")
    if not isinstance(visual_identity, dict):
        return [issue("visual_identity_missing", "slide_plan.visual_identity is required")]
    theme_archetype = visual_identity.get("theme_archetype")
    if not isinstance(theme_archetype, str) or not theme_archetype.strip():
        issues.append(issue("visual_identity_theme_missing", "visual_identity.theme_archetype is required"))
    inferred = infer_theme_archetype(plan)
    if inferred and theme_archetype and theme_archetype != inferred:
        issues.append(
            issue(
                "visual_identity_theme_mismatch",
                f"visual_identity.theme_archetype {theme_archetype!r} does not match inferred theme {inferred!r}",
            )
        )

    design_dna = visual_identity.get("design_dna")
    if not isinstance(design_dna, dict):
        issues.append(issue("visual_identity_design_dna_missing", "visual_identity.design_dna is required"))
        design_dna = {}
    for field in ["palette", "layout_motif", "shape_language", "image_treatment", "component_bias"]:
        if not collect_strings(design_dna.get(field)):
            issues.append(issue(f"visual_identity_design_dna_missing_{field}", f"visual_identity.design_dna.{field} is required"))
    if len(visual_anchors(visual_identity, design_dna)) < 3:
        issues.append(issue("visual_identity_anchors_too_few", "visual_identity must include at least 3 theme-specific visual anchors"))
    if not isinstance(visual_identity.get("forbidden_reuse"), (dict, list)):
        issues.append(issue("visual_identity_forbidden_reuse_missing", "visual_identity.forbidden_reuse is required"))
    if not isinstance(visual_identity.get("distinctness_target"), dict):
        issues.append(issue("visual_identity_distinctness_target_missing", "visual_identity.distinctness_target is required"))

    palette_intent = design_palette_intent(design_dna)
    selected_theme = plan.get("project_theme") or plan.get("theme_id") or plan.get("style_preset")
    background_dark = style_background_is_dark(selected_theme if isinstance(selected_theme, str) else None)
    if background_dark is not None:
        wants_light = any(token in palette_intent for token in ["light", "white", "bright", "浅", "白", "明亮"])
        wants_dark = any(token in palette_intent for token in ["dark", "black", "deep", "深", "黑"])
        if wants_light and background_dark:
            issues.append(issue("visual_identity_style_palette_conflict", "style_preset is dark but visual_identity requests a light palette"))
        if wants_dark and not background_dark:
            issues.append(issue("visual_identity_style_palette_conflict", "style_preset is light but visual_identity requests a dark palette"))

    renderer_ids = [slide.get("renderer_id") for slide in slides if isinstance(slide, dict) and isinstance(slide.get("renderer_id"), str)]
    content_renderers = [
        slide.get("renderer_id")
        for slide in slides
        if isinstance(slide, dict) and slide.get("page_type") == "content" and isinstance(slide.get("renderer_id"), str)
    ]
    if renderer_ids and all(renderer_id in DEFAULT_RENDERERS for renderer_id in renderer_ids):
        issues.append(issue("visual_identity_renderer_default_only", "renderer_id sequence uses only generic default renderers"))
    if len(set(content_renderers)) <= 1 and len(content_renderers) >= 3:
        issues.append(issue("visual_identity_content_renderer_monoculture", "content pages need more than one renderer family for theme-specific structure"))
    return issues


def run_strategy_review(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan_path = project / PLAN_PATH
    if not plan_path.exists():
        raise StrategyReviewError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_path)
    issues: list[dict[str, Any]] = []

    if plan.get("language") != "zh-CN":
        issues.append(issue("language_not_zh_cn", "slide_plan.language must be zh-CN"))
    if not isinstance(plan.get("audience"), str) or not plan.get("audience", "").strip():
        issues.append(issue("audience_missing", "slide_plan.audience must be a non-empty string"))
    deck_structure = plan.get("deck_structure")
    if not isinstance(deck_structure, list) or not all(isinstance(item, str) for item in deck_structure):
        issues.append(issue("deck_structure_missing", "slide_plan.deck_structure must be a string array"))
        deck_structure = []
    else:
        for page_type in sorted({"cover", "content", "closing"} - set(deck_structure)):
            issues.append(issue("deck_structure_missing_page_type", f"deck_structure must include {page_type}"))

    slides = plan.get("slides")
    slide_receipts: list[dict[str, Any]] = []
    if not isinstance(slides, list) or not slides:
        issues.append(issue("slides_missing", "slide_plan.slides must be a non-empty array"))
        slides = []
    issues.extend(validate_full_deck_strategy(plan, slides, deck_structure))
    issues.extend(validate_visual_identity(plan, slides))
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict):
            issues.append(issue("slide_not_object", "slide item must be an object", page=index))
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        page_type = raw_slide.get("page_type")
        body_points = list_of_strings(raw_slide.get("body_points") or raw_slide.get("bullets"))
        source_refs = list_of_strings(raw_slide.get("source_refs") or raw_slide.get("sources"))
        if page_type not in ALLOWED_PAGE_TYPES:
            issues.append(issue("slide_page_type_missing", "slide.page_type must be cover, section, content, or closing", page=page))
        if not isinstance(raw_slide.get("section"), str) or not raw_slide.get("section", "").strip():
            issues.append(issue("slide_section_missing", "slide.section must be a non-empty string", page=page))
        if not isinstance(raw_slide.get("role"), str) or not raw_slide.get("role", "").strip():
            issues.append(issue("slide_role_missing", "slide.role must be a non-empty string", page=page))
        issues.extend(require_chinese(raw_slide.get("title"), "slide_title_not_chinese", "slide.title must be Chinese text", page=page))
        issues.extend(require_chinese(raw_slide.get("key_message"), "slide_key_message_not_chinese", "slide.key_message must be Chinese text", page=page))
        if page_type == "content":
            if len(body_points) < 2:
                issues.append(issue("content_body_points_too_few", "content slides require at least 2 body_points", page=page))
            if not source_refs:
                issues.append(issue("content_source_refs_missing", "content slides require source_refs", page=page))
        slide_receipts.append(
            {
                "page": page,
                "page_type": page_type,
                "section": raw_slide.get("section"),
                "role": raw_slide.get("role"),
                "title": raw_slide.get("title"),
                "key_message": raw_slide.get("key_message"),
                "body_points": body_points,
                "source_refs": source_refs,
            }
        )

    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-strategy-review/v1",
        "status": status,
        "language": plan.get("language"),
        "audience": plan.get("audience"),
        "deck_structure": deck_structure,
        "deck_intent": plan_deck_intent(plan),
        "target_slide_count": first_positive_int(plan.get("target_slide_count"), plan.get("page_count")),
        "slides": slide_receipts,
        "summary": {"error_count": len(issues), "warning_count": 0, "slide_count": len(slide_receipts)},
        "issues": issues,
        "generated_at": now_iso(),
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-strategy-review.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["issues"].extend(issue(item["code"], item["message"], path=item["path"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])

    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SVGlide strategy fields before confirmation and generation.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_strategy_review(Path(args.project))
    except (OSError, StrategyReviewError) as error:
        print(f"svglide_strategy_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
