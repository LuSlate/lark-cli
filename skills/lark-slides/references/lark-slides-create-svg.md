# slides +create-svg

从一个或多个 SVGlide SVG 文件创建飞书幻灯片：

```bash
lark-cli slides +create-svg \
  --as user \
  --title "Demo" \
  --file page1.svg \
  --file page2.svg
```

## 适用场景

- AI 已经能生成符合 [svg-protocol.md](svg-protocol.md) 的 SVGlide SVG。
- 希望按文件逐页创建，避免把大段 XML/SVG 塞进 shell 参数。
- 需要 SVG 内本地图片占位符自动上传并替换为 file token。
- 需要把原生 chart 的 canonical JSON spec 作为 root chart spec marker 透传给服务端。

不适用：

- 你只有普通 SVG，且没有 `slide:role` 协议标记。
- 复杂普通 SVG 不能直接提交；需要把实际可渲染元素标成 SVGlide role。`g` / 嵌套 `svg` 容器可以保留，但不能代替子元素 role。
- 你想通过 SVG 路径提交 whiteboard marker；`slide:role="whiteboard"` 和旧 `data-svglide-whiteboard` marker 会被 CLI 拒绝。
- 你需要插入到指定页前；MVP 只创建新 presentation 并按顺序追加页面。

## Flags

| Flag | 说明 |
|------|------|
| `--title` | presentation 标题，省略时为 `Untitled` |
| `--file` | SVG 文件路径；可重复，页面顺序就是 flag 顺序 |
| `--assets` | 可选 `assets.json`，把 SVG `@path` 映射到已上传 file token |
| `--dry-run` | 展示创建空白 presentation + N 次 `/slide` 调用，不真实创建 |

## 请求链路

CLI 先创建空白 presentation：

```http
POST /open-apis/slides_ai/v1/xml_presentations
```

随后对每个 SVG 文件调用现有 slide create 路由：

```http
POST /open-apis/slides_ai/v1/xml_presentations/{xml_presentation_id}/slide?revision_id=-1
```

body：

```json
{
  "slide": {
    "content": "<svg ...>...</svg>"
  }
}
```

不会新增 `/svg_slide` 路由，也不会把 `file_meta_map` 当成 CLI 到服务端的契约。

chart spec marker 也不新增 API。CLI 不会上传 chart 资源，也不会调用任何 chart 创建接口；它只把通过 marker 外壳、hash 和 JSON spec 基础校验的 marker 留在同一个 `slide.content` SVG 中。

## 图片处理

SVG 内本地图片写成：

```xml
<image slide:role="image" href="@./hero.png" x="0" y="0" width="320" height="180" />
```

`<image>` 可以位于 `g` / 嵌套 `svg` 容器中；CLI 会全局扫描 `<image href="@...">` 或 `<image xlink:href="@...">` 并替换为 canonical `href="file_token"`。

CLI 会：

1. 上传本地图片到新 presentation。
2. 把 `href="@./hero.png"` 或 `xlink:href="@./hero.png"` 替换为 canonical `href="file_token"`。
3. 注入 transport metadata：`<metadata data-svglide-assets="true"><img src="file_token" /></metadata>`。

注意：图片上传成功只证明 Drive media upload 成功，不证明目标 live lane 已能解析
SVGlide image token。若某个 lane 中纯 SVG 页可创建、但带 `@./assets/...`
的页面在上传后进入 `/slide` 阶段报 `nodeServer internal error`，应按
image-token 兼容性问题处理，而不是继续修改图片文件本身。`ppe_pure_svg`
的内部路由和已知边界记录在
[routes/create-svg/private/ppe-pure-svg-live.md](routes/create-svg/private/ppe-pure-svg-live.md)，
这份知识只属于 `slides +create-svg` route，XML/SXSD 路径不得调用。

预上传资源可用 `--assets`：

```json
{
  "@./hero.png": "boxcn..."
}
```

## Chart Spec Marker

`slides +create-svg` 支持一种最小 chart marker，用于透传 canonical JSON chart spec。payload 不是 SXSD `<chart>` XML，也不是 chart snapshot/staticData；服务端会在 SVGlide parser 内部把 spec 转成 chart 创建所需数据：

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:slide="https://slides.bytedance.com/ns"
     slide:role="slide"
     slide:contract-version="svglide-authoring-contract/v1"
     width="960" height="540" viewBox="0 0 960 540">
  <g slide:role="chart"
     slide:chart-ref="chart-sales-001"
     x="80" y="96" width="420" height="260">
    <metadata
      data-svglide-chart="svglide-chart-inline/v1"
      data-format="svglide-chart-spec-v1"
      data-encoding="base64url-json"
      data-payload-hash="sha256:<64 hex>"
    >BASE64URL_PAYLOAD</metadata>
  </g>
</svg>
```

Decoded canonical JSON shape:

```json
{"version":"svglide-chart-spec/v1","chartType":"bar","data":{"categories":["Q1","Q2"],"series":[{"name":"Revenue","values":[12.5,18]}]}}
```

CLI 校验范围只包括：

- marker 必须是 root `<svg>` 直系 `<g slide:role="chart">`。
- `slide:chart-ref` 和 `x/y/width/height` bbox 必填，bbox 只接受数字或 `px`。
- marker 内必须且只能有一个 `<metadata>`。
- metadata 必须使用 `data-svglide-chart="svglide-chart-inline/v1"`、`data-format="svglide-chart-spec-v1"`、`data-encoding="base64url-json"`。
- payload 必须是无 padding base64url，`data-payload-hash` 必须匹配 decoded canonical JSON bytes 的 sha256；不要对 base64 文本计算 hash。
- decoded payload 必须是 JSON object，且包含 `version="svglide-chart-spec/v1"`、`chartType`、`data.categories`、`data.series[].name` 和 `data.series[].values`。
- MVP 只支持 `chartType="bar"` / `"line"`；`categories` 和每个 `values` 数组长度必须一致；`values` 只能是有限 JSON number。

旧 `sxsd-chart-v1` / `base64url` 的 SXSD `<chart>` XML payload 不属于 SVGlide chart marker 协议面，会被 CLI 拒绝。`slide:role="whiteboard"` 和旧的 `data-svglide-whiteboard` marker 明确不属于 `+create-svg` 协议面。

## 生成质量规则

这些规则用于生成阶段主动规避服务端降级、近似和泛化错误。几何数值、path 命令、role/必填属性、图片 href 等基础约束已由 CLI 强校验；版式、美观和文本溢出仍需要生成器或人工复核。

### Open Design 方法在 SVGlide 中的边界

SVGlide 借鉴 Open Design 的“受约束创作系统”，不是照搬 HTML deck runtime。

| Open Design 机制 | SVGlide 对应做法 |
|-|-|
| deck mode / skill routing | 只有 `slides +create-svg` route 加载 SVG 私有规则；XML/SXSD 路径不得读取 SVG private recipe。 |
| template seed / layout catalog | 使用 `svg-seeds.json` 中的 `seed_id + layout_skeleton + visual_recipe + layout_boxes + content_budget + text_budget_by_role + footer_safe_zone + vertical_text_policy` 作为 SVG seed，不复制 HTML section。 |
| design system / tokens | 使用 `style-presets.json` 和 `style_system`，翻译为显式 SVG `fill` / `stroke` / 字号 / 文本承载面。 |
| craft | 读取 `svglide-craft.md`，约束排版、SVG advantage、反 AI 味和资产 lane。 |
| artifact lint / publication guard | 使用 `svg_preflight.py`、preview review、dry-run、live readback 和截图/native oracle。 |

不要照搬 HTML deck 的 `1920x1080` stage、`runtime.js`、keyboard navigation、localStorage、CSS animation、Chart.js 或 canvas FX。SVGlide 只复制 Open Design 的生成控制体系：先选 seed/layout，再替换内容，保留结构和预算，不从空白画布开始。SVGlide 的硬边界仍是 `960x540` 协议化 SVG，并由 Slides server 转成真实线上文档快照。

### Seed Skeleton Contract

seed skeleton 不是灵感参考，而是初始版式骨架。生成器必须保留 seed 的 `required_layout_box_roles`、关键 `layout_boxes`、`reserved_bands.footer`、`footer_safe_zone` 和文本容量上限；允许在 seed 容忍范围内微调坐标，但不得删除角色、把 footer 改成正文区，或用 freestyle 坐标绕过 seed。

每页必须先选 `seed_id`，再填内容。内容放不下时，处理顺序是删减、拆页、换 seed；不得放宽 seed 的 `content_budget`、`text_budget_by_role`、`footer_safe_zone` 或 `vertical_text_policy`。新增页面结构时，先新增/更新 `svg-seeds.json`，再生成 SVG。

### 与现有规划层对齐

SVG 创建不使用单独的规划目录。新建或大幅改写 SVG deck 时，仍然复用 [planning-layer.md](planning-layer.md) 规定的 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`，不要另建 `.lark-slides/svg-plan` 或只保留散落的 `.svg` 文件。

