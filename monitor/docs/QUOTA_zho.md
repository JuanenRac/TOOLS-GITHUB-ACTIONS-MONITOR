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
GraphQL 不用于工作流的运行:它不提供这些数据。

## GitHub App 逐步设置
1. 在 GitHub 中依次进入 *Settings*、*Developer settings*、*GitHub Apps*、*New GitHub App*。无需 webhook。**只读**权限:Actions、Checks、Code scanning alerts、Commit statuses、Contents、Dependabot alerts、Issues、Pull requests、Secret scanning alerts 和 Metadata。
2. *Generate a private key*,把 `.pem` 保存在**任何仓库之外**,只有你能读取。
3. *Install App* 到你的账户,选择所有要监视的仓库。
4. 在监视器中:打开 `github_app.enabled`,填写 `github_app.app_id`(App 编号)和 `github_app.key_path`(只填密钥的**路径**)。`github_app.installation_id` 可留空。
5. 用 `GET /api/github-app/status`(仅限本机)检查:显示 App 的名称、安装、已授予的权限和配额,绝不显示密钥或令牌。doctor 会检查 `openssl`、密钥文件及其权限。

安全:监视器从不读取、复制、打印或记录密钥;它把路径交给 `openssl`,由其签发最长十分钟的 JWT。安装令牌有效一小时,保存在内存中并提前五分钟续期。**只有读取**使用它;写入和操作仍使用你的令牌。若 App 失败或缺少权限,会用你的令牌重新读取。页面会显示两份配额。

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

第二个账户(`extra_reader.enabled`、`extra_reader.file`)是只读账户,其细粒度令牌保存在任何仓库之外的文本文件中,只有你能读取;设置中**只保存**该文件的路径。监视器在使用时读取令牌,保存在内存中,绝不存储、打印或记录。读取会按各来源的剩余调用数(免费 `rate_limit` 调用的数值减去此后已做的读取)在你的登录、App 和第二个账户之间分配;被拒绝的来源会被排除五分钟,并用下一个来源重新读取。写入和操作从不使用它。它用于你自己的账户(例如对这些仓库有读取权限的自己的第二个账户),而不是用他人账户绕过限制的办法。
