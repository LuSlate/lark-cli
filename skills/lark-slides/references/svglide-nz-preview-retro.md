# SVGlide 新西兰风光本地预览复盘与改进计划

## 背景

本次验证目标是基于主题“新西兰风光”生成一份可本地预览的 SVGlide deck，不做简单冒烟，而是尽量产出一套能体现真实视觉水平的多页结果。

最终产物为 5 页 SVG-native deck：

1. 封面：新西兰风光
2. 南岛：雪山、峡湾与冰川湖
3. 北岛：火山、地热与海岸
4. 7 日风光路线节奏
5. 四个风景关键词收束

最终链路通过到 `dry_run`：

```text
plan
  -> assets
  -> generate_svg
  -> prepare
  -> preview
  -> preflight
  -> preview_lint
  -> aesthetic_review
  -> chart_verify
  -> semantic_review
  -> runtime_review
  -> visual_distinctness_review
  -> quality_gate
  -> dry_run
```

本地项目路径：

```text
.tmp/nz-scenery-svglide
```

关键报告：

```text
.tmp/nz-scenery-svglide/06-check/preflight.json
.tmp/nz-scenery-svglide/06-check/preview-lint.json
.tmp/nz-scenery-svglide/06-check/semantic-review.json
.tmp/nz-scenery-svglide/06-check/runtime-review.json
.tmp/nz-scenery-svglide/06-check/quality-gate.json
.tmp/nz-scenery-svglide/receipts/dry_run.json
```

## 结论

这次耗时偏长的主因不是 runner 执行慢，而是：

```text
缺少模板化生成能力
+ 缺少自动契约补齐
+ 缺少门禁自动修复
+ 在本地探索阶段跑了接近 production 的严格门禁
```

最终 runner 实际执行耗时是秒级到几十秒级；主要时间花在人工写 SVG、人工调版式、人工补 `slide_plan.json`、人工补项目级 `renderer-registry.json`、手工处理状态重跑。

## 时间拆解

| 阶段 | 现象 | 结论 |
| --- | --- | --- |
| 项目初始化 | `init` 在 20:54:19 完成 | 很快，不是瓶颈 |
| source 准备 | `source` 在 20:57:14 完成 | 主要是人工写 source notes/evidence |
| SVG 生成脚本编写 | 手写 5 页 direct SVG generator | 最大耗时来源 |
| preview/preflight 修复 | 被文本高度、卡片容器、文本重叠打回 | 模板没有文本预算和布局约束 |
| semantic review 修复 | 可见文字没有完整追溯到 plan/source | 计划层和产物层没有自动对齐 |
| runtime review 修复 | 自定义 renderer_id 未登记 | 缺少项目级 renderer registry 自动生成 |
| final dry_run | `quality_gate` 和 `dry_run` 最终 passed | 链路可以跑通，但前置人工摩擦太多 |
| 本地视觉截图 | 环境缺 Playwright/resvg/CairoSVG，最后用 QuickLook | 预览渲染工具链不稳定 |

## 具体卡点

### 1. `preview_lint` 对文本框高度敏感

失败表现：

```text
preview_text_overflow_risk
preview_big_number_box_tight
```

触发页面：

- 第 1 页：`南岛`、`北岛`、`路线`
- 第 4 页：标题和阶段标签
- 第 5 页：标题、关键词、说明文本

根因：

手写 SVG 时没有统一的文本预算函数，只是凭视觉估计设置 `foreignObject` 的 `width/height`。门禁按保守行高判断后，短文本也可能被判为有溢出风险。

判断：

规则本身不应删除，因为 PPT 导出后文本被裁切是严重问题。但探索阶段不应要求人工逐个调框。

改进：

- 模板层内置 `fitTextBox()` 预算。
- 所有 text component 默认给足 `line-height * lines + padding`。
- `preview_lint` 在 `draft_preview` profile 下将轻微高度不足降级为 warning。
- runner 增加自动修复建议或自动扩高能力。

### 2. `preflight` 拦截了第 5 页卡片文本重叠

失败表现：

```text
text_bbox_overlap
text_container_overflow
```

根因：

为了修 `preview_lint`，人工增大了关键词卡片内文本框高度，但没有同步增大卡片容器，也没有重新计算卡片内部 y 坐标。

判断：

这类门禁不算太紧。文本重叠和容器越界在真实 PPT 中会直接翻车，应该阻断。

改进：

- 卡片模板必须用布局函数生成，而不是人工坐标。
- 卡片容器高度由内容反推。
- 文本变更后自动触发布局重算。
- `preflight` 输出更精确的元素位置和最近容器，减少人工定位时间。

