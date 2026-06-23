# SVGlide 设计资产组合系统执行总纲

Updated: 2026-06-23

本文件整合原三处 current 文档职责：

```text
svglide-design-asset-composition-tdd-plan.md：Diff 级 TDD 改造计划
svglide-design-asset-parallel-team.md：并行团队与防偏移审查
INDEX.md：当前文档入口
```

后续执行以本文件为唯一 current source of truth；`INDEX.md` 只负责入口登记。

## 1. 目标

把 SVGlide 从“模板命中后临场生成页面”，改造成可测试、可解释、可回归的设计资产组合系统。

目标链路：

```text
问题语义
=> deck recipe
=> template family
=> style_pack
=> density mode
=> component variant
=> image treatment
=> page plan
=> Satori HTML/CSS/SVG
=> 本地预览或提交 slide server
```

关键原则：

- `template family` 负责页面结构，不承担全部视觉差异。
- `style_pack` 负责视觉气质，不能只靠 `palette`。
- `component variant` 负责同一结构下的表达差异。
- `image treatment` 负责真实图片、产品截图、图表优先级。
- `diversity gate` 只控制跨主题或同批样本的重复度，不能破坏单份 deck 的统一性。
- 42 条 Base 样本是 golden case，不是 42 个硬编码模板。

## 1.1 参考仓库启发与反照搬边界

本计划吸收 `beautiful-html-templates` 和 `ppt-master` 的做法，但不照搬任一方案。

### beautiful-html-templates 的启发

`beautiful-html-templates` 的关键价值不是模板数量，而是每个模板都有可被 agent 路由的 metadata：

```text
mood
tone
best_for
avoid_for
density
formality
scheme
slide_count
```

对 SVGlide 的启发：

```text
所有设计资产都必须可描述、可索引、可解释。
template family / style_pack / component variant / image treatment 都要有 metadata。
selector 不能只输出“选了哪个模板”，必须输出为什么选。
```

不能照搬的地方：

```text
beautiful 的模板是封闭视觉系统，选中后不鼓励改色。
SVGlide 需要同一个 template family 支持多套 style_pack。
因此 SVGlide 不能把 template 当最终视觉，只能把 template 当结构家族。
```

### ppt-master 的启发

`ppt-master` 明确禁止模板 fuzzy match，把模糊理解放到 Strategist 阶段，再通过 `design_spec.md` / `spec_lock.md` 锁定颜色、字体、图片策略、页面节奏。

对 SVGlide 的启发：

```text
生成前必须先有 selection metadata。
style_pack / image_treatment / page rhythm 需要 deck 级锁定。
每页生成不能重新发明主色、字体、图片策略和装饰语言。
```

不能照搬的地方：

```text
ppt-master 的 Eight Confirmations 是强用户确认。
SVGlide 链路不再需要 confirm_plan。
因此 SVGlide 应该自动选择 + 输出 receipt + 低置信度 fail closed，而不是每次打断用户确认。
```

### SVGlide 采用的第三种路线

```text
beautiful 的模板 metadata
+ ppt-master 的设计锁定机制
+ SVGlide 自己的 recipe/style_pack/component/image strategy 组合层
+ golden tests + diversity gate
```

明确不做：

```text
不优先建设 embedding / KNN / vector search。
不把 semantic routing 写成不可测试的 LLM 感觉判断。
不让 template fuzzy match 直接决定最终视觉。
```

## 2. 非目标

本计划不做以下事情：

- 不改 `slide_engine`。
- 不改 `slide server` 的 create-svg 接口。
- 不引入新的线上提交流程。
- 不把 42 条样本各自做成固定模板。
- 不允许 fallback 到 `svglide baseline theme` 后继续假装命中成功。
- 不允许用随机装饰线、随机几何图案填充视觉差异。

## 3. 当前落点

主要改动位于 CLI 的 lark-slides skill：

```text
/Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private/skills/lark-slides
```

执行前注意：

