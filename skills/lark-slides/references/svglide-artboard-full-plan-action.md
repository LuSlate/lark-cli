# SVGlide Artboard/Satori Full Plan Action And Supervision Guide

Last updated: 2026-06-21

## 0. Strict Full-Plan Mandate

This file is the local action plan for completing the entire `/Users/bytedance/Downloads/PLAN.md`, not only P0, not only a demo deck, and not only the currently unblocked local vertical slice.

Executor and reviewer agents must treat completion as an evidence-based state:

```text
all gates 0-12b DONE
all reviewer verdicts PASS
PLAN.md completion status updated
real live_create/readback evidence present
legacy direct_svg regression still passing
instruction/plan/output adherence evidence present
packaging/distribution decision closed or explicitly rescoped in PLAN.md
```

Anything less than that is `IN_PROGRESS` or `BLOCKED`.

The current execution cursor is:

```text
Visual Acceptance Repair Follow-Up: VF5 Real-Run Benchmark Suite
Status: VF5_FIXTURE_DISTINCTNESS_PASS_REVIEWER_PASS_REAL_ROUTE_POLICY_BLOCKED
Current issue: Gate 12b/P0-P1 engineering milestone is PASS, but real prompt-to-preview runs can still pass quality_gate/dry_run while producing visually unacceptable decks.
Next allowed executor task: configure and run an actual trusted internal planner/image provider instance before any real-model quality or upper-bound claim.
Next forbidden executor task: claiming high-quality, upper-bound, final visual, or production-quality generated output without fresh visual_acceptance evidence.
```

Supervisor rule:

- The reviewer subagent must reject any attempt to skip the current cursor.
- The reviewer subagent must reject "looks good" visual evidence unless it is tied to receipts, hashes, commands, and runner output.
- The reviewer subagent must reject fake dry-run, handwritten `.tmp` state, system screenshots, or direct Satori SVG as completion evidence.
- The executor must update this file after every gate status change.
- The executor must send this file, the relevant evidence file, changed file list, and validation commands to the reviewer before claiming a gate is done.

## 1. Goal

The goal is to complete the full plan in:

```text
/Users/bytedance/Downloads/PLAN.md
```

This file is the local execution and supervision contract for executor agents and reviewer subagents. It exists to prevent partial vertical slices, visual demos, or smoke tests from being mistaken for completion of the full plan.

Completion means:

```text
Deck/Slide planning contract
-> CanvasSpec as page source of truth
-> Template Registry / Theme Token / Component Library
-> Satori renderer
-> resvg preview and raster fallback path
-> SatoriToSVGlide compiler
-> existing SVGlide prepare / preview / preflight / reviews / quality_gate
-> dry_run
-> visual acceptance evidence for visual quality claims
-> ppe_proof
-> live_create
-> readback
-> instruction / plan / output adherence
-> regression and packaging decision evidence
```

The current state is not full completion. As of 2026-06-21:

```text
Gates 0-8: complete with reviewer PASS
Gate 9: complete with reviewer PASS
Gate 10: complete with reviewer PASS
Gate 11: complete with reviewer PASS
Gate 12a: complete with reviewer PASS
Gate 12b: complete with reviewer PASS
P1: asset system scale-out, prompt/planning, and packaging decision complete with reviewer PASS
P2: not started
Visual Acceptance Repair Follow-Up: VF0 DONE/PASS, VF1 DONE/PASS, VF2 DONE/PASS, VF3 DONE/PASS, VF4 DONE/PASS, VF5 FIXTURE_DISTINCTNESS_PASS/REVIEWER_PASS/REAL_ROUTE_POLICY_BLOCKED
```

Current active cursor:

```text
Gate 8 is now DONE/PASS. It was previously blocked because
`xml_presentations.get` returned 5090000 for presentations containing
`svglide-chart-spec-v1` chart markers.

The slide-side fix has now been committed, pushed, built, and deployed to
`creation.slide.nodeserver_pre_release` in `ppe_pure_svg`:

slide branch: feat/svglide-chart-direct-snapshot
slide commit: 8f682ab082f7d86ade966eb2ffc5849827b17dc5
ENV ticket: 2068537756495360000
TCE deployment: 362509781
TCE service: 208677037
deployed main repo: ee/slide/server@1.0.0.1184
service status: running

Fresh Gate 8 readback now passes:

chart-only deck: C5fxszdjrlftMedvShmcOWtinqe
chart-only slide: pvv
combined deck: J35tspvJgltBnsdJpL7chnv6n2f
combined slides: pdd, pdu, pdR
combined checks: page_count, slide_order, blank_page, text_fit, bounds,
  chart_markers, image_assets, core_visible_text all passed.

Reviewer verdict: PASS.

Next cursor: current P0/P1 milestone closed with Gate 12b reviewer PASS.

The current P0/P1 engineering milestone is closed. The new visual acceptance follow-up is not complete until its own VF gates pass review.
```

New follow-up cursor:

