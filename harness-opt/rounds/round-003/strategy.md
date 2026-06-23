# Round 3 候选策略（模块=references/lark-im-chat-create.md, tier=T1, 主指标=token）

## 根因与选择
| 根因 | 来源(评测归因/规范经验) | 承载模块(reach) | annotation 风险级 | coverage 档 | P级 | 选中 |
|---|---|---|---|---|---|---|
| RC-1 chat-create.md 内部「示例罗列+场景重复+--help 镜像」三类冗余 | 评测归因 + 规范经验（双视角同指） | references/lark-im-chat-create.md(0.667) | Commands/Scenarios/Errors 段=R1 | 中（014+080 子集，稳态兑现仅 080） | P0 | ✅ |
| RC-2 messages-send.md 内部冗余 | 评测归因 | references/lark-im-messages-send.md(0.333) | — | — | — | （round-2 已收割，不再是抓手） |
| RC-3 SKILL.md 常驻正文 | 评测归因 | SKILL.md(1.0) | 多为 R2/R3 路由·identity | — | — | （round-1 已压一刀；剩余多为全域路由/身份，effect 风险高，不选） |

- 选中理由：RC-1 是 reach>0 集合里**唯一从未被任何轮收割的干净文件**（2023 至今原样），且其冗余型态与 round-2 已采纳并 PASS 的 messages-send.md 完全同型（罗列+重复+--help 镜像）。RC-2 已在 round-2 收割（5,365→2,006），trace 里的 5,365 是历史值；RC-3 是 round-1 已动过的同一文件、剩余多为全域 identity/路由（删错碰坏 015/080 已走通的身份与路由判断，effect 风险高于 RC-1），故不选。
- 选模块理由：chat-create.md reach=0.667（014+080 调用前都读到，状态③，非触达问题——纯减体积场景）；它正是承载 RC-1 的文件。未选 reach=0 的 22 个盲区 reference（改了也不在判决集、无法被采纳，触 reach 锁）。
- 规范经验源补注：双视角同指一处。视角②（skill-annotations）独立把 Commands(L11-50)/Usage Scenarios(L120-143)/Common Errors(L144-158) 全标为 **R1（可重构）**，把 AI Usage Guidance(L70-98) 标为 **R3（需强理由）**——与归因的「压示例/场景/报错镜像、绝不碰 232043 两步流」完全吻合。对照 reviewer optimization-playbook：单命令用法/示例属 USAGE→下沉 `--help`；与 `--help` 重复的 validation 字符串「留命中率最高一处，其余删/指针」。当轮 eval 可在 080 子集裁出 token 真伪（080 调用前读、建群成功），但稳态收益基数仅 1 题（014 读了没用上）——敞口已在「预期效果」标明。

## 改了什么（逐处）
- **Commands(L12-50)** — 12 个 bash 示例（多条仅差一个 flag）压成 5 个差异化示例 + 一行 `--help` 指针。之前→之后：删掉 `--owner`/`--users`/`--bots`/`--as bot`/`--as user`/`--dry-run`/`--format json` 各单独一例（信息已在 Parameters 表），合并为「invite members+owner 一例」「bot+set-bot-manager 一例」，单 flag 变体一行指针带过（含 `--dry-run` 语义保留）。
- **Usage Scenarios(L120-143)** — 整段 3 场景删除/搬迁。Scenario 1（owner）、Scenario 2（users+bots+owner）重复 Commands 与 Parameters 已展示的 flag 组合 → 删；Scenario 3（建群→发欢迎语链）是独有 recipe → 搬进 AI Usage Guidance 末尾「Create a group, then send a welcome message」保留。
- **Common Errors(L144-158)** — 9 行压成 2 行。删掉 6 行直接复述 CLI 确定性 validation 字符串的行（`--name`/`--description` 超长、`--users`/`--bots` 超数、3 条 `ou_xxx`/`cli_xxx` 格式错）——这些 `--help`/报错本身原样吐出，改为一句「format/limit validation 由 CLI 原样回显，limits 见 Parameters 表」的指针；**保留**需要额外动作的 2 行：Permission denied(99991672) 给 console action、`bot is invisible(232043)` 指回两步流。

