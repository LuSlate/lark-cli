# apps +plugin-uninstall

卸载插件包。运行时命令事实以 `lark-cli apps +plugin-uninstall --help` 为准。

## 何时用

用户不再需要某个插件能力时，卸载对应的插件包。卸载前应先删除该插件的所有实例。

## 命令骨架

- `--name <key>`：要卸载的插件包 key。
- `--project-path`：妙搭应用根目录。

## 示例

```bash
lark-cli apps +plugin-uninstall --name <plugin-key> --project-path <path>
```

## 输出契约

- 删除 `node_modules/{key}` + 移除 `actionPlugins` 条目。
