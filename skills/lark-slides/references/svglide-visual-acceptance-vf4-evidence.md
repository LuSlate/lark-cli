# SVGlide VF4 Theme And Deck Rhythm Lock Evidence

Last updated: 2026-06-21

## Scope

VF4 adds deck-level checks so a deck cannot pass visual acceptance while every page collapses into the same generic composition or an uncontrolled theme mix.

It covers:

- deck rhythm summary
- layout family variety
- renderer sequence variety
- visual recipe variety
- maximum consecutive renderer repetition
- theme token budget
- downstream enforcement that passed artboard VA includes `deck_rhythm`

It does not claim VF5 completion.

## Implemented Contract

`06-check/visual-acceptance.json` now includes:

```text
deck_rhythm:
  schema_version: svglide-deck-rhythm/v1
  slide_count: ...
  layout_family_sequence: [...]
  renderer_sequence: [...]
  visual_recipe_sequence: [...]
  theme_ids: [...]
  unique_layout_family_count: ...
  unique_renderer_count: ...
  unique_visual_recipe_count: ...
  unique_theme_id_count: ...
  longest_layout_run: {value, length}
  longest_renderer_run: {value, length}
  longest_visual_recipe_run: {value, length}
  thresholds: ...
  theme_policy: ...
```

## Blocking Checks

Visual acceptance now fails when:

- all slides use one `layout_family`
- all slides use one `renderer_id`
- decks with four or more slides have fewer than two layout families
- decks with four or more slides have fewer than two renderers
- decks with four or more slides collapse to one `visual_recipe`
- one renderer repeats more than three consecutive pages
- the deck uses more than two theme IDs without `theme_policy.allow_multi_theme=true`

## Downstream Enforcement

`svglide_project_runner.py` rejects passed `artboard_satori` VA without `deck_rhythm`.

`svglide_pre_submit_review.py` rejects passed `artboard_satori` VA without `deck_rhythm`.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

Result:

```text
Ran 13 tests in 0.453s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
```

Result:

```text
Ran 47 tests in 9.294s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_pre_submit_review_test.py
```

Result:

```text
Ran 13 tests in 0.480s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_quality_gate_test.py
```

Result:

```text
Ran 32 tests in 2.084s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 379 tests in 23.333s
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

- valid VA output includes `deck_rhythm`
- collapsed layout/renderer/visual recipe and fragmented themes are detected

`svglide_project_runner_test.py`:

- downstream delivery rejects passed artboard VA without `deck_rhythm`

`svglide_pre_submit_review_test.py`:

- pre-submit rejects passed artboard VA without `deck_rhythm`

## Reviewer Checklist

Reviewer must verify:

- visual acceptance writes `deck_rhythm`
- collapsed layout/renderer/visual recipe fails
- long renderer repetition fails
- theme fragmentation fails unless explicitly allowed
- downstream gates reject missing `deck_rhythm`
- no claim is made that VF5 is complete

## Reviewer Verdict

Reviewer: Pascal

Verdict: PASS

Blocking issues:

- None.

Non-blocking risks:

- `allow_multi_theme` was command-verified but does not yet have dedicated unit coverage.
- `deck_rhythm` depends on plan-level `layout_family`, `renderer_id`, and `visual_recipe` fields; missing fields are skipped by design in VF4 and should be tightened when VF5 evidence shows repeated missing metadata.
