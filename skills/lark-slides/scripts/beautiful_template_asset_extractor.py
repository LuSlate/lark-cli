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
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
LARK_SLIDES_DIR = SCRIPT_DIR.parent
CLI_ROOT = LARK_SLIDES_DIR.parent.parent
REFERENCES_DIR = LARK_SLIDES_DIR / "references"
INVENTORY_PATH = REFERENCES_DIR / "svglide-reference-source-inventory.json"
ABSORPTION_DIR = REFERENCES_DIR / "absorptions" / "beautiful-html-templates"
FAMILIES_PATH = REFERENCES_DIR / "beautiful-html-template-families.json"
DEFAULT_SOURCE_ROOTS = [
    CLI_ROOT / "beautiful-html-templates",
    CLI_ROOT.parent / "beautiful-html-templates",
    Path("/Users/bytedance/bd-projects/beautiful-html-templates"),
]

DEFAULT_VARIANTS = [
    "cover",
    "agenda",
    "section_divider",
    "context_overview",
    "metric_dashboard",
    "problem_analysis",
    "cause_analysis",
    "comparison",
    "timeline",
    "case_evidence",
    "action_plan",
    "risk_dependency",
    "closing",
]

DEFAULT_COMPONENTS = [
    "title_block",
    "section_label",
    "metric_card",
    "finding_callout",
    "evidence_table",
    "comparison_matrix",
    "timeline",
    "process_flow",
    "image_panel",
    "logo_strip",
    "mini_chart",
    "qualitative_radar",
    "action_list",
    "risk_matrix",
    "architecture_diagram",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(CLI_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_source_root(source_root: str | None = None) -> Path:
    candidates = [Path(source_root)] if source_root else DEFAULT_SOURCE_ROOTS
    for candidate in candidates:
        if candidate and (candidate / "index.json").exists() and (candidate / "templates").is_dir():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"beautiful-html-templates source root not found. Searched: {searched}")


def words(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [part.strip() for part in re.split(r"[,;/|]", str(value)) if part.strip()]


def parse_design_blocks(design_md: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in design_md.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#") or line.strip() == "---":
            continue
        top_match = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*):\s*$", line)
        if top_match:
            current = top_match.group(1).replace("-", "_")
            blocks.setdefault(current, {})
            continue
        if current is None:
            continue
        kv_match = re.match(r"^\s{2}([a-zA-Z0-9_-]+):\s*(.+?)\s*$", line)
        if not kv_match:
            continue
        key = kv_match.group(1).replace("-", "_")
        value = kv_match.group(2).strip().strip('"')
        blocks[current][key] = value
    return blocks


def css_variables(template_html: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, value in re.findall(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);", template_html):
        result[name.replace("-", "_")] = value.strip()
    return result


def css_class_names(template_html: str) -> list[str]:
    names: set[str] = set()
    for raw in re.findall(r'class="([^"]+)"', template_html):
        for name in raw.split():
            if name:
                names.add(name)
    return sorted(names)


def html_layout_variants(template_html: str) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for class_name in css_class_names(template_html):
        if not class_name.startswith("layout-"):
            continue
        variant_id = class_name.removeprefix("layout-").replace("-", "_")
        if variant_id in seen:
            continue
        seen.add(variant_id)
        variants.append(
            {
                "variant_id": variant_id,
                "source_class": class_name,
                "layout_intents": [variant_id.replace("_", "-")],
                "required_slots": ["title", "key_message"],
                "component_candidates": ["title_block", "section_label"],
            }
        )
    return variants


def first_value(mapping: dict[str, Any], keys: list[str], fallback_values: list[str]) -> str:
    for key in keys:
        value = mapping.get(key) or mapping.get(key.replace("_", "-"))
        if value:
            return str(value)
    for value in fallback_values:
        if value:
            return value
    return "#000000"


def palette_roles_from_tokens(palette: dict[str, Any], color_tokens: dict[str, str], css_tokens: dict[str, str]) -> dict[str, str]:
    merged: dict[str, Any] = {}
    merged.update(css_tokens)
    merged.update(color_tokens)
    merged.update(palette)
    values = [str(value) for key, value in merged.items() if key != "description" and str(value).strip()]
    return {
        "background": first_value(merged, ["background", "bg", "paper", "cream", "primary"], values),
        "surface": first_value(merged, ["surface", "card_bg", "card-bg", "cream", "gray"], values),
        "primary": first_value(merged, ["primary", "accent", "ink", "blue"], values),
        "accent": first_value(merged, ["accent", "primary", "pink", "red", "green"], values),
        "text": first_value(merged, ["text", "ink"], values),
        "muted": first_value(merged, ["text_muted", "text-muted", "muted", "gray"], values),
        "border": first_value(merged, ["border", "primary", "ink"], values),
        "positive": first_value(merged, ["positive", "green"], values),
        "negative": first_value(merged, ["negative", "red"], values),
    }


def inventory_slug(item: dict[str, Any]) -> str:
    slug = str(item.get("template_slug") or "").strip()
    if slug:
        return slug
    item_id = str(item.get("id") or "")
    match = re.search(r"beautiful-html-templates\.template\.([^.]+)\.", item_id)
    if match:
        return match.group(1)
    rel_path = str(item.get("source_repo_relative_path") or item.get("source_path") or "")
    match = re.search(r"(?:templates|screenshots)/([a-z0-9-]+)(?:/|-)", rel_path)
    return match.group(1) if match else ""


def load_inventory_by_slug(path: Path = INVENTORY_PATH) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    payload = load_json(path)
    items = payload.get("items", [])
    if not isinstance(items, list):
        return {}
    by_slug: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict) or item.get("source_repo") != "beautiful-html-templates":
            continue
        slug = inventory_slug(item)
        if slug:
            by_slug.setdefault(slug, []).append(item)
    return by_slug


def load_absorptions_by_slug(path: Path = ABSORPTION_DIR) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return load_absorptions_from_family_registry()
    by_slug: dict[str, list[dict[str, Any]]] = {}
    for record_path in sorted(path.glob("*.json")):
        record = load_json(record_path)
        source_item_id = str(record.get("source_item_id") or "")
        match = re.search(r"beautiful-html-templates\.template\.([^.]+)\.", source_item_id)
        slug = match.group(1) if match else record_path.name.split(".", 1)[0]
        record["_record_path"] = repo_relative(record_path)
        by_slug.setdefault(slug, []).append(record)
    return by_slug or load_absorptions_from_family_registry()


def load_absorptions_from_family_registry(path: Path = FAMILIES_PATH) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    payload = load_json(path)
    families = payload.get("families", [])
    if not isinstance(families, list):
        return {}
    by_slug: dict[str, list[dict[str, Any]]] = {}
    for family in families:
        if not isinstance(family, dict) or family.get("status") != "absorbed":
            continue
        slug = str(family.get("template_id") or "").strip()
        source = family.get("source") if isinstance(family.get("source"), dict) else {}
        mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
        provenance = source.get("absorption_provenance") or mapping.get("absorption_provenance") or []
        if not slug or not isinstance(provenance, list):
            continue
        records: list[dict[str, Any]] = []
        for item in provenance:
            if not isinstance(item, dict):
                continue
            record = dict(item)
            record["_record_path"] = str(item.get("path") or "")
            record["source_item_id"] = str(item.get("source_item_id") or "")
            record["absorbed_as"] = [str(value) for value in item.get("absorbed_as", []) if str(value)]
            record["svglide_asset_ids"] = [str(value) for value in item.get("svglide_asset_ids", []) if str(value)]
            record["source_context_refs"] = [str(value) for value in item.get("source_context_refs", []) if str(value)]
            records.append(record)
        if records:
            by_slug[slug] = records
    return by_slug


def disposition_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(item.get("disposition") or "unknown") for item in items))


