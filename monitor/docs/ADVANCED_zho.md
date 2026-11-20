<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 高级功能(默认全部关闭)

本页的一切在你于*设置 > 高级*(或 `actions_monitor.json`)中开启之前都是**关闭**的,决定谁能访问监视器或它能在 GitHub 上做什么的键都标记为安全选项。只开启你需要的。

## 监听网络

默认页面只在 `127.0.0.1` 上响应。开启 `listen.network`(需重启)后,它还会监听 `listen.host`:本机的私有地址,或代表所有接口的 `0.0.0.0`。公网地址会被拒绝。

- **每个请求都需要访问令牌**(Cookie、`X-Monitor-Access` 头或 `Authorization: Bearer`)。令牌是 `listen.token_env` 所指环境变量的值(16 个字符或更多);没有时每次启动会生成随机令牌,仅在控制台显示一次。打开那里打印的地址一次:它会设置 Cookie 并跳转到干净的地址。
- 页面的一次性令牌被强制启用,模式开启期间每个标签页都会显示红色提示条,`listen.*`、`github_token.*`、`act.*` 和 `github_actions.*` 的键只能从本机修改。
- `listen.allowed_hosts` 列出可用来打开页面的名称(防御 DNS 重绑定)。
- **风险。** 流量是明文 HTTP:能监听你网络的人可以读取令牌和数据。只在可信网络中使用,或在前面放置带 HTTPS 的反向代理(见 `DEPLOYMENT.md`)。切勿暴露到互联网。精简版绝不会监听本机以外。
- **HTTPS。** 使用自己的证书和密钥(`listen.tls_cert_file`、`listen.tls_key_file`),监视器会自己提供 HTTPS;在替你处理 HTTPS 的代理之后,请设置 `listen.secure_cookie`。两种情况下,浏览器每次更改都会发送 `Origin: https://主机:端口`,检查只接受会话的协议(另一种协议、其他主机、其他端口或格式错误的来源都会被拒绝)。浏览器使用的地址必须带有监视器的端口,但如果位于默认 443 端口上、转发不带端口的 `Host` 和 `Origin` 的 HTTPS 代理之后,请把它的公开名称填入 `listen.proxy_public_host`(仅限主机名,默认为空)。它只在 HTTPS 下生效,只有这一个名称可以不带端口被接受,并且只能在本机上更改。
- **用 POST 打开会话。** 除了带 `?access=` 的地址已弃用:默认被拒绝(开启 `listen.query_access` 才会接受),接受时也只对 `GET` 有效,但令牌会留在历史记录、日志和 `Referer` 中,监视器会用 `Deprecation` 响应头回应。保持关闭(默认)时,只用 `POST /api/access` 或请求头 `X-Monitor-Access` 打开会话。带 `?access=` 的地址仍然可用。当 `listen.host` 为 `0.0.0.0` 时,设置页顶部会显示红色横幅提醒。架构中标记为安全的所有设置(不仅是 `listen.*`、`github_token.*`、`act.*` 和 `github_actions.*`,还有 Webhook、AI 操作、通知、OpenTelemetry、镜像、runner 和输出)只能在本机修改。
- **在网络上监听时的第一步。** 保持 `listen.query_access` 为默认的关闭状态 (这样令牌就不会出现在地址、历史记录或日志中; 用 `POST /api/access` 或请求头打开会话), 并在前面加上 HTTPS (`listen.tls_cert_file` 中的证书或 HTTPS 代理) 或 VPN。若你开启了旧地址,网络模式启动时, 控制台会重复这条提示。

## 团队模式：用户与角色

默认关闭：一个人无需登录使用监视器。开启 `auth.enabled`（无需重启）后，在第一位管理员创建之前什么都不会改变。lite 版从不登录。

