<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# 面向运维人员的命令行

`monitor_cli.py` 的基础用法见 [CLI_zho.md](CLI_zho.md)。本页面向常驻终端的人：应答如何输出（`--format`）、如何持续观察（`watch`）、如何补全命令（`completions`）、退出码，以及电视所用的地址（`kiosk`）。这里的一切都只读取本机监控器（或 `--url` 指定的监控器）的 API；不会向 GitHub 写入任何内容，也不会消耗配额。

## 格式：`--format`

| 格式 | 得到什么 |
|---|---|
| `text` | 各命令一贯输出的内容。这是默认值。 |
| `table` | 排成适合终端宽度的列（日文和中文字符占两个单元格）。没有颜色，因此遵守 `NO_COLOR`。 |
| `plain` | 每行一条记录，字段以制表符分隔，没有表头：适用于 `grep`、`cut` 和 `awk`。文本中的制表符或换行会变成空格。 |
| `json` | 文档 `{"ok", "exit", "data"}`。`--json` 与之相同。 |
| `ndjson` | 每行一个 JSON 对象，每条记录一个（警报、账户、仓库、事件）。只回答一件事的命令（`status`、`health`）输出一行。 |

`--format` 优先于 `--json`，二者都优先于设置 `cli.default_format`（默认 `text`）。三种结构化格式都来自与 `--json` 相同的文档，因此绝不会不一致。空列表在 `ndjson` 和 `plain` 中不输出任何内容。

## `watch`：反复进行同一次读取

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` 重复执行该命令的读取。它读取的是监控器的 API 而不是 GitHub，所以较短的间隔不会消耗配额。选项：

- `--interval 秒数`：两次读取之间的停顿。下限是设置 `cli.watch.min_interval_seconds`（默认 2）：更短的间隔会被提高到该值。不带 `--interval` 时停顿为 `cli.watch.default_interval_seconds`（5）。
- `--once`：读取一次后退出（退出码即该命令的退出码）。
- `--exit-on-change`：当被观察的内容与第一次读取时不同（警报的集合，或状态的数字），循环以退出码 **6** 结束。时钟走动不算变化。不带该选项时永远不会出现退出码 6。
- `--no-clear`：两次读取之间不清屏（只有在终端上且仅在 `text` 和 `table` 下才会清屏）。
- 读取不到的监控器会以越来越长的停顿重试（间隔翻倍，最长一分钟），错误输出到标准错误。**Ctrl-C** 以退出码 0 结束循环。

## `watch branch`：你刚推送的提交

```
git push && python bin/monitor_cli.py watch branch
python bin/monitor_cli.py watch branch --repo acme/widgets --branch main --wait 300
python bin/monitor_cli.py watch branch --single-pass --format json
```

`watch branch` 会向 git 询问当前文件夹所在的仓库（`origin`）、分支和提交，并在监视器中跟踪该提交的工作流：等待它们出现，运行时显示，并自行结束。退出码在所有工作流都通过时为 **0**，在有工作流失败、被取消或未能按时结束时为 **1**（失败与超时不加区分，因此 `git push && monitor_cli.py watch branch` 可以放进脚本）。它读取监视器已有的运行记录，从不读取 GitHub，所以不消耗配额；该仓库必须是监视器所监视的仓库之一。远程地址只用于找出所有者和名称，从不输出（它可能含有令牌）。

- `--repo 所有者/名称` 和 `--branch 名称` 会替换 git 的结果。使用其中任何一个（或没有提交）时，跟踪的是该分支每个工作流的最新运行，而不是某一个提交的运行。
- `--single-pass`（或 `--once`）：读取一次后结束，返回当时的代码（运行未结束时为 1）。
- `--wait 秒数`：等待运行结束的时间，超时则以 1 放弃（10 到 86400）。不使用它时，等待时间为设置 `cli.watch.branch_timeout_seconds`（900）。
- 游离提交没有分支：请提供 `--branch`。没有指向 GitHub 的 `origin` 远程的文件夹需要 `--repo`。

## `completions`：补全命令

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

脚本由命令行的真实解析器生成，所以提供的正是实际存在的命令、词和选项：新选项不会被遗漏，并且有测试对二者进行比较。该命令只**打印**；不会编辑您的任何文件，也不需要监控器。请按上面的方式，把输出放到您的 shell 读取补全的位置。

## 退出码

| 代码 | 含义 |
|---|---|
| 0 | 一切正常（`watch` 中的 Ctrl-C 也是） |
| 1 | 命令使用错误 |
| 2 | 无法连接监控器 |
| 3 | 监控器或 GitHub 拒绝了凭据 |
| 4 | 监控器有应答但处于降级状态（离线、配额用尽、尚无数据），或应答无法解析 |
| 5 | `alerts --fail-on 级别` 发现了该级别或更严重的警报 |
| 6 | `watch --exit-on-change` 发现了变化（仅在给出该选项时） |

0 到 5 与 [CLI_zho.md](CLI_zho.md) 中的相同；有测试使本表与代码保持一致。

### 面向运维人员的 `status` 退出码

默认情况下，`status` 保持上表的退出码，因此任何脚本都不会改变。使用 `--status-codes operator`（或把设置 `cli.status_codes` 设为 `operator`）后，命令只表达三件事：**0** 正常，**1** 无服务（无法连接监视器或凭据被拒），**2** 在运行但需要关注。需要关注指：监视器无法连接 GitHub、还没有数据、凭据失明、因配额低于下限而暂停刷新、回答中带有错误、回答不是监视器的回答，或者 **磁盘上的代码与正在运行的进程版本不同**（更新后没有重启监视器；`/api/health` 用 `code_stale` 表示，`--doctor` 有 `running` 检查）。使用错误仍为 1。原因在 `--json` 的 `attention` 字段中。红色工作流的失败不在其内：那类情况请用 `alerts --fail-on`。

## 使用 `jq` 的示例

这些示例只使用属于应答稳定结构的字段，并由测试针对模拟监控器运行（在安装了 `jq` 时）。

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`：电视或墙面的地址

`monitor_cli.py kiosk [ops|team|release|quiet]` 会打印供无人操作的屏幕使用的监控器地址。参见 [KIOSK_zho.md](KIOSK_zho.md)。

## 设置

| 设置 | 默认值 | 含义 |
|---|---|---|
| `cli.default_format` | `text` | 未给出 `--format` 或 `--json` 时的格式：`text`、`table`、`plain`、`json` 或 `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | `watch` 的最短停顿（1 到 3600） |
| `cli.watch.default_interval_seconds` | 5 | 未给出 `--interval` 时 `watch` 的停顿（1 到 3600） |
| `cli.status_codes` | `classic` | `status` 的退出码：`classic`（表中的）或 `operator`（0 正常，1 无服务，2 在运行但需要关注） |
| `cli.watch.branch_timeout_seconds` | 900 | `watch branch` 等待该提交的运行结束的时间（10 到 86400） |

## 此版本不做的事

- `completions` 没有 `--install`：它从不写入用户的文件。
- 没有 `proposals` 命令：监控器目前还没有可供操作的提案路由。
