<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# 多个账户

完整版可以同时监视多个 GitHub 账户（个人或组织）。每个账户都是一个独立的监视器：单独的进程，拥有自己的文件夹、在 `127.0.0.1` 上的自己的端口、自己的配置，以及自己对 GitHub 额度的读取。某个账户的崩溃、响应缓慢或速率限制，绝不会影响其他账户。精简版只有一个账户，没有以下任何内容：它甚至不会显示下面的选项。

## 无需任何操作时

没有 `accounts/` 文件夹时，监视器的工作方式与以前完全一样：一个账户，文件放在代码旁边。只有当你想要多个账户时才需要继续阅读。

## 账户文件夹

```
accounts/
  global.json              可选：{"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   此账户的配置（它的 github_owner、repos、哨兵等）
  org-acme/
    actions_monitor.json
```

账户的 ID 由小写字母、数字、`_` 和 `-` 组成（最长 40 个字符），因为它是文件夹名；其他内容都会被拒绝。`enabled_accounts` 是 `"all"` 或一个列表；`default_account` 是未指定账户时打开的那个。`MONITOR_ACCOUNTS_DIR` 可以移动该文件夹。每个账户把缓存、事件、分析、哨兵状态和日志都放在自己的文件夹里，所以两个账户绝不会共用一个文件。

## 从一个账户迁移到多个

```
python actions_monitor.py --migrate-accounts          # 显示将复制的内容，不写入任何东西
python actions_monitor.py --migrate-accounts --apply  # 复制到 accounts/default/
python actions_monitor.py --accounts                  # 列出账户
```

原文件绝不会被移动或删除：检查无误后由你自己删除。第二次运行会被拒绝，因此两种状态绝不会混在一起。要添加账户，请创建带有其 `github_owner` 的 `accounts/<id>/actions_monitor.json`（复制模板 `actions_monitor.example.json`）。

## 运行

存在 `accounts/` 文件夹时运行 `python actions_monitor.py` 会启动监督程序，这是一个运行在常用端口（8765）上的小进程，它为每个账户启动一个监视器，并为页面和工具提供唯一的地址。它不从 GitHub 读取任何内容，也不写入任何内容。如果某个账户停止，它会以逐渐增加的等待时间重新启动它（2、5、15、30、60，然后 120 秒），在此期间概览会显示它已停止。`python actions_monitor.py --account personal` 只运行该账户，作为普通监视器。

## 页面

页面还是你熟悉的那个，页眉下方有账户切换器，并新增 **所有账户** 一项，为每个账户显示一张卡片（状态、仓库、运行中、失败中），可打开其中任何一个。每个窗口都保留自己的账户和视图：它们从地址中读取，而不是来自会被另一个窗口覆盖的单一设置。

| 地址 | 显示内容 |
|---|---|
| `/?account=org-acme` | 该账户的页面 |
| `/?account=all` | 所有账户的卡片 |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | 一个面板 |
| `/?chrome=0` | 没有页眉按钮、标签页和过滤器：适合墙面或第二块显示器的屏幕 |

要使用多个屏幕，每个视图打开一个窗口，例如 `?view=now&chrome=0`、`?view=alerts&chrome=0` 和 `?view=live&chrome=0`。一个监视器为它们全部提供服务，所以不会重复消耗额度。**实时**视图显示 GitHub 最近发送的事件、webhook 接收器的状态（开或关，已接受、已忽略、重复或已拒绝的投递数量，绝不显示密钥）以及工作模式的选择器。

## API

`GET /api/accounts` 是概览，`GET /api/accounts/<id>/status` 是某个账户，`/api/` 下的其他请求都会发往用 `?account=<id>` 或请求头 `X-Account-Id` 指定的账户（未指定则为默认账户）。未知账户返回 404。访问规则与单个监视器相同：同样的主机和来源检查，以及网络模式下同样的访问令牌。更改的一次性令牌必须向该更改所发往的同一账户申请。

## 一个 webhook 服务所有账户

`POST /api/webhook` 是整个安装的唯一地址。监督程序只读取载荷中仓库的所有者（`repository.full_name`），并把事件原样交给 `github_owner` 就是该所有者的账户；该账户用自己的密钥验证签名。没有人监视的所有者会得到响应并被忽略。想自己选择账户，请加上 `?account=<id>`。

## 限制与坦白

- 多个账户就是多个进程：每个进程各自读取 GitHub，因此额度由你使用的登录共享。请在卡片中留意，必要时按账户调低 `refresh_seconds` 或 `max_workers`。
- 需要真实浏览器、真实 GitHub 账户和真实 webhook 隧道的检查由你来做；测试使用账户监视器的替身，绝不会调用 GitHub。
- 后续版本会把这些账户合并到一个进程中；上面的文件夹布局和 API 保持不变。