```text
Visual Acceptance Repair Follow-Up is now active.
Source: skills/lark-slides/references/svglide-visual-acceptance-repair-action.md
Current gate: VF5 Real-Run Benchmark Suite
Blocking rule: quality_gate/dry_run alone do not prove visual quality.
Required future artifact for visual quality claims: 06-check/visual-acceptance.json and receipts/visual_acceptance.json.
Latest PASS evidence files:
- skills/lark-slides/references/svglide-visual-acceptance-vf1-evidence.md
- skills/lark-slides/references/svglide-visual-acceptance-vf2-evidence.md
- skills/lark-slides/references/svglide-visual-acceptance-vf3-evidence.md
- skills/lark-slides/references/svglide-visual-acceptance-vf4-evidence.md
Current review evidence file: skills/lark-slides/references/svglide-visual-acceptance-vf5-evidence.md
```

## 2. Source Of Truth

Primary source:

```text
/Users/bytedance/Downloads/PLAN.md
```

Branch and worktree:

```text
worktree: /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private
branch: feat/svglide-artboard-satori
```

Important local references:

```text
skills/lark-slides/references/svglide-artboard-p0-goal-lock.md
skills/lark-slides/references/svglide-visual-acceptance-repair-action.md
skills/lark-slides/references/svglide-artboard-satori.contract.md
skills/lark-slides/references/svglide-canvas-spec.schema.json
skills/lark-slides/references/svglide-semantic-map.schema.json
skills/lark-slides/references/svglide-node-layout-map.schema.json
skills/lark-slides/references/svglide-artboard-receipt.schema.json
skills/lark-slides/references/svglide-template-registry.json
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_artboard_renderer.py
skills/lark-slides/scripts/svglide_template_fit_check.py
skills/lark-slides/scripts/svglide_quality_gate.py
skills/lark-slides/scripts/artboard_renderer/
```

If this guide conflicts with `PLAN.md`, `PLAN.md` wins. If `PLAN.md` is too vague for implementation, update the plan or a referenced contract first, then implement.

## 3. Roles

Executor:

- Implements only the next unblocked task.
- Updates receipts, tests, fixtures, and docs together with code changes.
- Reports exact files changed, exact validations run, and remaining gaps.
- Must not mark a gate complete without reviewer evidence.

Reviewer subagent:

- Audits against this guide and `PLAN.md`.
- Challenges missing evidence, vague claims, or shortcut paths.
- Returns `PASS` only when all blocking checks for the current gate pass.
- Returns `BLOCKED` if any required artifact, receipt, freshness check, or verification is missing.
- Owns final gate verdicts. The executor cannot self-promote a gate to reviewer `PASS`.
- Must inspect repo files and receipts, not only executor prose.

Main agent:

- Maintains the plan and task status.
- Dispatches implementation and review.
- Resolves conflicts between executor and reviewer using repo evidence.
- Keeps this file updated whenever a gate changes state.
- Re-routes work back to the executor when the reviewer returns `BLOCKED`.

## 4. Hard Rules

Do not use these shortcuts as completion evidence:

```text
direct_svg demo replacing artboard_satori evidence
handwritten .tmp generator replacing runner integration
QuickLook / qlmanage / system screenshot replacing resvg main path
manual state.json patch replacing runner behavior
relaxed production gate replacing correct receipts
Satori SVG copied directly to live SVG
unregistered template or theme treated as valid
external HTML/CSS library directly used as runtime renderer
quality_gate checking only file existence without hash/freshness
quality_gate or dry_run treated as visual quality acceptance
fake lark-cli dry_run treated as live_create/readback evidence
executor-written claim treated as reviewer evidence
```

Temporary diagnostics are allowed, but diagnostic outputs cannot be counted as plan completion.

## 4.1 Supervision Loop

For every gate from Gate 4 onward, use this loop:

```text
1. Executor selects exactly one gate or one blocker inside a gate.
2. Executor updates code/docs/fixtures/receipts for that scope only.
3. Executor runs the minimum validation commands listed in this file.
4. Executor writes or updates a gate evidence file.
5. Main agent sends the exact scope, changed files, commands, and evidence paths to the reviewer subagent.
6. Reviewer returns PASS or BLOCKED using the required format.
7. Main agent updates the status board.
8. If BLOCKED, the next executor task must address the reviewer blocker before moving to another gate.
```

The executor must not skip from a blocked gate to a later gate unless this file records an explicit scope deferral approved by the reviewer.

## 5. Required Reporting Format

Every executor update must use this shape:

```text
Scope:
- ...

Files changed:
- ...

Validation run:
- command:
- result:
- evidence path:

Plan items advanced:
- PLAN.md section:
- previous status:
- new status:

Remaining blockers:
- ...
```

Every reviewer subagent response must use this shape:

```text
Verdict: PASS / BLOCKED

Blocking issues:
- ...

Non-blocking risks:
- ...

Evidence checked:
- file / command / receipt:

Next required action:
- ...
```

## 6. Execution Gates

The executor must proceed in order. A later gate cannot be marked complete while an earlier gate is blocked.

### Gate 0: Baseline And Branch Discipline

Purpose: prove the work starts from the right branch and does not break legacy `direct_svg`.

Required actions:

- Confirm current branch is `feat/svglide-artboard-satori`.
- Confirm worktree is `/Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private`.
- Record dirty files before starting each chunk.
- Run legacy direct SVG regression.
- Confirm no `slide_engine` or `slide` changes are required for P0.

Required evidence:

```text
git status --short --branch
legacy direct_svg runner receipt
legacy quality_gate result
```

Reviewer blocking checks:

- Block if branch/worktree is wrong.
- Block if direct SVG is broken without an explicit PLAN-approved migration.
- Block if unrelated repo changes are included.

