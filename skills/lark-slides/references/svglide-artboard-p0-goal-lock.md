# SVGlide Artboard/Satori P0 Goal Lock

## 1. Current Objective

当前唯一目标是按 `/Users/bytedance/Downloads/PLAN.md` 跑通一个可重复的 `artboard_satori` 竖切，而不是继续做新的 `direct_svg` 视觉 demo。

目标链路：

```text
3 页 artboard_satori fixture
-> 命中 3 个 Template Registry 模板
-> Satori 渲染
-> resvg 输出 PNG/contact sheet
-> compiler 输出 SVGlide protocol SVG
-> quality_gate + dry_run 通过
```

## 2. Source Of Truth

实现和审查必须优先对齐以下文件：

```text
/Users/bytedance/Downloads/PLAN.md
skills/lark-slides/references/svglide-artboard-satori.contract.md
skills/lark-slides/references/svglide-canvas-spec.schema.json
skills/lark-slides/references/svglide-renderer-registry.json
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_artboard_renderer.py
skills/lark-slides/scripts/artboard_renderer/package.json
```

如果本文件与 `PLAN.md` 冲突，以 `PLAN.md` 为主；如果 `PLAN.md` 表述仍不够工程化，先补本文件或相关 contract，再进入实现。

## 3. Hard No-Go Rules

接下来不允许用以下方式制造“看起来完成”：

```text
不再用 direct_svg 做新的主验证
不再手写 .tmp/.../generate_svg.py 作为主路径
不再用 QuickLook / qlmanage 作为主截图路径
不先放松 production 门禁来制造通过
不降低或删除任何既有 production gate；artboard 只能增加检查
不新增无法被 Template Registry / renderer registry 追踪的模板或 renderer
不手工 patch state.json 作为常规 runner 操作
不把 Satori 输出 SVG 当作 SVGlide 语义真源
不把外部 HTML/CSS 库直接接入运行时
```

允许临时诊断，但诊断结果不能作为 P0 验收证据。

## 4. Required Vertical Slice

P0 竖切必须至少包含 3 页 fixture：

| Page | Required template | Purpose |
| --- | --- | --- |
| 1 | `cover-hero` | 证明封面模板和主题 token 生效 |
| 2 | `comparison-cards` | 证明多内容块模板、文本预算和 template fit 生效 |
| 3 | `summary-final` | 证明收束页模板、可见文本追溯和多页一致性生效 |

每页必须满足：

```text
generation_mode = artboard_satori
canvas_spec.version 存在
canvas_spec.template_id 来自 Template Registry
canvas_spec.theme 或 theme_id 存在
canvas_spec.content.title 存在
visible_text / semantic elements 可追溯
artboard receipt 存在
```

P0 当前只验收到 `quality_gate + dry_run`。`ppe_proof / live_create / readback` 属于 P0c 后续闭环，不是本竖切的通过条件；但本竖切不能做任何会阻碍 P0c 的协议或 receipt 设计。

## 5. Dependency Lock

`skills/lark-slides/scripts/artboard_renderer/package.json` 必须显式声明：

```text
satori
@resvg/resvg-js
```

P0 主路径：

```text
Satori SVG -> @resvg/resvg-js -> PNG preview / contact sheet
```

QuickLook、Chromium、Playwright 只能作为 fallback 或调试工具，不能作为 P0 默认路径。

receipt 必须记录：

```text
node_version
satori_version
resvg_version
font_hashes
template_id
theme_id
input_canvas_spec_hash
output_satori_svg_hash
output_svglide_svg_hash
output_png_hash
```

## 6. Template Registry And Theme Lock

模板和主题不能用“等价来源”模糊带过。P0 必须有明确 registry/theme 证据：

```text
skills/lark-slides/references/svglide-template-registry.json
skills/lark-slides/scripts/artboard_renderer/templates/*.mjs
skills/lark-slides/scripts/artboard_renderer/themes/*.mjs
```

如果 P0 选择项目级 registry，也必须落盘为：

```text
02-plan/template-registry.json
02-plan/theme-registry.json
```

并且必须满足：

```text
未知 template_id fail-fast
未知 theme_id fail-fast
template_id 必须来自 registry
theme_id 必须来自 registry
template registry hash 写入 template-fit receipt
theme registry hash 写入 artboard-render receipt
generate_svg receipt 汇总 registry/theme hash
quality_gate 校验 registry/theme hash fresh
```

