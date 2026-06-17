# Validation Checklist

创建或大幅改写演示文稿后，必须做一次显式验证。目标是发现空白页、XML 损坏、内容截断、明显溢出、弱视觉层级和未验证输出。

小型已有页编辑也要做对应范围的验证：至少读取被改页面或全文 XML，确认目标元素已更新且未破坏周边结构。

## Required Flow

1. 记录创建或编辑返回的 `xml_presentation_id`，以及已知的 `slide_id` / `revision_id`。
2. 用 `xml_presentations.get` 回读全文 XML。
3. 检查实际页数是否符合计划或用户要求。
4. 检查每页 `<data>` 内是否有预期主要元素。
5. 检查没有明显空白页、破损页、缺失标题或缺失主视觉。
6. 检查页面不是全部退化为标题加 bullet list。
7. 检查视觉层级：标题、主视觉、支撑信息三者可区分。
8. 检查明显溢出和布局风险：重叠、越界、底部拥挤、长文本框。
9. 在最终回复中给出简短验证记录。

回读命令：

```bash
lark-cli slides xml_presentations get --as user \
  --params '{"xml_presentation_id":"YOUR_ID"}'
```

## Automated XML Text Overlap Lint

回读 XML 保存到本地文件后，优先运行 XML 语法和文本重叠静态检查：

```bash
python3 skills/lark-slides/scripts/xml_text_overlap_lint.py --input <presentation.xml>
```

通过标准：

- `summary.error_count == 0`。任何 error 都必须先修复再交付。
- 当前工具只检查 XML well-formed 和文本元素之间的明显重叠；它不检查越界、文本高度不足、图文压盖、表格/图表压盖或底部拥挤。
- 该工具不能替代页数核对、关键内容核对或真实视觉验收。

常见 code 的处理方向：

| code | 含义 | 处理方式 |
|------|------|----------|
| `xml_not_well_formed` | XML 语法错误或文本未转义 | 修复标签闭合、属性引号、`&` / `<` / `>` 转义 |
| `bbox_overlap` | 文本元素的估算绘制区域明显重叠 | 拉开文本坐标、缩小文本框/字号，或改成明确的分栏/分组结构 |

## Automated SVGlide Plan And SVG Preflight

走 `slides +create-svg` 前，必须先运行 SVG plan/source preflight：

```bash
python3 skills/lark-slides/scripts/svg_preflight.py \
  --route-manifest skills/lark-slides/references/routes/create-svg/route.manifest.json \
  --report-scope public \
  --plan .lark-slides/plan/<deck-id>/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/pages/page-001.svg
```

通过标准：

- `summary.error_count == 0`，任何 error 都必须先修复再调用 live API。
- SVG 生成脚本必须先完整结束，再运行 `svg_preflight.py`；不要让生成和 preflight 并行读写同一 output 目录。
- `style_preset` 必须存在于 `references/style-presets.json`。
- `seed_id` 必须存在于 `references/svg-seeds.json`，并且 plan 的 `layout_skeleton_id`、`layout_family`、`visual_recipe`、`layout_boxes`、`content_budget`、`text_budget_by_role`、`footer_safe_zone` 与 seed 一致。
- public `visual_recipe` 必须存在于 `references/svg-recipes.json`；研究文档里的 dotted recipe 名称不能直接写入 `slide_plan.json`。
- `style_selection_reason` 必须说明为什么这个 preset 适合当前 deck。
- `style_system` 必须包含 palette、typography、background strategy 和 motif。
- 多页 deck 必须声明 `page_rhythm` / `deck_rhythm`，用于检查节奏、密度变化和重复页风险；authoring profile 下缺失会给 warning，`validation_profile=golden` 或 strict profile 下为 error。
- 每页必须包含 `seed_id`、`layout_skeleton_id`、`layout_boxes`、`content_budget` 或 `text_capacity`、`text_budget_by_role`、`one_idea` 或 `key_message`、`reserved_bands.footer`、`footer_safe_zone`、`vertical_text_policy`、`visual_recipe`、`visual_signature`、`svg_effects`、`required_primitives`、`svg_primitives`、`xml_like_risk`、`content_density_contract`、`risk_flags`、`source_policy`。
- Strategist contract 字段必须可检查：每页声明 `page_type`、可定位到 layout box / SVG element / component / bbox 的 `main_visual_anchor`；`reference_asset` 不能只写描述性文字，必须是 `{source, asset_id/id}` 或带 source/license/path 的资产元数据。
- declared `svg_effects` 和 `required_primitives` 必须能在对应 SVG source 中命中。
- 可见 slide 文本不得泄漏 preset 名称、source token、prompt、tool name 或本地文件路径。