当需要把生成、prepare、preview、preflight、preview_lint、quality_gate、dry-run、PPE proof、live create 和 readback 串成可恢复流水线时，项目级 `project_manifest.json`、`state.json`、`prepared/` 和 `receipts/` 规则见 [svglide-project-pipeline.md](svglide-project-pipeline.md)。该文档只管本地执行状态，不替代 `slide_plan.json`、SVG 协议或 route-private 规则。

在通用 plan 字段基础上，SVG deck 还应补充这些 SVG 专属字段：

```json
{
  "output_mode": "svglide-svg",
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
  "style_preset": "raw_grid",
  "style_selection_reason": "raw_grid fits technical training pages that need dense but readable visual structure",
  "style_system": {
    "palette": {
      "background": "#F5F5F5",
      "text": "#0A0A0A",
      "accent": "#F2D4CF"
    },
    "typography": "strong title, readable native text labels",
    "background_strategy": "muted grid panels with one stable background family",
    "motif": "dense grid panels with restrained accent labels"
  },
  "svg_constraints": {
    "text_element": "foreignObject slide:role=shape slide:shape-type=text",
    "path_commands": "M/L/H/V/C/Q/Z only",
    "image_href": "@./path or file token only",
    "css": "explicit font-size/font-weight/color/line-height/text-align; no font shorthand"
  },
  "svg_files": [
    {"page": 1, "path": ".lark-slides/plan/<deck-id>/pages/page-001.svg"}
  ],
  "preflight": {
    "command": "python3 skills/lark-slides/scripts/svg_preflight.py --route-manifest skills/lark-slides/references/routes/create-svg/route.manifest.json --report-scope public --plan .lark-slides/plan/<deck-id>/slide_plan.json --input .lark-slides/plan/<deck-id>/pages/page-001.svg",
    "status": "pending"
  },
  "readback_verification": {
    "status": "pending",
    "checks": ["page_count", "blank_page", "canvas_bounds", "text_overlap", "asset_tokens", "closing_slide"]
  }
}
```

每页还必须有 `visual_design_contract`。它不是新的一套平行 plan，而是把现有
`seed_id`、`visual_recipe`、`renderer_id`、`design_pattern_selection` 和页面
视觉目标锁成可验收字段：

```json
{
  "visual_design_contract": {
    "schema_version": "svglide-visual-design-contract/v1",
    "page_kind": "chart_takeaway",
    "visual_thesis": "这一页视觉上要让用户记住的结论",
    "composition_archetype": "data_stage",
    "pattern_bundle": ["chart.bar_chart"],
    "density": "dense",
    "primary_motif": "takeaway_chart",
    "required_visual_evidence": ["chart_geometry", "insight_strip", "full_page_archetype"]
  }
}
```

`required_visual_evidence` 必须由 renderer 写入
`receipts/emitted_components.json` 的 page-level component `effects`、
`primitives`、`renderer_id` 或 component id。`quality_gate` 会核对这些证据；
只在 plan 里声明但 SVG/component report 没有落地时不得进入 dry-run/live。

模板也复用现有 `template_tool.py search -> summarize -> extract` 路由。模板摘要只用于选择主题、页面流、视觉节奏和布局骨架；生成 SVG 时要把模板结构翻译成 SVG layout boxes / visual recipes，不要照搬模板 XML，也不要读取完整模板 XML。

SVG deck 的 `slides[]` 还必须包含这些可校验字段，避免生成结果虽然能创建但内容千篇一律、信息量不足或在资料缺失时编造事实：

```json
{
  "page": 3,
  "renderer_id": "dashboard_scorecard",
  "page_rhythm": "dense",
  "page_type": "kpi_overview",
  "chart_type": "kpi_cards",
  "main_visual_anchor": "2x2 KPI scorecard with hero numbers and micro bars",
  "annotation_zone": {"role": "right_observation", "x": 690, "y": 126, "width": 206, "height": 246},
  "seed_id": "dashboard_kpi_grid",
  "layout_skeleton_id": "dashboard_kpi_grid_skeleton",
  "layout_family": "dashboard",
  "visual_recipe": "fake_ui_dashboard",
  "layout_boxes": [
    {"id": "title", "role": "title", "x": 48, "y": 34, "width": 864, "height": 48},
    {"id": "primary-kpi", "role": "metric", "x": 64, "y": 106, "width": 260, "height": 128},
    {"id": "secondary-grid", "role": "grid", "x": 348, "y": 106, "width": 548, "height": 128},
    {"id": "chart-row", "role": "chart", "x": 64, "y": 258, "width": 832, "height": 150},
    {"id": "body", "role": "body", "x": 64, "y": 426, "width": 832, "height": 56},
    {"id": "footer", "role": "footer", "x": 64, "y": 500, "width": 832, "height": 24}
  ],
  "content_budget": {"max_visible_chars": 360, "title": 34, "body": 230, "footer": 36, "max_text_boxes": 14},
  "text_capacity": {"max_visible_chars": 360, "title": 34, "body": 230, "footer": 36, "max_text_boxes": 14},
  "text_budget_by_role": {
    "title": {"max_chars": 34, "max_lines": 2, "max_boxes": 1, "min_font_px": 22},
    "body": {"max_chars": 230, "max_lines": 5, "max_boxes": 1, "min_font_px": 12},
    "metric": {"max_chars": 96, "max_lines": 3, "max_boxes": 4, "min_font_px": 12},
    "footer": {"max_chars": 36, "max_lines": 1, "max_boxes": 1, "min_font_px": 9}
  },
  "reserved_bands": {"footer": {"x": 48, "y": 496, "width": 864, "height": 32}},
  "footer_safe_zone": {"x": 48, "y": 496, "width": 864, "height": 32, "allowed_roles": ["footer"], "min_gap_above_px": 8},
  "vertical_text_policy": {"mode": "deny", "allowed_roles": [], "max_chars": 0, "max_lines": 0},
  "one_idea": "operating status is readable through dashboard structure",
  "key_message": "dashboard structure turns scattered metrics into one operating view",
  "visual_intent": "use a product-console dashboard surface to make metrics feel operational",
  "visual_focal_point": "central metric card and trend line",
  "visual_signature": "fake product console frame + micro chart geometry + status chips",
  "reference_asset": {"source": "svglide_design_pattern", "asset_id": "chart.kpi_cards", "usage": "page-type geometry only; do not copy raw SVG paths"},
  "svg_effects": ["chart_geometry", "connector_flow", "typography"],
  "required_primitives": ["dashboard", "micro_chart"],
  "svg_primitives": ["dashboard", "micro_chart", "typography", "geometric_shape"],
  "xml_like_risk": "without SVG primitives this page would degrade into three metric cards plus bullets",
  "recipe_fallback": "if dashboard micro charts are too dense, keep the fake UI frame and simplify charts to bar-like rects",
  "density": "high",
  "density_structure": "dashboard with four metric cards, trend line, and source note",
  "content_density_contract": "dashboard >= 4 metrics",
  "asset_contract": "none_required | {mode: authoring_preview_rich|online_pure_fallback|production_asset_strict, retrieval_query, source_type, license, local_path_or_href, usage_page, source_url/generated_by, replacement_required}",
  "risk_flags": ["text_overflow", "image_license", "conversion_dasharray"],
  "source_status": "source_verified | attachment_missing | user_prompt_only",
  "source_policy": "when attachment_missing, show 待从附件补齐 / 来源缺失 and avoid numeric claims",
  "layout_guardrails": [
    "renderer_id must change actual geometry, not only the name",
    "visual_recipe must map to SVGlide-safe primitives present in the SVG source",
    "main text and chart labels stay inside safe area",
    "dense page uses a structured visual carrier, not a long bullet box",
    "avoid XML-like card layout unless the page has real SVG-native visual structure"
  ]
}
```

### SVGlide Design Pattern Lessons

SVGlide design pattern 的可借鉴点是生成流程和页型合同，不是 PPTX/DrawingML 导出链路，也不是复制现成 SVG。SVGlide 生成时必须把经验收敛成 protocol-safe 字段：

- `page_rhythm`: `anchor` / `breathing` / `dense`。8 页以上 deck 不能全是 dense 或全是同一张卡片结构；封面、目录、章节、收尾应形成节奏。
- `page_type`: 页面叙事类型，例如 `cover`、`editor_note`、`contents`、`chart_takeaway`、`chapter`、`closing`。
- `chart_type`: 当页面主视觉是图表时必须声明，例如 `kpi_cards`、`bar_chart`、`dumbbell_chart`、`bubble_chart`、`donut_chart`、`horizontal_bar_chart`、`comparison_table`、`sankey_chart`、`pareto_chart`、`hub_spoke`、`dual_axis_line_chart`、`quadrant_text_bullets`。
- `main_visual_anchor`: 一句话说明这页的主视觉锚点。不能写成“高级图表”或“信息可视化”；必须能被截图肉眼确认。
- `annotation_zone`: 右侧观察、底部 source、图例或 callout 的固定区域。密集页靠图表承载信息，文字只做解释。
- `reference_asset`: 记录借鉴的 SVGlide design pattern layout/chart/image/style 资产，只表示结构和选择理由，不表示复制 raw SVG。

