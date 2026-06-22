# SVGlide 参考仓库榨干执行计划

更新时间：2026-06-22

## 0. 执行目标

这份文档是把本地参考仓库中的设计生成能力吸收到 SVGlide 的可执行计划。

目标不是新增一批“看起来还行”的模板数量，而是把已验证参考源逐项清点、去重、抽象、转成 SVGlide 自有资产或规则，并用真实 SVGlide 链路证明它们能工作。

完成状态必须满足：

```text
source census 完成
-> 每个 source item 都有 disposition
-> 每个被吸收的 item 都有 abstraction record
-> 每个 abstraction 都对应至少一个 SVGlide target asset 或 quality rule
-> 每个 target 都有 fixture proof
-> fixture 能通过 Satori-compatible artboard path 渲染
-> 输出能编译为 SVGlide protocol SVG
-> quality_gate 和 visual_acceptance 通过
-> 涉及后端行为的能力有 dry_run/readback 证明
-> independent reviewer PASS
```

任何少于以上证据链的状态，都只能标记为 `IN_PROGRESS`。

## 1. 范围

### 1.1 参考源

```text
/Users/bytedance/bd-projects/open-design
/Users/bytedance/bd-projects/ppt-master
/Users/bytedance/bd-projects/workspaces/SVGlide/PosterGen
/Users/bytedance/bd-projects/workspaces/SVGlide/satori
/Users/bytedance/bd-projects/og-images-generator
/Users/bytedance/bd-projects/beautiful-html-templates
```

### 1.2 SVGlide 目标工作树

```text
/Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private
branch: feat/svglide-artboard-satori
default push remote: origin
```

### 1.3 目标能力

```text
template asset library
theme token system
component library
real image and chart strategy
layout planner
reference project asset abstraction
quality gates and visual acceptance
trusted internal image provider route
VF5 benchmark and claim boundary
planner ownership and selection receipts
agent progress surface
```

### 1.4 禁止项

```text
do not add ppt-master as a runtime dependency
do not run open-design HTML/CSS as SVGlide runtime renderer
do not use PosterGen's generation workflow as SVGlide runtime
do not submit raw Satori SVG directly to the backend
do not count screenshot-only proof as backend readback proof
do not create doc-only abstractions without fixtures
do not count a source family until its real local path and inventory evidence exist
do not add og-images-generator as a runtime dependency
do not execute or embed beautiful-html-templates HTML/CSS as the SVGlide runtime renderer
do not delegate Deck Planner / Slide Planner / Canvas Planner output to another agent, subagent, codex exec, claude, Tika, AIME, BitsAI, or any external planner/provider unless the current user request explicitly asks to validate unattended provider automation
do not treat fixture benchmark PASS as real-model or real-image quality PASS
do not accept codex, claude, or any external/default planner as trusted VF5 real-route evidence
do not claim real image coverage unless a trusted stage_command provider materializes validated local image files
```

## 2. 当前基线

当前 `feat/svglide-artboard-satori` 的观察基线：

```text
baseline frozen at: 2026-06-22 12:56:08 CST
executor: Codex
reviewer: independent reviewer required before completion claim
branch: feat/svglide-artboard-satori
upstream: origin/feat/svglide-artboard-satori
local HEAD: 551f333563f5a26ec9568ad8090a0f14a1a419c7
remote HEAD: origin/feat/svglide-artboard-satori at 551f333563f5a26ec9568ad8090a0f14a1a419c7
working tree: dirty in the local workspace; existing unrelated modified/untracked files must not be reverted
template registry: 30 active templates
template selection_metadata coverage: 0 / 30 active templates
theme registry: 22 active themes
theme selection_metadata coverage: 0 / 22 active themes
style-presets palette assets: 35 presets
component layer: primitives plus P0 template components
visual acceptance: implemented as a separate delivery/claim gate after dry_run for artboard_satori
visual acceptance outputs: 06-check/visual-acceptance.json and receipts/visual_acceptance.json
visual acceptance scope: quality_gate/dry_run freshness, preview/contact-sheet evidence, artboard receipt hashes, template guardrails, page geometry, deck rhythm, and visual_evidence pages
template guardrails: svglide-template-guardrails.json is part of the acceptance input hash boundary
VF5 benchmark: fixture benchmark suite exists and stops before live_create
VF5 real benchmark: no PASS is claimed; real route requires trusted provider id, command planner, trusted asset provider, stage_command image backend, and SVGLIDE_IMAGE_STAGE_COMMAND
asset stage: stage_command image backend exists for trusted internal image generation/acquisition and validates image bytes before acquisition
semantic asset matcher: local harness has reached the completion threshold with 160 cases; P0 threshold was 60 cases
semantic asset matcher test command: python3 skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
semantic asset matcher test status: passed, 160 tests
planner ownership: current executor must own deck/slide/canvas planning decisions unless the user explicitly asks to validate unattended provider automation
```

