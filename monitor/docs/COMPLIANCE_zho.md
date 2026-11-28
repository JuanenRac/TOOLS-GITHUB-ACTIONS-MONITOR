<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# 合规: 关于你的安装你能证明什么

这里的所有功能默认关闭, 仅用于完整版; 两项限制例外, 它们对监控器的每个进程都生效。其中任何一项都不是认证。

## 严格只读模式

`security.read_only_strict` (关)。开启后, 无论版型或其他设置如何, 都不向 GitHub 写入任何内容: 只启动 `gh` 的读取命令 (无法确定为读取的一律拒绝), 不执行 `git push`, 不运行 `act`, 对 GitHub API 只发 GET 或 HEAD 请求。它通过 Python 审计钩子在所有部件之下强制执行, 能看到启动的每个程序。只能在监控器所在电脑上修改, 放宽需要重启。「关于」窗口和 `/api/about` (`restrictions`) 显示是否生效。

## 网络策略

`security.egress_policy`: `default`、`github_only` 或 `none`; `security.egress_allow` 增加主机 (`名称`、`*.名称`、地址) 或 `program:名称`。`github_only` 时监控器进程只能访问 `api.github.com`、`uploads.github.com`、`GH_HOST` 指定的主机 (GitHub Enterprise) 以及你允许的目标; `none` 时只能访问本机, 且不启动 `gh`。自行联网的程序 (联网的 `git` 命令、`apprise`、`curl`、`docker`、密钥库工具) 不会启动。被拒绝的连接会以指明设置项的错误失败。当已配置的目标超出策略时 `python bin/monitor_cli.py doctor` 会失败, `doctor --egress` 列出所有目标。它不是防火墙, 不管理本机其他程序。密钥库工具包括 `sops` 和 `bws`：如果你的工具不需要网络，请把 `program:sops` 加入 `security.egress_allow`。存在但无法读取或理解的配置文件会收紧限制而不是放开：启用严格只读模式和 `github_only`（若其文本要求则为 `none`），直到修复并重启监视器；doctor 会指出。写在 `actions_monitor_lite.json` 中的 `security.*` 对精简版同样有效，并与主文件叠加。

## 合规报告

`python bin/monitor_cli.py compliance report` (可加 `--json`)、`GET /api/compliance/report` (管理员) 以及「安全」标签页末尾的方框。每行标明是**已检查** (监控器实际查看过) 还是**仅声明** (配置如此): 版本与支持、版型、认证与身份提供方、网络模式与 TLS、两项限制与目标、保留与法律保留、操作日志及其链、备份及其加密、静态加密 (无)、存储、插件、部署形式和配置档案。不含任何密钥、路径或姓名。`GET /api/compliance/state` 返回限制、保留表和导出状态。仍在生效的限制即使文件不再要求也会报告，无法查看的内容显示为 `unknown`。

## 保留与法律保留

事件、分析和评分沿用原有设置 (`retention.events_days`、`retention.analytics_days`、`retention.mode`)。其他类别除非指定天数否则永久保存: `retention.audit_days` (操作日志的整个轮转文件)、`retention.reports_days` (保留每个账户的最新报告)、`retention.ai_log_days`、`retention.backups_days` (保留最新备份)。每次清除都在操作日志中记一行。`retention.legal_hold` 停止一切删除: 事件、分析、评分、报告、备份、事件流和提示记录的裁剪, 以及日志的轮转和清除。AI 提议会自行过期; 已配对设备保留到你移除为止; 本版本不保存事后复盘、事故和备注。

## 操作日志的签名检查点

`audit_checkpoints.enabled` (关) 用本安装的密钥对链签名 (HMAC-SHA256): `config/audit_checkpoint.key`, 或用 `MONITOR_AUDIT_KEY_FILE` 指定的文件单独存放。第一行建一个检查点, 之后至少每小时、每 1000 行一个; 锚点同样签名; 末尾被截断后又写入新行时, 链中会留下记录。`python bin/monitor_cli.py audit verify` (`--audit-from N`)、`audit checkpoint` 以及 `audit purge --older-than-days N` (`--dry-run`), 后者删除整个轮转文件并为链的延续处签名。能读密钥的人就能签名: 请让它远离能写日志的人。

## 操作日志导出

`audit_export.enabled` (关), `audit_export.target` = `file` (`path`, 超过 `max_mb` 轮转)、`syslog` (`host`、`port` 6514、基于 TLS TCP 的 RFC 5424、`ca_file`) 或 `http` (`url`, POST JSON 行, 令牌取自 `token_env` 指定的变量)。内网地址需要 `audit_export.allow_private_targets`。日志本身就是队列: 目标未接收的行在其中等待; 超过 `spool_mb` 时 doctor 报告 `system.audit_export_lag`, 发送前已被轮转掉的行计为丢失。`python bin/monitor_cli.py audit export` 立即执行一次。仅对本机接收端做过测试, 未在真实 syslog 或 SIEM 产品上验证。

## 受支持的版本

仅支持最新发布的版本, 没有长期支持分支。当得知有更新版本时 doctor (`compliance_support`) 会提醒。

## 加固措施的证据

`[IMP]` 表示本仓库有测试实际检验该控制; `[PAR]` 表示只检验了一部分, 该行说明缺什么。清单见 `schemas/controls.json`, 有测试检查本表与所列测试是否一致。

| 控制项 | 状态 | 名称 |
|---|---|---|
| `sqlite_contention` | [IMP] | 多个进程写同一数据库 |
| `storage_migrations` | [IMP] | 存储迁移 |
| `retention_by_category` | [IMP] | 按类别保留与法律保留 |
| `incoming_webhook` | [IMP] | 入站 webhook: 签名、大小、时间 |
| `metrics_labels` | [IMP] | /metrics 的标签 |
| `timezone` | [IMP] | 时区与夏令时 |
| `read_only_strict` | [IMP] | 严格只读 |
| `egress_policy` | [IMP] | 网络策略 |
| `audit_chain` | [IMP] | 操作日志链与检查点 |
| `service_and_volume` | [PAR] | systemd 服务与大数据库 (网络文件系统未测试) |

## 已知限制

- 坐在监控器电脑前的 `viewer` 账户视为本地用户, 能看到完整路径。
- 入站 webhook 仅对 `workflow_run` 和 `workflow_job` 投递检查时间窗口。
- 在 `none` 或 `github_only` 下, 监控器启动的 Python 进程只有导入监控器时才应用同一策略; 你自己运行的程序不受约束。
- 本版本没有静态加密、长期支持分支和联邦功能。
