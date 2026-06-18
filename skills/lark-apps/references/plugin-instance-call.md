# 插件实例调用代码编写指南

创建/更新插件实例后，根据本文件生成调用代码。

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
```

若摘录字段缺失，不得进入实现阶段。

## call / callStream 函数签名

```typescript
.call(actionKey: string, input: object)       // 非流式，返回 Promise<output>
.callStream(actionKey: string, input: object)  // 流式，返回 AsyncIterable<chunk>
```

```typescript
// ❌ 错误：把参数 JSON.stringify 后当 actionKey
plugin.call(JSON.stringify({ text: '...' }));
// ❌ 错误：漏掉 actionKey，直接传参数
plugin.call({ text: '...' });
// ✅ 正确：第一个参数是 actionKey 字符串，第二个是 input 对象
plugin.call('textGenerate', { text: '...' });
```

**唯一导入方式**（严禁其他路径）：
```typescript
// ❌ 严禁
import { capabilityClient } from '@lark-apaas/client-capability';
// ✅ 唯一指定
import { capabilityClient } from '@lark-apaas/client-toolkit';
```

---

## 按应用类型选择调用方式

### Design / Modern 应用（appType=3/6，纯前端）

只有 Client 侧调用，无 Server 侧。

| outputMode | 调用方式 |
|------------|---------|
| `unary` | `capabilityClient.load(id).call(actionKey, input)` |
| `stream` | `capabilityClient.load(id).callStream(actionKey, input)` |

### 全栈应用（appType=2，NestJS + React）

有 Client 侧和 Server 侧两条路。

| 优先级 | 场景 | 调用方式 |
|--------|------|---------|
| **首选** | 绝大多数场景 | `capabilityClient.load(id).call()` |
| **首选** | 流式输出场景 | `capabilityClient.load(id).callStream()` |
| **兜底** | Client 侧无法满足时 | `CapabilityService.load(id).call()` |

**何时用 Server 侧**：
1. 涉及敏感凭证（token/secret 不能暴露给前端）
2. 多步骤强事务编排（需要原子性）
3. 触发器/定时任务（无前端上下文）
4. 插件结果需持久化到数据库（调用+落库在同一方法中完成）

> 不涉及持久化，仅即时展示（流式渲染、发消息）→ Client 侧。

---

## Client 侧调用

### 非流式调用（outputMode = "unary"）

```typescript
import { capabilityClient } from '@lark-apaas/client-toolkit';
import { logger } from "@lark-apaas/client-toolkit/logger";

const result = await capabilityClient
  .load('task_text_summary')
  .call('textGenerate', { task_content: '...' });

logger.info(result);
```

### 流式调用（outputMode = "stream"）

```typescript
const streamResult = capabilityClient
  .load('task_text_summary')
  .callStream('textGenerate', { task_content: '...' });

const stream = normalizeStream(streamResult);
let fullContent = '';
for await (const chunk of stream) {
  const delta = readFirstStringField(chunk as Record<string, unknown>, ['content']);
  if (delta) {
    fullContent += delta;
    setContent(fullContent);
  }
}
```

### normalizeStream（必须）

`callStream()` 可能返回 `AsyncIterable<chunk>` 或 `{ output: AsyncIterable<chunk> }`，必须归一化：

```typescript
type AnyRecord = Record<string, unknown>;

function isAsyncIterable(value: unknown): value is AsyncIterable<AnyRecord> {
  return !!value && typeof (value as AnyRecord)[Symbol.asyncIterator] === 'function';
}

function normalizeStream(resultOrStream: unknown): AsyncIterable<AnyRecord> {
  if (isAsyncIterable(resultOrStream)) return resultOrStream;
  if (
    resultOrStream && typeof resultOrStream === 'object' &&
    'output' in (resultOrStream as AnyRecord) &&
    isAsyncIterable((resultOrStream as AnyRecord).output)
  ) {
    return (resultOrStream as AnyRecord).output as AsyncIterable<AnyRecord>;
  }
  throw new Error('Invalid callStream result: cannot find AsyncIterable stream');
}

