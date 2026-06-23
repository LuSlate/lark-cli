# Round 1 归因（候选模块见 candidate_modules；模块由 candidate-writer 根据诊断和 reach 选定）

> 目标（objective.json）：**在不回退成功率的前提下降低 lark-im skill 文档的 token 成本**。effect 是硬门槛、不可退化；token 与 duration 是并列成本杆。tier=T1，仅可改 `skills/lark-im/**`。
> 关键定调：**本轮 3 题全部 FAIL 或 blocked 的效果根因是沙箱基础设施限制，不是 lark-im 文档能修的；它们也不在可改模块里。** 因此本轮的真实抓手是 token 轴（每次运行常驻 + 误导性内容），不是去「修挂题」。下面分维度说明。

## 跨 case 共同根因（优先看）

### RC-1（效果，FAIL 主因）—— 非文档根因 / 本轮不可修：user 身份授权在沙箱内无法完成
- **现象**：3 题用户都说「使用我的身份」，agent 走 `--as user` → 返回 `authentication / token_missing` → 按授权规则发起 `auth login --no-wait` → 生成二维码 → 把链接交给用户并结束本轮。沙箱里没有真人扫码，user 身份永远 `missing`，于是建群/搜群/发消息全部 blocked。三题轨迹高度同构（015/080/014）。
- **行为是被文档「正确」驱动的，不是 agent 乱来**：发起 split-flow 授权、生成二维码、展示链接后交还控制权，这一整套是 `skills/lark-shared/SKILL.md`（L17、L72–105）明确 MUST 的流程。agent 严格照做。
- **归因落点**：根因在**沙箱无法完成交互式 user 授权**（基础设施）＋ 驱动该行为的授权流程文档在 `lark-shared`。
- **为什么本轮不可修（重要，给 candidate-writer 的边界）**：
  1. `lark-shared/SKILL.md` **不在 candidate_modules**（objective.modules 只含 `skills/lark-im/**`），无权改。
  2. 即便能改，沙箱不能扫码这一物理限制不是文档能绕过的——这是环境，不是内容缺失。
  3. **不要试图通过让 agent 改走 `--as bot` 来「修绿」**：用户显式要「我的身份」，grader 判分点也写「使用当前用户身份创建」。改路由去 bot 是 reward-hack（绕过判分点、语义回退），不是合法的成功率修复。reviewer 会据此 FAIL。
- **axis=效果**，但标注为**无文档根因 / 本轮不改**。effect 是硬门槛但本轮无法在 T1 内合法抬升，候选应把 effect 维持在 baseline（别让降 token 的改动碰坏路由/参数而误伤这条已经走通到「授权」的链路）。

### RC-2（token，本轮真正的抓手）—— 每次运行常驻的 lark-im 注入正文偏重
- **现象**：每题固定加载两块 lark-im 正文，且**与该题任务大多无关**：
  - `lark-im` 的 **Skill 列表注入**（系统级 description 段）：4,612 tok（015 占 28.2%、080 占 18.8%、014 占 25.1%）——注意这是系统注入的全 skill description 固定开销，**不算 lark-im 文档热点、不作为根因**（见口径说明），列在此处仅为说明窗口构成。
  - `lark-im` 的 **SKILL.md 正文**（经 Skill 工具加载，reach=1.0）：约 **5,722–5,777 tok/题**，三题都常驻。这是 `skills/lark-im/SKILL.md`，**在可改模块内，是 token 轴的头号可控热点**。
- **SKILL.md 里有大量与本轮任务无关的常驻清单**：`## API Resources` 段（L114+）逐条列了 chats / chat.members / messages / reactions / threads / image / pin / feed 等**每个 resource.method 的 identity 规则与 owner/admin/tenant 约束**（L123–190，几十行）。本轮 3 题只用到建群、搜群/搜消息、发消息、转发、@——绝大多数 method 行每次运行都被加载却从不被用到。这是典型「每次运行都会加载的运行时冗余清单常驻」。
- **可信度=常驻静态**：SKILL.md 经 Skill 工具每题必加载（reach=1.0），tiktoken 可测、跨题稳定（5,722/5,724/5,777 三题一致）。这是降 token 最稳的发力点。
- **axis=token**。文档位置：`skills/lark-im/SKILL.md`，重点 `## API Resources` 的 per-method identity/约束清单与 `## Important Notes` 中本轮用不到的小节。

