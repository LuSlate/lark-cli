# Update 链路 — 修改插件实例

修改已有实例的 name、formValue、paramsSchema。关键点：改 schema 可能影响已有调用代码。

## 流程

```
Step 1: +plugin-instance-get --id <id> → 查看现状
Step 2: 读 plugin-instance-schema.md + 设计修改方案
Step 3: +plugin-instance-update --id <id> --form-value @file [--params-schema @file] [--name <n>]
Step 4: 校验通过？ → 否：走 plugin-retry-protocol.md（max 3 次）
Step 5: paramsSchema 变化？
         ├── 不变 → 完成
         └── 变化 → 扫描代码引用 → 读 plugin-instance-call.md → 改代码
```

## Step 1 — 查看现状

```bash
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

确认当前的 pluginKey、paramsSchema、formValue，理解要改什么。

## Step 2 — 设计修改方案

**必读**：[`plugin-instance-schema.md`](plugin-instance-schema.md)

同时读取插件 manifest 确认 form.schema 约束：
```bash
cat <project-path>/node_modules/<pluginKey>/manifest.json
```

## Step 3 — 执行更新

```bash
# 只改名
lark-cli apps +plugin-instance-update --id <id> --name "新名称" --project-path <path>

# 改 formValue
lark-cli apps +plugin-instance-update --id <id> --form-value '{"prompt":"新 prompt {{input.text}}"}' --project-path <path>

# 同时改 formValue + paramsSchema
lark-cli apps +plugin-instance-update --id <id> \
  --form-value @form.json --params-schema @schema.json --project-path <path>
```

CLI 自动保留不可变字段（id / pluginKey / pluginVersion / createdAt），只更新你传入的字段 + updatedAt。

## Step 4 — 校验失败处理

同 Create 链路，按 [`plugin-retry-protocol.md`](plugin-retry-protocol.md) 处理。

## Step 5 — paramsSchema 变化时更新代码

判断 paramsSchema 是否变化（加/改/删了 properties）：

**加/改字段** → 调用方需要传新参数：
1. 读 manifest + 更新后的 capability JSON
2. `grep -rn "load('${id}')" <project-path>/` 找到代码引用
3. 按 [`plugin-instance-call.md`](plugin-instance-call.md) 更新调用代码中的 input 参数

**删字段** → 调用方不再需要传该参数：
1. 同上找到引用
2. 移除已删除参数的传入
3. 检查是否有上游依赖该参数的逻辑需要清理

**未变化** → 无需改代码，直接完成。
