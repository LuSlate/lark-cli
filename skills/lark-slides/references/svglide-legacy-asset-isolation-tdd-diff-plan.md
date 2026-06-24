# SVGlide 老旧资产隔离 TDD Diff 级开发计划

## 0. 目标

本计划目标是把老旧资产从 SVGlide 默认生成链路中隔离出去，避免用户正常生成时被 legacy theme、legacy palette、旧 P0 template、baseline layout、placeholder image strategy、fixture-only chart strategy 和过宽语义规则污染。

目标不是第一阶段删除所有旧文件，而是先做到：

1. 默认生产链路不再选择 legacy 资产。
2. fixture/debug 链路仍可显式启用 legacy，避免一次性打断历史回归测试。
3. 所有 fallback、placeholder、fixture-only 策略都不能被包装成高质量成功。
4. 每个阶段都有 Red test、Green diff、验证命令和防偏移审查点。

## 1. 当前污染入口

| 资产类型 | 当前入口 | 风险 |
| --- | --- | --- |
| Theme | `skills/lark-slides/scripts/beautiful_template_runtime.py` 中 `LEGACY_THEME_COLORS` | 22 个旧主题全部 active，默认进入候选池 |
| Palette | `beautiful_template_runtime.py` 中 `palette_registry()` | 每个旧主题都生成 `family.<theme_id>`，被 fallback 使用 |
| Template | `beautiful_template_runtime.py` 中 `TEMPLATE_IDS` | 前 15 个旧 P0 模板仍 active |
| Semantic Map | `svglide_semantic_asset_matcher.py` 中“链路”触发 architecture | 普通“生成链路/业务链路”误命中技术架构 |
| Selector | `svglide_theme_template_selector.py` 中 architecture boost | `architecture-blueprint` 仍被强 boost |
| Layout | `svglide-layout-archetypes.json` 中 `svglide-baseline.layouts` | baseline layout 仍 active，且 `architecture-blueprint` 是 catch-all |
| Image Strategy | `svglide-image-strategies.json` 中 baseline placeholder | fixture-only placeholder 易被当成真实图片能力 |
| Chart Strategy | `svglide-chart-strategies.json` 中 baseline chart | fixture-only chart 易被当成真实图表能力 |
| Quality Gate | `svglide_quality_gate.py` 及相关 review/gate | 没有统一阻断 legacy/fallback 成功声明 |

## 2. 处置原则

| 原则 | 具体要求 |
| --- | --- |
| 生产默认只允许可信资产 | 默认 selector 只能选择 `production` 且 `default_selectable=true` 的资产 |
| legacy 可保留但必须隔离 | legacy 只允许 fixture/debug 显式启用 |
| fallback 不能冒充成功 | `stable_fallback`、placeholder image、fixture-only chart 必须降级或阻断 |
| 先隔离再删除 | 第一阶段不删除旧文件，避免破坏 fixture 和历史测试 |
| 测试先行 | 每个行为变化先写失败测试，再实现 |
| 防偏移 | 独立审查者必须检查实现是否仍符合本计划，不允许把 legacy 换个名字继续默认可选 |

## 3. 新资产状态模型

所有 registry 输出和 JSON registry 应统一使用以下字段。第一阶段可在运行时补齐，不要求所有源 JSON 一次改完。

```json
{
  "status": "production | experimental | legacy_debug | deprecated",
  "quality_tier": "trusted | needs_review | fixture_only",
  "default_selectable": true,
  "selection_scope": "production | debug | fixture",
  "legacy_reason": "optional text"
}
```

语义：

| 字段 | 说明 |
| --- | --- |
| `status=production` | 可进入默认用户生成 |
| `status=experimental` | 可在受控实验中使用，默认不进生产 |
| `status=legacy_debug` | 只允许 fixture/debug 显式启用 |
| `status=deprecated` | 不允许新生成使用，只为历史读取存在 |
| `quality_tier=trusted` | 有来源、视觉基准、中文策略和回归验证 |
| `quality_tier=fixture_only` | 只证明 fixture 能跑，不证明真实生成质量 |
| `default_selectable=true` | 默认 selector 可选 |

## 4. 团队并行方案

### 4.1 团队角色

| 角色 | 负责范围 | 产出 | 禁止事项 |
| --- | --- | --- | --- |
| Coordinator / Integrator | 拆任务、合并 diff、跑最终测试 | 集成分支、最终报告 | 不直接绕过失败测试 |
| Runtime Registry Executor | `beautiful_template_runtime.py`、runtime registry tests | production/legacy registry 隔离；按 promotion 结果输出 registry | 不决定哪些 family 可以升一档，不改 selector 逻辑 |
| Theme Promotion Executor | `beautiful-html-template-families.json`、theme 抽象和 promotion tests | 二档 absorbed family 转一档 production theme；维护 promotion gate | 不把 source_inventory_only 直接升 production，不绕过 theme token/视觉证据要求 |
| Beautiful Template Renderer Executor | `artboard_renderer/templates/beautiful/`、`render.mjs`、artboard renderer tests | 把 beautiful template 从 registry 元数据升级为 dedicated executable renderer | 不把通用 `beautifulTemplate()` fallback 标为 production，不改 slide server |
| Template Fidelity Executor | `beautiful_template_fidelity_check.py`、golden/fidelity tests | 建立 screenshot-level fidelity gate 和 receipt | 不用“文件存在/能渲染”替代视觉相似度，不绕开 reference screenshot |
| Font Runtime Executor | `artboard_renderer/font-manifest.json`、typography components、renderer tests | 建立 display/body/label/metric 字体角色 | 不把所有 role 映射回同一个 `SVGlideDefault` |
| Semantic & Selector Executor | `svglide_semantic_asset_matcher.py`、`svglide_theme_template_selector.py` | 语义触发和模板选择修复 | 不改 JSON registry |
| Data Registry Executor | `svglide-layout-archetypes.json`、image/chart strategy JSON | baseline 条目降级、catch-all 拆分 | 不改 Python selector |
| Quality Gate Executor | `svglide_quality_gate.py`、review/gate 脚本 | legacy/fallback 阻断规则 | 不改生成器实现 |
| Fixture Compatibility Executor | fixture/debug allow legacy、历史测试修复 | `include_legacy` debug 通道 | 不让 debug 逻辑泄漏到 production |
| Independent Reviewer / Anti-drift | 对照本文档审查所有 diff | 审查意见、阻断清单 | 不写业务实现 |

### 4.2 并行执行波次

```text
Wave 0: 锁定计划和基线
  Coordinator + Reviewer

Wave 1: Red tests 并行
  Runtime Registry Executor
  Theme Promotion Executor
  Beautiful Template Renderer Executor
  Template Fidelity Executor
  Font Runtime Executor
  Semantic & Selector Executor
  Data Registry Executor
  Quality Gate Executor

Wave 2: Green implementation 并行
  Runtime Registry Executor 修改 runtime registry
  Theme Promotion Executor 补齐二档转一档 theme 抽象
  Beautiful Template Renderer Executor 拆 dedicated renderer 并降级通用 fallback
  Template Fidelity Executor 接入 screenshot fidelity gate
  Font Runtime Executor 接入字体角色
  Semantic & Selector Executor 修改 matcher/selector
  Data Registry Executor 修改 JSON registry
  Quality Gate Executor 修改 gate/review

Wave 3: Fixture compatibility
  Fixture Compatibility Executor 修复历史 fixture/debug 测试

Wave 4: 集成验证
  Coordinator 跑全量相关测试
  Reviewer 做防偏移审查
```

### 4.3 子团队创建提示词

给 Runtime Registry Executor：

```text
你负责 SVGlide legacy asset isolation 的 Runtime Registry 部分。
只允许修改 beautiful_template_runtime.py 及对应 runtime/theme/palette/template 测试。
先写失败测试，证明默认 registry 不包含 legacy themes/templates/palettes。
再实现 production/legacy pool 分离、读取 Theme Promotion Executor 已通过 gate 的 promoted themes，并提供 include_legacy=True 的 debug 通道。
不要决定 family 是否可以 promotion，不要修改 selector、quality gate、JSON registry。
完成后返回 diff 摘要、测试命令、剩余风险。
```

给 Semantic & Selector Executor：

```text
你负责 SVGlide legacy asset isolation 的 Semantic/Selector 部分。
只允许修改 svglide_semantic_asset_matcher.py、svglide_theme_template_selector.py 及对应测试。
先写失败测试：
1. “真实生成链路/业务链路/用户链路”不得触发 technical architecture。
2. WorkBuddy/内部复盘不得命中 architecture-blueprint。
3. 明确“微服务调用链路架构图”仍可命中 architectural-spec。
再实现收窄规则。
不要修改 runtime registry、JSON registry、quality gate。
```

给 Theme Promotion Executor：

```text
你负责 SVGlide legacy asset isolation 的二档转一档 theme promotion。
只允许修改 beautiful-html-template-families.json、beautiful_template_runtime.py 中读取 promotion 的逻辑，以及 theme/palette/knowledge absorption 相关测试。
先写失败测试：
1. blue-professional 这类 absorbed 但缺 theme.* 的 family 不会直接进入 production theme。
2. 补齐 theme.*、palette token、semantic_fit、visual_dna、cjk_policy、usage_policy 后可以进入 production theme。
3. source_inventory_only family 不得 promotion。
再实现 promotion gate。
promotion gate 必须检查 theme_token、source_trace、screenshots/design.md 证据、best_for/avoid_when、CJK 策略、family_usage_policy。
不要修改 selector、quality gate、layout/image/chart registry。
```

给 Data Registry Executor：

