# 规划层

新建演示文稿或大幅改写页面时，必须先写 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`，再生成 XML。这个文件是演示文稿的设计中间层，用来把叙事、页面角色、布局、视觉重点和文字密度固定下来，避免从用户提示直接跳到 XML。

小型已有页编辑可豁免，例如只替换一个标题、改一个数字、插入一个块、上传并插入一张图。只要任务会重排多页、生成新演示文稿、替换整页结构，仍然需要规划层。

## 必需流程

1. 理解用户需求，必要时澄清主题、受众、页数、风格。
2. 激活素材处理层：按 `asset-planning.md` 解析提示词中的附件路径、素材目录、上传文件名和链接，盘点用户提供的本地素材、可引用链接和缺口素材；本地素材优先，没有合适本地素材时再使用内置模板或联网搜索。
3. 选择唯一规划目录：`.lark-slides/plan/<deck-or-task-id>/`。
4. 先创建目录：`mkdir -p .lark-slides/plan/<deck-or-task-id>`。
5. 写入 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`。
6. 读取 `xml-schema-quick-ref.md`、`visual-planning.md` 和 `asset-planning.md`。
7. 按规划文件、视觉规划和素材规划规则逐页生成 XML，把 `layout_type`、`visual_focus`、`text_density` 转成具体页面几何和文本量约束，并把缺失素材转成可执行兜底视觉。
8. 创建或大幅改写后，按 `validation-checklist.md` 做显式验证；本文件只要求验证记录能说明规划到 XML 的对应关系。

