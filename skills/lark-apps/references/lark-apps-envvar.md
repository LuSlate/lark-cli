# apps envvar

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md)（认证 / 全局参数 / 安全）。

管理妙搭应用环境变量。查看用 `+envvar-list`，设置用 `+envvar-set`，删除用 `+envvar-delete`。没有单变量 get 命令；要确认某个 key 是否存在，使用 list 后用 `--jq` 过滤。

## 查看

`+envvar-list` 默认查 dev，且默认不返回 value。只有显式传 `--include-values` 后，响应中才可能出现变量值；不要在公开日志里展示带值输出。

```bash
lark-cli apps +envvar-list --app-id <app_id>
lark-cli apps +envvar-list --app-id <app_id> --env online
lark-cli apps +envvar-list --app-id <app_id> --include-values --jq '.data.items[] | select(.key == "FOO")'
```

## 设置

dev 环境设置不需要 `--yes`。设置 online 环境需要人类确认并显式传 `--yes`；`--dry-run` 可用于预览请求且不需要 `--yes`。变量值支持直接传 `<value>`，也支持 `@file` 或 stdin 输入。

```bash
lark-cli apps +envvar-set --app-id <app_id> --key FOO --value <value>
lark-cli apps +envvar-set --app-id <app_id> --key FOO --value @./secret.txt
lark-cli apps +envvar-set --app-id <app_id> --env online --key FOO --value <value> --dry-run
lark-cli apps +envvar-set --app-id <app_id> --env online --key FOO --value <value> --yes
```

## 删除

`+envvar-delete` 是 high-risk-write。尊重 exit 10 confirmation protocol：先让用户确认要删除哪些 key，再传 `--yes`。不要自动补 `--yes`。

```bash
lark-cli apps +envvar-delete --app-id <app_id> --key FOO --dry-run
lark-cli apps +envvar-delete --app-id <app_id> --key FOO --yes
lark-cli apps +envvar-delete --app-id <app_id> --env online --key FOO --yes
```

## 反模式

- 不要把 `+env-pull` 当成环境变量管理命令；它只是刷新本地 `.env.local` 的兜底工具。
- 不要为了看一个变量臆造名为 envvar-get 的 apps shortcut；用 `+envvar-list --include-values` 加 `--jq`。
- 不要把真实 secret 写进示例或对话输出；需要示例时使用 `<value>`、`@file` 或 stdin。
