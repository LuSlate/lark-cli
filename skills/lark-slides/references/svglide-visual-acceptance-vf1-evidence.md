# SVGlide VF1 Visual Acceptance Gate Evidence

Last updated: 2026-06-21

## Scope

VF1 implements a deterministic visual acceptance gate after engineering gates and before visual delivery claims.

This evidence covers:

- machine visual acceptance check
- runner stage ordering and freshness checks
- pre-submit binding to visual acceptance evidence
- quality gate independence from visual acceptance
- unit-test coverage for pass, fail, stale, and skipped engineering-only cases

It does not claim VF2-VF5 completion. Some VF2/VF3/VF4 checks are partially implemented in `svglide_visual_acceptance.py`, but the later gates still require their own reviewer PASS.

## Files Changed

```text
skills/lark-slides/scripts/svglide_visual_acceptance.py
skills/lark-slides/scripts/svglide_visual_acceptance_test.py
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_project_runner_test.py
skills/lark-slides/scripts/svglide_pre_submit_review.py
skills/lark-slides/scripts/svglide_pre_submit_review_test.py
skills/lark-slides/scripts/svglide_quality_gate_test.py
skills/lark-slides/references/svg-private-manifest.json
skills/lark-slides/references/svglide-svg-private.rules.json
skills/lark-slides/references/svglide-visual-acceptance-repair-action.md
skills/lark-slides/references/svglide-artboard-full-plan-action.md
```

## Implemented Behavior

```text
dry_run
  -> visual_acceptance
  -> ppe_proof
  -> pre_submit_review
  -> live_create
  -> readback
```

`quality_gate` stays an engineering gate. It does not require visual acceptance.

`visual_acceptance` writes:

```text
06-check/visual-acceptance.json
receipts/visual_acceptance.json
```

For `artboard_satori`, a delivery claim requires:

- `quality_gate` passed
- `dry_run` passed
- `05-preview/preview.html`
- `05-preview/preview-manifest.json`
- `05-preview/contact-sheet.png`
- fresh `receipts/generate_svg.json`
- fresh artboard receipts
- fresh page PNG / semantic map / node layout map hashes
- downstream freshness checks for the recorded artboard receipt / page PNG / semantic map / node layout map hashes
- no blocking visual acceptance issues

For non-artboard output, the check is explicitly:

```text
status: skipped
action: engineering_only
deliverable_pass: false
```

This skipped state cannot support high-quality visual claims.

## Deterministic Checks

Current VF1 deterministic checks include:

- expected page count vs instruction/final plan/preview manifest
- generator contact sheet hash vs current contact sheet
- quality gate and dry run status
- dry run prepared file hash agreement with quality gate
- artboard receipt count and artifact freshness
- page PNG freshness
- semantic map freshness
- node layout map freshness
- text bbox inside canvas and safe area
- high-priority text overlap
- excessive page/text/decorative density
- unregistered sharp decorative geometry
- chart-like marks without chart contract
- collapsed layout or renderer rhythm
- fragmented theme usage

## Pre-Submit Binding

`svglide_pre_submit_review.py` now treats `06-check/visual-acceptance.json` as a required reviewed artifact.

It validates:

- visual acceptance status is `passed`, or `skipped` only with `action=engineering_only`
- skipped visual acceptance has `deliverable_pass=false`
- passed visual acceptance has `deliverable_pass=true`
- visual acceptance plan hash is current
- visual acceptance quality gate / dry run / preview / preview manifest / contact sheet hashes are current when recorded
- visual acceptance recorded artboard artifact hashes are current when recorded
- `receipts/visual_acceptance.json` exists and matches `06-check/visual-acceptance.json`
- human `reviewed_artifacts.visual_acceptance` points to the current visual acceptance check hash

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

Result:

```text
Ran 5 tests in 0.208s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
```

Result:

```text
Ran 45 tests in 9.922s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_pre_submit_review_test.py
```

Result:

