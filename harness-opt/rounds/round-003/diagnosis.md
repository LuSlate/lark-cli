# Round 3 归因（parent=557349b…（round-2 已采纳候选）；候选模块见 candidate_modules，由 candidate-writer 据诊断+reach 点名）

> 目标（objective.json）：**在不回退成功率的前提下降低 lark-im skill 文档的 token 成本**。effect 是硬门槛、不可退化；token 与 duration 是并列成本杆。tier=T1，仅可改 `skills/lark-im/**`。target_axis=token。
> 判分点只当「什么算挂」的锚，不抄 grader 药方。

## ⚠️ trace 与当前文件的版本错位（先看，决定本轮抓手是否还在）

**本轮派工单 trace = round-1 的全 3 题 child-runs**（round-2 只评了 080，故用 round-1 作最近的全覆盖代理）。这些 trace 里的 reference 体积是 **round-1/round-2 改动之前** 的旧版。我用 session-analyze 所用的同一 ai-tokenizer 实测了**当前工作树**文件，确认两者错位如下：

| 文件 | trace 内体积（旧版，Read 计） | 当前实测（raw / Read 计） | 已被哪轮收割 |
|---|---|---|---|
| `SKILL.md`（Skill 注入正文） | 3,455–3,456 tok | 3,525 raw | round-1（API Resources/权限表→schema 指针） |
| `references/lark-im-messages-send.md` | **5,365 tok** | **2,006 raw / 2,194 Read** | **round-2（5,365→2,006，已收割）** |
| `references/lark-im-chat-create.md` | 3,060–3,062 tok | **2,336 raw / 2,645 Read** | **未动过（2023 至今原样），唯一未收割** |

**含义**：round-2 诊断里的 **RC-2（messages-send.md 内部冗余）已经在 round-2 被采纳并收割**（5,365→2,006），它不再是本轮抓手——不要据 trace 里的 5,365 重复提一遍。本轮 trace 里那块 5,365 是历史值，当前已不存在。**reach>0 集合里唯一还没被压过的干净文件就是 `chat-create.md`**（round-2 的 RC-3）。

## 跨 case 共同根因（优先看；按对 TOKEN 目标的杠杆排序）

### RC-1（token，本轮头号且基本是唯一的干净抓手，reach=0.667：014+080）—— `chat-create.md` 内部存在「示例罗列 + 场景重复 + --help 镜像」三类可压缩冗余，且从未被优化过
- **现象**：`chat-create.md` 当前 2,336 raw tok（Read 计 ~2,645），是 reach>0 集合里**唯一未被任何轮收割**的 reference。section 级实测分布（raw tok）：

  | section | tok | 性质 |
  |---|---|---|
  | header(1-11) | 198 | 载重（scope/映射），保留 |
  | **Commands(12-50) 12 个 bash 示例** | **425** | **过度罗列**：多条仅差一个 flag（`--owner` / `--users` / `--bots` / `--as bot` / `--as user` / `--dry-run` 各一例），信息已在 Parameters 表里 |
  | Parameters 表(52-69) | 500 | 多数载重；`--chat-mode` 的 L68 长注解与表内 L62 行语义重复 |
  | AI Usage Guidance(70-108) | 442 | **载重**（232043 两步流是 080/014 路由依据），但表述偏长 |
  | Output Fields(109-119) | 126 | 载重 |
  | **Usage Scenarios(120-143) 3 个场景** | **198** | **重复**：Scenario 1/2 重复 Commands 已展示的 `--owner`/`--users`/`--bots` 组合；Scenario 3 重复 messages-send 的串联用法 |
  | **Common Errors(144-158) 9 行** | **395** | **部分 --help 镜像**：多行直接复述确定性 validation 字符串（`--name exceeds 60`、`--users exceeds 50`、`invalid user id` 等），这些 `--help` / 报错本身就会原样吐出 |
  | References(159-163) | 44 | 载重 |