- **第一位管理员。** 在运行监视器的电脑上打开 `/login` 创建（只能在该电脑上、只能一次；经代理到达的请求会被拒绝）。或在控制台运行：`python -m github_actions_monitor.security.auth_cli create-admin 名称 --password-env 变量名`（密码绝不出现在命令行中）。此后页面会要求登录；同一工具的 `reset-password` 和 `revoke` 可找回丢失的管理员密码。
- **角色。** `viewer` 只读（所有 GET）；`maintainer` 还可更改工作模式，并且仅在监控所在的计算机上（不能通过网络）静音和确认警报；`admin` 还可更改设置、用户以及一切可能触及 GitHub 或外部的内容。未列出的路由对除 admin 外的所有人关闭。每个用户还有可查看的账户列表（admin 可看全部）：用 `?account=` 或 `X-Account-Id` 请求其他账户，在 API 和导出中都返回 403 `account_scope`。 重复给出 `account` 的请求会返回 400 `account_repeated`：账户只决定一次，被判断的与被服务的是同一个。
- **会话。** 浏览器获得 Cookie `monitor_session`（HttpOnly、SameSite=Strict，HTTPS 时加 Secure）和 CSRF 令牌（`X-CSRF-Token`，由登录和 `/api/auth/me` 返回），每个 POST 都必须携带。脚本或应用使用 `POST /api/auth/login` 并传 `{"client": "api"}`，将得到的令牌以 `Authorization: Bearer msn_...` 发送（仅在 `auth.allow_bearer` 开启时有效；默认关闭）。页面的一次性令牌（`session_guard`）在会话之外仍然适用。
- **密码。** 仅以加盐的 scrypt 哈希保存，至少 `auth.min_length` 个字符。错误密码达到 `auth.max_failed_logins` 次后，该用户被锁定 `auth.lockout_minutes` 分钟，每个地址还有自己的请求上限。新的密码、角色或状态会结束该用户的会话；始终至少保留一位有效管理员。 坐在监控所在计算机前的人永远不会被锁定，其错误密码也不计入该用户；不存在的名称同样会被计数和锁定，因此“已锁定”不会泄露哪些名称存在。
- **端点。** `/api/auth/login`、`logout`、`me`、`bootstrap`、`password`；管理员可用 `/api/auth/users`（含 `/update`、`/delete`、`/revoke`）和 `/api/auth/audit`。错误为带稳定代码的 JSON：`{"error": "...", "code": "..."}`。
- **审计。** `auth_audit.jsonl`（私有文件，保留一份旧副本）记录登录、锁定、被拒绝的请求和用户变更；绝不记录密码、哈希或令牌。`auth.audit` 可关闭。
- **多个账户。** 使用 `ACCOUNTS.md` 的账户时，`GET /api/accounts` 只列出、`/api/accounts/<id>/status` 以及所有带 `?account=` 或 `X-Account-Id` 的请求只能访问分配给该用户的账户（admin 可看全部）。账户的监视器知道是谁在操作，因此“警报”标签页的静音会记录是谁做的（`GET /api/alerts` 中的 `muted_by` 和静音历史）。
- **页面。** 页眉中的一个框显示已登录者的名称和角色，并打开菜单：修改我的密码、用户和审计（管理员）、退出登录。页面发出的每个更改都带有 CSRF 令牌；在个人模式和 lite 版中，页面不绘制也不发出任何新请求。
- **风险。** 在网络上使用未加密的 HTTP 时，Cookie 和密码以明文传输：与网络模式一样，请使用 HTTPS 或 VPN。

## 监视器保存的 GitHub 令牌

默认仍是你自己的 `gh` 登录。开启 `github_token.enabled` 后,你可以在设置 > 高级中粘贴令牌:它保存在系统安全存储中(Windows DPAPI、macOS 钥匙串、Linux Secret Service),只有在缺失时才保存到权限 600 的文件中(页面会说明)。它绝不会写入 `actions_monitor.json`、日志、“关于”面板或支持文本,只通过进程环境传给 `gh`。**删除令牌**按钮会从所有位置清除它。

## 对 GitHub 的操作

