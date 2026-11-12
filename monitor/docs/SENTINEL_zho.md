<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# 哨兵及其检查 A1-A13

**哨兵**是完整版的后半部分。*监视器*显示此刻什么在运行、什么失败了；*哨兵*每隔几分钟检查整个账户，回答另一个问题：**什么需要人来处理**。它只读取 GitHub（从不写入），在本机保存一份简短的历史，并把发现的内容整理成十三项编号检查，即 **A1 至 A13**，每项一个信号灯。

**精简版不包含它。** `MONITOR_LITE_GITHUB_ACTIONS`（端口 8766）没有哨兵：该模块甚至不会被导入，相关接口返回 404。完整版（`MONITOR_GITHUB_ACTIONS`，端口 8765）会自动启动它；可用 `sentinel.enabled`（设置 > 哨兵）关闭。两个版本对“main 上为红”（A2）使用同一条规则，所以数字一致。

## 如何启动及其开销

它随完整版监视器启动，在同一进程的独立线程中运行，拥有自己的 GitHub 调用预算（`sentinel.budget_per_hour`，默认 600，以及 `sentinel.max_calls_per_tick`）。当 GitHub 剩余配额低于 `sentinel.min_rate_remaining` 时它停止请求，页面会显示因配额而暂停。它做的任何事都不会写入 GitHub。

## 它写入的文件（位于监视器旁，从不公开）

| 文件 | 内容 |
|---|---|
| `ci_red.json` | 架构 2：每个仓库中为红的工作流，以及发布等待签名的小时数。供其他工具使用的稳定约定，见 `CI_RED_SCHEMA_zho.md` 和 `CI_RED_BRIDGE_zho.md`。位置：`sentinel.ci_red_file`。 |
| `sentinel_history.json` | 每日合计（警报、红、候选），用于趋势和“自昨天以来新增”。 |
| `sentinel_cache.json` | 慢速读取的最近结果，重启后不必全部重新请求。 |
| `events_monitor.jsonl`, `events_state.json` | 事件流（什么变红、什么被修复），每个事件带稳定的 `code`。 |
| `SENTINEL_REPORT_*.txt` | 每日报告，若存在审计文件夹则保存其中。 |

## 如何解读

每项检查有五个级别之一：**ok**（无需处理）、**info**（值得了解）、**warn**（尽快查看）、**bad**（立即处理）和 **unknown**（尚无法检查：**unknown 绝不会显示为绿色**）。标签页顶部的报告用几行做总结；详情按检查展开。在监视器中被过滤掉的仓库不会被检查。

## 各项检查

| 检查 | 检查内容与确切规则 | 配置位置 | 级别与处理方式 |
|---|---|---|---|
| **A1** | **构建。** 运行中或排队时间超过限制的 run 视为*卡住*。同时列出带标签 `build-failed` 或 `build-stuck` 的未关闭 issue。事件为 `dynamic`（Dependabot 内部）的 run 会被忽略。 | `stuck_minutes` | 有卡住或未关闭 issue 时为 **bad**。打开该 run，取消或重跑；修复后关闭 issue。 |
| **A2** | **红色 CI。** 对每个工作流文件，取其在**默认分支**上**最后一次已完成**的 run：失败（`failure`、`timed_out`、`startup_failure`、`action_required`）即为红。`cancelled`、`skipped`、`neutral`、`stale` 的 run、进行中的 run 以及其他分支的 run 不代表任何结论，也不会掩盖更早的红。*连续*=连续为红的次数。当仓库的 run 列表与所要求的样本一样长时，某个工作流可能被挤到之外：哨兵会向 GitHub 询问每个这类工作流的最后一次 run。 | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | 有工作流为红时为 **bad**；仓库没有 run 数据或某个工作流无法解析时为 **unknown**（绝不为绿）。修复工作流或重跑；精简版显示相同数字，但因为要猜测默认分支而标为近似值。 |
| **A3** | **安全警报。** 每个仓库未关闭的 CodeQL、Dependabot 和密钥扫描警报及其严重程度，以及自历史上一日以来新增的数量。 | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | 任何密钥警报或 critical/high 警报为 **bad**；其他为 **warn**；加载中为 **unknown**。先轮换泄露的密钥，再更新或忽略其余。 |
| **A4** | **Dependabot 拉取请求。** Dependabot 未合并的 PR 及其存在时间、*大版本*跳跃和合并冲突；他人的 PR 只计数。 | `sentinel.stale_pr_days` (7) | 有大版本跳跃或冲突时为 **warn**；仅有 PR 时为 **info**。合并绿色的；对冲突的变基或关闭。 |
| **A5** | **发布。** (a) *候选*：CHANGELOG 的 `[Unreleased]` 下至少有 `candidate_min_entries` 条，且上一次发布早于 `candidate_days`（或没有发布）。(b) 发布工作流的*绿色构建*比上一次发布更新。(c) *等待签名*：超过 `pending_sign_hours` 仍未签名和发布的绿色构建；只有能用该生态系统的公钥验证通过的签名才算数。 | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | 有候选或待签名时为 **warn**；有未发布的绿色构建时为 **info**。切出发布或为构建签名。 |
| **A6** | **卫生。** 每个仓库：规则集 `protect-main` 为 ACTIVE、标签 `dependencies` 存在、必需文件存在（默认 README、LICENSE、CHANGELOG、SECURITY）、要求按 SHA 固定、`allowed_actions` 为 `selected`，且没有被 GitHub 停用的定时工作流。 | `sentinel.required_files`, `sentinel.hygiene_seconds` | 任一仓库有问题时为 **warn**；仍有未检查的为 **info**。每个问题都会指出修复方法。 |
| **A7** | **用量。** 每个仓库和生态系统最近 24 小时与 7 天的 Actions 分钟数、剩余的 API 配额，以及每个生态系统的*预算*：低于上限 80% 为 **ok**，达到 80% 为 **warn**，达到 100% 为 **over**。 | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | 配额低于限制或预算达到 80% 时为 **warn**。降低刷新频率或精简过长的工作流。 |
| **A8** | **轮次。** 读取审计文件夹中的审计和轮次文件（`sentinel.audit_files` 的匹配模式）并显示其状态。没有审计文件夹则为空。 | `sentinel.audit_files.*`, `audit_dir` | 仅 **info**。无需处理。 |
| **A9** | **路线图。** 各生态系统的 GitHub Projects 看板是否*有活力*：最近 8 天内已对账，且不早于其定义。需要 `gh` 的 `read:project` 权限；没有时标签页仅按定义工作，并说明缺什么。 | (fixed: 8 days) | 看板过期或从未对账为 **warn**；未配置为 **unknown**。 |
| **A10** | **Actions 与发布的表面。** 对克隆仓库进行的二十五项只读检查和少量冷调用，列在下表中。每项都有开关，必要时还有阈值。 | `sentinel.surface.*` | 按检查项，见下文。配额不足时暂停（报告会说明）。 |
| **A11** | **发布就绪度、生态系统健康度与固定版本。** 每个仓库的就绪度（条目、CI、版本、构建、签名、下一步）；每个生态系统 0-100 的健康分，按权重扣除红、卡住、密钥、高危警报、警报、陈旧 PR、未签名构建和卫生的扣分；以及落后的依赖固定版本。只有当 `min_coverage` 比例的仓库有数据时才显示分数。 | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | 分数低于 `warn_below` 为 **warn**；有落后仓库为 **info**；数据不足为 **unknown**。 |
| **A12** | **分析。** 每个工作流、其作业排队时间和每个步骤的 p50 / p95；比平时变慢的工作流（`analytics.slow_factor`）；*不稳定（flaky）*的工作流（失败后在同一提交上通过）。只是标签，绝不改变什么算红。 | `analytics.*` | 没有自己的信号灯。先看变慢的和 flaky 的。 |
| **A13** | **工作流 linter。** 对本地克隆的静态规则：`unpinned_uses`、`permissions`、`secrets_in_clear`、`injection`、`pr_target`。每个发现都有级别（信息/警告/错误）；注释 `# monitor-lint: ignore 规则 原因` 或 `lint.ignore` 可将其静音。 | `lint.*` | 取最严重发现的颜色。先修复错误；页面可按级别过滤。 |

