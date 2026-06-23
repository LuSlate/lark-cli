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
  Semantic & Selector Executor
  Data Registry Executor
  Quality Gate Executor

Wave 2: Green implementation 并行
  Runtime Registry Executor 修改 runtime registry
  Theme Promotion Executor 补齐二档转一档 theme 抽象
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

## 6. 最小提交边界

建议拆成 4 个 commit，方便回滚。

| Commit | 范围 | 说明 |
| --- | --- | --- |
| 1 | M0 + M1 + M1.5 + M2 | runtime registry、二档转一档和 palette fallback 隔离 |
| 2 | M3 + M4 | semantic matcher 和 template selector 修复 |
| 3 | M5 + M6 | JSON registry 降级和 quality gate 阻断 |
| 4 | M7 + M8 | fixture/debug 兼容和 E2E 回归 |

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
  skills/lark-slides/scripts/svglide_template_admission_test.py \
  skills/lark-slides/scripts/svglide_selection_metadata_lint_test.py \
  skills/lark-slides/scripts/svglide_quality_gate_test.py
```

扩展验收：

```bash
python3 -m unittest \
  skills/lark-slides/scripts/beautiful_template_e2e_dry_run_test.py \
  skills/lark-slides/scripts/svglide_generation_benchmark_test.py \
  skills/lark-slides/scripts/svglide_visual_acceptance_test.py \
  skills/lark-slides/scripts/svglide_strategy_review_test.py \
  skills/lark-slides/scripts/svglide_selection_review_test.py \
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
