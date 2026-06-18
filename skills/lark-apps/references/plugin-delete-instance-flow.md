# Delete 链路 — 删除插件实例

删除实例前必须先清理代码引用，避免运行时报错。

## 流程

```
Step 1: +plugin-instance-get --id <id> → 确认实例存在
Step 2: 扫描代码引用
Step 3: 有引用？
         ├── 有 → 读 plugin-instance-call.md → 清理调用代码
         └── 无 → 直接删除
Step 4: +plugin-instance-delete --id <id>
Step 5: 确认清理完成
```

## Step 1 — 确认实例存在

```bash
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

实例不存在 → 无需删除，直接告知用户。

## Step 2 — 扫描代码引用

```bash
grep -rn "load('${id}')\|load(\"${id}\")" <project-path>/client/ <project-path>/server/ <project-path>/shared/
```

查找所有使用 `capabilityClient.load('<id>')` 或 `capabilityService.load('<id>')` 的位置。

## Step 3 — 清理代码引用

如果有引用：
1. 移除或替换调用代码（视业务逻辑决定是删除功能还是换用其他实例）
2. 清理相关的 import、类型定义、状态变量
3. 如果该实例的结果被持久化到数据库字段，考虑是否需要清理字段或保留历史数据

## Step 4 — 删除实例

```bash
lark-cli apps +plugin-instance-delete --id <id> --project-path <path> --format json
```

删除是幂等的：文件不存在也返回 `deleted: true`，不报错。

## Step 5 — 确认清理

```bash
# 确认文件已删除
lark-cli apps +plugin-instance-get --id <id> --project-path <path>
# 应返回 "instance not found"

# 确认代码无残留引用
grep -rn "${id}" <project-path>/client/ <project-path>/server/ <project-path>/shared/
```