def source_type_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(item.get("source_type") or "unknown") for item in items))


def classify_industries(text: str) -> list[str]:
    checks = [
        ("B2B SaaS", r"saas|software|developer|tool"),
        ("consulting", r"consulting|advisory|strategy|briefing"),
        ("finance and investor relations", r"investor|finance|financial|quarterly|disclosure"),
        ("culture and arts", r"art|museum|exhibition|biennale|curatorial|literary|zine"),
        ("education and training", r"education|training|course|lesson|workshop"),
        ("consumer brand", r"brand|campaign|marketing|launch|community|food|restaurant"),
        ("gaming and hackathon", r"game|gaming|hackathon|web3|crypto|arcade"),
    ]
    result = [label for label, pattern in checks if re.search(pattern, text, re.IGNORECASE)]
    return result or ["general presentation"]


def classify_decorative_motifs(text: str) -> list[str]:
    checks = [
        ("grid", r"grid|matrix|table|cell"),
        ("accent line", r"line|rule|divider|border"),
        ("card panels", r"card|panel|tile"),
        ("paper texture", r"paper|parchment|grain|texture"),
        ("window chrome", r"window|browser|desktop|retro"),
        ("poster blocks", r"poster|block|frame|border"),
        ("quote mark", r"quote|editorial"),
        ("sticker collage", r"pin|sticker|collage|zine"),
        ("pixel motif", r"pixel|arcade|8-bit|crt"),
    ]
    result = [label for label, pattern in checks if re.search(pattern, text, re.IGNORECASE)]
    return result or ["family accent motif", "card panels"]


