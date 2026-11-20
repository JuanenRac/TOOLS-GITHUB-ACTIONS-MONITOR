<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# 更多配额,更少消耗

GitHub 为每个账户提供有限的 **API 调用配额**,由使用它的所有工具共享。本指南说明其工作方式,以及监视器减少消耗的所有办法。

## 配额如何运作
- **REST**:每位用户每小时 5000 次调用(未登录为 60 次)。**GraphQL** 有自己独立的配额。Actions 中工作流的 `GITHUB_TOKEN` 也有自己的配额。**GitHub App** 有独立于你的配额,随其安装的仓库数量增长(130 个仓库时约每小时 10 000 次)。
- 什么计入、什么不计入:返回 `304 Not Modified`(ETag)的条件读取不计入;查询 `rate_limit` 免费;`git push`、`git fetch` 和 `git clone` 不使用 API。

## 监视器节省的办法
1. **条件读取**(ETag 和 `304`):`cache.etag.enabled`(默认开启);页面会显示节省了多少次读取。
2. **节省模式**:只每 4 分钟读取活跃仓库,其余每 30 分钟;`modes.auto_low`(开启)在剩余调用数低于 1000 时进入,超过 2500 或配额恢复时返回;预设在 `modes.low`。状态栏会说明数字可能较旧以及有多旧。
3. **中央面板作为基线**:`central.source`(`off`、`git`、`http`)读取你的个人资料仓库中由工作流用自己的令牌刷新的 `data/sentinel.json`,不消耗你的配额。`central.max_age_minutes`(120):比这更旧则为“滞后”,不被信任。
4. **配额用尽时只给一条通知**:读取暂停到配额恢复,页面只说一次“配额已用尽,HH:MM 恢复”(而不是每个仓库一个错误),并自动继续。
5. **用于读取的 GitHub App**(`github_app.*`),见下。
6. **面向安静仓库的 GraphQL(默认开启)**:`network.graphql_checks` 通过有独立配额的 GraphQL 分批(`network.graphql_batch`,默认 20)读取不活跃的仓库;一次调用可替代许多次 REST 调用。它只能看到默认分支的最后一次提交(未在其上运行的工作流不会列出),也没有时长、重试次数或其他分支,因此活跃的仓库以及 GraphQL 没有应答的仓库会在同一周期内继续通过 REST 读取。统计(批次、仓库、点数、转交 REST 的仓库)显示在摘要和面向 AI 工具的状态中。在真实账户上测量之后默认开启:分两批读取 40 个仓库,只用了 2 次调用而不是 40 次(减少 95 %),每个仓库都得到了应答,也没有错误。将 `network.graphql_checks` 设为 false 即可全部通过 REST 读取。

## GitHub App 逐步设置
1. 在 GitHub 中依次进入 *Settings*、*Developer settings*、*GitHub Apps*、*New GitHub App*。无需 webhook。**只读**权限:Actions、Checks、Code scanning alerts、Commit statuses、Contents、Dependabot alerts、Issues、Pull requests、Secret scanning alerts 和 Metadata。
2. *Generate a private key*,把 `.pem` 保存在**任何仓库之外**,只有你能读取。
3. *Install App* 到你的账户,选择所有要监视的仓库。
4. 在监视器中:打开 `github_app.enabled`,填写 `github_app.app_id`(App 编号)和 `github_app.key_path`(只填密钥的**路径**)。`github_app.installation_id` 可留空。
5. 用 `GET /api/github-app/status`(仅限本机)检查:显示 App 的名称、安装、已授予的权限和配额,绝不显示密钥或令牌。doctor 会检查 `openssl`、密钥文件及其权限。

安全:监视器只在签发最长十分钟的 JWT 时把密钥读入内存(用标准库签名,无需 `openssl`;`openssl` 只是后备),从不复制、打印或记录它。安装令牌有效一小时,保存在内存中并提前五分钟续期。**只有读取**使用它;写入和操作仍使用你的令牌。若 App 失败或缺少权限,会用你的令牌重新读取。页面会显示两份配额。

## 多个工具共享同一份配额时
账户下的所有工具消耗同一份每小时 5000 次调用。好的做法:给 `gh` 加一个小包装,带有几分钟的**共享缓存**和**保留额度**(剩余不到约 1000 次时拒绝调用,紧急情况除外),需要新数据的工作放在**配额恢复之后**,并且绝不使用 `gh run watch`(它会轮询)。例如:一个包装脚本把每次读取的结果存入以命令命名的临时文件并在 120 秒内重复提供,并在任何其他调用前先检查 `gh api rate_limit`。

## 不要这样做
不要用同一用户的多个账户或多个令牌绕过限制:这违反 GitHub 的规则,账户可能被封。请使用 App、中央面板和节省模式。