### Gate 1: Contract Layer Completion

Purpose: close the engineering contract before adding more visual features.

Required actions:

- Finalize `generation_mode=direct_svg|artboard_satori`.
- Keep existing `generator_mode=script|external` semantics unchanged.
- Make `CanvasSpec` the page source of truth for artboard mode.
- Make `semantic-map/v1` an explicit compiler IR.
- Make `node-layout-map/v1` an explicit Satori/Yoga observation artifact or document the accepted substitute.
- Update generator receipt schema to include artboard receipts and hashes.
- Ensure `artboard_satori` requires legal `canvas_spec` per page.

Required artifacts:

```text
skills/lark-slides/references/svglide-plan.schema.json
skills/lark-slides/references/svglide-canvas-spec.schema.json
skills/lark-slides/references/svglide-semantic-map.schema.json
skills/lark-slides/references/svglide-node-layout-map.schema.json
skills/lark-slides/references/svglide-generator-receipt.schema.json
skills/lark-slides/references/svglide-artboard-receipt.schema.json
skills/lark-slides/references/svglide-artboard-satori.contract.md
```

Reviewer blocking checks:

- Block if `CanvasSpec` is optional in `artboard_satori` mode.
- Block if semantic map and node layout map boundaries are unclear.
- Block if receipt schema does not support hash/freshness verification.
- Block if legacy `direct_svg` plans no longer validate.

### Gate 2: Template, Theme, Component, And Input Quality System

Purpose: prevent Satori from rendering arbitrary low-quality input.

Required actions:

- Provide at least 3 P0 templates:
  - `cover-hero`
  - `comparison-cards`
  - `summary-final`
- Provide at least 3 formal theme tokens in the renderer registry or theme registry.
- Provide a Satori-compatible component layer:
  - `Title`
  - `Subtitle`
  - `Chip`
  - `StatCard`
  - `ImageFrame`
- Ensure all templates and components use only the approved Satori CSS subset.
- Implement template fit checks for:
  - unknown `template_id`
  - unknown `theme_id`
  - overlong title
  - missing required content
  - card count overflow
  - unsafe text budget
  - unsafe bbox or safe-area violation
- Add golden fixtures for each P0 template.

Required artifacts:

```text
skills/lark-slides/references/svglide-template-registry.json
skills/lark-slides/scripts/artboard_renderer/templates/
skills/lark-slides/scripts/artboard_renderer/themes/
skills/lark-slides/scripts/artboard_renderer/components/
skills/lark-slides/scripts/svglide_template_fit_check.py
skills/lark-slides/scripts/fixtures/svglide_artboard/
receipts/template-fit-check.json in fixture runs
```

Reviewer blocking checks:

- Block if only one formal theme exists.
- Block if demo-local themes are not registered.
- Block if templates are hardcoded without registry hashes.
- Block if unknown template/theme does not fail fast.
- Block if fixtures are too narrow to prove 3-template behavior.

### Gate 3: Satori Renderer And resvg Preview

Purpose: prove CanvasSpec can render into preview artifacts through the intended renderer.

Required actions:

- Keep `artboard_renderer` as an isolated Node package for P0.
- Declare `satori` and `@resvg/resvg-js` in `package.json`.
- Keep `pnpm-lock.yaml` committed for the subpackage.
- Render each page to raw Satori SVG.
- Render each page to PNG using `@resvg/resvg-js`.
- Generate contact sheet from PNG artifacts.
- Record renderer runtime details.
- Record font hashes.
- Record input and output hashes.

Required artifacts:

```text
skills/lark-slides/scripts/artboard_renderer/package.json
skills/lark-slides/scripts/artboard_renderer/pnpm-lock.yaml
04-svg/artboard/raw/page-###.satori.svg
04-svg/artboard/page-###.png
05-preview/contact-sheet.png
receipts/artboard-render.json
```

Required validation commands:

```bash
node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

Reviewer blocking checks:

- Block if `resvg_version` is missing.
- Block if PNGs are produced by QuickLook/system screenshot as the main path.
- Block if Satori SVG is empty or copied directly to live output.
- Block if font hashes are not recorded.
- Block if renderer artifacts are not hash-bound to CanvasSpec/theme/template inputs.

### Gate 4: SatoriToSVGlide Compiler

Purpose: produce editable SVGlide protocol SVG from CanvasSpec and renderer outputs.

Current reviewer verdict: `PASS`.

Resolved blocking issues:

```text
1. The current compiler path still treats raw Satori SVG as the conversion input.
   The receipt may say `CanvasSpec`, but the implementation must prove the
   generated SVGlide protocol SVG is derived from CanvasSpec / semantic-map /
   owned template IR.

2. P0 Gate 4 scope must be explicit. If image/chart mapping is not implemented
   in Gate 4, the plan must state that P0 Gate 4 only certifies text/shape
   mapping, while image/chart/readback remain Gate 8/P0c work.
```

Required actions:

- Convert using CanvasSpec/semantic map, not by trusting raw Satori SVG as semantic truth.
- Keep raw Satori SVG as preview/layout evidence only.
- Record the actual compiler input artifact and hash, for example:
  - `04-svg/artboard/page-###.semantic-map.json`
  - `semantic_map_sha256`
  - `compiler_input=SemanticMapIR`
  - `satori_svg_usage=preview_only`
