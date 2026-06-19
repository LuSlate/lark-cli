# SVGlide Assets Contract

本文只在 `svglide-svg` route admission 之后读取。`assets` stage 负责在 SVG 生成前把素材依赖变成可审计状态。

## Inputs

- `02-plan/slide_plan.json`
- optional `02-plan/svglide.lock.json`
- optional existing `03-assets/assets.json`

## Outputs

- `03-assets/assets.json`
- `03-assets/asset-manifest.json`
- `receipts/assets.json`

`assets.json` 是 `@./path` 到 file token 的可选映射：

```json
{
  "@./03-assets/hero.png": "boxcn_xxx"
}
```

`asset-manifest.json` 记录 plan/lock/assets hash、asset contracts、缺失素材和不可创建素材。

## Contract Sources

`svglide_assets.py` 从这些字段收集素材契约：

- `slide_plan.json.asset_contracts`
- `slide_plan.json.assets`
- `slide_plan.json.images`
- `svglide.lock.json.asset_contracts`
- `svglide.lock.json.assets`
- `svglide.lock.json.images`

每个契约至少应包含：

```json
{
  "id": "hero",
  "href": "@./03-assets/hero.png",
  "required": true,
  "usage_page": 1,
  "license": "owned | preview_unverified | generated | user_provided"
}
```

## Blocking Rules

- Required `@./...` 本地文件不存在：阻断。
- Required `http://`、`https://`、`data:` 图片：阻断 live create；必须下载成本地文件或换成 file token。
- `assets.json` 非 object 或 key/value 不是 string：阻断。
- Optional missing asset 可以记录为 `missing_optional`，但不能形成空图片框。

## Relationship With Prepare

`prepare` 只消费 `assets` stage 的结果，不负责决定素材策略。`prepare` 可以验证 SVG 内的 `@./...` 引用是否已映射或本地存在，但不能补全来源、授权或生成图片。
