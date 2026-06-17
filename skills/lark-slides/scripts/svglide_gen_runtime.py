#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


W = 960
H = 540
COMPONENT_REPORT_SCHEMA = "svglide-component-report/v1"
DESIGN_PATTERN_USAGE_SCHEMA = "svglide-design-pattern-usage/v1"
RUNTIME_CACHE_SCHEMA = "svglide-gen-runtime-cache/v1"
SUPPORTED_PAGE_KINDS = (
    "cover",
    "agenda",
    "section",
    "editor_note",
    "kpi_cards",
    "bar_chart",
    "bubble_chart",
    "donut_chart",
    "sankey_chart",
    "hub_spoke",
    "insight_callout",
    "closing",
)
DEFAULT_ACCENTS = ("#2563EB", "#0F9F8E", "#F59E0B", "#E11D48", "#7C3AED", "#0891B2", "#65A30D", "#334155")
THEME_MOTIF_EFFECTS = {
    "oasis_residential": ["oasis_water_ribbon", "oasis_poplar_texture", "oasis_adras_band"],
    "ai_capital": ["ai_grid_field", "ai_capital_rail", "ai_compute_nodes"],
    "low_altitude_logistics": ["logistics_air_lane", "logistics_dispatch_nodes", "logistics_route_mesh"],
}
PAGE_KIND_ALIASES = {
    "cover_slide": "cover",
    "contents": "agenda",
    "table_of_contents": "agenda",
    "toc": "agenda",
    "agenda_numbered_path": "agenda",
    "section_divider": "section",
    "section_divider_index": "section",
    "chapter": "section",
    "editor-note": "editor_note",
    "editorial_note": "editor_note",
    "note": "editor_note",
    "kpi": "kpi_cards",
    "metric_cards": "kpi_cards",
    "bubble": "bubble_chart",
    "bubble_scatter": "bubble_chart",
    "donut": "donut_chart",
    "sankey": "sankey_chart",
    "hub": "hub_spoke",
    "hub-and-spoke": "hub_spoke",
    "hub_and_spoke": "hub_spoke",
    "annotation": "insight_callout",
    "insight": "insight_callout",
    "spotlight": "insight_callout",
    "spotlight_diagnosis_callout": "insight_callout",
    "ending": "closing",
    "summary": "closing",
}
DEFAULT_ASSET_BY_KIND = {
    "cover": "layout.page_type.cover",
    "agenda": "chart.agenda_list",
    "section": "chart.numbered_steps",
    "editor_note": "layout.page_type.content",
    "closing": "layout.page_type.ending",
    "bar_chart": "chart.bar_chart",
    "bubble_chart": "chart.bubble_chart",
    "donut_chart": "chart.donut_chart",
    "hub_spoke": "chart.hub_spoke",
    "insight_callout": "chart.labeled_card",
    "kpi_cards": "chart.kpi_cards",
    "sankey_chart": "chart.sankey_chart",
}
BG = "#070A0F"
BG_2 = "#0D1118"
PANEL = "#111820"
PANEL_2 = "#17202B"
RULE = "#29323D"
INK = "#F4EFE7"
MUTED = "#9AA0A8"
RED = "#E63946"
GOLD = "#C8BFB4"
SERIF = "Cambria,'Times New Roman','Source Han Serif SC','Noto Serif CJK SC',serif"
SANS = "'Source Han Sans SC','Noto Sans CJK SC',Roboto,sans-serif"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def attrs(values: dict[str, object]) -> str:
    return " ".join(f'{key}="{esc(value)}"' for key, value in values.items() if value is not None)


def tag(name: str, values: dict[str, object], content: str = "") -> str:
    if content:
        return f"<{name} {attrs(values)}>{content}</{name}>"
    return f"<{name} {attrs(values)} />"


