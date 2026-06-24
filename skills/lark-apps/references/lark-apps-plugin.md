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

## 铁律

1. **只能通过 CLI 命令修改 capability JSON** — 禁止 Agent 直接编辑 `capabilities/*.json`，必须通过 `+plugin-instance-create` / `+plugin-instance-update` / `+plugin-instance-delete` 操作。
2. **先装包再建实例** — `+plugin-instance-create` 前必须确保插件包已安装（`+plugin-install`）。
3. **禁止用 `npm install` 代替 `+plugin-install`** — 插件包写入 `actionPlugins`，npm 写入 `dependencies`，两套独立机制。
4. **操作前必读仓库 Skill** — 执行任何插件 CRUD 或生成调用代码前，必须先读取项目中的插件 Skill。

## 详细指引（读取仓库 Skill）

插件目录、用户意图映射、Schema 规则、CRUD 详细流程、AI Prompt 编写指引、校验重试协议等内容已下沉到应用仓库 Skill 中。

**执行任何插件操作前，必须先读取项目中的插件 Skill 文件**：

```
<project-path>/.agents/skills/plugin-guide/SKILL.md
```

其中 `<project-path>` 为当前妙搭应用的根目录（含 `.spark/meta.json`）。

该文件包含：
- 17 个 AI 插件的完整目录与能力速查
- 用户意图 → 插件选择映射表
- paramsSchema / formValue 的 Schema 规则与字段映射
- AI Prompt 编写规则与各场景模板
- Create / Update / Delete / Get 详细流程
- 校验失败重试协议
- 插件设计原则（原子化、链式、流式）
- 调用代码生成指引
