# SVGlide Craft

这份文档是 `slides +create-svg` 的短版 craft 规则。它只约束 SVG 生成质量，不改变 `svg-protocol.md` 和 `lark-slides-create-svg.md` 的硬协议。

## Context Order

生成 SVGlide SVG 时按这个顺序理解上下文：

```text
svg-protocol.md
  -> lark-slides-create-svg.md
  -> style-presets.json / style-presets.md
  -> svg-seeds.json
  -> svg-recipes.json / svg-visual-recipes.md
  -> svglide-craft.md
  -> slide_plan.json
  -> SVG source
  -> svg_preflight.py
  -> preview review
  -> dry-run / live create / readback
```

## Open Design Local Adaptation

SVGlide 复制 Open Design 的生成控制体系，不复制 HTML runtime/CSS。不要迁移 `1920x1080` stage、runtime.js、localStorage、keyboard navigation、CSS animation、Chart.js 或 canvas FX。SVGlide 输出仍然是 `960 x 540` protocol SVG，再由 Slides 服务转成 slide snapshot。

生成顺序：

```text
choose style_preset
-> choose seed_id from svg-seeds.json
-> keep seed layout_skeleton / layout_boxes / text_budget_by_role / footer_safe_zone / vertical_text_policy
-> replace content inside the existing boxes
-> verify content_budget / text_capacity / role text budget
-> write SVG
-> run svg_preflight.py
```

	每页 plan 必须有 `seed_id`、`layout_skeleton_id`、`layout_boxes`、`content_budget` 或 `text_capacity`、`text_budget_by_role`、`one_idea` 或 `key_message`、`reserved_bands.footer`、`footer_safe_zone`、`vertical_text_policy`。如果内容放不进 seed，不要从空白画布重画；先删内容、拆页，或换一个更合适的 seed。

## SVGlide Design Pattern Lessons

SVGlide 内置设计模式的关键是页型先行和节奏先行。生成时只能借鉴流程与结构合同，不复制 PPTX 导出、DrawingML 限制或 raw SVG path。

每页先锁定：

```json
{
  "page_rhythm": "anchor | breathing | dense",
  "page_type": "cover | editor_note | contents | chart_takeaway | chapter | closing",
  "chart_type": "bar_chart | sankey_chart | hub_spoke | ...",
  "main_visual_anchor": "the visible chart/scene/motif that makes this page memorable",
  "annotation_zone": {"role": "right_observation", "x": 690, "y": 126, "width": 206, "height": 246},
  "reference_asset": {"source": "svglide_design_pattern", "asset_id": "chart.bar_chart", "usage": "geometry pattern only"}
}
```

硬规则：

- `page_rhythm` 要有起伏：anchor/breathing 页给叙事留气口，dense 页才承载图表密度。
- `main_visual_anchor` 必须能在截图里一眼看到；标题、三 bullet、普通卡片不算 anchor。
- `chart_type` 一旦声明，SVG source 必须画出对应几何：bar 要有多根 bar，sankey 要有多条 flow path，hub 要有中心节点和 spokes，quadrant 要有 2x2 区块。
- `bubble_chart` 和 `donut_chart` 不能退化成普通卡片页：bubble 至少用多枚圆形节点表达规模/关系，donut 至少用环形/圆形结构、分段和中心 KPI 表达构成。
- dense 页的信息密度必须由 chart/table/flow/hub/quadrant 承担，不能靠堆文字或装饰线。
- 图片 atmosphere 只服务 cover/chapter/showcase；图片必须无可见文字、预留 SVG 标题负空间，并有 asset_contract。
- 浅字、白字、name-plate、label-back、badge 和 pill 必须有独立承载面；底板不能压住 note、source、正文或图表标签。
- 高饱和红/金等强调色只用于核心数字、风险、章节锚点或极少数对比线，不能把每个组件都染成同等权重。

硬默认：

- 不从空白 SVG 起稿；seed skeleton 是版式合同，不是风格灵感。
- `layout_boxes` 只能在 seed 容忍范围内微调；大改结构先换 seed 或新增 seed。
- `text_budget_by_role` 只能收紧不能放宽；局部 title/body/callout/footer 超量时删内容、拆页或换 seed。
- `footer/source/legal/page mark` 只放 `footer_safe_zone`；正文、图例、chart label、标签和解释文字不得进入或贴近 footer band。
- 默认禁止竖排正文、`writing-mode`、`text-orientation` 和旋转长文本；只有 seed 允许的短装饰标签可保留。

