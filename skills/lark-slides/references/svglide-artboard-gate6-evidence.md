# SVGlide Artboard Gate 6 Evidence

Date: 2026-06-21

Gate: `Gate 6: P0a And P0b Local E2E`

Reviewer status before this evidence: `PENDING`

Reviewer verdict after re-review: `PASS`

## Scope

This evidence proves the checked-in P0a and P0b artboard fixtures are repeatable
through the real runner path, not ad hoc scripts.

Gate 6 does not claim `live_create` or `readback`; those remain Gate 7.

## P0a Fresh Run

Fixture source:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/p0a-cover
```

Fresh project:

```text
/private/tmp/svglide-p0a-gate6-zNSbw5
```

Command:

```bash
SVGLIDE_LARK_CLI_CMD="python3 /private/tmp/svglide_fake_lark_cli.py" \
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  /private/tmp/svglide-p0a-gate6-zNSbw5 \
  --until dry_run \
  --network-policy fixture \
  --asset-provider none \
  --image-backend none
```

Result:

```text
current_stage = dry_run
generate_svg = passed
prepare = passed
preflight = passed
quality_gate = passed
dry_run = passed
```

Template/theme hit:

```text
page 1 = cover-hero / dark-clarity
```

Required artifacts present:

```text
04-svg/artboard/raw/page-001.satori.svg
04-svg/artboard/page-001.png
04-svg/artboard/page-001.canvas-template.svg
04-svg/artboard/page-001.semantic-map.json
04-svg/artboard/page-001.node-layout-map.json
04-svg/artboard/page-001.receipt.json
04-svg/page-001.svg
05-preview/contact-sheet.png
06-check/quality-gate.json
07-create/dry-run.json
receipts/generate_svg.json
```

## P0b Fresh Run

Fixture source:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/p0b-three-page
```

Fresh project:

```text
/private/tmp/svglide-p0b-gate5-qg7PC6
```

Command:

```bash
SVGLIDE_LARK_CLI_CMD="python3 /private/tmp/svglide_fake_lark_cli.py" \
python3 skills/lark-slides/scripts/svglide_project_runner.py run \
  /private/tmp/svglide-p0b-gate5-qg7PC6 \
  --until dry_run \
  --network-policy fixture \
  --asset-provider none \
  --image-backend none
```

Result:

```text
current_stage = dry_run
generate_svg = passed
prepare = passed
preflight = passed
quality_gate = passed
dry_run = passed
```

Template/theme hit list:

```text
page 1 = cover-hero / dark-clarity
page 2 = comparison-cards / forest-signal
page 3 = summary-final / warm-editorial
```

Runner and receipt evidence:

```text
receipts/generate_svg.json:
  generation_mode = artboard_satori
  artboard_receipts = [
    04-svg/artboard/page-001.receipt.json,
    04-svg/artboard/page-002.receipt.json,
    04-svg/artboard/page-003.receipt.json
  ]

receipts/artboard-render.json:
  summary.max_workers = 3
  pages = [1, 2, 3]

receipts/satori-bridge.json:
  summary.max_workers = 3
  pages = [1, 2, 3]

06-check/quality-gate.json:
  status = passed
  failed_check_count = 0

07-create/dry-run.json:
  status = passed
```

## Validation Context

The same code state also passed:

```text
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
  Ran 254 tests
  OK

git diff --check
  passed with no output
```

## Remaining Scope

This evidence does not claim:

```text
Gate 7 P0c live_create/readback
Gate 8 chart marker readback
Gate 8 image asset readback
Gate 8 raster fallback fixture
Gate 9+ P1/P2 scale-out work
```