- **这正是 round-2 已经在 messages-send.md 上验证过、且被采纳的同一套压缩模式**：round-2 把 messages-send.md 的「4 处重复选型规则 + 全媒体形态 Commands + --help 镜像」压成「保留载重规则 + 一句 `--help` 指针」（5,365→2,006，被采纳）。chat-create.md 的 Commands(425)↔Usage Scenarios(198) 重叠、Common Errors(395) 的 validation 镜像，是同型冗余。
- **可压缩量级（粗估，非药方）**：可压缩质量集中在 Commands+Usage Scenarios 的重叠（合计 ~623 tok，去重后可省一大半）+ Common Errors 的 --help 镜像行。**保守估计可从 2,336 压到 ~1,500–1,700 raw tok（省约 600–800 tok，约 30%）**，与 messages-send.md 的压缩比同量级。具体改法与确切降幅由 candidate-writer 决定、评测裁决。
- **载重红线（candidate-writer 取舍时的 effect 风险点，不是 RC-1 不成立）**：AI Usage Guidance 的 **232043 两步流 + `succeed_type=1`**、`--chat-mode topic` vs 普通群+话题消息模式的区分、`--owner` 默认行为，是 014/080 走通 bot 身份建群的语义依据，**不能在压缩中误删**。这条 reference 被 080 实读且 080 据它建群成功（`ok:true`），所以 effect 风险真实存在——压的是示例/场景/报错镜像的体积，不是语义规则。
- **axis=token**。可信度=**按需读取**（reach=0.667，子集=014+080，2 题）。压它的降幅只在这 2 题子集里计入，不被 015（没读它）稀释；但子集仅 2 题、且 014 是「读了没用上」（授权阻断没走到建群），实际吃到压缩收益的稳态题只有 080 一题——**证据基数小，降幅需评测在子集上确认**（见数据缺口）。

### RC-2（token，已收割，本轮不再是抓手）—— messages-send.md 的内部冗余 round-2 已压掉
- round-2 RC-2 已被采纳：messages-send.md 5,365→2,006 raw。**本轮不要据 trace 里的 5,365 重复提**。当前 messages-send.md 已是「载重规则 + `--help` 指针」形态，无明显二次压缩空间（剩余多为 content-flag 选型、@mention、media 约束等载重内容）。reach=0.333（仅 080）。

### RC-3（token，无 T1 干净抓手）—— SKILL.md 常驻正文 round-1 已压过，剩余多为载重 identity/路由
- SKILL.md 经 Skill 工具每题必加载（reach=1.0），当前 3,525 raw tok（round-1 已把 API Resources/权限表折叠成 schema 指针）。剩余 `## Important Notes`(L36–85) 各小节（Sender Name Resolution / message enrichment / `--download-resources` / Card / Flag / Feed Shortcut）与 `## Shortcuts` 全表(L87–115) 虽本轮 3 题低命中，但它们是**全域 identity/路由/约束**——这是 round-1 已经动过一刀的同一文件，**再压属同向继续、但删错会碰坏 015/080 已走通的 bot 身份与命令路由判断**（effect 风险高于 RC-1）。**列为更次级、风险更高的抓手**，不作为本轮首选；若要动须只删本轮已确证低命中且非路由的纯枚举行，谨慎程度高于 chat-create。

## 命令失败热点（跨 case；失败类型由我从 timeline 命令串读出，非判决数字）

| lark-cli 命令 | 失败次数 | 涉及题数 | 主要失败类型 | 指向的文档问题 |
|---|---|---|---|---|
| `contact +search-user` | 4 | 1 (014) | bot exit2(invalid_argument) ×2；`--as user` token_missing ×2 | **跨 lark-contact 域**，非 lark-im 内容 |
| `auth qrcode --output <绝对/沙箱外路径>` | 1 | 1 (014) | unsafe output path，改相对路径重试成功 | 路径约束在 lark-shared（不可改） |
| `im +messages-search` | 2 | 1 (015) | bot exit2 + `--as user` exit2 | 该命令 user-only（SKILL 表已注明）；bot 身份必败，agent 没看清就猜 |
| `im +chat-messages-list --page-all` | 1 | 1 (015) | exit2（无过滤 page-all） | 见下「015 token 黑洞」 |
- **解读**：本轮**没有一条 lark-im 命令因「参数名/类型写错」系统性失败**。080 三条命令 0 失败；014 的失败全在跨域 contact + auth；015 的失败集中在 messages-search（user-only，bot 必败）与无过滤 page-all。**没有 lark-im 侧常规「报错/参数整形」工单**——与 token 减体积方向一致，本轮抓手是减体积不是补内容。

