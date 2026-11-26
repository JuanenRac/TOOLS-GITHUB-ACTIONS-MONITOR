<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# 仓库与组织的安全态势

一组只读检查,查看仓库和组织的防护情况:Webhook、Actions 设置、扫描、分支、部署密钥、密钥年龄、应用和发布。不对 GitHub 做任何更改。适用于 Complete 和 Full 版本;默认关闭。

## 开启

开启 `posture.enabled`(设置 > 安全态势)。每周期读取少量仓库(`posture.repos_per_cycle`),每个仓库最多每 `posture.refresh_hours` 一次;会消耗 GitHub 配额。`posture.org_checks` 加入组织检查。

## 检查内容

每个发现项标明其在 OWASP CI/CD 十大风险和 CIS 软件供应链指南中的位置。该对应关系仅帮助阅读,并非认证。

| 领域 | 标识符 |
|---|---|
| Webhook 投递 | webhook.no_secret webhook.plain_http webhook.tls_off |
| Actions 设置 | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| 代码与依赖 | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| 分支 | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| 密钥 | deploy.write deploy.old stored.old |
| 组织 | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed |
| 运行器 | runner.not_hardened runner.coverage_lost |
| 发布版本 | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## 如实的覆盖范围

GitHub 拒绝或未应答的内容列为**未检查**,绝不视为正常,该区域此前的发现项予以保留。许多设置需要管理读取权限:报告列出各组检查所需权限及被拒绝项。Webhook 只保存主机名,密钥只保存名称和日期。发布版本与此前所见比较,因此首次读取仅作记录。跳过已归档仓库和复刻。

## 基线与选项

`posture.profile` 为 basic 或 strict。`posture.types` 按模式指定类型(`standard`、`library`、`internal`、`sandbox`),各有基线;`posture.skip` 排除检查。`posture.release_branches` 是需保护的分支模式。`posture.deploy_max_days` 和 `posture.stored_max_days` 设定年龄上限。需主动开启:`posture.audit_log`(组织审计日志,GitHub Enterprise)、`posture.review_sample`(未经批准即合并)、`posture.runner_runs`(实际运行中的加固步骤)。`posture.releases` 监视被替换的文件和移动的标签;`posture.release_window` 设定发布时段。

## 查看位置

哨兵区的安全标签页显示发现项、各仓库安全流水线成熟度、每日历史和权限。`posture.alerts` 将每个发现项放入告警页,可静音。API:`GET /api/posture`。命令行:

```
posture status
posture matrix
posture check --repo-name my-repo
```

## 限制

不读取成员的细粒度令牌(GitHub 仅向 GitHub App 列出),也不管理第二个写入型应用。组织检查仅用虚构应答测试过。