```text
skills/lark-slides/scripts/svglide_project_runner.py
skills/lark-slides/scripts/svglide_project_runner_test.py
```

这两个文件当前可能已有未提交改动。实际执行时必须先读现有 diff，再决定如何合并，不能覆盖。

## 4. 核心数据模型

### 4.1 deck recipe

`deck recipe` 表示“这类问题应该用什么叙事结构和设计资产组合”。

示例：

```json
{
  "recipe_id": "internal_business_review",
  "display_name": "内部业务复盘",
  "intent_tags": ["复盘", "经营分析", "业务汇报"],
  "content_shape": ["问题-原因-动作", "数据-洞察-决策"],
  "audience": ["内部管理层", "业务团队"],
  "template_family_candidates": ["blue-professional", "editorial-tri-tone"],
  "style_pack_candidates": ["corporate_blue_data", "teal_amber_growth"],
  "density_modes": ["data-heavy", "executive-summary"],
  "component_slots": ["kpi_strip", "metric_cards", "timeline", "risk_matrix"],
  "image_treatment_candidates": ["chart-first", "online-evidence-image"],
  "avoid_when": ["儿童教育", "游戏介绍", "纯故事叙述"]
}
```

### 4.2 style_pack

`style_pack` 是组合视觉皮肤，不只是颜色。

示例：

```json
{
  "style_pack_id": "product_ai_indigo_cyan",
  "palette_id": "indigo_cyan",
  "typography_id": "tech_editorial",
  "background_system_id": "clean_panel_grid",
  "chart_palette_id": "ai_product_chart",
  "image_treatment_id": "real_product_screenshot",
  "decoration_policy_id": "minimal_grid_only",
  "component_variant_bias": [
    "metric_cards",
    "comparison_matrix",
    "timeline"
  ]
}
```

### 4.3 命中等级

```text
L1: 明确命中已有 deck recipe，可直接生成。
L2: 命中相近 recipe，需要轻量组合资产。
L3: 只命中资产族，需要生成 new_recipe_proposal，并进入 review。
L4: 无法可靠匹配，fail closed，不允许静默套 baseline。
```

## 5. Diff 级 TDD 里程碑

### M1. 新增资产组合注册表

Red diff：

```text
+ skills/lark-slides/scripts/svglide_recipe_selector_test.py
+ skills/lark-slides/scripts/fixtures/svglide_recipe_matching/cases_42.json
```

测试要求：

- 每条 case 至少能解析出 `expected_primary_type`。
- 每条 case 的期望 recipe 必须存在。
- 每个 recipe 必须声明 template/style_pack/component/image treatment。
- 每个 recipe/style_pack 必须有可路由 metadata，至少覆盖 `mood`、`tone`、`best_for`、`avoid_for`、`density`、`formality`。
- 不允许通过 case_id 或 prompt 子串硬编码 42 条样本。

Green diff：

```text
+ skills/lark-slides/references/svglide-deck-recipe-registry.schema.json
+ skills/lark-slides/references/svglide-deck-recipe-registry.json
+ skills/lark-slides/references/svglide-style-pack-registry.schema.json
+ skills/lark-slides/references/svglide-style-pack-registry.json
+ skills/lark-slides/references/svglide-semantic-route-cases.schema.json
+ skills/lark-slides/references/svglide-semantic-route-cases.json
+ skills/lark-slides/scripts/svglide_recipe_selector.py
```

验证命令：

```bash
cd /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private
python3 skills/lark-slides/scripts/svglide_recipe_selector_test.py
```

### M2. 42 条样本 golden routing

Red diff：

```text
~ skills/lark-slides/scripts/fixtures/svglide_recipe_matching/cases_42.json
~ skills/lark-slides/scripts/svglide_recipe_selector_test.py
```

测试输入结构：

```json
{
  "case_id": "W17",
  "prompt": "内部业务复盘...",
  "expected_primary_type": "经营 / 业务 / 数据分析与复盘",
  "expected_recipe_ids": ["internal_business_review"],
  "min_match_level": "L2"
}
```