经验规则：

- 先选页型和图表，再写 SVG；不要从空白画布临场拼元素。
- 图表页必须有真实 chart geometry。声明了 `sankey_chart` 就要有 source/node/sink/flow；声明了 `bar_chart` 就要有 axis/bar/value/callout。
- 密集页的复杂度来自图表、表格、flow、hub、quadrant 等结构，不来自增加装饰线或文字盒。
- 封面和章节页可以使用图片/纹理作为 atmosphere，但图片必须预留负空间、无可见文字，并由 `asset_contract` 记录来源和替代策略。
- 红色/高饱和强调色只打关键数字、风险信号或章节标记；不要让所有图形同等抢眼。

经验归属：

- 本文件只保留 create-svg 的入口流程、plan 字段边界和 CLI 发布约束。
- 页型、图表几何、视觉节奏和 SVGlide design pattern 借鉴规则归 [svglide-craft.md](svglide-craft.md)。
- 项目目录、stage、timing、prepare resume、asset usage receipt 和 live guard 归 [svglide-project-pipeline.md](svglide-project-pipeline.md)。
- 自动门禁和 archetype drift 归 [validation-checklist.md](validation-checklist.md)。
- 截图/人工审美判断和 label/backing 遮挡经验归 [svg-aesthetic-review.md](svg-aesthetic-review.md)。

### Runtime Recipe Registry

Public `visual_recipe` 的机器真源是 [svg-recipes.json](svg-recipes.json)，`svg_preflight.py` 会直接读取它。[svg-visual-recipes.md](svg-visual-recipes.md) 是人类可读的选择指南，不是第二份 runtime catalog。

研究文档可以使用内部 taxonomy 讨论设计，但写入 `slide_plan.json` 前必须映射到 `svg-recipes.json` 中的 public underscore id，例如 `infographic_scorecard`、`geometric_composition`、`path_flow`、`fake_ui_dashboard`。公开文档、公开 fixtures 和 public preflight report 不应暴露 route-private 或 research dotted id。

### Runtime Seed Registry

SVGlide page seed 的机器真源是 [svg-seeds.json](svg-seeds.json)，`svg_preflight.py` 会直接读取它。seed 是 Open Design 经验的本地化控制层，不是可复制的 HTML 模板。

每个 seed 至少包含：

- `page_use`: 适用页型。
- `visual_recipe` / `layout_family`: seed 对应的结构类型。
- `layout_boxes`: 可复用的 title/body/visual/chart/footer 等盒子坐标。
- `content_budget` / `default_text_capacity`: 全页、title、body、footer 和 text box 数量预算。
- `reserved_bands`: footer/source/legal/page mark 等保留区域。
- `required_primitives`: seed 需要 SVG source 实现的 primitives。
- `quality_rules`: seed 的本地审查规则。

生成器必须先选 `seed_id`，再替换内容。允许微调 layout boxes，但必须保留 seed 的关键角色和 reserved band；如果需要完全不同的信息结构，换 seed，不要在原 seed 上硬塞内容。

### Style Preset Catalog

SVGlide 高质量生成必须先从 [style-presets.json](style-presets.json) 选择一个 deck-level `style_preset`，并把它翻译成 `style_system`。`style_preset` 不替代 `visual_recipe`：前者定义视觉语言，后者定义页面结构和 SVG-native 表达价值。

生成前还必须读取 [svg-visual-recipes.md](svg-visual-recipes.md)。该文件是当前 CLI 执行链路的短规则入口，负责把研究 catalog 映射成可写入 `slide_plan.json` 的 underscore `visual_recipe` 枚举、安全效果边界和 deck 多样性要求。

生成顺序：

```text
semantic plan
-> style_preset + style_system
-> deck arc
-> page seed_id from svg-seeds.json
-> page visual_recipe
-> layout boxes
-> SVG source
-> svg_preflight.py --route-manifest ... --report-scope public --plan
```

`visual_recipe` 可以反向校验 `style_preset`：如果页面结构需要强数据密度、路径流动或真实图片叙事，而 preset 的留白、色彩或 text surface 无法承载，应调整 preset 或重写该页视觉计划。

`style_system` 至少包含：

- `palette`: 背景、正文、强调色。
- `typography`: 标题、标签、正文的字号/字重策略。
- `background_strategy`: 全 deck 背景和例外页规则。
- `motif`: 可复用的视觉母题，例如 grid panels、stamp labels、court lanes、riso color plates。

每页必须声明：

- `visual_signature`: 这一页相对普通 XML/PPT 模板的独特 SVG 视觉记忆点。
- `svg_effects`: 真实使用或计划使用的 SVG 表达能力，例如 `path`、`connector_flow`、`gradient`、`texture`、`chart_geometry`、`image_overlay`。

`svg_preflight.py` 会校验 preset 是否存在、`style_system` 是否完整、可见文本是否泄漏 preset 名称/source token/tool/path，以及 declared `svg_effects` 是否能在 SVG source 中命中。

### SVG-native runtime recipe summary

SVG 不是普通矢量图文件的传输外壳。每页都必须选择一个 `visual_recipe`，并在 `svg_primitives` 中声明真实会绘制的 SVGlide-safe primitives。`renderer_id` 负责几何布局命名；`visual_recipe` 负责说明这页为什么值得走 SVG。

本节只是 `svg-recipes.json` 的人工摘要，帮助快速选型；不要手工维护为第二份 runtime catalog。实际生成和校验以 [svg-recipes.json](svg-recipes.json) 为准，生成前再读 [svg-visual-recipes.md](svg-visual-recipes.md)，避免把研究文档里的 dotted recipe 名称直接写进运行时 plan。

| `visual_recipe` | 适用页型 | required primitives | forbidden patterns / fallback |
|---|---|---|---|
| `hero_typography` | 封面、章节页、观点页 | `typography`, `geometric_shape` | 不要只写普通标题；大字用 `foreignObject`，描边/裁切感用大字背板、路径轮廓或分层 shape 模拟 |
| `geometric_composition` | 战略框架、阶段划分、版式强分区 | `geometric_shape`, `path` | 不要只堆 3 个矩形卡片；斜切块、多边形全部用 `path` 写，不用 `polygon` |
| `path_flow` | 路线、旅程、流程、增长路径 | `path`, `annotation` | 不依赖 `marker` / `stroke-dasharray`；箭头用显式三角 `path`，虚线用短 line/dot 组合 |
| `infographic_scorecard` | 数据战报、OKR、业务复盘 | `typography`, `micro_chart` | 不要只放大数字；补环形/条形/标尺等微图表，圆环用双层填充圆或 path |
| `icon_capability_map` | 能力地图、模块总览、平台能力 | `icon`, `geometric_shape` | 图标用 SVGlide-safe path/line/rect 组合，不用外链 iconfont 或根级 `<text>` |
| `gradient_depth` | 能力升级、概念页、氛围页 | `gradient`, `geometric_shape` | 渐变只作为层次，不能替代信息结构；关键文字必须有深色承载底 |
| `mask_clip_showcase` | 成果展示、产品/品牌视觉页 | `typography`, `image_overlay` | 不直接依赖 `mask` / `clipPath`；用大字描边、半透明 shape 遮罩、裁切安全区模拟 |
| `technical_texture` | 技术架构封面、工程系统页 | `texture`, `path` | 不用 `<pattern>`；网格、点阵、扫描线用重复 line/circle/rect 显式绘制 |
| `metaphor_loop` | 闭环、反馈系统、运营机制 | `path`, `geometric_shape` | 不只画 4 个圆节点；旁边必须补机制表、KPI 标签、输入输出或责任说明 |
| `spotlight_annotation` | 问题定位、架构标注、案例诊断 | `spotlight`, `annotation` | 发光用多层半透明 circle/rect/path 模拟，不依赖复杂 filter；标注线和 callout 必须对齐目标 |
| `fake_ui_dashboard` | 产品能力、CLI/平台/监控展示 | `dashboard`, `micro_chart` | 不要把 3 张指标卡伪装成 dashboard；必须有 UI frame、状态栏、图表/日志/趋势等操作界面细节 |
| `brand_system` | 系列化 deck、主题页、收尾页 | `typography`, `geometric_shape` | 不只换颜色；必须复用标题位置、边栏、编号、强调色、图标线宽或背景 motif |

`svg_preflight.py` 会校验 `visual_recipe` 枚举、必填字段、recipe required primitives、8 页以上 recipe family 多样性，以及 plan 声明的 primitives 是否能在 SVG source 中检测到。生成器不能只在 plan 里声明 recipe，实际仍画 XML 式卡片。

