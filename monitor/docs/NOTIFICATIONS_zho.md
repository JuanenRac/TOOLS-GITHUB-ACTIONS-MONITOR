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
- `kind` 为 `red_new`、`red_fixed`、`stuck_new`、`pending_sign`、`release_due`、`rate_low`、`offline`、`online`、`alerts_up`、`workflow_failed`、`collab_new`、`collab_fixed`、`credential_blind`、`credential_back` 之一。字段只会增加。返回任意 2xx;其他一律算作失败。
- `mqtt` 把同样的 JSON 作为 QoS 0 消息的负载发布到 `notify.channels.mqtt.topic`。

## 每小时上限统计的是消息

`notify.max_per_hour` 限制的是离开电脑的「消息」，而不是事件：发往三个渠道的一个事件会消耗三个额度，每个渠道一个。额度不足以覆盖所有渠道时，列表中靠前的渠道收到消息，其余的被丢弃（页面将其计为“受限”）。无法发送的渠道（没有密钥、地址错误）不消耗额度。计数在同一把锁下完成，因此多个线程永远不会超过上限。
