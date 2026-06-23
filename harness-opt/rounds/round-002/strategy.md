# Round 2 候选策略（模块=references/lark-im-messages-send.md, tier=T1, 主指标=token）

## 根因与选择

| 根因 | 来源(评测归因/规范经验) | 承载模块(reach) | annotation 风险级 | coverage 档 | P级 | 选中 |
|---|---|---|---|---|---|---|
| RC-2: messages-send.md 单文件最大、内部「选 content flag」规则重复 4 处 + 全媒体形态罗列 + Parameters/Notes 镜像 --help | 评测归因①（080 实读实用）＋规范经验②（annotation R1×140/R2×109，仅 1 段 R3） | references/lark-im-messages-send.md (0.333) | R1/R2 主导，唯一 R3=Safety Constraints(L9–22) | 密 / overfit 低 | P1 | ✅ |
| RC-1: SKILL.md `## Important Notes` 低命中 + `## Shortcuts` 全表常驻 | 评测归因①（reach=1.0，3 题全命中） | SKILL.md (1.0) | R2/R3 混合（identity/约束密集） | 密 / 中 | P0(命中) 但 effect 高风险 |  |
| RC-3: chat-create.md 按需偏大 | 评测归因① | references/lark-im-chat-create.md (0.667) | — | 密 | P1 |  |

- **选中理由**：RC-2 是诊断点名「最干净的 token 杠杆」——单文件最大块（实测 ~5,365 tok，占 080 visible 24.8%），且 080 调用前已读、确实据它发卡片成功（reach=0.333、actual=1，非「读了没用」）。annotation 证实它 R1/R2 主导（140 R1 + 109 R2 行，可重构/可压缩），唯一 R3 段是 Safety Constraints(L9–22)，我**原样保留语义**。coverage=「密」、overfit「低」→ 本轮 eval 能在 080 上裁真伪。这是纯减体积、零能力删除、不碰 SKILL.md 路由的改动。
- **为什么不选 RC-1**：reach=1.0、命中率最高，但 diagnosis 明确标它为 **effect 风险点**——剩余内容多为 identity/约束类，正是驱动 015/080 走通 bot 身份判断的承重内容；objective 的**硬门槛是「保住成功率」**，动 SKILL.md 最可能误伤这条已绿链路。本轮放弃，避免拿成功率换 token。
- **为什么不选 RC-3**：diagnosis 判其杠杆最低（体积不离群），列为更次级；同一根因一轮只动一个，留待后续轮次。
- **选模块理由**：messages-send.md reach=0.333>0（满足 reach 锁），承载选中的 RC-2，是非域 reference、改它不触碰 SKILL.md 的身份路由面。多文件无——本轮只动这一个文件。
- **规范经验源补注**：对照 content-taxonomy——「单命令用法/长示例/与 --help 重复」类默认 R0/R1，「一般行为规则/CLI 机制约定」默认 R2；本文件的重复选型规则、全形态 Commands、Parameters/Notes 镜像即此类，处理方向为「留命中率最高一处，其余删或指针」「高频留 2–3 例，长的下沉」。当轮可被 080 裁真伪（coverage 密/overfit 低）。

## 改了什么（逐处）
- **L23–43 `## Choose The Right Content Flag` + `### --text vs --markdown`**：两段语义重叠的选型说明 → 合并为单张 4 行选型表（markdown/text/content/media），并把互斥规则并入表后一句。删掉 `### --text vs --markdown` 整段（与表重复）。
- **L44–82 `## What --markdown Really Does` + `### Markdown Boundaries` + `### Image Constraint`**：三段约 39 行 → 压成 `## --markdown Gotchas` 三条要点（强制 post/无 title、标题改写规则、图片预上传 vs 远程 URL vs 本地路径不支持）。删掉 JSON wrap 示意、逐条 boundary 罗列等可由行为观察得到的展开。
- **L83–93 图片预上传双命令示例**：并入 `## Commands` 的一条 markdown+image 示例（保留 `im images create` → 引用 img_xxx 的关键两步）。
- **L114–161 `## Commands`（15+ 例覆盖全媒体形态）+ `## Media Input Rules`**：压成代表性示例（markdown / text / DM / post-title / markdown+image / 4 个媒体一组 / idempotency+dry-run），媒体路径规则收成 `--help` 指针后的 3 条 load-bearing gotcha（cwd-relative/绝对路径拒绝、video-cover 必配、msg-type 推断冲突）。
- **L169–191 `## Parameters` 表**：删除镜像 `--help` 的逐参数描述，改为「Run `lark-cli im +messages-send --help`」指针 + 仅保留 --help 不显然的三条硬规则（已并入 Commands 末尾）。
- **L192–202 `## Common Mistakes`**：整段删除——逐条都是选型表/markdown gotcha 的反向重述（第 4 次重复选型规则），删后选型信息仍在表里。
- **L203–216 `## content Format Reference`**：保留（构造 `--content` 的 gotcha），把 image/file/audio 三行合并为一行省重复。
- **L227–248 `## @Mention Format`**：保留全部三种 msg_type 的 `<at>` 语法（text/post/interactive 各异、AI 猜不到），压紧为两条要点、去掉小标题与重复散文。
- **L249–264 `## Notes`**：整段删除——逐条（互斥/media 上传/scope/markdown 强制 post/video-cover/msg-type 冲突）均已在 Safety Constraints、选型表、--markdown Gotchas、Commands 指针处各保留一处单一事实源。

