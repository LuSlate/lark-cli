# 插件实例 CRUD

Schema 规则 + Create / Update / Delete / Get 四条链路 + 校验重试协议。

---

## Schema 规则

生成 paramsSchema 和 formValue 前必读本章节。

### 变量三层映射

```
调用方传值              paramsSchema 定义变量       formValue 消费变量                         Plugin form.schema 接收
(resume_text="...")  →  (定义: resume_text)     →  ("prompt": "...{{input.resume_text}}...")  →  (prompt 字段)
(article="...")      →  (定义: article)         →  ("content": "{{input.article}}")           →  (content 字段)
```

**关键区分**：
- formValue 的 **key** = Plugin form.schema 的字段名（如 `prompt`、`content`、`fileUrl`）
- formValue 的 **value** 中通过 `{{input.xxx}}` 引用 paramsSchema 定义的变量
- 变量名（paramsSchema）与 form 字段名（form.schema）分属不同层，通常名称不同

### paramsSchema 生成规则

#### 支持的参数类型（仅 4 种）

**文本**：
```json
{ "type": "string", "description": "文本参数描述" }
```

**数组**：
```json
{ "type": "array", "description": "描述", "items": { "type": "string", "description": "元素描述" } }
```

**图片**：
```json
{ "type": "array", "format": "plugin-image-url", "description": "描述", "items": { "type": "string" } }
```

**文件**：
```json
{ "type": "array", "format": "plugin-file-url", "description": "描述", "items": { "type": "string" } }
```

#### 约束

- 只允许 string 和 array 两种 type（图片/文件是 array + format）
- 每个参数**必须**有 type 和 description
- array 类型**必须**有 items 字段
- format 只允许 `plugin-image-url` 或 `plugin-file-url`
- 参考 form.schema 字段的 type 进行定义，保持类型一致（不能给图片/文件类型定义为 string）
- 若 form.schema 字段描述写"不允许使用参数"，则不生成对应 paramsSchema
- 参数设计应体现"收敛输入，扩展能力"：用语义明确的参数名（如 `keywords`、`article_text`），避免过于开放的参数（如直接暴露 `prompt`）

### formValue 生成规则

- **key 必须**对应 form.schema 中定义的字段
- **value** 可以是常量，或 `{{input.xxx}}` 引用 paramsSchema 参数
- **类型一致性**：
  - form.schema type=string → `"字段名": "{{input.param}}"` 或常量字符串
  - form.schema type=array + paramsSchema type=array → **透传**：`"字段名": "{{input.param}}"`（禁止再包数组）
  - form.schema type=array + paramsSchema type=string → **包装**：`"字段名": ["{{input.param}}"]`
- **禁止双层包装**：paramsSchema 已经是 array 时，`["{{input.param}}"]` 会导致运行时 `[url]` → `[[url]]`
- 无法明确赋值的字段留空字符串 `""`，不要硬编码
- **业务枚举参数的动静态判断**：
  - 用户指定单一固定值（如"翻译成英文"）→ formValue 直接填常量
  - 用户列举多个值或暗示可选（如"翻译成中英日韩"）→ 必须生成 paramsSchema 参数
- 若 form.schema 字段描述写"固定填默认值 xxx"→ 直接填固定值，不引用参数

### 插件字段映射表

不同插件的"内容入口"字段各不相同，必须先看 manifest 的 form.schema。下表覆盖全部 AI 插件：

#### 文本类

| 插件 | 内容入口字段 | 映射方式 | 其他常用字段 |
|------|------------|---------|------------|
| ai-text-generate | `prompt` | 用户输入嵌入 prompt 字符串 | `modelID`、`modelParams`（固定值，不引用参数） |
| ai-text-summary | `content` | 直接赋值 `"content": "{{input.xxx}}"` | `requirement`（摘要要求，可常量或参数） |
| ai-translate | `content` | 直接赋值 | `targetLanguage`（单一语言写常量，多语言生成参数） |
| ai-categorization | `textToBeCategorized` | 直接赋值 | `categories`（分类列表，array 类型） |
| ai-text-to-json | `prompt` | 文本嵌入 prompt，无独立 text 字段 | `jsonStructure`（固定结构定义，不引用参数）、`modelID`、`modelParams` |
| ai-search-summary | `prompt` | 用户查询嵌入 prompt | `modelID`、`modelParams`（固定值） |

