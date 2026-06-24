# 插件实例 CRUD

插件实例的创建、更新、删除、查询命令参考。详细的 Schema 规则、CRUD 流程指引、校验重试协议请读取仓库 Skill：`<project-path>/.agents/skills/plugin-guide/SKILL.md`。

---

## Create — 创建插件实例

```bash
lark-cli apps +plugin-instance-create \
  --id <语义化ID> \
  --plugin <key@version> \
  --name <名称> \
  --description <描述> \
  --form-value <json|@file> \
  --params-schema <json|@file> \
  --project-path <path> \
  --format json
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--id` | 是 | 语义化 ID，小写+短横线，如 `task-text-summary` |
| `--plugin` | 是 | 插件包 key@version，如 `@official-plugins/ai-text-generate@1.0.0` |
| `--name` | 是 | 实例显示名称 |
| `--description` | 否 | 实例描述 |
| `--form-value` | 是 | formValue JSON，或 `@file.json` 从文件读取 |
| `--params-schema` | 是 | paramsSchema JSON，或 `@file.json` 从文件读取 |
| `--project-path` | 是 | 妙搭应用根目录 |
| `--force` | 否 | 覆盖已存在的同 ID 实例 |

校验失败时返回 `ok: false` + `error.hint`，按仓库 Skill 中的重试协议处理（max 3 次）。

---

## Update — 更新插件实例

```bash
lark-cli apps +plugin-instance-update \
  --id <id> \
  [--name <新名称>] \
  [--form-value <json|@file>] \
  [--params-schema <json|@file>] \
  --project-path <path> \
  --format json
```

只传需要修改的字段，CLI 自动保留不可变字段（id / pluginKey / pluginVersion / createdAt）。

---

## Delete — 删除插件实例

```bash
lark-cli apps +plugin-instance-delete --id <id> --project-path <path> --format json
```

幂等操作，文件不存在也返回 `deleted: true`。删除前建议先扫描代码引用：

```bash
grep -rn "load('${id}')" <project-path>/client/ <project-path>/server/
```

---

## Get — 查询

| 查什么 | 命令 |
|--------|------|
| 已声明的插件包及安装状态 | `+plugin-list --project-path <path>` |
| 所有实例概览 | `+plugin-instance-list --project-path <path>` |
| 所有实例（仅 id+name） | `+plugin-instance-list --summary --project-path <path>` |
| 单个实例完整配置 | `+plugin-instance-get --id <id> --project-path <path>` |
| 插件的 actions/schema | `cat <project-path>/node_modules/<pluginKey>/manifest.json` |

所有命令支持 `--format json` 和 `--dry-run`。
