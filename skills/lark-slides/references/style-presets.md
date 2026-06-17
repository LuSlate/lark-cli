# SVGlide Style Presets

`style-presets.json` is the runtime source of truth for the 35 `beautiful-feishu-whiteboard` style presets plus the SVGlide `data_journalism_editorial` preset distilled from ppt-master. This Markdown file is only a human-readable guide.

## Boundary

Style presets are not slide templates. They do not replace `visual_recipe`, `renderer_id`, or the page semantic plan.

- `visual_recipe`: explains the page structure and SVG-native value, such as `path_flow`, `technical_texture`, or `fake_ui_dashboard`.
- `style_preset`: selects the visual language, palette, panel treatment, connector density, label density, and texture.
- `style_system`: records how the selected preset is translated into the current deck.

Do not copy raw whiteboard nodes, raw coordinates, source prompts, source file paths, tool names, source tokens, or preset names into visible slide content.

## Required Plan Fields

For `output_mode="svglide-svg"`, the deck plan must include:

```json
{
  "style_preset": "raw_grid",
  "style_selection_reason": "raw_grid fits technical training pages that need dense but readable visual structure",
  "style_system": {
    "palette": {
      "background": "#F5F5F5",
      "text": "#0A0A0A",
      "accent": "#F2D4CF"
    },
    "typography": "strong title, readable native text labels",
    "background_strategy": "muted grid panels with one stable background family",
    "motif": "dense grid panels with restrained accent labels"
  }
}
```

Each slide must also include:

```json
{
  "visual_recipe": "path_flow",
  "visual_signature": "curved route path with explicit stage annotations",
  "svg_effects": ["path", "connector_flow", "typography"],
  "svg_primitives": ["path", "annotation"],
  "required_primitives": ["path", "annotation"]
}
```

Use `visual_plan` as a nested container when useful. `svg_preflight.py` accepts both the nested shape and the existing flat fields; nested `visual_plan` wins when both are present.

## Selection Rule

1. Choose intensity first.
   - `Restrained`: serious, quiet, institutional, text-first decks.
   - `Balanced`: default for business, technical, training, and explanatory decks.
   - `Bold`: posters, showcases, event material, playful explainers, high-energy pages.
2. Match the user's tone and topic.
3. Keep the semantic plan stable. Switching from `raw_grid` to `reading_room` should change visual treatment, not invent new facts or rearrange the story.
4. Pick page-level overrides only for cover, section divider, or poster-like moments. Most slides should inherit the deck-level `style_preset`.

## PPT Master Editorial Preset

Use `data_journalism_editorial` when a deck needs the dark, data-journalism feel seen in ppt-master's `ppt169_global_ai_capital_2026` example. Translate the reference into SVGlide-safe parts: dark graphite ground, large editorial title hierarchy, thin chart rules, small source/footer text, restrained red numeric emphasis, and real chart geometry. Do not copy ppt-master SVG paths, images, or PPTX export assumptions.

## SVGlide-Safe Translation

Translate style into supported SVG primitives:

- Palette -> explicit `fill`, `stroke`, and text colors.
- Panel treatment -> `rect`, `path`, and grouped layout boxes. Text-bearing panels must be translated into a concrete surface kind, not a naked white rectangle.
- Connector density -> explicit `line` or supported `path`; do not rely on `marker` or key-path `stroke-dasharray`.
- Texture -> repeated native `line`, `circle`, or `rect`; do not rely on `<pattern>` as the only effect.
- Image overlay -> real `<image slide:role="image">` plus explicit shape masks/overlays when needed.

Unsafe effects such as `filter`, `mask_clip`, `pattern`, `symbol`, `stroke_dasharray`, and `image_opacity` may appear in the plan only when a safe rewrite or fallback is declared.

## Text Surface Translation

Every style preset has a `shape_language.panel_treatment`. Translate it into one of these SVG-safe text surfaces:

- `accent_rail_card`: tinted card with a 6-10px left/top rail in the preset accent color.
- `tinted_panel`: non-white preset support fill plus visible stroke.
- `glass_overlay`: semi-transparent panel on an image with matching overlay color.
- `dark_backing`: dark rect/card/overlay for light text.
- `label_chip`: short label only; no explanatory sentence.
- `metric_tile`: KPI tile with a role color, separator, rail, or small chart cue.

Rules:

- Do not use bare `fill="#ffffff"` rectangles for user-visible text unless the page is an intentional wireframe/table and the panel has visible stroke or grid structure.
- Keep text surfaces at least 24px away from the title box.
- Connector lines must terminate at card/node/chart edges; they must not run through visible text.
- If a preset uses low contrast or editorial whitespace, improve the text surface with spacing, stroke, role color, and alignment rather than adding more plain boxes.

## Quality Gates

Before calling `slides +create-svg`, run:

```bash
python3 skills/lark-slides/scripts/svg_preflight.py \
  --route-manifest skills/lark-slides/references/routes/create-svg/route.manifest.json \
  --report-scope public \
  --plan .lark-slides/plan/<deck-id>/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/pages/page-001.svg
```

The preflight checks:

- preset exists in `style-presets.json`;
- `style_system` has palette, typography, background strategy, and motif;
- each page declares `visual_signature` and `svg_effects`;
- unsafe effects have fallback or rewrite notes;
- declared effects and primitives are present in the SVG source;
- visible slide text does not leak preset names, source tokens, prompts, tool names, or local file paths.
- text surfaces avoid `plain_white_text_panel`, `title_surface_pressure`, and `connector_crosses_text` issues.
