# lark-apps 插件管理

妙搭应用的插件（Plugin）体系：插件包安装、插件实例 CRUD、调用代码生成。

**触发关键词**：用户要实现 AI生文/AI生图/AI翻译/AI摘要/AI分类/图片理解/图片识别/图片抠图/图片对比/图生图/语音识别/语音合成/文档解析/网页抓取/文本转JSON/搜索摘要 等能力时，或提到 Plugin/PluginInstance/Capability/插件安装/卸载/创建实例时加载本 Skill。

## 核心概念

- **插件包（Plugin Package）**：npm 格式的功能包，安装到 `node_modules/`，含 `manifest.json` 描述 actions 和 form.schema。
- **插件实例（Plugin Instance / Capability）**：基于插件包创建的业务配置，存储在 `capabilities/{id}.json`，定义 `paramsSchema`（业务入参）和 `formValue`（表单映射，通过 `{{input.xxx}}` 引用 paramsSchema 参数）。
- **变量映射**：`调用方传值 → paramsSchema 定义变量 → formValue 消费变量 {{input.xxx}} → Plugin form.schema 接收`。

### ⚠️ 插件包 ≠ npm 包（必读）

| | 插件包 | npm 依赖 |
|------|------|------|
| 安装命令 | `lark-cli apps +plugin-install` | `npm install` |
| 写入字段 | `package.json` → **`actionPlugins`** | `package.json` → `dependencies` / `devDependencies` |
| 用途 | 妙搭平台 AI 能力 | 项目依赖库 |
| **禁止** | ❌ 不能用 `npm install` 装插件包 | ❌ 不能用 `+plugin-install` 装普通依赖 |

两套机制完全独立。插件包虽然放在 `node_modules/`，但由 `actionPlugins` 字段管理，**与 npm dependencies 无关**。混淆会导致运行时找不到插件。

## 确认项目上下文

所有本地 plugin 命令需要 `--project-path`。按以下顺序确认：

1. cwd 有 `.spark/meta.json` → 直接用 cwd
2. 用户给了 app_id → `grep -rl "app_id值" --include="meta.json" .` 搜索工作区
3. 用户给了应用名称 → `find . -maxdepth 2 -type d -name "名称"` 定位
4. 都没有 → 询问用户要操作哪个应用
5. 找不到 → 提示先 `lark-cli apps +create` + `apps +init`

确认后，所有后续命令统一传 `--project-path <路径>`。

## 命令速查

### 插件包管理

| 命令 | 功能 | 鉴权 |
|------|------|------|
| `+plugin-install --name <key@ver>` | 下载 tgz → 解压到 node_modules → 更新 package.json | user token |
| `+plugin-install`（无 --name） | 批量安装 package.json actionPlugins 中声明的所有插件 | user token |
| `+plugin-uninstall --name <key>` | 删除 node_modules/{key} + 移除 actionPlugins 条目 | 无 |
| `+plugin-list` | 列出已声明插件及安装状态（installed / declared_not_installed） | 无 |

### 插件实例 CRUD

| 命令 | 功能 | 鉴权 |
|------|------|------|
| `+plugin-instance-create --plugin <key@ver> --name <n> --form-value <json\|@file>` | 校验 + 写 capability JSON | 无 |
| `+plugin-instance-update --id <id> [--name] [--form-value]` | 更新实例可变字段 | 无 |
| `+plugin-instance-delete --id <id>` | 删除实例（幂等） | 无 |
| `+plugin-instance-get --id <id>` | 读取单个实例 | 无 |
| `+plugin-instance-list [--summary]` | 列出所有实例 | 无 |

所有本地命令支持 `--project-path`、`--capabilities-dir`、`--format json`、`--dry-run`。

---

## AI 插件目录（17 个）

### 插件能力速查

#### 文本类