### Create-SVG Route-Private Recipes

SVG 私有 recipe 只属于 `slides +create-svg` route，用于鼓励更强的 SVG-native 艺术处理。它们不是 XML/SXSD 的共享知识，也不能写进普通共享 plan。

- Public/shared `slide_plan.json` 只能使用 public recipe id，或在 create-svg route 下使用抽象值 `visual_recipe: "route_private"`。
- Exact private recipe id 只允许出现在 route-private manifest、route-private selection sidecar、private fixture 或 internal report。
- 当使用 `route_private` 时，必须传入 create-svg route manifest；如果需要解析到具体 private recipe，还必须传入 route-private selection sidecar。没有 manifest/sidecar 时 preflight fail-closed，不猜测、不回退。
- Public preflight report 使用 `--report-scope public`，不得输出 exact private recipe id、manifest path、selection path 或 private enum list。
- XML 创建、普通 `+create`、共享 planning docs 和公开 fixtures 不得读取 route-private manifest，也不得调用 SVG 私有 recipe。

### 生成阶段 Fail-Fast Gate

`slide_plan.json` 不是说明文档，而是生成阶段的硬契约。生成器必须先通过 plan gate，再渲染 SVG；本地 `svg_preflight.py --plan` 失败时禁止调用 live API。

每页 SVG plan 必填：

| Field | 作用 | 失败后处理 |
|---|---|---|
| `renderer_id` | 标识具体渲染器/几何结构 | 换真实 renderer，不用 `two_column_1` 这类假命名 |
| `seed_id` | 绑定 `svg-seeds.json` 中的 page seed | 先选 seed，再写内容；不要从空白页直接开始 |
| `layout_skeleton_id` | 绑定 seed 的机器化版式骨架 | 不匹配或缺失时从 seed 复制；大改结构必须换 seed |
| `layout_family` | 做 deck 级版式多样性检查 | 相邻页重复时换阅读方向、主视觉位置或信息结构 |
| `visual_recipe` | 说明这页为什么值得走 SVG | 从 `svg-recipes.json` 选择，不能自造枚举 |
| `visual_design_contract` | 锁定视觉 thesis、composition archetype、motif 和必须落地的 evidence | 补齐合同，或改 renderer/component report 证明 evidence |
| `layout_boxes` | seed 派生的标题、正文、视觉、chart、footer 坐标 | 缺角色或 bbox 非正数时先修布局 |
| `content_budget` / `text_capacity` | seed 派生的文本容量预算 | 超量时删内容、拆页或换 seed |
| `text_budget_by_role` | seed 派生的 role 级文本预算 | 局部超量时删内容、拆页或换 seed，不用缩字/竖排硬塞 |
| `one_idea` / `key_message` | 单页只承载一个核心观点 | 先收敛消息，再替换 seed 内容 |
| `reserved_bands` | footer/source/legal/page mark 等保留区域 | body/callout 不得侵入 footer band |
| `footer_safe_zone` | footer band 的 allowed roles 和上方净距 | 只有 footer/source/legal/page mark 可以进入；正文、图表标签和图例必须离开 |
| `vertical_text_policy` | 竖排/旋转文本策略 | 默认 deny；只有 seed 明确允许的短装饰标签可使用 |
| `required_primitives` | 这页必须在 SVG source 中真实出现的 primitive | 至少覆盖 recipe required primitives |
| `svg_primitives` | 实际计划绘制的 primitive | 必须覆盖 `required_primitives` |
| `visual_intent` | SVG 视觉表达目的 | 写清楚 SVG-native 价值，不写空泛风格词 |
| `visual_focal_point` | 页面视觉焦点 | 用于判断布局是否围绕主视觉组织 |
| `xml_like_risk` | 退化成普通 XML 卡片页的风险 | 明确说明不用 SVG 会丢失什么结构 |
| `content_density_contract` | 信息密度硬契约 | 高密度页必须量化，例如 `dashboard >= 4 metrics` |
| `asset_contract` | 图片/素材来源与许可契约 | 无图写 `none_required`；Preview 网络图必须记录 `retrieval_query` / `source_url`，授权未确认可写 `license=preview_unverified` 且不阻断；正式交付必须补 source/license/local path 或替换 |
| `risk_flags` | 生成风险显式登记 | 无风险用空数组；不要省略字段 |
| `source_policy` | 缺数据/数字声明处理策略 | 防止自动扩写时编造业务数字 |

deck 级硬门禁：

- 用户未说明页数，或只说“一份 slide / 一份 PPT / 做个 slide / 生成一个 slide”这类模糊表达时，默认 `page_count=10`；不要仅因页数缺失而停下来追问。明确“一页 / 单页 / onepage / one slide / 只要封面”才按 `page_count=1`。默认 10 页必须包含 closing slide，并满足 10 页 deck 的 layout / renderer 多样性门禁。
- 8 页以上必须有明确 closing slide。
- 10 页以上至少 5 种 `layout_family`。
- 不允许连续 3 页使用同一 `layout_family`。
- 8 页以上至少 5 种 `visual_recipe` family。
- 10 页以上至少 5 种真实 `renderer_id`。
- 高密度页必须有量化 `content_density_contract`，不能只写“信息丰富”。

量化密度契约建议：

```text
matrix/table >= 6 cells
timeline >= 4 nodes
dashboard >= 4 metrics
flow >= 4 stages
risk_grid >= 4 items
comparison >= 4 rows or columns
```

如果 SVG source 无法满足对应数量，`svg_preflight.py` 会报 `plan_content_density_contract_not_met`，生成器必须补真实结构，不要只改字段名。

### 生成前强约束

以下规则来自实际 SVGlide live 生成、回读和修复经验，生成器必须先满足这些规则，再追求视觉复杂度。

- MUST: 默认使用 Lark Slides 当前回读画布 `960 x 540`，即 root 写成 `width="960" height="540" viewBox="0 0 960 540"`。不要默认用 `1280 x 720`，否则服务端回读后可能整页偏大并裁切。
- MUST: 主体元素使用安全区，建议 `safe = x:48 y:40 w:864 h:460`。除全屏背景外，文本、卡片、图表、标签、节点和图例都必须落在安全区内。
- MUST: 多页 deck 应包含明确的 closing slide。8 页以上讲解/汇报型 deck 不要把 roadmap / next-playbook 当作结束页；最后一页应包含 `closing`、`summary`、`Q&A`、`Thanks` 或下一步联系信息。
- MUST: `slides[]` 必须记录 `renderer_id`，且它要对应真实几何结构，而不是 `two-column-1` / `two-column-2` 这种名字变化。10 页以上 deck 至少 5 种 renderer/layout family；不得连续 3 页使用同一 renderer。
- MUST: `slides[]` 必须记录 `seed_id`、`layout_skeleton_id`、`layout_family`、`layout_boxes`、`content_budget` 或 `text_capacity`、`text_budget_by_role`、`reserved_bands.footer`、`footer_safe_zone`、`vertical_text_policy`、`one_idea` 或 `key_message`、`visual_recipe`、`visual_intent`、`visual_focal_point`、`visual_design_contract`、`required_primitives`、`svg_primitives`、`xml_like_risk`、`content_density_contract`、`risk_flags`、`source_policy`。`asset_contract` 应尽量记录；MVP 阶段缺失只 warning。没有 SVG-native recipe 的页面不应走 `slides +create-svg`，应改用普通 Slides XML 或重新选择 SVG recipe。
- MUST: `visual_recipe` 必须来自 catalog，且 `svg_primitives` 必须覆盖该 recipe 的 required primitives。`renderer_id` 不能替代 `visual_recipe`。
- MUST: `seed_id` 必须来自 `svg-seeds.json`，seed 的 `visual_recipe` / `layout_family` 必须和 plan 一致。`route_private` 只隐藏具体 private recipe，不跳过 seed/layout/budget 控制。
- MUST: seed skeleton 是版式合同，不是灵感参考。生成器必须继承 seed 的 `required_layout_box_roles`、`layout_skeleton_id`、`layout_boxes`、`text_budget_by_role`、`footer_safe_zone` 和 `vertical_text_policy`；内容放不下时删减、拆页或换 seed，不得放宽 seed budget 或自由重画骨架。
- MUST: 任何 footer/source/note/legal/page mark 文本必须落在 `reserved_bands.footer` 内；正文、callout、chart labels、图例、标签和解释文字不得压进 footer band，并应与 `footer_safe_zone` 顶部保持至少 `min_gap_above_px` 净距。背景和装饰可穿过 footer band，但不得承载关键文字。
- MUST: 默认禁止 `writing-mode`、`text-orientation`、竖排正文和 90° 旋转长文本；不要用竖排解决窄列或溢出。只有 seed 的 `vertical_text_policy` 明确允许时，才可用短标题、章节号或装饰性标签，并且必须通过 preview review。
- MUST: 标签、chip、badge、装饰块不得覆盖标题、正文、竖排说明或图表标签；如果需要强调，用独立 layout box 或扩大文本承载面，不要把标记压在可读文本上。
- MUST: 不要把可见内容写进 `display:none`、`visibility:hidden`、近零 opacity、`overflow:hidden`、`clip-path` 或 `mask` 裁切的 text box；`svg_preflight.py` 会报 `hidden_visible_text` 或 `clipped_visible_text`。
- MUST: 8 页以上 SVG deck 至少使用 5 种 visual recipe family；不能整套 deck 都是卡片、双栏或普通 dashboard。
- MUST: 高密度页必须声明 `density_structure` 和量化 `content_density_contract`，例如 `matrix/table >= 6 cells`、`timeline >= 4 nodes`、`dashboard >= 4 metrics`、`flow >= 4 stages`、`risk_grid >= 4 items`。只有“大标题 + 大图 + 2-3 个短 chip”不算高密度。
- MUST: 来源不足、附件缺失、用户未提供数据时，必须在 plan 中写 `source_status` 和 `source_policy`，并在页面上显式表达“待从附件补齐 / 来源缺失 / no numeric claims”。不要编造客户、排名、真实论文数据、金额、占比、链接、logo 或引用。
- MUST: `foreignObject` 文本样式使用显式 CSS：`font-size`、`font-weight`、`font-family`、`color`、`line-height`、`text-align`。不要用 `font:` shorthand 表达关键字号和加粗。
- MUST: 白色或接近白色的文字必须完整落在深色 shape 承载底上。标题、封面副标题、CTA、页脚等不能跨出深色底，压到浅色图片、白色蒙层或白底上；需要时扩大色块、加深色背板/遮罩，或改用深色文字。
- MUST: 圆形/椭圆节点只承载短标签，不承载解释句。节点内 `foreignObject` bbox 必须小于节点 bbox；微解释、指标、下一步和注释放到独立说明卡、图例、机制表或外侧 callout。
- MUST: 提交前和 live 回读后都检查边界和重叠：非背景元素不得越过 `960 x 540`，第 2/3 页等信息密集页必须额外检查 text bbox overlap。
- SHOULD: 如果本地预览使用更大画布，例如 `1280 x 720`，必须在输出给 `slides +create-svg` 前按比例换算为 `960 x 540`，而不是只改 root viewBox。