### 3. `semantic_review` 要求可见文字追溯到 plan/source

失败表现：

```text
visible_text_not_in_plan_or_source
body_point_not_chinese
content_body_points_too_many
```

根因：

SVG 中出现了大量设计文案和英文页签：

```text
SCENIC ATLAS
SOUTH
NORTH
ROUTE
TAKEAWAY
Day 1
Tekapo 蓝
SVGlide 本地预览...
```

这些文案没有在 `slide_plan.json` 或 source evidence 中完整登记。

判断：

规则方向是对的。PPT 生成链路需要保证“计划层负责内容，渲染层不私自发明业务文案”。但当前执行方式太依赖人工。

改进：

- Slide Planner 需要输出 `visible_text` 字段。
- Template Renderer 需要把实际渲染文本反写为 text inventory。
- semantic review 应比较 `planned_visible_text` 和 `rendered_visible_text`，而不是让人手工补。
- 英文装饰标签应有明确字段，例如 `decorative_labels`，并允许白名单。
- 对纯设计辅助文案区分 `content_text` 和 `decorative_text`。

### 4. 修改 plan 后 receipt/hash 级联失效

失败表现：

```text
plan confirmation plan_sha256 does not match current plan
assets manifest plan_sha256 does not match current project files
```

根因：

为了修 semantic review 修改了 `slide_plan.json`，但 `plan-confirmation.json`、assets manifest、generate receipt 等下游文件仍指向旧 hash。

判断：

hash 校验是必要的，但当前恢复方式太手工。

改进：

- runner 增加 `reset --from <stage>`。
- runner 增加 `rerun --from <stage> --until <stage>`。
- 当 plan hash 改变时，自动标记下游 stage stale。
- 对本地预览提供 `--auto-confirm-plan`，仅限非 live create。
- state 文件不要靠人工 patch。

### 5. `runtime_review` 要求 renderer_id 登记

失败表现：

```text
renderer_unknown
```

触发 renderer：

```text
nz_scenic_cover
nz_south_island_panels
nz_north_island_map
nz_route_timeline
nz_closing_keywords
```

根因：

为了让这套 deck 的页面类型更语义化，使用了项目自定义 `renderer_id`，但一开始没有生成项目级：

```text
02-plan/renderer-registry.json
```

判断：

这个规则也不应删除。renderer registry 是后续运行时可追踪、模板资产可治理的基础。

改进：

- Slide Planner 选模板时自动生成项目级 renderer registry。
- Template Registry 中的模板 id 自动映射到 renderer id。
- 对 direct SVG prototype 支持临时 renderer registry。
- `runtime_review` 在报错时输出建议 registry stub。

### 6. 本地预览渲染工具链不稳定

失败表现：

- node_repl 的 Playwright 调用失败。
- 本地没有 `playwright`。
- 本地没有 `rsvg-convert`。
- 本地没有 `cairosvg`。
- `sips` 不能直接转换当前 SVG。
- 最后使用 macOS QuickLook `qlmanage` 生成缩略图。

判断：

这不是主链路的核心问题，但严重影响“让我看看实际效果”的体验。

改进：

- CLI/skill 内置稳定预览截图工具。
- 优先选项：Playwright 渲染 `preview.html`。
- SVG 单页截图选项：resvg。
- 产物应自动生成：

```text
05-preview/preview.html
05-preview/contact-sheet.png
05-preview/page-001.png
...
```

## 门禁是否太紧

不是简单的“太紧”。

更准确的判断：

```text
production 门禁是合理的
但不应该直接用于 draft preview 的人工探索阶段
```

建议分三档：

### `draft_preview`

用于本地快速看效果。

只阻断：

- SVG 无法解析
- 页面空白
- 文本严重重叠
- 关键元素明显出画布
- preview.html 无法生成

降级为 warning：

- 轻微文本框高度不足
- 装饰元素轻微越过 safe area
- 文案未完全补齐 text inventory
- renderer registry 缺失但可推断

### `review_preview`

用于准备给人评审。

阻断：

- 文本溢出风险
- 容器越界
- 页面视觉重复度过高
- 语义和计划明显不一致
- renderer_id 未登记

允许 warning：

- 非核心装饰标签未完全追溯
- 少量安全区装饰 warning

### `production_live`

用于真实创建线上 Slides。

阻断全部关键门禁：

- generator receipt
- preflight
- preview_lint
- aesthetic_review
- semantic_review
- runtime_review
- visual_distinctness_review
- quality_gate
- dry_run