禁止临时在 renderer 代码里硬编码一个未登记模板并把它算作“命中模板”。

## 7. Acceptance Evidence

P0 通过时必须能提供以下证据：

```text
02-plan/slide_plan.json
02-plan/template-registry.json 或 skills/lark-slides/references/svglide-template-registry.json
02-plan/theme-registry.json 或 skills/lark-slides/scripts/artboard_renderer/themes/*.mjs
04-svg/artboard/raw/page-###.satori.svg
04-svg/artboard/page-###.png
04-svg/page-###.svg
05-preview/contact-sheet.png
06-check/canvas-spec-validate.json
06-check/template-fit.json
06-check/quality-gate.json
07-create/dry-run.json
receipts/canvas-spec-validate.json
receipts/template-fit-check.json
receipts/artboard-render.json
receipts/satori-bridge.json
receipts/generate_svg.json
receipts/dry_run.json
```

并且报告中必须能证明：

```text
真的走 artboard_satori
真的命中 3 个模板
真的使用 @resvg/resvg-js
quality_gate passed
dry_run passed
没有依赖 direct_svg 旁路
没有依赖 QuickLook 作为主路径
```

## 8. Quality Gate Hard Requirements

`quality_gate` 通过必须证明以下 hash/freshness 关系，不允许只检查文件存在：

```text
generate_svg.receipt.generation_mode == artboard_satori
generate_svg.receipt.artboard_receipts 非空且页数匹配
canvas-spec-validate receipt hash == 当前 slide_plan canvas_spec hash
template-fit receipt hash == 当前 CanvasSpec + Template Registry hash
artboard-render receipt hash == 当前 CanvasSpec + Theme Registry + font inputs hash
satori-bridge receipt hash == 当前 CanvasSpec + semantic-map + node-layout-map + raw Satori SVG hash
prepared SVG hash == satori-bridge 输出 SVGlide SVG hash
PNG/contact-sheet hash == artboard-render 或 preview artifact 记录值
dry_run 输入 prepared files hash == quality_gate prepared_files hash
```

`quality_gate` 还必须保证：

```text
direct_svg receipt 不能作为 artboard_satori 验收证据
缺少 resvg_version 时失败
缺少 template_id/theme_id 时失败
缺少 template registry/theme registry hash 时失败
缺少 node-layout-map 或 drift 超阈值时失败
```

任何为了让 P0 通过而删除、降级或绕过既有 production 检查的改动，都视为偏离目标。

## 9. Stage Discipline

每次阶段汇报只回答四件事：

```text
做了什么
改了哪些文件
跑了哪些验证
离 P0 竖切还差什么
```

不在 P0 竖切完成前扩展到：

```text
完整 Deck Planner
外部美学资产大规模抽取
自动 repair loop
线上 live_create
CLI binary/npm 分发方案
复杂图表
真实图片资产
```

## 10. Subagent Supervisor Checklist

独立监督者每次审查必须检查：

```text
1. 是否偏离当前唯一目标
2. 是否偷偷回到 direct_svg
3. 是否绕开 Template Registry
4. 是否缺少 CanvasSpec / template_id / theme_id
5. 是否没有安装或调用 @resvg/resvg-js
6. 是否用 QuickLook / browser 截图冒充主路径
7. 是否为了过门禁而放松 production gate
8. 是否手工 patch state.json 代替 runner 能力
9. 是否有可重复 fixture 和测试证据
10. 是否能映射回 PLAN.md 的 P0/P1 条目
11. 是否具备 canvas-spec/template-fit/artboard-render/satori-bridge 的具体 receipt
12. quality_gate 是否检查 hash/freshness，而不是只检查文件存在
13. registry/theme 是否 hash-bound 且未知 id fail-fast
```

审查输出格式：

```text
Verdict: PASS / BLOCKED

Blocking issues:
- ...

Non-blocking risks:
- ...

Evidence checked:
- ...

Required next action:
- ...
```

## 11. First Implementation Steps

推荐执行顺序：

```text
1. 给 artboard_renderer 加 @resvg/resvg-js，并生成 PNG/contact sheet
2. 补最小 Template Registry，包含 cover-hero / comparison-cards / summary-final
3. 补 3 页 artboard_satori fixture 的 CanvasSpec
4. 让 generate_svg receipt 汇总 artboard receipts 和 PNG 输出
5. quality_gate 检查 artboard receipts fresh
6. 跑到 dry_run
```

任何下一步如果不能落到以上 6 项之一，默认先不做。
