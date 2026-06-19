#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


PLAN_PATH = Path("02-plan/slide_plan.json")
PREPARED_SVG_DIR = Path("04-svg/prepared")
OUTPUT_PATH = Path("06-check/chart-verify.json")
PASS_ACTION = "create_live"
FAIL_ACTION = "repair_and_rerun"
CHART_MARK_RE = re.compile(r"<(rect|circle|path|line|polyline|polygon)\b", re.IGNORECASE)


class ChartVerifyError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ChartVerifyError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChartVerifyError(f"invalid JSON in {path}: expected object")
    return payload


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def issue(code: str, message: str, *, page: int | None = None, path: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    if path:
        payload["path"] = path
    return payload


def prepared_svg_files(project: Path) -> list[Path]:
    root = project / PREPARED_SVG_DIR
    return sorted(path for path in root.glob("*.svg") if path.is_file()) if root.exists() else []


def prepared_file_hashes(project: Path) -> list[dict[str, str]]:
    return [{"path": relpath(path, project), "sha256": file_sha256(path)} for path in prepared_svg_files(project)]


def chart_verify_required(slide: dict[str, Any]) -> bool:
    contract = slide.get("chart_contract")
    if isinstance(contract, dict):
        verify = contract.get("verify")
        if verify == "required" or contract.get("precision") == "exact":
            return True
    for key in ["role", "renderer_id", "layout_family", "visual_recipe"]:
        value = slide.get(key)
        if isinstance(value, str) and any(token in value.lower() for token in ["chart", "graph", "plot"]):
            if isinstance(contract, dict) and contract.get("verify") == "optional":
                return False
    return False


def chart_data_present(slide: dict[str, Any]) -> bool:
    contract = slide.get("chart_contract")
    if not isinstance(contract, dict):
        return False
    for key in ["data", "series", "values", "source_data", "labels"]:
        value = contract.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, dict) and value:
            return True
    return False


def run_chart_verify(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan_file = project / PLAN_PATH
    if not plan_file.exists():
        raise ChartVerifyError(f"missing required plan file: {PLAN_PATH.as_posix()}")
    plan = read_json_object(plan_file)
    slides = plan.get("slides") if isinstance(plan.get("slides"), list) else []
    svgs = prepared_svg_files(project)
    issues: list[dict[str, Any]] = []
    verified_pages: list[dict[str, Any]] = []
    for index, raw_slide in enumerate(slides, 1):
        if not isinstance(raw_slide, dict) or not chart_verify_required(raw_slide):
            continue
        page = raw_slide.get("page") if isinstance(raw_slide.get("page"), int) else index
        svg_path = svgs[index - 1] if index - 1 < len(svgs) else None
        page_issues: list[dict[str, Any]] = []
        if not chart_data_present(raw_slide):
            page_issues.append(issue("chart_contract_data_missing", "required chart verification needs chart_contract data/series/labels", page=page))
        if svg_path is None:
            page_issues.append(issue("chart_svg_missing", "required chart page has no prepared SVG", page=page))
        else:
            raw_svg = svg_path.read_text(encoding="utf-8")
            if not CHART_MARK_RE.search(raw_svg):
                page_issues.append(issue("chart_marks_missing", "prepared SVG does not contain chart-like marks", page=page, path=relpath(svg_path, project)))
        issues.extend(page_issues)
        verified_pages.append(
            {
                "page": page,
                "status": "failed" if page_issues else "passed",
                "svg": relpath(svg_path, project) if svg_path else None,
                "issue_count": len(page_issues),
            }
        )
    status = "failed" if issues else "passed"
    result: dict[str, Any] = {
        "schema_version": "svglide-chart-verify/v1",
        "status": status,
        "action": PASS_ACTION if status == "passed" else FAIL_ACTION,
        "project": str(project),
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": file_sha256(plan_file),
            "svg_dir": PREPARED_SVG_DIR.as_posix(),
        },
        "prepared_files": prepared_file_hashes(project),
        "pages": verified_pages,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "required_chart_count": len(verified_pages),
        },
        "issues": issues,
    }
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-chart-verify.schema.json"))
    schema_issues = svglide_schema.validate_json_schema(result, schema)
    if schema_issues:
        result["status"] = "failed"
        result["action"] = FAIL_ACTION
        result["issues"].extend(issue(item["code"], item["message"], path=item["path"]) for item in schema_issues)
        result["summary"]["error_count"] = len(result["issues"])
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify page-level chart contracts for SVGlide.")
    parser.add_argument("project")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_chart_verify(Path(args.project))
    except (OSError, ChartVerifyError) as error:
        print(f"svglide_chart_verify: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
