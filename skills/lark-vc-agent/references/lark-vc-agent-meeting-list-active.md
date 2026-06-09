
# vc +meeting-list-active

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

查询「当前正在进行中（Ongoing）的会议列表」。该命令是**读操作**，按发起方身份返回不同语义：

- **UAT（`--as user`）**：以**当前用户**身份，查询用户**自己**当前正在参加的会议列表。无需 `--user-id`。
- **TAT（`--as bot`）**：以**应用/机器人**身份，按目标用户 `--user-id`（open_id, `ou_...`）查询该用户当前在会列表，并**只保留 bot 也在其中**的会议（用户与 bot 的共同在会列表）。

返回每条会议的 `meeting_no` / `meeting_id` / `meeting_title`，覆盖**无 / 单 / 多** 会议三种语义。返回的 `meeting_id` 可直接喂给 [`+meeting-events`](lark-vc-agent-meeting-events.md)。

本 skill 对应 shortcut：`lark-cli vc +meeting-list-active`（调用 `GET /open-apis/vc/v1/bots/active-meetings`）。

## 命令

```bash
# UAT：查我自己当前在会列表
lark-cli vc +meeting-list-active --as user --format pretty

# TAT：查目标用户与 bot 共同在会的会议
lark-cli vc +meeting-list-active --as bot --user-id ou_xxxxxxxxxxxxxxxx --format json

# 预览 API 调用（不实际请求）
lark-cli vc +meeting-list-active --as bot --user-id ou_xxxxxxxxxxxxxxxx --dry-run
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--as <user\|bot>` | 否 | 发起身份。`user`=UAT（查自己）；`bot`=TAT（查目标用户与 bot 共同在会）。默认取配置的 default-as |
| `--user-id <open_id>` | TAT 必填 | 目标用户 open_id（`ou_...`）。仅 `--as bot` 时使用且必填；`--as user` 时忽略 |
| `--format <fmt>` | 否 | 输出格式：json (CLI 默认) / pretty（本 skill 推荐） / table / ndjson / csv |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

## 核心约束

### 1. 数据为后台聚合级，非毫秒实时

在会列表来自 admin meeting_list（Ongoing）数据源。它匹配「IM 聊天后定位用户当前在哪些会」这类场景，但不保证毫秒级实时；刚入会/刚离会可能有秒级延迟。

### 2. UAT 与 TAT 身份语义不同

- UAT 返回的是**用户自己**的在会列表，按操作者身份天然鉴权，无需管理员权限。
- TAT 在用户在会列表基础上**额外过滤**「bot 是否也在这场会中」，因此结果是用户与 bot 的**交集**。若 bot 未入任何会，TAT 通常返回空列表。

### 3. 返回语义：无 / 单 / 多

- **无**：`meetings` 为空数组——用户当前不在任何进行中会议（TAT 下为无共同在会）。
- **单**：返回单条，可直接用其 `meeting_id`。
- **多**：返回全部，由调用方提示用户选择。

## 权限

| Shortcut | 所需 scope |
|----------|-----------|
| `+meeting-list-active` | `vc:meeting.active:read` |