### 生成器实现约束与 Preflight

生成器必须先把高概率错误拦在本地，再调用 `lark-cli`。不要依赖 live 创建后的人工修补来发现基础问题。

实现约束：

- MUST: SVG 生成 helper 的返回类型保持一致。推荐统一返回 `string`，或统一返回 `string[]` 后在页面末尾 `flat().filter(Boolean).join("\n")`；不要混用 `...items.map(...).join("\n")`，这会把已拼好的 SVG 标签按字符展开，生成非法 XML。
- MUST: 所有组件都从稳定布局盒推导坐标，避免散点手调。文本、标签、图例、曲线端点和卡片内容应有明确的父盒和对齐规则。
- MUST: 生成脚本要先写 deck plan / asset list，再写页面；不能边补坐标边生成最终 SVG。
- MUST: 生成器要把 preflight 规则前移为本地 assert。写 SVG 前先由实际组件 manifest 反推出 `svg_primitives`，再检查 `visual_recipe` required primitives、`required_primitives`、`content_density_contract` 数量、主体 safe area、文本 bbox 和最小文本框高度；断言失败时修组件或布局，不要只改 `slide_plan.json` 字段。
- MUST: 高密度结构要由组件实际数量驱动，例如 `scorecard >= 4 metrics` 必须生成 4 个能被识别为 metric/bar/card 的元素；`timeline >= 4 nodes` 必须生成 4 个真实节点和标签；不要用文字描述冒充结构。
- MUST: 文本组件要按字号、行高和预估行数计算最小 `foreignObject` 高度。卡片、节点、脚注、图例的正文框不得出现 0、高度个位数或明显低于一行文字的 bbox。
- MUST: 主体文本、卡片、图表、标签、节点和图例必须落在 safe area；全画布背景、边缘承载底、图片遮罩和装饰边框可以超出 safe area，但应只承担背景/承载作用，不承载关键文本。
- MUST: 承载可见文字的卡片、callout、badge、panel 和 insight box 必须有 `text_surface_contract`，不能默认裸白底黑字。至少使用一种 style-preset 派生处理：tinted fill、accent rail、visible stroke、glass overlay、number/icon marker、深色背板或与背景共用的承载色。
- MUST: `titleBox` 是不可侵入区域。callout、badge、panel、connector、装饰线和图片标签与标题框底部至少保持 24px 视觉间距；如果标题是两行或大号字，优先扩大间距或移动卡片，而不是压缩标题。
- MUST: connector line/path 只连接到卡片、节点或图表边缘，不能穿过 title、中心文字、callout 文案或图例。若线条只是背景纹理，降低 opacity 并在 plan 中标为 decorative，不要让它承担 connector_flow。
- SHOULD: 对高风险页面使用更保守的留白：标题与图表标签至少相隔 24px，曲线端点标签不要压在标题/图例区域，卡片内文字与边框至少留 10-14px。
- SHOULD: 把每页的 `safe`、`titleBox`、`visualBox`、`textBox`、`calloutBox`、`connectorPath` 等布局盒保存为可检查数据，便于自动计算越界、重叠、标题压力和 connector 穿字。

推荐生成顺序：

```text
deck/page plan
-> layout boxes
-> components with emitted primitive manifest
-> generator asserts: recipe/primitives/density/text/safe-area
-> write SVG + slide_plan.json from the same manifest
-> svg_preflight.py --plan ...
-> dry-run / live create / readback
```

### 本地 HTML 预览（建议）

HTML 预览是生成阶段的轻量质检，不是 SVGlide 协议或 CLI API 的硬依赖。

- SHOULD: 生成 SVGlide deck 后、调用 `slides +create-svg` 前，生成一个本地 `preview.html`，把每页 SVG 按 16:9 画布嵌入，并展示页码、标题、`renderer_id` / `visual_recipe`、图片资产状态、preview-only 图片来源和明显 warning。
- SHOULD: 如果当前 agent、IDE 或浏览器工具支持打开本地文件，打开 `preview.html` 进行人工或截图式预览，优先检查：
  - 页面是否空白、明显裁切或整体偏大。
  - 标题、正文、图片和装饰元素是否重叠。
  - 白色/浅色文字是否压到浅色背景或图片亮部。
  - 相邻页面是否版式过度重复。
  - 信息密度是否明显不足，尤其是高密度页是否真的有 matrix/table/timeline/dashboard/flow/risk grid。
  - 结尾页是否存在。
  - 图片是否显示，是否有破图、空图片框、图片过少或 preview-only 来源未记录。
- SHOULD: 在最终产物目录记录 `preview.html` 路径；如果未生成或无法打开，说明原因，并继续执行 preflight / dry-run / readback。
- 在 project runner quality lane 中，`preview_lint` 是 hard gate：缺少
  `preview.html` 或出现高置信 objective lint error 时，必须在 `dry_run`
  前失败。手工排障路径仍可在无 preview 时继续 preflight、dry-run 和 readback，
  但不得进入 guarded live creation，也不得标记为 production/golden 交付。
- MUST NOT: 用 HTML 预览替代 `svg_preflight.py`、`slides +create-svg --dry-run` 或 live readback。HTML 预览主要提前发现审美、布局和素材问题；服务端转换后的字体、path bbox、图片 token 和部分 SVG 效果仍必须通过 readback 验证。

打开预览后必须按 [svg-aesthetic-review.md](svg-aesthetic-review.md) 做一次人工或截图式审查。重点看所有页面的标题区、装饰线、badge、文本框、图片框、safe area、重复版式和 SVG 视觉优势；如果多页出现同类问题，修生成规则后重新生成，不要只逐页微调坐标。

本地 preflight 必须在 `slides +create-svg` 前执行，失败即停：

