# Material And Asset Planning

新建演示文稿或大幅改写页面时，planning layer 必须先激活本素材处理层，再写入或更新 `slide_plan.json`。目标是让 agent 先利用用户已经提供的本地素材和上下文，再决定是否需要内置模板、联网搜索或 XML-native 兜底。

本文件覆盖两类对象：

- `material_inventory`：deck 级素材盘点，记录本地素材、链接、缺口、用途和搜索策略。
- `asset_need`：page 级视觉资产需求，记录每页是否需要图片、图表、截图、图标、文案来源或兜底视觉。

## Core Rules

- 本地素材优先。用户给了文件、目录、截图、PDF、PPTX、文案、数据表、链接或已有 slides 时，先按 Attachment Resolution 解析并盘点用途；禁止忽略附件直接生成大纲或 XML。
- 没有合适本地素材时，才考虑联网搜索、内置模板、IconPark 或 XML-native 兜底。联网搜索只用于确实需要外部事实、图片、logo、公开截图或背景补充的场景。
- 素材进入 plan 前必须分类并写清用途；不要把“有文件”直接等同于“应出现在页面上”。
- 页面不能依赖不可获得素材才能完成。每个 `asset_need` 都必须有 `fallback_if_missing`。
- 真实图片进入 slides 前必须走支持的上传路径：`slides +media-upload` 或 `+create --slides` 的 `@./path` 占位符。禁止把 http(s) 外链直接写进 `<img src>`。
- `.pptx` / `.pdf` 被用户称为模板、风格参考、参考 PPT、教案 PPT、品牌手册、研究报告或含有页面截图/图表时，按 Local Material Handling 判断是否导入回读，用作二次创作素材。导入是写操作；如果用户已经明确要求“根据附件制作 PPT”，可视为已有意图，否则先确认。

## Attachment Resolution

在写 `slide_plan.json` 前，先把用户提供的附件文本转成可操作的本地路径清单。

1. 从 prompt 提取所有附件线索：`附件文件路径：...`、`文件：...`、`上传文件：...`、相对路径、绝对路径、目录路径，以及结构化输入中单独列出的文件名。
2. 逐个解析路径：
   - 已是绝对路径：直接检查是否存在。
   - 相对路径：先按当前工作目录解析；如果用户或调用方另行说明了素材根目录，也要按该根目录解析同一相对路径。
   - 只有文件名：先查用户明确给出的素材目录；没有目录时，只在当前工作目录和任务上下文明确给出的附件目录中查找。
   - 包含 URL 或在线 slides/wiki/drive/doc 链接：按对应 skill/API 获取内容或 token；不要当成本地路径。
3. 如果路径文本和真实文件名只有轻微差异（例如 `-` 与 `_`、`.` 与 `_`、URL 转义、空格、中文括号、图片平台后缀中的 `~` 被本地保存为 `_`），在同目录用文件名相似匹配找候选；只有唯一高置信候选时使用，并在 `material_inventory.inputs[].notes` 记录映射。
4. 对目录路径必须先列出直接子文件并按扩展名分组；不要只记录目录本身。
5. 找不到的附件写入 `material_inventory.missing`，并说明会用什么 XML-native 或内置能力兜底。找不到附件不能成为空白页的理由。

最小盘点动作：

- 文档/表格/图片/PPT/PDF 至少要记录 `source`、`resolved_path`、`kind`、`usage`、`status`。
- 如果素材会进入页面，`asset_need.candidate_sources` 必须使用解析后的可用路径，而不是原始不可用的路径文本。
- 如果素材只用于理解或风格参考，也必须在 `material_inventory.inputs` 中出现，避免后续 XML 生成阶段遗忘。

## Material Roles

将每个输入素材归入以下角色之一；一个素材可以有多个角色，但要分别说明用途。

