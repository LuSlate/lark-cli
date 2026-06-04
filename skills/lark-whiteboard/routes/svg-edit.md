# SVG 编辑路径

通过导出画板的 SVG → 编辑 SVG → 回写画板，实现对已有画板的可视化编辑。

---

## ⚠️ 有损性警告 & 适用判断

SVG 导出是**纯视觉快照**，再次导入后画板语义（思维导图层级/表格结构/连线绑定/容器类型/mention/节点 ID/锁定/评论/历史）**不可恢复**。

**保留的信息**：形状几何（位置/大小/路径）、文本内容与基本格式（字号/粗体/斜体/对齐）、填充色/描边色/透明度（线性渐变降级为第一个 stop-color 纯色）、连接器路径形状与箭头样式、`<g>` 嵌套的基本分组关系（≥2 子元素时重建为 DirectFocusGroup）。

> **注意**：`<path>` 元素会被 path-analyzer 尝试识别为标准形状（rect/圆角矩形/椭圆/菱形/三角形/平行四边形）；无法识别的复杂路径降级为 SvgIcon（视觉保真但不可编辑）。

| 操作意图 | 可行性 | 说明 |
|---|---|---|
| 修改文字内容 | ✅ | 编辑 `<text>` 元素 |
| 修改颜色/填充 | ✅ | fill/stroke 属性（线性渐变降级为第一个 stop-color） |
| 调整位置/大小 | ✅ | 坐标和尺寸属性 |
| 增删独立形状/装饰 | ✅ | 添加或移除 SVG 元素 |
| 修改连线路径走向 | ✅ | path/polyline 路径数据 |
| 修改箭头样式 | ✅ | `<marker>` 定义，connector-transformer 恢复箭头类型 |
| 修改描边虚线样式 | ⚠️ | stroke-dasharray 只映射 3 种固定样式（实线/短划线/点线），自定义模式会被近似 |
| 修改字体 | ❌ | 画板硬编码 Noto Sans SC，font-family 导入后无效 |
| 添加 mention/hyperlink | ❌ | 文本语义丢失，无法通过 SVG 注入 |
| 添加外部图片 | ❌ | 仅支持内置 iconSource URL，其他 URL 和 data URI 降级为 SvgIcon |
| 调整思维导图层级 | ❌ | 父子层级/布局类型/折叠状态丢失，走[重绘路径](../SKILL.md#修改-workflow) |
| 增减表格行列 | ❌ | 行列/合并单元格结构丢失，暂无可用路径 |
| 重建连接器端点绑定 | ❌ | `startObject`/`endObject` 丢失，回写后连线自由浮动 |
| 修改容器从属关系 | ❌ | Frame/Section/Container 退化为 DirectFocusGroup，走[重绘路径](../SKILL.md#修改-workflow) |

---

## Workflow

### 0. 用户确认（强制）

在执行任何编辑前，**必须**向用户说明：

> SVG 编辑只保证视觉层面对齐，画板语义（层级/节点类型/思维导图结构/表格结构/连线绑定/容器类型/mention 等）将不可恢复，是否继续？

**用户未确认前不得执行后续步骤。**

### 1. 导出当前画板 SVG

```bash
lark-cli whiteboard +query \
  --whiteboard-token <TOKEN> \
  --output_as svg \
  --output <dir>/original.svg \
  --as user
```

### 2. 编辑 SVG

在导出的 SVG 上进行修改。参考 [`svg.md` § 画板怎么处理 SVG](./svg.md#画板怎么处理-svg) 了解可识别元素与不支持的装饰特性。

**技术约束**：
- 新增文字必须用 `<text>`（不是 `<path>`），容器宽度留够（CJK ≈ 1em / Latin ≈ 0.6em）
- 避免 `skewX` / `skewY` / `matrix(...)` 变换
- 禁止使用 `<radialGradient>` / `<filter>` / `<pattern>` / `<clipPath>` / `<mask>`

**编辑原则**（区别于从零创作）：

- **风格一致**：新增/修改元素应匹配导出 SVG 中已有的配色、字号、线宽、间距风格，不引入突兀的视觉差异
- **最小改动**：只修改用户要求的部分，不主动"优化"或重排无关区域
- **结构稳定**：尽量保留原有 `<g>` 层级结构，避免不必要的重组导致分组关系变化
- **连线协调**：连接器端点绑定已丢失，若移动了形状，必须手动同步调整视觉上连接到该形状的 connector path 端点坐标，否则连线会"断开"
- **内部引用完整性**：不要随意删改 `<defs>` 中被 `url(#id)` 引用的元素（`<marker>`/`<linearGradient>` 等）或修改其 `id`，否则引用方会失效

### 3. 渲染审查

```bash
# 渲染 PNG 预览
npx -y @larksuite/whiteboard-cli@^0.1.1-beta -i <dir>/edited.svg -o <dir>/edited.png -f svg

# 几何检查（text-overflow / node-overlap）
npx -y @larksuite/whiteboard-cli@^0.1.1-beta -i <dir>/edited.svg -f svg --check
```

结合 PNG 视觉效果和 `--check` 报告进行调整，有问题则修改 SVG 后重新渲染（最多 2 轮）。

### 4. 写回画板

```bash
# dry-run 探测（输出含 "XX nodes will be deleted" 时需再次向用户确认）
npx -y @larksuite/whiteboard-cli@^0.1.1-beta -i <dir>/edited.svg -f svg --to openapi --format json \
  | lark-cli whiteboard +update \
    --whiteboard-token <TOKEN> \
    --source - --input_format raw \
    --idempotent-token <10+字符唯一串> \
    --overwrite --dry-run --as user

# 用户确认后执行
npx -y @larksuite/whiteboard-cli@^0.1.1-beta -i <dir>/edited.svg -f svg --to openapi --format json \
  | lark-cli whiteboard +update \
    --whiteboard-token <TOKEN> \
    --source - --input_format raw \
    --idempotent-token <10+字符唯一串> \
    --overwrite --as user
```

> `--overwrite` 必须携带，否则会增量叠加导致内容重复。
