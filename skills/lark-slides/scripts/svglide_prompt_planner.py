#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_planner_contracts
import svglide_palette_selector
import svglide_schema
import svglide_theme_template_selector
import beautiful_template_runtime


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PLANNER_DIR = Path("02-plan/planner")
INSTRUCTION_PATH = Path("00-input/instruction.json")
PROMPT_RECEIPT_PATH = Path("receipts/prompt-planner.json")
SOURCE_PLAN_PATH = Path("source/source-plan.json")
SOURCE_NOTES_PATH = Path("source/source-notes.md")
EVIDENCE_PATH = Path("source/evidence.json")
PLAN_CONFIRMATION_PATH = Path("02-plan/plan-confirmation.json")
PLANNER_OUTPUTS = {
    "deck-planner": Path("02-plan/deck-plan.json"),
    "slide-planner": Path("02-plan/slide-plan.json"),
    "canvas-planner": Path("02-plan/slide_plan.json"),
}
PROMPT_PATHS = {
    "deck-planner": Path("skills/lark-slides/prompts/svglide/deck-planner.prompt.md"),
    "slide-planner": Path("skills/lark-slides/prompts/svglide/slide-planner.prompt.md"),
    "canvas-planner": Path("skills/lark-slides/prompts/svglide/canvas-planner.prompt.md"),
}
SCHEMA_PATHS = {
    "deck-planner": Path("skills/lark-slides/references/svglide-deck-plan.schema.json"),
    "slide-planner": Path("skills/lark-slides/references/svglide-slide-plan.schema.json"),
    "canvas-planner": Path("skills/lark-slides/references/svglide-canvas-plan.schema.json"),
}
SVG_PRIVATE_REQUIRED_RULE_FILES = [
    "skills/lark-slides/references/lark-slides-create-svg.md",
    "skills/lark-slides/references/svg-aesthetic-review.md",
    "skills/lark-slides/references/svg-protocol.md",
    "skills/lark-slides/references/svglide-artifacts.spec.md",
    "skills/lark-slides/references/svglide-assets.contract.md",
    "skills/lark-slides/references/svglide-checks.checklist.md",
    "skills/lark-slides/references/svglide-create-svg.contract.md",
    "skills/lark-slides/references/svglide-generate-svg.contract.md",
    "skills/lark-slides/references/svglide-lock.contract.md",
    "skills/lark-slides/references/svglide-plan.contract.md",
    "skills/lark-slides/references/svglide-planning-layer.md",
    "skills/lark-slides/references/svglide-ppt-master-migration.matrix.md",
    "skills/lark-slides/references/svglide-preview.spec.md",
    "skills/lark-slides/references/svglide-readback.contract.md",
    "skills/lark-slides/references/svglide-route-admission.md",
    "skills/lark-slides/references/svglide-svg-private.rules.json",
    "skills/lark-slides/references/svglide-validation-checklist.md",
    "skills/lark-slides/references/svglide-visual-planning.md",
    "skills/lark-slides/references/svglide-workflow.spec.md",
]


class PromptPlannerError(Exception):
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


def repo_path(rel: Path | str) -> Path:
    return REPO_ROOT / Path(rel)


def project_path(project: Path, rel: Path | str) -> Path:
    return project / Path(rel)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def compact_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def strip_markdown_fence(text: str) -> str:
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def extract_json_object(text: str) -> dict[str, Any]:
    raw = strip_markdown_fence(text)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise PromptPlannerError("planner response did not contain a JSON object")
        payload = json.loads(raw[start : end + 1])
    if not isinstance(payload, dict):
        raise PromptPlannerError("planner response must be a JSON object")
    return payload


def validate_payload(payload: dict[str, Any], schema_rel: Path, *, output_path: str) -> list[dict[str, str]]:
    schema = read_json(repo_path(schema_rel))
    return [
        {"code": item["code"], "message": item["message"], "path": item["path"], "output_path": output_path}
        for item in svglide_schema.validate_json_schema(payload, schema)
    ]


def theme_registry_bundle() -> list[dict[str, Any]]:
    registry = beautiful_template_runtime.theme_registry()
    result: list[dict[str, Any]] = []
    for item in registry.get("themes", []) if isinstance(registry, dict) else []:
        if not isinstance(item, dict) or item.get("status") != "active":
            continue
        record = {"id": item.get("id"), "status": item.get("status")}
        record["colors"] = item.get("colors")
        result.append(record)
    return result


