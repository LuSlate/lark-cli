# vc +meeting-list-active

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、身份切换和权限处理。

列出当前进行中的会议，用来发现 `+meeting-events` 需要的长数字 `meeting_id`。

本 skill 对应 shortcut：`lark-cli vc +meeting-list-active`（调用 `GET /open-apis/vc/v1/bots/user_active_meeting`）。

## 命令

```bash
# UAT：查询当前登录用户正在参加的会议
lark-cli vc +meeting-list-active --as user --format pretty

# TAT：查询指定 open_id 当前参加、且 bot 也在会中的会议
lark-cli vc +meeting-list-active --as bot --user-id ou_xxx --format json

# 预览 API 调用
lark-cli vc +meeting-list-active --as bot --user-id ou_xxx --dry-run
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--user-id <id>` | TAT 必填，UAT 不需要 | 目标用户 open_id，格式为 `ou_...`。CLI 直接透传给接口，不接受 internal user_id 或数字 ID |
| `--format <fmt>` | 否 | 输出格式：json / pretty / table / ndjson / csv |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

## 身份语义

### UAT / `--as user`

- 不传 `--user-id`。
- 返回当前登录用户正在参加的会议。
- 这是 UAT 下读取会中事件的前置发现步骤；后续必须继续用 `--as user` 调用：

```bash
lark-cli vc +meeting-events --as user --meeting-id <meeting_id> --page-all --format pretty
```

### TAT / `--as bot`

- 必须传 `--user-id <user_open_id>`，即 `ou_...`。
- 返回该用户当前正在参加、且 bot 也在会中的会议；它不是任意用户当前会议全集。
- 如果返回空，不代表用户不在任何会议中，只能说明没有找到“用户在会中且 bot 也在会中”的当前会。
- TAT 读取事件仍然要求 bot 在会中。常见流程是：

```bash
# 方式 1：先让 bot 入会，直接从 join 响应拿 meeting.id
lark-cli vc +meeting-join --as bot --meeting-number 123456789 --format json
lark-cli vc +meeting-events --as bot --meeting-id <meeting.id> --page-all --format pretty

# 方式 2：bot 已经在会中时，用 active meeting 发现 meeting_id
lark-cli vc +meeting-list-active --as bot --user-id <user_open_id> --format json
lark-cli vc +meeting-events --as bot --meeting-id <meeting_id> --page-all --format pretty
```

## 多会议选择

- 如果返回多个会议，不要自动挑第一个。
- 向用户展示每个候选的 `meeting_title` / `meeting_no` / `meeting_id`，等待用户选择。
- 选择后继续沿用发现 meeting_id 时的身份：UAT 发现的 meeting_id 用 `--as user`，TAT 发现的 meeting_id 用 `--as bot`。

## 9 位会议号匹配

用户提供 9 位会议号但没有明确要求 bot 入会时，把会议号当作 active meeting 的筛选条件，而不是写操作指令。

```bash
lark-cli vc +meeting-list-active --as user --format json
```

匹配规则：

- 在返回会议中匹配 `meeting_no == <9位会议号>`。
- 匹配到唯一会议：取该项的长数字 `meeting_id`，后续用同一身份调用 `+meeting-events`。
- 匹配到多个会议：展示候选，让用户选择。
- 没有匹配：说明当前身份没有发现该会议号对应的 active meeting；不要自动调用 `+meeting-join`，除非用户明确要求入会。

TAT 场景已有目标用户 `open_id` 时，先按 bot 身份查 active，再用同样规则匹配：

```bash
lark-cli vc +meeting-list-active --as bot --user-id <user_open_id> --format json
```

## 常见错误与排查

| 错误现象 | 根本原因 | 解决方案 |
|---------|---------|---------|
| `--user-id is required when --as bot` | TAT 未传目标用户 | 传入目标用户 open_id |
| 返回空列表 | 没有满足“目标用户在会中且 bot 也在会中”的当前会 | 先让 bot 入会，或确认 `user_id` 和会议状态 |
| `--user-id` 格式错误 | 传入了 internal user_id 或其他非 `ou_...` 值 | 改传目标用户 open_id |
| TAT / `--as bot` 权限不足 | 应用 scope、租户安装、权限可访问的数据范围或 VC Agent privilege 未配置完整 | 不要执行 `auth login`。检查 `vc:meeting.meetingevent:read`、应用发布/安装，以及开放平台“权限可访问的数据范围”：选择“按条件筛选”，条件为“会议的归属者 包含 与应用的可用范围一致”；仍失败再排查内测 privilege / 灰度 |

## 参考

- [lark-vc-agent-meeting-join](lark-vc-agent-meeting-join.md) — 让 bot 真实入会并拿 `meeting.id`
- [lark-vc-agent-meeting-events](lark-vc-agent-meeting-events.md) — 使用 `meeting_id` 读取会中事件
