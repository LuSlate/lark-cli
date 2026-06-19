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


SVG_IMAGE_TAG_RE = re.compile(r"<image\b[^>]*>", re.IGNORECASE | re.DOTALL)
SVG_IMAGE_HREF_RE = re.compile(r"""(?:^|\s)(?:xlink:href|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


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


def source_svg_files(project: Path) -> list[Path]:
    svg_dir = project / "04-svg"
    if not svg_dir.exists():
        raise PrepareError(f"missing svg directory: {svg_dir}")
    files = sorted(path for path in svg_dir.glob("*.svg") if path.is_file())
    if not files:
        raise PrepareError(f"no source SVG files found in {svg_dir}")
    return files


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
    prepared_dir = project / "04-svg" / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    receipts_dir = project / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    prepared_files: list[dict[str, Any]] = []
    asset_refs: list[dict[str, Any]] = []
    for source in sources:
        svg_text = source.read_text(encoding="utf-8")
        refs = validate_asset_refs(project, source, svg_text, assets)
        target = prepared_dir / source.name
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
        "asset_refs": asset_refs,
        "normalizations": [],
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
