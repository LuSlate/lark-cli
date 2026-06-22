# SVGlide SVG Protocol

最小模板：

```xml
<svg
  xmlns="http://www.w3.org/2000/svg"
  xmlns:slide="https://slides.bytedance.com/ns"
  slide:role="slide"
  slide:contract-version="svglide-authoring-contract/v1"
  width="960"
  height="540"
  viewBox="0 0 960 540"
>
  <rect slide:role="shape" x="60" y="60" width="240" height="135" fill="#E8EEF8" />
  <foreignObject slide:role="shape" slide:shape-type="text" x="90" y="98" width="240" height="60">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:20px;font-weight:700;color:#1F2937;line-height:1.2">SVGlide</div>
  </foreignObject>
  <image slide:role="image" href="@./hero.png" x="390" y="60" width="240" height="135" />
</svg>
```

## 必须满足

- root 必须是非 namespaced 的 `<svg>`，不能是 `<svg:svg>`。
- root 必须声明 `xmlns:slide="https://slides.bytedance.com/ns"`。
- root 必须包含 `slide:role="slide"`。
- root 应包含 `slide:contract-version="svglide-authoring-contract/v1"`，用于标识这是 SVGlide authoring contract 输入，而不是普通 SVG。
- 可渲染元素必须有对应 `slide:role`：shape 使用 `slide:role="shape"`，图片使用 `slide:role="image"`。
- `<g>` 和嵌套 `<svg>` 可以作为容器，用于继承样式和 transform；容器内真正渲染的元素仍必须声明 `slide:role`。
- `slide:role="shape"` 目前只支持 `rect`、`ellipse`、`circle`、`line`、`path`、`foreignObject`。
- 文本使用文本型 shape：`<foreignObject slide:role="shape" slide:shape-type="text">...</foreignObject>`。
- 图片使用 `<image slide:role="image" href="file_token">`；本地占位符写成 `href="@./image.png"`。
- 原生 chart 可使用 root 直系 `<g slide:role="chart" slide:chart-ref="..." x="..." y="..." width="..." height="...">` spec marker；marker 内只能有一个 chart metadata，metadata payload 是 base64url 编码后的 canonical JSON chart spec，不是 SXSD `<chart>` XML，也不是 chart snapshot/staticData。
- `<defs>` 和 `<style>` 会被服务端解析/跳过输出；支持嵌套在 `g` / 嵌套 `svg` 容器中。
- CLI 注入的 transport metadata `<metadata data-svglide-assets="true">` 会被跳过输出但用于传输图片元数据。

## 坐标系与画布

- 当前 `slides +create-svg` 新建的 Lark Slides presentation 回读画布通常是 `960 x 540`。生成 SVG deck 时默认使用 `width="960" height="540" viewBox="0 0 960 540"`，不要默认用 `1280 x 720`。
- 服务端不会保证把 `viewBox="0 0 1280 720"` 自动缩放到 `960 x 540`。如果用 1280x720 设计，必须在提交前整体换算到目标画布，或在回读 XML 后验证没有越界。
- 生成时为所有主体元素预留安全区，建议 `x >= 48`、`y >= 40`、`right <= 912`、`bottom <= 500`。全屏背景可以铺满 `0,0,960,540`，但主体文字、图表和卡片仍应留在安全区内。
- 回读 XML 后必须检查主体元素边界：非背景元素的 `topLeftX + width <= 960` 且 `topLeftY + height <= 540`。任何页面越界都视为生成失败，需要重排或缩放后重建。

## 几何必填属性

SVGlide leaf shape 必须显式写出服务端建模所需的几何属性，不依赖 SVG 默认值。缺失这些属性通常会被服务端包装成 `shape missing required attribute` 或 generic invalid param。

| Element | Required attributes |
|---------|---------------------|
| `rect slide:role="shape"` | `x`, `y`, `width`, `height` |
| `foreignObject slide:role="shape" slide:shape-type="text"` | `x`, `y`, `width`, `height` |
| `image slide:role="image"` | `href`, `x`, `y`, `width`, `height` |
| `circle slide:role="shape"` | `cx`, `cy`, `r` |
| `ellipse slide:role="shape"` | `cx`, `cy`, `rx`, `ry` |
| `line slide:role="shape"` | `x1`, `y1`, `x2`, `y2` |
| `path slide:role="shape"` | `d` |
| root 直系 `g slide:role="chart"` | `slide:chart-ref`, `x`, `y`, `width`, `height` |

这些属性即使取值为 `0` 也要写出来。例如背景图必须写成：

```xml
<image slide:role="image" href="@./background.jpg" x="0" y="0" width="960" height="540" />
```