- Output current SVGlide protocol:
  - `xmlns:slide="https://slides.bytedance.com/ns"`
  - valid `slide:role`
  - valid text/shape mapping for P0 Gate 4
- Ensure final live SVG does not contain unsupported raw Satori constructs.
- Implement fail-fast or decorative raster fallback for unsupported Satori features.
- Write bridge receipt with input and output hashes.
- If image/chart mapping is deferred, explicitly document the deferral and keep Gate 8 as the owner for chart/image proof.

Required artifacts:

```text
04-svg/page-###.svg
04-svg/artboard/page-###.canvas-template.svg
receipts/satori-bridge.json
```

Reviewer blocking checks:

- Block if final SVG is just raw Satori SVG.
- Block if final SVG is compiled from raw Satori SVG while receipts imply CanvasSpec.
- Block if the compiler input artifact and hash are missing.
- Block if text is not mapped to the current SVGlide text protocol.
- Block if unsupported `filter/mask/clipPath/pattern/foreignObject` paths enter live without explicit fallback policy.
- Block if image/chart mapping is claimed but no fixture/readback evidence exists.
- Block if bridge receipt cannot prove current input/output freshness.

### Gate 5: Runner And Quality Gate Integration

Purpose: make the new path part of the existing stage graph, not a side script.

Required actions:

- `generate_svg` dispatches on `generation_mode`.
- `direct_svg` legacy path remains compatible.
- `artboard_satori` runs CanvasSpec validation, template fit, render, bridge, and generate receipt.
- Per-page render/compile supports bounded concurrency:
  - default `max_workers = min(4, page_count)`
  - final generated file order must remain page-number stable
- `quality_gate` validates all artboard receipts and hashes.
- `quality_gate` fails on stale prepared SVG.
- `quality_gate` fails when required artboard receipts are missing.

Required artifacts:

```text
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_quality_gate.py
receipts/generate_svg.json
06-check/quality-gate.json
```

Required validation:

```bash
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Reviewer blocking checks:

- Block if `artboard_satori` can pass with missing receipts.
- Block if hash/freshness checks only check file existence.
- Block if prepared SVG can be modified after bridge and still pass.
- Block if page order is nondeterministic under concurrency.
- Block if direct SVG regression tests are not run.

### Gate 6: P0a And P0b Local E2E

Purpose: prove 1-page and 3-page local vertical slices are repeatable.

Required actions:

- Add a complete P0a fixture bundle.
- Add a complete P0b fixture bundle.
- P0a runs to `dry_run`.
- P0b runs at least to `quality_gate`, preferably to `dry_run`.
- Fixture bundles include required project files, not just `slide_plan.json`.
- Evidence must prove:
  - artboard mode was used
  - all 3 P0 templates were hit
  - resvg was used
  - quality gate passed
  - dry run passed when required

Required fixture paths:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/
```

Required output evidence:

```text
02-plan/slide_plan.json
04-svg/artboard/raw/page-###.satori.svg
04-svg/artboard/page-###.png
04-svg/page-###.svg
05-preview/contact-sheet.png
06-check/quality-gate.json
07-create/dry-run.json
receipts/canvas-spec-validate.json
receipts/template-fit-check.json
receipts/artboard-render.json
receipts/satori-bridge.json
receipts/generate_svg.json
```

Reviewer blocking checks:

- Block if demo is generated outside the fixture path and cannot be repeated.
- Block if P0b does not hit all required P0 templates.
- Block if P0b uses only one formal theme while plan requires three.
- Block if fixture bypasses runner stages.

### Gate 7: P0c Live Closure

Purpose: prove the new path can create and read back real Slides.

Required actions:

- Prepare a P0c fixture with `07-create/ppe-proof.input.json`.
- Run `dry_run`.
- Run `ppe_proof`.
- Run `live_create`.
- Run `readback`.
- Verify created slide count, page order, core visible text, and no blank pages.
- Verify the online result does not have obvious overflow or missing images.

Required artifacts:

```text
07-create/dry-run.json
07-create/ppe-proof.json
07-create/live-create.json
08-readback/readback-check.json
```

Reviewer blocking checks:

- Block if fake lark-cli is used as live evidence.
- Block if `ppe_proof` inputs do not match current quality gate and dry-run outputs.
- Block if readback is not performed.
- Block if created pages are blank, missing expected text, or out of order.

### Gate 8: Special Cases And Fallback Coverage

Purpose: cover features likely to break the renderer/compiler boundary.

Required actions:

- Add unsupported Satori feature fixture.
- Add chart marker fixture for `svglide-chart-spec-v1`.
- Add image asset fixture with binding and readback.
- Add local raster fallback fixture for an isolated unsupported decoration.
- Prove fail-fast behavior before live for unsupported editable features.

Reviewer blocking checks:

- Block if unsupported features silently pass.
- Block if raster fallback lacks bbox/island receipt.
- Block if chart marker or image asset is not verified through readback.

### Gate 9: P1 Asset System Scale-Out

Purpose: move from P0 templates to a reusable visual system.

Required actions:

- Convert external visual references into owned Satori-compatible templates.
- Use external repos only as inspiration/input data, not runtime dependency.
- Build a source intake inventory before converting assets. Each source family must record:
  - `source_path`
  - `source_type`
  - `extract_fields`
  - `conversion_target`
  - `acceptance_rule`
  - `forbidden_usage`
