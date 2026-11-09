<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 更新日志

工具本身(监视器 + 哨兵 + 批处理工具)的版本,采用自己的语义化版本号。源文件是英文的 CHANGELOG.md,本文件包含相同的版本和章节。

## [1.7.0]

完整版支持多个账户，每个账户都是独立的监视器，页面也认识它们。精简版保持不变：只有一个账户，甚至不会显示新的选项。

### 新增

- **多个账户**（仅完整版）。每个账户（个人或组织）都有一个文件夹 `accounts/<id>/`，其中有自己的 `actions_monitor.json`、缓存、事件、分析、哨兵状态和日志；`accounts/global.json` 是可选的（`default_account`、`enabled_accounts`），`MONITOR_ACCOUNTS_DIR` 可以移动该文件夹。ID 由小写字母、数字、`_` 和 `-` 组成（最长 40 个字符），因此始终是安全的文件夹名。没有 `accounts/` 文件夹时一切照旧：一个账户，文件放在代码旁边。
- **监督程序**（`accounts_supervisor.py`）：存在 `accounts/` 文件夹时，`python actions_monitor.py` 会在常用端口上启动一个小进程，为每个账户运行一个监视器（`account_child.py`），每个都在 `127.0.0.1` 上有自己的端口。某个账户的崩溃、响应缓慢或速率限制绝不会影响其他账户；停止的账户会以逐渐增加的等待时间重新启动（2、5、15、30、60，然后 120 秒），在此期间概览会显示它已停止。它不从 GitHub 读取任何内容，也不写入任何内容；停止它时会结束它启动的所有进程，在 Windows 上也一样。
- **账户的 API**：`GET /api/accounts`（概览）、`GET /api/accounts/<id>/status`，`/api/` 下的其他请求都会发往用 `?account=<id>` 或请求头 `X-Account-Id` 指定的账户（未指定则为默认账户；未知账户返回 404）。访问规则与单个监视器相同，更改的一次性令牌要向该更改所发往的同一账户申请。
- **一个 webhook 服务所有账户**：`POST /api/webhook` 是整个安装的唯一地址；监督程序只读取 `repository.full_name` 中的所有者，并把事件原样交给 `github_owner` 就是该所有者的账户，由该账户用自己的密钥验证签名。没有人监视的所有者会得到响应并被忽略。
- **`--accounts`、`--account <id>` 和 `--migrate-accounts [--apply]`**：列出账户、只运行一个账户作为普通监视器，并把旧布局迁移到 `accounts/default/`。迁移除非加 `--apply` 否则只是试运行，绝不移动或删除原文件，会拒绝第二次运行，也不会触碰精简版的文件。
- **多账户页面**：页眉下方有账户切换器，以及为每个账户显示一张卡片（状态、仓库、运行中、失败中）的 **所有账户** 一项。每个窗口都保留自己的账户和视图，它们从地址中读取。
- **按地址选择视图**（`?view=now|alerts|charts|repos|settings|live` 和 `?chrome=0`，没有页眉按钮、标签页和过滤器的屏幕，适合墙面或第二块显示器）。**实时**视图显示 GitHub 最近发送的事件、webhook 接收器的状态（绝不显示密钥）和工作模式选择器。`GET /api/live-status` 是它的数据来源。
- 用于图片的 `tools/demo_accounts.py`、八种语言的指南 `ACCOUNTS.md`，以及针对每项更改的测试（测试从 866 项增加到 914 项）。

### 变更

- 作为多个账户之一的监视器，其状态文件通过 `state_dir()` 放在自己的文件夹中；单个监视器依旧像以前一样把它们放在代码旁边。
- README 的图片已重新拍摄，八种语言的 README 展示了账户。

### 安全

- 除非开启网络模式，监督程序和各账户只在 `127.0.0.1` 上监听。webhook 没有主机检查，也没有访问令牌（隧道会改变主机），它的凭证仍然是 GitHub 的 HMAC；会话的 Cookie 绝不会传给账户。

### 修复

