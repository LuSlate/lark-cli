
# calendar +search-event

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

按关键词、时间范围和参会人搜索日历日程。只读操作。

本 skill 对应 shortcut：`lark-cli calendar +search-event`。

## 命令

```bash
# 按关键词搜索
lark-cli calendar +search-event --query "周会"

# 按时间范围过滤
lark-cli calendar +search-event --time-range "2026-04-20~2026-04-27"

# 按参会人过滤（支持用户 ou_、群聊 oc_、会议室 omm_）
lark-cli calendar +search-event --attendee-ids "ou_user1,oc_chat1,omm_room1"

# 组合搜索
lark-cli calendar +search-event --query "周会" --time-range "2026-04-20~2026-04-27" --attendee-ids "ou_user1"

# 指定日历 ID（默认使用主日历）
lark-cli calendar +search-event --query "周会" --calendar-id <calendar_id>
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--calendar-id <id>` | 否 | 日历 ID，默认使用主日历 |
| `--query <keyword>` | 否 | 搜索关键词。默认为空 |
| `--attendee-ids <ids>` | 否 | 参会人 ID，逗号分隔。支持用户（`ou_`）、群聊（`oc_`）、会议室（`omm_`）前缀自动识别 |
| `--time-range <range>` | 否 | 搜索时间范围(ISO 8601 时间)，格式 `start~end`（如 `2026-04-20T00:00:00+08:00~2026-04-27T23:59:59+08:00`） |
| `--page-token <token>` | 否 | 分页 Token，获取下一页 |
| `--page-size <size>` | 否 | 每页条数，1-30，默认 20 |

> 开始时间必须早于结束时间，否则校验失败。

## 输出结果

| 字段 | 说明 |
|------|------|
| `calendar_id` | 搜索的日历 ID |
| `items` | 日程列表 |
| `has_more` | 是否有更多结果 |
| `page_token` | 下一页 Token |

### items 中的字段

| 字段 | 说明 |
|------|------|
| `event_id` | 日程 ID |
| `summary` | 日程主题 |
| `start` | 开始时间 |
| `end` | 结束时间 |
| `is_all_day` | 是否全天日程 |
| `app_link` | 日程应用链接 |

> 注意：如需日程详情，请使用 `calendar events get`。

## 分页

- 使用 `page_size` 控制每页条数（1-30），默认 20。
- 当 `has_more` 为 `true` 时，使用返回的 `page_token` 获取下一页。
- 必须持续翻页直到 `has_more` 为 `false`，确保不遗漏结果。

## 提示

- 搜索已结束的会议应优先使用 `vc +search`，因为即时会议不会出现在日历中。

## 参考

- [lark-calendar](../SKILL.md) — 日历全部命令
- [lark-calendar-meeting](lark-calendar-meeting.md) — 从日程获取会议信息
- [lark-vc](../../lark-vc/SKILL.md) — 搜索历史会议
- [lark-shared](../../lark-shared/SKILL.md) — 认证和全局参数
