#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "svglide-ppt-master-asset-map/v1"
REQUIRED_FIELDS = {
    "id",
    "source_path",
    "kind",
    "ppt_master_role",
    "svglide_target",
    "protocol_compatibility",
    "conversion_strategy",
    "activation_status",
    "selection_tags",
    "copy_policy",
    "license_status",
    "granularity",
    "unsupported_features",
    "normalized_primitives",
    "non_migratable_reason",
    "risk_flags",
    "golden_example_required",
}
REQUIRED_KINDS = {
    "brand_preset",
    "layout_template",
    "deck_template",
    "chart_template",
    "icon_library",
    "visual_style",
    "image_palette",
    "image_rendering",
    "image_type_template",
    "narrative_mode",
    "example_project",
    "workflow_reference",
}
RAW_SVG_NORMALIZED_PRIMITIVES = [
    "960x540_canvas",
    "slide_role_shape",
    "foreignObject_text",
    "primitive_shapes",
]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)


class InventoryError(ValueError):
    """Raised when the local ppt-master tree cannot produce a valid inventory."""


def script_path() -> Path:
    return Path(__file__).resolve()


def cli_worktree_root() -> Path:
    return script_path().parents[3]


def default_source_root() -> Path:
    return cli_worktree_root().parents[1] / "ppt-master"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def digest_paths(source_root: Path, paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted({p for p in paths if p.exists() and p.is_file()}):
        rel = path.relative_to(source_root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def rel_source(path: Path, source_root: Path) -> str:
    path = path.resolve()
    source_root = source_root.resolve()
    if path == source_root:
        return source_root.name
    return f"{source_root.name}/{path.relative_to(source_root).as_posix()}"


def slug(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_").lower()
    return normalized or "item"


def tokenize(*values: object) -> list[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            tokens.update(tokenize(*value))
            continue
        tokens.update(match.group(0).lower() for match in TOKEN_RE.finditer(str(value)))
    return sorted(tokens)


def limited_tags(*values: object, extra: Iterable[str] = ()) -> list[str]:
    tags = tokenize(*values)
    for tag in extra:
        tags.extend(tokenize(tag))
    return sorted(set(tags))[:32]


def files_under(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file())


def direct_md_files(path: Path) -> list[Path]:
    return sorted(p for p in path.glob("*.md") if p.name != "_index.md")


def direct_dirs(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir()) if path.exists() else []


def svg_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".svg":
        return [path]
    return sorted(p for p in path.rglob("*.svg") if p.is_file()) if path.exists() else []


def image_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def count_base64_images(paths: Iterable[Path]) -> int:
    count = 0
    for path in paths:
        try:
            count += path.read_text(encoding="utf-8", errors="ignore").count("data:image")
        except OSError:
            continue
    return count


def detect_svg_unsupported(paths: Iterable[Path]) -> list[str]:
    features: set[str] = set()
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        if "<text" in lowered:
            features.add("raw_svg_text")
        if "slide:role" not in lowered:
            features.add("missing_slide_role")
        if "viewbox=\"0 0 1280 720\"" in lowered or "width=\"1280\"" in lowered or "height=\"720\"" in lowered:
            features.add("1280x720_canvas")
        if "<image" in lowered:
            features.add("embedded_image")
        if "data:image" in lowered:
            features.add("embedded_base64_image")
        if "<foreignobject" in lowered:
            features.add("foreignObject")
        if "<filter" in lowered:
            features.add("filter_effect")
        if "<mask" in lowered:
            features.add("mask_effect")
        if "<clippath" in lowered:
            features.add("clipPath")
        if "<use" in lowered:
            features.add("symbol_use")
    return sorted(features)


def make_resource(
    *,
    resource_id: str,
    source_path: Path,
    source_root: Path,
    kind: str,
    ppt_master_role: str,
    svglide_target: str,
    protocol_compatibility: str,
    conversion_strategy: str,
    selection_tags: Iterable[str],
    copy_policy: str = "derive_contract_only",
    license_status: str = "reference_only",
    granularity: str = "file",
    unsupported_features: Iterable[str] = (),
    normalized_primitives: Iterable[str] = (),
    non_migratable_reason: str = "",
    risk_flags: Iterable[str] = (),
    golden_example_required: bool = True,
    activation_status: str = "candidate",
    metadata: dict | None = None,
    summary: str = "",
) -> dict:
    source_files = files_under(source_path) if source_path.is_dir() else [source_path]
    resource = {
        "id": resource_id,
        "source_path": rel_source(source_path, source_root),
        "kind": kind,
        "ppt_master_role": ppt_master_role,
        "svglide_target": svglide_target,
        "protocol_compatibility": protocol_compatibility,
        "conversion_strategy": conversion_strategy,
        "activation_status": activation_status,
        "selection_tags": sorted(set(selection_tags)),
        "copy_policy": copy_policy,
        "license_status": license_status,
        "granularity": granularity,
        "unsupported_features": sorted(set(unsupported_features)),
        "normalized_primitives": sorted(set(normalized_primitives)),
        "non_migratable_reason": non_migratable_reason,
        "risk_flags": sorted(set(risk_flags)),
        "golden_example_required": golden_example_required,
        "normalized_fixture": "",
        "source_digest": digest_paths(source_root, source_files),
    }
    if summary:
        resource["summary"] = summary
    if metadata:
        resource["metadata"] = metadata
    return resource


def build_brand_resources(source_root: Path) -> list[dict]:
    index_path = source_root / "skills/ppt-master/templates/brands/brands_index.json"
    brands = read_json(index_path)
    resources = []
    for name, data in sorted(brands.items()):
        root = index_path.parent / name
        summary = data.get("summary", "")
        svgs = svg_files(root)
        resources.append(
            make_resource(
                resource_id=f"brand.{slug(name)}",
                source_path=root,
                source_root=source_root,
                kind="brand_preset",
                ppt_master_role="brand identity preset",
                svglide_target="style-presets.json/brand-visual-tokens",
                protocol_compatibility="needs_normalization",
                conversion_strategy="Extract color, typography, spacing, and brand-tone contracts; do not copy brand marks into runtime output.",
                selection_tags=limited_tags("brand", name, summary),
                granularity="template_directory",
                unsupported_features=sorted(set(detect_svg_unsupported(svgs) + ["brand_logo_assets"])),
                normalized_primitives=["color_tokens", "typography_rules", "logo_exclusion_zone"],
                non_migratable_reason="Brand marks and logos require explicit authorization before production use.",
                risk_flags=["brand_trademark", "third_party_logo", "requires_license_review"],
                metadata={
                    "summary": summary,
                    "primary_color": data.get("primary_color", ""),
                    "svg_file_count": len(svgs),
                    "image_file_count": len(image_files(root)),
                    "file_count": len(files_under(root)),
                },
                summary=summary,
            )
        )
    return resources


def build_layout_resources(source_root: Path) -> list[dict]:
    index_path = source_root / "skills/ppt-master/templates/layouts/layouts_index.json"
    layouts = read_json(index_path)
    resources = []
    for name, data in sorted(layouts.items()):
        root = index_path.parent / name
        summary = data.get("summary", "")
        svgs = svg_files(root)
        resources.append(
            make_resource(
                resource_id=f"layout.{slug(name)}",
                source_path=root,
                source_root=source_root,
                kind="layout_template",
                ppt_master_role="page skeleton and rhythm template",
                svglide_target="svg-seeds.json/layout-skeletons",
                protocol_compatibility="needs_normalization",
                conversion_strategy="Extract page slots, density, rhythm, and spacing contracts; regenerate as SVGlide seeds.",
                selection_tags=limited_tags("layout", name, summary, data.get("page_types", [])),
                granularity="template_directory",
                unsupported_features=detect_svg_unsupported(svgs),
                normalized_primitives=RAW_SVG_NORMALIZED_PRIMITIVES + ["layout_boxes", "content_budget"],
                non_migratable_reason="Raw 1280x720 SVG templates lack SVGlide slide roles and must be re-authored before activation.",
                risk_flags=["pptx_export_bias", "requires_svglide_normalization"],
                metadata={
                    "summary": summary,
                    "canvas_format": data.get("canvas_format", ""),
                    "page_count": data.get("page_count", len(svgs)),
                    "page_types": data.get("page_types", []),
                    "svg_file_count": len(svgs),
                },
                summary=summary,
            )
        )
    return resources


def build_deck_resources(source_root: Path) -> list[dict]:
    index_path = source_root / "skills/ppt-master/templates/decks/decks_index.json"
    decks = read_json(index_path)
    resources = []
    for name, data in sorted(decks.items()):
        root = index_path.parent / name
        summary = data.get("summary", "")
        svgs = svg_files(root)
        resources.append(
            make_resource(
                resource_id=f"deck.{slug(name)}",
                source_path=root,
                source_root=source_root,
                kind="deck_template",
                ppt_master_role="finished deck style and page-sequence template",
                svglide_target="deck-rhythm-pack/style-pack reference",
                protocol_compatibility="needs_normalization",
                conversion_strategy="Extract page sequence, rhythm, and style rules; do not copy finished deck SVG or logos.",
                selection_tags=limited_tags("deck", name, summary),
                granularity="template_directory",
                unsupported_features=sorted(set(detect_svg_unsupported(svgs) + ["finished_deck_template"])),
                normalized_primitives=RAW_SVG_NORMALIZED_PRIMITIVES + ["deck_rhythm", "style_tokens"],
                non_migratable_reason="Finished deck templates contain brand assets and raw SVG pages that require re-authoring.",
                risk_flags=["brand_trademark", "third_party_logo", "requires_svglide_normalization"],
                metadata={
                    "summary": summary,
                    "canvas_format": data.get("canvas_format", ""),
                    "page_count": data.get("page_count", len(svgs)),
                    "primary_color": data.get("primary_color", ""),
                    "svg_file_count": len(svgs),
                    "image_file_count": len(image_files(root)),
                },
                summary=summary,
            )
        )
    return resources


def build_chart_resources(source_root: Path) -> list[dict]:
    index_path = source_root / "skills/ppt-master/templates/charts/charts_index.json"
    index = read_json(index_path)
    resources = []
    for name, data in sorted(index.get("charts", {}).items()):
        path = index_path.parent / f"{name}.svg"
        summary = data.get("summary", "")
        resources.append(
            make_resource(
                resource_id=f"chart.{slug(name)}",
                source_path=path,
                source_root=source_root,
                kind="chart_template",
                ppt_master_role="visualization template",
                svglide_target="svg-recipes.json/component-catalog",
                protocol_compatibility="needs_normalization",
                conversion_strategy="Extract geometry slots and chart role contract; do not copy final SVG as a page template.",
                selection_tags=limited_tags("chart", name, summary),
                granularity="file",
                unsupported_features=detect_svg_unsupported([path]),
                normalized_primitives=RAW_SVG_NORMALIZED_PRIMITIVES + ["chart_data_slots", "geometry_contract"],
                non_migratable_reason="Raw chart SVG must be normalized into SVGlide primitives and checked before activation.",
                risk_flags=["pptx_export_bias", "requires_svglide_normalization"],
                metadata={"summary": summary, "view_box": index.get("meta", {}).get("defaultViewBox", "")},
                summary=summary,
            )
        )
    return resources


def icon_style(library: str) -> str:
    styles = {
        "chunk-filled": "filled sharp-corner geometric icons",
        "tabler-filled": "filled rounded icons",
        "tabler-outline": "stroke outline icons",
        "phosphor-duotone": "duotone soft-depth icons",
        "simple-icons": "brand-logo silhouettes",
    }
    return styles.get(library, "SVG icon library")


def build_icon_resources(source_root: Path) -> list[dict]:
    icons_root = source_root / "skills/ppt-master/templates/icons"
    resources = []
    for root in direct_dirs(icons_root):
        icon_paths = sorted(root.glob("*.svg"))
        samples = [path.stem for path in icon_paths[:20]]
        is_brand = root.name == "simple-icons"
        resources.append(
            make_resource(
                resource_id=f"icon_library.{slug(root.name)}",
                source_path=root,
                source_root=source_root,
                kind="icon_library",
                ppt_master_role="icon library summary and searchable index",
                svglide_target="icon-registry/style-binding",
                protocol_compatibility="needs_normalization",
                conversion_strategy="Expose a library-level summary and searchable index; select one style library per deck and never inject every SVG into the prompt.",
                selection_tags=limited_tags("icon", root.name, icon_style(root.name), samples),
                granularity="library_summary",
                unsupported_features=["raw_svg_icon_files"] + (["brand_logo_assets"] if is_brand else []),
                normalized_primitives=["data-icon_placeholder", "searchable_icon_index", "single_library_binding"],
                non_migratable_reason="Individual icon SVGs are not copied into the main prompt; brand icons require license review.",
                risk_flags=(["brand_trademark", "third_party_logo"] if is_brand else ["large_library_prompt_risk"]),
                metadata={
                    "style": icon_style(root.name),
                    "icon_count": len(icon_paths),
                    "sample_icons": samples,
                    "index_policy": "library_summary_only",
                },
                summary=icon_style(root.name),
            )
        )
    return resources


def build_reference_doc_resources(
    source_root: Path,
    *,
    rel_dir: str,
    kind: str,
    id_prefix: str,
    ppt_master_role: str,
    svglide_target: str,
    conversion_strategy: str,
    normalized_primitives: list[str],
    extra_tags: Iterable[str] = (),
) -> list[dict]:
    root = source_root / rel_dir
    resources = []
    for path in direct_md_files(root):
        name = path.stem
        summary = first_heading_or_line(path)
        resources.append(
            make_resource(
                resource_id=f"{id_prefix}.{slug(name)}",
                source_path=path,
                source_root=source_root,
                kind=kind,
                ppt_master_role=ppt_master_role,
                svglide_target=svglide_target,
                protocol_compatibility="documentation_reference",
                conversion_strategy=conversion_strategy,
                selection_tags=limited_tags(id_prefix, name, summary, extra_tags),
                copy_policy="derive_rules_only",
                license_status="reference_only",
                granularity="file",
                unsupported_features=[],
                normalized_primitives=normalized_primitives,
                non_migratable_reason="Reference prose is a source for derived rules, not a runtime asset.",
                risk_flags=["style_drift_if_copied_verbatim"],
                metadata={"summary": summary, "bytes": path.stat().st_size},
                summary=summary,
            )
        )
    return resources


def first_heading_or_line(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
            if stripped:
                return stripped[:160]
    except OSError:
        return ""
    return ""


def build_mode_resources(source_root: Path) -> list[dict]:
    return build_reference_doc_resources(
        source_root,
        rel_dir="skills/ppt-master/references/modes",
        kind="narrative_mode",
        id_prefix="mode",
        ppt_master_role="deck-level narrative mode",
        svglide_target="deck intent and page rhythm selector",
        conversion_strategy="Derive narrative mode tags and page rhythm signals.",
        normalized_primitives=["deck_intent", "page_rhythm", "story_arc"],
        extra_tags=["narrative", "mode"],
    )


def build_workflow_reference_resources(source_root: Path) -> list[dict]:
    rel_paths = [
        "skills/ppt-master/references/strategist.md",
        "skills/ppt-master/references/executor-base.md",
        "skills/ppt-master/references/visual-review.md",
        "skills/ppt-master/references/shared-standards.md",
        "skills/ppt-master/references/image-layout-patterns.md",
        "skills/ppt-master/references/image-layout-spec.md",
    ]
    resources = []
    for rel_path in rel_paths:
        path = source_root / rel_path
        summary = first_heading_or_line(path)
        resources.append(
            make_resource(
                resource_id=f"workflow.{slug(path.stem)}",
                source_path=path,
                source_root=source_root,
                kind="workflow_reference",
                ppt_master_role="pipeline and quality-gate reference",
                svglide_target="runner receipts, quality gate, and asset planning docs",
                protocol_compatibility="documentation_reference",
                conversion_strategy="Derive process checks, receipt fields, and review heuristics without importing ppt-master as runtime dependency.",
                selection_tags=limited_tags("workflow", path.stem, summary),
                copy_policy="derive_process_contract_only",
                license_status="reference_only",
                granularity="file",
                unsupported_features=[],
                normalized_primitives=["receipt_contract", "quality_gate_signal", "stage_boundary"],
                non_migratable_reason="Workflow references shape implementation rules and are not prompt-time visual assets.",
                risk_flags=["second_protocol_risk"],
                golden_example_required=False,
                metadata={"summary": summary, "bytes": path.stat().st_size if path.exists() else 0},
                summary=summary,
            )
        )
    return resources


def build_image_reference_collections(source_root: Path) -> list[dict]:
    root = source_root / "skills/ppt-master/references/ai-image-comparison"
    collections = [
        ("type", "image_type_visual_references"),
        ("rendering", "image_rendering_visual_references"),
        ("palette", "image_palette_visual_references"),
    ]
    resources = []
    for dirname, role in collections:
        path = root / dirname
        if not path.exists():
            continue
        pngs = image_files(path)
        resources.append(
            make_resource(
                resource_id=f"image_reference_collection.{slug(dirname)}",
                source_path=path,
                source_root=source_root,
                kind="image_reference_collection",
                ppt_master_role=role,
                svglide_target="asset_strategy/reference-oracle",
                protocol_compatibility="reference_only",
                conversion_strategy="Summarize bitmap reference coverage; do not copy images into CLI runtime.",
                selection_tags=limited_tags("image reference", dirname, [p.stem for p in pngs[:20]]),
                copy_policy="derive_contract_only",
                license_status="reference_only",
                granularity="collection_summary",
                unsupported_features=["bitmap_reference_images"],
                normalized_primitives=["asset_strategy_tags", "visual_oracle_labels"],
                non_migratable_reason="Reference PNGs require provenance and authorization before production use.",
                risk_flags=["third_party_image", "runtime_dependency_risk"],
                golden_example_required=False,
                metadata={"image_count": len(pngs), "sample_images": [p.name for p in pngs[:12]]},
                summary=f"{dirname} bitmap reference collection",
            )
        )
    return resources


def build_example_resources(source_root: Path) -> list[dict]:
    examples_root = source_root / "examples"
    resources = []
    for project in direct_dirs(examples_root):
        final_svgs = svg_files(project / "svg_final")
        output_svgs = svg_files(project / "svg_output")
        pages = final_svgs or output_svgs
        media = image_files(project / "images")
        base64_count = count_base64_images(final_svgs + output_svgs)
        notes_count = len(direct_md_files(project / "notes")) if (project / "notes").exists() else 0
        all_project_files = files_under(project)
        unsupported = ["finished_deck_asset"]
        if media:
            unsupported.append("third_party_images")
        if base64_count:
            unsupported.append("embedded_base64_image")
        if list((project / "exports").glob("*.pptx")):
            unsupported.append("pptx_export")
        summary = first_heading_or_line(project / "README.md") or project.name
        resources.append(
            make_resource(
                resource_id=f"example.{slug(project.name)}",
                source_path=project,
                source_root=source_root,
                kind="example_project",
                ppt_master_role="finished example deck and mining corpus",
                svglide_target="golden/negative corpus and style-mining source",
                protocol_compatibility="reference_only",
                conversion_strategy="Mine page rhythm, style signals, and failure cases; do not copy finished pages, images, base64, or PPTX exports.",
                selection_tags=limited_tags("example", project.name, summary, [p.stem for p in pages[:8]]),
                copy_policy="derive_contract_only",
                license_status="reference_only",
                granularity="project_page_media_summary",
                unsupported_features=unsupported,
                normalized_primitives=["page_rhythm", "layout_family_labels", "style_signals", "negative_corpus_signals"],
                non_migratable_reason="Example projects are finished artifacts with generated images, possible third-party media, base64, and PPTX exports.",
                risk_flags=["third_party_image", "base64_asset", "finished_deck_copy_risk"],
                golden_example_required=False,
                metadata={
                    "summary": summary,
                    "page_count": len(pages),
                    "svg_final_count": len(final_svgs),
                    "svg_output_count": len(output_svgs),
                    "media_count": len(media),
                    "base64_count": base64_count,
                    "notes_count": notes_count,
                    "pptx_export_count": len(list((project / "exports").glob("*.pptx"))) if (project / "exports").exists() else 0,
                    "page_samples": [p.name for p in pages[:10]],
                    "media_samples": [p.name for p in media[:10]],
                    "project_digest": digest_paths(source_root, all_project_files),
                },
                summary=summary,
            )
        )
    return resources


def build_asset_map(source_root: Path) -> dict:
    source_root = source_root.resolve()
    if not source_root.exists():
        raise InventoryError(f"ppt-master source does not exist: {source_root}")

    resources: list[dict] = []
    resources.extend(build_brand_resources(source_root))
    resources.extend(build_layout_resources(source_root))
    resources.extend(build_deck_resources(source_root))
    resources.extend(build_chart_resources(source_root))
    resources.extend(build_icon_resources(source_root))
    resources.extend(
        build_reference_doc_resources(
            source_root,
            rel_dir="skills/ppt-master/references/visual-styles",
            kind="visual_style",
            id_prefix="visual_style",
            ppt_master_role="visual style guide",
            svglide_target="style-presets.json/quality-oracle",
            conversion_strategy="Derive style tags, visual anti-patterns, and quality-oracle signals.",
            normalized_primitives=["style_tags", "forbidden_patterns", "quality_oracle"],
            extra_tags=["style", "visual"],
        )
    )
    resources.extend(
        build_reference_doc_resources(
            source_root,
            rel_dir="skills/ppt-master/references/image-palettes",
            kind="image_palette",
            id_prefix="image_palette",
            ppt_master_role="image palette reference",
            svglide_target="asset_strategy/image-palette-binding",
            conversion_strategy="Derive palette tags and image-planning hints; do not copy generated images.",
            normalized_primitives=["palette_tags", "image_style_binding"],
            extra_tags=["image", "palette"],
        )
    )
    resources.extend(
        build_reference_doc_resources(
            source_root,
            rel_dir="skills/ppt-master/references/image-renderings",
            kind="image_rendering",
            id_prefix="image_rendering",
            ppt_master_role="image rendering preset",
            svglide_target="asset_strategy/rendering-preset",
            conversion_strategy="Derive rendering tags and fallback policy for image planning.",
            normalized_primitives=["rendering_tags", "fallback_policy"],
            extra_tags=["image", "rendering"],
        )
    )
    resources.extend(
        build_reference_doc_resources(
            source_root,
            rel_dir="skills/ppt-master/references/image-type-templates",
            kind="image_type_template",
            id_prefix="image_type",
            ppt_master_role="image composition recipe",
            svglide_target="asset_strategy/image-composition-recipe",
            conversion_strategy="Derive image composition contracts and prompt planning tags.",
            normalized_primitives=["composition_recipe", "asset_slots"],
            extra_tags=["image", "composition"],
        )
    )
    resources.extend(build_mode_resources(source_root))
    resources.extend(build_example_resources(source_root))
    resources.extend(build_workflow_reference_resources(source_root))
    resources.extend(build_image_reference_collections(source_root))
    resources.sort(key=lambda item: item["id"])

    counts = Counter(resource["kind"] for resource in resources)
    icon_svg_count = sum(resource.get("metadata", {}).get("icon_count", 0) for resource in resources)
    example_page_count = sum(resource.get("metadata", {}).get("page_count", 0) for resource in resources)
    example_media_count = sum(resource.get("metadata", {}).get("media_count", 0) for resource in resources)
    all_source_files = files_under(source_root)
    asset_map = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": source_root.name,
        "generation_policy": {
            "runtime_dependency": "none",
            "raw_svg_default": {
                "protocol_compatibility": "needs_normalization",
                "copy_policy": "derive_contract_only",
                "license_status": "reference_only",
                "activation_status": "candidate",
            },
            "icon_policy": "library_summary_and_searchable_index_only",
            "example_policy": "project_page_media_summary_only",
        },
        "summary": {
            "counts": {
                **dict(sorted(counts.items())),
                "total_resources": len(resources),
                "icon_svg_files": icon_svg_count,
                "example_pages": example_page_count,
                "example_media_files": example_media_count,
            },
            "digests": {
                "all_source_files": digest_paths(source_root, all_source_files),
                "brands": digest_paths(source_root, files_under(source_root / "skills/ppt-master/templates/brands")),
                "layouts": digest_paths(source_root, files_under(source_root / "skills/ppt-master/templates/layouts")),
                "decks": digest_paths(source_root, files_under(source_root / "skills/ppt-master/templates/decks")),
                "charts": digest_paths(source_root, files_under(source_root / "skills/ppt-master/templates/charts")),
                "icons": digest_paths(source_root, files_under(source_root / "skills/ppt-master/templates/icons")),
                "references": digest_paths(source_root, files_under(source_root / "skills/ppt-master/references")),
                "examples": digest_paths(source_root, files_under(source_root / "examples")),
            },
        },
        "resources": resources,
    }
    validate_asset_map(asset_map)
    return asset_map


def validate_asset_map(asset_map: dict) -> None:
    if asset_map.get("schema_version") != SCHEMA_VERSION:
        raise InventoryError("unexpected schema_version")
    resources = asset_map.get("resources")
    if not isinstance(resources, list) or not resources:
        raise InventoryError("asset map has no resources")

    counts = Counter()
    for index, resource in enumerate(resources):
        missing = REQUIRED_FIELDS - set(resource)
        if missing:
            raise InventoryError(f"resource[{index}] missing fields: {sorted(missing)}")
        counts[resource["kind"]] += 1
        if resource["activation_status"] == "rejected" and not resource["non_migratable_reason"]:
            raise InventoryError(f"{resource['id']} is rejected without a reason")
        if resource["activation_status"] == "active" and not resource["golden_example_required"]:
            raise InventoryError(f"{resource['id']} active resources must require golden examples")
        raw_like = (
            resource["source_path"].endswith(".svg")
            or resource.get("metadata", {}).get("svg_file_count", 0)
            or resource.get("metadata", {}).get("raw_svg_file_count", 0)
            or "raw_svg_icon_files" in resource["unsupported_features"]
        )
        if raw_like and resource["protocol_compatibility"] == "needs_normalization":
            if resource["copy_policy"] != "derive_contract_only":
                raise InventoryError(f"{resource['id']} raw SVG must use derive_contract_only")
            if resource["license_status"] != "reference_only":
                raise InventoryError(f"{resource['id']} raw SVG must be reference_only")
            if resource["activation_status"] in {"validated", "active"}:
                raise InventoryError(f"{resource['id']} raw SVG cannot start as validated/active")
        for field in ("selection_tags", "unsupported_features", "normalized_primitives", "risk_flags"):
            if not isinstance(resource[field], list):
                raise InventoryError(f"{resource['id']} field {field} must be a list")

    missing_kinds = sorted(REQUIRED_KINDS - set(counts))
    if missing_kinds:
        raise InventoryError(f"inventory missing required resource kinds: {missing_kinds}")


def render_markdown(asset_map: dict) -> str:
    counts = asset_map["summary"]["counts"]
    digests = asset_map["summary"]["digests"]
    resources = asset_map["resources"]
    lines = [
        "# ppt-master Asset Inventory",
        "",
        "This file is generated by `skills/lark-slides/scripts/ppt_master_asset_inventory.py`.",
        "The JSON asset map is the source of truth; this Markdown is a human-readable summary.",
        "",
        "## Safety Defaults",
        "",
        "- Raw ppt-master SVG assets start as `needs_normalization`, `derive_contract_only`, `reference_only`, and `candidate`.",
        "- Icon assets are summarized by library and searchable index metadata; individual icon SVG files are not injected into the main prompt.",
        "- Examples are summarized by project/page/media counts and treated as reference corpus, not runtime assets.",
        "- Production/golden selection must not use rejected, reference-only, or raw unnormalized assets.",
        "",
        "## Counts",
        "",
        "| Kind | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Digests", "", "| Scope | SHA-256 prefix |", "| --- | --- |"])
    for key, value in sorted(digests.items()):
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(["", "## Resource Summary", "", "| Kind | Example IDs |", "| --- | --- |"])
    by_kind: dict[str, list[str]] = {}
    for resource in resources:
        by_kind.setdefault(resource["kind"], []).append(resource["id"])
    for kind, ids in sorted(by_kind.items()):
        preview = ", ".join(f"`{item}`" for item in ids[:8])
        if len(ids) > 8:
            preview += f", ... (+{len(ids) - 8})"
        lines.append(f"| `{kind}` | {preview} |")

    lines.extend(["", "## Example Corpus", "", "| Example | Pages | Media | Base64 | Digest |", "| --- | ---: | ---: | ---: | --- |"])
    for resource in resources:
        if resource["kind"] != "example_project":
            continue
        metadata = resource.get("metadata", {})
        lines.append(
            f"| `{resource['id']}` | {metadata.get('page_count', 0)} | {metadata.get('media_count', 0)} | "
            f"{metadata.get('base64_count', 0)} | `{metadata.get('project_digest', '')}` |"
        )

    lines.extend(["", "## Icon Libraries", "", "| Library | Icons | Policy |", "| --- | ---: | --- |"])
    for resource in resources:
        if resource["kind"] != "icon_library":
            continue
        metadata = resource.get("metadata", {})
        lines.append(f"| `{resource['id']}` | {metadata.get('icon_count', 0)} | {metadata.get('index_policy', '')} |")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the SVGlide ppt-master asset inventory.")
    parser.add_argument("--source", type=Path, default=default_source_root(), help="Path to the local ppt-master checkout.")
    parser.add_argument("--out-json", type=Path, help="Output path for ppt-master-asset-map.json.")
    parser.add_argument("--out-md", type=Path, help="Output path for ppt-master-asset-inventory.md.")
    parser.add_argument("--check", action="store_true", help="Validate the source and generated map without writing files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    asset_map = build_asset_map(args.source)
    if args.check:
        print(json.dumps(asset_map["summary"], ensure_ascii=False, indent=2))
        return 0
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(asset_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(asset_map), encoding="utf-8")
    if not args.out_json and not args.out_md:
        print(json.dumps(asset_map, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
