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

不适用：

- 你只有普通 SVG，且没有 `slide:role` 协议标记。
- 复杂普通 SVG 不能直接提交；需要把实际可渲染元素标成 SVGlide role。`g` / 嵌套 `svg` 容器可以保留，但不能代替子元素 role。
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

预上传资源可用 `--assets`：

```json
{
  "@./hero.png": "boxcn..."
}
```

## 生成质量规则

这些规则用于生成阶段主动规避服务端降级、近似和泛化错误。几何数值、path 命令、role/必填属性、图片 href 等基础约束已由 CLI 强校验；版式、美观和文本溢出仍需要生成器或人工复核。

### 生成前强约束

以下规则来自实际 SVGlide live 生成、回读和修复经验，生成器必须先满足这些规则，再追求视觉复杂度。

- MUST: 默认使用 Lark Slides 当前回读画布 `960 x 540`，即 root 写成 `width="960" height="540" viewBox="0 0 960 540"`。不要默认用 `1280 x 720`，否则服务端回读后可能整页偏大并裁切。
- MUST: 主体元素使用安全区，建议 `safe = x:48 y:40 w:864 h:460`。除全屏背景外，文本、卡片、图表、标签、节点和图例都必须落在安全区内。
- MUST: 多页 deck 应包含明确的 closing slide。8 页以上讲解/汇报型 deck 不要把 roadmap / next-playbook 当作结束页；最后一页应包含 `closing`、`summary`、`Q&A`、`Thanks` 或下一步联系信息。
- MUST: `foreignObject` 文本样式使用显式 CSS：`font-size`、`font-weight`、`font-family`、`color`、`line-height`、`text-align`。不要用 `font:` shorthand 表达关键字号和加粗。
- MUST: 提交前和 live 回读后都检查边界和重叠：非背景元素不得越过 `960 x 540`，第 2/3 页等信息密集页必须额外检查 text bbox overlap。
- SHOULD: 如果本地预览使用更大画布，例如 `1280 x 720`，必须在输出给 `slides +create-svg` 前按比例换算为 `960 x 540`，而不是只改 root viewBox。

### Deck 级密度规划

生成多页 SVG deck 前，先写 deck-level plan。页面类型只定义叙事职责，密度由 `deck_type`、受众、页面目的和节奏共同决定，不要把某个 page type 永久绑定为固定密度。

最小 plan schema：

```json
{
  "deck_type": "explain | decision | product | brand | technical | education | report",
  "audience": "who will read it",
  "goal": "what the deck should make the audience understand or decide",
  "density_strategy": "how low/medium/high density pages are distributed",
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
- MUST: 高密度页必须有承载信息的视觉结构，例如矩阵、流程、地图、时间线、标注图、案例卡或手绘微图表，不能只有装饰图形。
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

`foreignObject` 文本优先使用显式 CSS。为了服务端转换到 SXSD/XML 后保留样式，字号、加粗、颜色、行距和对齐必须写成独立属性；不要把关键样式藏在 `font:` shorthand 或只写在复杂外层 wrapper 上：

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
- 服务端支持 `foreignObject` 内的 `<br />`。为了本地预览和标题排版稳定，标题/大段文本优先使用多个块级 `div` 或 `p` 控制行高，不要只靠 `<br />` 调整复杂布局。
- 如果需要垂直居中，优先通过更准确的文本框高度、段落行高和 y 坐标解决；布局 wrapper 可以使用，但实际文字节点仍要带显式 `font-size` / `font-weight` / `color`。

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

### 图片使用

可以使用 Unsplash 等免版权图库，但不能把远程 URL 直接写进 SVG。正确流程是先下载到本地，再写成本地占位符：

```xml
<image slide:role="image" href="@./assets/hero.jpg" x="0" y="0" width="960" height="540" />
```

图片不只用于局部卡片背景，也可以作为整页背景、半出血主视觉、材质纹理、案例示例或图鉴封面。作为整页背景时，必须叠加半透明遮罩或暗角，保证标题和正文对比度。

### 信息密度与图鉴感

短 note 不要占一个很宽胶囊。优先写成“编号/标签 + 主句 + 微解释/数值”：

```text
03 GRID ENERGY 86% | storage demand peaks before grid balancing
```

内容页可以用三种方式提高密度，不要把高密度等同于堆文字：

- `text-dense`: 多解释、多证据、多注释，适合背景分析和概念讲解。
- `chart-dense`: SVG shape 手绘矩阵、流程、时间线、微柱状、雷达、散点、标尺；不要默认依赖 Slides 原生 chart，也不要把外部图表截图当成唯一方案。
- `visual-dense`: 高级视觉图案或图片上叠加标注层、数据 callout、局部标签、对比线和图例。

视觉区要补足可读细节，避免只有装饰符号：

- 局部标注、刻度、坐标轴、图例。
- 行业标签、材料纹理、指标卡。
- 路线节点、连接线、层级分区。
- 小型表格、雷达/柱状/散点等微图表。

### 生成后检查

生成脚本或人工复核必须检查：

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
- 图片是否已变成本地 `@./path` 或 file token，不能保留 http(s) / data URL。

## 错误处理

任一页失败时，错误会包含：

- `xml_presentation_id`
- 失败页序号
- 已成功页数
- 已创建的 `slide_ids`

如果服务端 detail 带有 `SVGLIDE_ERROR_JSON:` marker，CLI 会提取并在错误中展示 `svglide_error`，用于定位 `type`、`page_index`、`tag_name`、`element_id`、`role` 和 `hint`。
