<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# 作为监视器客户端的命令行

`python bin/monitor_cli.py 命令` 向正在运行的监视器询问它所知道的信息（对 `127.0.0.1` 或 `--url` / `MONITOR_URL` 地址发出 `GET`）并打印出来。它不会重复页面对 GitHub 的工作，从不向 GitHub 写入，也不更改任何设置。旧的工具（`bin/read_report.py`、`--doctor`、`bin/gha_dispatch_all.py`）照常可用。

## 命令

| 命令 | 显示内容 | 精简版 |
|---|---|---|
| `status` | 版本、版本类型、账户、仓库、运行与失败情况、配额 | 支持 |
| `health`（或 `check`） | 在读取任何重内容之前的快速检查：监视器能否连接、是否接受此客户端、该账户的 GitHub 登录是否有响应 | 支持 |
| `doctor` | 此安装的 `--doctor` 检查（监视器无需运行） | 支持 |
| `backup` | 安装的完整备份（监视器无需运行）：`backup create [文件] [--account ID]`、`verify 文件 [--deep]`、`restore 文件 [--account ID] [--to-dir 文件夹] [--force]`、`status`、`list`；`--encrypt` 配合 `--key-env 名称` 进行加密（可选库）；见 [OPS_zho.md](OPS_zho.md) | 不支持 |
| `accounts` | 监督进程的账户（仅多账户时） | 不支持 |
| `alerts` | 所有哨兵的警报合成一个列表：`--sentinel ci\|collab\|security\|supply\|delivery`、`--level info\|warning\|error`、`--muted show\|hide\|only` | 不支持 |
| `score` | 账户评分：数值、等级、趋势、各部分、覆盖率以及按仓库的细分；`--compare` 将其与窗口内的历史记录比较 | 不支持 |
| `compare` | 将当前时段与上一时段对比：各项数值及其变化与方向，哪些变差或变好；`--window 7\|30d`、`--days all\|workdays\|weekend`、`--baseline previous\|year_ago`、`--format table\|json\|ndjson\|csv`；某项数据不足时退出码为 4，使用 `--fail-on` 且有数值变差时为 5 | 不支持 |
| `api` | 面向客户端的只读 API:`api openapi` 输出每条已冻结路由的 OpenAPI 文档(可重定向到文件),`api me` 说明监视器如何看待此客户端(模式、用户、角色、会话可做的事、契约版本);`api.v1_enabled` 关闭的监视器会如实告知;`api contract-check` 对其运行面向客户端的契约套件(有检查失败时退出码为 4) | 不支持 |
| `team` | 按需要人处理的优先顺序列出仓库的健康状况；`--severity warn\|bad` 只保留较差的，`--repo owner/name` 显示单个仓库的详情 | 否 |
| `live` | Webhook 接收器的状态和最近的事件 | 不支持 |
| `ai` | `ai models [--refresh]` 列出 AI 提供方的模型及各模型的数据；`ai test --provider 名称 --model 名称` 用合成文本试用一个模型（延迟、令牌、估算成本）；`ai doctor` 说明 AI 为何没有响应，且不输出密钥 | 不支持 |
| `lessons` | 这个 CI 的失败教会了什么:`lessons list`、`lessons brief --repo NAME`(推送前阅读)、`lessons failures`、`lessons close` | 不支持 |
| `briefs` | AI 工具读取的各标签页摘要:`briefs index`、`briefs show TAB`、`briefs all` | 支持 |
| `credential` | 在一切运行时为某个账户更换 GitHub 登录:`credential replace\|reload [--account ID] [--new-token-file FILE\|-]`;从不打印令牌 | 不支持 |
| `install-skill` | 把监视器的一个技能(`internal` 或 `external`)复制到 AI 工具读取技能的文件夹:`install-skill external --dest FOLDER`;无需监视器正在运行 | 不支持 |
| `gh-token` | 打印 GitHub App 的一小时安装令牌,使工具的读取消耗 App 的配额(仅在 `github_app.share_reads` 开启时);请不带 `--json` 运行 | 不支持 |

