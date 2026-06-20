#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLAN_PATH = Path("02-plan/slide_plan.json")
LOCK_PATH = Path("02-plan/svglide.lock.json")
SOURCE_RECEIPT_PATH = Path("source/source-receipt.json")
ASSETS_DIR = Path("03-assets")
ASSETS_JSON = ASSETS_DIR / "assets.json"
ASSET_MANIFEST = ASSETS_DIR / "asset-manifest.json"
RAW_ASSETS_DIR = ASSETS_DIR / "raw"
PROCESSED_ASSETS_DIR = ASSETS_DIR / "processed"
IMAGE_JOBS = ASSETS_DIR / "image-jobs.json"
RECEIPT_PATH = Path("receipts/assets.json")
NETWORK_POLICIES = {"auto", "online", "offline", "fixture"}
IMAGE_BACKENDS = {"auto", "openai", "gemini", "qwen", "flux", "stage_command", "none"}


class AssetsError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_network_policy(value: str | None) -> str:
    policy = (value or "offline").strip().lower()
    if policy not in NETWORK_POLICIES:
        raise AssetsError(f"unsupported network policy: {value}")
    return policy


def normalize_image_backend(value: str | None) -> str:
    backend = (value or "none").strip().lower()
    if backend not in IMAGE_BACKENDS:
        raise AssetsError(f"unsupported image backend: {value}")
    return backend


def online_enabled(policy: str) -> bool:
    return policy in {"auto", "online"}


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


def optional_sha256(path: Path | None) -> str | None:
    return file_sha256(path) if path and path.exists() and path.is_file() else None


def dominant_colors(path: Path, *, limit: int = 5) -> list[str]:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return []
    try:
        with Image.open(path) as image:
            image.thumbnail((96, 96))
            converted = image.convert("RGB")
            colors = converted.getcolors(maxcolors=96 * 96) or []
    except OSError:
        return []
    ranked = sorted(colors, key=lambda item: item[0], reverse=True)
    result: list[str] = []
    for _count, color in ranked:
        hex_color = "#{:02X}{:02X}{:02X}".format(*color)
        if hex_color not in result:
            result.append(hex_color)
        if len(result) >= limit:
            break
    return result


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


def placement_role(contract: dict[str, Any]) -> str:
    raw = contract.get("placement_role") or contract.get("role") or contract.get("usage")
    if isinstance(raw, str) and raw:
        lowered = raw.lower()
        if lowered in {"cover", "background", "section", "closing", "body_visual", "inline_figure"}:
            return lowered
    page = contract.get("usage_page") or contract.get("page")
    if page == 1:
        return "cover"
    return "body_visual"


def image_query(contract: dict[str, Any]) -> str:
    for key in ["query", "suggested_query", "search_query", "purpose", "alt", "id"]:
        value = contract.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "presentation visual evidence"


def safe_asset_id(value: Any, index: int) -> str:
    raw = str(value or f"asset-{index:03d}").strip().lower()
    safe = "".join(ch if ch.isalnum() else "-" for ch in raw).strip("-")
    return safe or f"asset-{index:03d}"


def extension_from_url(url: str, content_type: str | None = None) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return suffix
    guessed = mimetypes.guess_extension(content_type or "")
    if guessed in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return guessed
    return ".jpg"


