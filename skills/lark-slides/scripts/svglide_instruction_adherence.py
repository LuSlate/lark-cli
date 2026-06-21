#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CHECK_VERSION = "svglide-instruction-adherence/v1"
INSTRUCTION_FILE = Path("00-input/instruction.json")
CANVAS_PLAN = Path("02-plan/slide_plan.json")
DECK_PLAN = Path("02-plan/deck-plan.json")
SLIDE_PLAN = Path("02-plan/slide-plan.json")
REPAIR_PLAN = Path("02-plan/repair-plan.json")
READBACK_CHECK = Path("08-readback/readback-check.json")
READBACK_RAW = Path("08-readback/xml-presentations-get.json")
QUALITY_GATE = Path("06-check/quality-gate.json")
DRY_RUN = Path("07-create/dry-run.json")
PPE_PROOF = Path("07-create/ppe-proof.json")
LIVE_CREATE = Path("07-create/live-create.json")
CHECK_PATH = Path("06-check/instruction-adherence.json")
RECEIPT_PATH = Path("receipts/instruction-adherence.json")


class InstructionAdherenceError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise InstructionAdherenceError(f"missing required file: {path}") from err
    except json.JSONDecodeError as err:
        raise InstructionAdherenceError(f"invalid JSON: {path}: {err}") from err
    if not isinstance(payload, dict):
        raise InstructionAdherenceError(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, project: Path) -> str:
    return path.relative_to(project).as_posix()


