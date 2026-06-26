# apps +plugin-install

安装插件包到项目。运行时命令事实以 `lark-cli apps +plugin-install --help` 为准。

## 何时用

用户要接入 AI 能力或飞书平台能力，需要先安装对应的插件包。安装后才能创建插件实例。

**判断规则**：
1. AI 模型服务能力（文本生成、图片理解、语音识别等）必须通过插件接入，禁止自行编写替代实现。
2. 飞书平台能力（操作多维表格、发送消息等）优先查看是否有对应插件，插件不支持时再考虑自行通过飞书 OpenAPI 实现。

**前置步骤**：安装前先读仓库 Skill `<project-path>/.agents/skills/plugin-guide/SKILL.md`，获取插件目录、Schema 规则、实例 CRUD、调用代码生成等完整指引。

**插件包 ≠ npm 包**：插件包写入 `actionPlugins`，npm 写入 `dependencies`，两套独立机制。禁止用 `npm install` 代替本命令。

## 命令骨架

- `--name <key>`：插件包 key（从仓库 Skill 的「AI 插件目录」获取）。不传则批量安装 `actionPlugins` 中声明的所有插件。
- `--version <ver>`：指定版本（如 `1.0.0`）。不传则安装最新版。

在项目根目录下运行（和 npm 一样，无需指定路径）。

## 示例

```bash
# 安装最新版
lark-cli apps +plugin-install --name <plugin-key>

# 安装指定版本
lark-cli apps +plugin-install --name <plugin-key> --version 1.0.0

# 批量安装已声明的所有插件
lark-cli apps +plugin-install
```

## 输出契约

- 已安装同版本会跳过（status=already_installed）。
- 失败时 hint 指示原因（网络/版本不存在/package.json 缺失）。
