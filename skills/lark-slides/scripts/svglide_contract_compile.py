#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path
from typing import Any, Sequence

import svglide_asset_injector
import svglide_svg_contract as contract


RAW_MANIFEST = Path("04-artboard/raw/manifest.json")
CONTRACT_DIR = Path("04-svg/contract")
CONTRACT_MANIFEST = CONTRACT_DIR / "manifest.json"


class ContractCompileError(Exception):
    pass


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractCompileError(f"missing json file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractCompileError(f"invalid json file: {path}: {exc}") from exc


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def number(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str) and value.strip().endswith("px"):
            value = value.strip()[:-2]
        return float(value)
    except (TypeError, ValueError):
        return default


def scalar(value: float) -> str:
    return f"{value:g}"


def load_raw_manifest(project: Path) -> dict[str, Any]:
    path = project / RAW_MANIFEST
    if not path.exists():
        raise ContractCompileError(f"missing raw visual manifest: {path}")
    data = read_json(path)
    if not isinstance(data, dict):
        raise ContractCompileError(f"raw visual manifest must be an object: {path}")
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ContractCompileError(f"raw visual manifest has no pages: {path}")
    return data


def load_assets(project: Path) -> dict[str, str]:
    path = project / "03-assets" / "assets.json"
    if not path.exists():
        return {}
    data = read_json(path)
    if not isinstance(data, dict):
        raise ContractCompileError(f"assets json must be an object: {path}")
    return {str(key): str(value) for key, value in data.items() if isinstance(key, str)}


def page_path(project: Path, value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ContractCompileError(f"raw manifest page is missing {field}")
    return project / value


def empty_report(source: str, semantic_map: str, output: str) -> dict[str, Any]:
    return {
        "version": "svglide-contract-compile/v1",
        "source": source,
        "semantic_map": semantic_map,
        "output": output,
        "status": "passed",
        "summary": {
            "semantic_required": 0,
            "visual_required": 0,
            "decorative_optional": 0,
            "compiled_elements": 0,
            "degraded_elements": 0,
            "rasterized_regions": 0,
            "dropped_decorations": 0,
            "blocking_issues": 0,
        },
        "compiled": [],
        "degraded": [],
        "rasterized": [],
        "dropped": [],
        "blocking_issues": [],
        "input_sha256": "",
        "semantic_map_sha256": "",
        "output_sha256": "",
    }


def element_id(element: dict[str, Any], fallback: str) -> str:
    raw = element.get("element_id") or element.get("id") or fallback
    return str(raw)


def element_importance(element: dict[str, Any]) -> str:
    value = str(element.get("importance") or "").strip()
    if value in {"semantic_required", "visual_required", "decorative_optional"}:
        return value
    kind = str(element.get("kind") or "")
    if kind in {"text", "image", "chart"} or element.get("source_ref"):
        return "semantic_required"
    return "visual_required"


def record_decision(
    report: dict[str, Any],
    *,
    element: dict[str, Any],
    decision: str,
    reason: str,
    output_ref: str | None = None,
    fallback: str = "element",
) -> None:
    importance = element_importance(element)
    entry = {
        "element_id": element_id(element, fallback),
        "source_ref": element.get("source_ref"),
        "importance": importance,
        "source_tag": element.get("kind"),
        "decision": decision,
        "reason": reason,
        "output_ref": output_ref,
    }
    if decision == "compiled":
        report["compiled"].append(entry)
        report["summary"]["compiled_elements"] += 1
    elif decision == "degraded":
        report["degraded"].append(entry)
        report["summary"]["degraded_elements"] += 1
    elif decision == "rasterized":
        report["rasterized"].append(entry)
        report["summary"]["rasterized_regions"] += 1
    elif decision == "dropped":
        report["dropped"].append(entry)
        report["summary"]["dropped_decorations"] += 1
    elif decision == "blocked":
        report["blocking_issues"].append(entry)
        report["summary"]["blocking_issues"] += 1
    report["summary"][importance] += 1


def bbox(element: dict[str, Any]) -> dict[str, float]:
    raw = element.get("bbox") if isinstance(element.get("bbox"), dict) else {}
    return {
        "x": number(raw.get("x"), 0),
        "y": number(raw.get("y"), 0),
        "width": max(number(raw.get("width"), 1), 1),
        "height": max(number(raw.get("height"), 1), 1),
    }


def style(element: dict[str, Any]) -> dict[str, Any]:
    return element.get("style") if isinstance(element.get("style"), dict) else {}


def element_common_attrs(element: dict[str, Any]) -> dict[str, str]:
    eid = element_id(element, "element")
    attrs = {"id": eid, "data-node-id": eid}
    source_ref = element.get("source_ref")
    if isinstance(source_ref, str) and source_ref:
        attrs["data-source-ref"] = source_ref
    source_attrs = element.get("attrs") if isinstance(element.get("attrs"), dict) else {}
    for key in ["data-svglide-role", "data-svglide-motif-id", "data-svglide-motif-owner", "data-svglide-origin-template"]:
        value = element.get(key)
        if value is None:
            value = source_attrs.get(key)
        if value is not None:
            attrs[key] = str(value)
    return attrs


def compile_text(element: dict[str, Any], report: dict[str, Any]) -> str:
    box = bbox(element)
    css_style = style(element)
    fill = str(css_style.get("fill") or css_style.get("color") or "#111827")
    font_size = number(css_style.get("font_size") or css_style.get("font-size"), 24)
    font_weight = int(number(css_style.get("font_weight") or css_style.get("font-weight"), 700))
    attrs = contract.text_shape_attrs(
        {
            **element_common_attrs(element),
            "x": scalar(box["x"]),
            "y": scalar(box["y"]),
            "width": scalar(box["width"]),
            "height": scalar(box["height"]),
            "fill": fill,
            "color": fill,
        }
    )
    css = f"color:{fill};font-size:{font_size:g}px;font-weight:{font_weight};font-family:Inter,Arial,sans-serif;line-height:1.18;"
    text = escape(str(element.get("text") or ""))
    record_decision(report, element=element, decision="compiled", reason="compiled to foreignObject text shape", output_ref=attrs["id"])
    return f'<foreignObject {contract.svg_attrs(attrs)}><div xmlns="{contract.XHTML_NS}" style="{escape(css, quote=True)}">{text}</div></foreignObject>'


def compile_shape(element: dict[str, Any], report: dict[str, Any]) -> str | None:
    kind = str(element.get("kind") or "")
    box = bbox(element)
    css_style = style(element)
    fill = str(css_style.get("fill") or "#F8FAFC")
    attrs = contract.shape_attrs(element_common_attrs(element))
    if kind == "rect":
        attrs.update({"x": scalar(box["x"]), "y": scalar(box["y"]), "width": scalar(box["width"]), "height": scalar(box["height"]), "fill": fill})
    elif kind == "circle":
        attrs.update({"cx": scalar(box["x"] + box["width"] / 2), "cy": scalar(box["y"] + box["height"] / 2), "r": scalar(max(min(box["width"], box["height"]) / 2, 1)), "fill": fill})
    elif kind == "ellipse":
        attrs.update({"cx": scalar(box["x"] + box["width"] / 2), "cy": scalar(box["y"] + box["height"] / 2), "rx": scalar(max(box["width"] / 2, 1)), "ry": scalar(max(box["height"] / 2, 1)), "fill": fill})
    elif kind == "line":
        attrs.update(
            {
                "x1": scalar(number(css_style.get("x1"), box["x"])),
                "y1": scalar(number(css_style.get("y1"), box["y"])),
                "x2": scalar(number(css_style.get("x2"), box["x"] + box["width"])),
                "y2": scalar(number(css_style.get("y2"), box["y"] + box["height"])),
                "stroke": str(css_style.get("stroke") or fill),
                "stroke-width": scalar(number(css_style.get("stroke_width") or css_style.get("stroke-width"), 2)),
            }
        )
    elif kind == "path":
        d = css_style.get("d") or element.get("d")
        if not isinstance(d, str) or not d.strip():
            record_decision(report, element=element, decision="blocked", reason="path is missing d data")
            return None
        attrs.update({"d": d, "fill": str(css_style.get("fill") or "none"), "stroke": str(css_style.get("stroke") or fill)})
        if css_style.get("stroke_width") or css_style.get("stroke-width"):
            attrs["stroke-width"] = scalar(number(css_style.get("stroke_width") or css_style.get("stroke-width"), 2))
    else:
        return None
    record_decision(report, element=element, decision="compiled", reason=f"compiled {kind} to slide shape", output_ref=attrs["id"])
    return f"<{kind} {contract.svg_attrs(attrs)}/>"


def image_href(element: dict[str, Any]) -> str | None:
    css_style = style(element)
    for key in ["href", "src", "asset_href"]:
        value = element.get(key)
        if isinstance(value, str) and value:
            return value
        style_value = css_style.get(key)
        if isinstance(style_value, str) and style_value:
            return style_value
    return None


def compile_image(element: dict[str, Any], report: dict[str, Any], assets: dict[str, str]) -> str | None:
    href = image_href(element)
    if not href:
        record_decision(report, element=element, decision="blocked", reason="semantic image is missing href")
        return None
    resolved = assets.get(href, href)
    if resolved.startswith("data:") or resolved.startswith("http://") or resolved.startswith("https://"):
        if element_importance(element) == "semantic_required":
            record_decision(report, element=element, decision="blocked", reason="semantic image must use local placeholder or file token")
            return None
        record_decision(report, element=element, decision="degraded", reason="external image href cannot be guaranteed for live create")
    box = bbox(element)
    attrs = contract.image_attrs({**element_common_attrs(element), "href": resolved, "x": scalar(box["x"]), "y": scalar(box["y"]), "width": scalar(box["width"]), "height": scalar(box["height"])})
    record_decision(report, element=element, decision="compiled", reason="compiled to slide image", output_ref=attrs["id"])
    return f"<image {contract.svg_attrs(attrs)}/>"


def compile_unknown(element: dict[str, Any], report: dict[str, Any]) -> str | None:
    importance = element_importance(element)
    if importance == "decorative_optional":
        record_decision(report, element=element, decision="dropped", reason="unsupported decorative element dropped with report")
        return None
    if importance == "visual_required":
        box = bbox(element)
        attrs = contract.shape_attrs(
            {
                **element_common_attrs(element),
                "x": scalar(box["x"]),
                "y": scalar(box["y"]),
                "width": scalar(box["width"]),
                "height": scalar(box["height"]),
                "fill": "none",
                "stroke": "#94A3B8",
                "stroke-width": "1",
                "opacity": "0.35",
            }
        )
        record_decision(report, element=element, decision="degraded", reason="unsupported visual element degraded to editable bounding shape", output_ref=attrs["id"])
        return f"<rect {contract.svg_attrs(attrs)}/>"
    record_decision(report, element=element, decision="blocked", reason="unsupported semantic element cannot be compiled")
    return None


def compile_semantic_element(element: dict[str, Any], report: dict[str, Any], assets: dict[str, str]) -> str | None:
    kind = str(element.get("kind") or "")
    if kind == "text":
        return compile_text(element, report)
    if kind in {"rect", "circle", "ellipse", "line", "path"}:
        return compile_shape(element, report)
    if kind == "image":
        return compile_image(element, report, assets)
    return compile_unknown(element, report)


def finalize_report(report: dict[str, Any]) -> None:
    if report["summary"]["blocking_issues"]:
        report["status"] = "failed"
    elif report["summary"]["degraded_elements"] or report["summary"]["rasterized_regions"] or report["summary"]["dropped_decorations"]:
        report["status"] = "passed_with_warnings"
    else:
        report["status"] = "passed"


def compile_page(project: Path, page_entry: dict[str, Any], assets: dict[str, str]) -> dict[str, Any]:
    page = int(number(page_entry.get("page"), 1))
    source_path = page_path(project, page_entry.get("source"), field="source")
    semantic_path = page_path(project, page_entry.get("semantic_map"), field="semantic_map")
    output_path = project / "04-svg" / f"page-{page:03d}.svg"
    report_path = project / "04-svg" / "contract" / f"page-{page:03d}.report.json"
    semantic_map = read_json(semantic_path)
    elements = semantic_map.get("elements") if isinstance(semantic_map, dict) else None
    if not isinstance(elements, list):
        raise ContractCompileError(f"semantic map has no elements: {semantic_path}")
    report = empty_report(rel(project, source_path), rel(project, semantic_path), rel(project, output_path))
    children: list[str] = []
    for index, raw_element in enumerate(elements, 1):
        if not isinstance(raw_element, dict):
            continue
        child = compile_semantic_element(raw_element, report, assets)
        if child:
            children.append(child)
    root_attrs = contract.svg_root_attrs({"width": "960", "height": "540", "viewBox": "0 0 960 540"})
    output = "<svg " + contract.svg_attrs(root_attrs) + ">\n" + "\n".join(f"  {child}" for child in children) + "\n</svg>\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    report["input_sha256"] = file_sha256(source_path)
    report["semantic_map_sha256"] = file_sha256(semantic_path)
    report["output_sha256"] = file_sha256(output_path)
    finalize_report(report)
    write_json(report_path, report)
    return {
        "page": page,
        "source": report["source"],
        "semantic_map": report["semantic_map"],
        "output": report["output"],
        "report": rel(project, report_path),
        "status": report["status"],
        "input_sha256": report["input_sha256"],
        "semantic_map_sha256": report["semantic_map_sha256"],
        "output_sha256": report["output_sha256"],
        "summary": report["summary"],
    }


def refresh_pages_after_asset_injection(project: Path, pages: list[dict[str, Any]], injection_summary: dict[str, Any]) -> None:
    if not pages:
        return
    refreshed_at = injection_summary.get("generated_at")
    for page in pages:
        output_rel = page.get("output")
        report_rel = page.get("report")
        if not isinstance(output_rel, str) or not isinstance(report_rel, str):
            continue
        output_path = project / output_rel
        report_path = project / report_rel
        if not output_path.exists() or not report_path.exists():
            continue
        digest = file_sha256(output_path)
        page["output_sha256"] = digest
        report = read_json(report_path)
        if isinstance(report, dict):
            report["output_sha256"] = digest
            report["asset_injection_summary"] = injection_summary
            if refreshed_at:
                report["post_asset_injection_refreshed_at"] = refreshed_at
            write_json(report_path, report)


def write_manifest(project: Path, pages: list[dict[str, Any]], asset_injection_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    blocking = sum(int(page["summary"].get("blocking_issues", 0)) for page in pages)
    degraded = sum(int(page["summary"].get("degraded_elements", 0)) for page in pages)
    rasterized = sum(int(page["summary"].get("rasterized_regions", 0)) for page in pages)
    dropped = sum(int(page["summary"].get("dropped_decorations", 0)) for page in pages)
    status = "failed" if blocking else "passed_with_warnings" if degraded or rasterized or dropped else "passed"
    manifest_pages = [{key: page[key] for key in ["page", "source", "semantic_map", "output", "report", "status", "input_sha256", "semantic_map_sha256", "output_sha256"]} for page in pages]
    manifest = {
        "version": "svglide-contract-compile-manifest/v1",
        "stage": "contract_compile",
        "status": status,
        "pages": manifest_pages,
        "summary": {
            "pages": len(pages),
            "blocking_issues": blocking,
            "degraded_elements": degraded,
            "rasterized_regions": rasterized,
            "dropped_decorations": dropped,
        },
    }
    if asset_injection_summary is not None:
        manifest["asset_injection_summary"] = asset_injection_summary
    write_json(project / CONTRACT_MANIFEST, manifest)
    receipts_dir = project / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        receipts_dir / "contract_compile.json",
        {
            "stage": "contract_compile",
            "status": status,
            "contract_manifest": CONTRACT_MANIFEST.as_posix(),
            "pages": manifest_pages,
            "summary": manifest["summary"],
            "raw_visual_manifest_sha256": file_sha256(project / RAW_MANIFEST) if (project / RAW_MANIFEST).exists() else None,
            "asset_injection_summary": asset_injection_summary,
        },
    )
    return manifest


def existing_svg_files(project: Path) -> list[Path]:
    return sorted(path for path in (project / "04-svg").glob("*.svg") if path.is_file())


def write_passthrough_report(project: Path, svg_path: Path, page: int) -> dict[str, Any]:
    report_path = project / "04-svg" / "contract" / f"page-{page:03d}.report.json"
    source = rel(project, svg_path)
    report = empty_report(source, source, source)
    report["compiled"].append(
        {
            "element_id": f"page-{page:03d}",
            "source_ref": None,
            "importance": "semantic_required",
            "source_tag": "svg",
            "decision": "compiled",
            "reason": "existing canonical SVG accepted by compatibility path",
            "output_ref": source,
        }
    )
    report["summary"]["semantic_required"] = 1
    report["summary"]["compiled_elements"] = 1
    digest = file_sha256(svg_path)
    report["input_sha256"] = digest
    report["semantic_map_sha256"] = digest
    report["output_sha256"] = digest
    write_json(report_path, report)
    return {
        "page": page,
        "source": source,
        "semantic_map": source,
        "output": source,
        "report": rel(project, report_path),
        "status": "passed",
        "input_sha256": digest,
        "semantic_map_sha256": digest,
        "output_sha256": digest,
        "summary": report["summary"],
    }


def compile_existing_svgs(project: Path) -> dict[str, Any]:
    files = existing_svg_files(project)
    if not files:
        raise ContractCompileError("no existing SVG files found under 04-svg")
    return write_manifest(project, [write_passthrough_report(project, path, index) for index, path in enumerate(files, 1)])


def compile_project(project: Path, *, allow_existing_svg: bool = False) -> dict[str, Any]:
    project = project.resolve()
    if allow_existing_svg and not (project / RAW_MANIFEST).exists():
        return compile_existing_svgs(project)
    manifest = load_raw_manifest(project)
    pages = manifest.get("pages")
    assert isinstance(pages, list)
    assets = load_assets(project)
    compiled_pages = [compile_page(project, page, assets) for page in pages if isinstance(page, dict)]
    if not compiled_pages:
        raise ContractCompileError("raw visual manifest produced no compilable pages")
    injection_summary = svglide_asset_injector.inject_project_assets(project)
    refresh_pages_after_asset_injection(project, compiled_pages, injection_summary)
    return write_manifest(project, compiled_pages, asset_injection_summary=injection_summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compile raw SVGlide visual artifacts into canonical SVGlide SVG.")
    parser.add_argument("--project", required=True, help="SVGlide project directory under .lark-slides/plan/<deck-id>")
    parser.add_argument("--allow-existing-svg", action="store_true", help="Write pass-through contract manifest for legacy direct SVG projects.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = compile_project(Path(args.project), allow_existing_svg=args.allow_existing_svg)
    except ContractCompileError as exc:
        print(f"svglide_contract_compile: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if manifest.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