- Target P1 asset counts from `PLAN.md`:
  - 15-25 Canvas Templates
  - 10-18 Theme Tokens
  - 20-40 Component Variants
  - 6-10 Layout Archetypes
- Add abstraction guide evidence for each source family.
- Add template quality fixtures and regression previews.

Allowed reference sources and intake rules:

```text
1. /Users/bytedance/bd-projects/open-design/design-templates/*
   Read: template.json, example.html, preview screenshots when available.
   Extract: palette, typography, mood, density, occasion, layout skeleton, component combinations.
   Convert to: Theme Token, Canvas Template brief, Satori component candidates.
   Forbidden: do not run arbitrary HTML/CSS as the SVGlide runtime renderer.

2. /Users/bytedance/bd-projects/open-design/design-templates/html-ppt-zhangzara-*
   Read: template.json, example.html, style sample images.
   Extract: high-aesthetic style DNA, color hierarchy, display/body type pairing, spacing, poster/editorial/grid traits.
   Convert to: deduped strong-style Theme Tokens and a small number of strong-style Canvas Templates.
   Forbidden: do not copy all style packs blindly; dedupe and keep only reusable Satori-compatible patterns.

3. /Users/bytedance/bd-projects/ppt-master/examples/examples.json
   plus /Users/bytedance/bd-projects/ppt-master/examples/*/{design_spec.md,spec_lock.md,svg_final/*.svg}
   Extract: deck rhythm, page archetypes, visual style rules, palette rules, element density, bbox/font-size facts, golden page examples.
   Convert to: golden fixtures, style/quality rules, deck rhythm patterns, Canvas Template candidates.
   Forbidden: do not use ppt-master SVG as final SVGlide output and do not add ppt-master as a CLI runtime dependency.

4. /Users/bytedance/bd-projects/workspaces/SVGlide/PosterGen
   Read: config/poster_config.yaml, config/prompts/*.txt, src/agents/*, resource/*, data/*.
   Extract: research-poster layout heuristics, section balancing, color extraction, text-height/min-font rules, logo/affiliation/image placement patterns.
   Convert to: special research-poster templates, quality rules, layout heuristics, asset-binding cases.
   Forbidden: do not integrate PosterGen's LangGraph/Python generation workflow as the SVGlide runtime.

5. html-ppt-skill
   Status: allowed only after the real local path is documented.
   Extract: full-deck rhythm, single-page layouts, theme tokens.
   Convert to: deck rhythm patterns, Canvas Templates, Theme Tokens.
   Forbidden: do not count this source as verified until the source path and inventory evidence exist.

6. Other poster / OG / example sources
   Status: allowed only when documented in PLAN.md with source path, license/provenance, intake fields, and forbidden usage.
```

Reviewer blocking checks:

- Block if an external HTML/CSS/SVG library is directly used as runtime renderer.
- Block if a source family has no intake inventory entry.
- Block if a source path is unverified but counted toward P1 asset targets.
- Block if conversion evidence does not show source example -> abstraction record -> CanvasSpec fixture -> registry/theme/component output.
- Block if templates do not map to CanvasSpec schema.
- Block if visual assets do not have golden fixtures.
- Block if generated pages degrade to title-plus-bullets.

### Gate 10: Prompt And Planning Layer

Purpose: turn a user topic into structured data without letting LLM write arbitrary HTML/CSS/SVG.

Required actions:

- Add prompt contracts for:
  - Deck Planner
  - Slide Planner
  - Canvas Planner
  - Repair Planner
- Each prompt must declare:
  - input bundle
  - output schema
  - output path
  - validation command
  - forbidden outputs
- LLM output must be structured JSON, not free HTML/CSS/SVG.
- Planner outputs must pass schema and template fit before Satori.

Reviewer blocking checks:

- Block if prompts produce unrestricted HTML/CSS/SVG.
- Block if planner output bypasses CanvasSpec validation.
- Block if repair prompt rewrites the whole deck instead of scoped JSON Patch where PLAN requires patch behavior.

### Gate 11: Packaging And Distribution Decision

Purpose: settle how Satori/resvg enters CLI distribution.

Required actions:

- Decide whether `artboard_renderer` stays as a skill subpackage, is embedded, or is packaged separately.
- Decide how native `@resvg/resvg-js` dependency is installed for CLI users.
- Decide whether `skills_embed.go` changes are required.
- Add CI or local install validation for macOS arm64/x64.
- Document fallback when Node dependencies are missing.

Reviewer blocking checks:

- Block if the CLI release story requires users to manually clone Satori source.
- Block if native dependency install is undocumented.
- Block if package output cannot reproduce `render.mjs --check-runtime`.

### Gate 12a: Instruction / Plan / Output Adherence

Purpose: ensure explicit user instructions, planner outputs, generated CanvasSpec, and final readback remain consistent before final acceptance.

Required actions:

- Add or verify a durable user instruction source, preferably `00-input/instruction.json`, with at least topic, target slide count, language, audience, must-include, must-avoid, and output requirements.
- Add or verify an adherence checker such as `svglide_instruction_adherence.py`.
- Check that `target_slide_count` is consistent across instruction, `deck-plan.json`, `slide-plan.json`, final `slide_plan.json`, and readback.
- Check that slide count, page order, title/key-message propagation, chosen template/theme, language, required sections, and forbidden items match the instruction and planner chain.
- On failure, require scoped repair output rather than full regeneration by default:
  - append missing deck/slide/canvas entries when pages are missing
  - patch only affected slide fields or CanvasSpec leaves when localized
  - rerun from the smallest affected stage
  - allow full replan only when the deck narrative itself is invalid
