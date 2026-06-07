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

### 与现有规划层对齐

SVG 创建不使用单独的规划目录。新建或大幅改写 SVG deck 时，仍然复用 [planning-layer.md](planning-layer.md) 规定的 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`，不要另建 `.lark-slides/svg-plan` 或只保留散落的 `.svg` 文件。

在通用 plan 字段基础上，SVG deck 还应补充这些 SVG 专属字段：

```json
{
  "output_mode": "svglide-svg",
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
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
    "command": "python3 skills/lark-slides/scripts/svg_preflight.py --input .lark-slides/plan/<deck-id>/pages/page-001.svg",
    "status": "pending"
  },
  "readback_verification": {
    "status": "pending",
    "checks": ["page_count", "blank_page", "canvas_bounds", "text_overlap", "asset_tokens", "closing_slide"]
  }
}
```

模板也复用现有 `template_tool.py search -> summarize -> extract` 路由。模板摘要只用于选择主题、页面流、视觉节奏和布局骨架；生成 SVG 时要把模板结构翻译成 SVG layout boxes / visual recipes，不要照搬模板 XML，也不要读取完整模板 XML。

### 生成前强约束

以下规则来自实际 SVGlide live 生成、回读和修复经验，生成器必须先满足这些规则，再追求视觉复杂度。

- MUST: 默认使用 Lark Slides 当前回读画布 `960 x 540`，即 root 写成 `width="960" height="540" viewBox="0 0 960 540"`。不要默认用 `1280 x 720`，否则服务端回读后可能整页偏大并裁切。
- MUST: 主体元素使用安全区，建议 `safe = x:48 y:40 w:864 h:460`。除全屏背景外，文本、卡片、图表、标签、节点和图例都必须落在安全区内。
- MUST: 多页 deck 应包含明确的 closing slide。8 页以上讲解/汇报型 deck 不要把 roadmap / next-playbook 当作结束页；最后一页应包含 `closing`、`summary`、`Q&A`、`Thanks` 或下一步联系信息。
- MUST: `foreignObject` 文本样式使用显式 CSS：`font-size`、`font-weight`、`font-family`、`color`、`line-height`、`text-align`。不要用 `font:` shorthand 表达关键字号和加粗。
- MUST: 提交前和 live 回读后都检查边界和重叠：非背景元素不得越过 `960 x 540`，第 2/3 页等信息密集页必须额外检查 text bbox overlap。
- SHOULD: 如果本地预览使用更大画布，例如 `1280 x 720`，必须在输出给 `slides +create-svg` 前按比例换算为 `960 x 540`，而不是只改 root viewBox。

### 生成器实现约束与 Preflight

生成器必须先把高概率错误拦在本地，再调用 `lark-cli`。不要依赖 live 创建后的人工修补来发现基础问题。

实现约束：

- MUST: SVG 生成 helper 的返回类型保持一致。推荐统一返回 `string`，或统一返回 `string[]` 后在页面末尾 `flat().filter(Boolean).join("\n")`；不要混用 `...items.map(...).join("\n")`，这会把已拼好的 SVG 标签按字符展开，生成非法 XML。
- MUST: 所有组件都从稳定布局盒推导坐标，避免散点手调。文本、标签、图例、曲线端点和卡片内容应有明确的父盒和对齐规则。
- MUST: 生成脚本要先写 deck plan / asset list，再写页面；不能边补坐标边生成最终 SVG。
- SHOULD: 对高风险页面使用更保守的留白：标题与图表标签至少相隔 24px，曲线端点标签不要压在标题/图例区域，卡片内文字与边框至少留 10-14px。
- SHOULD: 把每页的 `safe`、`titleBox`、`visualBox`、`textBox` 等布局盒保存为可检查数据，便于自动计算越界和重叠。

本地 preflight 必须在 `slides +create-svg` 前执行，失败即停：

- `python3 skills/lark-slides/scripts/svg_preflight.py --input page-*.svg` 通过；如果脚本不可用，再退回 `xmllint --noout page-*.svg` 加人工检查。
- root 是 `width="960" height="540" viewBox="0 0 960 540"`。
- root / leaf `slide:role` 完整，所有 leaf 有几何必填属性。
- 禁止 `font:` shorthand、http(s) / data URL 图片、未下载的远程图片、空图片框。
- 禁止 unsupported path command；`path d` 只含 `M/L/H/V/C/Q/Z`。
- 非背景元素不得越界；主体元素应在 safe area 内。
- 文本框做 bbox overlap 近似检查，尤其是目录、痛点、竞品表、案例图表和总结页。
- 图片资产文件存在、大小合理、授权来源清单完整。

创建顺序：

```text
generate deck plan -> generate assets -> generate SVG files
-> local preflight -> lark-cli slides +create-svg --dry-run
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
  "asset_strategy": "which real images are needed, where they will be used, copyright/license source, and fallback if unavailable",
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
- MUST: 每个 SVG deck 默认都要包含真实图片资产，不要全程只用矢量 shape 冒充“配图”。展示型、宣传型、产品型、品牌型和案例型 deck 至少包含 3 处图片使用，其中至少 1 页使用全幅或半出血图片主视觉。
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

