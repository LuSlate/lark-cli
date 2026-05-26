# minutes +todo

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

对妙记中的**单条**待办做新增 / 更新 / 删除。写操作。

本 skill 对应 shortcut：`lark-cli minutes +todo`（调用 `PUT /open-apis/minutes/v1/minutes/{minute_token}/todo`）。

## 典型触发表达

- "给这条妙记加一条待办"
- "把某条待办改成……"
- "标记某条待办为已完成 / 取消完成"
- "删除某条待办"

## 命令

```bash
# 新增一条待办（不带 id，content 与 is_done 成对）
lark-cli minutes +todo --minute-token obcnxxxxxxxxxxxxxxxxxxxx --todo "跟进预算审批" --is-done=false

# 更新已有待办（带 id，覆盖内容与完成状态）
lark-cli minutes +todo --minute-token obcnxxxxxxxxxxxxxxxxxxxx --todo-id 1234567890 --todo "整理会议纪要" --is-done

# 删除已有待办（只带 id，不带 --todo）
lark-cli minutes +todo --minute-token obcnxxxxxxxxxxxxxxxxxxxx --todo-id 1234567890

# 预览 API 调用
lark-cli minutes +todo --minute-token obcnxxxxxxxxxxxxxxxxxxxx --todo "新待办" --is-done --dry-run
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--minute-token <token>` | 是 | 妙记 Token |
| `--todo <text>` | 视操作 | 待办纯文本；新增 / 更新时必填，且必须与 `--is-done` 成对出现；删除时不传 |
| `--is-done` | 视操作 | 完成状态布尔值；传 `--is-done` 表示 `true`，传 `--is-done=false` 表示 `false`；仅在带 `--todo` 时使用 |
| `--todo-id <id>` | 视操作 | 已有待办的 id；更新 / 删除时必填，新增时不传 |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

## 三种操作的判定

| `--todo-id` | `--todo` | 行为 |
|-------------|----------|------|
| 不传 | 有内容 | **新增**一条待办（需 `--is-done`） |
| 传 | 有内容 | **更新** id 对应的待办（需 `--is-done`） |
| 传 | 不传 | **删除** id 对应的待办 |

## 核心约束

### 1. 先读后写，待办 id 如何获取

更新 / 删除前先用 `lark-cli vc +notes --minute-tokens <token>` 读取当前待办。返回的每条待办带 `todo_id` 字段，用作 `--todo-id` 的取值。

> 待办 id 仅用于程序内部定位某条待办，不必展示给用户；本命令的输出也不会回显 id。

读取与写入均使用 `is_done` 布尔字段。已删除的待办不会出现在读取结果中。

### 2. 待办内容为纯文本

`content` **不是 Markdown**，请直接传入待办描述文字。

- 不要写 `# 标题`、`**加粗**`、`- 列表` 等 Markdown 语法
- 如需多行内容，可直接使用换行；但不会被渲染为 Markdown 格式

### 3. 请求体字段

请求体 `todo_items` 始终只包含**一条**待办：

| CLI | JSON 字段 | 说明 |
|-----|-----------|------|
| `--todo` | `content` | 纯文本待办描述（新增 / 更新必填；删除不传） |
| `--is-done` | `is_done` | 是否已完成（新增 / 更新必填；删除不传） |
| `--todo-id` | `todo_id` | 已有待办 id（更新 / 删除必填；新增不传） |

### 4. 所需权限

| 身份 | 所需权限 |
|------|---------|
| user | `minutes:minutes:update` |

## 输出结果

```json
{
  "minute_token": "obcnxxxxxxxxxxxxxxxxxxxx",
  "operation": "add",
  "updated": true
}
```

| 字段 | 说明 |
|------|------|
| `minute_token` | 妙记 Token |
| `operation` | 本次操作类型：`add` / `update` / `delete` |
| `updated` | 是否已成功提交 |

## 如何获取 minute_token

| 来源 | 获取方式 |
|------|---------|
| 妙记 URL | 从 URL 末尾提取，如 `https://sample.feishu.cn/minutes/obcnxxxxxxxxxxxxxxxxxxxx` |
| 妙记搜索 | `lark-cli minutes +search --query "关键词"` |
| 会议产物查询 | `lark-cli vc +notes --minute-tokens <token>` |

## 常见错误与排查

| 错误现象 | 根本原因 | 解决方案 |
|---------|---------|---------|
| 参数无效 | `minute_token` 缺失 | 检查 token |
| 未指定操作 | 既没传 `--todo` 也没传 `--todo-id` | 新增 / 更新需 `--todo`，删除需 `--todo-id` |
| 缺少 `is_done` | 传了 `--todo` 未传 `--is-done` | `--todo` 与 `--is-done` 必须成对出现 |
| 删除时多传了 `--is-done` | 删除只需 `--todo-id` | 删除时不要传 `--todo` / `--is-done` |
| 权限不足 | 缺少 `minutes:minutes:update` | 运行 `auth login --scope "minutes:minutes:update"` |

## 参考

- [lark-minutes](../SKILL.md) — 妙记全部命令
- [minutes +summary](lark-minutes-summary.md) — 替换 AI 总结（不支持的 Markdown 会按原始文本展示，详见该文档）
- [lark-vc-notes](../../lark-vc/references/lark-vc-notes.md) — 读取总结、待办等 AI 产物
- [lark-shared](../../lark-shared/SKILL.md) — 认证和全局参数