## 根因归纳

本次慢点可以归纳为四类：

### 1. 设计生成没有模板系统

现在实际是“人工画 5 页”，不是“主题输入后模板系统生成 5 页”。

缺失能力：

- Template Registry
- Theme Token
- CanvasSpec
- Satori-compatible / SVG-native component library
- 文本自动布局
- 页面类型自动映射

### 2. 计划层和渲染层没有自动闭环

渲染层实际出现的可见文本、renderer id、layout family、装饰标签，都需要回到计划层或 registry 中。但现在是人工补。

缺失能力：

- visible_text 自动生成
- text inventory 自动比对
- renderer registry 自动生成
- plan hash 级联失效管理

### 3. 门禁只有拦截，缺少自动修复

当前门禁能发现问题，但不会给 runner 一个可执行修复动作。

缺失能力：

- 自动扩高 text box
- 自动增大 card container
- 自动移动重叠文本
- 自动生成 registry stub
- 自动重跑 stale stages

### 4. 本地预览体验没有产品化

产物存在，但“快速看效果”还依赖手工打开 HTML、手工截图、手工拼图。

缺失能力：

- 自动打开预览
- 自动生成 contact sheet
- 自动截图
- preview report 中显示封面/缩略图

## 改进计划

### P0：减少同类返工

目标：下一次同类 5 页本地预览不再因为文本高度、registry、hash 手工处理卡住。

任务：

1. runner 增加 `reset --from <stage>`。
2. runner 增加 `--auto-confirm-plan`，仅允许非 live 阶段使用。
3. direct_svg/artboard 生成时自动写 `visible_text` 或 text inventory。
4. 生成项目级 `02-plan/renderer-registry.json`。
5. preview_lint 对 `draft_preview` 支持轻微文本高度 warning。
6. preflight 报告补充 bbox 坐标和最近容器信息。

验收：

```text
主题输入后，人工只改一次 generator 或模板，runner 能自动从 stale stage 续跑到 dry_run。
```

### P1：模板化常见页面

目标：不要再手写 5 页 direct SVG。

先做 5 个模板：

```text
cover_hero
three_scenic_cards
map_and_notes
route_timeline
keyword_wall
```

每个模板必须内置：

- schema 输入
- theme token
- text budget
- safe area
- visible_text 输出
- renderer registry metadata
- preview fixture

验收：

```text
输入主题“新西兰风光”后，5 页 deck 由模板组合生成，人工不需要逐页调坐标。
```

### P2：质量门禁 profile 化

目标：本地探索和线上创建使用不同严格度。

新增或明确三档：

```text
draft_preview
review_preview
production_live
```

验收：

```text
draft_preview 能在不牺牲严重质量底线的前提下快速给出可看预览；
production_live 仍保持严格创建标准。
```

### P3：自动修复闭环

目标：门禁发现的问题可以被 runner 自动修复一部分。

优先自动修：

- text box height
- card container height
- renderer registry stub
- visible_text 补全建议
- stale receipt reset

验收：

```text
preview_lint/preflight 常见问题不需要人工 patch SVG 坐标。
```

### P4：本地预览产品化

目标：跑完后自动给用户可视化结果。

产物：

```text
05-preview/preview.html
05-preview/contact-sheet.png
05-preview/page-001.png
05-preview/page-002.png
...
```

实现建议：

- HTML 截图：Playwright
- SVG 单页截图：resvg
- fallback：QuickLook 仅作为 macOS fallback，不作为主链路

验收：

```text
runner dry_run 后自动输出 contact sheet，用户无需手工打开浏览器也能先看一眼。
```

## 建议的目标耗时

| 阶段 | 当前体感 | 改进后目标 |
| --- | --- | --- |
| 主题到 draft preview | 10-20 分钟 | 1-3 分钟 |
| draft preview 到 review preview | 多轮人工修 | 3-5 分钟 |
| review preview 到 production dry_run | 手工补契约 | 1 分钟以内 |
| 单次 runner 重跑 | 秒级到几十秒 | 秒级到几十秒 |

## 下一步建议

优先级最高的不是放松所有门禁，而是把“探索生成”和“线上创建”分层。

建议先做：

```text
1. runner reset/rerun 能力
2. draft_preview profile
3. 自动 visible_text
4. 自动项目级 renderer-registry
5. 5 个基础模板
```

做完这 5 件事后，同样的“新西兰风光 5 页预览”应该可以从人工 10-20 分钟降到 1-3 分钟，并且不会牺牲最终 production_live 的质量门禁。