## 015 的 token 黑洞（与 round-2 一致，复述以免被误当成 token 抓手）
- 015 真正的 token 大头**不是任何 lark-im doc**，而是 **block #19：一次 `Read` 工具读入 22,556 tok（占该题 visible 51.5%）**。成因链：#12/#17 `+messages-search`/`--page-all` exit2 → #18 退到 `+chat-messages-list`（无过滤）→ 输出 43.5KB 被持久化 → agent `Read` 整文件 → 22.5k tok 灌进上下文 → 再靠本地 grep(#27–33) 抠出「飞豆」两条。
- **从文档角度**：`chat-messages-list.md` 本题 reach=0（状态①：调用前从没读），它本写了 `--start/--end`、`--page-size` 等可避免全量拉取的约束。**但补它=增常驻/触达内容，与本轮降 token 目标方向相反**（见方向冲突）；且 22.5k 是**单次工具输出**（强依赖该群消息量，单题不可外推），不是稳定常驻热点。**结论：观察项，交评测裁决，不作为本轮 token 抓手。**

## 可发现性时序（约束 5 三态；判「前置能不能救」的决定性证据）
> 对每条相关 reference / `--help`，按相对首次失败调用的读取时序统计。`--help` 扫 Bash（本轮 3 题均未跑任何 `--help`）。

| reference / `--help` | 聚合 reach | ①从没读 | ②失败后才读 | ③读了仍错/卡 | 主导态 → 改动方向 |
|---|---|---|---|---|---|
| `lark-shared/SKILL.md` | 1.0 | 0 | 0 | — | 三题调用前都读了；014 仍卡（环境，非内容）；不可改 |
| `chat-create.md` | 0.667 | 0 | 0 | — | 080 调用前读→建群成功；014 调用前读→授权阻断（非 reference 错）。**非触达问题，纯减体积** |
| `messages-send.md` | 0.333 | 0 | 0 | — | 080 调用前读→发卡片成功。**非触达问题**（已收割） |
| `chat-messages-list.md` | 0.0 | 1 (015) | 0 | — | ① 015 调用前从没读→`--page-all` 全量拉取→token 黑洞。触达缺口，但补它=增 token，与目标冲突 |
| `messages-search.md` | 0.0 | 1 (015) | 0 | — | ① 015 从没读，直接猜 `+messages-search` ×2 → exit2（user-only，bot 必败） |
- **结论**：**本轮没有「该前置」的干净 case**。RC-1（chat-create.md 减体积）是「调用前已读、内容够用 → 去冗余」的纯 token 减法，不涉及触达。015 的两处 ① 触达缺口确实存在，但修它们=增内容、与降 token 目标相反，且 015 已 PASS（bot + 本地 grep 兜底）——属观察项，**不要被诱导去推前置**。

## 方向冲突记录（硬性约束 7）
- **减体积（RC-1 chat-create.md，与 objective.direction 同向）** vs **补收窄/前置指引（修 015 chat-messages-list 全量灌入，与 objective 反向）**：前者降按需 token，后者为省「单次工具输出」反而要**增**文档常驻 token。两者方向相反，**不可合并**。本轮目标是降 token，取减体积一侧；015 全量灌入作为观察项记录、不作为要补的内容根因。

## 差距台账复盘
- 无（`discard-ledger.json` 为空，无已跑未采纳候选）。

## 逐 case

### 1 (014) [workorder=PASS / 实质 FAIL] token=34,555(reported)/visible 17,364 耗时=37s 命令失败率=5/7 维度=效果(不可修)
- 判分点结果：3 条全 ✗——建群/拉人/发消息全未发生，卡在 `contact +search-user` 解析 open_id（user 授权阻断 + 跨域 contact）。verdict=PASS 系聚合口径，按判分点证据当 FAIL 处理。
- 命令失败：5/7。`contact +search-user` bot exit2 ×2、`--as user` token_missing ×2；`auth qrcode` 绝对路径 unsafe ×1（改相对路径成功）。**全部非 lark-im 命令**。
- 可发现性时序：#4 读 SKILL.md 正文(3,456) + #6 读 lark-shared(3,751，跨 skill) + #7 读 chat-create.md(3,062，调用前已读)；失败在更上游的跨域 contact + 授权。**非 lark-im 触达问题**。
- token 归因：SKILL.md 正文 3,456（常驻静态，19.9%）+ lark-shared 3,751（**跨 skill，不归因 lark-im**）+ chat-create.md 3,062（按需，17.6%，**本题读了没用上**——授权阻断没走到建群）+ 系统 Skill 列表注入 4,612（固定开销，不归因）。lark-cli 命令累计含多次短失败回显，单条都短、非热点。
- 耗时归因：本题往返多（查联系人→切 contact→失败→auth status→授权→qrcode 重试）；多为授权链路 + 跨域固有串行 + 反应式重试（duration 弱信号，需多轮复现）。
- 文档根因：效果=沙箱 user 授权 + 跨域 contact（环境，**无 lark-im 文档根因，本轮不改**）；token=chat-create.md 按需冗余（RC-1，但本题读了没用上，收益只在 080 这种走通题里兑现）+ SKILL.md 常驻（RC-3，风险高、次级）。

