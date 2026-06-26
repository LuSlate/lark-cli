#!/bin/sh
# SessionStart 钩子：确保 lark-cli 二进制存在。
# 只装二进制（npm install -g 的 postinstall 从 GitHub Releases 下载预编译包，非交互），
# 不跑 install 向导，避免重复全局安装 skills（skills 已由本插件提供）。

# 已安装 -> 秒退，零开销
if command -v lark-cli >/dev/null 2>&1; then
  exit 0
fi

# 缺二进制：后台非交互安装，不阻塞会话启动
# ponytail: 不加锁，npm install -g 幂等，最坏情况两次会话各起一次，无害
LOG="${TMPDIR:-/tmp}/lark-cli-install.log"
(npm install -g @larksuite/cli >"$LOG" 2>&1 &)

# 给模型/用户一句上下文提示
cat <<EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"lark-cli 二进制未检测到，正在后台安装（npm install -g @larksuite/cli，日志：$LOG）。完成前飞书命令暂不可用；若长时间未生效，请手动运行：npx @larksuite/cli@latest install"}}
EOF
exit 0
