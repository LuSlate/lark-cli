#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import svglide_artboard_renderer as artboard
import svglide_schema


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
CONTRACTS_PATH = Path("skills/lark-slides/references/svglide-planner-prompt-contracts.json")
OUTPUT_PATH = Path("06-check/planner-contract-check.json")
RECEIPT_PATH = Path("receipts/planner-contract-check.json")
REQUIRED_PROMPT_IDS = {"deck-planner", "slide-planner", "canvas-planner", "repair-planner"}
FORBIDDEN_MARKUP_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"<\s*html\b",
        r"<\s*(div|span|p|section|article|main|body)\b",
        r"<\s*style\b",
        r"<\s*script\b",
        r"<\s*svg\b",
        r"```html",
        r"```css",
        r"```svg",
        r"<!doctype",
        r"\bclass\s*=",
        r"\bclassName\s*=",
        r"\bbase64,",
    ]
]
FORBIDDEN_REPAIR_TOP_LEVEL_KEYS = {"slides", "canvas_spec", "deck_plan", "slide_plan", "full_deck", "html", "css", "svg"}
UNSCOPED_PATCH_PATHS = {"", "/", "/slides"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def issue(code: str, message: str, *, path: str | None = None, prompt_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        payload["path"] = path
    if prompt_id is not None:
        payload["prompt_id"] = prompt_id
    return payload


def repo_path(rel: str) -> Path:
    return REPO_ROOT / rel


def project_path(project: Path, rel: str) -> Path:
    return project / rel


def iter_strings(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(iter_strings(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(iter_strings(item))
    return result


def markup_issues(payload: Any, *, path: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for text in iter_strings(payload):
        for pattern in FORBIDDEN_MARKUP_PATTERNS:
            if pattern.search(text):
                issues.append(issue("planner_output_forbidden_markup", "planner output contains forbidden free markup", path=path))
                return issues
    return issues


def validate_contract_file() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    contracts_path = repo_path(CONTRACTS_PATH.as_posix())
    contracts = read_json(contracts_path)
    records = contracts.get("contracts") if isinstance(contracts, dict) else None
    if not isinstance(records, list):
        return {}, [issue("prompt_contracts_invalid", "contracts must be an array", path=CONTRACTS_PATH.as_posix())], []
    prompt_ids = {item.get("id") for item in records if isinstance(item, dict)}
    missing = REQUIRED_PROMPT_IDS - {item for item in prompt_ids if isinstance(item, str)}
    for prompt_id in sorted(missing):
        issues.append(issue("prompt_contract_missing", f"missing prompt contract: {prompt_id}", prompt_id=prompt_id))
    pages: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            issues.append(issue("prompt_contract_invalid", "contract entry must be an object"))
            continue
        prompt_id = str(item.get("id") or "")
        required = ["prompt_path", "input_bundle", "output_schema", "output_path", "validation_command", "forbidden_outputs"]
        for key in required:
            if key not in item:
                issues.append(issue("prompt_contract_field_missing", f"contract missing {key}", prompt_id=prompt_id))
        prompt_path = repo_path(str(item.get("prompt_path") or ""))
        schema_path = repo_path(str(item.get("output_schema") or ""))
        if not prompt_path.exists():
            issues.append(issue("prompt_file_missing", f"prompt file does not exist: {prompt_path}", prompt_id=prompt_id))
            continue
        if not schema_path.exists():
            issues.append(issue("prompt_schema_missing", f"output schema does not exist: {schema_path}", prompt_id=prompt_id))
        prompt_text = prompt_path.read_text(encoding="utf-8")
        expected_tokens = [str(item.get("output_schema") or ""), str(item.get("output_path") or ""), str(item.get("validation_command") or "")]
        for token in expected_tokens:
            if token and token not in prompt_text:
                issues.append(issue("prompt_contract_declaration_missing", f"prompt file does not declare {token}", prompt_id=prompt_id))
        lowered = prompt_text.lower()
        for token in ["json only", "html", "css", "svg"]:
            if token not in lowered:
                issues.append(issue("prompt_forbidden_output_not_declared", f"prompt file must explicitly mention {token}", prompt_id=prompt_id))
        forbidden = item.get("forbidden_outputs")
        if not isinstance(forbidden, list) or not {"free_html", "free_css", "free_svg", "markdown_fence"}.issubset(set(forbidden)):
            issues.append(issue("prompt_contract_forbidden_outputs_incomplete", "forbidden_outputs must include free_html/free_css/free_svg/markdown_fence", prompt_id=prompt_id))
        pages.append(
            {
                "id": prompt_id,
                "prompt_path": str(item.get("prompt_path") or ""),
                "prompt_sha256": file_sha256(prompt_path),
                "output_schema": str(item.get("output_schema") or ""),
                "output_path": str(item.get("output_path") or ""),
            }
        )
    return contracts, issues, pages


def validate_schema_payload(payload: Any, schema_rel: str, *, path: str) -> list[dict[str, Any]]:
    schema = read_json(repo_path(schema_rel))
    return [issue(item["code"], item["message"], path=item["path"]) for item in svglide_schema.validate_json_schema(payload, schema)]


def validate_canvas_plan(project: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(validate_schema_payload(payload, "skills/lark-slides/references/svglide-plan.schema.json", path="02-plan/slide_plan.json"))
    slides = payload.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            issues.append(issue("planner_slide_invalid", f"slide {index} must be an object", path=f"$.slides[{index - 1}]"))
            continue
        spec = slide.get("canvas_spec")
        if not isinstance(spec, dict):
            issues.append(issue("planner_canvas_spec_missing", f"slide {index} is missing canvas_spec", path=f"$.slides[{index - 1}].canvas_spec"))
            continue
        for item in artboard.validate_canvas_spec(spec, page=index):
            issues.append(issue(item["code"], item["message"], path=f"$.slides[{index - 1}].canvas_spec"))
        registry_issues, _ = artboard.validate_registry_bindings(project, spec, page=index)
        for item in registry_issues:
            issues.append(issue(item["code"], item["message"], path=f"$.slides[{index - 1}].canvas_spec"))
    return issues


def validate_slide_plan(project: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    _, template_registry, templates = artboard.load_template_registry(project)
    _, theme_registry, themes = artboard.load_theme_registry(project)
    include_legacy_templates = template_registry.get("include_legacy_debug") is True
    include_legacy_themes = theme_registry.get("include_legacy_debug") is True
    slides = payload.get("slides")
    if not isinstance(slides, list):
        return issues
    for index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        template_id = slide.get("template_id")
        theme_id = slide.get("theme_id")
        template = templates.get(template_id) if isinstance(template_id, str) else None
        theme = themes.get(theme_id) if isinstance(theme_id, str) else None
        path = f"$.slides[{index}]"
        if template is None:
            issues.append(issue("slide_plan_template_unknown", f"template_id is not registered: {template_id!r}", path=f"{path}.template_id"))
        elif not artboard.beautiful_template_runtime.is_runtime_selectable(template, include_legacy_debug=include_legacy_templates):
            issues.append(issue("slide_plan_template_inactive", f"template_id is not active: {template_id!r}", path=f"{path}.template_id"))
        if theme is None:
            issues.append(issue("slide_plan_theme_unknown", f"theme_id is not registered: {theme_id!r}", path=f"{path}.theme_id"))
        elif not artboard.beautiful_template_runtime.is_runtime_selectable(theme, include_legacy_debug=include_legacy_themes):
            issues.append(issue("slide_plan_theme_inactive", f"theme_id is not active: {theme_id!r}", path=f"{path}.theme_id"))
        allowed = template.get("supported_theme_ids") if isinstance(template, dict) else None
        if isinstance(allowed, list) and isinstance(theme_id, str) and theme_id not in allowed:
            issues.append(issue("slide_plan_theme_not_allowed", f"template_id {template_id!r} does not allow theme_id {theme_id!r}", path=f"{path}.theme_id"))
    return issues


def validate_repair_plan(payload: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for key in FORBIDDEN_REPAIR_TOP_LEVEL_KEYS:
        if key in payload:
            issues.append(issue("repair_plan_full_rewrite_forbidden", f"repair plan must not contain top-level {key}", path=f"$.{key}"))
    patches = payload.get("patches")
    if not isinstance(patches, list):
        return issues
    for index, patch in enumerate(patches):
        if not isinstance(patch, dict):
            issues.append(issue("repair_patch_invalid", "patch must be an object", path=f"$.patches[{index}]"))
            continue
        path = patch.get("path")
        if not isinstance(path, str):
            issues.append(issue("repair_patch_path_invalid", "patch.path must be a string", path=f"$.patches[{index}].path"))
            continue
        if path in UNSCOPED_PATCH_PATHS or re.fullmatch(r"/slides/\d+", path) or re.fullmatch(r"/slides/\d+/canvas_spec", path):
            issues.append(issue("repair_patch_unscoped", f"patch path is too broad: {path}", path=f"$.patches[{index}].path"))
        if re.fullmatch(r"/slides/\d+/canvas_spec/(content|theme|semantic_elements|quality_constraints)", path) or re.fullmatch(r"/slides/\d+/content_requirements", path):
            issues.append(issue("repair_patch_broad_path", f"patch path must target a leaf field, not a whole object: {path}", path=f"$.patches[{index}].path"))
        if not (path.startswith("/slides/") or path.startswith("/style_system/") or path.startswith("/art_direction/")):
            issues.append(issue("repair_patch_path_not_allowed", f"patch path must target slides/style_system/art_direction: {path}", path=f"$.patches[{index}].path"))
        if path in {"/style_system", "/art_direction"}:
            issues.append(issue("repair_patch_broad_path", f"patch path must target a leaf field, not a whole object: {path}", path=f"$.patches[{index}].path"))
        value = patch.get("value")
        if patch.get("op") in {"add", "replace"} and isinstance(value, (dict, list)):
            issues.append(issue("repair_patch_value_too_broad", "repair patch values must be scalar leaf values", path=f"$.patches[{index}].value"))
    return issues


def validate_outputs(project: Path, contracts: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    for contract in contracts.get("contracts", []):
        if not isinstance(contract, dict):
            continue
        prompt_id = str(contract.get("id") or "")
        output_rel = str(contract.get("output_path") or "")
        schema_rel = str(contract.get("output_schema") or "")
        output_path = project_path(project, output_rel)
        if not output_path.exists():
            issues.append(issue("planner_output_missing", f"missing planner output: {output_rel}", prompt_id=prompt_id))
            continue
        try:
            payload = read_json(output_path)
        except json.JSONDecodeError as error:
            issues.append(issue("planner_output_json_invalid", str(error), path=output_rel, prompt_id=prompt_id))
            continue
        output_issues = validate_schema_payload(payload, schema_rel, path=output_rel)
        output_issues.extend(markup_issues(payload, path=output_rel))
        if prompt_id == "slide-planner" and isinstance(payload, dict):
            output_issues.extend(validate_slide_plan(project, payload))
        if prompt_id == "canvas-planner" and isinstance(payload, dict):
            output_issues.extend(validate_canvas_plan(project, payload))
        if prompt_id == "repair-planner" and isinstance(payload, dict):
            output_issues.extend(validate_repair_plan(payload))
        issues.extend({**item, "prompt_id": prompt_id} for item in output_issues)
        pages.append(
            {
                "prompt_id": prompt_id,
                "output_path": output_rel,
                "output_sha256": file_sha256(output_path),
                "schema": schema_rel,
                "error_count": len(output_issues),
            }
        )
    return issues, pages


def run(project: Path) -> dict[str, Any]:
    project = project.resolve()
    contracts, contract_issues, prompt_pages = validate_contract_file()
    output_issues, output_pages = validate_outputs(project, contracts) if contracts else ([], [])
    issues = contract_issues + output_issues
    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-planner-contract-check/v1",
        "stage": "planner-contract-check",
        "status": status,
        "action": "continue_to_generate_svg" if status == "passed" else "repair_and_rerun",
        "inputs": {
            "prompt_contracts": CONTRACTS_PATH.as_posix(),
            "prompt_contracts_sha256": file_sha256(repo_path(CONTRACTS_PATH.as_posix())),
            "project": project.as_posix(),
        },
        "prompt_contracts": prompt_pages,
        "planner_outputs": output_pages,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "prompt_contract_count": len(prompt_pages),
            "planner_output_count": len(output_pages),
        },
        "issues": issues,
        "output_path": OUTPUT_PATH.as_posix(),
        "receipt_path": RECEIPT_PATH.as_posix(),
    }
    write_json(project / OUTPUT_PATH, result)
    write_json(project / RECEIPT_PATH, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SVGlide planner prompt contracts and structured planner outputs.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.project)
    except (OSError, json.JSONDecodeError) as error:
        print(f"svglide_planner_contracts: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
