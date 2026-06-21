# SVGlide Artboard Gate 12a Evidence

Status: DONE / reviewer PASS

Gate: Instruction / Plan / Output Adherence

Reviewer verdict:

```text
Verdict: PASS
Blocking issues: none
Non-blocking risk: Gate 12a PASS does not mean Gate 12b or full PLAN completion.
```

## Scope

Gate 12a verifies that a durable user instruction remains consistent through:

```text
00-input/instruction.json
-> 02-plan/deck-plan.json
-> 02-plan/slide-plan.json
-> 02-plan/slide_plan.json
-> 04-svg/page-###.svg
-> 08-readback/readback-check.json + xml-presentations-get.json
```

It does not enter Gate 12b final acceptance.

## Files Added Or Updated

```text
skills/lark-slides/scripts/svglide_instruction_adherence.py
skills/lark-slides/scripts/svglide_instruction_adherence_test.py
.tmp/svglide-p0c-gate7-live6/00-input/instruction.json
.tmp/svglide-p0c-gate7-live6/02-plan/deck-plan.json
.tmp/svglide-p0c-gate7-live6/02-plan/slide-plan.json
.tmp/svglide-p0c-gate7-live6/02-plan/slide_plan.json
.tmp/svglide-p0c-gate7-live6/08-readback/readback-check.json
.tmp/svglide-p0c-gate7-live6/08-readback/xml-presentations-get.json
.tmp/svglide-p0c-gate7-live6/06-check/instruction-adherence.json
.tmp/svglide-p0c-gate7-live6/receipts/instruction-adherence.json
```

Removed stale Gate10-only evidence:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner/01-project/instruction-lock.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner/06-check/instruction-adherence.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate10_planner/receipts/instruction-adherence.json
```

## Durable Instruction Capture

Project:

```text
.tmp/svglide-p0c-gate7-live6
```

Instruction artifact:

```text
.tmp/svglide-p0c-gate7-live6/00-input/instruction.json
```

Captured requirements:

```text
topic: SVGlide Artboard P0c live closure
language: zh-CN
audience: SVGlide engineers
target_slide_count: 3
must_include:
  - 画板链路 P0b
  - 三页 fixture 验证模板系统、质量门禁和 dry-run 编排。
  - 新旧链路差异
  - 核心变化是把美学标准从自由生成迁移到受控设计系统。
  - 下一步进入真实 Satori
  - 先稳定多页画板系统，再替换底层 renderer 并推进 live/readback。
must_avoid:
  - 自由 HTML
  - 自由 CSS
  - 自由 SVG
  - 系统截图
  - 编造具体数值
output_requirements:
  - generation_mode=artboard_satori
  - final_format=SVGlide protocol SVG
  - live_create_required=true
  - readback_required=true
  - page_order_locked=true
repair_policy:
  - default_on_missing_page=scoped_append_page
  - default_on_local_mismatch=scoped_leaf_patch
```

Explicit constraints are surface-aware:

```text
plan evidence:
  - artboard_satori
  - SVGlide protocol SVG
  - 不输出自由 HTML/CSS/SVG
  - 不使用系统截图
  - readback / 页数 / 顺序 / 关键文本
output/readback evidence:
  - Satori
  - resvg
  - readback
```

## Adherence Check

Scoped repair performed before the final check:

```text
target: .tmp/svglide-p0c-gate7-live6/02-plan/slide_plan.json
patch type: leaf-only key_message repair
patched fields:
  - /slides/0/key_message
  - /slides/1/key_message
  - /slides/2/key_message
reason: align final slide_plan key_message with instruction, deck-plan, slide-plan, SVG output, and readback visible key text
full regeneration: not used
```

Readback was then refreshed with the current branch CLI so the readback binding hashes the scoped-repaired plan:

```bash
env SVGLIDE_LARK_CLI_CMD='go run .' PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_readback.py \
  .tmp/svglide-p0c-gate7-live6 \
  --pretty
```

Result:

```text
status: passed
input_binding.plan_sha256: 3aa06d0877a587f8b62d0c8934fcc03ec8e34823c00c725f4e16c3d44ceb3bb7
readback page_count / slide_order / core_visible_text: passed
```

Command:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_instruction_adherence.py \
  .tmp/svglide-p0c-gate7-live6 \
  --pretty
```

Result:

```text
status: passed
issues: []
target_slide_count: 3
deck_plan.slide_count: 3
slide_plan.slide_count: 3
final slide_plan.slide_count: 3
output_pages: 3
readback.slide_count: 3
readback.slide_ids: pbb, pbu, pbe
must_include_missing: []
must_avoid_present: []
constraint_checks: all missing_text={}
repair_recommendations: no_repair_needed
```

Readback binding freshness:

```text
plan_sha256 matched current 02-plan/slide_plan.json
quality_gate_sha256 matched current 06-check/quality-gate.json
dry_run_sha256 matched current 07-create/dry-run.json
ppe_proof_sha256 matched current 07-create/ppe-proof.json
live_create_sha256 matched current 07-create/live-create.json
```

Receipt paths:

```text
.tmp/svglide-p0c-gate7-live6/06-check/instruction-adherence.json
.tmp/svglide-p0c-gate7-live6/receipts/instruction-adherence.json
```

## What The Checker Enforces

- `00-input/instruction.json` exists and uses `svglide-instruction/v1`.
- `target_slide_count` matches deck-plan, slide-plan, final `slide_plan`, SVG output page count, readback page count, and readback slide id count.
- Actual `slides[]` length in deck-plan, slide-plan, and final `slide_plan` matches the instruction, so a stale target field cannot hide missing pages.
- Page order matches instruction, deck-plan, slide-plan, and final `slide_plan`.
- Per-page title, exact `key_message`, required text, template id, and theme id propagate through planner outputs, final `slide_plan`, SVG output, and readback visible text.
- `zh-CN` output/readback pages contain CJK visible text.
- `must_include` is present in readback.
- `must_avoid` is absent from SVG output and readback.
- Explicit constraints are checked on their declared evidence surfaces: plan, output, and/or readback.
- Readback hash bindings match current plan, quality gate, dry-run, PPE proof, and live-create artifacts when those bindings are present.
- Repair plans must target scoped `/slides/...` leaf paths; broad deck rewrites or object/list replacement values fail.

## Focused Tests

Command:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_instruction_adherence_test.py
```

Result:

```text
9 tests passed
```

Covered cases:

```text
1. text matching ignores spacing.
2. broad object/list repair patch is rejected.
3. happy path writes both check and receipt.
4. deck-plan slides[] count drift fails with scoped append/delete recommendation.
5. missing final CanvasSpec page fails.
6. missing slide-plan page fails with scoped append/delete recommendation.
7. final slide_plan key_message drift fails even when readback binding is fresh.
8. forbidden text in SVG output/readback fails.
9. stale readback input_binding plan hash fails.
```

## Reviewer Checklist

- Confirm `00-input/instruction.json` is the durable instruction artifact for Gate 12a.
- Confirm the receipt hashes instruction, deck-plan, slide-plan, final `slide_plan`, SVG pages, and readback artifacts.
- Confirm readback checks page count, order, title/key text, language, must_include, and must_avoid.
- Confirm missing pages/local mismatches are mapped to scoped repair recommendations, not full regeneration.
- Confirm Gate 12a reviewer PASS is recorded and is not treated as Gate 12b final acceptance.
