# SVGlide Generate SVG Contract

本文只在 `svglide-svg` route admission 之后读取。`generate_svg` 是源 SVG 生成阶段，对应产物是 `04-svg/page-###.svg`。

## Stage Boundary

`generate_svg` 不做这些事：

- 不上传文件。
- 不调用 `slides +create-svg`。
- 不生成线上 presentation。
- 不替代 `prepare`、`preflight`、`preview_lint` 或 `readback`。

`generate_svg` 只做这些事：

- 读取确认后的 plan/lock/assets。
- 生成或登记源 SVG。
- 为整 deck 和每页写 hash receipt。

## Inputs

- `02-plan/slide_plan.json`
- optional `02-plan/svglide.lock.json`
- `03-assets/asset-manifest.json`
- optional generator script:
  - `04-svg/generate_svg.py`
  - `logs/generate_svg.py`
  - `logs/generate_svgs.py`

## Outputs

- `04-svg/page-###.svg`
- `04-svg/page-###.receipt.json`
- `receipts/generate_svg.json`

## Page Receipt

每页 receipt 必须至少包含：

```json
{
  "version": "svglide-page-generation/v1",
  "stage": "generate_svg",
  "page": 1,
  "source_svg": "04-svg/page-001.svg",
  "source_sha256": "<sha256>",
  "lock_path": "02-plan/svglide.lock.json",
  "lock_sha256": "<sha256>",
  "asset_manifest_path": "03-assets/asset-manifest.json",
  "asset_manifest_sha256": "<sha256>",
  "generator_mode": "script | external",
  "theme_archetype": "company_ecosystem",
  "identity_fit_reason": "renderer and visual recipe fit the declared visual_identity",
  "reuse_risk_score": 0,
  "fallback_skeleton_used": false
}
```

The deck-level `receipts/generate_svg.json` must summarize these page identity records in `page_identity_summary` and expose `fallback_skeleton_used`. Strict profiles reject `fallback_skeleton_used=true`; preview-only profiles may treat it as a repair warning.

## Discipline

- 新建 deck 优先让 `generate_svg` 执行项目内 generator script。
- 如果源 SVG 已由外部 agent 生成，可登记为 `generator_mode=external`，但必须记录 hash。
- 生成后修改 `04-svg/page-###.svg` 必须重跑 `generate_svg`，否则 `prepare` 阻断。
- CLI 不迁移 ppt-master “禁止脚本生成”的规则；CLI 允许脚本生成，但必须用 lock/assets/hash/receipt 把漂移控制住。
- Generator scripts must consume `slide_plan.visual_identity`; if they fall back to a generic skeleton, they must mark that fact in the page and deck receipts.