def text_values(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, list):
        for item in value:
            result.extend(text_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(text_values(item))
    return result


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def contains_text(haystack_values: list[str], needle: str) -> bool:
    if not needle:
        return True
    normalized = normalize_text(needle)
    return any(normalized in normalize_text(value) for value in haystack_values)


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def slide_svg_paths(project: Path) -> list[Path]:
    return sorted((project / "04-svg").glob("page-*.svg"))


def svg_text(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<[^>]+>", " ", text)
    return [raw]


def readback_payload(project: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    return read_json(project / READBACK_CHECK), read_json(project / READBACK_RAW)


def find_first_key(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys:
                return child
        for child in value.values():
            found = find_first_key(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first_key(child, keys)
            if found is not None:
                return found
    return None


def extract_readback_content(raw_readback: dict[str, Any]) -> str:
    value = find_first_key(raw_readback, {"content"})
    return value if isinstance(value, str) else ""


def split_readback_slides(content: str) -> list[tuple[str, str]]:
    slides: list[tuple[str, str]] = []
    for match in re.finditer(r"<slide\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</slide>", content, flags=re.DOTALL):
        slide_id = match.group(1)
        body = re.sub(r"<[^>]+>", " ", match.group(2))
        slides.append((slide_id, body))
    return slides


def readback_visible_text_by_page(raw_readback: dict[str, Any]) -> dict[int, list[str]]:
    content = extract_readback_content(raw_readback)
    slides = split_readback_slides(content)
    return {index + 1: [text] for index, (_slide_id, text) in enumerate(slides)}


def all_readback_visible_text(raw_readback: dict[str, Any]) -> list[str]:
    return [text for _slide_id, text in split_readback_slides(extract_readback_content(raw_readback))]


def readback_slide_ids(raw_readback: dict[str, Any]) -> list[str]:
    return [slide_id for slide_id, _text in split_readback_slides(extract_readback_content(raw_readback))]


def build_plan_texts(project: Path) -> dict[str, list[str]]:
    paths = [DECK_PLAN, SLIDE_PLAN, CANVAS_PLAN]
    values: list[str] = []
    by_path: dict[str, list[str]] = {}
    for rel in paths:
        path = project / rel
        if path.exists():
            payload = read_json(path)
            texts = text_values(payload)
            by_path[rel.as_posix()] = texts
            values.extend(texts)
    by_path["__all__"] = values
    return by_path


def planned_slide_count(payload: dict[str, Any]) -> int | None:
    raw = payload.get("target_slide_count") or payload.get("page_count")
    if isinstance(raw, int):
        return raw
    slides = payload.get("slides")
    if isinstance(slides, list):
        return len(slides)
    return None


def plan_slides(payload: dict[str, Any]) -> list[dict[str, Any]]:
    slides = payload.get("slides")
    if not isinstance(slides, list):
        return []
    return [slide for slide in slides if isinstance(slide, dict)]


def slide_pages(slides: list[dict[str, Any]]) -> list[int]:
    pages: list[int] = []
    for index, slide in enumerate(slides, start=1):
        page = slide.get("page")
        pages.append(page if isinstance(page, int) else index)
    return pages


def template_matches(plan_slide: dict[str, Any], expected_template: str) -> bool:
    actual = plan_slide.get("template_id")
    if actual == expected_template:
        return True
    allowed = plan_slide.get("allowed_template_ids")
    return isinstance(allowed, list) and expected_template in allowed


def theme_matches(plan_slide: dict[str, Any], expected_theme: str) -> bool:
    actual = plan_slide.get("theme_id")
    return actual is None or actual == expected_theme


def constraint_terms(constraint: dict[str, Any], surface: str) -> list[str]:
    specific = constraint.get(f"required_{surface}_text")
    if isinstance(specific, list):
        return [item for item in specific if isinstance(item, str)]
    if surface == "plan":
        fallback = constraint.get("required_text")
        if isinstance(fallback, list):
            return [item for item in fallback if isinstance(item, str)]
    return []


def validate_repair_scope(project: Path, instruction: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    repair_path = project / REPAIR_PLAN
    policy = instruction.get("repair_policy") if isinstance(instruction.get("repair_policy"), dict) else {}
    if not repair_path.exists():
        return issues, {"present": False}
    payload = read_json(repair_path)
    expected_target = policy.get("target_plan_path")
    if isinstance(expected_target, str) and payload.get("target_plan_path") != expected_target:
        issues.append({"code": "repair_target_plan_mismatch", "message": f"repair target_plan_path must be {expected_target}"})
    allowed_prefixes = policy.get("allowed_path_prefixes") if isinstance(policy.get("allowed_path_prefixes"), list) else ["/slides/"]
    broad_paths = {"/", "/slides", "/slides/", "/slides/0", "/slides/1", "/slides/2", "/style_system", "/art_direction"}
    patches = payload.get("patches")
    if not isinstance(patches, list) or not patches:
        issues.append({"code": "repair_patches_missing", "message": "repair plan must include non-empty patches"})
        return issues, {"present": True, "patch_count": 0}
    scoped = []
    for index, patch in enumerate(patches):
        if not isinstance(patch, dict):
            issues.append({"code": "repair_patch_invalid", "message": f"repair patch {index} must be an object"})
            continue
        path = patch.get("path")
        if not isinstance(path, str) or not path.startswith("/"):
            issues.append({"code": "repair_patch_path_invalid", "message": f"repair patch {index} must use absolute JSON Pointer path"})
            continue
        if path in broad_paths or path.endswith("/canvas_spec") or path.endswith("/content"):
            issues.append({"code": "repair_patch_too_broad", "message": f"repair patch {index} path is too broad: {path}"})
        if not any(path.startswith(prefix) for prefix in allowed_prefixes if isinstance(prefix, str)):
            issues.append({"code": "repair_patch_outside_allowed_prefix", "message": f"repair patch {index} path is outside allowed prefixes: {path}"})
        value = patch.get("value")
        if isinstance(value, (dict, list)):
            issues.append({"code": "repair_patch_value_too_broad", "message": f"repair patch {index} must replace a leaf value, not object/list"})
        scoped.append({"op": patch.get("op"), "path": path, "leaf_value": not isinstance(value, (dict, list))})
    return issues, {"present": True, "patch_count": len(patches), "patches": scoped}


def validate_instruction_adherence(project: Path) -> dict[str, Any]:
    project = project.resolve()
    instruction_path = project / INSTRUCTION_FILE
    canvas_plan_path = project / CANVAS_PLAN
    instruction = read_json(instruction_path)
    deck_plan = read_json(project / DECK_PLAN)
    slide_plan = read_json(project / SLIDE_PLAN)
    canvas_plan = read_json(canvas_plan_path)
    readback_check, raw_readback = readback_payload(project)
    issues: list[dict[str, str]] = []
    if instruction.get("version") != "svglide-instruction/v1":
        issues.append({"code": "instruction_version_invalid", "message": "instruction must use svglide-instruction/v1"})
    target_slide_count = instruction.get("target_slide_count")
    slides = plan_slides(canvas_plan)
    deck_slides = plan_slides(deck_plan)
    planner_slides = plan_slides(slide_plan)
    if not slides:
        issues.append({"code": "plan_slides_missing", "message": "canvas plan must include slides[]"})
    plan_count = len(slides)
    svg_paths = slide_svg_paths(project)
    readback_ids = readback_slide_ids(raw_readback)
    readback_page_count = (((readback_check.get("checks") or {}).get("page_count") or {}).get("actual"))
    if isinstance(target_slide_count, int):
        for name, payload in (("deck-plan.json", deck_plan), ("slide-plan.json", slide_plan), ("slide_plan.json", canvas_plan)):
            count = planned_slide_count(payload)
            if count != target_slide_count:
                issues.append({"code": "target_slide_count_mismatch", "message": f"{name} slide count must be {target_slide_count}, got {count}"})
        for name, plan_list in (("deck-plan.json", deck_slides), ("slide-plan.json", planner_slides), ("slide_plan.json", slides)):
            if len(plan_list) != target_slide_count:
                issues.append({"code": "planner_slide_count_mismatch", "message": f"{name} slides[] length must be {target_slide_count}, got {len(plan_list)}"})
        if canvas_plan.get("target_slide_count") is not None and canvas_plan.get("target_slide_count") != target_slide_count:
            issues.append({"code": "target_slide_count_mismatch", "message": "canvas plan target_slide_count must match instruction"})
        if plan_count != target_slide_count:
            issues.append({"code": "plan_slide_count_mismatch", "message": f"plan has {plan_count} slides, expected {target_slide_count}"})
        if len(svg_paths) != target_slide_count:
            issues.append({"code": "output_slide_count_mismatch", "message": f"output has {len(svg_paths)} SVG pages, expected {target_slide_count}"})
        if readback_page_count != target_slide_count:
            issues.append({"code": "readback_slide_count_mismatch", "message": f"readback has {readback_page_count} pages, expected {target_slide_count}"})
        if len(readback_ids) != target_slide_count:
            issues.append({"code": "readback_slide_id_count_mismatch", "message": f"readback content has {len(readback_ids)} slide ids, expected {target_slide_count}"})
    expected_order = list(range(1, target_slide_count + 1)) if isinstance(target_slide_count, int) else slide_pages(slides)
    for name, page_order in (
        ("instruction.json", slide_pages(plan_slides({"slides": instruction.get("slides") if isinstance(instruction.get("slides"), list) else []}))),
        ("deck-plan.json", slide_pages(deck_slides)),
        ("slide-plan.json", slide_pages(planner_slides)),
        ("slide_plan.json", slide_pages(slides)),
    ):
        if page_order and page_order != expected_order:
            issues.append({"code": "page_order_mismatch", "message": f"{name} page order must be {expected_order}, got {page_order}"})
    binding = readback_check.get("input_binding") if isinstance(readback_check.get("input_binding"), dict) else {}
    binding_checks: list[dict[str, Any]] = []
    for binding_key, rel_path in (
        ("plan_sha256", CANVAS_PLAN),
        ("quality_gate_sha256", QUALITY_GATE),
        ("dry_run_sha256", DRY_RUN),
        ("ppe_proof_sha256", PPE_PROOF),
        ("live_create_sha256", LIVE_CREATE),
    ):
        path = project / rel_path
        if not path.exists():
            continue
        actual_sha = file_sha256(path)
        expected_sha = binding.get(binding_key)
        matched = expected_sha == actual_sha
        binding_checks.append({"binding_key": binding_key, "path": rel_path.as_posix(), "matched": matched})
        if expected_sha is not None and not matched:
            issues.append({"code": "readback_binding_hash_mismatch", "message": f"readback {binding_key} does not match current {rel_path.as_posix()}"})
    checks = readback_check.get("checks") if isinstance(readback_check.get("checks"), dict) else {}
    for check_name in ("page_count", "slide_order", "core_visible_text"):
        check = checks.get(check_name) if isinstance(checks.get(check_name), dict) else {}
        if check.get("status") != "passed":
            issues.append({"code": "readback_check_not_passed", "message": f"readback check {check_name} must be passed"})
    plan_texts = build_plan_texts(project)
    all_plan_texts = plan_texts.get("__all__", [])
    output_texts_by_page = {index + 1: svg_text(path) for index, path in enumerate(svg_paths)}
    readback_texts_by_page = readback_visible_text_by_page(raw_readback)
    all_output_texts = [text for texts in output_texts_by_page.values() for text in texts]
    all_readback_texts = all_readback_visible_text(raw_readback)
    page_checks: list[dict[str, Any]] = []
    expected_pages = instruction.get("slides") or instruction.get("page_order")
    if not isinstance(expected_pages, list):
        issues.append({"code": "instruction_page_order_missing", "message": "instruction must include slides[] or page_order[]"})
        expected_pages = []
    for expected in expected_pages:
        if not isinstance(expected, dict):
            issues.append({"code": "instruction_page_invalid", "message": "page_order entries must be objects"})
            continue
        page = expected.get("page")
        if not isinstance(page, int) or page < 1 or page > len(slides):
            issues.append({"code": "instruction_page_out_of_range", "message": f"instruction page out of range: {page}"})
            continue
        slide = slides[page - 1] if isinstance(slides[page - 1], dict) else {}
        deck_slide = deck_slides[page - 1] if page <= len(deck_slides) else {}
        planner_slide = planner_slides[page - 1] if page <= len(planner_slides) else {}
        expected_title = expected.get("title")
        expected_key_message = expected.get("key_message")
        expected_template = expected.get("template_id")
        expected_theme = expected.get("theme_id")
        slide_template = (slide.get("canvas_spec") or {}).get("template_id") if isinstance(slide.get("canvas_spec"), dict) else slide.get("template_id")
        slide_theme = (slide.get("canvas_spec") or {}).get("theme_id") if isinstance(slide.get("canvas_spec"), dict) else slide.get("theme_id")
        if expected_title and slide.get("title") != expected_title:
            issues.append({"code": "page_title_mismatch", "message": f"page {page} title mismatch"})
        if expected_key_message and slide.get("key_message") != expected_key_message:
            issues.append({"code": "page_key_message_mismatch", "message": f"page {page} key_message mismatch"})
        for plan_name, plan_slide in (("deck-plan.json", deck_slide), ("slide-plan.json", planner_slide)):
            if expected_title and plan_slide.get("title") != expected_title:
                issues.append({"code": "planner_page_title_mismatch", "message": f"page {page} {plan_name} title mismatch"})
            if expected_key_message and plan_slide.get("key_message") != expected_key_message:
                issues.append({"code": "planner_key_message_mismatch", "message": f"page {page} {plan_name} key_message mismatch"})
        if expected_template and slide_template != expected_template:
            issues.append({"code": "page_template_mismatch", "message": f"page {page} template mismatch"})
        for plan_name, plan_slide in (("deck-plan.json", deck_slide), ("slide-plan.json", planner_slide)):
            if expected_template and not template_matches(plan_slide, expected_template):
                issues.append({"code": "planner_template_mismatch", "message": f"page {page} {plan_name} template mismatch"})
        if expected_theme and slide_theme != expected_theme:
            issues.append({"code": "page_theme_mismatch", "message": f"page {page} theme mismatch"})
        for plan_name, plan_slide in (("deck-plan.json", deck_slide), ("slide-plan.json", planner_slide)):
            if expected_theme and not theme_matches(plan_slide, expected_theme):
                issues.append({"code": "planner_theme_mismatch", "message": f"page {page} {plan_name} theme mismatch"})
        required_text = expected.get("required_text")
        missing_plan: list[str] = []
        missing_output: list[str] = []
        missing_readback: list[str] = []
        page_text_requirements: list[str] = []
        if isinstance(expected_title, str):
            page_text_requirements.append(expected_title)
        if isinstance(expected_key_message, str):
            page_text_requirements.append(expected_key_message)
        if isinstance(required_text, list):
            page_text_requirements.extend([item for item in required_text if isinstance(item, str)])
        if page_text_requirements:
            page_plan_texts = text_values(slide)
            page_output_texts = output_texts_by_page.get(page, [])
            page_readback_texts = readback_texts_by_page.get(page, [])
            for item in page_text_requirements:
                if not contains_text(page_plan_texts, item):
                    missing_plan.append(item)
                if not contains_text(page_output_texts, item):
                    missing_output.append(item)
                if not contains_text(page_readback_texts, item):
                    missing_readback.append(item)
        if missing_plan:
            issues.append({"code": "page_required_text_missing_in_plan", "message": f"page {page} missing required text in plan: {missing_plan}"})
        if missing_output:
            issues.append({"code": "page_required_text_missing_in_output", "message": f"page {page} missing required text in SVG output: {missing_output}"})
        if missing_readback:
            issues.append({"code": "page_required_text_missing_in_readback", "message": f"page {page} missing required text in readback: {missing_readback}"})
        page_checks.append({
            "page": page,
            "title": slide.get("title"),
            "template_id": slide_template,
            "theme_id": slide_theme,
            "required_text_count": len(page_text_requirements),
            "missing_plan_text": missing_plan,
            "missing_output_text": missing_output,
            "missing_readback_text": missing_readback,
        })
    language = instruction.get("language")
    if language == "zh-CN":
        for page, texts in output_texts_by_page.items():
            if not any(has_cjk(value) for value in texts):
                issues.append({"code": "language_cjk_missing", "message": f"page {page} output has no CJK text"})
        for page, texts in readback_texts_by_page.items():
            if not any(has_cjk(value) for value in texts):
                issues.append({"code": "readback_language_cjk_missing", "message": f"page {page} readback has no CJK text"})
    explicit_constraints = instruction.get("explicit_constraints")
    constraint_checks: list[dict[str, Any]] = []
    if isinstance(explicit_constraints, list):
        for constraint in explicit_constraints:
            if not isinstance(constraint, dict):
                issues.append({"code": "constraint_invalid", "message": "explicit constraint entries must be objects"})
                continue
            constraint_id = constraint.get("id")
            missing_by_surface: dict[str, list[str]] = {}
            for surface, haystack in (
                ("plan", all_plan_texts),
                ("output", all_output_texts),
                ("readback", all_readback_texts),
            ):
                missing = [
                    item
                    for item in constraint_terms(constraint, surface)
                    if not contains_text(haystack, item)
                ]
                if missing:
                    missing_by_surface[surface] = missing
                    issues.append({
                        "code": "constraint_text_missing",
                        "message": f"constraint {constraint_id} missing {surface} evidence text: {missing}",
                    })
            constraint_checks.append({"id": constraint_id, "missing_text": missing_by_surface})
    else:
        issues.append({"code": "explicit_constraints_missing", "message": "instruction lock must include explicit_constraints[]"})
    must_include = instruction.get("must_include")
    must_include_missing: list[str] = []
    if isinstance(must_include, list):
        for item in must_include:
            if isinstance(item, str) and not contains_text(all_readback_texts, item):
                must_include_missing.append(item)
        if must_include_missing:
            issues.append({"code": "must_include_missing_in_readback", "message": f"must_include missing in readback: {must_include_missing}"})
    else:
        issues.append({"code": "must_include_missing", "message": "instruction must include must_include[]"})
    must_avoid = instruction.get("must_avoid")
    must_avoid_present: list[str] = []
    if isinstance(must_avoid, list):
        for item in must_avoid:
            if isinstance(item, str) and (contains_text(all_readback_texts, item) or contains_text(all_output_texts, item)):
                must_avoid_present.append(item)
        if must_avoid_present:
            issues.append({"code": "must_avoid_present_in_output", "message": f"must_avoid text present in output/readback: {must_avoid_present}"})
    else:
        issues.append({"code": "must_avoid_missing", "message": "instruction must include must_avoid[]"})
    repair_issues, repair_scope = validate_repair_scope(project, instruction)
    issues.extend(repair_issues)
    repair_recommendations: list[dict[str, str]] = []
    for issue in issues:
        code = issue.get("code", "")
        if "slide_count" in code or "page_order" in code:
            repair_recommendations.append({"strategy": "scoped_append_or_delete_page", "reason": code})
        elif "missing" in code or "mismatch" in code or "must_avoid" in code:
            repair_recommendations.append({"strategy": "scoped_leaf_patch", "reason": code})
    if not repair_recommendations:
        repair_recommendations.append({"strategy": "no_repair_needed", "reason": "instruction adherence passed"})
    output_hashes = [{"path": relpath(path, project), "sha256": file_sha256(path)} for path in svg_paths]
    payload = {
        "version": CHECK_VERSION,
        "stage": "instruction_adherence",
        "status": "passed" if not issues else "failed",
        "checked_at": now_iso(),
        "project": project.as_posix(),
        "instruction": {"path": INSTRUCTION_FILE.as_posix(), "sha256": file_sha256(instruction_path)},
        "deck_plan": {"path": DECK_PLAN.as_posix(), "sha256": file_sha256(project / DECK_PLAN), "slide_count": planned_slide_count(deck_plan)},
        "slide_plan": {"path": SLIDE_PLAN.as_posix(), "sha256": file_sha256(project / SLIDE_PLAN), "slide_count": planned_slide_count(slide_plan)},
        "plan": {"path": CANVAS_PLAN.as_posix(), "sha256": file_sha256(canvas_plan_path), "slide_count": plan_count},
        "target_slide_count": target_slide_count,
        "output_pages": output_hashes,
        "readback": {
            "check_path": READBACK_CHECK.as_posix(),
            "check_sha256": file_sha256(project / READBACK_CHECK),
            "raw_path": READBACK_RAW.as_posix(),
            "raw_sha256": file_sha256(project / READBACK_RAW),
            "slide_count": readback_page_count,
            "slide_ids": readback_ids,
            "binding_checks": binding_checks,
        },
        "page_checks": page_checks,
        "constraint_checks": constraint_checks,
        "must_include_missing": must_include_missing,
        "must_avoid_present": must_avoid_present,
        "repair_scope": repair_scope,
        "repair_recommendations": repair_recommendations,
        "issues": issues,
    }
    return payload


def write_check_outputs(project: Path, payload: dict[str, Any]) -> None:
    write_json(project / CHECK_PATH, payload)
    write_json(project / RECEIPT_PATH, payload)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate user instruction, plan, output, and repair adherence for an SVGlide project.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        payload = validate_instruction_adherence(args.project)
        write_check_outputs(args.project, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    except InstructionAdherenceError as err:
        payload = {
            "version": CHECK_VERSION,
            "stage": "instruction_adherence",
            "status": "failed",
            "checked_at": now_iso(),
            "project": args.project.as_posix(),
            "issues": [{"code": "instruction_adherence_error", "message": str(err)}],
        }
        write_check_outputs(args.project, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
