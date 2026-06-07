# SVGlide SVG Protocol

最小模板：

```xml
<svg
  xmlns="http://www.w3.org/2000/svg"
  xmlns:slide="https://slides.bytedance.com/ns"
  slide:role="slide"
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
- 可渲染元素必须有对应 `slide:role`：shape 使用 `slide:role="shape"`，图片使用 `slide:role="image"`。
- `<g>` 和嵌套 `<svg>` 可以作为容器，用于继承样式和 transform；容器内真正渲染的元素仍必须声明 `slide:role`。
- `slide:role="shape"` 目前只支持 `rect`、`ellipse`、`circle`、`line`、`path`、`foreignObject`。
- 文本使用文本型 shape：`<foreignObject slide:role="shape" slide:shape-type="text">...</foreignObject>`。
- 图片使用 `<image slide:role="image" href="file_token">`；本地占位符写成 `href="@./image.png"`。
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

这些属性即使取值为 `0` 也要写出来。例如背景图必须写成：

```xml
<image slide:role="image" href="@./background.jpg" x="0" y="0" width="960" height="540" />
```

CLI 会把这些几何属性作为生成质量门禁：值只能是数字或 `px` 长度，例如 `0`、`1280`、`320.5`、`80px`。不要使用 `%`、`em`、`rem`、`calc(...)` 或省略单位后依赖 SVG 默认值。服务端可能会对部分非法几何值降级为 `0` 并给 warning，但正式生成应在 CLI 侧提前修正。

## 当前支持的 SVG 子集

- Shape: `rect`、`ellipse`、`circle`、`line`、`path`、`foreignObject`。
- Container: `g`、嵌套 `svg`。
- Definitions: `defs` 内的 `linearGradient`、`radialGradient`、`filter/feDropShadow`；支持嵌套 `defs` 和 gradient `href` / `xlink:href` 继承。
- CSS: tag、`.class`、`#id`、`.a.b`、`tag.class` 等简单 selector；支持 specificity 和 source order；复杂 selector、media query、伪类会被忽略。
- Paint: `fill`、`stroke`、`stroke-width`、`opacity`、`fill-opacity`、`stroke-opacity`、`stroke-dasharray`、`stroke-linecap`、`stroke-linejoin`。
- Gradient: `stop-color` / `stop-opacity` 可来自属性、inline style 或 CSS；`gradientTransform`、`spreadMethod`、focal 点等复杂能力会被近似或忽略。
- Effects: 支持 `filter="url(#...)"` 指向的 `feDropShadow`、CSS `filter: drop-shadow(...)`、以及首层 `box-shadow`；多层 shadow、spread、inset 会被近似或忽略。
- Transform: `translate`、`scale`、`matrix`、`rotate`；transform 参数应写数字或 `px`，复杂 transform 会被近似或忽略。
- Path: 只使用 `M/L/H/V/C/Q/Z`；CLI 会拒绝 arc `A`、smooth curve `S/T` 和其他未知命令。
- Text: `foreignObject slide:shape-type="text"` 内支持常见 XHTML 文本标签、`br` 和基础文字样式。

文本样式应使用 parser 友好的显式 CSS 属性，例如 `font-size`、`font-weight`、`font-family`、`color`、`line-height`、`text-align`、`letter-spacing`。不要依赖 `font:` shorthand、复杂 flex 布局或浏览器默认样式来表达关键字号、加粗和行距；这些在转换到 SXSD/XML 时可能降级为默认样式。

## 不支持

- 不要把普通 SVG 直接交给 `+create-svg`，CLI 不会自动补齐 SVGlide 协议。
- 不支持缺少 role 的可渲染元素，例如 `<rect .../>`；必须写成 `<rect slide:role="shape" .../>`。
- 不要把 `<g>` 当作可渲染 shape；`<g>` 只是容器，实际 `rect`、`path`、`foreignObject`、`image` 等子元素仍需各自声明 `slide:role`。
- 不支持根级 `<text slide:role="text">`；用 `foreignObject + slide:shape-type="text"`。
- 不要在 `<image>` 上保留 `xlink:href`；CLI 会统一输出 canonical `href`。
- 不要用 http(s) 或 data URL 外链图片；先下载到本地并让 CLI 上传，或用 `--assets` 提供已上传 file token。
- `slides +create-svg` MVP 不支持指定 `beforeSlideBlockID` 插入到某一页前；它创建新 presentation 后按 `--file` 顺序追加。

这些能力依赖 slide server SVGlide parser 新版本。如果 BOE/线上未部署对应 server 分支，CLI 放行后仍可能收到服务端 `SVGLIDE_ERROR_JSON` 或 generic invalid param。

## 图片与 Metadata

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
