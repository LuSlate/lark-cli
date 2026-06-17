# lark-slides xml_presentation.slide get

## 用途

按 `slide_id` 或 1-based `slide_number` 拉取指定演示文稿单页的 XML 内容（可指定历史版本）。常用于"读-改-写"编辑闭环的第一步。

## 命令

```bash
lark-cli slides xml_presentation.slide get --as user --params '<json_params>'
```

## 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `--params` | JSON string | 是 | 路径参数与查询参数 |

### params JSON 结构

```json
{
  "xml_presentation_id": "slides_example_presentation_id",
  "slide_id": "slide_example_id",
  "slide_number": 1,
  "revision_id": -1
}
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `xml_presentation_id` | string | 是 | 目标演示文稿唯一标识 |
| `slide_id` | string | 否 | 目标页面唯一标识；与 `slide_number` 同时传时优先使用 `slide_id` |
| `slide_number` | integer | 否 | 目标页码，从 1 开始；未传 `slide_id` 时可用 |
| `revision_id` | integer | 否 | 版本号，`-1` 表示最新版（默认）|

## 使用示例

### 按 slide_id 读最新版本

```bash
lark-cli slides xml_presentation.slide get --as user --params '{
  "xml_presentation_id": "slides_example_presentation_id",
  "slide_id": "slide_example_id"
}'
```

### 按页码读取

```bash
lark-cli slides xml_presentation.slide get --as user --params '{
  "xml_presentation_id": "slides_example_presentation_id",
  "slide_number": 2
}'
```

### 只提取 XML 内容

```bash
lark-cli slides xml_presentation.slide get --as user \
  --params '{"xml_presentation_id":"slides_example_presentation_id","slide_id":"slide_example_id"}' \
  | jq -r '.data.slide.content'
```

### 读指定历史版本

```bash
lark-cli slides xml_presentation.slide get --as user --params '{
  "xml_presentation_id": "slides_example_presentation_id",
  "slide_id": "slide_example_id",
  "revision_id": 42
}'
```

## 返回值

```json
{
  "code": 0,
  "data": {
    "slide": {
      "slide_id": "slide_example_id",
      "content": "<slide id=\"slide_example_id\"><style/><data>...</data></slide>"
    },
    "revision_id": 100
  },
  "msg": "success"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.slide.slide_id` | string | 页面唯一标识 |
| `data.slide.content` | string | 页面完整 XML（`<slide>` 根节点，不含 xmlns）|
| `data.revision_id` | integer | 此次读到的版本号，可用于后续 replace 的乐观锁 |

## 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 404 | 演示文稿或页面不存在 | 检查 `xml_presentation_id` / `slide_id` / `slide_number` |
| 403 | 权限不足 | 需要 `slides:presentation:read` scope，并对该 PPT 有访问权限 |
| 400 | `revision_id` 不存在 | 传了无效版本号，用 `-1` 或真实存在的版本号 |

## 注意事项

1. **执行前必做**：`lark-cli schema slides.xml_presentation.slide.get` 查看最新参数结构
2. **选择器优先级**：`slide_id` 和 `slide_number` 至少传一个；如果同时传，CLI 会以 `slide_id` 为准。
3. **block_id 提取**：返回 XML 里每个顶层块（shape、img、table、chart、whiteboard 等）的 `id` 属性即为 `block_id`，通常是 3 字符短码，例如 `<shape id="bUn" ...>`。用以下命令列出当前页所有 block_id：

   ```bash
   lark-cli slides xml_presentation.slide get --as user \
     --params "{\"xml_presentation_id\":\"$PID\",\"slide_id\":\"$SID\"}" \
     | jq -r '.data.slide.content' | grep -oE 'id="[^"]+"' | sed 's/id="//;s/"//'
   ```

## 相关命令

- [slides +replace-slide](lark-slides-replace-slide.md) — 块级替换 shortcut（推荐）
- [xml_presentation.slide replace](lark-slides-xml-presentation-slide-replace.md) — 底层 replace API 参考
- [xml_presentations get](lark-slides-xml-presentations-get.md) — 读整个 PPT
- [lark-slides-edit-workflows.md](lark-slides-edit-workflows.md) — 读-改-写闭环
