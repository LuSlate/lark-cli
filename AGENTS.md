# AGENTS.md

## Goal (pick one per PR)

- Make CLI better: improve UX, error messages, help text, flags, and output clarity.
- Improve reliability: fix bugs, edge cases, and regressions with tests.
- Improve developer velocity: simplify code paths, reduce complexity, keep behavior explicit.
- Improve quality gates: strengthen tests/lint/checks without adding heavy process.

## Build & Test

```bash
make build          # Build (runs fetch_meta first)
make unit-test      # Required before PR (runs with -race where supported, e.g. amd64/arm64)
make test           # Full: vet + unit + integration
```

## Notification Opt-Outs

`lark-cli` emits two notice types into JSON envelope `_notice` to nudge AI agents toward fixes:

- `_notice.update` — a newer binary is available on npm
- `_notice.skills` — locally installed skills are out of sync with the running binary

To suppress them in non-CI scripts (CI envs are auto-skipped):

| Env var | Effect |
|---------|--------|
| `LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1` | Suppress `_notice.update` |
| `LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1` | Suppress `_notice.skills` |

Both notices recommend the same fix command: `lark-cli update`. The skills notice's `current` field is `""` when skills have never been synced (cold start) and a version string when synced for an older binary (drift).

## Pre-PR Checks (match CI gates)

1. `make unit-test`
2. `go vet ./...`
3. `gofmt -l .` — must produce no output
4. `go mod tidy` — must not change `go.mod`/`go.sum`
5. `go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@v2.1.6 run --new-from-rev=origin/main`
6. If dependencies changed: `go run github.com/google/go-licenses/v2@v2.0.1 check ./... --disallowed_types=forbidden,restricted,reciprocal,unknown`

## Commit & PR

