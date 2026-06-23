
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