def template_registry_bundle() -> list[dict[str, Any]]:
    registry = beautiful_template_runtime.template_registry()
    result: list[dict[str, Any]] = []
    for item in registry.get("templates", []) if isinstance(registry, dict) else []:
        if not isinstance(item, dict) or item.get("status") != "active":
            continue
        result.append(
            {
                "id": item.get("id"),
                "renderer_id": item.get("renderer_id"),
                "layout_family": item.get("layout_family"),
                "required_content": item.get("required_content"),
                "optional_content": item.get("optional_content"),
                "max_items": item.get("max_items"),
                "text_budget": item.get("text_budget"),
                "supported_theme_ids": item.get("supported_theme_ids"),
                "source_template_id": item.get("source_template_id"),
                "claim_level": item.get("claim_level"),
                "family_usage_policy_summary": item.get("family_usage_policy_summary"),
                "cjk_policy_summary": item.get("cjk_policy_summary"),
                "extension_grammar_summary": item.get("extension_grammar_summary"),
                "benchmark_roles": item.get("benchmark_roles"),
            }
        )
    return result


def template_family_policy_context_bundle() -> list[dict[str, Any]]:
    return beautiful_template_runtime.family_policy_context()


def load_selection_context(project: Path | None = None) -> dict[str, Any]:
    if project is None:
        return {}
    context: dict[str, Any] = {}
    for key, rel in {
        "palette_selection": Path("02-plan/palette-selection.json"),
        "theme_template_selection": Path("02-plan/theme-template-selection.json"),
    }.items():
        path = project / rel
        if not path.exists():
            continue
        try:
            context[key] = read_json(path)
        except (OSError, json.JSONDecodeError):
            context[key] = {"status": "unreadable", "path": rel.as_posix()}
    return context


def load_context(project: Path | None = None) -> dict[str, Any]:
    context = {
        "templates": template_registry_bundle(),
        "template_family_policy_context": template_family_policy_context_bundle(),
        "themes": theme_registry_bundle(),
        "layout_archetypes": read_json(repo_path("skills/lark-slides/references/svglide-layout-archetypes.json")),
        "component_registry": beautiful_template_runtime.component_registry(),
        "canvas_spec_schema": read_json(repo_path("skills/lark-slides/references/svglide-canvas-spec.schema.json")),
        "planner_prompt_contracts": read_json(repo_path("skills/lark-slides/references/svglide-planner-prompt-contracts.json")),
    }
    context["selection"] = load_selection_context(project)
    return context


def instruction_payload(*, prompt: str, language: str, target_slide_count: int, audience: str) -> dict[str, Any]:
    return {
        "schema_version": "svglide-instruction/v1",
        "source": "cli_raw_prompt",
        "raw_prompt": prompt,
        "language": language,
        "target_slide_count": target_slide_count,
        "deck_intent": "full_deck" if target_slide_count > 1 else "single_page",
        "audience": audience,
        "route": "svglide-svg",
        "generation_mode": "artboard_satori",
        "created_at": now_iso(),
        "must_include": [
            "deck plan",
            "slide plan",
            "canvas spec",
            "asset contracts",
            "real visual asset acquisition before dry_run",
        ],
        "must_avoid": [
            "do not invent unsourced dates, prices, valuations, rankings, forecasts, scientific measurements, travel logistics, or regulatory facts",
            "do not present assumptions, rumors, or estimates as confirmed facts",
            "do not output free HTML, CSS, SVG, JSX, or TSX",
            "do not call live_create",
        ],
    }


def build_source_prompt(instruction: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are the SVGlide Source Planner.",
            "Use web/search knowledge if available, but return JSON only.",
            "Output exactly this object shape:",
            '{"schema_version":"svglide-source-plan/v1","source_notes_markdown":"...","evidence":{...}}',
            "The evidence object must use schema_version svglide-evidence/v1, source_status ready, and at least 3 items.",
            "Every evidence item must have id and text of at least 20 characters. Include source/url/date when known.",
            "Do not invent topic-specific facts. Mark uncertain or unsourced details as analysis context or pending confirmation.",
            "",
            "Instruction:",
            compact_json(instruction),
        ]
    )


