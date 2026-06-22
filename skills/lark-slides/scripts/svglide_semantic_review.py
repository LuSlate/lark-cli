#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


PLAN_PATH = Path("02-plan/slide_plan.json")
EVIDENCE_PATH = Path("source/evidence.json")
SOURCE_RECEIPT_PATH = Path("source/source-receipt.json")
PREPARED_SVG_DIR = Path("04-svg/prepared")
CHECK_DIR = Path("06-check")
SEMANTIC_REVIEW = CHECK_DIR / "semantic-review.json"
TEXT_INVENTORY = CHECK_DIR / "text-inventory.json"
ALLOWED_PAGE_TYPES = {"cover", "section", "content", "closing"}
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"
TEXT_LIKE_TAG_RE = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?(?:text|tspan|foreignObject)\b[^>]*>(.*?)</(?:[A-Za-z_][\w.-]*:)?(?:text|tspan|foreignObject)>",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")
GENERATED_SAFE_RE = re.compile(r"^[\d\s.,:%+\-/()#]+$")
NUMERIC_CLAIM_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?:\s?[%万亿千百]|[KMBTkmbt])?")
MIN_EVIDENCE_TEXT_CHARS = 20
MIN_CHART_EVIDENCE_CHARS = 80


class SemanticReviewError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SemanticReviewError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SemanticReviewError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_object_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_object(path)


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path is not None:
        payload["path"] = path
    return payload


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def has_cjk(value: str) -> bool:
    return bool(CJK_RE.search(value))


def mostly_generated_safe(value: str) -> bool:
    text = normalize_text(value)
    return len(text) <= 2 or bool(GENERATED_SAFE_RE.fullmatch(text))


def collect_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        text = normalize_text(value)
        if text:
            strings.append(text)
    elif isinstance(value, list):
        for item in value:
            strings.extend(collect_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(collect_strings(item))
    return strings


def text_matches_allowed(text: str, allowed: list[str]) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    for candidate in allowed:
        normalized_candidate = normalize_text(candidate)
        if not normalized_candidate:
            continue
        if normalized == normalized_candidate:
            return True
        if normalized in normalized_candidate or normalized_candidate in normalized:
            return True
    return False


def load_evidence(project: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = project / EVIDENCE_PATH
    if not path.exists():
        return None, [issue("missing_evidence_json", f"missing required evidence file: {EVIDENCE_PATH.as_posix()}")]
    evidence = read_json_object(path)
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-evidence.schema.json"))
    schema_issues = [
        issue(item["code"], item["message"], path=item["path"])
        for item in svglide_schema.validate_json_schema(evidence, schema)
    ]
    if evidence.get("source_status") != "ready":
        schema_issues.append(issue("source_status_not_ready", "evidence source_status must be ready"))
    items = evidence.get("items")
    if isinstance(items, list):
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str) or len(normalize_text(text)) < MIN_EVIDENCE_TEXT_CHARS:
                schema_issues.append(issue("source_item_text_too_short", f"evidence item {index} text is too short"))
    return evidence, schema_issues


def evidence_ids(evidence: dict[str, Any] | None) -> set[str]:
    ids: set[str] = set()
    if not isinstance(evidence, dict):
        return ids
    items = evidence.get("items")
    if not isinstance(items, list):
        return ids
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = item.get("id")
        if isinstance(raw, str) and raw:
            ids.add(raw)
            ids.add(f"source:{raw}")
    return ids


def evidence_items_by_ref(evidence: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    items_by_ref: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence, dict):
        return items_by_ref
    items = evidence.get("items")
    if not isinstance(items, list):
        return items_by_ref
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = item.get("id")
        if isinstance(raw, str) and raw:
            items_by_ref[raw] = item
            items_by_ref[f"source:{raw}"] = item
    return items_by_ref


def evidence_strings_for_refs(evidence: dict[str, Any] | None, refs: list[str]) -> list[tuple[str, str]]:
    by_ref = evidence_items_by_ref(evidence)
    strings: list[tuple[str, str]] = []
    for ref in refs:
        item = by_ref.get(ref)
        if not item:
            continue
        for key, value in item.items():
            if isinstance(value, str):
                text = normalize_text(value)
                if text:
                    strings.append((text, f"source/evidence.json:{ref}.{key}"))
    return strings


def evidence_text_length_for_refs(evidence: dict[str, Any] | None, refs: list[str]) -> int:
    by_ref = evidence_items_by_ref(evidence)
    total = 0
    seen: set[str] = set()
    for ref in refs:
        item = by_ref.get(ref)
        if not item:
            continue
        raw_id = item.get("id")
        dedupe_key = raw_id if isinstance(raw_id, str) else ref
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        text = item.get("text")
        if isinstance(text, str):
            total += len(normalize_text(text))
    return total


def prepared_svg_files(project: Path) -> list[Path]:
    root = project / PREPARED_SVG_DIR
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*.svg") if path.is_file())


def prepared_file_hashes(project: Path) -> list[dict[str, str]]:
    return [{"path": relpath(path, project), "sha256": file_sha256(path)} for path in prepared_svg_files(project)]


def extract_visible_texts(svg_path: Path) -> list[str]:
    raw = svg_path.read_text(encoding="utf-8")
    texts: list[str] = []
    try:
        root = ET.fromstring(raw)
        for element in root.iter():
            local_name = element.tag.rsplit("}", 1)[-1]
            if local_name in {"text", "foreignObject"}:
                text = normalize_text("".join(element.itertext()))
                if text:
                    texts.append(text)
    except ET.ParseError:
        for match in TEXT_LIKE_TAG_RE.finditer(raw):
            text = normalize_text(TAG_RE.sub("", match.group(1)))
            if text:
                texts.append(text)
    return texts


def source_refs_for_slide(slide: dict[str, Any]) -> list[str]:
    raw = slide.get("source_refs") or slide.get("sources") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str) and item]


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def has_numeric_claim(values: list[str]) -> bool:
    return any(NUMERIC_CLAIM_RE.search(value) for value in values)