```text
你负责 SVGlide legacy asset isolation 的 JSON registry 部分。
只允许修改 svglide-layout-archetypes.json、svglide-image-strategies.json、svglide-chart-strategies.json 及 registry lint 测试。
先写失败测试，证明 production registry 不允许 svglide-baseline.* 条目 active/default_selectable。
再把 baseline 条目标为 legacy_debug/fixture_only，并拆掉 architecture-blueprint catch-all。
不要修改 Python selector。
```

给 Quality Gate Executor：

```text
你负责 SVGlide legacy asset isolation 的 Quality Gate 部分。
只允许修改 quality gate、visual acceptance、strategy review、selection review 相关脚本和测试。
先写失败测试，证明 production run 中出现 legacy asset、stable_fallback、fixture-only image/chart 时不能通过高质量验收。
再实现 gate issue 输出。
不要修改 runtime registry 或 selector。
```

给 Independent Reviewer：

```text
你是防偏移审查者。
只读本文档和所有 diff，不写实现。
逐项检查：
1. 默认生产链路是否仍可能选中 legacy theme/palette/template/layout/image/chart。
2. debug/fixture 兼容是否显式且不可泄漏到 production。
3. fallback 是否还可能被报告为高质量成功。
4. 测试是否覆盖 WorkBuddy、内部复盘、真实生成链路、明确技术架构正例。
5. 二档转一档是否经过 promotion gate，且没有把 source_inventory_only family、缺 theme_token 的 family 或无视觉证据的 family 升为 production。
6. Runtime Registry 是否只是消费 promotion 结果，而不是自行放行 family。
输出阻断项和非阻断建议。
```

## 5. Diff 级 TDD 里程碑

### M0. 建立 legacy 状态词汇和测试基线

目标：让后续所有代码和 JSON 有统一状态语义。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py` | registry 资产必须支持 `status`、`quality_tier`、`default_selectable` 语义 |
| `skills/lark-slides/scripts/svglide_runtime_review_test.py` | 默认 registry 不允许 legacy asset 被标记为 production |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | 新增状态常量和 normalize helper |
| `skills/lark-slides/references/svglide-template-guardrails.json` | 如已有 guardrail，补充 legacy/default_selectable 规则 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py \
  skills/lark-slides/scripts/svglide_runtime_review_test.py
```

防偏移审查点：

```text
不得只加字段但继续让 legacy 进入默认候选。
```

### M1. Theme / Palette 默认候选隔离

目标：默认用户生成不再使用 legacy theme 和 legacy family palette。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_theme_test.py` | `theme_registry()` 默认不包含 `blueprint-technical`、`cobalt-grid`、`glass-neon`、`retro-desktop` |
| `skills/lark-slides/scripts/svglide_palette_selector_test.py` | `palette_registry()` 默认不输出 `family.blueprint-technical` 等 legacy palette |
| `skills/lark-slides/scripts/svglide_brand_palette_resolver_test.py` | 未知品牌不得 stable fallback 到 legacy palette |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | 拆分 `PRODUCTION_THEME_IDS`、`LEGACY_THEME_IDS` |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `all_theme_ids(include_legacy=False)` 默认只返回 production |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `theme_registry(include_legacy=False)` 默认只输出 production |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `palette_registry(include_legacy=False)` 默认只输出 production family palette + brand palette |

建议 production theme 初始 allowlist：

```text
blue-professional derived themes if available
paper-research
swiss-red
stone-architect
forest-editorial
editorial-tritone
ivory-ledger
```

必须 legacy_debug 的高风险主题：

```text
blueprint-technical
cobalt-grid
glass-neon
acid-studio
retro-desktop
sakura-catalog
raw-grid-mono
warm-editorial
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_test.py \
  skills/lark-slides/scripts/svglide_palette_selector_test.py \
  skills/lark-slides/scripts/svglide_brand_palette_resolver_test.py
```

防偏移审查点：

```text
include_legacy=True 只能在 fixture/debug 测试中显式使用。
默认调用路径不得传 include_legacy=True。
```

### M1.5. 二档 beautiful family 转一档 production theme

目标：把高价值但缺少 `theme.*` 映射的 absorbed family 转成正式 production theme，避免生产主题池只靠缩减旧资产而变小。

二档定义：

```text
family.status == "absorbed"
family.claim_level == "svglide_absorbed"
family 已有 template/layout/component/chart/image_strategy 等映射
family 暂无 theme.* 映射
family 具备 design.md / template.json / screenshots / visual_dna / semantic_fit / cjk_policy / family_usage_policy / extension_grammar
```

一档定义：

```text
family.status == "absorbed"
family.claim_level == "svglide_absorbed"
family.svglide_mapping.svglide_asset_ids 包含 theme.*
theme 有稳定 token：colors、semantic_colors、typography、spacing、motif_budget、template_bindings
theme 有适用/禁用语义：semantic_fit.best_for、avoid_when、tones、industries、formality
theme 有中文策略：cjk_policy
theme 有使用策略：family_usage_policy
theme 有视觉证据：screenshot_benchmarks 或 reference_screenshot
```

首批候选：

| family | 当前价值 | 缺口 | 目标 theme |
| --- | --- | --- | --- |
| `blue-professional` | 内部复盘、管理层看板、经营分析最有价值 | 缺 `theme.*` 映射和 theme token | `theme.blue-professional` |

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | absorbed family 缺 `theme.*` 时应被识别为 promotion candidate，而不是 production theme |
| `skills/lark-slides/scripts/svglide_theme_test.py` | `blue-professional` 未补齐 theme token 前不能进入 production theme |
| `skills/lark-slides/scripts/svglide_theme_test.py` | 补齐 `theme.blue-professional` 后可以进入 production theme |
| `skills/lark-slides/scripts/svglide_palette_selector_test.py` | promoted theme 必须生成对应 production palette，且不是 legacy fallback |
| `skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py` | `source_inventory_only` family 不得 promotion |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/beautiful-html-template-families.json` | 为 `blue-professional` 补充 `theme.blue-professional` 映射 |
| `skills/lark-slides/references/beautiful-html-template-families.json` | 补齐 theme token：颜色、语义色、字体、间距、motif budget、template bindings |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | 新增 `promoted_theme_ids()`，从 absorbed family 的 `theme.*` 映射生成 production theme |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `theme_registry()` 合并 promoted themes 和 production hard allowlist |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `palette_registry()` 为 promoted themes 生成 `family.<theme_id>`，并标记 `source_trace` 指向 family |

建议 `theme.blue-professional` 初始 token：

```text
theme_id: blue-professional
source_family: blue-professional
mode: light
background: cream paper / off-white
surface: white or very light blue-gray
primary: electric cobalt blue
accent: restrained cyan or slate
text: deep navy
muted: slate gray
best_for: internal review, business review, executive dashboard, operating review
avoid_when: playful poster, cyberpunk, technical blueprint, food/travel lifestyle
template_bindings: executive-dashboard, trend-grid-report, ledger-briefing, dense-panel-grid
motif_policy: clean professional panels, no decorative random lines
```

#### M1.5.1 blue-professional 升级示例：Red / Green diff

这一节给出 `blue-professional` 从二档转一档的最小可执行 diff。执行者必须按顺序做：先 Red test，再 Green diff，不允许先改实现再补测试。

##### Red diff A：识别 promotion candidate，但不直接进 production

目标：证明当前 `blue-professional` 是高价值二档候选，但在没有 `theme.*` 映射和 theme token 前，不能直接进入 production theme。

文件：`skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py`

新增测试：

```python
def test_blue_professional_is_theme_promotion_candidate(self):
    family = load_family("blue-professional")

    self.assertEqual(family["status"], "absorbed")
    self.assertEqual(family["claim_level"], "svglide_absorbed")
    self.assertIn("template.executive-dashboard", family["svglide_mapping"]["svglide_asset_ids"])
    self.assertNotIn("theme.blue-professional", family["svglide_mapping"]["svglide_asset_ids"])

    candidate = beautiful_template_runtime.theme_promotion_candidate(family)
    self.assertEqual(candidate["source_family"], "blue-professional")
    self.assertEqual(candidate["promotion_status"], "candidate_missing_theme_mapping")
```

文件：`skills/lark-slides/scripts/svglide_theme_test.py`

新增测试：

```python
def test_blue_professional_without_theme_mapping_is_not_production_theme(self):
    registry = beautiful_template_runtime.theme_registry()
    theme_ids = {item["id"] for item in registry["themes"]}

    self.assertNotIn("blue-professional", theme_ids)
```

Red 预期：

```text
新增测试应失败，因为当前还没有 theme_promotion_candidate helper，
且 blue-professional 也没有正式 theme.* 映射。
```

##### Green diff A：补 theme 映射和 theme token

目标：只把 `blue-professional` 这个 absorbed family 升级，不扩大到所有 absorbed family。

文件：`skills/lark-slides/references/beautiful-html-template-families.json`

最小 JSON diff：

