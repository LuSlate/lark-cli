# SVGlide Artifacts Spec

Read this file only after `svglide-svg` route admission. It defines the artifact layout expected by the SVG route checks and delivery records.

## Artifact Directories

Use one run directory per deck or task:

```text
.lark-slides/plan/<deck-id>/
  00-input/
  01-project/
    project_manifest.json
    state.json
  02-plan/
    slide_plan.json
    deck-plan.json
    canvas-plan.json
    svglide.lock.json
    theme-productization.input.json
    theme-registry.json
    theme-migration.patch.json
    themes/
    plan-confirmation.request.json
    plan-confirmation.json
  03-assets/
    assets.json
    asset-manifest.json
  04-svg/
    page-001.svg
    page-001.receipt.json
    page-002.svg
    page-002.receipt.json
    generate_svg.py
    prepared/
      page-001.svg
      page-002.svg
  05-preview/
    preview.html
    preview-manifest.json
  06-check/
    preflight.json
    preview-lint.json
    aesthetic-review.json
    quality-gate.json
  07-create/
    create-command.txt
    dry-run.json
    live-create.json
  08-readback/
    xml-presentations-get.json
    readback-check.json
  09-export/
    export-manifest.json
    svglide-artifacts.zip
  receipts/
  logs/
```

Do not create a separate SVG-only plan root. The SVG route extends the common `.lark-slides/plan/<deck-id>/` layout.

## Required Artifacts

| Artifact | Required | Producer | Consumer |
|---|---:|---|---|
| `01-project/project_manifest.json` | yes | runner init | all later stages |
| `01-project/state.json` | yes | runner | stage control |
| `02-plan/slide_plan.json` | yes | planner/generator | preflight, preview, live create, readback |
| `02-plan/deck-plan.json` | when using `model-plan` | prompt/model planner | planner contract checks, audit |
| `02-plan/canvas-plan.json` | when using `model-plan` | prompt/model planner | planner contract checks, artboard planning |
| `02-plan/svglide.lock.json` | when execution parameters are locked | planner/generator | preflight and runner |
| `02-plan/theme-productization.input.json` | when productizing a project theme | user/model/theme tooling | `theme_productization` optional stage |
| `02-plan/theme-registry.json` | when project theme overrides are used | `theme_productization` | `theme_validate`, artboard renderer |
| `02-plan/theme-migration.patch.json` | when migrating a plan theme | `theme_productization` | audit and review |
| `02-plan/themes/*.json` | when project themes are used | `theme_productization` | `theme_validate`, artboard renderer |
| `02-plan/plan-confirmation.request.json` | only when optional `confirm_plan` is run without confirmation | runner confirm_plan | compatibility/manual approval surface |
| `02-plan/plan-confirmation.json` | optional compatibility artifact | user/chat/confirm surface | optional runner confirm_plan |
| `source/evidence.json` | yes before strategy/generation | source stage or user-provided evidence | strategy review, semantic review, quality gate |
| `source/source-receipt.json` | yes before strategy/generation | source stage | assets, generate_svg, quality audit |
| `03-assets/assets.json` | yes before SVG generation | assets stage | prepare and CLI upload/rewrite |
| `03-assets/asset-manifest.json` | yes before SVG generation | assets stage | generate_svg and audit |
| `04-artboard/raw/page-###.visual.svg` | when using `artboard_satori` | artboard renderer | contract compile input, preview evidence, quality gate raw hash check |
| `04-artboard/raw/page-###.semantic-map.json` | when using `artboard_satori` | artboard renderer | contract compile, semantic/source-ref quality gate |
| `04-artboard/raw/page-###.node-observations.json` | when using `artboard_satori` | Satori renderer | node layout map compiler |
| `04-artboard/raw/page-###.node-layout-map.json` | when using `artboard_satori` | artboard renderer | template-fit and quality gate drift checks |
| `04-artboard/raw/manifest.json` | when using `artboard_satori` | artboard renderer | contract compile input and freshness gate |
| `04-svg/page-###.svg` | yes after `contract_compile` | contract compile or legacy direct SVG | prepare |
| `04-svg/contract/page-###.report.json` | yes after `contract_compile` | contract compile | prepare, preflight, quality gate |
| `04-svg/contract/manifest.json` | yes after `contract_compile` | contract compile | prepare, preflight, quality gate |
| `04-svg/page-###.receipt.json` | direct SVG only | `generate_svg` compatibility path | audit |
| `04-svg/prepared/page-###.svg` | yes before preview/check/create | prepare | preview, preflight, `slides +create-svg --file` |
| `05-preview/preview.html` | yes before preview lint | preview generator | preview lint and aesthetic review |
| `05-preview/preview-manifest.json` | yes before preview lint | preview generator | preview lint and audit |
| `06-check/preflight.json` | yes | `svg_preflight.py` | quality gate |
| `06-check/preview-lint.json` | yes | `svg_preview_lint.py` | quality gate |
| `06-check/aesthetic-review.json` | yes before quality gate | aesthetic_review stage | quality gate |
| `06-check/template-fit.json` | when using `artboard_satori` | template fit check | quality gate |
| `06-check/theme-productization.json` | when using theme productization | `theme_productization` optional stage | audit and review |
| `06-check/chart-verify.json` | yes before quality gate | chart_verify stage | quality gate |
| `06-check/semantic-review.json` | yes before quality gate | semantic_review stage | quality gate |
| `06-check/text-inventory.json` | yes before quality gate | semantic_review stage | quality gate and generator provenance audit |
| `06-check/runtime-review.json` | yes before quality gate | runtime_review stage | quality gate |
| `06-check/semantic-advisory.json` | optional advisory | semantic advisory script | human review |
| `06-check/ppt-master-inventory.json` | optional migration governance | ppt-master inventory script | human review |
| `06-check/quality-gate.json` | yes before create | quality gate | dry-run and live-create wrapper |
| `07-create/create-command.txt` | yes before create | create wrapper | audit |
| `07-create/dry-run.json` | yes before live create | CLI dry-run wrapper | live-create wrapper |
| `07-create/ppe-proof.json` | yes before live create | ppe_proof stage | live-create wrapper |
| `07-create/live-create.json` | yes after live create | CLI output capture | readback and recovery |
| `08-readback/xml-presentations-get.json` | yes after live create | readback checker | readback verifier |
| `08-readback/readback-check.json` | yes after live create | readback checker | delivery decision |
| `09-export/export-manifest.json` | when running export | export stage | handoff package audit |
| `09-export/svglide-artifacts.zip` | when running export with archive | export stage | handoff package |
| `receipts/<stage>.json` | yes per completed or blocked stage | runner or stage script | audit and resume |
| `receipts/assets.json` | yes before generate_svg | runner `assets` | generate_svg and audit |
| `receipts/generate_svg.json` | yes before prepare | runner `generate_svg` | prepare and audit |
| `receipts/repair-loop.json` | when auto repair is run | repair loop | audit and rerun |
| `receipts/theme-productization.json` | when theme productization is run | theme productization | audit |
| `receipts/export.json` | when export is run | export stage | handoff package audit |
| `notes/notes-review.json` | optional speaker handoff | speaker notes script | human handoff |

