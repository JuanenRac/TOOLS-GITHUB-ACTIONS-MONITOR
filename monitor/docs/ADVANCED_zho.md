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
- **用 POST 打开会话。** 除了带 `?access=` 的地址已弃用:默认仍可使用(已有的设置不会失效),且只对 `GET` 有效,但令牌会留在历史记录、日志和 `Referer` 中,监视器会用 `Deprecation` 响应头回应。关闭 `listen.query_access` 即可拒绝它,只用 `POST /api/access` 或请求头 `X-Monitor-Access` 打开会话。带 `?access=` 的地址仍然可用。当 `listen.host` 为 `0.0.0.0` 时,设置页顶部会显示红色横幅提醒。架构中标记为安全的所有设置(不仅是 `listen.*`、`github_token.*`、`act.*` 和 `github_actions.*`,还有 Webhook、AI 操作、通知、OpenTelemetry、镜像、runner 和输出)只能在本机修改。
- **在网络上监听时的第一步。** 先关闭 `listen.query_access` (这样令牌就不会出现在地址、历史记录或日志中; 用 `POST /api/access` 或请求头打开会话), 并在前面加上 HTTPS (`listen.tls_cert_file` 中的证书或 HTTPS 代理) 或 VPN。网络模式启动时若仍接受旧地址, 控制台会重复这条提示。

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

`listen.trusted_proxy`(默认关闭):仅当同一台计算机上属于你自己的反向代理是唯一入口时使用。此时失败的尝试会计入 `X-Forwarded-For` 的最后一个地址(你的代理追加的那个;在 nginx 中为 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`),而不是代理本身,并且还会按代理的所有客户端合计计数,上限为三倍。监控会相信任何经回环地址到达的连接上的该请求头,因此绝不要与位于另一台机器上的代理一起使用;如果其他人可以直接访问监控,请保持关闭。声明了代理(`listen.proxy_public_host`、`listen.secure_cookie` 或 `listen.trusted_proxy`)时,从主端口到达的任何请求都不算作本机;`listen.local_port`(0 = 关闭,否则为 1024 到 65535)会为在运行监控的电脑前的人再打开一个只监听 `127.0.0.1` 的端口(见部署指南)。
