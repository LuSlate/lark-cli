# SVGlide Assets Contract

本文只在 `svglide-svg` route admission 之后读取。`assets` stage 负责在 SVG 生成前把素材依赖变成可审计状态。

## Inputs

- `02-plan/slide_plan.json`
- optional `02-plan/svglide.lock.json`
- optional existing `03-assets/assets.json`

## Outputs

- `03-assets/assets.json`
- `03-assets/asset-manifest.json`
- `03-assets/image-jobs.json`
- `receipts/assets.json`

`assets.json` 是 `@./path` 到 file token 的可选映射：

```json
{
  "@./03-assets/hero.png": "boxcn_xxx"
}
```

`asset-manifest.json` 记录 plan/lock/assets hash、asset contracts、缺失素材、素材获取结果、来源 URL、license、digest、placement role、safe text zones、fallback 和不可创建素材。

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
  "placement_role": "cover | background | body_visual | inline_figure | closing",
  "query": "search phrase or image prompt seed",
  "license": "owned | preview_unverified | generated | user_provided"
}
```

## Online Acquisition

`assets` stage 默认由 runner 传入 `--network-policy auto`，按以下顺序处理素材：

1. 已有本地 `@./...` 文件或 `assets.json` file token。
2. 外部 stage command 或用户预置文件。
3. 可联网时下载 HTTP 图片或通过 provider 搜索图片。
4. 配置 image backend 时写入 `03-assets/image-jobs.json`，由外部 backend 生成。
5. 不能获取真实图片时记录 `svg_fallback`，生成阶段必须用 SVG-native component 兜底。

测试、golden 和 CI 使用 `--network-policy fixture` 或 `--offline`，不得依赖真实网络。

`image-jobs.json` 只记录 prompt 和 backend 计划，不要求主模型具备多模态能力，也不在 runner 内强制调用图片生成服务。

## Blocking Rules

- Required `@./...` 本地文件不存在：阻断。
- Required `http://`、`https://`、`data:` 图片：如果 acquisition 不能下载成本地文件或换成 file token，则阻断 live create。
- `assets.json` 非 object 或 key/value 不是 string：阻断。
- Optional missing asset 可以记录为 `missing_optional`，但不能形成空图片框。
- Cover/background/closing 图片必须在 manifest 中记录 `safe_text_zones`，标题和结论必须使用 editable overlay。
- Body visual 和 inline figure 必须保留 source/caption/annotation 所需 metadata；核心论点和数据不得烘焙进图片。

## Relationship With Prepare

`prepare` 只消费 `assets` stage 的结果，不负责决定素材策略。`prepare` 可以验证 SVG 内的 `@./...` 引用是否已映射或本地存在，但不能补全来源、授权或生成图片。
