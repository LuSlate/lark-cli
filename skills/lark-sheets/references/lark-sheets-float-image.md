# Lark Sheet Float Image

> **单元格图片 vs 浮动图片**：飞书表格有两种图片类型，请根据需求选择正确的工具：
> - **单元格图片**：图片嵌入在单元格内部，随单元格移动，属于单元格内容的一部分。→ 使用 `+cells-set`，在 `rich_text` 中设置 `type: "embed-image"`（见 lark-sheets-write-cells）。
> - **浮动图片**（本 Skill）：图片悬浮在单元格上方，可自由指定位置、大小和层级，不属于任何单元格的内容。→ 使用本 Skill 的 `+float-image-{create|update|delete}`。

## 真对象硬约束

当用户要求"插入图片 / 添加 logo / 放一张图"时，**必须**通过 `+float-image-{create|update|delete}`（浮动图片）或 `+cells-set` 的 `embed-image`（单元格图片）创建真实的图片对象。**禁止**只在文本回复中给出图片链接 / 描述图片内容代替插入。判断标准：交付后 `+float-image-list` 或单元格 `rich_text` 必须能读到该图片对象。

## 使用场景

读写**浮动图片**对象（悬浮在单元格上方的图片，不属于单元格内容）。本 reference 覆盖 4 个 shortcut：

| 操作需求 | 使用工具 | 说明 |
|---------|---------|------|
| 查看已有浮动图片 | `+float-image-list` | 获取浮动图片的位置、大小和层级配置 |
| 创建/更新/删除浮动图片 | `+float-image-{create|update|delete}` | 对浮动图片执行写入操作 |

典型工作流：先读取现有浮动图片了解配置 → 执行创建/更新/删除 → **必须再次读取验证结果**。

**常见配置错误（必须注意）**：
- **单元格图片 vs 浮动图片选择错误**：如果用户希望图片嵌入单元格内部（随单元格移动），应使用 `+cells-set` 的 `rich_text` + `embed-image`，而非本 Skill
- **图片位置参数要精确**：锚点单元格的行列索引和偏移量决定了图片位置，设置不当会导致图片遮挡数据
- **创建后必须验证**：调用 `+float-image-list` 确认图片位置和大小正确

图片来源有三种方式，`+float-image-create` 上三者 **XOR、必给其一**（`--image` / `--image-token` / `--image-uri`）：

- **`--image <本地路径>`（首选，最省事）**：直接给本地图片文件路径（PNG/JPEG/GIF/BMP/HEIC 等）。CLI 会自动把它以 `parent_type=sheet_image` 上传，拿到 file_token 后创建浮动图，**不用你手动上传 / 取 token**。路径规则同其它本地文件 flag：必须是当前工作目录内的相对路径（绝对路径会被 Validate 拒，`--dry-run` 也会拦）。
- `--image-token`：复用**已存在**的图片 file_token。常见来源：① `+float-image-list` 返回的 `image_token`（适合"换皮不换位置"复用同一张图）；② `+cells-set-image` 成功返回里的 `file_token`（它也是 `sheet_image` 上传句柄）。适合"同一张图复用到多处"，省去重复上传。
- `--image-uri`：图片 reference_id（image URI），由系统自动转 file_token。

> ⚠️ **`--image` 仅 `+float-image-create` 支持**。`+float-image-update` 换图仍只接受 `--image-token` / `--image-uri`（patch 模式：不传则保留原图）；要在 update 里换一张本地新图，先用 `+cells-set-image` 上传到任意临时单元格、从返回取 `file_token`，再把它传给 update 的 `--image-token`。

## Shortcuts

| Shortcut | Risk | 分组 |
| --- | --- | --- |
| `+float-image-list` | read | 对象 |
| `+float-image-create` | write | 对象 |
| `+float-image-update` | write | 对象 |
| `+float-image-delete` | high-risk-write | 对象 |

## Flags

### `+float-image-list`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--float-image-id` | string | optional | 按 id 过滤；省略时列工作表全部 |

### `+float-image-create`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--image-name` | string | required | 图片名称，含扩展名（如 `logo.png`） |
| `--image-token` | string | xor | 图片 file_token（与 `--image-uri` 二选一）。常见来源：`+float-image-list` 返回的 `image_token` |
| `--image-uri` | string | xor | 图片 reference_id（与 `--image-token` 二选一）；图片上传链路返回的 reference_id |
| `--position-row` | int | required | 图片左上角所在行（0-based） |
| `--position-col` | string | required | 图片左上角所在列（列字母，如 `A` / `B`） |
| `--size-width` | int | required | 图片宽度（像素） |
| `--size-height` | int | required | 图片高度（像素） |
| `--offset-row` | int | optional | 在 `--position-row` 基础上的行内偏移（像素） |
| `--offset-col` | int | optional | 在 `--position-col` 基础上的列内偏移（像素） |
| `--z-index` | int | optional | 图片 Z 轴层级，控制重叠顺序 |
| `--image` | string | xor | 本地图片路径（PNG/JPEG 等）；CLI 自动上传为 sheet_image 并用返回的 file_token，省去手动拿 token（与 --image-token / --image-uri 三选一） |

