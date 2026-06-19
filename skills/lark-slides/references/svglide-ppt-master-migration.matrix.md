# SVGlide 对照 ppt-master 迁移矩阵

本文只在 `svglide-svg` route admission 之后读取。它记录 ppt-master 参考规则如何迁移到 CLI SVGlide，不是要求把 ppt-master 整套本地 PPTX 生成系统搬进 CLI。

## 迁移原则

- 迁移阶段思想、执行锁、资产可追溯、质量门和 readback 语义。
- 不迁移 ppt-master 的本地 `finalize_svg.py -> svg_to_pptx.py` 导出链。
- CLI 仍以 `slides +create-svg` 为交付入口，prepared SVG 仍通过既有 XML presentation API 写入。
- 所有长期约束必须落到 JSON artifact、runner stage 或 check script；不能只停留在提示词。

## Matrix

| ppt-master source | 抽取规则 | CLI SVGlide 落点 | 迁移 |
|---|---|---|---|
| `skills/ppt-master/SKILL.md` Core Pipeline | 串行阶段、每阶段输入输出明确，阻塞点不能跳过 | `svglide_project_runner.py` stage graph, `svglide-workflow.spec.md` | adapt |
| `skills/ppt-master/SKILL.md` Eight Confirmations | 生成前用户确认设计参数；确认后自动继续非阻塞步骤 | `confirm_plan` + `02-plan/plan-confirmation.json` hash 绑定 | yes |
| `templates/spec_lock_reference.md` | `design_spec` 讲 why，`spec_lock` 锁 what；执行时只读锁内值 | `02-plan/slide_plan.json` + `02-plan/svglide.lock.json` | adapt |
| `executor-base.md` per-page spec_lock reread | 防止长 deck 颜色、字体、图标、资产、页面节奏漂移 | `svglide.lock.json` 的 `style_tokens`、`page_contracts`、`asset_contracts` | yes |
| `executor-base.md` template/chart batch read | 模板和图表结构先锁定，生成时按页引用，不临时猜 | `page_contracts[].layout_ref` / `chart_ref`，未来接 template roster | adapt |
| `SKILL.md` Image_Generator | AI/web/user/formula 分流，失败有审计，不留空框 | `assets` stage, `03-assets/assets.json`, `03-assets/asset-manifest.json` | adapt |
| `technical-design.md` image embedding | 开发态可本地引用，交付态必须 token 化或可上传 | `svglide_assets.py` + `svglide_prepare.py` + `slides +create-svg --assets` | yes |
| `SKILL.md` Executor | 真正生成 SVG 的阶段必须在确认和资产后，不能提前写 SVG | `generate_svg` stage | yes |
| `SKILL.md` no sub-agent / no batch generation | ppt-master 禁止 subagent 和批量脚本；CLI runner 不能完全照搬 | CLI 允许执行 generator script，但必须记录 lock/assets/source hash 和 per-page receipt | adapt |
| `shared-standards.md` | SVG/PPT 兼容黑名单要在后处理/创建前阻断 | `svg_preflight.py` | yes |
| `technical-design.md` Quality Gate | 检查失败回到源 SVG 修复，不做静默自动修复 | `preflight -> preview_lint -> aesthetic_review -> semantic_review -> quality_gate` | yes |
| `visual-review` / live preview | 审美问题不是 API contract，但要有可审查产物和阻断动作 | `05-preview/preview.html` + `06-check/aesthetic-review.json` | adapt |
| `technical-design.md` readback | 本地 preview 不能替代服务端转换后的回读 | `svglide_readback.py`, `08-readback/readback-check.json` | yes |
| `finalize_svg.py` / `svg_to_pptx.py` | ppt-master 本地 DrawingML 导出 | 不迁移；CLI 使用 `slides +create-svg` API | no |
| `update_spec.py` | 颜色/字体窄范围批量传播 | 暂不迁移；CLI 通过改 plan/lock 后 rerun stage | no |

## 当前 CLI 执行映射

```text
plan
-> confirm_plan
-> assets
-> generate_svg
-> prepare
-> preview
-> preflight
-> preview_lint
-> aesthetic_review
-> semantic_review
-> quality_gate
-> dry_run
-> live_create
-> readback
```

默认本地验证停在 `quality_gate` 或 `dry_run`。除非用户明确要求，不自动执行 `live_create`。
