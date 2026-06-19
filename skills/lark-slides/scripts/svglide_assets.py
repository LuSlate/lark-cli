#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLAN_PATH = Path("02-plan/slide_plan.json")
LOCK_PATH = Path("02-plan/svglide.lock.json")
SOURCE_RECEIPT_PATH = Path("source/source-receipt.json")
ASSETS_DIR = Path("03-assets")
ASSETS_JSON = ASSETS_DIR / "assets.json"
ASSET_MANIFEST = ASSETS_DIR / "asset-manifest.json"
RECEIPT_PATH = Path("receipts/assets.json")


class AssetsError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json_object(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise AssetsError(f"missing required file: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AssetsError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AssetsError(f"invalid JSON in {path}: expected object")
    return payload


def normalize_assets_json(project: Path) -> dict[str, str]:
    path = project / ASSETS_JSON
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        return {}
    data = read_json_object(path)
    normalized: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise AssetsError(f"{ASSETS_JSON}: keys and values must be strings")
        normalized[key] = value
    return normalized


def iter_contract_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return list(value.values())
    return []


def collect_asset_contracts(plan: dict[str, Any], lock: dict[str, Any]) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for source_name, source in [("plan", plan), ("lock", lock)]:
        for key in ["asset_contracts", "assets", "images"]:
            for index, raw in enumerate(iter_contract_values(source.get(key))):
                if isinstance(raw, str):
                    contracts.append({"source": source_name, "key": key, "id": raw, "href": raw, "required": True})
                elif isinstance(raw, dict):
                    item = dict(raw)
                    item.setdefault("source", source_name)
                    item.setdefault("key", key)
                    item.setdefault("id", item.get("name") or item.get("href") or item.get("path") or f"{key}-{index + 1}")
                    item.setdefault("required", True)
                    contracts.append(item)
    return contracts


def local_asset_path(project: Path, ref: str) -> Path | None:
    if ref.startswith("@./"):
        rel = ref[3:]
    elif ref.startswith("@/"):
        rel = ref[2:]
    else:
        return None
    candidate = (project / rel).resolve()
    root = project.resolve()
    if candidate != root and root not in candidate.parents:
        raise AssetsError(f"asset path escapes project root: {ref}")
    return candidate


def evaluate_contract(project: Path, contract: dict[str, Any], assets: dict[str, str]) -> dict[str, Any]:
    href = contract.get("href") or contract.get("placeholder") or contract.get("path")
    token = contract.get("token") or contract.get("file_token")
    required = bool(contract.get("required", True))
    status = "declared"
    issues: list[dict[str, str]] = []
    result = {
        "id": str(contract.get("id")),
        "source": str(contract.get("source", "unknown")),
        "href": href if isinstance(href, str) else None,
        "required": required,
        "status": status,
        "token": token if isinstance(token, str) else None,
        "issues": issues,
    }
    if not isinstance(href, str) or not href:
        result["status"] = "metadata_only"
        return result
    if href in assets:
        result["status"] = "mapped_token"
        result["token"] = assets[href]
        return result
    local_path = local_asset_path(project, href)
    if local_path is not None:
        result["path"] = relpath(local_path, project)
        if local_path.exists() and local_path.is_file():
            result["status"] = "local_file"
        elif required:
            result["status"] = "missing"
            issues.append({"code": "missing_local_asset", "message": f"asset file is missing: {href}"})
        else:
            result["status"] = "missing_optional"
        return result
    if href.startswith("http://") or href.startswith("https://") or href.startswith("data:"):
        result["status"] = "invalid_for_create_svg" if required else "preview_only"
        if required:
            issues.append({"code": "invalid_asset_href", "message": "create-svg inputs require local @ paths or file tokens"})
        return result
    result["status"] = "external_or_token"
    return result


def run_assets(project: Path) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    plan = read_json_object(project / PLAN_PATH)
    lock = read_json_object(project / LOCK_PATH, required=False)
    assets = normalize_assets_json(project)
    contracts = collect_asset_contracts(plan, lock)
    evaluated = [evaluate_contract(project, contract, assets) for contract in contracts]
    issues = [issue for item in evaluated for issue in item["issues"]]
    status = "failed" if issues else "passed"
    manifest = {
        "version": "svglide-assets/v1",
        "status": status,
        "plan_path": PLAN_PATH.as_posix(),
        "plan_sha256": file_sha256(project / PLAN_PATH),
        "lock_path": LOCK_PATH.as_posix() if (project / LOCK_PATH).exists() else None,
        "lock_sha256": file_sha256(project / LOCK_PATH) if (project / LOCK_PATH).exists() else None,
        "source_receipt_path": SOURCE_RECEIPT_PATH.as_posix() if (project / SOURCE_RECEIPT_PATH).exists() else None,
        "source_receipt_sha256": file_sha256(project / SOURCE_RECEIPT_PATH) if (project / SOURCE_RECEIPT_PATH).exists() else None,
        "assets_json": ASSETS_JSON.as_posix(),
        "assets_json_sha256": file_sha256(project / ASSETS_JSON),
        "contracts": evaluated,
        "summary": {
            "contract_count": len(evaluated),
            "error_count": len(issues),
            "mapped_token_count": sum(1 for item in evaluated if item["status"] == "mapped_token"),
            "local_file_count": sum(1 for item in evaluated if item["status"] == "local_file"),
        },
        "issues": issues,
    }
    write_json(project / ASSET_MANIFEST, manifest)
    receipt = {
        "stage": "assets",
        "status": status,
        "started_at": started_at,
        "ended_at": now_iso(),
        "inputs": [PLAN_PATH.as_posix()] + ([LOCK_PATH.as_posix()] if (project / LOCK_PATH).exists() else []),
        "outputs": [ASSETS_JSON.as_posix(), ASSET_MANIFEST.as_posix()],
        "manifest": manifest,
    }
    write_json(project / RECEIPT_PATH, receipt)
    return receipt


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate SVGlide asset contracts before SVG generation.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        receipt = run_assets(Path(args.project))
    except (OSError, AssetsError) as error:
        print(f"svglide_assets: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
