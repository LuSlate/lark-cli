# SVGlide Reference Absorption Matrix

This matrix tracks which high-quality presentation-generation capabilities have been absorbed into the SVGlide SVG route. It is intentionally written in SVGlide terms: the CLI must run independently and must not depend on an external reference project at runtime.

| Capability | Status | CLI Landing Area | Acceptance Evidence |
|---|---|---|---|
| Project state machine | absorbed | `svglide_project_runner.py` | stages emit receipts and `receipts/timings.json` |
| Source pack | absorbed | `source/source_pack.json`, `slide_plan.source_pack` | generation receipt includes `source_pack_digest` and status |
| Design spec lock | planned | `source/design_spec.json`, `slide_plan.strategy_locks` | strategy receipt lists mode, visual style, style preset, chart policy |
| Renderer registry | planned | `svglide-renderer-registry.json` | active renderers validate against seed and recipe catalogs |
| Layout contracts | absorbed | `svg-seeds.json` | active slides carry `seed_id`, `layout_boxes`, budgets, safe zone |
| Visual recipes | absorbed | `svg-recipes.json` | active slides carry `visual_recipe` and required primitives |
| Style system | absorbed | `style-presets.json` | active plan carries `style_preset` and `style_system` |
| Design pattern selection | absorbed | `design_pattern_selection`, `receipts/design-pattern-usage.json` | selected assets are proven by component report geometry |
| Renderer assetization | planned | `svglide_gen_runtime.py`, renderer registry | each active renderer has page kind, seed, recipe, and runtime family |
| Chart geometry verification | planned | `chart_verify` runner stage | chart pages emit `receipts/chart-verify.json` before quality gate |
| Preview lint | absorbed | `svg_preview_lint.py` | `preview_lint` receipt includes score, issues, and validation profile |
| Quality gate | absorbed | `quality_gate` runner stage | gate aggregates preflight, preview lint, components, design usage |
| Timing receipt | absorbed | `receipts/timings.json` | every runner stage records elapsed time and over-budget status |
| Golden smoke suite | absorbed | `svglide_golden_suite.py` | built-in cases cover AI capital, Aksu oasis, runtime smoke |
| Editable PPTX export | not_applicable | outside SVGlide SVG route | SVG route publishes through `slides +create-svg` |
| PowerPoint animation/audio/video | not_applicable | outside SVGlide SVG route | not required for Lark Slides SVG create flow |

## Rules

- Runtime assets must use SVGlide-native names.
- External examples can inform contracts, but raw files are not copied into the CLI runtime path.
- A capability is not `absorbed` unless it has a receipt, validator, test, or golden case that proves it is exercised.
