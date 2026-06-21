# SVGlide Artboard Gate 10 Evidence

Gate: `Gate 10: Prompt And Planning Layer`

Status: `PASS`

Date: 2026-06-21

Reviewer history:

```text
Initial review: BLOCKED
Blockers:
  1. Slide Planner output did not validate template_id/theme_id against Template/Theme Registry.
  2. Repair Planner allowed broad object patch paths such as /slides/0/canvas_spec/content.
Fixes:
  1. svglide_planner_contracts.py now validates Slide Planner template/theme IDs against active registries and template supported_theme_ids.
  2. Repair Planner validation now rejects broad paths for whole content/theme/semantic_elements/quality_constraints/content_requirements objects.
  3. Repair Planner validation rejects object/list patch values for add/replace; patches must target scalar leaf values.
  4. Focused tests now include negative coverage for unregistered slide-plan template and broad repair object patch.
Current state: re-review requested after fresh validation.
Final reviewer verdict: PASS.
```

## Scope

Gate 10 turns a user topic into structured planner JSON without letting the LLM output arbitrary HTML/CSS/SVG.

Implemented planner chain:

```text
Deck Planner
-> Slide Planner
-> Canvas Planner
-> Repair Planner
```

The planner chain is validated before Satori is invoked:

```text
prompt contracts
-> planner output schemas
-> forbidden free markup scan
-> CanvasSpec validation
-> Template Registry / Theme Registry binding
-> template text_budget / max_items admission
-> scoped JSON Patch repair validation
```

## Prompt Contracts

Contract registry:

```text
skills/lark-slides/references/svglide-planner-prompt-contracts.json
```

Prompt files:

```text
skills/lark-slides/prompts/svglide/deck-planner.prompt.md
skills/lark-slides/prompts/svglide/slide-planner.prompt.md
skills/lark-slides/prompts/svglide/canvas-planner.prompt.md
skills/lark-slides/prompts/svglide/repair-planner.prompt.md
```

Every prompt declares:

```text
input_bundle
output_schema
output_path
validation_command
forbidden_outputs
```

All prompts require JSON-only output and forbid free HTML, free CSS, free SVG, JSX/TSX, Markdown fences, raw Satori SVG, and base64 image data.

## Output Schemas

Schemas:

```text
skills/lark-slides/references/svglide-deck-plan.schema.json
skills/lark-slides/references/svglide-slide-plan.schema.json
skills/lark-slides/references/svglide-canvas-plan.schema.json
skills/lark-slides/references/svglide-repair-plan.schema.json
```

Schema roles:

```text
svglide-deck-plan.schema.json: narrative and deck-level intent only
svglide-slide-plan.schema.json: registered template_id/theme_id selection
svglide-canvas-plan.schema.json: final artboard_satori slide_plan.json with CanvasSpec
svglide-repair-plan.schema.json: scoped JSON Patch operations only
```

## Validation Script

Implemented:

```text
skills/lark-slides/scripts/svglide_planner_contracts.py
```

The script validates:

```text
1. Required four prompt contracts exist.
2. Prompt files exist and declare schema/path/validation command.
3. Prompt contracts include forbidden outputs.
4. Planner outputs exist at contract-declared paths.
5. Planner outputs pass their schemas.
6. Planner outputs do not contain free HTML/CSS/SVG markup patterns.
7. Canvas Planner output also passes existing svglide-plan.schema.json.
8. Every CanvasSpec passes CanvasSpec validation.
9. Every CanvasSpec passes Template Registry / Theme Registry binding.
10. Template required_content, max_items, and text_budget are enforced before Satori.
11. Repair Planner output cannot contain full deck/slides/canvas_spec rewrites.
12. Repair patch paths must be scoped to slides/style_system/art_direction fields.
13. Slide Planner template_id and theme_id must be active registry entries.
14. Slide Planner theme_id must be allowed by the selected template.
15. Repair patch paths must target leaf fields, not whole CanvasSpec content/theme/semantic objects.
```

Output receipts:

```text
06-check/planner-contract-check.json
receipts/planner-contract-check.json
```

## Fixture

Gate 10 fixture:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner/
```

Planner outputs:

```text
02-plan/deck-plan.json
02-plan/slide-plan.json
02-plan/slide_plan.json
02-plan/repair-plan.json
```

Topic:

```text
冰岛火山研究
```

The fixture proves:

```text
Deck Planner output stays narrative-only.
Slide Planner chooses registered templates/themes.
Canvas Planner emits full artboard_satori slide_plan.json with CanvasSpec.
Repair Planner emits one scoped JSON Patch, not a full-deck rewrite.
```

## Validation Commands

JSON parse:

```bash
python3 -c 'import json, pathlib; paths=list(pathlib.Path("skills/lark-slides/references").glob("svglide-*.json"))+list(pathlib.Path("skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner/02-plan").glob("*.json")); [json.load(p.open(encoding="utf-8")) for p in paths]; print(len(paths))'
```

Result:

```text
37 JSON files parsed
```

Python compile:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m py_compile \
  skills/lark-slides/scripts/svglide_planner_contracts.py \
  skills/lark-slides/scripts/svglide_planner_contracts_test.py
```

Result:

```text
PASS
```

Planner contract fixture:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_planner_contracts.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner \
  --pretty
```

Result:

```text
status: passed
prompt_contract_count: 4
planner_output_count: 4
error_count: 0
```

Artboard continuation proof:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_artboard_renderer.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner \
  --pretty
```

Result:

```text
status: passed
page_count: 3
max_workers: 3
contact_sheet: 05-preview/contact-sheet.png
```

Focused tests:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_planner_contracts_test.py
```

Result:

```text
Ran 5 tests in 0.204s
OK
```

Full scripts regression:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 270 tests in 15.565s
OK
```

Renderer runtime checks:

```bash
node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

Result:

```text
PASS
satori_version: 0.26.0
resvg_version: 2.6.2
```

Diff check:

```bash
git diff --check
```

Result:

```text
PASS
```

## Boundary Note

`svglide_template_fit_check.py` is a runner post-generate check that requires `receipts/generate_svg.json`. Gate 10 does not use it directly as the planner gate. Instead, `svglide_planner_contracts.py` performs pre-Satori planner admission by calling CanvasSpec validation and Template/Theme Registry binding, including template required content, `max_items`, and `text_budget`.

The artboard renderer command above is included only to prove that the validated Canvas Planner output can continue into Satori/resvg; it is not a substitute for planner contract validation.
