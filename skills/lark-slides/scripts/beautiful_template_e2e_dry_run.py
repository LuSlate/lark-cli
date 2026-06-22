#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any

import beautiful_template_matcher
import svg_preflight


SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = SCRIPT_DIR.parent / "references"
DEFAULT_OUT_DIR = REFERENCES_DIR / "examples" / "beautiful-template-dry-runs"

RECIPES = [
    ("hero_typography", "hero", ["typography", "geometric_shape"], ["typography"]),
    ("icon_capability_map", "capability_map", ["icon", "geometric_shape"], ["typography"]),
    ("infographic_scorecard", "scorecard", ["typography", "micro_chart"], ["typography", "chart_geometry"]),
    ("fake_ui_dashboard", "dashboard", ["dashboard", "micro_chart"], ["chart_geometry"]),
    ("gradient_depth", "depth", ["gradient", "geometric_shape"], ["gradient", "typography"]),
    ("spotlight_annotation", "annotation", ["spotlight", "annotation"], ["typography"]),
    ("brand_system", "brand", ["typography", "geometric_shape"], ["typography"]),
]


def style_plan_fields(case_id: str) -> dict[str, Any]:
    return {
        "output_mode": "svglide-svg",
        "plan_path": f".lark-slides/plan/{case_id}/slide_plan.json",
        "loaded_rule_set": sorted(svg_preflight.SVG_PRIVATE_REQUIRED_RULE_FILES),
        "quality_gates": {
            "no_text_overflow": True,
            "no_debug_guides": True,
            "no_xml_like_pages": True,
        },
        "art_direction": {
            "cover_treatment": "template-family cover with one dominant structured visual block",
            "section_divider_treatment": "template-family section rhythm when section pages exist",
            "closing_treatment": "closing summary mirrors the selected family motif",
            "deck_motif": "beautiful-html-template family translated into native SVG structure",
            "svg_native_moments": ["cover structure", "comparison grid", "closing motif"],
        },
    }


def svg_text(element_id: str, text: str, x: int, y: int, width: int, height: int, size: int = 24) -> str:
    return (
        f'<foreignObject id="{element_id}" slide:role="shape" slide:shape-type="text" '
        f'x="{x}" y="{y}" width="{width}" height="{height}">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="font-size:{size}px;font-weight:800;font-family:Arial;color:#111827;line-height:1.16;">'
        f"{escape(text)}</div></foreignObject>"
    )


def svg_for_recipe(recipe: str, page: int, title: str, include_image: bool = False) -> str:
    body = [
        '<rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#F5F5F5" />',
        svg_text(f"title-{page}", title, 64, 44, 620, 90, 44),
    ]
    if recipe == "hero_typography":
        body.append('<rect id="hero-panel" slide:role="shape" x="64" y="150" width="520" height="230" fill="#ffffff" stroke="#111827" />')
    elif recipe == "icon_capability_map":
        for index in range(6):
            x = 96 + (index % 3) * 170
            y = 160 + (index // 3) * 110
            body.append(f'<circle id="capability-glyph-{index}" slide:role="shape" cx="{x}" cy="{y}" r="22" fill="#2563EB" />')
    elif recipe == "infographic_scorecard":
        for index, width in enumerate([180, 140, 210, 120], 1):
            y = 170 + index * 44
            body.append(f'<rect id="metric-bar-{index}" slide:role="shape" x="120" y="{y}" width="{width}" height="18" fill="#2563EB" />')
        body.append(svg_text(f"metric-label-{page}", "metric structure", 120, 150, 260, 34, 18))
    elif recipe == "fake_ui_dashboard":
        for index in range(4):
            x = 80 + index * 205
            body.append(f'<rect id="dashboard-card-{index}" slide:role="shape" x="{x}" y="150" width="170" height="110" fill="#ffffff" stroke="#CBD5E1" />')
            body.append(f'<rect id="dashboard-bar-{index}" slide:role="shape" x="{x + 18}" y="230" width="{90 + index * 12}" height="16" fill="#2563EB" />')
    elif recipe == "gradient_depth":
        body.insert(0, '<defs><linearGradient id="depth-gradient" x1="0" x2="1"><stop offset="0%" stop-color="#2563EB"/><stop offset="100%" stop-color="#F2D4CF"/></linearGradient></defs>')
        body.append('<rect id="gradient-slab" slide:role="shape" x="90" y="150" width="740" height="230" fill="url(#depth-gradient)" />')
    elif recipe == "spotlight_annotation":
        body.append('<rect id="spotlight-focus-panel" slide:role="shape" x="96" y="158" width="360" height="180" fill="#ffffff" stroke="#2563EB" />')
        body.append(svg_text(f"annotation-label-{page}", "annotation focus", 520, 200, 260, 58, 22))
    elif recipe == "brand_system":
        body.append('<rect id="brand-system-panel" slide:role="shape" x="90" y="150" width="740" height="230" fill="#ffffff" stroke="#111827" />')
        body.append(svg_text(f"brand-system-{page}", "summary", 130, 210, 260, 48, 24))
    if include_image:
        body.append('<image id="required-real-image" slide:role="image" href="https://example.com/zhipu-minimax-product.png" x="600" y="150" width="260" height="160" />')
        body.append('<rect id="image-overlay" slide:role="shape" x="600" y="150" width="260" height="160" fill="#111827" opacity="0.18" />')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" '
        'slide:role="slide" slide:contract-version="svglide-authoring-contract/v1" width="960" height="540" viewBox="0 0 960 540">\n  '
        + "\n  ".join(body)
        + "\n</svg>\n"
    )


