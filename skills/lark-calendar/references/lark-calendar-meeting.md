
# calendar +meeting

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

通过日程 ID（event_id） 获取关联的视频会议信息，包括会议 ID（meeting_id） 和绑定的会议纪要文档（meeting_note）。只读操作。

本 skill 对应 shortcut：`lark-cli calendar +meeting`。

## 命令

```bash
# 查询单个日程的会议信息
lark-cli calendar +meeting --event-ids <event_id>

# 指定日历 ID（默认使用主日历）
lark-cli calendar +meeting --event-ids <event_id1> --calendar-id <calendar_id>
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--event-ids <ids>` | 是 | 日程事件实例 ID，逗号分隔支持批量，最多 50 个 |
| `--calendar-id <id>` | 否 | 日历 ID，默认使用主日历("primary") |

## 输出结果

返回 `meetings` 数组，每条记录包含：

| 字段 | 说明 |
|------|------|
| `event_id` | 日程 ID |
| `meeting_id` | 关联的视频会议 ID（如有）。 |
| `meeting_note` | 关联的会议纪要文档 Token（如有）。 |

## 典型场景

### 场景 1：从日程获取会议信息

```bash
# 1. 查看日程安排，获取 event_id
lark-cli calendar +agenda --start 2026-06-10 --end 2026-06-11

# 2. 获取日程关联的会议信息
lark-cli calendar +meeting --event-ids <event_id>

# 3. 用 meeting_id 进一步获取会议详情
lark-cli vc +detail --meeting-ids <meeting_id>
```

## 与其他命令的关系

| 需求 | 推荐命令 |
|------|---------|
| 从日程获取会议 ID 和纪要文档 | `calendar +meeting` |
| 通过会议 ID 获取 note_id 和 minute_token | `vc +detail --meeting-ids` |
| 通过 note_id 获取 note_doc_token / verbatim_doc_token / shared_doc_tokens | `note +detail --note-id` |
| 读取纪要 / 逐字稿 / 共享文档正文 | `docs +fetch --api-version v2 --doc <doc_token>` |
| 获取妙记产物（需手动指定 `--summary` / `--todo` / `--chapter` / `--keyword` / `--transcript`，不传不返回） | `minutes +detail --minute-tokens` |

## 参考

- [lark-calendar](../SKILL.md) — 日历全部命令
- [lark-vc](../../lark-vc/SKILL.md) — 视频会议（进一步获取会议详情）
- [lark-shared](../../lark-shared/SKILL.md) — 认证和全局参数
