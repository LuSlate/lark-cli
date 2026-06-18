# lark-apps 插件管理

妙搭应用的插件（Plugin）体系：插件包安装、插件实例 CRUD、调用代码生成。

**触发关键词**：用户要实现 AI生文/AI生图/AI翻译/AI摘要/AI分类/图片理解/图片识别/图片抠图/图片对比/图生图/语音识别/语音合成/文档解析/网页抓取/文本转JSON 等能力时，或提到 Plugin/PluginInstance/Capability/插件安装/卸载/创建实例时加载本 Skill。

## 核心概念

- **插件包（Plugin Package）**：npm 格式的功能包，安装到 `node_modules/`，含 `manifest.json` 描述 actions 和 form.schema。
- **插件实例（Plugin Instance / Capability）**：基于插件包创建的业务配置，存储在 `capabilities/{id}.json`，定义 `paramsSchema`（业务入参）和 `formValue`（表单映射，通过 `{{input.xxx}}` 引用 paramsSchema 参数）。
- **变量映射**：`调用方传值 → paramsSchema 定义变量 → formValue 消费变量 {{input.xxx}} → Plugin form.schema 接收`。

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

## 意图路由

根据用户意图选择对应链路，**必须读取对应的 flow 文件后再执行**：

| 用户意图 | 路由到 | 必读 |
|---------|--------|------|
| 新增插件能力（"加个 AI 翻译""接入文本生成"） | **Create 链路** | [`plugin-create-instance-flow.md`](plugin-create-instance-flow.md) |
| 修改已有实例配置（"改一下 prompt""换个模型"） | **Update 链路** | [`plugin-update-instance-flow.md`](plugin-update-instance-flow.md) |
| 删除实例（"去掉这个能力""不需要了"） | **Delete 链路** | [`plugin-delete-instance-flow.md`](plugin-delete-instance-flow.md) |
| 查看实例详情 / 列出已有实例 / 查已装插件 | **Get 链路** | [`plugin-get-instance-flow.md`](plugin-get-instance-flow.md) |
| 写插件调用代码（Create/Update 完成后的下一步） | 读 call 指南 | [`plugin-instance-call.md`](plugin-instance-call.md) |

## 本期支持的插件（17 个）

ai-text-generate / ai-text-summary / ai-text-to-json / ai-translate / ai-search-summary / ai-text-to-image / ai-background-replace / ai-image-compare / ai-image-matting / ai-image-to-image / ai-image-to-json / ai-image-understanding / ai-speech-synthesis / ai-speech-to-text / ai-categorization / ai-doc-parser / web-crawler

**不支持**（需用户通过 GUI 手动配置）：飞书发消息、飞书创建群组、飞书多维表格、飞书审批、飞书 aPaaS。

## 铁律

1. **只能通过 CLI 命令修改 capability JSON 文件** — 禁止 Agent 直接用文件编辑工具写 `capabilities/*.json`，必须通过 `+plugin-instance-create` / `+plugin-instance-update` / `+plugin-instance-delete` 操作，确保校验和格式一致性。
2. **先装包再建实例** — `+plugin-instance-create` 前必须确保插件包已安装（`+plugin-install`），否则校验会因读不到 manifest 而失败。
3. **校验失败走重试协议** — Create / Update 返回校验错误时，按 [`plugin-retry-protocol.md`](plugin-retry-protocol.md) 处理：解析 hint → 修正 → 重试（max 3 次）。
4. **写代码前读源码** — Create 完成后，Agent 应读取 `node_modules/{pluginKey}/manifest.json` 和 `capabilities/{id}.json` 理解插件能力，再按 [`plugin-instance-call.md`](plugin-instance-call.md) 生成调用代码。禁止凭记忆猜测 actionKey / inputSchema / outputMode。
5. **不要在 formValue 中使用 Handlebars 控制语法** — 仅允许 `{{input.xxx}}`，严禁 `{{#if}}` / `{{#each}}` / `{{else}}` 等。