常见 code 的处理方向：

| code | 含义 | 处理方式 |
|------|------|----------|
| `plan_style_preset_unknown` | plan 引用了不存在的 35 preset | 从 `style-presets.json` 选择有效 `style_id` |
| `plan_unknown_seed` | plan 引用了不存在的 `seed_id` | 从 `svg-seeds.json` 选择有效 seed |
| `plan_seed_visual_recipe_mismatch` | seed 和 `visual_recipe` 不匹配 | 换 seed 或换 recipe，保持结构一致 |
| `plan_seed_layout_skeleton_missing` / `plan_seed_layout_skeleton_mismatch` / `plan_seed_layout_skeleton_drift` | plan 没有继承 seed skeleton，或关键 layout box 偏离 seed 容忍范围 | 从 `svg-seeds.json` 复制 skeleton/boxes；需要大改结构时新增或更换 seed |
| `plan_seed_content_budget_loosened` | plan 试图放宽 seed 的文本容量预算 | seed budget 是上限，只能收紧；超量时删内容、拆页或换 seed |
| `plan_missing_text_budget_by_role` / `plan_seed_text_budget_loosened` / `plan_text_role_budget_exceeded` | 缺少 role 级文本预算，或局部 title/body/callout/footer 超量 | 按 role 删减、拆页或换 seed，不要缩小字号、隐藏文本或改竖排 |
| `plan_missing_layout_boxes` | plan 没有声明 seed 派生 layout boxes，或缺必需 box role | 从 seed 复制并调整 title/body/visual/chart/footer boxes |
| `plan_text_box_count_exceeded` / `plan_source_text_box_count_exceeded` | plan 或最终 SVG 的文本盒数量超过 seed 上限 | 减少文字表面或换更高容量 seed |
| `plan_source_text_box_count_below_seed_minimum` | 最终 SVG 没保留 seed 要求的最低文本结构 | 补齐 seed 需要的可读文本盒，或换更稀疏 seed |
| `plan_content_budget_exceeded` / `plan_title_capacity_exceeded` / `plan_body_capacity_exceeded` / `plan_footer_capacity_exceeded` | 文案超过 seed 的容量预算 | 删减文案、拆页或换更合适的 seed |
| `plan_source_content_budget_exceeded` | 最终 SVG 可见文本超过 seed 容量 | 缩短实际渲染文案或拆页 |
| `plan_source_role_text_budget_exceeded` | 最终 SVG 某个 role 的字符数、文本盒、行数或字号违反 seed 预算 | 修 source SVG 对应 role；不要只改 plan 字段 |
| `plan_text_box_outside_seed_layout_box` | 最终 SVG 文本盒偏离 seed 派生 layout box | 按 plan box 重排 SVG，或先更新 plan box 再渲染 |
| `plan_footer_reserved_band_violation` | footer/source/note 文本不在 footer 保留区，或正文侵入 footer band | 调整 body/footer boxes，让 footer 类文本落入 `reserved_bands.footer` |
| `plan_missing_footer_safe_zone` / `footer_safe_zone_intrusion` | 缺少 footer safe-zone，或非 footer 文本进入/贴近 footer band | footer/source/legal/page mark 只放 zone 内；正文、图例、标签和 chart label 上移 |
| `plan_vertical_text_policy_missing` / `unsupported_vertical_text` / `vertical_text_disallowed_role` / `vertical_text_budget_exceeded` | 未声明竖排策略，或正文/长文使用竖排、writing-mode、旋转文本 | 默认改回横排；只有 seed 允许的短装饰标签可保留 |
| `label_text_overlap` / `right_title_safe_zone_crowded` | 标签、badge、装饰块或右上标题栏压住可读文本 | 移动标记、扩大文本承载面、拆分标题区或减少 chip 文案 |
| `plan_required_for_create_svg_route` | create-svg route 只传 SVG，没传 `--plan` | 必须带 `slide_plan.json`，防止绕过 seed/recipe/layout gate |
| `hidden_visible_text` / `clipped_visible_text` | 可见文案被 hidden/opacity/overflow/clip-path/mask 隐藏或裁切 | 删除隐藏文案、扩大 text box，或取消裁切 |
| `plan_unknown_visual_recipe` | plan 引用了不存在的 public recipe，或把 dotted research id 当 runtime id | 从 `svg-recipes.json` 选择有效 underscore id，或在 create-svg private route 中使用 `visual_recipe=route_private` |
| `plan_missing_visual_signature` | 页面没有声明 SVG 视觉记忆点 | 写清这页相对普通 PPT/XML 模板的独特视觉结构 |
| `plan_missing_svg_effects` | 页面没有声明 SVG 表达能力 | 声明真实会绘制的 `path`、`connector_flow`、`gradient`、`texture`、`chart_geometry` 等 |
| `plan_svg_effect_not_found` | plan 声明的 effect 没在 SVG source 中出现 | 修改 SVG source，或删除不真实的 effect 声明 |
| `plan_missing_page_rhythm` | 多页 deck 没有声明节奏合同 | 添加 deck-level `page_rhythm`，说明封面/章节/内容/总结节奏和重复页约束 |
| `plan_missing_page_type` | 页面缺少可检查页型 | 添加 `page_type`，并让 renderer/layout/visual_recipe 与页型一致 |
| `plan_missing_main_visual_anchor` | 主视觉锚点缺失或只是自然语言 | 指向 layout box role、`#svg-element-id`、component_id，或写明确 bbox |
| `plan_main_visual_anchor_not_met` | SVG source 没有在主视觉锚点区域生成可见几何 | 调整 source SVG，把主视觉放回声明的锚点区域，或先更新 plan anchor |
| `plan_reference_asset_unstructured` | `reference_asset` 是纯文字或缺少 source/id/path | 改成结构化 source metadata；没有参考资产时显式写 no_asset |
| `plan_style_preset_visible_leak` | 可见文本泄漏 preset 名/source token | 仅在 plan metadata 中保留 preset 信息，画面只写用户主题内容 |