def classify_visual_effects(text: str) -> list[dict[str, str]]:
    effect_specs = [
        ("tinted_card", "native_svg", r"card|panel|tint|surface"),
        ("accent_rule", "native_svg", r"line|rule|divider|border"),
        ("soft_shadow", "approximate", r"shadow|elevation"),
        ("gradient_accent", "css_to_satori", r"gradient|radial|glow"),
        ("image_crop", "native_svg", r"image|photo|mask|crop"),
        ("paper_texture", "approximate", r"paper|grain|texture"),
        ("window_chrome", "native_svg", r"window|browser|chrome"),
        ("bold_border", "native_svg", r"brutalist|border|frame"),
    ]
    effects: list[dict[str, str]] = []
    for effect_id, lowering_policy, pattern in effect_specs:
        if re.search(pattern, text, re.IGNORECASE):
            effects.append(
                {
                    "effect_id": effect_id,
                    "lowering_policy": lowering_policy,
                    "notes": f"Derived from beautiful-html-template source signal: {effect_id}.",
                }
            )
    if not effects:
        effects.append(
            {
                "effect_id": "tinted_card",
                "lowering_policy": "native_svg",
                "notes": "Default static card effect for family candidate.",
            }
        )
    return effects


def screenshot_paths(source_root: Path, slug: str) -> list[str]:
    screenshot_dir = source_root / "screenshots"
    matches = sorted(screenshot_dir.glob(f"{slug}*.png"))
    return [f"beautiful-html-templates/screenshots/{path.name}" for path in matches[:3]]


def readme_gallery_by_slug(source_root: Path) -> dict[str, list[str]]:
    readme = source_root / "README.md"
    if not readme.exists():
        return {}
    by_slug: dict[str, list[str]] = {}
    for match in re.finditer(r"\./screenshots/([a-z0-9-]+-\d+\.png)", readme.read_text(encoding="utf-8")):
        name = match.group(1)
        slug = re.sub(r"-\d+\.png$", "", name)
        by_slug.setdefault(slug, []).append(f"beautiful-html-templates/screenshots/{name}")
    return {slug: paths[:3] for slug, paths in by_slug.items() if paths}


def screenshot_slide_number(path: str) -> int:
    match = re.search(r"-(\d+)\.png$", path)
    return int(match.group(1)) if match else 0


def screenshot_benchmarks(source_root: Path, slug: str, template_json: dict[str, Any], visual_targets: list[str], gallery_by_slug: dict[str, list[str]]) -> list[dict[str, Any]]:
    paths = gallery_by_slug.get(slug) or screenshot_paths(source_root, slug)
    roles = ["cover_reference", "mid_deck_reference", "late_deck_reference"]
    tagline = str(template_json.get("tagline") or template_json.get("description") or template_json.get("best_for") or slug)
    out: list[dict[str, Any]] = []
    for index, path in enumerate(paths[:3]):
        role = roles[index] if index < len(roles) else "reference"
        out.append(
            {
                "path": path,
                "role": role,
                "slide_number": screenshot_slide_number(path),
                "why_selected": f"README gallery {role.replace('_', ' ')} for {slug}: {tagline[:180]}",
                "visual_targets": visual_targets[:6] or ["palette", "type_scale", "chrome", "density", "layout_balance"],
                "acceptance_use": ["matcher_thumbnail", "visual_qa", "few_shot_reference"],
            }
        )
    return out