- 1.6.8 的实时视图没有接收器的状态：webhook 关闭或密钥少于 32 个字符时它什么也不说，现在会说明是哪一种情况。

## [1.6.8]

1.6.7 的 HTTPS 代理现在用真实代理进行验证,图片已重新拍摄,更新历史已翻译到 1.6.3。

### 新增

- `python tools/manual_check_live.py proxy 主机 [端口] [连接地址]`:通过你真实的 443 端口 HTTPS 代理检查页面能被放行(会话用正文中的访问令牌打开,Cookie 返回时带 `Secure` 和 `HttpOnly`),并且三个请求仍被拒绝(另一种协议、另一个主机名、带端口的名称)。它从 `MONITOR_ACCESS_TOKEN` 读取访问令牌,绝不打印,不带参数运行时会说明在 nginx 或 Caddy 中该怎么配置。
- `tools/demo_monitor.py --network` 按网络模式下的样子显示页面(持久的红色横幅,以及设置中针对所有接口的警告和新的代理名称),以便拍摄;演示仍然只监听 `127.0.0.1`。`tools/make_screenshots.py` 用它新拍了两张图:`web_network_now` 和 `web_network_settings`。
- 贯穿整条链路的测试:真实 TLS 上的客户端、终止 TLS 并转发不带端口的 `Host` 和 `Origin` 的反向代理,以及其后的真实监视器。它们检查从页面发出的更改能到达设置,没有 `listen.proxy_public_host` 时同样的请求被拒绝,错误的协议、名称或端口仍被拒绝,会话能打开且 Cookie 带 `Secure`,以及手动检查与代理一致并且绝不打印令牌(测试从 858 项增加到 866 项)。

### 变更

- 更新历史(帮助 > 更新日志)已将 1.6.8 至 1.6.3 翻译为其他七种语言(1.6.7 和 1.6.5 早已翻译);1.6.3 之前的条目在已翻译的提示下保留英文。
- README 的图片已重新拍摄,共 76 张,八种语言的 README 展示了设置的“高级”子标签页和网络模式的两张图片。
- `docs/MIGRATING.md` 新增了从 1.6.7 到 1.6.8 的部分,八种语言的路线图列出了剩余事项:更早的更新历史条目,以及需要你自己的服务才能完成的检查。

### 修复

- 1.6.7 的更新历史称只翻译了 1.6.7 和 1.6.5,并且代理只用检查逻辑验证过;本版本把其余内容翻译到 1.6.3,并如上所述对代理做了端到端验证。

## [1.6.7]

默认 443 端口上的 HTTPS 代理现在可以配合网络模式使用,并且更新历史有更多内容被翻译。

### 新增

- `listen.proxy_public_host`(设置 > 高级 > 网络,默认为空):默认 443 端口上的 HTTPS 代理的公开主机名,该代理转发的 `Host` 和 `Origin` 不带端口。此前检查会把两者与监视器的端口比较,因此这样的代理会被拒绝;现在这一个名称会被原样接受。它只在网络模式开启且会话为 HTTPS(直接 TLS 或 `listen.secure_cookie`)时生效,必须是普通主机名(带端口、路径、用户名、空格或 IPv6 字面量都会使其变为空),与架构中标记为 `secure` 的所有设置一样只能在本机上更改,其标签和帮助提供八种语言。
- 为本版本的每项更改添加了测试(测试从 843 项增加到 858 项,新文件检查检查逻辑、取值、架构和文本)。

### 安全

- 检查的例外被限制到最窄:只有这一个名称可以不带端口被接受,绝不接受其他不带端口的主机,绝不在普通 HTTP 下接受,并且 `Origin` 必须带有同一名称和 `https` 协议(其他协议、端口、路径、用户名或不同的主机仍会被拒绝)。代理名称绝不会出现在检查的公开状态中。

### 变更

- 更新历史(帮助 > 更新日志)已将 1.6.7 和 1.6.5 翻译为其他七种语言(1.6.6 早已翻译);更早的条目在已翻译的提示下保留英文原文,并将按从新到旧的顺序继续翻译。
- `docs/ADVANCED.md`(八种语言)现在说明默认端口上的代理,而不再说它不受支持;`docs/MIGRATING.md` 新增了从 1.6.6 到 1.6.7 的部分;设置指南和帮助索引已重新生成。

