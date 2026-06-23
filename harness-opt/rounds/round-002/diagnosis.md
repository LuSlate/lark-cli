# Round 2 归因（parent=round-1 已采纳候选 51f2a70e；候选模块见 candidate_modules，由 candidate-writer 据诊断+reach 点名）

> 目标（objective.json）：**在不回退成功率的前提下降低 lark-im skill 文档的 token 成本**。effect 是硬门槛、不可退化；token 与 duration 是并列成本杆。tier=T1，仅可改 `skills/lark-im/**`。
> 判分点只当「什么算挂」的锚，不抄 grader 药方。
> **本轮 trace = round-1 已采纳候选（51f2a70e，SKILL.md 已 trim 到约 3,915 tok）的行为**，不是 baseline。三题 session 实测已确认 SKILL.md 注入正文为 3,751 tok/题（与 trim 后体积一致），round-1 报告的 5,722 tok/题是 trim 前数字，已过期。

## ⚠️ 对 round-1 定调的关键修正（先看，影响整轮方向）

round-1 把三题一律定调为「user 身份授权在沙箱内不可完成 → 全部 blocked」。**实测 trace 推翻了这个 monolith：三题行为完全不同，只有 1 题真卡授权。**

| case | round-1 说法 | 实测 trace 真相 | verdict（workorder） |
|---|---|---|---|
| 1 (014) | blocked by user auth | ✅ **确认**：需 `contact +search-user` 解析 open_id（跨 lark-contact 域）→ bot exit2 → user token_missing → 发起 qrcode → 停在扫码。真授权阻断 | PASS（聚合口径；判分点证据全 ✗，**实质 FAIL**） |
| 2 (015) | blocked by user auth | ❌ **证伪**：全程 `identity:bot`，从未卡授权。搜群✓、定位「飞豆」消息✓、转发✓、@傅六铭✓，两次 `messages-send` 全 `ok:true`。**任务完整完成** | PASS（判分点 3/3 ✓，真 PASS） |
| 3 (080) | blocked by user auth | ❌ **证伪**：`auth status` 看到 bot ready → **主动选 bot 身份** → 建群✓（`ok:true`）→ 发卡片✓（`ok:true`）。**任务完整完成** | PASS（判分点 3/3 ✓，真 PASS） |

**含义**：本轮 effect 实际是 **2 真 PASS + 1 实质 FAIL**，不是 round-1 描述的「三题全 blocked」。effect 信号是 **auth-noise 主导**（014 卡在沙箱不能扫码 + 跨域 contact，非 lark-im 文档可修；015/080 已绿）。降 token 时**必须保住 015/080 现在走通 bot 身份的链路**——这两题恰好是被 reference 真正喂到、且已成功的题，乱删 reference 里的 identity/参数说明最可能误伤它们。

## 跨 case 共同根因（优先看；按对 TOKEN 目标的杠杆排序）

### RC-1（token，头号抓手，3 题全命中、最稳）—— SKILL.md `## Important Notes` + Shortcuts 全表常驻，本轮任务低命中
- **现象**：SKILL.md 经 Skill 工具每题必加载（reach=1.0），实测 3,751 tok/题、三题一致（常驻静态）。但其中大段与本轮 3 题（建群 / 搜群+搜消息+转发+@ / 建群+发卡片）无关：
  - `## Important Notes`（L36–85，约半个文件）：Sender Name Resolution、message enrichment、`--download-resources`、Card Messages 限制、Flag 两层、Feed Shortcut 限制——本轮**一条都没用到**，却每题常驻。
  - `## Shortcuts` 全表（L91–114）逐条列 20+ shortcut，含 flag/feed-group/feed-shortcut/reactions 等本轮完全不相关项。
- **可信度=常驻静态**：tiktoken 可测、跨题稳定（3,751×3）。这是降 token 最稳的发力点，且 3 题全命中（reach=1.0），降幅不被任何子集稀释。
- **axis=token**。文档位置：`skills/lark-im/SKILL.md` 的 `## Important Notes` 低命中小节 + `## Shortcuts` 全量表。
- **方向张力（必须标注）**：这是 round-1 已经动过一刀的同一文件（折叠了 API Resources/权限表）。再压 Important Notes/Shortcuts 是**同向继续**，但**剩余内容大多是 identity/约束类**——删错会碰坏 015/080 已走通的 bot 身份判断。candidate-writer 取舍时这是 effect 风险点，不是 RC-1 不成立。