### 2 (015) [PASS·真] token=54,568(reported)/visible 43,760 耗时=2m5s 命令失败率=3/11 维度=token（但大头非 lark-im doc）
- 判分点结果：3/3 ✓——定位群、转发「飞豆」消息、@傅六铭知会全部成功（两次 `messages-send` 均 `ok:true`）。**全程 bot 身份，无授权阻断**。
- 命令失败：3/11。`+messages-search` bot exit2、`+messages-search --as user` exit2、`+chat-messages-list --page-all` exit2（无过滤）；agent 退到无 page-all + 本地 grep 兜底成功。（#14 `--page-all | grep` 返回空属「成功但无命中」，非硬失败，未计入。）
- 可发现性时序：① `messages-search.md` / `chat-messages-list.md` 调用前从没读（reach=0），直接猜命令。**本题未读任何 lark-im reference**，故 lark-im reference 的体积与本题 token 无关。
- token 归因：**本题 token 大头不是 lark-im doc**，是 block #19 一次 `Read` 持久化文件 = **22,556 tok（51.5%，归「其他工具调用/返回」）**，成因=`--page-all` 无过滤全量拉取→43.5KB→Read 灌入（**单次输出**可信度，强依赖该群消息量）。SKILL.md 正文 3,448（常驻）。lark-shared 3,749（跨 skill，不归因）。**RC-1 改 chat-create.md 对本题 token 无影响**（本题没读它）。
- 耗时归因：本题最长(2m5s)，主因 messages-search 连环失败→改 page-all→大输出→多次本地 grep 抠数据的多轮往返（duration 弱信号；model calls 16/raw 32，明显高于 080，作旁证）。
- 文档根因：token 黑洞的放大器=`chat-messages-list.md` 没被读到（状态①）+ SKILL.md 表未提示大群应 server-side 收窄——但**补这条与降 token 目标相反**（方向张力），列为观察项；本题已 PASS。本轮 token 抓手（RC-1）不落在本题。

### 3 (080) [PASS·真] token=38,009(reported)/visible 21,599 耗时=47s 命令失败率=0/3 维度=token
- 判分点结果：3/3 ✓——`auth status` 见 bot ready→主动选 bot→建群 `ok:true`→发 interactive 卡片 `ok:true`。**任务完整完成，零命令失败**。
- 命令失败：0/3。三条 lark-cli（auth status / chat-create / messages-send）全成功。
- 可发现性时序：#4 读 SKILL.md 正文(3,455) + #6 读 lark-shared(3,751，跨 skill) + #9 读 chat-create.md(3,060) + #10 读 messages-send.md(5,365，旧版) ，全部状态③（调用前已读且用上）。**无触达问题。** 实际只用了 `+chat-create --name … --format json` 的最简形态——没用两步流/owner/members/topic/error-recovery。
- token 归因：**本题是纯 token 抓手题**——读取 Skill 占 56.4%：messages-send.md 5,365（trace 旧版，**当前已被 round-2 压到 2,006，本轮不再可压**）+ SKILL.md 正文 3,455（常驻，RC-3）+ chat-create.md 3,060（按需，**RC-1，当前 2,336，本轮唯一干净抓手**）。系统 Skill 列表注入 4,612（固定开销，不归因）。lark-shared 3,751（跨 skill，不归因）。
- 耗时归因：47s，全部为正常建群+发卡片串行，无重试、无写后回查（无离群）。
- 文档根因：无效果根因（已绿）；token=RC-1（chat-create.md 内部冗余，本题是其收益唯一稳态兑现题）+ RC-3（SKILL.md 常驻，风险高、次级）。**本题 token 杠杆最清晰且 effect 风险可控**（命令全成功，压 chat-create.md 的示例/场景/报错镜像不碰 080 实际用到的最简建群链路）。