这个基线足够继续 Phase 2/Phase 3 和第一批资产实现，但不能据此声称参考仓库已经被充分转化为 SVGlide 能力，也不能据此声称真实模型、真实图片或上限质量已经通过。

## 3. 参考源优先级

`beautiful-html-templates` 是本计划的 P0 visual asset reference source。

原因：

```text
它本身就是 HTML slide template library。
它有面向 agent 的模板选择流程。
它有结构化模板元数据 index.json。
当前本地 clone 中有 34 套 template systems 和 102 张 screenshots。
每套模板通常包含 template.json、template.html 和 design.md。
它的概念可以直接映射到 SVGlide templates、themes、components、layout archetypes 和 planner-selection rules。
```

按目标能力划分的优先级：

```text
template asset library:
  P0 beautiful-html-templates
  P1 ppt-master, open-design

theme token system:
  P0 beautiful-html-templates
  P1 open-design, ppt-master

component library:
  P0 beautiful-html-templates
  P1 open-design

layout planner:
  P0 beautiful-html-templates
  P1 ppt-master
  P2 PosterGen for research-poster density and section balancing

real image and chart strategy:
  P0 ppt-master
  P0 trusted internal stage_command provider route for executable image proof
  P1 PosterGen
  P2 beautiful-html-templates for image treatment style only

Satori and renderer constraints:
  P0 satori
  P1 og-images-generator

quality gates and anti-slop rules:
  P0 open-design
  P1 beautiful-html-templates screenshots
```

`beautiful-html-templates` 单仓库的规划产出目标：

```text
owned theme token candidates: 18-26
Canvas template / layout archetype candidates: 20-34
component or section variant candidates: 50-90
design, negative, or visual-acceptance rules: 30-50
total useful asset/rule candidates: 80-140
```

这些数字是规划目标，不是完成证明。完成仍然要看 source inventory、deduplication、abstraction records、fixtures、receipts 和 reviewer PASS。

## 4. 必交付物

### 4.1 参考源清单（Source Inventory）

路径：

```text
skills/lark-slides/references/svglide-reference-source-inventory.json
```

用途：完整记录每个参考仓库中可用 source item 的清点结果。

每个 item 至少包含：

```json
{
  "id": "ppt-master.example.attention_is_all_you_need.page_001",
  "source_repo": "ppt-master",
  "source_path": "/Users/bytedance/bd-projects/ppt-master/examples/...",
  "source_type": "deck_page|template|theme|layout|component|quality_rule|renderer_constraint|prompt_rule|selection_rule|benchmark_route|trusted_provider_route|progress_rule",
  "priority": "P0|P1|P2",
  "source_hash": "sha256:...",
  "extract_fields": ["palette", "typography", "layout_skeleton"],
  "disposition": "pending|absorbed|duplicate_of|forbidden_runtime_dependency|not_applicable_to_svglide|blocked_with_reason",
  "disposition_reason": "",
  "owner_target": "template|theme|component|layout_planner|asset_stage|quality_gate|visual_acceptance|vf5_benchmark|progress_surface|docs",
  "absorption_record": "skills/lark-slides/references/absorptions/...",
  "review_status": "pending|pass|blocked"
}
```

规则：

```text
完成时不能有未分类的 source item。
每个跳过的 item 都必须说明为何不适用或为何被禁止。
每个 duplicate 都必须指向 canonical absorbed item。
```

### 4.2 抽象记录（Abstraction Records）

路径模式：

```text
skills/lark-slides/references/absorptions/<source-repo>/<source-id>.json
```

用途：把外部源细节转成 SVGlide 自有概念，而不是复制外部 HTML/CSS/SVG。

每条记录至少包含：

