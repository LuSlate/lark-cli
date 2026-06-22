# docs history（历史版本与回滚）

用于查看 Docx 历史版本、按 `history_version_id` 回滚，以及查询回滚任务状态。

## 安全流程

1. 先用 `+history-list` 找到目标版本的 `history_version_id`。
2. 如果用户指定的是 `revision_id`，在 `entries[].revision_id` 中找对应条目，然后取同一条的 `history_version_id`；不要把 `revision_id` 直接传给 `+history-revert`。
3. 如果用户指定的是某一时刻，按 `entries[].edit_time` 匹配；优先选择不晚于目标时刻的最近一条历史记录，无法明确匹配时先向用户确认候选版本。
4. 再用 `+history-revert --history-version-id <history_version_id>` 发起回滚。默认最多等待 30 秒；如果返回 `status: running`，记录 `task_id`。
5. 用 `+history-revert-status` 轮询 `task_id`，直到状态不再是 `running`。
6. 回滚完成后，用 `docs +fetch` 读取文档确认内容。

## 按 revision_id 或时间点回滚

当用户说“回滚到 revision_id=42”“恢复到昨天下午 3 点的版本”这类需求时，流程是：

1. 执行 `docs +history-list --doc <doc>` 获取历史记录列表，必要时用 `page_token` 翻页。
2. 用用户给出的 `revision_id` 匹配 `entries[].revision_id`，或用用户给出的时间匹配 `entries[].edit_time`。时间匹配时选择目标时刻之前最近的一条；如果相邻版本含义不清，向用户展示候选并确认。
3. 从匹配条目读取 `history_version_id`。`history_version_id` 对应服务端 `minor_history.version`，这是回滚接口需要的 ID。
4. 执行 `docs +history-revert --doc <doc> --history-version-id <history_version_id>`。

## 命令

```bash
# 列出历史版本
lark-cli docs +history-list --doc "<docx_url_or_token>" --page-size 20

# 翻页
lark-cli docs +history-list --doc "<docx_url_or_token>" --page-size 20 --page-token "<page_token>"

# 回滚到指定 history_version_id（默认等待 30000ms）
lark-cli docs +history-revert --doc "<docx_url_or_token>" --history-version-id 42

# 只发起任务，不等待
lark-cli docs +history-revert --doc "<docx_url_or_token>" --history-version-id 42 --wait-timeout-ms 0

# 查询回滚任务状态
lark-cli docs +history-revert-status --doc "<docx_url_or_token>" --task-id "<task_id>"
```

## 参数

| 命令 | 参数 | 必填 | 说明 |
|-|-|-|-|
| `+history-list` | `--doc` | 是 | Docx URL/token，或可解析为 Docx 的 wiki URL |
| `+history-list` | `--page-size` | 否 | 返回条数，范围 `1-20`，默认 `20` |
| `+history-list` | `--page-token` | 否 | 上一页返回的 `page_token` |
| `+history-revert` | `--doc` | 是 | Docx URL/token，或可解析为 Docx 的 wiki URL |
| `+history-revert` | `--history-version-id` | 是 | `+history-list` 返回的 `history_version_id`，必须大于 0 |
| `+history-revert` | `--wait-timeout-ms` | 否 | 等待回滚完成的毫秒数，范围 `0-30000`，默认 `30000` |
| `+history-revert-status` | `--doc` | 是 | 同一个文档 |
| `+history-revert-status` | `--task-id` | 是 | `+history-revert` 返回的 `task_id` |

## 返回值要点

`+history-list` 返回：

```json
{
  "entries": [
    {
      "revision_id": 42,
      "history_version_id": "11",
      "edit_time": "1780000000",
      "type": 1,
      "name": "版本名",
      "description": "版本说明",
      "editor_ids": ["ou_xxx"]
    }
  ],
  "has_more": true,
  "page_token": "page_token"
}
```

`+history-revert` 返回：

```json
{
  "task_id": "task_xxx",
  "status": "running",
  "history_version_id": "11",
  "poll_after_ms": 10000
}
```

`+history-revert-status` 返回：

```json
{
  "status": "partial_failed",
  "history_version_id": "11",
  "failed_block_tokens": ["blk_xxx"]
}
```

`status` 可能是 `running`、`done`、`partial_failed`、`failed`。当状态是 `partial_failed` 或 `failed` 时，优先检查 `failed_block_tokens`。
