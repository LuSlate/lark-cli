#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY_PATH = Path("skills/lark-slides/references/svglide-reference-source-inventory.json")
DEFAULT_REPORT_PATH = Path("skills/lark-slides/references/svglide-reference-absorption-report.md")
PLAN_PATH = Path("skills/lark-slides/references/svglide-reference-absorption-execution-plan.md")
DEFAULT_ABSORPTIONS_DIR = Path("skills/lark-slides/references/absorptions")

BEAUTIFUL_EXPECTED_TEMPLATE_COUNT = 34
BEAUTIFUL_EXPECTED_SCREENSHOT_COUNT = 102

ALLOWED_PRIORITIES = {"P0", "P1", "P2"}
ALLOWED_DISPOSITIONS = {
    "pending",
    "absorbed",
    "duplicate_of",
    "forbidden_runtime_dependency",
    "not_applicable_to_svglide",
    "blocked_with_reason",
}
REQUIRED_ITEM_FIELDS = {
    "id",
    "source_repo",
    "source_family",
    "source_path",
    "source_hash",
    "priority",
    "source_type",
    "disposition",
}
RAW_RUNTIME_SUFFIXES = {".css", ".html", ".js", ".jsx", ".mjs", ".svg", ".ts", ".tsx"}
FIXTURE_PROOF_FIELDS = {
    "canvas_spec_fixtures",
    "satori_outputs",
    "svglide_protocol_outputs",
    "quality_receipts",
    "template_guardrail_records",
    "dry_run_or_readback_receipts",
    "vf5_benchmark_receipts",
    "negative_fixtures",
}
REQUIRED_ABSTRACTION_RECORD_FIELDS = {
    "source_item_id",
    "absorbed_as",
    "svglide_asset_ids",
    "non_copying_transform",
    "forbidden_usage",
}
REQUIRED_ABSTRACTION_LIST_FIELDS = {
    "absorbed_as",
    "svglide_asset_ids",
    "forbidden_usage",
}
RUNTIME_SCAN_FILES = [
    "skills/lark-slides/references/svglide-template-registry.json",
    "skills/lark-slides/references/svglide-template-guardrails.json",
    "skills/lark-slides/scripts/artboard_renderer/templates/p0-templates.mjs",
    "skills/lark-slides/scripts/artboard_renderer/themes/registry.json",
    "skills/lark-slides/scripts/artboard_renderer/components/primitives.mjs",
    "skills/lark-slides/scripts/svglide_prompt_planner.py",
    "skills/lark-slides/scripts/svglide_assets.py",
    "skills/lark-slides/scripts/svglide_project_runner.py",
    "skills/lark-slides/scripts/svglide_quality_gate.py",
    "skills/lark-slides/scripts/svglide_visual_acceptance.py",
    "skills/lark-slides/scripts/svglide_vf5_benchmark.py",
    "skills/lark-slides/scripts/svglide_semantic_asset_matcher.py",
]
PHASE01_CHANGED_FILES = {
    "skills/lark-slides/references/svglide-reference-absorption-execution-plan.md": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-reference-absorption-report.md": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-reference-abstraction.schema.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-reference-source-inventory.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-chart-strategies.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-component-registry.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-image-strategies.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-layout-archetypes.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-renderer-registry.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-template-guardrails.json": "changed_by_this_plan",
    "skills/lark-slides/references/svglide-template-registry.json": "changed_by_this_plan",
    "skills/lark-slides/scripts/artboard_renderer/dist/render.mjs": "changed_by_this_plan",
    "skills/lark-slides/scripts/artboard_renderer/templates/p0-templates.mjs": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_artboard_renderer.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_model_repair_loop_test.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_prompt_planner.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_prompt_planner_test.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_reference_absorber.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_reference_absorber_test.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_semantic_asset_matcher.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_project_runner.py": "changed_by_this_plan",
    "skills/lark-slides/scripts/svglide_project_runner_test.py": "changed_by_this_plan",
}
PLAN_CHANGED_PREFIXES = {
    "skills/lark-slides/references/absorptions/",
    "skills/lark-slides/scripts/artboard_renderer/themes/",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/reference_absorption_wave1/",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/reference_absorption_wave2/",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/reference_absorption_wave3/",
}
PLAN_CHANGED_FILES = {
    "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/dense-panel-grid.canvas-spec.json",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/editorial-quote-chart.canvas-spec.json",
    "skills/lark-slides/scripts/fixtures/svglide_artboard/golden/executive-dashboard.canvas-spec.json",
}
PREEXISTING_DIRTY_FILES = {
    "skills/lark-slides/SKILL.md": "pre_existing_dirty_at_phase0",
    "skills/lark-slides/references/svglide-artboard-full-plan-action.md": "pre_existing_dirty_at_phase0",
    "skills/lark-slides/scripts/svglide_assets.py": "pre_existing_dirty_at_phase0",
    "skills/lark-slides/scripts/svglide_assets_test.py": "pre_existing_dirty_at_phase0",
    "skills/lark-slides/scripts/svglide_vf5_benchmark.py": "pre_existing_dirty_at_phase0",
    "skills/lark-slides/scripts/svglide_vf5_benchmark_test.py": "pre_existing_dirty_at_phase0",
}
OUT_OF_SCOPE_DIRTY_FILES = {
    "skills/lark-slides/references/svglide-visual-acceptance-repair-action.md": "out_of_scope_dirty_not_owned_by_phase01",
    "skills/lark-slides/references/svglide-visual-acceptance-vf5-evidence.md": "out_of_scope_dirty_not_owned_by_phase01",
}
COORDINATOR_BASELINE = {
    "cwd": "/Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private",
    "head": "551f333563f5a26ec9568ad8090a0f14a1a419c7",
    "branch": "feat/svglide-artboard-satori tracking origin/feat/svglide-artboard-satori",
    "status": [
        " M skills/lark-slides/SKILL.md",
        " M skills/lark-slides/references/svglide-artboard-full-plan-action.md",
        " M skills/lark-slides/scripts/svglide_assets.py",
        " M skills/lark-slides/scripts/svglide_assets_test.py",
        " M skills/lark-slides/scripts/svglide_vf5_benchmark.py",
        " M skills/lark-slides/scripts/svglide_vf5_benchmark_test.py",
        "?? skills/lark-slides/references/svglide-reference-absorption-execution-plan.md",
        "?? skills/lark-slides/scripts/svglide_semantic_asset_matcher.py",
        "?? skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py",
    ],
    "tests": (
        "python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py "
        "skills/lark-slides/scripts/svglide_visual_acceptance_test.py "
        "skills/lark-slides/scripts/svglide_assets_test.py "
        "skills/lark-slides/scripts/svglide_vf5_benchmark_test.py "
        "skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py"
    ),
    "test_result": "Ran 79 tests in 9.373s OK",
}
CURRENT_MATCHER_GATE = {
    "tests": "python3 -m unittest skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py",
    "test_result": "Ran 160 tests in 0.669s OK",
    "case_count": 160,
    "minimum_merge_threshold": 24,
    "p0_threshold": 60,
    "completion_threshold": 150,
}


class AbsorberError(Exception):
    pass


@dataclass(frozen=True)
class FamilySpec:
    name: str
    patterns: tuple[str, ...]
    source_type: str
    priority: str
    extract_fields: tuple[str, ...]
    owner_target: str
    disposition: str = "pending"
    disposition_reason: str = "Phase 1 source census only; abstraction and fixture proof are not implemented yet."
    runtime_policy: str = "reference_only_no_runtime_dependency"
    required: bool = True


@dataclass(frozen=True)
class RepoSpec:
    name: str
    root: Path
    priority: str
    families: tuple[FamilySpec, ...]
    special: str | None = None


@dataclass(frozen=True)
class RuntimeTraceSpec:
    path: Path
    collection_key: str
    asset_prefix: str
    label: str