- Conventional Commits in English: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`
- PR title in the same format. Fill `.github/pull_request_template.md` completely.
- Never commit secrets, tokens, or internal sensitive data.

## Source Layout

| Path | What it does |
|------|-------------|
| `cmd/root.go` | Entry point, command registration, strict mode pruning |
| `cmd/profile/` | Multi-profile management (add/list/use/rename/remove) |
| `cmd/config/` | Config init, show, strict-mode |
| `cmd/service/` | Auto-registered API commands from embedded metadata |
| `shortcuts/common/runner.go` | Shortcut execution pipeline, Flag.Input (@file/stdin) resolution |
| `shortcuts/` | Domain-specific shortcut implementations |
| `internal/cmdutil/factory.go` | Factory pattern — identity resolution, credential, config |
| `internal/cmdutil/factory_default.go` | Production factory wiring |
| `internal/credential/` | Credential provider chain (extension → default) |
| `extension/credential/` | Plugin-facing credential interfaces and env provider |
| `internal/client/client.go` | APIClient: DoSDKRequest, DoStream |
| `internal/core/config.go` | Multi-profile config loading/saving |
| `internal/vfs/` | Filesystem abstraction (use `vfs.*` instead of `os.*`) |
| `internal/validate/path.go` | Path safety validation |

## Who Uses This CLI

This CLI's primary consumers include AI agents (Claude Code, Cursor, Gemini CLI). Your code is read by machines — error messages, output format, and flag design all directly affect agent success rates.

The one rule to internalize: **every error message you write will be parsed by an AI to decide its next action.** Make errors structured, actionable, and specific.

## Code Conventions

### Structured errors in commands

Command-facing failures must be typed `errs.*` errors — never the legacy `output.Err*` helpers and never a final bare `fmt.Errorf`. AI agents parse the stderr envelope's `type` / `subtype` / `param` / `hint` fields to decide their next action; the full taxonomy lives in `errs/ERROR_CONTRACT.md`.

Picking a constructor:

| Failure | Constructor |
|---------|-------------|
| User flag/arg fails validation | `errs.NewValidationError(errs.SubtypeInvalidArgument, ...).WithParam("--flag")` |
| Valid request, wrong system state | `errs.NewValidationError(errs.SubtypeFailedPrecondition, ...).WithHint(...)` |
| Lark API returned `code != 0` | `runtime.CallAPITyped` (shortcuts) / `errclass.BuildAPIError` (raw responses) — never hand-build |
| Network / transport failure | `errs.NewNetworkError(errs.SubtypeNetworkTransport, ...)` |
| Local file I/O failure | `errs.NewInternalError(errs.SubtypeFileIO, ...)` — validate the path first (`validate.SafeInputPath` / `SafeOutputPath`) and use `vfs.*` |
| Unclassified lower-layer error as final | `errs.NewInternalError(errs.SubtypeUnknown, ...).WithCause(err)` |
| Lower layer already returned a typed error | pass it through unchanged — re-wrapping downgrades its classification |

Signatures that are easy to guess wrong:

- `runtime.CallAPITyped(method, url string, params map[string]interface{}, data interface{}) (map[string]interface{}, error)` — it performs the HTTP request itself and classifies `code != 0` into a typed error; just return the error it gives you.
- Typed pass-through check: `if _, ok := errs.ProblemOf(err); ok { return err }` — `ProblemOf` returns `(*errs.Problem, bool)`, not a nilable pointer.
- `.WithParam` exists only on `*errs.ValidationError`. `InternalError` / `NetworkError` have no param field — file or endpoint context goes in the message or `.WithHint(...)`.

`forbidigo` + `lint/errscontract` reject the legacy `output.Err*` helpers, bare final `fmt.Errorf` / `errors.New`, and legacy envelope literals on migrated paths. Beyond what lint catches, three authoring conventions apply:

- Preserve the underlying error with `.WithCause(err)` so `errors.Is` / `errors.Unwrap` keep working.
- `param` names only the user input that actually failed. Recovery guidance goes in `.WithHint(...)`; machine-readable recovery fields (`missing_scopes`, `log_id`) carry server/system ground truth only — never caller-side guesses.
- Error-path tests assert typed metadata via `errs.ProblemOf` (`category` / `subtype` / `param`) and cause preservation, not message substrings alone.

### stdout is data, stderr is everything else

Program output (JSON envelopes) goes to stdout. Progress, warnings, hints go to stderr. Mixing them corrupts pipe chains.

### Use `vfs.*` instead of `os.*`

All filesystem access goes through `internal/vfs`. This enables test mocking.

### Validate paths before reading

CLI arguments are untrusted (they come from AI agents). Call `validate.SafeInputPath` before any file I/O.

### Tests

- Every behavior change needs a test alongside the change.
- `cmdutil.TestFactory(t, config)` for test factories.
- `t.Setenv("LARKSUITE_CLI_CONFIG_DIR", t.TempDir())` to isolate config state.

### E2E Testing

**Dry-run E2E (required for every shortcut change)**
- Validates request structure without calling real APIs
- Place in `tests/cli_e2e/dryrun/` or the corresponding domain directory
- Set env vars `LARKSUITE_CLI_APP_ID`/`APP_SECRET`/`BRAND`, use `--dry-run`, assert method/URL/params
- No secrets needed — runs on fork PRs
- Explore correct params with `lark-cli <domain> --help` and `lark-cli schema` first

**Live E2E (required for new flows or behavior changes)**
- Validates real API round-trips
- Place in `tests/cli_e2e/<domain>/`
- Must be self-contained: create -> use -> cleanup
- Needs bot credentials (CI secrets, skipped on fork PRs)
- Reference: `tests/cli_e2e/task/task_status_workflow_test.go`

| Change | Dry-run E2E | Live E2E |
|--------|:-----------:|:--------:|
| New shortcut | Required | Required |
| Modify shortcut flags/params | Required | If behavior changes |
| Shortcut bug fix | Required | If regression risk |
| Internal refactor (no shortcut impact) | Not needed | Not needed |



## CCM Harness Skill Routing (v2)

When the user's request matches one of these patterns, invoke the corresponding `/ccm-harness:*` skill via the Skill tool. Skills include multi-step workflows, gates, and quality checks that produce more reliable results than ad-hoc answers. When in doubt, invoke the skill — a false positive is cheaper than a false negative.

### 主链路（spec → idl → dev → release）

| 用户表达 | Skill |
|---------|-------|
| "新需求 / 这是个新功能 / 开始一个 req / 写 spec / 起 spec / PRD 来了 / 把 PRD 转 spec / 改 spec / 微调 spec / spec 局部更新 / spec 加一个字段" | `/ccm-harness:draft-spec <req-id> [<arg2>] [--force]`（Phase 0 路由器自动决定 init / generate / update capability）|
| "review spec / 看 spec / 评审 spec / spec 评审" | `/ccm-harness:spec-review <req-id>` |
| "生成 thrift / 起 idl / 把 spec 转 thrift" | `/ccm-harness:draft-idl` |
| "推 thrift / 落 contract / Frozen Spec / codegen / 生成框架代码" | `/ccm-harness:codegen-idl <req-id>` |
| "实现 spec / 写后端 / 后端开发 / 实现这个功能" | `/ccm-harness:backend-dev <req-id>` |
| "前端怎么改 / 写前端 / 前端开发 / 前端编码" | `/ccm-harness:frontend-coding <req-id>` |
| "部署 BOE / 上 PPE / 部署到 feature 环境" | `/ccm-harness:deploy <req-id>` |
| "提 release / 上线 / 发布 / 走 PRE-GRAY-ONLINE" | `/ccm-harness:release <req-id>` |
| "触发打包 / build / 起 SCM 编译" | `/ccm-harness:build <repo or psm>` |

### 守护与诊断

| 用户表达 | Skill |
|---------|-------|
| "工作流到哪一步了 / 下一步咋走 / 我迷路了" | `/ccm-harness:doctor` |
| "调试 / debug / 这个 bug 怎么排" | `/ccm-harness:debug` |
| "查 CI 失败 / CI 跑挂了 / pipeline 红了" | `/ccm-harness:check-ci-failure <mr>` |
| "检查实现是否符合 spec / 蓝图对比" | `/ccm-harness:check-impl-gap` |
| "spec 跟代码飘了吗 / drift 检查" | `/ccm-harness:spec-review <req-id> --mode drift` |
| "Hub 知识跟代码一致吗" | `/ccm-harness:check-knowledge-consistency` |
| "代码 review / 看 MR / cr 一下" | `/ccm-harness:code-review <mr>` |
| "设计 review / 看技术方案" | `/ccm-harness:design-review <doc>` |

### 工程辅助

| 用户表达 | Skill |
|---------|-------|
| "通知 reviewer / 发 review 卡片" | `/ccm-harness:notify-reviewer <mr>` |
| "自动修 MR / 按 review 改" | `/ccm-harness:autofix-mr <mr>` |
| "生成测试用例 / 起 case / 筛选可执行 case / E2E 用例 / Playwright 脚本 / 自动化验收" | `/ccm-harness:test`（路由到 `ccm-e2e-check -> exec-e2e`） |
| "查 idl / 看 thrift 定义" | `/ccm-harness:lookup-idl <psm>` |
| "看仓库最近改了啥 / 仓库脉搏" | `/ccm-harness:pulse` |

### 元能力（Skill / Prompt 研发）

| 用户表达 | Skill |
|---------|-------|
| "起一个新 skill / 设计 skill" | `/ccm-harness:meta-draft-skill` |
| "做评测集 / 给 skill 出评测数据" | `/ccm-harness:meta-build-evalset` |
| "跑评测 / Fornax 实验" | `/ccm-harness:meta-run-eval` |
| "优化 skill / skill 反馈优化" | `/ccm-harness:meta-optimize-skill` |

### 环境与配置

| 用户表达 | Skill |
|---------|-------|
| "升级 ccm-harness / 更新插件" | `/ccm-harness:upgrade` |
| "看遥测 / 最近的反馈" | `/ccm-harness:show-telemetry` |
| "清遥测 / 重置 telemetry" | `/ccm-harness:clear-telemetry` |
| "上报问题 / 提 issue" | `/ccm-harness:report-issue` |
| "看本地教训 / project learnings / 我们踩过啥" | `/ccm-harness:learn` |
| "反馈 / 评分这次 skill" | `/ccm-harness:feedback` |

### 使用提示

- **入口**：新需求**必从** `/ccm-harness:draft-spec <req-id>` 开始（Phase 0 路由器自动决定建目录 / 带 PRD 一气呵成）。
- **不跳步**：spec → idl → dev → release 是流水线，不是菜单——按顺序推进，反向走需要 `/ccm-harness:draft-spec <req-id> "<change-desc>"` 局部修（路由进 update capability）。
- **横切**：任何阶段发现 spec 要局部改 → `/ccm-harness:draft-spec <req-id> "<change-desc>"`；想检测漂移 → `/ccm-harness:spec-review <req-id> --mode drift`；CI 红 → `/ccm-harness:check-ci-failure`；迷路 → `/ccm-harness:doctor`。

完整流程文档：`docs/user-guide/workflow.md`
