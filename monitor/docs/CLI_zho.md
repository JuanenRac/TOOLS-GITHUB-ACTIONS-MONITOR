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
| `alerts` | 所有哨兵的警报合成一个列表：`--sentinel ci\|collab\|security\|supply\|delivery`、`--level info\|warning\|error`、`--muted show\|hide\|only`；`--since 90m|24h|7d|2w` 列出在该时间段内某一时刻处于打开状态的警报，包括已关闭的（来自监视器运行时保存的历史；警报消失十分钟后算作已关闭） | 不支持 |
| `proposals` | AI 提出的操作（`ai.actions.enabled`）：`proposals list`、`show ID`、`approve ID`、`reject ID`、`execute ID`（id 可以缩写）。`approve` 和 `reject` 只记录决定；`execute` 通过与页面相同的入口执行，需要 `ai.actions.execute`，开启 `ai.actions.require_approval` 时需先批准。批准、拒绝和执行只能在本机进行 单用户时 `approve` 需要 `--code` 和指纹前八位；多用户时请在页面用自己的会话批准（两人）。 | 不支持 |
| `score` | 账户评分：数值、等级、趋势、各部分、覆盖率以及按仓库的细分；`--compare` 将其与窗口内的历史记录比较 | 不支持 |
| `compare` | 将当前时段与上一时段对比：各项数值及其变化与方向，哪些变差或变好；`--window 7\|30d`、`--days all\|workdays\|weekend`、`--baseline previous\|year_ago`、`--format table\|json\|ndjson\|csv`；某项数据不足时退出码为 4，使用 `--fail-on` 且有数值变差时为 5；其他命令使用 `--format csv` 属于误用（退出码 1） | 不支持 |
| `api` | 面向客户端的只读 API:`api openapi` 输出每条已冻结路由的 OpenAPI 文档(可重定向到文件),`api me` 说明监视器如何看待此客户端(模式、用户、角色、会话可做的事、契约版本);`api.v1_enabled` 关闭的监视器会如实告知;`api contract-check` 对其运行面向客户端的契约套件(有检查失败时退出码为 4) | 不支持 |
| `team` | 按需要人处理的优先顺序列出仓库的健康状况；`--severity warn\|bad` 只保留较差的，`--repo owner/name` 显示单个仓库的详情 | 否 |
| `live` | Webhook 接收器的状态和最近的事件 | 不支持 |
| `ai` | `ai models [--refresh]` 列出 AI 提供方的模型及各模型的数据；`ai test --provider 名称 --model 名称` 用合成文本试用一个模型（延迟、令牌、估算成本）；`ai doctor` 说明 AI 为何没有响应，且不输出密钥 | 不支持 |
| `lessons` | 这个 CI 的失败教会了什么:`lessons list`、`lessons brief --repo NAME`(推送前阅读)、`lessons failures`、`lessons close` | 不支持 |
| `briefs` | AI 工具读取的各标签页摘要:`briefs index`、`briefs show TAB`、`briefs all` | 支持 |
| `docs` | 此版本的指南，直接从安装目录读取（无需监视器）：`docs list` 列出名称和标题，`docs show NAME` 按 `--lang` 的语言显示其中一份 | 否 |
| `screens` | 页面的“屏幕”菜单:`screens list`(每种屏幕及其能否打开)和 `screens urls`(可直接用于展台命令的完整地址) | 不支持 |
| `keyring` | 可以签名的公钥：`keyring list`、`add`（`--key-id`、`--public-key`、`--key-scope`、`--expires`）、`revoke --key-id`、`verify --document FILE`；无需监视器，私钥会被拒绝 | 否 |
| `verify-release` | 无网络时按 SHA256SUMS 及其签名校验下载的发布文件夹：`verify-release --folder DIR`；不可信时退出码为 4 另有 `--installed`（本安装对照物料清单）、`--attestations`、`--fetch`（需要 `ops.verify_release.fetch`）；`doctor --verify-release DIR` 校验安装；`keyring check-rotation --document FILE` 校验新密钥公告。 | 否 |
| `toolbox` | 无需运行监视器、在本机上工作的运维小工具：`toolbox limits [N]`（配置与其上限的对比）、`toolbox workspaces`（工作区及正在使用的工作区）、`toolbox ledger [--force]`（已发送通知的台账；`--force` 将其清除）、`toolbox summary`（按类型、仓库和日期统计事件）以及 `toolbox export-events FILE`（按文件名结尾把事件写成 jsonl、csv、parquet 或 duckdb；parquet 和 duckdb 需要各自的包，文件必须是新的） | 否 |
| `credential` | 在一切运行时为某个账户更换 GitHub 登录:`credential replace\|reload [--account ID] [--new-token-file FILE\|-]`;从不打印令牌 | 不支持 |
| `install-skill` | 把监视器的一个技能(`internal` 或 `external`)复制到 AI 工具读取技能的文件夹:`install-skill external --dest FOLDER`;无需监视器正在运行 | 不支持 |
| `gh-token` | 打印 GitHub App 的一小时安装令牌,使工具的读取消耗 App 的配额(仅在 `github_app.share_reads` 开启时);请不带 `--json` 运行 | 不支持 |
| `watch` | 反复进行同一次读取（`watch status\|alerts`、`--interval`、`--once`、`--exit-on-change`）；参见 [CLI_OPERATOR_zho.md](CLI_OPERATOR_zho.md) | 不支持 |
| `completions` | `bash`、`zsh`、`fish` 或 `powershell` 的补全脚本，由真实解析器生成（只打印） | 不支持 |
| `kiosk` | 电视或墙面所用的监控器地址（`ops`、`team`、`release`、`quiet`）；参见 [KIOSK_zho.md](KIOSK_zho.md) | 不支持 |
| `metrics` | 以 `名称=值` 的行输出数值，供 cron 和邮件使用；加上 `--if-problem` 时一切正常则不输出任何内容；参见 [CLI_OPERATOR.md](CLI_OPERATOR.md) | 否 |
| `posture` | 仓库与组织安全态势,只读(`posture status|matrix|check --repo-name`);见 [POSTURE.md](POSTURE_zho.md) | 否 |
| `external-ci` | 外部 CI 来源,只读(`external-ci list|status|probe --source`);见 [EXTERNAL_CI.md](EXTERNAL_CI_zho.md) | 否 |
| `plugin` | 插件：`plugin list|validate|pack|verify|init|install|enable|disable|uninstall|audit`；参见 [PLUGINS.md](PLUGINS_zho.md) | 否 |

