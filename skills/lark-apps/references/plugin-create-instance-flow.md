# Create 链路 — 新增插件实例

从用户需求到插件可调用的完整流程。本链路最严格，每一步都有前置门禁。

## 流程

```
Step 1: +plugin-install --name <key@ver>
Step 2: 读 plugin-instance-schema.md + 设计 paramsSchema / formValue
Step 3: +plugin-instance-create --plugin <key@ver> --name <n> --form-value @file [--params-schema @file]
Step 4: 校验通过？ → 否：走 plugin-retry-protocol.md（max 3 次）
Step 5: 读 node_modules/{pluginKey}/manifest.json + capabilities/{id}.json
Step 6: 读 plugin-instance-call.md → 生成调用代码
```

## Step 1 — 安装插件包

```bash
lark-cli apps +plugin-install --name @official-plugins/ai-text-generate@1.0.0 --project-path <path>
```

- 鉴权：需要 user token（先 `lark-cli auth login`）
- 已安装同版本会跳过（status=already_installed）
- 失败时 hint 会指示原因（网络/版本不存在/package.json 缺失）

## Step 2 — 设计 paramsSchema 和 formValue

**必读**：[`plugin-instance-schema.md`](plugin-instance-schema.md) — 变量映射规则、参数类型约束、formValue 生成规则。

设计前必须先读插件的 form.schema：
```bash
cat <project-path>/node_modules/<pluginKey>/manifest.json
```

根据 form.schema 的字段和用户业务意图，设计：
1. **paramsSchema** — 对外暴露的业务入参（变量定义）
2. **formValue** — 将变量映射到 form.schema 字段（变量消费）
3. **语义化 ID** — 如 `task-text-summary`，小写+短横线，描述业务用途

## Step 3 — 创建实例

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

### 前置检查（CLI 自动执行）

| 检查项 | 失败时 hint |
|--------|-----------|
| package.json 存在 | `run 'lark-cli apps +init'` |
| capabilities 路径可解析 | `use --capabilities-dir or check .env.local` |
| 插件包已安装 | `run '+plugin-install ...' first` |
| 版本匹配 | warning（非 error）：`installed X differs from Y` |
| ID 唯一 | `use --force to overwrite, or choose a different --id` |
| formValue 校验（5 规则） | 逐条列出违规项 |

## Step 4 — 校验失败处理

CLI 返回 `ok: false` + `error.hint` 逐条列出问题时，按 [`plugin-retry-protocol.md`](plugin-retry-protocol.md) 处理：

1. 解析 hint 中的每条违规
2. 修正 formValue / paramsSchema
3. 重新调用 `+plugin-instance-create`（或 `--force` 覆盖）
4. 最多重试 3 次，3 次仍失败则上报用户

## Step 5 — 读取插件源码

创建成功后，读取以下文件获取完整信息：

```bash
# 插件 manifest（actions / inputSchema / outputSchema / outputMode）
cat <project-path>/node_modules/<pluginKey>/manifest.json

# 创建的实例配置（paramsSchema / formValue）
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

## Step 6 — 生成调用代码

**必读**：[`plugin-instance-call.md`](plugin-instance-call.md) — Client/Server 决策、outputMode 处理、normalizeStream。

根据 manifest 中的 `actions[].outputMode` 选择调用方式：
- `unary` → `capabilityClient.load(id).call(actionKey, input)`
- `stream` → `capabilityClient.load(id).callStream(actionKey, input)` + normalizeStream

## Red Flags

| 念头 | 反驳 |
|------|------|
| "我记得这个插件的 schema，不用读 manifest" | manifest 可能更新过，必须每次读 |
| "create 完直接写代码" | 没读 manifest 就写代码 = 猜 actionKey/params |
| "install 之前先 create" | 没装包 manifest 读不到，校验会失败 |
| "formValue 校验报错，我直接编辑 JSON 文件" | 铁律：只能通过 CLI 命令修改 capability JSON |
