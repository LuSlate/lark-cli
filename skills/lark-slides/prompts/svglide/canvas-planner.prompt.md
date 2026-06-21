# SVGlide Canvas Planner Prompt

## Contract

- Input bundle: `02-plan/slide-plan.json`, `svglide-template-registry.json`, `themes/registry.json`, `svglide-canvas-spec.schema.json`, golden CanvasSpec examples.
- Output schema: `skills/lark-slides/references/svglide-canvas-plan.schema.json`.
- Output path: `02-plan/slide_plan.json`.
- Validation command: `python3 skills/lark-slides/scripts/svglide_planner_contracts.py <project>`.

## Output Rules

Return JSON only. Do not wrap the answer in Markdown fences.

The Canvas Planner turns each slide plan into the final `generation_mode=artboard_satori` `slide_plan.json`. Every slide must include a full `canvas_spec` with:

- `version`
- `canvas`
- `safe_area`
- `template_id`
- `theme_id`
- `theme`
- `content`
- `semantic_elements`
- `quality_constraints`

The output must pass `svglide-plan.schema.json`, `svglide-canvas-plan.schema.json`, CanvasSpec validation, Template Registry binding, Theme Registry binding, and template text-budget/max-items checks before Satori is invoked.

## Forbidden Outputs

Do not output free HTML, CSS, SVG, JSX, TSX, Markdown prose, raw Satori SVG, foreignObject snippets, or arbitrary inline style. Use structured CanvasSpec JSON only.