Green diff：

```text
~ skills/lark-slides/scripts/svglide_recipe_selector.py
```

输出结构：

```json
{
  "recipe_id": "internal_business_review",
  "match_level": "L1",
  "confidence": 0.86,
  "signals": {
    "intent": ["复盘", "业务"],
    "audience": ["内部"],
    "content_shape": ["数据分析", "行动项"]
  }
}
```

验收标准：

```text
42/42 可路由
L1 + L2 = 42
L4 = 0
每条都有 recipe/template/style_pack/component/image_treatment
```

### M3. 42 条以外泛化测试

Red diff：

```text
+ skills/lark-slides/scripts/fixtures/svglide_recipe_matching/out_of_sample.json
~ skills/lark-slides/scripts/svglide_recipe_selector_test.py
```

覆盖用例：

```text
豆包 App 竞品分析
智谱与 MiniMax 对比
香港小吃文化介绍
粤语文化介绍
AI 教育产品融资 BP
新能源供应链投资分析
城市治理年度复盘
医疗培训课件
```

Green diff：

```text
~ skills/lark-slides/scripts/svglide_recipe_selector.py
```

验收标准：

```text
out_of_sample 不要求全部 L1
L2/L3 必须能解释命中原因
L4 必须 fail closed，并输出缺失信号
不得自动套 svglide baseline theme
```

### M4. 接入 template / style_pack / component / image treatment

Red diff：

```text
~ skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
~ skills/lark-slides/scripts/beautiful_template_matcher_test.py
~ skills/lark-slides/scripts/svglide_selection_review_test.py
```

新增断言：

```text
selection metadata 必须包含：
- deck_recipe_selection
- template_family_selection
- style_pack_selection
- density_mode_selection
- component_variant_selection
- image_treatment_selection
```

Green diff：

```text
~ skills/lark-slides/scripts/svglide_semantic_asset_matcher.py
~ skills/lark-slides/scripts/beautiful_template_matcher.py
~ skills/lark-slides/scripts/svglide_selection_review.py
```

验证命令：

```bash
python3 skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
python3 skills/lark-slides/scripts/beautiful_template_matcher_test.py
python3 skills/lark-slides/scripts/svglide_selection_review_test.py
```

### M5. plan contract 和 preflight 防偏移

Red diff：

```text
~ skills/lark-slides/scripts/svg_preflight_test.py
~ skills/lark-slides/scripts/svglide_quality_gate_test.py
```

失败条件：

```text
缺少 deck_recipe_selection
缺少 style_pack_selection
缺少 image_treatment_selection
缺少 deck 级 style lock
同一 deck 内出现多套无解释主色
出现 disallowed decoration policy
出现 baseline theme fallback
真实图片需求被降级为本地生成图片
```

Green diff：

```text
~ skills/lark-slides/references/svglide-plan.schema.json
~ skills/lark-slides/references/svglide-plan.contract.md
~ skills/lark-slides/scripts/svg_preflight.py
~ skills/lark-slides/scripts/svglide_quality_gate.py
```

验收标准：

```text
本地预览和真实提交共用同一 selection metadata
preflight 能在生成前拦住明显错误组合
quality gate 能在生成后拦住视觉偏移
每页生成只能消费 deck 级 selection/style lock，不能逐页重新发明视觉语言
```

### M6. runner 写入可审计 receipt

Red diff：

```text
~ skills/lark-slides/scripts/svglide_project_runner_test.py
```

测试要求生成目录中存在：

```text
02-plan/selection-metadata.json
02-plan/recipe-routing-receipt.json
```

Green diff：

```text
~ skills/lark-slides/scripts/svglide_project_runner.py
```

receipt 示例：

