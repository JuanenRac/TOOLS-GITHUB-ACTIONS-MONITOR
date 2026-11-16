<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# 通知

可选功能,**默认关闭**。动态流中的事件(新的红色、卡住的构建、等待签名的构建、连接丢失、由 Webhook 报告的失败运行)可以发送到聊天或设备。通知只是带链接的消息:它从不在 GitHub 上重新运行、取消或写入任何内容。

## 渠道

- `telegram`(机器人)、`discord` 和 `slack`(频道 Webhook)、`matrix`(房间)、`mqtt`(本机上的代理,用于灯和信标)以及 `http_local`(向本机上的地址发送 POST)。
- 每个渠道在设置标签页(子标签页“通知”)中都有自己的开关和发送测试的按钮。


## 安全

- 令牌和 Webhook URL 从不保存在配置中:你设置的是环境变量的名称,值仅在发送时读取,从不显示、从不记录。
- `discord` 只接受 `discord.com`,`slack` 只接受 `hooks.slack.com`;`mqtt` 和 `http_local` 只接受 `127.0.0.1`、`localhost` 或 `[::1]`。
- 只要 `notify.allow_private_targets` 保持关闭(默认),就拒绝属于或解析到回环、私有(10.x、172.16-31.x、192.168.x、fc00::/7)、链路本地(169.254.x,含云元数据地址,fe80::/10)、共享(100.64.0.0/10)或保留地址的目标。名称只解析一次,连接指向已检查的地址,每次重定向也遵循同一规则。这样填错的 Matrix 服务器就无法到达你的路由器或云主机的元数据服务。
- 每小时最多有 `notify.max_per_hour` 条消息离开本机;发送失败会被计数并忽略,绝不会让监视器停止。


## 适配器约定

- 要连接列表之外的服务,请在本机运行一个小型接收程序,并让 `http_local` 指向它。它会收到 `Content-Type: application/json` 的 POST,正文如下:`{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`。
- `kind` 为 `red_new`、`red_fixed`、`stuck_new`、`pending_sign`、`release_due`、`rate_low`、`offline`、`online`、`alerts_up`、`workflow_failed`、`ai_alert`、`collab_new`、`collab_fixed`、`credential_blind`、`credential_back`, `score_dropped`, `security_new`, `security_fixed` 之一。字段只会增加。返回任意 2xx;其他一律算作失败。
- `mqtt` 把同样的 JSON 作为 QoS 0 消息的负载发布到 `notify.channels.mqtt.topic`。

## Apprise（可选，默认关闭）

`apprise` 渠道把消息交给 `apprise` 命令（请自行安装，例如 `pip install apprise`），从而可以到达它支持的任何服务。这些地址包含各服务的机密，所以放在名称为 `notify.channels.apprise.urls_env` 的环境变量中（用空格或逗号分隔，最多十个）；调用期间它们会写入一个私有的临时文件，绝不放进命令参数，命令得到的环境中不含监视器的密钥。**Apprise 自行建立连接，监视器对私有地址的防护不适用于它**，所以它能到达哪里取决于你给它的地址；因此该渠道有独立的开关，默认关闭，并标记为安全设置。若找不到该命令，渠道会显示 `not_installed`；失败与其他失败一样被计数，绝不会让监视器停止。

## 每小时上限统计的是消息

`notify.max_per_hour` 限制的是离开电脑的「消息」，而不是事件：发往三个渠道的一个事件会消耗三个额度，每个渠道一个。额度不足以覆盖所有渠道时，列表中靠前的渠道收到消息，其余的被丢弃（页面将其计为“受限”）。无法发送的渠道（没有密钥、地址错误）不消耗额度。计数在同一把锁下完成，因此多个线程永远不会超过上限。

## 按用户通知（团队模式）

默认关闭（`notify.users.enabled`）。团队模式开启后，每位用户在 `GET/POST /api/auth/me/notify` 中选择渠道（`ntfy`、`teams`、`email`）、哨兵（`ci`、`collab`）、最低级别（`info`、`warn`、`bad`）、是否接收系统事件，以及消息是立即发送还是汇总为摘要（`hourly`、`daily`）。角色决定用户可获知的内容：查看者获知其可见账户的 CI 事件；维护者另外获知等待人处理的事项（等待签名的构建、到期的发布）；管理员另外获知系统事件。某账户的事件绝不会发给无权查看该账户的人。`notify.users.max_per_hour` 限制每位用户收到的消息数。

- `ntfy`：每位用户在 `notify.channels.ntfy.server`（https 或本机服务器）上的主题；访问令牌可选。
- `teams`：Teams 频道传入 Webhook 的地址（仅限 Microsoft 的主机）。
- `email`：用户的地址，经本机无需登录的中继发送（`notify.channels.email`）。

Teams Webhook 地址和 ntfy 令牌由系统加密保存（DPAPI、钥匙串、Secret Service 或私有文件），绝不会出现在响应、日志或配置中；删除用户时一并删除。`MONITOR_SECRET_BACKEND=file` 强制使用私有文件。在管理员开启之前，每个渠道都是关闭的。摘要汇总用户尚未查看的告警（最多 `notify.digest.max_items` 条）；`POST /api/auth/me/notify/seen` 将其标记为已读，不再发送；`POST /api/auth/me/notify/test` 向该用户的渠道发送测试消息。管理员可在 `GET /api/auth/notify` 读取所有人的偏好（不含任何密钥）。

### 每位用户的面板

在团队模式下，已登录用户的菜单（顶部的名字）里有**通知**一项。面板显示并保存与 `GET/POST /api/auth/me/notify` 相同的偏好：是否接收通知、渠道（带主题和可选令牌的 ntfy、带频道网址的 Teams、带地址的电子邮件）、哨兵（CI、协作）、最低级别、系统事件（仅管理员）以及每条告警是立即发送还是按小时或按天汇总。已保存的密钥只显示为已保存，绝不会回到页面中；只有输入新的才会发送，留空则保留。**发送测试**会向您的渠道发一条消息，**我已查看告警**会把待处理的标记为已查看。如果管理员没有开启 `notify.users.enabled`，面板会说明：您可以保存选择，但暂不会发送任何内容。

## 警报很多，或同样的警报反复出现

`alerts` 块中的四组可选设置（默认全部关闭或为空）决定哪些内容会到达上面的渠道。列表、“警报”标签页和事件流仍会显示全部内容。

- **永久静默**（`alerts.silences`）：每行一条，`仓库:工作流:分支;原因;复查日期`。除仓库外都是可选的，`*` 匹配任意文本。匹配的警报显示为已静默，不通知任何人，复查日期当天会提醒一次；静默会一直有效直到你删除。
- **服务与短周期 cron**（`alerts.service`）：只按计划或手动运行、偶尔失败的工作流，只有连续失败 `failures` 次，或最近运行失败比例达到 `rate_percent` 时才会通知；通知一次、恢复也只通知一次，而不是循环告警。`workflows` 可把更多工作流加入此类。
- **按提交合并**（`alerts.group`）：同一仓库有 `min` 个或更多工作流在同一提交上变红时，只发一条通知并列出它们。
- **数量多时的摘要**（`alerts.digest`）：最近一小时内发出 `threshold` 条通知后，其余的会被暂存，并每隔 `minutes` 分钟合并为一条摘要。被暂存的事件仍保留在事件流中。