- Write `06-check/instruction-adherence.json` and `receipts/instruction-adherence.json`.
- Include tests for count mismatch, missing slide-plan/canvas pages, forbidden content, and a passing fixture.

Reviewer blocking checks:

- Block if user instructions are not recorded in a durable project artifact.
- Block if `target_slide_count` can drift from actual planner/readback page count.
- Block if missing pages trigger full regeneration instead of scoped append/patch when localized repair is possible.
- Block if `quality_gate` or final acceptance can pass without instruction adherence evidence.
- Block if final readback does not check page count, order, title/key text, and explicit must-include/must-avoid constraints where applicable.

### Gate 12b: Final Full-Plan Acceptance

Purpose: certify that the whole plan, not only P0, is complete.

Required evidence:

```text
P0a/P0b/P0c passed with receipts
legacy direct_svg regression passed
chart marker readback passed
image asset readback passed
unsupported feature fail-fast passed
template/theme/component scale targets met or PLAN.md explicitly revised
prompt contracts implemented and validated
packaging/distribution decision implemented or explicitly scoped with owner/date
instruction/plan/output adherence receipt passed
all unit/integration/regression tests passed
PLAN.md completion table updated
reviewer subagent final PASS recorded
```

Reviewer final blocking checks:

- Block if any `PLAN.md` P0 success standard is incomplete.
- Block if P1/P2 scope was silently dropped without updating `PLAN.md`.
- Block if live/readback evidence is missing.
- Block if instruction/plan/output adherence evidence is missing or stale.
- Block if final claim depends on fake local dry-run only.

## 7. Status Board

Update this board after each meaningful implementation chunk.