```json
{
  "prompt": "豆包 App",
  "recipe_id": "consumer_ai_product_analysis",
  "template_family": "blue-professional",
  "style_pack": "product_ai_indigo_cyan",
  "density_mode": "product-showcase",
  "image_treatment": "real-product-screenshot",
  "match_level": "L2",
  "confidence": 0.73
}
```

执行前必须先处理当前 dirty diff，避免覆盖已有 runner 改动。

### M7. diversity gate

Red diff：

```text
+ skills/lark-slides/scripts/svglide_diversity_gate_test.py
+ skills/lark-slides/scripts/fixtures/svglide_diversity_gate/repeated_combinations.json
```

测试规则：

```text
deck 内：
- style_pack 必须统一
- 主色系统必须统一
- page layout/component 可以变化

跨 deck 或同批样本：
- template_id + style_pack_id + layout_variant + component_variant 重复度过高时失败
- 允许同 template family，不允许同一完整组合过度重复
```

Green diff：

```text
+ skills/lark-slides/scripts/svglide_diversity_gate.py
~ skills/lark-slides/scripts/svglide_quality_gate.py
```

验收标准：

```text
不会再出现一份 PPT 四页四种主色
不会让 42 条样本看起来都是同一套蓝色模板换字
```

### M8. 文档和运行手册

Red diff：

```text
~ skills/lark-slides/SKILL.md
+ skills/lark-slides/references/svglide-design-asset-routing.md
```

Green diff：

```text
更新 SVG route 文档，明确：
- recipe selection 是生成前必经阶段
- style_pack 不是 palette 的别名
- 本地预览和 live create 必须使用同一 selection metadata
- L3 new_recipe_proposal 如何进入后续资产扩容
```

验证：

```bash
rg -n "recipe selection|style_pack|diversity gate|selection-metadata" skills/lark-slides
```

## 6. 总体验收命令

```bash
cd /Users/bytedance/bd-projects/workspaces/SVGlide/.worktrees/cli-svglide-svg-private

python3 skills/lark-slides/scripts/svglide_recipe_selector_test.py
python3 skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
python3 skills/lark-slides/scripts/beautiful_template_matcher_test.py
python3 skills/lark-slides/scripts/svglide_selection_review_test.py
python3 skills/lark-slides/scripts/svg_preflight_test.py
python3 skills/lark-slides/scripts/svglide_quality_gate_test.py
python3 skills/lark-slides/scripts/svglide_diversity_gate_test.py
python3 skills/lark-slides/scripts/svglide_project_runner_test.py
```

## 7. 完成定义

满足以下条件才算完成：

- 42 条 golden case 全部可路由。
- 每条都有可解释的 recipe/template/style_pack/component/image_treatment。
- 42 条以外的主题至少能 L2/L3 解释性命中。
- L4 不允许继续生成。
- 不再出现无来源装饰线、随机几何图案。
- 不再出现本地预览默认不加图片的问题。
- 同一 deck 内视觉统一，不同主题之间视觉有可感知差异。
- 本地预览和真实提交链路使用同一份 selection metadata。
- 所有新增逻辑有测试覆盖，且测试先红后绿。

## 8. 并行团队

### A. 架构负责人

职责：

- 维护总目标和边界。
- 决定 recipe/style_pack/component/image_treatment 的模型边界。
- 合并各执行者的 diff。
- 确保不改 `slide_engine` 和 `slide server`。

不可做：

- 不直接跳过测试改实现。
- 不允许把 42 条 case 硬编码成 42 套模板。

### B. Golden Case 负责人

职责：

- 把 42 条样本整理成 `cases_42.json`。
- 定义一级类型、期望 recipe、最低命中等级。
- 补充 out-of-sample 泛化用例。

产物：

```text
skills/lark-slides/scripts/fixtures/svglide_recipe_matching/cases_42.json
skills/lark-slides/scripts/fixtures/svglide_recipe_matching/out_of_sample.json
```

### C. Registry 负责人

职责：

- 建立 deck recipe schema/registry。
- 建立 style_pack schema/registry。
- 复用现有 template、palette、component、asset strategy registry。

