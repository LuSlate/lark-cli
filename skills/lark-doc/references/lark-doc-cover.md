# docs 封面图（cover-get / cover-update / cover-delete）

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md) 了解认证、全局参数和安全规则。

新版文档 Docx 封面图的获取 / 更新 / 删除。底层走 docx OpenAPI：

- 获取：`GET /open-apis/docx/v1/documents/:document_id`，封面在 `data.document.cover`
- 更新 / 删除：`PATCH /open-apis/docx/v1/documents/:document_id`，body `update_cover.cover`（删除时为 `null`）

```bash
# 获取封面（输出 cover.token / offset_ratio_x / offset_ratio_y）
lark-cli docs +cover-get --doc "https://xxx.larkoffice.com/docx/Z1Fj...tnAc"

# 更新封面（token 必须是与该 docx 建立 docx_image relation 的图片 token）
lark-cli docs +cover-update --doc Z1Fj...tnAc --token <file_token>
# 可选偏移比例（不传则用服务端默认裁剪；只接受有限浮点数）
lark-cli docs +cover-update --doc Z1Fj...tnAc --token <file_token> --offset-ratio-x 0.1 --offset-ratio-y 0.2

# 删除封面（发送 cover:null）
lark-cli docs +cover-delete --doc Z1Fj...tnAc
```

## ⚠️ 封面 token 的 relation 规则（关键）

封面更新接口**只接受与目标 Docx 建立了 `docx_image` relation 的图片 token**。不能复用正文图片块 token、IM 图片 token、普通 Drive file token。

本地图片走**两步式**：先上传为绑定到目标文档的 docx_image 资源，再把返回的 file_token 传给 `+cover-update --token`：

```bash
# 1) 上传封面图片，建立 docx_image relation
lark-cli docs +media-upload \
  --file ./cover.png \
  --parent-type docx_image \
  --parent-node <document_id> \
  --doc-id <document_id>
# 2) 用返回的 file_token 更新封面
lark-cli docs +cover-update --doc <document_id> --token <file_token>
```

**不要**用 `docs +media-insert` 返回的 token 当封面——那是正文 image block 的 relation（parent_node=<image_block_id>），调 cover-update 会被 OpenAPI 拒绝（relation mismatch）。

## 参数

| 参数 | 命令 | 必填 | 说明 |
|------|------|------|------|
| `--doc` | get/update/delete | 是 | docx 文档 URL 或 token；当前仅支持 docx，wiki/doc URL 会返回结构化错误（请传 docx document_id）|
| `--token` | update | 是 | 封面图 file_token，须有 docx_image relation（见上文）|
| `--offset-ratio-x` | update | 否 | 水平方向偏移比例（对齐 Docx OpenAPI `document.cover.offset_ratio_x`）；不传则用服务端默认；只接受有限浮点数，范围由服务端校验 |
| `--offset-ratio-y` | update | 否 | 垂直方向偏移比例（同上）|

## 输出与约定

- stdout 输出 JSON（`{"cover": {...}}`），stderr 给人读提示，AI Agent 友好。
- `cover-get` 原样输出服务端返回的 `cover.token` / `offset_ratio_x` / `offset_ratio_y`，不补默认值。
- 未传 offset 时，请求体 `update_cover.cover` 不写入 offset 字段（不替用户补 0 / 0.5）。
- offset 非数值 / NaN / Inf 在 CLI 侧前置拒绝；数值范围由服务端校验，下游错误结构化透出。
- 用 `--dry-run` 可只查看将要发出的 method / path / body，不真正调用。