所有命令的选项：`--json`（以单个 JSON 文档输出：`{"ok", "exit", "data"}`）、`--account ID`、`--url URL`、`--lite`（端口 8766）、`--timeout 秒数`（1 到 60）、`--lang 代码`。在网络模式下,请把访问令牌放在监视器自己读取的环境变量 `MONITOR_ACCESS_TOKEN` 中(`MONITOR_TOKEN` 作为别名也可用;`--token TOKEN` 是最后手段,因为命令行选项会出现在进程列表中)。优先顺序:`MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token`。令牌通过请求头 `X-Monitor-Access` 传送,绝不出现在地址或屏幕上。对其他计算机使用未加密 `http` 的 `--url` 时,会在 stderr 打印警告(令牌和响应将以明文传输):在不受你控制的网络中请使用 `https`。

命令行是面向客户端的只读 API 的客户端:契约冻结的路由(`docs/schemas/api_contract.json`)先在 `/api/v1/` 下请求;若监视器在那里返回 404(API 已关闭,`api.v1_enabled`),则改请求旧路由,且不再尝试该前缀。两条路径的文档相同,因此任何命令的输出都不会改变。`cli.prefer_v1`(默认开启)可将其关闭,环境变量 `MONITOR_CLI_PREFER_V1`(`0` 或 `1`)优先。契约未冻结的路由始终按旧方式请求。

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
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` 区分三种情况：监视器没有响应（2）、GitHub 登录失败（3）、配额耗尽或无法连接 GitHub（4）；尚未完成首次读取的监视器会如实说明（4），而不是显示空数字。

## 精简版

`python bin/monitor_cli.py status --lite`、`doctor --lite` 和 `health --lite` 与端口 8766 通信。需要账户、哨兵或 Webhook 接收器的命令会以退出码 1 被拒绝。精简版没有账户，也没有警报 API。

## `ai-hook`: 告诉 AI 工具监控器看到了什么

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` 不需要监控器正在运行。它在 AI 工具的钩子设置中添加、显示或移除联动脚本 `bin/ai_hook.py` (见 AI 告警指南): 设置文件会被合并, 保留一份备份, `--json` 的输出是纯 ASCII。默认动作是 `status`。

## 命令行中的访问令牌

在网络模式下, 令牌依次从 `MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token-file FILE` 的第一行读取 (请让该文件只有你能读取: 在有文件模式的系统上, 其他用户可读时命令会发出警告), 最后才是 `--token`, 它会出现在进程列表中, 因此会在 stderr 打印警告。

## 存储工具

`python tools/migrate_storage.py` 在文件与 SQLite 之间迁移状态,`python tools/backup_storage.py` 为两者创建、检查和恢复备份(详见 [STORAGE_zho.md](STORAGE_zho.md))。`--doctor` 为此有两项检查:存储和保留。

## 批量调度器:工作流的输入

`python bin/gha_dispatch_all.py plan --inputs` 还会在每个目标下列出其工作流在手动触发时要求的输入(名称、类型、必填或可选、默认值、选择项的选项以及说明)。它们通过 `git show` 从本地克隆 `origin/main` 中的工作流文件读取:不会触发任何运行、不会发送任何内容,也不会调用 `gh`。`--json` 会为每一行添加 `inputs` 列表;当文件不在 `origin/main` 中或使用读取器不认识的写法(流式 `inputs: {…}`)时为 `null`,工作流不需要输入时为 `[]`。

## 备份与 doctor

`backup` 和 `doctor` 直接作用于安装的文件夹，因此不需要监视器在运行。`doctor` 在一切正常时（含警告）以 `0` 退出，检查失败时为 `1`，只有警告且 `--strict`（或 `ops.doctor.strict_exit`）开启时为 `3`，doctor 本身无法运行时为 `4`；这些是 doctor 的退出码，其他命令保持上文的退出码。`backup` 完成时以 `0` 退出，被拒绝或备份包未通过验证时为 `1`。检查项、恢复和计划备份见指南 [OPS_zho.md](OPS_zho.md)。
