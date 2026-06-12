# Lark Sheet Recover

## 使用场景

写。整表回退到指定历史 revision（方案 B）。本 reference 覆盖 1 个 shortcut：

| 操作需求 | 使用工具 | 说明 |
|---------|---------|------|
| 整表回退到历史版本 | `+recover` | 把整个 spreadsheet 回退到 `--to-revision` 指定的版本，丢弃其后所有编辑 |

⚠️ **全文档破坏性回退**：`+recover` 丢弃 `--to-revision` 之后的**所有**编辑，包括其他协作者的改动。只在 agent 自己的草稿表、或确认要整表回滚时使用。要精确撤销本链路最近几笔编辑，请用 `+undo`（逐笔、可控、不波及他人）。

## Shortcuts

| Shortcut | Risk | 分组 |
| --- | --- | --- |
| `+recover` | write | 撤销恢复 |

## Flags

### `+recover`

_公共：URL/token（无 sheet 定位） · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--to-revision` | int | required | 整表回退到该 revision（来自此前写操作返回的 revision） |

## Examples

### `+recover`

把整表回退到某个历史版本。`--to-revision` 取此前某次写操作响应里返回的 `revision`。

```bash
lark-cli sheets +recover --spreadsheet-token <token> --to-revision 42
```

- 回退会产生一个**新** revision（不是删历史，而是追加一条回退记录），响应里返回这个新 revision。
- 回退不可逆地丢弃 `--to-revision` 之后的内容，执行前先确认要丢弃的范围。
- 与 `+undo` 的区别：`+undo` 精确撤销本 CLI 链路最近 N 笔编辑、不动他人改动；`+recover` 是全文档回到某版本、丢弃所有后续（含他人）。需要细粒度撤销时优先 `+undo`。
