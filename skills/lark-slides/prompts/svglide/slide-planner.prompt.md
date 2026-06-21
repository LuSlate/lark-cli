# SVGlide Slide Planner Prompt

## Contract

- Input bundle: `02-plan/deck-plan.json`, `svglide-template-registry.json`, `themes/registry.json`, `svglide-layout-archetypes.json`, `svglide-component-registry.json`.
- Output schema: `skills/lark-slides/references/svglide-slide-plan.schema.json`.
- Output path: `02-plan/slide-plan.json`.
- Validation command: `python3 skills/lark-slides/scripts/svglide_planner_contracts.py <project>`.

## Output Rules

Return JSON only. Do not wrap the answer in Markdown fences.

The Slide Planner chooses registered templates and themes for each slide. It may define structured content requirements, but it must not write CanvasSpec yet.

Every slide must choose a `template_id` and `theme_id` from the registries. Keep content short enough for the selected template budgets.

## Forbidden Outputs

Do not output free HTML, CSS, SVG, JSX, TSX, Markdown prose, raw Satori SVG, or unregistered template/theme IDs. Do not bypass Template Registry or Theme Registry.
