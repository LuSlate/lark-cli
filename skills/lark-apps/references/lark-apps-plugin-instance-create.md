# apps +plugin-instance-create

创建插件实例。运行时命令事实以 `lark-cli apps +plugin-instance-create --help` 为准。

## 何时用

用户要接入某个 AI 能力或飞书平台能力，插件包已安装后，创建对应的插件实例。创建前必须读取仓库 Skill 了解 Schema 规则：`<project-path>/.agents/skills/plugin-guide/SKILL.md`。

## 命令骨架

- `--id`：语义化 ID，小写+短横线，如 `task-text-summary`。
- `--plugin`：插件包 key，如 `@official-plugins/ai-text-generate`。
- `--name`：实例显示名称。
- `--description`：实例描述（可选）。
- `--form-value`：formValue JSON，或 `@file.json` 从文件读取。
- `--params-schema`：paramsSchema JSON，或 `@file.json` 从文件读取。
- `--project-path`：妙搭应用根目录。
- `--force`：覆盖已存在的同 ID 实例（可选）。

## 示例

```bash
lark-cli apps +plugin-instance-create \
  --id task-text-summary \
  --plugin @official-plugins/ai-text-generate \
  --name "任务摘要生成" \
  --form-value '{"prompt":"请总结以下任务内容：\n{{input.task_content}}"}' \
  --params-schema '{"type":"object","properties":{"task_content":{"type":"string","description":"任务详情文本"}},"required":["task_content"]}' \
  --project-path ./my-app --format json

# 大 JSON 场景用 @file 传入
lark-cli apps +plugin-instance-create \
  --id task-text-summary \
  --plugin @official-plugins/ai-text-generate \
  --name "任务摘要生成" \
  --form-value @form.json --params-schema @schema.json \
  --project-path ./my-app --format json
```

## 输出契约

- 成功返回 `ok: true` + 创建的实例配置。
- 校验失败返回 `ok: false` + `error.hint`，按仓库 Skill 中的重试协议处理（max 3 次，create 重试加 `--force`）。

## Agent 规则

- 创建前必须先 `+plugin-install` 安装插件包。
- formValue / paramsSchema 的设计规则在仓库 Skill 中，不要凭记忆猜测。
- 创建成功后，读 manifest + capability JSON，再按仓库 Skill 生成调用代码。