## SVGlide Aesthetic Preview Review

`svg_preflight.py` 通过后，走 `slides +create-svg` 前还必须做本地预览审查。读取 [svg-aesthetic-review.md](svg-aesthetic-review.md)，检查 rendered preview，而不是只看 plan 字段或静态 XML。

Project runner quality lane 还必须在 `dry_run` 前运行 `preview_lint` 和
`quality_gate`。手工排障路径可以不跑 preview lint 继续定位问题，但该路径
不得进入 guarded live creation、production delivery 或 golden regression promotion。

## SVGlide Archetype Drift Checks

SVGlide 项目必须同时检查计划、执行 manifest、SVG source 和 receipts。不要只
验证单个文件。

- `slide_plan.page_count`、`slide_plan.slides`、`slide_plan.svg_files` 和
  `project_manifest.pages` 的数量必须一致；少传 SVG input 是 error，不允许
  preflight 只检查已传入的子集。
- `prepare` receipt 在 plan、manifest 或 source SVG 变化后必须失效；后续
  `preflight`、`preview_lint`、`quality_gate`、`dry_run` 不得复用旧 prepare。
- 声明 `chart_type` 或 SVGlide design pattern chart 参考时，SVG 必须命中对应几何合同：
  `bubble_chart` 至少有多枚圆形节点，`donut_chart` 至少有环形/圆形结构和中心
  文本，`bar_chart` 至少有可识别轴/条形/数值区域。不能把图表页退化成普通
  卡片、closing 或 bullet list。
- `design_pattern_selection.selected_assets` 只放真正启用并落地的参考资产；
  `enabled:false` 可作为候选保留，但不进入 quality gate。启用资产必须由
  `receipts/design-pattern-usage.json` 的 page-level trace 证明。
- `visual_design_contract.required_visual_evidence` 必须由
  `receipts/emitted_components.json` 的 page-level component `effects`、
  `primitives`、`renderer_id` 或 component id 证明。缺少 evidence 时
  `quality_gate` 失败；这类问题不能只改 plan 字段，必须修 renderer 或 SVG。