| 插件 key | 能力 | 输出模式 | 输出类型 | 适用场景 |
|---------|------|---------|---------|---------|
| `ai-text-generate` | 文本生成 | stream | 流式文本 `content` | 文案、报告、对话、问答 |
| `ai-text-summary` | 文本摘要 | stream | 流式文本 `summary` | 长文本摘要、要点提取 |
| `ai-translate` | 多语言翻译 | stream | 流式文本 `translation` | 中英日韩等多语言互译 |
| `ai-categorization` | 文本分类 | unary | `{categories: string[]}` | 打标签、情感分析、内容分类 |
| `ai-text-to-json` | 文本→结构化 JSON | unary | `{字段名: 值}` | 信息提取、表单自动填充（最多 20 字段） |
| `ai-search-summary` | 搜索摘要 | stream | 流式文本 `content` | 联网搜索 + 摘要生成 |

#### 图片类

| 插件 key | 能力 | 输出模式 | 输出类型 | 适用场景 |
|---------|------|---------|---------|---------|
| `ai-text-to-image` | 文生图 | unary | `{images: string[]}` | 根据文本描述生成图片 |
| `ai-image-to-image` | 图生图 | unary | `{images: string[]}` | 图片编辑、风格转换 |
| `ai-image-understanding` | 图片理解 | stream | 流式文本 `content` | 图片描述、问答、OCR |
| `ai-image-to-json` | 图片→结构化 JSON | unary | `{字段名: 值}` | 图片信息提取（单步直达） |
| `ai-image-compare` | 图片对比 | stream | 流式文本 `content` | 两张图片差异分析 |
| `ai-image-matting` | 抠图 | unary | `{images: string[]}` | 去背景、主体提取 |
| `ai-background-replace` | 换背景 | unary | `{images: string[]}` | 替换图片背景 |

#### 文档/语音/其他

| 插件 key | 能力 | 输出模式 | 输出类型 | 适用场景 |
|---------|------|---------|---------|---------|
| `ai-doc-parser` | 文档解析 | unary | **纯文本 string** | PDF/Word/Excel 文本提取 |
| `ai-speech-to-text` | 语音识别 | unary | **纯文本 string** | 音频转文字 |
| `ai-speech-synthesis` | 语音合成 | unary | 音频 URL string | 文字转语音 |
| `web-crawler` | 网页抓取 | unary | 网页内容 string | 抓取指定 URL 的页面内容 |

> 所有插件 key 使用时需加 `@official-plugins/` 前缀，如 `@official-plugins/ai-text-generate@1.0.0`。

**不支持**（需用户通过 GUI 手动配置）：飞书发消息、飞书创建群组、飞书多维表格、飞书审批、飞书 aPaaS。

### 用户意图 → 插件选择

当用户表达需求但没指定插件时，按此表选择：

| 用户表述 | 对应插件 | 类型 |
|---------|---------|------|
| "AI 写文案 / 生成文本 / 帮我写" | `ai-text-generate` | 流式生成 |
| "总结 / 摘要 / 提取要点" | `ai-text-summary` | 流式生成 |
| "翻译成XX / 多语言" | `ai-translate` | 流式生成 |
| "分类 / 打标签 / 情感分析" | `ai-categorization` | 结构化 |
| "从文本提取字段 / 文本转结构化" | `ai-text-to-json` | 结构化 |
| "搜索并总结 / 联网查询" | `ai-search-summary` | 流式生成 |
| "AI 生图 / 文生图 / 生成图片" | `ai-text-to-image` | 图片 |
| "图片编辑 / 风格转换 / 图生图" | `ai-image-to-image` | 图片 |
| "识别图片 / 图片问答 / 看图说话" | `ai-image-understanding` | 流式生成 |
| "从图片提取信息 / 图片转结构化" | `ai-image-to-json` | 结构化 |
| "对比两张图 / 图片差异" | `ai-image-compare` | 流式生成 |
| "抠图 / 去背景" | `ai-image-matting` | 图片 |
| "换背景 / 替换背景" | `ai-background-replace` | 图片 |
| "解析文档 / 读 PDF / 读 Word" | `ai-doc-parser` | 文本提取 |
| "语音合成 / 文字转语音 / 朗读" | `ai-speech-synthesis` | 音频 |
| "语音识别 / 音频转文字" | `ai-speech-to-text` | 文本提取 |
| "抓取网页 / 爬取页面" | `web-crawler` | 文本提取 |

