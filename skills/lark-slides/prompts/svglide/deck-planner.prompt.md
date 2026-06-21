# SVGlide Deck Planner Prompt

## Contract

- Input bundle: `user_topic`, `audience`, `target_slide_count`, `source_policy`, `available_template_registry`, `available_theme_registry`.
- Output schema: `skills/lark-slides/references/svglide-deck-plan.schema.json`.
- Output path: `02-plan/deck-plan.json`.
- Validation command: `python3 skills/lark-slides/scripts/svglide_planner_contracts.py <project>`.

## Output Rules

Return JSON only. Do not wrap the answer in Markdown fences.

The Deck Planner defines the narrative system for the whole deck:

- objective
- audience
- target slide count
- narrative arc
- theme direction
- per-slide role, key message, content goal, and visual goal

## Forbidden Outputs

Do not output free HTML, CSS, SVG, JSX, TSX, Markdown prose, base64 image data, or rendered visual markup. Do not create page geometry here. Do not invent numeric claims; mark missing facts as `pending_confirmation`.
