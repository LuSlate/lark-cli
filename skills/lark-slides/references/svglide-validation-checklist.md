# SVGlide Validation Checklist

Read this file only after `svglide-svg` route admission. Shared XML validation still lives in `validation-checklist.md`.

## Required Flow

1. Validate the SVG plan against `svglide-plan.schema.json` and route admission.
2. Run local source preflight with `svg_preflight.py --plan`.
3. Build or inspect a local preview when practical, then run `svg_preview_lint.py` before live create.
4. Record an aesthetic review following `svg-aesthetic-review.md`; this review cannot replace deterministic lint.
5. Run `slides +create-svg --dry-run` when command behavior is under review.
6. After live create, use `xml_presentations.get` readback and record page count, blank-page, asset, bounds, and text-fit checks.

Treat the gate as a single chain:

```text
route admission
-> loaded_rule_set + art_direction + business_claims
-> svg_preflight --plan
-> svg_preview_lint.py
-> aesthetic review record
-> dry-run / live create
-> readback checks
```

Any P0/error-level result before live create blocks the API call.

## Local Preflight

```bash
python3 skills/lark-slides/scripts/svg_preflight.py \
  --plan .lark-slides/plan/<deck-id>/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/pages/page-001.svg
```

Pass criteria:

- `summary.error_count == 0`; any error blocks live API calls.
- `loaded_rule_set` records the SVG private design and validation files loaded for the run.
- `art_direction` records cover, section-divider/tempo, closing, deck motif, and at least 3 source-backed SVG-native moments.
- `quality_gates` includes `no_text_overflow`, `no_debug_guides`, and `no_xml_like_pages` set to true.
- Visible numeric or business claims have `business_claims` source records; derived or assumed claims include derivation/assumption notes.
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
| `plan_missing_loaded_rule_set` | SVG private refs were not recorded | Add the manifest-required SVG rule file list |
| `plan_missing_art_direction` | No deck-level design strategy | Add cover/section/closing treatments, motif, and SVG-native moments |
| `plan_missing_business_claims` | Visible numeric/business claims lack source records | Mark each claim as prompt-provided, derived, assumption, etc. |

## Preview Lint

Run preview lint on local HTML/SVG preview before live create:

```bash
python3 skills/lark-slides/scripts/svg_preview_lint.py \
  .lark-slides/plan/<deck-id>/preview.html --pretty
```

Pass criteria:

- `summary.error_count == 0`; errors block live create.
- `action == "create_live"`.
- `page_issues` has no `preview_safe_area_debug_rect_visible`, `preview_debug_guide_visible`, `preview_text_overflow_risk`, or `preview_big_number_box_tight`.
- `rendering_mode` may be `static_dom_approximation` until a headless renderer is available; keep `screenshot_paths` in the output shape so rendered checks can be added without changing downstream gates.

Preview lint owns rendered/local-preview risks. Do not duplicate recipe-family or source-primitives rules here; those stay in `svg_preflight.py`.

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
- If independent review score is below the configured threshold, record `action: repair_and_rerun`; do not treat self-scoring as a gate.

## Readback Checks

Live create is not complete until readback confirms:

- Actual page count matches the plan and user request.
- No page is blank or missing its key message.
- Images are visible or explicitly documented as preview-only risk.
- Converted XML keeps content inside canvas and safe area.
- Text boxes, labels, and footer/source notes remain readable.
- Closing slide is present when required.
- Readback records must be tied to the same `plan_path` and preflight/preview lint output. HTML preview is not a substitute for readback because server conversion can change text boxes, image tokens, and bounds.