## 设置
| 设置 | 默认 |
|---|---|
| `cache.etag.enabled` | 开 |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | 开 / 1000 / 2500 |
| `modes.low.*`(`refresh_seconds`、`cold_refresh_seconds`、`runs_per_repo`、`hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / 空 / 空 / 空 |

## 故障排除与常见问题
- *“配额已用尽,HH:MM 恢复”*:请等待;监视器会自动继续。可能是其他工具在消耗,请查看它们。
- *数字较旧*:节省模式已启用(选择或自动);状态栏会说明。
- *App 不工作*:查看 `/api/github-app/status` 和 doctor:openssl、密钥路径、权限。
- *`git fetch` 消耗配额吗?* 不消耗。另见 [QUOTAS_zho.md](QUOTAS_zho.md)(套餐与分钟)和 [MODES_zho.md](MODES_zho.md)。

## “配额”标签页与第二个账户
与配额有关的一切都在一处:*设置*中的*配额*标签页。它汇集了模式(`modes.auto_low`、`modes.auto_low_enter`、`modes.auto_low_exit` 以及 `modes.low.*` 中的节省模式数值)、节省(`network.etag`,与 `cache.etag.enabled` 一起生效)、中央面板(`central.source`、`central.max_age_minutes`)、GitHub App(`github_app.*`)和**用于读取的第二个账户**。标签页中的按钮会显示每个来源(你的登录、App、第二个账户)的配额和恢复时间,测试 App 和第二个账户,列出 App 缺少的权限,并应用推荐值或默认值。

第二个账户(`extra_reader.enabled`、`extra_reader.file`)是只读账户,其细粒度令牌保存在任何仓库之外的文本文件中,只有你能读取;设置中**只保存**该文件的路径。监视器在使用时读取令牌,保存在内存中,绝不存储、打印或记录。读取会按各来源的剩余调用数(免费 `rate_limit` 调用的数值减去此后已做的读取)在你的登录、App 和第二个账户之间分配;被拒绝的来源会被排除五分钟,并用下一个来源重新读取。写入和操作从不使用它。它用于你自己的账户(例如对这些仓库有读取权限的自己的第二个账户),而不是用他人账户绕过限制的办法。该文件必须位于监控的账户文件夹内(`accounts/`,或 `MONITOR_ACCOUNTS_DIR` 指定的文件夹),并且绝不会通过链接读取;`extra_reader.any_folder`(默认关闭)可取消文件夹限制。取决于“谁在询问”的内容(你的账户、其组织、通知、对 `@me` 的搜索、`gh auth`、没有所有者的 `gh repo list`)始终由你自己的登录回答,只有简单的 `gh api ENDPOINT` 读取(最多带有 `--jq`、`--paginate`、`-H`、`-i` 和 `--cache` 选项)才会在各来源之间分配:任何其他调用都交给你的登录。

## openssl 程序与每个端口一个监控器

监控器先在 PATH 中查找 `openssl`，找不到时再查找 Git for Windows 存放它的位置（Program Files 以及用户 Programs 下的 `Git\usr\bin`、`Git\mingw64\bin`）和 macOS、Linux 的常用目录，因此从 `.bat` 或服务启动的监控器也能找到。`github_app.openssl_path`（程序的绝对路径）可手动指定。`/api/github-app/status` 显示 `openssl` 和 `openssl_path`，当使用的不是 PATH 中的那个时，doctor 会说明由哪一个签名。

在 Windows 上，监控器独占其端口（SO_EXCLUSIVEADDRUSE）：两个进程不能再同时监听 8765。如果在另一个监控器已在该端口应答时又启动一个，它会说明情况并退出，而不是去找别的端口。

## 配额分配：首选来源与保留量

默认情况下，每次读取都交给剩余调用最多的来源（用户、GitHub App、第二个账户）。`readpool` 块可在设置的“配额”标签页中改变这一点，默认值保持一贯的保守（`auto`，保留量 0）：

- `readpool.prefer.<类型>`（`auto`、`user`、`app`、`extra`）：某一类读取优先由哪个来源应答。类型由调用本身判定：`runs`（运行、工作流、检查）、`security`（代码扫描、Dependabot、密钥扫描）、`issues`（议题和拉取请求）、`history`（发布、提交、标签、内容）、`discovery`（组织、搜索、仓库列表）以及 `other`。若首选来源失败或低于其保留量，则由其他来源应答，用户排在最后。
- `readpool.reserve.<来源>`（0 到 4000）：该来源保留的空闲调用数。当某来源的剩余调用不超过其保留量时，只要有其他来源可用，监控器就不用它读取。用 `readpool.reserve.user` 可为你的工具和代理的 `gh` 给用户留出调用。
- `quota.failover`(默认关闭):返回 429 或“rate limit exceeded”的读取会改用另一个可读取的来源再读一次,用尽的来源在下一次免费检查之前视为已耗尽。所有来源都耗尽时,会显示该读取最后一份良好的副本及其时龄,而不是报错(`quota.failover_max_age_minutes`,默认 60,范围 1 至 1440;更旧的副本不显示)。限制绝不会被当作权限被拒,写入从不切换来源,`GET /api/quota-pool/status` 的 `failover` 块记录了它起作用的次数。

写入和操作始终使用用户的令牌。配额条和工作模式（快速和加速）按所有来源的总和计算：磁贴显示总和，其提示显示各来源的数值，配额标签页（状态）在用户、App 和第二个账户的配额旁增加一行总计。

## 减少读取：优先 webhook 与免费来源

这两种方式**默认关闭**，只作用于安静的仓库(其最近的运行都已结束且为绿色)。正在运行、为红色或被事件触及的仓库照常读取。

- `savings.webhook_first`：只要传入 webhook 保持活跃(在最近 `savings.webhook_window_minutes` 分钟内送达过事件)，安静的仓库就不会在其慢速轮次中被读取：有事情发生时 GitHub 会通知。每隔 `savings.webhook_full_minutes` 分钟仍会完整读取一次。没有活跃的 webhook 时一切照旧。
- `savings.webhook_live_per_repo`:把“在线”的判断细化到每个仓库。只有在最近 `savings.webhook_window_minutes` 分钟内收到过自己事件的安静仓库才会跳过缓慢读取;webhook 从未配置或已失效的仓库照常读取,其他仓库则被节省。它节省的读取更少,Webhook 面板会统计自身在线的仓库。默认关闭;需与 `savings.webhook_first` 一起使用。
- `savings.feeds.enabled`：在用 API 读取安静的仓库之前，先向不消耗配额的来源询问其默认分支的最新提交——提交的公开 Atom 订阅源、`git ls-remote`，或二者之一(`savings.feeds.method`：`atom`、`git`、`auto`)。如果它就是上次完整读取时的提交，仓库保持现状。每隔 `savings.feeds.max_age_minutes` 分钟无论如何都会完整读取一次。仅限公开仓库：对于私有仓库、出错或异常响应，仓库照常用 API 读取。离开本机的只有发往 github.com 的 GET 请求，绝不含密码，也不写入任何内容。监视器处于隔离网络(air-gapped)时不使用。

代价：在安静的仓库上，没有推送而开始的运行(定时任务、重新运行)要到下一次完整读取时才会被发现，而不是立刻。配额标签页(状态)显示自监视器启动以来每种方式节省的读取次数(每次约相当于一次 API 调用)：条件读取、GraphQL、优先 webhook、Atom 订阅源、git 和中央面板。

## 大型账户:运行列表覆盖什么,以及预算

每小时启动数百次运行的仓库,会在几分钟内填满 20-100 条的运行列表,较早的失败或很少运行的工作流就根本不在其中。监控器会如实说明,而不是显示成绿色:

- **覆盖范围**:仓库表显示每个列表回溯到多久以前。已满但回溯时间少于 `sampling.min_coverage_minutes` 的列表标记为“覆盖不足”;比请求数量短的列表为“完整”(包含全部历史);总数为 2,500 或 40,000 是 GitHub 停止计数的地方,因此显示为“至少”。`GET /api/data` 的 `sampling` 块带有同样的数字。
- **再看一次**:开启 `sampling.default_branch_probe` 后,已满的列表每次读取还会多发一次请求,获取默认分支的推送(不含拉取请求),使决定 main 是否为红色的运行不会被拉取请求和定时任务挤出。
- **查看仍在运行的运行**:开启 `sampling.active_probe` 后,已满的列表会再用两个轻量请求获取仍处于 `in_progress` 和 `queued` 的运行,避免在列表窗口之前开始的长时间运行被丢失或显示为已结束。每个已满仓库每次读取多两个请求;默认关闭。
- **A2 一并解决**:需要查询的工作流不少于 `sentinel.a2_resolve_batch_min` 的仓库,只请求一次其默认分支最新已完成的运行(最多 `sentinel.a2_resolve_batch_pages` 页,每页 100 条)并一并解决;该列表中没有的逐个查询。有 100 个以上工作流时只需几个周期,而不是每周期四个。
- **预算**:`sampling.api_budget_per_hour`(0 = 无)限制每小时对运行列表的请求数。超出后先读取有红色工作流的仓库(始终为它们保留预算的十分之一),其余等待,页面会说明有多少个。按仓库数量和间隔估算的每小时请求数,在达到 3,500(GitHub 每小时允许 5,000)或设置了预算时显示。

默认值不会改变仓库很少的账户:再看一次和预算默认关闭,“覆盖不足”标记只在已满列表回溯不到半小时时出现。

## App 已开启但没有被使用时

如果 `github_app.enabled` 已开启但 App 无法提供令牌，读取会继续使用你的令牌，额度是用户较小的那一个。这绝不会悄无声息：doctor 会带着原因变为黄色，失败会在被吞掉的失败列表中记录一次，额度标签页会显示一行 `GitHub App`，给出原因和正在使用的上限。原因：密钥无法读取或不是不带口令的 RSA 密钥（`key_unreadable`）、密钥无法签名（`sign_failed`）、App 未安装到该账户（`app_not_installed`）、GitHub 拒绝了令牌（`token_refused`）、App 已开启但缺少编号或密钥文件（`not_configured`）。同样的说明在 `GET /api/quota` 的 `app` 和 `GET /api/github-app/status` 的 `signer`、`code` 中。
