# lark-vc-agent 权限与身份错误排查

本 reference 只在 `lark-vc-agent` 命令返回权限或身份错误时使用。先以 CLI 返回的 metadata / error envelope 为准，不要根据文案猜测。

## 应用身份权限配置检查

应用身份 `--as bot` 报 `no permission`、`missing required scope(s)`、`permission_violations`、`ErrNotInGray` 或 `20017` 时，不要引导用户执行 `auth login`。按顺序检查：

1. 当前功能仍在内测中。先提示用户加入早鸟群，确认内测权限已开通。
2. 以 CLI 返回的 metadata / error envelope 为准，确认提示的 VC Agent 相关权限已开通。常见读取 active meeting / events 需要会中事件读取权限；应用机器人入会 / 离会需要 bot 入会写权限。
3. 应用已发布并安装到当前租户。
4. 开放平台“权限可访问的数据范围”已开通并保存。
5. 数据范围选择“按条件筛选”，条件配置为：**会议的归属者 包含 与应用的可用范围一致**。
6. 如果 scope、安装和数据范围都正确，仍返回 `ErrNotInGray` / `20017`，再按 VC Agent privilege / 灰度白名单处理，提示联系平台同学开通。

## 用户身份被拒绝时

用户身份 `--as user` 报权限或身份不支持类错误时，不要反复引导用户执行 `auth login`。先按 CLI 返回的 metadata / error envelope 判断：

1. 如果错误表明当前接口不支持用户身份访问，而用户只是查询当前登录用户所在的进行中会议，说明该链路需要改用应用身份流程；需要目标用户 open_id，并要求应用机器人已在会中，或先按用户确认执行入会。
2. 如果用户明确要求应用机器人入会、旁听、代参会或读取应用机器人可见事件，直接切到 `--as bot`，再按“应用身份权限配置检查”处理。

## 早鸟群

`https://go.larkoffice.com/join-chat/2f4nb0e1-fe00-4f67-bed7-25beaf533fbd`