### RC-2（token，次级抓手，080 命中、按需读取）—— `messages-send.md` 单文件偏大且内部高度冗余
- **现象**：080 读了 `messages-send.md`，实测 **5,365 tok**——本轮所有按需 reference 里最大的单块（占 080 visible 的 24.8%）。该 reference 实测被读且**确实用上了**（080 据此发卡片成功），不是「读了没用」。
- **从文档看为何这么大**：messages-send.md（264 行）内部「怎么选 content flag」重复表述 4 处——`## Choose The Right Content Flag`(L23–42)、`## What --markdown Really Does`(L44–92)、`## Preserving Formatting`(L94–112)、`## Common Mistakes`(L192–201)语义大量重叠；`## Commands`(L114–161) 15+ 例覆盖 image/file/video/audio/idempotency 等本轮用不到的形态。这是「单文件冗余 + 全形态罗列」，不是信息缺失。
- **可信度=按需读取**：只在实读它的子集（reach=0.333，仅 080）里计入，压缩降幅在该子集不被稀释——但**子集只有 1 题**，证据基数小，效果需评测确认（见数据缺口）。
- **axis=token**。文档位置：`skills/lark-im/references/lark-im-messages-send.md`。

### RC-3（token，次级抓手，014+080 命中、按需读取）—— `chat-create.md` 按需读取偏大
- **现象**：014 与 080 都读了 `chat-create.md`，实测 3,060–3,062 tok（reach=0.667）。080 据此建群成功（用上了）；014 读后因 user 授权阻断没走到建群（读了但本题没用上）。
- **可信度=按需读取**（reach=0.667，子集 2 题）。体积本身不离群，杠杆低于 RC-2，列为更次级。
- **axis=token**。文档位置：`skills/lark-im/references/lark-im-chat-create.md`。

### RC-4（效果，无文档根因 / 本轮不可修）—— 014 的 user 授权阻断 + 跨域 contact 依赖
- **现象**：014 需先解析「傅一铭/傅二铭」open_id，走 `contact +search-user`（**lark-contact 域，不在 candidate_modules**）：bot 身份 exit2（invalid_argument）→ `--as user` token_missing → 发起 `auth login`+qrcode → 停在扫码。判分点证据全 ✗。
- **归因落点**：根因=沙箱不能交互扫码（环境）＋ 跨域 contact 命令不可用（非 lark-im）。**lark-im 文档侧无根因、无可修点**——这正是约束 3 的「无文档根因 / 本题不改」出口，不要为凑根因往 lark-im doc 上硬编。
- **axis=效果**，标注**无文档根因 / 本轮不改**。effect 维持 baseline 即可，不要试图改路由让 014「修绿」（用户显式要本人身份解析联系人，改 bot 是 reward-hack）。

## 命令失败热点（跨 case；失败类型由我从 timeline 命令串读出，非判决数字）

| lark-cli 命令 | 失败次数 | 涉及题数 | 主要失败类型 | 指向的文档问题 |
|---|---|---|---|---|
| `contact +search-user` | 4 | 1 (014) | bot exit2(invalid_argument) ×2；user token_missing ×2 | **跨 lark-contact 域**，非 lark-im 内容 |
| `auth qrcode --output 绝对路径` | 1 | 1 (014) | unsafe output path，改相对路径重试成功 | 路径约束在 lark-shared（不可改） |
| `im +messages-search` | 2 | 1 (015) | exit2（bot 身份 + `--as user` 均 exit2） | 见下「messages-search 难用」分析 |
| `im +chat-messages-list --page-all` | 1 | 1 (015) | exit2（无过滤 page-all） | 见下「015 token 黑洞」分析 |
- **解读**：本轮**没有一条 lark-im 命令因「参数名/类型写错」系统性失败**。080 三条命令 0 失败；015 的失败集中在 `messages-search`（见下）。这意味着**没有 lark-im 侧的常规「报错/参数整形」工单**——与 RC-1/2/3 的 token 方向一致，本轮抓手是减体积不是补内容。

