# SVGlide Lock Contract

本文只在 `svglide-svg` route admission 之后读取。`02-plan/svglide.lock.json` 是执行锁，不是第二份完整 plan。它只锁定 SVG 生成和检查必须稳定使用的值。

## 角色边界

- `slide_plan.json`：用户可见计划，描述内容、页序、来源、风格意图。
- `svglide.lock.json`：机器执行锁，描述生成 SVG 时不能漂移的参数。
- `plan-confirmation.json`：可选的兼容确认产物，不再阻塞默认生成链路。

## Required Shape

```json
{
  "version": "svglide-lock/v1",
  "route": "svglide-svg",
  "plan_path": "02-plan/slide_plan.json",
  "canvas": {"width": 960, "height": 540, "viewBox": "0 0 960 540"},
  "safe_area": {"x": 48, "y": 40, "width": 864, "height": 460},
  "quality_profile": "production",
  "style_tokens": {
    "colors": {},
    "typography": {},
    "spacing": {},
    "shape_rules": {}
  },
  "generation_rules": {
    "text_strategy": "foreignObject",
    "image_strategy": "local_or_token_only",
    "forbidden": []
  },
  "asset_contracts": [],
  "business_claims": [],
  "page_contracts": [
    {
      "page": 1,
      "path": "04-svg/prepared/page-001.svg",
      "rhythm": "anchor",
      "layout_family": "cover",
      "template_variant": "cover",
      "component_selection": [{"component_id": "title_block", "binds": ["title"]}],
      "asset_strategy": {"strategy_id": "structured_fallback"},
      "asset_refs": [],
      "chart_ref": null
    }
  ],
  "pages": []
}
```

## Field Rules

- `style_tokens.colors` 是生成时唯一的颜色来源；需要新颜色时先改 lock 并重新确认。
- `style_tokens.typography` 是字体和字号锚点；生成器不得临时发明一套字体。
- `asset_contracts` 声明页面可用图片、图标、图表或 file token 依赖。
- `business_claims` 记录可见事实片段和来源，用于 preflight/readback 追踪。
- `page_contracts` 是每页生成规则；`rhythm` 可取 `anchor`、`dense`、`breathing`。
- `pages` 可保留兼容旧字段；新逻辑优先读取 `page_contracts`。

## Drift Rules

- `assets` stage 必须记录 plan、lock、assets hash。
- `generate_svg` stage 必须读取当前 lock 和 assets manifest，并把 hash 写入 deck receipt 和 page receipt。
- `prepare` 前如果 source SVG hash 和 `generate_svg` receipt 不一致，必须重跑 `generate_svg`。
- `dry_run/live_create` 前如果 prepared SVG hash 和 `quality_gate` 不一致，必须重跑检查链。