def http_get(url: str, *, timeout: float = 10.0) -> tuple[bytes, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "SVGlide/online-first"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("content-type")


def http_json(url: str, *, timeout: float = 10.0) -> Any:
    body, _content_type = http_get(url, timeout=timeout)
    return json.loads(body.decode("utf-8"))


def openverse_candidate(query: str) -> dict[str, Any] | None:
    params = urllib.parse.urlencode({"q": query, "page_size": "5"})
    payload = http_json(f"https://api.openverse.org/v1/images/?{params}")
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return None
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("thumbnail")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return {
                "url": url,
                "source_url": item.get("foreign_landing_url") or url,
                "license": item.get("license") or "preview_unverified",
                "title": item.get("title") or query,
                "provider": "openverse",
            }
    return None


def save_download(project: Path, *, asset_id: str, url: str) -> Path:
    body, content_type = http_get(url)
    target_dir = project / RAW_ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{asset_id}{extension_from_url(url, content_type)}"
    target.write_bytes(body)
    return target


def build_image_job(contract: dict[str, Any], *, asset_id: str, backend: str) -> dict[str, Any]:
    role = placement_role(contract)
    query = image_query(contract)
    prompt = contract.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        prompt = (
            f"Editorial 16:9 presentation image for {query}, role {role}, professional visual style, "
            "large negative space for editable text overlay, no readable text, no watermark, no logos."
        )
    return {
        "id": asset_id,
        "page": contract.get("usage_page") or contract.get("page"),
        "placement_role": role,
        "backend": backend,
        "prompt": prompt,
        "negative_prompt": "text, watermark, logo, fake numbers, low quality, distorted subject",
        "size": "1792x1024",
        "requires_image_input": False,
        "status": "planned",
    }


def acquire_contract_asset(
    project: Path,
    contract: dict[str, Any],
    *,
    index: int,
    policy: str,
    provider: str,
    no_image_search: bool,
    no_ai_image: bool,
    image_backend: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    asset_id = safe_asset_id(contract.get("id"), index)
    role = placement_role(contract)
    query = image_query(contract)
    href = contract.get("href") or contract.get("path")
    base = {
        "asset_id": asset_id,
        "page": contract.get("usage_page") or contract.get("page"),
        "placement_role": role,
        "asset_kind": "unknown",
        "query": query,
        "provider": provider,
        "license": contract.get("license") if isinstance(contract.get("license"), str) else None,
        "retrieved_at": None,
        "safe_text_zones": contract.get("safe_text_zones") if isinstance(contract.get("safe_text_zones"), list) else [],
        "crop_hint": contract.get("crop_hint") if isinstance(contract.get("crop_hint"), str) else None,
        "source_url": contract.get("source_url") if isinstance(contract.get("source_url"), str) else None,
        "file": None,
        "sha256": None,
        "fallback_reason": None,
    }
    if isinstance(href, str):
        local = local_asset_path(project, href)
        if local is not None and local.exists() and local.is_file():
            base.update({"asset_kind": "user_file", "file": relpath(local, project), "sha256": file_sha256(local), "status": "local_file"})
            colors = dominant_colors(local)
            if colors:
                base["dominant_colors"] = colors
            return base, None
        if href.startswith(("http://", "https://")) and online_enabled(policy) and not no_image_search:
            try:
                downloaded = save_download(project, asset_id=asset_id, url=href)
                base.update(
                    {
                        "asset_kind": "web_image",
                        "file": relpath(downloaded, project),
                        "sha256": file_sha256(downloaded),
                        "source_url": href,
                        "license": base["license"] or "preview_unverified",
                        "retrieved_at": now_iso(),
                        "status": "acquired",
                        "safe_text_zones": base["safe_text_zones"] or [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                )
                colors = dominant_colors(downloaded)
                if colors:
                    base["dominant_colors"] = colors
                return base, None
            except (OSError, urllib.error.URLError, TimeoutError) as error:
                base["fallback_reason"] = f"download_failed: {error}"
    if policy == "fixture":
        base.update({"asset_kind": "svg_fallback", "status": "fallback_used", "fallback_reason": "network_policy=fixture"})
    elif not online_enabled(policy) or no_image_search:
        base.update({"asset_kind": "svg_fallback", "status": "fallback_used", "fallback_reason": "image_search_disabled_or_offline"})
    else:
        try:
            candidate = openverse_candidate(query)
            if candidate:
                downloaded = save_download(project, asset_id=asset_id, url=str(candidate["url"]))
                base.update(
                    {
                        "asset_kind": "web_image",
                        "file": relpath(downloaded, project),
                        "sha256": file_sha256(downloaded),
                        "source_url": candidate.get("source_url"),
                        "license": candidate.get("license") or "preview_unverified",
                        "retrieved_at": now_iso(),
                        "status": "acquired",
                        "safe_text_zones": base["safe_text_zones"] or [{"x": 0.05, "y": 0.12, "w": 0.42, "h": 0.72}],
                    }
                )
                colors = dominant_colors(downloaded)
                if colors:
                    base["dominant_colors"] = colors
                return base, None
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            base["fallback_reason"] = f"image_search_failed: {error}"
        base.update({"asset_kind": "svg_fallback", "status": "fallback_used", "fallback_reason": base["fallback_reason"] or "no_candidate"})
    job = None if no_ai_image or image_backend == "none" else build_image_job(contract, asset_id=asset_id, backend=image_backend)
    if job:
        base["asset_kind"] = "ai_image"
        base["status"] = "planned"
    return base, job


def write_image_jobs(project: Path, jobs: list[dict[str, Any]], *, backend: str) -> None:
    payload = {
        "schema_version": "svglide-image-jobs/v1",
        "backend": backend,
        "generated_at": now_iso(),
        "jobs": jobs,
    }
    path = project / IMAGE_JOBS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def run_assets(
    project: Path,
    *,
    network_policy: str = "offline",
    asset_provider: str = "auto",
    image_backend: str = "none",
    no_image_search: bool = False,
    no_ai_image: bool = False,
    refresh_online: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    started_at = now_iso()
    policy = normalize_network_policy(network_policy)
    backend = normalize_image_backend(image_backend)
    plan = read_json_object(project / PLAN_PATH)
    lock = read_json_object(project / LOCK_PATH, required=False)
    assets = normalize_assets_json(project)
    contracts = collect_asset_contracts(plan, lock)
    evaluated = [evaluate_contract(project, contract, assets) for contract in contracts]
    acquired: list[dict[str, Any]] = []
    image_jobs: list[dict[str, Any]] = []
    for index, contract in enumerate(contracts, 1):
        item, job = acquire_contract_asset(
            project,
            contract,
            index=index,
            policy=policy,
            provider=asset_provider,
            no_image_search=no_image_search,
            no_ai_image=no_ai_image,
            image_backend=backend,
        )
        acquired.append(item)
        if job:
            image_jobs.append(job)
    write_image_jobs(project, image_jobs, backend=backend)
    palette_candidates: list[str] = []
    for item in acquired:
        for color in item.get("dominant_colors") if isinstance(item.get("dominant_colors"), list) else []:
            if isinstance(color, str) and color not in palette_candidates:
                palette_candidates.append(color)
    evaluated_by_id = {str(item.get("id")): item for item in evaluated}
    for item in acquired:
        evaluated_item = evaluated_by_id.get(str(item.get("asset_id")))
        if isinstance(evaluated_item, dict):
            evaluated_item.update({key: value for key, value in item.items() if value is not None})
            if item.get("status") == "acquired":
                evaluated_item["status"] = "acquired"
                evaluated_item["issues"] = []
    issues = [issue for item in evaluated for issue in item["issues"]]
    status = "failed" if issues else "passed"
    manifest = {
        "version": "svglide-assets/v1",
        "status": status,
        "network_policy": policy,
        "asset_provider": asset_provider,
        "image_backend": backend,
        "plan_path": PLAN_PATH.as_posix(),
        "plan_sha256": file_sha256(project / PLAN_PATH),
        "lock_path": LOCK_PATH.as_posix() if (project / LOCK_PATH).exists() else None,
        "lock_sha256": file_sha256(project / LOCK_PATH) if (project / LOCK_PATH).exists() else None,
        "source_receipt_path": SOURCE_RECEIPT_PATH.as_posix() if (project / SOURCE_RECEIPT_PATH).exists() else None,
        "source_receipt_sha256": file_sha256(project / SOURCE_RECEIPT_PATH) if (project / SOURCE_RECEIPT_PATH).exists() else None,
        "assets_json": ASSETS_JSON.as_posix(),
        "assets_json_sha256": file_sha256(project / ASSETS_JSON),
        "image_jobs": IMAGE_JOBS.as_posix(),
        "image_jobs_sha256": optional_sha256(project / IMAGE_JOBS),
        "contracts": evaluated,
        "acquired_assets": acquired,
        "visual_identity_palette_candidates": palette_candidates[:8],
        "summary": {
            "contract_count": len(evaluated),
            "error_count": len(issues),
            "mapped_token_count": sum(1 for item in evaluated if item["status"] == "mapped_token"),
            "local_file_count": sum(1 for item in evaluated if item["status"] == "local_file"),
            "acquired_count": sum(1 for item in acquired if item.get("status") == "acquired"),
            "fallback_count": sum(1 for item in acquired if item.get("status") == "fallback_used"),
            "image_job_count": len(image_jobs),
        },
        "issues": issues,
    }
    write_json(project / ASSET_MANIFEST, manifest)
    receipt = {
        "stage": "assets",
        "status": status,
        "started_at": started_at,
        "ended_at": now_iso(),
        "network_policy": policy,
        "asset_provider": asset_provider,
        "image_backend": backend,
        "inputs": [PLAN_PATH.as_posix()] + ([LOCK_PATH.as_posix()] if (project / LOCK_PATH).exists() else []),
        "outputs": [ASSETS_JSON.as_posix(), ASSET_MANIFEST.as_posix(), IMAGE_JOBS.as_posix()],
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
    parser.add_argument("--network-policy", default="offline", choices=sorted(NETWORK_POLICIES))
    parser.add_argument("--asset-provider", default="auto")
    parser.add_argument("--image-backend", default="none", choices=sorted(IMAGE_BACKENDS))
    parser.add_argument("--no-image-search", action="store_true")
    parser.add_argument("--no-ai-image", action="store_true")
    parser.add_argument("--refresh-online", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        receipt = run_assets(
            Path(args.project),
            network_policy=args.network_policy,
            asset_provider=args.asset_provider,
            image_backend=args.image_backend,
            no_image_search=args.no_image_search,
            no_ai_image=args.no_ai_image,
            refresh_online=args.refresh_online,
        )
    except (OSError, AssetsError) as error:
        print(f"svglide_assets: error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