- `quality_gate` 会把 preflight 中的 Strategist contract issue codes 写入
  `strategist_contract` 摘要，并把 visual design contract 证明写入
  `visual_design_contract` 摘要；`validation_profile=golden` 要求零 warning、结构化
  component report，以及正式 schema 的 design-pattern usage receipt。
- SVGlide design pattern 参考只允许变成 SVGlide-safe 的页型、图表几何、节奏、色彩纪律
  和审查规则；不要复制 raw SVG、图片或 PPTX/DrawingML 导出实现。

通过标准：

- 所有页面都检查过，不只检查封面。
- 无标题、正文、badge、装饰线、图片框、图表标签的明显重叠或裁切。
- root 和主要内容遵循 `960 x 540` 画布和 safe area。
- 每页有清晰 `visual_focal_point`，视觉焦点对应 `visual_signature`。
- 页面不是普通卡片/bullet 页伪装成 SVG；应能看出 path、texture、chart geometry、connector flow、image overlay、icon system、dashboard frame 或其他 SVG-native 结构。
- 多页没有重复出现同一个布局错误；如果有，必须修生成规则并重新生成相关页面。
- 用户可见交付 deck 的审美目标默认不低于 `75/100`；低于 `65/100` 应重新生成或显式降级为草稿。
- 验证记录包含 `preview_path`、`visual_score`、`threshold`、`issue_ids`、`action`。`action=create_live` 才能继续调用 live API；`action=repair_and_rerun` 必须先修 source SVG / plan 并重新跑 preflight。

live creation 要求 `quality_gate.status=passed`。`passed_with_waiver` 只允许
authoring/debug dry-run，不得用于 production、golden 或 live lane。

## Chart Data Verification

当页面声明 `chart_type`、chart marker、或图表类 reference asset 时，不能只检查
“有图表几何”。还要检查数据到视觉坐标的映射是否可信。

计划层必须包含：

```json
{
  "chart_decision": {
    "chart_type": "bar_chart",
    "reason": "bar chart fits category comparison and supports one takeaway",
    "data_ref": "brief",
    "anchor_role": "chart",
    "bbox_tolerance_px": 12
  },
  "chart_verification": {
    "status": "required",
    "receipt": "receipts/chart-verify.json",
    "checks": ["plot_area", "mark_count", "label_alignment", "scale_mapping"]
  }
}
```

验证记录建议写入 `receipts/chart-verify.json`，并至少包含：

- `data_source`: source pack id, inline chart spec id, or explicit unavailable marker.
- `chart_type`: normalized chart type.
- `mapping_formula`: how values map to bar height/width, line point y, stacked share, radar radius, or node/flow weight.
- `expected_marks`: expected bars, points, stacks, sectors, vertices, or flows.
- `verification.status`: `passed`, `failed`, or `not_applicable_missing_data`.

最终验证记录要写清：

```text
Chart data: checked N/N chart pages; failed M; missing data K.
```

若没有可信数据源，页面可以保留示意图，但必须在 `source_policy` 中写明 no numeric
claims，不得伪造真实数值、排名、比例或来源。

## Live Create And Image Token Gate

`svg_preflight.py` 通过后，仍必须跑 `slides +create-svg --dry-run`。Dry-run 要确认：

- 请求链路是 create presentation 后按 `--file` 顺序追加 SVG 页。
- 含 `@./assets/...` 的 SVG 会先出现 `medias/upload_all`，再在 page content 中出现 transport metadata。
- 纯 SVG 发布版不得残留 `<image>`、`@./assets` 或 `uploaded_file_token`。
- 所有 `url(#id)` 引用都有对应 `defs` id；dry-run 不一定能拦住未定义渐变。

对 `ppe_pure_svg` 或其他尚未稳定证明支持 image token 的 live lane，先单独 smoke：

- 一页纯 SVG：验证 lane 支持 SVGlide parser。
- 一页含本地 `@./assets/...` 图片：验证 upload 后的 image token 能被 `/slide` 解析。