## [1.6.6]

修复网络模式和 `act` 的问题,完成 1.6.5 遗留事项,并把更新历史提供为八种语言。

### 新增

- 当网络模式在所有接口(`listen.host` = `0.0.0.0`)上监听时,设置页顶部显示常驻红色横幅(八种语言)。此前只有 `--doctor` 会提示。
- `POST /api/access` 配合 `{"token": "..."}`:把访问令牌放在请求正文中打开网络模式会话,因此令牌不会留在地址栏、历史记录或日志里。检查与其他请求相同(主机、来源、错误令牌后的锁定、恒定时间比较);返回的 Cookie 带 `HttpOnly`、`SameSite=Strict`,HTTPS 下还带 `Secure`。1.6.5 中带 `?access=` 的地址仍然可用。
- 监视器有意忽略的失败的计数器(`degraded.py`):每次在控制台输出一行结构化日志,按来源计数并保存在监视器旁的 `degraded.json`,新增 `--doctor` 检查项 `degraded`,关于面板中新增“被忽略的失败”一行。行为不变:它们仍然绝不会让监视器停止。
- 更新历史(帮助 > 更新日志)现在每种语言有一个翻译文件 `docs/CHANGELOG_<语言>.md`,版本和章节与英文源文件相同;任何翻译缺少某个版本时,`tools/make_help_index.py --check` 和测试都会失败。尚未翻译的条目会用读者的语言说明这一点。
- 本版本的每项更改都有测试(测试套件从 811 项增加到 843 项)。

### 修复

- **通过 HTTPS 的网络模式无法从页面使用。** 同源检查只接受 `http://` 来源,因此在直接 TLS 或 HTTPS 代理(`listen.secure_cookie`)下,浏览器自己发送的 `Origin: https://...` 被拒绝,所有更改(设置、确认)都返回 403。现在检查按会话的协议(https 或 http,绝不两者都接受)生成允许的来源,精确比较主机和端口,并拒绝格式错误的来源。已用真实的 TLS 服务器和测试生成的证书验证。
- `act`:Stop 现在会释放该次运行,因此进程不结束时下一次启动不会再永远返回 `busy`;迟到的工作线程绝不会影响更新的运行;输出管道和计时器在所有情况下(正常结束、超时、Stop、意外错误)都会关闭,测试套件不再产生 `ResourceWarning`。
- `tools/make_screenshots.py` 过去可能一声不响地结束:浏览器不再捕获管道并有时间限制,缺少浏览器或演示无法启动时会提示,`MONITOR_BROWSER` 可手动指定浏览器,有图片未生成时退出码为 1。

### 安全

- 在网络模式下,架构中标记为 `secure` 的每一项设置都只能从本机修改,而不再只是之前的四类(`listen.`、`github_token.`、`act.`、`github_actions.`):还包括 Webhook、AI 操作、通知、OpenTelemetry、镜像、runner、输出等。列表取自架构,因此新增的安全设置无需任何人记住就会被覆盖;测试会逐一检查。

### 变更

- README 和指南中的关于、帮助、现在、基础和高级的截图已重新拍摄。
- `docs/ADVANCED.md`(八种语言):使用自己的证书或在代理之后的 HTTPS、来源规则、通过 POST 打开的会话以及警告横幅。

## [1.6.5]

一个专注于完整性与安全的版本:没有大型新功能。无法证明的东西不再被视为安全。

### 新增

- 新设置,默认值均偏保守:`dispatch.required_ci`(文件中还有 `dispatch.required_ci_repos` 和 `dispatch.required_ci_profiles`)、`act.allow_symlinks`、`listen.tls_cert_file`、`listen.tls_key_file`、`listen.secure_cookie`、`listen.max_failed_attempts`、`webhook.replay_seconds`、`webhook.max_per_minute`;设置指南已重新生成。
- 为旧版本写入的批次提供 `finalize --accept-legacy`,并新增 `--doctor` 的 `risks` 和 `backend` 检查(八种语言)。
- 为本版本的每项更改添加了测试(测试从 729 项增加到 800 多项)。

