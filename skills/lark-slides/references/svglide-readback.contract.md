# SVGlide Readback Contract

本文只在 `svglide-svg` route admission 之后读取。readback 是 live create 之后的服务端转换验证，不能用本地 preview 替代。

## Inputs

- `07-create/live-create.json`
- `02-plan/slide_plan.json`
- optional `03-assets/assets.json`
- optional `04-svg/prepared/page-###.svg`

## Outputs

- `08-readback/xml-presentations-get.json`
- `08-readback/readback-check.json`

## Required Checks

`svglide_readback.py` 必须尽力检查：

- `presentation_id`：live create 是否返回 presentation id。
- `page_count`：计划页数和回读页数是否一致。
- `slide_ids`：创建出的 slide id 数量是否一致。
- `blank_page`：回读结构里是否存在空白页标记。
- `asset_tokens`：`assets.json` 中的 file token 是否能在回读结构中找到。
- `text_fit`：回读结构中是否出现文本溢出类标记。
- `bounds`：回读结构中是否出现越界/裁切类标记。
- `chart_markers`：源 SVG 含 chart marker 时，回读结构应保留 chart 相关信息。
- `business_claims`：plan 中记录的可见业务事实片段应能在回读文本中找到。
- `input_binding`：记录 `plan_sha256`、`quality_gate_sha256`、`dry_run_sha256`、`ppe_proof_sha256`、`live_create_sha256`、`revision_id`、`expected_slide_count` 和 `created_slide_count`，用于证明 readback 绑定的是当前计划、当前质量门、当前 dry-run/PPE proof 和当前 live create 产物。

## Boundary

readback 是线上转换后的结构检查，不是审美检查，也不是内容策划检查。页面是否“好看”、是否重复由 `aesthetic_review` 和人工检查负责；中文、页型结构、内容厚度和 SVG 文本来源由 `semantic_review` 在 create 前负责。