```diff
 {
   "template_id": "blue-professional",
   "status": "absorbed",
   "claim_level": "svglide_absorbed",
   "svglide_mapping": {
     "absorbed_as": [
       "component_variant",
       "layout_archetype",
-      "planner_selection_signal",
-      "template_candidate"
+      "planner_selection_signal",
+      "template_candidate",
+      "theme_candidate"
     ],
     "svglide_asset_ids": [
       "chart_strategy.executive-ranking-bars",
       "component.RankingBar",
       "component.SingleAccentMetricCard",
       "component.single_accent_metric_card",
       "layout.executive_dashboard",
-      "template.executive-dashboard"
+      "template.executive-dashboard",
+      "theme.blue-professional"
     ]
   },
+  "theme_token": {
+    "theme_id": "blue-professional",
+    "status": "production",
+    "quality_tier": "trusted",
+    "default_selectable": true,
+    "selection_scope": "production",
+    "source_family": "blue-professional",
+    "mode": "light",
+    "colors": {
+      "background": "#FDFAE7",
+      "surface": "#F5F7FF",
+      "panel": "#FFFFFF",
+      "primary": "#1E2BFA",
+      "accent": "#1E2BFA",
+      "text": "#111111",
+      "muted": "#6B6B6B",
+      "border": "rgba(30, 43, 250, 0.2)",
+      "success": "#059669",
+      "danger": "#DC2626"
+    },
+    "semantic_colors": {
+      "background": "paper",
+      "surface": "professional_panel",
+      "primary": "electric_cobalt",
+      "accent": "electric_cobalt",
+      "text": "deep_ink",
+      "muted": "neutral_gray"
+    },
+    "typography": {
+      "display": "system-sans-cjk-heavy",
+      "body": "system-sans-cjk-regular",
+      "metric": "system-sans-cjk-heavy",
+      "label": "system-sans-cjk-medium"
+    },
+    "template_bindings": [
+      "executive-dashboard",
+      "trend-grid-report",
+      "ledger-briefing",
+      "dense-panel-grid"
+    ],
+    "best_for": [
+      "internal review",
+      "business review",
+      "executive dashboard",
+      "operating review",
+      "investor report"
+    ],
+    "avoid_when": [
+      "playful poster",
+      "cyberpunk",
+      "technical blueprint",
+      "food/travel lifestyle"
+    ],
+    "motif_policy": {
+      "allowed": ["grid", "accent line", "card panels", "paper texture"],
+      "forbidden": ["random decorative lines", "cyber glow", "blueprint node maze"],
+      "budget": "low"
+    }
+  }
 }
```

防偏移要求：

```text
theme_token 必须引用现有 visual_dna.palette_roles、semantic_fit、cjk_policy、family_usage_policy。
不能凭空创造与 screenshots/design.md 不一致的新风格。
```

##### Red diff B：promoted theme 进入 registry 并生成 palette

文件：`skills/lark-slides/scripts/svglide_theme_test.py`

新增测试：

```python
def test_blue_professional_promoted_to_production_theme(self):
    registry = beautiful_template_runtime.theme_registry()
    themes = {item["id"]: item for item in registry["themes"]}

    self.assertIn("blue-professional", themes)
    self.assertEqual(themes["blue-professional"]["status"], "production")
    self.assertEqual(themes["blue-professional"]["quality_tier"], "trusted")
    self.assertTrue(themes["blue-professional"]["default_selectable"])
    self.assertIn("executive-dashboard", themes["blue-professional"]["template_bindings"]["supported_template_ids"])
    self.assertNotIn("blueprint-technical", themes)
```

文件：`skills/lark-slides/scripts/svglide_palette_selector_test.py`

新增测试：

```python
def test_blue_professional_promoted_theme_gets_production_palette(self):
    registry = beautiful_template_runtime.palette_registry()
    palettes = {item["palette_id"]: item for item in registry["palettes"]}

    self.assertIn("family.blue-professional", palettes)
    self.assertEqual(palettes["family.blue-professional"]["status"], "production")
    self.assertEqual(palettes["family.blue-professional"]["quality_tier"], "trusted")
    self.assertTrue(palettes["family.blue-professional"]["default_selectable"])
    self.assertNotIn("family.blueprint-technical", palettes)
```

文件：`skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py`

新增测试：

```python
def test_source_inventory_only_family_cannot_promote_theme(self):
    records = beautiful_template_runtime.promoted_theme_records()
    source_families = {item["source_family"] for item in records}

    self.assertNotIn("8-bit-orbit", source_families)
    self.assertNotIn("block-frame", source_families)
    self.assertNotIn("capsule", source_families)
```

Red 预期：

```text
新增测试应失败，因为当前 beautiful_template_runtime 只从 LEGACY_THEME_COLORS 生成 theme/palette，
还不会读取 family.theme_token。
```

##### Green diff B：runtime 读取 promoted theme

文件：`skills/lark-slides/scripts/beautiful_template_runtime.py`

新增 helper：

```diff
+def theme_asset_ids(family: dict[str, Any]) -> list[str]:
+    mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
+    raw_ids = mapping.get("svglide_asset_ids") if isinstance(mapping.get("svglide_asset_ids"), list) else []
+    return [item for item in raw_ids if isinstance(item, str) and item.startswith("theme.")]
+
+
+def is_promotable_theme_family(family: dict[str, Any]) -> bool:
+    if family.get("status") != "absorbed":
+        return False
+    if family.get("claim_level") != "svglide_absorbed":
+        return False
+    if not theme_asset_ids(family):
+        return False
+    token = family.get("theme_token")
+    if not isinstance(token, dict):
+        return False
+    return bool(token.get("theme_id") and token.get("colors") and token.get("template_bindings"))
+
+
+def theme_promotion_candidate(family: dict[str, Any]) -> dict[str, Any] | None:
+    if family.get("status") != "absorbed" or family.get("claim_level") != "svglide_absorbed":
+        return None
+    if theme_asset_ids(family):
+        return {
+            "source_family": family.get("template_id"),
+            "promotion_status": "has_theme_mapping",
+        }
+    mapping = family.get("svglide_mapping") if isinstance(family.get("svglide_mapping"), dict) else {}
+    asset_ids = mapping.get("svglide_asset_ids") if isinstance(mapping.get("svglide_asset_ids"), list) else []
+    has_runtime_assets = any(str(item).startswith(("template.", "layout.", "component.", "chart_strategy.", "image_strategy.")) for item in asset_ids)
+    if not has_runtime_assets:
+        return None
+    return {
+        "source_family": family.get("template_id"),
+        "promotion_status": "candidate_missing_theme_mapping",
+    }
+
+
+def promoted_theme_records() -> list[dict[str, Any]]:
+    records: list[dict[str, Any]] = []
+    for family in families():
+        if not is_promotable_theme_family(family):
+            continue
+        token = family["theme_token"]
+        colors = token.get("colors") if isinstance(token.get("colors"), dict) else {}
+        theme_id = str(token["theme_id"])
+        records.append(
+            {
+                "id": theme_id,
+                "status": "production",
+                "quality_tier": "trusted",
+                "default_selectable": True,
+                "source_family": family.get("template_id"),
+                "colors": colors,
+                "selection_metadata": {
+                    "scheme": token.get("mode") or "light",
+                    "mood_tags": list(token.get("best_for") or []),
+                    "avoid_for": list(token.get("avoid_when") or []),
+                    "supported_template_ids": list(token.get("template_bindings") or []),
+                    "brand_affinity": [],
+                    "contrast_profile": "normal",
+                    "token_override_policy": "restricted",
+                },
+                "template_bindings": {"supported_template_ids": list(token.get("template_bindings") or [])},
+                "source_trace": [
+                    {
+                        "source": FAMILIES_PATH.as_posix(),
+                        "source_family": family.get("template_id"),
+                        "theme_id": theme_id,
+                    }
+                ],
+            }
+        )
+    return records
```

修改 `theme_registry()`：

```diff
 def theme_registry() -> dict[str, Any]:
+    promoted = promoted_theme_records()
     return {
         "version": "svglide-theme-registry/generated-from-beautiful-family-v1",
-        "themes": [
+        "themes": promoted + [
             {
                 "id": theme_id,
-                "status": "active",
+                "status": "production",
+                "quality_tier": "trusted",
+                "default_selectable": True,
                 "colors": theme_payload(theme_id)["colors"],
                 "selection_metadata": theme_payload(theme_id)["selection_metadata"],
                 "template_bindings": theme_payload(theme_id)["template_bindings"],
             }
-            for theme_id in all_theme_ids()
+            for theme_id in all_theme_ids()
         ],
     }
```

修改 `palette_registry()`：

```diff
 def palette_registry() -> dict[str, Any]:
     palettes: list[dict[str, Any]] = []
+    for theme in promoted_theme_records():
+        colors = theme.get("colors") if isinstance(theme.get("colors"), dict) else {}
+        palettes.append(
+            {
+                "palette_id": f"family.{theme['id']}",
+                "status": "production",
+                "quality_tier": "trusted",
+                "default_selectable": True,
+                "mode": theme.get("selection_metadata", {}).get("scheme") or "light",
+                "colors": colors,
+                "data_series": [colors.get("primary"), colors.get("accent"), colors.get("success"), colors.get("danger")],
+                "source_trace": theme.get("source_trace") or [],
+                "selection_metadata": {
+                    "tone_tags": theme.get("selection_metadata", {}).get("mood_tags", []),
+                    "avoid_for": theme.get("selection_metadata", {}).get("avoid_for", []),
+                    "density": "medium",
+                    "formality": "medium-high",
+                    "industry_tags": ["business", "consulting", "finance", "enterprise software"],
+                    "best_for": theme.get("selection_metadata", {}).get("mood_tags", []),
+                    "brand_affinity": [],
+                },
+            }
+        )
```

实现注意：

```text
上面的 diff 是开发目标，不要求逐字照抄。
但最终行为必须满足测试：
1. blue-professional 来自 family.theme_token。
2. source_inventory_only 不能 promotion。
3. family.blue-professional palette 可默认选择。
4. legacy palette 不可默认选择。
```

##### Red diff C：语义命中 promoted theme

目标：升级后，“内部复盘 / 管理层看板 / 经营分析”应优先命中 `blue-professional`，而不是 legacy 主题。

文件：`skills/lark-slides/scripts/svglide_theme_template_selector_test.py`

新增测试：

