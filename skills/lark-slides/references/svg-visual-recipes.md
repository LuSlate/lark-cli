# SVGlide Visual Recipes

This file is the short executable recipe guide for `slides +create-svg`.
It distills the research catalog into generation-time rules that can fit into
the agent context. The longer research source remains outside the CLI skill:
`/Users/bytedance/bd-projects/workspaces/SVGlide/svglide-visual-guidance/visual_recipe_catalog.md`.

## Boundary

- `visual_recipe` defines page structure and why this page deserves SVG.
- `style_preset` defines visual language, palette, texture, density, and motif.
- `renderer_id` defines the concrete geometry renderer.

Do not use `style_preset` as a substitute for `visual_recipe`. Do not invent
new recipe ids in `slide_plan.json`.

## Hard Defaults

- Canvas: `width="960" height="540" viewBox="0 0 960 540"`.
- Safe area: keep key text, labels, charts, cards, nodes, and legends inside
  `x=48..912` and `y=40..500`.
- Grid: use a stable 12-column or 8px-step layout; avoid ad hoc coordinates.
- Text: Chinese body copy should stay around 28 characters per line; English
  body copy around 62 characters per line.
- Decoration: decorative lines, watermarks, texture, and background geometry
  must not compete with or touch the title/focal content.
- Deck diversity: 8+ page SVG decks should use at least 5 visual recipe families.

## Plan Fields

Every SVG page plan must include these fields before writing SVG:

```json
{
  "visual_recipe": "path_flow",
  "visual_intent": "show a staged route from current state to target state",
  "visual_focal_point": "curved route spine with the final target node",
  "visual_signature": "curved route path plus stage annotations",
  "svg_effects": ["path", "connector_flow", "typography"],
  "required_primitives": ["path", "annotation"],
  "svg_primitives": ["path", "annotation", "typography"],
  "xml_like_risk": "without the route geometry this becomes ordinary bullets",
  "content_density_contract": "flow >= 4 stages",
  "risk_flags": [],
  "source_policy": "do not invent unsupported numbers"
}
```

## Recipe Selection Matrix

Use these CLI-supported underscore ids in `slide_plan.json`.

| User intent | `visual_recipe` | Must show in SVG source |
|---|---|---|
| Cover, section opener, hero statement | `hero_typography` | large type, geometric carrier, clear focal object |
| Strategic framework, strong geometric layout | `geometric_composition` | non-card geometry, `path` or shaped regions |
| Roadmap, journey, process, route | `path_flow` | explicit path/line spine, arrows or stage markers |
| KPI, scorecard, data recap | `infographic_scorecard` | big number plus micro chart or gauge geometry |
| Capability map, module overview | `icon_capability_map` | consistent SVG-safe icons and labeled regions |
| Depth, atmosphere, concept emphasis | `gradient_depth` | gradient or layered translucent geometry plus readable text |
| Product/result/image story | `mask_clip_showcase` | image region plus safe overlay/crop simulation |
| Technical system, grid, coded texture | `technical_texture` | repeated lines/dots/rects, grid, scanline, or diagram texture |
| Loop, flywheel, feedback system | `metaphor_loop` | closed path or looped process plus input/output labels |
| Diagnosis, callout, focused annotation | `spotlight_annotation` | highlight region, callout line, annotation target |
| Dashboard, console, monitoring surface | `fake_ui_dashboard` | UI frame, status bar, metrics, micro charts/log rows |
| Brand or series identity page | `brand_system` | stable title system, motif, palette, and repeated identity element |

## Safe Effects

Prefer effects that can be represented by SVGlide-safe primitives:

- `path`: curves, waves, routes, custom shapes.
- `gradient`: background depth and emphasis; keep text on solid backing.
- `texture`: repeated `line`, `circle`, or `rect`; do not rely on `<pattern>`.
- `connector_flow`: explicit line/path plus arrow triangles or dots.
- `chart_geometry`: bars, points, lines, gauges, axes, and labels.
- `grid_geometry`: matrix, table-like visual summary, structured alignment grid.
- `watermark_text`: low-contrast large text that never blocks reading.
- `image_overlay`: real image plus explicit translucent shape overlays.
- `spotlight`: layered translucent shapes, not complex filter-only glow.

## Risky Effects

These may appear in visual planning only when a safe rewrite or fallback is
declared in `risk_flags` / `recipe_fallback`:

- `filter`
- `mask_clip`
- `pattern`
- `symbol`
- `stroke_dasharray`
- `image_opacity`

For critical visuals, rewrite them into explicit shapes, lines, dots, overlays,
or pre-composited images before calling `slides +create-svg`.

## Anti-Regression Rules

- A page that is mostly `rect + foreignObject` is not enough for SVGlide unless
  it also has a real SVG-native structure: path, chart geometry, icon system,
  texture, spotlight, dashboard frame, connector flow, or image overlay.
- The first visible object should match the page's `visual_focal_point`.
- Similar pages may share `style_preset`, but should not share the same layout
  skeleton with only text and background color changed.
- Dotted recipe names from research notes, such as `cover.hero`, are not valid
  runtime ids. Map them to the underscore ids above before writing the plan.