开启 `github_actions.enabled` 后,监视器可以重新运行失败的运行(`rerun_failed`、`rerun_run`、`rerun_job`)、取消运行(`cancel`)、关闭 issue 或 pull request(`close_issue`、`close_pr`)并合并(`merge_pr`,使用 `github_actions.merge_method`)。只能使用 `github_actions.allowed` 中的名称(默认 `rerun_failed` 和 `cancel`)。**每个操作都单独确认**:页面会精确显示将发送的内容(方法和端点),在你用一次性令牌确认该计划之前不发送任何东西。GitHub 令牌需要相应权限(运行需 `workflow`,issue 和 pull request 需 `repo`;否则显示 GitHub 的拒绝)。每次尝试都会写入 `github_actions_log.jsonl`。AI 助手无法启动其中任何一个。

## 用 act 在本机运行工作流

开启 `act.enabled` 并在 `act.allowed` 中写入 `仓库:文件.yml:事件` 条目(三者都需精确)后,确认确切的命令行,按钮就会在本地克隆上运行 `act`。不提供真实密钥(密钥、变量、环境和输入文件均为空,环境最小化且没有任何令牌),输出实时显示,一次只运行一个,有时间上限 `act.timeout_seconds`,你也可以停止它。

## 构件的本地副本

开启 `mirror.enabled` 并在本机设置 `mirror.folder` 后,已完成运行的构件会被复制到那里(每个周期 `mirror.max_per_cycle` 个,文件夹上限 `mirror.max_mb`,保留 `mirror.keep_days` 天),每个仅一次,文件夹内的名称经过清理。

## 自托管运行器

开启 `runners.enabled` 后,设置 > 高级会把每个运行器显示为空闲、忙碌或离线。磁盘和负载只显示在 `runners.metrics`({名称:本机或私有地址上 node exporter 的地址})列出的运行器上。

开启 `runners.model.enabled`(默认关闭,只读)后,作业的标签(`runs-on`)用于区分 **GitHub 托管**、**大型**、**第三方付费**和**自托管**运行器。可用 `runners.model.thirdparty_labels`(标签的开头)、`runners.model.large_labels`(您自己的大型运行器组的名称或模式)和 `runners.model.self_labels` 添加自己的名称。每个周期最多读取 `runners.model.jobs_per_cycle` 个未完成的运行(每个一次请求)。`GET /api/runners/model` 和设置 > 高级随后显示按类型的队列(等待中的作业和最长等待)、`finops.jobs_per_cycle` 抽样的已完成运行按类型的分钟数与成本(第三方的一分钟仅在设置了 `runners.model.thirdparty_usd_per_minute` 时才有价格;GitHub 从不对其计费)、过去一小时启动 `runners.model.runaway_runs_per_hour` 次或更多的工作流(拉取请求不计;监视器只能看到每个仓库抽样的运行,上限高于该样本时会说明),以及等待自托管运行器达到 `runners.model.queue_warn_minutes` 分钟或更久的作业及原因:没有在线运行器具有其标签、所有匹配的运行器都在忙,或空闲运行器不接取(`runners.enabled` 关闭时为 `unknown`)。失控的工作流和无人接取的自托管队列都是警报(`runners.model.alerts`,级别 `runners.model.alert_level`)。 运行器列表、账户的组织、更新通知和每个来源的配额由周期读取(最多每五分钟一次,或按各自的节奏);`GET` 路由只显示已读取的内容,绝不启动 `gh`。 当 `runners.model.observed_reads_per_cycle` 大于 0(默认关闭)时,监控器还会读取在自托管运行器上有作业的仓库的工作流文件,并把文件所写的内容(`runs-on`)与作业实际运行的位置对照:`GET /api/runners/model` 中的 `observed` 列出每个这样的仓库、看到的运行器,以及值得留意时的原因(来自表达式或没有任何文件声明的运行器,或公开仓库中的自托管运行器)。只能看到未完成运行的作业,仓库每六小时重新读取一次,文件仅在变化时才读取;不会写入任何内容。

**已知限制。** 类型由作业的标签读取,因此您重命名的运行器组需要 `runners.model.large_labels` 或 `runners.model.self_labels`。仓库的套餐可能是 `unknown`(私有或免费仓库不会说明):此时配额显示为无套餐上限,而不是报错。

## OpenTelemetry

开启 `otlp.enabled` 并设置 `otlp.endpoint`(HTTPS,或本机上的 HTTP)后,已完成的运行作为追踪发出,页眉数字作为指标发出(JSON 格式的 OTLP/HTTP),每个运行仅一次。只发送仓库、工作流、分支、事件、结论和时长。