```text
Ran 10 tests in 0.307s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_quality_gate_test.py
```

Result:

```text
Ran 32 tests in 1.017s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 366 tests in 22.183s
OK
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache python3 -m py_compile \
  skills/lark-slides/scripts/svglide_visual_acceptance.py \
  skills/lark-slides/scripts/svglide_project_runner.py \
  skills/lark-slides/scripts/svglide_pre_submit_review.py \
  skills/lark-slides/scripts/svglide_quality_gate_test.py
```

Result:

```text
OK
```

```bash
python3 -m json.tool skills/lark-slides/references/svg-private-manifest.json >/dev/null
python3 -m json.tool skills/lark-slides/references/svglide-svg-private.rules.json >/dev/null
```

Result:

```text
OK
```

## Tests Added Or Updated

`svglide_visual_acceptance_test.py`:

- valid artboard fixture passes and writes check/receipt
- valid artboard fixture records artboard receipt, semantic map, node layout map, and page PNG hashes
- missing contact sheet fails
- stale contact sheet hash fails
- high-priority text overlap fails
- direct SVG output is skipped as engineering-only

`svglide_project_runner_test.py`:

- visual acceptance aliases resolve
- stage order places visual acceptance after dry run and before delivery stages
- dry-run target excludes visual acceptance
- production live order includes visual acceptance
- artboard delivery stages require current visual acceptance
- downstream delivery stages reject visual acceptance check/receipt mismatch
- downstream delivery stages reject skipped visual acceptance if it is mislabeled as deliverable
- downstream delivery stages reject stale artboard receipt and page PNG after visual acceptance

`svglide_pre_submit_review_test.py`:

- human reviewed artifacts must include current visual acceptance
- missing visual acceptance blocks pre-submit review
- failed visual acceptance blocks pre-submit review
- stale visual acceptance human artifact blocks pre-submit review
- stale artboard artifact recorded by visual acceptance blocks pre-submit review

`svglide_quality_gate_test.py`:

- failed visual acceptance file does not affect quality gate pass/fail

## Reviewer Checklist

Reviewer must verify:

- `quality_gate` does not depend on `visual_acceptance`
- `dry_run` does not depend on `visual_acceptance`
- artboard delivery stages cannot proceed without fresh passed visual acceptance
- artboard delivery stages cannot proceed if recorded artboard receipt/page artifact hashes changed after visual acceptance
- skipped visual acceptance remains engineering-only and cannot be relabeled as deliverable
- pre-submit cannot replace machine visual acceptance with a human checkbox
- skipped visual acceptance is visibly marked `engineering_only` and `deliverable_pass=false`
- evidence commands above pass in this branch

## Reviewer Verdict

Reviewer: Pascal

Verdict:

```text
PASS
```

Blocking issues:

```text
None.
```

Reviewer-verified evidence:

- `quality_gate` and `dry_run` remain engineering gates.
- `artboard_satori` delivery order is `dry_run -> visual_acceptance -> ppe_proof -> pre_submit_review -> live_create -> readback`.
- downstream stages call `require_visual_acceptance_current()`.
- visual acceptance records `artboard_artifacts` for artboard receipt, semantic map, node layout map, and page PNG.
- runner and pre-submit rehash recorded artboard artifacts before proceeding.
- mutating `04-svg/artboard/page-001.receipt.json` or `04-svg/artboard/page-001.png` after VA now raises stale-artifact failure.
- skipped visual acceptance must remain `engineering_only` with `deliverable_pass=false`.
- evidence doc does not overclaim VF2-VF5.

## Remaining Work After VF1

VF2:

- richer screenshot/crop metadata and reviewer-friendly page evidence

VF3:

- stronger template registry constraints for admitted motifs, chart contracts, and image slots

VF4:

- stronger deck-level theme/rhythm policy and fixtures

VF5:

- real prompt benchmark suite and comparison screenshots for `spacex IPO analysis`, `Iceland volcano research`, and `New Zealand landscape`