```python
def test_internal_business_review_prefers_blue_professional_theme(self):
    result = run_theme_template_selection("生成一份内部业务复盘报告，面向管理层，包含核心指标、风险和行动项")

    self.assertEqual(result["selected_theme_id"], "blue-professional")
    self.assertNotEqual(result["selected_theme_id"], "blueprint-technical")
    self.assertNotEqual(result["selected_template_id"], "architecture-blueprint")
```

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | `score_theme()` 读取 promoted theme 的 `best_for`、`avoid_for`、`template_bindings` |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | internal review / business review / executive dashboard 对 `blue-professional` 加分 |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | technical blueprint / cyberpunk / playful poster 对 `blue-professional` 降分 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py
```

防偏移审查点：

```text
不能硬编码“内部复盘永远选 blue-professional”。
应通过 promoted theme 的 semantic_fit/best_for/template_bindings 产生加分。
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py \
  skills/lark-slides/scripts/svglide_theme_test.py \
  skills/lark-slides/scripts/svglide_palette_selector_test.py \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py
```

防偏移审查点：

```text
不能因为 blue-professional 视觉好就跳过 promotion gate。
不能把 source_inventory_only family 直接升 production。
不能只加 theme 名称，必须补齐 theme token、语义适用范围、禁用范围、中文策略和视觉证据。
promotion 后必须可追溯到 beautiful-html-template family、screenshots 和 absorption record。
```

### M2. Stable fallback 改成安全中性色板

目标：没有品牌/素材色板时，不再从全部 active palette 稳定随机选。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_brand_palette_resolver_test.py` | 未知品牌返回 `neutral-safe` 或明确 `fallback_blocked`，不得返回 legacy palette |
| `skills/lark-slides/scripts/svglide_palette_review_test.py` | `stable_fallback` 结果必须带 `quality_gate_fallback=true` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_brand_palette_resolver.py` | 新增 `neutral_safe_palette()` |
| `skills/lark-slides/scripts/svglide_brand_palette_resolver.py` | `stable_palette_fallback()` 只看 `default_selectable=true` |
| `skills/lark-slides/scripts/svglide_brand_palette_resolver.py` | fallback receipt 增加 `quality_gate_fallback=true` |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_brand_palette_resolver_test.py \
  skills/lark-slides/scripts/svglide_palette_review_test.py
```

防偏移审查点：

```text
不能把 legacy palette 改名为 neutral-safe。
neutral-safe 必须是低风险、低饱和、适合商务报告的保守色板。
```

### M3. 收窄 Semantic Map 中“链路”误触发

目标：裸词“链路”不再触发技术架构。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py` | “真实生成链路”不含 `technical architecture` |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py` | “业务链路/用户链路/增长链路”不含 `architecture` content shape |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py` | “微服务调用链路架构图”仍含 `technical architecture` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher.py` | 从 architecture 触发词中删除裸词“链路” |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher.py` | 新增组合触发：`技术链路`、`调用链路`、`服务链路`、`系统链路`、`架构链路` |
| `skills/lark-slides/scripts/svglide_semantic_asset_matcher.py` | 可选新增 negative context：`真实生成链路`、`业务链路`、`用户链路` |

验证命令：

```bash
python3 -m unittest skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py
```

防偏移审查点：

```text
不能用更宽的“流程/过程/路径”替代“链路”继续误触发 architecture。
```

### M4. Template 默认选择隔离

目标：旧 P0 模板不进入默认 selector；architecture 场景默认只选可信新模板。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | WorkBuddy 不得选择 `architecture-blueprint` |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | 内部复盘不得选择 `architecture-blueprint` |
| `skills/lark-slides/scripts/svglide_template_admission_test.py` | default template registry 不包含 legacy P0 |
| `skills/lark-slides/scripts/svglide_template_fit_check_test.py` | `architecture-blueprint` 只能 debug/fixture admission |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | 拆分 `PRODUCTION_TEMPLATE_IDS` 和 `LEGACY_TEMPLATE_IDS` |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `template_registry(include_legacy=False)` 默认只输出 production |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | 过滤 `default_selectable=false` |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | architecture boost target 从 `{architectural-spec, architecture-blueprint}` 改为 production-only |

第一阶段建议 legacy P0：

```text
cover-hero
comparison-cards
summary-final
section-title
agenda-list
timeline-steps
process-flow
metric-dashboard
quote-focus
image-feature
research-poster
data-story
risk-alert
roadmap-lanes
architecture-blueprint
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py \
  skills/lark-slides/scripts/svglide_template_admission_test.py \
  skills/lark-slides/scripts/svglide_template_fit_check_test.py
```

防偏移审查点：

```text
如果 production pool 暂时不足，不能把 legacy P0 放回默认池。
应减少候选或使用 neutral-safe fallback，而不是恢复污染源。
```

### M5. Layout / Image / Chart JSON registry 降级

目标：baseline 和 fixture-only 策略不能作为 production success 资产。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py` | `svglide-baseline.*` 来源不得 `status=active` 且 `default_selectable=true` |
| `skills/lark-slides/scripts/svglide_assets_test.py` | fixture-only image strategy 不得被视为 real asset |
| `skills/lark-slides/scripts/svglide_chart_verify_test.py` | fixture-only chart strategy 不得声明 backend readback |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/svglide-layout-archetypes.json` | baseline archetypes 改 `legacy_debug` / `fixture_only` / `default_selectable=false` |
| `skills/lark-slides/references/svglide-layout-archetypes.json` | 拆掉 `architecture-blueprint` catch-all，不再绑定 `roadmap-lanes`、`risk-alert`、`quote-focus`、`summary-final` |
| `skills/lark-slides/references/svglide-image-strategies.json` | baseline placeholder 改 `legacy_debug`，保留 forbidden claims |
| `skills/lark-slides/references/svglide-chart-strategies.json` | baseline chart 改 `legacy_debug`，保留 no-readback forbidden claims |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py \
  skills/lark-slides/scripts/svglide_assets_test.py \
  skills/lark-slides/scripts/svglide_chart_verify_test.py
```

防偏移审查点：

```text
不得只改 source_trace 文案隐藏 baseline 来源。
source_trace 必须保留，状态必须降级。
```

### M6. Quality Gate 阻断 legacy / fallback 成功声明

目标：即使前面某处漏了，最终 gate 也不能让 legacy/fallback 伪装为高质量成功。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_quality_gate_test.py` | production receipt 中出现 `legacy_asset_used=true` 时 fail |
| `skills/lark-slides/scripts/svglide_visual_acceptance_test.py` | placeholder-only image 不能 deliverable pass |
| `skills/lark-slides/scripts/svglide_strategy_review_test.py` | fixture-only chart 不能作为 backend chart success |
| `skills/lark-slides/scripts/svglide_selection_review_test.py` | selected legacy theme/template/palette 输出 P0 issue |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_quality_gate.py` | 新增 legacy/fallback issue 聚合 |
| `skills/lark-slides/scripts/svglide_visual_acceptance.py` | 读取 asset strategy status，阻断 placeholder-only |
| `skills/lark-slides/scripts/svglide_selection_review.py` | 识别 legacy selection 并输出 blocker |
| `skills/lark-slides/scripts/svglide_strategy_review.py` | 识别 fixture-only chart/image success claim |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_quality_gate_test.py \
  skills/lark-slides/scripts/svglide_visual_acceptance_test.py \
  skills/lark-slides/scripts/svglide_strategy_review_test.py \
  skills/lark-slides/scripts/svglide_selection_review_test.py
```

防偏移审查点：

```text
gate issue 必须是 blocker/P0，不是 warning。
除非运行模式显式是 fixture/debug。
```

### M7. Fixture / Debug 兼容通道

目标：历史 fixture 仍可跑，但必须显式启用 legacy，并在 receipt 中标记。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | fixture 模式可显式 include legacy |
| `skills/lark-slides/scripts/svglide_golden_suite_test.py` | fixture receipt 必须写 `legacy_asset_used=true` |
| `skills/lark-slides/scripts/svglide_project_runner_test.py` | production mode 不允许隐式 include legacy |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_project_runner.py` | fixture/debug 模式传 `include_legacy=True` |
| `skills/lark-slides/scripts/svglide_artboard_renderer.py` | legacy template receipt 标记 source/status |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | 更新旧 fixture 期望 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py \
  skills/lark-slides/scripts/svglide_golden_suite_test.py \
  skills/lark-slides/scripts/svglide_project_runner_test.py
```

防偏移审查点：

```text
fixture compatibility 不得通过修改默认 registry 达成。
必须是显式 fixture/debug 参数。
```

### M8. E2E 回归场景

目标：用真实失败场景和正例保护未来不回退。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_e2e_dry_run_test.py` | WorkBuddy 不得选 legacy theme/template |
| `skills/lark-slides/scripts/svglide_generation_benchmark_test.py` | “内部业务复盘”命中 professional/report asset，不命中 architecture |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | “香港小吃”不得命中 technical/blueprint |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | “微服务调用链路架构图”命中 `architectural-spec` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| 相关 fixtures | 更新选择 receipt 和 expected output |
| `skills/lark-slides/scripts/fixtures/...` | 只在必要时更新，不做大面积重录 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_e2e_dry_run_test.py \
  skills/lark-slides/scripts/svglide_generation_benchmark_test.py \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py
