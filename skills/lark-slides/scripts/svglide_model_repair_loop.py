#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_PLAN = Path("02-plan/slide_plan.json")
DEFAULT_REPAIR_PLAN = Path("02-plan/repair-plan.json")
DEFAULT_RECEIPT = Path("receipts/repair-loop.json")
UNSCOPED_PATCH_PATHS = {"", "/", "/slides", "/style_system", "/art_direction", "/asset_contracts"}
ALLOWED_PATCH_ROOTS = ("slides", "style_system", "art_direction", "asset_contracts")


class RepairLoopError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def project_rel(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_project_path(project: Path, path: Path) -> Path:
    return path if path.is_absolute() else project / path


def pointer_tokens(path: str) -> list[str]:
    if not path.startswith("/"):
        raise RepairLoopError(f"JSON Patch path must be an absolute JSON Pointer: {path}")
    if path == "/":
        return [""]
    return [token.replace("~1", "/").replace("~0", "~") for token in path[1:].split("/")]


def is_array_index(token: str) -> bool:
    return bool(re.fullmatch(r"0|[1-9]\d*", token))


def value_at(document: Any, tokens: list[str]) -> Any:
    current = document
    for token in tokens:
        if isinstance(current, list):
            if not is_array_index(token):
                raise RepairLoopError(f"JSON Pointer list token must be an index: {token}")
            index = int(token)
            if index >= len(current):
                raise RepairLoopError(f"JSON Pointer index out of range: {token}")
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise RepairLoopError(f"JSON Pointer key does not exist: {token}")
            current = current[token]
        else:
            raise RepairLoopError(f"JSON Pointer cannot descend into scalar at token: {token}")
    return current


def parent_and_key(document: Any, tokens: list[str]) -> tuple[Any, str]:
    if not tokens:
        raise RepairLoopError("JSON Patch path cannot target the whole document")
    return value_at(document, tokens[:-1]) if len(tokens) > 1 else document, tokens[-1]


def validate_repair_plan_schema(repair_plan: dict[str, Any]) -> list[dict[str, Any]]:
    schema = svglide_schema.read_json(REPO_ROOT / "skills/lark-slides/references/svglide-repair-plan.schema.json")
    return svglide_schema.validate_json_schema(repair_plan, schema)


def validate_plan_schema(plan: dict[str, Any]) -> list[dict[str, Any]]:
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-plan.schema.json"))
    return svglide_schema.validate_json_schema(plan, schema)


def broad_path_issue(path: str) -> str | None:
    if path in UNSCOPED_PATCH_PATHS:
        return f"patch path is too broad: {path}"
    if re.fullmatch(r"/slides/\d+", path) or re.fullmatch(r"/asset_contracts/\d+", path):
        return f"patch path must not rewrite an entire array item: {path}"
    if re.fullmatch(r"/slides/\d+/(canvas_spec|content_requirements|body_points|risk_flags|svg_effects|required_primitives|svg_primitives)", path):
        return f"patch path must target a leaf field, not a whole object/list: {path}"
    if re.fullmatch(r"/slides/\d+/canvas_spec/(content|theme|semantic_elements|quality_constraints)", path):
        return f"patch path must target a leaf field, not a whole object/list: {path}"
    if re.fullmatch(r"/slides/\d+/canvas_spec/semantic_elements/\d+", path):
        return f"patch path must target a leaf field, not a whole semantic element: {path}"
    if re.fullmatch(r"/slides/\d+/canvas_spec/semantic_elements/\d+/bbox", path):
        return f"patch path must target a bbox leaf field, not the whole bbox: {path}"
    return None


def validate_patch_scope(plan: dict[str, Any], patch: dict[str, Any], index: int) -> None:
    op = patch.get("op")
    path = patch.get("path")
    if op not in {"add", "replace", "remove", "test"}:
        raise RepairLoopError(f"patches[{index}].op is not supported: {op}")
    if not isinstance(path, str):
        raise RepairLoopError(f"patches[{index}].path must be a string")
    tokens = pointer_tokens(path)
    if not tokens or tokens[0] not in ALLOWED_PATCH_ROOTS:
        raise RepairLoopError(f"patches[{index}].path must target slides/style_system/art_direction/asset_contracts: {path}")
    issue = broad_path_issue(path)
    if issue:
        raise RepairLoopError(f"patches[{index}]: {issue}")
    if op in {"add", "replace"} and isinstance(patch.get("value"), (dict, list)):
        raise RepairLoopError(f"patches[{index}].value must be a scalar leaf value")
    if op in {"replace", "remove", "test"}:
        target = value_at(plan, tokens)
        if isinstance(target, (dict, list)):
            raise RepairLoopError(f"patches[{index}] targets a broad object/list value: {path}")
    if op == "add":
        parent, key = parent_and_key(plan, tokens)
        if isinstance(parent, list):
            if key != "-" and (not is_array_index(key) or int(key) > len(parent)):
                raise RepairLoopError(f"patches[{index}] add index is out of range: {path}")
        elif not isinstance(parent, dict):
            raise RepairLoopError(f"patches[{index}] add parent must be an object or list: {path}")


def apply_one_patch(document: Any, patch: dict[str, Any]) -> None:
    tokens = pointer_tokens(patch["path"])
    op = patch["op"]
    if op == "test":
        actual = value_at(document, tokens)
        if actual != patch.get("value"):
            raise RepairLoopError(f"test patch failed at {patch['path']}: expected {patch.get('value')!r}, got {actual!r}")
        return
    parent, key = parent_and_key(document, tokens)
    if isinstance(parent, list):
        if op == "add":
            if key == "-":
                parent.append(patch.get("value"))
            else:
                parent.insert(int(key), patch.get("value"))
            return
        if not is_array_index(key):
            raise RepairLoopError(f"JSON Patch list token must be an index: {key}")
        index = int(key)
        if op == "replace":
            parent[index] = patch.get("value")
        elif op == "remove":
            del parent[index]
        return
    if not isinstance(parent, dict):
        raise RepairLoopError(f"JSON Patch parent is not an object/list: {patch['path']}")
    if op == "replace":
        if key not in parent:
            raise RepairLoopError(f"replace target does not exist: {patch['path']}")
        parent[key] = patch.get("value")
    elif op == "remove":
        if key not in parent:
            raise RepairLoopError(f"remove target does not exist: {patch['path']}")
        del parent[key]
    elif op == "add":
        parent[key] = patch.get("value")


def build_receipt(
    *,
    status: str,
    started_at: str,
    project: Path,
    plan_path: Path,
    repair_plan_path: Path,
    failing_receipt_path: Path,
    original_plan_sha256: str | None,
    updated_plan_sha256: str | None,
    patches: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "svglide-repair-loop-receipt/v1",
        "stage": "repair-loop",
        "status": status,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "plan": project_rel(plan_path, project),
            "plan_sha256": original_plan_sha256,
            "repair_plan": project_rel(repair_plan_path, project),
            "repair_plan_sha256": file_sha256(repair_plan_path) if repair_plan_path.exists() else None,
            "failing_receipt": project_rel(failing_receipt_path, project),
            "failing_receipt_sha256": file_sha256(failing_receipt_path) if failing_receipt_path.exists() else None,
        },
        "outputs": {
            "plan": project_rel(plan_path, project) if updated_plan_sha256 else None,
            "plan_sha256": updated_plan_sha256,
            "receipt": DEFAULT_RECEIPT.as_posix(),
        },
        "summary": {
            "patch_count": len(patches),
            "scoped_patch_only": status == "passed",
            "error_count": len(issues),
        },
        "patches": [{"op": patch.get("op"), "path": patch.get("path"), "reason": patch.get("reason")} for patch in patches],
        "issues": issues,
    }


