# apps observability

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../../lark-shared/SKILL.md)（认证 / 全局参数 / 安全）。

查询妙搭应用的线上运行观测和产品访问分析。所有 observability 命令只支持 `--env online`；省略 `--env` 时默认就是 online，传 dev 或其他环境是不支持的。

## 命令选择

- 日志检索：用 `+log-list` 搜索日志，用 `+log-get` 按 log ID 取单条日志。
- 前端 ERROR 日志详情：`+log-get` 可能补充 `source_stack`；没有独立的 source-stack 命令。
- Trace 检索：用 `+trace-list` 搜索 trace，用 `+trace-get` 按 trace ID 取详情。
- 运行时指标：请求数、错误、延迟、CPU、memory 用 `+metric-query`。
- 产品分析：PV、UV、访问量这类业务访问分析用 `+analytics-query`，不要放到 runtime metric 里混查。

## 示例

```bash
lark-cli apps +log-list --app-id <app_id> --level error --keyword timeout --since 1h
lark-cli apps +log-get --app-id <app_id> --log-id <log_id>
lark-cli apps +trace-list --app-id <app_id> --trace-id <trace_id>
lark-cli apps +trace-get --app-id <app_id> --trace-id <trace_id>
lark-cli apps +metric-query --app-id <app_id> --metric requests --series total --since 1d
lark-cli apps +metric-query --app-id <app_id> --metric latency --series p99 --since 1d
lark-cli apps +metric-query --app-id <app_id> --metric cpu --since 1h
lark-cli apps +metric-query --app-id <app_id> --metric memory --since 1h
lark-cli apps +analytics-query --app-id <app_id> --analytics users --series active-users --granularity day
lark-cli apps +analytics-query --app-id <app_id> --analytics page-view --granularity day
```

## 使用边界

- 如果用户问“接口慢、报错多、CPU/内存高”，优先走 `+metric-query`。
- 如果用户问“页面访问量、PV、UV、活跃用户”，优先走 `+analytics-query`。
- 如果用户已有 `trace_id` 或 `log_id`，直接用对应 get 命令；不知道 ID 时先 list。
