# 插件实例 Schema 规则

生成 paramsSchema 和 formValue 前必读本文件。

## 变量三层映射

```
调用方传值              paramsSchema 定义变量       formValue 消费变量                         Plugin form.schema 接收
(resume_text="...")  →  (定义: resume_text)     →  ("prompt": "...{{input.resume_text}}...")  →  (prompt 字段)
(article="...")      →  (定义: article)         →  ("content": "{{input.article}}")           →  (content 字段)
```

**关键区分**：
- formValue 的 **key** = Plugin form.schema 的字段名（如 `prompt`、`content`、`fileUrl`）
- formValue 的 **value** 中通过 `{{input.xxx}}` 引用 paramsSchema 定义的变量
- 变量名（paramsSchema）与 form 字段名（form.schema）分属不同层，通常名称不同

## paramsSchema 生成规则

### 支持的参数类型（仅 4 种）

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

### 约束

- 只允许 string 和 array 两种 type（图片/文件是 array + format）
- 每个参数**必须**有 type 和 description
- array 类型**必须**有 items 字段
- format 只允许 `plugin-image-url` 或 `plugin-file-url`
- 参考 form.schema 字段的 type 进行定义，保持类型一致（不能给图片/文件类型定义为 string）
- 若 form.schema 字段描述写"不允许使用参数"，则不生成对应 paramsSchema
- 参数设计应体现"收敛输入，扩展能力"：用语义明确的参数名（如 `keywords`、`article_text`），避免过于开放的参数（如直接暴露 `prompt`）

## formValue 生成规则

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

## 插件字段映射表

不同插件的"内容入口"字段各不相同，必须先看 manifest 的 form.schema：

| 插件 | 内容入口字段 | 映射方式 |
|------|------------|---------|
| ai-text-generate | `prompt` | 用户输入嵌入 prompt 字符串 |
| ai-text-to-json | `prompt` | 文本嵌入 prompt，无独立 text 字段 |
| ai-text-summary | `content` | 直接赋值 `"content": "{{input.xxx}}"` |
| ai-translate | `content` | 直接赋值 |
| ai-categorization | `textToBeCategorized` | 直接赋值 |
| ai-speech-synthesis | `text` | 直接赋值 |
| ai-image-understanding | `prompt` + `images` | 图片传 images，指令嵌入 prompt |
| ai-doc-parser | `fileUrl` | array 类型透传 `"fileUrl": "{{input.xxx}}"` |

## AI Prompt 编写规则

当插件涉及 AI 能力时，formValue 的 prompt 字段**应包含完整的高质量提示词**，而非简单透传。

### 禁止的做法

```json
// ❌ 直接透传，无任何预设指令
"prompt": "{{input.prompt}}"
// ❌ 过于简单
"prompt": "根据关键词生成文案：{{input.keywords}}"
// ❌ 文生图/图生图一次调用仅支持一张图
"prompt": "请根据以下要求，生成3张配图"
```

### Prompt 编写要素

1. **角色设定**：明确 AI 扮演的角色或专业背景
2. **任务描述**：清晰说明要完成的具体任务
3. **输入说明**：标明用户输入将被插入的位置及其含义
4. **输出要求**：明确输出的格式、结构、长度等
5. **风格约束**：指定语气、风格、受众等
6. **质量标准**：设定内容质量的具体标准

### 各场景 Prompt 模板参考

#### 文本生成类
```json
"prompt": "你是一位资深的[平台名]内容创作专家，擅长撰写高互动率的内容。\n\n请根据以下关键词生成一篇文案：\n关键词：{{input.keywords}}\n\n内容要求：\n1. 标题（15-25字）：使用数字、疑问句或悬念式开头，包含1-2个emoji\n2. 正文（300-500字）：口语化表达，分3-5段，适当使用emoji\n3. 结尾：设置互动问题，包含3-5个话题标签"
```

#### 图片理解类
```json
"prompt": "你是一位专业的图像分析专家。\n\n请对提供的图片进行深度分析：\n1. 基础信息：图片类型、主体内容、场景环境\n2. 细节描述：颜色、构图、关键元素、文字信息\n3. 语义理解：图片传达的含义、情感、潜在用途\n\n{{input.additional_requirements}}\n\n输出要求：描述准确客观，不确定的内容明确标注"
```

#### 文生图类
```json
"prompt": "请生成一张高质量图片：\n\n主题内容：{{input.subject}}\n\n画面要求：\n1. 风格：[根据需求填写]\n2. 构图：[居中/三分法/对称等]\n3. 光线：[自然光/柔和光等]\n4. 色调：[明亮温暖/冷色调等]\n\n质量要求：画面清晰、主体突出、色彩和谐、无变形失真"
```

#### 数据提取/分析类
```json
"prompt": "你是一位数据分析专家，擅长从非结构化内容中提取关键信息。\n\n请从以下内容中提取信息：\n{{input.content}}\n\n提取要求：\n1. 识别关键实体（人名、地点、组织、日期、金额等）\n2. 提取核心事实和数据点\n3. 归纳主要观点或结论"
```

#### AI 对话/问答类
```json
"prompt": "你是一位[专业领域]专家。请以专业、友好的态度回答用户问题。\n\n用户问题：{{input.question}}\n\n回答要求：准确、完整、通俗易懂、结构化、提供可操作建议"
```

### 动态参数与预设内容结合

- **用户输入作为"素材"**：prompt 主体应是详细的任务指令，`{{input.xxx}}` 作为素材嵌入
- **避免空泛透传**：即使需要用户自定义 prompt，也应提供默认模板
- **预留扩展性**：可设可选参数（如 `{{input.additional_requirements}}`）供补充需求

## 模板语法限制

- **仅允许** `{{input.参数名}}` 一种语法
- **严禁** `{{#if}}`、`{{#each}}`、`{{#unless}}`、`{{/if}}`、`{{/each}}`、`{{else}}`
- 需要条件逻辑时用自然语言表述

## 一致性铁律

1. **定义的变量必须被引用** — paramsSchema 中定义了 `xxx`，formValue 中至少有一处 `{{input.xxx}}`
2. **引用的变量必须被定义** — formValue 中出现 `{{input.xxx}}`，paramsSchema.properties 中必须有 `xxx`
3. **paramsSchema 允许为空** — 当 formValue 所有字段都是常量时可以是 `{}`
4. **paramsSchema/formValue 不一致 → 后端 actions 为空 → 插件无法调用** — 这是常见致命错误

## ID 生成规则

1. 基于插件实例的名称和描述，设计有业务语义的 ID
2. 格式：小写字母 + 数字 + 短横线（如 `task-text-summary`）
3. 长度不超过 128 字符
4. 必须在当前项目内唯一
5. 与已存在的 ID 冲突时重新生成
6. 未命名时用 `unnamed-plugin-N`

### 示例

```
名称"数据分析"，描述"分析数据发现趋势"，已存在["data-analysis-1"] → data-analysis-trend-2
名称"智能图片理解"，描述"（测试）" → test-image-understanding-1
名称"未命名插件" → unnamed-plugin-1
```
