<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# 作为监视器客户端的命令行

`python monitor_cli.py 命令` 向正在运行的监视器询问它所知道的信息（对 `127.0.0.1` 或 `--url` / `MONITOR_URL` 地址发出 `GET`）并打印出来。它不会重复页面对 GitHub 的工作，从不向 GitHub 写入，也不更改任何设置。旧的工具（`read_report.py`、`--doctor`、`gha_dispatch_all.py`）照常可用。

## 命令

| 命令 | 显示内容 | 精简版 |
|---|---|---|
| `status` | 版本、版本类型、账户、仓库、运行与失败情况、配额 | 支持 |
| `health`（或 `check`） | 在读取任何重内容之前的快速检查：监视器能否连接、是否接受此客户端、该账户的 GitHub 登录是否有响应 | 支持 |
| `doctor` | 此安装的 `--doctor` 检查（监视器无需运行） | 支持 |
| `accounts` | 监督进程的账户（仅多账户时） | 不支持 |
| `alerts` | 所有哨兵的警报合成一个列表：`--sentinel ci\|collab`、`--level info\|warning\|error`、`--muted show\|hide\|only` | 不支持 |
| `live` | Webhook 接收器的状态和最近的事件 | 不支持 |

所有命令的选项：`--json`（以单个 JSON 文档输出：`{"ok", "exit", "data"}`）、`--account ID`、`--url URL`、`--lite`（端口 8766）、`--timeout 秒数`（1 到 60）、`--lang 代码`。在网络模式下,请把访问令牌放在监视器自己读取的环境变量 `MONITOR_ACCESS_TOKEN` 中(`MONITOR_TOKEN` 作为别名也可用;`--token TOKEN` 是最后手段,因为命令行选项会出现在进程列表中)。优先顺序:`MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token`。令牌通过请求头 `X-Monitor-Access` 传送,绝不出现在地址或屏幕上。对其他计算机使用未加密 `http` 的 `--url` 时,会在 stderr 打印警告(令牌和响应将以明文传输):在不受你控制的网络中请使用 `https`。

为人而写的时间（`Last read` 行、静音、日志、报告、通知）使用本机的时区并标明其名称，旁边附上 UTC 时间（`11:43:07 CET (10:43:07 UTC)`）。可用 `display.timezone` 选择其他时区（`local`、`utc` 或如 `Europe/Madrid` 的名称；环境变量 `MONITOR_TIMEZONE` 优先于文件）。`--json` 保持 UTC，并新增 `updated_local`。

## 退出码（稳定）

| 代码 | 含义 |
|---|---|
| 0 | 一切正常 |
| 1 | 命令用法错误（对需要完整版的命令使用 `--lite` 也是） |
| 2 | 无法连接监视器 |
| 3 | 监视器拒绝此客户端，或该账户的 GitHub 登录失败或已过期（凭据问题，而非配额耗尽） |
| 4 | 监视器有响应但处于降级状态：离线、配额耗尽、尚无数据、没有该端点，或响应不是 JSON |
| 5 | `alerts --fail-on 级别` 发现了该级别或更严重的未处理警报（已静音的不计） |

## 示例

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` 区分三种情况：监视器没有响应（2）、GitHub 登录失败（3）、配额耗尽或无法连接 GitHub（4）；尚未完成首次读取的监视器会如实说明（4），而不是显示空数字。

## 精简版

`python monitor_cli.py status --lite`、`doctor --lite` 和 `health --lite` 与端口 8766 通信。需要账户、哨兵或 Webhook 接收器的命令会以退出码 1 被拒绝。精简版没有账户，也没有警报 API。

## `ai-hook`: 告诉 AI 工具监控器看到了什么

`python monitor_cli.py ai-hook install|status|uninstall [--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` 不需要监控器正在运行。它在 AI 工具的钩子设置中添加、显示或移除联动脚本 `ai_hook.py` (见 AI 告警指南): 设置文件会被合并, 保留一份备份, `--json` 的输出是纯 ASCII。默认动作是 `status`。

## 命令行中的访问令牌

在网络模式下, 令牌依次从 `MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token-file FILE` 的第一行读取 (请让该文件只有你能读取: 在有文件模式的系统上, 其他用户可读时命令会发出警告), 最后才是 `--token`, 它会出现在进程列表中, 因此会在 stderr 打印警告。