## 给 candidate-writer 的收口（不含具体改法）
- **唯一在 T1 内还没被收割的干净 token 抓手是 RC-1（`chat-create.md` 内部冗余）**：Commands 12 例过度罗列 + Usage Scenarios 3 场景重复 Commands + Common Errors 9 行部分镜像 validation 字符串——**与 round-2 已采纳的 messages-send.md 压缩同型**，粗估可省 ~600–800 raw tok（约 30%）。reach=0.667（014+080），降幅在子集计入。
- **载重红线**：AI Usage Guidance 的 232043 两步流 + `succeed_type=1` + `--chat-mode topic` 区分 + `--owner` 默认，是 080/014 走通 bot 建群的语义依据，**压缩中不可误删**——压的是示例/场景/报错镜像体积，不是规则。
- **RC-2 已收割**：messages-send.md round-2 已 5,365→2,006，trace 里的 5,365 是历史值，**不要重复提**。
- **RC-3（SKILL.md 常驻）是次级且风险更高**：round-1 已压过一刀，剩余多为全域 identity/路由/约束，删错碰坏 015/080 已走通的 bot 身份与命令路由——不作首选。
- **不要推前置**：本轮没有「该前置」的干净 case。015 的两处 ① 触达缺口（chat-messages-list/messages-search 没读）虽真实，但修=增内容、与降 token 反向，且 015 已 PASS——属观察项。
- **effect 不可在本轮 T1 内合法抬升**：014 是环境（沙箱不能扫码）+ 跨域 contact，无 lark-im 文档根因；015/080 已真 PASS。effect deltas 视作 auth-noise，不追。
- **干净 token 抓手接近见底（诚实判断）**：reach>0 集合三个文件中，messages-send.md（round-2）与 SKILL.md（round-1）已各压一刀，**chat-create.md 是最后一个未动过的干净文件**。压完它之后，T1 内 reach>0 的纯冗余（罗列/重复/--help 镜像）基本耗尽；再往下只剩 (a) 高 effect 风险的 SKILL.md 载重内容，或 (b) reach=0 的 22 个盲区 reference（压了也不在判决集、无法被采纳）。**本轮 RC-1 很可能是这条优化路径上最后一个低风险、可被采纳的 token 抓手。**
- **缺失信息（doc_fix_hint 语气，非药方）**：chat-create.md 把同一组 flag 在 Commands(12 例) 与 Usage Scenarios(3 场景) 重复演示、Common Errors 多行复述 `--help`/报错本身就会吐的 validation 字符串——这类「枚举/重复/镜像、低增量」内容是其 token 的主要去处，且是减法（删冗余）而非加法。

## 数据缺口
1. **trace 版本错位（最关键）**：本轮 trace=round-1 旧版 child-runs，messages-send.md 在 trace 里仍是 5,365（round-2 已压到 2,006）。所有「当前文件体积」结论我已用 ai-tokenizer 实测当前工作树校正（SKILL.md 3,525 / chat-create.md 2,336 / messages-send.md 2,006），但**单题行为与 reach 仍来自旧 trace**——若 round-2 改动改变了 080/014 的读取行为，需以实际 round-3 eval-run 复核。
2. **RC-1 子集小**：chat-create.md reach=0.667 但实际吃到压缩收益的稳态题只有 080（014 读了没用上、授权阻断），证据基数=1，降幅需评测在子集确认。
3. **015 的 22.5k 黑洞是单次工具输出**，强依赖该群消息量，非稳定常驻热点，单题不可外推；且与降 token 目标方向冲突，不作抓手。
4. **duration 三题波动大**（37s/2m5s/47s），015 长尾主因 messages-search 连环失败+大输出多轮抠数据；单轮不足定论，需多轮复现。model calls(8/16/6) 比 wall-clock 稳，可作旁证。
5. **工具调用口径不一致**：trend.json 的 R1 tool_calls=26.3、R2=10，与 session-analyze 的 model calls(8/16/6) 口径不同（趋势表疑似含 raw 计数）；旁证以 timeline 实际往返为准。趋势看：R1→R2 命令失败率 0.60→0.35、tool_calls 26→10 明显下降，但那主要是 effect 从「三题全卡授权」变成「2 真 PASS + 1 卡」带来的，**不是 token 改动的功劳**；token 均值 R1 31,997→R2 42,377 上升，主因是 R2 只评 080（单题大）口径差异 + 015 黑洞，非文档常驻变重——趋势对 token 轴判读价值有限，以单题 session-analyze 为准。
6. **effect 维度全部归因为「无文档根因/不可修」**：014 跨域+环境，015/080 已绿。本轮 effect 无 T1 可发力点，deltas 视作 auth-noise。