def markdown_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    start: int | None = None
    start_level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        if match.group(2).strip().lower() == heading.lower():
            start = index
            start_level = len(match.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{2,6})\s+", lines[index])
        if match and len(match.group(1)) <= start_level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def first_section_paragraph(section: str, heading: str) -> str:
    subsection = markdown_section(section, heading)
    if not subsection:
        return ""
    chunks = []
    for raw in subsection.splitlines()[1:]:
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("```"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        chunks.append(line)
        if len(" ".join(chunks)) > 240:
            break
    return " ".join(chunks)[:360]


CJK_FONT_PATTERNS = [
    r"Noto\s+(?:Sans|Serif)\s+(?:SC|TC|JP|CJK)",
    r"Source\s+Han\s+(?:Sans|Serif)",
    r"LXGW\s+[A-Za-z ]+",
    r"ZCOOL\s+[A-Za-z]+",
    r"PingFang\s+SC",
    r"Microsoft\s+YaHei",
    r"SimHei",
    r"SimSun",
    r"Yozai",
    r"悠哉字体\s*Yozai",
    r"霞鹜[^|,，。)）`*]+",
    r"站酷[^|,，。)）`*]+",
]


def clean_font_name(value: str) -> str:
    cleaned = re.sub(r"[`*_\"'()（）\[\]]", "", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:80]


def cjk_font_candidates(cjk_section: str) -> list[str]:
    candidates: list[str] = []
    for pattern in CJK_FONT_PATTERNS:
        for match in re.finditer(pattern, cjk_section, flags=re.IGNORECASE):
            name = clean_font_name(match.group(0))
            if name and name.lower() not in {item.lower() for item in candidates}:
                candidates.append(name)
    return candidates


def classify_italic_policy(cjk_section: str, full_design: str) -> str:
    text = f"{cjk_section}\n{full_design}".lower()
    if re.search(r"never italic|no italic|drop italic|italic does not exist|fake italic|oblique", text):
        return "drop_italic"
    if re.search(r"color shift|color-only|color only|emphasis.*color", text):
        return "color_only_emphasis"
    if re.search(r"weight|bold", text):
        return "weight_only_emphasis"
    return "latin_only"


def classify_letter_spacing_policy(cjk_section: str) -> str:
    text = cjk_section.lower()
    if re.search(r"letter-spacing|tracking|tracked|uppercase|text-transform", text):
        return "reset_letter_spacing_for_cjk_keep_latin_labels"
    return "reset_letter_spacing_for_cjk"


def extract_cjk_policy(design_md: str, template_json: dict[str, Any]) -> dict[str, Any]:
    cjk_section = markdown_section(design_md, "CJK & International Content")
    fonts = cjk_font_candidates(cjk_section)
    display_font = fonts[0] if fonts else "Noto Sans SC"
    body_font = fonts[1] if len(fonts) > 1 else display_font
    known_gap = first_section_paragraph(cjk_section, "Known CJK Gap") or first_section_paragraph(cjk_section, "Aesthetic Notes")
    if not known_gap:
        known_gap = "Preserve the family rhythm while replacing unsafe remote CJK font loading with SVGlide system font roles."
    italic_policy = classify_italic_policy(cjk_section, design_md)
    emphasis_policy = "color_or_weight_only" if italic_policy != "latin_only" else "latin_only_emphasis"
    return {
        "strategy": "replace_family_whole_element" if fonts else "single_cjk_family_all_roles",
        "display_font_cn": display_font,
        "body_font_cn": body_font,
        "mono_font_policy": "latin_only_or_system_mono",
        "runtime_font_policy": "system_font_only_no_remote_dependency",
        "runtime_font_stack": ["system-sans-cjk", "system-sans-cjk-heavy", "system-sans-cjk-regular", "system-mono"],
        "emphasis_policy": emphasis_policy,
        "italic_policy": italic_policy,
        "letter_spacing_policy": classify_letter_spacing_policy(cjk_section),
        "mixed_run_spacing": "pangu_spacing" if re.search(r"Pangu|盘古", cjk_section, re.IGNORECASE) else "none_required",
        "latin_accent_policy": "latin_only_allowed_when_semantic_annotation",
        "known_degradation": known_gap,
        "design_intent_font_pairing": fonts[:6],
        "source_section_heading": "CJK & International Content",
        "source_section_sha256": hashlib.sha256(cjk_section.encode("utf-8")).hexdigest(),
    }


def extract_family_usage_policy(agents_md: str) -> dict[str, Any]:
    return {
        "closed_visual_system": True,
        "cross_family_layout_mix_allowed": False,
        "recolor_allowed": False,
        "font_substitution_allowed": False,
        "decorative_elements_policy": "identity_element_not_noise",
        "extend_missing_layout_policy": {
            "same_fonts": True,
            "same_palette": True,
            "same_spacing_rhythm": True,
            "same_component_grammar": True,
            "same_decorative_vocabulary": True,
            "same_chrome": True,
        },
        "soft_matching_policy": {
            "tone_first": True,
            "occasion_is_soft_signal": True,
            "avoid_for_is_soft_warning": True,
            "taste_can_override_industry": True,
            "formality_density_as_sanity_check": True,
        },
        "hard_rules": [
            "preserve_fonts_palette_grid_slide_classes_decorative_elements",
            "do_not_recolor_without_explicit_brand_override",
            "do_not_mix_template_families",
            "extend_missing_layout_inside_same_family",
            "do_not_strip_identity_decorations",
        ],
        "source": "beautiful-html-templates/AGENTS.md",
        "source_sha256": hashlib.sha256(agents_md.encode("utf-8")).hexdigest(),
    }


def extract_extension_grammar(
    slug: str,
    template_json: dict[str, Any],
    design_blocks: dict[str, dict[str, str]],
    class_names: list[str],
    combined_text: str,
) -> dict[str, Any]:
    density = str(template_json.get("density") or "medium")
    formality = str(template_json.get("formality") or "medium")
    tagline = str(template_json.get("tagline") or template_json.get("description") or template_json.get("best_for") or slug)
    component_tokens = sorted(
        {
            token
            for token in (
                list(design_blocks.get("components", {}).keys())
                + [name.removeprefix("layout-") for name in class_names if name.startswith(("layout-", "s-", "card", "panel", "stat"))]
            )
            if token
        }
    )
    chrome = [name for name in class_names if re.search(r"footer|page|number|chrome|label|eyebrow|nav|badge|stamp", name)]
    motifs = classify_decorative_motifs(combined_text)
    return {
        "layout_rhythm": f"{slug}: {density} density, {formality} formality. {tagline[:180]}",
        "spacing_rhythm": "Reuse source spacing tokens and grid gaps: " + json.dumps(design_blocks.get("spacing", {}), ensure_ascii=False)[:220],
        "component_grammar": component_tokens[:10] or DEFAULT_COMPONENTS[:6],
        "chrome_rules": chrome[:8] or ["preserve family header/footer labels", "preserve page-number rhythm", "no unrelated chrome"],
        "decorative_vocabulary": motifs,
        "allowed_new_layouts": ["comparison", "risk", "timeline", "action_plan", "case_evidence", "metric_dashboard"],
        "forbidden_mutations": ["new_palette", "cross_family_components", "fake_italic", "new_decorative_motif", "remote_font_dependency"],
        "density_limits": density,
        "source_basis": {
            "template_id": slug,
            "design_signal_sha256": hashlib.sha256(combined_text[:12000].encode("utf-8")).hexdigest(),
            "class_name_count": len(class_names),
        },
    }


def variant_record(variant_id: str) -> dict[str, Any]:
    role_map = {
        "cover": ["cover"],
        "agenda": ["agenda"],
        "section_divider": ["section"],
        "context_overview": ["context_overview"],
        "metric_dashboard": ["metric_overview", "business_review"],
        "problem_analysis": ["problem_analysis"],
        "cause_analysis": ["cause_analysis"],
        "comparison": ["comparison"],
        "timeline": ["timeline", "roadmap"],
        "case_evidence": ["case_evidence"],
        "action_plan": ["action_plan"],
        "risk_dependency": ["risk_dependency"],
        "closing": ["closing"],
    }
    component_map = {
        "metric_dashboard": ["metric_card", "mini_chart", "finding_callout"],
        "problem_analysis": ["finding_callout", "evidence_table"],
        "cause_analysis": ["process_flow", "finding_callout"],
        "comparison": ["comparison_matrix", "evidence_table"],
        "timeline": ["timeline", "process_flow"],
        "case_evidence": ["image_panel", "finding_callout"],
        "action_plan": ["action_list", "risk_matrix"],
        "risk_dependency": ["risk_matrix", "action_list"],
    }
    return {
        "variant_id": variant_id,
        "page_roles": role_map.get(variant_id, [variant_id]),
        "layout_intents": [variant_id.replace("_", "-")],
        "required_slots": ["title", "key_message"],
        "optional_slots": ["image", "metrics", "evidence", "source_note"],
        "component_candidates": component_map.get(variant_id, ["title_block", "section_label"]),
    }


def extract_family(
    source_root: Path,
    slug: str,
    inventory_by_slug: dict[str, list[dict[str, Any]]] | None = None,
    absorptions_by_slug: dict[str, list[dict[str, Any]]] | None = None,
    agents_md: str = "",
    gallery_by_slug: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    template_dir = source_root / "templates" / slug
    template_json = load_json(template_dir / "template.json")
    design_md = (template_dir / "design.md").read_text(encoding="utf-8")
    template_html = (template_dir / "template.html").read_text(encoding="utf-8")
    inventory_items = (inventory_by_slug or {}).get(slug, [])
    absorption_records = (absorptions_by_slug or {}).get(slug, [])
    absorbed_as = sorted({str(item) for record in absorption_records for item in record.get("absorbed_as", []) if str(item)})
    svglide_asset_ids = sorted({str(item) for record in absorption_records for item in record.get("svglide_asset_ids", []) if str(item)})
    source_context_refs = sorted({str(item) for record in absorption_records for item in record.get("source_context_refs", []) if str(item)})
    absorption_paths = [str(record.get("_record_path")) for record in absorption_records if record.get("_record_path")]
    source_item_ids = sorted({str(record.get("source_item_id")) for record in absorption_records if record.get("source_item_id")})
    absorption_provenance = [
        {
            "path": str(record.get("_record_path")),
            "source_item_id": str(record.get("source_item_id") or ""),
            "absorbed_as": [str(item) for item in record.get("absorbed_as", [])],
            "svglide_asset_ids": [str(item) for item in record.get("svglide_asset_ids", [])],
            "source_context_refs": [str(item) for item in record.get("source_context_refs", [])],
            "sha256": str(record.get("sha256") or "")
            or (file_sha256(CLI_ROOT / str(record.get("_record_path"))) if record.get("_record_path") and (CLI_ROOT / str(record.get("_record_path"))).exists() else ""),
        }
        for record in absorption_records
    ]
    status = "absorbed" if absorption_records else "source_inventoried"
    claim_level = "svglide_absorbed" if absorption_records else "source_inventory_only"
    combined = "\n".join(
        [
            json.dumps(template_json, ensure_ascii=False),
            design_md[:8000],
            template_html[:8000],
        ]
    )
    palette = template_json.get("palette") if isinstance(template_json.get("palette"), dict) else {}
    typography = template_json.get("typography") if isinstance(template_json.get("typography"), dict) else {}
    design_blocks = parse_design_blocks(design_md)
    css_tokens = css_variables(template_html)
    class_names = css_class_names(template_html)
    layout_variants = html_layout_variants(template_html)
    screenshots = (gallery_by_slug or {}).get(slug) or screenshot_paths(source_root, slug)
    palette_roles = palette_roles_from_tokens(palette, design_blocks.get("colors", {}), css_tokens)
    visual_targets = ["palette", "type_scale", "chrome", "density", "layout_balance"] + classify_decorative_motifs(combined)[:2]
    return {
        "template_id": slug,
        "source": {
            "source_repo": "beautiful-html-templates",
            "source_template_json": f"beautiful-html-templates/templates/{slug}/template.json",
            "source_design_md": f"beautiful-html-templates/templates/{slug}/design.md",
            "source_template_html": f"beautiful-html-templates/templates/{slug}/template.html",
            "source_screenshots": screenshots,
            "reference_screenshot": screenshots[0] if screenshots else "",
            "reference_svg": "",
            "receipt": "",
            "inventory_item_ids": [str(item.get("id")) for item in inventory_items if item.get("id")],
            "inventory_source_type_counts": source_type_counts(inventory_items),
            "inventory_disposition_counts": disposition_counts(inventory_items),
            "absorption_records": absorption_paths,
            "source_item_ids": source_item_ids,
            "absorption_provenance": absorption_provenance,
            "source_context_refs": source_context_refs,
        },
        "status": status,
        "claim_level": claim_level,
        "runtime_policy": {
            "direct_satori_svg_allowed": False,
            "requires_contract_compile": True,
            "requires_visual_qa": True,
        },
        "font_policy": {
            "original_families": words(typography.get("display")) + words(typography.get("body")),
            "fallback_stack": "system-sans-cjk",
            "font_role_map": {
                "display": "system-sans-cjk-heavy",
                "body": "system-sans-cjk-regular",
                "metric": "system-sans-cjk-heavy",
                "label": "system-sans-cjk-medium",
                "mono": "system-mono",
            },
        },
        "cjk_policy": extract_cjk_policy(design_md, template_json),
        "family_usage_policy": extract_family_usage_policy(agents_md),
        "extension_grammar": extract_extension_grammar(slug, template_json, design_blocks, class_names, combined),
        "semantic_fit": {
            "best_for": words(template_json.get("best_for")) or words(template_json.get("occasion")),
            "industries": classify_industries(combined),
            "tones": words(template_json.get("tone")) + words(template_json.get("mood")),
            "formality": str(template_json.get("formality") or "medium"),
            "density": str(template_json.get("density") or "medium"),
            "avoid_when": words(template_json.get("avoid_for")),
        },
        "design_tokens": {
            "colors": design_blocks.get("colors", {}),
            "typography": design_blocks.get("typography", {}) or {str(key): str(value) for key, value in typography.items()},
            "spacing": design_blocks.get("spacing", {}),
            "radii": design_blocks.get("radii", {}),
            "components": design_blocks.get("components", {}),
            "css_variables": css_tokens,
            "css_class_names": class_names,
        },
        "visual_dna": {
            "palette_roles": palette_roles,
            "typography_role": typography.get("style") or "source-defined typography roles lowered to system fonts",
            "typography_roles": {
                "display": typography.get("display") or "system-sans-cjk-heavy",
                "body": typography.get("body") or "system-sans-cjk-regular",
                "metric": "display numeric emphasis -> system-sans-cjk-heavy",
                "label": "compact label -> system-sans-cjk-medium",
                "caption": "small caption -> system-sans-cjk-regular",
            },
            "decorative_motifs": classify_decorative_motifs(combined),
            "visual_effects": classify_visual_effects(combined),
            "screenshot_benchmarks": screenshot_benchmarks(source_root, slug, template_json, visual_targets, gallery_by_slug or {}),
            "density": str(template_json.get("density") or "medium"),
        },
        "svglide_mapping": {
            "absorbed_as": absorbed_as,
            "svglide_asset_ids": svglide_asset_ids,
            "source_context_refs": source_context_refs,
            "absorption_records": absorption_paths,
            "source_item_ids": source_item_ids,
            "absorption_provenance": absorption_provenance,
        },
        "component_candidates": DEFAULT_COMPONENTS,
        "layout_variants": layout_variants or [variant_record(variant_id) for variant_id in DEFAULT_VARIANTS],
        "variants": [variant_record(variant_id) for variant_id in DEFAULT_VARIANTS],
    }


def extract_registry(source_root: str | None = None) -> dict[str, Any]:
    root = resolve_source_root(source_root)
    index = load_json(root / "index.json")
    templates = index.get("templates", [])
    slugs = sorted(str(item.get("slug")) for item in templates if item.get("slug"))
    inventory_by_slug = load_inventory_by_slug()
    absorptions_by_slug = load_absorptions_by_slug()
    agents_md = (root / "AGENTS.md").read_text(encoding="utf-8") if (root / "AGENTS.md").exists() else ""
    gallery_by_slug = readme_gallery_by_slug(root)
    return {
        "version": "beautiful-html-template-families/v1",
        "source": {
            "repo": "beautiful-html-templates",
            "template_count": len(slugs),
            "source_root": "beautiful-html-templates",
            "inventory_item_count": sum(len(items) for items in inventory_by_slug.values()),
            "absorbed_family_count": len(absorptions_by_slug),
        },
        "families": [extract_family(root, slug, inventory_by_slug, absorptions_by_slug, agents_md, gallery_by_slug) for slug in slugs],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract beautiful-html-templates into SVGlide template family registry.")
    parser.add_argument("--source-root", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    registry = extract_registry(args.source_root)
    text = json.dumps(registry, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
