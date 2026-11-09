<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 更新日志

工具本身(监视器 + 哨兵 + 批处理工具)的版本,采用自己的语义化版本号。源文件是英文的 CHANGELOG.md,本文件包含相同的版本和章节。

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

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **Alerts for AIs**: the monitor writes a local, read-only feed (`ai_alerts.jsonl`, one line per event, and `ALERTS_BRIEF.md`, rewritten at every cycle, 2 KB by default) with one alert per red workflow: stable id, severity, probable cause told apart as real or transient with editable rules, suggested action, and a state (open, acknowledged, resolved by itself when the workflow turns green). Everything goes through a cleaner of tokens, keys, e-mail addresses, IP addresses and home folders. `GET /api/ai/brief` and `GET /api/ai/alerts`, an optional read-only MCP server (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`, and `ack_alert` with `--allow-ack`), a notification when a new REAL alert appears, an optional hook to an address on this computer (off), and an optional `ai_hint` in `ci_red.json`. New guide `AI_ALERTS.md` in eight languages.
- **Opt-in features, all off by default, each with its switch in Settings > Advanced** and tests that prove they refuse without the switch, the confirmation or the token: the network mode (a private address, an access token for every request, accepted host names, a persistent red bar, exposure keys changeable only from the computer itself); a GitHub token kept by the monitor in the secure store of the system (Windows DPAPI, macOS Keychain, Linux Secret Service, else a file with permissions 600) and never in a setting, a log or an answer, with a delete button; actions on GitHub (run again, cancel, close, merge), each confirmed on its own after showing exactly what will be sent; running a workflow here with `act` from a closed list, with no real secrets; a local mirror of artifacts; self-hosted runners (idle, busy, offline, optional disk and load); OpenTelemetry export (traces and metrics, OTLP/HTTP JSON); the organisations of the login; FinOps by job labels (Linux, Windows, macOS and larger runners), the price of the minutes above the included ones, Codespaces, Packages and storage from the billing report. New guide `ADVANCED.md` in eight languages, and `tools/manual_check_live.py` to try the real services by hand.
- `--doctor --json`; the doctor also reports busy ports, the allowance left, whether you have your own targets file, the one-use token and the exposure. The README of the package starts with the choice of launcher (complete, lite, batch, terminal, doctor, demo).
- The terminal application edits the simple settings (not the security ones) and has an AI tab; a persistent banner for settings that need a restart survives a reload; the header shows when the sentinel's A10 is paused for quota and how much of the minutes budget is used; the welcome is remembered by the server too.
- `redrule.py` ignores the dynamic runs of dependency updates like the dashboard does, and the shared cases of the rule are now a test fixture.

### 变更

- **The Help is complete in eight languages**: the roadmap, contributing, security and support documents are translated, the fixed labels of the changelog are translated and its entries are marked as English only, with a translated notice; `tools/make_help_index.py --check` and a test fail when a topic lacks a language. A search shows at most 30 hits and a huge document no longer holds the server thread.
- The red tile counts workflows in both editions and says in how many repositories. The lite edition inherits the refresh rhythm of the complete one at its first start.
- A passing failure (a TLS hiccup, a 5xx) is retried with an exponential backoff and is shown as an error only after three cycles in a row; the last picture stays.
- The terminal view of the lite edition no longer asks for the sentinel; the lite edition never loads the sentinel module (the local guard moved to `localguard.py`).
- `--demo` redirects every file it could write (logs, caches, event feed, history, welcome) to its temporary folder.

### 安全

- With `updates.check` off or `airgapped` on, the monitor makes no network request at all for the update notice (tested).
- Verified against the real GitHub API: the scopes of the token are read correctly, the organisations list and the billing report degrade silently (a login without the `user` scope gets "not found" and the monitor keeps the estimate).

## [1.6.3]

> 此版本的说明目前仅有英文,翻译将在后续版本中补充。

### 新增

- **About panel** (the **i** button of the header, in both editions): version, edition, author, licence, Python and system, links (repository, releases, changelog, documentation, issues), the files it uses (read only), the health of the server, the credits of the libraries and a button that copies the information for support (no secret, no token, the home folder shown as `~`). `GET /api/about`, and `--about` in the console.
- **Help panel** (the **?** button, the key `?`, and a "?" in the tab bar that opens the page of the tab you are on): the whole documentation (README, quick start, every guide, roadmap, changelog, contributing, security) as an index you can search, in the language of the page and in English where a document is not translated, served by the local server without Internet. It is built from the real documents by `tools/make_help_index.py` (`--check` in the CI), so no text is written twice; the markdown is rendered safely (everything escaped, no image loaded, only `http(s)` links and links to other documents). In the console: `--help-topics [TOPIC]` and `--help-search WORDS`.
- **Notice of a newer version**: a discreet badge in the header, a line in About, in the console and in `--doctor` when a newer release is published. One read-only request a day to the public releases page, through the same client as everything else (conditional read), never downloads or installs anything, sends nothing about you, ignores pre-releases, compares versions as numbers (1.6.10 is newer than 1.6.9), is silent offline and is off with `updates.check` or in an air-gapped installation (`airgapped`).
- **Settings > Basic**, the first tab: open the browser at start, the update notice, the air-gapped switch, the one-use token, the discovery options, the lifecycle rules, and the plan and quotas. Under it, what the monitor found in the account (owner, repositories found, watched, left out), the news and the suggested groups.
- **`--doctor`**: Python, `gh`, the login, the allowance, the network, the write permission of the folder, a free port, and the optional Docker, Rich and Textual; each failure comes with the exact command that fixes it, in eight languages.
- **`--demo`**: the page with invented data, with no `gh`, no login and no network; nothing of yours is read or written.
- **A welcome of three steps** the first time the page is opened (what it does, what it found in your account, where to go next).
- **Automatic discovery**: events for a new, vanished, archived or unarchived repository (console, Settings > Basic and, in the complete edition, the notifications); a suggested group when three or more unclassified repositories share a prefix, added only after your confirmation and with a copy of the file; lifecycle rules to leave out forks, empty and private repositories; an optional automatic refresh frequency that follows the real activity inside the call budget.
- **A one-use token** (`session_guard`, on by default) that the page asks for right before it saves a setting or confirms an action, and a **restart bar** on every tab while a saved setting waits for a restart.
- **Levels of the workflow linter** (information, warning, error) as filters in the page, and `Scripts` in the terminal application.
- **Quotas and plans for every kind of account**: your plan in Settings > Basic; the figures (included minutes as money, rates per system, concurrency, limits of a job and of a run, allowances of the API) live in `quotas.json`, which you can edit without a new version; billable minutes apart from clock minutes (public repositories cost none, private ones use the multiplier of Windows or macOS), a monthly projection marked as an estimate, a warning once per month at 75 % and 90 % of the included minutes through the notifications, jobs running and queued against the limit of the plan, jobs near the 6-hour limit and the kind of token read from GitHub's own headers (with the advice to log in when only 60 calls an hour are left). The real usage comes only from the optional, read-only billing report (`quota.billing_api`, off by default, silent on a 403 or 404). `GET /api/quota`.
- **Working modes: normal, fast and turbo** (`modes.py`, guide `MODES`): a selector with a gauge icon in the header and `--mode` / `--mode-minutes` in the console, in both editions. The presets live in the `modes` block of the configuration; before it starts the page shows the worst-case calls an hour, what the conditional reads usually save and how long the allowance left would last; it goes back to normal by itself when the time is up or when the allowance falls under `min_rate_remaining`, with a notice; without a login (60 calls an hour) fast and turbo are refused with the reason; it needs the one-use token, lives in memory and the console banner names it. `GET` and `POST /api/mode`.
- **After a secondary rate limit** the monitor waits at least a minute and then doubles the wait up to five minutes instead of retrying quickly.
- **The interactive terminal application** `tui_textual.py` (optional, `pip install textual`): tabs Summary, Repositories, Builds, Performance, Scripts and Settings (the basic switches), a filter, the levels of the linter, refresh, open in the browser, About and Help; `--lite` shows the lite tabs. The simple Rich view (`tui.py`, `--once`) stays and also has `--about` and `--help-topics`.
- **The edition is clear at a glance**: a start-up banner (`GitHub Actions Monitor LITE 1.6.3 · port 8766 · actions_monitor_lite.json · no sentinel · http://127.0.0.1:8766/`, or COMPLETE · port 8765 · sentinel on), the title of the window of the console and of the terminal, the tag `[LITE]` / `[COMPLETE]` in the status lines, in `--doctor` and in the terminal views, and the same title in the launchers.
- New guides in eight languages: **The sentinel and its checks A1-A13** (what it is, how it starts, the files it writes, how to read it, the exact rule, the setting and the action of each check and the twenty-five checks of A10; a test keeps the guide and the code in agreement), **Quotas and plans** and **Your first five minutes** (`FIRST_STEPS`); the migration guide has a block from 1.5.x to 1.6.x and the README has a chooser between the two editions.
- Tests for all of it (the semantic versions, the notice offline, switched off and air-gapped, the safe markdown, the index, the one-use token, discovery, `--doctor`, the quotas for public and private repositories, Windows and macOS, no token, Enterprise and a 403 of the billing report, the banner and the launchers).

### 变更

- The Settings page starts with the **Basic** tab; the guide `SETTINGS` is generated with it.
- The monitor lists the repositories of the account with their kind (archived, fork, private, empty); an older `gh` without those fields falls back to the plain list.

### 安全

- Nothing new writes to GitHub. The update notice, the billing report and the discovery are read only and switchable; none of them sends data about you. The Help and About panels are served from this computer and the support text carries no secret.
- Writing a setting, confirming an action of the AI assistant and adding a suggested group need the one-use token of the page.

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