def build_deck_prompt(instruction: dict[str, Any], context: dict[str, Any]) -> str:
    base = repo_path(PROMPT_PATHS["deck-planner"]).read_text(encoding="utf-8")
    bundle = {
        "instruction": instruction,
        "available_template_registry": context["templates"],
        "available_theme_registry": context["themes"],
        "output_schema": read_json(repo_path(SCHEMA_PATHS["deck-planner"])),
    }
    return "\n\n".join(
        [
            base,
            "Additional run instruction: output JSON only and satisfy the schema exactly.",
            "For this topic, build a complete deck narrative without inventing unsourced facts or forcing another domain's structure.",
            "Keep titles and key messages concise enough for slide canvases.",
            "Input bundle:",
            compact_json(bundle),
        ]
    )


def build_slide_prompt(instruction: dict[str, Any], deck_plan: dict[str, Any], context: dict[str, Any], deck_sha: str) -> str:
    base = repo_path(PROMPT_PATHS["slide-planner"]).read_text(encoding="utf-8")
    bundle = {
        "instruction": instruction,
        "deck_plan": deck_plan,
        "deck_plan_ref": {"path": "02-plan/deck-plan.json", "sha256": deck_sha},
        "available_template_registry": context["templates"],
        "available_theme_registry": context["themes"],
        "layout_archetypes": context["layout_archetypes"],
        "component_registry": context["component_registry"],
        "selection_context": context.get("selection", {}),
        "output_schema": read_json(repo_path(SCHEMA_PATHS["slide-planner"])),
    }
    return "\n\n".join(
        [
            base,
            "Additional run instruction: output JSON only and use only palette/template/theme candidates from selection_context when present.",
            "Use varied page shapes that fit this topic. Include at least one image-feature page when visual assets are requested and one evidence/data/story page when the content has claims or comparisons.",
            "Do not output asset contracts here; only choose template/theme/content requirements.",
            "Input bundle:",
            compact_json(bundle),
        ]
    )


def build_canvas_prompt(instruction: dict[str, Any], deck_plan: dict[str, Any], slide_plan: dict[str, Any], context: dict[str, Any]) -> str:
    base = repo_path(PROMPT_PATHS["canvas-planner"]).read_text(encoding="utf-8")
    bundle = {
        "instruction": instruction,
        "deck_plan": deck_plan,
        "slide_plan": slide_plan,
        "available_template_registry": context["templates"],
        "available_theme_registry": context["themes"],
        "component_registry": context["component_registry"],
        "selection_context": context.get("selection", {}),
        "canvas_spec_schema": context["canvas_spec_schema"],
        "output_schema": read_json(repo_path(SCHEMA_PATHS["canvas-planner"])),
        "required_loaded_rule_set": SVG_PRIVATE_REQUIRED_RULE_FILES,
        "required_family_plan_fields": [
            "template_family_selection",
            "template_variant",
            "semantic_blocks",
            "component_selection",
            "asset_strategy",
        ],
        "content_key_guidance": {
            "cover-hero": ["eyebrow", "title", "subtitle", "chips"],
            "section-title": ["eyebrow", "title", "subtitle"],
            "agenda-list": ["title", "items"],
            "comparison-cards": ["title", "left_title", "right_title", "left_points", "right_points", "conclusion"],
            "timeline-steps": ["title", "events"],
            "process-flow": ["title", "steps"],
            "metric-dashboard": ["title", "metrics"],
            "risk-alert": ["title", "risks", "severity", "summary"],
            "image-feature": ["title", "subtitle", "points", "image_label", "caption"],
            "data-story": ["eyebrow", "title", "subtitle", "metrics", "metric_labels", "milestones", "callout"],
            "summary-final": ["eyebrow", "title", "subtitle", "takeaways"],
        },
    }
    return "\n\n".join(
        [
            base,
            "Additional run instruction: output JSON only.",
            "When selection_context is present, template_id/theme_id/palette_id must come from its candidates and every canvas_spec must include selection_trace.",
            "The top-level object must also be the final 02-plan/slide_plan.json.",
            "For ordinary user prompts, set deck_intent to full_deck, target_slide_count/page_count to the instruction target, and produce that many slides.",
            "Do not produce a 4-page sample unless instruction.deck_intent is sample/single_page/fixture.",
            "The top-level plan must include theme_policy with scope deck and allow_multi_theme false unless the user explicitly asks for multiple theme chapters.",
            "The top-level plan must include asset_policy with required true and minimum_visual_asset_count at least 3.",
            "It must include top-level asset_contracts as an array of at least 3 objects for real visual acquisition.",
            "Each asset contract must include id, page or usage_page, placement_role, query, required true, safe_text_zones, and crop_hint.",
            "Use placement_role cover for page 1, body_visual for image-feature pages, and closing for the final page.",
            "For body_visual assets, choose image-feature pages so the generated SVG has an asset slot.",
            "Use generation_mode artboard_satori and route svglide-svg.",
            "The top-level plan must include project_palette, project_theme, palette_selection_receipt, and selection_receipt from selection_context.",
            "The top-level plan must include language, audience, deck_structure, and visual_identity before plan confirmation is written.",
            "loaded_rule_set must include every path in required_loaded_rule_set.",
            "Use template_family_selection, template_variant, semantic_blocks, component_selection, and asset_strategy for visual planning.",
            "Do not output legacy low-level primitive planning fields; keep visual planning at template family, semantic block, component, and asset strategy level.",
            "Every slide must include asset_contract; use none_required only when the final SVG will not use image primitives.",
            "Every visible numeric or business claim must have a top-level business_claims entry with source_type and source_note/assumption/derivation.",
            "deck_structure must include at least cover, content, and closing. Do not output a single-slide poster plan.",
            "visual_identity must include theme_archetype, design_dna.palette, design_dna.layout_motif, design_dna.shape_language, design_dna.image_treatment, design_dna.component_bias, at least 3 theme_visual_anchors, forbidden_reuse, and distinctness_target.",
            "Every slide must include page_type, section, role, body_points, and source_refs; content slides need at least 2 body_points and source_refs.",
            "For each selected template, provide every visible content key listed in content_key_guidance. Do not rely on renderer fallback/default text.",
            "For data-story, metrics must be a list of short strings, not objects; metric_labels and milestones must be explicit visible string lists.",
            "If component_selection includes a chart component, include chart_contract with type, source_refs, encoding, and claims.",
            "Canvas specs must use 960x540 canvas, safe_area x=48 y=40 width=864 height=460, and at least one semantic element bbox inside safe_area.",
            "Keep visible text short; no title over 34 Chinese chars or 44 Latin chars.",
            "Input bundle:",
            compact_json(bundle),
        ]
    )


