<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# 设置选项卡

设置选项卡（侧边栏中的设置项）可直接在页面上修改 `actions_monitor.json` 中的值，无需手动编辑该文件。
该选项卡使用页面的八种语言编写，外观与页面其余部分保持一致。

<!-- settings:begin -->
## 可以更改的内容

只有 `settings_api.py` 列表(架构)中的键。每个键都有类型和范围,页面会说明更改是需要**重启**监视器(循环只读取一次配置)还是**立即生效**。

该标签页按从常用到高级的顺序分为子标签页:此浏览器、基本、常规、刷新与限制、哨兵、表面检查(A10)、就绪(A11)、文件夹与文件、输出,然后是集成。每个子标签页内的设置按带标题的块分组;块的第一个字段是它的总开关,关闭时该块其余部分变暗且不可编辑。每个字段都显示单位(秒、分钟、小时、天、MB、次)、范围、徽标(需要重启/立即生效)、以保守默认值启动的安全选项徽标,以及一行帮助。搜索框会筛选所有子标签页的设置;每个子标签页统计未保存的更改;保存和放弃按钮始终可见;浏览器会记住上次使用的子标签页。标签页遵循键盘操作模式(方向键、Home、End)。

| 标签页 | 块与设置 |
|---|---|
| 此浏览器 | 页面语言、主题(自动/浅色/深色)、“现在”标签页的紧凑视图。它们保存在浏览器中,而不是文件中。 |
| 基本 | **启动**: `open_browser`<br>**更新**: `updates.check`<br>**监听网络**: `airgapped`<br>**套餐与配额**: `account.plan`, `quota.default_runner`, `quota.warn_percent`, `quota.alert_percent`, `quota.billing_api`<br>**安全**: `session_guard`<br>**发现**: `discovery.events`, `discovery.suggest_groups`, `discovery.auto_frequency`<br>**生命周期**: `discovery.hide` |
| 常规 | **身份**: `github_owner`, `language`<br>**范围**: `mode`, `repos`, `ecosystems`, `show_unclassified`, `exclude`<br>**历史**: `report_history_days` |
| 刷新与限制 | **活跃仓库**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**非活跃仓库**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**后台任务**: `issues_refresh_seconds`, `discover_refresh_seconds`, `discover_limit`, `max_workers`<br>**API 配额**: `min_rate_remaining` |
| 读取与缓存 | **条件读取**: `cache.etag.enabled`, `cache.etag.ttl_hours` |
| 哨兵 | **主要**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**给 AI 的警报**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**API 预算**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**发布与签名**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**红色查询(A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**拉取请求**: `sentinel.stale_pr_days`<br>**必需文件**: `sentinel.required_files`<br>**Actions 分钟数**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**审计文件**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra`<br>**议题和拉取请求**: `sentinels.collab.enabled`, `sentinels.collab.refresh_seconds`, `sentinels.collab.max_repos_per_tick`, `sentinels.collab.min_rate_remaining`, `sentinels.collab.repos`, `sentinels.collab.rules.issue_stale_days`, `sentinels.collab.rules.issue_critical_labels`, `sentinels.collab.rules.pr_review_pending_days`, `sentinels.collab.rules.pr_draft_max_days`, `sentinels.collab.rules.pr_conflict_days`, `sentinels.collab.rules.watch_external_comments`, `sentinels.collab.rules.ignore_labels`, `alerts.mute_hours` |
| 表面检查(A10) | **主要**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**被手动禁用的 workflow**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**没有运行记录的定时任务**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**未用 SHA 固定的 uses:**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**权限过宽（write-all）**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**检出 PR 代码的 pull_request_target**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**并发卡住（同一 workflow 有多个排队运行）**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**仅在矩阵中的一个系统上失败**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**构建产物（artifact）开销**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**为红色或缺失的必需检查**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**已发布但不完整的 release**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**发布标签与清单/CHANGELOG 版本对比**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**被遗忘的草稿与预发布**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**按存续时间排列的严重/高危告警（仓库排名）**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**安全覆盖情况（CodeQL / Dependabot）**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**密钥扫描：未处理与已解决**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**按优先级排序的 Dependabot**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**可以关闭的 issue（仅为建议）**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**各生态系统已过期的里程碑**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**长期未处理的人工 PR**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**修改 workflow 或 CODEOWNERS 的 PR（优先）**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**合并队列：已批准且 CI 为绿色**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**清单中的成熟度与证据对比**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**8 种语言 README 一致性被破坏**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**构建证明**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| 就绪度(A11) | **主要**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**健康度权重**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**固定版本**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| 文件夹与文件 | **本地文件夹**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**数据文件**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| 供其他工具使用的输出 | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**Grafana JSON**: `outputs.json.enabled`<br>**状态仪表板**: `outputs.dashboard.enabled` |
| 哨兵使用的外部 AI | **服务**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit`<br>**限制**: `ai.max_input_chars`, `ai.max_output_chars`, `ai.timeout_seconds`<br>**范围**: `ai.events`, `ai.allowed_repos`, `ai.answer_language`<br>**操作**: `ai.actions.enabled`, `ai.actions.execute`, `ai.actions.allowed`, `ai.actions.max_per_hour`, `ai.actions.ttl_seconds`<br>**给 AI 的警报**: `ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.hook.enabled`, `ai_alerts.hook.url`, `ai_alerts.hook.max_per_hour` |
| 入站 Webhook | **入站 Webhook**: `webhook.enabled`, `webhook.signing_state`, `webhook.record_events`, `webhook.live_events_keep`, `webhook.replay_seconds`, `webhook.max_per_minute` |
| 通知 | **主要**: `notify.enabled`, `notify.events`, `notify.max_per_hour`<br>**Telegram**: `notify.channels.telegram.enabled`, `notify.channels.telegram.token_env`, `notify.channels.telegram.chat_id`<br>**Discord**: `notify.channels.discord.enabled`, `notify.channels.discord.url_env`<br>**Slack**: `notify.channels.slack.enabled`, `notify.channels.slack.url_env`<br>**Matrix**: `notify.channels.matrix.enabled`, `notify.channels.matrix.homeserver`, `notify.channels.matrix.room`, `notify.channels.matrix.token_env`<br>**MQTT(本机)**: `notify.channels.mqtt.enabled`, `notify.channels.mqtt.host`, `notify.channels.mqtt.port`, `notify.channels.mqtt.topic`<br>**HTTP(本机)**: `notify.channels.http_local.enabled`, `notify.channels.http_local.url` |
| 分析 | **主要**: `analytics.enabled`, `analytics.keep_days`<br>**样本**: `analytics.min_samples`, `analytics.max_samples`, `analytics.jobs_per_cycle`, `analytics.steps`<br>**信号**: `analytics.slow_factor`, `analytics.flaky` |
| 工作流检查器 | **主要**: `lint.enabled`, `lint.refresh_seconds`, `lint.in_report`, `lint.ignore`<br>**uses: 未固定到完整的提交 SHA**: `lint.rules.unpinned_uses.enabled`, `lint.rules.unpinned_uses.severity`<br>**没有 permissions 块,或为 write-all**: `lint.rules.permissions.enabled`, `lint.rules.permissions.severity`<br>**看起来像写在文件里的密钥**: `lint.rules.secrets_in_clear.enabled`, `lint.rules.secrets_in_clear.severity`<br>**第三方文本被粘贴进 run: 脚本**: `lint.rules.injection.enabled`, `lint.rules.injection.severity`<br>**pull_request_target 检出了 PR 的代码**: `lint.rules.pr_target.enabled`, `lint.rules.pr_target.severity` |
| 高级(可选) | **监听网络**: `listen.network`, `listen.host`, `listen.token_env`, `listen.allowed_hosts`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.proxy_public_host`, `listen.max_failed_attempts`, `listen.query_access`<br>**自有 GitHub 令牌**: `github_token.enabled`, `github_token.store`<br>**对 GitHub 的操作**: `github_actions.enabled`, `github_actions.allowed`, `github_actions.merge_method`<br>**在本机运行工作流 (act)**: `act.enabled`, `act.allowed`, `act.timeout_seconds`, `act.allow_symlinks`<br>**批量构建**: `dispatch.required_ci`<br>**构件的本地副本**: `mirror.enabled`, `mirror.folder`, `mirror.max_mb`, `mirror.keep_days`, `mirror.max_per_cycle`<br>**自托管运行器**: `runners.enabled`, `runners.scope`<br>**OpenTelemetry 导出**: `otlp.enabled`, `otlp.endpoint`, `otlp.interval_seconds`<br>**组织**: `organizations.discover`<br>**分钟成本 (FinOps)**: `finops.jobs_per_cycle` |
| 终端视图 | **终端**: `tui.theme`, `tui.refresh_seconds` |

每项设置只出现在一个地方。只读:`webhook.signing_state` 仅说明共享密钥是否已定义;密钥本身永不显示。

监视哪些仓库:生态系统示例目录以一个 `rest` 组(前缀 `*`,“Everything else”)结尾,它接收其他组都不认领的所有仓库,因此默认不会遗漏任何仓库。如果你自己的目录遗漏了仓库,页面横幅会告诉你数量(“你的生态系统筛选器隐藏了账户 M 个仓库中的 N 个”)。

外部 AI:`ai.provider` 可以是 `ollama`(本机)、`openai-compatible`(任何 OpenAI 风格的端点,也适用于 Gemini 的 OpenAI 兼容端点和 OpenAI 本身)、`anthropic`(Messages API;模型由你选择)或 `copilot`(用你自己的登录运行 `gh copilot`;会消耗高级请求)。密钥从不保存:只设置环境变量的名称。见 AI_zho.md。

### 固定版本来源示例

只有列出了来源才会读取固定版本;列表为空时不读取任何内容,页面会如实说明。下面是一个已注释的示例:

```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```
<!-- settings:end -->

## 永远无法在页面上修改或查看的内容

令牌、机密、签名密钥、Webhook 机密、哨兵可以运行的命令（`sentinel.notify_command`）、AI 的 API 密钥（只能设置其环境变量的名称）以及其他工具的任何键：它们**不在模式中**，因此页面既不显示也不写入这些内容，提到其中任何一项的请求都会被拒绝。文件中的其他所有键都会原样保留。

## 保存的工作方式

1. 只发送发生变化的值，形式为 `POST /api/settings`，带有 `Content-Type: application/json`，请求体最大 16 KB。
2. 每个值都会按其类型和范围进行检查；只要有一个值无效，整个请求就会被拒绝，且不会写入任何内容。路径必须是不含控制字符的文本，不能是
   网络（UNC）路径，也不能位于 `D:` 盘。
3. 先前的文件会被复制到 `config_backups/actions_monitor-<time>.json`（保留最近十份副本）。
4. 新文件先写入临时文件，再移动覆盖旧文件（原子操作），因此崩溃也不会留下写了一半的文件。不是有效 JSON 的文件绝不会被页面覆盖。
5. 页面会说明哪些已保存的值需要重启，并一直显示横幅，直到您重启为止。

## 谁可以发出请求

只有同一台机器上的页面：服务器监听 `127.0.0.1`，并拒绝 `Host` 或 `Origin` 不是其自身地址的请求（与其他所有端点的检查相同）。
来自其他站点的表单无法访问它，因为请求必须是 JSON。

## 1.5.0 之前

工具的语言过去由系统语言决定；现在它们以英语启动，语言是一项设置（此处为 `language`、`MONITOR_LANG` 或 `--lang`）。
`parte_history_days` 现在是 `report_history_days`（旧名称仍会被读取）。
