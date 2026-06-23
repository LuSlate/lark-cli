# Round 1 归因派工单（parent=phi0；模块未定，由 candidate-writer 据诊断点名）

> **只读输入**——opt-attributor 读本文件，把诊断**另写** `diagnosis.md`（给 candidate-writer）+ 逐题结构化 `attribution.json`（给 dashboard）。**不要覆盖本文件**，留作派工单↔诊断的前后对比。
> 判分点只当「什么算挂」的锚，禁止照抄 grader 药方（已从派工单剔除）。

## 模块运行时可达性（选模块第一步的证据；要选须在 strategy.md 说明理由）
> reach=**实测**触达率（域主 SKILL.md 经 Skill 工具加载、reference 经 Read，都从 trace 实测，没有恒在的面）；判决集=实测∪预期触达。**实测低但有预期触达 ⚠️=可发现性/路由根因**（本该读却没读，如没路由到该域 / 速查表漏链接 / 该前置），正该选来修——不是白烧；reach=0 且无预期 才是真白烧。 **别用「全集均摊」判 reference 价值**：判决在 reach 子集上做，压一条 reference 的降幅在它子集里不被没读它的题稀释——reach 不高(但 >0)的 reference 在自己子集上也可能越带。
- `skills/lark-im/SKILL.md` → reach=1.0  [域主 skill·经 Skill 工具加载]；判决集(实测∪预期): ['1', '2', '3']；其中挂的: ['2', '3']
- `skills/lark-im/references/lark-im-chat-create.md` → reach=0.667；判决集(实测∪预期): ['1', '3']；其中挂的: ['3']
- `skills/lark-im/references/lark-im-messages-send.md` → reach=0.667；判决集(实测∪预期): ['1', '3']；其中挂的: ['3']
- （另 22 个 reference reach=0 且无预期触达，本轮无关，略）

### 2  [FAIL]  ctx=34616  (acc=274168)  52787ms  tools=25
- session.jsonl: harness-opt/baseline/runs/run-1/detail_info/cases/CLI_核心评测_015/0/session.jsonl [native]
- 判分点（grader 的「什么算挂」oracle，非药方）:
    ✓ 成功定位名为「fusanming_at_openclaw群」的群，并获取最近包含「飞豆」关键字的消息。
    ✓ 将筛选出的相关消息内容转发到「fusanming_at_需求测试群」。
    ✓ 在「fusanming_at_需求测试群」中 @傅六铭 做知会，消息发送成功。

### 3  [FAIL]  ctx=31289  (acc=225396)  46776ms  tools=22
- session.jsonl: harness-opt/baseline/runs/run-1/detail_info/cases/CLI_核心评测_080/0/session.jsonl [native]
- 判分点（grader 的「什么算挂」oracle，非药方）:
    ✓ 使用用户身份创建一个名为「今晚吃什么」的群，预期返回 chat_id
    ✓ 创建一张飞书卡片，卡片内容包含「今天晚上吃什么」
    ✓ 将该卡片发送到新建群中，预期返回 message_id

### 1  [PASS]  ctx=30086  (acc=292379)  51004ms  tools=32
- session.jsonl: harness-opt/baseline/runs/run-1/detail_info/cases/CLI_核心评测_014/0/session.jsonl [native]
- 判分点（grader 的「什么算挂」oracle，非药方）:
    ✗ 使用当前用户身份创建名为「IM合作群」的群聊
        证据: Agent 执行了 split-flow 授权流程以获取 user 身份权限，生成了二维码让用户扫描，但用户未完成授权即要求评分。Auth status 显示 'User identity: missing'，群聊未被创建。
    ✗ 将傅一铭和傅二铭加入该群
        证据: 依赖群聊创建结果。由于群聊未创建（blocked by user identity missing），无法添加成员。
    ✗ 在该群发送文本消息「大家体验有问题随时沟通」，并返回可验证的 chat_id / message_id
        证据: 依赖群聊创建结果。由于群聊未创建，无法发送消息。
