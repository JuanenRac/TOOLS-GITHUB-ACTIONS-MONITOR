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