如果纯 SVG 页成功、图片页在上传成功后 `/slide` 报 `nodeServer internal error`，短期线上发布可切到单独 `online-pure` SVG 目录，用 shape、path、gradient 和 texture geometry 替代图片区域。这个 fallback 只用于 live 发布，不得覆盖带真实图片的 authoring preview，并必须在最终交付说明中标注。

Project runner live lane 中，`ppe_proof` 必须把 raw environment evidence
标准化为 `receipts/env-proof.json`；`live_create` 只读取 normalized receipt。
proxy 仅配置但未观测到实际命中，不足以发布。

这一步和 preflight 分工如下：

- `svg_preflight.py`: 负责协议、plan、枚举、必填字段、bbox、primitive 命中和确定性错误。
- `svg-aesthetic-review.md`: 负责截图/预览视角的层级、节奏、压迫感、重复问题、可读性和 SVG 视觉优势。

## Page Count And Structure

- 实际页数必须等于用户要求或 `slide_plan.json` 的页数。
- 如果创建过程部分失败，先记录已创建的 `xml_presentation_id`，再回读确认哪些页已写入。
- 每页都应包含 `<data>`，且 `<data>` 内至少有一个非背景主体元素。
- 封面、章节页、总结页可以文字较少，但不能只有空背景。
- 技术解释页、对比页、流程页、架构页必须有匹配的结构元素，例如分组框、连线、时间轴、表格或图形化区域。

## Expected Elements

按 `slide_plan.json` 和用户要求逐页核对：

- 标题或主结论存在，并能对应 `key_message`。
- `layout_type` 对应的主要结构已生成。
- `visual_focus` 是页面中最醒目或最大的信息区域之一。
- `text_density` 影响了文本量，没有用长 bullet 框替代规划。
- `asset_need` 有真实素材时已放入正确区域；没有真实素材时，`fallback_if_missing` 已用 XML 形状、线条、标签、表格或图表兜底。

如果用户指定了关键页，例如“架构解释”“Self-Attention 机制解释”“对比或演进视角”“总结页”，最终验证记录必须逐项说明这些页已存在。

## Blank Or Broken Page Signals

把下面情况视为需要修复后再交付：

- `<data/>` 为空，或只有背景、装饰线、空 `<content/>`。
- 关键文本没有出现在回读 XML 中。
- 图片仍是 `@./path`，或 `<img src>` 是 http(s) 外链。
- 页面依赖的图片区域为空，且没有 fallback visual。
- 返回 XML 缺页、页序明显错误，或某页内容被 shell 截断。
- 大量形状坐标完全相同，导致主体内容重叠。
- 渐变背景回退成空白或白底，导致文字不可读。

## Whiteboard Elements

`slide.get` 回读 XML 时，`<whiteboard>` 块只返回位置属性（`topLeftX`、`topLeftY`、`width`、`height`），SVG / Mermaid 内容**不随 XML 返回**。

- whiteboard 验证只能核对坐标是否越界：`topLeftX + width ≤ 960`，`topLeftY + height ≤ 540`。
- SVG 和 Mermaid 内容的正确性无法通过回读 XML 验证，需要人工视觉验收。
- 不要在验证记录中声称 whiteboard 内容已验证，除非用户确认了视觉效果。

## Layout And Overflow Risk

优先修复这些明显风险：

- 正文或标签框高度不足，文本很可能被截断。
- 多个主体元素在同一区域重叠，而不是有意叠加背景。
- 重要内容越过画布边界，或贴近底部超过 `y=500`。
- 高密度页使用单个长 bullet list，没有分栏、表格或分组。
- 标题、主视觉、正文的字号和颜色差异太弱，视觉层级不清。
- 所有内容页都是同一套标题加 bullets 坐标。

## Verification Record

最终回复必须包含简短验证记录，建议格式：

```text
验证记录：
- 回读：已执行 xml_presentations.get，实际页数 N / 预期 N。
- 关键页：架构解释 / Self-Attention / 对比或演进 / 总结页均存在。
- 结构：检查了主要 shape/img/table/chart 元素，无明显空白页或破损页。
- 布局：检查了标题层级、主视觉、重叠/越界/文本溢出风险。
```

不要声称完成了人工视觉验收，除非确实打开或获取了可视化结果。仅从 XML 静态检查得出的结论，应表述为“静态检查未发现明显问题”。
