# SVGlide Artboard Gate 12 Scope

Status: final acceptance scope for current implementation milestone

## Accepted Milestone

Gate 12 acceptance covers the implemented SVGlide Artboard/Satori milestone through Gate 12a:

```text
P0 technical vertical slice
P0 live/readback special cases
P1 template/theme/component scale-out
P1 planner prompt contracts
P1 packaging/distribution decision
Gate 12a instruction / plan / output / readback adherence
```

This milestone proves:

- `generation_mode=artboard_satori` can run through the existing SVGlide control plane.
- Satori output is preview/layout evidence, not the direct live SVG semantic source.
- Final live input remains SVGlide protocol SVG.
- `ppe_pure_svg` readback covers chart marker and image asset cases.
- Template/theme/component assets meet the current P1 minimum scale.
- Planner prompts produce structured JSON contracts instead of free HTML/CSS/SVG.
- `artboard_renderer` has a releaseable skill-local packaging story.
- Instruction, planner output, generated SVG, and readback evidence are bound by Gate 12a adherence receipts.

## Not Claimed

Not claimed: complete high-quality PPT generation system with actual model-driven topic-to-deck loop.

Not claimed in this milestone:

- actual model invocation from arbitrary user topic to Deck Plan / Slide Plan / CanvasSpec
- automated visual repair loop that calls a model and writes scoped JSON Patch
- full semantic-map-as-compiler-IR implementation for every element type
- true Satori `onNodeDetected` layout observation wired as `node-layout-map/v1`
- production CI coverage on a real macOS x64 host

These are not silently dropped. They are explicit follow-up scope.

## Follow-Up Items

### 1. Real Topic Model Loop

Owner: SVGlide artboard follow-up executor

Target date: 2026-06-28

Scope:

```text
user topic
-> model-generated deck-plan.json
-> model-generated slide-plan.json
-> model-generated canvas-plan.json
-> planner contract validation
-> template/theme binding
-> artboard_satori render
-> quality_gate
-> preview repair loop if needed
```

Acceptance:

- At least one real topic deck runs from model output, not handwritten fixtures.
- All planner outputs pass schema and registry binding.
- Repair prompt is used only as scoped JSON Patch.

### 2. Semantic Map Compiler IR

Owner: SVGlide artboard follow-up executor

Target date: 2026-06-28

Scope:

```text
CanvasSpec.semantic_elements
-> semantic-map/v1 elements with bbox/role/source_ref/style
-> compiler consumes semantic-map/v1 as element-level IR
-> final SVGlide text/image/chart/shape roles are generated from semantic-map
```

Acceptance:

- `semantic-map/v1` is no longer only a summary receipt.
- compiler receipts include `input_semantic_hash`.
- semantic review can compare visible text/source refs against element-level semantic map.

### 3. True Node Layout Observation

Owner: SVGlide artboard follow-up executor

Target date: 2026-06-28

Scope:

```text
Satori renderer layout observation
-> node-layout-map/v1
-> element_id alignment
-> drift check against semantic-map bbox
```

Acceptance:

- `node-layout-map/v1` records measured layout, not only static template geometry.
- quality gate blocks material layout drift before live create.

### 4. Real macOS x64 Runtime Validation

Owner: SVGlide release/CI owner

Target date: 2026-06-28

Scope:

```text
macOS x64 host
-> pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile
-> node dist/render.mjs --check-runtime
-> package check receipt
```

Acceptance:

- x64 host runtime check confirms `@resvg/resvg-js-darwin-x64` loads and renders PNG.
- result is attached to package evidence or CI artifact.