```json
{
  "source_item_id": "ppt-master.example.x.page_001",
  "absorbed_as": ["layout_archetype", "theme_rule", "chart_strategy"],
  "svglide_asset_ids": ["template.data_story_split_hero", "theme.finance_dark"],
  "non_copying_transform": "Describes the reusable structure, not copied SVG/CSS.",
  "forbidden_usage": ["do_not_use_ppt_master_svg_as_output"],
  "canvas_spec_fixtures": ["skills/lark-slides/fixtures/artboard/...json"],
  "satori_outputs": [".../raw-satori.svg"],
  "svglide_protocol_outputs": [".../page-001.svg"],
  "quality_receipts": [".../quality-gate.json", ".../visual-acceptance.json"],
  "template_guardrail_records": ["skills/lark-slides/references/svglide-template-guardrails.json"],
  "dry_run_or_readback_receipts": [".../dry-run.json", ".../readback.json"],
  "vf5_benchmark_receipts": [".../vf5-benchmark.json"],
  "trusted_provider_evidence": ["trusted_provider_evidence from vf5-benchmark receipt when real image/model claims are made"],
  "negative_fixtures": [".../unsupported-css.json"],
  "review_notes": ""
}
```

### 4.3 吸收工具（Absorber Tooling）

路径：

```text
skills/lark-slides/scripts/svglide_reference_absorber.py
```

必须支持的命令：

```bash
python3 skills/lark-slides/scripts/svglide_reference_absorber.py census --repo all --out skills/lark-slides/references/svglide-reference-source-inventory.json
python3 skills/lark-slides/scripts/svglide_reference_absorber.py check-inventory skills/lark-slides/references/svglide-reference-source-inventory.json
python3 skills/lark-slides/scripts/svglide_reference_absorber.py check-absorption skills/lark-slides/references/svglide-reference-source-inventory.json
python3 skills/lark-slides/scripts/svglide_reference_absorber.py report --format md --out skills/lark-slides/references/svglide-reference-absorption-report.md
```

工具遇到以下情况必须失败：

```text
a source path is missing
a source hash is stale
an item has no priority
an item has no disposition
an absorbed item has no abstraction record
an abstraction has no fixture proof
a duplicate item has no canonical target
a forbidden item is still referenced by runtime code
```

### 4.4 资产注册表与运行时资产

只有在 abstraction record 已存在后，才允许新增或修改 SVGlide 自有资产。

主要目标路径：

```text
skills/lark-slides/references/svglide-template-registry.json
skills/lark-slides/scripts/artboard_renderer/templates/p0-templates.mjs
skills/lark-slides/scripts/artboard_renderer/themes/registry.json
skills/lark-slides/scripts/artboard_renderer/themes/*.json
skills/lark-slides/scripts/artboard_renderer/components/primitives.mjs
skills/lark-slides/scripts/svglide_prompt_planner.py
skills/lark-slides/scripts/svglide_assets.py
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_pre_submit_review.py
skills/lark-slides/scripts/svglide_quality_gate.py
skills/lark-slides/scripts/svglide_visual_acceptance.py
skills/lark-slides/scripts/svglide_vf5_benchmark.py
skills/lark-slides/scripts/svglide_semantic_asset_matcher.py
skills/lark-slides/references/svglide-template-guardrails.json
```

不能新增没有 `source_trace` 或 `abstraction_record` 的 registry item。

### 4.5 证据报告

路径：

```text
skills/lark-slides/references/svglide-reference-absorption-report.md
```

必须包含：

```text
source census totals by repo and source_type
P0 beautiful-html-templates coverage and drift report
disposition totals
absorbed assets by target capability
beautiful-html-templates-derived templates/themes/components/layouts
new templates/themes/components/layout archetypes
quality rules added
visual_acceptance and template_guardrails evidence
VF5 fixture benchmark result and explicit real benchmark claim boundary
trusted internal image provider route evidence when real image claims are made
semantic matcher case count and remaining case-gap against 24/60/150 thresholds
fixtures and receipts
negative fixtures
skipped items with reasons
reviewer verdict
remaining blocked items
```

## 5. 执行阶段

### 阶段 0：冻结基线

负责人：main agent

动作：

```bash
git status --short --branch
git rev-parse HEAD
python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_assets_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_vf5_benchmark_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
```

验收标准：

```text
在 report 中记录 current branch 和 HEAD
列出 dirty files，并标记为 pre-existing 或 changed by this plan
baseline tests 通过，或记录明确的 pre-existing failure
```

### 阶段 1：参考源清点

负责人：executor

动作：

```text
枚举每个参考仓库中的可用 source item。
除明显 forbidden runtime dependency 外，清点阶段不急于决定是否吸收。
对所有用于提取的 source file 计算 hash。
把每个 item 记录到 svglide-reference-source-inventory.json。
```

仓库清点规则：