def slide_has_chart_signal(slide: dict[str, Any]) -> bool:
    for key in ["layout_family", "visual_recipe", "renderer_id", "role"]:
        value = slide.get(key)
        if isinstance(value, str) and any(token in value.lower() for token in ["chart", "graph", "plot", "bar", "line", "donut"]):
            return True
    for key in ["chart_contract", "chart_data", "charts"]:
        if slide.get(key):
            return True
    primitives = slide.get("svg_primitives") or slide.get("primitives")
    return isinstance(primitives, list) and any(
        isinstance(item, str) and any(token in item.lower() for token in ["chart", "graph", "plot", "bar", "line", "donut"])
        for item in primitives
    )


def check_plan_structure(plan: dict[str, Any], evidence: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    slide_results: list[dict[str, Any]] = []
    if plan.get("language") != "zh-CN":
        issues.append(issue("language_not_zh_cn", "slide_plan.language must be zh-CN"))
    audience = plan.get("audience")
    if not isinstance(audience, str) or not audience.strip():
        issues.append(issue("audience_missing", "slide_plan.audience must be a non-empty string"))

    deck_structure = plan.get("deck_structure")
    if not isinstance(deck_structure, list) or not all(isinstance(item, str) for item in deck_structure):
        issues.append(issue("deck_structure_missing", "slide_plan.deck_structure must be a string array"))
        deck_structure = []
    else:
        missing_types = {"cover", "content", "closing"} - set(deck_structure)
        for page_type in sorted(missing_types):
            issues.append(issue("deck_structure_missing_page_type", f"deck_structure must include {page_type}"))

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        issues.append(issue("slides_missing", "slide_plan.slides must be a non-empty array"))
        return issues, slide_results

    page_types = [slide.get("page_type") if isinstance(slide, dict) else None for slide in slides]
    if len(deck_structure) == len(slides) and list(deck_structure) != page_types:
        issues.append(issue("deck_structure_mismatch", "deck_structure must match slides[].page_type when lengths are equal"))

    known_source_refs = evidence_ids(evidence)
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict):
            issues.append(issue("slide_not_object", "slide item must be an object", page=index))
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        page_issues: list[dict[str, Any]] = []
        page_type = raw_slide.get("page_type")
        section = raw_slide.get("section")
        role = raw_slide.get("role")
        title = raw_slide.get("title")
        key_message = raw_slide.get("key_message")
        body_points = list_of_strings(raw_slide.get("body_points") or raw_slide.get("bullets"))
        source_refs = source_refs_for_slide(raw_slide)

        if page_type not in ALLOWED_PAGE_TYPES:
            page_issues.append(issue("slide_page_type_missing", "slide.page_type must be cover, section, content, or closing", page=page))
        if not isinstance(section, str) or not section.strip():
            page_issues.append(issue("slide_section_missing", "slide.section must be a non-empty string", page=page))
        if not isinstance(role, str) or not role.strip():
            page_issues.append(issue("slide_role_missing", "slide.role must be a non-empty string", page=page))
        if not isinstance(title, str) or not title.strip() or not has_cjk(title):
            page_issues.append(issue("slide_title_not_chinese", "slide.title must be non-empty Chinese text", page=page))
        if not isinstance(key_message, str) or not key_message.strip() or not has_cjk(key_message):
            page_issues.append(issue("slide_key_message_not_chinese", "slide.key_message must be non-empty Chinese text", page=page))

        if page_type == "content":
            if len(body_points) < 2:
                page_issues.append(issue("content_body_points_too_few", "content slides require at least 2 body_points", page=page))
            if len(body_points) > 4:
                page_issues.append(issue("content_body_points_too_many", "content slides should keep body_points within 2-4 items", page=page))
            if not source_refs:
                page_issues.append(issue("content_source_refs_missing", "content slides require at least one source_ref", page=page))
            if slide_has_chart_signal(raw_slide) and (len(body_points) < 3 or evidence_text_length_for_refs(evidence, source_refs) < MIN_CHART_EVIDENCE_CHARS):
                page_issues.append(
                    issue(
                        "chart_rich_content_too_thin",
                        "chart-rich content slides require at least 3 body_points and stronger evidence coverage",
                        page=page,
                    )
                )
        if page_type == "closing" and len(body_points) < 2:
            page_issues.append(issue("closing_takeaways_too_few", "closing slides require at least 2 takeaways/body_points", page=page))
        for body_index, point in enumerate(body_points, 1):
            if not has_cjk(point):
                page_issues.append(issue("body_point_not_chinese", f"body_points[{body_index}] must contain Chinese text", page=page))
        for ref in source_refs:
            if known_source_refs and ref not in known_source_refs:
                page_issues.append(issue("source_ref_not_found", f"source_ref is not present in evidence.json: {ref}", page=page))
        numeric_values = [value for value in [title, key_message, *body_points] if isinstance(value, str)]
        if has_numeric_claim(numeric_values) and not source_refs:
            page_issues.append(issue("numeric_claim_uncited", "numeric claims require at least one source_ref", page=page))

        issues.extend(page_issues)
        slide_results.append(
            {
                "page": page,
                "page_type": page_type,
                "section": section,
                "role": role,
                "body_point_count": len(body_points),
                "source_ref_count": len(source_refs),
                "error_count": len(page_issues),
            }
        )
    return issues, slide_results


