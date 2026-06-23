# Round 1 候选策略（模块=skills/lark-im/SKILL.md, tier=T1, 主指标=token）

## 根因与选择
| 根因 | 来源(评测归因/规范经验) | 承载模块(reach) | annotation 风险级 | coverage 档 | P级 | 选中 |
|---|---|---|---|---|---|---|
| RC-2：SKILL.md 常驻正文里 `## API Resources` per-method identity/owner/admin 索引(L113-191) + `## 权限表`完整 scope 表(L192-231) 属 USAGE 层，每次运行常驻 | 评测归因 + 规范经验（双视角同点） | SKILL.md(1.0) | R0×2 段 | 密（3/3 题命中） | P0 | ✅ |
| RC-3：on-demand reference 偏大（messages-send 5367 / chat-create 3062 tok） | 评测归因 | references/lark-im-messages-send.md(0.667)、chat-create.md(0.667) | R1 多 / R3 少 | 中（仅 080/014） | P1 | |
| RC-1：user 身份沙箱授权不可完成 | 评测归因（effect） | lark-shared（不可改） | — | — | — | 不可修 |
| RC-4：auth qrcode 路径被拒重试 | 评测归因（duration） | lark-shared（不可改） | — | — | — | 不可修 |

- **选中理由**：本轮 objective 主轴=token，effect 因 RC-1（沙箱 user 授权 + 驱动文档在不可改的 lark-shared）本轮无法在 T1 内合法抬升，故只在 token 轴发力。RC-2 是 reach=1.0 的头号可控热点——3 题全命中、tiktoken 稳定（5,722/5,724/5,777）、每次运行都付费。RC-3 是 reach=0.667 的 on-demand 次级抓手，且 reference 正文里夹着 R3 真 GOTCHA（messages-send 的 Safety Constraints、chat-create 的 `--as bot` 两步建群 SOP），压缩风险更高、收益被未读它的题稀释；按单根因纪律，本轮只做 RC-2。RC-1/RC-4 落 lark-shared，越界即被 scope check 拒，且沙箱物理限制非文档可绕——不碰。
- **选模块理由**：SKILL.md reach=1.0（经 Skill 工具每题必加载），是 RC-2 的唯一承载。改动全部落在它内部，coherent，不触任何别的 skill。
- **规范经验源补注**：双视角在同一处汇合——
  - 视角②（annotation）：`skill-annotations.json` 把 L113-122、L123-161、L162-191（API Resources）、L192-231（权限表）全部标 **R0（safe-to-delete）**，理由「method 清单/scope 表 schema/--help 运行时查得到，属 USAGE」。
  - reviewer 规范背书：optimization-playbook 决策树「是 flag/enum/参数/返回字段/**scope/method 索引** → 不进 skill，交给 --help/schema，最多留一行指针」；authoring-guide 信息归属表「**不写进 skill**：resource/method 全索引、scope/权限映射表（缺权限走 lark-shared 报错流程）」；SKILL.md 锚点 6「`--help`/schema 管 USAGE，reference 只留 gotcha」。三处独立指向同一删除对象。
  - coverage：3/3 题都加载 SKILL.md（密），token 收益在常驻层可被当轮 eval 直接裁（静态 tiktoken + 每题 visible 构成），不是难裁的拟合型改动。

## 改了什么（逐处）
- `skills/lark-im/SKILL.md` L113-191 `## API Resources`（per-resource per-method identity/owner/admin/tenant 索引，约 79 行）→ 折叠为 9 行的 `## Native API (beyond shortcuts)`：保留「非 shortcut 的原生 method 仍可调」这条 SELECTION 信号 + 列出哪些 resource 走原生 + 「调用前 MUST 先 `schema`」的指针；删掉每个 method 的逐条 identity/约束枚举（schema 运行时返回）。
- `skills/lark-im/SKILL.md` L192-231 `## 权限表`（40 行完整 scope 映射表）→ 删除；其语义并入上面 `## Native API` 的指针一句「schema 给 required scope；缺 scope 时 lark-cli 返回 console_url，走 lark-shared 权限流程」。
- `skills/lark-im/SKILL.md` Shortcuts 速查表新增 2 行：`reactions.*` → `references/lark-im-reactions.md`、`feed.groups.*` → `references/lark-im-feed-groups.md`。**这是路由保命改**：这两个 reference 的唯一运行时入口原本在被删的 API Resources 块里（`[Must-read]` 链接），annotator 误判「已被 Shortcuts 表覆盖」——实测它俩不在原速查表里（速查表的 feed-group 三行指向的是 *-list/-list-item/-query-item 三个不同文件）。不补这 2 行 = 删 reference 链接 = 该 reference reach 永久归 0、路由断裂。

## 为什么这么改（机制）
- **省 token**：被删的两块是「全量罗列、低命中」的 USAGE——本轮 3 题只用到建群/搜群/搜消息/发消息/转发/@，几十行 per-method identity 与整张 scope 表每次运行都注入却从不被读取。删后 Agent 仍能：(1) 经 SKILL.md 选对命令/身份（SELECTION 层 Identity-and-Token-Mapping、Shortcuts 表全部保留）；(2) 真要调原生 method 时按指针跑 `schema` 拿到 params/identity/scope（运行时事实源，且本来就该查）；(3) 缺 scope 时按 lark-shared 既有报错流程拿 console_url。即「删了 Agent 还做得对吗？做得对就删」（锚点 2）。
- **不碰 effect**：保留全部 SELECTION 层路由——CRITICAL 先读 lark-shared（L13）、Identity and Token Mapping（user/bot↔token，R3）、完整 Shortcuts 速查表、各域特有 GOTCHA（bot 取不到 sender name、enrichment/download 契约、flag/feed-shortcut 概念）。没有改 identity 路由、没有改参数正确性、没有删 scope 提示语义（指针仍指向 schema+lark-shared 流程）。已经走到「user 授权」这一步的链路不会被碰断。
- **规范背书**：optimization-playbook §2 决策树 + authoring-guide 信息归属表 L95 + SKILL.md 锚点 6，三处独立判定 method 索引/scope 表「不进 skill，最多留一行指针」——本改动正是把两块 USAGE 折叠成指针。

## 预期效果
- **成功率（effect 硬门槛）**：不退化。删除的是 USAGE 枚举，保留全部 SELECTION/路由/身份/GOTCHA。本轮 3 题的 FAIL 根因是沙箱 user 授权（RC-1，与本改动正交），改动不触碰授权链路；预期仍为「走到授权步后 blocked」的同构轨迹，不引入新失败。
- **context（分两层）**：
  - (1) **静态字数差**：SKILL.md 从 4,960 → 2,986 tok（cl100k_base，reviewer 脚本实测），**-1,974 tok / -39.8%**；落入金标杆带（中位数 ~2,400、lark-shared 2,709），接近上一轮 IM 治理目标 2,040。
  - (2) **每题运行时 context 方向**：3 题全部下降，且降幅≈静态差——因为 SKILL.md reach=1.0 每题必全量加载，常驻层减重直接等额传导到每题 visible（评测里 SKILL.md 正文 5,722-5,777 tok/题 → 预计降约 2k/题）。**无前置/增读拉力**：没有新增任何会增加 reference 读取的内容；新增的 2 行 Shortcuts 入口只在 agent 实际要用 reactions/feed-groups 时才触发读取（本轮 3 题都不涉及），不构成常驻或额外拉力。与 direction（token↓）一致，无张力。
- **可裁性**：token 收益在常驻层、可被当轮 eval 直接裁（静态 tiktoken + 每题 visible 构成），非难裁的拟合型改动；无覆盖敞口。

## 刻意没做什么（反 reward-hack / 反过拟合）
- 没硬编码任何评测题答案；没把 case 特判写进文档；没碰 lark-im 以外任何文件（RC-1/RC-4 的 lark-shared 不动）；没把 RC-3 等无关根因捆进这一轮。
- **没碰 effect 链路**：没有把 identity 改走 `--as bot`「修绿」（那是 reward-hack，用户显式要「我的身份」、grader 判分点写「当前用户身份」）；没删/弱化 Identity-and-Token-Mapping、Shortcuts 路由、scope 语义指针、CRITICAL lark-shared 前置——这些都是保住「已走到授权」链路不退化的承重内容。
- **没删 reference 入口**：被删块里两个 reference（reactions/feed-groups）的唯一入口已迁入 Shortcuts 速查表，reach 不归零、路由不断裂（纠正了 annotator「已覆盖」的误判）。
- **没做输出裁剪、没碰命令行为**（T1 docs-only，且 playbook 红线：输出裁剪须独立设计验证）。
- **没补「前置授权说明」**：诊断证据显示 3 题调用前都已读到 SKILL.md（reach=1.0），失败在更上游的沙箱授权（状态③语义、根因是环境），前置救不了且只会增 token，与目标背道——明确不做。
- 这是「减体积」改动、与评测错误分布无拟合关系，不存在朝错误分布过拟合的敞口；lite 无 sealed 也不构成隐患。

## 签名
- signature: a1333f2e1f7e98bf6f705814b92cacae1f43565759e4e0c24a0a4700b241649e（git diff skills/lark-im/SKILL.md 内容哈希）  tier: T1