```text
open-design:
  扫描 design-templates、template metadata、example HTML、previews、craft guidance
  按 theme、layout skeleton、typography、component combination、anti-slop rule 分类

ppt-master:
  扫描 examples/examples.json、example design_spec.md、spec_lock.md、svg_final pages、chart/template/style registries
  按 deck rhythm、page archetype、palette rule、image strategy、chart strategy、density fact、golden page 分类

PosterGen:
  扫描 config/poster_config.yaml、config/prompts、src/agents、resource、data samples
  按 research-poster layout heuristic、column balancing、text measurement、utilization rule、image/logo placement 分类

satori:
  扫描 README、supported CSS docs、test cases、layout examples、image/font constraints
  按 renderer constraint、supported pattern、unsupported negative fixture、HTML/CSS subset rule 分类

og-images-generator:
  扫描 README、package.json、src、demos、test cases、config examples
  按 HTML/CSS-to-image pipeline、metadata-to-visual mapping、OG layout template、font/image handling、static output manifest、Satori-compatible helper、renderer failure case 分类
  转成自有 agent progress rules、image-generation template patterns、renderer constraints、manifest/receipt ideas 和 negative fixtures
  forbidden: 不添加为 CLI runtime dependency，不把 SVGlide backend input 路由到 OG-image PNG output

beautiful-html-templates:
  path: /Users/bytedance/bd-projects/beautiful-html-templates
  priority: P0 for visual asset harvest
  扫描 index.json、AGENTS.md、README.md、templates/*/template.json、templates/*/template.html、templates/*/design.md、screenshots/*.png
  按 HTML slide template、cover layout、mid-deck layout、later-deck layout、visual section、card/list/table component、typography pair、color system、spacing rhythm、decorative vocabulary、image treatment、planner selection signal 分类
  转成自有 Theme Tokens、Canvas Templates、Component Variants、Layout Archetypes 和 visual negative examples
  minimum inventory proof: index.json 中的 34 templates、102 screenshots，以及每个 template folder 中存在的 template.json/template.html/design.md
  forbidden: 不执行或嵌入其 HTML/CSS 作为 SVGlide runtime renderer；没有 license/provenance 和 source hashes 前不能算 absorbed
```

验收标准：

```text
inventory 文件存在
所有 source paths 都是 absolute 且 readable
所有 source hashes 都存在
所有 source items 都有 P0/P1/P2 priority
没有具体 source item 的 source family 不能计入覆盖
beautiful-html-templates 覆盖 index.json、34 templates 和 102 screenshots，除非记录了 source drift
check-inventory command 通过
```

### 阶段 2：处置与去重

负责人：executor + reviewer

动作：

```text
为每个 inventory item 指定 disposition。
把 duplicate 合并到 canonical absorbed concept。
拒绝法律或技术上不能转成 SVGlide asset 的 source-specific artifact。
为 blocked item 记录精确 blocker。
```

允许的 `disposition`：

```text
absorbed
duplicate_of
forbidden_runtime_dependency
not_applicable_to_svglide
blocked_with_reason
```

验收标准：

```text
没有 pending disposition
所有 duplicate 都指向 absorbed canonical item
所有 forbidden item 都说明会违反哪个 runtime boundary
reviewer 至少抽查 20 个 skipped item，并能从 source files 复现跳过原因
```

### 阶段 3：抽象记录

负责人：executor

动作：

```text
为每个 absorbed item 创建 abstraction record。
把 source detail 翻译成 SVGlide-owned concept。
当多个 source 支撑同一概念时，把 abstraction 聚合成 target asset。
```

必须覆盖的 abstraction category：

```text
deck rhythm pattern
single-slide layout archetype
template candidate
theme token candidate
component variant
image strategy
chart strategy
typography rule
color rule
density and spacing rule
renderer constraint
negative fixture rule
```

验收标准：

```text
每个 absorbed inventory item 都链接到 abstraction record
每个 abstraction 都说明为什么能在 SVGlide 中复用
每个 abstraction 都说明哪些内容禁止复制
每个 abstraction 都至少有一个具体 SVGlide target
check-absorption command 通过 abstraction completeness 检查
```

### 阶段 4：资产实现

负责人：executor

动作：

```text
根据 abstraction records 实现 target SVGlide assets。
优先扩展当前 registries 和 renderer primitives，再考虑新系统。
外部参考仓库文件不能进入 runtime path。
```

最低实现目标：