### RC-3（token，次级抓手）—— 按需 reference 体积偏大，且只在用到的题里计入
- **现象**：080 读了 `chat-create.md`(3,062 tok) + `messages-send.md`(5,367 tok)，两块 reference 合计 8,429 tok，占该题 visible 的 34.4%。014 也读了 chat-create.md。
- **判据**：reach（chat-create=0.667、messages-send=0.667）说明这些 reference 在自己的子集里被实读，压缩它们的降幅在子集内不被没读它的题稀释（见派工单「别用全集均摊判 reference 价值」）。`messages-send.md` 单文件 5,367 tok 尤其大。
- **可信度=按需读取**：只在实际 Read 该 reference 的题里计入，不能按全集均摊。
- **axis=token**。文档位置：`skills/lark-im/references/lark-im-messages-send.md`、`lark-im-chat-create.md`。

### RC-4（duration，弱信号，需复现）—— `auth qrcode --output "/tmp/..."` 被拒后反应式重试
- **现象**：3 题都先用 `--output "/tmp/lark_auth_qr.png"`（或 `/workspace/agent-cwd/qrcode.png`）→ 报 `validation / invalid_argument: unsafe output path` → 改用相对路径 `./xxx.png` 重试成功。每题多 1–2 个往返。
- **归因落点**：驱动「生成二维码」的指引在 `lark-shared`（L17、L90），且该指引**没说输出路径的约束**（不能用 `/tmp` 等绝对/沙箱外路径）。这是「报错没指下一步 + 文档没写约束」的耗时根因。
- **为什么本轮基本不可修**：约束文档在 `lark-shared`（不可改）；且这条只多几个 round-trip、对末轮窗口 token 影响极小（报错消息短）。
- **可信度**：耗时波动大，单题不算数；但此模式**3 题一致复现**，作为 duration 旁证可信度提升。不过它仍**不在 T1 可改范围**，仅记录。
- **axis=duration**，标注为**驱动文档不可改（lark-shared）**。

## 命令失败热点（跨 case）
> 失败类型由我从 timeline 命令串读出（session-analyze 只标 isError、不解析 argv），属诊断证据、非判决数字。

| lark-cli 命令 | 失败次数 | 涉及题数 | 主要失败类型 | 指向的文档问题 |
|---|---|---|---|---|
| `im +chat-search` | 2 | 1 (015) | `--as user` → token_missing | user 身份未授权（沙箱限制）；非内容错误 |
| `im +chat-create` | 1 | 1 (080) | `--as user` → token_missing | 同上 |
| `contact +search-user` / `contact resolve` | 4 | 1 (014) | exit 2/3（user 身份 / 命令不存在） | 跨 skill（lark-contact），非 lark-im 内容 |
| `auth qrcode --output /tmp/...` | 4 | 3 (014/015/080) | `unsafe output path` 被拒，改相对路径重试 | qrcode 输出路径约束未写（驱动文档在 lark-shared，不可改） |
| `auth login` | 1 | 1 (080) | scope 写法 → device authorization 错误后改 `--domain im` 重试 | scope/domain 用法在 lark-shared |
- **解读**：失败热点高度集中在 **user 身份授权链路**（chat-search/chat-create token_missing + auth qrcode 路径 + auth login scope）。这一整条链路的驱动与约束文档都在 `lark-shared`，**不是 lark-im 文档能修的**。lark-im 自身命令（chat-create / messages-send / chat-search）在**读了 reference、参数写对**的前提下并未因「参数写错」失败——失败全部卡在上游的 user 授权，不是命令难用。**这意味着没有 lark-im 侧的「报错/输出整形」工单**。