### `+float-image-update`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--float-image-id` | string | required | 目标图片 id |
| `--image-name` | string | optional | 图片名称，含扩展名（如 `logo.png`） |
| `--image-token` | string | xor | 图片 file_token（与 `--image-uri` 二选一）。常见来源：`+float-image-list` 返回的 `image_token` |
| `--image-uri` | string | xor | 图片 reference_id（与 `--image-token` 二选一）；图片上传链路返回的 reference_id |
| `--position-row` | int | optional | 图片左上角所在行（0-based） |
| `--position-col` | string | optional | 图片左上角所在列（列字母，如 `A` / `B`） |
| `--size-width` | int | optional | 图片宽度（像素） |
| `--size-height` | int | optional | 图片高度（像素） |
| `--offset-row` | int | optional | 在 `--position-row` 基础上的行内偏移（像素） |
| `--offset-col` | int | optional | 在 `--position-col` 基础上的列内偏移（像素） |
| `--z-index` | int | optional | 图片 Z 轴层级，控制重叠顺序 |

### `+float-image-delete`

_公共四件套 · 系统：`--yes`、`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--float-image-id` | string | required | 目标图片 id |

## Examples

公共四件套：所有 shortcut 顶部排列 `--url` / `--spreadsheet-token` / `--sheet-id` / `--sheet-name`（XOR）。浮动图片是 sheet 级对象——和单元格内嵌图片不同（后者走 `+cells-set`）。

### `+float-image-list`

```bash
lark-cli sheets +float-image-list --url "..." --sheet-id "$SID"
```

### `+float-image-create`

所有字段拍平为独立 flag：图片来源 `--image` / `--image-token` / `--image-uri`（三选一 XOR）/ `--image-name` / `--position-{row,col}` / `--size-{width,height}` / `--offset-{row,col}` / `--z-index`。

```bash
# 首选：直接给本地图片路径，CLI 自动上传（无需手动拿 token）
lark-cli sheets +float-image-create --url "..." --sheet-id "$SID" \
  --image ./logo.png \
  --position-row 2 --position-col B --size-width 300 --size-height 200 --z-index 1

# 用已有 file_token（从 +float-image-list 的 image_token 或 +cells-set-image 返回的 file_token）
lark-cli sheets +float-image-create --url "..." --sheet-id "$SID" \
  --image-name "logo.png" --image-token "$TOKEN" \
  --position-row 0 --position-col A --size-width 200 --size-height 150

# 用 reference_id（图片上传链路返回的 image reference_id；与 --image-token 二选一）
lark-cli sheets +float-image-create --url "..." --sheet-id "$SID" \
  --image-name "logo.png" --image-uri "$IMAGE_URI" \
  --position-row 2 --position-col B --size-width 300 --size-height 200 --z-index 1
```

### `+float-image-update`

> **patch 模式**：除了 `--float-image-id`（必填，定位目标图片）外，其它字段都可选——只传你需要改的那几个，未传的字段保持原值不变。至少传一个改动字段。
>
> 推荐流程：先 `+float-image-list --float-image-id <id>` 回读当前完整属性，再针对要改的字段调一次 `+float-image-update`。

```bash
# 只改位置，保留其它属性
lark-cli sheets +float-image-update --url "..." --sheet-id "$SID" \
  --float-image-id "$IMG_ID" --position-row 5 --position-col C

# 只换图，位置/尺寸不变
lark-cli sheets +float-image-update --url "..." --sheet-id "$SID" \
  --float-image-id "$IMG_ID" --image-name "new-logo.png" --image-token "$NEW_TOKEN"
```

### `+float-image-delete`

```bash
lark-cli sheets +float-image-delete --url "..." --sheet-id "$SID" --float-image-id "$IMG_ID" --yes
```

### Validate / DryRun / Execute 约束

- `Validate`：XOR 公共四件套；`+float-image-create` 要求 `--image` / `--image-token` / `--image-uri` **恰好给一个**，`--position-row/col` 与 `--size-width/height` 必填且为合法整数；传 `--image` 时还会校验路径安全（绝对路径 / 越出工作目录会被拒，`--dry-run` 同样拦）。`+float-image-update` 必须 `--float-image-id`，其余字段至少传 1 个（patch 模式：未传字段保持原值，换图只接受 `--image-token` / `--image-uri`）；`+float-image-delete` 强制 `--yes` 或 `--dry-run`。
- `DryRun`：写操作输出"将要 POST/PATCH/DELETE 的 float_image 请求模板"；传 `--image` 时会多打印一步本地图片上传（`POST /open-apis/drive/v1/medias/upload_all`，`parent_type=sheet_image`）。
- `Execute`：写后调用 `+float-image-list --float-image-id <id>` 回读，envelope.meta.verification 给出新位置 / 尺寸对比。