```text
templates: expand from 15 active to at least 30 active, only if each template has source trace and fixture proof
themes: expand from 10 active to at least 20 active, only if each theme has token audit and fixture proof
components: expand primitives into at least 60 variants, including text, image, chart, metric, timeline, callout, section, table, logo/affiliation, and poster blocks
layout archetypes: at least 14 reusable archetypes, including research poster, dense dashboard, editorial story, image-led explainer, timeline, compare/contrast, section divider, data story, quote/claim, process, editorial cover, zine/poster, grid system, and full-bleed image story
image strategies: at least 20 documented and fixture-backed strategies
chart strategies: at least 12 documented and fixture-backed strategies
renderer constraints: Satori supported and unsupported rules encoded as checks or negative fixtures
```

数字是下限，不是完成证明。真正完成证明仍然是完整 source disposition 和可验证吸收链。

`beautiful-html-templates` 的贡献目标：

```text
at least 18 owned theme-token candidates evaluated
at least 20 Canvas template or layout archetype candidates evaluated
at least 50 component or section variants evaluated
at least 30 design/negative/visual-acceptance rules evaluated
at least 12 high-value templates converted into SVGlide fixtures in the first implementation wave
每个 converted template 必须保留 design DNA，但不能把外部 HTML/CSS 复制进 runtime
```

验收标准：

```text
每个新增 registry item 都包含 source_trace 或 abstraction_record reference
每个新增 runtime asset 至少有一个 CanvasSpec fixture
所有 fixtures 都能通过 artboard renderer 渲染
所有生成的 protocol SVG files 通过现有质量检查
涉及 visual-quality claims 时 visual_acceptance 通过
```

### 阶段 5：Planner 选择集成

负责人：executor

动作：

```text
让 planner 能根据 task type、source material、visual density、image availability、chart availability 和 output constraints 选择扩展后的 assets。
阻止无限制 HTML/CSS/SVG 生成。
增加 selection receipts，让 reviewer 能看到 template/theme/component 的选择理由。
当前执行者必须亲自完成 Deck Planner / Slide Planner / Canvas Planner 的推理和产物生成。
不得为了完成当前链路调用另一个 agent、subagent、codex exec、claude、Tika、AIME、BitsAI 或外部 planner/provider 来生成 deck plan、slide plan、slide_plan、CanvasSpec 或 asset contracts。
允许普通工具读取文件、做确定性转换、事实检索、素材获取、渲染、校验和导出，但这些工具不能接管 planner 决策。
```

planner 必须输出：

```text
brief_signals
brief_occasion
brief_mood
brief_tone
brief_formality
brief_density
content_shape
selected_template_id
selected_theme_id
selected_layout_archetype
selected_component_variants
image_strategy_ids
chart_strategy_ids
renderer_constraint_profile
selection_receipt_path
source_trace_refs
abstraction_record_refs
candidate_templates_considered
candidate_rejection_reasons
fallback_reason when a richer asset is not selected
```

验收标准：

```text
planner output schema 校验通过
render 前 template-fit check 通过
selection receipts 指向 registry items 和 abstraction records
没有 prompt path 能注入 raw external HTML/CSS/SVG
beautiful-html-templates-derived assets 按 occasion、mood、tone、formality、density、scheme 选择，而不是只按 template name 选择
planner ownership rule 有测试或 reviewer evidence，证明当前链路没有委托外部 planner 生成 planning artifacts
semantic asset matcher 当前机制锁定阶段至少 24 cases 通过；当前 4-case smoke harness 不能算满足最低门槛
```

semantic asset matcher 测试预算：

```text
最低可合入：24 cases
  positive hit cases: 12
  negative mismatch cases: 6
  boundary / rewrite cases: 6

P0 可验收：60 cases
  positive hit cases: 30
  negative mismatch cases: 15
  boundary / rewrite cases: 15

榨干完成态：150-250 cases，目标约 200 cases
  template hit cases: 120-170
  negative cases: 40-60
  style override / boundary cases: 30-50
```

这些测试必须覆盖：

```text
未知主题词能否拆成 brief_occasion / brief_mood / brief_tone / brief_formality / brief_density / content_shape
top-1 selected_template_id 是否合理
top-3 candidate_templates_considered 是否合理
错误候选是否有 candidate_rejection_reasons
style override 是否能改变排序
同义改写是否稳定
不会所有请求都命中同一个 default template
```

### 阶段 6：证明链 fixtures

负责人：executor

动作：

```text
每个 implemented target 至少增加一个 positive fixture。
每个 new gate 或 renderer constraint 至少增加一个 negative fixture。
运行完整 proof chain。
```

必须证明的链路：

