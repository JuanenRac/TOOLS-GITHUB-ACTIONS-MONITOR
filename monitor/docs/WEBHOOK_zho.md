<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# 入站 Webhook

可选功能,**默认关闭**。它让 GitHub 通知监视器“有变化”,这样仓库会在下一个周期被刷新,而不必等下一次轮询。

## 它做什么(仅刷新)

被接受的事件只会把其中指明的仓库标记为在下一个周期刷新。不会向 GitHub 或磁盘写入任何内容,事件的文本不会被保存或显示,并且只接受监视器已在监视的仓库。能理解的事件:`workflow_run`、`workflow_job`、`push`、`release`、`check_run`, `check_suite` 和 `ping`;其他事件返回 `202` 并被忽略。

## 安全

- 监视器仍然只监听 `127.0.0.1`。GitHub 只能通过你有意搭建的隧道到达它；本工具从不自己开启隧道。
- 在 `webhook.enabled` 开启**并且**共享密钥（32 个字符或更多）位于 `webhook.secret_env` 所指的环境变量中之前，接收器保持关闭（默认变量为 `MONITOR_WEBHOOK_SECRET`；`MONITOR_WEBHOOK_SECRET_FILE` 可指向一个首行为密钥的文件，容器的 secret 就是这样提供的）。密钥绝不会写入 `actions_monitor.json`、被显示、被记录到日志，也不会被监视器启动的程序继承；设置标签页只说明它是否已定义。旧方式（文件中的 `secret`）仅在 `webhook.allow_config_secret` 为 true 时才会读取，使用期间实时视图会发出警告。
- 共享密钥是唯一的屏障:GitHub 无法发送访问令牌,因此接收端不要求令牌,只信任签名。接收端已开启但未设置密钥时,它会以 `401` 拒绝每一次投递,doctor 会以红色提示。请把地址放在你自己控制的隧道或代理之后。
- 每个请求都必须带有 `X-Hub-Signature-256: sha256=<hmac>`，用该密钥生成并以恒定时间比较；其他一律返回 `401`，在验证签名之前不会查看任何内容。
- 超过 256 KB 的请求体返回 `413`，且在任何计算之前就拒绝。
- 列表是封闭的：只处理 `workflow_run`、`workflow_job`、`check_run`、`push`、`release`、`check_suite` 和 `ping`，事件中只保留经过验证的短字段（绝不保留提交信息或任何自由文本），其余一律返回 `202` 并丢弃。

## 如何开启

1. 生成一个 32 个或更多随机字符的密钥，例如 `python -c "import secrets; print(secrets.token_hex(32))"`。
2. 通过监视器的环境把它交给监视器，绝不要通过文件：在启动监视器前于 PowerShell 中执行 `$env:MONITOR_WEBHOOK_SECRET = "<密钥>"`；在 shell 中用 `export MONITOR_WEBHOOK_SECRET=...`；在服务中用 `Environment=` 或 `EnvironmentFile=`（仅你可读的文件）；在容器中用 `-e` 或由 `MONITOR_WEBHOOK_SECRET_FILE` 指定的 secret 文件。
3. 开启接收器（设置 > 入站 Webhook > 接收器开启，或在 `actions_monitor.json` 中写入 `"webhook": {"enabled": true}`），然后重启监视器。
4. 让地址可达：GitHub 无法访问 `127.0.0.1`。使用你有意搭建的隧道（以 `/api/webhook` 结尾的 HTTPS 地址），或在本机使用 `gh webhook forward` 指向 `http://127.0.0.1:端口/api/webhook`（如何在不把密钥写进命令行的情况下提供同一个密钥，请见 GitHub CLI 文档）。
5. 在 GitHub 中打开仓库（或组织）> Settings > Webhooks > Add webhook。**Payload URL**：以 `/api/webhook` 结尾的隧道地址。**Content type**：`application/json`。**Secret**：同一个密钥。**SSL verification**：启用。**Events**：选择“Let me select individual events”，然后选 Workflow runs 和 Workflow jobs，可选 Check runs、Pushes 和 Releases。**Active**：开启。组织级的一个 webhook 覆盖其所有仓库；监视器会忽略它不监视的仓库。
6. 检查：在 GitHub 的 Recent deliveries 中，第一个 `ping` 必须显示 `200`；在监视器中，实时视图会显示接收器已开启、计数器和覆盖情况。

## 实时事件