def provider_command(
    *,
    provider: str,
    planner_command: str | None,
    stage: str,
    raw_output: Path,
    schema_path: Path | None,
    search: bool,
) -> list[str]:
    if planner_command:
        values = {
            "stage": stage,
            "raw_output": raw_output.as_posix(),
            "schema": schema_path.as_posix() if schema_path else "",
        }
        return [part.format(**values) for part in shlex.split(planner_command)]
    if provider == "claude":
        return ["claude", "-p", "--output-format", "text"]
    if provider == "codex":
        command = ["codex", "exec", "--ephemeral", "--sandbox", "read-only"]
        if search:
            command.append("--search")
        if schema_path is not None:
            command.extend(["--output-schema", schema_path.as_posix()])
        command.extend(["--output-last-message", raw_output.as_posix(), "-"])
        return command
    raise PromptPlannerError(f"unsupported planner provider: {provider}")


def trusted_provider_evidence(provider: str, planner_command: str | None, trusted_provider_id: str | None) -> dict[str, Any]:
    requires_trusted_provider = provider != "codex" or bool(planner_command)
    if requires_trusted_provider and not trusted_provider_id:
        raise PromptPlannerError(
            "trusted_provider_id is required when using an external planner provider or --planner-command"
        )
    return {
        "provider": provider,
        "planner_command_present": bool(planner_command),
        "requires_trusted_provider": requires_trusted_provider,
        "trusted_provider_id": trusted_provider_id,
        "authorized": (not requires_trusted_provider) or bool(trusted_provider_id),
    }


def planner_file(stage: str, suffix: str) -> Path:
    safe = stage.replace("_", "-")
    return PLANNER_DIR / f"{safe}.{suffix}"


