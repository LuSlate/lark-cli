# 插件实例调用指南

创建/更新插件实例后，根据本文件做调用决策，再读技术栈 Skill 写代码。

## 调用前获取权威依据

**必须**先读取以下文件获取 actions 信息：

```bash
# 插件 manifest — actions / outputMode / inputSchema / outputSchema
cat <project-path>/node_modules/<pluginKey>/manifest.json

# 实例配置 — paramsSchema / formValue
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

**编码前闸门**：先列出 Schema 摘录，确认后再写代码。

```
pluginInstanceId: xxx
actionKey: xxx
outputMode: unary | stream
input.required: [...]
output.fields: [...]
调用侧: Client | Server（仅全栈应用）
持久化: 是 | 否（及方式）
```

若摘录字段缺失，不得进入实现阶段。

### Client vs Server 决策

| 应用类型 | 可选调用侧 |
|---------|-----------|
| Design / Modern（appType=3/6，纯前端） | 只有 Client 侧 |
| 全栈应用（appType=2，NestJS + React） | Client 侧（首选）或 Server 侧 |

**Server 侧仅在以下场景使用**：
1. 涉及敏感凭证（token/secret 不能暴露给前端）
2. 多步骤强事务编排（需要原子性）
3. 触发器/定时任务（无前端上下文）
4. 插件结果需持久化到数据库（调用+落库在同一方法中完成）

> 不涉及上述场景，仅即时展示（流式渲染、一次性展示）→ Client 侧。

### 持久化决策

**设计阶段就要判断**，不要等到写代码时才想。

以下任一条件成立时，插件结果**必须**保存到数据库：
1. 结果会在其他页面展示
2. 结果供后续功能消费
3. 用户再次访问时需要看到结果
4. 结果对应数据库中已有字段

仅一次性即时展示（聊天对话、临时预览）时可不持久化。

**持久化方式优先级**：
- **推荐（A）**：Server 侧 Service 调用插件 + 同一方法落库
- **备选（B）**：Client 侧调用插件 → 流式结束后调已有 CRUD 接口保存

复用已有 create/update 接口，不要为插件结果单独建 API。

### 失败日志最小集

```typescript
{ pluginInstanceId, actionKey, outputMode, inputKeys, error }
```

---

## 生成调用代码

完成上述决策后，**读取项目的技术栈 Skill** 获取具体代码模式（import 路径、call/callStream 写法、normalizeStream、NestJS 注入等）。

技术栈 Skill 的位置（`<project-path>` 即 `lark-apps-plugin.md` § 确认项目上下文 中已确定的应用根目录）：

```
<project-path>/.agent/skills/plugin-guide/SKILL.md
```

如该文件不存在，检查 `<project-path>/skills/plugin-guide/SKILL.md`。都不存在时，按以下最小规则写代码：
- `import { capabilityClient } from '@lark-apaas/client-toolkit'`
- `outputMode = unary` → `capabilityClient.load(id).call(actionKey, input)`
- `outputMode = stream` → `capabilityClient.load(id).callStream(actionKey, input)`

技术栈 Skill 按项目类型不同：
- **Design / Modern 应用**（纯前端）→ Skill 中仅 `capabilityClient`，代码放 `<project-path>/client/`
- **全栈应用**（NestJS + React）→ Skill 中含 `capabilityClient` + `CapabilityService`，Client 代码放 `<project-path>/client/`，Server 代码放 `<project-path>/server/`