- `python3 skills/lark-slides/scripts/svg_preflight.py --route-manifest skills/lark-slides/references/routes/create-svg/route.manifest.json --report-scope public --plan .lark-slides/plan/<deck-id>/slide_plan.json --input page-*.svg` 通过；如果脚本不可用，再退回 `xmllint --noout page-*.svg` 加人工检查。
- 生成脚本和 preflight 不得并行读写同一个 output 目录；必须等 SVG 文件全部写完后再跑 preflight，避免读到中间态导致误判。
- root 是 `width="960" height="540" viewBox="0 0 960 540"`。
- root / leaf `slide:role` 完整，所有 leaf 有几何必填属性。
- plan 中每页 `layout_family`、`visual_recipe`、`visual_intent`、`visual_focal_point`、`required_primitives`、`svg_primitives`、`xml_like_risk`、`content_density_contract`、`risk_flags`、`source_policy` 完整，且 recipe required primitives 能在对应 SVG source 中命中。`asset_contract` 在 MVP 阶段缺失只 warning；有条件时仍应补全。
- 禁止 SVG 退化成 XML-like 卡片页：如果页面基本只有 `rect + foreignObject`，且没有 path、gradient、image overlay、annotation、micro chart、icon、texture、spotlight、flow 等 SVG-native primitive，preflight 必须失败。
- 禁止零尺寸元素；文本框、图片、卡片和圆/椭圆必须有正向宽高，不能生成 `height="0"` 的隐藏说明。
- `<image opacity="...">` 或图片 style 里写 `opacity:` 在 MVP 阶段只 warning；当前转换链路不会稳定保留到 readback `<img>`。需要淡化图片时，优先把透明度预合成进 PNG/JPG，或在图片上方加半透明 `rect` 遮罩。
- 禁止白色/浅色文字跨出深色承载底；如果 preflight 报 `light_text_without_dark_backing`，优先扩大深色背景或加文本背板，不要只缩小字号。
- 禁止把解释文字塞进圆形/椭圆节点；如果 preflight 报 `node_text_overflow`，节点内只保留短标签，把说明迁移到旁边卡片、表格或图例。
- 警惕 `circle` / `ellipse` 的 `stroke-width`；当前转换链路可能只保留 border color 而丢失 width。关键圆环、节点外圈和粗描边用双层填充圆/椭圆模拟，或改成 path/rect。
- 禁止关键路线、闭环、流程连接、timeline rail 使用 `stroke-dasharray`；普通装饰虚线也会 warning。关键路线必须用显式短线段或小圆点 markers 组成，不要把虚线作为唯一视觉表达。
- 禁止 `font:` shorthand 和空图片框。MVP 阶段 http(s) / data URL 图片、未下载远程图片只 warning；正式交付和可见性要求高的 deck 仍应下载到本地并走 `@./path` 上传或使用 file token。
- 对尚未证明支持 image token 的 live lane，先用一页纯 SVG 和一页含 `@./assets/...` 的图片 SVG 分别 smoke；如果图片页上传成功但 `/slide` 失败，可以为线上发布生成单独的 `online-pure` SVG 目录，用 SVG-native 几何和渐变替代图片区域，但必须保留原图片预览版本并在交付说明里标注降级。
- 禁止 unsupported path command；`path d` 只含 `M/L/H/V/C/Q/Z`。
- 非背景元素不得越界；主体元素应在 safe area 内。
- 文本框做 bbox overlap 近似检查，尤其是目录、痛点、竞品表、案例图表和总结页。
- 图片资产文件存在、大小合理，或 http(s)/data URL 能在 preview 中显示。Preview 阶段来源/授权不完整只 warning，但必须用 `asset_contract.license=preview_unverified` 或 `risk_flags=["image_preview_only"]` 显式标记；正式交付再补齐来源/授权或替换。
- deck plan 通过 renderer 多样性、layout family 多样性、closing slide、高密度结构、资产契约、来源保护六类校验。

创建顺序：

```text
generate deck plan -> generate assets -> generate SVG files
-> optional preview.html and browser preview when supported
-> local preflight with --plan -> lark-cli slides +create-svg --dry-run
-> live create -> xml_presentations get readback
-> readback bbox / text overlap / closing slide checks
```

readback 不能省略。服务端会把 SVGlide 转成 Slides XML，文字 bbox、path bounds 和图片 token 可能和本地 SVG 预估不同；本地 preflight 负责拦住确定错误，readback 负责发现转换后的版式漂移。

### Deck 级密度规划

生成多页 SVG deck 前，先写 deck-level plan。页面类型只定义叙事职责，密度由 `deck_type`、受众、页面目的和节奏共同决定，不要把某个 page type 永久绑定为固定密度。

最小 plan schema：

```json
{
  "deck_type": "explain | decision | product | brand | technical | education | report",
  "audience": "who will read it",
  "goal": "what the deck should make the audience understand or decide",
  "density_strategy": "how low/medium/high density pages are distributed",
  "asset_strategy": "which query/topic-related web images should be searched and fetched, where they will be used, preview source/url/license risk, and production replacement plan if needed",
  "visual_rhythm": "how layout, imagery, charts, and text density vary across pages",
  "slides": [
    {
      "page": 1,
      "page_type": "cover",
      "density": "low",
      "density_mode": "visual-dense",
      "takeaway": "one sentence the audience should remember",
      "evidence": [],
      "visual_structure": "full-bleed image with title overlay",
      "layout_guardrails": ["large hero title", "no dense body copy"]
    }
  ]
}
```

常用 `page_type`：

```text
cover, opener, agenda, section-divider, context, problem, opportunity,
executive-summary, content, data, comparison, process, case-study, demo,
architecture, system, roadmap, timeline, decision, recommendation,
risk, tradeoff, summary, closing, q-and-a, appendix
```

密度规则：

- MUST: 每页都要有明确 `takeaway`，即使是封面、分隔页和结束页。
- MUST: 每个 SVG deck 默认都要包含真实图片资产，不要全程只用矢量 shape 冒充“配图”。Preview 阶段应优先根据用户 query、deck 标题和页面主题去网络检索并拉取强相关图片，再补充产品截图、网页截图、场景图、材质纹理、图鉴图和 AI 生成图增强视觉冲击；展示型、宣传型、产品型、品牌型和案例型 deck 至少包含 3 处图片使用，其中至少 1 页使用全幅或半出血图片主视觉。
- MUST: 高密度页必须有承载信息的视觉结构，例如矩阵、流程、地图、时间线、标注图、案例卡或手绘微图表，不能只有装饰图形。
- MUST: 生成器必须先扩写页面“结构信息”，再绘制 SVG。信息密度不足时，优先补结构化解释层，例如编号标签、微解释、比较维度、轴线、图例、阶段、来源状态、下一步，而不是把同一句话换写成多个 chip。
- MUST: 流程页、闭环页、机制页和产品体系页不能只有“4 个圆节点 + 短标签”。至少补 1 层结构化信息，例如机制表、KPI 标签、触发条件、责任/频率、输入输出、风险提示或下一步动作。
- SHOULD: 高密度内容页通常包含 3-6 个信息块和若干可读细节，但 executive brief、品牌页、产品视觉页、短汇报可以降低数量，只保留强结论、关键证据和视觉锚点。
- SHOULD NOT: 不要让所有高密度页长成同一种“主结论 + 3-6 卡片 + 3 个 callout”模板。
- MUST NOT: 缺少素材或数据时不要编造数字、客户名、logo、排名、引用或真实案例；用 qualitative label、relative scale、hypothesis/assumption 标注兜底。

### 结构示例

8-10 页讲解型 deck 可参考这个节奏，但不要把它当成唯一模板；如果 deck 已经包含 roadmap / playbook，仍建议再补一页 closing：

```text
cover -> opener/context -> agenda/map -> content -> data/comparison
-> process/system breakdown -> case-study/demo -> content/implications
-> summary -> closing
```

5 页决策汇报优先前置结论：

```text
cover -> executive-summary -> options/comparison -> recommendation/risk -> next steps
```

6 页产品/品牌 deck 可以强化视觉叙事：

```text
cover -> value proposition -> user scenario -> feature map/demo
-> proof/roadmap -> closing
```

边界处理：

- 3-5 页短 deck 可以省略 agenda，把 summary 并入 closing。
- 15 页以上长 deck 应增加 section-divider 或 recap，避免连续高密度阅读疲劳。
- 技术方案要混合 architecture、process、tradeoff、risk，不要连续堆文字。
- 教学讲解要前置 context / concept map，逐步增加密度。
- 素材不足时，用抽象视觉系统、定性矩阵、annotated wireframe、scenario card 兜底，并标明假设。

### 先定义布局盒

不要直接手写散点坐标。每页先定义稳定布局盒，再把文字、图形、图例和图片放进盒内：

```text
page = 960 x 540
safe = x:48 y:40 w:864 h:460
titleBox = x:54 y:52 w:600 h:96
visualBox = x:516 y:176 w:350 h:260
notesGrid = x:54 y:430 w:760 h:48
```

生成后检查：

- 关键元素必须在 safe area 内。
- 同组元素使用同一个父盒推导坐标。
- 图例、标签、指标不能浮在不上不下的位置，必须相对主视觉左/右/下边对齐。
- 如果页面有圆、节点、卡片或框体，内容中心应和外框中心基本一致，不靠手调 `x + 10`、`y + 10` 维持观感。
- 不要把 1280x720 的坐标直接提交给 `slides +create-svg`。当前服务端回读画布通常是 960x540，错误坐标系会表现为每页偏大、右侧卡片裁切、底部标签越界。

### 文本安全余量

