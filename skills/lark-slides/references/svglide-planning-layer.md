# SVGlide Planning Layer

Read this file only after `svglide-svg` route admission. It extends the shared `planning-layer.md`; it does not replace the common narrative, page role, layout, asset, and verification fields.

Compatibility note: new runner-first artifact paths are defined in `svglide-artifacts.spec.md` and `svglide-plan.contract.md`. Keep this file for planning-field semantics; use the staged `02-plan`, `04-svg`, `05-preview`, `06-check`, `07-create`, and `08-readback` layout for new work.

## Page Count

When the user asks for an SVG/SVGlide deck but does not specify page count, or uses ambiguous wording such as "a slide", "a PPT", "make a slide", or "generate a slide", default to `10` pages. Generate `1` page only when the user explicitly asks for one page, a single page, onepage, one slide, or only a cover. Explicit page counts always win.

Default 10-page SVG decks must record `deck_intent: "full_deck"` plus `page_count` or `target_slide_count: 10` and include an explicit closing slide. Short outputs must opt in with `deck_intent: "sample"`, `"single_page"`, `"fixture"`, or `"smoke"`; otherwise a 4-page cover/content/content/closing structure is treated as an incomplete deck.

## Required Top-Level Extensions

SVG route plans must include:

- `route` or `output_mode` with value `svglide-svg`.
- `canvas` with `width: 960`, `height: 540`, and `viewBox: "0 0 960 540"`.
- `safe_area` compatible with the current `48,40,864,460` safe area.
- `template_family_selection`: deck-level selection from `beautiful-html-template-families.json`, including selected family, candidates, and selection reason.
- `deck_intent`: `full_deck` for ordinary user generation; `sample`, `single_page`, `fixture`, or `smoke` only when the user or test explicitly asks for that shorter shape.
- `target_slide_count` or `page_count`: ordinary `full_deck` generation defaults to at least `10`.
- `theme_policy`: deck-level theme scope. Default is `{"scope": "deck", "allow_multi_theme": false}`; multiple `theme_id` values require an explicit reason and `allow_multi_theme: true`.
- `asset_policy`: real-preview asset expectations. For ordinary local previews use `{"required": true, "minimum_visual_asset_count": 3}`.
- `visual_identity`: the theme-specific visual system that prevents unrelated decks from sharing the same skeleton. Required fields:
  - `theme_archetype`: such as `company_ecosystem`, `space_capital_market`, `travel_destination`, or `academic_paper`.
  - `design_dna`: `palette`, `layout_motif`, `shape_language`, `image_treatment`, `component_bias`, plus at least 3 theme-specific visual anchors.
  - `forbidden_reuse`: recent-deck reuse rules for palette, cover structure, and default skeleton.
  - `distinctness_target`: palette, renderer sequence, and layout sequence similarity thresholds.
- `loaded_rule_set`: exact SVG private rule files loaded after route admission. It must include the manifest-required design and validation references, not only protocol files.
- `plan_path`: the `.lark-slides/plan/<deck-or-task-id>/02-plan/slide_plan.json` path that later preflight, preview lint, live create, and readback records belong to.
- `quality_gates`: deterministic gates requested before source generation, including `no_text_overflow: true`, `no_debug_guides: true`, and `no_xml_like_pages: true`.
- `art_direction`: the deck-level visual strategy that must drive family variants and component composition, not just prose. Required fields:
  - `cover_treatment`
  - `section_divider_treatment`
  - `closing_treatment`
  - `deck_motif`
  - `svg_native_moments` with at least 3 source-backed moments
- `business_claims`: source records for visible numeric or business claims. Use `prompt_provided`, `user_provided`, `attachment`, `readback`, `derived`, `assumption`, or `pending_confirmation`; derived or assumed claims must include a derivation or assumption note.
- `svg_files`: ordered source files when `slides +create-svg --file` will consume generated pages.
- `fallback_policy`: `strict-native` or `auto` when the compiler gate is available.

## Required Slide Extensions

Each SVG slide must include:

- `renderer_id`: the concrete geometry/renderer used for the page.
- `layout_family`: deck-level layout family for diversity checks.
- `template_variant`: the selected family variant for this page.
- `semantic_blocks`: page content split into semantic blocks.
- `component_selection`: registry components bound to semantic blocks.
- `asset_strategy`: real image, chart, or structured fallback strategy.
- `content_density_contract`: a measurable structure contract for dense pages.
- `risk_flags`: an array; use `[]` when no risk is known.
- `source_policy`: how missing data, attachments, claims, numbers, logos, and citations are handled.
- `asset_contract`: image/source metadata, or `none_required` when no image asset is used.

## Example Shape

