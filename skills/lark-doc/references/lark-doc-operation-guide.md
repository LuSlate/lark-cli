# lark-doc 操作入口 Guide

本文件维护执行前的入口判断：先用“操作大类前置”确定必读 reference，再用“易混边界”避免跨 skill 或资源类型选错。具体参数、示例和工作流仍以各 reference 为准。

所有操作都默认先读 [`../../lark-shared/SKILL.md`](../../lark-shared/SKILL.md)，了解认证、权限、安全规则、全局参数和路径限制。

## 操作大类前置

| 操作大类 | 触发场景 | 必读 reference | 条件加读 |
|-|-|-|-|
| 读取文档 | 浏览、总结、摘取正文、定位 block、获取直达链接、提取素材或嵌入对象 token | [`lark-doc-fetch.md`](lark-doc-fetch.md) | 需要 Markdown 输出或基于 Markdown 更新时读 [`lark-doc-md.md`](lark-doc-md.md) |
| 创建文档 | 新建 Docx/Wiki 文档，含短文档、长文档骨架、Markdown 导入 | [`lark-doc-create.md`](lark-doc-create.md), [`lark-doc-xml.md`](lark-doc-xml.md) | 用户提供 `.md` 或明确要求 Markdown 时读 [`lark-doc-md.md`](lark-doc-md.md)；长文档读 [`style/lark-doc-create-workflow.md`](style/lark-doc-create-workflow.md)；需要根据题材组织文档时读 [`style/topics/topic-router.md`](style/topics/topic-router.md)；需要富 block 或美化时读 [`style/lark-doc-style.md`](style/lark-doc-style.md) |
| 编辑文档 | 替换、插入、删除、移动、复制、追加、覆盖、改写、润色、重排版 | [`lark-doc-update.md`](lark-doc-update.md), [`lark-doc-xml.md`](lark-doc-xml.md) | 用户明确要求 Markdown 或需 Markdown 跨行匹配时读 [`lark-doc-md.md`](lark-doc-md.md)；改写/润色读 [`style/lark-doc-update-workflow.md`](style/lark-doc-update-workflow.md)；需要富 block 或美化时读 [`style/lark-doc-style.md`](style/lark-doc-style.md) |
| 正文素材 | 插入、预览或下载正文图片/附件，下载画板缩略图 | 对应操作的 [`lark-doc-media-insert.md`](lark-doc-media-insert.md) / [`lark-doc-media-preview.md`](lark-doc-media-preview.md) / [`lark-doc-media-download.md`](lark-doc-media-download.md) | 需要从文档中提取素材 token 时先读 [`lark-doc-fetch.md`](lark-doc-fetch.md) |
| 文档级资源 | 下载、更新或删除 Docx 封面图 | [`lark-doc-resource-cover.md`](lark-doc-resource-cover.md) | 无；封面不是正文 `<img>`，不要走 `+media-*` |
| 画板协作 | 新增 Mermaid/SVG 画板，或更新已有画板 | [`lark-doc-whiteboard.md`](lark-doc-whiteboard.md) | 插入新的 `<whiteboard>` block 时读 [`lark-doc-xml.md`](lark-doc-xml.md)；更新已有复杂画板时读 [`../../lark-whiteboard/SKILL.md`](../../lark-whiteboard/SKILL.md)；需要美化/结构化表达时读 [`style/lark-doc-style.md`](style/lark-doc-style.md) |
| 嵌入对象下钻 | 正文中出现 `<sheet>`、`<bitable>`、`<cite file-type=...>`、`<vc-transcribe-tab>`、`<synced_reference>` 等 | [`lark-doc-fetch.md`](lark-doc-fetch.md) | 按对象类型切到 [`../../lark-sheets/SKILL.md`](../../lark-sheets/SKILL.md)、[`../../lark-base/SKILL.md`](../../lark-base/SKILL.md)、[`../../lark-note/SKILL.md`](../../lark-note/SKILL.md) 或继续用 `docs +fetch` 读取源文档 |
| 非本 skill | 评论、评论回复、reaction、权限、云空间文件管理、导入导出 | 对应目标 skill | 评论/云空间管理走 [`../../lark-drive/SKILL.md`](../../lark-drive/SKILL.md)；表格/Base 内部数据走 sheets/base |

## 易混边界

- 正文图片、附件和画板缩略图走正文素材操作；文档封面走 [`lark-doc-resource-cover.md`](lark-doc-resource-cover.md)，不要把封面当正文 `<img>` 处理。
- 已有复杂画板的查询、导出、渲染验证和写入以 [`../../lark-whiteboard/SKILL.md`](../../lark-whiteboard/SKILL.md) 的流程为准。
- 评论、权限、云空间文件管理、导入导出不归本 skill，按场景切到 [`../../lark-drive/SKILL.md`](../../lark-drive/SKILL.md)。
- 文档内嵌 `<sheet>` / `<bitable>` / `<cite file-type=...>` 时，本 skill 只负责提取 token；对象内部数据读取和修改切到对应 skill。

## 格式选择

- **创建 / 导入场景**：XML 和 Markdown 都可以。用户提供 `.md` 本地文件、或明确说“导入 Markdown”时直接用 Markdown；否则默认 XML。
- **精准编辑场景**：`str_replace` / `block_insert_after` / `block_replace` / `block_delete` / `block_move_after` 等局部精修优先 XML。
- **Markdown 限制**：Markdown 不携带 block ID，也无样式。需要按 block ID 定位时，先用 `docs +fetch --detail with-ids` 局部获取目标段落。
- **富 block**：callout、grid、table、whiteboard 等结构化表达由内容和用户意图决定；不要为了“丰富”强行套用固定结构。

## 校验要点

- 写操作后，如继续 block 级操作，按 [`lark-doc-update.md`](lark-doc-update.md) 的“Block ID 生命周期”判断是否需要重新 fetch。
- `overwrite` / `block_replace` / `block_delete` 后不要复用受影响旧 ID。
- 插入 / 复制新块后，要操作新块必须重新 fetch 获取新 block ID。
- 正文素材走 `+media-*`；文档封面走 `+resource-* --type cover`。