#### 图片类

| 插件 | 内容入口字段 | 映射方式 | 其他常用字段 |
|------|------------|---------|------------|
| ai-text-to-image | `prompt` | 图片描述嵌入 prompt | `ratio`（宽高比，单一写常量）、`style`（风格，可常量或参数） |
| ai-image-to-image | `prompt` + `images` | 指令嵌入 prompt，图片传 images（image 类型透传） | `strength`（编辑强度，通常常量） |
| ai-image-understanding | `prompt` + `images` | 指令嵌入 prompt，图片传 images（image 类型透传） | `modelID`、`modelParams`（固定值） |
| ai-image-to-json | `prompt` + `images` | 文本嵌入 prompt，图片传 images | `jsonStructure`（固定结构定义）、`modelID`、`modelParams` |
| ai-image-compare | `prompt` + `images` | 对比指令嵌入 prompt，两张图片传 images | — |
| ai-image-matting | `images` | 图片直接传入（image 类型透传） | — |
| ai-background-replace | `images` + `prompt` | 原图传 images，新背景描述嵌入 prompt | — |

#### 文档/语音/其他

| 插件 | 内容入口字段 | 映射方式 | 其他常用字段 |
|------|------------|---------|------------|
| ai-doc-parser | `fileUrl` | file 类型：paramsSchema 为 array → 透传 `"fileUrl": "{{input.xxx}}"`；paramsSchema 为 string → 包装 `"fileUrl": ["{{input.xxx}}"]` | — |
| ai-speech-to-text | `fileUrl` | 同 ai-doc-parser | — |
| ai-speech-synthesis | `text` | 直接赋值 `"text": "{{input.xxx}}"` | `voice`（语音角色，通常常量） |
| web-crawler | `url` | 直接赋值 `"url": "{{input.xxx}}"` | — |

### AI Prompt 编写规则

当插件涉及 AI 能力时，formValue 的 prompt 字段**应包含完整的高质量提示词**，而非简单透传。

#### 禁止的做法

```json
// ❌ 直接透传，无任何预设指令
"prompt": "{{input.prompt}}"
// ❌ 过于简单
"prompt": "根据关键词生成文案：{{input.keywords}}"
// ❌ 文生图/图生图一次调用仅支持一张图
"prompt": "请根据以下要求，生成3张配图"
```

#### Prompt 编写要素

1. **角色设定**：明确 AI 扮演的角色或专业背景
2. **任务描述**：清晰说明要完成的具体任务
3. **输入说明**：标明用户输入将被插入的位置及其含义
4. **输出要求**：明确输出的格式、结构、长度等
5. **风格约束**：指定语气、风格、受众等
6. **质量标准**：设定内容质量的具体标准

#### 各场景 Prompt 模板参考

**文本生成类**：
```json
"prompt": "你是一位资深的[平台名]内容创作专家，擅长撰写高互动率的内容。\n\n请根据以下关键词生成一篇文案：\n关键词：{{input.keywords}}\n\n内容要求：\n1. 标题（15-25字）：使用数字、疑问句或悬念式开头，包含1-2个emoji\n2. 正文（300-500字）：口语化表达，分3-5段，适当使用emoji\n3. 结尾：设置互动问题，包含3-5个话题标签"
```

**图片理解类**：
```json
"prompt": "你是一位专业的图像分析专家。\n\n请对提供的图片进行深度分析：\n1. 基础信息：图片类型、主体内容、场景环境\n2. 细节描述：颜色、构图、关键元素、文字信息\n3. 语义理解：图片传达的含义、情感、潜在用途\n\n{{input.additional_requirements}}\n\n输出要求：描述准确客观，不确定的内容明确标注"
```

**文生图类**：
```json
"prompt": "请生成一张高质量图片：\n\n主题内容：{{input.subject}}\n\n画面要求：\n1. 风格：[根据需求填写]\n2. 构图：[居中/三分法/对称等]\n3. 光线：[自然光/柔和光等]\n4. 色调：[明亮温暖/冷色调等]\n\n质量要求：画面清晰、主体突出、色彩和谐、无变形失真"
```