## 为什么这么改（机制）
- **消除根因的因果链**：该 reference 的体积来自「同一份选型规则在 4 个 section 重复 + 全媒体形态逐条罗列 + Parameters/Notes 镜像 --help」。token 不是被任务必需信息占用，而是被**重复表述**占用。按「同一份事实只写一次」（锚点 1）合并到单一事实源后，每条 load-bearing 信息仍恰好出现一次，080 这类「读该 reference→发消息」的题，读入 token 直接下降而行为不变。
- **不删能力**：每个 flag（text/markdown/content/image/file/video/audio/idempotency/dry-run/msg-type/video-cover/as）、每条硬约束（互斥、video-cover 必配、cwd-relative 路径、绝对路径拒绝、markdown 强制 post/无 title、msg-type 冲突校验）、三套 `<at>` 语法、content 各 msg_type 样例、Safety Constraints、identity+scope 映射——全部保留，只是从「重复 N 次/逐条罗列」变成「一处/代表性示例 + --help 指针」。
- **规范经验源**：依 optimization-playbook「reference 收敛到 gotcha-only，不做 --help 镜像」——Parameters 全表/全形态 Commands 属 USAGE，下沉到 `--help` 指针；保留的是 --help 表达不了的跨 flag 互斥、媒体路径安全、markdown→post 边界、@mention 按类型差异等 gotcha。annotation 标这些段为 R1（可重构/下沉），符合处理方向；唯一 R3（Safety）原样保留。

## 预期效果
- **成功率**：不退化。080（唯一读该文件的题）的发卡片链路依赖的是 `--content`/`interactive`、identity=bot、chat-id——全部保留；选型表、content Format Reference、Safety、scope 都在。015/080 走通 bot 身份的判断由 SKILL.md + identity 段承载，本轮**没碰 SKILL.md**，零误伤面。014 与本文件无关（reach 不含 014）。
- **context（分两层）**：
  - (1) **静态字数差**：16,407 → 6,399 chars（-61.0%）；tiktoken cl100k 3,869 → 1,799 tok（-53.5%）。（注：diagnosis 报 ~5,365 tok 系另一 tokenizer/含注入开销；此处用 cl100k 自测，方向与幅度一致。）
  - (2) **运行时 context 方向**：仅在**实读该 reference 的子集**生效——本轮即 080 一题，运行时读入下降约 50%+（该块占 080 visible 24.8%，预计 080 visible 降约 12–13%）。其余两题（014/015）不读该文件，运行时 token **不变**（既不增也不减）。这是按需 reference，不是常驻面，不会影响未读它的题。
- **覆盖敞口**：RC-2 子集仅 080 一题（reach=0.333），证据基数小。coverage 判该文件「密/overfit 低」，本轮 eval 可在 080 上裁真伪，但单题不可外推到「所有发消息任务」。建议后续补「读 messages-send.md 后用 --markdown / 媒体 / @mention」的 case 加厚子集。预期收益落在 **token 轴**（080 visible 下降），effect 轴维持不退化。

## 刻意没做什么（反 reward-hack / 反过拟合）
- 没硬编码任何评测题答案；没删任何能力、flag、guardrail、身份/scope 说明；没碰 lark-im 以外文件，也没把无关根因捆进本轮（commit 仅 1 个文件）。
- **没碰 SKILL.md（RC-1）**：尽管 reach=1.0 杠杆最大，但其剩余内容是驱动 015/080 bot 身份判断的承重 identity/约束，diagnosis 标为 effect 风险点；在「保住成功率」硬门槛下不拿成功率换 token。
- **没补收窄/分页指引**（015 的 22.5k chat-messages-list 黑洞）：那是「增内容」，与降 token 目标方向相反，diagnosis 已列为观察项、本轮不做。
- 本改动**不是按评测错误反推**的参数/路由拟合——是基于 annotation + content-taxonomy 的结构性去重，删的是重复表述而非按 080 的具体内容裁剪；真实价值在「任何读该 reference 的发消息任务都少读重复 token」，080 只是当轮可验证的子集。
- 未发现需要 breaking（T3）才能根治的点；本轮纯 T1 文档去重即可。

## 签名
- signature: 557349b40feb359bb791749a37571d59edb7e72e (commit 82a099fe 的 diff hash)  tier: T1