```text
source item
-> abstraction record
-> SVGlide target asset
-> CanvasSpec fixture
-> Satori-compatible render
-> SVGlide protocol SVG
-> quality_gate
-> visual_acceptance
-> VF5 fixture benchmark when claiming prompt-to-visual-acceptance chain reliability
-> trusted real VF5 benchmark when claiming real-model or upper-bound visual quality
-> dry_run/readback when backend behavior is involved
```

验收标准：

```text
proof chain 可由机器检查
receipt files 包含 input/output hashes
涉及 visual quality claim 时，visual acceptance evidence 包含 fresh screenshot 或 geometry evidence
涉及 real image claim 时，asset evidence 必须来自 trusted:<provider-id> + --image-backend stage_command + SVGLIDE_IMAGE_STAGE_COMMAND，并包含 validated local image hash
涉及 real-model 或上限质量 claim 时，VF5 receipt 必须 real_benchmark=true 且包含 trusted_provider_evidence；fixture benchmark 只能证明链路形态
影响后端行为的 chart/image case 有 readback proof
```

### 阶段 7：Agent 进度展示面

负责人：executor

动作：

```text
更新 SVGlide runner，让用户侧 progress 只报告 milestone artifacts。
隐藏 internal thinking、retries、review loops、repair attempts 和 rejected drafts。
```

用户侧只展示这些里程碑：

```text
正在生成主题 plan 和图片资产
已完成 1/4 关键产物: 主题 plan + 图片资产
已完成 2/4 关键产物: Satori-compatible HTML/CSS
已完成 3/4 关键产物: Satori preview SVG / visual acceptance evidence
已完成 4/4 关键产物: backend snapshot JSON
```

运行规则：

```text
stdout remains machine-readable final JSON
agent/human progress goes to stderr or logs/agent-progress.jsonl
raw stack traces and repeated repair chatter are not shown in agent progress mode
current runner CLI does not accept --progress yet; Phase 7 must add it before any command or doc claims progress mode support
```

验收标准：

```text
progress tests cover artboard_satori 4/4
progress tests cover direct_svg denominator separately
failure tests show one concise blocked message
stdout JSON tests still pass
```

### 阶段 8：独立审查

负责人：reviewer

reviewer 必须检查仓库状态和源证据，不能只看 executor 的文字说明。

阻断项：

```text
若 source census 跳过某个 repository 且没有 blocker，则阻断
若任何 source item 仍为 pending，则阻断
若 absorbed item 缺少 abstraction record，则阻断
若 registry asset 没有 reverse traceability，则阻断
若 fixture 只证明文件存在，则阻断
若声称 visual quality 但没有 visual_acceptance evidence，则阻断
若声称 backend behavior 但没有 dry_run/readback evidence，则阻断
若 external runtime dependencies 泄漏进 SVGlide，则阻断
若 new assets 只是为了凑数量而高度近似，则阻断
若 generated pages 退化成 title-plus-bullets，则阻断
若 beautiful-html-templates inventory 没覆盖 index.json、所有 template folders、template.json/template.html/design.md files 和 screenshots，则阻断
若 beautiful-html-templates-derived assets 丢失 mood/tone/density/scheme selection metadata，则阻断
若 beautiful-html-templates HTML/CSS 被复制进 runtime，而不是转成 owned SVGlide abstractions，则阻断
若 planning artifacts 来自未获当前用户明确授权的外部 planner/provider 或另一个 agent，则阻断
若真实图片或真实 benchmark claim 没有 trusted_provider_evidence 和 stage_command 证据，则阻断
若 fixture VF5 benchmark 被表述成 real benchmark PASS，则阻断
```

reviewer 抽样要求：

```text
至少抽查 12 个 beautiful-html-templates template systems，覆盖 high-density、editorial、playful、dark、light 和 wildcard visual styles
每个 source repo 至少抽查 10 个 absorbed items
整体至少抽查 20 个 skipped 或 duplicate items
抽查所有 new runtime dependency changes
抽查所有 new quality gate relaxations
抽查所有 planner/provider boundary changes
抽查 VF5 fixture benchmark 和 real benchmark claim boundary
本地重新运行 inventory 和 absorption checks
本地重新运行 targeted unit tests
```

验收标准：

```text
reviewer verdict 为 PASS
所有 reviewer requested changes 已修复，或在本文档中明确 rescope
report 记录 reviewer name/session、commands、commit 和 verdict
```

## 6. 执行顺序

必须按顺序执行，不允许跳过：