def call_planner(
    project: Path,
    *,
    stage: str,
    prompt: str,
    output_rel: Path | None,
    schema_rel: Path | None,
    provider: str,
    planner_command: str | None,
    trusted_provider_id: str | None,
    search: bool,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started_at = now_iso()
    input_rel = planner_file(stage, "input.txt")
    raw_rel = planner_file(stage, "raw.txt")
    receipt_rel = planner_file(stage, "receipt.json")
    write_text(project_path(project, input_rel), prompt)
    raw_output = project_path(project, raw_rel)
    if raw_output.exists():
        raw_output.unlink()
    command = provider_command(
        provider=provider,
        planner_command=planner_command,
        stage=stage,
        raw_output=raw_output,
        schema_path=repo_path(schema_rel) if schema_rel else None,
        search=search,
    )
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if not raw_output.exists():
        write_text(raw_output, completed.stdout)
    raw_text = raw_output.read_text(encoding="utf-8")
    issues: list[dict[str, Any]] = []
    payload: dict[str, Any] | None = None
    status = "passed"
    if completed.returncode != 0:
        status = "failed"
        issues.append({"code": "planner_command_failed", "returncode": completed.returncode, "stderr": completed.stderr})
    else:
        try:
            payload = extract_json_object(raw_text)
        except (json.JSONDecodeError, PromptPlannerError) as error:
            status = "failed"
            issues.append({"code": "planner_output_json_invalid", "message": str(error)})
    if payload is not None and schema_rel is not None and output_rel is not None:
        schema_issues = validate_payload(payload, schema_rel, output_path=output_rel.as_posix())
        if schema_issues:
            status = "failed"
            issues.extend(schema_issues)
    if payload is not None and output_rel is not None and not issues:
        write_json(project_path(project, output_rel), payload)
    receipt = {
        "schema_version": "svglide-prompt-planner-stage-receipt/v1",
        "stage": stage,
        "status": status,
        "provider": provider,
        "trusted_provider_id": trusted_provider_id,
        "search_enabled": search,
        "started_at": started_at,
        "ended_at": now_iso(),
        "command": command,
        "returncode": completed.returncode,
        "input_path": input_rel.as_posix(),
        "input_sha256": file_sha256(project_path(project, input_rel)),
        "raw_output_path": raw_rel.as_posix(),
        "raw_output_sha256": file_sha256(project_path(project, raw_rel)),
        "output_path": output_rel.as_posix() if output_rel else None,
        "output_sha256": file_sha256(project_path(project, output_rel)) if output_rel and project_path(project, output_rel).exists() else None,
        "stdout_tail": completed.stdout[-1000:],
        "stderr_tail": completed.stderr[-2000:],
        "issues": issues,
    }
    write_json(project_path(project, receipt_rel), receipt)
    if status != "passed" or payload is None:
        raise PromptPlannerError(f"{stage} failed; see {project_path(project, receipt_rel)}")
    return payload, receipt


def validate_source_plan(source_plan: dict[str, Any]) -> None:
    evidence = source_plan.get("evidence")
    if not isinstance(evidence, dict):
        raise PromptPlannerError("source-planner output must include evidence object")
    issues = validate_payload(evidence, Path("skills/lark-slides/references/svglide-evidence.schema.json"), output_path=EVIDENCE_PATH.as_posix())
    if evidence.get("source_status") != "ready":
        issues.append({"code": "source_status_not_ready", "message": "source-planner evidence must be ready", "path": "$.source_status"})
    items = evidence.get("items")
    if not isinstance(items, list) or len(items) < 3:
        issues.append({"code": "source_item_count_too_low", "message": "source-planner evidence needs at least 3 items", "path": "$.items"})
    if issues:
        raise PromptPlannerError(f"source-planner evidence failed validation: {issues}")


def write_source_outputs(project: Path, source_plan: dict[str, Any]) -> None:
    validate_source_plan(source_plan)
    write_json(project_path(project, SOURCE_PLAN_PATH), source_plan)
    notes = source_plan.get("source_notes_markdown")
    if not isinstance(notes, str) or not notes.strip():
        notes = "# Source Notes\n\n- Planner did not provide notes; see source/evidence.json.\n"
    write_text(project_path(project, SOURCE_NOTES_PATH), notes.rstrip() + "\n")
    write_json(project_path(project, EVIDENCE_PATH), source_plan["evidence"])


def write_repair_plan(project: Path) -> Path:
    repair = {
        "schema_version": "svglide-repair-plan/v1",
        "target_plan_path": "02-plan/slide_plan.json",
        "change_reason": "No repair requested in prompt-plan path; keep scoped repair artifact available for contract validation.",
        "patches": [
            {
                "op": "test",
                "path": "/slides/0/page",
                "value": 1,
                "reason": "Verify first slide page index without rewriting the deck.",
            }
        ],
    }
    path = project / "02-plan/repair-plan.json"
    write_json(path, repair)
    return path


def require_asset_contracts(plan: dict[str, Any]) -> None:
    contracts = plan.get("asset_contracts")
    if not isinstance(contracts, list) or len(contracts) < 3:
        raise PromptPlannerError("canvas-planner output must include at least 3 top-level asset_contracts")
    for index, contract in enumerate(contracts, 1):
        if not isinstance(contract, dict):
            raise PromptPlannerError(f"asset_contracts[{index - 1}] must be an object")
        missing = [key for key in ["id", "query", "required"] if key not in contract]
        if missing:
            raise PromptPlannerError(f"asset_contracts[{index - 1}] missing {missing}")
        if not (contract.get("page") or contract.get("usage_page")):
            raise PromptPlannerError(f"asset_contracts[{index - 1}] must include page or usage_page")


def write_plan_confirmation(project: Path, *, source: str) -> dict[str, Any]:
    plan = project / PLANNER_OUTPUTS["canvas-planner"]
    payload = {
        "version": "svglide-plan-confirmation/v1",
        "status": "confirmed",
        "confirmed_by": "user",
        "confirmed_at": now_iso(),
        "plan_path": PLANNER_OUTPUTS["canvas-planner"].as_posix(),
        "plan_sha256": file_sha256(plan),
        "confirmation_source": source,
    }
    write_json(project / PLAN_CONFIRMATION_PATH, payload)
    return payload


def ensure_fresh_outputs(project: Path, *, force: bool) -> None:
    existing = [
        INSTRUCTION_PATH,
        SOURCE_PLAN_PATH,
        EVIDENCE_PATH,
        Path("02-plan/deck-plan.json"),
        Path("02-plan/slide-plan.json"),
        Path("02-plan/slide_plan.json"),
        PLAN_CONFIRMATION_PATH,
    ]
    present = [path.as_posix() for path in existing if (project / path).exists()]
    if present and not force:
        raise PromptPlannerError(f"prompt-plan outputs already exist; pass --force to overwrite: {present}")


def run_prompt_plan(
    project: Path,
    *,
    prompt: str,
    target_slide_count: int = 10,
    language: str = "zh-CN",
    audience: str = "投资/战略分析读者",
    provider: str = "codex",
    planner_command: str | None = None,
    trusted_provider_id: str | None = None,
    search: bool = True,
    timeout: int = 300,
    force: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    provider_evidence = trusted_provider_evidence(provider, planner_command, trusted_provider_id)
    ensure_fresh_outputs(project, force=force)
    instruction = instruction_payload(prompt=prompt, language=language, target_slide_count=target_slide_count, audience=audience)
    write_json(project / INSTRUCTION_PATH, instruction)
    receipts: list[dict[str, Any]] = []

    source_plan, source_receipt = call_planner(
        project,
        stage="source-planner",
        prompt=build_source_prompt(instruction),
        output_rel=None,
        schema_rel=None,
        provider=provider,
        planner_command=planner_command,
        trusted_provider_id=trusted_provider_id,
        search=search,
        timeout=timeout,
    )
    write_source_outputs(project, source_plan)
    receipts.append(source_receipt)
    evidence = source_plan.get("evidence") if isinstance(source_plan.get("evidence"), dict) else None
    palette_selection = svglide_palette_selector.select_palette(project, prompt, top_k=5, evidence=evidence)
    svglide_palette_selector.write_palette_selection(project, palette_selection)
    theme_template_selection = svglide_theme_template_selector.select_theme_template(project, prompt, top_k=5, evidence=evidence)
    svglide_theme_template_selector.write_selection(project, theme_template_selection)
    context = load_context(project)

    deck_plan, deck_receipt = call_planner(
        project,
        stage="deck-planner",
        prompt=build_deck_prompt(instruction, context),
        output_rel=PLANNER_OUTPUTS["deck-planner"],
        schema_rel=SCHEMA_PATHS["deck-planner"],
        provider=provider,
        planner_command=planner_command,
        trusted_provider_id=trusted_provider_id,
        search=search,
        timeout=timeout,
    )
    receipts.append(deck_receipt)
    deck_sha = file_sha256(project / PLANNER_OUTPUTS["deck-planner"])

    slide_plan, slide_receipt = call_planner(
        project,
        stage="slide-planner",
        prompt=build_slide_prompt(instruction, deck_plan, context, deck_sha),
        output_rel=PLANNER_OUTPUTS["slide-planner"],
        schema_rel=SCHEMA_PATHS["slide-planner"],
        provider=provider,
        planner_command=planner_command,
        trusted_provider_id=trusted_provider_id,
        search=search,
        timeout=timeout,
    )
    receipts.append(slide_receipt)

    canvas_plan, canvas_receipt = call_planner(
        project,
        stage="canvas-planner",
        prompt=build_canvas_prompt(instruction, deck_plan, slide_plan, context),
        output_rel=PLANNER_OUTPUTS["canvas-planner"],
        schema_rel=SCHEMA_PATHS["canvas-planner"],
        provider=provider,
        planner_command=planner_command,
        trusted_provider_id=trusted_provider_id,
        search=search,
        timeout=timeout,
    )
    require_asset_contracts(canvas_plan)
    receipts.append(canvas_receipt)

    repair_plan = write_repair_plan(project)
    confirmation = write_plan_confirmation(project, source=INSTRUCTION_PATH.as_posix())
    contract_check = svglide_planner_contracts.run(project)
    if contract_check.get("status") != "passed":
        raise PromptPlannerError(f"planner contract check failed; see {project / '06-check/planner-contract-check.json'}")

    result = {
        "schema_version": "svglide-prompt-planner-receipt/v1",
        "stage": "prompt-plan",
        "status": "passed",
        "provider": provider,
        "provider_type": provider,
        "trusted_provider_evidence": provider_evidence,
        "search_enabled": search,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "instruction": INSTRUCTION_PATH.as_posix(),
            "instruction_sha256": file_sha256(project / INSTRUCTION_PATH),
            "prompt": prompt,
            "target_slide_count": target_slide_count,
            "language": language,
            "audience": audience,
        },
        "outputs": {
            "source_plan": SOURCE_PLAN_PATH.as_posix(),
            "source_notes": SOURCE_NOTES_PATH.as_posix(),
            "evidence": EVIDENCE_PATH.as_posix(),
            "deck_plan": PLANNER_OUTPUTS["deck-planner"].as_posix(),
            "slide_plan": PLANNER_OUTPUTS["slide-planner"].as_posix(),
            "canvas_plan": PLANNER_OUTPUTS["canvas-planner"].as_posix(),
            "repair_plan": relpath(repair_plan, project),
            "plan_confirmation": PLAN_CONFIRMATION_PATH.as_posix(),
            "planner_contract_check": "06-check/planner-contract-check.json",
        },
        "planner_stage_receipts": [receipt["stage"] for receipt in receipts],
        "planner_stage_receipt_paths": [planner_file(receipt["stage"], "receipt.json").as_posix() for receipt in receipts],
        "planner_raw_outputs": [
            {
                "stage": receipt["stage"],
                "path": receipt["raw_output_path"],
                "sha256": receipt["raw_output_sha256"],
            }
            for receipt in receipts
        ],
        "plan_confirmation": confirmation,
        "summary": {
            "slide_count": len(canvas_plan.get("slides", [])) if isinstance(canvas_plan.get("slides"), list) else None,
            "asset_contract_count": len(canvas_plan.get("asset_contracts", [])) if isinstance(canvas_plan.get("asset_contracts"), list) else 0,
            "planner_contract_status": contract_check.get("status"),
        },
    }
    write_json(project / PROMPT_RECEIPT_PATH, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate SVGlide source/deck/slide/canvas plans from a raw prompt.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--target-slide-count", type=int, default=8)
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--audience", default="投资/战略分析读者")
    parser.add_argument("--provider", default="codex", choices=["codex", "claude", "command"])
    parser.add_argument("--planner-command", help="custom command with {stage}, {raw_output}, and {schema} placeholders")
    parser.add_argument("--trusted-provider-id", help="required for external planner providers or --planner-command")
    parser.add_argument("--no-search", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_prompt_plan(
            args.project,
            prompt=args.prompt,
            target_slide_count=args.target_slide_count,
            language=args.language,
            audience=args.audience,
            provider=args.provider,
            planner_command=args.planner_command,
            trusted_provider_id=args.trusted_provider_id,
            search=not args.no_search,
            timeout=args.timeout,
            force=args.force,
        )
    except (OSError, subprocess.TimeoutExpired, PromptPlannerError, json.JSONDecodeError) as error:
        print(f"svglide_prompt_planner: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
