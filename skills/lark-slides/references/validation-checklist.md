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
  --plan .lark-slides/plan/<deck-id>/slide_plan.json \
  --input .lark-slides/plan/<deck-id>/pages/page-001.svg
```

通过标准：

- `summary.error_count == 0`，任何 error 都必须先修复再调用 live API。
- `style_preset` 必须存在于 `references/style-presets.json`。
- `style_selection_reason` 必须说明为什么这个 preset 适合当前 deck。
- `style_system` 必须包含 palette、typography、background strategy 和 motif。
- 每页必须包含 `visual_recipe`、`visual_signature`、`svg_effects`、`required_primitives`、`svg_primitives`、`xml_like_risk`、`content_density_contract`、`risk_flags`、`source_policy`。
- declared `svg_effects` 和 `required_primitives` 必须能在对应 SVG source 中命中。
- 可见 slide 文本不得泄漏 preset 名称、source token、prompt、tool name 或本地文件路径。

常见 code 的处理方向：

| code | 含义 | 处理方式 |
|------|------|----------|
| `plan_style_preset_unknown` | plan 引用了不存在的 35 preset | 从 `style-presets.json` 选择有效 `style_id` |
| `plan_missing_visual_signature` | 页面没有声明 SVG 视觉记忆点 | 写清这页相对普通 PPT/XML 模板的独特视觉结构 |
| `plan_missing_svg_effects` | 页面没有声明 SVG 表达能力 | 声明真实会绘制的 `path`、`connector_flow`、`gradient`、`texture`、`chart_geometry` 等 |
| `plan_svg_effect_not_found` | plan 声明的 effect 没在 SVG source 中出现 | 修改 SVG source，或删除不真实的 effect 声明 |
| `plan_style_preset_visible_leak` | 可见文本泄漏 preset 名/source token | 仅在 plan metadata 中保留 preset 信息，画面只写用户主题内容 |

## SVGlide Aesthetic Preview Review

`svg_preflight.py` 通过后，走 `slides +create-svg` 前还必须做本地预览审查。读取 [svg-aesthetic-review.md](svg-aesthetic-review.md)，检查 rendered preview，而不是只看 plan 字段或静态 XML。

通过标准：

- 所有页面都检查过，不只检查封面。
- 无标题、正文、badge、装饰线、图片框、图表标签的明显重叠或裁切。
- root 和主要内容遵循 `960 x 540` 画布和 safe area。
- 每页有清晰 `visual_focal_point`，视觉焦点对应 `visual_signature`。
- 页面不是普通卡片/bullet 页伪装成 SVG；应能看出 path、texture、chart geometry、connector flow、image overlay、icon system、dashboard frame 或其他 SVG-native 结构。
- 多页没有重复出现同一个布局错误；如果有，必须修生成规则并重新生成相关页面。
- 用户可见交付 deck 的审美目标默认不低于 `75/100`；低于 `65/100` 应重新生成或显式降级为草稿。
- 验证记录包含 `preview_path`、`visual_score`、`threshold`、`issue_ids`、`action`。`action=create_live` 才能继续调用 live API；`action=repair_and_rerun` 必须先修 source SVG / plan 并重新跑 preflight。

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
