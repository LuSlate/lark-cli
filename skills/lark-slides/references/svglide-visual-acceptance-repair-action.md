# SVGlide Visual Acceptance Repair Action Plan

Last updated: 2026-06-21

## 0. Current Cursor

```text
Follow-up: Visual Acceptance Repair
Cursor: VF5 Real-Run Benchmark Suite
Status: VF5_FIXTURE_DISTINCTNESS_PASS_REVIEWER_PASS_REAL_ROUTE_POLICY_BLOCKED
Trigger: a real prompt-to-preview run can pass quality_gate and dry_run while the rendered deck is visually unacceptable.
Previous gate: VF4 Theme And Deck Rhythm Lock DONE/PASS
```

This is a new follow-up scope after Gate 12b PASS for the current P0/P1 milestone. It does not rewrite that milestone. It fixes the missing visual acceptance layer exposed by real generation runs.

## 1. Problem Statement

The current chain can produce this invalid state:

```text
quality_gate: passed
dry_run: passed
preview: visually unacceptable
```

Examples of unacceptable output include:

- inconsistent or chaotic palette
- text overlap
- text overflow
- decorative primitives that look arbitrary or sharp without semantic purpose
- fake chart-like marks without a chart contract
- real images not integrated into the CanvasSpec layout
- repeated page composition that makes different topics look nearly identical

`quality_gate` and `dry_run` are engineering gates. They are necessary, but they are not sufficient evidence that the deck is a high-quality generated output.

## 2. Source Of Truth

Primary plan:

```text
/Users/bytedance/Downloads/PLAN.md
```

Supervision guide:

```text
skills/lark-slides/references/svglide-artboard-full-plan-action.md
```

Relevant current failed/weak evidence surfaces:

```text
.tmp/current-cli-quality-runs/spacex-ipo-current-cli-20260621-2125
/Users/bytedance/bd-projects/workspaces/SVGlide/.tmp/theme-comparison-spacex-ipo/outputs/current-cli/current-cli-preview-full.png
```

If a referenced failed-run path is missing on a later machine, the rule still stands: the next real prompt-to-preview run must be judged by rendered visual evidence, not by receipts alone.

## 3. Definitions

```text
engineering_pass:
  quality_gate passed and dry_run passed.

visual_acceptance:
  rendered preview/contact sheet passes the visual rubric and writes
  06-check/visual-acceptance.json plus receipts/visual_acceptance.json.

deliverable_pass:
  engineering_pass and visual_acceptance both pass.
```

No generated deck may be called "high-quality", "upper bound", "final visual result", or "production-quality preview" unless it reaches `deliverable_pass`.

## 4. Hard Rules

- `quality_gate passed` must not be reported as visual quality pass.
- `dry_run passed` must not be reported as visual quality pass.
- A deck with `visual_acceptance=failed` blocks delivery claims even when `quality_gate` and `dry_run` pass.
- Reviewer evidence must include rendered screenshots/contact sheets, not only JSON receipts.
- Visual review must inspect the final rendered preview path that the user sees.
- Random decorative geometry is forbidden unless it has a semantic role, is part of an admitted template, or is marked as a controlled background motif.
- Chart-like visuals are forbidden unless backed by a chart contract or explicitly classified as non-data decoration.
- Structural images must be represented in CanvasSpec asset slots before render; late image paste is not enough.
- Repeated page layouts must be explained by the deck rhythm; accidental sameness across pages or topics is a failure.
- If visual acceptance fails, the default action is scoped repair of affected templates, theme tokens, CanvasSpec, or assets. Do not default to full regeneration.

## 5. Required Artifacts

Every real prompt-to-preview run that is used to demonstrate quality must include:

```text
00-input/instruction.json
02-plan/deck-plan.json
02-plan/slide-plan.json
02-plan/slide_plan.json
03-assets/asset-manifest.json
05-preview/preview.html
05-preview/contact-sheet.png
06-check/quality-gate.json
06-check/visual-acceptance.json
07-create/dry-run.json
receipts/quality_gate.json
receipts/visual_acceptance.json
receipts/dry_run.json
```

The visual acceptance receipt must record:

- input instruction hash
- final slide plan hash
- asset manifest hash
- contact sheet hash
- preview URL or local preview path
- checked page count
- failed pages and issue codes
- repair recommendation scope

## 6. Visual Acceptance Rubric

The first implementation of `svglide_visual_acceptance.py` must be deterministic and conservative. It should fail obvious bad output before any model-based taste review is added.

