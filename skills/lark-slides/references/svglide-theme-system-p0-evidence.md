# SVGlide Theme System P0 Evidence

This file is the reviewer-facing evidence for the Theme System P0 plan in
`/Users/bytedance/Desktop/SVGlide-Theme-System-立项文档.md`.

## Scope

P0 proves a minimal executable loop:

- ThemeSpec exists and rejects invalid themes.
- `theme_validate` validates plan/canvas `theme_id` against the registry.
- `theme_adherence` checks final `04-svg/prepared/*.svg` colors and direct
  text contrast.
- `quality_gate` consumes theme receipts and freshness.
- `production_live` requires a current human `pre_submit_review` before
  `live_create`.
- `direct_svg` is not blocked by artboard package checks.

P0 does not claim automatic aesthetics, image/gradient sampling, full CSS
cascade, editor UI, slide server changes, PPTX export, animation, narrated
output, or a complete theme/template product surface.

P1/P2 are not targets for this evidence slice. In particular, this file does
not claim model-driven theme extraction, productized theme authoring UI,
cross-deck theme migration, export packaging, or automated aesthetic approval.

## Branch And Baseline

Observed during this evidence update:

```text
worktree: /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private
branch: feat/svglide-artboard-satori
implementation base HEAD before evidence patch: 842e2d44dec7a16f1b432687e2ae4e49fb9b2333
```

The original document's section 0 described an older target HEAD where many
files were still dirty overlay. Current branch HEAD already contains the Theme
System implementation files from commit `842e2d44`.

## P0 Checklist

| Item | Status | Evidence |
| --- | --- | --- |
| P0-0 baseline normalization | PASS | artboard renderer, package check, canvas schema, and template registry are tracked in HEAD |
| P0-1 ThemeSpec schema | PASS | `references/svglide-theme-spec.schema.json`; `svglide_theme_test.py` |
| P0-2 theme utilities | PASS | `svglide_theme.py` covers registry/theme load, stable hashes, static SVG colors, contrast |
| P0-3 theme_validate | PASS | `svglide_theme_validate.py` writes `06-check/theme-validate.json` and `receipts/theme-validate.json` |
| P0-4 theme_adherence | PASS | `svglide_theme_adherence.py` checks final prepared SVG colors, contrast, and stale theme validation |
| P0-5 pre_submit_review | PASS | `svglide_pre_submit_review.py` requires structured human approval and freshness |
| P0-6a runner theme/package stages | PASS | `svglide_project_runner.py` supports `theme_validate`, `package_check`, `theme_adherence` |
| P0-6b production_live submit gate | PASS | `production_live` path requires current `pre_submit_review` before `live_create` |
| P0-7 quality_gate integration | PASS | `svglide_quality_gate.py` consumes theme receipts; `artboard_satori` requires package check; `direct_svg` does not |
| P0-8 fixtures/evidence/regression | PASS | positive and negative fixtures added under `fixtures/svglide_artboard/theme-system-*`; this file records commands |

Contract details closed during this update:

- `pre_submit_review` accepts both the keyed object format and the document
  example format `[{kind, path, sha256}]` for `reviewed_artifacts`.
- runner `pre_submit_review` uses the documented default human input file:
  `06-check/pre-submit-human-review.json`.

## Fixture Coverage

Positive fixtures:

- `skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori`
  - three pages: cover, content, closing
  - `generation_mode=artboard_satori`
  - expected: `theme_validate=passed`, `theme_adherence=passed`
- `skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg`
  - one direct SVG page
  - expected: `theme_validate=passed`, `theme_adherence=passed`
  - used to document that `direct_svg` does not require artboard package check

Negative fixtures:

- `skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color`
  - expected issue: `theme_unknown_color`
- `skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast`
  - expected issue: `contrast_too_low`
- `skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate`
  - expected issue: `theme_validate_plan_stale`

The fixture regression is executable through:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_theme_system_p0_fixture_test.py
```

## P0-8 Receipt Paths

Positive receipt paths written by the fixture commands:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori/06-check/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori/receipts/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori/06-check/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori/receipts/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg/06-check/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg/receipts/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg/06-check/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg/receipts/theme-adherence.json
```