CLI 会把这些几何属性作为生成质量门禁：值只能是数字或 `px` 长度，例如 `0`、`1280`、`320.5`、`80px`。不要使用 `%`、`em`、`rem`、`calc(...)` 或省略单位后依赖 SVG 默认值。服务端可能会对部分非法几何值降级为 `0` 并给 warning，但正式生成应在 CLI 侧提前修正。

## 当前支持的 SVG 子集

- Shape: `rect`、`ellipse`、`circle`、`line`、`path`、`foreignObject`。
- Container: `g`、嵌套 `svg`。
- Chart marker: root 直系 `g slide:role="chart"`，用于透传 canonical JSON chart spec。
- Definitions: `defs` 内的 `linearGradient`、`radialGradient`、`filter/feDropShadow`；支持嵌套 `defs` 和 gradient `href` / `xlink:href` 继承。
- CSS: tag、`.class`、`#id`、`.a.b`、`tag.class` 等简单 selector；支持 specificity 和 source order；复杂 selector、media query、伪类会被忽略。
- Paint: `fill`、`stroke`、`stroke-width`、`opacity`、`fill-opacity`、`stroke-opacity`、`stroke-dasharray`、`stroke-linecap`、`stroke-linejoin`。
- Gradient: `stop-color` / `stop-opacity` 可来自属性、inline style 或 CSS；`gradientTransform`、`spreadMethod`、focal 点等复杂能力会被近似或忽略。
- Effects: 支持 `filter="url(#...)"` 指向的 `feDropShadow`、CSS `filter: drop-shadow(...)`、以及首层 `box-shadow`；多层 shadow、spread、inset 会被近似或忽略。
- Transform: `translate`、`scale`、`matrix`、`rotate`；transform 参数应写数字或 `px`，复杂 transform 会被近似或忽略。
- Path: 只使用 `M/L/H/V/C/Q/Z`；CLI 会拒绝 arc `A`、smooth curve `S/T` 和其他未知命令。
- Text: `foreignObject slide:shape-type="text"` 内支持常见 XHTML 文本标签、`br` 和基础文字样式。

## SVG-native 效果的 SVGlide-safe 写法

视觉参考图、浏览器 SVG demo 或 `svglide-visual-effects-gallery.html` 只能作为效果方向，不能直接当作 `slides +create-svg` 输入。生成器必须把浏览器 SVG 能力改写为当前 SVGlide 支持面：

| 浏览器 SVG 常见写法 | SVGlide-safe 写法 |
|---|---|
| 根级 `<text>` / 普通 SVG text | `foreignObject slide:role="shape" slide:shape-type="text"`，并显式写 `font-size`、`font-weight`、`color`、`line-height` |
| `<polygon>` / `<polyline>` | 改成 `path slide:role="shape"`，只使用 `M/L/H/V/C/Q/Z` |
| `<marker>` 箭头 | 用独立三角形 `path` 或短 line + arrowhead path 显式绘制 |
| `<pattern>` 网格、点阵、纹理 | 用重复的 `line`、`circle`、`rect` 显式铺排；不要依赖 pattern 展开 |
| `mask` / `clipPath` 大字裁切 | 用大字描边、深色/渐变背板、半透明 shape overlay 或裁切后的本地图片替代 |
| 多层 `filter`、blur、glow | 用多层半透明 circle/rect/path 模拟光晕；仅把简单 drop-shadow 当增强，不当核心表达 |
| `stroke-dasharray` 关键路线 | 用短 line segment 或 filled dot markers 手工排布；关键流程不要只靠虚线；带 `route` / `path` / `flow` / `loop` / `timeline` / `rail` 等语义的虚线会被 preflight 视为错误 |
| `<image opacity="...">` | MVP preflight 只 warning；高保真场景应预合成到图片，或在图片上方加半透明 `rect slide:role="shape"` |
| iconfont / 外链 SVG 图标 | 用 SVGlide-safe path/line/rect/circle 组合本地绘制，或先转成受支持的本地图片资产 |

每个 SVGlide 页面应通过 template family、variant、semantic blocks、component selection 和 asset strategy 证明它不是普通卡片页。只有 `rect + foreignObject` 的普通卡片页应优先走 XML/SXSD，或重新选择更合适的 family variant。

文本样式应使用 parser 友好的显式 CSS 属性，例如 `font-size`、`font-weight`、`font-family`、`color`、`line-height`、`text-align`、`letter-spacing`。不要依赖 `font:` shorthand、复杂 flex 布局或浏览器默认样式来表达关键字号、加粗和行距；这些在转换到 SXSD/XML 时可能降级为默认样式。

