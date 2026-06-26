# Lark / Feishu CLI — Claude Code 插件

把 [larksuite/cli](https://github.com/larksuite/cli) 的 26 个 AI Agent 技能作为 Claude Code 插件分发。本 fork 通过 GitHub Action 每日自动同步上游 `skills/`，**上游更新 → 插件可更新**。

## 前置：lark-cli 二进制（已自动处理）

技能调用 `lark-cli` 命令。插件带了一个 `SessionStart` 钩子：检测到二进制缺失时，会**后台自动安装**（`npm install -g @larksuite/cli`，只装二进制、不重复装 skills）。装好后需用 `lark-cli` 登录鉴权（见 `lark-shared` 技能）。

钩子失败或想手动装，运行：

```bash
npx @larksuite/cli@latest install
```

## 安装插件

```
/plugin marketplace add LuSlate/lark-cli
/plugin install lark-cli@larksuite
```

## 更新

```
/plugin marketplace update larksuite   # 刷新市场目录
/plugin update lark-cli@larksuite       # 拉取最新技能
```

插件未固定 `version`，版本=git commit SHA，所以每次自动同步产生新 commit 后都能更新到。

## 同步机制

`.github/workflows/sync-skills-from-upstream.yml` 每天把上游 `skills/` 镜像过来。也可在 Actions 页手动 `Run workflow`。

> 注：本 fork 仅保证 `skills/` 跟随上游；其余 Go 源码不随同步刷新（插件运行时不依赖，二进制由上述 npx 命令单独安装）。
