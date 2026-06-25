# apps +plugin-install

安装插件包到项目。运行时命令事实以 `lark-cli apps +plugin-install --help` 为准。

## 何时用

用户要接入 AI 能力或飞书平台能力，需要先安装对应的插件包。安装后才能创建插件实例。具体有哪些可用插件、该选哪个，读取仓库 Skill：`<project-path>/.agents/skills/plugin-guide/SKILL.md`。

**插件包 ≠ npm 包**：插件包写入 `actionPlugins`，npm 写入 `dependencies`，两套独立机制。禁止用 `npm install` 代替本命令。

## 命令骨架

- `--name <key>`：插件包 key（从仓库 Skill 的「AI 插件目录」获取）。不传则批量安装 `actionPlugins` 中声明的所有插件。
- `--project-path`：妙搭应用根目录。

## 示例

```bash
# plugin-key 从仓库 Skill 的「AI 插件目录」获取
lark-cli apps +plugin-install --name <plugin-key> --project-path <path>

# 批量安装已声明的所有插件
lark-cli apps +plugin-install --project-path <path>
```

## 输出契约

- 已安装同版本会跳过（status=already_installed）。
- 失败时 hint 指示原因（网络/版本不存在/package.json 缺失）。