## A10 的各项检查

它们都是给人的只读建议；监视器从不关闭 issue、合并拉取请求或发布版本。用 `sentinel.surface.checks.<名称>.enabled` 关闭其中一项。

| 检查 | 查找内容 | 默认 |
|---|---|---|
| `workflows_disabled` | 被手动禁用的 workflow | on |
| `dead_schedule` | 没有运行记录的定时任务 | on · days=14 |
| `unpinned_uses` | 未用 SHA 固定的 uses: | on |
| `broad_permissions` | 权限过宽（write-all） | on |
| `pr_target` | 检出 PR 代码的 pull_request_target | on |
| `stuck_concurrency` | 并发卡住（同一 workflow 有多个排队运行） | on · minutes=60 |
| `matrix_os` | 仅在矩阵中的一个系统上失败 | on · max_per_tick=4 |
| `artifacts` | 构建产物（artifact）开销 | on · max_mb=500, retention_days=30 |
| `required_checks` | 为红色或缺失的必需检查 | on |
| `release_assets` | 已发布但不完整的 release | on · recent_days=30, required |
| `tag_vs_version` | 发布标签与清单/CHANGELOG 版本对比 | on |
| `packages` | GitHub Packages | on |
| `drafts` | 被遗忘的草稿与预发布 | on · days=14 |
| `security_aged` | 按存续时间排列的严重/高危告警（仓库排名） | on · days=30 |
| `coverage` | 安全覆盖情况（CodeQL / Dependabot） | on |
| `secret_resolved` | 密钥扫描：未处理与已解决 | on |
| `dependabot_priority` | 按优先级排序的 Dependabot | on |
| `issue_close` | 可以关闭的 issue（仅为建议） | on |
| `milestones` | 各生态系统已过期的里程碑 | on |
| `pr_human` | 长期未处理的人工 PR | on · days=7 |
| `pr_workflow_touch` | 修改 workflow 或 CODEOWNERS 的 PR（优先） | on |
| `merge_queue` | 合并队列：已批准且 CI 为绿色 | on |
| `maturity` | 清单中的成熟度与证据对比 | on |
| `parity` | 8 种语言 README 一致性被破坏 | on |
| `attestation` | 构建证明 | on · max_per_tick=3 |

## 所有配置在哪里

上面的每个阈值都是设置页中**哨兵**、**表面检查（A10）**、**就绪度（A11）**、**文件夹与文件**、**分析**和**工作流 linter** 标签页的设置项，也是 `actions_monitor.json` 的键。带范围的完整列表见 `SETTINGS_zho.md`。帮助面板和 `--help-topics sentinel` 可离线显示本页。

## 第二个哨兵与警报列表

除了这个哨兵（CI），完整版还有 **Collab 哨兵**，它按自己的周期关注未关闭的 Issue 和拉取请求，从不向 GitHub 写入：[COLLAB_zho.md](COLLAB_zho.md)。**警报**标签页把两者的警报汇总成一个列表，可按来源和级别筛选，并提供会自行结束的本地静音（`alerts.mute_hours`）；`GET /api/alerts` 提供同一个列表。