## 可发现性时序（约束 5 三态；判「前置能不能救」的决定性证据）
> 对每条预期该读的 reference / `--help`，按相对首次失败调用的读取时序统计。`--help` 扫 Bash（不在 reach 里）。

| reference / `--help` | 聚合 reach | ①从没读 | ②失败后才读 | ③读了仍错 | 主导态 → 改动方向 |
|---|---|---|---|---|---|
| `lark-shared/SKILL.md` | 1.0 | 0 | 0 | 3 | ③ 调用前已读，仍卡授权 → **非触达问题**；且不可改 |
| `lark-im-chat-create.md` | 0.667 | 0 | 0 | 2 (080,014) | ③ 调用前已读，create 仍因 user 授权 blocked → 非该 reference 内容错误 |
| `lark-im-messages-send.md` | 0.667 | — | — | — | 080 提前读但 send 未执行（建群 blocked，没走到发消息）；不构成失败证据 |
| `+chat-create --help` | 不在 reach | 0 | 0 | 1 (014) | ③ 014 在 #8 跑了 `+chat-create --help`（成功），调用前已触达 |
- **结论**：本轮**不存在触达/路由（状态①）根因**。三题都在调用前读到了 SKILL.md（reach=1.0）、读到了相关 reference、甚至跑了 `--help`。失败发生在**内容已触达之后的上游授权环节（状态③语义，但根因是环境而非文档内容错）**。
- **对 candidate-writer 的含义**：**不要把 RC-1 误判为①而推「前置授权说明」**——内容已经读到了，前置救不了沙箱不能扫码。前置类改动在本轮对 effect 无效，只会增 token，与目标背道而驰。

## 差距台账复盘
- 无（round 1，`discard-ledger.json` 为空）。

## 逐 case

### 2 (015) [FAIL] token=34616 耗时=52787ms 命令失败率=3/5 维度=效果(不可修)+token
- 判分点结果：3 条全未满足——定位群、转发消息、@知会都依赖 user 身份搜群，user 身份未授权 → 全部 blocked。
- 命令失败：3/5。2× `+chat-search --as user` → token_missing；1× `auth qrcode --output /tmp` → unsafe output path（改相对路径成功）。
- 可发现性时序：SKILL.md 调用前已读（reach=1.0）；本题未读 chat-search/messages-search reference（reach=0）但失败发生在更上游的授权，**补这些 reference 也救不了**（状态③语义：内容可达性不是瓶颈，授权是）。
- token 归因：SKILL.md 正文 5,777 tok（常驻静态，35.3%）+ 系统级 Skill 列表注入 4,612 tok（固定开销，不归因）。本题未读大 reference，故 token 主来源就是常驻 SKILL.md 正文。
- 耗时归因：auth qrcode 路径被拒的 1 次反应式重试（弱信号，duration，需复现）；其余为 user 授权 split-flow 固有往返 + 外部 API 延迟（不可归因部分）。
- 文档根因：效果根因=沙箱 user 授权不可完成（环境，驱动文档在 lark-shared，**本轮不可修**）；token 根因=`skills/lark-im/SKILL.md` 常驻正文偏重（**可修，T1 抓手**）。

### 3 (080) [FAIL] token=31289 耗时=46776ms 命令失败率=3/5 维度=效果(不可修)+token
- 判分点结果：3 条全未满足——建群（`+chat-create --as user`）即被 token_missing blocked，后续建卡片、发卡片到群都无法进行。
- 命令失败：3/5。1× `+chat-create --as user` token_missing；1× `auth login --scope "..."` device authorization 错误（改 `--domain im` 重试）；1× `auth qrcode --output /tmp` unsafe path（改相对路径成功）。
- 可发现性时序：调用前读了 SKILL.md + chat-create.md + messages-send.md（全部状态③，调用前已触达）；建群仍因 user 授权 blocked，**非 reference 内容错误**。
- token 归因：**本题 token 最重，读取 Skill 占 49.6%**——chat-create.md 3,062 + messages-send.md 5,367 = 8,429 tok（按需读取）＋ SKILL.md 正文 5,722 tok（常驻静态）。这是 RC-2 + RC-3 同时发力的题。messages-send.md 提前读但本题根本没走到发消息（建群已 blocked），属「读了没用上」的浪费。
- 耗时归因：auth qrcode 重试 + auth login scope 写错重试，各 1 次反应式往返（弱信号，duration，需复现）。
- 文档根因：效果=沙箱 user 授权（不可修）；token=SKILL.md 常驻正文 + 两个偏大 reference（**可修，T1 抓手；本题杠杆最高**）。

