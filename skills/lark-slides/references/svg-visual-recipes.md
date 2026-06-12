# SVGlide 视觉 Recipe

这份文档是 `slides +create-svg` 的短版可执行 recipe 指南。
它把研究目录提炼成生成阶段可放入 agent 上下文的规则。
更完整的研究资料保留在 CLI skill 外；公开生成上下文只使用本文列出的
underscore runtime id。

## 边界

- `visual_recipe` 定义页面结构，以及这一页为什么值得用 SVG。
- `style_preset` 定义视觉语言、配色、纹理、密度和 motif。
- `renderer_id` 定义具体几何渲染器。

不要用 `style_preset` 替代 `visual_recipe`。不要在 `slide_plan.json`
里发明新的 recipe id。

## 硬默认值

- 画布：`width="960" height="540" viewBox="0 0 960 540"`。
- 安全区：关键文本、标签、图表、卡片、节点和图例保持在
  `x=48..912` and `y=40..500`.
- 网格：使用稳定的 12 栏或 8px 步进布局，避免临时手调坐标。
- 文本：中文正文每行控制在约 28 个字；英文正文每行约 62 个字符。
- 装饰：装饰线、水印、纹理和背景几何不能抢夺标题/焦点内容的注意力，也不能贴住它们。
- Deck 多样性：8 页以上 SVG deck 应至少使用 5 种 visual recipe family。

## Plan 字段

写 SVG 前，每个 SVG 页面 plan 都必须包含这些字段：

```json
{
  "visual_recipe": "path_flow",
  "visual_intent": "show a staged route from current state to target state",
  "visual_focal_point": "curved route spine with the final target node",
  "visual_signature": "curved route path plus stage annotations",
  "svg_effects": ["path", "connector_flow", "typography"],
  "required_primitives": ["path", "annotation"],
  "svg_primitives": ["path", "annotation", "typography"],
  "xml_like_risk": "without the route geometry this becomes ordinary bullets",
  "content_density_contract": "flow >= 4 stages",
  "risk_flags": [],
  "source_policy": "do not invent unsupported numbers"
}
```

## Recipe Selection Matrix

在 `slide_plan.json` 中使用这些 CLI 支持的 underscore id。

| 用户意图 | `visual_recipe` | SVG source 中必须体现 |
|---|---|---|
| 封面、章节开场、hero 观点页 | `hero_typography` | 大字、几何承载体、清晰焦点对象 |
| 战略框架、强几何版式 | `geometric_composition` | 非卡片式几何、`path` 或异形区域 |
| 路线图、旅程、流程、路径 | `path_flow` | 显式 path/line 主线、箭头或阶段标记 |
| KPI、战报、数据复盘 | `infographic_scorecard` | 大数字加微图表或仪表几何 |
| 能力地图、模块总览 | `icon_capability_map` | 风格统一的 SVG-safe 图标和标注区域 |
| 层次、氛围、概念强调 | `gradient_depth` | 渐变或分层半透明几何，并保证文字可读 |
| 产品/成果/图片叙事 | `mask_clip_showcase` | 图片区域加安全的 overlay/crop 模拟 |
| 技术系统、网格、编码质感 | `technical_texture` | 重复 line/dot/rect、网格、扫描线或图解纹理 |
| 闭环、飞轮、反馈系统 | `metaphor_loop` | 闭合路径或循环流程，并带输入/输出标签 |
| 诊断、callout、焦点标注 | `spotlight_annotation` | 高亮区域、callout 线、标注目标 |
| Dashboard、控制台、监控界面 | `fake_ui_dashboard` | UI frame、状态栏、指标、微图表/日志行 |
| 品牌或系列身份页 | `brand_system` | 稳定标题系统、motif、配色和重复身份元素 |

## 安全 Effects

优先使用可以由 SVGlide-safe primitives 表达的效果：

- `path`：曲线、波形、路线、自定义形状。
- `gradient`：背景层次和重点强调；关键文字必须有稳定承载底。
- `texture`：重复的 `line`、`circle` 或 `rect`；不要只依赖 `<pattern>`。
- `connector_flow`：显式 line/path 加箭头三角或圆点。
- `chart_geometry`：柱、点、线、仪表、坐标轴和标签。
- `grid_geometry`：矩阵、表格式视觉摘要、结构化对齐网格。
- `watermark_text`：低对比大字，不能影响阅读。
- `image_overlay`：真实图片加显式半透明 shape 覆盖层。
- `spotlight`：分层半透明形状，不依赖复杂 filter 光效。

## 高风险 Effects

这些效果只有在 `risk_flags` / `recipe_fallback` 中声明了安全改写或
fallback 时，才允许出现在 visual planning 中：

- `filter`
- `mask_clip`
- `pattern`
- `symbol`
- `stroke_dasharray`
- `image_opacity`

关键视觉在调用 `slides +create-svg` 前，应改写成显式 shape、line、dot、
overlay，或预合成图片。

## 反退化规则

- 如果页面主要只是 `rect + foreignObject`，还不足以证明值得走 SVGlide；
  除非它同时具备真实 SVG-native 结构：path、chart geometry、icon system、
  texture、spotlight、dashboard frame、connector flow 或 image overlay。
- 第一眼看到的对象应该和该页 `visual_focal_point` 一致。
- 相似页面可以共享 `style_preset`，但不能只替换文案和背景色，布局骨架完全不变。
- 研究笔记里的 dotted recipe 名称不是有效运行时 id。
  写入 plan 前必须映射到上面的 underscore id。