function readFirstStringField(chunk: AnyRecord, keys: string[]): string {
  for (const key of keys) {
    const value = chunk[key];
    if (typeof value === 'string') return value;
  }
  return '';
}
```

### 流式 chunk 字段速查

chunk 是扁平对象，字段名与 outputSchema 一致。**禁止** `chunk.data?.text`、`chunk.choices[0]` 等非 capabilityClient 格式。

| 插件 | chunk 字段 | 正确写法 | 错误写法 |
|------|-----------|---------|---------|
| ai-text-generate | `content` | `chunk.content` | ~~`chunk.data?.text`~~ |
| ai-translate | `translation` | `chunk.translation` | ~~`chunk.content`~~ |
| ai-text-summary | `summary` | `chunk.summary` | ~~`chunk.content`~~ |
| ai-image-understanding | `content` | `chunk.content` | ~~`chunk.data?.text`~~ |
| ai-search-summary | `content` | `chunk.content` | ~~`chunk.data?.text`~~ |

> 同一应用多页面调用同一插件时，所有页面必须使用一致的 chunk 字段名。

### 多插件并行流式（推荐）

需求涉及多种独立输出（标题、正文、图片等）时，拆分为多个插件并行调用：

```tsx
const handleGenerate = async (keywords: string) => {
  // 封面图（非流式，异步不阻塞）
  capabilityClient.load('cover_generator')
    .call<{ images: string[] }>('textToImage', { keywords })
    .then(res => res?.images?.[0] && setCoverUrl(res.images[0]))
    .catch(err => logger.warn('封面生成失败', err));

  // 标题（非流式）
  const titleResult = await capabilityClient
    .load('title_generator')
    .call<{ content: string }>('textGenerate', { keywords });
  setTitle(titleResult?.content || '');

  // 正文（流式）
  const contentStream = capabilityClient
    .load('content_generator')
    .callStream<{ content: string }>('textGenerate', { keywords });
  const stream = normalizeStream(contentStream);
  let fullContent = '';
  for await (const chunk of stream) {
    const delta = readFirstStringField(chunk as Record<string, unknown>, ['content']);
    if (delta) { fullContent += delta; setContent(fullContent); }
  }
};
```

---

## Server 侧调用（仅全栈应用）

### NestJS 注入

```typescript
import { Injectable, Inject, Logger } from '@nestjs/common';
import { CapabilityService } from '@lark-apaas/fullstack-nestjs-core';

@Injectable()
export class XxxService {
  private readonly logger = new Logger(XxxService.name);
  constructor(@Inject() private readonly capabilityService: CapabilityService) {}

  async callPlugin(input: Record<string, unknown>) {
    try {
      return await this.capabilityService
        .load('<pluginInstanceId>')
        .call('<actionKey>', input);
    } catch (error) {
      this.logger.error('pluginInstance call failed', {
        pluginInstanceId: '<id>',
        actionKey: '<key>',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }
}
```

### Server 侧编排原则

- PluginInstance 调用属于外部依赖 / side-effect
- 除非业务要求强一致性，默认不阻塞主业务流程
- 推荐异步触发 + catch 兜底：

```typescript
this.somePluginSideEffect(input).catch(error => {
  this.logger.warn('PluginInstance side-effect failed, ignored', {
    error: error instanceof Error ? error.message : 'Unknown error'
  });
});
```

---

## 持久化决策

以下任一条件成立时，插件结果**必须**保存到数据库：
1. 结果会在其他页面展示
2. 结果供后续功能消费
3. 用户再次访问时需要看到结果
4. 结果对应数据库中已有字段

仅一次性即时展示时可不持久化。

- 前端调用后需持久化 → 流式结束后调已有 CRUD 接口保存
- 复用已有 create/update 接口，不要为插件结果单独建 API

## 失败日志最小集

```typescript
{ pluginInstanceId, actionKey, outputMode, inputKeys, error }
```
