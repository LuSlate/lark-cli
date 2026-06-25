# apps +plugin-instance-create

创建插件实例。运行时命令事实以 `lark-cli apps +plugin-instance-create --help` 为准。

## 前置条件

本命令的 `--plugin`、`--form-value`、`--params-schema` 参数取值均依赖仓库 Skill 中的规则。未读 `<project-path>/.agents/skills/plugin-guide/SKILL.md` 直接执行会导致参数错误。

## 何时用

用户要接入某个 AI 能力或飞书平台能力，插件包已安装后，创建对应的插件实例。

## 命令骨架

- `--id`：语义化 ID，小写+短横线。
- `--plugin`：插件包 key（从仓库 Skill 的「AI 插件目录」获取）。
- `--name`：实例显示名称。
- `--description`：实例描述（可选）。
- `--form-value`：formValue JSON，或 `@file.json` 从文件读取。
- `--params-schema`：paramsSchema JSON，或 `@file.json` 从文件读取。
- `--project-path`：妙搭应用根目录。
- `--force`：覆盖已存在的同 ID 实例（可选）。

## 示例

```bash
# plugin-key、formValue、paramsSchema 的设计规则见仓库 Skill
lark-cli apps +plugin-instance-create \
  --id <语义化ID> \
  --plugin <plugin-key> \
  --name <名称> \
  --form-value <json|@file> \
  --params-schema <json|@file> \
  --project-path <path> --format json

# 大 JSON 场景用 @file 传入
lark-cli apps +plugin-instance-create \
  --id <语义化ID> \
  --plugin <plugin-key> \
  --name <名称> \
  --form-value @form.json --params-schema @schema.json \
  --project-path <path> --format json
```

## 输出契约

- 成功返回 `ok: true` + 创建的实例配置。
- 校验失败返回 `ok: false` + `error.hint`，按仓库 Skill 中的重试协议处理（max 3 次，create 重试加 `--force`）。

## Agent 规则

- 创建前必须先 `+plugin-install` 安装插件包。
- formValue / paramsSchema 的设计规则在仓库 Skill 中，不要凭记忆猜测。
- 创建成功后，读 manifest + capability JSON，再按仓库 Skill 生成调用代码。