白色或接近白色的文字必须完整落在深色 shape 承载底上；如果标题跨到浅色图片、白色蒙层或白底，生成器应扩大深色底、加背板/遮罩，或改用深色文字。圆形/椭圆节点内只放短标签，解释句、指标和说明放到独立 callout、legend 或机制表中。

生成 live smoke 或跨 lane 验证用 SVG 时，颜色优先写成 hex/rgb 加独立透明度属性，例如 `fill="#0F172A" opacity="0.72"`、`stroke="#38BDF8" stroke-opacity="0.8"`。不要在首轮验证里大量依赖 `rgba(...)` 作为 SVG leaf 的 `fill` / `stroke` 值；不同 server lane 的 paint 解析能力可能不一致，hex + opacity 更容易定位问题。渐变仍按 XML 协议要求使用 `rgba(...)` 停靠点。

图片透明度当前不是稳定协议面：`<image opacity="...">` 在 SVG 输入中会通过 CLI 传给服务端，但转换后的 Slides XML `<img>` 不一定保留 alpha。MVP 阶段 preflight 只 warning；生成器不得在高保真页面依赖 image opacity，要么把淡化效果预合成到本地图片文件，要么用一个半透明 `rect slide:role="shape"` 覆盖在图片上方。shape opacity 会转换为 Slides XML `alpha`，比 image opacity 更稳定。

圆形和椭圆描边宽度也不是稳定协议面：`circle` / `ellipse` 的 `stroke-width` 可能在 readback 中降级。关键圆环请用两层填充圆/椭圆模拟，或改用 path/rect；普通细描边可以保留但需要视觉回读确认。

虚线描边也不是稳定协议面：`stroke-dasharray`，尤其是自定义 path 上的虚线闭环，可能在 readback 中降级。关键流程线、路线图和闭环图用短 line segment 或 filled dot markers 显式绘制；带 `route`、`path`、`flow`、`loop`、`timeline`、`rail` 等语义的 dashed path 会被 `svg_preflight.py` 作为 error 拦截。普通装饰虚线也需要 live readback 复核。

## Chart Spec Marker

当 SVG 页面需要创建原生 chart 时，使用 root 直系 chart marker。payload 是 canonical JSON bytes，先对这段 decoded JSON bytes 计算 `sha256`，再用无 padding base64url 写入 metadata 文本：

```xml
<g slide:role="chart"
   slide:chart-ref="chart-sales-001"
   x="80" y="96" width="420" height="260">
  <metadata
    data-svglide-chart="svglide-chart-inline/v1"
    data-format="svglide-chart-spec-v1"
    data-encoding="base64url-json"
    data-payload-hash="sha256:<64 hex>"
  >BASE64URL_PAYLOAD</metadata>
</g>
```

Decoded canonical JSON shape:

```json
{"version":"svglide-chart-spec/v1","chartType":"bar","data":{"categories":["Q1","Q2"],"series":[{"name":"Revenue","values":[12.5,18]}]}}
```

约束：

- `g slide:role="chart"` 必须是 root `<svg>` 的直系子节点，不能嵌套在普通 `g` / 嵌套 `svg` 中。
- `slide:chart-ref`、`x`、`y`、`width`、`height` 必填；bbox 数值只能是数字或 `px` 长度。
- marker 内必须且只能有一个 `<metadata>` 子节点。
- metadata 必须声明 `data-svglide-chart="svglide-chart-inline/v1"`、`data-format="svglide-chart-spec-v1"`、`data-encoding="base64url-json"` 和 `data-payload-hash="sha256:<64 hex>"`。
- metadata 文本是无 padding 的 base64url payload；解码后必须是 canonical JSON chart spec。不要把 SXSD `<chart>` XML 放入 SVGlide chart marker。
- JSON spec 必须包含 `version="svglide-chart-spec/v1"`、`chartType`、`data.categories`、`data.series[].name` 和 `data.series[].values`。MVP 只支持 `chartType="bar"` / `"line"`；`categories` 和每个 `values` 数组长度必须一致；`values` 只能是有限 JSON number。
- CLI 校验上述结构、hash 和基础数据合法性，不会为 chart 调用任何额外 API。请求体仍是 `{ "slide": { "content": "<svg ...>" } }`。
- 不要把 chart marker 当成 SVG 手绘微图表的替代品；如果只是视觉小图、指标条或仪表盘装饰，仍优先用 SVGlide-safe shape/path 直接绘制。

## 不支持

