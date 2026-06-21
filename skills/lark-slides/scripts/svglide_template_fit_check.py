#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


PLAN_PATH = Path("02-plan/slide_plan.json")
GENERATOR_RECEIPT = Path("receipts/generate_svg.json")
OUTPUT_PATH = Path("06-check/template-fit.json")
RECEIPT_PATH = Path("receipts/template-fit-check.json")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def issue(code: str, message: str, *, page: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if page is not None:
        payload["page"] = page
    return payload


def text_height_ok(node: dict[str, Any]) -> bool:
    height = node.get("height")
    kind = node.get("kind")
    if kind != "text":
        return True
    return isinstance(height, (int, float)) and height >= 24


def node_in_canvas(node: dict[str, Any]) -> bool:
    x = node.get("x")
    y = node.get("y")
    width = node.get("width")
    height = node.get("height")
    if not all(isinstance(value, (int, float)) for value in [x, y, width, height]):
        return False
    return x >= 0 and y >= 0 and width > 0 and height > 0 and x + width <= 960 and y + height <= 540


def run_template_fit(project: Path) -> dict[str, Any]:
    project = project.resolve()
    plan = read_json(project / PLAN_PATH)
    generator = read_json(project / GENERATOR_RECEIPT)
    artboard_receipts = generator.get("artboard_receipts")
    issues: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    registry_hashes: dict[str, Any] = {}
    if not isinstance(artboard_receipts, list) or not artboard_receipts:
        issues.append(issue("artboard_receipts_missing", "generator receipt must include artboard_receipts"))
        artboard_receipts = []
    for item in artboard_receipts:
        if not isinstance(item, str) or not (project / item).exists():
            issues.append(issue("artboard_receipt_missing", f"missing artboard receipt: {item}"))
            continue
        receipt = read_json(project / item)
        if not registry_hashes:
            registry_hashes = {
                "template_registry": receipt.get("template_registry"),
                "template_registry_sha256": receipt.get("template_registry_sha256"),
                "theme_registry": receipt.get("theme_registry"),
                "theme_registry_sha256": receipt.get("theme_registry_sha256"),
                "theme_files": receipt.get("theme_files"),
            }
        page = receipt.get("page") if isinstance(receipt.get("page"), int) else None
        node_layout = receipt.get("node_layout_map")
        if not isinstance(node_layout, str) or not (project / node_layout).exists():
            issues.append(issue("node_layout_map_missing", f"missing node layout map in {item}", page=page))
            continue
        layout = read_json(project / node_layout)
        nodes = layout.get("nodes") if isinstance(layout.get("nodes"), list) else []
        page_issues: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                page_issues.append(issue("node_invalid", "node layout entry must be an object", page=page))
                continue
            if not node_in_canvas(node):
                page_issues.append(issue("node_out_of_canvas", f"node is outside canvas: {node.get('id')}", page=page))
            if not text_height_ok(node):
                page_issues.append(issue("text_box_too_short", f"text node height is too short: {node.get('id')}", page=page))
        issues.extend(page_issues)
        pages.append(
            {
                "page": page,
                "artboard_receipt": item,
                "node_layout_map": node_layout,
                "node_layout_map_sha256": file_sha256(project / node_layout),
                "node_count": len(nodes),
                "error_count": len(page_issues),
            }
        )
    status = "failed" if issues else "passed"
    result = {
        "schema_version": "svglide-template-fit/v1",
        "stage": "template-fit-check",
        "status": status,
        "action": "create_live" if status == "passed" else "repair_and_rerun",
        "inputs": {
            "slide_plan": PLAN_PATH.as_posix(),
            "plan_sha256": file_sha256(project / PLAN_PATH),
            "generator_receipt": GENERATOR_RECEIPT.as_posix(),
            "generator_receipt_sha256": file_sha256(project / GENERATOR_RECEIPT),
            "artboard_receipts": artboard_receipts,
            **registry_hashes,
        },
        "pages": pages,
        "summary": {
            "error_count": len(issues),
            "warning_count": 0,
            "page_count": len(pages),
        },
        "issues": issues,
        "output_path": OUTPUT_PATH.as_posix(),
        "receipt_path": RECEIPT_PATH.as_posix(),
    }
    output = project / OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = project / RECEIPT_PATH
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CanvasSpec template layout fit.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_template_fit(args.project)
    except (OSError, json.JSONDecodeError) as error:
        print(f"svglide_template_fit_check: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
