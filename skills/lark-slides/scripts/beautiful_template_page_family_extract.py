#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("/Users/bytedance/bd-projects/beautiful-html-templates")
DEFAULT_ROLE_BY_INDEX = {
    1: "cover",
    2: "agenda",
    10: "closing",
}
ROLE_BY_VARIANT_ID = {
    "cover": "cover",
    "agenda": "agenda",
    "toc": "agenda",
    "metrics": "data_metrics",
    "dashboard": "data_dashboard",
    "split": "content_split",
    "bars": "data_chart",
    "quote": "quote_or_emphasis",
    "timeline": "process_or_timeline",
    "detail": "detail",
    "closing": "closing",
}
SKIP_SLIDE_CLASSES = {
    "slide-content",
    "slide-header",
    "slide-title",
    "slide-subtitle",
    "slide-counter",
    "slides-container",
}
GENERIC_SLIDE_CLASSES = {
    "slide",
    "active",
    "dark",
    "light",
    "grain",
    "scanlines",
    "crt-glow",
}


def _source_relative(path: Path) -> str:
    return f"{SOURCE_ROOT.name}/{path.relative_to(SOURCE_ROOT).as_posix()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _body_html(html: str) -> str:
    match = re.search(r"<body\b[^>]*>(?P<body>.*)</body>", html, re.IGNORECASE | re.DOTALL)
    return match.group("body") if match else html


def _class_attr(tag: str) -> str:
    match = re.search(r"class=[\"'](?P<class>[^\"']+)[\"']", tag, re.IGNORECASE)
    return match.group("class") if match else ""


def _data_slide(tag: str) -> int | None:
    match = re.search(r"data-slide=[\"']?(?P<index>\d+)[\"']?", tag, re.IGNORECASE)
    if match:
        return int(match.group("index"))
    label = re.search(r"data-screen-label=[\"']\s*(?P<index>\d+)", tag, re.IGNORECASE)
    return int(label.group("index")) if label else None


def _slide_index(classes: list[str], tag: str, fallback: int) -> int:
    data_index = _data_slide(tag)
    if data_index is not None:
        return data_index
    for cls in classes:
        match = re.fullmatch(r"slide-(\d+)", cls)
        if match:
            return int(match.group(1))
    return fallback


def _is_slide_root(classes: list[str], tag: str) -> bool:
    if not classes or any(cls in SKIP_SLIDE_CLASSES for cls in classes):
        return False
    return "slide" in classes or "data-screen-label=" in tag.lower()


def _variant_id(classes: list[str], index: int, block: str) -> str:
    for cls in classes:
        if cls.startswith("layout-"):
            return cls.removeprefix("layout-")
    for cls in classes:
        match = re.fullmatch(r"slide-(\d+)", cls)
        if match:
            inferred = _role_from_block(index, block)
            return inferred if inferred != "content" else f"slide-{match.group(1)}"
    for cls in classes:
        if cls.startswith("slide--"):
            return cls.removeprefix("slide--").replace("-", "_")
    for cls in classes:
        if cls.startswith("slide-"):
            return cls.removeprefix("slide-").replace("-", "_")
    for cls in classes:
        if cls.startswith("s-"):
            return cls.removeprefix("s-").replace("-", "_")
    for cls in classes:
        if cls not in GENERIC_SLIDE_CLASSES and not cls.startswith("bg-"):
            return cls.replace("-", "_")
    return f"slide-{index}"


def _source_class(classes: list[str], index: int) -> str:
    for cls in classes:
        if cls.startswith("layout-"):
            return cls
    for cls in classes:
        if re.fullmatch(r"slide-\d+", cls):
            return cls
    for cls in classes:
        if cls.startswith("slide--"):
            return cls
    for cls in classes:
        if cls.startswith("slide-"):
            return cls
    for cls in classes:
        if cls.startswith("s-"):
            return cls
    for cls in classes:
        if cls not in GENERIC_SLIDE_CLASSES and not cls.startswith("bg-"):
            return cls
    return f"data-slide-{index}"


def _role_from_block(index: int, block: str) -> str:
    if index in DEFAULT_ROLE_BY_INDEX:
        return DEFAULT_ROLE_BY_INDEX[index]
    text = re.sub(r"<[^>]+>", " ", block).lower()
    class_blob = " ".join(re.findall(r"class=[\"']([^\"']+)[\"']", block, flags=re.IGNORECASE)).lower()
    blob = f"{text} {class_blob}"
    if "timeline" in blob or "roadmap" in blob or "phase" in blob:
        return "process_or_timeline"
    if "quote" in blob or "blockquote" in blob or "testimonial" in blob:
        return "quote_or_emphasis"
    if "metric" in blob or "chart" in blob or "stat" in blob or "kpi" in blob or "bar" in blob:
        return "data_dashboard"
    if "agenda" in blob or "contents" in blob:
        return "agenda"
    if "closing" in blob or "thank" in blob or "contact" in blob:
        return "closing"
    if "team" in blob or "leadership" in blob or "detail" in blob:
        return "detail"
    return "content"


def _page_role(variant_id: str, index: int, block: str) -> str:
    return ROLE_BY_VARIANT_ID.get(variant_id, _role_from_block(index, block))