Negative receipt paths written by the fixture commands:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color/06-check/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color/receipts/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color/06-check/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color/receipts/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast/06-check/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast/receipts/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast/06-check/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast/receipts/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate/06-check/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate/receipts/theme-validate.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate/06-check/theme-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate/receipts/theme-adherence.json
```

## Commands Run

Command templates used for reviewer reproduction:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_validate.py <project_root> --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py <project_root> --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest <test_file_or_test_case>
```

Real fixture commands run for this P0-8 evidence pass:

```bash
git -C /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private status --short --branch
git -C /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private rev-parse HEAD

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_validate.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_validate.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_validate.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_validate.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/artboard-satori \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-p0/direct-svg \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/unknown-color \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/low-contrast \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_theme_adherence.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/theme-system-invalid/stale-theme-validate \
  --pretty

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_validate_test.py \
  skills/lark-slides/scripts/svglide_theme_adherence_test.py

env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_theme_system_p0_fixture_test.py
```

Observed P0-8 command results:

```text
branch: feat/svglide-artboard-satori
HEAD: 842e2d44dec7a16f1b432687e2ae4e49fb9b2333
artboard-satori theme_validate: passed, page_count=3, theme_count=1
artboard-satori theme_adherence: passed, prepared_svg_count=3
direct-svg theme_validate: passed, page_count=1, theme_count=1
direct-svg theme_adherence: passed, prepared_svg_count=1
unknown-color theme_validate: passed
unknown-color theme_adherence: failed as expected with theme_unknown_color
low-contrast theme_validate: passed
low-contrast theme_adherence: failed as expected with contrast_too_low
stale-theme-validate theme_adherence: failed as expected with theme_validate_plan_stale
svglide_theme_validate_test.py + svglide_theme_adherence_test.py: Ran 11 tests, OK
theme_system_p0_fixture_test.py: Ran 4 tests, OK
```

Targeted P0 tests:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest \
    skills/lark-slides/scripts/svglide_theme_test.py \
    skills/lark-slides/scripts/svglide_theme_validate_test.py \
    skills/lark-slides/scripts/svglide_theme_adherence_test.py \
    skills/lark-slides/scripts/svglide_pre_submit_review_test.py \
    skills/lark-slides/scripts/svglide_project_runner_test.py \
    skills/lark-slides/scripts/svglide_quality_gate_test.py \
    skills/lark-slides/scripts/svglide_theme_system_p0_fixture_test.py
```

Result:

```text
Ran 103 tests in 8.395s
OK
```

Full scripts unittest discovery:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 335 tests in 16.636s
OK
```

Package check tests:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_artboard_package_check_test.py
```

Result:

```text
Ran 4 tests in 0.127s
OK
```

Go root package test:

```bash
env GOCACHE=/private/tmp/svglide-gocache go test .
```

Result:

```text
ok  	github.com/larksuite/cli	0.739s
```

Package runtime check:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_artboard_package_check.py \
  --output-dir /private/tmp/svglide-theme-system-p0-package-check-final \
  --pretty
```

Result:

```text
status: passed
runtime_check_count: 2
output receipts:
  /private/tmp/svglide-theme-system-p0-package-check-final/06-check/artboard-package-check.json
  /private/tmp/svglide-theme-system-p0-package-check-final/receipts/artboard-package-check.json
```

## Key Runtime Boundaries

- `pre_submit_review` is a human receipt validator. It is not an automatic
  aesthetics model.
- `theme_adherence` only checks static SVG colors and direct text/background
  contrast in final prepared SVG files.
- Satori SVG remains an artboard preview/intermediate artifact; final theme
  adherence is checked on `04-svg/prepared/*.svg`.
- `direct_svg` still runs theme checks, but it must not require
  `artboard-package-check`.
- `export` is outside Theme System P0. The P0 plan explicitly does not claim
  PPTX or narrated deck output.