## 为什么这么改（机制）
- **省 context 的因果**：chat-create.md 是 lazy reference，读到即整文件进窗口（080/014 reach=0.667）。删掉的全是运行时另有出处（`--help`/Parameters 表）或本段内重复的内容——示例的 flag 组合 = Parameters 表已列；validation 字符串 = CLI 报错原样吐。删后 Agent 仍能：经 SKILL.md 选对 `+chat-create`、经 Parameters 表/`--help` 补全 flag 用法、遇 232043 走两步流。即 optimization-playbook §13 核心判据「删掉后 Agent 是否仍能选对命令并补到用法」——成立。
- **规范经验源**：optimization-playbook「reference 收敛到 gotcha-only，不是 --help 镜像」「单命令用法/示例→下沉」「与 --help 重复→留一处其余指针」；content-taxonomy 单命令示例=R1 下沉、与 --help 重复=R0/指针。annotation 三段独立标 R1，本改动落在 R1 重构范围内，未触 R3 段。

## 预期效果
- 成功率（effect，硬门槛）：**不退化**。所有 effect 红线逐条保留并已 grep 校验（见下「刻意没做什么」）。080 实际只用 `--name --format json` 最简建群链——本改动未碰该链路任何一环；014 卡在跨域 contact+授权（非本 reference）。
- context（分两层）：
  - **(1) 静态字数差**：bytes 7996→6450（-19.3%）、chars -19.5%、words -23.0%、tiktoken(cl100k 代理) 2125→1714(-19.3%)。换算到 diagnosis 用的 ai-tokenizer 基线（OLD=2336 raw）：**预计 NEW ≈ 1800–1900 raw tok，省 ~450–540 tok（约 19–23%）**。
  - **(2) 运行时 context 方向**：对**读到 chat-create.md 的题（080，及理论上 014）下降** ~450–540 tok；对没读它的题（015）**无影响**（015 大头是单次 `Read` 22.5k 工具输出，与本 reference 无关）。本改动是纯删减、无新增前置/增读拉力，不会抬升运行时 token。
  - **与 direction 一致**（objective=降 token），无张力。
- **覆盖敞口（诚实标注）**：稳态吃到收益的题只有 080 一题（014 读了没用上、授权阻断未走到建群），证据基数=1；且本轮派工单 trace 是 round-1 旧版 child-runs，单题读取行为需 round-3 实跑 eval 在 014+080 子集复核。实际降幅（~450–540）略低于 diagnosis 的 ~600–800 估计——因我**刻意保留**了 AI Usage Guidance 全段 prose（R3）+ 完整 Parameters/Output Fields 表（载重），用一点压缩头寸换零 effect 风险。

## 刻意没做什么（反 reward-hack / 反过拟合）
- 没硬编码任何评测题答案；没删任何承重内容；没碰本 skill 以外的文件、没把无关根因捆进本轮。
- **逐条保留的载重红线（已 grep 校验存在）**：
  - 232043 两步流全段（contact search → `--users 当前用户` 建群 → `chat.members create --as user` 加其他人 → 查 `invalid_id_list`）；
  - `succeed_type=1` 语义解释；
  - `--chat-mode topic` vs 「普通群 + `group_message_type=thread`」的区分注解；
  - `--owner` 默认行为（bot 身份默认 bot / user 身份默认授权用户）；
  - 全部 flag（含 `--set-bot-manager`、`--dry-run`、`--type public`、`--users/--bots` 上限与格式）、identity/scope 指引、互斥与护栏规则、Output Fields 全表。
- 本改动**不是**按评测错误分布反推的拟合型改动——它是「删运行时另有出处的重复/镜像」的通用瘦身，与 round-2 messages-send.md 同型同纪律；非针对某几题的特判。
- 未做 RC-3（SKILL.md 进一步压缩）：剩余多为全域 identity/路由，删错有 effect 风险，超出本轮低风险抓手范围。未做 015 的前置补充：那是增内容、与降 token 反向（方向冲突，diagnosis 已记录）。

## 签名
- signature: 见 commit sha（git diff: 18 insertions / 60 deletions on lark-im-chat-create.md）  tier: T1
