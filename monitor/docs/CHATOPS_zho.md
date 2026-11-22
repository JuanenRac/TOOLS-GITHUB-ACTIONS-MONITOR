<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# 聊天命令(Slack 和 Discord)

可选功能,**默认关闭**。它让人们可以在 Slack 或 Discord 频道里向监视器询问简短的状态:有多少仓库是红色的、未处理的警报、队列和评分。它是**只读**的。

## 它做什么(以及绝不做什么)

- 命令是一份封闭的列表:`help`、`status`、`alerts`、`red`、`queue` 和 `score`。其他任何内容都会得到"不认识该命令"。`chatops.allowed_words` 只能缩小这份列表。
- 命令只读取监视器已经拥有的内容(最近一次周期、警报、评分)。它从不向 GitHub 写入,从不执行操作,从不更改设置,也从不读取密钥;没有这样的命令,也无法从聊天里添加。
- 回复只有提问的人能看到,不提及任何人,也不含链接,只有一种例外:当 `chatops.links` 开启(默认)时,在按原样显示的名称旁附上仓库地址(`https://<主机>/<所有者>/<仓库>`,已校验)。来自 GitHub 的所有文本(仓库名或工作流名)都会被清理、截断,并针对平台做转义。
- 每条到达监视器的命令都会在操作日志(`chatops_command`)中留下一行,记录聊天的 ID,绝不记录请求的文本。

## 安全

- 在 `chatops.enabled` 和平台开关(`chatops.slack.enabled`、`chatops.discord.enabled`)都开启,**并且**凭据已在环境中之前,保持关闭。设置只保存变量的名称(`chatops.slack.signing_secret_env`、`chatops.discord.public_key_env`),从不保存其值;该值不会被写入、显示或记录。
- Slack:每个请求必须带有 `X-Slack-Signature: v0=<hmac>`(用签名密钥对 `v0:<时间戳>:<正文>` 计算的 HMAC-SHA256),且 `X-Slack-Request-Timestamp` 不得早于 `chatops.max_age_seconds`(最多五分钟)。无论签名是什么,比较所花的时间都相同。
- Discord:每个请求必须带有 `X-Signature-Ed25519` 和 `X-Signature-Timestamp`:对时间戳加正文的 Ed25519 签名,用你的应用公钥校验(RFC 8032,标准库;不经校验绝不接受任何内容)。
- 错误、过旧或来自未来的签名会得到 `401`,正文一概不看。已接受过的签名不会再次被接受。超过 16 KB 的正文得到 `413`。一个地址每分钟最多可发 120 个请求。
- **名单是必需的**:`chatops.allowed_teams`、`chatops.allowed_channels` 和 `chatops.allowed_users`。三个都没填时不会执行任何命令(平台的验证挑战仍会被应答,以便你完成设置)。有内容的名单必须包含请求的团队、频道或用户。
- 每分钟的限制:`chatops.rate_per_user_per_minute`、`chatops.rate_per_channel_per_minute` 和 `chatops.rate_per_minute`。回复必须在 3 秒内送达:监视器从内存中回答,如果更慢,就会说明自己很忙。
- 这两个路由(`/api/chatops/slack`、`/api/chatops/discord`)不要求网络模式的访问令牌,因为平台无法发送它:签名就是它们的凭据,与入站 Webhook 一样。除非你开启网络模式,监视器仍只监听 `127.0.0.1`;平台只能通过你有意搭建的 HTTPS 地址(隧道或反向代理;本工具从不自行开启)访问它。请只通过它公开 `/api/chatops/`。

## 命令

| 命令 | 回复 |
| --- | --- |
| `help` | 命令列表 |
| `status` | 红色、卡住、等待、绿色和空闲的仓库数,以及未处理的警报 |
| `alerts` | 未处理的警报(级别、代码和仓库),最多 `chatops.max_rows` 行 |
| `red` | 红色的工作流及其持续时间,最多 `chatops.max_rows` 行 |
| `queue` | 运行中、排队中、等待批准的数量,以及 24 小时已用分钟数 |
| `score` | 评分、它的字母等级和变化 |

`chatops.show_repo_names` 决定名称:`all`(所有名称,包括私有仓库)、`public`(默认:私有仓库显示为 `private-N`,不显示其工作流名称)或 `none`。**`all` 的风险:** 私有仓库和工作流的名称会到达你的名单所允许的每个频道和用户。因此名单是必需的,且每个有内容的名单都必须匹配(团队、频道和用户同时匹配)。如果频道比有权知道这些名称的人更宽泛,请保持 `public`(默认)或选择 `none`。

## Slack 步骤

1. 打开 api.slack.com/apps > Create New App > From scratch,命名并选择你的工作区。
2. Slash Commands > Create New Command:命令 `/monitor`,**Request URL** 填 `https://<你的公网地址>/api/chatops/slack`,再写一句简短说明。不需要任何机器人权限范围。
3. Basic Information > App Credentials > **Signing Secret**:复制它,通过环境(而不是文件)交给监视器:启动监视器前在 PowerShell 中执行 `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"`,在 shell 中执行 `export MONITOR_SLACK_SIGNING_SECRET=...`,在服务或容器中使用环境条目或密钥文件。
4. 把应用安装到工作区(Install App)。
5. 填写名单:你的团队 ID(以 `T` 开头)、频道 ID(打开频道详情,ID 在底部:`C...`)和你的成员 ID(你的个人资料 > Copy member ID:`U...`)。把它们填入 设置 > 聊天命令,或在 `actions_monitor.json` 中写 `"chatops": {"allowed_channels": ["C0123456789"]}`。
6. 开启聊天命令和 Slack,然后重启监视器。

## Discord 步骤

1. 打开 discord.com/developers/applications > New Application。在 General Information 中复制 **Public Key**(64 个十六进制字符),通过环境交给监视器:PowerShell 中 `$env:MONITOR_DISCORD_PUBLIC_KEY = "<公钥>"`,shell 中 `export MONITOR_DISCORD_PUBLIC_KEY=...`。
2. 填写名单,开启聊天命令和 Discord(设置 > 聊天命令),然后重启监视器。请在下一步**之前**完成:保存地址时 Discord 会发送一个带签名的测试,如果监视器不应答就会拒绝该地址。
3. General Information > **Interactions Endpoint URL**:填 `https://<你的公网地址>/api/chatops/discord`,然后 Save。
4. 用你自己的工具(Discord API,`POST /applications/<应用 ID>/commands`)注册一次命令,请求体如下:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. 仅用范围 `applications.commands` 邀请应用(OAuth2 > URL Generator);不需要任何机器人权限。ID:在 Discord 中开启开发者模式(高级),对服务器、频道和你的用户使用"复制 ID"。

## 试一试

在允许的频道里输入 `/monitor help`(Slack)或 `/monitor command:status`(Discord)。其他回应:

| 你看到的 | 含义 |
| --- | --- |
| 没有反应,或"没有响应" | 地址不可达、监视器已关闭,或它回复了 `401`(密钥或公钥错误,或时钟偏差超过五分钟) |
| "此处不能使用该命令。" | 团队、频道或用户不在名单中 |
| "命令太多。" | 触发了每分钟三项限制之一 |
| "监视器还没有读取 GitHub。" | 第一个周期尚未完成 |