- 不要把普通 SVG 直接交给 `+create-svg`，CLI 不会自动补齐 SVGlide 协议。
- 不支持缺少 role 的可渲染元素，例如 `<rect .../>`；必须写成 `<rect slide:role="shape" .../>`。
- 不要把 `<g>` 当作可渲染 shape；`<g>` 只是容器，实际 `rect`、`path`、`foreignObject`、`image` 等子元素仍需各自声明 `slide:role`。
- 不支持根级 `<text slide:role="text">`；用 `foreignObject + slide:shape-type="text"`。
- 不要在 `<image>` 上保留 `xlink:href`；CLI 会统一输出 canonical `href`。
- 不支持 `slide:role="whiteboard"`，也不支持旧的 `data-svglide-whiteboard` SVGlide whiteboard marker；whiteboard 内容必须走 XML/whiteboard 路径。
- 用户可见 preview / `local_real_preview` / production 阶段只允许可审计的线上图片来源：`source_url` 必须是 `http(s)` 或内部资产服务 URL，并且必须有明确 license/provenance。`data:`、本地生成图、`preview_unverified` 和无来源本地文件只能用于 debug/fixture，不能作为真实预览成功条件。
- `slides +create-svg` MVP 不支持指定 `beforeSlideBlockID` 插入到某一页前；它创建新 presentation 后按 `--file` 顺序追加。

这些能力依赖 slide server SVGlide parser 新版本。如果 BOE/线上未部署对应 server 分支，CLI 放行后仍可能收到服务端 `SVGLIDE_ERROR_JSON` 或 generic invalid param。

## 图片与 Metadata

SVG deck 默认应使用真实图片资产，不要为了规避上传链路而全程用纯矢量 shape 冒充配图。Preview 阶段图片是拉开 SVGlide 和 XML 生成差距的关键能力：宣传、产品、品牌、案例、教学和视觉展示型 deck 应优先根据用户 query、deck 主题和页面标题去网络检索并拉取强相关图片，再包含封面/半出血主视觉/案例场景/产品截图/材质纹理/图鉴图等图片使用；只有用户明确要求纯矢量，或图片获取、上传链路完全不可用时，才退回纯矢量方案，并在结果中说明原因。

图片资产采用双模式：

- **User-visible preview / local_real_preview**：版权/授权不完整会阻断。必须先从用户 query、deck 标题、章节标题和 page takeaway 生成图片检索词，使用公开可访问图片 URL、图库条目、官网/产品页截图或内部资产服务，并记录 `retrieval_query`、`source_url`、`license`、`retrieved_at`。不得用 AI 生成图、程序化本地图或 `preview_unverified` 冒充真实图片资产。
- **Debug / fixture preview**：只用于本地开发、golden 和 CI，可保留 `preview_unverified`、程序化图或 fixture 图，但这类产物不能汇报为用户可见真实预览。
- **Production mode**：正式交付必须替换为用户提供、公司/项目自有、明确可商用授权图库，或授权条件清晰的 AI 生成资产。推荐来源包括 Unsplash、Pexels、Pixabay、Openverse、Wikimedia Commons、The Met Open Access、Smithsonian Open Access 和 NASA Image and Video Library，但每张图都应检查具体 license、署名和第三方权利。

用户可见链路素材清单不完整必须 fail-closed；debug/fixture 阶段可以降级为 warning，但结果必须标记为不可用于真实预览。

当 SVG source 使用 `<image>` 时，对应 slide plan 应尽量有 `asset_contract`，并至少包含：

```json
{
  "mode": "preview",
  "source_type": "public_url | web_search | screenshot | Unsplash | Pexels | Wikimedia | Openverse | internal_asset | user_provided | owned",
  "retrieval_query": "topic-specific image query derived from user query and page topic",
  "license": "owned | user_provided | cc-by | cc0 | unsplash | pexels | pixabay | public_domain | internal_licensed",
  "local_path": "@./assets/hero.jpg",
  "href": "https://example.com/hero.jpg",
  "usage_page": 1,
  "source_url": "https://...",
  "retrieved_at": "2026-06-08",
  "attribution": "optional attribution string when required",
  "replacement_required": false
}
```

无图片页可以写 `"asset_contract": "none_required"`。如果 SVG source 检测到 image primitive，但 `asset_contract` 缺少检索词、来源、许可、本地路径或使用页，用户可见 profile 必须由 Asset Gate 阻断；只有 debug/fixture 可降级为 warning。

`slides +create-svg` 会把 `<image href="@./image.png">` 上传为 file token，并注入：

```xml
<metadata data-svglide-assets="true">
  <img src="boxcn..." />
</metadata>
```

metadata 只用于让现有服务端链路生成 `FileMetaMap`。如果使用 `--assets assets.json` 传入预上传 token，CLI 也会按同样规则替换和注入。

`assets.json` 格式：

```json
{
  "@./image.png": "boxcn...",
  "./other.png": "boxcn..."
}
```