- 当 `webhook.record_events` 开启(默认)时,已签名的 `workflow_run` 事件会立即更新该仓库的运行列表,而无需先读取 GitHub:该运行保留其原有的事件类型,因此颜色不会改变,并且仓库会在下一个周期再次读取以确认(每个被接受的事件读取一次)。`workflow_job` 事件还会为分析带来排队时间和每个步骤的时间。
- 只保留经过验证的简短字段(工作流、运行、状态、结论、分支、短提交、运行链接、时长);绝不保留提交信息或作者。工作流、分支、作业和步骤的简短名称也会保留,压缩为一行,并像离开监视器的任何文本一样清理。最新的 `webhook.live_events_keep` 个事件可在 `GET /api/live-events` 读取(网络模式下需访问令牌)。
- 当 `webhook.record_events` 开启(默认)时,已签名的 `workflow_run` 事件会立即更新该仓库的运行列表,而无需读取 GitHub:但该仓库仍会在下一个周期被重新读取(事件是消息,读取才是证据),因此一次投递会立刻显示变化,却不会省下一次读取。`workflow_job` 事件还会为分析带来排队时间和每个步骤的时间。
- 只保留经过验证的简短字段(工作流、运行、状态、结论、分支、短提交、运行链接、时长);绝不保留提交信息。工作流、分支和作业的名称是第三方编写的最多 100 个字符的文本:它们会被保留并以纯文本显示,步骤名称则进入统计。最新的 `webhook.live_events_keep` 个事件可在 `GET /api/live-events` 读取(能打开页面的人:网络模式下用访问令牌,团队模式下用会话)。
- 可选，默认关闭：开启 `live.sse.enabled` 后，`GET /api/live-events/stream` 会在事件被接受时以服务器发送事件的形式发送这些事件（先是 `hello`，之后每个事件一个 `live` 帧，带有递增的 `id`，可用 `Last-Event-ID` 或 `?since=` 续传，另有保活注释和最后的 `bye`）。只读；在网络模式下与其他请求一样需要访问令牌；最多 `live.sse.max_clients` 个监听者，每个持续 `live.sse.max_seconds`。Lite 版没有它。
- 当通知开启时,以红色结束的运行还会发送 `workflow_failed` 通知。关闭 `webhook.record_events` 后,Webhook 恢复为上述仅刷新模式。
- GitHub 无法访问 `127.0.0.1`:请使用 `gh webhook forward`(见 GitHub CLI 文档)或你有意搭建的隧道,指向 `http://127.0.0.1:端口/api/webhook`。

## 时间上的覆盖

实时视图会说明事件在多大程度上覆盖了状态：**由事件覆盖**（最近一个事件比 `savings.webhook_window_minutes` 更新，默认 60 分钟）、**已有 ... 没有事件**（更旧：仓库安静或隧道中断）或**正在等待第一个事件**。轮询始终是后备：从未到达的推送（监视器当时关闭、隧道中断）会在下一次读取该仓库时被补上，所以事件减少读取次数，但绝不取代读取。同样的数字也在 `GET /api/live-status` 的 `coverage` 和 `secret_source`（`env`、`config` 或 `none`；绝不含密钥）中。

## 如果不起作用

| 响应 | 含义 |
|---|---|
| `404` | 接收器已关闭，或环境变量中的密钥缺失或短于 32 个字符。 |
| `401` | 签名不匹配：两边使用同一个密钥，内容类型为 `application/json`。 |
| `413` | 请求体超过 256 KB。 |
| `400` | 没有有效的 `X-GitHub-Delivery` ID，或内容无法理解。 |
| `202` | 已接受但被忽略：未监视的仓库、列表之外的事件、重复推送，或超出每分钟限额的仓库。 |
| `429` | 同一地址一分钟内发送了超过 120 个签名正确的请求，或超过 `webhook.max_bad_per_minute`（默认 120）个签名无法验证的请求。 |

## 重放与洪泛

被人截获后重新发送的有效签名请求会得到应答但不会被执行：每次投递都需要 `X-GitHub-Delivery` ID，已接受的 ID 以及已签名的请求体本身会在 `webhook.replay_seconds` 内被记住（默认一小时，内存有上限），因此被截获后换一个 ID 重发的请求仍是同一次投递，重复请求得到 `202 {"duplicate": true}`。（在 GitHub 页面手动重新投递会重复同一请求体，因此在此窗口内会被忽略。）一个仓库每分钟最多引发 `webhook.max_per_minute` 个被接受的事件，其余只应答并忽略。若载荷包含 `full_name`，其所有者必须是被监视的账户（或 `webhook.allowed_owners` 中的一个）。一个地址每分钟可发送 120 个签名正确的请求，以及 `webhook.max_bad_per_minute` 个签名无法验证的请求；两者在任何模式下都分开计数，因此垃圾请求永远不会耗尽真实投递的配额（使用 `listen.trusted_proxy` 时，地址为代理所看到的地址）。接受事件后，该仓库已保存的条件读取会被丢弃，并在下个周期重新读取，因此实时事件总会与 GitHub 对账。 投递记忆保存在数据文件夹中的私有文件里(`webhook.persist_deliveries`,默认开启;有上限,损坏的文件视为空记忆),因此重启不会让被截获的投递重新生效。开启 `webhook.reject_stale`(默认关闭)后,自身时间早于 `webhook.replay_seconds` 的已签名工作流事件只会得到应答而被忽略。一个地址的签名正确请求的配额是 `webhook.max_verified_per_minute`(120)。`webhook.secret_env` 绝不接受系统变量或你的 GitHub 登录变量(PATH、GH_TOKEN 等),也不接受属于其他设置的密钥,且一个名称只能写在一个设置里。

## 实时视图检查清单

1. 在 `webhook.secret_env` 所指的环境变量中放入至少 32 个字符的密钥，并开启 Webhook。
2. 转发端口（`gh webhook forward`）或打开隧道，并在 GitHub 中使用以 `/api/webhook` 结尾的地址。
3. 运行一个工作流（或向受监视的仓库推送），并在 `?view=live` 中查看该事件。GitHub 的 `ping` 只验证签名：它返回 `200`，不会出现在列表中，而从 GitHub 重新发送会被当作重复而忽略。
4. 留意页头的配额：使用 Webhook 后，较慢的周期就够了。
