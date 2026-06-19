# SVGlide Plan Contract

Read this file only after `svglide-svg` route admission. It defines the execution plan files consumed by preflight, preview, create, and readback stages.

## Files

Primary plan:

```text
.lark-slides/plan/<deck-id>/02-plan/slide_plan.json
```

Optional execution lock:

```text
.lark-slides/plan/<deck-id>/02-plan/svglide.lock.json
```

`slide_plan.json` is the user-visible plan. `svglide.lock.json` is an execution profile: it locks route, canvas, safe area, style system, quality profile, ordered page paths, and required SVG constraints. It must not introduce new user-visible content.

For the expanded execution-lock contract, see `svglide-lock.contract.md`.

Plan confirmation:

```text
.lark-slides/plan/<deck-id>/02-plan/plan-confirmation.json
```

The runner writes `02-plan/plan-confirmation.request.json` when confirmation is missing. A human-confirmed `plan-confirmation.json` is required before asset collection, `generate_svg`, prepare, dry-run, or live-create.

## Minimum Plan Fields

`slide_plan.json` must include:

- `route` or `output_mode` set to `svglide-svg`
- `plan_path` pointing to `02-plan/slide_plan.json`
- `loaded_rule_set` with `svglide-svg-private.rules.json`
- `canvas` with `width: 960`, `height: 540`, and `viewBox: "0 0 960 540"`
- `safe_area`
- `style_system` or equivalent style profile
- `art_direction`
- `quality_gates`
- `business_claims` when visible claims are used
- `asset_contracts` when visible images, icons, chart data, or file tokens are required
- ordered `svg_files` pointing to `04-svg/prepared/page-###.svg`
- `slides` metadata matching the ordered SVG pages

## Lock Fields

When present, `svglide.lock.json` must include:

```json
{
  "version": "svglide-lock/v1",
  "route": "svglide-svg",
  "plan_path": "02-plan/slide_plan.json",
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {},
  "style_tokens": {},
  "quality_profile": "production",
  "generation_rules": {},
  "asset_contracts": [],
  "business_claims": [],
  "page_contracts": [
    {
      "page": 1,
      "path": "04-svg/prepared/page-001.svg",
      "rhythm": "anchor",
      "layout_family": "cover",
      "visual_recipe": "",
      "required_primitives": [],
      "svg_effects": []
    }
  ],
  "pages": [
    {
      "page": 1,
      "path": "04-svg/prepared/page-001.svg",
      "visual_recipe": "",
      "required_primitives": [],
      "svg_effects": []
    }
  ]
}
```

## Confirmation Fields

`plan-confirmation.json` must include:

```json
{
  "version": "svglide-plan-confirmation/v1",
  "status": "confirmed",
  "confirmed_by": "user",
  "confirmed_at": "2026-06-18T00:00:00+08:00",
  "plan_path": "02-plan/slide_plan.json",
  "plan_sha256": "<sha256>",
  "lock_path": "02-plan/svglide.lock.json",
  "lock_sha256": "<sha256>"
}
```

`lock_path` and `lock_sha256` are required only when `02-plan/svglide.lock.json` exists. The hash fields must match the current files so stale confirmations cannot authorize changed plans.

## Conflict Rules

- If the lock exists, preflight treats it as the execution source for route, canvas, safe area, quality profile, and ordered page paths.
- If plan and lock disagree on route, page count, page path, canvas, safe area, or style profile, preflight reports `plan_lock_conflict`.
- If the lock is absent, P0 allows the equivalent execution profile to live inside `slide_plan.json` for compatibility.
- The lock must stay small. It is not a second full plan schema and must not duplicate page copy, speaker notes, or narrative outline.
- If plan confirmation is absent or stale, runner must stop before generation and create `02-plan/plan-confirmation.request.json`.