def research_quality_issues(project: Path, evidence: dict[str, Any] | None, *, profile: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    receipt = read_json_object_optional(project / SOURCE_RECEIPT_PATH)
    research = receipt.get("research") if isinstance(receipt.get("research"), dict) else {}
    status = None
    if isinstance(research, dict):
        raw_status = research.get("status")
        status = raw_status if isinstance(raw_status, str) else None
    if status is None and isinstance(evidence, dict):
        raw_status = evidence.get("research_status")
        status = raw_status if isinstance(raw_status, str) else None
    sources = research.get("sources") if isinstance(research, dict) and isinstance(research.get("sources"), list) else []
    if status in {"blocked_by_network", "skipped_by_user"}:
        issues.append(issue("research_missing_for_current_topic", f"source research status is {status}"))
    if profile in {"production", "production_live", "local_real_preview"} and status == "partial":
        issues.append(issue("research_partial_for_production", "production profiles require ready/researched source status"))
    if status == "researched" and not sources:
        issues.append(issue("source_credibility_missing", "researched source receipt must include sources"))
    summary = {
        "status": status or "legacy",
        "source_count": len(sources),
        "retrieved_at": receipt.get("ended_at") if isinstance(receipt, dict) else None,
    }
    return issues, summary


def build_text_inventory(project: Path, plan: dict[str, Any], evidence: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    inventory_slides: list[dict[str, Any]] = []
    for index, svg_path in enumerate(prepared_svg_files(project), 1):
        page = index
        if index <= len(slides) and isinstance(slides[index - 1], dict):
            current_slide = slides[index - 1]
            raw_page = slides[index - 1].get("page")
            if isinstance(raw_page, int):
                page = raw_page
        else:
            current_slide = {}
        page_plan_strings = [(text, f"slide_plan.json:slides[{index - 1}]") for text in collect_strings(current_slide)]
        page_evidence_strings = evidence_strings_for_refs(evidence, source_refs_for_slide(current_slide))
        texts = []
        unmatched: list[str] = []
        for text in extract_visible_texts(svg_path):
            if text_matches_allowed(text, [item[0] for item in page_plan_strings]):
                source = "slide_plan.json"
                source_path = next((item[1] for item in page_plan_strings if text_matches_allowed(text, [item[0]])), None)
                status = "matched"
            elif text_matches_allowed(text, [item[0] for item in page_evidence_strings]):
                source = "source/evidence.json"
                source_path = next((item[1] for item in page_evidence_strings if text_matches_allowed(text, [item[0]])), None)
                status = "matched"
            elif mostly_generated_safe(text):
                source = "generator"
                source_path = None
                status = "allowed_generated"
            else:
                source = "generator"
                source_path = None
                status = "unmatched"
                unmatched.append(text)
                issues.append(issue("visible_text_not_in_plan_or_source", f"visible SVG text is not traceable to plan or source: {text!r}", page=page, path=relpath(svg_path, project)))
            texts.append({"text": text, "source": source, "source_path": source_path, "status": status})
        inventory_slides.append({"page": page, "svg": relpath(svg_path, project), "texts": texts, "unmatched_texts": unmatched})
    inventory = {
        "schema_version": "svglide-text-inventory/v1",
        "generated_at": now_iso(),
        "slides": inventory_slides,
        "summary": {
            "slide_count": len(inventory_slides),
            "text_count": sum(len(slide["texts"]) for slide in inventory_slides),
            "unmatched_text_count": sum(len(slide["unmatched_texts"]) for slide in inventory_slides),
        },
    }
    return inventory, issues


def run_semantic_review(project: Path, *, profile: str = "preview_only") -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan_file = project / PLAN_PATH
    if not plan_file.exists():
        raise SemanticReviewError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_file)
    evidence, evidence_issues = load_evidence(project)
    issues, slide_results = check_plan_structure(plan, evidence)
    issues.extend(evidence_issues)
    research_issues, research_summary = research_quality_issues(project, evidence, profile=profile)
    issues.extend(research_issues)

    svgs = prepared_svg_files(project)
    if not svgs:
        issues.append(issue("prepared_svg_missing", f"no prepared SVG files found under {PREPARED_SVG_DIR.as_posix()}"))
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    if svgs and slides and len(svgs) != len(slides):
        issues.append(issue("prepared_svg_count_mismatch", "prepared SVG file count must match slide_plan.slides length"))

    text_inventory, text_issues = build_text_inventory(project, plan, evidence)
    issues.extend(text_issues)
    text_inventory_schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-text-inventory.schema.json"))
    for item in svglide_schema.validate_json_schema(text_inventory, text_inventory_schema):
        issues.append(issue(item["code"], item["message"], path=item["path"]))

    output_dir = project / CHECK_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    text_inventory_path = project / TEXT_INVENTORY
    text_inventory_path.write_text(json.dumps(text_inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-semantic-review/v1",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "profile": profile,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": file_sha256(plan_file),
            "evidence": EVIDENCE_PATH.as_posix() if (project / EVIDENCE_PATH).exists() else None,
            "evidence_sha256": file_sha256(project / EVIDENCE_PATH) if (project / EVIDENCE_PATH).exists() else None,
            "svg_dir": PREPARED_SVG_DIR.as_posix(),
        },
        "prepared_files": prepared_file_hashes(project),
        "text_inventory": TEXT_INVENTORY.as_posix(),
        "checks": {
            "language": "passed" if not any(item["code"] == "language_not_zh_cn" for item in issues) else "failed",
            "deck_structure": "passed" if not any(item["code"].startswith("deck_structure") for item in issues) else "failed",
            "content_density": "passed" if not any("body_points" in item["code"] or "takeaways" in item["code"] or item["code"] == "content_source_refs_missing" for item in issues) else "failed",
            "plan_svg_text_alignment": "passed" if not text_issues else "failed",
            "research_freshness": "passed" if not any(item["code"].startswith("research_") for item in issues) else "failed",
            "source_credibility": "passed" if not any(item["code"] == "source_credibility_missing" for item in issues) else "failed",
            "numeric_claims": "passed" if not any(item["code"] == "numeric_claim_uncited" for item in issues) else "failed",
        },
        "research": research_summary,
        "slides": slide_results,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "slide_count": len(slide_results),
            "prepared_svg_count": len(svgs),
            "unmatched_text_count": text_inventory["summary"]["unmatched_text_count"],
        },
        "issues": issues,
        "output_path": SEMANTIC_REVIEW.as_posix(),
    }

    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-semantic-review.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["action"] = FAIL_ACTION
        result["issues"].extend(issue(item["code"], item["message"], path=item["path"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])

    output_path = project / SEMANTIC_REVIEW
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic semantic and content checks for a SVGlide project.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--profile", default="preview_only", choices=["preview_only", "local_real_preview", "production_live", "production", "debug"])
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_semantic_review(Path(args.project), profile=args.profile)
    except (OSError, SemanticReviewError) as error:
        print(f"svglide_semantic_review: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