### 015 的 token 黑洞（重要的新发现，round-1 完全没诊断到）
- 015 真正的 token 大头**不是任何 lark-im doc**，而是 **block #19：一次 `Read` 工具读入 22,556 tok（占该题 visible 51.5%）**。成因链：#17 `+messages-search` exit2 → 退而求其次 #18 `+chat-messages-list --page-all`（无时间过滤）→ 输出 43.5KB 被持久化到文件 → agent `Read` 整个文件 → 22.5k tok 灌进上下文。后面又靠本地 `grep`(#27–33) 抠出「飞豆」两条。
- **从文档角度**：`chat-messages-list.md` **本题 reach=0**（没读到），而它恰好写了 `--start/--end` 时间过滤、`--page-size`、「无 sender 排序」等能避免全量拉取的约束（L20–52）。SKILL.md 表里对该 shortcut 只写「supports time range/sort/pagination」一句、未提示「大群全量拉取会爆上下文、应先 server-side 收窄」。**这是一个真实的「该读没读 → 全量灌入」放大器**（约束 5 状态①：调用前从没读该 reference）。
- **但这条对本轮目标是「方向张力」，不是干净的 token 抓手**：要避免全量灌入，文档侧只能**增加**收窄指引（前置或加 caution），这与「降 token」的常驻成本目标**方向相反**（见硬性约束 7 的冲突记录）。且 22.5k 黑洞是**单次工具输出**（单次输出可信度、单题、强烈依赖该群消息量），不是稳定常驻热点。**结论：列为观察项交评测裁决，不要当成 RC-1 那种干净抓手去推「前置 chat-messages-list」——很可能只增 token 不省。**

## 可发现性时序（约束 5 三态；判「前置能不能救」的决定性证据）
> 对每条相关 reference / `--help`，按相对首次失败调用的读取时序统计。`--help` 扫 Bash（本轮 3 题均未跑任何 `--help`）。

| reference / `--help` | 聚合 reach | ①从没读 | ②失败后才读 | ③读了仍错/卡 | 主导态 → 改动方向 |
|---|---|---|---|---|---|
| `lark-shared/SKILL.md` | 1.0 | 0 | 0 | — | 三题调用前都读了；014 仍卡（环境，非内容）；不可改 |
| `chat-create.md` | 0.667 | 0 | 0 | — | 080 调用前读→建群成功；014 调用前读→授权阻断（非 reference 错）。**非触达问题** |
| `messages-send.md` | 0.333 | 0 | 0 | — | 080 调用前读→发卡片成功。**非触达问题** |
| `chat-messages-list.md` | 0.0 | 1 (015) | 0 | — | ① **015 调用前从没读**→直接 `--page-all` 全量拉取→token 黑洞。触达缺口，但补它=增 token，与目标冲突（见上） |
| `messages-search.md` | 0.0 | 1 (015) | 0 | — | ① 015 从没读 messages-search.md，直接猜 `+messages-search` ×2 → exit2。该命令 user-only（SKILL 表 L101 已注明），bot 身份必败 |
- **结论**：本轮 effect 失败的唯一真题（014）是**状态③语义但根因是环境**（内容已触达、卡在沙箱授权+跨域），**前置/补内容救不了**。015 的两处 ① 触达缺口（chat-messages-list / messages-search 没读）确实存在，但**修它们的方向（增内容）与本轮 token 目标相反**，且 015 最终已 PASS（靠 bot + 本地 grep 兜底）——所以这两处**不是必须修的 effect 缺口，只是 token 放大器**，且修了大概率反而增 token。
- **对 candidate-writer 的含义**：**本轮没有「该前置」的干净 case**。RC-1/2/3 都是「调用前已读、内容够用 → 减体积」的纯 token 减法，不涉及触达。不要被 015 的两处 ① 诱导去推前置——那会与目标背道而驰。

