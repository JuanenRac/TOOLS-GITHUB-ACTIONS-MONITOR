<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# 运维安装

面向需要连续运行数月的监视器（完整版）。涵盖完整备份、恢复、计划备份、带有 cron 可以信赖的退出码的 doctor，以及如何把它部署成设备化服务（systemd 或 Docker）。精简版（Lite）没有这些功能。

## 备份包

`python bin/monitor_cli.py backup create [文件]` 写出一个 `.zip`（格式 2），并在放到位之前先验证它。不给 `文件` 时，它会写入数据文件夹的 `backups` 文件夹（`ops.backup.dir`），名称为 `ghamon-backup-<UTC 时间>.zip`。不需要停止监视器：数据通过存储（文件或 SQLite）的原子读取获得，绝不会复制一个正在写入的数据库。

| 成员 | 内容 |
|---|---|
| `dump.jsonl` | 每个账户（其设置、哨兵的状态、小型文档、事件、分析、评分快照）和全局记录（用户及其可见的账户；绝不含会话） |
| `files.json` | 页面的设置和安装的列表（`targets.json`、`ecosystems.json`、`profiles.json`、静音），已清理；若存在可选模块的存储，也会一并保存 (`proposals.json`, `devices.json`) |
| `manifest.json` | 格式、产品版本、模式、计数，以及每个成员的大小和 SHA-256 |

**绝不会带上的内容：** GitHub 或 App 的令牌和密钥、密码、任何 `*_env` 变量的值（只有名称）、webhook 的密钥、AI 提供方的密钥、会话以及密钥库的内容。设置先经过白名单（与设置页面能显示的键相同），再经过清理，丢弃任何看起来像密钥的键以及任何看起来像令牌或私钥的文本。关闭 `ops.backup.include_config` 时，设置和列表完全不包含。恢复不会带回任何凭据：请重新设置 GitHub 登录（恢复清单会提醒）。

备份只有其所有者可以读取（模式 600），除非你要求，否则备份包不加密：见下文。

### 单个账户的备份包

`backup create --account ID [文件]` 写出一个账户的备份包：只包含它的转储（其设置以同样方式清理），别无其他。它不含任何用户或会话，也不含安装的设置或列表；清单中写明 `scope: account`。`backup verify` 会检查它只包含该账户，`backup restore 文件` 会恢复该账户（无需 `--account`），不触碰目标处的其他账户、用户或文件；仅当该账户在目标处已存在且没有 `--force` 时才会被拒绝。这是迁移或找回单个账户的方式。

### 加密备份（可选）

`ops.backup.encrypt`（单次备份用 `--encrypt`）用取自环境变量的密钥以 AES-256-GCM 加密备份包，变量名由 `ops.backup.key_env`（`--key-env 名称`）指定。密钥绝不是设置项，绝不会被写下，也绝不会出现在命令行上。它需要可选库 `cryptography`（`pip install cryptography`；监视器的核心仍然只用标准库）。没有该库，或密钥不足 12 个字符时，备份会被明确的消息**拒绝**，并且不写入任何内容：你要求加密时绝不会生成明文备份，也绝不会用更弱的方式加密。加密文件以 `.enc` 结尾；`verify` 和 `restore` 用同一个变量打开它。请把密钥与文件分开保存：没有密钥就无法打开备份。

## 验证、列出与状态

- `backup verify 文件` 重新读取备份包，检查每个成员的大小和 SHA-256 以及计数。被改动的字节、缺失的成员或清单未列出的成员都会被报告。`--deep` 还会把它恢复到临时文件夹并检查结果。
- `backup list` 显示文件夹中的备份；`backup status` 显示最近一次有效备份、其时间、计划以及最近一次失败。
- 第一种格式的备份包（2.1.0 之前生成）仍可验证和恢复。

## 恢复

`python bin/monitor_cli.py backup restore 文件`：先停止监视器（只要有监视器在其端口上应答，恢复就会被拒绝）。它先验证备份包，再写入账户和文件。

- 已有账户的存储会被拒绝，除非加上 `--force`（此时备份包的账户会覆盖写入；设置会被**合并**：备份包中没有的键绝不会被删除）。
- `--account ID` 只恢复该账户，其他账户和全局文件保持不变（仅当该账户已存在且没有 `--force` 时被拒绝）。
- `--to-dir 文件夹` 恢复到一个空文件夹（文件后端），不触碰当前安装：用于查看备份或迁移到另一台机器。
- 它会在数据文件夹中写入 `ops/restore_report.json`，并打印还需要做的事：重新设置 GitHub 登录、重新设置备份包未包含的设置、重启监视器以便监督进程启动每个账户、运行 doctor。

## 计划备份

有两种方式，选用其一：

1. 在监视器内：`ops.backup.enabled`（默认关闭）每隔 `ops.backup.interval_hours` 在独立线程中生成一份备份，保留最新的 `ops.backup.keep` 份（只会删除名称符合备份格式的文件），并把结果记录在 `ops/backup_status.json`。失败（磁盘已满、缺少密钥）会被记录并显示在“关于”面板和 doctor 中；它绝不会让监视器停止。
2. 用 systemd：`deploy/github-actions-monitor-backup.service` 和 `deploy/github-actions-monitor-backup.timer`（见下文）。

