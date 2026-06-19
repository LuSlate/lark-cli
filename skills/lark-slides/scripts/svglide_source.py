#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_schema


SOURCE_DIR = Path("source")
SOURCE_NOTES = SOURCE_DIR / "source-notes.md"
EVIDENCE_PATH = SOURCE_DIR / "evidence.json"
RESEARCH_QUERIES = SOURCE_DIR / "research_queries.json"
RESEARCH_MD = SOURCE_DIR / "research.md"
SOURCE_RECEIPT = SOURCE_DIR / "source-receipt.json"
RECEIPT_PATH = Path("receipts/source.json")
PROJECT_MANIFEST = Path("01-project/project_manifest.json")
MIN_READY_ITEMS = 3
MIN_EVIDENCE_TEXT_CHARS = 20
NETWORK_POLICIES = {"auto", "online", "offline", "fixture"}


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


def normalize_network_policy(value: str | None) -> str:
    policy = (value or "offline").strip().lower()
    if policy not in NETWORK_POLICIES:
        raise SourceError(f"unsupported network policy: {value}")
    return policy


def network_allows_research(policy: str, no_online_research: bool) -> bool:
    return policy in {"auto", "online"} and not no_online_research


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceError(f"invalid JSON in {path}: expected object")
    return payload


def read_json_object_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json_object(path)


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


def project_title(project: Path) -> str:
    manifest = read_json_object_optional(project / PROJECT_MANIFEST)
    raw = manifest.get("title") or manifest.get("deck_id") or project.name
    return raw if isinstance(raw, str) and raw.strip() else project.name


def research_queries_for(project: Path) -> list[str]:
    title = project_title(project).strip()
    return [
        title,
        f"{title} 最新数据",
        f"{title} 背景 分析",
    ]