## 方向冲突记录（硬性约束 7）
- **减体积（RC-1/2/3，与 objective.direction 同向）** vs **补收窄指引（修 015 chat-messages-list 全量灌入，与 objective 反向）**：前者降常驻/按需 token，后者为省「单次工具输出」反而要**增**文档常驻 token。两者方向相反，**不可合并**。本轮目标是降 token，应取减体积一侧；015 的全量灌入作为观察项记录、不作为本轮要补的内容根因。

## 差距台账复盘
- 无（round 2，`discard-ledger.json` 为空，无已跑未采纳候选）。

## 逐 case

### 1 (014) [workorder=PASS / 实质 FAIL] token=34555(reported)/visible 17,364 耗时=37s 命令失败率≈5/7 维度=效果(不可修)
- 判分点结果：3 条全 ✗——建群/拉人/发消息全未发生，卡在 `contact +search-user` 解析 open_id（user 授权阻断）。verdict=PASS 系聚合口径，按判分点证据当 FAIL 处理。
- 命令失败：≈5/7。`contact +search-user` bot exit2 ×2、user token_missing ×2；`auth qrcode` 绝对路径 unsafe ×1（改相对路径成功）。**全部非 lark-im 命令的内容错误**。
- 可发现性时序：调用前读了 SKILL.md(reach=1.0)+chat-create.md(3,062 tok)；失败在更上游的跨域 contact + 授权。**非 lark-im 触达问题**。
- token 归因：SKILL.md 正文 3,751（常驻静态，21.6%）+ chat-create.md 3,062（按需，17.6%，本题没走到建群=读了没用上）+ 系统 Skill 列表注入 4,612（固定开销，不归因）。lark-cli 命令累计含多次短失败回显，单条都短、非热点。
- 耗时归因：本题往返多（查联系人→切 contact→失败→auth status→授权→qrcode 重试）。多为授权链路 + 跨域固有串行 + 反应式重试（duration 弱信号，需多轮复现）。
- 文档根因：效果=沙箱 user 授权 + 跨域 contact（环境，**无 lark-im 文档根因，本轮不改**）；token=SKILL.md 常驻（RC-1）+ chat-create.md 按需（RC-3）。

### 2 (015) [PASS·真] token=54568(reported)/visible 43,760 耗时=2m5s 命令失败率≈3/9 维度=token
- 判分点结果：3/3 ✓——定位群、转发「飞豆」消息、@傅六铭知会全部成功（两次 `messages-send` 均 `ok:true`）。**全程 bot 身份，无授权阻断**。
- 命令失败：≈3/9。`+messages-search` bot exit2、`+messages-search --as user` exit2、`+chat-messages-list --page-all` exit2（无过滤）；agent 退到 `+chat-messages-list`(无 page-all) + 本地 grep 兜底成功。
- 可发现性时序：① `messages-search.md` / `chat-messages-list.md` **调用前从没读**（reach=0），直接猜命令。messages-search 是 user-only（SKILL 表 L101 已注明）、bot 身份必败——agent 没看清就猜。
- token 归因：**本题 token 大头不是 lark-im doc**，是 block #19 一次 `Read` 持久化文件 = **22,556 tok（51.5%，其他工具调用/返回）**，成因=`--page-all` 无过滤全量拉取→43.5KB→Read 灌入（单次输出可信度，强依赖该群消息量）。SKILL.md 正文 3,749（常驻）。lark-shared 3,749（跨 skill，不归因 lark-im）。
- 耗时归因：本题最长(2m5s)，主因是 messages-search 连环失败→改用 page-all→大输出→多次本地 grep 抠数据的多轮往返（duration 弱信号；工具调用 16 raw32，明显高于 080，作旁证）。
- 文档根因：token 黑洞的放大器=`chat-messages-list.md` 没被读到 + SKILL.md 表未提示大群应 server-side 收窄——但**补这条与降 token 目标相反**（方向张力，见上），列为观察项；本题已 PASS。常规 token 抓手仍是 RC-1（SKILL.md 减体积）。