```

防偏移审查点：

```text
不能通过把测试期望改宽来通过。
必须证明 legacy 不在默认 selection result 里。
```

### M9. Beautiful Template 可执行化与 Fidelity Gate

目标：在完成 legacy 隔离后，继续解决 beautiful 模板“已吸收但未高保真可执行”的问题。最终 production 默认链路必须从“可选元数据”升级为“可执行 renderer + golden fixture + screenshot fidelity receipt”。

M9 前置输入要求：

```text
font_strategy / typography_strategy / text_style_strategy 是后续 dedicated renderer 的前置输入。
没有完成字体与排版抽取契约的模板，不允许进入 default_selectable / production。
后续 renderer/golden/fidelity 必须消费该契约；不能只把字段写入 matrix 或 visual_contract。
只有具备 dedicated renderer、golden fixture、visual_contract、font/typography/text-style receipt、screenshot fidelity pass 的模板，才能进入 production/default_selectable。
```

当前事实：

```text
beautiful 原始模板：34 套
CLI absorbed family：34 套
当前 runtime selectable template：34 套 = 19 个 promoted beautiful template + 15 个静态 production template
当前风险：15 个静态 production template 已可选，但缺少 executable/fidelity contract
当前 dedicated high-fidelity renderer：不足，仍主要依赖 p0-templates.mjs 简化重画或通用 fallback
```

目标状态：

```text
34 套 beautiful 原始模板
-> 34 套全部进入 candidate/evaluation matrix，明确 family_id -> template_id -> renderer_id -> renderer_module -> golden_spec -> reference_screenshot -> promotion_status
-> 只有通过 dedicated renderer + golden fixture + screenshot fidelity pass + visual_contract + selector/gate 接入的模板才进入 production/default selectable
-> 未通过 gate 的模板保持 experimental / needs_review / legacy_debug，不能默认可选
-> default_selectable_count 不做数量承诺，可以小于 34
-> 每套 production/default_selectable template 必须有 reference screenshot fidelity receipt
-> 每套 production/default_selectable template 必须有 font_roles / typography_roles / text_style_roles receipt 证据
-> selector 只选择通过 executable + fidelity contract 的模板
```

M9 执行顺序：

```text
Step 1: 先建立 34/34 candidate registry / evaluation matrix。
Step 2: 再做 1 套闭环样板，例如 blue-professional -> executive-dashboard。
Step 3: 样板跑通 dedicated renderer、golden fixture、screenshot fidelity receipt、selector、quality_gate。
Step 4: 再逐套扩展其他 family。
Step 5: 未完成 fidelity 的模板保持 needs_review / experimental / legacy_debug，并过滤出默认链路。
```

#### M9.1 收紧 production template 定义

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | candidate registry 必须有 34 个 family，不等于 default registry 必须有 34 个 production template |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | 每个 default_selectable template 必须包含真实存在的 `renderer_module`、`golden_spec`、`fidelity_receipt`、`visual_contract`、`fidelity_gate.status=passed` |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | 历史 promoted/static production-like template 如果缺 executable/fidelity contract，不能被 selector 默认选择 |
| `skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py` | `status=production/trusted` 不能单独代表 runtime selectable |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `template_promotion_candidate()` 增加 executable contract 校验 |
| `skills/lark-slides/scripts/beautiful_template_runtime.py` | `is_runtime_selectable()` 增加 `renderer_module`、`fidelity_gate`、`supported_page_types`、`visual_contract` 判断 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py
```

防偏移审查点：

```text
不能通过降低测试断言让旧数据继续伪装 production。
debug/fixture-only 资产可以保留，但必须不能进入默认选择面。
不得把 34 套 family 批量改成 default_selectable=true 来通过测试。
不得为了让测试过而硬补 renderer_module / fidelity_gate / template_token 字段；字段必须对应真实文件和 receipt 证据。
独立审查者必须把“硬补字段伪装 production/default_selectable”列为 P0 阻断项。
```

#### M9.2 拆掉通用 beautiful fallback 的 production 权限

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | production beautiful template 不得只走 `beautifulTemplate(spec, cfg)` 通用 fallback |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | production template 缺 dedicated renderer 时必须失败 |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/artboard_renderer/templates/p0-templates.mjs` | `BEAUTIFUL_TEMPLATE_CONFIGS` 仅保留为 debug/fixture fallback |
| `skills/lark-slides/scripts/artboard_renderer/render.mjs` | `renderTree()` 优先查 dedicated beautiful renderer；production 缺 renderer 直接 fail |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/index.mjs` | 新增 dedicated beautiful renderer registry |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/<template-id>.mjs` | 每套 production template 一个 renderer module |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_artboard_renderer_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py
```

防偏移审查点：

```text
不能把历史 promoted/default-like 模板继续挂在同一个 beautifulTemplate() 大函数上并宣称 production。
新 renderer module 至少要表达该模板独有布局、motif、字体角色和图片槽位。
```

#### M9.3 建立 34 套评估矩阵，并先完成 1 套闭环样板

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | 34 个 beautiful family 都必须出现在 evaluation matrix 中 |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | evaluation matrix 必须显式记录 `family_id -> template_id -> renderer_module -> golden_spec -> reference_screenshot -> promotion_status` |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | `blue-professional -> executive-dashboard` 必须先完成 production 闭环样板 |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | production 样板 template 必须有 golden fixture |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | production 样板 template 必须有 dedicated renderer module |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 新增 34 套评估矩阵 |
| `skills/lark-slides/references/beautiful-html-template-families.json` | 只在闭环通过的 family 上补 production token；未通过的不得硬补 production 字段 |
| `skills/lark-slides/scripts/fixtures/svglide_artboard/golden/executive-dashboard.canvas-spec.json` | 确认或补齐 `blue-professional -> executive-dashboard` 样板 golden spec |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/executive-dashboard.mjs` | 新增或迁移样板 dedicated renderer |

必须在 matrix 中显式列出的 family 清单：

```text
8-bit-orbit
biennale-yellow
block-frame
blue-professional
bold-poster
broadside
capsule
cartesian
cobalt-grid
coral
creative-mode
daisy-days
editorial-tri-tone
emerald-editorial
editorial-forest
grove
long-table
mat
monochrome
neo-grid-bold
peoples-platform
pin-and-paper
pink-script
playful
raw-grid
retro-windows
retro-zine
sakura-chroma
scatterbrain
signal
soft-editorial
stencil-tablet
studio
vellum
```

matrix 每行必须包含：

```text
family_id
template_id
renderer_id
renderer_module
golden_spec
reference_screenshot
fidelity_receipt
source_trace
visual_contract
fidelity_gate
promotion_status = production | experimental | needs_review | legacy_debug
default_selectable
blocking_issues
```

production 行额外必须满足：

```text
status=production
quality_tier=trusted
default_selectable=true
selection_scope=production
supported_page_types 非空
visual_contract 非空
fidelity_gate.status=passed
renderer_executable=true
renderer_module 文件真实存在
golden_spec 文件真实存在
reference_screenshot 文件真实存在
fidelity_receipt 文件真实存在，且引用同一 reference screenshot
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py \
  skills/lark-slides/scripts/beautiful_template_matcher_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py