| Gate | Status | Owner | Reviewer verdict | Evidence |
|---:|---|---|---|---|
| 0 Baseline and branch discipline | DONE | executor | PASS | Branch/worktree verified; legacy `direct_svg` baseline ran to `quality_gate` at `/private/tmp/svglide-direct-gate0-9Wl2gp` with `generation_mode=direct_svg` and no `artboard_receipts`; evidence recorded in `svglide-artboard-gate0-gate1-evidence.md` |
| 1 Contract layer completion | DONE | executor | PASS | Plan schema now rejects `artboard_satori` slides without `canvas_spec`; semantic map now emits `elements[]`; PLAN/contract receipt wording aligned to per-page `artboard_receipts` + aggregate `artboard_additional_receipts`; reviewer PASS recorded in `svglide-artboard-gate0-gate1-evidence.md` |
| 2 Template/theme/component/input quality | DONE | executor | PASS | 3 templates + 3 registered themes + component module + `templates/p0-templates.mjs` exist; registry text budgets, golden CanvasSpec fixtures, and safe-area/semantic bbox admission checks added; P0b `/private/tmp/svglide-p0b-gate2-safe-YVT67C` passed template-fit/quality-gate/dry-run; evidence recorded in `svglide-artboard-gate2-evidence.md` |
| 3 Satori renderer and resvg preview | DONE | executor | PASS | `node render.mjs --check-runtime` and `node dist/render.mjs --check-runtime` passed with Satori 0.26.0 / resvg 2.6.2; P0b raw SVG/PNG/contact sheet and receipts verified; evidence recorded in `svglide-artboard-gate3-evidence.md` |
| 4 SatoriToSVGlide compiler | DONE | executor | PASS | Main artboard path writes template SVG as preview/layout evidence and now compiles final SVGlide SVG from `semantic-map/v1` as `SemanticMapIR`; raw Satori SVG is `preview_only`; quality gate rejects RawSatori compiler metadata; original P0b evidence remains recorded in `svglide-artboard-gate4-evidence.md` |
| 5 Runner and quality gate integration | DONE | executor | PASS | Page jobs now run with bounded `max_workers=min(4,page_count)` and stable sorted receipts; full test suite passed 254 tests; direct_svg `/private/tmp/svglide-direct-gate5-iYPBBA` passed quality_gate; artboard P0b `/private/tmp/svglide-p0b-gate5-qg7PC6` passed dry_run; evidence recorded in `svglide-artboard-gate5-evidence.md` |
| 6 P0a/P0b local E2E | DONE | executor | PASS | P0a `/private/tmp/svglide-p0a-gate6-zNSbw5` ran to dry_run; P0b `/private/tmp/svglide-p0b-gate5-qg7PC6` ran to dry_run; P0b hits `cover-hero/dark-clarity`, `comparison-cards/forest-signal`, `summary-final/warm-editorial`; evidence recorded in `svglide-artboard-gate6-evidence.md` |
| 7 P0c live closure | DONE | executor | PASS | Reviewer PASS: strengthened PPE proof validates Whistle capture/proxy/rule hash/injected headers; fresh P0c `.tmp/svglide-p0c-gate7-live6` ran `dry_run -> ppe_proof -> live_create -> readback`; live deck `MPcnsjAH5l5r2edcpWYcNhFVnVd` created 3 slides `["pbb","pbu","pbe"]`; readback passed page count, slide order, nonblank, text-fit/bounds marker scan, and 22 CanvasSpec visible text fragments; evidence recorded in `svglide-artboard-gate7-evidence.md` |
| 8 Special cases and fallback coverage | DONE | executor | PASS | Reviewer PASS: local Gate 8 evidence `.tmp/svglide-gate8-special-cases-r4/gate8-special-cases.json` passed all 4 cases; image-only and raster-only live/readback pass; previous chart-only and combined readback failures were traced to `creation.slide.nodeserver_pre_release::GetSXSDXml` on stale lane package `ee/slide/server@1.0.0.1149`; slide-side fix is committed and pushed at `8f682ab082f7d86ade966eb2ffc5849827b17dc5`; focused Jest passes 6/6 and strict single-file TypeScript passes; deploy-lane ticket `2068537756495360000` succeeded, TCE deployment `362509781` finished, service `208677037` is running `ee/slide/server@1.0.0.1184`; fresh chart-only readback `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json` passed for deck `C5fxszdjrlftMedvShmcOWtinqe` / slide `pvv`; fresh combined readback `.tmp/svglide-gate8-live/08-readback/readback-check.json` passed for deck `J35tspvJgltBnsdJpL7chnv6n2f` / slides `pdd,pdu,pdR` with chart marker and 2 image assets verified; evidence recorded in `svglide-artboard-gate8-evidence.md`; current P0/P1 milestone is closed by Gate 12b reviewer PASS |
| 9 P1 asset system scale-out | DONE | executor | PASS | Source intake inventory, 15 active templates, 10 themes, 23 component variants, 10 layout archetypes, 15 golden CanvasSpec fixtures, Node/Satori renderer support, Python fallback, and tests are implemented; source intake has required fields plus per-source conversion traceability; `ppt-master` provenance records MIT and is test-guarded; `node --check`, Python compile, JSON parse, renderer source/dist runtime checks, `pnpm --dir ... run build`, focused artboard tests 15/15, scripts regression 265/265, and `git diff --check` all pass; reviewer PASS recorded in `svglide-artboard-gate9-evidence.md` |
| 10 Prompt and planning layer | DONE | executor | PASS | Prompt contracts for Deck/Slide/Canvas/Repair planners, four output schemas, `svglide_planner_contracts.py`, Gate 10 fixture, and tests are implemented; planner contract check validates JSON-only outputs, schema conformance, Slide Planner registry binding, CanvasSpec + registry binding before Satori, and scoped leaf-level repair JSON Patch; focused planner tests 5/5, scripts regression 270/270, renderer source/dist runtime checks, artboard continuation proof, and `git diff --check` pass; reviewer PASS recorded in `svglide-artboard-gate10-evidence.md` |
| 11 Packaging and distribution decision | DONE | executor | PASS | Reviewer PASS: `artboard_renderer` stays as a skill-local Node subpackage; Satori is bundled into `dist/render.mjs`; `@resvg/resvg-js` remains a pinned native runtime dependency; `skills_embed.go` embeds prompts, flat Python scripts, and renderer package resources with a whitelist excluding `node_modules`; package check `status=passed`, source/dist runtime checks pass, package-check tests 4/4 pass, `go test .` passes, embedded skills listing includes renderer and planner prompt resources; reviewer noted macOS x64 is structurally validated through lockfile optional native package coverage, not executed on x64 host; evidence recorded in `svglide-artboard-gate11-evidence.md` |
| 12a Instruction / plan / output adherence | DONE | executor | PASS | Reviewer PASS: durable `.tmp/svglide-p0c-gate7-live6/00-input/instruction.json` and `svglide_instruction_adherence.py` validate instruction -> deck-plan -> slide-plan -> final `slide_plan` -> SVG output -> readback for target slide count, actual `slides[]` count, page order, exact title/key_message, template/theme, language, must_include/must_avoid, explicit constraint surfaces, and readback hash bindings; scoped leaf repair aligned final `slide_plan` key_message fields, then readback was refreshed with current branch CLI and matched the new plan hash; instruction adherence receipt `status=passed`; focused tests 9/9 pass; evidence recorded in `svglide-artboard-gate12a-evidence.md` |
| 12b Final full-plan acceptance | DONE | executor | PASS | Reviewer PASS: final acceptance checker requires Gate 0-12a DONE/PASS, Gate 12a instruction-adherence check/receipt status passed, current instruction/deck-plan/slide-plan/final-plan/output/readback hashes matched, readback binding checks matched, package receipt passed, PLAN scope caveat present, and Gate 12 scope deferrals with owner/date; final acceptance receipt `status=passed`; package check passed; focused final tests 3/3, scripts regression 286/286, `go test .`, and `git diff --check` pass; evidence recorded in `svglide-artboard-gate12-evidence.md` |

Status values:

```text
TODO
IN_PROGRESS
PARTIAL
BLOCKED
DONE
```

Only a reviewer subagent can move `Reviewer verdict` to `PASS`.

## 7.1 Current Next Task

Gate 12b has reviewer PASS for the P0/P1 engineering milestone. The active follow-up is now Visual Acceptance Repair.