## Path Rules

- `02-plan/slide_plan.json` must include `plan_path` pointing to itself.
- If present, `02-plan/plan-confirmation.json` must bind the confirmed plan with `plan_sha256`; if `02-plan/svglide.lock.json` exists, it must also bind `lock_sha256`.
- `svg_files` must list `04-svg/prepared/page-###.svg` pages in the same order as `slides +create-svg --file`.
- `03-assets/asset-manifest.json` must bind current plan/lock/assets/source receipt hashes before `generate_svg`.
- Raw visual artifacts must not change after `receipts/generate_svg.json`; canonical SVG files under `04-svg/page-###.svg` must not change after `receipts/contract_compile.json`; rerun `generate_svg` or `contract_compile` before `prepare` according to the stale input.
- SVG image placeholders should use local `@./assets/...` paths or file tokens. HTTP(S) and data image hrefs are not valid `slides +create-svg` inputs.
- Every check record must include the same `plan_path`, relevant input paths, summary counts, and final action. `semantic-review.json` must bind current plan/evidence/prepared SVG hashes; `quality-gate.json` must consume current generator, chart, semantic, runtime, preflight, preview, and aesthetic receipts.
- Project theme registries may bind productized themes to local templates through `template_bindings.supported_template_ids`; `theme_validate` still rejects unknown templates and unbound themes.
- Artboard receipts must bind `semantic-map/v1` with `input_semantic_hash`; measured node layout maps must record observation source and drift status.
- `07-create/ppe-proof.json` must bind current quality gate, dry-run, and proof input hashes before live create.
- Failed or partial live creates must still record `xml_presentation_id`, created slide ids, uploaded image count, and the failing page index when available.
- `09-export/export-manifest.json` is a verified SVGlide artifact package manifest. It does not imply PPTX, animation, or narration support unless those formats are explicitly marked as passed.
- Runtime artifacts under `.lark-slides/plan/<deck-id>/` are per-run outputs. Do not commit them unless a test fixture explicitly requires it.