## 组织与成本

- `organizations.discover` 在设置 > 基础中列出登录账户的组织。要监视其中一个,请启动第二个监视器并把 `github_owner` 设为它。
- `finops.jobs_per_cycle` 大于 0 时,每个周期读取这么多已完成私有运行的作业标签,使分钟数使用正确的倍率(Linux、Windows、macOS 以及 `quotas.json` 中的大型运行器),而不是假定的单一系统。开启账单报告(`quota.billing_api`)后,还会显示 Codespaces 和 Packages 的费用、已用存储,以及超出包含分钟数部分的价格。

## 对真实服务进行检查

`python tools/manual_check_live.py`(在仓库中)会读取你令牌的权限范围、账单报告、组织、运行器和 `gh copilot` 的参数,并请求正在运行的监视器通过你的渠道发送测试消息。它从不索取密钥。

## 安全说明（开启任何功能前请先阅读）

- **网络模式**：仅在可信网络中使用。访问令牌不能代替加密；在普通 HTTP 下，令牌和数据以明文传输。请在前面放置 HTTPS 代理（并设置 `listen.secure_cookie`），或为监视器提供你自己的证书和密钥（`listen.tls_cert_file`、`listen.tls_key_file`）：这时它自己提供 HTTPS（TLS 1.2 或更高），文件无法使用时拒绝启动。请优先选择本机的一个私有地址，而不是所有接口。只接受 IPv4 地址。首次访问后地址栏中的令牌会被清除，Cookie 为 HttpOnly、SameSite=Strict（HTTPS 下还有 Secure）。一分钟内发送 `listen.max_failed_attempts` 次错误令牌的地址会被拒绝五分钟。`/metrics` 和 `dashboard.json` 会列出你的仓库：网络模式下它们同样需要令牌。
- **GitHub 上的操作**：**默认关闭，每个操作一次确认，封闭列表**（重新运行运行或作业、取消、关闭 issue 或 pull request、在你列入时合并 pull request）。删除分支或仓库、密钥和设置**不在**其中。AI 只能提出更小的列表（`rerun_failed`、`rerun_run`、`close_issue`），并且从不合并。
- **act**：默认关闭，每次运行都要确认，`仓库:文件:事件` 封闭列表，不使用真实密钥。克隆必须是工作区内的真实文件夹：作为指向别处的链接的文件夹会被拒绝，除非开启 `act.allow_symlinks`。时间限制和停止会结束该运行启动的整个进程树，并删除它创建的 `act-` 容器。
- **你自己的令牌**在有系统存储时保存在其中；普通文件（权限 600）是最弱的存储。它只交给 `gh`，从不交给 `act` 或你的命令。`--doctor` 显示存储位置，从不显示令牌。
- **应避免的组合**（`--doctor` 会指出）：在所有接口上开启网络模式；网络模式开启时 AI 操作可执行；网络模式开启时使用 `act`；令牌保存在普通文件中。
- MCP 服务器只通过标准输入输出通信；切勿放在网络端口之后。

