# SVGlide Project Pipeline

This document owns local project execution artifacts for `slides +create-svg`.
It does not replace `slide_plan.json`, `svg-protocol.md`, `lark-slides-create-svg.md`,
or `svg_preflight.py`.

## Scope

The pipeline standardizes how a generated SVGlide deck is stored, resumed, timed,
validated, and published.

It owns:

- `.lark-slides/plan/<deck-id>/project_manifest.json`
- `.lark-slides/plan/<deck-id>/state.json`
- `pages/`, `prepared/`, `preview/`, `logs/`, and `receipts/`
- the stage order and runner receipts

It does not own:

- SVG protocol syntax
- chart creation protocol
- seed / recipe / style semantics
- image upload implementation
- Lark Slides server behavior
- PPTX or DrawingML compatibility

## Stage Order

```text
source -> strategy -> generate -> prepare -> preview -> preflight -> preview_lint -> chart_verify -> quality_gate -> dry_run -> ppe_proof -> live_create -> readback
```

`render_contact_sheet` is an optional artifact stage after readback/raster
receipts. It is not part of the default `--until dry_run` authoring path.

`dry_run` and `live_create` must consume `prepared/*.svg`, never the authoring
`pages/*.svg`.

## Directory Layout

```text
.lark-slides/plan/<deck-id>/
  project_manifest.json
  state.json
  source/
    brief.md
    inputs.json
    evidence.json
    source_pack.json
    design_spec.json
  slide_plan.json
  assets/
    asset_manifest.json
  pages/
    page-001.svg
  prepared/
    page-001.svg
  preview/
    preview.html
  logs/
    source.log
    strategy.log
    generate.log
    prepare.log
    preview.log
    preflight.log
    preview-lint.log
    chart-verify.log
    dry-run.log
    live-create.log
    readback.log
  receipts/
    timings.json
    env.json
    source.json
    strategy.json
    prepare.json
    preflight.json
    preview-lint.json
    chart-verify.json
    quality-gate.json
    dry-run.json
    live-create.json
    readback.json
```

## Manifest

`project_manifest.json` indexes execution files and commands. It must not redefine
design truth already owned by `slide_plan.json`.

```json
{
  "deck_id": "example-deck",
  "title": "Example Deck",
  "lane": "pure_svg",
  "plan": "slide_plan.json",
  "source": {
    "status": "user_prompt_only",
    "brief": "source/brief.md",
    "evidence": "source/evidence.json",
    "source_pack": "source/source_pack.json"
  },
  "pages": [
    {
      "page": 1,
      "source_svg": "pages/page-001.svg",
      "prepared_svg": "prepared/page-001.svg"
    }
  ],
  "stage_commands": {
    "generate": "python3 generate_deck.py",
    "prepare": "builtin:copy_and_normalize_svg",
    "preview": "python3 generate_preview.py"
  },
  "live_guard": {
    "target_env": "ppe_pure_svg",
    "requires_allow_live": true,
    "requires_auth_verified": true,
    "requires_proxy_receipt": true
  }
}
```

Stage commands are parsed as argv and executed with `shell=False`. Project-local
commands run from the project directory. Commands under `skills/lark-slides/`
run from the CLI worktree root.

`slide_plan.json` is still the design source of truth. `project_manifest.json`
is the execution index. Before `prepare`, these counts must agree:

- `slide_plan.page_count`
- `len(slide_plan.slides)` when `slides` is present
- `len(slide_plan.svg_files)` when `svg_files` is present
- `len(project_manifest.pages)`

When the plan changes, regenerate or update the manifest in the same step.
Do not let `prepare`, `preflight`, `dry_run`, or `live_create` consume a stale
manifest after pages were added, deleted, or reordered.

## Source And Strategy Discipline

Pure topic input must first become structured source state before page SVG is
rendered. Store the original brief in `source/brief.md`; store source status,
evidence ids, numeric-claim policy, and missing-source notes in
`source/source_pack.json` or top-level `slide_plan.source_pack`. Research notes
or citation indexes belong in `source/evidence.json` when they exist. The
runner-owned `source` stage writes these files before generation when the
project starts from a prompt or manifest brief.

`slide_plan.json` must keep strategy decisions in the existing plan surface:

- `narrative_mode`: story mode, not visual style.
- `visual_style`: visual language target.
- `strategy_locks`: exactly eight locked decisions with `id`, `decision`, and
  `evidence_ref`.
- `asset_strategy`, `chart_policy`, and `icon_policy`: deck-level selection
  policy.
- page-level `source_refs`, `asset_selection_reason`,
  `rejected_asset_alternatives`, `chart_decision`, and `chart_verification`.

The runner-owned `strategy` stage writes `source/design_spec.json` and refreshes
`slide_plan.json` with the current strategy locks, style system, renderer
selection, source pack reference, and design spec reference. `design_spec.json`
is a receipt-like summary for audit and comparison; `slide_plan.json` remains
the protocol-facing plan.

The runner fingerprints source files, plan, catalogs, generated SVG, prepared
SVG, and receipts. Source pack changes should invalidate receipts rather than
letting old generation or quality evidence be reused silently.

`source`, `strategy`, `preview_lint`, `preflight`, `chart_verify`,
`quality_gate`, `ppe_proof`, `dry_run`, `live_create`, and `readback` are
runner-owned stages. Do not override `preview_lint` through `stage_commands`;
the runner calls the bundled `scripts/svg_preview_lint.py` with a fixed
argument contract.

