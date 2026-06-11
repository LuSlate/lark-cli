#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TOP_LEVEL_ALLOWED_INDEXES = {
    "slides +create-svg",
    "svglide-route-admission.md",
    "svg-private-manifest.json",
}

TOP_LEVEL_PRIVATE_TOKENS = [
    "style-presets",
    "visual_recipe",
    "visual_signature",
    "svg_effects",
    "svg_effect",
    "safe-native-v1",
    "required_primitives",
    "svg_primitives",
    "xml_like_risk",
]

ROUTE_ADMISSION_BODY_TOKENS = [
    "style_preset",
    "visual_recipe",
    "visual_signature",
    "svg_effects",
    "required_primitives",
    "svg_primitives",
    "xml_like_risk",
    "content_density_contract",
]

XML_DOC_PRIVATE_TOKENS = TOP_LEVEL_PRIVATE_TOKENS + [
    "svg_preflight.py",
    "svg-aesthetic-review.md",
    "svglide-plan.schema.json",
    "safe-native-v1.profile.json",
]

SVG_ONLY_PLAN_FIELDS = {
    "style_preset",
    "style_selection_reason",
    "style_system",
    "svg_constraints",
    "svg_files",
    "visual_recipe",
    "visual_intent",
    "visual_focal_point",
    "visual_signature",
    "svg_effects",
    "required_primitives",
    "svg_primitives",
    "xml_like_risk",
    "recipe_fallback",
    "content_density_contract",
    "risk_flags",
    "source_status",
    "source_policy",
    "asset_contract",
    "fallback_policy",
    "requires_fallback",
}

SVG_REQUIRED_TOP_FIELDS = {
    "style_preset",
    "style_selection_reason",
    "style_system",
    "slides",
}

SVG_REQUIRED_SLIDE_FIELDS = {
    "renderer_id",
    "layout_family",
    "visual_recipe",
    "visual_intent",
    "visual_focal_point",
    "visual_signature",
    "svg_effects",
    "required_primitives",
    "svg_primitives",
    "xml_like_risk",
    "content_density_contract",
    "risk_flags",
    "source_policy",
}

XML_SHARED_DOCS = [
    "references/planning-layer.md",
    "references/validation-checklist.md",
    "references/visual-planning.md",
    "references/asset-planning.md",
]

XML_CREATE_PRIVATE_SYMBOL_RE = re.compile(
    r"\bSVGlide\b|"
    r"\bsvgFallback[A-Za-z0-9_]*\b|"
    r"\bclassifySVGlide[A-Za-z0-9_]*\b|"
    r"\bsvgPlan[A-Za-z0-9_]*\b|"
    r"safe-native-v1|"
    r"internal/svglide|"
    r"svg_preflight|"
    r"style-presets|"
    r"visual_recipe|"
    r"visual_signature|"
    r"svg_effects|"
    r"required_primitives|"
    r"svg_primitives|"
    r"xml_like_risk"
)


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, path: str, message: str, detail: str | None = None) -> dict[str, str]:
    item = {"code": code, "path": path, "message": message}
    if detail:
        item["detail"] = detail
    return item


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def token_occurrences(text: str, tokens: list[str]) -> list[str]:
    lower = text.lower()
    return sorted({token for token in tokens if token.lower() in lower})


