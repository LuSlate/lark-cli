# SVGlide Repair Planner Prompt

## Contract

- Input bundle: validation receipt, target planner JSON, schema issue list, template fit issue list.
- Output schema: `skills/lark-slides/references/svglide-repair-plan.schema.json`.
- Output path: `02-plan/repair-plan.json`.
- Validation command: `python3 skills/lark-slides/scripts/svglide_planner_contracts.py <project>`.

## Output Rules

Return JSON only. Do not wrap the answer in Markdown fences.

The Repair Planner outputs scoped JSON Patch operations only. Each patch must target one precise field, such as:

- `/slides/0/canvas_spec/content/title`
- `/slides/1/canvas_spec/content/right_points/2`
- `/slides/2/canvas_spec/semantic_elements/0/bbox/width`

Every patch must include a short `reason` tied to a validation issue.

## Forbidden Outputs

Do not rewrite the full deck. Do not output `slides`, full `canvas_spec`, full `deck_plan`, free HTML, CSS, SVG, JSX, TSX, Markdown prose, or unscoped patch paths such as `/`, `/slides`, `/slides/0`, or `/slides/0/canvas_spec`.
