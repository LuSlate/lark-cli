# SVGlide Preview Spec

Read this file only after `svglide-svg` route admission. Preview validates local visual quality before API calls; it does not replace source preflight or live readback.

## Preview Contract

`preview.html` should:

- Read `04-svg/prepared/*.svg` in `svg_files` order.
- Write `05-preview/preview.html`.
- Write `05-preview/preview-manifest.json`.
- Embed every prepared SVG page in the preview HTML.
- Preserve the 16:9 `960 x 540` page box.
- Keep page labels and review metadata outside the SVG canvas.
- Show image assets as they will appear in local preview, with preview-only sources recorded in the plan.
- Avoid visible safe-area rectangles, debug guides, bbox guides, or layout helper marks.

## Lint Contract

Run:

```bash
python3 skills/lark-slides/scripts/svg_preview_lint.py \
  .lark-slides/plan/<deck-id>/05-preview/preview.html --pretty
```

Required output shape:

```json
{
  "rendering_mode": "static_dom_approximation",
  "screenshot_paths": [],
  "summary": {"error_count": 0, "warning_count": 0},
  "page_issues": [],
  "action": "create_live"
}
```

Any preview lint error sets `action` to `repair_and_rerun` and blocks live create.

Save the lint output as `06-check/preview-lint.json`. It is only one input to `quality_gate`; `svglide_semantic_review.py` must also pass before create.

## Review Contract

After lint passes, record an aesthetic review with:

- `preview_path`: `05-preview/preview.html`
- `plan_path`: `02-plan/slide_plan.json`
- checked page count
- score and threshold
- issue ids and affected pages
- action: `create_live` or `repair_and_rerun`

The review must inspect every page for blank output, clipping, text overlap, image visibility, weak SVG-native structure, repeated layouts, and closing slide presence. If a repeated issue appears across pages, repair the generator or source pattern and rerun preflight and preview lint.

## Boundary

Preview can catch local layout problems. It does not validate Chinese delivery quality, page type structure, content depth, source refs, or generator text provenance; those belong to `svglide_semantic_review.py`. Readback is still required because the server conversion can change text boxes, image tokens, path bounds, and supported SVG effects.
