<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | [🇪🇸 Español](ORGANIZATIONS_spa.md) | [🇫🇷 Français](ORGANIZATIONS_fra.md) | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# 组织与大型账号

如何让监视器指向一个组织,或指向拥有数百个仓库的个人账号,以及读取结果为空时该怎么办。

## 1. 能用的最小令牌

监视器只读取。使用 `gh` 的登录(`gh auth login`)或 `GH_TOKEN` 中的令牌,并只授予它所需的最小权限。

| 令牌类型 | 应授予的权限 |
|---|---|
| **经典**(个人访问令牌) | 私有仓库需要 `repo`(全部公开时 `public_repo` 即可),列出组织的仓库和团队需要 `read:org`。可选:`security_events`(代码扫描警报,面板 A3)、`read:project`(Projects 看板,面板 A9)。不需要 `workflow` 或任何写入范围。 |
| **细粒度** | 只有一个*资源所有者*:每个组织(或每个个人账号)创建一个令牌。仓库访问:全部,或所选仓库。只读权限:Metadata、Actions、Contents、Pull requests、Issues、Administration(ruleset 和分支规则)、Code scanning alerts、Dependabot alerts、Secret scanning alerts。组织可能要求所有者先批准该令牌。 |
| **GitHub App** | 使用 App 的配额而不是你的配额读取(参见 `QUOTA.md`)。 |

**个人账号**(`github_owner` 是用户)读取自己的仓库不需要以上之外的权限。你所属组织的仓库,需用资源所有者(细粒度)或范围(经典)包含该组织的令牌读取。

## 2. 单点登录(SSO)与私有仓库

如果组织强制使用 SAML 单点登录,经典令牌必须获得该组织的授权:在 GitHub 打开 *Settings > Developer settings > Personal access tokens*,选择令牌并点击 *Configure SSO > Authorize*。用 `gh auth login` 完成的登录,会在你于浏览器中接受该组织时获得授权。在此之前,GitHub 会返回 `403`(*Resource protected by organization SAML enforcement*),或者更糟:返回 `200` 但漏掉私有仓库(响应头 `X-GitHub-SSO: partial-results`),看起来就像一个仓库很少的组织。

看不到私有仓库的令牌会收到 `404`,与该仓库不存在时完全一样。因此空响应可能意味着:SSO 未授权、缺少范围或权限、该登录看不到的私有仓库,或者根本没有 Actions。下一节可以区分这些情况。

## 3. `--doctor` 会解释

`py -3 bin/actions_monitor.py --doctor`(也可用 `bin/monitor_cli.py doctor`)会进行三次小的读取,并报告两行:

- **该登录可以读取账号或组织**(`access`):`ok`,并给出登录名及其范围;或 `warn`,详情中给出原因:`sso`(未授权,或私有仓库被隐藏)、`rate_limited`、`scope`(缺少权限)、`not_found`(账号不存在或不可见)、`forbidden`;GitHub 拒绝凭据时为 `fail`。细粒度令牌没有可列出的范围,该行会如实说明。
- **每小时读取量在配额之内**(`estimate`):账号的仓库数,以及当前设置所需的每小时读取量,与个人令牌每小时 5000 次相比。这是不发起调用的估算:runs 的轮询(十分之一的仓库为热门,每 `refresh_seconds` 刷新;其余每 `cold_refresh_seconds`)、哨兵(最多 `sentinel.budget_per_hour`),以及在无克隆读取工作流文件时它们的份额。超过 60% 时为 `warn`。要降低:调大 `cold_refresh_seconds`、开启 Low 模式、监视更少的仓库(`repos`),或改用 GitHub App 读取。

凡是监视器读不到工作流文件的地方,同样的原因会连同仓库一起写出:哨兵面板 A13 会把它们列为带原因的*无法评估*,而不是无声的“没有数据”。

## 4. 监视不属于你的账号(无权限的观察者)

任何令牌都能读取任何账号的公开仓库,因此你可以用一个没有任何范围的令牌监视开源组织。观察者得不到、而监视器视为*未知*且绝不视为*正常*的内容:ruleset 和分支保护、Dependabot、代码扫描和机密扫描警报、设置,以及已禁用 Actions 的仓库的 run 列表。依赖这些内容的面板(A3、A6 的部分)对这些仓库显示为空或标记为无法评估。监视器从不写入任何内容,因此无需写权限。

## 5. 已知限制

- 个人令牌的配额是每小时 5000 次读取;安装在大型组织上的 GitHub App 配额更高(参见 `QUOTA.md`)。上面的估算是判断是否够用的最快方式。
- 监视器读取每个仓库最近 runs 的样本。每小时启动数百个 run 的仓库是通过该样本观察的,而不是逐个 run。
- GitHub 默认保留 run 的日志和构件 90 天;监视器无法读取 GitHub 已删除的内容。
- 细粒度令牌只属于一个所有者:监视两个组织需要两个令牌(监视器的两个账号,参见 `ACCOUNTS.md`)。
- 要求批准令牌或禁止经典令牌的组织,需要所有者先操作;监视器的任何设置都无法绕过这一点。