### 安全

- **绿色提交需要必需的 CI。** 只有当必需的工作流文件在该提交上成功(默认 `ci.yml`;`dispatch.required_ci`、`dispatch.required_ci_repos`、`dispatch.required_ci_profiles`)、没有失败、超时或等待审批的内容(`action_required` 与失败一样会阻止)、没有仍在运行的内容且运行列表完整时(最多读取五页;更长的列表不算绿色),`gha_dispatch_all.py` 才会把提交标记为绿色。
- **`git fetch` 失败会停止该仓库的调度**,git 命令有时间限制,提交 ID 会被校验;过期的 `origin/main` 绝不会被当作证明。
- **目录不能离开自己的文件夹,也不能更改调度。** `tool` 必须是位于工具文件夹中的普通文件名(指向外部的链接同样会被拒绝);`extra` 只能包含 `-f key=value` 形式的工作流输入(绝不能是 `dry_run`、`ref`、`-R`、`--ref`);`finalize_flags` 只能是长选项;`gh workflow run` 的参数由经过校验的部分构建,并在批次触发时再次检查。
- **旧批次不会被盲目签名。** `finalize` 只会把批次记录了“基于已检查提交构建”的运行提供给签名。旧版本写入的批次为 `needs_review`;`finalize --accept-legacy` 会重新从 GitHub 读取该运行,只有当其提交与记录一致时才接受,给出警告,并在每次签名前要求输入 LEGACY 一词。
- **`act` 保持在工作区之内。** 克隆会被解析,且必须是工作区内的真实文件夹(链接、带 `..` 的名称或指向别处的 `.github` 都会被拒绝;`act.allow_symlinks` 允许指向克隆的链接)。时间限制和 Stop 会结束该运行启动的整个进程树(Linux 和 macOS 上是进程组,Windows 上是对其自身 PID 执行 `taskkill /T`),并删除该运行创建的 `act-` 容器。
- **网络模式**:直接使用你自己的证书和密钥提供 HTTPS(`listen.tls_cert_file`、`listen.tls_key_file`;TLS 1.2 或更高;若无法使用,监视器不会以普通 HTTP 启动),或在 HTTPS 代理之后使用 `Secure` Cookie(`listen.secure_cookie`);访问令牌会立即离开地址栏(重定向,无 `Referer`);发送过多错误令牌的地址会被拒绝五分钟(`listen.max_failed_attempts`);页面地址就是服务器监听的地址;只接受 IPv4 地址,设置和检查中都是如此;连接为普通 HTTP 时控制台会提示。
- **Webhook**:每次投递都需要其 `X-GitHub-Delivery` ID,重复的投递在 `webhook.replay_seconds` 内会被忽略;一个仓库每分钟最多引发 `webhook.max_per_minute` 个被接受的事件;`full_name` 中的所有者必须是被监视的账户;网络模式下,一个地址每分钟最多 120 个请求;被接受的事件会丢弃该仓库已保存的条件读取,并将其标记为下一个周期处理;带有异常字符的签名头会被直接拒绝。
- **MCP 服务器**:格式错误的消息(参数、实参、id、方法)只会为该消息返回错误,工具中意外的缺陷是不会终止服务器的内部错误,超过 64 KB 的行会被拒绝。
- **保存的 GitHub 令牌只交给 `gh`。** 它不再放入监视器的环境中,因此 `act`、你的通知命令和其他子进程都无法继承它。
- **GET 绝不写入。** 审计文件夹中日报的副本是带一次性令牌的 POST(`/api/sentinel/parte/save`);GET 上的 `?save=1` 已被移除。
- `--doctor` 会指出危险的组合(网络模式监听所有接口、网络模式开启时 AI 执行动作、网络模式开启时使用 `act`、令牌存放在明文文件中),并显示令牌的保存位置,但绝不显示令牌本身。