素材和模板不能代替规划文件。素材处理层只能影响背景理解、`theme_style`、`visual_system`、页面流、文案输入、布局选择和局部视觉骨架；最终仍必须有 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`。

如果用户提供 `.pptx` 或 `.pdf`，并称其为 PPT 模板、幻灯片模板、版式/风格参考，先按 `lark-drive` 的 `drive +import --type slides` 导入为在线幻灯片，并把回读 XML 作为 `style_reference`。模板/风格参考不等于一定重建新页：如果模板含需要复用的背景图、装饰图、品牌图片或复杂图片版式，优先把导入后的在线幻灯片作为工作底稿，保留图片令牌并局部编辑；如果只需要风格和布局骨架，再新建 XML 原生页面。导入是写操作；用户已经明确要求“根据该附件生成/改写 PPT”时可视为已有意图，否则先确认。

如果用户提供 `.pptx`，并要求“在此基础上修改 / 调整布局 / 美化 / 精简 / 增加目录 / 内容不用改 / 不要随便修改内容 / 保留框架 / 已有一版 PPT”，该文件是 `rewrite_source`，不是普通模板。导入并回读 XML 后，`slide_plan.json` 必须逐页记录原稿内容的保留、精简、新增和重排策略；优先保留导入页上的既有图片资产并局部编辑，整页结构变化、换模板或导入页块级编辑不可靠时，才按源页重建 XML 原生页面，再替换或删除旧页。不得直接新生成一套脱离原稿的页面。

不要把附件路径只当作提示词文本。像 `附件文件路径：path/to/report.docx` 这样的路径必须解析到真实文件；相对路径按当前工作目录和用户明确给出的素材根目录解析，不能硬编码某个固定附件目录。

## 规划路径

每个演示文稿或任务使用独立的规划目录，避免同一工作区内多个演示文稿相互覆盖。

推荐 ID：

- 新建演示文稿：标题短标识加日期时间，例如 `q3-review-20260507-1805`。
- 改写已有 PPT：使用 `xml_presentation_id`。
- 主题不明确或未命名任务：短任务标识加日期时间。

规则：

- 不要复用 `.lark-slides/plan/slide_plan.json` 作为共享路径。
- 写文件前先创建目录。
- 同一个演示文稿的 XML 生成和创建后验证必须复用同一个规划路径。

## 产物生命周期

`.lark-slides/` 是本地智能体状态，用于恢复、迭代和后续编辑；默认不要把它当作源码提交。

保留：

- 创建成功或完成大幅改写后，保留 `.lark-slides/plan/<deck-or-task-id>/slide_plan.json`。规划文件是该演示文稿后续可编辑的设计状态。
- 对后续工作有帮助时，保留小型清单，例如 `xml_presentation_id`、页面 ID、`revision_id`、规划路径和验证状态。

清理或避免保留：

- 创建和验证成功后的临时 XML 请求内容。一次性 XML 优先放在 `/tmp`，或成功后删除生成的 XML 文件。
- 已不匹配当前演示文稿状态的陈旧 XML 草稿。

例外：

- 如果创建失败或部分成功，保留相关 XML 或调试请求内容，直到恢复完成。先记录 `xml_presentation_id`，再拉取当前状态后重试。

## JSON 结构

```json
{
  "presentation_goal": "说明方案并争取下一阶段批准。",
  "audience": "了解领域背景、但需要简洁决策叙事的产品和工程负责人。",
  "theme_style": "清爽商务风格，浅色背景，克制蓝色强调，视觉层级清晰。",
  "material_inventory": {
    "local_first": true,
    "inputs": [
      {
        "source": "./reference.pdf",
        "resolved_path": "./reference.pdf",
        "kind": "style_reference",
        "usage": "导入为在线幻灯片后，提取页面流、配色、字体层级和可复用视觉母题。",
        "status": "available"
      }
    ],
    "missing": [
      {
        "need": "产品界面截图",
        "search_policy": "仅在没有本地截图时搜索；否则使用 XML 原生兜底视觉。"
      }
    ]
  },
  "visual_system": {
    "background_strategy": "内容页使用统一浅色基底；封面和结尾页可使用同一强调色体系下的深色处理。",
    "motif": "可复用的左侧强调条，以及一致的卡片和页眉处理。",
    "color_roles": {
      "primary": "用于主要结构母题，占约 60-70% 的视觉权重。",
      "secondary": "用于分组区域、对比面板或辅助类别。",
      "accent": "仅用于关键数字、结论或焦点标记。"
    }
  },
  "typography_constraints": {
    "title_max_lines": 2,
    "body_max_lines_per_box": 2,
    "footer_max_lines": 1,
    "long_text_handling": "先缩短、拆分到多个文本框，或把细节移到演讲者备注；不要靠极小字号硬塞。"
  },
  "verification_plan": {
    "check_background_consistency": true,
    "check_text_fit": true,
    "check_visual_focus": true,
    "check_asset_rendering": true
  },
  "slides": [
    {
      "page": 1,
      "title": "方案标题",
      "key_message": "该方向已经具备小范围试点条件。",
      "layout_type": "title-cover",
      "visual_focus": "大标题区域配一条简洁支撑语。",
      "asset_need": {
        "asset_type": "logo",
        "purpose": "在开场页传达产品或团队身份。",
        "suggested_query": "产品标志",
        "fallback_if_missing": "使用小型文字徽标和抽象形状母题替代真实标志。"
      },
      "text_density": "low",
      "speaker_intent": "界定本次决策问题，并建立整份演示文稿的观点。"
    }
  ]
}
```

## 必需字段

顶层字段：

- `presentation_goal`：整份演示文稿要达成的目标。
- `audience`：目标读者或听众，以及他们默认具备的背景。
- `theme_style`：视觉语气、配色方向和专业风格。
- `material_inventory`：规划层对本地输入、链接参考、选定用途、缺失素材、搜索策略和兜底方案的记录。遵循 `asset-planning.md`。
- `visual_system`：演示文稿级视觉规则，必须跨页稳定，包括背景策略、复用母题和颜色角色。
- `typography_constraints`：演示文稿级文字行数、文本框密度和长文本处理限制，用于约束 XML 生成前的文案。
- `verification_plan`：最终验证记录必须覆盖的规划专属检查项。创建后的详细验证见 `validation-checklist.md`。
- `slides`：有序页面计划。

每一页必须包含：

- `page`：从 1 开始的页码。
- `title`：页面标题。
- `key_message`：本页必须传达的单一核心观点。
- `layout_type`：计划使用的页面结构。
- `visual_focus`：主导视觉对象或区域。
- `asset_need`：仅用于规划的结构化素材元数据；不要求立即搜索、下载或上传。遵循 `asset-planning.md`。
- `text_density`：`low`、`medium` 或 `high`。
- `speaker_intent`：演讲者为什么需要这一页，以及它如何推进叙事。

## 布局词表

除非用户明确需要自定义结构，否则使用以下 `layout_type` 值之一：

- `title-cover`
- `section-divider`
- `two-column`
- `image-left-text-right`
- `image-right-text-left`
- `big-number`
- `timeline`
- `comparison`
- `architecture-diagram`
- `process-flow`
- `quote-highlight`
- `conclusion`

该值必须影响 XML 几何结构，不能只是标签。例如，`timeline` 应生成横向或纵向序列，`comparison` 应生成清晰并排区域，`big-number` 应为大指标保留主导空间。

## 文字密度规则

- `low`：标题加 1 条短陈述，或 1-3 个很短的标签。
- `medium`：标题加 2-4 条简洁要点，或 2-4 个带标签区域。
- `high`：仅在用户确实需要细节时使用；优先用表格、分栏或分组区域，不要使用长项目符号列表。

不要让所有页面都变成“标题 + 项目符号”。对于 4 页及以上的演示文稿，在内容允许时尽量使用至少 4 种不同的 `layout_type`。

文字密度必须匹配计划中的几何结构。如果页面需要长标题、双语标签、论文图注、法律声明或密集技术表述，必须记录如何缩短、拆分或移到演讲者备注。不要依赖小字号或紧凑文本框来塞下内容。

## 视觉系统规划

生成 XML 前，定义能贯穿整份演示文稿的视觉系统：

- `background_strategy`：说明普通内容页的默认背景，以及哪些页面角色可以有意不同。不要让页面使用接近但不一致的背景色。
- `motif`：选择一到两个可复用结构装置，例如侧边栏、页眉轨道、编号节点、卡片处理、图示泳道或章节色带。母题要足够一致，让页面看起来属于同一套设计。
- `color_roles`：分配主色、辅助色和强调色角色。同一种颜色不能在不同页面表达无关含义。
- `cover_content_relationship`：如果封面使用不同的深色或图片主导处理，说明它如何通过共享颜色、母题或几何关系连接内容页。
- `closing_relationship`：如果结尾页呼应封面，明确写出，避免看起来像临时换了主题。

这些是规划约束，不是装饰备注。它们必须影响生成 XML 中的坐标、背景填充、形状样式和文本位置。

## 迭代状态

继续编辑已有演示文稿时，更新同一个规划路径，不要创建脱节的新规划文件。规划文件必须和已经实际创建的内容保持一致。

长任务推荐使用的可选字段：

- `deck_status`：当前页数、已知目标页数，以及最后验证的版本或时间戳。
- `created_slides`：页码、已知页面 ID 和页面角色。
- `assets_used`：来源、适用时的本地路径、已知上传令牌，以及使用它的页面。
- `open_issues`：仍需修正的布局、文本适配、素材或一致性风险。

不要因为之前的演示文稿用过某个模式就硬编码页码。应按页面角色和证据需求规划，例如“来源中有可读图时，方法概览页应使用图”，而不是把截图、图表或示意图绑定到固定页码。规划文件应描述决策规则，而不是僵硬模板序列。

## 素材规划

`material_inventory` 记录 XML 生成前的演示文稿级来源处理；`asset_need` 记录页面级视觉需求。两者都遵循 `asset-planning.md`。

本地素材优先于远程搜索。常见素材角色：

- `background_reference`：用于理解主题、事实、受众或约束的文件或链接。
- `style_reference`：用于配色、字体、布局、母题和页面流的 PDF、PPTX、在线幻灯片或模板。
- `visual_asset`：可能出现在页面中的图片、截图、标志、图标、图表、示意图或论文图。
- `copy_source`：作为内容输入的正文、提纲、笔记、PRD、报告或转写稿。
- `data_source`：用于图表或表格的数据表、CSV/XLSX、指标或结构化数值。
- `rewrite_source`：需要保留、优化、精简、扩展或重组的已有 PPT/PDF/在线幻灯片，不应只当作宽泛风格参考。

规划页面前，先解析所有附件路径，并写入 `material_inventory.inputs`。每个可用本地输入应包含：

- `source`：用户原始提供的路径或文件标签。
- `resolved_path`：实际存在的本地路径；能被 `lark-cli` 使用时，优先记录相对当前工作目录的路径。
- `kind`：一个或多个素材角色。
- `usage`：它将如何影响叙事、视觉、数据或风格。
- `status`：`available`、`imported`、`uploaded`、`read`、`skipped` 或 `missing`。
- `notes`：可选映射细节，例如“用户提供的相对路径已按指定素材目录解析”。

如果附件是模板/风格演示文稿或 PDF，并已导入为在线幻灯片，在已知时还要记录 `imported_xml_presentation_id` 或 `import_ticket`，然后把导入 XML 作为 `style_reference`。

对导入的模板/风格演示文稿，还要按 `asset-planning.md` 记录 `template_asset_strategy`：`preserve_imported_page`、`rebuild_in_imported_presentation`、`rebuild_new_presentation` 或 `mixed`。在同一个已导入演示文稿内创建或替换页面时，可以复用导入页的图片令牌；不要把 `<img src>` 令牌直接复制到另一个新演示文稿，除非已经把图片下载并重新上传到目标演示文稿。如果导入的在线幻灯片文件会成为编辑后的最终交付物，记录 `target_title`，并在编辑完成后重命名在线文件，避免仍保留源模板或附件标题。

如果附件是 `rewrite_source`，每个受影响页面计划都应说明来源页或来源章节，以及预期操作：`preserve`、`condense`、`expand`、`reorder`、`restyle` 或 `replace_visual_only`。对于“内容不用改”类请求，默认使用 `replace_visual_only` 或 `restyle`，并保持原始论断、数字、名称和页面意图不变。

如果本地 `.pdf` / `.pptx` 是风格参考，使用 `lark-drive` 将其导入为在线幻灯片，再用 `xml_presentations.get` 读取 XML 后规划。这是写操作，需要用户意图。默认只提取设计语言；除非用户要求，否则不要复制源文本。

单个计划素材使用对象，多个真实需求使用数组；没有有用素材时使用 `asset_type: "none"`。每个计划素材必须包含：

- `asset_type`：`paper_figure`、`architecture_diagram`、`icon`、`logo`、`chart`、`infographic`、`screenshot`、`flow_diagram` 或 `none`。
- `purpose`：该素材为什么能帮助传达本页核心观点。
- `suggested_query`：仅作为后续查找提示的短查询；除非另有要求，否则不要执行。
- `fallback_if_missing`：使用形状、标签、表格、白板图或占位面板构成的具体 XML 原生兜底视觉方案。

详细规则和示例见 `asset-planning.md`。

合格示例：

- `{"asset_type":"architecture_diagram","purpose":"解释组件关系。","suggested_query":"服务架构图","fallback_if_missing":"用分组方框、连接箭头和短标签绘制组件图。"}`
- `{"asset_type":"logo","purpose":"标识客户场景。","suggested_query":"客户标志","fallback_if_missing":"使用小徽标中的文字标签。"}`
- `{"asset_type":"chart","purpose":"展示采用率趋势。","suggested_query":"月度采用率趋势图","fallback_if_missing":"绘制带轴标签和数据点的简单趋势折线图。"}`

## XML 生成约定

写每页页面 XML 前，把规划字段映射成具体决策：

- `key_message` 决定标题、主导论断或主要结论。
- `material_inventory` 决定哪些本地素材、导入风格参考、远程搜索结果或兜底方案允许影响页面。
- `layout_type` 决定坐标结构和元素类型。具体布局规则见 `visual-planning.md`。
- `visual_focus` 决定最大视觉区域或被强调对象。
- `text_density` 限制可见文字量。
- `asset_need` 只用于指导占位图、图标、图表、截图或基于形状的兜底视觉。缺失真实素材时必须使用 `fallback_if_missing`，不能留下空白区域。

创建或改写 PPT 后，以 `validation-checklist.md` 作为验证依据。验证记录还应说明规划专属映射：

- 页数与规划文件一致。
- 计划中的 `key_message`、`layout_type`、`visual_focus`、`text_density` 和 `asset_need` 已体现在 XML 中。
- `visual_system` 和 `typography_constraints` 明显影响了背景、结构、层级和文本位置。
- 维护的 `deck_status`、`created_slides`、`assets_used` 或 `open_issues` 字段已更新为当前演示文稿状态。