| Role | 用途 | 常见来源 | 默认处理 |
|------|------|----------|----------|
| `background_reference` | 补充主题背景、事实、约束、术语、受众信息 | PDF、文档、网页、PRD、报告、会议纪要 | 读取/摘要后影响叙事和页面重点 |
| `style_reference` | 参考 PPT 风格、配色、版式、字体层级、页面流 | PDF、PPTX、已有 slides、内置模板 | 提取设计语言，不默认复制正文 |
| `visual_asset` | 可直接进入页面的视觉素材 | 图片、截图、logo、图表、论文 figure | 上传后放入计划区域；不合适则重绘或兜底 |
| `copy_source` | 文案、标题、大纲、讲稿、卖点、结论来源 | Markdown、TXT、Docx、用户 prompt、会议纪要 | 改写成低密度 slide 文案 |
| `data_source` | 生成表格、指标卡、图表的数据来源 | CSV、XLSX、表格截图、结构化数据 | 转成 chart/table/数字卡 |
| `brand_asset` | 品牌识别和视觉约束 | logo、VI 色板、品牌手册 | 影响 `theme_style` / `visual_system` |
| `rewrite_source` | 需要在原内容、页序或框架基础上二次创作的原稿 | 用户已有 PPTX/PDF/slides、旧版汇报、待美化稿 | 导入/回读后逐页规划保留、精简、新增和重排 |

## Source Priority

1. 用户显式提供的本地素材。
2. 当前工作区内与任务明确相关的素材。
3. 用户给出的在线 slides/wiki/drive/doc 链接。
4. 内置模板库和 IconPark。
5. 联网搜索公开素材或背景信息。
6. XML-native 兜底视觉。

如果多个来源冲突，用户显式提供的素材优先；无法判断时，在 plan 的 `open_issues` 里记录需要用户确认。

## Local Material Handling

- `.pptx`：如果是模板或风格参考，先用 `lark-cli drive +import --type slides` 导入为 online slides，再用 `slides xml_presentations.get` 回读 XML，提取页面流、配色、背景、字体层级、布局骨架和 motif。先判断模板是否包含需要复用的背景图、装饰图、品牌图片或复杂图片版式：如果需要复用，优先把导入后的 slides 作为工作底稿做局部编辑，保留原有图片 token；如果只需要风格和布局骨架，再新建 XML-native 页面。默认不复制模板原文案；如果用户要求“结合模板内容”，再按页角色提取可复用结构。
- `.pptx` 作为待改写原稿：当用户说“在此基础上”“调整布局”“美化”“精简”“增加目录”“内容不用改”“不要随便修改内容”“保留框架”“已有一版 PPT”“根据这份 PPT 生成/丰富/修改”时，该 PPTX 不只是 `style_reference`，必须同时作为 `rewrite_source`。导入并回读全文 XML 后，规划时逐页说明原内容哪些保留、哪些精简、哪些新增、哪些重排。用户明确要求“内容不用改”或“不要随便修改内容”时，默认只改布局、视觉层次、图片/图表表达和页间组织，不改事实、数值和主要文案。优先保留导入页上的既有图片资产并做局部编辑；整页结构变化、换模板或导入页块级编辑不可靠时，才按源页重建 XML-native 页面，再替换或删除旧页。
- `.pdf`：如果是模板、品牌手册或包含可复用页面视觉，先用 `lark-cli drive +import --type slides` 导入并回读 XML，提取视觉系统或页面骨架；如果是论文、报告、PRD 或正文资料，先按内容角色读取/摘要。含可复用 figure/logo/品牌色时，优先作为 `visual_asset` 或 `brand_asset`，不能只用作普通背景文字。
- 已有 online slides：直接回读 XML，把它作为 `style_reference` 或 `rewrite_source`；不要再走导入。
- `.png` / `.jpg` / `.jpeg` 等图片：判断是可直接展示、需要裁切/缩放、还是只用于理解。进入 XML 前必须上传或使用 `@./path` 占位符。
- `.md` / `.txt` / 文档类内容：作为 `copy_source` 或 `background_reference`，提炼为低密度页面文案，不要整段搬进 slide。
- `.docx` / `.doc`：通常是 `copy_source` 和 `background_reference`。先读取或转换提取正文、标题层级、表格和内嵌图片线索，再改写为 slide 叙事。用户要求“不要杜撰数据”时，数值和图表只能来自这类源文件或表格源；缺数据则在 plan 中标注缺口。
- `.xlsx` / `.xls` / `.csv`：通常是 `data_source`。先识别工作表、列名、时间范围、指标和关键数值，再规划 `<chart>` / 表格 / 数字卡。用户明确要求精准图表时，必须让图表数据来自表格，不要手工编造。

## Image Asset Migration

导入的 PPTX/PDF 页面里可能已有 `<img src="file_token">`、背景图或品牌图。这些图片 token 可以在同一个导入后的 presentation 内复用；只有跨到另一个新建 presentation 时，才不能直接复制旧 XML 里的 `<img src>`。