`foreignObject` 文本优先使用显式 CSS。为了服务端转换后保留样式，字号、加粗、颜色、行距和对齐必须写成独立属性；不要把关键样式藏在 `font:` shorthand 或只写在复杂外层 wrapper 上：

```xml
<foreignObject slide:role="shape" slide:shape-type="text" x="54" y="62" width="600" height="42">
  <div xmlns="http://www.w3.org/1999/xhtml"
       style="margin:0;padding:0;font-size:30px;font-weight:900;font-family:Arial,'Source Han Sans SC';color:#111827;line-height:1.12;text-align:left;letter-spacing:0;">
    关键结论：增长来自三件事
  </div>
</foreignObject>
```

中文和混排字体要留安全高度：

- subtitle 不小于 64px。
- note / chip 单行文本盒不小于 20px。
- 小型标签文本盒不小于 14px。
- 多行文字要按行高预估高度，再额外留 8-12px。
- 右侧图例或矩阵格里的文字不得贴边，水平 padding 至少 10-14px。
- 白色/浅色文字的 bbox 必须完全落在深色 rect/card/overlay 内；封面标题如果跨出色块，应优先扩大色块或改成深色字，不要让白字压在浅色图片或白色蒙层上。
- 圆形/椭圆节点内只放短标签，解释文字移动到节点外的 callout、legend 或机制表；不要让圆内文本框宽度超过圆形直径。
- 服务端支持 `foreignObject` 内的 `<br />`。为了本地预览和标题排版稳定，标题/大段文本优先使用多个块级 `div` 或 `p` 控制行高，不要只靠 `<br />` 调整复杂布局。
- 如果需要垂直居中，优先通过更准确的文本框高度、段落行高和 y 坐标解决；布局 wrapper 可以使用，但实际文字节点仍要带显式 `font-size` / `font-weight` / `color`。

### 文本承载面美学

文本框不是视觉主元素，但承载文字的 surface 是页面层级的一部分。生成器必须先决定 surface 类型，再放置文字：

```json
{
  "text_surface_contract": {
    "surface_kind": "accent_rail_card | tinted_panel | glass_overlay | dark_backing | label_chip | metric_tile",
    "min_gap_to_title": 24,
    "padding": {"x": 14, "y": 12},
    "allow_plain_white_panel": false
  }
}
```

- `accent_rail_card`: 卡片左侧或顶部有 6-10px 强调条，适合 callout、洞察点和团队分工。
- `tinted_panel`: 使用 preset 派生浅底和细描边，适合普通信息组；不要用纯白裸框。
- `glass_overlay`: 图片上方使用半透明浅底或深底，并与图片遮罩同色系。
- `dark_backing`: 白字必须完整落在深色承载底内。
- `label_chip`: 仅承载短标签，避免承载解释句。
- `metric_tile`: KPI 数字可用高对比底色，但仍要有角色色、分隔线或图形关系。

`svg_preflight.py` 会把以下问题作为 error：`plain_white_text_panel`、`title_surface_pressure`、`connector_crosses_text`。这些错误必须修 source SVG / layout boxes，不能只在 plan 里改字段。

### 几何与 path 安全线

leaf 几何属性必须写数字或 `px`，不要生成百分比、`em/rem`、`calc(...)`：

```xml
<rect slide:role="shape" x="80" y="96" width="420px" height="240px" />
```

`path d` 只生成 `M/L/H/V/C/Q/Z` 命令。不要生成 `A`、`S`、`T` 等命令；需要圆角或弧线时，用 `C` / `Q` 近似，或改用 `circle` / `ellipse` / `rect`。

Transform 参数同样使用数字或 `px`。不要写 `translate(10%, 20%)`，先在布局盒里换算成绝对坐标。

### 版式节奏

同一 deck 不能连续复用同一种“暗色网格 + 左文案 + 右卡片 + 底部 chips”。10 页左右的讲解型 deck 至少混用这些结构：

- 封面 / 全幅图片背景页。
- 目录矩阵页或行业地图页。
- 左文右图 / 左图右文双栏页。
- 全幅路线图或时间线页。
- 2x2 / 2x4 总结矩阵页。
- 数据仪表页、流程页、对比页或案例页。

相邻页面至少改变一个主结构维度：主视觉位置、网格列数、图片用法、文本密度或阅读方向。

### 图片使用与 Preview Image Mode

默认必须规划和使用图片资产。Preview 阶段的目标是验证 SVGlide 的视觉表达上限，版权/授权不作为阻断条件；不要因为 license 未确认就退回纯矢量或低信息卡片页。推荐先从用户 query、deck 标题、章节标题和页面 takeaway 生成 2-5 个图片检索词，去网络检索并拉取主题强相关图片；再补充网页截图、产品截图、图库图、新闻/历史/艺术/科普图片、材质纹理或 AI 生成图做占位视觉。必须在 plan / README 里记录 `retrieval_query`、来源 URL，或标记 `license=preview_unverified`，并避免明显不适当素材、敏感肖像和会造成商业背书误导的 logo/商标。正式交付时，再统一替换为用户提供、公司/项目自有、明确可商用授权图库，或授权条件清晰的 AI 生成资产。

最稳流程仍然是先下载或生成到本地，再写成本地占位符：

```xml
<image slide:role="image" href="@./assets/hero.jpg" x="0" y="0" width="960" height="540" />
```

推荐的网络拉图流程：

1. 从用户 query、deck title、page takeaway、章节标题中提取 `retrieval_query`，优先使用具体名词、场景、人物、作品、产品、地点、历史事件或学科对象，避免只搜抽象词。
2. 对封面、章节过渡页、案例页、教学解释页和产品/品牌页优先执行网络图片搜索或网页截图获取，选择和主题直接相关的真实图片，不用无关风景图凑数。
3. 能下载时先保存到 `assets/` 并用 `@./assets/...` 引用；来不及下载时可以先保留 http(s) URL 进入 preview，但 live/readback 后必须确认可见。
4. 每张图在 `asset_contract` 记录 `retrieval_query`、`source_type`、`source_url`、`retrieved_at`、`license=preview_unverified`、`usage_page`、`replacement_required=true`。
5. 网络不可用或无法找到强相关图片时，才退回 AI 生成图、程序化纹理或纯 SVG 视觉，并在 `risk_flags` 写 `network_image_fetch_unavailable`。

图片不只用于局部卡片背景，也可以作为整页背景、半出血主视觉、材质纹理、案例示例、产品截图、数据仪表截图、网页/应用界面截图、人物/场景图、图鉴封面、历史/艺术/科学素材或产品细节局部。作为整页背景时，必须叠加半透明遮罩或暗角，保证标题和正文对比度。

图片数量与用法建议：

- MUST: 在 `asset_strategy` 或产物 README 中记录图片检索词、图片来源、授权/许可类型、下载 URL 或生成方式；Preview 阶段无法确认授权时写 `license=preview_unverified` 和 `replacement_required=true`，preflight 不阻断，最终交付应替换为可授权资产。
- MUST: 5 页以上 deck 至少使用 2 张真实图片；8 页以上 deck 至少使用 4 张；宣传/产品/品牌/案例/教学型 deck 至少使用 5 张或至少 40% 页面含图片。
- MUST: 封面优先使用图片或图片+抽象图形混合主视觉，不要只用网格、光效和几何背景。
- MUST: 案例页优先使用行业场景图、产品截图、仪表盘截图或真实质感背景，并叠加数据 callout。
- MUST: 同一 deck 中混用全幅背景、半出血图片、卡片图、纹理/材质背景、标注型截图、图鉴式小图和局部裁切特写，避免所有图片都只是小卡片背景。
- SHOULD: 对教育、历史、艺术、医学、产品讲解等主题，优先用图片建立具象认知：人物、器物、场景、局部特写、对比图、流程截图、资料封面或时间背景图。
- MUST NOT: 保留空图片框或破图。Preview/MVP 阶段允许 http(s) 外链或 data URL 先进入 preflight warning，但 live/readback 后必须确认可见；正式交付应替换为本地 `@./path` 或 file token。

Preview 阶段优先使用这些来源来快速获得丰富视觉；正式交付时再逐图确认授权、署名和替换计划：

| Source | 适合用途 | Preview 规则 |
|--------|----------|------|
| Web image search / topic query | 和用户 query、页面主题、作品/人物/地点/产品直接相关的真实图片 | 优先使用；记录 `retrieval_query`、图片页 URL 和 `preview_unverified`，正式交付再确认或替换 |
| Unsplash / Pexels / Pixabay | 高质量摄影、封面背景、场景图 | 结合主题 query 检索；记录图片页 URL；license 可先写 `preview_unverified`，正式交付再确认 |
| Openverse / Wikimedia Commons | 百科、历史、技术、公共领域素材 | 记录单图 URL 和作者/页面；preview 可先用，正式交付补 license / attribution |
| The Met / Smithsonian / NASA Open Access | 艺术、科学、历史、航天视觉 | 记录条目 URL；preview 可先用，正式交付确认 Open Access / 第三方权利 |
| 官网 / 产品页 / 新闻图 / 搜索图 | 产品截图、竞品页、事件背景、真实语境 | Preview 可作为视觉占位；必须标记 `license=preview_unverified`，正式交付替换或删去 |
| AI 生成图 / 程序化纹理 | 抽象背景、材质、概念图 | 记录生成方式和提示词摘要；正式交付确认模型/平台授权 |