### 修复

- 通知的 `max_per_hour` 现在限制的是消息而不是事件(每个渠道一个单位,在同一个锁下一次性预订);无法发送的渠道不会预订任何额度。
- 同时保存两次设置不再丢失其中一次(进程内的锁和锁文件)。
- 签名队列的导出会说明为什么没有写入(被拒绝的驱动器或网络路径、文件夹而不是文件、系统错误),而不是只给出一个拒绝。
- 次级限制的等待和超时后的重试带有随机抖动。
- 在干净文件夹中解压 zip 的测试不再属于常规测试集:`make_release.py` 先带时间限制运行一次测试集,再把干净安装作为独立阶段运行,任一失败时都会显示 stdout 和 stderr。

### 变更

- 通知、Webhook、高级功能、输出、AI 警报和迁移的指南以八种语言说明了以上所有内容;`docs/MIGRATING.md` 新增了从 1.6.4 到 1.6.5 的部分。

## [1.6.4]

### 新增

- **面向 AI 的警报**:监视器写入一个本地只读的数据流(`ai_alerts.jsonl`,每个事件一行,以及每个周期重写一次的 `ALERTS_BRIEF.md`,默认 2 KB),每个红色工作流对应一条警报:稳定的 ID、严重程度、用可编辑规则区分为真实或暂时的可能原因、建议操作,以及状态(未处理、已确认、工作流变绿后自动解决)。所有内容都会经过清理器,去除令牌、密钥、电子邮件地址、IP 地址和主目录。提供 `GET /api/ai/brief` 和 `GET /api/ai/alerts`、可选的只读 MCP 服务器(`mcp_server.py`:`get_alerts`、`get_red_repos`、`get_run_failure`、`get_quota`,以及带 `--allow-ack` 的 `ack_alert`)、出现新的真实警报时的通知、指向本机地址的可选钩子(关闭),以及 `ci_red.json` 中可选的 `ai_hint`。新增指南 `AI_ALERTS.md`,提供八种语言。
- **可选功能,全部默认关闭,每项在 设置 > 高级 中都有自己的开关**,并有测试证明在缺少开关、确认或令牌时会拒绝:网络模式(私有地址、每个请求都需要访问令牌、接受的主机名、持久的红色横幅、只能在本机更改的暴露相关键);由监视器保存在系统安全存储中的 GitHub 令牌(Windows DPAPI、macOS Keychain、Linux Secret Service,否则为权限 600 的文件),绝不出现在设置、日志或响应中,并带有删除按钮;GitHub 上的操作(重新运行、取消、关闭、合并),每项在准确显示将发送的内容后单独确认;用 `act` 从封闭列表中在本地运行工作流,不使用真实密钥;制品的本地镜像;自托管运行器(空闲、忙碌、离线,可选磁盘和负载);OpenTelemetry 导出(跟踪和指标,OTLP/HTTP JSON);登录账户的组织;按作业标签的 FinOps(Linux、Windows、macOS 和更大的运行器)、超出包含分钟数部分的价格,以及账单报告中的 Codespaces、Packages 和存储。新增指南 `ADVANCED.md`,提供八种语言,并新增 `tools/manual_check_live.py`,用于手动试用真实服务。
- `--doctor --json`;doctor 还会报告被占用的端口、剩余额度、你是否有自己的目标文件、一次性令牌和暴露情况。软件包的 README 以启动器的选择开头(完整版、精简版、批处理、终端、doctor、演示)。
- 终端应用可编辑简单设置(不含安全设置),并带有 AI 标签页;需要重启的设置的持久提示在重新加载后仍然保留;页眉会显示哨兵的 A10 何时因额度而暂停,以及分钟预算已用多少;欢迎页也由服务器记住。
- `redrule.py` 像仪表板一样忽略依赖更新的动态运行,规则的共享用例现在是测试夹具。

### 变更