在 `slide_plan.json` 中为模板或原稿记录 `template_asset_strategy`：

- `preserve_imported_page`：模板页含需要复用的背景图、装饰图、品牌图或复杂图片版式。优先在导入页上用 `+replace-slide` / `block_insert` / `block_replace` 做局部编辑，保留现有 `<img>` token。
- `rebuild_in_imported_presentation`：需要重做 XML-native 页面，但仍在同一个导入后的 presentation 内创建/替换页面。可以复用该 presentation 内已有图片 token，无需下载再上传；删除旧页前先确认新页已创建成功。
- `rebuild_new_presentation`：需要另建一个新 presentation。若要复用导入页图片，必须先把图片下载到本地，再上传到目标演示文稿，或在 `+create --slides` 中使用 `@./relative/path` 占位符让 CLI 为新文稿上传并替换 token。
- `mixed`：同一 deck 中部分页面保留导入页图片资产，部分页面重建。每页在 plan 里说明来源页、目标 presentation、是否复用同一 presentation 的图片 token、是否需要重新上传。

首次运行时先判断目标页是否仍在导入后的同一个 presentation 内。只要同一 presentation，就可以复用回读 XML 里的图片 token；跨 presentation 时才需要下载/重新上传。若不能确认目标 presentation，写入 `open_issues`，不要静默复制图片 token 到新文稿。

如果选择 `preserve_imported_page`、`rebuild_in_imported_presentation` 或 `mixed`，且导入后的 slides 会作为最终交付物继续编辑，完成后必须把在线文件标题改成用户任务对应的新标题，避免仍保留导入时的模板/原附件名称。标题修改走 `lark-drive` 的 `drive files patch`，使用 `new_title` 字段；不要为了改标题重建整份 PPT。

## Secondary Creation From Attachments

用户要求“根据附件制作/改写/生成 PPT”时，附件不是可选参考，而是主要创作输入。默认执行以下策略：

- 先用文档类附件建立叙事和事实边界：标题层级、关键结论、数据、案例、限制条件。
- 再按 Local Material Handling 使用 PPTX/PDF/slides 类附件：作为 `rewrite_source` 时保留并重排原页内容；作为 `style_reference` 时提取页流、配色、版式、字体层级和图形 motif；作为内容资料时提取事实、结构和可复用图表。
- 再用图片/截图/logo/figure 建立页面视觉重点：可直接用的图片走上传；不适合直接用的图像改绘成 XML-native 图表、流程图或信息图。
- 表格数据优先生成真实 `<chart>`、表格或数字卡；禁止为了好看而杜撰趋势、比例或数值。
- 如果附件里有素材但 plan 没有使用，必须在 `material_inventory.inputs[].usage` 说明“不使用”的原因，例如低清晰度、与主题无关、重复、版权不明或数据不可解析。

## Search Policy

联网搜索不是默认动作。只有出现以下情况才搜索：

- 用户要求查找公开事实、行业背景、竞品、logo、截图、图片或最新资料。
- plan 中存在关键视觉缺口，本地素材和内置模板都不能满足。
- 用户给出的主题需要真实世界背景才能避免空泛表达。

搜索结果使用规则：

- 图片素材必须先落到本地，再按 Core Rules 的上传路径进入 XML。
- 背景信息必须转化为 `background_reference` 摘要和页面结论，不要把长文本塞进页面。
- 无法确认版权或来源可靠性时，只作为风格/信息参考，不直接作为可展示图片。
- 如果搜索失败或不适合使用，按 `fallback_if_missing` 生成 XML-native 视觉。

## Plan Shape

Deck 级 `material_inventory` 片段示例：

```json
{
  "material_inventory": {
    "local_first": true,
    "inputs": [
      {
        "source": "./template.pdf",
        "resolved_path": "./template.pdf",
        "kind": "style_reference",
        "usage": "Import as slides and extract palette, page flow, typography hierarchy, and motif.",
        "status": "available"
      },
      {
        "source": "./notes.md",
        "resolved_path": "./notes.md",
        "kind": "copy_source",
        "usage": "Condense into slide headlines and speaker intent.",
        "status": "available"
      },
      {
        "source": "./draft.pptx",
        "resolved_path": "./draft.pptx",
        "kind": ["style_reference", "rewrite_source"],
        "usage": "Import and read back XML; preserve source claims and restyle each page.",
        "status": "available"
      }
    ],
    "missing": [
      {
        "need": "Product screenshot for workflow page",
        "search_policy": "Use local screenshot if provided; otherwise search only if user wants real UI imagery.",
        "fallback_if_missing": "Draw a simplified UI wireframe with labeled panels."
      }
    ]
  }
}
```

