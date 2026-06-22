# SVGlide Workflow Spec

Read this file only after `svglide-svg` route admission. It summarizes the P0 execution graph for runner-first `slides +create-svg` work and points to the private SVG route files for detailed rules.

## Stage Graph

```text
request
-> route admission
-> load SVG private rule set
-> init run directory
-> source
-> optional model-plan
-> optional theme_productization
-> plan
-> strategy_review
-> user confirms plan
-> assets
-> generate_svg
-> prepare SVG inputs
-> build local preview
-> preflight
-> preview_lint
-> aesthetic_review
-> chart_verify
-> semantic_review
-> runtime_review
-> visual_distinctness_review
-> quality_gate
-> dry-run create
-> ppe_proof
-> live create
-> readback
-> optional export
-> delivery record
```

## Stage Contract

| Stage | Input | Output | Gate |
|---|---|---|---|
| route admission | user request, source root, plan route | confirmed `svglide-svg` route | if not admitted, stay on XML route |
| load rules | `svglide-svg-private.rules.json` | recorded `loaded_rule_set` | missing required private files blocks preflight |
| init | deck id, title | `.lark-slides/plan/<deck-id>/01-project/` | repeat init of the same deck id is rejected unless explicitly forced |
| source | `source/evidence.json` or `source/source-notes.md`; online research unless disabled | `source/evidence.json`, `source/research_queries.json`, `source/research.md`, `source/source-receipt.json`, `receipts/source.json` | `source_status=thin/blocked`, blocked online research, too few evidence items, or stale source receipt blocks strategy/generation |
| model-plan | user prompt and provider command/model config | `source/evidence.json`, `02-plan/deck-plan.json`, `02-plan/slide-plan.json`, `02-plan/canvas-plan.json`, planner raw output hashes | provider output must be JSON, pass planner contracts, and record `provider_type`; external model credentials are not assumed |
| theme_productization | theme productization request and optional slide plan | project `ThemeSpec`, `02-plan/theme-registry.json`, optional migrated plan and patch receipt | ThemeSpec schema, project template binding, and migration patch must be valid |
| plan | user goal, page count, sources | `02-plan/slide_plan.json`, optional `02-plan/svglide.lock.json`, `receipts/plan.json` | plan must declare route/output mode, style, loaded rules, visual identity, art direction, quality gates, and SVG page metadata |
| strategy_review | `02-plan/slide_plan.json` | `02-plan/strategy-review.json` | language, audience, deck structure, page types, sections, roles, key messages, visual identity, theme anchors, and content minimums must pass before confirmation |
| confirm plan | `02-plan/slide_plan.json`, optional lock | `02-plan/plan-confirmation.json`, `receipts/confirm_plan.json` | user confirmation is required before assets, SVG generation, prepare, dry-run, or live-create |
| assets | confirmed plan/lock asset contracts | `03-assets/assets.json`, `03-assets/asset-manifest.json`, `03-assets/image-jobs.json`, `receipts/assets.json` | empty image boxes, required HTTP/data assets that cannot be acquired, missing local files, and unsafe image placements block the chain |
| generate_svg | confirmed plan, lock, and assets manifest | ordered `04-svg/page-###.svg` files, per-page receipts, `receipts/generate_svg.json` | each page must use SVGlide roles, 960 x 540 canvas, and safe geometry |
| prepare | `generate_svg` source SVG pages and asset map | ordered `04-svg/prepared/page-###.svg` files, `receipts/prepare.json` | unresolved local image placeholders block the chain; source SVG changes after `generate_svg` require rerun |
| build preview | prepared SVG pages and plan metadata | `05-preview/preview.html`, `05-preview/preview-manifest.json` | preview is a visual review aid, not the API contract |
| preflight | plan, prepared SVG | `06-check/preflight.json` | SVG protocol, plan contract, loaded rules, geometry, text, assets, and business claims must pass |
| preview_lint | local preview HTML | `06-check/preview-lint.json` | preview action must be `create_live` |
| aesthetic_review | preview lint, preview manifest, asset manifest | `06-check/aesthetic-review.json` | deterministic auto approval must be `approved`, image-led pages must have safe text zones, and action must be `create_live`; this is not a learned aesthetics model |
| chart_verify | plan chart contracts and prepared SVG | `06-check/chart-verify.json` | required or exact chart pages must have data and chart-like marks; no required chart records `required_chart_count=0` and passes |
| semantic_review | plan, evidence, source receipt, prepared SVG pages | `06-check/semantic-review.json`, `06-check/text-inventory.json` | language, audience, deck structure, page types, content density, source refs, numeric claim citations, research status, and visible SVG text provenance must pass |
| runtime_review | plan renderer/layout declarations, asset manifest | `06-check/runtime-review.json` | missing renderer/layout declarations, renderer/layout monoculture, or asset/renderer mismatch blocks quality gate |
| visual_distinctness_review | current plan and recent local project plans | `06-check/visual-distinctness.json` | different themes must not reuse the same style preset, palette, cover treatment, and renderer/layout sequence; default-only renderer sequences fail |
| quality_gate | generator receipt, preflight, preview lint, aesthetic review, chart verify, semantic review, runtime review, visual distinctness, source/assets readiness | `06-check/quality-gate.json` | required checks must all pass and be fresh before dry-run or live create; strict profiles reject blocked research, failed asset manifests, and fallback skeleton generation |
| dry-run create | checked prepared SVG files | `07-create/dry-run.json`, `07-create/create-command.txt` | request order and asset rewrites must match files |
| ppe_proof | current quality gate, dry-run, and PPE input | `07-create/ppe-proof.json` | live create is blocked unless PPE/auth/proxy/header proof is passed and fresh |
| live create | same checked prepared SVG files and PPE proof | `07-create/live-create.json` | partial failures must preserve the returned ids for recovery |
| readback | presentation id | `08-readback/readback-check.json` | page count, blank pages, bounds, text fit, assets, input binding, and closing slide must be checked |
| repair_loop | failing receipt and scoped repair plan | updated `02-plan/slide_plan.json`, `receipts/repair-loop.json` | only scoped scalar JSON Patch is allowed; broad structural rewrites are rejected |
| export | passed readback, live-create, quality-gate, and prepared SVGs | `09-export/export-manifest.json`, optional zip, `receipts/export.json` | packages verified SVGlide artifacts; PPTX/animation/narration must be explicitly marked separately |

## Route Boundary

The SVG route is private to `slides +create-svg`. XML creation, XML edit, and SXSD work must not load these SVG private strategy files unless route admission later proves that the request is SVG route work.

## Online-First Controls

User generation defaults to `--network-policy auto`: `source` may acquire current web evidence and `assets` may acquire web images or write AI image jobs. Deterministic suites should pass `--network-policy fixture` or `--offline`; resume reuses existing source/assets unless `--refresh-online` is set. `--no-online-research`, `--no-image-search`, and `--no-ai-image` disable the corresponding acquisition path without changing the stage graph.

For user-facing local generation, use `--profile local_real_preview`. It targets `visual_acceptance`, does not run `live_create` or `readback`, and applies strict full-deck, unified-theme, and real-asset checks before the preview can be treated as deliverable.
