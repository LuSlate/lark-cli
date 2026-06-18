# Get 链路 — 查询插件信息

查询操作，无副作用。根据查什么路由到不同命令。

## 路由

| 查什么 | 命令 | 示例 |
|--------|------|------|
| 已声明的插件包及安装状态 | `+plugin-list` | `lark-cli apps +plugin-list --project-path <path>` |
| 所有已建的实例（概览） | `+plugin-instance-list` | `lark-cli apps +plugin-instance-list --project-path <path>` |
| 所有已建的实例（仅 id+name） | `+plugin-instance-list --summary` | 同上加 `--summary` |
| 某个实例的完整配置 | `+plugin-instance-get --id <id>` | `lark-cli apps +plugin-instance-get --id <id> --project-path <path>` |
| 插件的 actions / schema | 直接读 manifest | `cat <project-path>/node_modules/<pluginKey>/manifest.json` |

## +plugin-list

列出 package.json `actionPlugins` 中声明的插件包，交叉检查 node_modules 报告安装状态。

```bash
lark-cli apps +plugin-list --project-path <path> --format json
```

返回：
```json
{
  "ok": true,
  "data": {
    "plugins": [
      {"key": "@official-plugins/ai-text-generate", "version": "1.0.0", "status": "installed"},
      {"key": "@official-plugins/ai-translate", "version": "1.0.0", "status": "declared_not_installed"}
    ]
  }
}
```

`declared_not_installed` → 需要 `+plugin-install` 安装。

## +plugin-instance-list

扫描 capabilities 目录下所有 `*.json` 文件。

```bash
lark-cli apps +plugin-instance-list --project-path <path> --format json
```

capabilities 目录不存在时返回空列表（不报错）。`--summary` 只返回 id 和 name。

## +plugin-instance-get

读取单个实例的完整配置（id、pluginKey、pluginVersion、name、description、paramsSchema、formValue、createdAt、updatedAt）。

```bash
lark-cli apps +plugin-instance-get --id <id> --project-path <path> --format json
```

实例不存在 → 返回错误 + hint `list instances with '+plugin-instance-list'`。

## 读取插件源码（写代码前必做）

Agent 需要写调用代码时，不要只靠 instance-get 的输出，还要读插件的 manifest 获取 actions 详情：

```bash
# manifest 包含 actions[].key / inputSchema / outputSchema / outputMode
cat <project-path>/node_modules/<pluginKey>/manifest.json
```

然后按 [`plugin-instance-call.md`](plugin-instance-call.md) 生成调用代码。