def run_repair_loop(
    project: Path,
    *,
    failing_receipt: Path,
    repair_plan: Path = DEFAULT_REPAIR_PLAN,
    plan: Path = DEFAULT_PLAN,
    receipt_path: Path = DEFAULT_RECEIPT,
) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan_path = resolve_project_path(project, plan)
    repair_plan_path = resolve_project_path(project, repair_plan)
    failing_receipt_path = resolve_project_path(project, failing_receipt)
    output_receipt = resolve_project_path(project, receipt_path)
    patches: list[dict[str, Any]] = []
    original_hash = file_sha256(plan_path) if plan_path.exists() else None
    try:
        current_plan = read_json(plan_path)
        repair_payload = read_json(repair_plan_path)
        failing_payload = read_json(failing_receipt_path)
        if not isinstance(current_plan, dict):
            raise RepairLoopError("slide_plan must be a JSON object")
        if not isinstance(repair_payload, dict):
            raise RepairLoopError("repair plan must be a JSON object")
        if not isinstance(failing_payload, dict):
            raise RepairLoopError("failing receipt must be a JSON object")
        if failing_payload.get("status") == "passed":
            raise RepairLoopError("failing receipt status must not be passed")
        schema_issues = validate_repair_plan_schema(repair_payload)
        if schema_issues:
            raise RepairLoopError(f"repair plan schema failed: {schema_issues}")
        if repair_payload.get("target_plan_path") != project_rel(plan_path, project):
            raise RepairLoopError("repair plan target_plan_path does not match selected slide_plan")
        raw_patches = repair_payload.get("patches")
        if not isinstance(raw_patches, list):
            raise RepairLoopError("repair plan patches must be a list")
        patches = raw_patches
        for index, patch in enumerate(patches):
            if not isinstance(patch, dict):
                raise RepairLoopError(f"patches[{index}] must be an object")
            validate_patch_scope(current_plan, patch, index)
        updated_plan = copy.deepcopy(current_plan)
        for patch in patches:
            apply_one_patch(updated_plan, patch)
        plan_issues = validate_plan_schema(updated_plan)
        if plan_issues:
            raise RepairLoopError(f"patched slide_plan failed schema validation: {plan_issues}")
        write_json(plan_path, updated_plan)
        receipt = build_receipt(
            status="passed",
            started_at=started_at,
            project=project,
            plan_path=plan_path,
            repair_plan_path=repair_plan_path,
            failing_receipt_path=failing_receipt_path,
            original_plan_sha256=original_hash,
            updated_plan_sha256=file_sha256(plan_path),
            patches=patches,
            issues=[],
        )
        write_json(output_receipt, receipt)
        return receipt
    except (OSError, json.JSONDecodeError, RepairLoopError) as error:
        issues = [{"code": "repair_loop_failed", "message": str(error)}]
        receipt = build_receipt(
            status="failed",
            started_at=started_at,
            project=project,
            plan_path=plan_path,
            repair_plan_path=repair_plan_path,
            failing_receipt_path=failing_receipt_path,
            original_plan_sha256=original_hash,
            updated_plan_sha256=None,
            patches=patches,
            issues=issues,
        )
        write_json(output_receipt, receipt)
        raise RepairLoopError(str(error)) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a scoped SVGlide repair-plan JSON Patch to slide_plan.json.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--failing-receipt", type=Path, required=True)
    parser.add_argument("--repair-plan", type=Path, default=DEFAULT_REPAIR_PLAN)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        receipt = run_repair_loop(
            args.project,
            failing_receipt=args.failing_receipt,
            repair_plan=args.repair_plan,
            plan=args.plan,
            receipt_path=args.receipt,
        )
    except RepairLoopError as error:
        print(f"svglide_model_repair_loop: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
