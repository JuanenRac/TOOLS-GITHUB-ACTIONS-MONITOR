<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | [🇪🇸 Español](STORAGE_spa.md) | [🇫🇷 Français](STORAGE_fra.md) | [🇮🇹 Italiano](STORAGE_ita.md) | [🇩🇪 Deutsch](STORAGE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# 存储与保留

说明完整版把学到的内容保存在哪里、如何更改,以及它会自动删除什么。精简版始终只用普通文件,没有数据库也没有保留任务,也不会显示这里的任何内容。

## 保存的内容

每个账户:配置(`actions_monitor.json`)、哨兵的状态、事件流、事件流已经通报过的内容、分析样本、静音设置和更新提示。整个安装:用户、他们可以看到的账户以及他们的会话(团队模式使用)。条件读取的缓存和日志始终是普通文件。

## 两种存储后端

|  | `file`(默认) | `sqlite` |
|---|---|---|
| 位置 | `accounts/<id>/`(没有 `accounts/` 时在启动器旁边) | `accounts/<id>/storage.sqlite3`,每个账户一个数据库 |
| 写入 | 先写临时文件并刷到磁盘,再改名 | 一个短事务,WAL 日志 |
| 适用于 | 个人使用;可以阅读和编辑的文件 | 连续运行数月的服务;事件很多 |

在账户(或监视器)的配置中选择:`"storage": {"backend": "sqlite"}`。配置本身始终是 JSON 文件,因为正是它指明了存储后端。使用 SQLite 时,事件流在数据库中,而不在 `events_monitor.jsonl` 里。打不开的数据库会阻止启动:监视器绝不会背着你把状态写到别处。

## 决定:每个账户一个存储(模型 A)

*背景。* 完整版为每个账户运行一个进程。*决定。* 每个进程有自己的存储:自己的文件,或 `accounts/<id>/` 里自己的数据库 `storage.sqlite3`。两个进程从不写同一个文件,因此它们之间无需加锁,一个账户的问题也不会损坏另一个账户。*代价。* 跨账户的查询需要读取多个数据库。

*已备好:模型 B,一个共享数据库。* 在每个账户的 `storage` 区块里写同一个路径(`"path": "/data/monitor.sqlite3"`)。它可行,是因为每张表都带有账户信息,WAL 让页面在哨兵写入时也能读取,事务很短,数据库忙时最多等待 5 秒。它经过测试(两个进程同时运行周期;页面在它们写入时通过 HTTP 应答),但不是默认选项:它比 A 更脆弱,只有在需要跨账户 SQL 时才值得使用。

## 有保证的内容

- 写入是原子的:读取者看到的要么是旧值,要么是新值。中途被强制终止(`kill -9`)的进程会留下旧值;使用 SQLite 时,下次启动会自动恢复。
- 架构带有版本(`schema_version`)。每次迁移都与版本号的更新在同一个事务中执行,所以被中断的迁移会让数据库保持原样,并在下次启动时重新执行。由更新版本写出的数据库会被拒绝,绝不会被降级。
- 损坏或缺失的项目按空处理:监视器用磁盘上现有的内容启动。

## 迁移数据与备份

```
python tools/migrate_storage.py --from file --to sqlite              # 试运行:显示将要复制的内容
python tools/migrate_storage.py --from file --to sqlite --apply      # 复制,然后比较每一项和每条事件
python tools/backup_storage.py backup backup.zip --backend sqlite    # 带清单和 SHA-256 的 .zip
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # 恢复到空的存储(覆盖已有账户用 --force)
```

迁移从不修改或删除你的文件,中断后可以继续(一个账户要么整体复制,要么完全不复制),两边不一致时以失败结束;确认无误后再切换存储后端并重启。由文件制作的备份可以恢复到 SQLite,反之亦然。`--db FILE` 选择模型 B 的共享数据库;`--flat` 表示没有 `accounts/` 的安装。`--doctor` 在不修改的情况下检查数据库(是否存在、完整性、架构)。

## 保留

连续运行数月的监视器会无限增长,所以在每次刷新结束时会快速执行一遍(每隔 `retention.interval_hours`,默认 24)来清除旧内容:

| 设置 | 默认 | 含义 |
|---|---|---|
| `retention.enabled` | 开 | 开关 |
| `retention.events_days` | 90 | 超过此天数的事件会被删除 |
| `retention.analytics_days` | 180 | 超过此天数的分析历史会被删除 |
| `retention.mode` | `delete` | `archive` 会先把旧事件写入 `events/archive/` 中的 `.gz` |
| `retention.events_max_kb` | 512 | 文件存储时事件流文件的大小上限(与以往相同) |
| `retention.warn_events_mb` | 20 | 超过此大小时 `--doctor` 发出警告 |

清理只处理超过期限的事件和分析日期;它绝不会改动配置、哨兵状态、静音设置,也不会删除没有时间的事件。每次清理都会在审计文档中留下一行(时间、删除和保留的事件数、归档文件、分析天数、错误)。`--doctor` 会警告事件的大小;对作为服务运行的监视器(网络模式、没有浏览器、容器或 `MONITOR_SERVICE=1`),如果配置里没有 `retention` 区块,也会警告。缩短期限之前请先备份。