def _slots(block: str, role: str) -> list[str]:
    slots: list[str] = []
    lower = block.lower()
    if re.search(r"<h[1-4]\b|title", lower):
        slots.append("title")
    if "subtitle" in lower or "<p" in lower:
        slots.append("subtitle")
    if "metric" in lower or "stat" in lower or "kpi" in lower:
        slots.append("metrics")
    if "<li" in lower or "card" in lower or "item" in lower:
        slots.append("items")
    if "quote" in lower or "blockquote" in lower:
        slots.append("quote")
    if "timeline" in lower or "phase" in lower:
        slots.append("timeline")
    if not slots:
        slots.append("title")
    if role in {"cover", "closing"} and "title" not in slots:
        slots.insert(0, "title")
    return slots


def _slide_blocks(html: str) -> list[tuple[str, list[str], int, str]]:
    body = _body_html(html)
    tag_matches = list(re.finditer(r"<(?:section|div)\b[^>]*class=[\"'][^\"']*[\"'][^>]*>", body, re.IGNORECASE))
    roots: list[tuple[re.Match[str], list[str], int]] = []
    for match in tag_matches:
        classes = _class_attr(match.group(0)).split()
        if _is_slide_root(classes, match.group(0)):
            roots.append((match, classes, _slide_index(classes, match.group(0), len(roots) + 1)))
    blocks: list[tuple[str, list[str], int, str]] = []
    for position, (match, classes, index) in enumerate(roots):
        end = roots[position + 1][0].start() if position + 1 < len(roots) else len(body)
        block = body[match.start():end]
        blocks.append((match.group(0), classes, index, block))
    return blocks


def extract_family(family_id: str, *, source_root: Path = SOURCE_ROOT) -> dict[str, Any]:
    family_dir = source_root / "templates" / family_id
    template_html_path = family_dir / "template.html"
    design_md_path = family_dir / "design.md"
    template_json_path = family_dir / "template.json"
    if not template_html_path.is_file():
        raise FileNotFoundError(template_html_path)
    html = template_html_path.read_text(encoding="utf-8", errors="ignore")
    metadata = _read_json(template_json_path) if template_json_path.is_file() else {}
    design_md = design_md_path.read_text(encoding="utf-8", errors="ignore") if design_md_path.is_file() else ""

    variants: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for tag, classes, index, block in _slide_blocks(html):
        variant_id = _variant_id(classes, index, block)
        source_class = _source_class(classes, index)
        page_role = _page_role(variant_id, index, block)
        unique_variant_id = variant_id
        if unique_variant_id in variants:
            unique_variant_id = f"{variant_id}-{index}"
        variants[unique_variant_id] = {
            "source_class": source_class,
            "source_slide_index": index,
            "page_role": page_role,
            "required_slots": _slots(block, page_role),
            "optional_slots": ["eyebrow", "decoration"],
            "source_refs": [
                {
                    "path": _source_relative(template_html_path),
                    "selector_or_token": f".{source_class}",
                    "raw_value": tag.strip(),
                }
            ],
            "extraction_confidence": "css_extracted_from_template_html" if source_class.startswith("layout-") else "inferred_from_layout",
        }
    core_roles = list(dict.fromkeys(variant["page_role"] for variant in variants.values()))
    return {
        "version": "svglide-beautiful-page-family-extraction/v1",
        "family_id": family_id,
        "source": {
            "source_template_html": _source_relative(template_html_path),
            "source_design_md": _source_relative(design_md_path) if design_md_path.is_file() else "",
            "source_template_json": _source_relative(template_json_path) if template_json_path.is_file() else "",
            "design_md_bytes": len(design_md.encode("utf-8")),
        },
        "source_metadata": {
            "name": metadata.get("name"),
            "slide_count": metadata.get("slide_count"),
            "density": metadata.get("density"),
            "mood": metadata.get("mood"),
            "best_for": metadata.get("best_for"),
        },
        "page_family": {
            "source_slide_count": len(variants),
            "core_page_roles": core_roles,
            "production_minimum_roles": ["cover", "agenda", "content", "data", "quote_or_emphasis", "process_or_timeline", "closing"],
        },
        "page_variants": variants,
        "claim_boundary": "source extraction only; does not imply renderer, fidelity, quality gate, or production/default selectable status",
    }


def extract_all(*, source_root: Path = SOURCE_ROOT) -> dict[str, Any]:
    reports = []
    for family_dir in sorted((source_root / "templates").iterdir()):
        if family_dir.is_dir() and (family_dir / "template.html").is_file():
            reports.append(extract_family(family_dir.name, source_root=source_root))
    return {
        "version": "svglide-beautiful-page-family-extraction-report/v1",
        "summary": {
            "family_count": len(reports),
            "families_with_page_variants": sum(1 for report in reports if report["page_variants"]),
            "total_page_variants": sum(len(report["page_variants"]) for report in reports),
        },
        "families": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract beautiful-html-templates page-family variants.")
    parser.add_argument("--family", help="extract one family id")
    parser.add_argument("--source-root", default=SOURCE_ROOT.as_posix())
    args = parser.parse_args()
    source_root = Path(args.source_root)
    payload = extract_family(args.family, source_root=source_root) if args.family else extract_all(source_root=source_root)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
