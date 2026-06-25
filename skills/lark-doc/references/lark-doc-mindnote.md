# 飞书思维笔记（Mindnote）

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 和 [`../../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和路由规则。

当用户要查看思维笔记节点、读取节点内容、批量创建节点时，入口属于 `lark-doc`，但实际执行命令使用 `lark-cli mindnotes ...`，不是 `docs +...`。

## 命令

```bash
# 先看命令帮助
lark-cli mindnotes nodes list --help
lark-cli mindnotes nodes create --help

# 读取节点列表
lark-cli mindnotes nodes list --mindnote-id "D05hbLa3dm08GbnerjwbvNmUcgf"

# 创建子节点
lark-cli mindnotes nodes create \
  --mindnote-id "D05hbLa3dm08GbnerjwbvNmUcgf" \
  --data '{
    "client_token":"fe599b60-450f-46ff-b2ef-9f6675625b97",
    "nodes":[
      {
        "parent_id":"node_parent123",
        "texts":[
          {"element_type":"text","text":{"content":"子节点内容"}}
        ],
        "highlight":"yellow",
        "finish":false
      }
    ]
  }'
```

## 参数

### `mindnotes nodes list`

| 参数 | 必填 | 说明 |
|------|------|------|
| `--mindnote-id` | 是 | 思维笔记 token / 唯一标识 |

返回重点：`data.nodes` 中常见字段有 `node_id`、`parent_id`、`texts`、`notes`、`images`、`finish`、`highlight`。

### `mindnotes nodes create`

命令参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--mindnote-id` | 是 | 思维笔记 token / 唯一标识 |
| `--data` | 是 | JSON 请求体 |

请求体字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `client_token` | 否 | 幂等 token，建议写操作传入 |
| `nodes` | 是 | 待创建节点数组 |
| `nodes[].parent_id` | 否 | 父节点 ID；创建子节点时传入 |
| `nodes[].texts` | 否 | 节点正文富文本数组 |
| `nodes[].notes` | 否 | 节点备注富文本数组 |
| `nodes[].images` | 否 | 节点图片列表 |
| `nodes[].highlight` | 否 | `red` / `yellow` / `pink` / `blue` / `cyan` / `olive` / `grey` |
| `nodes[].finish` | 否 | 节点完成状态 |

富文本字段 `texts` / `notes` 是元素数组。最常见的是：

```json
[{"element_type":"text","text":{"content":"节点内容"}}]
```

## 推荐工作流

1. 先拿到 `mindnote_id`。
2. 先执行 `mindnotes nodes list`，确认目标 `parent_id`。
3. 再执行 `mindnotes nodes create`。
4. 写操作优先带 `client_token`，避免重试时重复创建。

> [!CAUTION]
> `mindnotes nodes create` 是写操作，执行前确认目标思维笔记和插入位置。

## 参考

- [lark-doc-fetch](lark-doc-fetch.md) — 获取文档内容
- [lark-shared](../../lark-shared/SKILL.md) — 认证和全局参数
