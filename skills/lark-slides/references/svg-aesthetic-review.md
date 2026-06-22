# SVGlide 审美 Review

这份文档用于本地 SVG/HTML preview 生成之后、调用 `slides +create-svg` 之前。
它是从以下审美评分标准中提炼出的短版执行清单：
`/Users/bytedance/bd-projects/workspaces/SVGlide/svglide-visual-guidance/svg_aesthetic_rubric.md`.

这份 review 补充 `svg_preflight.py`。Preflight 负责确定性的协议、plan 和
bbox 问题；这份清单负责需要人工或截图判断的渲染后视觉质量问题。

## 必须执行的 Review 流程

1. 生成本地 SVG 文件，并在条件允许时生成本地 `preview.html`。
2. 运行 `svg_preflight.py --plan ... --input ...`；先修复所有 error。
3. 打开或检查 preview。必须审查所有页面，不只看封面。
4. 重复出现的版式问题要修生成器或 source SVG，不能只改 `slide_plan.json`。
5. live 创建前重新运行 preflight 和 preview。

不要用 preview review 替代 live readback。服务端转换后仍可能改变文本框、
图片 token、path bounds 和不支持的效果。

## 阻断性视觉问题

调用 live API 前必须修复这些问题：

| 问题 | 处理方式 |
|---|---|
| 文本重叠、文本容器溢出、标题被裁切 | 重新生成 layout boxes 或减少文本；不要只是整体缩小 |
| badge、pill、章节标签或页码标签贴住/压住标题 | 把 badge 移出标题块，或保留至少 12-16px 垂直间距 |
| 装饰线或色带压迫标题 | 把线移到标题区上方，或下移标题，保留呼吸感 |
| 主体内容超出 `960 x 540` 或 safe area | 按 960x540 画布重新计算坐标 |
| 浅色图片/背景上的低对比文本 | 增加实色承载底、overlay，或切换文字颜色 |
| 空图片框或 preview 破图 | live 创建前替换资产或使用视觉 fallback |
| 页面缺少视觉焦点 | 围绕一个主导数字、图解、图片或标题重建页面 |
| 页面只是普通卡片/bullet，缺少 family 变体价值 | 选择更合适的 template variant/component set，或不要走 SVG 路线 |
| 同类版式问题在多页重复出现 | 修共享生成规则，然后重新生成受影响页面 |

## Issue 严重级别

在 preview notes 和最终验证记录中使用这些级别：

| 级别 | 含义 | 处理方式 |
|---|---|---|
| P0 | 不应该 live 创建 | 在 `slides +create-svg` 前修复或重新生成 |
| P1 | 可以渲染，但用户可见质量明显低于目标 | 交付前修复；只有用户明确接受草稿时才继续 |
| P2 | 小幅打磨项或残余风险 | 记录下来，有时间再修 |

默认映射：

- P0：preflight error、不安全 SVG、破图/空图、画布裁切、关键文本裁切或重叠、对比度不可读、必需资产缺失、不支持视觉缺少 fallback。
- P1：焦点弱、布局骨架重复、装饰/标题拥挤、视觉层级弱、图表/图解意图不匹配、可见 SVG 优势弱。
- P2：轻微对齐差异、小的颜色不一致、非关键来源元数据 warning、只影响打磨的间距问题。

## 评分标准

使用 0-100 分。用户可见 deck 的默认目标是 `>= 75`。
低于 `65` 时，live 创建前必须重新生成或修复。

| 维度 | 权重 | 好结果 |
|---|---:|---|
| 沟通匹配度 | 15 | 页面类型和视觉形式匹配用户意图 |
| 视觉层级 | 15 | 2 秒内能看到唯一焦点 |
| 布局稳定性 | 15 | 网格、间距、对齐和 safe area 一致 |
| 可读性 | 15 | 字号、行长、对比度和换行可读 |
| 颜色纪律 | 10 | 强调色数量少，且语义一致 |
| 数据/图解完整性 | 10 | 图表、流程和图解诚实表达关系 |
| 风格一致性 | 8 | 图标、圆角、线宽、阴影和 motif 像同一套 deck |
| SVG 优势 | 7 | 页面明显受益于 path、texture、chart geometry、flow 或 overlay |
| 来源/资产可追溯 | 5 | 使用外部参考和 preview 资产时有记录 |

## Review 问题

每页都问这些问题：

- 这一页的一句话 takeaway 是什么？
- 第一眼落点在哪里，是否就是预期的 `visual_focal_point`？
- 视线顺序是否符合 title -> focal visual -> evidence -> detail？
- 有没有 badge、线条、水印、标签或缩略图挤压文本？
- 页面是否使用了 SVG-native 结构，还是只有普通盒子和文本？
- 如果这一页变成普通 XML/PPT 卡片布局，会损失什么？
- 图表/流程/表格选择是否适合它要表达的关系？
- 颜色和强调方式是否和整套 deck 保持一致？

## 修复优先级

1. 布局正确性：画布、safe area、重叠、溢出、裁切。
2. 可读性：对比度、字号、行长、文本框高度充足。
3. 层级：一个焦点对象、清晰标题、支撑细节降级。
4. SVG 优势：path/flow/chart/icon/texture/image overlay 真实存在。
5. Deck 节奏：避免只换文案却重复同一骨架。
6. 资产/来源治理：preview 资产可见，来源元数据存在。

## 可接受的输出记录

报告验证结果时，明确说明检查过什么：

```text
SVG preview review:
- preflight: passed / fixed errors first
- preview_path: .lark-slides/plan/<deck-id>/preview.html
- preview: checked all N pages for overlap, safe area, readability, and repeated layout issues
- visual_score: 82 / threshold 75
- issue_ids: none / [P1 visual.layout.decorative_line_title_pressure page=3]
- action: create_live / repair_and_rerun / draft_only
- remaining risk: live readback may still change text bbox or unsupported effects
```