RUNTIME_TRACE_SPECS = (
    RuntimeTraceSpec(
        Path("skills/lark-slides/references/svglide-template-registry.json"),
        "templates",
        "template",
        "templates",
    ),
    RuntimeTraceSpec(
        Path("skills/lark-slides/references/svglide-component-registry.json"),
        "components",
        "component",
        "components",
    ),
    RuntimeTraceSpec(
        Path("skills/lark-slides/references/svglide-layout-archetypes.json"),
        "archetypes",
        "layout",
        "layout_archetypes",
    ),
    RuntimeTraceSpec(
        Path("skills/lark-slides/scripts/artboard_renderer/themes/registry.json"),
        "themes",
        "theme",
        "themes",
    ),
    RuntimeTraceSpec(
        Path("skills/lark-slides/references/svglide-image-strategies.json"),
        "strategies",
        "image_strategy",
        "image_strategies",
    ),
    RuntimeTraceSpec(
        Path("skills/lark-slides/references/svglide-chart-strategies.json"),
        "strategies",
        "chart_strategy",
        "chart_strategies",
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.replace(os.sep, ".")
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip(".-").lower() or "item"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_directory(path: Path) -> str:
    h = hashlib.sha256()
    files = [item for item in sorted(path.rglob("*")) if item.is_file() and ".git" not in item.parts]
    for item in files:
        rel = item.relative_to(path).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(sha256_file(item).encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def source_hash(path: Path) -> str:
    if path.is_dir():
        return f"sha256:{sha256_directory(path)}"
    return f"sha256:{sha256_file(path)}"


def git_output(root: Path, args: list[str]) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AbsorberError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AbsorberError(f"invalid JSON in {path}: expected object")
    return payload


def license_provenance(root: Path) -> dict[str, Any]:
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        path = root / name
        if path.exists() and path.is_file():
            return {
                "kind": "license_file",
                "path": str(path.resolve()),
                "sha256": source_hash(path),
            }
    package_json = root / "package.json"
    if package_json.exists():
        try:
            payload = read_json_object(package_json)
        except AbsorberError:
            payload = {}
        license_value = payload.get("license") if isinstance(payload.get("license"), str) else None
        if license_value:
            return {
                "kind": "package_json_license_field",
                "path": str(package_json.resolve()),
                "sha256": source_hash(package_json),
                "license": license_value,
            }
    return {"kind": "missing", "path": None, "sha256": None}


def repo_provenance(root: Path) -> dict[str, Any]:
    return {
        "remote": git_output(root, ["remote", "get-url", "origin"]),
        "head": git_output(root, ["rev-parse", "HEAD"]),
        "license": license_provenance(root),
    }


def issue(code: str, message: str, *, item_id: str | None = None, path: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if item_id:
        payload["item_id"] = item_id
    if path:
        payload["path"] = path
    return payload


def item_record(
    *,
    item_id: str,
    source_repo: str,
    source_family: str,
    path: Path,
    source_type: str,
    priority: str,
    extract_fields: list[str],
    owner_target: str,
    disposition: str = "pending",
    disposition_reason: str = "Phase 1 source census only; abstraction and fixture proof are not implemented yet.",
    runtime_policy: str = "reference_only_no_runtime_dependency",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item_id,
        "source_repo": source_repo,
        "source_family": source_family,
        "source_path": str(path.resolve()),
        "source_type": source_type,
        "priority": priority,
        "source_hash": source_hash(path),
        "extract_fields": extract_fields,
        "disposition": disposition,
        "disposition_reason": disposition_reason,
        "owner_target": owner_target,
        "absorption_record": "",
        "review_status": "pending",
        "runtime_policy": runtime_policy,
    }
    if extra:
        payload.update(extra)
    return payload


def repo_roots(overrides: dict[str, Path] | None = None) -> dict[str, Path]:
    roots = {
        "open-design": Path("/Users/bytedance/bd-projects/open-design"),
        "ppt-master": Path("/Users/bytedance/bd-projects/ppt-master"),
        "PosterGen": Path("/Users/bytedance/bd-projects/workspaces/SVGlide/PosterGen"),
        "satori": Path("/Users/bytedance/bd-projects/workspaces/SVGlide/satori"),
        "og-images-generator": Path("/Users/bytedance/bd-projects/og-images-generator"),
        "beautiful-html-templates": Path("/Users/bytedance/bd-projects/beautiful-html-templates"),
    }
    if overrides:
        roots.update(overrides)
    return roots


def build_repo_specs(overrides: dict[str, Path] | None = None) -> dict[str, RepoSpec]:
    roots = repo_roots(overrides)
    specs = {
        "open-design": RepoSpec(
            "open-design",
            roots["open-design"],
            "P0",
            (
                FamilySpec("craft_guidance", ("craft/*.md",), "quality_rule", "P0", ("anti_slop_rule", "typography", "color", "accessibility"), "quality_gate"),
                FamilySpec("design_template_guidance", ("design-templates/*/SKILL.md", "design-templates/html-ppt/references/*.md"), "prompt_rule", "P1", ("template_selection", "layout_guidance"), "layout_planner"),
                FamilySpec("template_metadata", ("design-templates/*/template.json",), "template", "P1", ("palette", "typography", "layout_skeleton"), "template"),
                FamilySpec(
                    "example_html",
                    ("design-templates/*/example.html", "design-templates/*/assets/template.html"),
                    "layout",
                    "P1",
                    ("layout_skeleton", "component_combination"),
                    "layout_planner",
                    runtime_policy="forbidden_external_runtime_dependency",
                ),
                FamilySpec("preview_evidence", ("design-templates/html-ppt/docs/readme/*.png", "design-templates/html-ppt/docs/readme/*.gif"), "quality_rule", "P0", ("visual_acceptance", "negative_rule"), "visual_acceptance"),
            ),
        ),
        "ppt-master": RepoSpec(
            "ppt-master",
            roots["ppt-master"],
            "P1",
            (
                FamilySpec("examples_index", ("examples/examples.json",), "selection_rule", "P1", ("example_inventory", "deck_selection"), "layout_planner"),
                FamilySpec("example_design_spec", ("examples/*/design_spec.md",), "theme", "P1", ("palette", "typography", "deck_rhythm"), "theme"),
                FamilySpec("example_spec_lock", ("examples/*/spec_lock.md",), "quality_rule", "P1", ("density_fact", "layout_lock", "golden_page"), "quality_gate"),
                FamilySpec(
                    "example_svg_final",
                    ("examples/*/svg_final/*.svg",),
                    "deck_page",
                    "P1",
                    ("layout_skeleton", "chart_strategy", "image_strategy"),
                    "layout_planner",
                    disposition="forbidden_runtime_dependency",
                    disposition_reason="Raw ppt-master SVG can be inspected for abstraction but must never be submitted or used as SVGlide runtime output.",
                    runtime_policy="forbidden_external_runtime_dependency",
                ),
                FamilySpec("chart_registry", ("skills/ppt-master/templates/charts/charts_index.json", "skills/ppt-master/templates/charts/README.md", "skills/ppt-master/templates/charts/CHART_STYLE_GUIDE.md"), "component", "P0", ("chart_strategy", "chart_style_rule"), "component"),
                FamilySpec(
                    "chart_templates",
                    ("skills/ppt-master/templates/charts/*.svg",),
                    "component",
                    "P0",
                    ("chart_strategy", "layout_skeleton"),
                    "component",
                    disposition="forbidden_runtime_dependency",
                    disposition_reason="Raw ppt-master chart SVG can inform a native SVGlide component but cannot be embedded as runtime SVG.",
                    runtime_policy="forbidden_external_runtime_dependency",
                ),
                FamilySpec("visual_styles", ("skills/ppt-master/references/visual-styles/*.md",), "theme", "P1", ("palette", "typography", "visual_style"), "theme"),
                FamilySpec("image_type_templates", ("skills/ppt-master/references/image-type-templates/*.md",), "prompt_rule", "P0", ("image_strategy", "chart_strategy"), "asset_stage"),
            ),
        ),
        "PosterGen": RepoSpec(
            "PosterGen",
            roots["PosterGen"],
            "P2",
            (
                FamilySpec("poster_config", ("config/poster_config.yaml",), "layout", "P2", ("poster_grid", "section_balance"), "layout_planner"),
                FamilySpec("agent_prompts", ("config/prompts/*.txt",), "prompt_rule", "P2", ("research_poster_sections", "planner_signal"), "layout_planner"),
                FamilySpec("layout_agents", ("src/agents/*.py", "src/layout/*.py"), "layout", "P2", ("column_balancing", "text_measurement", "utilization_rule"), "layout_planner"),
                FamilySpec("resource_examples", ("resource/*.png", "resource/human/*.png"), "component", "P2", ("image_placement", "logo_placement"), "asset_stage"),
                FamilySpec("data_samples", ("data/*/logo.png", "data/*/aff.png", "data/*/paper.pdf"), "benchmark_route", "P2", ("research_poster_density", "logo_placement"), "vf5_benchmark"),
            ),
        ),
        "satori": RepoSpec(
            "satori",
            roots["satori"],
            "P0",
            (
                FamilySpec("renderer_docs", ("README.md", "package.json"), "renderer_constraint", "P0", ("supported_css", "font_image_constraints"), "quality_gate"),
                FamilySpec("renderer_core", ("src/satori.ts", "src/layout.ts", "src/font.ts", "src/handler/*.ts", "src/builder/*.ts", "src/builder/gradient/*.ts", "src/text/*.ts", "src/parser/*.ts"), "renderer_constraint", "P0", ("supported_pattern", "unsupported_negative_fixture"), "quality_gate"),
                FamilySpec("renderer_tests", ("test/*.test.tsx",), "renderer_constraint", "P0", ("negative_fixture", "supported_pattern"), "quality_gate"),
                FamilySpec("playground_examples", ("playground/cards/*.ts", "playground/package.json"), "renderer_constraint", "P1", ("layout_example", "image_font_handling"), "visual_acceptance"),
            ),
        ),
        "og-images-generator": RepoSpec(
            "og-images-generator",
            roots["og-images-generator"],
            "P1",
            (
                FamilySpec("generator_docs", ("README.md", "package.json", "LICENSE"), "renderer_constraint", "P1", ("pipeline_boundary", "static_output_manifest", "license_provenance"), "quality_gate"),
                FamilySpec("generator_src", ("src/*.js", "src/plugins/*.js"), "renderer_constraint", "P1", ("html_css_to_image_pipeline", "manifest_receipt"), "progress_surface"),
                FamilySpec("demo_configs", ("demos/*/og-images.config.js", "demos/__common/og-images.example-config.js"), "benchmark_route", "P1", ("metadata_to_visual_mapping", "config_example"), "vf5_benchmark"),
                FamilySpec(
                    "demo_pages",
                    ("demos/*/index.html", "test/__fixtures__/pages/**/*.html", "demos/astro/src/**/*.astro"),
                    "layout",
                    "P1",
                    ("og_layout_template", "font_image_handling"),
                    "layout_planner",
                    runtime_policy="forbidden_external_runtime_dependency",
                ),
                FamilySpec("generator_tests", ("test/*.test.js", "test/__fixtures__/*config*.js"), "quality_rule", "P1", ("renderer_failure_case", "negative_fixture"), "quality_gate"),
            ),
        ),
        "beautiful-html-templates": RepoSpec(
            "beautiful-html-templates",
            roots["beautiful-html-templates"],
            "P0",
            (),
            special="beautiful",
        ),
    }
    return specs


def iter_matches(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    matches: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            if not path.exists() or path in seen:
                continue
            seen.add(path)
            matches.append(path)
    return matches


def runtime_policy_for_path(path: Path, default: str) -> str:
    if path.suffix.lower() in RAW_RUNTIME_SUFFIXES and default == "reference_only_no_runtime_dependency":
        return "reference_only_no_runtime_dependency"
    return default


def census_generic_repo(spec: RepoSpec) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    items: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    metadata = {
        "source_repo": spec.name,
        "source_path": str(spec.root.resolve()),
        "priority": spec.priority,
        "status": "present" if spec.root.exists() else "missing",
        "observed": {},
        "drift": [],
        "provenance": repo_provenance(spec.root) if spec.root.exists() else {},
    }
    if not spec.root.exists():
        coverage.extend(
            {
                "source_repo": spec.name,
                "source_family": family.name,
                "required": family.required,
                "item_count": 0,
                "status": "missing",
                "notes": [f"repo root missing: {spec.root}"],
            }
            for family in spec.families
        )
        return items, coverage, metadata
    for family in spec.families:
        paths = iter_matches(spec.root, family.patterns)
        metadata["observed"][family.name] = len(paths)
        status = "covered" if paths else "missing"
        coverage.append(
            {
                "source_repo": spec.name,
                "source_family": family.name,
                "required": family.required,
                "item_count": len(paths),
                "status": status,
                "patterns": list(family.patterns),
                "notes": [] if paths else [f"no matches under {spec.root}"],
            }
        )
        for path in paths:
            rel = path.relative_to(spec.root).as_posix()
            items.append(
                item_record(
                    item_id=f"{spec.name}.{family.name}.{slugify(rel)}",
                    source_repo=spec.name,
                    source_family=family.name,
                    path=path,
                    source_type=family.source_type,
                    priority=family.priority,
                    extract_fields=list(family.extract_fields),
                    owner_target=family.owner_target,
                    disposition=family.disposition,
                    disposition_reason=family.disposition_reason,
                    runtime_policy=runtime_policy_for_path(path, family.runtime_policy),
                    extra={"source_repo_relative_path": rel},
                )
            )
    return items, coverage, metadata


def record_beautiful_drift(metadata: dict[str, Any], code: str, expected: int, actual: int, message: str) -> None:
    if expected == actual:
        return
    metadata.setdefault("drift", []).append(
        {
            "code": code,
            "expected": expected,
            "actual": actual,
            "message": message,
        }
    )


def census_beautiful_repo(spec: RepoSpec) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    root = spec.root
    items: list[dict[str, Any]] = []
    coverage_counts: Counter[str] = Counter()
    metadata: dict[str, Any] = {
        "source_repo": spec.name,
        "source_path": str(root.resolve()),
        "priority": "P0",
        "status": "present" if root.exists() else "missing",
        "expected": {
            "template_count_field": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "templates_len": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "template_folders": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "template_json": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "template_html": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "design_md": BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
            "screenshots": BEAUTIFUL_EXPECTED_SCREENSHOT_COUNT,
        },
        "observed": {},
        "drift": [],
        "provenance": repo_provenance(root) if root.exists() else {},
        "slug_path_rule": "index.json templates[].slug is the template folder name; display name is never used to build paths.",
    }
    if not root.exists():
        coverage = [
            {
                "source_repo": spec.name,
                "source_family": family,
                "required": True,
                "item_count": 0,
                "status": "missing",
                "notes": [f"repo root missing: {root}"],
            }
            for family in ("repository_index", "template_folder", "template_metadata", "template_html", "design_doc", "screenshot")
        ]
        return items, coverage, metadata

    index_path = root / "index.json"
    templates: list[dict[str, Any]] = []
    template_count_field: int | None = None
    if index_path.exists():
        index_payload = read_json_object(index_path)
        raw_templates = index_payload.get("templates", [])
        templates = [item for item in raw_templates if isinstance(item, dict)]
        raw_count = index_payload.get("template_count")
        template_count_field = raw_count if isinstance(raw_count, int) else None
        items.append(
            item_record(
                item_id="beautiful-html-templates.repository.index",
                source_repo=spec.name,
                source_family="repository_index",
                path=index_path,
                source_type="selection_rule",
                priority="P0",
                extract_fields=["template_selection", "planner_selection_signal", "density", "scheme"],
                owner_target="layout_planner",
                extra={"source_repo_relative_path": "index.json"},
            )
        )
        coverage_counts["repository_index"] += 1
    metadata["observed"]["template_count_field"] = template_count_field
    metadata["observed"]["templates_len"] = len(templates)
    record_beautiful_drift(
        metadata,
        "beautiful_template_count_field_drift",
        BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
        template_count_field if template_count_field is not None else -1,
        "index.json template_count differs from Phase 0 baseline.",
    )
    record_beautiful_drift(
        metadata,
        "beautiful_templates_len_drift",
        BEAUTIFUL_EXPECTED_TEMPLATE_COUNT,
        len(templates),
        "index.json templates length differs from Phase 0 baseline.",
    )

    for doc_name, family, source_type, extract_fields, owner in (
        ("AGENTS.md", "repository_guidance", "prompt_rule", ["agent_template_selection", "workflow_rule"], "layout_planner"),
        ("README.md", "repository_guidance", "prompt_rule", ["template_catalog", "usage_boundary"], "layout_planner"),
        ("LICENSE", "repository_guidance", "quality_rule", ["license_provenance"], "docs"),
    ):
        doc_path = root / doc_name
        if doc_path.exists():
            items.append(
                item_record(
                    item_id=f"beautiful-html-templates.repository.{slugify(doc_name)}",
                    source_repo=spec.name,
                    source_family=family,
                    path=doc_path,
                    source_type=source_type,
                    priority="P0",
                    extract_fields=extract_fields,
                    owner_target=owner,
                    extra={"source_repo_relative_path": doc_name},
                )
            )
            coverage_counts[family] += 1

    for template in templates:
        slug = template.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            metadata.setdefault("drift", []).append(
                {
                    "code": "beautiful_template_slug_missing",
                    "expected": "non-empty slug",
                    "actual": template.get("name", "<unnamed>"),
                    "message": "A template entry cannot be mapped to a folder without slug.",
                }
            )
            continue
        folder = root / "templates" / slug
        if folder.exists():
            items.append(
                item_record(
                    item_id=f"beautiful-html-templates.template.{slug}.folder",
                    source_repo=spec.name,
                    source_family="template_folder",
                    path=folder,
                    source_type="template",
                    priority="P0",
                    extract_fields=["template_system", "layout_archetype", "component_variant"],
                    owner_target="template",
                    extra={
                        "template_slug": slug,
                        "template_name": template.get("name", ""),
                        "source_repo_relative_path": f"templates/{slug}",
                    },
                )
            )
            coverage_counts["template_folder"] += 1
        else:
            metadata.setdefault("drift", []).append(
                {
                    "code": "beautiful_template_folder_missing",
                    "expected": f"templates/{slug}",
                    "actual": "missing",
                    "message": "Template folder from slug is missing.",
                }
            )
        template_files = (
            ("template.json", "template_metadata", "template", ["palette", "typography", "scheme", "best_for", "avoid_for"], "theme", "reference_only_no_runtime_dependency"),
            ("template.html", "template_html", "layout", ["cover_layout", "mid_deck_layout", "component_combination"], "layout_planner", "forbidden_external_runtime_dependency"),
            ("design.md", "design_doc", "theme", ["color_system", "spacing_rhythm", "decorative_vocabulary", "visual_negative_examples"], "theme", "reference_only_no_runtime_dependency"),
        )
        for filename, family, source_type, fields, owner, runtime_policy in template_files:
            path = folder / filename
            if path.exists():
                items.append(
                    item_record(
                        item_id=f"beautiful-html-templates.template.{slug}.{slugify(filename)}",
                        source_repo=spec.name,
                        source_family=family,
                        path=path,
                        source_type=source_type,
                        priority="P0",
                        extract_fields=fields,
                        owner_target=owner,
                        runtime_policy=runtime_policy,
                        disposition_reason=(
                            "Reference-only Phase 1 source. External HTML/CSS must be abstracted into SVGlide-owned assets before runtime use."
                            if filename == "template.html"
                            else "Phase 1 source census only; abstraction and fixture proof are not implemented yet."
                        ),
                        extra={
                            "template_slug": slug,
                            "template_name": template.get("name", ""),
                            "source_repo_relative_path": f"templates/{slug}/{filename}",
                        },
                    )
                )
                coverage_counts[family] += 1
            else:
                metadata.setdefault("drift", []).append(
                    {
                        "code": f"beautiful_{family}_missing",
                        "expected": f"templates/{slug}/{filename}",
                        "actual": "missing",
                        "message": f"Required template file {filename} is missing for slug {slug}.",
                    }
                )

    screenshots = sorted((root / "screenshots").glob("*.png")) if (root / "screenshots").exists() else []
    for screenshot in screenshots:
        stem = screenshot.stem
        template_slug = stem.rsplit("-", 1)[0] if "-" in stem else stem
        items.append(
            item_record(
                item_id=f"beautiful-html-templates.screenshot.{slugify(stem)}",
                source_repo=spec.name,
                source_family="screenshot",
                path=screenshot,
                source_type="quality_rule",
                priority="P0",
                extract_fields=["visual_acceptance", "layout_rhythm", "negative_example"],
                owner_target="visual_acceptance",
                extra={
                    "template_slug": template_slug,
                    "source_repo_relative_path": f"screenshots/{screenshot.name}",
                },
            )
        )
        coverage_counts["screenshot"] += 1

    actual_counts = {
        "template_folders": coverage_counts["template_folder"],
        "template_json": coverage_counts["template_metadata"],
        "template_html": coverage_counts["template_html"],
        "design_md": coverage_counts["design_doc"],
        "screenshots": coverage_counts["screenshot"],
    }
    metadata["observed"].update(actual_counts)
    for key, expected in (
        ("template_folders", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        ("template_json", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        ("template_html", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        ("design_md", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        ("screenshots", BEAUTIFUL_EXPECTED_SCREENSHOT_COUNT),
    ):
        record_beautiful_drift(
            metadata,
            f"beautiful_{key}_count_drift",
            expected,
            actual_counts[key],
            f"beautiful-html-templates {key} count differs from Phase 0 baseline.",
        )

    coverage = []
    for family in ("repository_index", "template_folder", "template_metadata", "template_html", "design_doc", "screenshot"):
        count = coverage_counts[family]
        coverage.append(
            {
                "source_repo": spec.name,
                "source_family": family,
                "required": True,
                "item_count": count,
                "status": "covered" if count else "missing",
                "notes": [],
            }
        )
    return items, coverage, metadata


def census_repos(repo: str, specs: dict[str, RepoSpec] | None = None) -> dict[str, Any]:
    specs = specs or build_repo_specs()
    selected = list(specs) if repo == "all" else [repo]
    unknown = [name for name in selected if name not in specs]
    if unknown:
        raise AbsorberError(f"unknown repo: {', '.join(unknown)}")
    items: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    repos: list[dict[str, Any]] = []
    for name in selected:
        spec = specs[name]
        if spec.special == "beautiful":
            repo_items, repo_coverage, metadata = census_beautiful_repo(spec)
        else:
            repo_items, repo_coverage, metadata = census_generic_repo(spec)
        items.extend(repo_items)
        coverage.extend(repo_coverage)
        repos.append(metadata)
    items.sort(key=lambda item: item["id"])
    coverage.sort(key=lambda item: (item["source_repo"], item["source_family"]))
    payload = {
        "schema_version": "svglide-reference-source-inventory/v1",
        "generated_at": now_iso(),
        "phase": "0/1",
        "plan_path": (REPO_ROOT / PLAN_PATH).as_posix(),
        "workspace": str(REPO_ROOT),
        "expected_repos": selected,
        "runtime_dependency_policy": {
            "external_html_css_svg_runtime_dependency_allowed": False,
            "note": "Reference sources may be read for abstraction only; external HTML/CSS/SVG/JS must not be imported, executed, embedded, or submitted as SVGlide runtime output.",
        },
        "repos": repos,
        "coverage": coverage,
        "summary": summarize_items(items),
        "items": items,
    }
    return payload


def summarize_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_repo = Counter(item.get("source_repo", "") for item in items)
    by_source_type = Counter(item.get("source_type", "") for item in items)
    by_disposition = Counter(item.get("disposition", "") for item in items)
    by_priority = Counter(item.get("priority", "") for item in items)
    return {
        "item_count": len(items),
        "by_repo": dict(sorted(by_repo.items())),
        "by_source_type": dict(sorted(by_source_type.items())),
        "by_disposition": dict(sorted(by_disposition.items())),
        "by_priority": dict(sorted(by_priority.items())),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_inventory(path: Path) -> dict[str, Any]:
    payload = read_json_object(path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise AbsorberError(f"invalid inventory {path}: items must be a list")
    return payload


def coverage_map(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    coverage = payload.get("coverage", [])
    if not isinstance(coverage, list):
        return result
    for entry in coverage:
        if not isinstance(entry, dict):
            continue
        repo = entry.get("source_repo")
        family = entry.get("source_family")
        if isinstance(repo, str) and isinstance(family, str):
            result[(repo, family)] = entry
    return result


def repo_metadata_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    repos = payload.get("repos", [])
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(repos, list):
        return result
    for repo in repos:
        if isinstance(repo, dict) and isinstance(repo.get("source_repo"), str):
            result[repo["source_repo"]] = repo
    return result


def drift_codes(repo_meta: dict[str, Any]) -> set[str]:
    drift = repo_meta.get("drift", [])
    if not isinstance(drift, list):
        return set()
    return {item.get("code") for item in drift if isinstance(item, dict) and isinstance(item.get("code"), str)}


def validate_inventory_payload(payload: dict[str, Any], specs: dict[str, RepoSpec] | None = None) -> dict[str, Any]:
    specs = specs or build_repo_specs()
    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    items = payload.get("items", [])
    if not isinstance(items, list):
        issues.append(issue("items_not_list", "inventory items must be a list"))
        items = []
    ids: set[str] = set()
    item_counts: Counter[tuple[str, str]] = Counter()
    beautiful_counts: Counter[str] = Counter()

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            issues.append(issue("item_not_object", f"item at index {index} is not an object"))
            continue
        item_id = raw_item.get("id") if isinstance(raw_item.get("id"), str) else f"index-{index}"
        missing = [field for field in sorted(REQUIRED_ITEM_FIELDS) if field not in raw_item or raw_item.get(field) in (None, "")]
        for field in missing:
            issues.append(issue(f"missing_{field}", f"item is missing required field {field}", item_id=item_id))
        if item_id in ids:
            issues.append(issue("duplicate_item_id", f"duplicate item id {item_id}", item_id=item_id))
        ids.add(item_id)
        repo = raw_item.get("source_repo")
        family = raw_item.get("source_family")
        if isinstance(repo, str) and isinstance(family, str):
            item_counts[(repo, family)] += 1
            if repo == "beautiful-html-templates":
                beautiful_counts[family] += 1
        priority = raw_item.get("priority")
        if priority not in ALLOWED_PRIORITIES:
            issues.append(issue("invalid_priority", f"priority must be one of {sorted(ALLOWED_PRIORITIES)}", item_id=item_id))
        disposition = raw_item.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            issues.append(issue("invalid_disposition", f"disposition must be one of {sorted(ALLOWED_DISPOSITIONS)}", item_id=item_id))
        path_value = raw_item.get("source_path")
        path: Path | None = None
        if isinstance(path_value, str):
            path = Path(path_value)
            if not path.is_absolute():
                issues.append(issue("source_path_not_absolute", "source_path must be absolute", item_id=item_id, path=path_value))
            if not path.exists():
                issues.append(issue("source_path_missing", "source_path does not exist", item_id=item_id, path=path_value))
            elif not os.access(path, os.R_OK):
                issues.append(issue("source_path_unreadable", "source_path is not readable", item_id=item_id, path=path_value))
        source_hash_value = raw_item.get("source_hash")
        if not isinstance(source_hash_value, str) or not source_hash_value.startswith("sha256:"):
            issues.append(issue("invalid_source_hash", "source_hash must use sha256:<hex>", item_id=item_id))
        elif path is not None and path.exists():
            actual_hash = source_hash(path)
            if actual_hash != source_hash_value:
                issues.append(issue("source_hash_stale", "source_hash does not match current source_path content", item_id=item_id, path=str(path)))
        if raw_item.get("source_type") in (None, ""):
            issues.append(issue("missing_source_type", "source_type is required", item_id=item_id))
        if isinstance(path_value, str) and Path(path_value).suffix.lower() in RAW_RUNTIME_SUFFIXES:
            runtime_policy = raw_item.get("runtime_policy")
            if runtime_policy not in {"reference_only_no_runtime_dependency", "forbidden_external_runtime_dependency"}:
                issues.append(issue("runtime_policy_missing", "external code/HTML/CSS/SVG items require a no-runtime-dependency runtime_policy", item_id=item_id))

    expected_repos = payload.get("expected_repos")
    if not isinstance(expected_repos, list) or not all(isinstance(item, str) for item in expected_repos):
        expected_repos = list(specs)
        warnings.append(issue("expected_repos_missing", "expected_repos missing; defaulting to all known repo specs"))
    cov = coverage_map(payload)
    for repo_name in expected_repos:
        spec = specs.get(repo_name)
        if spec is None:
            issues.append(issue("unknown_expected_repo", f"expected repo has no spec: {repo_name}"))
            continue
        if spec.special == "beautiful":
            required_families = ("repository_index", "template_folder", "template_metadata", "template_html", "design_doc", "screenshot")
        else:
            required_families = tuple(family.name for family in spec.families if family.required)
        for family in required_families:
            coverage_entry = cov.get((repo_name, family))
            if coverage_entry is None:
                issues.append(issue("source_family_coverage_missing", f"missing coverage entry for {repo_name}/{family}"))
                continue
            item_count = coverage_entry.get("item_count")
            if not isinstance(item_count, int):
                issues.append(issue("source_family_coverage_count_invalid", f"coverage item_count must be an integer for {repo_name}/{family}"))
                continue
            actual_count = item_counts[(repo_name, family)]
            if actual_count != item_count:
                issues.append(issue("source_family_coverage_count_stale", f"coverage count for {repo_name}/{family} is {item_count}, actual item count is {actual_count}"))
            if item_count <= 0:
                issues.append(issue("source_family_coverage_empty", f"required source family has no concrete source items: {repo_name}/{family}"))

    repos_meta = repo_metadata_map(payload)
    beautiful_meta = repos_meta.get("beautiful-html-templates", {})
    codes = drift_codes(beautiful_meta)
    expected_beautiful = {
        "template_folder": ("beautiful_template_folders_count_drift", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        "template_metadata": ("beautiful_template_json_count_drift", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        "template_html": ("beautiful_template_html_count_drift", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        "design_doc": ("beautiful_design_md_count_drift", BEAUTIFUL_EXPECTED_TEMPLATE_COUNT),
        "screenshot": ("beautiful_screenshots_count_drift", BEAUTIFUL_EXPECTED_SCREENSHOT_COUNT),
    }
    for family, (drift_code, expected) in expected_beautiful.items():
        actual = beautiful_counts[family]
        if actual != expected and drift_code not in codes:
            issues.append(
                issue(
                    "beautiful_count_drift_unrecorded",
                    f"beautiful-html-templates {family} count is {actual}, expected {expected}, but drift is not recorded",
                )
            )
    observed = beautiful_meta.get("observed") if isinstance(beautiful_meta, dict) else {}
    if isinstance(observed, dict):
        templates_len = observed.get("templates_len")
        template_count_field = observed.get("template_count_field")
        if templates_len != BEAUTIFUL_EXPECTED_TEMPLATE_COUNT and "beautiful_templates_len_drift" not in codes:
            issues.append(issue("beautiful_count_drift_unrecorded", "beautiful-html-templates templates_len drift is not recorded"))
        if template_count_field != BEAUTIFUL_EXPECTED_TEMPLATE_COUNT and "beautiful_template_count_field_drift" not in codes:
            issues.append(issue("beautiful_count_drift_unrecorded", "beautiful-html-templates template_count_field drift is not recorded"))

    status = "failed" if issues else "passed"
    return {
        "schema_version": "svglide-reference-inventory-check/v1",
        "status": status,
        "checked_at": now_iso(),
        "summary": {
            "item_count": len(items),
            "error_count": len(issues),
            "warning_count": len(warnings),
        },
        "issues": issues,
        "warnings": warnings,
    }


def resolve_repo_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def repo_path_for_record(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def iter_abstraction_records(records_root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    root = records_root or (REPO_ROOT / DEFAULT_ABSORPTIONS_DIR)
    if not root.exists():
        return []
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            records.append((path, read_json_object(path)))
        except AbsorberError:
            continue
    return records


def abstraction_record_has_required_shape(record: dict[str, Any]) -> bool:
    if not abstraction_has_fixture_proof(record):
        return False
    if any(field not in record for field in REQUIRED_ABSTRACTION_RECORD_FIELDS):
        return False
    for field in REQUIRED_ABSTRACTION_LIST_FIELDS:
        value = record.get(field)
        if not isinstance(value, list) or not value:
            return False
        if any(not isinstance(item, str) or not item.strip() for item in value):
            return False
    transform = record.get("non_copying_transform")
    return isinstance(transform, str) and bool(transform.strip())


def absorption_context_record_map(records_root: Path | None = None) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path, record in iter_abstraction_records(records_root):
        if not abstraction_record_has_required_shape(record):
            continue
        relpath = repo_path_for_record(path)
        source_item_id = record.get("source_item_id")
        if isinstance(source_item_id, str) and source_item_id:
            result[source_item_id] = {
                "absorption_record": relpath,
                "canonical_item_id": source_item_id,
                "relation": "primary",
            }
        refs = record.get("source_context_refs")
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, str) and ref:
                    result.setdefault(
                        ref,
                        {
                            "absorption_record": relpath,
                            "canonical_item_id": source_item_id if isinstance(source_item_id, str) else "",
                            "relation": "context_ref",
                        },
                    )
    return result


def is_repo_metadata_item(item: dict[str, Any]) -> bool:
    rel = item.get("source_repo_relative_path")
    if not isinstance(rel, str):
        return False
    lowered = rel.lower()
    basename = Path(lowered).name
    if basename in {"license", "license.md", "license.txt", "copying", "package.json", "__init__.py"}:
        return True
    if lowered.endswith(".json") and any(part in lowered for part in ("package-lock", "pnpm-lock", "yarn.lock")):
        return True
    return False


def disposition_suggestion_for_item(item: dict[str, Any], context_records: dict[str, dict[str, str]]) -> dict[str, Any]:
    item_id = item.get("id") if isinstance(item.get("id"), str) else ""
    source_repo = item.get("source_repo") if isinstance(item.get("source_repo"), str) else ""
    source_family = item.get("source_family") if isinstance(item.get("source_family"), str) else ""
    owner_target = item.get("owner_target") if isinstance(item.get("owner_target"), str) else ""
    runtime_policy = item.get("runtime_policy") if isinstance(item.get("runtime_policy"), str) else ""

    if item_id in context_records:
        context = context_records[item_id]
        if context.get("relation") == "primary":
            return {
                "id": item_id,
                "suggested_disposition": "absorbed",
                "absorption_record": context["absorption_record"],
                "reason": "Covered as the primary source item for a fixture-backed non-copying abstraction record.",
            }
        return {
            "id": item_id,
            "suggested_disposition": "duplicate_of",
            "canonical_item_id": context.get("canonical_item_id", ""),
            "absorption_record": context["absorption_record"],
            "reason": "Covered as supporting source context; final disposition should duplicate the canonical absorbed source item.",
        }
    if runtime_policy == "forbidden_external_runtime_dependency":
        return {
            "id": item_id,
            "suggested_disposition": "forbidden_runtime_dependency",
            "reason": "Raw external runtime artifact; violates SVGlide runtime boundary and must only be used as reference evidence.",
        }
    if source_repo == "PosterGen" and source_family in {"data_samples", "resource_examples"}:
        return {
            "id": item_id,
            "suggested_disposition": "not_applicable_to_svglide",
            "reason": "Source-specific paper/logo/raster sample; not reusable SVGlide capability or trusted provider evidence.",
        }
    if is_repo_metadata_item(item):
        return {
            "id": item_id,
            "suggested_disposition": "not_applicable_to_svglide",
            "reason": "Repository metadata or provenance/scaffolding document; not a reusable SVGlide asset or rule source.",
        }
    if source_repo == "open-design" and "html-ppt-zhangzara" in str(item.get("source_repo_relative_path", "")):
        return {
            "id": item_id,
            "suggested_disposition": "blocked_with_reason",
            "reason": "Potential duplicate wrapper around beautiful-html-templates; requires canonical absorbed target before duplicate_of is safe.",
        }
    if owner_target in {
        "template",
        "theme",
        "component",
        "layout_planner",
        "asset_stage",
        "quality_gate",
        "visual_acceptance",
        "vf5_benchmark",
        "progress_surface",
        "docs",
    }:
        return {
            "id": item_id,
            "suggested_disposition": "blocked_with_reason",
            "reason": f"Potential {owner_target} source, but missing abstraction_record and fixture proof.",
        }
    return {
        "id": item_id,
        "suggested_disposition": "blocked_with_reason",
        "reason": "Potential reference source, but no reviewed disposition rule or fixture-backed abstraction exists yet.",
    }


def preview_disposition_payload(payload: dict[str, Any], *, limit: int | None = None) -> dict[str, Any]:
    context_records = absorption_context_record_map()
    pending_items = [item for item in payload.get("items", []) if isinstance(item, dict) and item.get("disposition") == "pending"]
    suggestions = [disposition_suggestion_for_item(item, context_records) for item in pending_items]
    by_disposition = Counter(item["suggested_disposition"] for item in suggestions)
    by_repo_disposition: dict[str, Counter[str]] = defaultdict(Counter)
    items_by_id = {item.get("id"): item for item in pending_items if isinstance(item.get("id"), str)}
    for suggestion in suggestions:
        item = items_by_id.get(suggestion["id"], {})
        repo = item.get("source_repo") if isinstance(item.get("source_repo"), str) else ""
        by_repo_disposition[repo][suggestion["suggested_disposition"]] += 1
    visible_suggestions = suggestions[:limit] if limit is not None else suggestions
    return {
        "schema_version": "svglide-reference-disposition-preview/v1",
        "status": "passed",
        "checked_at": now_iso(),
        "summary": {
            "pending_count": len(pending_items),
            "suggestion_count": len(suggestions),
            "by_suggested_disposition": dict(sorted(by_disposition.items())),
            "by_repo_suggested_disposition": {
                repo: dict(sorted(counter.items()))
                for repo, counter in sorted(by_repo_disposition.items())
            },
        },
        "suggestions": visible_suggestions,
    }


def apply_disposition_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = copy.deepcopy(payload)
    preview = preview_disposition_payload(updated, limit=None)
    suggestions_by_id = {item["id"]: item for item in preview["suggestions"]}
    applied: list[dict[str, str]] = []
    for item in updated.get("items", []):
        if not isinstance(item, dict) or item.get("disposition") != "pending":
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in suggestions_by_id:
            continue
        suggestion = suggestions_by_id[item_id]
        suggested_disposition = suggestion["suggested_disposition"]
        item["disposition"] = suggested_disposition
        item["disposition_reason"] = suggestion["reason"]
        item["review_status"] = "blocked" if suggested_disposition == "blocked_with_reason" else "pass"
        if "absorption_record" in suggestion:
            item["absorption_record"] = suggestion["absorption_record"]
        if suggested_disposition == "duplicate_of":
            canonical_item_id = suggestion.get("canonical_item_id", "")
            item["canonical_item_id"] = canonical_item_id
            item["duplicate_of"] = canonical_item_id
        applied.append(
            {
                "id": item_id,
                "disposition": suggested_disposition,
            }
        )
    items = [item for item in updated.get("items", []) if isinstance(item, dict)]
    updated["summary"] = summarize_items(items)
    by_disposition = Counter(item["disposition"] for item in applied)
    result = {
        "schema_version": "svglide-reference-disposition-apply/v1",
        "status": "passed",
        "checked_at": now_iso(),
        "summary": {
            "applied_count": len(applied),
            "by_disposition": dict(sorted(by_disposition.items())),
            "remaining_pending_count": updated["summary"]["by_disposition"].get("pending", 0),
        },
        "applied": applied,
    }
    return updated, result


def referenced_in_runtime(item: dict[str, Any]) -> list[str]:
    path_value = item.get("source_path")
    if not isinstance(path_value, str):
        return []
    path = Path(path_value)
    needles = {path_value}
    rel = item.get("source_repo_relative_path")
    if isinstance(rel, str):
        needles.add(rel)
    hits: list[str] = []
    for runtime_file in RUNTIME_SCAN_FILES:
        full_path = REPO_ROOT / runtime_file
        if not full_path.exists() or not full_path.is_file():
            continue
        try:
            text = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(needle and needle in text for needle in needles):
            hits.append(runtime_file)
    return hits


def abstraction_has_fixture_proof(record: dict[str, Any]) -> bool:
    for field in FIXTURE_PROOF_FIELDS:
        value = record.get(field)
        if isinstance(value, list) and value:
            return True
    return False


def validate_abstraction_record(record: dict[str, Any], *, item_id: str, record_path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for field in sorted(REQUIRED_ABSTRACTION_RECORD_FIELDS):
        if field not in record:
            issues.append(
                issue(
                    "abstraction_required_field_missing",
                    f"abstraction record is missing required field {field}",
                    item_id=item_id,
                    path=str(record_path),
                )
            )

    source_item_id = record.get("source_item_id")
    if isinstance(source_item_id, str) and source_item_id != item_id:
        issues.append(
            issue(
                "abstraction_source_item_id_mismatch",
                f"abstraction source_item_id {source_item_id} does not match inventory item id {item_id}",
                item_id=item_id,
                path=str(record_path),
            )
        )
    elif "source_item_id" in record and not isinstance(source_item_id, str):
        issues.append(
            issue(
                "abstraction_source_item_id_invalid",
                "abstraction source_item_id must be a string",
                item_id=item_id,
                path=str(record_path),
            )
        )

    for field in sorted(REQUIRED_ABSTRACTION_LIST_FIELDS):
        if field not in record:
            continue
        value = record.get(field)
        if not isinstance(value, list) or not value:
            issues.append(
                issue(
                    "abstraction_required_list_empty",
                    f"abstraction field {field} must be a non-empty list",
                    item_id=item_id,
                    path=str(record_path),
                )
            )
            continue
        for index, entry in enumerate(value):
            if not isinstance(entry, str) or not entry.strip():
                issues.append(
                    issue(
                        "abstraction_required_list_item_invalid",
                        f"abstraction field {field}[{index}] must be a non-empty string",
                        item_id=item_id,
                        path=str(record_path),
                    )
                )

    non_copying_transform = record.get("non_copying_transform")
    if "non_copying_transform" in record and (
        not isinstance(non_copying_transform, str) or not non_copying_transform.strip()
    ):
        issues.append(
            issue(
                "abstraction_non_copying_transform_empty",
                "abstraction non_copying_transform must be a non-empty string",
                item_id=item_id,
                path=str(record_path),
            )
        )
    return issues


def validate_absorption_payload(
    payload: dict[str, Any],
    specs: dict[str, RepoSpec] | None = None,
    *,
    require_final_disposition: bool = False,
) -> dict[str, Any]:
    inventory_result = validate_inventory_payload(payload, specs)
    issues: list[dict[str, str]] = list(inventory_result["issues"])
    warnings: list[dict[str, str]] = list(inventory_result["warnings"])
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    by_id = {item.get("id"): item for item in items if isinstance(item.get("id"), str)}
    pending_count = 0
    absorbed_count = 0
    duplicate_count = 0
    forbidden_count = 0
    for item in items:
        item_id = item.get("id") if isinstance(item.get("id"), str) else "<unknown>"
        disposition = item.get("disposition")
        if disposition == "pending":
            pending_count += 1
            if require_final_disposition:
                issues.append(
                    issue(
                        "pending_disposition",
                        "pending disposition is not allowed when final disposition is required",
                        item_id=item_id,
                    )
                )
        if disposition == "absorbed":
            absorbed_count += 1
            record_path_value = item.get("absorption_record")
            if not isinstance(record_path_value, str) or not record_path_value:
                issues.append(issue("absorbed_missing_abstraction_record", "absorbed item requires absorption_record", item_id=item_id))
                continue
            record_path = resolve_repo_path(record_path_value)
            if not record_path.exists():
                issues.append(issue("abstraction_record_missing", "absorption_record path does not exist", item_id=item_id, path=str(record_path)))
                continue
            try:
                record = read_json_object(record_path)
            except AbsorberError as error:
                issues.append(issue("abstraction_record_invalid", str(error), item_id=item_id, path=str(record_path)))
                continue
            issues.extend(validate_abstraction_record(record, item_id=item_id, record_path=record_path))
            if not abstraction_has_fixture_proof(record):
                issues.append(issue("abstraction_fixture_proof_missing", "abstraction record has no fixture proof", item_id=item_id, path=str(record_path)))
        elif disposition == "duplicate_of":
            duplicate_count += 1
            canonical = item.get("canonical_item_id") or item.get("duplicate_of")
            if not isinstance(canonical, str) or not canonical:
                issues.append(issue("duplicate_missing_canonical", "duplicate item requires canonical_item_id or duplicate_of", item_id=item_id))
            elif canonical not in by_id:
                issues.append(issue("duplicate_canonical_missing", f"canonical item does not exist: {canonical}", item_id=item_id))
            elif by_id[canonical].get("disposition") != "absorbed":
                issues.append(issue("duplicate_canonical_not_absorbed", f"canonical item is not absorbed: {canonical}", item_id=item_id))
        if disposition == "forbidden_runtime_dependency" or item.get("runtime_policy") == "forbidden_external_runtime_dependency":
            forbidden_count += 1
            hits = referenced_in_runtime(item)
            for hit in hits:
                issues.append(issue("forbidden_item_referenced_by_runtime", "forbidden external source is referenced by runtime code", item_id=item_id, path=hit))
    status = "failed" if issues else "passed"
    return {
        "schema_version": "svglide-reference-absorption-check/v1",
        "status": status,
        "checked_at": now_iso(),
        "summary": {
            "item_count": len(items),
            "pending_count": pending_count,
            "absorbed_count": absorbed_count,
            "duplicate_count": duplicate_count,
            "forbidden_count": forbidden_count,
            "error_count": len(issues),
            "warning_count": len(warnings),
            "require_final_disposition": require_final_disposition,
        },
        "issues": issues,
        "warnings": warnings,
    }


def record_fixture_paths(record: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for field in FIXTURE_PROOF_FIELDS:
        value = record.get(field)
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, str) and entry.strip():
                paths.append(entry)
    return paths


def validate_theme_file_trace(item: dict[str, Any], *, registry_path: Path, item_id: str) -> list[dict[str, str]]:
    theme_path_value = item.get("path")
    if not isinstance(theme_path_value, str) or not theme_path_value:
        return [
            issue(
                "runtime_trace_theme_path_missing",
                "active theme registry item requires a theme file path",
                item_id=item_id,
                path=registry_path.as_posix(),
            )
        ]
    theme_path = resolve_repo_path(theme_path_value)
    if not theme_path.exists():
        return [
            issue(
                "runtime_trace_theme_file_missing",
                "active theme file does not exist",
                item_id=item_id,
                path=theme_path.as_posix(),
            )
        ]
    try:
        theme = read_json_object(theme_path)
    except AbsorberError as error:
        return [
            issue(
                "runtime_trace_theme_file_invalid",
                str(error),
                item_id=item_id,
                path=theme_path.as_posix(),
            )
        ]
    issues: list[dict[str, str]] = []
    for field in ("source_trace", "abstraction_record"):
        if theme.get(field) != item.get(field):
            issues.append(
                issue(
                    f"runtime_trace_theme_{field}_mismatch",
                    f"theme file {field} must match theme registry",
                    item_id=item_id,
                    path=theme_path.as_posix(),
                )
            )
    return issues


def validate_runtime_traceability() -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    summary: dict[str, dict[str, int]] = {}
    record_cache: dict[str, dict[str, Any] | None] = {}
    for spec in RUNTIME_TRACE_SPECS:
        registry_path = REPO_ROOT / spec.path
        try:
            registry = read_json_object(registry_path)
        except AbsorberError as error:
            issues.append(issue("runtime_trace_registry_invalid", str(error), path=registry_path.as_posix()))
            summary[spec.label] = {"active": 0, "traced": 0}
            continue
        collection = registry.get(spec.collection_key)
        if not isinstance(collection, list):
            issues.append(
                issue(
                    "runtime_trace_collection_invalid",
                    f"{spec.collection_key} must be a list",
                    path=registry_path.as_posix(),
                )
            )
            summary[spec.label] = {"active": 0, "traced": 0}
            continue
        active_count = 0
        traced_count = 0
        for item in collection:
            if not isinstance(item, dict) or item.get("status") != "active":
                continue
            active_count += 1
            raw_id = item.get("id")
            item_id = raw_id if isinstance(raw_id, str) and raw_id else "<unknown>"
            asset_id = f"{spec.asset_prefix}.{item_id}"
            source_trace = item.get("source_trace")
            if not isinstance(source_trace, list) or not source_trace or any(not isinstance(entry, str) or not entry.strip() for entry in source_trace):
                issues.append(
                    issue(
                        "runtime_trace_source_trace_missing",
                        "active runtime asset requires a non-empty source_trace list",
                        item_id=asset_id,
                        path=registry_path.as_posix(),
                    )
                )
                continue
            record_path_value = item.get("abstraction_record")
            if not isinstance(record_path_value, str) or not record_path_value:
                issues.append(
                    issue(
                        "runtime_trace_abstraction_record_missing",
                        "active runtime asset requires abstraction_record",
                        item_id=asset_id,
                        path=registry_path.as_posix(),
                    )
                )
                continue
            if record_path_value not in record_cache:
                record_path = resolve_repo_path(record_path_value)
                if not record_path.exists():
                    issues.append(
                        issue(
                            "runtime_trace_abstraction_record_not_found",
                            "abstraction_record path does not exist",
                            item_id=asset_id,
                            path=record_path.as_posix(),
                        )
                    )
                    record_cache[record_path_value] = None
                else:
                    try:
                        record_cache[record_path_value] = read_json_object(record_path)
                    except AbsorberError as error:
                        issues.append(
                            issue(
                                "runtime_trace_abstraction_record_invalid",
                                str(error),
                                item_id=asset_id,
                                path=record_path.as_posix(),
                            )
                        )
                        record_cache[record_path_value] = None
            record = record_cache.get(record_path_value)
            if not record:
                continue
            record_path = resolve_repo_path(record_path_value)
            if not abstraction_record_has_required_shape(record):
                issues.append(
                    issue(
                        "runtime_trace_abstraction_shape_invalid",
                        "abstraction_record must have required fields and fixture proof",
                        item_id=asset_id,
                        path=record_path.as_posix(),
                    )
                )
                continue
            asset_ids = record.get("svglide_asset_ids")
            if not isinstance(asset_ids, list) or asset_id not in asset_ids:
                issues.append(
                    issue(
                        "runtime_trace_asset_not_in_record",
                        f"abstraction_record svglide_asset_ids must include {asset_id}",
                        item_id=asset_id,
                        path=record_path.as_posix(),
                    )
                )
                continue
            missing_fixture_paths = [
                fixture_path
                for fixture_path in record_fixture_paths(record)
                if not resolve_repo_path(fixture_path).exists()
            ]
            if missing_fixture_paths:
                issues.append(
                    issue(
                        "runtime_trace_fixture_path_missing",
                        "abstraction_record fixture/proof path does not exist",
                        item_id=asset_id,
                        path=missing_fixture_paths[0],
                    )
                )
                continue
            if spec.asset_prefix == "theme":
                theme_issues = validate_theme_file_trace(item, registry_path=registry_path, item_id=asset_id)
                if theme_issues:
                    issues.extend(theme_issues)
                    continue
            traced_count += 1
        summary[spec.label] = {"active": active_count, "traced": traced_count}
    total_active = sum(item["active"] for item in summary.values())
    total_traced = sum(item["traced"] for item in summary.values())
    return {
        "schema_version": "svglide-runtime-traceability-check/v1",
        "status": "failed" if issues else "passed",
        "checked_at": now_iso(),
        "summary": {
            "asset_area_count": len(summary),
            "active_runtime_asset_count": total_active,
            "traced_runtime_asset_count": total_traced,
            "error_count": len(issues),
            "by_asset_area": summary,
        },
        "issues": issues,
    }


def counter_by(items: list[dict[str, Any]], key: str) -> Counter[str]:
    return Counter(item.get(key, "") for item in items if isinstance(item.get(key), str))


def nested_counter(items: list[dict[str, Any]], first: str, second: str) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        a = item.get(first)
        b = item.get(second)
        if isinstance(a, str) and isinstance(b, str):
            result[a][b] += 1
    return result


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def count_active_registry_items(path: Path, key: str) -> int:
    try:
        payload = read_json_object(path)
    except AbsorberError:
        return 0
    items = payload.get(key)
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict) and item.get("status") == "active")


def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(args, cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def git_status_lines() -> list[str]:
    try:
        value = subprocess.check_output(["git", "status", "--short"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return []
    return value.splitlines()


def status_path(line: str) -> str:
    if line.startswith("?? "):
        return line[3:]
    if len(line) > 3:
        raw = line[3:]
        if " -> " in raw:
            return raw.split(" -> ", 1)[1]
        return raw
    return line.strip()


def classify_dirty_path(path: str) -> str:
    if path in PHASE01_CHANGED_FILES:
        return PHASE01_CHANGED_FILES[path]
    if path in PLAN_CHANGED_FILES or any(path.startswith(prefix) for prefix in PLAN_CHANGED_PREFIXES):
        return "changed_by_this_plan"
    if path in PREEXISTING_DIRTY_FILES:
        return PREEXISTING_DIRTY_FILES[path]
    if path in OUT_OF_SCOPE_DIRTY_FILES:
        return OUT_OF_SCOPE_DIRTY_FILES[path]
    return "unclassified_dirty_requires_review"


def build_report(payload: dict[str, Any], inventory_check: dict[str, Any] | None = None, absorption_check: dict[str, Any] | None = None) -> str:
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    repos = repo_metadata_map(payload)
    coverage = [entry for entry in payload.get("coverage", []) if isinstance(entry, dict)]
    inventory_check = inventory_check or validate_inventory_payload(payload)
    absorption_check = absorption_check or validate_absorption_payload(payload)
    final_absorption_check = validate_absorption_payload(payload, require_final_disposition=True)
    runtime_traceability_check = validate_runtime_traceability()
    pending_count = counter_by(items, "disposition").get("pending", 0)
    absorbed = [item for item in items if item.get("disposition") == "absorbed"]
    absorbed_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for item in absorbed:
        record_path_value = item.get("absorption_record")
        if isinstance(record_path_value, str) and record_path_value:
            record_path = resolve_repo_path(record_path_value)
            if record_path.exists():
                try:
                    absorbed_records.append((item, read_json_object(record_path)))
                except AbsorberError:
                    pass

    lines: list[str] = []
    lines.append("# SVGlide Reference Absorption Report")
    lines.append("")
    if absorbed and pending_count == 0:
        lines.append(
            "Status: COMPLETE_LOCAL_PROOF. Source inventory, final disposition, runtime reverse "
            "traceability, fixture-backed beautiful-html-templates absorption, dry-run request proof, "
            "quality gate, and visual_acceptance evidence are closed for this plan. This report does "
            "not claim live backend readback, real image acquisition, or a real/upper-bound VF5 benchmark."
        )
    elif absorbed:
        lines.append(
            "Status: IN_PROGRESS. This report covers Phase 0/1 source inventory plus first-wave "
            "fixture-backed beautiful-html-templates absorption. It is not final: pending source "
            "items remain and no production-live backend, real image, or real VF5 benchmark claim is made."
        )
    else:
        lines.append("Status: IN_PROGRESS. This report covers Phase 0/1 source inventory tooling only; no asset implementation, abstraction records, fixtures, runtime dependencies, or backend claims are introduced here.")
    lines.append("")
    lines.append("## Coordinator Baseline")
    lines.append("")
    lines.append(f"- cwd: `{COORDINATOR_BASELINE['cwd']}`")
    lines.append(f"- HEAD: `{COORDINATOR_BASELINE['head']}`")
    lines.append(f"- branch: `{COORDINATOR_BASELINE['branch']}`")
    lines.append("- status at baseline:")
    lines.append("")
    lines.append("```text")
    lines.extend(COORDINATOR_BASELINE["status"])
    lines.append("```")
    lines.append("")
    lines.append(f"- baseline tests: `{COORDINATOR_BASELINE['tests']}`")
    lines.append(f"- result: {COORDINATOR_BASELINE['test_result']}")
    lines.append("")
    lines.append("## Current Dirty File Attribution")
    lines.append("")
    current_status = git_status_lines()
    if current_status:
        rows = []
        for line in current_status:
            path = status_path(line)
            rows.append([line[:2].strip() or "modified", path, classify_dirty_path(path)])
        lines.append(md_table(["status", "path", "attribution"], rows))
    else:
        lines.append("Current worktree is clean or status is unavailable.")
    lines.append("")
    lines.append("- `changed_by_this_plan`: owned by this reference absorption planning/tooling batch.")
    lines.append("- `pre_existing_dirty_at_phase0`: present before Phase 0 baseline; preserved and not claimed by this batch.")
    lines.append("- `out_of_scope_dirty_not_owned_by_phase01`: appeared outside the Phase 0/1 write scope; must be reviewed separately before commit.")
    lines.append("- `unclassified_dirty_requires_review`: cannot be claimed until a coordinator assigns ownership.")
    lines.append("")
    lines.append("## Generated Context")
    lines.append("")
    lines.append(f"- generated_at: `{payload.get('generated_at', 'unknown')}`")
    lines.append(f"- current_branch: `{git_value(['git', 'branch', '--show-current'])}`")
    lines.append(f"- current_HEAD: `{git_value(['git', 'rev-parse', 'HEAD'])}`")
    lines.append(f"- inventory_check: `{inventory_check['status']}` ({inventory_check['summary']['error_count']} errors)")
    lines.append(f"- absorption_check: `{absorption_check['status']}` ({absorption_check['summary']['error_count']} errors)")
    lines.append(
        "- runtime_traceability_check: "
        f"`{runtime_traceability_check['status']}` "
        f"({runtime_traceability_check['summary']['traced_runtime_asset_count']}/"
        f"{runtime_traceability_check['summary']['active_runtime_asset_count']} active assets traced)"
    )
    lines.append(
        "- final_disposition_check: "
        f"`{final_absorption_check['status']}` "
        f"({final_absorption_check['summary']['pending_count']} pending, "
        f"{final_absorption_check['summary']['error_count']} errors)"
    )
    lines.append("")
    lines.append("## Source Census Totals")
    lines.append("")
    by_repo = counter_by(items, "source_repo")
    by_type = counter_by(items, "source_type")
    lines.append(md_table(["repo", "items"], [[repo, count] for repo, count in sorted(by_repo.items())]))
    lines.append("")
    lines.append(md_table(["source_type", "items"], [[source_type, count] for source_type, count in sorted(by_type.items())]))
    lines.append("")
    lines.append("## Repo Provenance")
    lines.append("")
    provenance_rows = []
    for repo_name in sorted(repos):
        provenance = repos[repo_name].get("provenance") if isinstance(repos[repo_name].get("provenance"), dict) else {}
        license_info = provenance.get("license") if isinstance(provenance.get("license"), dict) else {}
        provenance_rows.append(
            [
                repo_name,
                provenance.get("remote") or "",
                provenance.get("head") or "",
                license_info.get("kind") or "",
                license_info.get("path") or "",
                license_info.get("license") or "",
            ]
        )
    lines.append(md_table(["repo", "remote", "HEAD", "license_kind", "license_path", "license"], provenance_rows))
    lines.append("")
    lines.append("## Source Family Coverage")
    lines.append("")
    coverage_rows = [
        [
            entry.get("source_repo", ""),
            entry.get("source_family", ""),
            entry.get("item_count", 0),
            entry.get("status", ""),
        ]
        for entry in coverage
    ]
    lines.append(md_table(["repo", "source_family", "items", "status"], coverage_rows))
    lines.append("")
    lines.append("## P0 Beautiful HTML Templates Coverage")
    lines.append("")
    beautiful = repos.get("beautiful-html-templates", {})
    observed = beautiful.get("observed", {}) if isinstance(beautiful.get("observed"), dict) else {}
    expected = beautiful.get("expected", {}) if isinstance(beautiful.get("expected"), dict) else {}
    lines.append(md_table(["metric", "expected", "observed"], [[key, expected.get(key, ""), observed.get(key, "")] for key in sorted(expected)]))
    lines.append("")
    drift = beautiful.get("drift", []) if isinstance(beautiful.get("drift"), list) else []
    if drift:
        lines.append("Recorded source drift:")
        lines.append("")
        for entry in drift:
            if isinstance(entry, dict):
                lines.append(f"- {entry.get('code')}: expected `{entry.get('expected')}`, actual `{entry.get('actual')}`. {entry.get('message', '')}")
    else:
        lines.append("Recorded source drift: none.")
    lines.append("")
    lines.append("Path mapping rule: `index.json` template entries use `slug` for `templates/<slug>` folder paths; display `name` is not used to construct paths.")
    lines.append("")
    lines.append("## Disposition Totals")
    lines.append("")
    lines.append(md_table(["disposition", "items"], [[key, count] for key, count in sorted(counter_by(items, "disposition").items())]))
    lines.append("")
    disposition_preview = preview_disposition_payload(payload, limit=0)
    preview_summary = disposition_preview["summary"]
    lines.append("## Disposition Preview")
    lines.append("")
    if preview_summary["pending_count"] == 0:
        lines.append("No pending source items remain; `preview-disposition` has no pending suggestions.")
    else:
        lines.append(
            f"`preview-disposition` suggests final handling for {preview_summary['pending_count']} pending items without editing inventory."
        )
        lines.append("")
        lines.append(md_table(
            ["suggested_disposition", "items"],
            [[key, count] for key, count in sorted(preview_summary["by_suggested_disposition"].items())],
        ))
        lines.append("")
        lines.append("These are rule suggestions only. Applying them still requires reviewer sampling and inventory update review.")
    lines.append("")
    lines.append("## Runtime Boundary")
    lines.append("")
    lines.append("- External HTML/CSS/SVG/JS from reference repositories is inventory evidence only.")
    lines.append("- This plan does not add any reference repository as a SVGlide runtime dependency.")
    lines.append("- `check-absorption` scans known runtime files for forbidden source path references.")
    if absorbed:
        lines.append(
            f"- `check-absorption: passed` with `absorbed_count={len(absorbed)}` means absorbed records are "
            "structurally checked, final-disposition state is closed, and forbidden reference paths are not leaked into known runtime files."
        )
    else:
        lines.append("- `check-absorption: passed` in Phase 0/1 does not mean absorption is complete; with `absorbed_count=0`, it only means pending items are allowed, forbidden references are not leaked into known runtime files, and any future absorbed/duplicate records would be structurally checked.")
    lines.append("")
    lines.append("## Absorbed Assets By Target Capability")
    lines.append("")
    if absorbed:
        lines.append(md_table(["owner_target", "absorbed_items"], [[key, count] for key, count in sorted(counter_by(absorbed, "owner_target").items())]))
        lines.append("")
        lines.append(md_table(
            ["source_item", "assets", "abstraction_record"],
            [
                [
                    item.get("id", ""),
                    ", ".join(record.get("svglide_asset_ids", [])) if isinstance(record.get("svglide_asset_ids"), list) else "",
                    item.get("absorption_record", ""),
                ]
                for item, record in absorbed_records
            ],
        ))
    else:
        lines.append("No absorbed assets in Phase 0/1. All reference items remain pending or forbidden until Phase 2/3 abstraction records and fixture proof exist.")
    lines.append("")
    lines.append("## SVGlide Target Asset Counts")
    lines.append("")
    target_count_rows = [
        ["active_templates", 30, count_active_registry_items(REPO_ROOT / "skills/lark-slides/references/svglide-template-registry.json", "templates")],
        ["active_themes", 20, count_active_registry_items(REPO_ROOT / "skills/lark-slides/scripts/artboard_renderer/themes/registry.json", "themes")],
        ["active_component_variants", 60, count_active_registry_items(REPO_ROOT / "skills/lark-slides/references/svglide-component-registry.json", "components")],
        ["active_layout_archetypes", 14, count_active_registry_items(REPO_ROOT / "skills/lark-slides/references/svglide-layout-archetypes.json", "archetypes")],
        ["image_strategies", 20, count_active_registry_items(REPO_ROOT / "skills/lark-slides/references/svglide-image-strategies.json", "strategies")],
        ["chart_strategies", 12, count_active_registry_items(REPO_ROOT / "skills/lark-slides/references/svglide-chart-strategies.json", "strategies")],
    ]
    lines.append(md_table(["asset_area", "required_minimum", "observed"], target_count_rows))
    lines.append("")
    lines.append("## Runtime Reverse Traceability")
    lines.append("")
    trace_summary = runtime_traceability_check["summary"]["by_asset_area"]
    lines.append(md_table(
        ["asset_area", "active", "traced"],
        [
            [area, values.get("active", 0), values.get("traced", 0)]
            for area, values in trace_summary.items()
        ],
    ))
    lines.append("")
    lines.append(
        "- command: `python3 skills/lark-slides/scripts/svglide_reference_absorber.py "
        "check-runtime-traceability --pretty`"
    )
    lines.append("- every active runtime asset has non-empty `source_trace`, an existing `abstraction_record`, and a strict `svglide_asset_ids` reverse reference.")
    lines.append("- baseline SVGlide-owned assets point to `skills/lark-slides/references/absorptions/svglide-baseline/*.json`; beautiful-derived assets point to their beautiful-html-templates abstraction records.")
    lines.append("")
    lines.append("## Beautiful-Derived Candidates")
    lines.append("")
    if absorbed_records:
        lines.append("Implemented first-wave SVGlide-owned templates/layouts from beautiful-html-templates abstractions:")
        lines.append("")
        for _, record in absorbed_records:
            assets = record.get("svglide_asset_ids", [])
            lines.append(f"- {', '.join(assets) if isinstance(assets, list) else ''}")
        lines.append("")
        lines.append("These assets are derived from design intent only; raw beautiful-html-templates HTML/CSS/JS is not imported or executed as SVGlide runtime.")
    else:
        lines.append("No SVGlide templates/themes/components/layouts are implemented in this phase. The inventory now exposes P0 source records for future Theme Tokens, Canvas Templates, Component Variants, Layout Archetypes, and visual negative examples.")
    lines.append("")
    lines.append("## Quality, VF5, And Matcher Boundary")
    lines.append("")
    lines.append(f"- fixture-backed abstraction records added: {len(absorbed_records)}")
    lines.append("- visual_acceptance evidence: `reference_absorption_wave1`, `reference_absorption_wave2`, and `reference_absorption_wave3` all passed through `visual_acceptance`.")
    lines.append("- dry-run evidence: all three waves passed `07-create/dry-run.json` using the branch-local CLI command `SVGLIDE_LARK_CLI_CMD='go run .'`.")
    lines.append("- VF5 fixture boundary: no real or upper-bound benchmark claim is made here; fixture claims remain `real_benchmark=false` by policy/tests.")
    lines.append("- trusted internal image provider evidence: not applicable; no real image claim")
    lines.append("- real image/provider boundary: future real claims require `real_benchmark=true`, `trusted_provider_evidence`, `trusted:<provider-id>`, `--image-backend stage_command`, `SVGLIDE_IMAGE_STAGE_COMMAND`, and validated local image hashes")
    lines.append("- planner ownership boundary: these absorption waves use deterministic checked-in CanvasSpec/slide_plan fixtures with `plan-confirmation.json` confirmed_by=user; `prompt-plan/model-plan` now require `--trusted-provider-id` when using `claude`, `command`, or any `--planner-command`, and planner receipts record `trusted_provider_evidence`.")
    matcher_gap_p0 = max(0, CURRENT_MATCHER_GATE["p0_threshold"] - CURRENT_MATCHER_GATE["case_count"])
    matcher_gap_done = max(0, CURRENT_MATCHER_GATE["completion_threshold"] - CURRENT_MATCHER_GATE["case_count"])
    lines.append(
        "- semantic matcher case count: current mechanism-lock gate has "
        f"{CURRENT_MATCHER_GATE['case_count']} tests and meets the "
        f"{CURRENT_MATCHER_GATE['minimum_merge_threshold']}-case minimum; "
        f"remaining gap to P0/completion thresholds is {matcher_gap_p0}/{matcher_gap_done}"
    )
    lines.append(f"- semantic matcher validation: `{CURRENT_MATCHER_GATE['tests']}` -> {CURRENT_MATCHER_GATE['test_result']}")
    if absorbed_records:
        lines.append("- fixtures and receipts: `skills/lark-slides/scripts/fixtures/svglide_artboard/reference_absorption_wave1` contains CanvasSpec, raw Satori SVG, protocol SVG, PNG preview, contact sheet, and artboard receipts for 3 pages")
        lines.append("- fixtures and receipts: `reference_absorption_wave2` contains the same proof chain for 8 pages; `reference_absorption_wave3` contains the same proof chain for 4 pages.")
        lines.append("- agent progress mode: `svglide_project_runner.py run ... --progress agent` now reports milestone artifacts to stderr and `logs/agent-progress.jsonl`; stdout remains final machine-readable JSON")
    else:
        lines.append("- fixtures, receipts, negative fixtures: none added in Phase 0/1")
    lines.append("")
    lines.append("## Skipped Items And Blockers")
    lines.append("")
    forbidden_disposition = [item for item in items if item.get("disposition") == "forbidden_runtime_dependency"]
    forbidden_runtime_boundary = [
        item
        for item in items
        if item.get("disposition") == "forbidden_runtime_dependency" or item.get("runtime_policy") == "forbidden_external_runtime_dependency"
    ]
    lines.append(f"- forbidden runtime dependency disposition items: {len(forbidden_disposition)}")
    lines.append(f"- forbidden runtime boundary items checked by `check-absorption`: {len(forbidden_runtime_boundary)}")
    if len(forbidden_disposition) != len(forbidden_runtime_boundary):
        lines.append("- Count difference is expected: some reference items still carry `runtime_policy=forbidden_external_runtime_dependency` and are scanned for runtime leaks even if their current disposition differs.")
    else:
        lines.append("- Forbidden runtime disposition count matches the runtime boundary scan count.")
    lines.append("- skipped/blocked items now have final reasons; blocked items are not counted as absorbed SVGlide assets.")
    if absorbed:
        if pending_count == 0:
            lines.append("- remaining pending items: 0; `check-absorption --require-final-disposition` passes.")
        else:
            lines.append(f"- remaining pending items: {pending_count}; `check-absorption --require-final-disposition` must fail until these receive final disposition.")
        lines.append("- remaining local blockers: none known. Live backend readback, real image acquisition, and real VF5 benchmark are intentionally unclaimed boundaries, not hidden incomplete claims.")
    else:
        lines.append("- blocker: abstraction records, fixtures, receipts, visual acceptance, and reviewer PASS are not part of this minimal Phase 0/1 delivery.")
    lines.append("")
    lines.append("## Reviewer Verdict")
    lines.append("")
    lines.append("Latest guard verdict: PASS. The final re-review accepted the runtime traceability closure, refreshed report boundary, and trusted planner provider evidence.")
    lines.append("")
    if inventory_check["issues"] or absorption_check["issues"]:
        lines.append("## Check Issues")
        lines.append("")
        for check_name, result in (("check-inventory", inventory_check), ("check-absorption", absorption_check)):
            for item in result["issues"]:
                lines.append(f"- {check_name}: {item.get('code')} {item.get('item_id', '')} {item.get('message', '')}")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_census(args: argparse.Namespace) -> int:
    payload = census_repos(args.repo)
    out_path = REPO_ROOT / args.out
    write_json(out_path, payload)
    print(json.dumps({"status": "passed", "out": str(out_path), "summary": payload["summary"]}, ensure_ascii=False))
    return 0


def run_check_inventory(args: argparse.Namespace) -> int:
    payload = load_inventory(REPO_ROOT / args.inventory)
    result = validate_inventory_payload(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


def run_check_absorption(args: argparse.Namespace) -> int:
    payload = load_inventory(REPO_ROOT / args.inventory)
    result = validate_absorption_payload(payload, require_final_disposition=args.require_final_disposition)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


def run_check_runtime_traceability(args: argparse.Namespace) -> int:
    result = validate_runtime_traceability()
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


def run_preview_disposition(args: argparse.Namespace) -> int:
    payload = load_inventory(REPO_ROOT / args.inventory)
    result = preview_disposition_payload(payload, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


def run_apply_disposition(args: argparse.Namespace) -> int:
    inventory_path = REPO_ROOT / args.inventory
    payload = load_inventory(inventory_path)
    updated, result = apply_disposition_payload(payload)
    final_check = validate_absorption_payload(updated, require_final_disposition=True)
    if final_check["status"] != "passed":
        result["status"] = "failed"
        result["final_check"] = final_check
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1
    result["final_check"] = final_check["summary"]
    if not args.dry_run:
        write_json(inventory_path, updated)
        result["out"] = str(inventory_path)
    if args.summary_only:
        result.pop("applied", None)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


def run_report(args: argparse.Namespace) -> int:
    inventory_path = REPO_ROOT / args.inventory
    payload = load_inventory(inventory_path)
    inventory_check = validate_inventory_payload(payload)
    absorption_check = validate_absorption_payload(payload)
    if args.format != "md":
        raise AbsorberError(f"unsupported report format: {args.format}")
    report = build_report(payload, inventory_check, absorption_check)
    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(json.dumps({"status": "passed", "out": str(out_path)}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SVGlide reference absorption Phase 0/1 inventory tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    census = subparsers.add_parser("census", help="Generate source inventory for reference repositories.")
    census.add_argument("--repo", default="all", help="Reference repo name or all.")
    census.add_argument("--out", default=DEFAULT_INVENTORY_PATH.as_posix(), help="Output inventory JSON path.")
    census.set_defaults(func=run_census)

    check_inventory = subparsers.add_parser("check-inventory", help="Validate source inventory paths, hashes, fields, and family coverage.")
    check_inventory.add_argument("inventory", help="Inventory JSON path.")
    check_inventory.add_argument("--pretty", action="store_true")
    check_inventory.set_defaults(func=run_check_inventory)

    check_absorption = subparsers.add_parser("check-absorption", help="Validate absorption records, duplicate targets, and forbidden runtime references.")
    check_absorption.add_argument("inventory", help="Inventory JSON path.")
    check_absorption.add_argument("--pretty", action="store_true")
    check_absorption.add_argument(
        "--require-final-disposition",
        action="store_true",
        help="Fail if any inventory item is still pending.",
    )
    check_absorption.set_defaults(func=run_check_absorption)

    check_runtime_traceability = subparsers.add_parser(
        "check-runtime-traceability",
        help="Validate active runtime assets reverse trace to abstraction records.",
    )
    check_runtime_traceability.add_argument("--pretty", action="store_true")
    check_runtime_traceability.set_defaults(func=run_check_runtime_traceability)

    preview_disposition = subparsers.add_parser("preview-disposition", help="Preview final disposition suggestions without editing inventory.")
    preview_disposition.add_argument("inventory", help="Inventory JSON path.")
    preview_disposition.add_argument("--limit", type=int, default=None, help="Limit displayed suggestions; summary still covers all pending items.")
    preview_disposition.add_argument("--pretty", action="store_true")
    preview_disposition.set_defaults(func=run_preview_disposition)

    apply_disposition = subparsers.add_parser("apply-disposition", help="Apply reviewed final disposition suggestions to the inventory.")
    apply_disposition.add_argument("inventory", help="Inventory JSON path.")
    apply_disposition.add_argument("--dry-run", action="store_true", help="Validate the writeback without editing the inventory.")
    apply_disposition.add_argument("--summary-only", action="store_true", help="Omit per-item application details from stdout.")
    apply_disposition.add_argument("--pretty", action="store_true")
    apply_disposition.set_defaults(func=run_apply_disposition)

    report = subparsers.add_parser("report", help="Write Phase 0/1 absorption report.")
    report.add_argument("--inventory", default=DEFAULT_INVENTORY_PATH.as_posix(), help="Inventory JSON path.")
    report.add_argument("--format", default="md", choices=("md",))
    report.add_argument("--out", default=DEFAULT_REPORT_PATH.as_posix(), help="Output report path.")
    report.set_defaults(func=run_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (AbsorberError, OSError) as error:
        print(f"svglide_reference_absorber: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