默认必须规划和使用图片资产，并规避版权风险。图片必须来自用户提供、公司/项目自有、明确可商用授权图库，或授权条件清晰的 AI 生成资产；不要使用版权状态不明的图片、logo、截图、新闻配图、竞品官网图或搜索引擎随手抓取的素材。正确流程是先下载或生成到本地，再写成本地占位符：

```xml
<image slide:role="image" href="@./assets/hero.jpg" x="0" y="0" width="960" height="540" />
```

图片不只用于局部卡片背景，也可以作为整页背景、半出血主视觉、材质纹理、案例示例、产品截图、数据仪表截图或图鉴封面。作为整页背景时，必须叠加半透明遮罩或暗角，保证标题和正文对比度。

图片数量与用法建议：

- MUST: 在 `asset_strategy` 或产物 README 中记录图片来源、授权/许可类型、下载 URL 或生成方式；无法确认授权时不得使用。
- MUST: 5 页以上 deck 至少使用 1 张真实图片；8 页以上 deck 至少使用 2 张；宣传/产品/品牌/案例型 deck 至少使用 3 张。
- MUST: 封面优先使用图片或图片+抽象图形混合主视觉，不要只用网格、光效和几何背景。
- MUST: 案例页优先使用行业场景图、产品截图、仪表盘截图或真实质感背景，并叠加数据 callout。
- SHOULD: 同一 deck 中混用全幅背景、半出血图片、卡片图、纹理/材质背景和标注型截图，避免所有图片都只是小卡片背景。
- MUST NOT: 保留空图片框、破图、http(s) 外链或 data URL。素材不可用时要重新获取/生成，或在最终说明中明确为什么退回矢量。

优先使用这些来源，但每张图仍必须检查并记录具体页面上的授权信息：

| Source | 适合用途 | 规则 |
|--------|----------|------|
| Unsplash | 高质量摄影、封面背景、场景图 | 可商用图库；记录图片页 URL 和 license |
| Pexels | 商务、科技、生活类配图 | 可商用图库；记录图片页 URL 和 license |
| Pixabay | 图片、插画、视频、音频 | 可商用图库；避开人物/品牌/商标误导 |
| Openverse | CC / Public Domain 搜索 | 每张图 license 不同；按单图要求署名 |
| Wikimedia Commons | 百科、历史、技术、公共领域素材 | 每张图 license 不同；常见需要署名 |
| The Met Open Access | 艺术品、历史图像、文化视觉 | 仅使用 Open Access / CC0 条目 |
| Smithsonian Open Access | 博物馆、科学、历史、2D/3D 资产 | 仅使用 Open Access / CC0 条目 |
| NASA Image and Video Library | 太空、科技、地球、航天视觉 | 避开 NASA 标识商业背书、人物肖像和第三方权利 |

素材清单建议字段：

```json
{
  "local_path": "./assets/hero.jpg",
  "source": "Unsplash",
  "source_url": "https://...",
  "license": "Unsplash License",
  "commercial_use": true,
  "attribution_required": false,
  "notes": "No recognizable trademark or misleading endorsement"
}
```

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

- 是否已执行本地 preflight，且所有 SVG 通过 XML、协议、资产、bbox 和文本重叠检查。
- 是否已执行 `slides +create-svg --dry-run`，确认请求链路是创建 presentation + 按页追加 SVG。
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
- 图片是否已变成本地 `@./path` 或 file token，不能保留 http(s) / data URL。

验证记录建议写回 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json` 的 `readback_verification` 字段，并在最终回复中简述：

```text
验证记录：
- Preflight：N/N SVG 通过 root/role/geometry/path/image/bbox 检查。
- Dry-run：已确认 create presentation + N 次 /slide。
- Readback：实际页数 N / 预期 N；未发现空白页、破图或缺失 closing slide。
- 版式：检查 safe area、文本重叠、越界和相邻页版式变化。
- 资产：图片均为本地 @path 自动上传或 file token，无 http(s)/data URL。
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
4. 已创建 presentation 或部分页面时，默认保留现场并回读确认；是否删除空 presentation 必须单独由用户确认。

### 编辑已创建的 SVG deck

SVG deck 后续编辑走双轨，不承诺 source SVG id 能稳定映射到 readback XML block id：

| 修改类型 | 推荐路径 | 说明 |
|----------|----------|------|
| 小改标题、文本、图片或坐标 | `xml_presentation.slide.get` 读回 XML -> 找当前 block_id -> `slides +replace-slide` | 使用转换后的 XML 做块级编辑，页序和 slide_id 不变 |
| 大幅换版式、重画图表、调整视觉系统 | 修改 source SVG -> 重新 preflight -> 重新创建或替换目标页 | 保持 SVG 的视觉表达优势，避免在转换后 XML 上手搓复杂 SVG 结构 |
| 无法定位 block_id 或映射不可信 | 回 source SVG 修改 | 不生成 `edit-map.json`，除非服务端或转换结果能证明 source id 可稳定保留 |

小改前必须重新 `slide.get` 拿最新 block id 和 revision；大改后必须更新同一个 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`，保持 plan、SVG 文件、创建结果和验证记录一致。