### 设计原则

#### 原子化

**一个插件实例只做一件事**。不同输出类型、不同业务语义必须创建独立的插件实例。

```
✅ 正确：需要生成标题 + 生成正文
   → 创建两个 ai-text-generate 实例：title-generator、content-generator
   → 各自有独立的 prompt 和 paramsSchema

❌ 错误：把标题和正文塞进同一个实例的 prompt
   → 输出混在一起，无法分别渲染
```

同一个官方插件可以创建多个实例，每个实例服务不同的业务场景。

#### 链式调用

部分插件输出是纯文本，不能直接产出结构化数据。需要链式组合时：

```
文档 → 结构化：ai-doc-parser → ai-text-to-json（两步）
图片 → 结构化：ai-image-to-json（单步直达，优先用这个）
语音 → 结构化：ai-speech-to-text → ai-text-to-json（两步）
```

| 上游插件 | 上游输出 | 需要结构化时 | 下游插件 |
|---------|---------|------------|---------|
| `ai-doc-parser` | 纯文本 | 必须接下游 | `ai-text-to-json` |
| `ai-speech-to-text` | 纯文本 | 必须接下游 | `ai-text-to-json` |
| `ai-image-understanding` | 流式文本 | 优先用 `ai-image-to-json` 单步完成 | `ai-text-to-json` |

代码中的链式传递：上游插件输出在代码中作为下游插件实例的入参传入，每个实例的 paramsSchema 是独立的接口契约。

#### 流式标注

使用 stream 输出模式的插件，功能设计中需注明涉及流式渲染，代码中使用 `callStream` + `normalizeStream`。

---

## 意图路由

根据用户意图选择对应操作，**必须读取对应文件后再执行**：

| 用户意图 | 必读 |
|---------|------|
| 新增插件能力（"加个 AI 翻译""接入文本生成"） | [`lark-apps-plugin-crud.md`](lark-apps-plugin-crud.md) § Create |
| 修改已有实例配置（"改一下 prompt""换个模型"） | [`lark-apps-plugin-crud.md`](lark-apps-plugin-crud.md) § Update |
| 删除实例（"去掉这个能力""不需要了"） | [`lark-apps-plugin-crud.md`](lark-apps-plugin-crud.md) § Delete |
| 查看实例详情 / 列出已有实例 / 查已装插件 | [`lark-apps-plugin-crud.md`](lark-apps-plugin-crud.md) § Get |
| 写插件调用代码（Create/Update 完成后的下一步） | [`lark-apps-plugin-call.md`](lark-apps-plugin-call.md) |

## 铁律

1. **只能通过 CLI 命令修改 capability JSON 文件** — 禁止 Agent 直接用文件编辑工具写 `capabilities/*.json`，必须通过 `+plugin-instance-create` / `+plugin-instance-update` / `+plugin-instance-delete` 操作，确保校验和格式一致性。
2. **先装包再建实例** — `+plugin-instance-create` 前必须确保插件包已安装（`+plugin-install`），否则校验会因读不到 manifest 而失败。
3. **校验失败走重试协议** — Create / Update 返回校验错误时，按 [`lark-apps-plugin-crud.md`](lark-apps-plugin-crud.md) § 校验失败重试 处理：解析 hint → 修正 → 重试（max 3 次）。
4. **写代码前读源码** — Create 完成后，Agent 应读取 `node_modules/{pluginKey}/manifest.json` 和 `capabilities/{id}.json` 理解插件能力，再按 [`lark-apps-plugin-call.md`](lark-apps-plugin-call.md) 生成调用代码。禁止凭记忆猜测 actionKey / inputSchema / outputMode。
5. **不要在 formValue 中使用 Handlebars 控制语法** — 仅允许 `{{input.xxx}}`，严禁 `{{#if}}` / `{{#each}}` / `{{else}}` 等。
6. **禁止用 `npm install` 代替 `+plugin-install`** — 插件包写入 `actionPlugins`，npm 写入 `dependencies`，两套独立机制。混用会导致插件无法被识别。