def private_reference_names(manifest: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for raw in manifest.get("private_strategy_files", []):
        if not isinstance(raw, str):
            continue
        if any(char in raw for char in "*?[]"):
            continue
        names.add(raw)
        names.add(Path(raw).name)
    return {name for name in names if name}


def lint_top_skill(repo_root: Path, root: Path) -> list[dict[str, str]]:
    path = root / "SKILL.md"
    issues: list[dict[str, str]] = []
    if not path.exists():
        return [issue("missing_top_skill", relpath(path, repo_root), "SKILL.md is missing")]
    text = read_text(path)
    for token in token_occurrences(text, TOP_LEVEL_PRIVATE_TOKENS):
        issues.append(
            issue(
                "top_skill_private_token",
                relpath(path, repo_root),
                "Top-level skill contains SVG private strategy token",
                token,
            )
        )
    for token in TOP_LEVEL_ALLOWED_INDEXES:
        if token not in text:
            issues.append(
                issue(
                    "top_skill_missing_route_index",
                    relpath(path, repo_root),
                    "Top-level skill must keep route admission indexes",
                    token,
                )
            )
    return issues


def lint_route_admission(repo_root: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for raw in manifest.get("route_admission_files", []):
        if not isinstance(raw, str):
            issues.append(issue("route_admission_path_invalid", "<manifest>", "Route admission path must be a string", repr(raw)))
            continue
        path = repo_root / raw
        if not path.exists():
            issues.append(issue("route_admission_missing", raw, "Route admission file is missing"))
            continue
        text = read_text(path)
        for token in token_occurrences(text, ROUTE_ADMISSION_BODY_TOKENS):
            issues.append(
                issue(
                    "route_admission_private_body_token",
                    raw,
                    "Route admission file must not contain SVG strategy field body",
                    token,
                )
            )
    return issues


def lint_xml_docs(repo_root: Path, root: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    private_names = private_reference_names(manifest)
    for rel in XML_SHARED_DOCS:
        path = root / rel
        if not path.exists():
            continue
        text = read_text(path)
        for token in token_occurrences(text, XML_DOC_PRIVATE_TOKENS):
            issues.append(
                issue(
                    "xml_doc_private_token",
                    relpath(path, repo_root),
                    "XML/shared doc contains SVG private strategy token",
                    token,
                )
            )
        for name in sorted(private_names):
            if name in text:
                issues.append(
                    issue(
                        "xml_doc_private_reference",
                        relpath(path, repo_root),
                        "XML/shared doc references an SVG private strategy file",
                        name,
                    )
                )
    return issues


def is_svg_plan(plan: dict[str, Any]) -> bool:
    return plan.get("route") == "svglide-svg" or plan.get("output_mode") == "svglide-svg"


def walk_dict_keys(value: Any, path: str = "$") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            out.append((key, child_path))
            out.extend(walk_dict_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.extend(walk_dict_keys(child, f"{path}[{index}]"))
    return out


def lint_plan(plan: dict[str, Any], path: str = "<plan>") -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not is_svg_plan(plan):
        for key, key_path in walk_dict_keys(plan):
            if key in SVG_ONLY_PLAN_FIELDS:
                issues.append(
                    issue(
                        "xml_plan_svg_only_field",
                        path,
                        "XML route plan contains SVG-only field",
                        key_path,
                    )
                )
        return issues

    for key in sorted(SVG_REQUIRED_TOP_FIELDS):
        if key not in plan:
            issues.append(issue("svg_plan_missing_required_top_field", path, "SVG route plan missing required top-level field", key))
    if plan.get("route") != "svglide-svg" and plan.get("output_mode") != "svglide-svg":
        issues.append(issue("svg_plan_missing_route", path, "SVG route plan must declare route or output_mode as svglide-svg"))

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        issues.append(issue("svg_plan_missing_slides", path, "SVG route plan must contain a non-empty slides array"))
        return issues

    for index, slide in enumerate(slides):
        if not isinstance(slide, dict):
            issues.append(issue("svg_plan_slide_invalid", path, "SVG route slide must be an object", f"slides[{index}]"))
            continue
        for key in sorted(SVG_REQUIRED_SLIDE_FIELDS):
            if key not in slide:
                issues.append(
                    issue(
                        "svg_plan_missing_required_slide_field",
                        path,
                        "SVG route slide missing required field",
                        f"slides[{index}].{key}",
                    )
                )
    return issues


def lint_plan_file(path: Path) -> list[dict[str, str]]:
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return [issue("plan_json_invalid", path.as_posix(), "Plan JSON cannot be loaded", str(error))]
    if not isinstance(data, dict):
        return [issue("plan_root_invalid", path.as_posix(), "Plan root must be an object")]
    return lint_plan(data, path.as_posix())


def lint_code_imports(repo_root: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    slides_dir = repo_root / "shortcuts" / "slides"
    if slides_dir.exists():
        for path in sorted(slides_dir.glob("*create*.go")):
            name = path.name
            if name.endswith("_test.go") or name == "slides_create_svg.go":
                continue
            text = read_text(path)
            match = XML_CREATE_PRIVATE_SYMBOL_RE.search(text)
            if match:
                issues.append(
                    issue(
                        "xml_create_private_symbol",
                        relpath(path, repo_root),
                        "XML create path must not reference SVG private symbols",
                        match.group(0),
                    )
                )

    for rel in ["apps/server/tasks", "apps/server/controller"]:
        directory = repo_root / rel
        if not directory.exists():
            continue
        for path in sorted(directory.glob("**/*.ts")):
            text = read_text(path)
            if "modules/svg-parser-module/src/" in text or "safe-native-v1" in text:
                issues.append(
                    issue(
                        "server_private_svg_import",
                        relpath(path, repo_root),
                        "Shared server route must not import/read SVG private strategy internals",
                    )
                )
    return issues


def lint_manifest_shape(repo_root: Path, manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if manifest.get("route") != "svglide-svg":
        issues.append(issue("manifest_route_invalid", relpath(manifest_path, repo_root), "Manifest route must be svglide-svg"))
    for key in ["route_admission_files", "private_strategy_files", "allowed_route_entrypoints"]:
        if not isinstance(manifest.get(key), list) or not manifest.get(key):
            issues.append(issue("manifest_list_missing", relpath(manifest_path, repo_root), "Manifest must contain a non-empty list", key))
    return issues


def lint_repository(repo_root: Path, root_rel: str, manifest_rel: str, plan_paths: list[str] | None = None) -> list[dict[str, str]]:
    repo_root = repo_root.resolve()
    root = (repo_root / root_rel).resolve()
    manifest_path = (repo_root / manifest_rel).resolve()
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as error:
        return [issue("manifest_json_invalid", relpath(manifest_path, repo_root), "Manifest JSON cannot be loaded", str(error))]
    if not isinstance(manifest, dict):
        return [issue("manifest_root_invalid", relpath(manifest_path, repo_root), "Manifest root must be an object")]

    issues: list[dict[str, str]] = []
    issues.extend(lint_manifest_shape(repo_root, manifest_path, manifest))
    issues.extend(lint_top_skill(repo_root, root))
    issues.extend(lint_route_admission(repo_root, manifest))
    issues.extend(lint_xml_docs(repo_root, root, manifest))
    issues.extend(lint_code_imports(repo_root))

    for raw in plan_paths or []:
        issues.extend(lint_plan_file((repo_root / raw).resolve()))
    return issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint SVGlide route isolation boundaries")
    parser.add_argument("--manifest", default="skills/lark-slides/references/svg-private-manifest.json")
    parser.add_argument("--root", default="skills/lark-slides")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--plan", action="append", default=[], help="Optional slide_plan.json to validate")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    options = parse_args(argv)
    repo_root = Path(options.repo_root)
    issues = lint_repository(repo_root, options.root, options.manifest, options.plan)
    result = {
        "summary": {
            "error_count": len(issues),
        },
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