产物：

```text
skills/lark-slides/references/svglide-deck-recipe-registry.schema.json
skills/lark-slides/references/svglide-deck-recipe-registry.json
skills/lark-slides/references/svglide-style-pack-registry.schema.json
skills/lark-slides/references/svglide-style-pack-registry.json
```

### D. Selector 负责人

职责：

- 实现 recipe selector。
- 支持 L1/L2/L3/L4 命中等级。
- 输出可解释 signals。

产物：

```text
skills/lark-slides/scripts/svglide_recipe_selector.py
skills/lark-slides/scripts/svglide_recipe_selector_test.py
```

### E. 链路集成负责人

职责：

- 把 recipe/style_pack 接入现有 semantic asset matcher。
- 接入 beautiful template matcher。
- 接入 selection review。
- 接入 runner receipt。

产物：

```text
skills/lark-slides/scripts/svglide_semantic_asset_matcher.py
skills/lark-slides/scripts/beautiful_template_matcher.py
skills/lark-slides/scripts/svglide_selection_review.py
skills/lark-slides/scripts/svglide_project_runner.py
```

执行注意：

- `svglide_project_runner.py` 当前可能已有 dirty diff，必须先读再改。

### F. Gate / QA 负责人

职责：

- 接入 preflight。
- 接入 quality gate。
- 新增 diversity gate。
- 确保本地预览和 live create 共享 selection metadata。

产物：

```text
skills/lark-slides/scripts/svg_preflight.py
skills/lark-slides/scripts/svglide_quality_gate.py
skills/lark-slides/scripts/svglide_diversity_gate.py
```

### G. 独立审查者 / 防偏移负责人

职责：

- 只审查，不实现。
- 每轮检查是否偏离本总纲。
- 检查是否出现 baseline fallback、随机装饰、无图片策略、破坏 deck 统一性。
- 检查测试是否真的覆盖 42 条和 out-of-sample。

审查清单：

```text
是否仍然只靠 template 承担视觉变化？
是否新增了 style_pack，而不是只改 palette？
是否 deck 内统一、deck 间差异？
是否 L4 fail closed？
是否本地预览和真实提交共用 metadata？
是否没有改 slide_engine？
是否没有把 42 条 case 写死成 42 个模板？
是否所有新增行为都有 red test？
```

### H. 文档负责人

职责：

- 更新 `SKILL.md`。
- 新增设计资产路由说明。
- 更新 current docs index。

产物：

```text
skills/lark-slides/SKILL.md
skills/lark-slides/references/svglide-design-asset-routing.md
docs/current/INDEX.md
```

### I. 参考资产产品化负责人

职责：

- 从 `beautiful-html-templates` 抽取可复用的 metadata 设计，而不是照搬封闭模板规则。
- 从 `ppt-master` 抽取 design spec / spec lock 思路，而不是照搬强用户确认。
- 把参考仓库启发转成 SVGlide 可测试字段、fixture 和 gate。
- 检查 selector 是否退化成不可解释的“LLM 感觉判断”。
- 检查是否有人把 template fuzzy match 当成最终视觉决策。

产物：

```text
skills/lark-slides/references/svglide-reference-asset-lessons.md
skills/lark-slides/references/svglide-deck-recipe-registry.json
skills/lark-slides/references/svglide-style-pack-registry.json
```

不可做：

```text
不引入 embedding / KNN / vector search 作为第一阶段依赖。
不把 beautiful 的“选中模板后不改色”照搬到 SVGlide。
不把 ppt-master 的 Eight Confirmations 恢复成 confirm_plan。
```

## 9. 最大化并行方式

### 第一批并行

可以同时做：

```text
B. Golden Case 负责人：整理 cases_42/out_of_sample
C. Registry 负责人：建 schema/registry
I. 参考资产产品化负责人：输出参考仓库启发转化清单
G. 独立审查者：建立防偏移 checklist
H. 文档负责人：准备文档骨架
```

