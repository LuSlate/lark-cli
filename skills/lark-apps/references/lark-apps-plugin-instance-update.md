# apps +plugin-instance-update

更新已有插件实例的配置。运行时命令事实以 `lark-cli apps +plugin-instance-update --help` 为准。

## 前置条件

`--form-value`、`--params-schema` 的设计规则在仓库 Skill 中。未读 `<project-path>/.agents/skills/plugin-guide/SKILL.md` 直接修改会导致参数错误。

## 何时用

用户要修改已有插件实例的 name、formValue 或 paramsSchema（如改 prompt、换参数）。

## 命令骨架

- `--id`：要更新的实例 ID。
- `--name`：新名称（可选）。
- `--form-value`：新 formValue JSON 或 `@file.json`（可选）。
- `--params-schema`：新 paramsSchema JSON 或 `@file.json`（可选）。
- `--project-path`：妙搭应用根目录。

只传需要修改的字段，CLI 自动保留不可变字段（id / pluginKey / pluginVersion / createdAt）。

## 示例

```bash
# 只改名
lark-cli apps +plugin-instance-update --id <id> --name <新名称> --project-path <path>

# 改 formValue + paramsSchema
lark-cli apps +plugin-instance-update --id <id> \
  --form-value @form.json --params-schema @schema.json \
  --project-path <path> --format json
```

## 输出契约

- 成功返回 `ok: true` + 更新后的实例配置。
- 校验失败返回 `ok: false` + `error.hint`，按仓库 Skill 中的重试协议处理。

## Agent 规则

- paramsSchema 变化时，需扫描代码引用（`grep -rn "load('${id}')" <project-path>/`）并更新调用代码。