**数据提取/分析类**：
```json
"prompt": "你是一位数据分析专家，擅长从非结构化内容中提取关键信息。\n\n请从以下内容中提取信息：\n{{input.content}}\n\n提取要求：\n1. 识别关键实体（人名、地点、组织、日期、金额等）\n2. 提取核心事实和数据点\n3. 归纳主要观点或结论"
```

**AI 对话/问答类**：
```json
"prompt": "你是一位[专业领域]专家。请以专业、友好的态度回答用户问题。\n\n用户问题：{{input.question}}\n\n回答要求：准确、完整、通俗易懂、结构化、提供可操作建议"
```

#### 动态参数与预设内容结合

- **用户输入作为"素材"**：prompt 主体应是详细的任务指令，`{{input.xxx}}` 作为素材嵌入
- **避免空泛透传**：即使需要用户自定义 prompt，也应提供默认模板
- **预留扩展性**：可设可选参数（如 `{{input.additional_requirements}}`）供补充需求

### 模板语法限制

- **仅允许** `{{input.参数名}}` 一种语法
- **严禁** `{{#if}}`、`{{#each}}`、`{{#unless}}`、`{{/if}}`、`{{/each}}`、`{{else}}`
- 需要条件逻辑时用自然语言表述

### 一致性铁律

1. **定义的变量必须被引用** — paramsSchema 中定义了 `xxx`，formValue 中至少有一处 `{{input.xxx}}`
2. **引用的变量必须被定义** — formValue 中出现 `{{input.xxx}}`，paramsSchema.properties 中必须有 `xxx`
3. **paramsSchema 允许为空** — 当 formValue 所有字段都是常量时可以是 `{}`
4. **paramsSchema/formValue 不一致 → 后端 actions 为空 → 插件无法调用** — 这是常见致命错误

### ID 生成规则

1. 基于插件实例的名称和描述，设计有业务语义的 ID
2. 格式：小写字母 + 数字 + 短横线（如 `task-text-summary`）
3. 长度不超过 128 字符
4. 必须在当前项目内唯一
5. 与已存在的 ID 冲突时重新生成
6. 未命名时用 `unnamed-plugin-N`

```
名称"数据分析"，描述"分析数据发现趋势"，已存在["data-analysis-1"] → data-analysis-trend-2
名称"智能图片理解"，描述"（测试）" → test-image-understanding-1
名称"未命名插件" → unnamed-plugin-1
```

---

## Create 链路

从用户需求到插件可调用的完整流程。

```
Step 1: +plugin-install --name <key@ver>
Step 2: 设计 paramsSchema / formValue（读上方 Schema 规则）
Step 3: +plugin-instance-create
Step 4: 校验通过？ → 否：走下方「校验失败重试」（max 3 次）
Step 5: 读 manifest + capability JSON
Step 6: 读 lark-apps-plugin-call.md → 生成调用代码
```

### Step 1 — 安装插件包

```bash
lark-cli apps +plugin-install --name @official-plugins/ai-text-generate@1.0.0 --project-path <path>
```

- 鉴权：需要 user token（先 `lark-cli auth login`）
- 已安装同版本会跳过（status=already_installed）
- 失败时 hint 会指示原因（网络/版本不存在/package.json 缺失）

### Step 2 — 设计 paramsSchema 和 formValue

设计前必须先读插件的 form.schema：
```bash
cat <project-path>/node_modules/<pluginKey>/manifest.json
```

根据 form.schema 的字段和用户业务意图，设计：
1. **paramsSchema** — 对外暴露的业务入参（变量定义）
2. **formValue** — 将变量映射到 form.schema 字段（变量消费）
3. **语义化 ID** — 如 `task-text-summary`，小写+短横线，描述业务用途

### Step 3 — 创建实例

```bash
lark-cli apps +plugin-instance-create \
  --id task-text-summary \
  --plugin @official-plugins/ai-text-generate@1.0.0 \
  --name "任务摘要生成" \
  --description "根据任务详情生成摘要" \
  --form-value '{"prompt":"请总结以下任务内容：\n{{input.task_content}}"}' \
  --params-schema '{"type":"object","properties":{"task_content":{"type":"string","description":"任务详情文本"}},"required":["task_content"]}' \
  --project-path <path> \
  --format json
```