依赖关系：

```text
Selector 依赖 B + C 的初版产物
Registry 字段依赖 I 的转化清单
Gate 依赖 selection metadata 结构稳定
Runner 依赖 selector/matcher 输出稳定
```

### 第二批并行

可以同时做：

```text
D. Selector 负责人：实现 recipe selector
E. 链路集成负责人：准备 matcher/review 接口改造
F. Gate / QA 负责人：先写 failing tests
I. 参考资产产品化负责人：审 selector 是否正确吸收 beautiful/ppt-master
G. 独立审查者：审第一批 diff
```

### 第三批并行

可以同时做：

```text
E. 链路集成负责人：接入 matcher/review/runner
F. Gate / QA 负责人：接入 preflight/quality/diversity
H. 文档负责人：补运行手册
I. 参考资产产品化负责人：补参考资产扩容方法
G. 独立审查者：审集成行为是否偏移
```

## 10. 推荐执行顺序

```text
1. 先写 cases_42 和 registry schema 的红测。
2. 再补 registry 最小数据让测试变绿。
3. 写 selector 红测，覆盖 L1/L2/L3/L4。
4. 实现 selector。
5. 接入 matcher/review。
6. 接入 preflight/quality/diversity gate。
7. 最后接 runner receipt。
8. 跑全量测试。
9. 独立审查者做最终防偏移审查。
```

## 11. 每轮交付标准

每轮执行者提交前必须给出：

```text
改了哪些文件
新增了哪些测试
哪些测试先红后绿
是否影响 slide_engine/slide server
是否改变本地预览/live create 的边界
是否新增 baseline fallback
是否正确吸收 beautiful/ppt-master，还是误照搬
```

独立审查者每轮必须给出：

```text
通过 / 打回
打回原因
偏离了哪条计划
需要补哪条测试
是否可以进入下一轮
```

参考资产产品化负责人每轮必须给出：

```text
beautiful 的 metadata 哪些已进入 registry/schema/test
ppt-master 的 style lock 哪些已进入 selection metadata/gate
哪些参考做法被明确拒绝，原因是什么
是否出现 embedding/KNN/vector search 的非必要前置依赖
```

## 12. 并行风险

### 风险 1：数据模型先被不同执行者改散

处理：

```text
Registry 负责人先锁定 schema。
其他执行者只消费 schema，不私自扩字段。
```

### 风险 2：selector 为了过 42 条测试写硬编码

处理：

```text
必须同时跑 out_of_sample。
审查者检查 prompt substring 到 case_id 的硬编码。
```

### 风险 3：diversity gate 破坏 deck 统一性

处理：

```text
明确 deck 内统一，deck 间差异。
测试里必须覆盖“一份 deck 多页同 style_pack”的正例。
```

### 风险 4：本地预览和 live create 分叉

处理：

```text
runner receipt 必须成为共享输入。
本地预览不得走单独的降级主题。
```

### 风险 5：图片策略再次被跳过

处理：

```text
image_treatment_selection 是必填项。
真实产品/地点/人物主题必须默认 online evidence image。
无图只能作为显式策略，而不是本地预览默认行为。
```

### 风险 6：误照搬参考仓库

处理：

```text
beautiful 只吸收 metadata routing，不吸收模板封闭不可组合。
ppt-master 只吸收 design lock，不恢复强用户 confirm_plan。
第一阶段不引入 embedding / KNN / vector search。
```

## 13. 最终验收

团队整体完成必须满足：

```text
42 条 golden case 全部通过
out_of_sample 全部给出 L1/L2/L3/L4 明确解释
L4 fail closed
beautiful/ppt-master 启发已落成 schema/test/gate，而不是只写在文档里
无 baseline theme 静默 fallback
无随机装饰线
同一 deck 视觉统一
跨主题视觉可区分
本地预览和 live create 共用 selection metadata
所有新增路径都有测试
独立审查者最终通过
```
