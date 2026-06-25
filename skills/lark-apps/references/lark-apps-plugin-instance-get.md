# apps +plugin-instance-get

查询单个插件实例的完整配置。运行时命令事实以 `lark-cli apps +plugin-instance-get --help` 为准。

## 何时用

需要查看某个插件实例的当前 paramsSchema、formValue 等配置时。也用于生成调用代码前获取实例信息。

## 命令骨架

- `--id`：实例 ID。
- `--project-path`：妙搭应用根目录。

## 示例

```bash
lark-cli apps +plugin-instance-get --id task-text-summary --project-path ./my-app --format json
```

## 输出契约

- 返回实例的完整 JSON 配置（id、pluginKey、pluginVersion、name、description、paramsSchema、formValue 等）。
- 实例不存在时返回 `instance not found`。