For a slide derived from a `rewrite_source`, add source-page mapping inside that slide plan, for example:

```json
{
  "source_page": 3,
  "source_operation": "restyle",
  "preserve_content": "Keep the original claim, metrics, and section role; improve layout hierarchy and redraw the chart."
}
```

Page 级 `asset_need` 示例：

```json
{
  "asset_type": "screenshot",
  "source_preference": "local_first",
  "purpose": "Show the target workflow state instead of describing it with bullets.",
  "candidate_sources": ["./assets/workflow.png"],
  "suggested_query": "product workflow screenshot",
  "fallback_if_missing": "Draw a simplified UI wireframe with three panels and callout labels."
}
```

For a page without a meaningful asset need, use:

```json
{
  "asset_type": "none",
  "source_preference": "none",
  "purpose": "No external or simulated asset needed; the page is text-led.",
  "candidate_sources": [],
  "suggested_query": "",
  "fallback_if_missing": "Use typography, spacing, and simple accent shapes only."
}
```

## Supported Asset Types

- `paper_figure`: figure from a paper or technical article.
- `architecture_diagram`: system components, data flow, dependency map, or model structure.
- `icon`: small semantic symbol for a concept, step, role, or status.
- `logo`: brand, product, team, or customer mark.
- `chart`: line, bar, pie, radar, area, or combo data visual. Note: `<chart>` does not support funnel or scatter; map those to `<whiteboard>` at generation time.
- `infographic`: composed visual explanation, usually combining labels, numbers, and simple shapes.
- `screenshot`: product UI, terminal output, workflow state, or page capture.
- `flow_diagram`: process, sequence, decision tree, or mechanism diagram.
- `none`: explicitly no asset needed.

Do not invent new asset types unless the user asks for a special visual format. If a need is close to these types, choose the closest one and explain the detail in `purpose`.

## Planning Guidance

Match source type to slide role. Detailed geometry belongs in `visual-planning.md`; this mapping only helps choose `asset_need`.

- `architecture-diagram` layout usually pairs with `architecture_diagram` or `flow_diagram`.
- `process-flow` layout usually pairs with `flow_diagram`, `icon`, or `infographic`.
- `comparison` layout often works with `icon`, `chart`, or `infographic`.
- `timeline` layout often works with `icon`, `chart`, or shape-based milestone markers.
- `big-number` layout often works with `chart`, `data_source`, or `infographic`.
- `image-left-text-right` and `image-right-text-left` can use `screenshot`, `paper_figure`, `logo`, `infographic`, or a style reference layout.

`suggested_query` is a future lookup hint. Execute the search only when the search policy says remote material is needed and local sources are insufficient.

`fallback_if_missing` must be concrete enough to turn into XML, for example:

- "Draw a simplified attention matrix with 5 token labels, semi-transparent cells, and arrows to output token."
- "Use three grouped boxes with arrows from client to gateway to service; add small protocol labels."
- "Render a mini bar chart with 4 bars using shapes and value labels."
- "Use a bordered UI wireframe with product area labels, not an empty image."

Weak fallbacks to avoid:

- "Use a placeholder."
- "Find another image."
- "Leave blank if unavailable."
- "Use generic decoration."

## Plan To XML Contract

When generating XML:

1. Apply `material_inventory` first: local style references, copy sources, data sources, and visual assets decide what each page can use.
2. If a real visual asset exists and the workflow supports it, place it in the planned visual region.
3. If no asset exists, immediately render `fallback_if_missing` with XML-native shapes, text, lines, arrows, tables, whiteboard diagrams, or chart-like elements.
4. Size the fallback to satisfy `visual_focus`; it should be a real page element, not a tiny decoration.
5. Keep text-density limits. Do not compensate for missing assets by adding long bullet text.
6. After creation, fetch the presentation and verify asset pages are not blank and that each planned fallback is visible when no real asset was used.