## Prepare

`prepare` creates deterministic CLI-ready SVG files under `prepared/`.
`dry_run` and `live_create` must consume `prepared/*.svg`, never authoring
`pages/*.svg` directly.

Allowed P0 behavior:

- copy `pages/*.svg` to `prepared/*.svg`
- normalize file placement and receipt metadata
- record input and output digests

Disallowed P0 behavior:

- silently simplify visual effects
- apply PPTX/DrawingML compatibility rewrites
- mutate authoring `pages/*.svg`
- replace images or tokens outside the existing `slides +create-svg` transport path

## SVGlide Design Pattern Receipt

SVGlide design pattern references are allowed only as structure, rhythm, chart geometry,
style, and review inspiration. They are not runtime dependencies and raw SVG/PPTX
assets must not be copied into SVGlide output.

For quality lanes, `selected_assets` means "actually used by the generated
pages", not "interesting candidates found during research". Candidate assets
stay in research notes. Used assets must be proven by
`receipts/design-pattern-usage.json` with page-level trace entries that point
to the SVG evidence. The quality gate must fail when `selected_assets` includes
an asset that is not present in the usage receipt.

Every mutation must be recorded in `receipts/prepare.json`.

Chart pages should additionally write `receipts/chart-verify.json` when data
coordinates are available. This receipt verifies source data against visible SVG
or native chart geometry: expected mark count, bar height/width, line points,
stacked proportions, labels, and plot-area alignment. When data is not available,
the plan must say so and avoid numeric claims.

## Runner

The runner command is:

```bash
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  --project .lark-slides/plan/<deck-id> \
  --cli ./lark-cli \
  --until dry-run
```

Live creation requires explicit flags:

```bash
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  --project .lark-slides/plan/<deck-id> \
  --cli ./lark-cli \
  --until readback \
  --env ppe_pure_svg \
  --env-proof receipts/env-proof.json \
  --allow-live
```

P0 only allows `--env ppe_pure_svg` for live creation.

## Quality Gate

The project runner treats preview lint as a hard gate only in the project
quality lane. Manual debugging may continue from preflight to dry-run/readback
without `preview/preview.html`, but it must not proceed to guarded live creation
or production/golden delivery until preview lint and quality gate have passed.

`chart_verify` reads `slide_plan.json` and `prepared/*.svg`. When a slide
declares a required `chart_decision`, it writes `receipts/chart-verify.json`
proving that the expected chart carrier exists in the prepared SVG. This first
pass checks visible geometry and anchors; stricter data-to-coordinate checks can
extend the same receipt.

`quality_gate` reads the latest preflight receipt, preview lint receipt,
chart-verify receipt, raster report, allowlist, asset selection, visual design
contract, and component report evidence. If a slide declares
`visual_design_contract.required_visual_evidence`, the same page in
`receipts/emitted_components.json` must prove those evidence tokens through
component `effects`, `primitives`, `renderer_id`, or component id. During P0
migration, authoring/debug dry-run may use an unexpired legacy component
waiver. Production, golden, and live lanes must not use that waiver.

## PPE Proof

`ppe_proof` normalizes raw environment evidence into
`receipts/env-proof.json`. Raw proof may contain `observed_at_ms + ttl_ms`; the
runner writes a normalized `expires_at_ms` and live creation only reads the
normalized receipt.

## Receipts

Receipts are compact evidence files. Large raw command output goes under `logs/`.

Every receipt should include:

- stage name
- status
- elapsed time
- input digest and expanded `input_fingerprint`
- command argv when applicable
- log path
- parsed summary when available

`receipts/timings.json` aggregates stage elapsed times.

## Live Guard

`live_create` must refuse to run unless:

- `--allow-live` is present
- `--env ppe_pure_svg` is present
- auth verification succeeds
- `--env-proof` points to JSON evidence that `open.feishu.cn` was routed to
  `open.feishu-pre.cn` with `Env=Pre_release` and `x-tt-env=ppe_pure_svg`
- `dry_run` passed after the latest `prepare`
- `quality_gate` passed strictly after the latest preflight and preview lint
- `ppe_proof` is fresh for the current CLI path/version, auth subject, target
  host/headers, and smoke lane
- proxy/header configuration is recorded in `receipts/env.json`
- duplicate live creation is not already recorded

Proxy/header proof must be explicit for live creation. Local proxy presence alone
is recorded as `configured_not_observed` and is not enough to run `live_create`.

## Validation Profile

`validation_profile` may appear in `slide_plan.json` as a profile over existing
fields:

```json
{
  "validation_profile": {
    "mode": "svglide_project_pipeline",
    "locked_fields": ["canvas", "style_preset", "style_system", "visual_recipe"],
    "drift_policy": "warn_first"
  }
}
```

It is not a second source of truth. It must not redefine canvas, style, recipe,
asset, or protocol values.

## Boundaries

- Do not add a top-level `svglide_plan_lock`.
- Do not introduce a fourth structure catalog.
- Do not modify Open Design for this rollout.
- Do not rewrite Go CLI code in P0.
- Do not copy external runtime or raw assets.
- Do not treat local preview as a replacement for live readback.
