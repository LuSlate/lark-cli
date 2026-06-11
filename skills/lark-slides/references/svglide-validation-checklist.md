# SVGlide Validation Checklist

Read this file only after `svglide-svg` route admission. Shared XML validation still lives in `validation-checklist.md`.

## Required Flow

1. Validate the SVG plan against `svglide-plan.schema.json` and route admission.
2. Run local source preflight with `svg_preflight.py --plan`.
3. Build or inspect a local preview when practical and run aesthetic review before live create.
4. Run `slides +create-svg --dry-run` when command behavior is under review.
5. After live create, use `xml_presentations.get` readback and record page count, blank-page, asset, bounds, and text-fit checks.

## Local Preflight

```bash
python3 skills/lark-slides/scripts/svg_preflight.py \
  --plan .lark-slides/plan/<deck-id>/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/pages/page-001.svg
```

Pass criteria:

- `summary.error_count == 0`; any error blocks live API calls.
- The selected style preset exists in `style-presets.json`.
- The style system contains palette, typography, background strategy, and motif.
- Every page declares the SVG-only planning fields listed in `svglide-planning-layer.md`.
- Declared effects and required primitives match the corresponding source SVG.
- Visible slide text does not leak preset names, source tokens, prompts, tool names, or local file paths.

Common remediation:

| code | Meaning | Action |
|------|---------|--------|
| `plan_style_preset_unknown` | Unknown preset id | Choose a valid id from `style-presets.json` |
| `plan_missing_visual_signature` | No SVG visual memory point | State the distinctive structure on that page |
| `plan_missing_svg_effects` | No declared SVG capability | Declare real source-backed effects |
| `plan_svg_effect_not_found` | Declared effect missing in source | Adjust source SVG or remove inaccurate metadata |
| `plan_style_preset_visible_leak` | Preset/source metadata leaked into visible text | Keep metadata in plan only |

## Aesthetic Preview Review

After deterministic preflight passes, inspect rendered preview and follow `svg-aesthetic-review.md`.

Pass criteria:

- Every page is checked, not only the cover.
- No obvious overlap or clipping among titles, body text, badges, decorations, image frames, chart labels, and footers.
- Root canvas and main content follow the 960 x 540 canvas and safe area.
- Each page has a clear visual focal point that matches the declared signature.
- Pages do not look like ordinary card/bullet XML pages with SVG wrapped around them.
- Repeated layout problems are fixed in the generator or source, then preflight is rerun.
- Review records include preview path, score, threshold, issue ids, and action.

## Readback Checks

Live create is not complete until readback confirms:

- Actual page count matches the plan and user request.
- No page is blank or missing its key message.
- Images are visible or explicitly documented as preview-only risk.
- Converted XML keeps content inside canvas and safe area.
- Text boxes, labels, and footer/source notes remain readable.
- Closing slide is present when required.
