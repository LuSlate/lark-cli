# SVGlide VF3 Renderer And Template Guardrails Evidence

Last updated: 2026-06-21

## Scope

VF3 adds template-level guardrails so artboard output cannot silently invent arbitrary geometry, fake chart marks, or late-pasted images.

It covers:

- template guardrail registry
- decorative primitive admission by template
- chart-like mark contract requirement
- image element CanvasSpec slot/source requirement
- template density limits
- downstream freshness binding to the guardrail registry hash

It does not claim VF4-VF5 completion.

## Files Changed

```text
skills/lark-slides/references/svglide-template-guardrails.json
skills/lark-slides/references/svg-private-manifest.json
skills/lark-slides/references/svglide-svg-private.rules.json
skills/lark-slides/scripts/svglide_visual_acceptance.py
skills/lark-slides/scripts/svglide_visual_acceptance_test.py
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_pre_submit_review.py
skills/lark-slides/references/svglide-visual-acceptance-repair-action.md
skills/lark-slides/references/svglide-artboard-full-plan-action.md
```

## Guardrail Registry

New file:

```text
skills/lark-slides/references/svglide-template-guardrails.json
```

It defines:

- default allowed primitive kinds
- allowed decorative primitive kinds
- admitted motif tokens
- per-template decorative limits
- density limits
- chart contract requirement
- image CanvasSpec slot requirement

The registry is included in:

- `svg-private-manifest.json`
- `svglide-svg-private.rules.json`

## Visual Acceptance Behavior

`svglide_visual_acceptance.py` now:

- loads `svglide-template-guardrails.json`
- records `template_guardrails_sha256` in `visual_acceptance.inputs`
- applies per-template decorative primitive rules
- fails unregistered decorative motifs
- fails sharp decorative paths unless admitted by the template guardrail
- fails chart-like elements without `chart_contract`
- fails image/raster/bitmap elements without a CanvasSpec image slot
- fails image elements whose `source_ref` does not come from CanvasSpec
- applies template density limits from the guardrail registry

## Downstream Freshness

`svglide_project_runner.py` rejects stale visual acceptance if `template_guardrails_sha256` no longer matches the current guardrail registry.

`svglide_pre_submit_review.py` rejects stale visual acceptance if `template_guardrails_sha256` no longer matches the current guardrail registry.

## Validation Commands

```bash
python3 -m json.tool skills/lark-slides/references/svglide-template-guardrails.json >/dev/null
python3 -m json.tool skills/lark-slides/references/svg-private-manifest.json >/dev/null
python3 -m json.tool skills/lark-slides/references/svglide-svg-private.rules.json >/dev/null
```

Result:

```text
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

Result:

```text
Ran 12 tests in 0.443s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
```

Result:

```text
Ran 46 tests in 11.020s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_pre_submit_review_test.py
```

Result:

```text
Ran 12 tests in 0.339s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_quality_gate_test.py
```

Result:

```text
Ran 32 tests in 1.160s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 376 tests in 23.503s
OK
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache python3 -m py_compile \
  skills/lark-slides/scripts/svglide_visual_acceptance.py \
  skills/lark-slides/scripts/svglide_project_runner.py \
  skills/lark-slides/scripts/svglide_pre_submit_review.py \
  skills/lark-slides/scripts/svglide_artboard_renderer.py
```

Result:

```text
OK
```

```bash
git diff --check
```

Result:

```text
OK
```

## Tests Added

`svglide_visual_acceptance_test.py`:

- unregistered decorative path fails template guardrail
- boolean `template_motif` cannot bypass admitted motif registry
- registered decorative motif passes template guardrail
- chart-like mark requires `chart_contract`
- image element without CanvasSpec slot and source ref fails
- image element with CanvasSpec slot and source ref passes

`svglide_pre_submit_review_test.py`:

- pre-submit rejects passed artboard VA when `template_guardrails_sha256` is missing

## Reviewer Blockers Fixed

Initial VF3 review found two blockers:

- boolean `template_motif: true` could bypass template-bound admitted motifs.
- pre-submit only compared `template_guardrails_sha256` when present, so a passed artboard VA could omit it.

Fix:

- `motif_registered()` no longer treats boolean `template_motif` as sufficient.
- `test_template_motif_boolean_does_not_bypass_admitted_motif` covers the bypass.
- `svglide_pre_submit_review.py` now requires `template_guardrails_sha256` for passed `artboard_satori` VA.
- `test_visual_acceptance_artboard_requires_template_guardrails_hash` covers the pre-submit bypass.

## Reviewer Checklist

Reviewer must verify:

- the renderer cannot silently introduce arbitrary path/polygon/polyline decorations
- admitted decorative motifs are template-bound rather than globally allowed
- chart-like marks require `chart_contract`
- image elements must be planned in CanvasSpec instead of late-pasted
- density limits come from template guardrails
- visual acceptance records and downstream gates validate `template_guardrails_sha256`
- manifest/rules include the new guardrail registry
- no claim is made that VF4-VF5 are complete

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

- boolean `template_motif: true` no longer bypasses admitted motifs.
- passed artboard VA missing `template_guardrails_sha256` now fails pre-submit.
- runner and pre-submit validate `template_guardrails_sha256`.
- manifest and rules include `svglide-template-guardrails.json`.
- evidence doc does not claim VF4-VF5 completion.

Non-blocking risk:

- guardrail registry load can be made more fail-closed in a later hardening pass.