### 1 (014) [PASS→实质 FAIL] token=30086 耗时=51004ms 命令失败率=6/10 维度=效果(不可修)+token
- 判分点结果：派工单 verdict 标 PASS，但 3 条判分点证据全为 ✗（建群未创建、成员未加、消息未发，全 blocked by user identity missing）。**实质是 FAIL**，PASS 系上层聚合口径差异，归因按判分点证据处理。
- 命令失败：6/10（最高）。`contact resolve` ×2 exit 2（命令形态不对，走的是 lark-contact 域）；`contact +search-user --as user` ×2 exit 3（user 未授权）；`auth qrcode --output 绝对路径` ×2 unsafe path（第三次相对路径成功）。
- 可发现性时序：#7 调用前读 SKILL.md（reach=1.0）；#8 跑了 `+chat-create --help`（成功，状态③，调用前已触达建群用法）；随后为查联系人切到 lark-contact skill。失败集中在 user 授权与跨域 contact 查询，**非 lark-im 内容可达性问题**。
- token 归因：SKILL.md 正文 5,724 tok（常驻静态，31.1%）+ 系统 Skill 列表注入 4,612 tok（固定开销，不归因）+ lark-contact 正文 991 tok（跨域，非 lark-im）。lark-cli 命令累计 2,577 tok（14%），含多次失败回显，但单条都短、非热点。
- 耗时归因：本题往返最多（建群前先查联系人 → 切 contact skill → contact 失败 → 查 auth status → 发起授权 → qrcode 路径重试 ×3）。多为 user 授权链路 + 跨域查联系人固有串行 + 反应式重试（duration 弱信号，需复现）。
- 文档根因：效果=沙箱 user 授权 + 跨域 contact 不可用（环境，不可修）；token=`skills/lark-im/SKILL.md` 常驻正文（**可修，T1 抓手**）。

## 给 candidate-writer 的收口（不含具体改法）
- **唯一在 T1 内可合法发力的轴是 token**，对应 RC-2（SKILL.md 常驻正文，3 题全命中、最稳）与 RC-3（chat-create/messages-send reference 偏大，080 命中）。两者方向一致（减体积），可作为本轮候选的目标轴。
- **effect 不可在本轮 T1 内合法抬升**（RC-1 环境限制 + 驱动文档在不可改的 lark-shared）。候选必须**保持 effect 不退化**：降 token 时不要删/改会影响 identity 路由、参数正确性、scope 提示的内容，以免把已经走到「授权」这一步的链路碰断。
- **方向冲突提示**：RC-1 若有人想「补授权说明帮 agent 过」与目标（降 token）方向相反，且对沙箱无效——**明确不要做**。RC-2/RC-3（减体积）与目标同向，无冲突。
- **缺失信息（doc_fix_hint 语气，非药方）**：SKILL.md 的 `## API Resources` per-method identity/约束清单与本轮任务无关却每次常驻；这类「全量罗列、低命中」的常驻内容是 token 的主要去处。messages-send.md / chat-create.md 单文件偏大，按需读取时仍是大块。
- **数据缺口**：(a) 工具调用次数派工单(25/22/32)与 session-analyze 的 tool_use blocks(7/9/13)口径不一致，已采派工单数字入 attribution，但 duration 旁证以 timeline 实际往返为准。(b) duration 根因（RC-4）单轮不足以定论，需多轮/多次复现；且其驱动文档在 lark-shared 不可改。(c) 014 派工单 verdict=PASS 与判分点证据全 ✗ 冲突，归因按判分点证据当 FAIL 处理。