大 JSON 场景用 `@file` 传入：先写临时文件，再 `--form-value @form.json --params-schema @schema.json`。

#### 前置检查（CLI 自动执行）

| 检查项 | 失败时 hint |
|--------|-----------|
| package.json 存在 | `run 'lark-cli apps +init'` |
| capabilities 路径可解析 | `use --capabilities-dir or check .env.local` |
| 插件包已安装 | `run '+plugin-install ...' first` |
| 版本匹配 | warning（非 error）：`installed X differs from Y` |
| ID 唯一 | `use --force to overwrite, or choose a different --id` |
| formValue 校验（5 规则） | 逐条列出违规项 |

### Step 4 — 校验失败处理

CLI 返回 `ok: false` + `error.hint` 时，按下方「校验失败重试」处理。

### Step 5 — 读取插件源码

> 创建成功时 CLI 会自动生成 TypeScript 类型文件（`shared/plugin-types.ts`），无需手动调用。

```bash
cat <project-path>/node_modules/<pluginKey>/manifest.json
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

### Step 6 — 生成调用代码

**必读**：[`lark-apps-plugin-call.md`](lark-apps-plugin-call.md)

### Red Flags

| 念头 | 反驳 |
|------|------|
| "我记得这个插件的 schema，不用读 manifest" | manifest 可能更新过，必须每次读 |
| "create 完直接写代码" | 没读 manifest 就写代码 = 猜 actionKey/params |
| "install 之前先 create" | 没装包 manifest 读不到，校验会失败 |
| "formValue 校验报错，我直接编辑 JSON 文件" | 铁律：只能通过 CLI 命令修改 capability JSON |

---

## Update 链路

修改已有实例的 name、formValue、paramsSchema。关键点：改 schema 可能影响已有调用代码。

```
Step 1: +plugin-instance-get --id <id> → 查看现状
Step 2: 设计修改方案（读上方 Schema 规则）
Step 3: +plugin-instance-update
Step 4: 校验通过？ → 否：走下方「校验失败重试」（max 3 次）
Step 5: paramsSchema 变化？ → 变化则扫描代码引用并更新
```

### Step 1 — 查看现状

```bash
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

确认当前的 pluginKey、paramsSchema、formValue，理解要改什么。

### Step 2 — 设计修改方案

同时读取插件 manifest 确认 form.schema 约束：
```bash
cat <project-path>/node_modules/<pluginKey>/manifest.json
```

### Step 3 — 执行更新

```bash
# 只改名
lark-cli apps +plugin-instance-update --id <id> --name "新名称" --project-path <path>

# 改 formValue
lark-cli apps +plugin-instance-update --id <id> --form-value '{"prompt":"新 prompt {{input.text}}"}' --project-path <path>

# 同时改 formValue + paramsSchema
lark-cli apps +plugin-instance-update --id <id> \
  --form-value @form.json --params-schema @schema.json --project-path <path>
```

CLI 自动保留不可变字段（id / pluginKey / pluginVersion / createdAt），只更新你传入的字段 + updatedAt。

### Step 5 — paramsSchema 变化时更新代码

**加/改字段** → 调用方需要传新参数：
1. 读 manifest + 更新后的 capability JSON
2. `grep -rn "load('${id}')" <project-path>/` 找到代码引用
3. 按 [`lark-apps-plugin-call.md`](lark-apps-plugin-call.md) 更新调用代码中的 input 参数

**删字段** → 调用方不再需要传该参数：同上找到引用，移除已删除参数的传入。

**未变化** → 无需改代码，直接完成。

---

## Delete 链路

删除实例前必须先清理代码引用，避免运行时报错。

```
Step 1: +plugin-instance-get --id <id> → 确认实例存在
Step 2: 扫描代码引用 → 有引用则先清理
Step 3: +plugin-instance-delete --id <id>
Step 4: 确认清理完成
```

### 扫描代码引用

