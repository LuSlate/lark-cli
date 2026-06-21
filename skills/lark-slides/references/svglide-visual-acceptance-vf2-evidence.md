# SVGlide VF2 Screenshot And Geometry Evidence

Last updated: 2026-06-21

## Scope

VF2 strengthens visual acceptance evidence so reviewer and downstream gates can identify exactly what rendered artifact was judged.

It covers:

- actual contact sheet evidence path and hash
- deterministic contact sheet tile/crop metadata
- page-level preview anchors
- page PNG / semantic map / node layout map references
- page-level issue evidence paths
- downstream enforcement that artboard passed VA includes page-level `visual_evidence.pages`

It does not claim VF3-VF5 completion.

## Files Changed

```text
skills/lark-slides/scripts/svglide_visual_acceptance.py
skills/lark-slides/scripts/svglide_visual_acceptance_test.py
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_project_runner_test.py
skills/lark-slides/scripts/svglide_pre_submit_review.py
skills/lark-slides/scripts/svglide_pre_submit_review_test.py
skills/lark-slides/scripts/svglide_artboard_renderer.py
skills/lark-slides/references/svglide-visual-acceptance-repair-action.md
skills/lark-slides/references/svglide-artboard-full-plan-action.md
```

## Implemented Evidence Contract

`06-check/visual-acceptance.json` now includes:

```text
visual_evidence:
  schema_version: svglide-visual-evidence/v1
  contact_sheet:
    path: 05-preview/contact-sheet.png
    sha256: ...
  contact_sheet_grid:
    tile_width: 320
    tile_height: 180
    gap: 16
    max_cols: 3
  preview:
    path: 05-preview/preview.html
    sha256: ...
  preview_manifest:
    path: 05-preview/preview-manifest.json
    sha256: ...
  pages:
    - page: 1
      evidence_path: 05-preview/contact-sheet.png
      contact_sheet_tile: {x, y, width, height}
      preview_anchor: 05-preview/preview.html#page-1
      preview_source_path: 04-svg/prepared/page-001.svg
      page_png: 04-svg/artboard/page-001.png
      page_png_sha256: ...
      semantic_map: 04-svg/artboard/page-001.semantic-map.json
      node_layout_map: 04-svg/artboard/page-001.node-layout-map.json
```

Page-level visual issues now carry:

```text
page
code
path
bbox
evidence_path
preview_anchor
contact_sheet_tile
```

This gives reviewers one artifact to open and enough crop metadata to locate the failed page.

## Contact Sheet Producer

`svglide_artboard_renderer.write_contact_sheet()` now records:

- source PNG list
- fixed grid geometry
- per-page tile bbox
- per-page image bbox within the tile
- per-page label bbox
- source image dimensions

The visual acceptance checker can derive tile metadata independently, but the producer receipt now preserves the same geometry for debugging.

## Downstream Enforcement

`svglide_project_runner.py` now rejects passed `artboard_satori` visual acceptance if `visual_evidence.pages` is missing.

`svglide_pre_submit_review.py` now rejects passed `artboard_satori` visual acceptance if `visual_evidence.pages` is missing.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

Result:

```text
Ran 6 tests in 0.262s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
```

Result:

```text
Ran 46 tests in 8.863s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_pre_submit_review_test.py
```

Result:

```text
Ran 11 tests in 0.414s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_quality_gate_test.py
```

Result:

```text
Ran 32 tests in 1.067s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 369 tests in 21.555s
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

## Tests Added Or Updated

`svglide_visual_acceptance_test.py`:

- passed artboard fixture includes page-level visual evidence
- visual evidence points to `05-preview/contact-sheet.png`
- visual evidence includes preview anchor and deterministic contact sheet tile
- page-level overlap failure includes evidence path, preview anchor, and contact sheet tile
- stale page PNG failure includes page number, evidence path, preview anchor, and contact sheet tile

`svglide_project_runner_test.py`:

- downstream delivery rejects passed artboard VA without `visual_evidence.pages`

`svglide_pre_submit_review_test.py`:

- pre-submit rejects passed artboard VA without `visual_evidence.pages`

## Reviewer Blocker Fixed

Initial VF2 review found that stale page artifact failures from `check_recorded_hash()` did not carry `page`, so they could not be enriched with `evidence_path`, `preview_anchor`, and `contact_sheet_tile`.

Fix:

- `check_recorded_hash()` now accepts `page` and writes it into artifact missing/stale issues.
- `test_stale_page_png_failure_includes_visual_evidence_location` covers the reviewer repro.
- runner and pre-submit now validate that each `visual_evidence.pages` entry includes `page`, `evidence_path`, `preview_anchor`, and `contact_sheet_tile`.

## Reviewer Checklist

Reviewer must verify:

- reviewer can open `05-preview/contact-sheet.png` as the primary judged artifact
- each judged page has stable crop metadata
- each page has preview anchor metadata
- page-level failures include page number, issue code, evidence path, and crop metadata
- downstream gates reject missing `visual_evidence.pages`
- no claim is made that VF3-VF5 are complete

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

- stale page PNG failures now include `page`, `evidence_path`, `preview_anchor`, and `contact_sheet_tile`.
- visual acceptance writes page-level visual evidence tied to contact sheet and preview anchors.
- contact sheet producer records grid and per-page metadata.
- runner and pre-submit reject missing or malformed `visual_evidence.pages`.
- evidence doc does not claim VF3-VF5 completion.