`listen.trusted_proxy`(默认关闭):仅当同一台计算机上属于你自己的反向代理是唯一入口时使用。此时失败的尝试会计入 `X-Forwarded-For` 的最后一个地址(你的代理追加的那个;在 nginx 中为 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`),而不是代理本身,并且仅对到达时没有可用 `X-Forwarded-For` 的请求,再把它们合计计数,上限为三倍(这个共同的锁定绝不会拦下带有正确令牌的请求)。监控会相信任何经回环地址到达的连接上的该请求头,因此绝不要与位于另一台机器上的代理一起使用;如果其他人可以直接访问监控,请保持关闭。声明了代理(`listen.proxy_public_host`、`listen.secure_cookie` 或 `listen.trusted_proxy`)时,从主端口到达的任何请求都不算作本机;`listen.local_port`(0 = 关闭,否则为 1024 到 65535)会为在运行监控的电脑前的人再打开一个只监听 `127.0.0.1` 的端口(见部署指南)。 如果代理位于另一个容器或另一台机器上，请在 `listen.trusted_proxies`（`MONITOR_TRUSTED_PROXIES`；在 Docker Compose 文件中为网络 `MONITOR_SUBNET`）中列出其地址或网络：来自这些地址或本机的连接，其 `X-Forwarded-For` 会被信任用于统计尝试次数；这绝不会使请求被视为本机。

## 刷新循环:心跳与看门狗

`/api/data` 还会返回 `loop`:刷新周期所处的阶段(`collect`、`maintain`、`publish`、`log`、`extras`、`idle`)、周期已运行的时间、最近一次成功的周期、最近一次错误及其阶段、重启次数,以及写日志或写给 AI 的简报时的任何问题。页面底部栏在周期过长时显示红色,在无法写入文件时显示警告。看门狗会在把所有线程的回溯写入 `actions_monitor_log.txt` 之后,在新线程中重启超过 `watchdog_minutes`(默认 10,0 表示关闭)的周期。

## 没有管理员时网络模式不会启动

当 `auth.enabled` 与 `listen.network` 都开启而尚无用户时，监控器不会启动，并说明后续步骤：第一位管理员只能在本机创建，因此请先关闭 `listen.network` 并启动监控器（只监听本机），打开页面创建管理员，然后开启 `listen.network` 并重新启动。本地模式（127.0.0.1）始终可以启动。

## 最新功能的开关

以下所有功能均在本地且只读，除非另有说明，默认都是关闭的。每项在页面(? 按钮)和本文件夹中都有指南。 (经验记录默认开启，只写入本地文件；其余均关闭)

- `lessons.enabled` - docs/LESSONS_zho.md
- `savings.webhook_first`, `savings.feeds.enabled` - docs/QUOTA_zho.md
- `sentinels.collab.search_api` - docs/COLLAB_zho.md
- `logs.failed_step.enabled`, `github_app.share_reads` - docs/EXTRAS_zho.md
- `reports.workflow_hygiene.enabled`, `reports.queue.enabled`, `reports.release_view.enabled`, `reports.supply_chain.enabled` - docs/EXTRAS_zho.md
- `ai.skill` - docs/SKILLS_zho.md
- `ui.orientation`, `ui.screen1_tabs`, `ui.now_sort`, `ui.alerts_sort`, `ui.remember_folds` - docs/SCREENS_zho.md
- `ports.complete`, `ports.lite` - docs/DEPLOYMENT_zho.md
- `notify.users.enabled` - docs/NOTIFICATIONS_zho.md

## 符合 CI/CD 约定的 OpenTelemetry 和每个作业一个 span

OpenTelemetry 导出的两个开关（`otlp.*`，默认均关闭）让 trace 在后端更好用。`otlp.cicd_conventions` 会给每次运行的 span 加上 OpenTelemetry CI/CD 语义约定的属性（`cicd.pipeline.name`、`cicd.pipeline.run.id`、`cicd.pipeline.run.url.full`、`cicd.pipeline.result`、`cicd.pipeline.run.attempt`、`vcs.repository.name`、`vcs.repository.ref.name`），并把 span 命名为 `RUN <workflow>`；`gha.*` 属性保留。`otlp.job_spans` 为每个已完成的作业发送一个 span（`TASK <job>`），在同一条 trace 中作为其运行 span 的子 span，带有 runner、其组、标签、排队时间和结果；它需要 webhook，因为作业来自已签名的 `workflow_job` 事件（webhook 从未见过的作业没有 span）。其余不变：span 仍不包含标题、作者、提交信息或日志。

## 多个工作区

`workspaces.list` 保存 `名称=文件夹` 形式的条目（本机上的文件夹，绝不是网络地址），`workspaces.active` 指定监视器用于本地克隆、审计和签名记录的那一个。适用于想只改一个词就切换的第二组克隆（另一个组织、另一台计算机的副本）。环境变量 `MONITOR_ROOT` 优先于两者，`workspaces.active` 优先于 `workspace_root`。列表为空（默认）时一切不变。`monitor_cli.py toolbox workspaces` 会列出它们并说明正在使用哪一个。
