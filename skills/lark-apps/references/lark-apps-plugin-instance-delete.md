# apps +plugin-instance-delete

删除插件实例。运行时命令事实以 `lark-cli apps +plugin-instance-delete --help` 为准。

## 何时用

用户不再需要某个插件实例时删除。删除前应先清理代码中对该实例的引用。

## 命令骨架

- `--id`：要删除的实例 ID。
- `--project-path`：妙搭应用根目录。

## 示例

```bash
# 先扫描代码引用
grep -rn "load('task-text-summary')" ./my-app/client/ ./my-app/server/

# 确认无引用或已清理后删除
lark-cli apps +plugin-instance-delete --id task-text-summary --project-path ./my-app --format json
```

## 输出契约

- 幂等操作，文件不存在也返回 `deleted: true`。
