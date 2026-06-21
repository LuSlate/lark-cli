# SVGlide Artboard Gate 11 Evidence

Status: implemented, pending reviewer verdict

Gate: Packaging and distribution decision

## Scope

Gate 11 closes the distribution question for the Artboard/Satori lane:

- whether `artboard_renderer` stays as a skill subpackage, is embedded, or is packaged separately
- how `@resvg/resvg-js` native dependency is installed
- whether `skills_embed.go` needs changes
- how to validate macOS arm64/x64 install/runtime readiness
- what happens when Node dependencies are missing

## Decision

`artboard_renderer` remains a `lark-slides` skill-local Node subpackage. It is not moved into the root Go CLI package and does not require users to clone Satori source.

Satori is bundled into `dist/render.mjs`. `@resvg/resvg-js` remains a package-managed native runtime dependency pinned in the subpackage lockfile.

`skills_embed.go` is changed to embed a whitelist of prompts, flat Python scripts, and artboard renderer package resources, while excluding `node_modules`, fixtures, and generated project artifacts.

Full decision document:

```text
skills/lark-slides/references/svglide-artboard-packaging-decision.md
```

## Files Changed For Gate 11

```text
skills_embed.go
cmd/skill/skill.go
skills/lark-slides/scripts/artboard_renderer/package.json
skills/lark-slides/scripts/artboard_renderer/render.mjs
skills/lark-slides/scripts/artboard_renderer/dist/render.mjs
skills/lark-slides/scripts/artboard_renderer/templates/README.md
skills/lark-slides/references/svglide-artboard-satori.contract.md
skills/lark-slides/references/svglide-artboard-packaging-decision.md
skills/lark-slides/scripts/svglide_artboard_package_check.py
skills/lark-slides/scripts/svglide_artboard_package_check_test.py
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/06-check/artboard-package-check.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/receipts/artboard-package-check.json
```

## Package Check Result

Command:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 skills/lark-slides/scripts/svglide_artboard_package_check.py \
  --output-dir skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package \
  --pretty
```

Result:

```text
status: passed
issues: []
host: Darwin arm64
satori: 0.26.0
@resvg/resvg-js: 2.6.2
manual_satori_source_checkout_required: false
node_modules_embedded_in_go_binary: false
runtime_requires_native_resvg_install: true
```

Receipt paths:

```text
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/06-check/artboard-package-check.json
skills/lark-slides/scripts/fixtures/svglide_artboard/gate11_package/receipts/artboard-package-check.json
```

## Runtime Checks

Source entry:

```bash
node skills/lark-slides/scripts/artboard_renderer/render.mjs --check-runtime
```

Result:

```text
ok: true
renderer: satori-resvg
satori_version: 0.26.0
resvg_version: 2.6.2
font_path: /System/Library/Fonts/Supplemental/Arial Unicode.ttf
```

Published dist entry:

```bash
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

Result:

```text
ok: true
renderer: satori-resvg
satori_version: 0.26.0
resvg_version: 2.6.2
font_path: /System/Library/Fonts/Supplemental/Arial Unicode.ttf
```

## Build Check

Command:

```bash
pnpm --dir skills/lark-slides/scripts/artboard_renderer run build
```

Result:

```text
passed
dist/render.mjs rebuilt
```

`dist/render.mjs` no longer requires `satori/package.json`. It uses version constants and dynamically loads `@resvg/resvg-js`, so missing native resvg can be caught with a clear install instruction.

## Go Embed Check

Command:

```bash
go test .
```

Result:

```text
passed
```

The first sandboxed run was blocked by Go build cache writes under `~/Library/Caches/go-build`; the verified run used approved escalated execution for the cache write.

Embedded artboard renderer listing:

```bash
env GOCACHE=/private/tmp/svglide-gocache \
  go run . skills list lark-slides/scripts/artboard_renderer
```

Result includes:

```text
components/
dist/
package.json
pnpm-lock.yaml
render.mjs
templates/
themes/
```

Embedded prompt listing:

```bash
env GOCACHE=/private/tmp/svglide-gocache \
  go run . skills list lark-slides/prompts/svglide
```

Result includes:

```text
canvas-planner.prompt.md
deck-planner.prompt.md
repair-planner.prompt.md
slide-planner.prompt.md
```

## Unit Tests

Command:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest skills/lark-slides/scripts/svglide_artboard_package_check_test.py
```

Result:

```text
4 tests passed
```

Full scripts regression:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/svglide-pycache \
  python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

Result:

```text
274 tests passed
```

Whitespace check:

```bash
git diff --check
```

Result:

```text
passed
```

## Fallback Policy

If Node, Satori source dependencies, or native resvg dependencies are missing, generation must fail before live create.

Repair command:

```bash
pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile
node skills/lark-slides/scripts/artboard_renderer/dist/render.mjs --check-runtime
```

No-network environments must use a prewarmed pnpm store, CI-installed dependencies, or a packaged platform dependency layer. Generation must not auto-fetch packages while producing a deck.

## Reviewer Checklist

- Confirm no manual Satori source checkout is required.
- Confirm native `@resvg/resvg-js` install is documented and pinned.
- Confirm package output reproduces `render.mjs --check-runtime` for source and dist.
- Confirm `skills_embed.go` includes the required skill resources but not `node_modules`.
- Confirm `slides +create-svg` boundary remains final-SVG only.