素材清单建议字段：

```json
{
  "local_path": "./assets/hero.jpg",
  "source": "Unsplash",
  "retrieval_query": "Beethoven Symphony No. 5 concert hall orchestra",
  "source_url": "https://...",
  "retrieved_at": "2026-06-08",
  "license": "preview_unverified",
  "commercial_use": "unknown_in_preview",
  "replacement_required": true,
  "attribution_required": false,
  "usage_page": 1,
  "notes": "Preview-only visual placeholder; replace or verify license before production delivery"
}
```

### 信息密度与图鉴感

短 note 不要占一个很宽胶囊。优先写成“编号/标签 + 主句 + 微解释/数值”：

```text
03 GRID ENERGY 86% | storage demand peaks before grid balancing
```

内容页可以用三种方式提高密度，不要把高密度等同于堆文字：

- `text-dense`: 多解释、多证据、多注释，适合背景分析和概念讲解。
- `chart-dense`: SVG shape 手绘矩阵、流程、时间线、微柱状、雷达、散点、标尺；如果需要原生 bar/line chart，使用 root chart spec marker；不要把外部图表截图当成唯一方案。
- `visual-dense`: 高级视觉图案或图片上叠加标注层、数据 callout、局部标签、对比线和图例。

视觉区要补足可读细节，避免只有装饰符号：

- 局部标注、刻度、坐标轴、图例。
- 行业标签、材料纹理、指标卡。
- 路线节点、连接线、层级分区。
- 流程/闭环图旁边补机制表或说明卡，例如“触发条件 / 运营动作 / 衡量指标”，不要把说明句塞进圆形节点内部。
- 小型表格、雷达/柱状/散点等微图表。

### 转换稳定性经验

这些规则来自 live 创建后对比 source SVG 与 readback XML 的结果，属于生成侧必须规避的转换差异：

- `image opacity` 不稳定：本地 SVG 里的 `<image opacity="0.18">` / `<image opacity="0.22">` 可能会在 readback `<img>` 中丢失透明度。MVP preflight 只 warning；生成器仍应把淡化效果烘焙进图片本身，或使用半透明 shape 遮罩。
- shape opacity 稳定：`rect`、`circle`、`path` 等 shape 的 `opacity` 会转换为 XML `alpha`，可用于蒙层、暗角和装饰层。
- circle / ellipse stroke width 不稳定：圆形/椭圆描边可能只保留颜色、不保留宽度。关键外圈使用“外层有色圆 + 内层背景圆”的双 shape ring，或用 path 绘制；不要用单个 stroked circle 承载关键视觉。
- dashed stroke 不稳定：`stroke-dasharray` 可能降级，尤其是自定义 path 的虚线闭环。关键路线用短 line segment 或 filled dot markers 手工排布；普通装饰虚线也要经 readback 复核。
- path 会转换为 `type="custom"` 并做 bbox 内坐标归一化，这是预期行为；只要 readback bbox 和视觉位置正确，不算差异。
- 字体会被转换为服务端支持字体，例如 `Noto Sans` / `思源黑体`，因此生成阶段要给 `foreignObject` 留足高度，不要按浏览器本地字体做极限排版。
- image token 支持可能随 live lane 漂移：如果 readback 前创建失败，先区分“图片上传失败”和“上传后 `/slide` 失败”。后者是目标 lane 的 token 解析/权限问题，短期发布可改用独立 online-pure 版本；不要把 authoring preview 里的真实图片直接删掉。

### 生成后检查

生成脚本或人工复核必须检查：

- 是否已执行本地 preflight，且所有 SVG 通过 XML、协议、资产、bbox 和文本重叠检查。
- 是否已执行 `slides +create-svg --dry-run`，确认请求链路是创建 presentation + 按页追加 SVG。
- 如果使用 `@./assets/...`，dry-run 是否展示预期的 `medias/upload_all` 和 transport metadata；live 失败时是否已经用纯 SVG 页和图片页隔离出 lane 问题。
- live 创建后是否已用 `xml_presentations get` 读回，重新检查画布、页数、越界、文本重叠和 closing slide。
- root / leaf role 是否完整。
- 每个 leaf 是否有 [svg-protocol.md](svg-protocol.md) 中列出的几何必填属性。
- 几何属性和 transform 参数是否只使用数字或 `px`。
- `path d` 是否只包含 `M/L/H/V/C/Q/Z`。
- 文本是否截断、重叠或贴边。
- 内容是否在 safe area 内，关键图例和外框是否对齐。
- 相邻页面是否明显换版式。
- 每页是否有明确 takeaway；高密度页的视觉结构是否承载信息，而不只是装饰。
- 内容页是否避免了“大标题 + 大图 + 2-3 个短 chip”的低信息布局。
- 自称数据、排名、客户、引用、logo 或案例时，是否有来源；没有来源时是否改为定性或假设表达。
- 图片是否足够丰富并可见；如果 Preview/MVP 阶段暂时保留 http(s) / data URL 或 `preview_unverified` 来源，要记录 warning、确认 live/readback 可见，并在正式交付前列出替换项。

验证记录建议写回 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json` 的 `readback_verification` 字段，并在最终回复中简述：

```text
验证记录：
- Preflight：N/N SVG 通过 root/role/geometry/path/image/bbox 检查。
- Dry-run：已确认 create presentation + N 次 /slide。
- Readback：实际页数 N / 预期 N；未发现空白页、破图或缺失 closing slide。
- 版式：检查 safe area、文本重叠、越界和相邻页版式变化。
- 资产：Preview 阶段优先丰富图片和 readback 可见性；若保留 http(s)/data URL 或 `preview_unverified` 来源，必须记录 warning。正式交付再替换为本地 @path 自动上传或 file token，并补齐授权。
```

## 错误处理

任一页失败时，错误会包含：

- `xml_presentation_id`
- 失败页序号
- 已成功页数
- 已创建的 `slide_ids`

如果服务端 detail 带有 `SVGLIDE_ERROR_JSON:` marker，CLI 会提取并在错误中展示 `svglide_error`，用于定位 `type`、`page_index`、`tag_name`、`element_id`、`role` 和 `hint`。

失败后不要假设没有创建任何资源。先把恢复状态写回 plan 的 `recovery` 字段：

```json
{
  "xml_presentation_id": "slides...",
  "failed_page": 3,
  "failed_svg_file": ".lark-slides/plan/<deck-id>/pages/page-003.svg",
  "successful_slide_ids": ["abc", "def"],
  "svglide_error": {"type": "svg_validation_error", "tag_name": "foreignObject"},
  "next_action": "fix source SVG and rerun preflight before retry"
}
```

恢复顺序：

1. 本地 preflight 已失败：修对应 SVG 文件，不要调用 live API。
2. live 添加页失败且带 `svglide_error`：按 `type` / `tag_name` / `hint` 收敛 SVG 子集，例如降级复杂 filter、path、CSS 或文本结构。
3. plain XML 在同一路由成功但 SVG 失败：优先确认目标 server lane 是否部署了 SVGlide parser，不要盲目重写整套 deck。
4. SVG 通过本地 preflight 且失败在第 1 页，服务端只返回 generic `nodeServer invalid param`：优先检查 `lark-cli` 环境、代理和 PPE/BOE lane 是否命中目标 slide server。不要先把已通过协议校验的 deck 改回低质量 SVG。
5. 已创建 presentation 或部分页面时，默认保留现场并回读确认；是否删除空 presentation 必须单独由用户确认。

### 编辑已创建的 SVG deck

SVG deck 后续编辑走双轨，不承诺 source SVG id 能稳定映射到 readback XML block id：

| 修改类型 | 推荐路径 | 说明 |
|----------|----------|------|
| 小改标题、文本、图片或坐标 | `xml_presentation.slide.get` 读回 XML -> 找当前 block_id -> `slides +replace-slide` | 使用转换后的 XML 做块级编辑，页序和 slide_id 不变 |
| 大幅换版式、重画图表、调整视觉系统 | 修改 source SVG -> 重新 preflight -> 重新创建或替换目标页 | 保持 SVG 的视觉表达优势，避免在转换后 XML 上手搓复杂 SVG 结构 |
| 无法定位 block_id 或映射不可信 | 回 source SVG 修改 | 不生成 `edit-map.json`，除非服务端或转换结果能证明 source id 可稳定保留 |

小改前必须重新 `slide.get` 拿最新 block id 和 revision；大改后必须更新同一个 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`，保持 plan、SVG 文件、创建结果和验证记录一致。
