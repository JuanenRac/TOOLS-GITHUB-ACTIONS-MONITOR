<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# 入站 Webhook

可选功能,**默认关闭**。它让 GitHub 通知监视器“有变化”,这样仓库会在下一个周期被刷新,而不必等下一次轮询。

## 它做什么(仅刷新)

被接受的事件只会把其中指明的仓库标记为在下一个周期刷新。不会向 GitHub 或磁盘写入任何内容,事件的文本不会被保存或显示,并且只接受监视器已在监视的仓库。能理解的事件:`workflow_run`、`workflow_job`、`push`、`release`、`check_suite` 和 `ping`;其他事件返回 `202` 并被忽略。

## 安全

- 监视器仍然只监听 `127.0.0.1`。GitHub 只能通过你有意搭建的隧道访问它;工具本身从不打开隧道。
- 在 `webhook.enabled` 开启**并且** `actions_monitor.json` 中的共享密钥至少 32 个字符之前保持关闭(否则端点保持关闭)。
- 每个请求都必须带有用该密钥生成的 `X-Hub-Signature-256: sha256=<hmac>`;否则返回 `401`。密钥永不显示:设置标签页只说明它是否已定义。
- 超过 256 KB 的请求体返回 `413`。

## 如何开启

在 `actions_monitor.json` 中写入 `"webhook": {"enabled": true, "secret": "<32 个或更多随机字符>"}`;开关也在设置标签页(子标签页“入站 Webhook”),密钥只放在文件里。重启监视器。在 GitHub 的 Webhook 设置中使用内容类型 `application/json`、相同的密钥,以及以 `/api/webhook` 结尾的隧道 URL。

## 实时事件

- 当 `webhook.record_events` 开启(默认)时,已签名的 `workflow_run` 事件会立即更新该仓库的运行列表,而无需读取 GitHub:直到下一次计划读取之前,该仓库不消耗配额。`workflow_job` 事件还会为分析带来排队时间和每个步骤的时间。
- 只保留经过验证的简短字段(工作流、运行、状态、结论、分支、短提交、运行链接、时长);绝不保留提交信息或任何自由文本。最新的 `webhook.live_events_keep` 个事件可在 `GET /api/live-events` 读取(仅限本机)。
- 当通知开启时,以红色结束的运行还会发送 `workflow_failed` 通知。关闭 `webhook.record_events` 后,Webhook 恢复为上述仅刷新模式。
- GitHub 无法访问 `127.0.0.1`:请使用 `gh webhook forward`(见 GitHub CLI 文档)或你有意搭建的隧道,指向 `http://127.0.0.1:端口/api/webhook`。

## 重放与洪泛

被人截获后重新发送的有效签名请求会得到应答但不会被执行：每次投递都需要 `X-GitHub-Delivery` ID，已接受的 ID 会在 `webhook.replay_seconds` 内被记住（默认一小时，内存有上限），重复请求得到 `202 {"duplicate": true}`。（在 GitHub 页面手动重新投递会复用同一 ID，因此在此窗口内会被忽略。）一个仓库每分钟最多引发 `webhook.max_per_minute` 个被接受的事件，其余只应答并忽略。若载荷包含 `full_name`，其所有者必须是被监视的账户（或 `webhook.allowed_owners` 中的一个）。在网络模式下，一个地址每分钟可发送 120 个请求。接受事件后，该仓库已保存的条件读取会被丢弃，并在下个周期重新读取，因此实时事件总会与 GitHub 对账。
