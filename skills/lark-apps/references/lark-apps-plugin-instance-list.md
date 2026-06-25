# apps +plugin-instance-list

列出当前项目的所有插件实例。运行时命令事实以 `lark-cli apps +plugin-instance-list --help` 为准。

## 何时用

查看项目中已创建了哪些插件实例，判断是否需要新建或可以复用已有实例。

## 命令骨架

- `--summary`：仅输出 id + name（可选）。
- `--project-path`：妙搭应用根目录。

## 示例

```bash
lark-cli apps +plugin-instance-list --project-path ./my-app --format json

# 仅看 id 和 name
lark-cli apps +plugin-instance-list --summary --project-path ./my-app
```

## 输出契约

- 返回所有实例的配置列表。`--summary` 时仅返回 id 和 name。