```

防偏移审查点：

```text
不能把 34 套全部批量标记为 production/default_selectable。
不能只补 JSON 字段而没有 renderer/golden/fidelity 证据。
每套模板必须绑定 source screenshot evidence；缺证据只能 needs_review，不能 production。
blue-professional 样板通过前，不得批量 promotion 其余 family。
candidate_count == 34；default_selectable_count 不强制等于 34。
```

#### M9.4 加入 screenshot-level fidelity gate

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_fidelity_check_test.py` | 空白图、通用卡片图、reference screenshot 缺失、结构相似度低于阈值必须 fail |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | golden render 必须产出 template fidelity receipt |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_fidelity_check.py` | 新增结构型 fidelity checker |
| `skills/lark-slides/references/beautiful-template-fidelity.schema.json` | 新增 receipt schema |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | golden render 后写 `06-check/template-fidelity.json` 和 `receipts/template-fidelity.json` |

fidelity 检查不追求像素完美，但必须覆盖：

```text
主色面积比例
标题 bbox 区域
色块/边框/大图区域分布
留白比例
边缘密度
pHash 或颜色直方图相似度
```

最小可执行阈值：

```json
{
  "viewport": {"width": 960, "height": 540},
  "normalization": ["resize_960x540", "strip_alpha_to_white", "quantize_16_color_bins"],
  "weights": {
    "color_histogram": 0.25,
    "edge_density": 0.2,
    "layout_regions": 0.25,
    "text_bbox": 0.2,
    "whitespace_ratio": 0.1
  },
  "pass_threshold": 0.72,
  "warn_threshold": 0.62
}
```

reference screenshot 选择规则：

```text
每个 family 至少选择 1 张 cover/hero 截图作为 production gate reference。
如果 family 有 content / grid / closing 三类截图，则 matrix 中分别记录 reference role。
首轮 blue-professional 样板使用 beautiful-html-templates/screenshots/blue-professional-1.png。
所有 reference 路径必须来自 source_trace 或 beautiful-html-template-families.json 的 source_screenshots。
```

归一化命令必须可复跑：

```bash
python3 skills/lark-slides/scripts/beautiful_template_fidelity_check.py \
  --rendered <rendered.png> \
  --reference <reference.png> \
  --template-id <template-id> \
  --out 06-check/template-fidelity.json
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_fidelity_check_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py
```

防偏移审查点：

```text
fidelity gate 不能只检查文件存在。
阈值必须能阻断明显不像原图的简化重画。
receipt 必须包含 reference screenshot、render output、score 和 fail reason。
```

#### M9.5 升级 Satori 字体系统

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | renderer 至少注册 `body`、`display`、`label`、`metric` 四类字体角色 |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | `theme.typography.font_roles` 能影响 renderer receipt |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | production beautiful renderer 不能只依赖单一 `SVGlideDefault` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/artboard_renderer/render.mjs` | 新增 `loadFonts()`，支持多字体、多 weight，并输出 `font_receipt` |
| `skills/lark-slides/scripts/artboard_renderer/font-manifest.json` | 新增字体角色 manifest |
| `skills/lark-slides/scripts/artboard_renderer/components/typography.mjs` | 新增 `fontRole()` 等 helper |
| `skills/lark-slides/scripts/artboard_renderer/templates/p0-templates.mjs` | 移除 production 路径中的全局硬编码单字体 |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/*.mjs` | 使用 `fontRole("display")`、`fontRole("body")`、`fontRole("label")`、`fontRole("metric")` |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_artboard_renderer_test.py
```

防偏移审查点：

```text
不能为了通过测试把所有 role 映射到同一个 font face。
CJK fallback 必须明确，不能牺牲中文可读性。
```

#### M9.5.1 beautiful 字体与排版系统吸收

目标：给 34 个 beautiful template candidate 全部补齐 Slide 可用优先的字体与排版系统映射，并让它成为后续 renderer/fidelity 的强约束。该步骤不下载字体、不做 FontBlock、不改 slide server、不把任何模板升 production。

每个 candidate 必须补齐：

```text
font_strategy
typography_strategy
text_style_strategy
```

数据来源必须来自真实 beautiful 源模板：

```text
beautiful-html-templates/templates/<family>/design.md
beautiful-html-templates/templates/<family>/template.html
beautiful-html-templates/templates/<family>/template.json
beautiful-html-templates/screenshots/<family>-1.png 作为视觉校验参考
```

字体优先级：

```text
1. Slide 默认/系统字体
2. Adobe 开源字体：Source Sans Pro / Source Serif Pro / Source Code Pro / 思源黑体 / 思源宋体 / 思源等宽
3. 飞书内嵌开源商用中文字体
4. Google Fonts 仅作为 source_fonts 记录，不作为默认 production 依赖，除非有明确 receipt
```

`font_strategy` 必须包含：

```text
source_fonts
slide_native_preferred
adobe_or_embedded_fallback
cjk_fallback
role_mapping.display/body/label/metric
forbidden
mapping_reason
```

`typography_strategy` 必须包含：

```text
source_typography_tokens
role_mapping.display/body/label/metric
font_size_scale
font_weight_scale
line_height_scale
letter_spacing_scale
word_spacing
paragraph_spacing
text_transform_policy
hierarchy_ratio
max_lines
measure
alignment
wrapping_policy
text_direction
writing_mode
cjk_typography_adjustment
mapping_reason
extraction_confidence
source_refs
```

`text_style_strategy` 必须包含：

```text
bold.source_usage / mapped_weight / allowed_roles
italic.source_usage / mapped_style / fallback_when_unavailable
underline.source_usage / mapped_decoration / fallback_shape
line_through.source_usage / mapped_decoration / fallback_shape
emphasis.color_shift / font_family_switch / weight_shift / style_shift
text_decoration_policy.underline/style/color/thickness
text_decoration_policy.line_through/style/color/thickness
forbidden
extraction_confidence
source_refs
```

抽取证据规则：

```text
每个 strategy 字段必须有 extraction_confidence：
- direct_from_design_md
- css_extracted_from_template_html
- inferred_from_layout
- absent_use_default

如果 extraction_confidence 不是 absent_use_default，必须有 source_refs。
source_refs 每条必须包含 path、selector_or_token、raw_value。
word_spacing / text_direction / writing_mode / max_lines 等源模板可能缺失字段，允许 absent_use_default，但不能伪造成已抽取。
screenshots 只作为视觉校验参考，不能伪造成结构字段来源。
```

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/references/beautiful-template-visual-contract.schema.json` | schema 要求 `font_strategy`、`typography_strategy`、`text_style_strategy` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 34/34 visual_contract 或 matrix candidate 必须有三类 strategy |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | `font_strategy.role_mapping.display/body/label/metric` 必须完整 |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | role_mapping 字体必须来自允许白名单，或被标记为 `source_only` / `requires_download` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 源模板使用 italic / underline / text-decoration / text-transform / letter-spacing 时，contract 必须记录映射或 loss |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 每个 strategy 字段必须有 `extraction_confidence`；非 `absent_use_default` 必须有 `source_refs.path/selector_or_token/raw_value` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | `word_spacing` / `text_direction` / `writing_mode` / `max_lines` 等缺源字段只能标记 `absent_use_default`，不能伪造成 extracted |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 不能把 34 套 family 都映射成同一套 role_mapping 或 typography_strategy |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | default_selectable/production template 的 renderer receipt 必须体现 font_roles、typography_roles、text_style_roles |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | existing dedicated renderer 不能只调用 `fontRole()` 后忽略 `fontWeight` / `lineHeight` / `letterSpacing` / `textTransform` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 34 个 candidate 全部补 `font_strategy`、`typography_strategy`、`text_style_strategy`、`extraction_confidence`、`source_refs` |
| `skills/lark-slides/references/visual-contracts/beautiful/*.json` | 34 份 visual contract 同步写入三类 strategy、抽取置信度和 source refs |
| `skills/lark-slides/references/beautiful-template-visual-contract.schema.json` | 将三类 strategy 纳入 required 和结构校验 |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint.py` | 增加 strategy 完整性、字体白名单、source style mapping、非同质化校验 |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 增加 Red 对应测试 |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | 增加 34/34 strategy 统计和防伪字段测试 |
| `skills/lark-slides/scripts/fixtures/svglide_artboard/golden/*.canvas-spec.json` | 已有 dedicated renderer/golden spec 的模板补 `theme.typography.font_roles`、`role_tokens`、`text_style_roles` |

已有样本 retrofit 规则：

```text
不得回滚已经完成的 dedicated renderer、golden spec、preview、fidelity receipt、selector/gate/visual_contract/fidelity 测试。
已有 renderer/fidelity 的模板只视为“已完成 renderer/fidelity 的一批样本”，不视为 34 套复刻完成。
已有 dedicated renderer 必须检查是否只用了 fontRole()；如果没有显式消费 fontWeight / lineHeight / letterSpacing / textTransform，需要修 renderer，不允许只补 JSON 字段。
已有 renderer 必须表达 source design.md 里的 bold/italic/underline/emphasis 策略；Satori/Slide 无法表达的必须写入 satori_constraints 或 loss_notes。
已有 golden spec 必须补 theme.typography.font_roles 和 typography role tokens，且与 visual_contract/matrix 中策略一致。
已有 fidelity receipt 不因补策略而删除；如果 renderer 改动导致 preview PNG 变化，必须重跑 render 和 fidelity receipt，更新 receipt hash。
如果 fidelity 下降或失败，保留 failure reason，不能伪装 passed。
未完成 renderer 的模板只补三类 strategy，不伪装 renderer/fidelity。
新增 strategy 字段不改变 promotion_status，不自动提升 production/default_selectable。
```

执行规则：

```text
每个 family 必须映射 display/body/label/metric 四个角色。
每个 family 必须有 cjk_fallback 和 cjk_typography_adjustment。
如果某套四个 role 使用同一字体，必须写 justification。
未完成 renderer 的模板只补 contract/matrix，不伪装 renderer/fidelity。
如果 Satori/Slide 字体能力无法表达某个源样式，必须在 satori_constraints 或 loss_notes 中记录，不允许静默丢弃。
```

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py

python3 skills/lark-slides/scripts/beautiful_template_visual_contract_lint.py
```

完成标准：

```text
34/34 candidate 都有 font_strategy / typography_strategy / text_style_strategy。
34/34 candidate 的三类 strategy 都有逐字段 extraction_confidence。
非 absent_use_default 的字段都有 source_refs.path / selector_or_token / raw_value。
已有 renderer 的模板全部已对齐三类策略。
已有 golden spec 的 font_roles 与 visual_contract/matrix 中策略一致。
如有 renderer 变化，相关 preview/fidelity receipt 已重跑并更新 hash。
production/default_selectable 数量不因为本次 retrofit 自动增加。
```

#### M9.5.2 已有 renderer / golden / fidelity 的 retrofit

目标：对已经完成 renderer/fidelity 的样本补齐并回填三类策略，保留已有 dedicated renderer、golden spec、preview、fidelity receipt 和已通过的 selector/gate/visual_contract/fidelity 测试。该步骤只把既有样本纳入字体、排版、文本样式强约束，不把它们视为 34 套复刻完成，也不改变 promotion_status。

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | 每个已有 `renderer_module` 的 matrix 行，其 golden spec 必须包含 `theme.typography.font_roles` 与 `theme.typography.role_tokens.display/body/label/metric` |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | golden spec 的 `role_tokens` 必须与 matrix/visual_contract 的 `typography_strategy.role_mapping` 一致 |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | render receipt 必须输出 `font_roles`、`typography_roles`、`typography_strategy_source`，证明真实渲染链路消费了策略 |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | 已有 dedicated renderer 不能只注册 `fontRole()`；必须通过 receipt 或源码显式体现 `fontWeight`、`lineHeight`、`letterSpacing`、`textTransform` |
| `skills/lark-slides/scripts/beautiful_template_fidelity_check_test.py` | renderer 变化后必须能重新生成 preview PNG 和 fidelity receipt；失败时保留 failure reason，不能伪装 passed |
| `skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py` | strategy 字段补齐不得改变 production/default_selectable 统计 |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/fixtures/svglide_artboard/golden/*.canvas-spec.json` | 对已有 renderer 样本回填 `theme.typography.font_roles`、`role_tokens`、`strategy_source`，并与 matrix/contract 保持一致 |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/*.mjs` | 修复只靠 `fontRole()` 或错误 spread 顺序导致的策略覆盖/忽略；必要时显式设置 weight、line-height、letter-spacing、text-transform |
| `skills/lark-slides/references/receipts/template-fidelity/*.json` | renderer 或 spec 变化后重跑 preview/fidelity，保留新 hash；失败 receipt 必须记录原因 |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 已有 renderer/fidelity 样本继续保留 `renderer_module/golden_spec/fidelity_receipt`；新增 strategy 字段不改变 promotion 状态 |

执行规则：

```text
已有 dedicated renderer / golden spec / preview / fidelity receipt 不得回滚或删除。
已有通过的 selector/gate/visual_contract/fidelity 测试必须继续通过。
已有 renderer/fidelity 样本只算“已完成 renderer/fidelity 的一批样本”，不等于 34 套复刻完成。
已有 renderer 若改动导致 preview PNG 变化，必须重跑对应 fidelity receipt 并更新 hash。
fidelity 下降或失败时保留 failure reason，不能手工改成 passed。
未完成 renderer 的模板只补三类 strategy，不伪装 renderer/golden/fidelity。
新增 strategy 字段不改变 promotion_status，不自动提升 production/default_selectable。
```

完成标准：

```text
34/34 candidate 都有三类 strategy。
已有 renderer 的模板全部与 font_strategy / typography_strategy / text_style_strategy 对齐。
已有 golden spec 的 font_roles、role_tokens 与 visual_contract/matrix 策略一致。
如有 renderer 或 spec 变化，相关 preview/fidelity receipt 已重跑。
production/default_selectable 数量不因为本次 retrofit 增加。
```

防偏移审查点：

```text
不得只补字体名。
不得丢弃字重、字号、行高、字距、大小写、斜体、加粗、下划线、强调策略。
不得把 34 套 family 映射成同一套字体/排版规则。
不得用 Google Fonts 作为 production 默认依赖，除非有明确 receipt。
不得把 strategy 字段存在当成 production 资格。
不得硬补字段伪装 production。
不得没有 source_refs 却标记为 extracted。
不得让 renderer 忽略 typography contract。
```

#### M9.6 selector 只选真正可执行模板

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | selector 不返回缺 renderer/fidelity 的模板 |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | “内部复盘报告”能命中 `blue-professional` 或同类 business/report 模板 |
| `skills/lark-slides/scripts/svglide_theme_template_selector_test.py` | 图片素材不足时避开强图片模板 |
| `skills/lark-slides/scripts/svglide_recipe_selector_test.py` | production profile 不允许选择 debug fallback |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_theme_template_selector.py` | ranking 增加 `renderer_executable`、`fidelity_score`、`page_type_support`、`asset_slot_satisfied`、`avoid_generic_fallback` |
| `skills/lark-slides/scripts/svglide_recipe_selector.py` | recipe 不得把 production 请求路由到 fixture/debug renderer |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py \
  skills/lark-slides/scripts/svglide_recipe_selector_test.py
```

防偏移审查点：

```text
语义匹配不能压过可执行性。
缺图片时不能选择强依赖 hero image 的模板。
production 请求不能路由到 fixture/debug renderer。
```

#### M9.7 visual_dna 变成硬约束

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svg_preflight_test.py` | 标题面积过小、主视觉区域缺失、装饰线穿过文字必须 fail |
| `skills/lark-slides/scripts/svglide_runtime_review_test.py` | 全页卡片同质化、模板 motif 超预算必须 fail |
| `skills/lark-slides/scripts/svglide_visual_acceptance_test.py` | visual contract 不满足时不能 deliverable pass |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svg_preflight.py` | 新增 `title_bbox_contract`、`hero_region_contract`、`forbidden_decoration_overlap` |
| `skills/lark-slides/scripts/svglide_runtime_review.py` | 新增 `motif_budget`、`min_visual_hierarchy_delta`、`max_generic_component_ratio` |
| `skills/lark-slides/scripts/svglide_visual_acceptance.py` | 将 visual contract issue 接入 deliverable pass |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svg_preflight_test.py \
  skills/lark-slides/scripts/svglide_runtime_review_test.py \
  skills/lark-slides/scripts/svglide_visual_acceptance_test.py
```

防偏移审查点：

```text
visual_dna 不能只是描述字段，必须能阻断不符合模板视觉契约的输出。
禁止用“通过 aesthetic_review”替代具体 contract。
```

#### M9.8 runner 接入 template fidelity / adherence gate

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_project_runner_test.py` | `quality_gate` 前必须出现 `template_fidelity` 或 `template_adherence` receipt |
| `skills/lark-slides/scripts/svglide_quality_gate_test.py` | production profile 缺少 template fidelity/adherence receipt 必须 fail |
| `skills/lark-slides/scripts/svglide_quality_gate_test.py` | debug profile 跳过时必须声明 claim boundary |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_project_runner.py` | 在 `preview_lint -> aesthetic_review` 之间插入 `template_fidelity / template_adherence` |
| `skills/lark-slides/scripts/svglide_quality_gate.py` | quality gate 读取 `06-check/template-fidelity.json` 和 `receipts/template-fidelity.json` |
| `skills/lark-slides/scripts/svglide_project_runner.py` | 补 `STAGES`、stage alias、implemented stage、stale invalidation 和 receipt path |
| `skills/lark-slides/scripts/svglide_quality_gate.py` | production profile 将 template fidelity/adherence 纳入 required check |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_project_runner_test.py \
  skills/lark-slides/scripts/svglide_quality_gate_test.py

python3 skills/lark-slides/scripts/svglide_project_runner.py \
  run <fixture-project> \
  --until quality_gate \
  --profile production
```

防偏移审查点：

```text
不能只在 standalone test 里跑 fidelity，真实 runner 必须接入。
没有 fidelity/adherence receipt 时，不能宣称 high-quality / upper-bound visual。
```

### M10. 34 套 Beautiful Template 全部尽力复刻

目标：M9 只解决“未闭环模板不能污染 production 默认链路”；M10 才是把 34 套 beautiful template 逐套复刻成可执行 renderer 的主体工程。M10 的完成标准不是把 34 套硬标成 production，而是每套都完成真实复刻尝试、证据链、golden render 和 fidelity 判定。

目标状态：

```text
34 套 beautiful family
-> 34 份 visual_contract 文件
-> 34 个 dedicated renderer module
-> 34 个 golden canvas spec
-> 34 组原始 screenshot reference binding
-> 34 份真实命令生成的 fidelity receipt
-> 通过 fidelity/adherence gate 的逐个进入 production/default_selectable
-> 未通过的保持 needs_review，并列出失败原因和下一步修复点
```

非目标：

```text
不承诺像素级复刻。
不为了凑数量降低 fidelity 阈值。
不允许把 evaluation stub、generic fallback、p0 通用模板包装成 dedicated renderer。
不允许只有 matrix/registry 字段，没有真实 renderer/golden/screenshot/receipt。
```

#### M10.1 建立 34 份 visual_contract

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 每个 family 必须有 `references/visual-contracts/beautiful/<family>.json` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | 每份 contract 必须绑定 `template.html`、`template.json`、`design.md`、至少 1 张 screenshot |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | contract 必须包含 layout、typography、palette、decorative、image、component、page_type、satori、do_not_simplify 约束 |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | contract 必须包含 `font_strategy`、`typography_strategy`、`text_style_strategy` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | `font_strategy` 必须包含 `source_fonts`、`slide_native_preferred`、`adobe_or_embedded_fallback`、`cjk_fallback`、`role_mapping.display/body/label/metric`、`forbidden`、`mapping_reason` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | `typography_strategy` 必须包含 `source_typography_tokens`、`font_size_scale`、`font_weight_scale`、`line_height_scale`、`letter_spacing_scale`、`text_transform_policy`、`hierarchy_ratio`、`max_lines`、`measure`、`alignment`、`cjk_typography_adjustment` |
| `skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py` | `text_style_strategy` 必须包含 `bold`、`italic`、`underline`、`emphasis`、`forbidden` |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/beautiful-template-visual-contract.schema.json` | 新增 visual contract schema |
| `skills/lark-slides/references/visual-contracts/beautiful/*.json` | 为 34 套 family 生成独立 contract |
| `skills/lark-slides/references/visual-contracts/beautiful/*.json` | 为 34 套 family 补齐 `font_strategy`、`typography_strategy`、`text_style_strategy` |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 每行新增 `visual_contract_path`，并补齐 source evidence 和 screenshot binding |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 每行同步 `font_strategy`、`typography_strategy`、`text_style_strategy`，作为 renderer/fidelity 强约束 |
| `skills/lark-slides/references/beautiful-template-executable-matrix.json` | 区分 `renderer_module/golden_spec/fidelity_receipt` 真实证据字段和 `planned_renderer_module/planned_golden_spec/planned_fidelity_receipt` 计划字段 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py
```

防偏移审查点：

```text
contract 必须来自真实 template/design/screenshot 证据，不得手写空话。
非 production family 也要有 contract，因为 M10 的目标是全部尝试复刻，而不是只保护默认链路。
contract 文件存在不代表 production，production 仍必须等待 renderer/golden/fidelity pass。
未真实落地的 renderer/golden/receipt 只能写入 planned_* 字段；真实字段一旦非空，lint 必须校验文件存在。
font_strategy / typography_strategy / text_style_strategy 必须来自 source evidence，不能只写通用字体名。
不得丢弃字重、字号、行高、字距、大小写、斜体、加粗、下划线、强调策略。
不得把 34 套 family 映射成同一套字体/排版规则。
```

#### M10.2 建立 dedicated renderer module 批量模板

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/svglide_artboard_renderer_test.py` | matrix 中 `promotion_status=production` 的模板必须由 `templates/beautiful/<template-id>.mjs` 渲染 |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | 每个有 renderer module 的 beautiful template 必须能 render SVG/PNG |
| `skills/lark-slides/scripts/svglide_artboard_template_golden_test.py` | renderer contract 的 `source_family`、`reference_screenshot`、`template_id` 必须与 matrix 对齐 |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/<template-id>.mjs` | 每套 family 一个 dedicated renderer |
| `skills/lark-slides/scripts/artboard_renderer/templates/beautiful/index.mjs` | 显式注册 dedicated renderer，不通过 evaluation stub 注册 production |
| `skills/lark-slides/scripts/fixtures/svglide_artboard/golden/<template-id>.canvas-spec.json` | 每套 renderer 对应一个 golden spec |

批量顺序：

```text
Batch A: blue-professional, signal, soft-editorial, coral, bold-poster
Batch B: editorial-tri-tone, editorial-forest, emerald-editorial, broadside, monochrome, vellum
Batch C: cobalt-grid, capsule, cartesian, long-table, raw-grid, neo-grid-bold
Batch D: biennale-yellow, block-frame, mat, peoples-platform, stencil-tablet, studio
Batch E: 8-bit-orbit, creative-mode, daisy-days, playful, retro-windows, retro-zine
Batch F: grove, pin-and-paper, pink-script, sakura-chroma, scatterbrain
```

防偏移审查点：

```text
每个 renderer 必须表达该 family 的独有视觉结构：主色、版式骨架、标题层级、装饰词汇、图文关系。
允许因为 Satori 限制做近似，但必须在 visual_contract.satori_constraints 中写清损失。
禁止所有 renderer 复制同一个通用 pageShell 再换颜色。
```

#### M10.3 每批执行 TDD 闭环

每批 5-6 套模板按固定顺序推进：

```text
1. source audit：读取 template.html / template.json / design.md / screenshots
2. visual_contract：补 contract 并通过 lint
3. renderer red：增加 renderer/golden/fidelity 失败测试
4. renderer green：实现 dedicated renderer
5. golden render：生成 SVG + PNG
6. fidelity receipt：运行 checker，生成 receipt
7. selector/gate：只有 pass 的进入 production/default_selectable
8. independent review：审查是否存在字段补齐、假 receipt、通用 fallback 冒充
```

每套模板只有两种合法阶段结果：

```text
production/default_selectable:
  dedicated renderer 存在
  golden spec 存在
  reference screenshot 存在
  visual_contract 存在
  fidelity receipt 为真实命令生成
  fidelity/adherence passed
  selector/quality_gate 已消费 receipt

needs_review:
  已完成真实复刻尝试
  有 renderer 或失败草稿
  有 golden/render failure 记录
  有 fidelity/adherence failure reason
  default_selectable=false
  如果只是计划路径，必须写 planned_renderer_module / planned_golden_spec / planned_fidelity_receipt
```

防偏移审查点：

```text
不得出现第三种“字段看似齐全但没有证据”的状态。
不得把 fidelity failed 的模板放进 selector 默认链路。
不得把未完成 renderer 的 family 从矩阵中删除来降低分母。
不得把 planned_* 字段复制到真实证据字段里伪装完成。
```

#### M10.4 全量复刻验收报告

Red diff：

| 文件 | 新增测试 |
| --- | --- |
| `skills/lark-slides/scripts/beautiful_template_restoration_report_test.py` | 报告必须覆盖 34/34 family |
| `skills/lark-slides/scripts/beautiful_template_restoration_report_test.py` | 报告必须区分 candidate、attempted、rendered、fidelity_passed、production/default_selectable |
| `skills/lark-slides/scripts/beautiful_template_restoration_report_test.py` | 报告必须列出每个 needs_review 模板的阻断原因 |

Green diff：

| 文件 | 修改 |
| --- | --- |
| `skills/lark-slides/references/beautiful-template-restoration-report.json` | 生成全量复刻报告 |
| `skills/lark-slides/scripts/beautiful_template_restoration_report.py` | 从 matrix、contract、golden、receipt 汇总状态 |

验收指标：

| 指标 | 目标 |
| --- | --- |
| candidate family | 34/34 |
| visual_contract | 34/34 |
| font_strategy | 34/34 |
| typography_strategy | 34/34 |
| text_style_strategy | 34/34 |
| strategy_valid | 34/34 |
| screenshot binding | 34/34 |
| dedicated renderer attempt | 34/34 |
| golden render attempt | 34/34 |
| fidelity receipt attempt | 34/34 |
| production/default_selectable | 只统计 fidelity passed 的数量，不固定为 34 |
| legacy/baseline/default 污染 | 0 |
| hand-written fake receipt | 0 |
| missing-file production field | 0 |

验证命令：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_visual_contract_lint_test.py \
  skills/lark-slides/scripts/beautiful_template_restoration_report_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py \
  skills/lark-slides/scripts/beautiful_template_fidelity_check_test.py \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py \
  skills/lark-slides/scripts/svglide_quality_gate_test.py
```

防偏移审查点：

```text
最终报告不能只报 production 数量，必须同时报 failed/needs_review 明细。
如果某套模板无法基本还原，应保留失败证据和降级理由，而不是删除或伪装通过。
```

## 6. 最小提交边界

建议拆成 8 个 commit，方便回滚。

| Commit | 范围 | 说明 |
| --- | --- | --- |
| 1 | M0 + M1 + M1.5 + M2 | runtime registry、二档转一档和 palette fallback 隔离 |
| 2 | M3 + M4 | semantic matcher 和 template selector 修复 |
| 3 | M5 + M6 | JSON registry 降级和 quality gate 阻断 |
| 4 | M7 + M8 | fixture/debug 兼容和 E2E 回归 |
| 5 | M9.1 + M9.2 + M9.3 + M9.4 | beautiful template production contract、blue-professional 样板闭环、34 套 evaluation matrix、fidelity gate |
| 6 | M9.5 + M9.6 + M9.7 + M9.8 | 字体系统、executable-only selector、visual_dna 硬约束、runner gate 接入 |
| 7 | M10.1 + M10.2 | 34 份 visual_contract、dedicated renderer 批量模板和前两批样板 |
| 8 | M10.3 + M10.4 | 34 套逐批复刻、全量 fidelity 结果和 restoration report |

每个 commit 必须满足：

```text
1. 至少一个 Red test 在实现前失败过。
2. Green 后相关 unittest 通过。
3. Reviewer 对照本文档确认没有偏移。
```

## 7. 最终验收命令

快速验收：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/svglide_theme_test.py \
  skills/lark-slides/scripts/svglide_palette_selector_test.py \
  skills/lark-slides/scripts/beautiful_template_knowledge_absorption_test.py \
  skills/lark-slides/scripts/svglide_brand_palette_resolver_test.py \
  skills/lark-slides/scripts/svglide_semantic_asset_matcher_test.py \
  skills/lark-slides/scripts/svglide_theme_template_selector_test.py \
  skills/lark-slides/scripts/svglide_recipe_selector_test.py \
  skills/lark-slides/scripts/svglide_template_admission_test.py \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py \
  skills/lark-slides/scripts/svglide_artboard_renderer_test.py \
  skills/lark-slides/scripts/svglide_artboard_template_golden_test.py \
  skills/lark-slides/scripts/svglide_quality_gate_test.py
```

扩展验收：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_e2e_dry_run_test.py \
  skills/lark-slides/scripts/beautiful_template_fidelity_check_test.py \
  skills/lark-slides/scripts/svglide_generation_benchmark_test.py \
  skills/lark-slides/scripts/svg_preflight_test.py \
  skills/lark-slides/scripts/svglide_runtime_review_test.py \
  skills/lark-slides/scripts/svglide_visual_acceptance_test.py \
  skills/lark-slides/scripts/svglide_strategy_review_test.py \
  skills/lark-slides/scripts/svglide_selection_review_test.py \
  skills/lark-slides/scripts/svglide_project_runner_test.py \
  skills/lark-slides/scripts/svglide_golden_suite_test.py
```

若涉及 Go CLI 创建链路，还需补跑：

```bash
go test ./shortcuts/slides
```

## 8. 最终验收标准

默认 production 生成必须满足：

```text
0 legacy theme
0 legacy palette
>=1 promoted beautiful-html-template production theme, 首批应包含 blue-professional
0 legacy template
0 baseline layout
0 fixture-only image success claim
0 fixture-only chart success claim
0 naked “链路” architecture trigger
0 stable fallback high-quality success claim
34 beautiful family 有 evaluation matrix 行和明确 promotion_status
所有 default_selectable production template 都有 dedicated renderer module
所有 default_selectable production template 都有 golden canvas spec
所有 default_selectable production template 都有真实 screenshot fidelity receipt
所有 default_selectable production template 都有 visual_contract，且与 template_id/source screenshot 绑定
34/34 beautiful candidate 都有 font_strategy
34/34 beautiful candidate 都有 typography_strategy
34/34 beautiful candidate 都有 text_style_strategy
34/34 beautiful candidate 的字体与排版策略可解释、可验证，并以 Slide 可用字体优先
所有后续 dedicated renderer 必须消费 font/typography/text style strategy，不能只堆 renderer 或只写 fontRole
0 production beautiful template 走通用 beautifulTemplate() fallback
template fidelity/adherence receipt 是 production quality gate 的前置条件
```

debug/fixture 生成允许：

```text
legacy asset used = true
selection_scope = fixture/debug
quality claim = fixture-only/debug-only
不得进入 production quality pass
```

## 9. 风险和回滚

| 风险 | 影响 | 回滚策略 |
| --- | --- | --- |
| production pool 过小 | 某些主题候选减少 | 保留 neutral-safe fallback，不恢复 legacy |
| 历史 fixture 失败 | 测试短期变红 | 通过 `include_legacy=True` 修 fixture，不改 production |
| selector 过严 | 少数明确架构需求召回下降 | 用正例测试补回 `architectural-spec`，不恢复 `architecture-blueprint` |
| JSON registry 引用断裂 | lint 或 fixture 找不到资产 | 保留 legacy 条目和 source_trace，只改状态 |
| gate 过严 | 旧项目无法通过 high-quality | 允许 debug/fixture pass，但 production 必须 fail |

## 10. 执行开始前 checklist

```text
[ ] 当前 worktree status 已记录，避免覆盖用户改动。
[ ] 本文档路径已发给所有子团队。
[ ] 每个子团队只修改自己的文件范围。
[ ] Red tests 先落地并确认失败。
[ ] Green diff 不扩大范围。
[ ] Reviewer 完成防偏移审查后再进入下一波。
```