def make_slide(page: int, template_variant: str, semantic_blocks: list[dict[str, Any]], component_selection: list[dict[str, Any]], include_image: bool) -> tuple[dict[str, Any], str]:
    recipe, layout_family, primitives, effects = RECIPES[(page - 1) % len(RECIPES)]
    if page == 10:
        recipe, layout_family, primitives, effects = ("brand_system", "brand", ["typography", "geometric_shape"], ["typography"])
    if not component_selection:
        component_selection = [{"component_id": "title_block", "binds": [f"title_{page}"]}]
    title = "Closing summary" if page == 10 else f"{template_variant.replace('_', ' ')}"
    slide: dict[str, Any] = {
        "page": page,
        "title": title,
        "renderer_id": f"{layout_family}_{page}",
        "layout_family": layout_family,
        "density": "medium",
        "visual_intent": f"show {template_variant} with the selected template family",
        "visual_focal_point": "main structured visual block",
        "visual_signature": f"{template_variant} rendered through family variant structure",
        "content_density_contract": "medium-density structured template page",
        "asset_contract": "none_required",
        "risk_flags": [],
        "source_policy": "Use prompt-provided content only; do not fabricate numbers.",
        "template_variant": template_variant,
        "semantic_blocks": semantic_blocks or [{"block_id": f"title_{page}", "type": "finding", "content": title}],
        "component_selection": component_selection,
    }
    if include_image:
        slide["asset_strategy"] = {"strategy_id": "real_image_required", "expected_asset_count": 1}
        slide["image_slots"] = [
            {
                "slot_id": "company-product-image",
                "semantic_subject": "Zhipu and MiniMax product identity",
                "asset_type": "screenshot",
                "required": True,
                "real_image_required": True,
                "shared_asset_allowed": False,
            }
        ]
        slide["asset_contract"] = [
            {
                "asset_id": "zhipu-minimax-product-image",
                "binds_slot": "company-product-image",
                "source_type": "web_search_preview",
                "semantic_subject": "Zhipu and MiniMax product identity",
                "retrieval_query": "Zhipu AI MiniMax product identity screenshot",
                "license": "preview_unverified",
                "href": "https://example.com/zhipu-minimax-product.png",
                "usage_page": page,
                "source_url": "https://example.com/zhipu-minimax-product.png",
            }
        ]
    else:
        slide["asset_strategy"] = {"strategy_id": "structured_fallback", "no_fake_data": True}
    return slide, svg_for_recipe(recipe, page, title, include_image)


def run_case(case_id: str, query: str, out_dir: Path, include_images: bool) -> dict[str, Any]:
    case_dir = out_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    matched_plan = beautiful_template_matcher.plan_with_template_family(query, page_count=10)
    slides: list[dict[str, Any]] = []
    svg_paths: list[str] = []
    for raw_slide in matched_plan["slides"]:
        page = int(raw_slide["page"])
        include_image = include_images and page in {1, 7}
        slide, svg = make_slide(page, raw_slide["template_variant"], raw_slide.get("semantic_blocks", []), raw_slide["component_selection"], include_image)
        svg_path = case_dir / f"page-{page:03d}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        svg_paths.append(str(svg_path))
        slides.append(slide)
    plan = {
        "page_count": 10,
        **style_plan_fields(case_id),
        "template_family_selection": matched_plan["template_family_selection"],
        "svg_files": [{"page": index + 1, "path": f"page-{index + 1:03d}.svg"} for index in range(10)],
        "slides": slides,
    }
    plan_path = case_dir / "slide_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_html = "<!doctype html><html><body>" + "\n".join(f'<img src="page-{index + 1:03d}.svg" />' for index in range(10)) + "</body></html>\n"
    (case_dir / "preview.html").write_text(preview_html, encoding="utf-8")
    preflight = svg_preflight.lint_files(svg_paths, str(plan_path))
    required_slots = sum(len(svg_preflight.required_image_slots(slide)) for slide in slides)
    rendered_images = sum(file.get("visual_primitives", {}).get("counts", {}).get("image", 0) for file in preflight["files"])
    issues = preflight.get("plan", {}).get("issues", []) + [issue for file in preflight["files"] for issue in file.get("issues", [])]
    receipt = {
        "version": "beautiful-template-e2e-dry-run/v1",
        "case_id": case_id,
        "query": query,
        "selected_template_id": matched_plan["template_family_selection"]["selected_template_id"],
        "candidate_template_ids": matched_plan["template_family_selection"]["candidate_template_ids"],
        "slide_count": len(slides),
        "template_variant_count": len({slide["template_variant"] for slide in slides}),
        "component_count": len({item["component_id"] for slide in slides for item in slide["component_selection"]}),
        "required_image_slots": required_slots,
        "rendered_image_count": rendered_images,
        "required_image_fill_rate": 1.0 if required_slots == 0 else rendered_images / required_slots,
        "unowned_decorative_primitive_count": sum(1 for issue in issues if issue.get("code") == "unowned_decorative_primitive"),
        "preflight_summary": preflight["summary"],
        "status": "passed" if preflight["summary"]["error_count"] == 0 else "failed",
        "artifacts": {
            "plan": str(plan_path),
            "preview": str(case_dir / "preview.html"),
            "receipt": str(case_dir / "receipt.json"),
        },
    }
    (case_dir / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def run_all(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    receipts = [
        run_case("internal-review", "internal business review for management with metrics evidence and action plan", out_dir, include_images=False),
        run_case("zhipu-minimax", "Zhipu and MiniMax product comparison with company identity and real image slots", out_dir, include_images=True),
    ]
    summary = {
        "version": "beautiful-template-e2e-dry-run-summary/v1",
        "status": "passed" if all(item["status"] == "passed" for item in receipts) else "failed",
        "receipt_count": len(receipts),
        "receipts": receipts,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run beautiful template matcher-to-preflight dry-run fixtures.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    summary = run_all(Path(args.out_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
