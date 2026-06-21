# SVGlide Artboard / Satori Contract

P0a adds an `artboard_satori` generation mode inside `generate_svg`.

This mode is intentionally narrow:

- `CanvasSpec` is the semantic source of truth.
- A CanvasSpec-owned template artifact / semantic map is the direct compiler input for SVGlide private SVG.
- Raw Satori SVG is preview/layout evidence only; it is not the semantic source for final live SVG.
- `SVGLIDE_ARTBOARD_USE_NODE_SATORI=1` enables the Node adapter. Published skills must use the bundled adapter at `skills/lark-slides/scripts/artboard_renderer/dist/render.mjs`.
- Published CLI/skill resources must not require a sibling Satori source checkout; Satori is bundled into `dist/render.mjs`.
- The native `@resvg/resvg-js` package is still a runtime dependency and must be installed from the locked skill subpackage before `artboard_satori` runs.
- Live input remains SVGlide protocol SVG.
- The downstream chain stays unchanged: `prepare -> preview -> preflight -> quality_gate -> dry_run`.

## Boundary

Do not pass arbitrary Satori SVG to `slides +create-svg`.

The compiler must receive CanvasSpec-derived template IR, then produce SVGlide protocol SVG with private `slide:*` markers. P0 records this with per-page artboard receipts in `artboard_receipts` and aggregate child receipts in `artboard_additional_receipts`.

Default offline chain:

```text
CanvasSpec
  -> Satori-compatible template renderer
  -> 04-svg/artboard/page-xxx.canvas-template.svg
  -> compile_canvas_template_svg_to_svglide
  -> 04-svg/page-xxx.svg
```

Optional true Satori chain:

```text
CanvasSpec
  -> skills/lark-slides/scripts/artboard_renderer/dist/render.mjs
  -> bundled Satori runtime
  -> 04-svg/artboard/raw/page-xxx.satori.svg
  -> resvg PNG preview
  -> CanvasSpec template artifact remains compiler input
  -> compile_canvas_template_svg_to_svglide
  -> 04-svg/page-xxx.svg
```

Local development may run the unbundled source entry
`skills/lark-slides/scripts/artboard_renderer/render.mjs` after
`pnpm install --frozen-lockfile`. That path is not the release contract.

## P0 Supported Surface

P0 supports three templates:

- `template_id=cover-hero`
- `template_id=comparison-cards`
- `template_id=summary-final`

P0 has two Satori source modes:

- default offline mode: Python emits deterministic Satori-compatible SVG from the controlled template renderer
- real Satori mode: `skills/lark-slides/scripts/artboard_renderer/dist/render.mjs` renders CanvasSpec through bundled Satori runtime. It must not require a sibling Satori source repository, but it does require package-managed `@resvg/resvg-js` native dependencies.

## Adapter Packaging

The CLI repository is a Go binary plus separately installed skills. Satori is a
Node dependency and must not be added as a Go module.

Release shape:

```text
skills/lark-slides/scripts/artboard_renderer/
  package.json      # dependency declaration; satori and @resvg/resvg-js are exact registry versions
  pnpm-lock.yaml    # pinned build input
  render.mjs        # source entry for local development
  dist/render.mjs   # published runtime entry; Satori is bundled, resvg stays native
  templates/
  themes/
  components/
```

Build command:

```bash
cd skills/lark-slides/scripts/artboard_renderer
pnpm install --frozen-lockfile
pnpm run build
node dist/render.mjs --check-runtime
```

Gate 11 packaging validation:

```bash
python3 skills/lark-slides/scripts/svglide_artboard_package_check.py --pretty
```

Runtime rules:

- Published skills call `dist/render.mjs`.
- The adapter may fall back to source `render.mjs` only in local development.
- `satori` must be a fixed npm version in `package.json` and lockfile, not a `file:` dependency.
- `@resvg/resvg-js` must be a fixed npm version in `package.json` and lockfile; macOS arm64/x64 optional native packages must be present in `pnpm-lock.yaml`.
- `node_modules/` must not be committed or embedded into the Go binary. Release packaging must install dependencies for the target host or provide a preinstalled platform dependency layer.
- If Node or resvg dependencies are missing, fail before live create and run `pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile`, then rerun `node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime`.
- If no usable system font exists, set `SVGLIDE_SATORI_FONT_PATH` to a local `.ttf` or `.otf` font.

P0 native output surface:

- `rect slide:role="shape"`
- `circle slide:role="shape"`
- `foreignObject slide:role="shape" slide:shape-type="text"`

P0 Gate 4 certifies text/shape mapping only. Image asset binding and
`svglide-chart-spec-v1` chart markers remain separate Gate 8/P0c proof items and
must not be claimed as complete from Gate 4 evidence.

P0 fail-fast surface for final SVGlide output:

- remote assets
- remote fonts
- WOFF2 fonts
- `filter` / `fe*`
- `mask`
- `clipPath`
- `pattern`
- CSS animation / transition
- `%`, `em`, `rem`, or `calc(...)` geometry
- root-level SVG text in final SVGlide output

## Required Receipts

For `generation_mode=artboard_satori`, `receipts/generate_svg.json` must include:

- existing generator receipt fields: `generated_files`, `page_receipts`, `plan_sha256`, `evidence_sha256`, `asset_manifest_sha256`, `source_receipt_sha256`
- `generation_mode: "artboard_satori"`
- `artboard_receipts`: ordered per-page receipt paths, for example `04-svg/artboard/page-001.receipt.json`
- `artboard_additional_receipts`: aggregate receipt paths, currently `receipts/canvas-spec-validate.json`, `receipts/artboard-render.json`, and `receipts/satori-bridge.json`
- `template_fit_check`: `06-check/template-fit.json`
- `canvas_spec_validate`: `06-check/canvas-spec-validate.json`
- `artboard_render_receipt`: `receipts/artboard-render.json`
- `satori_bridge_receipt`: `receipts/satori-bridge.json`

Each per-page artboard receipt must bind:

- CanvasSpec hash
- raw Satori preview SVG hash
- CanvasSpec template SVG hash
- compiler input path and hash
- renderer mode (`local-static` or `satori-node`)
- compiler mode (`CanvasSpecTemplateSVG` / `preview_only`)
- semantic map hash
- node layout map hash
- final SVGlide SVG hash

`quality_gate` rejects missing, failed, or stale artboard receipts.