Required checks:

- page count matches instruction and final plan
- each page has a stable screenshot/contact-sheet crop
- no text bbox exceeds canvas or safe area
- no high-priority text overlaps another high-priority text bbox
- text contrast is above the configured threshold
- title/subtitle/body hierarchy is consistent with the selected template
- palette stays within the selected theme token plus allowed accent budget
- page density is within template limits
- arbitrary triangle/circle/path primitives are either admitted template background motifs or are flagged
- chart-like marks require chart contract evidence
- image slots declared by CanvasSpec resolve to real assets and are visible
- important images do not cover important text
- page compositions across a deck have planned rhythm, not accidental copy/paste sameness

Model-based visual judgment can be added later, but it cannot replace deterministic failures for overflow, overlap, missing assets, stale hashes, or unsupported chart-like marks.

## 7. Phased Execution

### VF0: Documentation Lock And Reviewer Team

Status: DONE/PASS

Actions:

- Add this document.
- Update `svglide-artboard-full-plan-action.md` so the active cursor points to this follow-up.
- Create independent reviewers for visual acceptance and pipeline boundary review.

Acceptance:

- The docs clearly separate `engineering_pass`, `visual_acceptance`, and `deliverable_pass`.
- The docs block future claims that `quality_gate/dry_run` alone prove visual quality.
- Reviewer subagents return PASS or concrete blockers.

Review result:

- Visual Gate Reviewer `Volta`: PASS.
- Pipeline Boundary Reviewer `Kant`: PASS after the docs were revised to keep `quality_gate` and `dry_run` as engineering gates and make `visual_acceptance` a separate delivery/claim gate.
- Next cursor: VF1 Visual Acceptance Gate.

### VF1: Visual Acceptance Gate

Status: DONE/PASS

Actions:

- Add `skills/lark-slides/scripts/svglide_visual_acceptance.py`.
- Add runner stage `visual_acceptance` as a separate delivery/claim gate after `dry_run` in deliverable profiles.
- Keep `quality_gate` and `dry_run` as engineering gates with their current semantics.
- Do not make `visual_acceptance` a precondition for `quality_gate` or `dry_run`.
- Make `deliverable_pass` and any high-quality visual claim require a fresh passed `visual_acceptance` receipt.
- Define or implement the producer for `05-preview/contact-sheet.png`; `preview.html` plus `preview-manifest.json` alone is not enough visual evidence.
- Write `06-check/visual-acceptance.json`.
- Write `receipts/visual_acceptance.json`.
- Add tests for pass/fail cases.

Implemented evidence:

- `svglide_visual_acceptance.py` writes `06-check/visual-acceptance.json` and `receipts/visual_acceptance.json`.
- `svglide_project_runner.py` runs `visual_acceptance` after `dry_run` and before `ppe_proof` / `pre_submit_review` / `live_create` / `readback` for artboard Satori delivery paths.
- `svglide_pre_submit_review.py` requires current `visual_acceptance` reviewed artifact and validates freshness against current plan, quality gate, preview, preview manifest, contact sheet, and visual acceptance receipt.
- `svglide_quality_gate.py` remains independent; visual acceptance is not a quality gate precondition.
- Evidence file: `skills/lark-slides/references/svglide-visual-acceptance-vf1-evidence.md`.

Acceptance:

- A known visually bad fixture fails before delivery claim.
- A known valid fixture passes.
- `quality_gate` and `dry_run` can still pass as engineering gates without visual acceptance.
- `deliverable_pass`, final visual acceptance, or any high-quality/upper-bound claim cannot pass for artboard Satori runs without a fresh passed visual acceptance receipt.
- Any opt-out profile must be labeled `engineering_only` or `non_visual` and must not allow visual delivery claims.

Reviewer status:

- Reviewer `Pascal`: PASS.
- Follow-up increment for skipped engineering-only boundary: PASS.
- Next cursor: VF2 Screenshot And Geometry Evidence.

### VF2: Screenshot And Geometry Evidence

Status: DONE/PASS

Actions:

- Bind visual acceptance to the actual `05-preview/contact-sheet.png` and per-page preview artifacts.
- Add deterministic page crop metadata where needed.
- Record page-level visual issue locations.

Implemented evidence:

- `svglide_visual_acceptance.py` writes `visual_evidence` with contact sheet path/hash, preview path/hash, preview manifest hash, page PNG, preview anchor, and deterministic contact sheet tile metadata.
- page-level issues receive `evidence_path`, `preview_anchor`, and `contact_sheet_tile`.
- `svglide_artboard_renderer.py` records contact sheet grid and per-page tile metadata at source.
- runner and pre-submit reject passed artboard visual acceptance without `visual_evidence.pages`.
- Evidence file: `skills/lark-slides/references/svglide-visual-acceptance-vf2-evidence.md`.

Acceptance:

- Reviewer can open one artifact and see the pages being judged.
- Failure reports identify page number, issue type, and evidence path.

Reviewer status:

- Reviewer `Pascal`: PASS.
- Next cursor: VF3 Renderer And Template Guardrails.

### VF3: Renderer And Template Guardrails

Status: DONE/PASS

Actions:

- Add template-level constraints for decorative primitives, chart-like marks, image slots, and density.
- Reject unregistered geometry patterns in production templates.
- Make structural images part of CanvasSpec and template planning.

Implemented evidence:

- Added `skills/lark-slides/references/svglide-template-guardrails.json`.
- `svglide_visual_acceptance.py` validates decorative primitives, admitted motifs, chart contracts, image slots, CanvasSpec image source refs, and density through the guardrail registry.
- runner and pre-submit bind visual acceptance to current `template_guardrails_sha256`.
- Manifest and rules include the new guardrail registry.
- Evidence file: `skills/lark-slides/references/svglide-visual-acceptance-vf3-evidence.md`.

Acceptance:

- The renderer cannot silently invent arbitrary visual primitives.
- Template fixtures show images and semantic elements integrated by layout, not pasted late.

Reviewer status:

- Reviewer `Pascal`: PASS.
- Next cursor: VF4 Theme And Deck Rhythm Lock.

### VF4: Theme And Deck Rhythm Lock

Status: DONE/PASS

Actions:

- Add deck-level theme consistency checks.
- Add planned layout-rhythm checks across pages.
- Prevent multiple topics from collapsing into the same generic look when distinct templates/assets are available.

Implemented evidence:

- `svglide_visual_acceptance.py` writes `deck_rhythm` with layout, renderer, visual recipe, theme, run-length, and threshold data.
- visual acceptance fails collapsed layout, renderer, visual recipe, long renderer repetition, and fragmented theme token usage.
- runner and pre-submit reject passed artboard VA without `deck_rhythm`.
- Evidence file: `skills/lark-slides/references/svglide-visual-acceptance-vf4-evidence.md`.

Acceptance:

- Two different topics can share a quality standard without becoming visually identical.
- Same topic reruns may vary in content/assets/layout choices while staying within theme and template rules.

Reviewer status:

- Reviewer `Pascal`: PASS.
- Non-blocking: add explicit `allow_multi_theme` branch unit coverage later if the theme policy surface grows.
- Next cursor: VF5 Real-Run Benchmark Suite.

### VF5: Real-Run Benchmark Suite

Status: DONE/PASS_FOR_FIXTURE_BENCHMARK_REAL_ROUTE_POLICY_BLOCKED

Actions:

- Add benchmark prompts:
  - `spacex IPO analysis`
  - `Iceland volcano research`
  - `New Zealand landscape`
- For each prompt, run from instruction capture through planner, assets, preview, quality gate, dry run, and then visual acceptance as the delivery/claim gate.
- Any earlier visual check is advisory only and must not be counted as `deliverable_pass`.
- Preserve receipts, previews, screenshots, and repair logs.

Acceptance:

- Bad outputs fail with actionable issue codes.
- Good outputs pass `deliverable_pass`.
- Comparison screenshots can be used for user review without relabeling failed outputs as upper-bound demos.

Implemented evidence:

- Added `svglide_vf5_benchmark.py` and `svglide_vf5_benchmark_test.py`.
- Added `svglide_fixture_model_provider_test.py` to prevent prompt-specific fixtures from collapsing back to one hardcoded topic.
- Added benchmark-local `--lark-cli-command` so dry-run can use the current branch CLI instead of a stale global `lark-cli`.
- Added trusted real-route guardrails: non-fixture VF5 now requires a `trusted_provider_id`, a trusted planner command, `--asset-provider trusted:<provider-id>`, and `--image-backend stage_command`.
- Added executable `SVGLIDE_IMAGE_STAGE_COMMAND` support so trusted internal image providers can materialize local assets during the assets stage; missing/failed stage command now fails asset acquisition instead of silently producing a real benchmark.
- Expanded the follow-up fixture model provider to a prompt-aware three-page deck with deck/slide/canvas planner outputs, canvas specs, asset contracts, loaded rules, visible template keys, chart contracts, topic-specific style presets, topic-specific palettes, and topic-specific CanvasSpec theme colors.
- Removed SpaceX-specific hardcoding from generic prompt-planner instructions.
- Extended strategy review theme inference for `volcanic_research_lab` and `alpine_coast_travel_board`.
- Strengthened canvas planner prompt constraints so renderer fallback text, object-form `data-story.metrics`, missing loaded rules, and missing chart contracts are rejected upstream.
- Updated semantic role mapping so `data-story` data marks are checked as chart primitives rather than arbitrary decoration.
- Fixture benchmark path: `.tmp/svglide-vf5-benchmark-fixture-v8`.
- Fixture benchmark status: `passed`, 3/3 cases, 3/3 `deliverable_pass`, `live_create` not run.
- Fixture benchmark hash: `70dc9a8a60ffbbd36f4bf8a51949108d107a8f370fb219eb664ff184cae3493a`.
- Fixture receipt hash: `351402b7316786b1248cca267878376989feabe0a20b528b51ecd751bcc76597`.
- Distinctness proof:
  - `spacex IPO 分析`: `raw_grid`, `space_capital_market`, action `continue_pipeline`, contact sheet `1119b9474eb5286ae47689c2ebdc3b6d9f2627fbac6dfff0586972b17746a34a`.
  - `冰岛火山研究`: `editorial_forest`, `volcanic_research_lab`, action `continue_pipeline`, contact sheet `1b0c93451c2b7c8ed19d8e81d4a1e9258ac1cae5951e40fd9b25ca3f42cfd280`.
  - `新西兰风光`: `cobalt_bloom`, `alpine_coast_travel_board`, action `continue_pipeline`, contact sheet `cd6d658b99fcdb780e6191fbf8565c35c86f882fb379b0eb1404979d5f14531e`.
- Evidence file: `skills/lark-slides/references/svglide-visual-acceptance-vf5-evidence.md`.

Real probe status:

- A real `codex` planner + online asset probe was attempted for `spacex-ipo-analysis`.
- Execution was blocked before start by environment escalation policy because it would transmit private repo prompt/schema/template/theme context to external model and image services.
- After this blocker, the benchmark was tightened so external/default planners are not accepted as trusted internal real-route evidence.
- No real benchmark PASS is claimed.

Reviewer status:

- Reviewer `Feynman`: PASS for VF5 fixture benchmark completion.
- Remaining scope: an actual trusted internal planner/image provider instance still has not been configured and run; no real external-model benchmark PASS is claimed.

## 8. Reviewer Protocol

Reviewers must answer:

```text
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

Reviewer PASS for this follow-up requires:

- this document exists and is referenced by the full-plan supervision guide
- the active cursor is not still Gate 12b stop state
- visual quality claims are blocked unless visual acceptance artifacts exist
- the create-svg boundary remains true: final live input is SVGlide protocol SVG, not direct Satori SVG
- the plan does not weaken existing quality_gate, dry_run, live_create, or readback requirements

## 9. Team Roles

Executor:

- Implements the current VF gate only.
- Updates this document when the cursor changes.
- Runs validation commands and records evidence.

Visual Gate Reviewer:

- Challenges whether the visual rubric catches the failures observed in real previews.
- Requires rendered evidence, not only receipts.
- Blocks ambiguous claims such as "looks fine" or "quality gate passed".

Pipeline Boundary Reviewer:

- Ensures Satori remains a renderer/converter inside the artboard lane.
- Ensures final live input remains SVGlide protocol SVG.
- Ensures `+create-svg` boundary and dry-run/live-create semantics are not bypassed.

Template/Theme Reviewer:

- Challenges template sameness, palette chaos, bad typography, and fake chart-like decoration.
- Requires source intake and owned Satori-compatible assets for production templates.

## 10. Current Blocking Principle

After VF1 reviewer PASS, the blocking principle is:

```text
The chain may be called runnable.
The chain may be called engineering-pass if quality_gate and dry_run pass.
The chain may be called deliverable-pass only with fresh passed visual_acceptance evidence.
The chain must not be called high-quality visual generation, upper-bound output, or final production-quality preview without fresh passed visual_acceptance evidence.
The current implementation cursor is VF5 Real-Run Benchmark Suite reviewer validation.
```