```text
0. Freeze baseline
1. 实现 inventory schema 和 absorber census command
2. 核实 og-images-generator 与 beautiful-html-templates 的 clone remote、HEAD、license 和 provenance
3. 优先 census beautiful-html-templates，作为 P0 visual asset source
4. census open-design、ppt-master、PosterGen、satori 和 og-images-generator
5. 增加 inventory validation tests
6. 分配 dispositions 并去重，优先处理 beautiful-html-templates 的 canonical theme/layout/component groups
7. 增加 abstraction schema 和 validation tests
8. 创建 absorbed items 的 abstraction records
9. 在第一波资产中实现 beautiful-html-templates-derived templates/themes/components/layout assets
10. 为每批资产增加 CanvasSpec fixtures 和 negative fixtures
11. 集成 planner selection 和 receipts，并证明 planner ownership 没有被外部 planner/provider 接管
12. 对 real image proof 接入 trusted stage_command provider route；未接入前只能声明 fixture/fallback image proof
13. 运行 proof chain 并写入 absorption report
14. 运行 VF5 fixture benchmark；只有配置可信内部 provider 后才运行 real VF5 benchmark
15. 运行 independent review
16. 修复 review findings
17. 重复 review/fix 直到 PASS
18. 经用户确认或确认本批次已有 push 授权后，commit 并 push 到 origin
```

批次规则：

```text
一个 batch 应包含 3-5 个相关 assets，并带上 fixtures 和 receipts
没有 proof 的 asset-only batch 不允许 commit
batch 不能大到 reviewer 无法检查 source traceability
```

## 7. 测试矩阵

定向测试：

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_reference_absorber_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_project_runner_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_visual_acceptance_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_assets_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_vf5_benchmark_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_quality_gate_test.py
python3 -m unittest skills/lark-slides/scripts/svglide_artboard_renderer_test.py
```

semantic asset matcher 测试要求：

```text
当前机制锁定阶段不得少于 24 cases
P0 可验收阶段不得少于 60 cases
榨干完成态不得少于 150 cases，目标约 200 cases
每个 P0 template 至少有 3 个 positive hit cases
每个高风险 template 至少有 2 个 negative mismatch cases
每类 content_shape 至少有 5 个 boundary / rewrite cases
测试必须断言 brief_signals、candidate_templates_considered、candidate_rejection_reasons 和排序结果
```

全量脚本测试：

```bash
python3 -m unittest discover skills/lark-slides/scripts -p '*_test.py'
```

静态检查：

```bash
git diff --check
python3 skills/lark-slides/scripts/svglide_reference_absorber.py check-inventory skills/lark-slides/references/svglide-reference-source-inventory.json
python3 skills/lark-slides/scripts/svglide_reference_absorber.py check-absorption skills/lark-slides/references/svglide-reference-source-inventory.json
```

proof-chain smoke 命令形态：

```bash
python3 skills/lark-slides/scripts/svglide_project_runner.py run <fixture-project> \
  --until visual_acceptance \
  --network-policy fixture \
  --image-backend none
```

backend-affecting proof 命令形态：

```bash
python3 skills/lark-slides/scripts/svglide_project_runner.py run <fixture-project> \
  --until readback \
  --profile production_live \
  --network-policy online \
  --asset-provider trusted:<provider-id> \
  --image-backend stage_command
```

不带 `--profile production_live` 的 `run --until readback` 只能作为普通 readback proof；不能声称 production-live proof，因为默认 production profile 不强制经过 pre_submit_review。

执行 backend-affecting proof 前必须设置：

```bash
export SVGLIDE_IMAGE_STAGE_COMMAND="<trusted internal image materializer command>"
```

VF5 fixture benchmark 命令形态：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/lark-slides/scripts/svglide_vf5_benchmark.py \
  --run-root .tmp/svglide-vf5-benchmark-fixture \
  --planner-provider command \
  --planner-command "python3 skills/lark-slides/scripts/fixtures/svglide_artboard/followup_model_loop/fixture_model_provider.py --stage {stage} --raw-output {raw_output}" \
  --target-slide-count 3 \
  --network-policy fixture \
  --image-backend none \
  --fixture-mode \
  --no-search
```

VF5 real benchmark 命令形态：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 skills/lark-slides/scripts/svglide_vf5_benchmark.py \
  --run-root .tmp/svglide-vf5-benchmark-real \
  --planner-provider command \
  --planner-command "<trusted internal planner command>" \
  --trusted-provider-id <provider-id> \
  --asset-provider trusted:<provider-id> \
  --image-backend stage_command \
  --network-policy online
