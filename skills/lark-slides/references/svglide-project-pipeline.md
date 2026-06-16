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
generate -> prepare -> preview -> preflight -> preview_lint -> quality_gate -> dry_run -> ppe_proof -> live_create -> readback
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
    generate.log
    prepare.log
    preview.log
    preflight.log
    preview-lint.log
    dry-run.log
    live-create.log
    readback.log
  receipts/
    timings.json
    env.json
    prepare.json
    preflight.json
    preview-lint.json
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

`preview_lint`, `preflight`, `quality_gate`, `ppe_proof`, `dry_run`,
`live_create`, and `readback` are runner-owned stages. Do not override
`preview_lint` through `stage_commands`; the runner calls the bundled
`scripts/svg_preview_lint.py` with a fixed argument contract.

## Prepare

`prepare` creates deterministic CLI-ready SVG files under `prepared/`.

Allowed P0 behavior:

- copy `pages/*.svg` to `prepared/*.svg`
- normalize file placement and receipt metadata
- record input and output digests

Disallowed P0 behavior:

- silently simplify visual effects
- apply PPTX/DrawingML compatibility rewrites
- mutate authoring `pages/*.svg`
- replace images or tokens outside the existing `slides +create-svg` transport path

Every mutation must be recorded in `receipts/prepare.json`.

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

`quality_gate` reads the latest preflight receipt, preview lint receipt, raster
report, allowlist, asset selection, and component report evidence. During P0
migration, authoring/debug dry-run may use an unexpired legacy component waiver.
Production, golden, and live lanes must not use that waiver.

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
- Do not copy `ppt-master` runtime or assets.
- Do not treat local preview as a replacement for live readback.