## Layout And Typography

- 默认画布 `960 x 540`，关键内容保持在 `x=48..912`、`y=40..500`。
- 先规划 `titleBox`、`visualBox`、`textBox`、`chartBox`、`calloutBox`、`imageBox`、`connectorPath`，再写 SVG。
- `layout_boxes` 必须来自 seed，并且在 plan 中显式记录；生成 SVG 时所有标题、正文、图表、callout、footer 坐标都从这些盒子推导。
- footer/source/legal/page mark 只放在 `reserved_bands.footer` / `footer_safe_zone`；正文、callout、label、legend、chart label 不能侵入 footer band。
- label / chip / badge / 装饰块不能覆盖可读文字；它们要么有自己的短文本盒，要么离正文和竖排说明保持明确间距。
- badge / pill 到标题至少 12-16px；装饰线到标题至少 18-24px；标题底部到任何 text surface 至少 24px。
- 中文正文每行约 18-28 字；英文正文每行约 45-62 字符。
- 正文不低于 14px；图表标签不低于 11px。
- 修重叠和溢出时重算 layout boxes，不要只整体缩小。

## Text Surface Contract

承载可见文字的区域不能默认裸白底黑字。使用一种 preset 派生 surface：

- `accent_rail_card`
- `tinted_panel`
- `glass_overlay`
- `dark_backing`
- `label_chip`
- `metric_tile`

禁止 connector line 穿过文字；禁止 label chip 承载长句；禁止多页重复裸白卡片。

禁止把可见文案放进隐藏或裁切容器：`display:none`、`visibility:hidden`、近零 opacity、`overflow:hidden`、`clip-path`、`mask` 都不能作为“塞下文本”的办法。

## SVG Advantage

每页必须声明并实现：

```json
{
  "visual_signature": "curved route path plus ownership badges",
  "svg_effects": ["path", "connector_flow", "typography"],
  "xml_like_risk": "without the route path this becomes ordinary bullets"
}
```

可接受的 SVG advantage：

- path / route / flow spine
- chart geometry
- dashboard / grid geometry
- image overlay
- spotlight annotation
- technical texture
- watermark text
- brand motif

不足以证明 SVG advantage：

- 标题 + bullets
- 普通白卡片
- 换色背景
- 单个静态 emoji/icon
- plan 声明了效果但 SVG source 中不存在。

## Anti AI Slop

live create 前必须清理：

- lorem、placeholder、`点击添加正文`、demo data；
- 编造数字、客户、年份、来源；
- source token、local path、preset 名、prompt、tool 名泄漏到可见文本；
- 默认蓝紫泛科技渐变；
- emoji 当图标系统；
- 连续多页同一三卡片结构；
- 空图片框、破图、未记录 preview-only 来源。

## Asset Lanes

| Lane | 用法 | 门禁 |
|-|-|-|
| `svg_reference_only` | 只参考外部 SVG 构图、线条、留白和配色。 | 必须有 `reference_source_contract`；不得复制 path/symbol/group。 |
| `preview_image` | 预览阶段使用真实图片或截图增强效果。 | 必须记录 `retrieval_query`、`source_url`、`license=preview_unverified`、`replacement_required=true`。 |
| `production_asset` | 正式交付使用的图片、图标、截图。 | 必须使用用户提供、自有、明确授权或可商用资产。 |

不要用纯 SVG lane 成功证明 image-token lane 一定成功；图片页必须单独 smoke/readback。

## Quality Gate

继续 live create 的条件：

- `svg_preflight.py` 无 error；
- 本地 preview 已产出并记录 `preview_path`、`issue_ids`、`visual_score` 和 `action`；
- 只有 `action=create_live` 才能继续 live API；P0 或未记录 preview action 时必须 `repair_and_rerun`；
- P1 已修复或用户明确接受草稿；
- dry-run 请求结构符合预期；
- readback 风险、图片 token 风险和 fallback 选择被记录。