```bash
grep -rn "load('${id}')\|load(\"${id}\")" <project-path>/client/ <project-path>/server/ <project-path>/shared/
```

如果有引用：
1. 移除或替换调用代码（视业务逻辑决定是删除功能还是换用其他实例）
2. 清理相关的 import、类型定义、状态变量
3. 如果该实例的结果被持久化到数据库字段，考虑是否需要清理字段或保留历史数据

### 执行删除

```bash
lark-cli apps +plugin-instance-delete --id <id> --project-path <path> --format json
```

删除是幂等的：文件不存在也返回 `deleted: true`，不报错。

### 确认清理

```bash
lark-cli apps +plugin-instance-get --id <id> --project-path <path>
# 应返回 "instance not found"

grep -rn "${id}" <project-path>/client/ <project-path>/server/ <project-path>/shared/
```

---

## Get 链路

查询操作，无副作用。根据查什么路由到不同命令。

| 查什么 | 命令 | 示例 |
|--------|------|------|
| 已声明的插件包及安装状态 | `+plugin-list` | `lark-cli apps +plugin-list --project-path <path>` |
| 所有已建的实例（概览） | `+plugin-instance-list` | `lark-cli apps +plugin-instance-list --project-path <path>` |
| 所有已建的实例（仅 id+name） | `+plugin-instance-list --summary` | 同上加 `--summary` |
| 某个实例的完整配置 | `+plugin-instance-get --id <id>` | `lark-cli apps +plugin-instance-get --id <id> --project-path <path>` |
| 插件的 actions / schema | 直接读 manifest | `cat <project-path>/node_modules/<pluginKey>/manifest.json` |

`+plugin-list` 返回示例：
```json
{
  "ok": true,
  "data": {
    "plugins": [
      {"key": "@official-plugins/ai-text-generate", "version": "1.0.0", "status": "installed"},
      {"key": "@official-plugins/ai-translate", "version": "1.0.0", "status": "declared_not_installed"}
    ]
  }
}
```

`declared_not_installed` → 需要 `+plugin-install` 安装。

**写代码前必做**：不要只靠 instance-get 的输出，还要读插件的 manifest 获取 actions 详情，再按 [`lark-apps-plugin-call.md`](lark-apps-plugin-call.md) 生成调用代码。

---

## 校验失败重试

`+plugin-instance-create` 或 `+plugin-instance-update` 返回 `ok: false` 且 error.type 为 `validation` 时：

```
校验失败 → 解析 error.message 中的每条违规（以 "- " 开头的行）
         → 逐条修正 formValue / paramsSchema
         → 重新调用（create 加 --force / update 直接重调）
         → 最多 3 次，3 次仍失败 → 上报用户
```

### 常见违规及修正方式

| 违规信息 | 原因 | 修正 |
|---------|------|------|
| `forbidden Handlebars syntax at formValue.xxx: {{#if` | formValue 中使用了控制语法 | 改为纯 `{{input.xxx}}` 或自然语言描述 |
| `paramsSchema property "x" type "number" is invalid` | 参数类型不在 string/array 范围 | 改为 `"type": "string"` 或 `"type": "array"` |
| `paramsSchema property "x" is array but missing items` | array 类型缺少 items 定义 | 补上 `"items": {"type": "string"}` |
| `paramsSchema property "x" missing description` | 参数缺少描述 | 补上 `"description": "..."` |
| `{{input.xxx}} at formValue.yyy is not defined in paramsSchema` | formValue 引用了未定义的变量 | 在 paramsSchema.properties 中补充定义，或修正拼写 |
| `paramsSchema property "x" is never referenced` | 定义了变量但 formValue 中没有引用 | 在 formValue 中补充 `{{input.x}}`，或从 paramsSchema 移除 |

### 修正要点

1. **不要直接编辑 capability JSON 文件** — 必须通过 CLI 命令重新提交
2. **Create 重试用 `--force`** — 覆盖上一次失败写入的文件
3. **Update 直接重新调用** — 会覆盖现有配置
4. **保持 paramsSchema 和 formValue 的一致性** — 修一个通常要同步改另一个
5. **3 次失败后不要继续猜** — 上报用户并附带完整错误，让用户决策
