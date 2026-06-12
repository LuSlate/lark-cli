# SVGlide Planning Layer

Read this file only after `svglide-svg` route admission. It extends the shared `planning-layer.md`; it does not replace the common narrative, page role, layout, asset, and verification fields.

## Page Count

When the user asks for an SVG/SVGlide deck but does not specify page count, or uses ambiguous wording such as "a slide", "a PPT", "make a slide", or "generate a slide", default to `10` pages. Generate `1` page only when the user explicitly asks for one page, a single page, onepage, one slide, or only a cover. Explicit page counts always win.

Default 10-page SVG decks must record `page_count` or `target_slide_count: 10` and include an explicit closing slide.

## Required Top-Level Extensions

SVG route plans must include:

- `route` or `output_mode` with value `svglide-svg`.
- `canvas` with `width: 960`, `height: 540`, and `viewBox: "0 0 960 540"`.
- `safe_area` compatible with the current `48,40,864,460` safe area.
- `style_preset`: a preset id from `style-presets.json`.
- `style_selection_reason`: why the preset fits the audience, topic, density, and tone.
- `style_system`: executable palette, typography, background strategy, and motif derived from the preset.
- `loaded_rule_set`: exact SVG private rule files loaded after route admission. It must include the manifest-required design and validation references, not only protocol files.
- `plan_path`: the `.lark-slides/plan/<deck-or-task-id>/slide_plan.json` path that later preflight, preview lint, live create, and readback records belong to.
- `quality_gates`: deterministic gates requested before source generation, including `no_text_overflow: true`, `no_debug_guides: true`, and `no_xml_like_pages: true`.
- `art_direction`: the deck-level visual strategy that must drive source geometry, not just prose. Required fields:
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
- `visual_recipe`: the SVG-native page recipe.
- `visual_intent`: the purpose of the SVG visual expression.
- `visual_focal_point`: the region or object that should dominate the page.
- `visual_signature`: the page's distinctive SVG memory point.
- `svg_effects`: canonical effects that are actually used or planned.
- `required_primitives`: primitives that must appear in the source.
- `svg_primitives`: primitives planned for the source.
- `xml_like_risk`: what would be lost if this were rendered as ordinary XML cards or bullets.
- `content_density_contract`: a measurable structure contract for dense pages.
- `risk_flags`: an array; use `[]` when no risk is known.
- `source_policy`: how missing data, attachments, claims, numbers, logos, and citations are handled.
- `asset_contract`: image/source metadata, or `none_required` when no image asset is used.

## Example Shape

```json
{
  "route": "svglide-svg",
  "output_mode": "svglide-svg",
  "page_count": 10,
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
  "style_preset": "raw_grid",
  "style_selection_reason": "raw_grid fits a technical training deck with dense but readable structure.",
  "style_system": {
    "palette": {"background": "#F5F5F5", "text": "#0A0A0A", "accent": "#F2D4CF"},
    "typography": "strong title, readable native text labels",
    "background_strategy": "muted grid panels with one stable background family",
    "motif": "dense grid panels with restrained accent labels"
  },
  "loaded_rule_set": [
    "skills/lark-slides/references/svglide-route-admission.md",
    "skills/lark-slides/references/style-presets.md",
    "skills/lark-slides/references/svg-visual-recipes.md",
    "skills/lark-slides/references/svg-aesthetic-review.md",
    "skills/lark-slides/references/svglide-planning-layer.md",
    "skills/lark-slides/references/svglide-validation-checklist.md",
    "skills/lark-slides/references/svglide-visual-planning.md"
  ],
  "plan_path": ".lark-slides/plan/demo/slide_plan.json",
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
  "svg_files": [{"page": 1, "path": ".lark-slides/plan/demo/pages/page-001.svg"}],
  "slides": [
    {
      "page": 1,
      "title": "Proposal Title",
      "key_message": "The initiative is ready for a focused pilot.",
      "renderer_id": "hero_path_cover",
      "layout_family": "hero",
      "visual_recipe": "hero_typography",
      "visual_intent": "Use oversized type and layered geometry to establish the point of view.",
      "visual_focal_point": "Large title block over a structured background motif.",
      "visual_signature": "Oversized title mass with a layered path frame.",
      "svg_effects": ["path", "typography"],
      "required_primitives": ["typography", "geometric_shape"],
      "svg_primitives": ["typography", "geometric_shape", "path"],
      "xml_like_risk": "Without SVG-specific geometry this becomes a plain title slide.",
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
- 8 or more SVG pages must declare cover, section-divider/tempo, and closing treatments in `art_direction`; the first and last page recipes must support those roles.
- 8 or more SVG pages should use at least 5 recipe families.
- 10 or more SVG pages should use at least 5 distinct `renderer_id` values and 5 `layout_family` values.
- Do not use the same renderer or layout family for 3 consecutive pages.
- High-density pages must quantify the density contract, such as `matrix >= 6 cells`, `timeline >= 4 nodes`, `dashboard >= 4 metrics`, `flow >= 4 stages`, or `risk_grid >= 4 items`.

## XML Boundary

These fields are SVG-only. Do not add them to XML route plans.
