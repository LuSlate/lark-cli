# SVGlide Workflow Spec

Read this file only after `svglide-svg` route admission. It summarizes the P0 execution graph for runner-first `slides +create-svg` work and points to the private SVG route files for detailed rules.

## Stage Graph

```text
request
-> route admission
-> load SVG private rule set
-> init run directory
-> source
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
-> quality_gate
-> dry-run create
-> ppe_proof
-> live create
-> readback
-> delivery record
```

## Stage Contract

| Stage | Input | Output | Gate |
|---|---|---|---|
| route admission | user request, source root, plan route | confirmed `svglide-svg` route | if not admitted, stay on XML route |
| load rules | `svglide-svg-private.rules.json` | recorded `loaded_rule_set` | missing required private files blocks preflight |
| init | deck id, title | `.lark-slides/plan/<deck-id>/01-project/` | repeat init of the same deck id is rejected unless explicitly forced |
| source | `source/evidence.json` or `source/source-notes.md` | `source/evidence.json`, `source/source-receipt.json`, `receipts/source.json` | `source_status=thin/blocked`, too few evidence items, or stale source receipt blocks strategy/generation |
| plan | user goal, page count, sources | `02-plan/slide_plan.json`, optional `02-plan/svglide.lock.json`, `receipts/plan.json` | plan must declare route/output mode, style, loaded rules, art direction, quality gates, and SVG page metadata |
| strategy_review | `02-plan/slide_plan.json` | `02-plan/strategy-review.json` | language, audience, deck structure, page types, sections, roles, key messages, and content minimums must pass before confirmation |
| confirm plan | `02-plan/slide_plan.json`, optional lock | `02-plan/plan-confirmation.json`, `receipts/confirm_plan.json` | user confirmation is required before assets, SVG generation, prepare, dry-run, or live-create |
| assets | confirmed plan/lock asset contracts | `03-assets/assets.json`, `03-assets/asset-manifest.json`, `receipts/assets.json` | empty image boxes, required HTTP/data assets, and missing local files block the chain |
| generate_svg | confirmed plan, lock, and assets manifest | ordered `04-svg/page-###.svg` files, per-page receipts, `receipts/generate_svg.json` | each page must use SVGlide roles, 960 x 540 canvas, and safe geometry |
| prepare | `generate_svg` source SVG pages and asset map | ordered `04-svg/prepared/page-###.svg` files, `receipts/prepare.json` | unresolved local image placeholders block the chain; source SVG changes after `generate_svg` require rerun |
| build preview | prepared SVG pages and plan metadata | `05-preview/preview.html`, `05-preview/preview-manifest.json` | preview is a visual review aid, not the API contract |
| preflight | plan, prepared SVG | `06-check/preflight.json` | SVG protocol, plan contract, loaded rules, geometry, text, assets, and business claims must pass |
| preview_lint | local preview HTML | `06-check/preview-lint.json` | preview action must be `create_live` |
| aesthetic_review | preview lint and preview manifest | `06-check/aesthetic-review.json` | review status must be `passed` and action must be `create_live` |
| chart_verify | plan chart contracts and prepared SVG | `06-check/chart-verify.json` | required or exact chart pages must have data and chart-like marks; no required chart records `required_chart_count=0` and passes |
| semantic_review | plan, evidence, prepared SVG pages | `06-check/semantic-review.json`, `06-check/text-inventory.json` | language, audience, deck structure, page types, content density, source refs, and visible SVG text provenance must pass |
| runtime_review | plan renderer/layout declarations | `06-check/runtime-review.json` | missing renderer/layout declarations or renderer/layout monoculture blocks quality gate |
| quality_gate | generator receipt, preflight, preview lint, aesthetic review, chart verify, semantic review, runtime review | `06-check/quality-gate.json` | required checks must all pass and be fresh before dry-run or live create |
| dry-run create | checked prepared SVG files | `07-create/dry-run.json`, `07-create/create-command.txt` | request order and asset rewrites must match files |
| ppe_proof | current quality gate, dry-run, and PPE input | `07-create/ppe-proof.json` | live create is blocked unless PPE/auth/proxy/header proof is passed and fresh |
| live create | same checked prepared SVG files and PPE proof | `07-create/live-create.json` | partial failures must preserve the returned ids for recovery |
| readback | presentation id | `08-readback/readback-check.json` | page count, blank pages, bounds, text fit, assets, input binding, and closing slide must be checked |

## Route Boundary

The SVG route is private to `slides +create-svg`. XML creation, XML edit, and SXSD work must not load these SVG private strategy files unless route admission later proves that the request is SVG route work.
