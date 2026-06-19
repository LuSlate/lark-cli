# SVGlide Checks Checklist

Read this file only after `svglide-svg` route admission. Treat the checks as one blocking chain; do not skip ahead after an earlier error.

## Checks Chain

```text
route admission
-> loaded_rule_set recorded
-> source evidence recorded
-> strategy review passed
-> plan confirmation recorded
-> assets manifest recorded
-> generate_svg source pages recorded
-> prepare SVG input set
-> svg_preflight.py --plan
-> svg_preview_lint.py
-> svglide_aesthetic_review.py
-> svglide_chart_verify.py
-> svglide_semantic_review.py
-> svglide_runtime_review.py
-> svglide_quality_gate.py
-> slides +create-svg dry-run
-> svglide_ppe_proof.py
-> live create
-> xml_presentations get readback
```

## Checklist

- [ ] Confirm `svglide-svg` route admission.
- [ ] Record `loaded_rule_set` from `svglide-svg-private.rules.json` in `02-plan/slide_plan.json`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> source` and confirm `source/source-receipt.json` has `status: "passed"`.
- [ ] Verify `02-plan/slide_plan.json` has route, canvas, safe area, style system, art direction, source policy, business claims, assets, and ordered `svg_files`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> strategy_review` and confirm `02-plan/strategy-review.json` has `status: "passed"`.
- [ ] Confirm `02-plan/plan-confirmation.json` has `status: "confirmed"`, `confirmed_by: "user"`, and current `plan_sha256` / optional `lock_sha256`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> assets` and confirm `03-assets/asset-manifest.json` has `status: "passed"`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> generate_svg` to generate or register source SVG pages under `.lark-slides/plan/<deck-id>/04-svg/`.
- [ ] Confirm `receipts/generate_svg.json` has `status: "passed"` and lists the generated source SVG hashes.
- [ ] Run `svglide_prepare.py` and verify prepared SVG pages under `.lark-slides/plan/<deck-id>/04-svg/prepared/`.
- [ ] Run source preflight:

```bash
python3 skills/lark-slides/scripts/svg_preflight.py \
  --plan .lark-slides/plan/<deck-id>/02-plan/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/04-svg/prepared/page-001.svg
```

- [ ] Save preflight output as `06-check/preflight.json` and confirm `summary.error_count == 0`.
- [ ] Build `05-preview/preview.html`.
- [ ] Run preview lint:

```bash
python3 skills/lark-slides/scripts/svg_preview_lint.py \
  .lark-slides/plan/<deck-id>/05-preview/preview.html --pretty
```

- [ ] Save preview lint output as `06-check/preview-lint.json`.
- [ ] Confirm preview lint `summary.error_count == 0` and `action == "create_live"`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> aesthetic_review` and confirm `06-check/aesthetic-review.json` action is `create_live`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> chart_verify` and confirm `06-check/chart-verify.json` status is `passed`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> semantic_review` and confirm `06-check/semantic-review.json` status is `passed`.
- [ ] Confirm `06-check/text-inventory.json` has no unmatched visible SVG text.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> runtime_review` and confirm `06-check/runtime-review.json` status is `passed`.
- [ ] Run `svglide_quality_gate.py` and confirm `06-check/quality-gate.json` status is `passed`.
- [ ] Run `slides +create-svg --dry-run` with the same ordered `--file` list; use repo-relative file paths, and set `SVGLIDE_LARK_CLI_CMD` when the current worktree implementation is not installed as the global `lark-cli`.
- [ ] Run `svglide_project_runner.py stage .lark-slides/plan/<deck-id> ppe_proof` and confirm `07-create/ppe-proof.json` status is `passed`.
- [ ] Run live `slides +create-svg` only after all blocking local gates, dry-run, and PPE proof pass.
- [ ] Read back with `slides xml_presentations get` and record `08-readback/readback-check.json` for page count, blank-page, bounds, text-fit, asset-token, and closing-slide checks.

## Blocking Conditions

Live create is blocked by:

- route not admitted
- missing `loaded_rule_set`
- missing, failed, stale, or thin source receipt/evidence
- missing or stale plan confirmation
- missing or failed assets manifest
- missing or stale `generate_svg` receipt
- preflight errors
- preview lint errors
- aesthetic review status other than `passed` or action other than `create_live`
- required chart verification missing, failed, or stale
- missing, failed, or stale semantic review
- missing, failed, or stale runtime review
- unmatched SVG visible text in `06-check/text-inventory.json`
- quality gate status other than `passed`
- missing, failed, or stale PPE proof before live create
- SVG page order mismatch between plan and command
- external HTTP(S) or data image hrefs in the `slides +create-svg` input
- missing readback plan for a live run

Warnings must be recorded with owners or replacement plans, but they do not block unless they affect visible correctness, licensing for production delivery, or command validity.
