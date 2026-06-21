# SVGlide Artboard Packaging Decision

Status: Gate 11 implemented, pending reviewer verdict

## Decision

`artboard_renderer` stays as a `lark-slides` skill-local Node subpackage:

```text
skills/lark-slides/scripts/artboard_renderer/
  package.json
  pnpm-lock.yaml
  render.mjs
  dist/render.mjs
  templates/
  themes/
  components/
```

The root CLI remains a Go binary. Satori/resvg are not added as Go modules and are not installed in the root CLI package.

## What Is Embedded

`skills_embed.go` now embeds a whitelist:

```text
skills/*/SKILL.md
skills/*/references
skills/*/routes
skills/*/scenes
skills/*/prompts
skills/*/scripts/*.py
skills/*/scripts/artboard_renderer/*.mjs
skills/*/scripts/artboard_renderer/package.json
skills/*/scripts/artboard_renderer/pnpm-lock.yaml
skills/*/scripts/artboard_renderer/components
skills/*/scripts/artboard_renderer/dist
skills/*/scripts/artboard_renderer/templates
skills/*/scripts/artboard_renderer/themes
```

This makes `lark-cli skills read/list` version-match the binary for prompts, Python scripts, and renderer package resources.

## What Is Not Embedded

The Go binary must not embed:

```text
node_modules/
fixtures/
runtime project artifacts
assets/
.tmp/
```

`@resvg/resvg-js` is native and platform-specific. It must be installed by the package manager or supplied by a platform dependency layer, not committed or broadly embedded.

## Dependency Installation

Required local or CI install command:

```bash
pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile
```

Required runtime checks:

```bash
node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
python3 skills/lark-slides/scripts/svglide_artboard_package_check.py --pretty
```

The subpackage pins:

```text
satori: 0.26.0
@resvg/resvg-js: 2.6.2
```

The lockfile must include macOS arm64 and x64 optional native packages:

```text
@resvg/resvg-js-darwin-arm64
@resvg/resvg-js-darwin-x64
```

## Runtime Contract

Satori is bundled into `dist/render.mjs`. The release path must not require users to clone a sibling Satori source repository.

`@resvg/resvg-js` remains the required native runtime dependency. Missing Node or resvg dependencies must fail before live create.

Operator repair command:

```bash
pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

No-network environments must not auto-fetch packages during generation. They need a prewarmed pnpm store, CI-installed dependencies, or a packaged platform dependency layer.

## CLI Boundary

`slides +create-svg` still consumes final SVGlide SVG files only. It does not run Satori, resvg, Python generation, or planner prompts.

The artboard generation path remains an agent/skill pipeline:

```text
Planner JSON
  -> CanvasSpec
  -> artboard_renderer Satori/resvg preview
  -> SatoriToSVGlide compiler
  -> existing SVGlide prepare/quality_gate/dry_run/live_create/readback
```

## Validation Evidence

Gate 11 evidence is recorded in:

```text
skills/lark-slides/references/svglide-artboard-gate11-evidence.md
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/06-check/artboard-package-check.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/receipts/artboard-package-check.json
```