```json
{
  "route": "svglide-svg",
  "output_mode": "svglide-svg",
  "deck_intent": "full_deck",
  "target_slide_count": 10,
  "page_count": 10,
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
  "template_family_selection": {
    "enabled": true,
    "source": "beautiful-html-template-families",
    "selected_template_id": "blue-professional",
    "candidate_template_ids": ["blue-professional", "signal", "cobalt-grid"],
    "selection_reason": "formal internal review with metrics, evidence, and action plan"
  },
  "theme_policy": {"scope": "deck", "allow_multi_theme": false},
  "asset_policy": {"required": true, "minimum_visual_asset_count": 3},
  "visual_identity": {
    "theme_archetype": "company_ecosystem",
    "design_dna": {
      "palette": "light corporate product ecosystem",
      "layout_motif": "product ecosystem wall",
      "shape_language": "low-radius app tiles and organization network nodes",
      "image_treatment": "company imagery for cover/closing; editable SVG components for body pages",
      "component_bias": "ecosystem_wall, org_network, editorial_profile",
      "theme_visual_anchors": ["app tile wall", "product matrix", "organization network"]
    },
    "forbidden_reuse": {"recent_decks": 5, "avoid_same_palette": true, "avoid_same_cover_structure": true, "avoid_default_skeleton": true},
    "distinctness_target": {"palette_overlap_max": 0.67, "renderer_sequence_similarity_max": 0.75, "layout_sequence_similarity_max": 0.75}
  },
  "loaded_rule_set": [
    "skills/lark-slides/references/svglide-route-admission.md",
    "skills/lark-slides/references/beautiful-html-template-families.json",
    "skills/lark-slides/references/component-registry.json",
    "skills/lark-slides/references/asset-strategy-registry.json",
    "skills/lark-slides/references/svg-aesthetic-review.md",
    "skills/lark-slides/references/svglide-planning-layer.md",
    "skills/lark-slides/references/svglide-validation-checklist.md",
    "skills/lark-slides/references/svglide-visual-planning.md"
  ],
  "plan_path": ".lark-slides/plan/demo/02-plan/slide_plan.json",
  "quality_gates": {
    "no_text_overflow": true,
    "no_debug_guides": true,
    "no_xml_like_pages": true
  },
  "art_direction": {
    "cover_treatment": "Hero typography with a single dominant claim and source-backed SVG geometry.",
    "section_divider_treatment": "Sparse chapter reset with oversized section number and shared motif.",
    "closing_treatment": "Closing loop or brand-system page that mirrors the cover motif and states the next action.",
    "deck_motif": "dense grid panels with restrained accent labels",
    "svg_native_moments": ["cover geometry", "data micro chart", "closing loop"]
  },
  "business_claims": [
    {"claim": "All numeric claims are prompt-provided or marked pending.", "source_type": "prompt_provided"}
  ],
  "svg_files": [{"page": 1, "path": ".lark-slides/plan/demo/04-svg/prepared/page-001.svg"}],
  "slides": [
    {
      "page": 1,
      "title": "Proposal Title",
      "key_message": "The initiative is ready for a focused pilot.",
      "renderer_id": "hero_path_cover",
      "layout_family": "hero",
      "template_variant": "cover",
      "semantic_blocks": [{"block_id": "title", "type": "title", "content": "Proposal Title"}],
      "component_selection": [{"component_id": "title_block", "binds": ["title"]}],
      "asset_strategy": {"strategy_id": "structured_fallback", "decision": "no external image required"},
      "content_density_contract": "hero >= 1 focal title",
      "asset_contract": "none_required",
      "risk_flags": [],
      "source_policy": "Use prompt-provided content only; no invented metrics."
    }
  ]
}
```

## Diversity Gates

- 8 or more SVG pages must end with an explicit closing, summary, thanks, Q&A, or next-step page.
- 8 or more SVG pages must declare cover, section-divider/tempo, and closing treatments in `art_direction`; the first and last page variants must support those roles.
- 8 or more SVG pages should use at least 6 template variants or an explicit family rhythm.
- 10 or more SVG pages should use at least 5 distinct `renderer_id` values and 5 `layout_family` values.
- Do not use the same renderer or layout family for 3 consecutive pages.
- High-density pages must quantify the density contract, such as `matrix >= 6 cells`, `timeline >= 4 nodes`, `dashboard >= 4 metrics`, `flow >= 4 stages`, or `risk_grid >= 4 items`.
- Topic-only decks must still declare a theme-specific `visual_identity`; using only default renderer sequences such as cover/chart/timeline/closing is a strategy failure.
- Different local projects should not reuse the same template family, palette, cover treatment, and renderer/layout sequence unless the theme archetype is intentionally the same.

## XML Boundary

These fields are SVG-only. Do not add them to XML route plans.