“关于”面板有一张**运维**卡片，显示模式（服务或本机）、最近一次有效备份、计划、当前生效的保留策略，以及按钮**立即备份**（管理员，从本机）。`GET /api/ops/status` 返回相同的数据；`POST /api/ops/backup` 生成一份备份。

## 按需清理

保留期清理每隔 `retention.interval_hours` 自动运行。要立即运行，有一个按钮（以及 `POST /api/ops/purge`），在 `ops.purge.enabled` 开启之前它**并不存在**（默认关闭）。请求默认是试运行（当前生效的策略以及将被删除的事件数），除非它指明 `dry_run` 为 false；而真正的清理在没有比 `ops.purge.require_backup_hours`（默认 24；0 表示不要求）更新的有效备份时会被拒绝。它会在保留期审计和操作日志中留下一行记录。

## doctor 及其退出码

`python bin/monitor_cli.py doctor [--strict] [--json]`（或 `python bin/actions_monitor.py --doctor`）检查安装，不改动任何内容，也不打印任何密钥。完整版在常规检查之后增加这些检查：

| 检查 | 检查内容 |
|---|---|
| `volumes` | 在数据、日志和备份文件夹中确实能写入、读取并删除一个文件（以 root 挂载或只读的 Docker 卷会在这里失败） |
| `supervisor` | 正在运行的监视器：监督进程和每个刷新周期的深度健康状况（不会启动任何东西） |
| `limits` | webhook 密钥已设置且至少有 `ops.doctor.webhook_min_length` 个字符（只比较长度），以及保留策略 |
| `sqlite_hot` | 以只读方式打开每个 SQLite 数据库：`quick_check`（默认）或 `integrity_check`（`ops.doctor.sqlite_check` 为 deep），在 `ops.doctor.sqlite_timeout_s` 处中止；断电后损坏的文件会失败 |
| `backup_age` | 最近一次有效备份与 `ops.doctor.backup_max_age_days` 对比 |
| `disk` | 数据卷的可用空间与 `ops.doctor.min_free_mb` 对比 |
| `metrics` | 当 Prometheus 输出开启且有监视器运行时，`/metrics` 有响应 |

**退出码（稳定，供 cron 使用）：** `0` 一切正常（没有 `--strict` 时，即使有警告也是 0）；`1` 至少一项检查失败；`3` 仅有警告且使用了 `--strict`（或 `ops.doctor.strict_exit`）；`4` doctor 本身无法运行。这些是 doctor 的退出码；`monitor_cli.py` 的其他命令保留各自的退出码。示例：`0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true`，并对非 0 的任何退出码发出告警。

## 作为设备化服务

**systemd**（无容器）：按 `deploy/github-actions-monitor.service` 中的注释操作，然后安装备份单元及其定时器：

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

要使用加密备份，请把 `ops.backup.key_env` 所指的变量放进 `/etc/github-actions-monitor/env`（模式 600）。定时器每天运行 `backup create`；备份无法生成时其退出码为 1。

**Docker：** `deploy/compose.yaml` 把备份放在独立的卷中（`/data/backups` 处的 `monitor-backups`），这样丢失数据卷不会连带丢失备份。用 `docker compose exec monitor python bin/monitor_cli.py backup list` 和 `docker cp` 取出文件，并在已停止的容器中或用 `--to-dir` 恢复。TLS 由 `deploy/Caddyfile` 的 Caddy 续期。

**升级时不丢失账户：** `backup create` → `backup verify 文件` → 停止监视器 → 替换产品文件夹（`config/`、`data/`、`logs/` 和 `ai/` 属于你，会被保留）→ `doctor` → 启动。出问题时用 `backup restore 文件`。**干净地卸载：** 停止并禁用单元，移除定时器，然后删除产品文件夹；只有想丢弃数据时，才删除 `config/`、`data/` 文件夹或 Docker 卷。

## 设置

全部位于“设置”标签页（文件夹和文件）以及 [SETTINGS_zho.md](SETTINGS_zho.md)：`ops.backup.*`（enabled、dir、interval_hours、keep、include_config、compress_level、encrypt、key_env）、`ops.purge.*`（enabled、require_backup_hours）和 `ops.doctor.*`（strict_exit、backup_max_age_days、min_free_mb、sqlite_check、sqlite_timeout_s、webhook_min_length）。每个开关默认关闭或取保守值，与安全相关的（计划备份、包含设置、加密、清理）都有相应标记。

另见 [STORAGE_zho.md](STORAGE_zho.md)（后端和保留策略）、[DEPLOYMENT_zho.md](DEPLOYMENT_zho.md)（服务、容器、TLS）和 [CLI_zho.md](CLI_zho.md)。

## 监视器监视自身的内存和线程

每隔 `selfwatch.interval_seconds`（60）秒，监视器读取自身的常驻内存、线程和处理器使用情况，并在 `/api/health` 中以 `selfwatch`（`state`：`ok` 或 `high`）显示。当内存超过 `selfwatch.rss_warn_mb`（1024）或线程超过 `selfwatch.threads_warn`（400）时，它会在被吞掉失败的计数器中记录一次（`selfwatch.high`，附带数值），尽可能释放，并在恢复正常时记录。可用 `selfwatch.enabled` 关闭。请把 `selfwatch.rss_warn_mb` 设为略低于容器的限制。CI 会在一个处理器、512 MB 的容器中用 120 个工作流的账户运行监视器（`tools/limits_check.py`）。
