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


SOURCE_DIR = Path("source")
SOURCE_NOTES = SOURCE_DIR / "source-notes.md"
EVIDENCE_PATH = SOURCE_DIR / "evidence.json"
SOURCE_RECEIPT = SOURCE_DIR / "source-receipt.json"
RECEIPT_PATH = Path("receipts/source.json")
MIN_READY_ITEMS = 3
MIN_EVIDENCE_TEXT_CHARS = 20


class SourceError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def optional_sha256(path: Path) -> str | None:
    return file_sha256(path) if path.exists() else None


def issue(code: str, message: str, *, path: str | None = None) -> dict[str, str]:
    payload = {"code": code, "message": message}
    if path:
        payload["path"] = path
    return payload


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceError(f"invalid JSON in {path}: expected object")
    return payload


def normalize_note_line(line: str) -> str:
    line = re.sub(r"^\s{0,3}[-*+]\s+", "", line.strip())
    line = re.sub(r"^\s*\d+[.)]\s+", "", line)
    return line.strip()


def evidence_from_notes(notes: str) -> dict[str, Any]:
    lines = []
    for raw in notes.splitlines():
        line = normalize_note_line(raw)
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    items = [
        {
            "id": f"item-{index:03d}",
            "text": line,
            "source": SOURCE_NOTES.as_posix(),
        }
        for index, line in enumerate(lines, 1)
    ]
    ready_items = sum(1 for item in items if len(item["text"]) >= MIN_EVIDENCE_TEXT_CHARS)
    source_status = "ready" if ready_items >= MIN_READY_ITEMS and ready_items == len(items) else "thin"
    return {
        "schema_version": "svglide-evidence/v1",
        "source_status": source_status,
        "items": items,
        "generated_from": SOURCE_NOTES.as_posix(),
    }


def load_or_build_evidence(project: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]], bool]:
    evidence_file = project / EVIDENCE_PATH
    notes_file = project / SOURCE_NOTES
    if evidence_file.exists():
        return read_json_object(evidence_file), [], False
    if notes_file.exists():
        evidence = evidence_from_notes(notes_file.read_text(encoding="utf-8"))
        evidence_file.parent.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return evidence, [], True
    return None, [issue("source_input_missing", "source/evidence.json or source/source-notes.md is required")], False


def evidence_issues(evidence: dict[str, Any] | None) -> list[dict[str, str]]:
    if evidence is None:
        return []
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-evidence.schema.json"))
    issues = [
        issue(item["code"], item["message"], path=item["path"])
        for item in svglide_schema.validate_json_schema(evidence, schema)
    ]
    if evidence.get("source_status") != "ready":
        issues.append(issue("source_status_not_ready", "source_status must be ready before planning/generation"))
    items = evidence.get("items")
    if not isinstance(items, list):
        return issues
    if len(items) < MIN_READY_ITEMS:
        issues.append(issue("source_item_count_too_low", f"evidence requires at least {MIN_READY_ITEMS} items"))
    seen: set[str] = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if isinstance(raw_id, str):
            if raw_id in seen:
                issues.append(issue("source_item_id_duplicate", f"duplicate evidence id: {raw_id}"))
            seen.add(raw_id)
        text = item.get("text")
        if not isinstance(text, str) or len(text.strip()) < MIN_EVIDENCE_TEXT_CHARS:
            issues.append(issue("source_item_text_too_short", f"evidence item {index} text is too short"))
    return issues


def validate_source_receipt(receipt: dict[str, Any]) -> list[dict[str, str]]:
    schema = svglide_schema.read_json(svglide_schema.schema_path("svglide-source-receipt.schema.json"))
    return [
        issue(item["code"], item["message"], path=item["path"])
        for item in svglide_schema.validate_json_schema(receipt, schema)
    ]


def run_source(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    evidence, issues, generated = load_or_build_evidence(project)
    issues.extend(evidence_issues(evidence))
    item_count = len(evidence.get("items", [])) if isinstance(evidence, dict) and isinstance(evidence.get("items"), list) else 0
    status = "failed" if issues else "passed"
    receipt: dict[str, Any] = {
        "schema_version": "svglide-source-receipt/v1",
        "stage": "source",
        "status": status,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": {
            "source_notes": SOURCE_NOTES.as_posix() if (project / SOURCE_NOTES).exists() else None,
            "source_notes_sha256": optional_sha256(project / SOURCE_NOTES),
            "evidence": EVIDENCE_PATH.as_posix() if (project / EVIDENCE_PATH).exists() else None,
            "evidence_sha256": optional_sha256(project / EVIDENCE_PATH),
        },
        "outputs": {
            "evidence": EVIDENCE_PATH.as_posix() if (project / EVIDENCE_PATH).exists() else None,
            "source_receipt": SOURCE_RECEIPT.as_posix(),
        },
        "generated_evidence_from_notes": generated,
        "source_status": evidence.get("source_status") if isinstance(evidence, dict) else None,
        "summary": {"error_count": len(issues), "evidence_item_count": item_count},
        "issues": issues,
    }
    schema_issues = validate_source_receipt(receipt)
    if schema_issues:
        receipt["status"] = "failed"
        receipt["issues"].extend(schema_issues)
        receipt["summary"]["error_count"] = len(receipt["issues"])
    for path in [project / SOURCE_RECEIPT, project / RECEIPT_PATH]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize and validate SVGlide source evidence.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_source(Path(args.project))
    except (OSError, SourceError) as error:
        print(f"svglide_source: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