### 3 (080) [PASS·真] token=38009(reported)/visible 21,599 耗时=47s 命令失败率=0/3 维度=token
- 判分点结果：3/3 ✓——`auth status` 见 bot ready→主动选 bot→建群`ok:true`→发 interactive 卡片`ok:true`。**任务完整完成，零命令失败**。
- 命令失败：0/3。三条 lark-cli（auth status / chat-create / messages-send）全成功。
- 可发现性时序：调用前读 SKILL.md + chat-create.md(3,060) + messages-send.md(5,365)，全部状态③（调用前已读且用上）。**无触达问题**。
- token 归因：**本题是纯 token 抓手题**——读取 Skill 占 56.4%：messages-send.md 5,365（按需，最大单块，RC-2）+ SKILL.md 3,751（常驻，RC-1）+ chat-create.md 3,060（按需，RC-3）。三块 reference/SKILL 都实读且 RC-2 的 messages-send.md 确实用上了。系统 Skill 列表注入 4,612（固定开销，不归因）。
- 耗时归因：47s，全部为正常建群+发卡片串行，无重试、无写后回查（无离群）。
- 文档根因：无效果根因（已绿）；token=RC-2(messages-send.md 内部冗余) + RC-1(SKILL.md 常驻) + RC-3(chat-create.md)。**本题 token 杠杆最高且无 effect 风险**（命令全成功，减 reference 体积不碰已走通链路）。

## 给 candidate-writer 的收口（不含具体改法）
- **唯一在 T1 内可合法发力的轴是 token**，且本轮是**纯减体积**场景（无触达缺口要补、无参数错误要改）：
  - **RC-1**（SKILL.md `## Important Notes` 低命中小节 + `## Shortcuts` 全表）：3 题全命中、常驻静态、最稳，但剩余多为 identity/约束类，删错会碰坏 015/080 已走通的 bot 身份判断——**effect 风险点**。
  - **RC-2**（messages-send.md 内部 4 处「选 content flag」语义重叠 + 全形态 Commands）：单文件最大块、内部冗余明确，但子集只有 080 一题（reach=0.333），证据基数小、效果需评测确认。
  - **RC-3**（chat-create.md 按需偏大）：杠杆最低，列为更次级。
- **effect 不可在本轮 T1 内合法抬升**：014 是环境（沙箱不能扫码）+ 跨域 contact，无 lark-im 文档根因。015/080 已真 PASS。候选必须**保住 015/080 走通 bot 身份的 identity/参数说明**，降 token 时别误伤。
- **不要推前置**：本轮没有「该前置」的干净 case。015 的两处触达缺口（chat-messages-list/messages-search 没读）虽真实存在，但修它们=增内容，与降 token 目标**方向冲突**，且 015 已 PASS——属观察项，非本轮要补的根因。
- **缺失信息（doc_fix_hint 语气）**：SKILL.md 的 Important Notes/Shortcuts 全量罗列、本轮低命中却每题常驻；messages-send.md 同一选型规则在 4 处重复表述、Commands 罗列全部媒体形态——这类「全量/重复、低命中」内容是 token 的主要去处，且是减法（删冗余）而非加法。
- **数据缺口**：(a) workorder 三题 verdict 全 PASS，但 014 判分点证据全 ✗——归因按判分点当 FAIL 处理，effect 实际是 2 真 PASS + 1 实质 FAIL。(b) RC-2/RC-3 子集小（messages-send.md 仅 080、chat-create.md 仅 014+080），单轮证据基数小，token 降幅需评测在子集上确认。(c) 015 的 22.5k 黑洞是单次工具输出，强依赖该群消息量，非稳定常驻热点，单题不可外推。(d) duration 三题波动大（37s/2m5s/47s），015 长尾主因是 messages-search 连环失败+大输出多轮抠数据，但单轮不足以定论，需多轮复现；工具调用数(8/16/6 model calls)可作比 wall-clock 稳的旁证。(e) 工具调用次数 session-analyze(model calls 8/16/6) 与 workorder 趋势表(R1 均值 26.3) 口径不一致，趋势表疑似含 raw 计数，旁证以 timeline 实际往返为准。