- **帮助现已提供完整的八种语言**:路线图、贡献、安全和支持文档已翻译,更新日志的固定标签已翻译,其条目带着已翻译的提示被标记为仅有英文;当某个主题缺少某种语言时,`tools/make_help_index.py --check` 和一项测试会失败。搜索最多显示 30 条结果,巨大的文档也不再占住服务器线程。
- 红色磁贴在两个版本中都统计工作流,并说明分布在多少个仓库。精简版首次启动时继承完整版的刷新节奏。
- 暂时性失败(TLS 抖动、5xx)会以指数退避重试,连续三个周期后才显示为错误;最后一次画面保持不变。
- 精简版的终端视图不再请求哨兵;精简版从不加载哨兵模块(本地防护已移到 `localguard.py`)。
- `--demo` 会把它可能写入的所有文件(日志、缓存、事件流、历史、欢迎页)重定向到它的临时文件夹。

### 安全

- 当 `updates.check` 关闭或 `airgapped` 开启时,监视器不会为更新提示发出任何网络请求(已测试)。
- 已对照真实的 GitHub API 验证:令牌的权限范围读取正确,组织列表和账单报告会静默降级(没有 `user` 权限范围的登录会得到“未找到”,监视器保留估算值)。

## [1.6.3]

### 新增

