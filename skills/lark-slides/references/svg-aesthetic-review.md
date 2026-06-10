# SVGlide Aesthetic Review

Use this file after generating local SVG/HTML preview and before calling
`slides +create-svg`. It is the short execution checklist distilled from:
`/Users/bytedance/bd-projects/workspaces/SVGlide/svglide-visual-guidance/svg_aesthetic_rubric.md`.

This review complements `svg_preflight.py`. Preflight catches deterministic
protocol, plan, and bbox problems; this checklist catches rendered visual
quality issues that need human or screenshot-based judgment.

## Required Review Flow

1. Generate local SVG files and, when possible, a local `preview.html`.
2. Run `svg_preflight.py --plan ... --input ...`; fix all errors first.
3. Open or inspect the preview. Review all slides, not just the cover.
4. Repair repeated layout problems in the generator or source SVG, not by
   changing only `slide_plan.json`.
5. Re-run preflight and preview before live creation.

Do not use preview review as a substitute for live readback. Service conversion
can still change text boxes, image tokens, path bounds, and unsupported effects.

## Blocking Visual Issues

Fix these before calling live API:

| Issue | Action |
|---|---|
| Text overlap, text container overflow, or clipped headline | Regenerate layout boxes or reduce text; do not just shrink everything |
| Badge, pill, section tag, or page label touches/overlaps headline | Move badge outside title block or add at least 12-16px vertical gap |
| Decorative line or band presses against title | Move the line above the title zone or lower title; keep clear breathing room |
| Main content outside `960 x 540` or safe area | Recompute coordinates using the 960x540 canvas |
| Low contrast text over light image/background | Add solid backing, overlay, or switch text color |
| Empty image frame or broken preview image | Replace asset or use a visual fallback before live creation |
| Page lacks focal point | Rebuild the page around one dominant number, diagram, image, route, or title |
| Page is ordinary cards/bullets with no SVG advantage | Choose a better `visual_recipe` or switch away from SVG route |
| Same layout issue repeats across multiple slides | Fix the shared generator rule, then regenerate affected pages |

## Issue Severity

Use these severities in preview notes and final validation records:

| Severity | Meaning | Action |
|---|---|---|
| P0 | The deck should not be created live | Fix or regenerate before `slides +create-svg` |
| P1 | The deck can render, but user-facing quality is clearly below target | Repair before delivery; only continue as draft if explicitly accepted |
| P2 | Minor polish or residual risk | Record and fix when time allows |

Default mapping:

- P0: preflight error, unsafe SVG, broken/empty image, canvas crop, clipped or overlapping essential text, unreadable contrast, missing required asset, no fallback for unsupported visual.
- P1: weak focal point, repeated layout skeleton, decorative/title crowding, low visual hierarchy, chart/diagram intent mismatch, visible SVG advantage weak.
- P2: minor alignment variance, small color inconsistency, non-critical source metadata warning, polish-only spacing issue.

## Scoring Rubric

Use a 0-100 review score. The default target for user-facing decks is `>= 75`.
Below `65`, regenerate or repair before live creation.

| Dimension | Weight | Good result |
|---|---:|---|
| Communication fit | 15 | Page type and visual form match the user's intent |
| Visual hierarchy | 15 | One focal point is clear within two seconds |
| Layout stability | 15 | Grid, spacing, alignment, and safe area are consistent |
| Readability | 15 | Font size, line length, contrast, and wrapping are readable |
| Color discipline | 10 | Accent colors are few and semantically consistent |
| Data/diagram integrity | 10 | Charts, flows, and diagrams express relationships honestly |
| Style consistency | 8 | Icons, radii, strokes, shadows, and motif feel like one deck |
| SVG advantage | 7 | The page visibly benefits from path, texture, chart geometry, flow, or overlay |
| Source/asset traceability | 5 | External references and preview assets are recorded when used |

## Review Questions

Ask these for each page:

- What is the one-sentence takeaway?
- Where does the eye land first, and is that the intended `visual_focal_point`?
- Does the scan path follow title -> focal visual -> evidence -> detail?
- Are any badges, lines, watermarks, labels, or thumbnails crowding text?
- Is the page using SVG-native structure, or only ordinary boxes and text?
- If this page were converted to a plain XML/PPT card layout, what would be lost?
- Are chart/flow/table choices appropriate for the relationship being shown?
- Are colors and emphasis consistent with the rest of the deck?

## Repair Priority

1. Layout correctness: canvas, safe area, overlap, overflow, clipping.
2. Readability: contrast, font size, line length, enough text box height.
3. Hierarchy: one focal object, clear title, supporting details demoted.
4. SVG advantage: path/flow/chart/icon/texture/image overlay actually present.
5. Deck rhythm: avoid repeating the same skeleton with only copy changed.
6. Asset/source hygiene: preview assets are visible and source metadata exists.

## Accepted Output Note

When reporting validation, say exactly what was checked:

```text
SVG preview review:
- preflight: passed / fixed errors first
- preview_path: .lark-slides/plan/<deck-id>/preview.html
- preview: checked all N pages for overlap, safe area, readability, and repeated layout issues
- visual_score: 82 / threshold 75
- issue_ids: none / [P1 visual.layout.decorative_line_title_pressure page=3]
- action: create_live / repair_and_rerun / draft_only
- remaining risk: live readback may still change text bbox or unsupported effects
```
