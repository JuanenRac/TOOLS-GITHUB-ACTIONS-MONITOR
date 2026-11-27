<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# 操作日志

仅 Complete，默认开启。除了访问审计（登录、锁定、拒绝）之外，监视器还保留一份**操作**日志：谁在什么时候、在哪个账户上修改了什么。包括设置的修改、静音及其解除、用户、密码、通知偏好或凭据的修改。每个操作一行 JSON，写入 `logs/audit_actions.jsonl`，从不重写。 它还会记录被确认的操作：GitHub 上的操作（重新运行、取消、触发、合并）、用 `act` 运行、保存或删除已保存的令牌、工作模式的更改、由发现功能添加的分组、添加的经验、此刻写出的报告、账户的登录以及 AI 的操作。该行写明确认了什么和结果，绝不包含请求正文。每条 POST 路由要么被记录，要么附理由列为豁免，新路由两者都不是时测试会失败。

## 一行写了什么

`at`、`action`（简单的词，如 `settings_change` 或 `alert_mute`）、`user`、`role`、`account`、`target`（简短的标识，如设置名或警报代码）、`result`（`ok`、`denied` 或 `error`），必要时还有 `details`。**绝不写入任何值或机密**：修改设置时只写设置的名称，不写设置的值；名称看起来像机密的键（token、password、key、cookie、authorization、session 等）会被丢弃；所有文本都会像给 AI 的备注一样被清理，并截断为 200 个字符。

## 哈希链

每一行都带有 `prev`（上一行的哈希）和 `hash`（它自己与 `prev` 的哈希）。事后被修改、删除或插入的行会破坏哈希链，`GET /api/audit-log` 会指出位置（`chain.broken_at`）。超过 `audit_log.max_mb` 后，旧部分会另存为 `audit_actions.jsonl.1`，哈希链在新文件中继续。哈希链能发现篡改，但无法阻止能访问该文件的人把它整个删除，所以请在重要的地方保留一份副本。 有多个账户时，每个账户在自己的文件夹中保存自己的文件（`accounts/<id>/audit_actions.jsonl`），API 只返回被查询账户的行；此变更之前写入的行留在旧的共享文件中。检查也涵盖轮转后的文件以及两者之间的衔接（`segments`，某行损坏时给出 `segment`）；`complete: false` 表示链条不是从第一个环节开始，因为轮转后的文件被之后的轮转替换或被删除。多个进程可以写入同一个文件：每一行在锁的保护下接到文件中真正的最后一行。链条没有密钥：能写入该文件的人可以截去最新的几行，或用新的哈希重写整个文件；如果要把它当作证据，请在别处保存一份副本。 使用 `audit_log.keep_generations`(默认 5,范围 1 到 20)时,旧的部分保存为 `.1`、`.2` 等:最新的是 `.1`,比这些文件更旧的会被删除,`GET /api/audit-log` 会跨所有文件校验哈希链。

## 谁能读取

管理员（没有团队模式时则是电脑前的人）。维护者仅在 `audit_log.maintainers_can_read` 开启时可以读取；其他人都不能。`GET /api/audit-log` 返回最近 200 行和哈希链的状态。Lite 版没有这些。 viewer 在入口处就会被拒绝。关闭日志时会写入它自己的最后一行（关闭它的那次更改）。无法写入的行会被计数：回答中的 `write_failures` 和 `last_write_error_at`，以及一条降级通知。修改自己密码失败的记录不写在这里（由访问审计保存）。

## 设置

设置，哨兵标签页，**操作日志**区块：`audit_log.enabled`（开启）、`audit_log.max_mb`（10）和 `audit_log.maintainers_can_read`（关闭）。 `audit_log.keep_generations`(5)是保留的轮转文件数。`audit_log.required`(关闭)开启后,需要记录的操作(对 GitHub 操作的确认、模式、静音、凭据等)在无法写入日志期间会被以 503 拒绝;设置保持开放,以便修复。

立即生成的备份（`POST /api/ops/backup`）和按需清理（`POST /api/ops/purge`，试运行也算）会记录为 `backup_run` 和 `purge_run`：记录行写明谁发起以及结果，绝不包含备份的内容。

## 签名检查点、清除与导出

开启 `audit_checkpoints.enabled` 后链用本安装的密钥签名, 日志还可清除和复制到别处: 见 [COMPLIANCE_zho.md](COMPLIANCE_zho.md)。`retention.legal_hold` 开启时日志不轮转也不清除。
