# SVGlide Design Asset Routing

This reference defines the executable SVG-route design asset layer.

## Goal

SVGlide does not map a prompt directly to one fixed template. It routes design in four layers:

```text
prompt -> deck recipe -> template family -> style pack -> page variants
```

The template family controls structure. The style pack controls palette, typography, background system, chart colors, image treatment, decoration policy, and component bias. This prevents `34 template families` from becoming only `34 looks`.

## Executable Stages

`select_style` runs these selectors in order:

1. `scripts/svglide_recipe_selector.py`
   - Input: prompt/instruction/evidence.
   - Output: `02-plan/selection-metadata.json`.
   - Also copied to `02-plan/recipe-routing-receipt.json` and `receipts/recipe_selection.json`.

2. `scripts/svglide_palette_selector.py`
   - If user-provided colors or real brand palette exist, they win.
   - Otherwise, a passed style pack supplies `project_palette` from `style_pack_registry`.
   - Output: `02-plan/palette-selection.json`.

3. `scripts/svglide_theme_template_selector.py`
   - Selects concrete template/theme candidates.
   - Output: `02-plan/theme-template-selection.json`.

`plan` then applies all receipts back into `02-plan/slide_plan.json`.

## Required Plan Fields

SVG route plans with design asset selection must carry:

- `deck_recipe_selection`
- `template_family_selection`
- `style_pack_selection`
- `density_mode_selection`
- `component_variant_selection`
- `image_treatment_selection`
- `style_lock`
- `selection_metadata_receipt`
- `recipe_routing_receipt`
- `palette_selection_receipt`
- `selection_receipt`

`style_lock.deck_level` must be `true`. Page-level layout and component variants may vary, but page-level `style_pack_id` or `canvas_spec.palette_id` must not drift away from the deck-level lock.

## Diversity Gate

`scripts/svglide_diversity_gate.py` writes `06-check/diversity-gate.json`.

It blocks:

- missing or non deck-level `style_lock`
- failed L4/fail-closed recipe selection
- slide-level style pack drift
- slide-level palette drift
- high recent reuse of the same `template_id + style_pack_id + layout_variant + component_variant`

For selection decks, `quality_gate` requires:

- `palette-review`
- `theme-template-selection-review`
- `plan-bundle-review`
- `diversity-gate`

## Registries

- `references/svglide-deck-recipe-registry.json`
- `references/svglide-style-pack-registry.json`
- `references/svglide-semantic-route-cases.json`
- `references/beautiful-html-template-families.json`
- `references/component-registry.json`
- `references/asset-strategy-registry.json`

## Validation Commands

```bash
python3 skills/lark-slides/scripts/svglide_recipe_selector_test.py
python3 skills/lark-slides/scripts/svglide_palette_selector_test.py
python3 skills/lark-slides/scripts/svglide_selection_review_test.py
python3 skills/lark-slides/scripts/svglide_diversity_gate_test.py
python3 skills/lark-slides/scripts/svglide_quality_gate_test.py
python3 skills/lark-slides/scripts/svglide_project_runner_test.py
```