```text
Completed follow-up gates:
- VF0 Documentation Lock And Reviewer Team: DONE/PASS.
- VF1 Visual Acceptance Gate: DONE/PASS.
- VF2 Screenshot And Geometry Evidence: DONE/PASS.
- VF3 Renderer And Template Guardrails: DONE/PASS.
- VF4 Theme And Deck Rhythm Lock: DONE/PASS.

Current follow-up cursor:
- VF5 Real-Run Benchmark Suite.
- Code implemented.
- Fixture benchmark v8 passed 3/3 cases through quality_gate, dry_run, and visual_acceptance.
- Fixture benchmark v8 also passed cross-topic visual distinctness: SpaceX uses `raw_grid`/`space_capital_market`, Iceland uses `editorial_forest`/`volcanic_research_lab`, and New Zealand uses `cobalt_bloom`/`alpine_coast_travel_board`; all distinctness pass actions are `continue_pipeline`, not `create_live`.
- Fixture benchmark artifacts:
  - `.tmp/svglide-vf5-benchmark-fixture-v8/06-check/vf5-benchmark.json`
  - `.tmp/svglide-vf5-benchmark-fixture-v8/receipts/vf5-benchmark.json`
  - benchmark hash `70dc9a8a60ffbbd36f4bf8a51949108d107a8f370fb219eb664ff184cae3493a`
  - receipt hash `351402b7316786b1248cca267878376989feabe0a20b528b51ecd751bcc76597`
- Real codex planner + online asset probe was attempted but blocked before execution by environment policy because it would transmit private repo prompt/schema/template/theme context to external model/image services.
- Non-fixture VF5 mode now requires an explicit trusted provider id, trusted planner command, trusted asset provider id, and `SVGLIDE_IMAGE_STAGE_COMMAND` with `--image-backend stage_command`; external/default planners are not accepted as trusted real-route evidence.
- Reviewer verdict: Feynman PASS for fixture benchmark completion.
- Remaining required action: configure and run an actual trusted internal planner/image provider instance before claiming real-model quality or upper-bound output.

Next required action:
- Reviewer audit for `skills/lark-slides/references/svglide-visual-acceptance-vf5-evidence.md`.
- Do not claim real external-model benchmark PASS.
- Do not claim high-quality visual output unless visual_acceptance evidence exists and passes.
- Do not claim P2/future scope as complete.
```

Gate 8 closure evidence:

```text
1. Service fix deployed:
   ENV ticket `2068537756495360000`, TCE deployment `362509781`,
   service `208677037`, `ee/slide/server@1.0.0.1184`.
2. Chart-only readback passed:
   `.tmp/svglide-gate8-live-chart/08-readback/readback-check.json`.
3. Combined chart + image + raster readback passed:
   `.tmp/svglide-gate8-live/08-readback/readback-check.json`.
4. Gate 8 evidence file updated:
   `skills/lark-slides/references/svglide-artboard-gate8-evidence.md`.
```

## 8. Subagent Review Prompt

Use this prompt when creating a reviewer subagent:

```text
You are the independent reviewer for SVGlide Artboard/Satori full-plan execution.

Primary source of truth:
/Users/bytedance/Downloads/PLAN.md

Supervision guide:
skills/lark-slides/references/svglide-artboard-full-plan-action.md

Your job is to challenge the executor and prevent partial completion from being called done.

You must inspect actual repo files, changed files, runner outputs, receipts,
schemas, fixtures, and test results. Do not accept executor prose as evidence.
Do not accept demos, screenshots, fake dry-runs, stale receipts, missing hashes,
or direct Satori SVG as completion evidence.

Current execution cursor:
Visual Acceptance Repair Follow-Up, VF5 Real-Run Benchmark Suite.
Gate 12b Final Full-Plan Acceptance remains DONE/PASS for the current P0/P1 engineering milestone.
P2/future scope remains explicitly not claimed. High-quality visual output is not claimable until visual_acceptance evidence passes. Real external-model benchmark PASS is not claimable when the real probe is policy-blocked.

For every review, answer these checks:

1. Is the executor working on the current allowed gate or blocker?
2. Are the claimed changed files in the correct repo/worktree?
3. Are receipts fresh and hash-bound to current inputs?
4. Did the executor run the required validation commands for this gate?
5. Does evidence include real runner/live/readback output where required?
6. Did legacy direct_svg remain compatible where the gate can affect it?
7. Did the executor update this supervision guide and gate evidence file?
8. Is any PLAN.md requirement silently dropped, weakened, or moved later?

Return:

Verdict: PASS / BLOCKED

Blocking issues:
- ...

Non-blocking risks:
- ...

Evidence checked:
- ...

Next required action:
- ...
```

## 9. Minimum Validation Command Set

Run these when relevant to the current gate:

```bash
git status --short --branch
```

```bash
node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime
```

```bash
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

```bash
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

For fixture E2E, use the runner with an explicit fixture path and stage target. Do not count ad hoc `.tmp` projects as the only evidence for a gate.

## 10. Completion Rule

The full plan is not complete until all of the following are true:

```text
all gates 0-12 are DONE
all reviewer verdicts are PASS
PLAN.md completion table is updated
real live_create/readback evidence exists for P0c
visual_acceptance evidence exists and passes for any claim of high-quality generated visual output
legacy direct_svg remains compatible
artboard_satori path has reproducible fixtures and tests
packaging/distribution path is explicit enough for CLI users
current Visual Acceptance Repair follow-up VF gates are DONE/PASS, unless this follow-up is explicitly scoped out in PLAN.md with owner/date
```

If any of these are false, the correct status is still `IN_PROGRESS` or `BLOCKED`, not complete.
