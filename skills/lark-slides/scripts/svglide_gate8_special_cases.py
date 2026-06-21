#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

import svglide_artboard_renderer as artboard
import svglide_asset_injector
import svglide_chart_verify
import svglide_prepare
import svglide_readback
import svg_preflight


SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = SCRIPT_DIR / "fixtures" / "svglide_artboard" / "gate8_special_cases"
OUTPUT_NAME = "gate8-special-cases.json"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class Gate8Error(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Gate8Error(f"expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_1X1)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relpath(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def xhtml_text(text: str, *, size: int = 24, color: str = "#F8FAFC") -> str:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div xmlns="http://www.w3.org/1999/xhtml" '
        f'style="font-family:Inter,Arial,sans-serif;font-size:{size}px;line-height:1.2;color:{color};font-weight:700;">'
        f"{escaped}</div>"
    )


def svg_shell(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:slide="https://slides.bytedance.com/ns" '
        'slide:role="slide" slide:contract-version="svglide-authoring-contract/v1" width="960" height="540" viewBox="0 0 960 540">\n'
        f"{body}\n"
        "</svg>\n"
    )


def write_minimal_plan(project: Path, slides: list[dict[str, Any]], *, title: str) -> None:
    write_json(
        project / "02-plan" / "slide_plan.json",
        {
            "route": "svglide-svg",
            "language": "zh-CN",
            "audience": "SVGlide engineers",
            "title": title,
            "slides": slides,
        },
    )


def fake_completed(payload: dict[str, Any]) -> Callable[..., Any]:
    import subprocess

    def run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    return run


def chart_payload() -> tuple[str, str, dict[str, Any]]:
    spec = read_json(FIXTURE_DIR / "chart-spec.json")
    raw = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return payload, "sha256:" + hashlib.sha256(raw).hexdigest(), spec


def chart_marker_svg() -> str:
    payload, payload_hash, _ = chart_payload()
    body = f"""
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#0B1F1A" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="72" y="60" width="640" height="48">{xhtml_text("Gate 8 chart marker", size=30)}</foreignObject>
  <g slide:role="chart" slide:chart-ref="chart-gate8-001" x="96" y="140" width="420" height="260">
    <metadata data-svglide-chart="svglide-chart-inline/v1" data-format="svglide-chart-spec-v1" data-encoding="base64url-json" data-payload-hash="{payload_hash}">{payload}</metadata>
  </g>
  <rect slide:role="shape" x="120" y="330" width="54" height="70" fill="#34D399" />
  <rect slide:role="shape" x="210" y="292" width="54" height="108" fill="#34D399" />
  <rect slide:role="shape" x="300" y="250" width="54" height="150" fill="#FBBF24" />
"""
    return svg_shell(body)


def image_asset_svg() -> str:
    return svg_shell(
        f"""
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#111827" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="64" y="68" width="520" height="48">{xhtml_text("Gate 8 image asset binding", size=28)}</foreignObject>
  <!-- svglide:asset-slot -->
  <rect slide:role="shape" x="592" y="112" width="288" height="216" fill="#1F2937" />
"""
    )


def raster_fallback_svg() -> str:
    return svg_shell(
        f"""
  <rect slide:role="shape" x="0" y="0" width="960" height="540" fill="#27130F" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="72" y="72" width="620" height="54">{xhtml_text("Gate 8 raster fallback island", size=30)}</foreignObject>
  <image slide:role="image" data-svglide-raster-fallback="isolated-decoration" data-svglide-fallback-reason="unsupported-filter-glow" href="@./03-assets/raw/glow.png" x="704" y="72" width="128" height="128" preserveAspectRatio="xMidYMid slice" />
  <rect slide:role="shape" x="72" y="180" width="520" height="74" fill="#3A211B" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="96" y="202" width="480" height="34">{xhtml_text("Only the decorative glow is rasterized.", size=22, color="#FFF7ED")}</foreignObject>
"""
    )


def check_no_svg_errors(result: dict[str, Any]) -> bool:
    return result.get("summary", {}).get("error_count") == 0


def case_result(name: str, status: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **extra}


def run_unsupported_case(root: Path) -> dict[str, Any]:
    project = root / "unsupported-feature"
    spec = read_json(FIXTURE_DIR / "unsupported-filter.canvas-spec.json")
    write_minimal_plan(project, [{"page": 1, "title": "Unsupported filter", "canvas_spec": spec}], title="Gate 8 Unsupported")
    render_failed = False
    render_error = ""
    try:
        artboard.render_project(project)
    except artboard.ArtboardError as error:
        render_failed = "canvas_spec_unsupported_features" in str(error)
        render_error = str(error)
    bridge_failed = False
    bridge_error = ""
    try:
        artboard.compile_satori_svg_to_svglide(
            '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="10" height="10" filter="url(#blur)"/></svg>'
        )
    except artboard.ArtboardError as error:
        bridge_failed = "satori_svg_effect_fail_fast" in str(error)
        bridge_error = str(error)
    status = "passed" if render_failed and bridge_failed else "failed"
    return case_result(
        "unsupported_feature_fail_fast",
        status,
        project=relpath(project, root),
        render_failed_before_live=render_failed,
        render_error=render_error,
        bridge_failed_before_live=bridge_failed,
        bridge_error=bridge_error,
        canvas_spec_fixture=relpath(FIXTURE_DIR / "unsupported-filter.canvas-spec.json", SCRIPT_DIR.parents[2]),
    )


def run_chart_case(root: Path) -> dict[str, Any]:
    project = root / "chart-marker"
    write_minimal_plan(
        project,
        [
            {
                "page": 1,
                "title": "Gate 8 chart marker",
                "chart_contract": {"verify": "required", "labels": ["Q1", "Q2", "Q3"], "data": [12, 18, 25]},
            }
        ],
        title="Gate 8 Chart",
    )
    svg_path = project / "04-svg" / "prepared" / "page-001.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(chart_marker_svg(), encoding="utf-8")
    preflight = svg_preflight.lint_files([svg_path.as_posix()])
    chart_verify = svglide_chart_verify.run_chart_verify(project)
    write_json(project / "07-create" / "live-create.json", {"xml_presentation_id": "gate8_chart", "slide_ids": ["chart-slide"]})
    readback = svglide_readback.run_readback(
        project,
        command_runner=fake_completed({"data": {"xml_presentation": {"content": f'<presentation><slide id="chart-slide">{chart_marker_svg()}</slide></presentation>'}}}),
    )
    status = (
        "passed"
        if check_no_svg_errors(preflight)
        and chart_verify["status"] == "passed"
        and readback["checks"]["chart_markers"]["status"] == "passed"
        else "failed"
    )
    payload, payload_hash, spec = chart_payload()
    return case_result(
        "chart_marker_svglide_chart_spec_v1",
        status,
        project=relpath(project, root),
        svg=relpath(svg_path, root),
        chart_spec_sha256=hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        chart_payload_hash=payload_hash,
        chart_payload_length=len(payload),
        preflight_summary=preflight["summary"],
        chart_verify_status=chart_verify["status"],
        readback_chart_markers=readback["checks"]["chart_markers"],
    )


def run_image_case(root: Path) -> dict[str, Any]:
    project = root / "image-asset"
    write_minimal_plan(project, [{"page": 1, "title": "Gate 8 image asset"}], title="Gate 8 Image")
    asset = project / "03-assets" / "raw" / "hero.png"
    write_png(asset)
    write_json(
        project / "03-assets" / "asset-manifest.json",
        {
            "version": "svglide-assets/v1",
            "status": "passed",
            "acquired_assets": [
                {
                    "asset_id": "hero",
                    "page": 1,
                    "placement_role": "body_visual",
                    "asset_kind": "user_file",
                    "status": "local_file",
                    "file": "03-assets/raw/hero.png",
                    "source_url": "https://example.com/gate8-hero",
                    "license": "preview_unverified",
                }
            ],
        },
    )
    write_json(project / "03-assets" / "assets.json", {"@./03-assets/raw/hero.png": "boxcn_gate8_hero"})
    source_svg = project / "04-svg" / "page-001.svg"
    source_svg.parent.mkdir(parents=True, exist_ok=True)
    source_svg.write_text(image_asset_svg(), encoding="utf-8")
    injection = svglide_asset_injector.inject_project_assets(project)
    prepare = svglide_prepare.prepare_project(project)
    write_json(project / "07-create" / "live-create.json", {"xml_presentation_id": "gate8_image", "slide_ids": ["image-slide"]})
    readback = svglide_readback.run_readback(
        project,
        command_runner=fake_completed(
            {"data": {"xml_presentation": {"content": '<presentation><slide id="image-slide"><image src="boxcn_gate8_hero"/></slide></presentation>'}}}
        ),
    )
    status = (
        "passed"
        if injection["used_count"] == 1
        and any(ref["refs"][0]["status"] == "mapped" for ref in prepare.get("asset_refs", []))
        and readback["checks"]["asset_tokens"]["status"] == "passed"
        and readback["checks"]["image_assets"]["status"] == "passed"
        else "failed"
    )
    return case_result(
        "image_asset_binding_readback",
        status,
        project=relpath(project, root),
        source_svg=relpath(source_svg, root),
        asset_sha256=file_sha256(asset),
        injection_summary={key: injection[key] for key in ["used_count", "injected_count", "skipped_count"]},
        prepare_asset_refs=prepare.get("asset_refs", []),
        readback_asset_tokens=readback["checks"]["asset_tokens"],
        readback_image_assets=readback["checks"]["image_assets"],
    )


def raster_fallback_records(svg_text: str, project: Path) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(svg_text)
    records: list[dict[str, Any]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "image":
            continue
        marker = element.get("data-svglide-raster-fallback")
        if marker != "isolated-decoration":
            continue
        href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href") or ""
        bbox = {
            "x": float(element.get("x") or 0),
            "y": float(element.get("y") or 0),
            "width": float(element.get("width") or 0),
            "height": float(element.get("height") or 0),
        }
        local = project / href[3:] if href.startswith("@./") else None
        records.append(
            {
                "marker": marker,
                "reason": element.get("data-svglide-fallback-reason"),
                "href": href,
                "bbox": bbox,
                "island": bbox["width"] <= 240 and bbox["height"] <= 240 and bbox["x"] >= 0 and bbox["y"] >= 0,
                "file_exists": bool(local and local.exists()),
                "file_sha256": file_sha256(local) if local and local.exists() else None,
            }
        )
    return records


def run_raster_fallback_case(root: Path) -> dict[str, Any]:
    project = root / "raster-fallback"
    write_minimal_plan(project, [{"page": 1, "title": "Gate 8 raster fallback"}], title="Gate 8 Raster Fallback")
    asset = project / "03-assets" / "raw" / "glow.png"
    write_png(asset)
    write_json(project / "03-assets" / "assets.json", {"@./03-assets/raw/glow.png": "boxcn_gate8_glow"})
    svg_path = project / "04-svg" / "page-001.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(raster_fallback_svg(), encoding="utf-8")
    prepare = svglide_prepare.prepare_project(project)
    prepared = project / "04-svg" / "prepared" / "page-001.svg"
    preflight = svg_preflight.lint_files([prepared.as_posix()])
    records = raster_fallback_records(prepared.read_text(encoding="utf-8"), project)
    fallback_receipt = {
        "version": "svglide-raster-fallback/v1",
        "status": "passed" if records and all(item["island"] and item["file_exists"] for item in records) else "failed",
        "source_svg": relpath(svg_path, project),
        "prepared_svg": relpath(prepared, project),
        "records": records,
    }
    write_json(project / "06-check" / "raster-fallback.json", fallback_receipt)
    status = "passed" if fallback_receipt["status"] == "passed" and check_no_svg_errors(preflight) else "failed"
    return case_result(
        "local_raster_fallback_island",
        status,
        project=relpath(project, root),
        prepare_asset_refs=prepare.get("asset_refs", []),
        preflight_summary=preflight["summary"],
        raster_fallback=fallback_receipt,
    )


def run_gate8(root: Path) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    cases = [
        run_unsupported_case(root),
        run_chart_case(root),
        run_image_case(root),
        run_raster_fallback_case(root),
    ]
    failed = [item for item in cases if item["status"] != "passed"]
    result = {
        "version": "svglide-gate8-special-cases/v1",
        "status": "failed" if failed else "passed",
        "generated_at": now_iso(),
        "root": str(root),
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "passed_count": len(cases) - len(failed),
            "failed_count": len(failed),
        },
        "output_path": OUTPUT_NAME,
    }
    write_json(root / OUTPUT_NAME, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Gate 8 special-case fixtures for SVGlide artboard/Satori.")
    parser.add_argument("output_root", help="Directory where Gate 8 fixture projects and evidence should be written")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_gate8(Path(args.output_root))
    except (OSError, Gate8Error, artboard.ArtboardError, svglide_prepare.PrepareError) as error:
        print(f"svglide_gate8_special_cases: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
