#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import svglide_satori_text_style_manifest


SVG_IMAGE_TAG_RE = re.compile(r"<image\b[^>]*>", re.IGNORECASE | re.DOTALL)
SVG_IMAGE_HREF_RE = re.compile(r"""(?:^|\s)(?:xlink:href|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
CONTRACT_MANIFEST = Path("04-svg/contract/manifest.json")
GENERATOR_RECEIPT = Path("receipts/generate_svg.json")


class PrepareError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_assets(project: Path) -> dict[str, str]:
    assets_path = project / "03-assets" / "assets.json"
    if not assets_path.exists():
        return {}
    try:
        data = json.loads(assets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrepareError(f"invalid assets json: {assets_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PrepareError(f"invalid assets json: {assets_path}: expected object")
    out: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise PrepareError(f"invalid assets json: {assets_path}: keys and values must be strings")
        out[key] = value
    return out


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PrepareError(f"invalid {label} json: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PrepareError(f"invalid {label} json: {path}: expected object")
    return data


def generation_mode(project: Path) -> str | None:
    path = project / GENERATOR_RECEIPT
    if not path.exists():
        return None
    data = read_json_object(path, "generator receipt")
    raw = data.get("generation_mode")
    return raw if isinstance(raw, str) else None


def source_svg_files(project: Path) -> list[Path]:
    svg_dir = project / "04-svg"
    if not svg_dir.exists():
        raise PrepareError(f"missing svg directory: {svg_dir}")
    files = sorted(path for path in svg_dir.glob("*.svg") if path.is_file())
    if not files:
        raise PrepareError(f"no source SVG files found in {svg_dir}")
    return files


def validate_contract_manifest(project: Path, sources: list[Path]) -> dict[str, Any] | None:
    manifest_path = project / CONTRACT_MANIFEST
    mode = generation_mode(project)
    if not manifest_path.exists():
        if mode == "artboard_satori":
            raise PrepareError(f"missing contract manifest for artboard_satori generation: {manifest_path}")
        return None

    manifest = read_json_object(manifest_path, "contract manifest")
    if manifest.get("status") == "failed":
        raise PrepareError(f"contract manifest status is failed: {manifest_path}")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise PrepareError(f"contract manifest has no pages: {manifest_path}")

    source_hashes = {str(path.relative_to(project)): file_sha256(path) for path in sources}
    manifest_outputs: set[str] = set()
    page_summaries: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise PrepareError(f"contract manifest page must be an object: {manifest_path}")
        if page.get("status") == "failed":
            raise PrepareError(f"contract manifest page status is failed: {page.get('page')}")
        output = page.get("output")
        output_sha256 = page.get("output_sha256")
        report = page.get("report")
        if not isinstance(output, str) or not output:
            raise PrepareError("contract manifest page is missing output")
        if not isinstance(output_sha256, str) or not output_sha256:
            raise PrepareError(f"contract manifest page output_sha256 is missing: {output}")
        if output not in source_hashes:
            raise PrepareError(f"contract manifest output is not a prepared source SVG: {output}")
        if source_hashes[output] != output_sha256:
            raise PrepareError(f"contract manifest output hash is stale: {output}")
        if not isinstance(report, str) or not (project / report).exists():
            raise PrepareError(f"contract manifest report is missing: {report}")
        report_payload = read_json_object(project / report, "contract report")
        if report_payload.get("status") == "failed":
            raise PrepareError(f"contract report status is failed: {report}")
        if report_payload.get("output") != output or report_payload.get("output_sha256") != output_sha256:
            raise PrepareError(f"contract report output does not match manifest: {report}")
        manifest_outputs.add(output)
        page_summaries.append({"page": page.get("page"), "output": output, "status": page.get("status"), "report": report})

    missing = sorted(set(source_hashes) - manifest_outputs)
    extra = sorted(manifest_outputs - set(source_hashes))
    if missing or extra:
        raise PrepareError(f"contract manifest outputs do not match source SVG files: missing={missing}, extra={extra}")

    return {
        "path": CONTRACT_MANIFEST.as_posix(),
        "sha256": file_sha256(manifest_path),
        "status": manifest.get("status"),
        "pages": page_summaries,
    }


def image_hrefs(svg_text: str) -> list[str]:
    hrefs: list[str] = []
    for tag in SVG_IMAGE_TAG_RE.findall(svg_text):
        match = SVG_IMAGE_HREF_RE.search(tag)
        if match:
            hrefs.append(match.group(1))
    return hrefs


def local_asset_path(project: Path, href: str) -> Path:
    if href.startswith("@./"):
        rel = href[3:]
    elif href.startswith("@/"):
        rel = href[2:]
    else:
        raise PrepareError(f"not a local SVGlide asset placeholder: {href}")
    candidate = (project / rel).resolve()
    project_root = project.resolve()
    if candidate != project_root and project_root not in candidate.parents:
        raise PrepareError(f"asset path escapes project root: {href}")
    return candidate


def validate_asset_refs(project: Path, svg_file: Path, svg_text: str, assets: dict[str, str]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for href in image_hrefs(svg_text):
        if not href.startswith("@"):
            continue
        if href in assets:
            refs.append({"href": href, "status": "mapped", "token": assets[href]})
            continue
        path = local_asset_path(project, href)
        if not path.exists() or not path.is_file():
            raise PrepareError(f"{svg_file}: unresolved image placeholder {href}; add file or map it in 03-assets/assets.json")
        refs.append({"href": href, "status": "local", "path": str(path.relative_to(project))})
    return refs


def prepare_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    assets = load_assets(project)
    sources = source_svg_files(project)
    contract_manifest = validate_contract_manifest(project, sources)
    prepared_dir = project / "04-svg" / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir = project / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    prepared_files: list[dict[str, Any]] = []
    asset_refs: list[dict[str, Any]] = []
    text_style_manifest_count = 0
    text_style_manifest_bound_count = 0
    text_style_manifest_loss_count = 0
    text_style_manifest_losses: list[dict[str, Any]] = []
    should_inject_text_style_manifest = generation_mode(project) == "artboard_satori"
    for source in sources:
        svg_text = source.read_text(encoding="utf-8")
        refs = validate_asset_refs(project, source, svg_text, assets)
        target = prepared_dir / source.name
        if should_inject_text_style_manifest:
            manifest_result = svglide_satori_text_style_manifest.inject_text_style_manifest(svg_text)
            target.write_text(manifest_result.svg_text, encoding="utf-8")
            text_style_manifest_count += manifest_result.item_count
            text_style_manifest_bound_count += manifest_result.bound_count
            text_style_manifest_loss_count += manifest_result.loss_count
            text_style_manifest_losses.extend(manifest_result.losses)
        else:
            shutil.copyfile(source, target)
        prepared_files.append(
            {
                "source": str(source.relative_to(project)),
                "prepared": str(target.relative_to(project)),
                "sha256": file_sha256(target),
            }
        )
        if refs:
            asset_refs.append({"source": str(source.relative_to(project)), "refs": refs})

    receipt: dict[str, Any] = {
        "stage": "prepare",
        "status": "passed",
        "started_at": started_at,
        "ended_at": now_iso(),
        "source_files": [item["source"] for item in prepared_files],
        "prepared_files": prepared_files,
        "assets_json": "03-assets/assets.json" if (project / "03-assets" / "assets.json").exists() else None,
        "contract_manifest": contract_manifest,
        "asset_refs": asset_refs,
        "normalizations": [],
        "text_style_manifest_count": text_style_manifest_count,
        "text_style_manifest_bound_count": text_style_manifest_bound_count,
        "text_style_manifest_loss_count": text_style_manifest_loss_count,
        "text_style_manifest": {
            "item_count": text_style_manifest_count,
            "bound_count": text_style_manifest_bound_count,
            "loss_count": text_style_manifest_loss_count,
            "losses": text_style_manifest_losses,
        },
    }
    receipt_path = receipts_dir / "prepare.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare SVGlide SVG files for CLI create-svg consumption.")
    parser.add_argument("project", help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        receipt = prepare_project(Path(args.project))
    except PrepareError as exc:
        print(f"svglide_prepare: error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