- **关于面板**(页眉的 **i** 按钮,两个版本都有):版本、版本类型、作者、许可证、Python 和系统、链接(仓库、发布、更新日志、文档、问题)、它使用的文件(只读)、服务器的健康状况、库的致谢,以及一个复制支持信息的按钮(不含密钥或令牌,主目录显示为 `~`)。`GET /api/about`,以及控制台中的 `--about`。
- **帮助面板**(**?** 按钮、`?` 键,以及标签栏中打开当前标签页对应页面的“?”):全部文档(README、快速入门、每份指南、路线图、更新日志、贡献、安全)作为可搜索的索引,使用页面的语言,未翻译的文档则使用英文,由本地服务器在无需互联网的情况下提供。它由 `tools/make_help_index.py`(CI 中的 `--check`)根据真实文档生成,因此没有任何文字被写两遍;Markdown 以安全方式渲染(全部转义、不加载图片、只允许 `http(s)` 链接和指向其他文档的链接)。控制台中:`--help-topics [主题]` 和 `--help-search 词语`。
- **新版本提示**:当有更新的发布时,页眉的低调徽章、关于中的一行、控制台和 `--doctor` 中都会提示。每天一次对公开发布页面的只读请求,使用与其他一切相同的客户端(条件读取),绝不下载或安装任何东西,不发送任何关于你的信息,忽略预发布版本,按数字比较版本(1.6.10 比 1.6.9 新),离线时保持安静,并可通过 `updates.check` 或在隔离安装(`airgapped`)中关闭。
- **设置 > 基本**,第一个标签页:启动时打开浏览器、更新提示、隔离安装开关、一次性令牌、发现选项、生命周期规则,以及套餐和配额。其下是监视器在账户中发现的内容(所有者、找到的仓库、被监视的、被排除的)、新动态和建议的分组。
- **`--doctor`**:Python、`gh`、登录、剩余额度、网络、文件夹的写入权限、空闲端口,以及可选的 Docker、Rich 和 Textual;每个失败都附带修复它的准确命令,提供八种语言。
- **`--demo`**:用虚构数据显示页面,无需 `gh`、登录和网络;你的任何内容都不会被读取或写入。
- **三步欢迎页**,首次打开页面时显示(它做什么、在你的账户中发现了什么、接下来去哪里)。
- **自动发现**:新增、消失、已归档或取消归档的仓库事件(控制台、设置 > 基本,在完整版中还有通知);当三个或更多未分类仓库共享同一前缀时给出建议分组,仅在你确认后添加,并保留文件副本;用于排除 fork、空仓库和私有仓库的生命周期规则;可选的自动刷新频率,在调用预算内跟随真实活动。
- **一次性令牌**(`session_guard`,默认开启):页面在保存设置或确认操作之前才会要求,并且在已保存的设置等待重启时,每个标签页上都有一条**重启提示条**。
- **工作流检查器的级别**(信息、警告、错误)作为页面中的过滤器,终端应用中新增 `Scripts`。
- **适用于各种账户的配额和套餐**:在 设置 > 基本 中选择你的套餐;各项数字(包含分钟数折算的金额、各系统的费率、并发数、作业和运行的限制、API 的额度)保存在 `quotas.json` 中,无需新版本即可编辑;可计费分钟与时钟分钟分开(公开仓库不收费,私有仓库使用 Windows 或 macOS 的倍率),每月预测标注为估算,在包含分钟数的 75 % 和 90 % 时每月通过通知提醒一次,正在运行和排队的作业对照套餐上限,接近 6 小时上限的作业,以及从 GitHub 自己的响应头读取的令牌类型(每小时只剩 60 次调用时会建议登录)。真实用量只来自可选的只读账单报告(`quota.billing_api`,默认关闭,遇到 403 或 404 时保持安静)。`GET /api/quota`。
- **工作模式:正常、快速和极速**(`modes.py`,指南 `MODES`):页眉中带仪表图标的选择器,以及控制台中的 `--mode` / `--mode-minutes`,两个版本都有。预设保存在配置的 `modes` 块中;启动前页面会显示最坏情况下每小时的调用次数、条件读取通常能节省多少,以及剩余额度能撑多久;时间到或额度低于 `min_rate_remaining` 时会自动回到正常并给出提示;未登录(每小时 60 次调用)时会说明原因并拒绝快速和极速;它需要一次性令牌,只存在于内存中,并且控制台横幅会点名它。`GET` 和 `POST /api/mode`。
- **遇到次级速率限制后**,监视器至少等待一分钟,然后把等待时间翻倍,最多到五分钟,而不是立即重试。
- **交互式终端应用** `tui_textual.py`(可选,`pip install textual`):概览、仓库、构建、性能、脚本和设置(基本开关)标签页,一个过滤器、检查器的级别、刷新、在浏览器中打开、关于和帮助;`--lite` 显示精简版的标签页。简单的 Rich 视图(`tui.py`、`--once`)依然保留,同样提供 `--about` 和 `--help-topics`。
- **一眼就能分清版本**:启动横幅(`GitHub Actions Monitor LITE 1.6.3 · 端口 8766 · actions_monitor_lite.json · 无哨兵 · http://127.0.0.1:8766/`,或 COMPLETE · 端口 8765 · 哨兵已启用)、控制台和终端的窗口标题、状态行、`--doctor` 和终端视图中的 `[LITE]` / `[COMPLETE]` 标记,以及启动器中的相同标题。
- 八种语言的新指南:**哨兵及其检查 A1-A13**(它是什么、如何启动、写入哪些文件、如何阅读、每项检查的确切规则、设置和操作,以及 A10 的二十五项检查;一项测试让指南与代码保持一致)、**配额与套餐**和**你的前五分钟**(`FIRST_STEPS`);迁移指南新增了从 1.5.x 到 1.6.x 的部分,README 中有两个版本之间的选择表。
- 为以上所有内容添加了测试(语义化版本、离线、关闭和隔离安装下的提示、安全的 Markdown、索引、一次性令牌、发现、`--doctor`、公开和私有仓库、Windows 和 macOS、无令牌、Enterprise 以及账单报告 403 时的配额、横幅和启动器)。

### 变更

- 设置页面以**基本**标签页开头;指南 `SETTINGS` 随之生成。
- 监视器列出账户的仓库及其类型(已归档、fork、私有、空);缺少这些字段的旧版 `gh` 会退回到简单列表。

### 安全

- 没有任何新内容会写入 GitHub。更新提示、账单报告和发现功能都是只读且可开关的;它们都不会发送关于你的数据。帮助和关于面板由本机提供,支持文本不含任何密钥。
- 写入设置、确认 AI 助手的操作以及添加建议的分组,都需要页面的一次性令牌。

## [1.6.2]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### 变更

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### 修复

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### 安全

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### 安全

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### 变更

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### 修复

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### 安全

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### 变更

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### 安全

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### 变更

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### 安全

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
