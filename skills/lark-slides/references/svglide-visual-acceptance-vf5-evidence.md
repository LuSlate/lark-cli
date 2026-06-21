# SVGlide VF5 Benchmark Suite Evidence

Last updated: 2026-06-21

## Scope

VF5 adds a repeatable prompt-to-visual-acceptance benchmark suite for the artboard Satori lane. The suite starts from a raw prompt, preserves planner receipts, runs through assets, preview, quality gate, local `+create-svg --dry-run`, and then `visual_acceptance`.

It stops before `live_create`.

## Implemented

- Added `skills/lark-slides/scripts/svglide_vf5_benchmark.py`.
- Added `skills/lark-slides/scripts/svglide_vf5_benchmark_test.py`.
- Added `skills/lark-slides/scripts/svglide_fixture_model_provider_test.py`.
- Added explicit `--lark-cli-command` support so benchmark dry-run can use the current branch CLI instead of a stale global `lark-cli`.
- Expanded `followup_model_loop/fixture_model_provider.py` from one poster-like page to a prompt-aware three-page deck fixture.
- Removed SpaceX-specific hardcoding from generic prompt-planner instructions.
- Extended strategy review theme inference for `volcanic_research_lab` and `alpine_coast_travel_board`.
- Strengthened canvas planner prompt constraints:
  - required loaded rule set
  - explicit visible template keys
  - no renderer fallback/default visible text
  - `data-story` string-list metrics/labels/milestones
  - chart pages require `chart_contract`
- Updated artboard semantic roles so `data-story` chart primitives are classified as `data_chart` and require a final canvas-plan `chart_contract`.

## Fixture Benchmark

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/lark-slides/scripts/svglide_vf5_benchmark.py \
  --run-root .tmp/svglide-vf5-benchmark-fixture-v6 \
  --planner-provider command \
  --planner-command "python3 skills/lark-slides/scripts/fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py --stage {stage} --raw-output {raw_output}" \
  --lark-cli-command "env GOCACHE=/private/tmp/svglide-gocache go run ." \
  --target-slide-count 3 \
  --network-policy fixture \
  --image-backend none \
  --fixture-mode \
  --no-search \
  --pretty
```

Result:

```text
status: passed
case_count: 3
passed_count: 3
failed_count: 0
deliverable_pass_count: 3
stopped_before_live_create: true
lark_cli_command: env GOCACHE=/private/tmp/svglide-gocache go run .
real_benchmark: false
```

Artifacts:

```text
.tmp/svglide-vf5-benchmark-fixture-v6/06-check/vf5-benchmark.json
.tmp/svglide-vf5-benchmark-fixture-v6/receipts/vf5-benchmark.json
```

Hashes:

```text
vf5-benchmark.json sha256: ad4abfd3e15e7150892ded8b42fd19ffa9a5afc81555157df197172257b79092
vf5-benchmark receipt sha256: 600bcf55e10cbef1405f9bdc7490f51d783154ac149694e0a0139dc78e1a027d
```

Case project roots:

```text
.tmp/svglide-vf5-benchmark-fixture-v6/projects/vf5-spacex-ipo-analysis
.tmp/svglide-vf5-benchmark-fixture-v6/projects/vf5-iceland-volcano-research
.tmp/svglide-vf5-benchmark-fixture-v6/projects/vf5-new-zealand-landscape
```

Per-case result:

```text
spacex-ipo-analysis:
  raw_prompt: spacex IPO 分析
  deck topic: spacex IPO 分析
  style_preset: raw_grid
  theme_archetype: space_capital_market
  slide_plan sha256: 0cac24bc90f35474a922e72002371164b8f2cb46e9b1c99ee67ad0734bd6b234
  contact_sheet sha256: 1119b9474eb5286ae47689c2ebdc3b6d9f2627fbac6dfff0586972b17746a34a
  visual_distinctness: passed, action continue_pipeline
  quality_gate: passed
  dry_run: passed
  visual_acceptance: passed
  deliverable_pass: true
  live_create: not run

iceland-volcano-research:
  raw_prompt: 冰岛火山研究
  deck topic: 冰岛火山研究
  style_preset: editorial_forest
  theme_archetype: volcanic_research_lab
  slide_plan sha256: c3c2ff6036124ff8f591d35c3d8e19c27f7e55478176288bf9286714ecab7ec8
  contact_sheet sha256: 1b0c93451c2b7c8ed19d8e81d4a1e9258ac1cae5951e40fd9b25ca3f42cfd280
  visual_distinctness: passed, action continue_pipeline
  quality_gate: passed
  dry_run: passed
  visual_acceptance: passed
  deliverable_pass: true
  live_create: not run