def text_box(
    box_id: str,
    x: int,
    y: int,
    width: int,
    height: int,
    text: str,
    *,
    size: int = 18,
    weight: int = 600,
    color: str = "#18212F",
    align: str = "left",
    family: str = SANS,
    line_height: float = 1.24,
    letter_spacing: float = 0,
) -> str:
    style = (
        f"font-family:{family};"
        f"font-size:{size}px;font-weight:{weight};color:{color};line-height:{line_height};"
        f"text-align:{align};letter-spacing:{letter_spacing}px;"
    )
    body = esc(text).replace("\n", "<br/>")
    return tag(
        "foreignObject",
        {
            "id": box_id,
            "slide:role": "shape",
            "slide:shape-type": "text",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="{style}">{body}</div>',
    )


def rect(rect_id: str, x: int, y: int, width: int, height: int, fill: str, **extra: object) -> str:
    return tag(
        "rect",
        {"id": rect_id, "slide:role": "shape", "x": x, "y": y, "width": width, "height": height, "fill": fill, **extra},
    )


def circle(circle_id: str, cx: int, cy: int, r: int, fill: str, **extra: object) -> str:
    return tag("circle", {"id": circle_id, "slide:role": "shape", "cx": cx, "cy": cy, "r": r, "fill": fill, **extra})


def assert_no_arc_path(d: str) -> None:
    if re.search(r"[Aa](?=[\s,\d.+-])", d):
        raise ValueError("SVGlide-safe SVG does not allow path A/a arc commands")


def path(path_id: str, d: str, fill: str = "none", stroke: str | None = None, **extra: object) -> str:
    assert_no_arc_path(d)
    values = {"id": path_id, "slide:role": "shape", "d": d, "fill": fill, **extra}
    if stroke:
        values["stroke"] = stroke
    return tag("path", values)


def line(line_id: str, x1: int, y1: int, x2: int, y2: int, stroke: str, **extra: object) -> str:
    return tag("line", {"id": line_id, "slide:role": "shape", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "stroke": stroke, **extra})


def asset_mark(asset_id: str, x: int, y: int, scale: float, color: str, *, opacity: float = 1.0) -> list[str]:
    # SVG-safe, arc-free ornament paths distilled into SVGlide editorial marks.
    marks = {
        "quote_ticks": ["M0 0 L8 0 L6 20 L0 20 Z", "M14 0 L22 0 L20 20 L14 20 Z"],
        "spark": ["M12 0 L16 9 L26 12 L16 15 L12 24 L8 15 L0 12 L8 9 Z"],
        "chevron": ["M0 0 L20 0 L32 12 L20 24 L0 24 L12 12 Z"],
        "slash": ["M0 24 L7 24 L25 0 L18 0 Z"],
    }
    paths = marks.get(asset_id)
    if not paths:
        raise ValueError(f"unknown asset mark {asset_id}")
    return [
        path(
            f"{asset_id}-{index+1}",
            d,
            fill=color,
            transform=f"translate({x} {y}) scale({scale})",
            opacity=opacity,
        )
        for index, d in enumerate(paths)
    ]


def radial_connector(cx: int, cy: int, tx: int, ty: int, start_radius: int, end_radius: int) -> tuple[int, int, int, int]:
    dx = tx - cx
    dy = ty - cy
    distance = math.hypot(dx, dy) or 1
    ux = dx / distance
    uy = dy / distance
    return (
        int(round(cx + ux * start_radius)),
        int(round(cy + uy * start_radius)),
        int(round(tx - ux * end_radius)),
        int(round(ty - uy * end_radius)),
    )


def bbox(x: int, y: int, width: int, height: int) -> dict[str, int]:
    return {"x": x, "y": y, "width": width, "height": height}


class ComponentReport:
    def __init__(self, *, generator: str = "svglide_gen_runtime") -> None:
        self.generator = generator
        self.pages: dict[int, list[dict[str, Any]]] = {}

    def add(
        self,
        page: int,
        component_id: str,
        renderer_id: str,
        box: dict[str, int],
        primitives: list[str],
        *,
        effects: list[str] | None = None,
        source_trace: str = "",
        asset_id: str = "",
    ) -> None:
        component = {
            "id": component_id,
            "renderer_id": renderer_id,
            "bbox": box,
            "primitives": primitives,
            "effects": effects or [],
        }
        if source_trace:
            component["source_trace"] = source_trace
        if asset_id:
            component["asset_id"] = asset_id
        self.pages.setdefault(page, []).append(component)

    def to_dict(self) -> dict[str, Any]:
        pages = [{"page": page, "components": self.pages[page]} for page in sorted(self.pages)]
        return {
            "schema_version": COMPONENT_REPORT_SCHEMA,
            "status": "passed",
            "generator": self.generator,
            "pages": pages,
            "summary": {
                "page_count": len(pages),
                "component_count": sum(len(page["components"]) for page in pages),
                "error_count": 0,
                "warning_count": 0,
            },
        }


def report_page(report: dict[str, Any], page: int) -> dict[str, Any]:
    for item in report.get("pages", []):
        if isinstance(item, dict) and item.get("page") == page:
            return item
    return {"page": page, "components": []}


def design_pattern_usage_receipt(report: dict[str, Any]) -> dict[str, Any]:
    usages: list[dict[str, Any]] = []
    for page in report.get("pages", []):
        if not isinstance(page, dict):
            continue
        component_ids: dict[str, list[str]] = {}
        traces: dict[str, str] = {}
        for component in page.get("components", []):
            if not isinstance(component, dict):
                continue
            asset_id = str(component.get("asset_id") or "").strip()
            if not asset_id:
                continue
            component_ids.setdefault(asset_id, []).append(str(component.get("id") or ""))
            traces[asset_id] = str(component.get("source_trace") or component.get("renderer_id") or "runtime")
        for asset_id, ids in sorted(component_ids.items()):
            usages.append(
                {
                    "page": page.get("page"),
                    "asset_id": asset_id,
                    "component_ids": [item for item in ids if item],
                    "source_trace": traces.get(asset_id, "runtime"),
                }
            )
    return {
        "schema_version": DESIGN_PATTERN_USAGE_SCHEMA,
        "status": "passed",
        "used_asset_ids": sorted({str(usage.get("asset_id") or "") for usage in usages if usage.get("asset_id")}),
        "page_usages": usages,
        "error_count": 0,
        "warning_count": 0,
    }


def svg_wrap(page: int, accent: str, body: list[str]) -> str:
    defs = f"""
  <defs>
    <linearGradient id="bg-{page}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BG}" />
      <stop offset="64%" stop-color="{BG_2}" />
      <stop offset="100%" stop-color="{accent}" stop-opacity="0.16" />
    </linearGradient>
  </defs>"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" '
        f'slide:role="slide" slide:contract-version="svglide-authoring-contract/v1" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        + defs
        + "\n  "
        + "\n  ".join(body)
        + "\n</svg>\n"
    )


def editorial_shell(page: int, accent: str, title: str, summary: str) -> list[str]:
    return [
        *editorial_background(page, accent),
        rect("title-surface", 78, 54, 700, 60, "#090D13", rx=0, opacity=0.82),
        rect("title-accent", 70, 52, 8, 36, accent, rx=3),
        text_box("kicker", 86, 40, 430, 18, f"PART {page:02d} / SVGLIDE EDITORIAL RENDERER", size=8, weight=800, color="#6D737D", family=SERIF, letter_spacing=2),
        text_box("title", 86, 62, 680, 44, title, size=25, weight=900, color=INK, family=SERIF),
        text_box("subtitle", 86, 120, 610, 34, summary[:130], size=10, weight=500, color=MUTED),
    ]


def editorial_background(page: int, accent: str) -> list[str]:
    return [
        rect("background", 0, 0, W, H, f"url(#bg-{page})"),
        rect("edge-shadow", 40, 0, 1, H, "#202632", opacity=0.65),
        rect("right-note-band", 790, 0, 1, H, "#1B232E", opacity=0.78),
    ]


def editorial_footer(page: int) -> str:
    return text_box(
        "footer",
        70,
        480,
        820,
        18,
        f"SVGlide local preview · design renderer v1 · {page:02d}",
        size=8,
        weight=600,
        color="#5F6670",
        align="center",
    )


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(compact_text(item) for item in value.values() if compact_text(item))
    if isinstance(value, list):
        return " ".join(compact_text(item) for item in value if compact_text(item))
    return str(value).strip()


def contract_required_evidence(spec: dict[str, Any]) -> list[str]:
    contract = spec.get("visual_design_contract")
    if not isinstance(contract, dict):
        return []
    raw = contract.get("required_visual_evidence")
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def evidence_effects(spec: dict[str, Any], defaults: list[str]) -> list[str]:
    out: list[str] = []
    for item in defaults:
        if item not in out:
            out.append(item)
    return out


def is_strategist_contract(plan: dict[str, Any]) -> bool:
    return text_from_any(plan.get("schema_version")).startswith("svglide-strategist-contract/")


def layout_boxes_by_role(spec: dict[str, Any]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    boxes = spec.get("layout_boxes")
    if not isinstance(boxes, list):
        return out
    for box in boxes:
        if not isinstance(box, dict):
            continue
        try:
            box_data = {
                "x": int(float(box.get("x", 0))),
                "y": int(float(box.get("y", 0))),
                "width": int(float(box.get("width", 0))),
                "height": int(float(box.get("height", 0))),
            }
        except (TypeError, ValueError):
            continue
        aliases = [
            text_from_any(box.get("id")),
            text_from_any(box.get("role")),
            text_from_any(box.get("name")),
            text_from_any(box.get("layout_box_role")),
        ]
        for alias in aliases:
            key = slug_id(alias).replace("-", "_")
            if key and key not in out:
                out[key] = box_data
    return out


def contract_box(boxes: dict[str, dict[str, int]], *roles: str, fallback: tuple[int, int, int, int]) -> dict[str, int]:
    for role in roles:
        normalized = slug_id(role).replace("-", "_")
        if normalized in boxes:
            return boxes[normalized]
    x, y, width, height = fallback
    return {"x": x, "y": y, "width": width, "height": height}


def role_text_limit(spec: dict[str, Any], role: str, fallback: int) -> int:
    budgets = spec.get("text_budget_by_role")
    if not isinstance(budgets, dict):
        return fallback
    raw = budgets.get(role)
    if isinstance(raw, dict):
        value = raw.get("max_chars") or raw.get("chars") or raw.get("max_visible_chars")
    else:
        value = raw
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(4, parsed)


def shorten(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: max(1, limit - 1)].rstrip() + "…"


PROMPT_PREFIX_RE = re.compile(
    r"^\s*(cover|kpi\s+dashboard|kpi|roadmap|process|comparison|capability|chart|closing|封面|仪表盘|路线图|流程|对比|能力|图表|收束)\s*[:：]\s*",
    re.IGNORECASE,
)


def strip_prompt_prefix(text: str) -> str:
    return PROMPT_PREFIX_RE.sub("", text).strip()


def topic_context(spec: dict[str, Any], deck_title: str = "") -> str:
    return " ".join(
        part
        for part in [
            deck_title,
            compact_text(spec.get("title")),
            compact_text(spec.get("key_message")),
            compact_text(spec.get("summary")),
            compact_text(spec.get("description")),
            compact_text(spec.get("body")),
        ]
        if part
    ).lower()


def is_low_altitude_context(context: str) -> bool:
    return any(token in context for token in ["低空", "无人机", "空域", "drone", "uav"])


DEFAULT_TOPIC_LABELS = {"核心节点", "资源配置", "执行路径", "价值回收", "风险控制", "下一步"}
TOPIC_STOPWORDS = {
    "需要",
    "围绕",
    "包括",
    "包含",
    "通过",
    "聚焦",
    "形成",
    "闭环",
    "方案",
    "策划",
    "项目",
    "核心",
    "关键",
    "the",
    "and",
    "with",
    "for",
    "from",
}


def topic_label_from_item(item: Any) -> str:
    if isinstance(item, dict):
        return text_from_any(item.get("title") or item.get("label") or item.get("name") or item.get("metric") or item.get("value"))
    return text_from_any(item)


def structured_topic_labels(spec: dict[str, Any], *, count: int) -> list[str]:
    labels: list[str] = []
    for key in ("items", "sections", "agenda", "nodes", "spokes", "metrics", "kpis", "cards", "targets", "segments"):
        value = spec.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            label_text = topic_label_from_item(item)
            if label_text and label_text not in labels:
                labels.append(shorten(label_text, 12))
            if len(labels) >= count:
                return labels
    return labels


def split_topic_phrases(text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"(?:围绕|包括|包含|聚焦|通过|覆盖)([^。；;：:\n]+)", text):
        candidates.extend(re.split(r"[、,，/／和与及]+", match.group(1)))
    candidates.extend(re.split(r"[。；;：:\n、,，/／]+", text))
    out: list[str] = []
    for raw in candidates:
        phrase = re.sub(r"\s+", " ", raw.strip(" -—·:：。；;，,"))
        if not phrase:
            continue
        phrase = re.sub(r"^(需要|围绕|包括|包含|通过|聚焦|形成|打造|构建)", "", phrase)
        phrase = re.sub(r"(形成闭环|形成体系|形成系统|闭环)$", "", phrase).strip()
        if not phrase:
            continue
        lowered = phrase.lower()
        if lowered in TOPIC_STOPWORDS:
            continue
        if len(phrase) > 12:
            continue
        if len(phrase) < 2:
            continue
        if phrase not in out:
            out.append(phrase)
    return out


def inferred_topic_labels(spec: dict[str, Any], deck_title: str = "", *, count: int) -> list[str]:
    labels = structured_topic_labels(spec, count=count)
    if len(labels) >= count:
        return labels[:count]
    context = " ".join(
        part
        for part in [
            deck_title,
            compact_text(spec.get("title")),
            compact_text(spec.get("key_message")),
            compact_text(spec.get("summary")),
            compact_text(spec.get("description")),
            compact_text(spec.get("body")),
        ]
        if part
    )
    for phrase in split_topic_phrases(context):
        if phrase not in labels and phrase not in DEFAULT_TOPIC_LABELS:
            labels.append(phrase)
        if len(labels) >= count:
            break
    return labels[:count]


def topic_node_labels(spec: dict[str, Any], deck_title: str = "", *, count: int = 5) -> list[str]:
    context = topic_context(spec, deck_title)
    if any(token in context for token in ["阿克苏", "绿洲", "胡杨", "四季", "水系", "oasis"]):
        labels = ["水系入口", "春配套", "夏活力", "胡杨秋境", "暖廊冬居", "地域纹样"]
    elif is_low_altitude_context(context):
        labels = ["订单入口", "空域调度", "无人机执行", "末端交付", "安全冗余", "运营回收"]
    elif any(token in context for token in ["ai", "capital", "compute", "gpu", "stargate", "openai"]):
        labels = ["资本入口", "算力承诺", "模型平台", "收入兑现", "生态回流", "风险折扣"]
    else:
        labels = inferred_topic_labels(spec, deck_title, count=count)
        if not labels:
            labels = ["核心节点", "资源配置", "执行路径", "价值回收", "风险控制", "下一步"]
    return labels[:count]


def semantic_caption_for_topic(spec: dict[str, Any], deck_title: str = "", *, count: int = 4) -> str:
    return " / ".join(topic_node_labels(spec, deck_title, count=count))


def add_semantic_caption(text: str, spec: dict[str, Any], deck_title: str = "", *, max_chars: int = 96) -> str:
    caption = semantic_caption_for_topic(spec, deck_title)
    if not caption:
        return text
    if all(label in text for label in caption.split(" / ")):
        return text
    combined = f"{text}\n{caption}" if text else caption
    return shorten(combined, max_chars)


def agenda_labels_for_topic(spec: dict[str, Any], deck_title: str = "", *, count: int = 6) -> list[str]:
    raw_items = spec.get("items") or spec.get("sections") or spec.get("agenda")
    labels: list[str] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                label_text = text_from_any(item.get("title") or item.get("label") or item.get("name"))
            else:
                label_text = text_from_any(item)
            if label_text:
                labels.append(label_text)
            if len(labels) >= count:
                return labels
    context = topic_context(spec, deck_title)
    if any(token in context for token in ["阿克苏", "绿洲", "胡杨", "四季", "水系", "oasis"]):
        labels = ["核心定位", "春之地块", "夏之地块", "秋之地块", "冬之地块", "价值展望"]
    elif any(token in context for token in ["ai", "capital", "compute", "gpu", "stargate", "openai"]):
        labels = ["资本入口", "算力承诺", "平台竞合", "财务兑现", "风险折扣", "2026 判断"]
    else:
        labels = ["问题定义", "核心逻辑", "能力结构", "推进路径", "风险控制", "结论行动"]
    return labels[:count]


def section_index_for_spec(spec: dict[str, Any], page: int) -> str:
    for key in ("section_index", "chapter_index", "index_label", "kicker"):
        value = text_from_any(spec.get(key))
        match = re.search(r"\d{1,2}", value)
        if match:
            return match.group(0).zfill(2)
    title = text_from_any(spec.get("title") or spec.get("headline"))
    match = re.search(r"\d{1,2}", title)
    if match:
        return match.group(0).zfill(2)
    return str(page).zfill(2)


def comparison_rows_for_topic(spec: dict[str, Any], deck_title: str = "") -> list[tuple[str, str, str]]:
    context = topic_context(spec, deck_title)
    if any(token in context for token in ["阿克苏", "绿洲", "胡杨", "四季", "水系", "oasis"]):
        return [
            ("空间", "单点景观割裂", "水系串联四境"),
            ("生活", "配套平均铺开", "春夏秋冬差异体验"),
            ("文化", "弱地域识别", "胡杨与纹样成为记忆点"),
        ]
    if is_low_altitude_context(context):
        return [
            ("效率", "地面高峰拥堵", "低空走廊直达"),
            ("成本", "线性增车扩张", "平台调度摊薄成本"),
            ("韧性", "单一路由失效", "空地协同冗余"),
        ]
    if any(token in context for token in ["ai", "capital", "compute", "gpu", "stargate", "openai"]):
        return [
            ("资本", "财务投资分散", "算力绑定资本闭环"),
            ("供给", "GPU 采购排队", "云厂商承诺前置"),
            ("回报", "估值叙事驱动", "收入兑现重新定价"),
        ]
    labels = inferred_topic_labels(spec, deck_title, count=3)
    if len(labels) >= 3:
        return [
            (labels[0], "单点动作分散", f"{labels[0]}成为主线"),
            (labels[1], "触点缺少协同", f"{labels[1]}形成抓手"),
            (labels[2], "价值表达模糊", f"{labels[2]}沉淀记忆"),
        ]
    return [
        ("效率", "资源分散推进", "主路径集中突破"),
        ("体验", "信息散落难记", "视觉系统承载重点"),
        ("风险", "后置发现问题", "前置门禁与回归"),
    ]


def dashboard_metrics_for_topic(spec: dict[str, Any], deck_title: str = "") -> list[tuple[str, str]]:
    context = topic_context(spec, deck_title)
    if any(token in context for token in ["阿克苏", "绿洲", "胡杨", "四季", "水系", "oasis"]):
        return [("4境", "四季地块"), ("1环", "水系闭环"), ("3核", "价值引擎"), ("全年龄", "人群覆盖")]
    if is_low_altitude_context(context):
        return [("92%", "准点率"), ("18m", "时效"), ("4.2k", "日单量"), ("-23%", "单均成本")]
    if any(token in context for token in ["ai", "capital", "compute", "gpu", "stargate", "openai"]):
        return [("$122B", "融资规模"), ("10GW", "算力承诺"), ("4家", "核心投资人"), ("2026", "资本窗口")]
    labels = inferred_topic_labels(spec, deck_title, count=4)
    if len(labels) >= 4:
        return [(f"{index:02d}", label) for index, label in enumerate(labels[:4], 1)]
    return [("4", "关键抓手"), ("1", "主路径"), ("3", "价值层"), ("90d", "推进节奏")]


def contract_text(
    spec: dict[str, Any],
    box_id: str,
    box: dict[str, int],
    text: str,
    *,
    role: str,
    size: int,
    weight: int = 700,
    color: str = "#111827",
    align: str = "left",
) -> str:
    limit = role_text_limit(spec, role, 34 if role == "title" else 120)
    return text_box(
        box_id,
        box["x"],
        box["y"],
        box["width"],
        box["height"],
        shorten(text, limit),
        size=size,
        weight=weight,
        color=color,
        align=align,
        family=SANS,
    )


def slide_anchor_role(spec: dict[str, Any]) -> str:
    anchor = spec.get("main_visual_anchor")
    if isinstance(anchor, dict):
        role = text_from_any(anchor.get("layout_box_role") or anchor.get("role"))
        if role:
            return role
    return "visual"


def contract_summary(spec: dict[str, Any], fallback: str) -> str:
    return strip_prompt_prefix(first_text(spec, ["key_message", "summary", "description", "subtitle", "body"], fallback))


def contract_title(spec: dict[str, Any], kind: str, deck_title: str) -> str:
    title = first_text(spec, ["title", "headline", "name"], "")
    if title:
        return strip_prompt_prefix(title)
    title_by_type = {
        "cover": deck_title,
        "kpi_overview": "运营指标总览",
        "roadmap": "阶段推进路线",
        "process_flow": "端到端运行链路",
        "comparison": "方案价值对照",
        "capability_map": "平台能力图谱",
        "chart_takeaway": "关键场景变化",
        "closing": "下一步行动建议",
    }
    page_type = text_from_any(spec.get("page_type"))
    if page_type in title_by_type:
        return title_by_type[page_type]
    page_type = text_from_any(spec.get("page_type")).replace("_", " ").title()
    return strip_prompt_prefix(page_type or kind.replace("_", " ").title() or deck_title)


def theme_key(spec: dict[str, Any] | None = None, deck_title: str = "") -> str:
    data = spec if isinstance(spec, dict) else {}
    context = topic_context(data, deck_title or text_from_any(data.get("_deck_title")))
    if any(token in context for token in ["阿克苏", "绿洲", "胡杨", "四季", "水系", "oasis", "adras", "艾德莱斯"]):
        return "oasis_residential"
    if is_low_altitude_context(context):
        return "low_altitude_logistics"
    if any(token in context for token in ["ai", "capital", "compute", "gpu", "stargate", "openai", "算力", "资本"]):
        return "ai_capital"
    return "general_editorial"


def theme_effects(spec: dict[str, Any] | None = None, deck_title: str = "") -> list[str]:
    return list(THEME_MOTIF_EFFECTS.get(theme_key(spec, deck_title), []))


def theme_background_motifs(page: int, accent: str, spec: dict[str, Any] | None = None) -> list[str]:
    key = theme_key(spec, text_from_any(spec.get("_deck_title")) if isinstance(spec, dict) else "")
    if key == "oasis_residential":
        return [
            path("theme-oasis-water-ribbon", "M824 122 C848 102 868 134 890 108 C900 96 904 98 908 92", stroke="#4A90E2", **{"stroke-width": 15, "stroke-linecap": "round", "opacity": 0.18}),
            path("theme-oasis-water-highlight", "M828 128 C850 112 870 140 892 114 C900 106 904 106 908 100", stroke=accent, **{"stroke-width": 4, "stroke-linecap": "round", "opacity": 0.42}),
            rect("theme-oasis-poplar-texture-1", 872, 160, 10, 230, "#8A5A2B", rx=0, opacity=0.12),
            rect("theme-oasis-poplar-texture-2", 890, 188, 7, 202, "#8A5A2B", rx=0, opacity=0.10),
            rect("theme-oasis-poplar-texture-3", 902, 172, 8, 218, "#FFC107", rx=0, opacity=0.12),
            rect("theme-oasis-adras-band", 824, 142, 54, 9, "#E91E63", rx=0, opacity=0.22),
            rect("theme-oasis-spring-swatch", 884, 142, 10, 9, "#8BC34A", rx=0, opacity=0.55),
            rect("theme-oasis-autumn-swatch", 898, 142, 10, 9, "#FFC107", rx=0, opacity=0.55),
        ]
    if key == "ai_capital":
        motifs: list[str] = [
            rect("theme-ai-grid-field", 674, 58, 206, 342, "#0F172A", rx=0, opacity=0.055),
            rect("theme-ai-capital-rail", 706, 76, 4, 306, accent, rx=0, opacity=0.38),
            rect("theme-ai-data-band", 736, 102, 104, 8, "#E11D48", rx=0, opacity=0.30),
        ]
        for index, (x, y) in enumerate(((742, 150), (814, 184), (766, 256), (836, 318)), 1):
            motifs.append(circle(f"theme-ai-compute-node-{index}", x, y, 7, accent, opacity=0.42))
        return motifs
    if key == "low_altitude_logistics":
        return [
            path("theme-logistics-air-lane-1", "M900 112 C903 96 905 124 908 108", stroke=accent, **{"stroke-width": 4, "stroke-linecap": "round", "opacity": 0.26}),
            path("theme-logistics-air-lane-2", "M900 138 C903 122 905 152 908 136", stroke="#0F9F8E", **{"stroke-width": 4, "stroke-linecap": "round", "opacity": 0.18}),
            rect("theme-logistics-dispatch-node-1", 900, 158, 8, 8, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 2, "opacity": 0.74}),
            rect("theme-logistics-dispatch-node-2", 900, 176, 8, 8, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 2, "opacity": 0.74}),
            rect("theme-logistics-route-mesh", 900, 196, 8, 28, accent, rx=0, opacity=0.08),
        ]
    return []


def contract_background(page: int, accent: str, spec: dict[str, Any] | None = None) -> list[str]:
    return [
        rect("background", 0, 0, W, H, "#F8FAFC"),
        rect("accent-page-wash", 720, 0, 240, H, accent, rx=0, opacity=0.085),
        *theme_background_motifs(page, accent, spec),
        rect("accent-wash-left", 48, 44, 10, 436, accent, rx=0, opacity=0.26),
        rect("accent-wash-bottom", 48, 476, 864, 4, accent, rx=0, opacity=0.18),
        rect("top-rule", 48, 32, 864, 4, accent, rx=0),
    ]


def contract_footer(page: int, spec: dict[str, Any], boxes: dict[str, dict[str, int]]) -> str:
    footer = contract_box(boxes, "footer", fallback=(64, 500, 832, 18))
    footer_label = first_text(spec, ["footer", "source_note", "visible_source_note", "_deck_title"], "Page")
    return contract_text(spec, "footer", footer, f"{footer_label} · {page:02d}", role="footer", size=9, weight=600, color="#64748B", align="center")


def visual_box_for_contract(spec: dict[str, Any], boxes: dict[str, dict[str, int]], fallback: tuple[int, int, int, int]) -> dict[str, int]:
    anchor = slide_anchor_role(spec)
    return contract_box(boxes, anchor, "visual", "chart", "flow", "table", "grid", "body", fallback=fallback)


def render_contract_cover(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str, deck_title: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(72, 150, 560, 120))
    body_box = contract_box(boxes, "body", fallback=(76, 284, 520, 72))
    visual = visual_box_for_contract(spec, boxes, (600, 84, 288, 360))
    body_copy = add_semantic_caption(summary, spec, deck_title, max_chars=role_text_limit(spec, "body", 96))
    body = [
        *contract_background(page, accent, spec),
        rect("cover-title-field", 64, 132, 584, 160, accent, rx=0, opacity=0.055),
        rect("cover-map-field", 592, 72, 308, 386, "#DBEAFE", rx=0, opacity=0.88),
        rect("cover-coordinate-stack-1", 616, 112, 236, 1, accent, rx=0, opacity=0.16),
        rect("cover-coordinate-stack-2", 616, 184, 236, 1, accent, rx=0, opacity=0.16),
        rect("cover-coordinate-stack-3", 616, 256, 236, 1, accent, rx=0, opacity=0.16),
        rect("cover-coordinate-stack-4", 616, 328, 236, 1, accent, rx=0, opacity=0.16),
        path("cover-route-ribbon", "M606 414 C658 298 698 250 750 192 C796 142 836 116 886 96 L886 134 C826 162 800 192 766 236 C714 304 674 358 638 430 Z", fill=accent, opacity=0.18),
        rect("visual-anchor-panel", visual["x"], visual["y"], visual["width"], visual["height"], "#E0F2FE", rx=0, opacity=0.96),
        rect("visual-anchor-side-band", visual["x"] + visual["width"] - 42, visual["y"], 42, visual["height"], accent, rx=0, opacity=0.24),
        rect("visual-grid-a", visual["x"] + 24, visual["y"] + 48, visual["width"] - 72, 1, accent, rx=0, opacity=0.14),
        rect("visual-grid-b", visual["x"] + 24, visual["y"] + 148, visual["width"] - 72, 1, accent, rx=0, opacity=0.14),
        rect("visual-grid-c", visual["x"] + 24, visual["y"] + 248, visual["width"] - 72, 1, accent, rx=0, opacity=0.14),
        path("visual-route-shadow", f"M{visual['x'] + 10} {visual['y'] + visual['height'] - 28} C{visual['x'] + 86} {visual['y'] + 48} {visual['x'] + 158} {visual['y'] + visual['height'] - 106} {visual['x'] + visual['width'] - 6} {visual['y'] + 34}", stroke="#94A3B8", **{"stroke-width": 24, "stroke-linecap": "round", "opacity": 0.20}),
        path("visual-route-path", f"M{visual['x'] + 24} {visual['y'] + visual['height'] - 42} C{visual['x'] + 96} {visual['y'] + 30} {visual['x'] + 172} {visual['y'] + visual['height'] - 80} {visual['x'] + visual['width'] - 24} {visual['y'] + 52}", stroke=accent, **{"stroke-width": 10, "stroke-linecap": "round", "opacity": 0.92}),
        rect("visual-node-a", visual["x"] + 38, visual["y"] + visual["height"] - 66, 28, 28, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 4}),
        rect("visual-node-b", visual["x"] + visual["width"] - 58, visual["y"] + 40, 28, 28, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 4}),
        contract_text(spec, "title", title_box, title, role="title", size=38, weight=900, color="#0F172A"),
        contract_text(spec, "body", body_box, body_copy, role="body", size=18, weight=650, color="#334155"),
        contract_footer(page, spec, boxes),
    ]
    report.add(page, "contract-cover", "contract.cover", bbox(visual["x"], visual["y"], visual["width"], visual["height"]), ["path", "geometric_shape", "typography"], effects=evidence_effects(spec, ["path", "typography", "full_page_archetype", "hero_route", "title_field"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_agenda(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 58, 624, 58))
    timeline = contract_box(boxes, "timeline", fallback=(110, 148, 690, 250))
    body_box = contract_box(boxes, "body", fallback=(110, 414, 690, 48))
    visual = contract_box(boxes, "visual", fallback=(732, 92, 128, 348))
    body_text_y = max(body_box["y"] + 14, title_box["y"] + title_box["height"] + 30)
    body_text_box = {
        "x": body_box["x"],
        "y": body_text_y,
        "width": body_box["width"],
        "height": max(40, body_box["y"] + body_box["height"] - body_text_y),
    }
    labels = agenda_labels_for_topic(spec, text_from_any(spec.get("_deck_title")), count=6)
    backplane_x = min(timeline["x"], body_box["x"]) - 18
    backplane_y = max(min(timeline["y"], body_box["y"]) - 18, title_box["y"] + title_box["height"] + 26)
    backplane_right = max(timeline["x"] + timeline["width"], body_box["x"] + body_box["width"]) + 18
    backplane_bottom = max(timeline["y"] + timeline["height"], body_box["y"] + body_box["height"]) + 18
    body = [
        *contract_background(page, accent, spec),
        rect("agenda-route-backplane", backplane_x, backplane_y, backplane_right - backplane_x, backplane_bottom - backplane_y, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.96}),
        rect("agenda-side-index-field", visual["x"], visual["y"], visual["width"], visual["height"], accent, rx=0, opacity=0.10),
        contract_text(spec, "title", title_box, title, role="title", size=24, weight=900, color="#0F172A"),
    ]
    y_step = max(34, timeline["height"] // max(1, len(labels)))
    points: list[tuple[int, int]] = []
    for index, _label_text in enumerate(labels, 1):
        x = timeline["x"] + timeline["width"] // 2 + (8 if index % 2 else -8)
        y = timeline["y"] + 20 + (index - 1) * y_step
        points.append((x, y))
        body.append(rect(f"agenda-number-{index}", x - 13, y - 13, 26, 26, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 2}))
        body.append(rect(f"agenda-index-tick-{index}", x - 30, y - 3, 16, 6, accent, rx=0, opacity=0.48))
    if points:
        route_d = "M" + " L".join(f"{x} {y}" for x, y in points)
        body.append(path("agenda-route-shadow", route_d, stroke="#94A3B8", **{"stroke-width": 12, "stroke-linecap": "round", "opacity": 0.12}))
        body.append(path("agenda-route-path", route_d, stroke=accent, **{"stroke-width": 4, "stroke-linecap": "round", "opacity": 0.72}))
    body.extend(
        [
            rect("agenda-visual-mark", visual["x"], visual["y"], visual["width"], visual["height"], accent, rx=0, opacity=0.36),
            contract_text(spec, "agenda-labels", body_text_box, " / ".join(f"{index:02d} {label}" for index, label in enumerate(labels, 1)), role="body", size=17, weight=750, color="#0F172A"),
            contract_footer(page, spec, boxes),
        ]
    )
    report.add(page, "contract-agenda", "contract.agenda", bbox(backplane_x, backplane_y, backplane_right - backplane_x, backplane_bottom - backplane_y), ["path", "geometric_shape", "typography"], effects=evidence_effects(spec, ["numbered_path", "section_index", "semantic_labels", "connector_flow"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_section(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str, deck_title: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(82, 164, 620, 104))
    body_box = contract_box(boxes, "body", fallback=(86, 300, 560, 58))
    visual = visual_box_for_contract(spec, boxes, (652, 80, 214, 356))
    section_index = section_index_for_spec(spec, page)
    hero_width = min(220, max(120, visual["width"] // 3))
    hero_x = max(48, min(visual["x"] + visual["width"] - hero_width - 48, 912 - hero_width))
    hero_y = max(visual["y"] + 18, min(visual["y"] + 34, 414))
    body_copy = add_semantic_caption(summary, spec, deck_title, max_chars=max(36, role_text_limit(spec, "body", 60) - 8))
    body = [
        *contract_background(page, accent, spec),
        rect("section-signal-field", 48, 66, 864, 386, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.95}),
        rect("section-index-rail", visual["x"], visual["y"], visual["width"], visual["height"], accent, rx=0, opacity=0.13),
        rect("section-motif-block", visual["x"] + 64, visual["y"] + 42, max(80, visual["width"] - 128), 16, accent, rx=0, opacity=0.26),
        rect("section-hero-number", hero_x, hero_y, hero_width, 92, accent, rx=0, opacity=0.18),
        rect("section-hero-number-mark", hero_x + 18, hero_y + 22, hero_width - 36, 12, accent, rx=0, opacity=0.62),
        contract_text(spec, "title", title_box, title, role="title", size=32, weight=900, color="#0F172A"),
        contract_text(spec, "body", body_box, body_copy, role="body", size=15, weight=650, color="#334155"),
        rect("section-bottom-rule", 82, 394, 520, 5, accent, rx=0, opacity=0.58),
        contract_footer(page, spec, boxes),
    ]
    report.add(page, "contract-section", "contract.section", bbox(48, 66, 864, 386), ["path", "geometric_shape", "typography"], effects=evidence_effects(spec, ["section_index", "hero_signal", "full_page_archetype"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_dashboard(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(48, 34, 864, 48))
    metric = contract_box(boxes, "metric", fallback=(64, 106, 260, 128))
    grid = contract_box(boxes, "grid", fallback=(348, 106, 548, 128))
    chart = contract_box(boxes, "chart", fallback=(64, 258, 832, 150))
    body_box = contract_box(boxes, "body", fallback=(64, 426, 832, 56))
    body = [*contract_background(page, accent, spec), contract_text(spec, "title", title_box, title, role="title", size=22, weight=900)]
    metrics = dashboard_metrics_for_topic(spec, text_from_any(spec.get("_deck_title")))
    body.append(rect("metric-hero-card", metric["x"], metric["y"], metric["width"], metric["height"], "#E0F2FE", rx=0, stroke=accent, **{"stroke-width": 2}))
    body.append(contract_text(spec, "metric", {"x": metric["x"] + 18, "y": metric["y"] + 20, "width": metric["width"] - 36, "height": 78}, f"{metrics[0][0]}\n{metrics[0][1]}", role="metric", size=27, weight=900, color=accent))
    for index, (value, label_text) in enumerate(metrics[1:], 1):
        x = grid["x"] + (index - 1) * max(1, grid["width"] // 3)
        w = max(92, grid["width"] // 3 - 14)
        body.append(rect(f"dashboard-card-{index}", x, grid["y"] + 10, w, 96, "#FFFFFF", rx=0, stroke="#CBD5E1", **{"stroke-width": 1}))
        body.append(rect(f"dashboard-card-cap-{index}", x, grid["y"] + 10, w, 8, accent, rx=0, opacity=0.42))
        body.append(text_box(f"metric-card-value-{index}", x + 16, grid["y"] + 25, w - 32, 28, value, size=22, weight=900, color="#0F172A"))
        body.append(text_box(f"metric-card-name-{index}", x + 16, grid["y"] + 53, w - 32, 18, label_text, size=9, weight=800, color="#475569"))
        body.append(rect(f"kpi-mini-bar-{index}", x + 16, grid["y"] + 78, w - 32, 14 + index * 5, accent, rx=0, opacity=0.72))
    body.append(line("chart-axis", chart["x"] + 70, chart["y"] + chart["height"] - 18, chart["x"] + chart["width"] - 70, chart["y"] + chart["height"] - 18, "#CBD5E1", **{"stroke-width": 1}))
    for grid_index in range(3):
        grid_y = chart["y"] + 22 + grid_index * 38
        body.append(line(f"chart-grid-{grid_index}", chart["x"] + 70, grid_y, chart["x"] + chart["width"] - 70, grid_y, "#E2E8F0", **{"stroke-width": 1, "opacity": 0.7}))
    for index, height in enumerate((48, 78, 104, 64), 1):
        x = chart["x"] + 80 + index * 120
        body.append(rect(f"chart-bar-{index}", x, chart["y"] + chart["height"] - height - 18, 56, height, accent, rx=0, opacity=0.8))
    body_text = {"x": body_box["x"], "y": body_box["y"], "width": body_box["width"], "height": min(42, body_box["height"])}
    metric_line = " / ".join(f"{label}{value}" for value, label in metrics)
    dashboard_copy = f"{summary} / {metric_line}" if summary else metric_line
    body.extend(
        [
            contract_text(spec, "body", body_text, dashboard_copy, role="body", size=13, weight=600, color="#334155"),
            contract_footer(page, spec, boxes),
        ]
    )
    report.add(page, "contract-dashboard", "contract.dashboard", bbox(chart["x"], chart["y"], chart["width"], chart["height"]), ["geometric_shape", "typography", "micro_chart", "dashboard"], effects=evidence_effects(spec, ["chart_geometry", "typography", "metric_hierarchy", "dashboard_grid"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_flow(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 46, 680, 52))
    flow = visual_box_for_contract(spec, boxes, (96, 160, 768, 210))
    body_box = contract_box(boxes, "body", fallback=(96, 380, 768, 48))
    callout_box = contract_box(boxes, "callout", "note", fallback=(flow["x"] + flow["width"] - 260, flow["y"] + flow["height"] + 22, 250, 48))
    body = [
        *contract_background(page, accent, spec),
        contract_text(spec, "title", title_box, title, role="title", size=22, weight=900),
        rect("flow-backplane", flow["x"], flow["y"] - 18, flow["width"], flow["height"] + 84, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.96}),
        rect("flow-lane-upper", flow["x"] + 24, flow["y"] + 22, flow["width"] - 48, 44, accent, rx=0, opacity=0.11),
        rect("flow-lane-lower", flow["x"] + 24, flow["y"] + flow["height"] - 78, flow["width"] - 48, 44, accent, rx=0, opacity=0.08),
    ]
    y = flow["y"] + flow["height"] // 2
    start_x = flow["x"] + 36
    step_gap = max(90, (flow["width"] - 72) // 4)
    points = []
    for index in range(5):
        x = start_x + index * step_gap
        points.append((x, y + (index % 2) * 26 - 13))
    path_d = "M" + " L".join(f"{x} {node_y}" for x, node_y in points)
    body.append(rect("flow-zone-band", flow["x"], flow["y"] + flow["height"] // 2 - 34, flow["width"], 68, accent, rx=0, opacity=0.13))
    body.append(path("flow-route-shadow", path_d, stroke="#94A3B8", **{"stroke-width": 20, "stroke-linecap": "round", "opacity": 0.18}))
    body.append(path("flow-route-path", path_d, stroke=accent, **{"stroke-width": 9, "stroke-linecap": "round", "opacity": 0.88}))
    labels = topic_node_labels(spec, text_from_any(spec.get("_deck_title")), count=5)
    for index, (x, node_y) in enumerate(points, 1):
        body.append(rect(f"flow-stage-panel-{index}", x - 30, node_y - 22, 60, 44, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 1, "opacity": 0.82}))
        body.append(rect(f"flow-tick-{index}", x - 5, node_y - 5, 10, 10, accent, rx=0, opacity=0.88))
    body_text = {"x": body_box["x"], "y": body_box["y"], "width": body_box["width"], "height": min(46, body_box["height"])}
    callout_text = {"x": callout_box["x"], "y": callout_box["y"], "width": callout_box["width"], "height": min(46, callout_box["height"])}
    body_copy = f"输入：{labels[0]} / {labels[1]} / {labels[2]}" if body_box["width"] < 220 else summary
    body.extend(
        [
            contract_text(spec, "body", body_text, body_copy, role="body", size=13, weight=600, color="#334155"),
            contract_text(spec, "callout", callout_text, " / ".join(labels), role="callout", size=12, weight=800, color=accent),
            contract_footer(page, spec, boxes),
        ]
    )
    report.add(page, "contract-flow", "contract.flow", bbox(flow["x"], flow["y"], flow["width"], flow["height"]), ["path", "annotation", "typography"], effects=evidence_effects(spec, ["path", "connector_flow", "typography", "flow_lanes", "phase_spine", "full_page_archetype"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_comparison(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 48, 720, 54))
    table = contract_box(boxes, "table", fallback=(84, 204, 792, 190))
    left_panel = contract_box(boxes, "left_panel", "left-panel", fallback=(72, 136, 384, 300))
    right_panel = contract_box(boxes, "right_panel", "right-panel", fallback=(504, 136, 384, 300))
    rows_data = comparison_rows_for_topic(spec, text_from_any(spec.get("_deck_title")))
    body = [
        *contract_background(page, accent, spec),
        contract_text(spec, "title", title_box, title, role="title", size=22, weight=900),
        rect("comparison-left-panel", left_panel["x"], left_panel["y"], left_panel["width"], left_panel["height"], "#EEF2FF", rx=0, opacity=0.72),
        rect("comparison-right-panel", right_panel["x"], right_panel["y"], right_panel["width"], right_panel["height"], "#ECFDF5", rx=0, opacity=0.72),
        rect("comparison-table-frame", table["x"], table["y"], table["width"], table["height"], "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 2}),
    ]
    rows = 3
    cols = 2
    for row in range(1, rows):
        y = table["y"] + row * table["height"] // rows
        body.append(rect(f"comparison-row-band-{row}", table["x"], y - 2, table["width"], 4, accent, rx=0, opacity=0.12))
        body.append(line(f"comparison-row-{row}", table["x"], y, table["x"] + table["width"], y, "#CBD5E1", **{"stroke-width": 1}))
    body.append(line("comparison-mid-line", table["x"] + table["width"] // 2, table["y"], table["x"] + table["width"] // 2, table["y"] + table["height"], "#CBD5E1", **{"stroke-width": 1}))
    for index, (row_label, left_copy, right_copy) in enumerate(rows_data, 1):
        row_y = table["y"] + (index - 1) * table["height"] // rows
        body.append(text_box(f"comparison-dimension-{index}", table["x"] + 14, row_y + 12, 62, 22, row_label, size=11, weight=900, color=accent))
        body.append(text_box(f"comparison-left-value-{index}", table["x"] + 88, row_y + 14, table["width"] // 2 - 112, 30, left_copy, size=12, weight=700, color="#334155"))
        body.append(text_box(f"comparison-right-value-{index}", table["x"] + table["width"] // 2 + 28, row_y + 14, table["width"] // 2 - 60, 30, right_copy, size=12, weight=800, color="#0F172A"))
    accent_path = f"M{table['x']} {table['y'] - 24} L{table['x'] + 132} {table['y'] - 24} L{table['x'] + 148} {table['y'] - 16}"
    body.extend([path("comparison-accent-path", accent_path, stroke=accent, **{"stroke-width": 3, "opacity": 0.54}), contract_footer(page, spec, boxes)])
    report.add(page, "contract-comparison", "contract.comparison", bbox(table["x"], table["y"], table["width"], table["height"]), ["path", "geometric_shape", "typography"], effects=evidence_effects(spec, ["path", "typography", "decision_matrix", "contrast_panels", "semantic_labels"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_hub(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 46, 660, 52))
    visual = visual_box_for_contract(spec, boxes, (92, 132, 776, 300))
    legend = contract_box(boxes, "legend", "body", fallback=(126, 454, 708, 26))
    cx = visual["x"] + visual["width"] // 2
    cy = visual["y"] + visual["height"] // 2
    radius = min(118, max(70, min(visual["width"], visual["height"]) // 3))
    labels = topic_node_labels(spec, text_from_any(spec.get("_deck_title")), count=5)
    body = [
        *contract_background(page, accent, spec),
        contract_text(spec, "title", title_box, title, role="title", size=22, weight=900),
        rect("hub-backplane", visual["x"], visual["y"], visual["width"], visual["height"], "#F8FAFC", rx=0, stroke="#D8E2EE", **{"stroke-width": 1}),
        path("hub-sector-1", f"M{cx} {cy} L{cx + radius + 58} {cy - 82} L{cx + radius + 80} {cy + 28} Z", fill=accent, opacity=0.12),
        path("hub-sector-2", f"M{cx} {cy} L{cx - radius - 74} {cy - 52} L{cx - radius - 38} {cy + 92} Z", fill=accent, opacity=0.09),
        rect("hub-satellite-panel-1", visual["x"] + 36, visual["y"] + 34, 138, 46, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.92}),
        rect("hub-satellite-panel-2", visual["x"] + visual["width"] - 174, visual["y"] + visual["height"] - 80, 138, 46, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.92}),
        rect("capability-orbit-outer", cx - radius - 42, cy - radius - 42, (radius + 42) * 2, (radius + 42) * 2, "none", rx=0, stroke=accent, **{"stroke-width": 2, "opacity": 0.18}),
        rect("capability-orbit-inner", cx - radius + 8, cy - radius + 8, (radius - 8) * 2, (radius - 8) * 2, "none", rx=0, stroke=accent, **{"stroke-width": 2, "opacity": 0.16}),
        rect("capability-center", cx - 42, cy - 42, 84, 84, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 4}),
        rect("capability-center-glow", cx - 66, cy - 66, 132, 132, accent, rx=0, opacity=0.08),
    ]
    for index, angle in enumerate((0, 72, 144, 216, 288), 1):
        radians = math.radians(angle)
        x = int(cx + math.cos(radians) * radius)
        y = int(cy + math.sin(radians) * radius)
        body.append(line(f"capability-spoke-{index}", cx, cy, x, y, accent, **{"stroke-width": 2, "opacity": 0.62}))
        body.append(circle(f"capability-icon-node-{index}", x, y, 20, "#E0F2FE"))
        body.append(circle(f"capability-icon-dot-{index}", x, y, 6, accent, opacity=0.72))
    legend_copy = " / ".join(labels)
    body.extend([contract_text(spec, "legend", legend, legend_copy, role="body", size=12, weight=600, color="#334155", align="center"), contract_footer(page, spec, boxes)])
    hub_box_x = min(visual["x"], legend["x"])
    hub_box_y = min(visual["y"], legend["y"])
    hub_box_right = max(visual["x"] + visual["width"], legend["x"] + legend["width"])
    hub_box_bottom = max(visual["y"] + visual["height"], legend["y"] + legend["height"])
    report.add(page, "contract-hub", "contract.hub", bbox(hub_box_x, hub_box_y, hub_box_right - hub_box_x, hub_box_bottom - hub_box_y), ["geometric_shape", "connector", "typography", "icon"], effects=evidence_effects(spec, ["connector_flow", "typography", "hub_spoke", "sector_field", "semantic_labels", "full_page_archetype"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_bar(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 42, 680, 48))
    takeaway = contract_box(boxes, "takeaway", "body", fallback=(66, 94, 660, 34))
    chart = contract_box(boxes, "chart", fallback=(86, 154, 650, 296))
    callout = contract_box(boxes, "callout", "annotation", fallback=(748, 168, 150, 168))
    labels = topic_node_labels(spec, text_from_any(spec.get("_deck_title")), count=4)
    body = [
        *contract_background(page, accent, spec),
        contract_text(spec, "title", title_box, title, role="title", size=22, weight=900),
        contract_text(spec, "body", takeaway, summary, role="body", size=12, weight=600, color="#334155"),
        rect("bar-plot-backplane", chart["x"] - 18, chart["y"] - 20, chart["width"] + 38, chart["height"] + 34, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1}),
        rect("bar-insight-strip", callout["x"] - 18, callout["y"] - 20, callout["width"] + 36, callout["height"] + 40, accent, rx=0, opacity=0.11),
        path("bar-variance-path", f"M{chart['x'] + 76} {chart['y'] + 210} C{chart['x'] + 210} {chart['y'] + 148} {chart['x'] + 350} {chart['y'] + 180} {chart['x'] + 528} {chart['y'] + 86}", stroke=accent, **{"stroke-width": 5, "stroke-linecap": "round", "opacity": 0.28}),
    ]
    for grid_index in range(4):
        grid_y = chart["y"] + 34 + grid_index * 46
        body.append(line(f"bar-grid-{grid_index}", chart["x"], grid_y, chart["x"] + chart["width"], grid_y, "#E2E8F0", **{"stroke-width": 1, "opacity": 0.72}))
    body.append(line("bar-axis-x", chart["x"], chart["y"] + chart["height"] - 24, chart["x"] + chart["width"], chart["y"] + chart["height"] - 24, "#94A3B8", **{"stroke-width": 1}))
    for index, value in enumerate((0.42, 0.62, 0.78, 0.55), 1):
        bar_h = int((chart["height"] - 70) * value)
        x = chart["x"] + 70 + index * 90
        y = chart["y"] + chart["height"] - 24 - bar_h
        body.append(rect(f"chart-bar-shadow-{index}", x + 8, y + 8, 52, bar_h, "#94A3B8", rx=0, opacity=0.12))
        body.append(rect(f"chart-bar-{index}", x, y, 52, bar_h, accent, rx=0, opacity=0.82))
    body.extend([contract_text(spec, "callout", callout, " / ".join(labels[:3]), role="callout", size=12, weight=800, color=accent, align="center"), contract_footer(page, spec, boxes)])
    report.add(page, "contract-bar", "contract.bar", bbox(chart["x"], chart["y"], chart["width"], chart["height"]), ["geometric_shape", "typography", "micro_chart"], effects=evidence_effects(spec, ["chart_geometry", "typography", "insight_strip", "full_page_archetype"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_annotation(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(64, 56, 640, 56))
    spotlight = contract_box(boxes, "spotlight", "visual", fallback=(88, 146, 532, 248))
    callout = contract_box(boxes, "callout", "note", fallback=(650, 168, 218, 176))
    caption = contract_box(boxes, "caption", "body", fallback=(104, 418, 720, 38))
    labels = topic_node_labels(spec, text_from_any(spec.get("_deck_title")), count=4)
    body_copy = summary or " / ".join(labels)
    body = [
        *contract_background(page, accent, spec),
        contract_text(spec, "title", title_box, title, role="title", size=24, weight=900),
        rect("spotlight-stage", spotlight["x"], spotlight["y"], spotlight["width"], spotlight["height"], "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.96}),
        rect("spotlight-focus-field", spotlight["x"] + 38, spotlight["y"] + 42, spotlight["width"] - 76, spotlight["height"] - 84, accent, rx=0, opacity=0.10),
        rect("spotlight-focus-core", spotlight["x"] + spotlight["width"] // 2 - 56, spotlight["y"] + spotlight["height"] // 2 - 40, 112, 80, "#FFFFFF", rx=0, stroke=accent, **{"stroke-width": 4}),
        path("spotlight-annotation-line-1", f"M{spotlight['x'] + spotlight['width'] // 2 + 56} {spotlight['y'] + spotlight['height'] // 2 - 12} L{callout['x'] - 24} {callout['y'] + 36}", stroke=accent, **{"stroke-width": 4, "stroke-linecap": "round", "opacity": 0.58}),
        path("spotlight-annotation-line-2", f"M{spotlight['x'] + spotlight['width'] // 2 + 56} {spotlight['y'] + spotlight['height'] // 2 + 28} L{callout['x'] - 24} {callout['y'] + 108}", stroke=accent, **{"stroke-width": 3, "stroke-linecap": "round", "opacity": 0.42}),
        rect("annotation-callout-panel", callout["x"], callout["y"], callout["width"], callout["height"], "#E0F2FE", rx=0, stroke=accent, **{"stroke-width": 3}),
        rect("annotation-callout-rail", callout["x"], callout["y"], 10, callout["height"], accent, rx=0, opacity=0.62),
        text_box("spotlight-label", spotlight["x"] + spotlight["width"] // 2 - 82, spotlight["y"] + spotlight["height"] // 2 - 8, 164, 18, labels[0], size=12, weight=900, color=accent, align="center"),
        text_box("annotation-callout-label", callout["x"] + 24, callout["y"] + 24, callout["width"] - 44, 20, labels[1] if len(labels) > 1 else "关键观察", size=11, weight=900, color=accent),
        text_box("annotation-callout-copy", callout["x"] + 24, callout["y"] + 58, callout["width"] - 44, 70, body_copy, size=13, weight=700, color="#334155"),
        text_box("annotation-caption", caption["x"], caption["y"], caption["width"], caption["height"], " / ".join(labels), size=12, weight=750, color="#475569", align="center"),
        contract_footer(page, spec, boxes),
    ]
    report.add(page, "contract-annotation", "contract.annotation", bbox(spotlight["x"], spotlight["y"], callout["x"] + callout["width"] - spotlight["x"], max(spotlight["height"], callout["y"] + callout["height"] - spotlight["y"])), ["geometric_shape", "annotation", "typography"], effects=evidence_effects(spec, ["spotlight", "annotation", "semantic_labels"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_closing(page: int, accent: str, spec: dict[str, Any], boxes: dict[str, dict[str, int]], title: str, summary: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    title_box = contract_box(boxes, "title", fallback=(72, 96, 620, 104))
    body_box = contract_box(boxes, "body", fallback=(76, 240, 520, 96))
    cta = contract_box(boxes, "callout", "cta", fallback=(628, 248, 236, 88))
    steps = ["双走廊", "三场景", "一中台"]
    body = [
        *contract_background(page, accent, spec),
        rect("closing-backplane", 64, 74, 832, 374, "#FFFFFF", rx=0, stroke="#D8E2EE", **{"stroke-width": 1, "opacity": 0.94}),
        path("closing-route-ribbon", "M84 392 C220 356 348 414 496 382 C622 354 730 386 862 338 L862 372 C724 412 624 382 504 410 C348 444 218 386 84 422 Z", fill=accent, opacity=0.10),
        path("closing-horizon-path", f"M76 390 C210 360 360 420 500 386 C640 348 760 408 864 360", stroke=accent, **{"stroke-width": 11, "stroke-linecap": "round", "opacity": 0.24}),
        rect("spotlight-callout-panel", cta["x"], cta["y"], cta["width"], cta["height"], "#E0F2FE", rx=0, stroke=accent, **{"stroke-width": 3}),
        rect("spotlight-callout-accent", cta["x"], cta["y"], 10, cta["height"], accent, rx=0, opacity=0.66),
        contract_text(spec, "title", title_box, title, role="title", size=28, weight=900),
        contract_text(spec, "body", body_box, summary, role="body", size=15, weight=650, color="#334155"),
        contract_text(spec, "callout", cta, "双走廊 / 三场景 / 一中台", role="callout", size=14, weight=900, color=accent, align="center"),
        contract_footer(page, spec, boxes),
    ]
    for index, step in enumerate(steps, 1):
        x = 76 + (index - 1) * 166
        body.append(rect(f"closing-step-card-{index}", x, 356, 138, 52, "#FFFFFF", rx=0, stroke="#CBD5E1", **{"stroke-width": 1}))
        body.append(rect(f"closing-step-index-{index}", x, 356, 28, 52, accent, rx=0, opacity=0.18))
    report.add(page, "contract-closing", "contract.closing", bbox(64, 74, 832, 374), ["path", "geometric_shape", "typography", "annotation"], effects=evidence_effects(spec, ["spotlight", "typography", "closing_ribbon", "action_cards", "full_page_archetype"]), source_trace=source_trace, asset_id=asset_id)
    return body


def render_contract_slide(page: int, kind: str, title: str, summary: str, asset_id: str, accent: str, spec: dict[str, Any], report: ComponentReport, deck_title: str) -> str:
    spec = dict(spec)
    spec["_deck_title"] = deck_title
    boxes = layout_boxes_by_role(spec)
    page_type = text_from_any(spec.get("page_type"))
    source_trace = asset_id or f"svglide-contract:{page_type or kind}"
    title = contract_title(spec, kind, deck_title)
    summary = contract_summary(spec, summary)
    if page_type == "cover" or kind == "cover":
        body = render_contract_cover(page, accent, spec, boxes, title, summary, report, source_trace, asset_id, deck_title)
    elif page_type == "agenda" or kind == "agenda":
        body = render_contract_agenda(page, accent, spec, boxes, title, report, source_trace, asset_id)
    elif page_type == "section_divider" or kind == "section":
        body = render_contract_section(page, accent, spec, boxes, title, summary, report, source_trace, asset_id, deck_title)
    elif page_type == "kpi_overview" or kind == "kpi_cards":
        body = render_contract_dashboard(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    elif page_type in {"roadmap", "process_flow"} or kind in {"timeline", "process_flow"}:
        body = render_contract_flow(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    elif page_type == "comparison" or kind == "comparison_table":
        body = render_contract_comparison(page, accent, spec, boxes, title, report, source_trace, asset_id)
    elif page_type == "capability_map" or kind == "hub_spoke":
        body = render_contract_hub(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    elif page_type == "chart_takeaway" or kind == "bar_chart":
        body = render_contract_bar(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    elif page_type == "insight_callout" or kind == "insight_callout":
        body = render_contract_annotation(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    elif page_type == "closing" or kind == "closing":
        body = render_contract_closing(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    else:
        body = render_contract_flow(page, accent, spec, boxes, title, summary, report, source_trace, asset_id)
    motifs = theme_effects(spec, deck_title)
    if motifs:
        report.add(
            page,
            f"theme-{theme_key(spec, deck_title)}",
            "theme.visual_language",
            bbox(0, 0, W, H),
            ["path", "geometric_shape"],
            effects=motifs,
            source_trace=f"theme:{theme_key(spec, deck_title)}",
            asset_id=asset_id,
        )
    return svg_wrap(page, accent, body)


def label(prefix: str, x: int, y: int, width: int, text: str, *, color: str = MUTED) -> str:
    return text_box(prefix, x, y, width, 18, text, size=9, weight=700, color=color)


def stat(prefix: str, x: int, y: int, value: str, caption: str, accent: str) -> list[str]:
    return [
        text_box(f"{prefix}-value", x, y, 150, 40, value, size=28, weight=900, color=accent),
        text_box(f"{prefix}-caption", x, y + 42, 150, 18, caption, size=8, weight=700, color=MUTED),
    ]


def merged_spec(spec: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(spec, dict):
        return {}
    out: dict[str, Any] = {}
    visual_plan = spec.get("visual_plan")
    if isinstance(visual_plan, dict):
        out.update(visual_plan)
    out.update(spec)
    return out


def spec_text(spec: dict[str, Any], keys: list[str], fallback: str = "") -> str:
    for key in keys:
        value = text_from_any(spec.get(key))
        if value:
            return value
    return fallback


def spec_dict(spec: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = spec.get(key)
        if isinstance(value, dict):
            return value
    return {}


def spec_list(spec: dict[str, Any], keys: list[str]) -> list[Any]:
    for key in keys:
        value = spec.get(key)
        if isinstance(value, list):
            return value
    return []


def clean_items(items: list[Any], limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str) and item.strip():
            out.append({"label": item.strip()})
        if len(out) >= limit:
            break
    return out


def item_text(item: dict[str, Any], keys: list[str], fallback: str = "") -> str:
    for key in keys:
        value = text_from_any(item.get(key))
        if value:
            return value
    return fallback


def item_color(item: dict[str, Any], fallback: str) -> str:
    color = text_from_any(item.get("color") or item.get("accent") or item.get("fill"))
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        return color.upper()
    return fallback


def slug_id(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def split_hero_title(title: str) -> str:
    title = title.strip() or "Untitled"
    if "\n" in title:
        return title
    if "·" in title:
        return title.replace("·", "·\n", 1)
    words = title.split()
    if len(words) >= 4:
        midpoint = len(words) // 2
        return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])
    if len(title) > 14:
        midpoint = len(title) // 2
        return title[:midpoint] + "\n" + title[midpoint:]
    return title


def metric_items(spec: dict[str, Any], defaults: list[tuple[str, str, str, str]]) -> list[tuple[str, str, str, str]]:
    raw_items = clean_items(spec_list(spec, ["metrics", "kpis", "cards", "items"]), len(defaults))
    if not raw_items:
        return defaults
    out: list[tuple[str, str, str, str]] = []
    for index, item in enumerate(raw_items):
        default = defaults[min(index, len(defaults) - 1)]
        out.append(
            (
                item_text(item, ["value", "number", "metric"], default[0]),
                item_text(item, ["label", "name", "title"], default[1]),
                item_text(item, ["note", "caption", "description"], default[2]),
                item_color(item, default[3]),
            )
        )
    while len(out) < len(defaults):
        out.append(defaults[len(out)])
    return out


def numeric_weight(value: str, fallback: float) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return fallback
    try:
        return max(1.0, float(match.group(0)))
    except ValueError:
        return fallback


def renderer_family(kind: str) -> str:
    if kind in {"cover", "editor_note", "closing"}:
        return f"layout.{kind}"
    if kind == "insight_callout":
        return "contract.annotation"
    if kind == "kpi_cards":
        return "chart.kpi"
    if kind == "bubble_chart":
        return "chart.bubble"
    if kind == "donut_chart":
        return "chart.donut"
    if kind == "sankey_chart":
        return "chart.sankey"
    if kind in {"toc", "chapter", "content", "ending", "reference_style"}:
        return f"layout.{kind}"
    chart_groups = {
        "line": {"line_chart", "area_chart", "stacked_area_chart", "dual_axis_line_chart"},
        "bar": {"bar_chart", "horizontal_bar_chart", "grouped_bar_chart", "stacked_bar_chart", "waterfall_chart", "pareto_chart", "butterfly_chart"},
        "proportion": {"pie_chart", "donut_chart", "treemap_chart", "funnel_chart", "sankey_chart"},
        "matrix": {"matrix_2x2", "quadrant_text_bullets", "quadrant_bubble_scatter", "heatmap_chart", "comparison_table", "feature_matrix_table", "harvey_balls_table"},
        "flow": {"process_flow", "pipeline_with_stages", "timeline", "roadmap_vertical", "gantt_chart", "journey_map", "snake_flow", "numbered_steps"},
        "hub": {"hub_spoke", "hub_inward_arrows", "mind_map", "top_down_tree", "client_server_flow", "module_composition", "layered_architecture"},
        "radial": {"circular_stages", "segmented_wheel", "concentric_circles", "radar_chart", "venn_diagram", "gauge_chart"},
        "table": {"basic_table", "consulting_table", "project_schedule_table", "financial_statement_table"},
    }
    for family, names in chart_groups.items():
        if kind in names:
            return f"chart.{family}"
    return "chart.framework"


def render_demo_slide(
    *,
    page: int,
    kind: str,
    title: str,
    summary: str,
    asset_id: str = "",
    accent: str = "#4A90E2",
    spec: dict[str, Any] | None = None,
    report: ComponentReport | None = None,
) -> str:
    renderer_id = renderer_family(kind)
    report = report or ComponentReport()
    payload = merged_spec(spec)
    source_trace = asset_id or f"svglide-pattern:{kind}"
    if kind == "cover":
        body = editorial_background(page, accent)
    else:
        body = editorial_shell(page, accent, title, summary)
    report.add(page, "title-block", renderer_id, bbox(70, 40, 700, 114), ["typography", "geometric_shape"], effects=["editorial_hierarchy"], source_trace=source_trace, asset_id=asset_id)

    if kind == "cover":
        body.extend(render_cover_visual(page, accent, title, summary, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "editor_note":
        body.extend(render_editor_note_visual(page, accent, title, summary, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "closing":
        body.extend(render_closing_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "kpi_cards":
        body.extend(render_kpi_cards_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "bubble_chart":
        body.extend(render_bubble_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "donut_chart":
        body.extend(render_donut_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif kind == "sankey_chart":
        body.extend(render_sankey_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif renderer_id.startswith("layout."):
        body.extend(render_layout_visual(page, kind, accent, report, source_trace, asset_id))
    elif renderer_id == "chart.line":
        body.extend(render_line_visual(page, accent, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.bar":
        body.extend(render_bar_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.proportion":
        body.extend(render_proportion_visual(page, accent, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.matrix":
        body.extend(render_matrix_visual(page, accent, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.flow":
        body.extend(render_flow_visual(page, accent, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.hub":
        body.extend(render_hub_visual(page, accent, payload, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.radial":
        body.extend(render_radial_visual(page, accent, report, renderer_id, source_trace, asset_id))
    elif renderer_id == "chart.table":
        body.extend(render_table_visual(page, accent, report, renderer_id, source_trace, asset_id))
    else:
        body.extend(render_framework_visual(page, accent, report, renderer_id, source_trace, asset_id))
    body.append(editorial_footer(page))
    report.add(page, "footer", renderer_id, bbox(64, 480, 832, 18), ["typography"], source_trace=source_trace)
    return svg_wrap(page, accent, body)


def render_cover_visual(page: int, accent: str, title: str, summary: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    kicker = spec_text(spec, ["kicker", "eyebrow", "section_label"], "GLOBAL AI CAPITAL / EDITORIAL BRIEFING")
    hero_title = split_hero_title(spec_text(spec, ["cover_title", "title"], title))
    subtitle = spec_text(spec, ["cover_subtitle", "body", "subtitle", "summary"], summary or "Capital, compute, and the closed-loop race for strategic control")
    year = spec_text(spec, ["year", "date", "period"], "2026")
    meta_1 = spec_text(spec, ["meta_1", "meta_primary", "right_label"], "INDUSTRY BRIEFING")
    meta_2 = spec_text(spec, ["meta_2", "meta_secondary", "right_note"], "AI INFRA\nCAPITAL MAP")
    body = [
        rect("cover-atmosphere", 0, 0, W, H, "#05070B", opacity=0.38),
        rect("cover-left-rail", 68, 74, 7, 348, RED, rx=0),
        rect("cover-master-rule", 94, 388, 520, 5, accent, rx=0),
        rect("cover-master-rule-muted", 632, 424, 142, 5, "#6D737D", rx=0),
        text_box("cover-kicker", 96, 76, 430, 18, kicker, size=9, weight=900, color=accent, family=SERIF, letter_spacing=2),
        text_box("title", 96, 126, 700, 160, hero_title, size=64, weight=900, color=INK, family=SERIF, line_height=1.08),
        text_box("cover-master-title", 98, 304, 560, 48, subtitle, size=19, weight=800, color=GOLD, family=SERIF, line_height=1.18),
        text_box("cover-year", 684, 72, 180, 54, year, size=40, weight=900, color=INK, align="right", family=SERIF),
        rect("cover-meta-rule", 746, 306, 92, 3, RED, rx=0),
        text_box("cover-meta-1", 704, 322, 136, 30, meta_1, size=8, weight=900, color=accent, align="right", family=SERIF, letter_spacing=1.5),
        text_box("cover-meta-2", 704, 360, 136, 44, meta_2, size=10, weight=900, color=MUTED, align="right"),
    ]
    for index in range(20):
        x = 880 + (index % 2) * 18
        y = 82 + (index // 2) * 32
        r = 2 if index % 3 else 3
        body.append(circle(f"cover-particle-{index+1}", x, y, r, accent if index % 2 else RED, opacity=0.28))
    body.extend(asset_mark("slash", 820, 418, 0.9, RED, opacity=0.48))
    for index, y in enumerate((438, 452, 466), 1):
        body.append(line(f"cover-data-line-{index}", 96, y, 846 - index * 78, y, "#28313D", **{"stroke-width": 1}))
    report.add(page, "cover-hero", renderer_id, bbox(68, 72, 796, 396), ["geometric_shape", "typography", "annotation"], effects=["editorial_cover", "large_hero_type"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_editor_note_visual(page: int, accent: str, title: str, summary: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    thesis = spec_text(spec, ["thesis", "key_message", "claim", "title"], "三组数字，足以定义 2026 年的 AI 资本格局。")
    copy = spec_text(spec, ["copy", "body", "description", "summary"], summary or "Capital is no longer a financing footnote; it is the operating system for compute, model access, and strategic control.")
    metrics = metric_items(
        spec,
        [
            ("$297B", "Q1 global venture capital", "", RED),
            ("$188B", "AI captured the majority", "", "#F4A261"),
        ],
    )
    side = spec_dict(spec, ["side_note", "sidebar", "question"])
    side_label = item_text(side, ["label", "title"], spec_text(spec, ["side_label"], "EDITORIAL\nQUESTION"))
    side_copy = item_text(side, ["copy", "note", "body"], spec_text(spec, ["side_copy"], "Who controls the capital loop when compute becomes scarce?"))
    body = [
        rect("note-panel", 82, 176, 666, 246, PANEL, rx=0, stroke=RULE, **{"stroke-width": 1}),
        *asset_mark("quote_ticks", 102, 188, 1.0, RED, opacity=0.95),
        rect("note-quote", 124, 238, 5, 92, accent, rx=0),
        text_box("note-thesis", 154, 206, 520, 54, thesis, size=24, weight=900, color=INK, family=SERIF),
        text_box("note-copy", 154, 274, 512, 44, copy, size=12, weight=600, color=MUTED),
        text_box("note-stat-a-value", 154, 328, 210, 66, metrics[0][0], size=50, weight=900, color=metrics[0][3], family=SERIF),
        text_box("note-stat-a-caption", 158, 400, 178, 18, metrics[0][1] or metrics[0][2], size=8, weight=800, color=MUTED),
        text_box("note-stat-b-value", 402, 328, 210, 66, metrics[1][0], size=50, weight=900, color=metrics[1][3], family=SERIF),
        text_box("note-stat-b-caption", 406, 400, 178, 18, metrics[1][1] or metrics[1][2], size=8, weight=800, color=MUTED),
        rect("note-side", 770, 184, 108, 226, "#0A0E14", rx=0, stroke="#222B36", **{"stroke-width": 1}),
        rect("note-side-accent", 770, 184, 108, 5, RED, rx=0),
        text_box("note-side-label", 786, 216, 76, 34, side_label, size=8, weight=900, color=accent, align="center"),
        text_box("note-side-copy", 786, 286, 76, 74, side_copy, size=9, weight=800, color=GOLD, align="center"),
    ]
    report.add(page, "editor-note-panel", renderer_id, bbox(82, 176, 796, 246), ["geometric_shape", "typography", "annotation"], effects=["editorial_note", "hero_metrics"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_closing_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = [
        rect("closing-list", 86, 174, 650, 260, PANEL, rx=0, stroke=RULE, **{"stroke-width": 1}),
        text_box("closing-section-label", 108, 188, 210, 18, spec_text(spec, ["section_label", "label"], "SIX TAKEAWAYS"), size=10, weight=900, color=RED),
    ]
    defaults = ["资本约束将先于模型约束", "算力采购成为战略资产负债表", "闭环投资提高生态锁定", "主权资本进入 AI 基建底层", "赢家从模型公司扩展到电力与网络", "现金流证明会替代叙事融资"]
    raw_items = clean_items(spec_list(spec, ["takeaways", "items", "bullets"]), 6)
    items = [(f"{index+1:02d}", item_text(item, ["copy", "text", "label", "title"], defaults[index])) for index, item in enumerate(raw_items)]
    while len(items) < 6:
        items.append((f"{len(items)+1:02d}", defaults[len(items)]))
    for index, (num, copy) in enumerate(items):
        col = index % 2
        row = index // 2
        x = 108 + col * 308
        y = 222 + row * 58
        body.append(rect(f"closing-red-index-{index+1}", x, y, 42, 34, RED if index == 0 else "#24171C", rx=0, stroke=RED, **{"stroke-width": 1}))
        body.append(text_box(f"closing-num-{index+1}", x + 5, y + 8, 32, 14, num, size=10, weight=900, color=INK if index == 0 else RED, align="center"))
        body.append(text_box(f"closing-copy-{index+1}", x + 58, y + 1, 210, 32, copy, size=13, weight=900, color=INK))
        body.append(line(f"closing-rule-{index+1}", x + 58, y + 42, x + 268, y + 42, RULE, **{"stroke-width": 1}))
    body.extend([
        rect("closing-critical", 86, 430, 650, 34, "#151D27", rx=0),
        rect("closing-critical-bar", 86, 430, 6, 34, accent),
        text_box("closing-critical-copy", 112, 439, 520, 16, spec_text(spec, ["critical_copy", "closing_statement", "callout"], "This is not yet the bubble bursting. It is the bubble compounding."), size=10, weight=900, color=GOLD),
        rect("closing-sidebar", 762, 190, 112, 220, "#0A0E14", rx=0, stroke="#222B36", **{"stroke-width": 1}),
        text_box("closing-sidebar-text", 782, 226, 72, 116, spec_text(spec, ["sidebar", "sidebar_text"], "CAPITAL\nDISCIPLINE\nREPLACES\nNARRATIVE\nFINANCE"), size=10, weight=900, color=MUTED, align="center"),
        rect("closing-sidebar-rule", 786, 366, 64, 4, RED, rx=0),
    ])
    report.add(page, "closing-system", renderer_id, bbox(86, 174, 788, 308), ["geometric_shape", "typography", "annotation"], effects=["closing_takeaways", "numbered_hierarchy"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_kpi_cards_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = []
    defaults = [
        ("$297B", "单季 VC 总额 / Q1 VC", "single-quarter record", RED),
        ("81%", "AI 占全季 VC / AI share", "of disclosed capital", "#F4A261"),
        ("$188B", "Top 4 笔大单 / Top 4 deals", "OpenAI · Anthropic · xAI · Waymo", "#B8B2A9"),
        ("65%", "集中度 / Concentration", "Top 4 share of global VC", RED),
    ]
    values = metric_items(spec, defaults)
    for index, (value, label_text, note, color) in enumerate(values):
        col = index % 2
        row = index // 2
        x = 78 + col * 260
        y = 184 + row * 126
        body.append(rect(f"kpi-card-{index+1}", x, y, 230, 116, PANEL, rx=0, stroke=RULE, **{"stroke-width": 1}))
        body.append(rect(f"kpi-card-accent-{index+1}", x, y, 4, 52, color, rx=0))
        body.append(text_box(f"kpi-label-{index+1}", x + 22, y + 18, 170, 16, label_text, size=8, weight=800, color=MUTED))
        body.append(text_box(f"kpi-value-{index+1}", x + 22, y + 36, 168, 56, value, size=42, weight=900, color=INK, family=SERIF, line_height=1.0))
        body.append(text_box(f"kpi-note-{index+1}", x + 22, y + 94, 178, 14, note, size=8, weight=700, color=GOLD))
    insight = spec_dict(spec, ["insight", "observation", "callout"])
    insight_label = item_text(insight, ["label"], "EDITORIAL NOTE")
    insight_title = item_text(insight, ["title", "headline"], "钱没变多，\n是更集中。")
    insight_copy = item_text(insight, ["copy", "body", "note"], "Capital concentrated into a select few companies and a single industry.")
    insight_number = item_text(insight, ["number", "value", "metric"], "$172B")
    body.extend([
        line("kpi-note-divider", 610, 184, 610, 438, RULE, **{"stroke-width": 1}),
        text_box("kpi-observation-label", 634, 202, 160, 16, insight_label, size=8, weight=900, color=RED),
        line("kpi-observation-rule", 634, 224, 736, 224, RED, **{"stroke-width": 1}),
        rect("kpi-observation-title-back", 626, 246, 208, 82, "#090D13", rx=0, opacity=0.58),
        text_box("kpi-observation-title", 634, 258, 180, 60, insight_title, size=22, weight=900, color=INK, family=SERIF),
        text_box("kpi-observation-copy", 634, 336, 190, 58, insight_copy, size=9, weight=700, color=GOLD),
        text_box("kpi-observation-number", 646, 404, 152, 36, insight_number, size=28, weight=900, color=RED, align="right", family=SERIF),
    ])
    report.add(page, "kpi-card-set", renderer_id, bbox(78, 184, 746, 254), ["geometric_shape", "typography", "metric", "annotation"], effects=["metric_grid", "editorial_sidebar"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_bubble_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    defaults = [
        {"name": "xAI", "arr": 5, "valuation": 230, "investors": 8, "note": "$5B / $230B · 8+ investors", "color": "#F4A261"},
        {"name": "OpenAI", "arr": 24, "valuation": 852, "investors": 7, "note": "$24B / $852B · 7+ investors", "color": RED},
        {"name": "Anthropic", "arr": 30, "valuation": 380, "investors": 5, "note": "$30B / $380B · 5 investors", "color": RED},
    ]
    raw_bubbles = clean_items(spec_list(spec, ["bubbles", "bubble_points", "points", "items"]), 5) or defaults
    plot_x = 132
    plot_y = 190
    plot_w = 690
    plot_h = 224
    max_arr = numeric_weight(spec_text(spec, ["x_max", "arr_max"], "40"), 40)
    max_valuation = numeric_weight(spec_text(spec, ["y_max", "valuation_max"], "1000"), 1000)
    body = [
        line("bubble-axis-y", plot_x, plot_y, plot_x, plot_y + plot_h, "#5C6470", **{"stroke-width": 1}),
        line("bubble-axis-x", plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h, "#5C6470", **{"stroke-width": 1}),
    ]
    for index, ratio in enumerate((0.2, 0.4, 0.6, 0.8), 1):
        y = int(round(plot_y + plot_h * (1 - ratio)))
        x = int(round(plot_x + plot_w * ratio))
        body.append(rect(f"bubble-grid-y-{index}", plot_x, y, plot_w, 1, RULE, rx=0, opacity=0.42))
        body.append(text_box(f"bubble-y-label-{index}", 86, y - 7, 36, 14, f"${int(max_valuation * ratio)}B", size=8, weight=700, color="#5C6470", align="right", family=SERIF))
        body.append(text_box(f"bubble-x-label-{index}", x - 20, plot_y + plot_h + 10, 40, 14, f"${int(max_arr * ratio)}B", size=8, weight=700, color="#5C6470", align="center", family=SERIF))
    body.extend([
        text_box("bubble-y-axis-title", plot_x, 170, 120, 14, "VALUATION ($B)", size=8, weight=800, color=MUTED, align="left", family=SERIF, letter_spacing=1),
        text_box("bubble-x-axis-title", 410, 438, 178, 12, "ANNUALIZED REVENUE (ARR, $B)", size=8, weight=800, color=MUTED, align="center", family=SERIF, letter_spacing=1),
        path("bubble-fair-line", f"M{plot_x + 44} {plot_y + plot_h - 4} L{plot_x + plot_w - 18} {plot_y + 22}", stroke="#8A857E", **{"stroke-width": 1, "stroke-dasharray": "6 4", "opacity": 0.54}),
        text_box("bubble-fair-line-label", 650, 182, 172, 14, spec_text(spec, ["reference_label"], "implied fair valuation trend"), size=8, weight=700, color=MUTED, align="right", family=SERIF),
    ])
    for index, item in enumerate(raw_bubbles):
        default = defaults[min(index, len(defaults) - 1)]
        name = item_text(item, ["name", "label", "title"], str(default["name"]))
        arr = numeric_weight(item_text(item, ["arr", "revenue", "x", "x_value"], str(default["arr"])), float(default["arr"]))
        valuation = numeric_weight(item_text(item, ["valuation", "value", "y", "y_value"], str(default["valuation"])), float(default["valuation"]))
        investors = numeric_weight(item_text(item, ["investors", "size", "weight"], str(default["investors"])), float(default["investors"]))
        color = item_color(item, str(default["color"]))
        note = item_text(item, ["note", "caption", "description"], str(default["note"]))
        x = int(round(plot_x + min(arr, max_arr) / max_arr * plot_w))
        y = int(round(plot_y + plot_h - min(valuation, max_valuation) / max_valuation * plot_h))
        radius = int(round(18 + investors * 3.8))
        item_id = f"bubble-{slug_id(name)}"
        label_x = x - 68
        note_x = x - 96
        label_y = y + radius + 18
        note_y = label_y + 18
        if index == 0:
            label_x = x - 20
            note_x = x - 20
            label_y = y - radius - 36
            note_y = label_y + 24
        elif index == 1:
            label_x = x - 236
            note_x = x - 256
            label_y = 160
            note_y = 184
        elif index == 2:
            label_x = x + 42
            note_x = x + 42
            label_y = y - 14
            note_y = label_y + 24
        elif y > plot_y + plot_h * 0.58:
            label_y = y - radius - 32
            note_y = label_y + 24
        body.append(circle(item_id, x, y, radius, color, stroke=color, **{"stroke-width": 2, "fill-opacity": 0.2}))
        body.append(circle(f"{item_id}-center", x, y, 3, color))
        body.append(rect(f"{item_id}-name-plate", label_x - 4, label_y - 1, 144, 18, "#070A0F", rx=0, opacity=0.78))
        body.append(text_box(f"{item_id}-label", label_x, label_y, 136, 18, name, size=11, weight=900, color=INK, align="center", family=SERIF))
        body.append(text_box(f"{item_id}-note", note_x, note_y, 192, 14, note, size=8, weight=700, color=MUTED, align="center", family=SERIF))
    insight = spec_text(
        spec,
        ["insight", "observation", "callout"],
        "所有气泡都站在公允线之上：估值跑得比收入快，xAI 偏离最远，Anthropic 兑现度最高。",
    )
    body.extend([
        rect("bubble-insight-band", 82, 452, 782, 16, PANEL, rx=0),
        rect("bubble-insight-rule", 82, 452, 4, 16, RED, rx=0),
        text_box("bubble-insight-copy", 102, 455, 720, 10, insight, size=8, weight=900, color=GOLD),
    ])
    report.add(page, "bubble-chart", renderer_id, bbox(82, 190, 782, 300), ["geometric_shape", "typography", "annotation", "metric"], effects=["bubble_scatter", "axis_grid", "valuation_revenue_encoding"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_donut_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    default_segments = [
        {"name": "Amazon", "value": "$50B", "note": "41% · AWS commitment", "share": 41, "color": accent},
        {"name": "Nvidia", "value": "$30B", "note": "25% · 10GW deployment", "share": 25, "color": "#F4A261"},
        {"name": "SoftBank", "value": "$30B", "note": "25% · Stargate vehicle", "share": 25, "color": "#B8B2A9"},
        {"name": "MSFT + a16z", "value": "$12B", "note": "9% · other investors", "share": 9, "color": RED},
    ]
    segments_raw = clean_items(spec_list(spec, ["segments", "donut_segments", "investors", "items"]), 4) or default_segments
    colors = [item_color(item, default_segments[min(index, 3)]["color"]) for index, item in enumerate(segments_raw)]
    shares = [numeric_weight(item_text(item, ["share", "percent", "weight"], ""), 100.0 / max(1, len(segments_raw))) for item in segments_raw]
    share_total = sum(shares) or 1.0
    body = [
        circle("donut-track", 300, 318, 116, "none", stroke="#2C333D", **{"stroke-width": 46}),
    ]
    circumference = 729.0
    offset = 0.0
    for index, (share, color) in enumerate(zip(shares, colors), 1):
        length = circumference * share / share_total
        body.append(
            circle(
                f"donut-segment-{index}",
                300,
                318,
                116,
                "none",
                stroke=color,
                **{
                    "stroke-width": 46,
                    "stroke-dasharray": f"{round(length, 1)} 729",
                    "stroke-dashoffset": round(-offset, 1),
                    "stroke-linecap": "butt",
                    "transform": "rotate(-90 300 318)",
                },
            )
        )
        offset += length
    center = spec_dict(spec, ["center", "total", "summary_metric"])
    center_value = item_text(center, ["value", "number"], spec_text(spec, ["center_value", "total_value"], "$122B"))
    center_label = item_text(center, ["label", "title"], spec_text(spec, ["center_label"], "TOTAL ROUND"))
    center_note = item_text(center, ["note", "caption"], spec_text(spec, ["center_note"], "@ $852B post-money"))
    body.extend([
        circle("donut-hole", 300, 318, 68, BG, stroke="#3A424E", **{"stroke-width": 1}),
        rect("donut-center-value-back", 236, 288, 128, 44, "#090D13", rx=0, opacity=0.62),
        text_box("donut-center-value", 242, 292, 116, 38, center_value, size=31, weight=900, color=INK, align="center", family=SERIF),
        text_box("donut-center-label", 250, 340, 100, 18, center_label, size=8, weight=800, color=MUTED, align="center"),
        text_box("donut-center-note", 248, 362, 104, 16, center_note, size=8, weight=700, color="#5C6470", align="center"),
        line("donut-investor-divider", 560, 196, 560, 436, RULE, **{"stroke-width": 1}),
        text_box("donut-investor-label", 590, 204, 166, 16, spec_text(spec, ["legend_label"], "INVESTOR BREAKDOWN"), size=8, weight=900, color=RED),
    ])
    for index, item in enumerate(segments_raw):
        name = item_text(item, ["name", "label", "title"], default_segments[min(index, 3)]["name"])
        value = item_text(item, ["value", "number"], default_segments[min(index, 3)]["value"])
        note = item_text(item, ["note", "caption"], default_segments[min(index, 3)]["note"])
        y = 242 + index * 48
        body.append(rect(f"donut-legend-row-back-{index+1}", 604, y - 2, 218, 42, "#090D13", rx=0, opacity=0.58))
        body.append(rect(f"donut-legend-key-{index+1}", 590, y, 5, 28, colors[index], rx=0))
        body.append(text_box(f"donut-legend-name-{index+1}", 612, y + 2, 104, 18, name, size=10, weight=900, color=INK))
        body.append(text_box(f"donut-legend-value-{index+1}", 750, y, 66, 20, value, size=16, weight=900, color=colors[index], align="right", family=SERIF))
        body.append(text_box(f"donut-legend-note-{index+1}", 612, y + 23, 202, 14, note, size=8, weight=700, color=MUTED))
        body.append(line(f"donut-legend-rule-{index+1}", 590, y + 44, 816, y + 44, RULE, **{"stroke-width": 1}))
    body.extend([
        rect("donut-micro-chart-1", 390, 424, 40, 10, RED, rx=0),
        rect("donut-micro-chart-2", 434, 424, 28, 10, "#F4A261", rx=0),
        rect("donut-micro-chart-3", 466, 424, 22, 10, "#B8B2A9", rx=0),
        rect("donut-micro-chart-4", 492, 424, 16, 10, "#8A857E", rx=0),
        text_box("donut-observation", 590, 440, 292, 24, spec_text(spec, ["observation", "insight"], "Three largest investors account for 91%."), size=8, weight=900, color=GOLD),
    ])
    report.add(page, "donut-chart", renderer_id, bbox(132, 196, 684, 240), ["geometric_shape", "annotation", "typography"], effects=["donut_proportion", "investor_breakdown"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_sankey_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    origin = spec_dict(spec, ["origin", "source"])
    origin_name = item_text(origin, ["name", "label", "title"], "Nvidia")
    origin_value = item_text(origin, ["value", "number"], "$40B+")
    origin_label = item_text(origin, ["note", "caption", "subtitle"], "equity invested")
    target_defaults = [
        {"name": "OpenAI", "value": "$30B", "color": "#F4A261"},
        {"name": "xAI", "value": "~$3B", "color": "#D98E4F"},
        {"name": "Anthropic", "value": "~$2B", "color": "#B97949"},
        {"name": "CoreWeave + other", "value": "~$4B", "color": "#9B6745"},
    ]
    target_items = clean_items(spec_list(spec, ["targets", "nodes", "recipients"]), 4) or target_defaults
    return_flow = spec_dict(spec, ["return_flow", "return", "outcome"])
    return_title = item_text(return_flow, ["title", "name", "label"], "芯片采购")
    return_value = item_text(return_flow, ["value", "number"], "$100B+")
    return_note = item_text(return_flow, ["note", "caption"], "implied return")
    insight = spec_text(spec, ["insight", "caption"], "Equity checks recycle into accelerator demand and multi-year compute commitments.")
    body = [
        text_box("sankey-origin-top-label", 104, 182, 90, 14, "ORIGIN", size=8, weight=900, color="#5C6470", align="center"),
        text_box("sankey-recipient-label", 454, 182, 120, 14, "RECIPIENT", size=8, weight=900, color="#5C6470", align="center"),
        text_box("sankey-return-label", 760, 182, 112, 14, "RETURN FLOW", size=8, weight=900, color="#5C6470", align="right"),
        line("sankey-top-rule", 70, 204, 878, 204, RULE, **{"stroke-width": 1}),
    ]
    right_nodes = []
    for index, item in enumerate(target_items):
        default = target_defaults[min(index, 3)]
        right_nodes.append(
            (
                436,
                224 + index * 60,
                item_color(item, default["color"]),
                item_text(item, ["name", "label", "title"], default["name"]),
                item_text(item, ["value", "number"], default["value"]),
            )
        )
    flows = [
        ("M210 300 C300 264 338 248 436 248", RED, 30),
        ("M210 324 C300 318 348 308 436 308", "#B43A3F", 16),
        ("M210 342 C300 354 348 368 436 368", "#8E343B", 12),
        ("M210 360 C300 392 348 428 436 428", "#6E2B34", 10),
        ("M610 248 C692 248 718 300 782 300", "#F4A261", 30),
        ("M610 308 C696 308 720 328 782 328", "#F4A261", 14),
        ("M610 368 C696 368 720 352 782 352", "#F4A261", 11),
        ("M610 428 C696 428 720 380 782 380", "#F4A261", 9),
    ]
    for index, (d, color, width) in enumerate(flows, 1):
        body.append(path(f"sankey-flow-{index}", d, stroke=color, **{"stroke-width": width, "stroke-linecap": "round", "opacity": 0.62 if index <= 4 else 0.46}))
    body.extend([
        rect("sankey-origin-1", 88, 252, 122, 154, RED, rx=0, opacity=0.96),
        text_box("sankey-origin-name-1", 110, 284, 78, 18, origin_name, size=13, weight=900, color=INK, align="center"),
        text_box("sankey-origin-value-1", 100, 316, 98, 42, origin_value, size=32, weight=900, color=INK, align="center", family=SERIF),
        text_box("sankey-origin-label-1", 108, 362, 86, 18, origin_label, size=8, weight=800, color="#F7C5C8", align="center"),
    ])
    for index, (x, y, color, name, value) in enumerate(right_nodes, 1):
        body.append(rect(f"sankey-target-{index}", x, y, 174, 38, color, rx=0, opacity=0.92))
        body.append(text_box(f"sankey-target-name-{index}", x + 12, y + 11, 92, 14, name, size=9, weight=900, color="#111820"))
        body.append(text_box(f"sankey-target-value-{index}", x + 126, y + 8, 36, 18, value, size=12, weight=900, color="#111820", align="right", family=SERIF))
    body.extend([
        rect("sankey-return-block", 782, 236, 90, 186, RED, rx=0, opacity=0.82),
        text_box("sankey-return-title", 810, 266, 50, 32, return_title, size=10, weight=900, color=INK, align="center"),
        text_box("sankey-return-value", 806, 320, 58, 52, return_value, size=17, weight=900, color=INK, align="center", family=SERIF),
        text_box("sankey-return-note", 804, 392, 58, 24, return_note, size=8, weight=800, color="#F7C5C8", align="center"),
        text_box("sankey-insight", 88, 448, 650, 18, insight, size=8, weight=800, color=GOLD),
    ])
    report.add(page, "sankey-flow-system", renderer_id, bbox(70, 182, 808, 266), ["path", "geometric_shape", "connector", "typography"], effects=["flow_width_encoding", "return_flow"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_layout_visual(page: int, kind: str, accent: str, report: ComponentReport, source_trace: str, asset_id: str) -> list[str]:
    body = [
        path("layout-hero-arc", "M86 380 C240 276 360 444 526 334 C676 234 780 332 878 260", stroke=accent, **{"stroke-width": 10, "stroke-linecap": "round", "opacity": 0.72}),
        rect("layout-panel-a", 96, 190, 228, 170, "#FFFFFF", rx=10, stroke="#CBD5E1", **{"stroke-width": 2}),
        rect("layout-panel-b", 366, 184, 210, 212, "#FFFFFF", rx=10, stroke="#CBD5E1", **{"stroke-width": 2}),
        rect("layout-panel-c", 618, 202, 238, 150, "#FFFFFF", rx=10, stroke="#CBD5E1", **{"stroke-width": 2}),
        text_box("layout-kind", 370, 418, 220, 28, kind.replace("_", " ").upper(), size=17, weight=800, color=accent, align="center"),
    ]
    report.add(page, "layout-structure", f"layout.{kind}", bbox(86, 184, 792, 262), ["path", "geometric_shape", "typography"], effects=["page_rhythm"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_line_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = [line("axis-x", 120, 420, 850, 420, "#CBD5E1", **{"stroke-width": 2}), line("axis-y", 120, 185, 120, 420, "#CBD5E1", **{"stroke-width": 2})]
    points = [(150, 380), (265, 330), (380, 350), (495, 266), (610, 292), (725, 216), (830, 238)]
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    body.append(path("line-series", d, stroke=accent, **{"stroke-width": 8, "stroke-linecap": "round", "stroke-linejoin": "round"}))
    for index, (x, y) in enumerate(points, 1):
        body.append(circle(f"line-point-{index}", x, y, 8, "#FFFFFF", stroke=accent, **{"stroke-width": 4}))
    report.add(page, "line-chart", renderer_id, bbox(120, 185, 730, 235), ["path", "connector", "geometric_shape"], effects=["chart_geometry"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_bar_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = [
        line("bar-axis-x", 132, 374, 650, 374, "#5C6470", **{"stroke-width": 1}),
        line("bar-axis-y", 132, 198, 132, 374, "#5C6470", **{"stroke-width": 1}),
    ]
    for index, y in enumerate((250, 280, 310, 340, 374), 1):
        body.append(line(f"bar-grid-{index}", 132, y, 650, y, "#222B36", **{"stroke-width": 1, "stroke-dasharray": "2 4", "opacity": 0.48}))
    defaults = [
        {"name": "Meta", "value": "$200B", "amount": 200, "color": RED},
        {"name": "MSFT", "value": "$190B", "amount": 190, "color": "#B8B2A9"},
        {"name": "Google", "value": "$190B", "amount": 190, "color": "#B8B2A9"},
        {"name": "Oracle", "value": "$145B+", "amount": 145, "color": "#8A857E"},
    ]
    raw_bars = clean_items(spec_list(spec, ["bars", "bar_series", "categories", "items"]), 4) or defaults
    amounts = [numeric_weight(item_text(item, ["amount", "raw_value", "value"], str(defaults[min(index, 3)]["amount"])), float(defaults[min(index, 3)]["amount"])) for index, item in enumerate(raw_bars)]
    max_amount = max(amounts) if amounts else 1.0
    bars = []
    for index, item in enumerate(raw_bars):
        default = defaults[min(index, 3)]
        value = item_text(item, ["value", "number"], str(default["value"]))
        height = int(round(84 + (amounts[index] / max_amount) * 92))
        bars.append((item_text(item, ["name", "label", "title"], str(default["name"])), value, height, item_color(item, str(default["color"]))))
    for index, (name, value, height, color) in enumerate(bars):
        x = 188 + index * 116
        y = 374 - height
        body.append(rect(f"bar-{index+1}", x, y, 74, height, color, rx=0, opacity=0.96))
        body.append(rect(f"bar-value-back-{index+1}", x - 12, y - 30, 98, 24, "#090D13", rx=0, opacity=0.74))
        body.append(text_box(f"bar-value-{index+1}", x - 10, y - 30, 94, 24, value, size=18, weight=900, color=INK, align="center", family=SERIF))
        body.append(text_box(f"bar-label-{index+1}", x - 8, 382, 90, 16, name, size=8, weight=800, color=MUTED, align="center"))
    body.extend([
        line("bar-insight-divider", 704, 190, 704, 432, RULE, **{"stroke-width": 1}),
        text_box("bar-insight-label", 724, 210, 148, 16, spec_text(spec, ["insight_label"], "KEY INSIGHT"), size=8, weight=900, color=RED),
        text_box("bar-insight-value", 724, 244, 154, 60, spec_text(spec, ["insight_value", "total_value"], "$725B"), size=42, weight=900, color=RED, family=SERIF),
        text_box("bar-insight-copy", 724, 320, 150, 74, spec_text(spec, ["insight", "insight_copy", "observation"], "Power, cooling, and land now shape the AI infrastructure bottleneck."), size=9, weight=800, color=GOLD),
    ])
    report.add(page, "bar-chart", renderer_id, bbox(132, 190, 742, 252), ["geometric_shape", "typography", "annotation"], effects=["chart_geometry", "editorial_sidebar"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_proportion_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    colors = [accent, "#8BC34A", "#FFC107", "#E91E63"]
    body = []
    for index, radius in enumerate([118, 92, 66, 40]):
        body.append(circle(f"ring-{index+1}", 330, 316, radius, colors[index], opacity=0.14 + index * 0.13))
    for index, color in enumerate(colors):
        body.append(rect(f"legend-{index+1}", 560, 228 + index * 48, 220, 26, color, rx=13, opacity=0.78))
    report.add(page, "proportion-system", renderer_id, bbox(212, 198, 568, 246), ["geometric_shape", "annotation"], effects=["proportion_focus"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_matrix_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = []
    for row in range(2):
        for col in range(2):
            x = 142 + col * 320
            y = 186 + row * 126
            body.append(rect(f"matrix-cell-{row}-{col}", x, y, 286, 96, "#FFFFFF", rx=10, stroke=accent, **{"stroke-width": 2, "opacity": 0.9}))
            body.append(text_box(f"matrix-label-{row}-{col}", x + 18, y + 24, 236, 30, f"Quadrant {row * 2 + col + 1}", size=17, weight=800, color="#1E293B"))
    report.add(page, "matrix-grid", renderer_id, bbox(142, 186, 606, 222), ["geometric_shape", "typography"], effects=["comparison_grid"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_flow_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = []
    for index in range(5):
        x = 112 + index * 154
        body.append(rect(f"flow-step-{index+1}", x, 246, 104, 76, accent, rx=18, opacity=0.82))
        body.append(text_box(f"flow-label-{index+1}", x + 8, 270, 88, 20, f"{index+1:02d}", size=19, weight=900, color="#0F172A", align="center"))
        if index < 4:
            body.append(line(f"flow-link-{index+1}", x + 110, 284, x + 146, 284, accent, **{"stroke-width": 5, "stroke-linecap": "round"}))
    report.add(page, "flow-chain", renderer_id, bbox(112, 246, 720, 76), ["geometric_shape", "connector", "typography"], effects=["process_flow"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_hub_visual(page: int, accent: str, spec: dict[str, Any], report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    hub = spec_dict(spec, ["hub", "center", "core"])
    hub_value = item_text(hub, ["value", "number"], "$500B")
    hub_label = item_text(hub, ["label", "name", "title"], "STARGATE")
    body = [
        rect("hub-panel", 86, 168, 690, 276, PANEL, rx=0, stroke=RULE, **{"stroke-width": 1}),
        circle("hub-orbit-outer", 442, 306, 126, "none", stroke="#26303B", **{"stroke-width": 1, "opacity": 0.82}),
        circle("hub-orbit-inner", 442, 306, 82, "none", stroke="#26303B", **{"stroke-width": 1, "opacity": 0.62}),
        circle("hub-core-glow", 442, 306, 64, accent, opacity=0.12),
        circle("hub-core", 442, 306, 58, BG, stroke=accent, **{"stroke-width": 3}),
        circle("hub-core-fill", 442, 306, 43, "#101720", stroke="#2A3440", **{"stroke-width": 1}),
        text_box("hub-core-value", 398, 286, 88, 22, hub_value, size=17, weight=900, color=INK, align="center"),
        text_box("hub-core-label", 400, 314, 84, 16, hub_label, size=8, weight=900, color=accent, align="center"),
    ]
    default_nodes = [
        {"name": "OpenAI", "note": "model demand", "color": RED},
        {"name": "Oracle", "note": "cloud sites", "color": "#F4A261"},
        {"name": "SoftBank", "note": "capital stack", "color": GOLD},
        {"name": "MGX", "note": "sovereign capital", "color": accent},
        {"name": "10GW", "note": "power target", "color": "#B8B2A9"},
        {"name": "7 sites", "note": "US footprint", "color": "#6D737D"},
    ]
    raw_nodes = clean_items(spec_list(spec, ["nodes", "spokes", "items"]), 6) or default_nodes
    positions = [(224, 226), (658, 226), (224, 382), (658, 382), (442, 190), (442, 422)]
    nodes = []
    for index, item in enumerate(raw_nodes):
        default = default_nodes[min(index, 5)]
        x, y = positions[index]
        nodes.append((x, y, item_text(item, ["name", "label", "title"], default["name"]), item_text(item, ["note", "caption", "description"], default["note"]), item_color(item, default["color"])))
    for index, (x, y, name, note, node_color) in enumerate(nodes, 1):
        sx, sy, ex, ey = radial_connector(442, 306, x, y, 62, 58)
        body.append(line(f"hub-spoke-{index}", sx, sy, ex, ey, node_color, **{"stroke-width": 1, "opacity": 0.65}))
        body.append(circle(f"hub-round-node-{index}", x, y, 18, "#0A0E14", stroke=node_color, **{"stroke-width": 2}))
        label_x = x - 132 if x < 442 else x + 26
        if x == 442:
            label_x = x + 44
            label_y = y - 24
        else:
            label_y = y - 54 if y < 306 else y + 30
        body.append(rect(f"hub-node-{index}", label_x, label_y, 116, 48, "#0A0E14", rx=0, stroke="#2A3440", **{"stroke-width": 1, "opacity": 0.9}))
        body.append(rect(f"hub-node-accent-{index}", label_x, label_y, 5, 48, node_color))
        body.append(text_box(f"hub-node-name-{index}", label_x + 16, label_y + 8, 84, 14, name, size=9, weight=900, color=INK, align="center"))
        body.append(text_box(f"hub-node-note-{index}", label_x + 16, label_y + 27, 84, 12, note, size=8, weight=700, color=MUTED, align="center"))
    body.extend([
        rect("hub-side", 792, 190, 78, 208, "#0A0E14", rx=0, stroke="#222B36", **{"stroke-width": 1}),
        rect("hub-side-rule", 792, 190, 78, 5, RED, rx=0),
        text_box("hub-side-copy", 806, 230, 50, 104, spec_text(spec, ["side_note", "side_copy"], "Project finance meets compute scarcity."), size=9, weight=900, color=GOLD, align="center"),
        text_box("hub-side-index", 800, 360, 62, 16, spec_text(spec, ["side_index", "index_label"], "CAPEX LOOP"), size=8, weight=900, color=MUTED, align="center"),
    ])
    report.add(page, "hub-network", renderer_id, bbox(86, 168, 784, 276), ["geometric_shape", "connector", "typography", "icon"], effects=["radial_network", "orbit_system"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_radial_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = []
    wedges = [(480, 310, 610, 230, 626, 330), (480, 310, 564, 430, 456, 448), (480, 310, 350, 390, 334, 290), (480, 310, 396, 190, 504, 172)]
    for index, (x1, y1, x2, y2, x3, y3) in enumerate(wedges, 1):
        body.append(path(f"radial-wedge-{index}", f"M{x1} {y1} L{x2} {y2} L{x3} {y3} Z", fill=accent, opacity=0.12 + index * 0.035))
    body.append(circle("radial-center", 480, 310, 54, "#FFFFFF", stroke=accent, **{"stroke-width": 5}))
    body.append(text_box("radial-center-label", 430, 296, 100, 28, "SYSTEM", size=15, weight=900, color=accent, align="center"))
    report.add(page, "radial-system", renderer_id, bbox(326, 178, 308, 264), ["geometric_shape", "annotation"], effects=["radial_balance"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_table_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = [rect("table-shell", 110, 184, 740, 250, "#FFFFFF", rx=12, stroke="#CBD5E1", **{"stroke-width": 2})]
    for row in range(1, 5):
        body.append(line(f"table-row-{row}", 110, 184 + row * 50, 850, 184 + row * 50, "#E2E8F0", **{"stroke-width": 2}))
    for col in range(1, 4):
        body.append(line(f"table-col-{col}", 110 + col * 185, 184, 110 + col * 185, 434, "#E2E8F0", **{"stroke-width": 2}))
    body.append(rect("table-header", 110, 184, 740, 50, accent, rx=12, opacity=0.82))
    report.add(page, "table-system", renderer_id, bbox(110, 184, 740, 250), ["geometric_shape", "typography"], effects=["dense_table"], source_trace=source_trace, asset_id=asset_id)
    return body


def render_framework_visual(page: int, accent: str, report: ComponentReport, renderer_id: str, source_trace: str, asset_id: str) -> list[str]:
    body = []
    for index in range(4):
        x = 132 + index * 178
        body.append(rect(f"framework-card-{index+1}", x, 218, 138, 148, "#FFFFFF", rx=16, stroke=accent, **{"stroke-width": 3, "opacity": 0.95}))
        body.append(circle(f"framework-dot-{index+1}", x + 69, 210, 18, accent, opacity=0.9))
        body.append(text_box(f"framework-label-{index+1}", x + 14, 282, 110, 28, f"Pillar {index+1}", size=15, weight=800, color="#1E293B", align="center"))
    report.add(page, "framework-cards", renderer_id, bbox(132, 192, 672, 174), ["geometric_shape", "typography"], effects=["parallel_structure"], source_trace=source_trace, asset_id=asset_id)
    return body


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def plan_path(project: Path, value: str) -> Path:
    path_value = Path(value).expanduser()
    if path_value.is_absolute():
        return path_value
    return project / path_value


def text_from_any(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def normalize_kind(value: Any, fallback: str) -> str:
    raw = text_from_any(value).replace(".", "_").replace("-", "_").lower()
    if raw.startswith("chart_"):
        raw = raw.removeprefix("chart_")
    if raw.startswith("layout_"):
        raw = raw.removeprefix("layout_")
    return PAGE_KIND_ALIASES.get(raw, raw or fallback)


def asset_id_from(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ["asset_id", "id", "design_pattern_id"]:
            found = asset_id_from(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = asset_id_from(item)
            if found:
                return found
    return ""


def selected_asset_ids(plan: dict[str, Any]) -> set[str]:
    selection = plan.get("design_pattern_selection")
    if not isinstance(selection, dict):
        return set()
    assets = selection.get("selected_assets")
    out: set[str] = set()
    if isinstance(assets, list):
        for asset in assets:
            asset_id = asset_id_from(asset)
            if asset_id:
                out.add(asset_id)
    else:
        asset_id = asset_id_from(assets)
        if asset_id:
            out.add(asset_id)
    return out


def slide_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ["slides", "pages", "page_plan"]:
        value = plan.get(key)
        if isinstance(value, list) and value:
            return [item for item in value if isinstance(item, dict)]
    page_count = plan.get("page_count") or plan.get("slide_count") or len(SUPPORTED_PAGE_KINDS)
    try:
        count = max(1, int(page_count))
    except (TypeError, ValueError):
        count = len(SUPPORTED_PAGE_KINDS)
    return [{"page_kind": SUPPORTED_PAGE_KINDS[index % len(SUPPORTED_PAGE_KINDS)]} for index in range(count)]


def first_text(item: dict[str, Any], keys: list[str], fallback: str) -> str:
    for key in keys:
        value = text_from_any(item.get(key))
        if value:
            return value
        visual_plan = item.get("visual_plan")
        if isinstance(visual_plan, dict):
            value = text_from_any(visual_plan.get(key))
            if value:
                return value
    return fallback


def slide_summary_text(item: dict[str, Any], kind: str) -> str:
    primary = first_text(
        item,
        ["summary", "subtitle", "key_message", "note", "speaker_note"],
        f"Runtime-generated {kind.replace('_', ' ')} page.",
    )
    body = first_text(item, ["body", "description", "supporting_copy"], "")
    if body and body not in primary:
        return f"{primary} {body}"
    return primary


def slide_kind(item: dict[str, Any], index: int) -> str:
    fallback = SUPPORTED_PAGE_KINDS[index % len(SUPPORTED_PAGE_KINDS)]
    generic_kinds = {"chart", "charts", "content", "page", "slide"}
    generic_match = ""
    visual_plan = item.get("visual_plan")
    for key in ["page_kind", "chart_type", "page_type", "archetype", "kind", "type", "renderer_id", "visual_recipe"]:
        for source in [item, visual_plan if isinstance(visual_plan, dict) else {}]:
            value = source.get(key)
            if not value:
                continue
            kind = normalize_kind(value, fallback)
            if kind in generic_kinds:
                generic_match = generic_match or kind
                continue
            return kind
    if generic_match:
        return generic_match
    return fallback


def slide_asset_id(item: dict[str, Any], kind: str, selected_assets: set[str]) -> str:
    visual_plan = item.get("visual_plan")
    nested_reference = visual_plan.get("reference_asset") if isinstance(visual_plan, dict) else None
    nested_asset = visual_plan.get("asset_id") if isinstance(visual_plan, dict) else None
    explicit = (
        asset_id_from(item.get("asset_id"))
        or asset_id_from(item.get("design_pattern_id"))
        or asset_id_from(item.get("reference_asset"))
        or asset_id_from(item.get("design_reference_assets"))
        or asset_id_from(nested_reference)
        or asset_id_from(nested_asset)
    )
    if explicit:
        return explicit
    default = DEFAULT_ASSET_BY_KIND.get(kind, "")
    if default and (not selected_assets or default in selected_assets):
        return default
    return ""


def valid_hex_color(value: str) -> str:
    return value.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else ""


def plan_palette_accent(plan: dict[str, Any], index: int) -> str:
    style_system = plan.get("style_system")
    palette = style_system.get("palette") if isinstance(style_system, dict) else None
    if not isinstance(palette, dict):
        return ""
    accent = valid_hex_color(text_from_any(palette.get("accent")))
    if accent:
        return accent
    support = palette.get("support")
    if isinstance(support, list) and support:
        for offset in range(len(support)):
            candidate = valid_hex_color(text_from_any(support[(index + offset) % len(support)]))
            if candidate:
                return candidate
    return ""


def slide_accent(item: dict[str, Any], index: int, plan: dict[str, Any] | None = None) -> str:
    accent = text_from_any(item.get("accent") or item.get("primary_color"))
    explicit = valid_hex_color(accent)
    if explicit:
        return explicit
    if isinstance(plan, dict):
        planned = plan_palette_accent(plan, index)
        if planned:
            return planned
    return DEFAULT_ACCENTS[index % len(DEFAULT_ACCENTS)]


def compose_project(project: Path, plan: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    plan = plan.expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    data = read_json(plan)
    if not isinstance(data, dict):
        raise ValueError("compose plan must contain a JSON object")

    pages_dir = project / "pages"
    receipts_dir = project / "receipts"
    pages_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir.mkdir(parents=True, exist_ok=True)

    report = ComponentReport()
    selected_assets = selected_asset_ids(data)
    deck_title = first_text(data, ["title", "deck_title", "name"], "SVGlide Runtime Deck")
    contract_mode = is_strategist_contract(data)
    page_outputs: list[dict[str, Any]] = []

    for index, item in enumerate(slide_items(data), 1):
        kind = slide_kind(item, index - 1)
        title = first_text(item, ["title", "headline", "name"], f"{deck_title}: {kind.replace('_', ' ').title()}")
        summary = slide_summary_text(item, kind)
        asset_id = slide_asset_id(item, kind, selected_assets)
        accent = slide_accent(item, index - 1, data)
        if contract_mode:
            svg = render_contract_slide(
                page=index,
                kind=kind,
                title=title,
                summary=summary,
                asset_id=asset_id,
                accent=accent,
                spec=item,
                report=report,
                deck_title=deck_title,
            )
        else:
            svg = render_demo_slide(page=index, kind=kind, title=title, summary=summary, asset_id=asset_id, accent=accent, spec=item, report=report)
        output = pages_dir / f"page-{index:03d}.svg"
        output.write_text(svg, encoding="utf-8")
        page_outputs.append(
            {
                "page": index,
                "page_kind": kind,
                "renderer_id": renderer_family(kind),
                "source_svg": rel_path(project, output),
                "asset_id": asset_id,
            }
        )

    component_report = report.to_dict()
    usage_receipt = design_pattern_usage_receipt(component_report)
    runtime_cache = {
        "schema_version": RUNTIME_CACHE_SCHEMA,
        "status": "passed",
        "generator": "svglide_gen_runtime",
        "project": project.as_posix(),
        "plan": rel_path(project, plan),
        "plan_digest": file_digest(plan),
        "supported_page_kinds": list(SUPPORTED_PAGE_KINDS),
        "page_count": len(page_outputs),
        "pages": page_outputs,
        "outputs": {
            "pages_dir": rel_path(project, pages_dir),
            "component_report": "receipts/emitted_components.json",
            "design_pattern_usage": "receipts/design-pattern-usage.json",
            "runtime_cache": "receipts/runtime-cache.json",
        },
    }
    write_json(receipts_dir / "emitted_components.json", component_report)
    write_json(receipts_dir / "design-pattern-usage.json", usage_receipt)
    write_json(receipts_dir / "runtime-cache.json", runtime_cache)
    return runtime_cache


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SVGlide runtime composition helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    compose = subparsers.add_parser("compose", help="compose SVGlide-safe SVG pages from a JSON plan")
    compose.add_argument("--project", required=True, help="project output directory")
    compose.add_argument("--plan", required=True, help="plan JSON path, absolute or relative to --project")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "compose":
        project = Path(args.project)
        plan = plan_path(project.expanduser().resolve(), args.plan)
        result = compose_project(project, plan)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