所有命令的选项：`--json`（以单个 JSON 文档输出：`{"ok", "exit", "data"}`）、`--account ID`、`--url URL`、`--lite`（端口 8766）、`--timeout 秒数`（1 到 60）、`--lang 代码`。在网络模式下,请把访问令牌放在监视器自己读取的环境变量 `MONITOR_ACCESS_TOKEN` 中(`MONITOR_TOKEN` 作为别名也可用;`--token TOKEN` 是最后手段,因为命令行选项会出现在进程列表中)。优先顺序:`MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token`。令牌通过请求头 `X-Monitor-Access` 传送,绝不出现在地址或屏幕上。对其他计算机使用未加密 `http` 的 `--url` 时,会在 stderr 打印警告(令牌和响应将以明文传输):在不受你控制的网络中请使用 `https`。

每个命令还接受 `--format text|table|plain|json|ndjson`（`--json` 即 `--format json`）；参见 [CLI_OPERATOR_zho.md](CLI_OPERATOR_zho.md)。

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
| 6 | `watch --exit-on-change` 发现了变化（仅在给出该选项时）；参见 [CLI_OPERATOR_zho.md](CLI_OPERATOR_zho.md) |

每个错误都带有 `help`：一句说明下一步的话，通常会指出应阅读的指南（`docs show FIRST_STEPS`）。文本格式中它是以 `帮助：` 开头的最后一行；使用 `--json` 时它是 `error` 旁边的 `help` 字段：`{"ok": false, "exit": 2, "error": "...", "help": "..."}`。

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

`backup` 和 `doctor` 直接作用于安装的文件夹，因此不需要监视器在运行。`doctor` 在一切正常时（含警告）以 `0` 退出，检查失败时为 `1`，只有警告且 `--strict`（或 `ops.doctor.strict_exit`）开启时为 `3`，doctor 本身无法运行时为 `4`；这些是 doctor 的退出码，其他命令保持上文的退出码。`backup` 完成时以 `0` 退出，被拒绝或备份包未通过验证时为 `1`。检查项、恢复和计划备份见指南 [OPS_zho.md](OPS_zho.md)。 doctor 还有 `compare_window`（两个时期的对比能否用它要求并保留的历史回溯两个窗口）和 `etag`（本机运行的监视器中条件读取以 304 应答的比例，以及 GitHub 的响应是否不带 ETag 返回）。

## 仓库身份与多个所有者

命令行：`identity status`、`identity plan`、`identity apply`。

```
python bin/monitor_cli.py identity plan
```

## 合规与操作日志

`compliance report` 说明本安装提供哪些保证; `audit verify|checkpoint|purge|export` 处理操作日志链。见 [COMPLIANCE_zho.md](COMPLIANCE_zho.md)。
