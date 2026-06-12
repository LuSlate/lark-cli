
# minutes +detail

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

通过妙记 Token 查询妙记详情，支持按需获取 AI 产物（总结、待办、章节、逐字稿、关键词）。只读操作。

> **重要约束**：必须**显式指定**要获取哪些产物的 flag（`--summary` / `--todo` / `--chapter` / `--keyword` / `--transcript`），未传任何产物 flag 时只返回基础信息（如 `title`），不会返回任何 AI 产物内容。一次性获取所有产物可使用：`--summary --todo --chapter --keyword --transcript`。

本 skill 对应 shortcut：`lark-cli minutes +detail`。

## 命令

```bash
# 查询妙记基础信息（标题）
lark-cli minutes +detail --minute-tokens obcxxxxxxxxxx

# 批量查询（逗号分隔，最多 50 个）
lark-cli minutes +detail --minute-tokens obcxxxxxxxxxx,obcyyyyyyyyyy

# 按需获取 AI 产物
lark-cli minutes +detail --minute-tokens obcxxxxxxxxxx --summary --todo --chapter --transcript --keyword

# 逐字稿输出到文件（默认 ./minutes/{minute_token}/transcript.txt）
lark-cli minutes +detail --minute-tokens obcxxxxxxxxxx --transcript

# 覆盖已有逐字稿文件
lark-cli minutes +detail --minute-tokens obcxxxxxxxxxx --transcript --overwrite
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--minute-tokens <tokens>` | 是 | 妙记 Token，逗号分隔支持批量，最多 50 个。仅支持小写字母和数字 |
| `--summary` | 否 | 包含 AI 总结 |
| `--todo` | 否 | 包含待办事项 |
| `--chapter` | 否 | 包含章节纪要 |
| `--transcript` | 否 | 包含逐字稿（保存到本地文件） |
| `--keyword` | 否 | 包含推荐关键词 |
| `--overwrite` | 否 | 覆盖已存在的逐字稿文件（仅 `--transcript` 有效） |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

## 输出结果

返回 `minutes` 数组，每条记录包含：

| 字段 | 说明 |
|------|------|
| `minute_token` | 妙记 Token |
| `title` | 妙记标题（如有） |
| `artifacts` | AI 产物（仅指定了 `--summary`/`--todo`/`--chapter`/`--transcript`/`--keyword` 时返回） |

### artifacts 字段

请求的 AI 产物**始终返回对应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `artifacts.summary` | string | AI 总结。为空时返回 `""` |
| `artifacts.todos` | array | 待办事项列表。为空时返回 `[]` |
| `artifacts.chapters` | array | 章节列表。为空时返回 `[]` |
| `artifacts.keywords` | array | 关键词列表。为空时返回 `[]` |
| `artifacts.transcript_file` | string | 逐字稿本地文件路径。为空时返回 `""` |

> 未请求的产物不会出现在 `artifacts` 中。例如只传了 `--summary`，则 `artifacts` 中只有 `summary` 字段。

### 逐字稿文件路径

指定 `--transcript` 时，逐字稿默认保存到 `./minutes/{minute_token}/transcript.txt`，与 `minutes +download` 的默认落点保持一致，便于 Agent 聚合同一妙记的所有产物。

## 如何获取输入参数

| 输入参数 | 获取方式 |
|---------|---------|
| `minute_token` | 从妙记 URL 中提取，如 `https://sample.feishu.cn/minutes/obcxxx` → `obcxxx` |
| `minute_token` | `vc +detail --meeting-ids` → 结果中的 `minute_token` 字段 |
| `minute_token` | `vc +recording --meeting-ids` → 结果中的 `minute_token` 字段 |
| `minute_token` | `minutes +search` → 结果中的 `minute_token` 字段 |

## 参考

- [lark-minutes](../SKILL.md) — 妙记全部命令
- [lark-vc](../../lark-vc/SKILL.md) — 视频会议（获取 minute_token）
- [lark-shared](../../lark-shared/SKILL.md) — 认证和全局参数