def write_research_queries(project: Path, queries: list[str], *, policy: str) -> None:
    payload = {
        "schema_version": "svglide-research-queries/v1",
        "network_policy": policy,
        "queries": queries,
        "generated_at": now_iso(),
    }
    path = project / RESEARCH_QUERIES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture_evidence(project: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    title = project_title(project)
    source = {
        "id": "fixture-src-001",
        "title": f"{title} fixture source",
        "url": "fixture://svglide/source",
        "source_type": "fixture",
        "credibility": "fixture",
        "retrieved_at": now_iso(),
    }
    items = [
        {
            "id": f"item-{index:03d}",
            "text": text,
            "source": source["title"],
            "url": source["url"],
        }
        for index, text in enumerate(
            [
                f"{title} 的演示需要先说明背景、核心矛盾和受众最关心的问题。",
                f"{title} 的正文应使用结构化证据支撑，不直接把单薄主题扩写成泛泛介绍。",
                f"{title} 的视觉表达应优先使用可编辑组件，并用素材增强封面、证据和记忆点。",
            ],
            1,
        )
    ]
    evidence = {
        "schema_version": "svglide-evidence/v1",
        "source_status": "ready",
        "items": items,
        "generated_from": "fixture",
        "research_status": "fixture",
        "sources": [source],
    }
    claims = [
        {"claim": item["text"], "source_ids": [source["id"]], "confidence": "fixture", "used_for_pages": []}
        for item in items
    ]
    return evidence, [source], claims


def http_json(url: str, *, timeout: float = 8.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "SVGlide/online-first"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def acquire_wikipedia_sources(queries: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for query in queries[:2]:
        params = urllib.parse.urlencode(
            {
                "action": "opensearch",
                "search": query,
                "limit": "3",
                "namespace": "0",
                "format": "json",
            }
        )
        payload = http_json(f"https://en.wikipedia.org/w/api.php?{params}")
        if not isinstance(payload, list) or len(payload) < 4:
            continue
        titles = payload[1] if isinstance(payload[1], list) else []
        descriptions = payload[2] if isinstance(payload[2], list) else []
        urls = payload[3] if isinstance(payload[3], list) else []
        for index, raw_url in enumerate(urls):
            if not isinstance(raw_url, str) or raw_url in seen_urls:
                continue
            title = titles[index] if index < len(titles) and isinstance(titles[index], str) else raw_url
            description = descriptions[index] if index < len(descriptions) and isinstance(descriptions[index], str) else ""
            text = description.strip() or f"{title} 是与 {query} 相关的公开百科来源，可作为初步背景资料。"
            if len(text) < MIN_EVIDENCE_TEXT_CHARS:
                text = f"{title} 是与 {query} 相关的公开资料来源，用于补充背景与上下文。"
            source_id = f"web-src-{len(sources) + 1:03d}"
            source = {
                "id": source_id,
                "url": raw_url,
                "title": title,
                "published_at": None,
                "retrieved_at": now_iso(),
                "source_type": "web",
                "credibility": "secondary",
            }
            sources.append(source)
            claims.append({"claim": text, "source_ids": [source_id], "confidence": "medium", "used_for_pages": []})
            seen_urls.add(raw_url)
            if len(sources) >= MIN_READY_ITEMS:
                return sources, claims
    return sources, claims


def evidence_from_sources(sources: list[dict[str, Any]], claims: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for index, claim in enumerate(claims, 1):
        source_id = claim.get("source_ids", [None])[0]
        source = next((item for item in sources if item.get("id") == source_id), {})
        items.append(
            {
                "id": f"item-{index:03d}",
                "text": str(claim.get("claim") or ""),
                "source": str(source.get("title") or source_id or "online source"),
                "url": str(source.get("url") or ""),
                "date": str(source.get("retrieved_at") or ""),
                "source_ids": claim.get("source_ids", []),
            }
        )
    return {
        "schema_version": "svglide-evidence/v1",
        "source_status": "ready" if len(items) >= MIN_READY_ITEMS else "thin",
        "items": items,
        "generated_from": "online_research",
        "research_status": "researched" if len(items) >= MIN_READY_ITEMS else "partial",
        "sources": sources,
        "claims": claims,
    }


def blocked_evidence(error: str) -> dict[str, Any]:
    return {
        "schema_version": "svglide-evidence/v1",
        "source_status": "blocked",
        "items": [
            {
                "id": "item-001",
                "text": f"在线资料获取失败，当前 evidence 仅记录阻断原因，不能用于正式生成：{error}",
                "source": "svglide_source",
            }
        ],
        "generated_from": "online_research",
        "research_status": "blocked_by_network",
    }


def write_research_markdown(project: Path, *, queries: list[str], sources: list[dict[str, Any]], claims: list[dict[str, Any]], status: str) -> None:
    lines = [
        "# Research",
        "",
        f"- status: {status}",
        f"- retrieved_at: {now_iso()}",
        "",
        "## Queries",
    ]
    lines.extend(f"- {query}" for query in queries)
    lines.extend(["", "## Sources"])
    if sources:
        for item in sources:
            lines.append(f"- [{item.get('title')}]({item.get('url')}) - {item.get('credibility')} - {item.get('retrieved_at')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Claims"])
    if claims:
        for item in claims:
            lines.append(f"- {item.get('claim')} (sources: {', '.join(item.get('source_ids') or [])})")
    else:
        lines.append("- none")
    path = project / RESEARCH_MD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_or_build_evidence(
    project: Path,
    *,
    network_policy: str,
    no_online_research: bool,
    refresh_online: bool,
) -> tuple[dict[str, Any] | None, list[dict[str, str]], bool, dict[str, Any]]:
    evidence_file = project / EVIDENCE_PATH
    notes_file = project / SOURCE_NOTES
    queries = research_queries_for(project)
    write_research_queries(project, queries, policy=network_policy)
    acquisition: dict[str, Any] = {
        "status": "reused_existing",
        "network_policy": network_policy,
        "queries": queries,
        "sources": [],
        "claims": [],
    }
    if evidence_file.exists() and not refresh_online:
        evidence = read_json_object(evidence_file)
        acquisition["status"] = evidence.get("research_status") or "reused_existing"
        acquisition["sources"] = evidence.get("sources") if isinstance(evidence.get("sources"), list) else []
        acquisition["claims"] = evidence.get("claims") if isinstance(evidence.get("claims"), list) else []
        return evidence, [], False, acquisition
    if notes_file.exists() and not refresh_online:
        evidence = evidence_from_notes(notes_file.read_text(encoding="utf-8"))
        evidence_file.parent.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        acquisition["status"] = "notes"
        return evidence, [], True, acquisition
    if network_policy == "fixture":
        evidence, sources, claims = fixture_evidence(project)
        evidence_file.parent.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_research_markdown(project, queries=queries, sources=sources, claims=claims, status="fixture")
        acquisition.update({"status": "fixture", "sources": sources, "claims": claims})
        return evidence, [], True, acquisition
    if not network_allows_research(network_policy, no_online_research):
        acquisition["status"] = "skipped_by_user" if network_policy == "offline" or no_online_research else "skipped"
        return None, [issue("source_input_missing", "source/evidence.json or source/source-notes.md is required")], False, acquisition
    try:
        sources, claims = acquire_wikipedia_sources(queries)
        evidence = evidence_from_sources(sources, claims)
        evidence_file.parent.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = evidence.get("research_status", "partial")
        write_research_markdown(project, queries=queries, sources=sources, claims=claims, status=str(status))
        acquisition.update({"status": status, "sources": sources, "claims": claims})
        return evidence, [], True, acquisition
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        evidence = blocked_evidence(str(error))
        evidence_file.parent.mkdir(parents=True, exist_ok=True)
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_research_markdown(project, queries=queries, sources=[], claims=[], status="blocked_by_network")
        acquisition.update({"status": "blocked_by_network", "error": str(error)})
        return evidence, [], True, acquisition


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


def run_source(
    project: Path,
    *,
    network_policy: str = "offline",
    no_online_research: bool = False,
    refresh_online: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    policy = normalize_network_policy(network_policy)
    evidence, issues, generated, acquisition = load_or_build_evidence(
        project,
        network_policy=policy,
        no_online_research=no_online_research,
        refresh_online=refresh_online,
    )
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
            "network_policy": policy,
            "no_online_research": no_online_research,
            "refresh_online": refresh_online,
        },
        "outputs": {
            "evidence": EVIDENCE_PATH.as_posix() if (project / EVIDENCE_PATH).exists() else None,
            "research_queries": RESEARCH_QUERIES.as_posix() if (project / RESEARCH_QUERIES).exists() else None,
            "research": RESEARCH_MD.as_posix() if (project / RESEARCH_MD).exists() else None,
            "source_receipt": SOURCE_RECEIPT.as_posix(),
        },
        "generated_evidence_from_notes": generated,
        "source_status": evidence.get("source_status") if isinstance(evidence, dict) else None,
        "research": acquisition,
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
    parser.add_argument("--network-policy", default="offline", choices=sorted(NETWORK_POLICIES))
    parser.add_argument("--no-online-research", action="store_true")
    parser.add_argument("--refresh-online", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_source(
            Path(args.project),
            network_policy=args.network_policy,
            no_online_research=args.no_online_research,
            refresh_online=args.refresh_online,
        )
    except (OSError, SourceError) as error:
        print(f"svglide_source: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