new-zealand-landscape:
  raw_prompt: 新西兰风光
  deck topic: 新西兰风光
  style_preset: cobalt_bloom
  theme_archetype: alpine_coast_travel_board
  slide_plan sha256: f2e6e640de3112ddadb0af4eb34660935fd7aad4a902b6dd6cfb109f1f5b93c6
  contact_sheet sha256: cd6d658b99fcdb780e6191fbf8565c35c86f882fb379b0eb1404979d5f14531e
  visual_distinctness: passed, action continue_pipeline
  quality_gate: passed
  dry_run: passed
  visual_acceptance: passed
  deliverable_pass: true
  live_create: not run
```

The first fixture attempt after prompt-specific support still failed reviewer concerns because generic SpaceX prompt text contaminated non-SpaceX selection. The provider now reads `Instruction.raw_prompt` first, and `svglide_fixture_model_provider_test.py` covers that regression. A later benchmark attempt failed visual distinctness because all three topics reused the same palette and renderer/layout sequence. The current v6 evidence passes after assigning topic-specific `style_preset`, `style_system.palette`, `visual_identity.theme_archetype`, and CanvasSpec theme colors. `visual_distinctness.action` is now `continue_pipeline`, not `create_live`, so local visual approval is not mislabeled as live submission permission.

## Local CLI Proof

Command:

```bash
env GOCACHE=/private/tmp/svglide-gocache go run . slides --help
```

Result includes:

```text
Available Commands:
  +create-svg    Create a Lark Slides presentation from SVG
```

This prevents VF5 evidence from accidentally using a stale globally installed `lark-cli` that lacks `slides +create-svg`.

## Real Probe Attempt

Attempted command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/lark-slides/scripts/svglide_vf5_benchmark.py \
  --run-root .tmp/svglide-vf5-benchmark-real-probe \
  --case spacex-ipo-analysis \
  --planner-provider codex \
  --lark-cli-command "env GOCACHE=/private/tmp/svglide-gocache go run ." \
  --target-slide-count 3 \
  --network-policy online \
  --image-backend auto \
  --timeout 900 \
  --pretty
```

Result:

```text
blocked before execution by escalation policy
```

Reason recorded by the execution environment:

```text
This real benchmark would transmit private repository prompt/schema/template/theme context from the workspace to external model and image services that are not clearly trusted internal destinations, which tenant policy forbids even with user approval.
```

No real benchmark PASS is claimed. The fixture benchmark is a deterministic CI-style chain proof, not a real external-model quality upper bound.

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_vf5_benchmark_test.py
```

Result:

```text
Ran 5 tests in 0.639s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_fixture_model_provider_test.py
```

Result:

```text
Ran 2 tests in 0.431s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_strategy_review_test.py
```

Result:

```text
Ran 5 tests in 0.021s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

Result:

```text
Ran 13 tests in 0.707s
OK
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache python3 -m py_compile \
  skills/lark-slides/scripts/svglide_vf5_benchmark.py \
  skills/lark-slides/scripts/svglide_visual_acceptance.py \
  skills/lark-slides/scripts/svglide_artboard_renderer.py \
  skills/lark-slides/scripts/svglide_prompt_planner.py \
  skills/lark-slides/scripts/svglide_strategy_review.py \
  skills/lark-slides/scripts/svglide_visual_distinctness_review.py \
  skills/lark-slides/scripts/fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py
```

Result:

```text
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
Ran 393 tests in 23.797s
OK
```

```bash
env GOCACHE=/private/tmp/svglide-gocache go test .
```

Result:

```text
ok  	github.com/larksuite/cli	0.622s
```

```bash
git diff --check
```

Result:

```text
OK
```

## Reviewer Checklist

Reviewer must verify:

- VF5 benchmark starts from `00-input/instruction.json`.
- Each case preserves planner raw outputs and stage receipts.
- Each case reaches `quality_gate`, `dry_run`, and `visual_acceptance`.
- `live_create` is not run.
- Benchmark dry-run uses the current local branch CLI through `--lark-cli-command`.
- Fixture mode is clearly labeled as not a real benchmark.
- The blocked real probe is not represented as a real PASS.

## Reviewer Verdict

Reviewer: Feynman

Verdict: PASS

Notes:

- PASS applies to VF5 fixture benchmark completion only.
- `real_benchmark=false`; no real external-model benchmark PASS is claimed.
- Real visual asset route remains open: all three fixture cases use fallback assets with `asset_real_coverage=0`.
- Latest v6 re-review confirmed all three `visual_distinctness.action` values are `continue_pipeline`, not `create_live`.
- The stale `Verdict: pending` footer from an earlier draft was removed after reviewer re-check.
- Required next action outside this fixture gate: implement a trusted internal real planner/image route before claiming real-model quality or upper-bound output.