```

## 8. 完成定义

只有以下条件全部为真，计划才算完成：

```text
六个 reference repositories 都有 inventory coverage
og-images-generator 和 beautiful-html-templates 已记录 remote、HEAD、license、source hashes
beautiful-html-templates P0 inventory 覆盖 34 个 index templates 和 102 张 screenshots，或记录精确 source drift
所有 source items 都有 final disposition
所有 absorbed items 都有 abstraction records
所有 runtime assets 都能 reverse traceability 到 abstraction records
beautiful-html-templates-derived assets 为 planner selection 保留 mood/tone/density/scheme metadata
semantic asset matcher P0 阶段至少 60 cases 通过，榨干完成态至少 150 cases 通过
semantic asset matcher tests 覆盖 positive hit、negative mismatch、boundary/rewrite、style override 和同义改写稳定性
planner ownership 有证据证明 planning artifacts 未被未授权外部 planner/provider 或另一个 agent 生成
所有 runtime assets 都有 positive fixtures
所有 new constraints 都有 negative fixtures
所有 visual quality claims 都有 visual_acceptance evidence
所有 backend-affecting image/chart claims 都有 dry_run/readback evidence
所有 real image claims 都有 trusted stage_command provider evidence 和 validated local image hashes
所有 VF5 fixture benchmark claims 都明确标记 real_benchmark=false
所有 real-model 或 upper-bound visual quality claims 都有 real_benchmark=true 的 VF5 receipt 和 trusted_provider_evidence
agent progress mode 隐藏 internal retries，只展示 milestone artifacts
runner smoke commands 与当前 CLI 参数一致；若启用 progress mode，必须先实现并测试 --progress 或等价机制
absorption report 已生成并提交
independent reviewer PASS 已记录
targeted tests 通过
git diff --check 通过
```

## 9. Reviewer 提示词

把以下内容交给独立 reviewer：

```text
你是 SVGlide reference absorption 的 independent reviewer。

请根据以下文档审查当前 repo state：
skills/lark-slides/references/svglide-reference-absorption-execution-plan.md

你必须检查 source files、inventory、abstraction records、fixtures、receipts 和 tests。
不能把 executor prose 当成证据。

返回一个 verdict：
PASS
REQUEST_CHANGES
BLOCKED

重点检查：
1. 每个 reference source item 是否都有 disposition
2. beautiful-html-templates 是否作为 P0 visual asset source 被完整 inventoried
3. 每个 absorbed item 是否都有 reverse traceability
4. abstractions 是否是 owned SVGlide concepts，而不是 copied runtime artifacts
5. fixtures 是否证明真实链路，而不只是证明文件存在
6. visual/backend claims 是否有 required receipts
7. new assets 是否有实质多样性，而不是 count padding
8. planner selection 是否保留 occasion、mood、tone、formality、density、scheme metadata
9. semantic asset matcher 是否达到当前阶段的 case 数量门槛，并覆盖 positive/negative/boundary/style override
10. planning artifacts 是否遵守 planner ownership rule，没有由未授权外部 planner/provider 或另一个 agent 生成
11. VF5 fixture benchmark 是否明确 real_benchmark=false，没有被写成真实质量 PASS
12. real image / real benchmark claim 是否有 trusted_provider_evidence、stage_command 和 validated local image hash
13. 文档中的 runner 命令是否匹配当前 svglide_project_runner.py CLI
```

## 10. 第一批任务

先只执行 Phase 0 和 Phase 1：

```text
1. 记录 baseline branch、HEAD、dirty files 和 test status
2. 记录 og-images-generator 和 beautiful-html-templates 的 remote、HEAD、license、provenance
3. 创建 svglide-reference-source-inventory.json
4. 创建 svglide_reference_absorber.py，并支持 census 和 check-inventory
5. 优先 census beautiful-html-templates，并证明覆盖 index.json、34 templates、template folders 和 screenshots
6. census 剩余五个 reference repositories
7. 增加 source path existence、hashing、schema validity、priority validity、no pending source family 测试
8. 记录当前 visual_acceptance/VF5/trusted image provider baseline，明确 fixture proof 与 real proof 的边界
9. 记录 semantic asset matcher 当前 case 数，并补到至少 24 cases 后才允许进入 planner selection integration
10. 在开始 asset implementation 前，请 reviewer 审查 census completeness、planner ownership boundary 和真实 provider claim boundary
```

在 reviewer 接受 census 和 inventory 规则前，不允许开始资产实现。
