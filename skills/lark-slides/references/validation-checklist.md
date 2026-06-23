# Validation Checklist

创建或大幅改写演示文稿后，必须做一次显式验证。目标是发现空白页、XML 损坏、内容截断、明显溢出、弱视觉层级和未验证输出。

小型已有页编辑也要做对应范围的验证：至少读取被改页面或全文 XML，确认目标元素已更新且未破坏周边结构。

## Required Flow

1. 记录创建或编辑返回的 `xml_presentation_id`，以及已知的 `slide_id` / `revision_id`。
2. 用 `xml_presentations.get` 回读全文 XML。
3. 检查实际页数是否符合计划或用户要求。
4. 如果计划基于导入 PDF/PPTX/slides 材料二次创作，检查最终 `xml_presentation_id` 是否等于 `target_xml_presentation_id`；如果另建了 presentation，必须在验证记录中说明用户明确要求另建或导入/回读失败原因。
5. 如果用户材料只用于模板风格或视觉线索，检查它是否仍作为 `rewrite_source` 导入/回读，并确认最终没有交付脱离该材料的新 deck。
6. 检查每页 `<data>` 内是否有预期主要元素。
7. 检查没有明显空白页、破损页、缺失标题或缺失主视觉。
8. 检查页面不是全部退化为标题加 bullet list。
9. 检查视觉层级：标题、主视觉、支撑信息三者可区分。
10. 检查没有遗留模板占位文案、示例公司名、示例日期或与用户主题无关的源模板文字。
11. 检查明显溢出和布局风险：重叠、越界、底部拥挤、长文本框。
12. 在最终回复中给出简短验证记录。

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

## Optional Screenshot Upgrade

如果截图或可视化预览能力可用，优先获取页面截图辅助判断最终效果；截图不能替代 XML 回读和页数核对。

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
- `template_asset_strategy` 为 `preserve_imported_page`、`rebuild_in_imported_presentation` 或 `mixed` 时，不能交付一份脱离导入材料的新 deck。
- 如果计划声明保留材料背景、装饰图、品牌图或复杂图片版式，回读 XML 中应仍存在对应的 `<img src>`、背景图片或等效重绘结构；如果未保留，验证记录必须说明原因。

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
- 导入底稿：如使用导入材料二次创作，最终 presentation 与 target_xml_presentation_id 一致；如不一致，已说明用户明确要求另建或导入/回读失败原因。
- 视觉底稿：如用户材料只提供模板风格或视觉线索，已确认它仍作为 rewrite_source 导入/回读并承载最终二创。
- 内容来源：如模板材料内容不可用，已确认未复制其占位文案；正文来自计划中的 copy_source 或用户输入。
- 截图：截图能力可用时，已用截图辅助判断最终效果。
- 关键页：架构解释 / Self-Attention / 对比或演进 / 总结页均存在。
- 结构：检查了主要 shape/img/table/chart 元素，无明显空白页或破损页。
- 模板清理：未发现模板占位文案、示例公司名、示例日期或无关模板文字。
- 布局：检查了标题层级、主视觉、重叠/越界/文本溢出风险。
```

不要声称完成了截图或人工视觉验收，除非确实打开、获取截图或拿到了可视化结果。仅从 XML 静态检查得出的结论，应表述为“静态检查未发现明显问题”。
