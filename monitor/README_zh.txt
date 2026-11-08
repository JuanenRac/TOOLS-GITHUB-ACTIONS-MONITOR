Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GitHub Actions 监视器 + 哨兵（版本 1.6.4）
============================================
该启动哪一个?(新用户两分钟就能决定)
  完整版  MONITOR_GITHUB_ACTIONS.*       带哨兵的页面(端口 8765):警报、签名队列、分析。有多个仓库时从这里开始。
  精简版  MONITOR_LITE_GITHUB_ACTIONS.*  不带哨兵的同一页面(端口 8766):显示红色、卡住和运行中的内容。更轻量,可与完整版同时运行。
  批处理  BATCH_GITHUB_ACTIONS.*         仅当你自己签名并发布构建时使用。
  终端    python tui_textual.py(精简版加 --lite)   交互式终端应用;tui.py --once 输出一屏。
  检查    python actions_monitor.py --doctor(脚本用 --json)   说明缺少什么以及修复它的准确命令。
  试用    python actions_monitor.py --demo   用虚构数据的页面:无需 gh、无需登录,不会碰你的任何数据。

运行要求：Python 3.11+，以及已登录的 GitHub CLI（`gh`）（gh auth login）。无需其他东西:核心不需要任何包(终端视图 tui.py 使用可选的 rich 包)。
首次使用的快速步骤：QUICKSTART_zh.txt。

启动       Windows：MONITOR_GITHUB_ACTIONS.bat | Linux：./MONITOR_GITHUB_ACTIONS.sh | macOS：双击 MONITOR_GITHUB_ACTIONS.command
           （会打开 http://127.0.0.1:<端口>，仅限本机）。在任何系统上也可以运行：  python3 actions_monitor.py  （Windows：py -3 actions_monitor.py）
批处理     BATCH_GITHUB_ACTIONS.bat / .sh / .command（gha_dispatch_all.py：plan、dispatch、status、finalize、hygiene）。可选，适用于在本机为构建签名的人。
它绝不会做的事   除非开启网络模式(设置 > 高级:私有地址、每个请求都需访问令牌、页面中的警告),否则只监听 127.0.0.1。除非开启保存在系统安全存储中的可选令牌,否则不保存任何令牌（向 `gh` 索取）。它自身不会向 GitHub 写入任何内容：只有批处理命令 `dispatch --go`、`dispatch --real` 和 `finalize --execute` 会写入 GitHub（触发 workflow、创建未签名草稿、发布），且仅在你亲自运行它们时才会。
           它不会自行签名，也不会自行发布任何东西：签名和发布是由你自己执行的命令，监视器只把它们显示为文本。
           关键判断不使用 AI；可选的 AI 解释功能默认关闭。

语言       8 种语言:en、es、de、fr、it、ja、zh、pt(葡萄牙语为葡萄牙本土)。默认以英语启动:不由系统语言决定。请在页面的“设置”选项卡(齿轮图标,浏览器会记住)中选择其他语言,
           或用 actions_monitor.json 的 "language"、环境变量 MONITOR_LANG,或命令行工具的 --lang 代码(优先级最高)。
           脚本读取的行(SKIP、DISPATCHED、READY、FAILED、Summary:、BUILD ONLY……)始终为英语。
配置       actions_monitor.json（首次启动时由 actions_monitor.example.json 生成）。常用键：github_owner（留空 = gh 登录的账户）、
           language、ecosystems_file、targets_file、refresh_seconds、cold_refresh_seconds、max_workers、min_rate_remaining、sentinel.*
           ecosystems_file：按名称前缀给仓库分组（见 ecosystems.example.json；"*" = 所有仓库）。targets_file：批处理工具使用的构建目录（见 targets.example.json）。
           profiles_file (profiles.example.json)：批次配置。这些文件中以 "_" 开头的键是元数据。
工作区     可选：存放你仓库本地克隆的文件夹（MONITOR_ROOT、json 中的 "workspace_root"，或含有 .monitor-root 文件的上级文件夹）。
           没有它时，监视器以“精简模式”启动并明确告知：只显示 GitHub API 提供的内容（没有本地签名队列、审计报告，也不读取 CHANGELOG）。
           有它时还会有发布候选、签名队列和批处理工具。签名记录目录："signed_dir"；审计文件目录："audit_dir"。
测试       py -3 -I -m unittest discover -s tests （Linux/macOS：python3 -I -m unittest discover -s tests）。不需要网络。
问题排查   "API rate limit"：gh 的共享配额（每小时 5000 次）已用完；请等待重置（gh api rate_limit），并调大 refresh_seconds / 调小 max_workers。
           gh 无响应时监视器会在启动时停止。损坏的缓存文件会被忽略；删除 sentinel_cache.json 可重新开始缓存。
           更新软件包后请重启监视器（正在运行的进程仍使用旧代码）。

工具       read_report.py [--lang 代码] [--json] [--export-status 目录] [--export-sign-queue 文件]  输出正在运行的监视器的内容（本机，不消耗 GitHub 配额）
           gha_dispatch_all.py [--lang 代码] plan|dispatch|status|finalize|hygiene    批量运行 GitHub Actions 构建（你的电脑上不编译任何东西）
           release_notes.py REPO [--since 标签] [--out 文件]    根据提交生成发布说明草稿（仅为建议；不发布任何内容）
           release_candidates.py    CHANGELOG [Unreleased] 中有条目且上次发布较早的项目（只读）
事件       哨兵每发生一次“变化”（新的红色、CI 恢复、构建卡住、新告警等）就在 events_monitor.jsonl 中写一行 JSON。每行都有与语言无关的稳定 `code`，
           以及 `kind`、`level`、`repo`、`args` 和以配置语言写成的 `text`。可用 `tail -F` 跟踪。
红色 CI    只有一个标准：默认分支上每个 workflow 的“最后一次已结束的运行”。红色 = failure、timed_out、startup_failure 或 action_required。
           cancelled、skipped、neutral 和 stale 不计入。

1.5.1 的新功能(历史:CHANGELOG.md)
  - 设置标签页：新增“哨兵使用的外部 AI”分组（ai.provider none / ollama / openai-compatible、模型、Ollama 地址（仅限本机）、https 端点、保存密钥的环境变量名称、每日调用次数）。密钥本身绝不会被保存。默认关闭；外部服务会收到你仓库的数据。
  - migrate_state.py：把 1.5.0 之前写入的文件改为新名称。`python migrate_state.py` 为演练；`--apply` 复制（旧文件保留），`--move` 重命名。不会覆盖任何内容。docs/MIGRATING.md 用 8 种语言写成一页。
  - 没有自己的目录文件时的首次启动：监视器会在控制台说明正在使用示例文件，`--init-catalog` 会创建 ecosystems.json、targets.json 和 profiles.json 的可编辑副本。
  - Python 3.11 或更高版本（在 Windows、Linux 和 macOS 上用 3.11 和 3.13 测试）。

1.5.0 的新功能(历史:CHANGELOG.md)
  - “设置”选项卡:在页面中修改 actions_monitor.json 的值(带类型和范围的允许键列表,经过校验,每次保存前在 config_backups/ 留副本,绝不处理令牌或密钥;docs/SETTINGS.md)。
  - 有浮雕感、悬停发光、按下凹陷的按钮,带名称和提示的 8 语言 SVG 图标,与状态仪表板一致的外观,有动感的条形和数字(prefers-reduced-motion 时全部停止)。
  - 可选输出,默认关闭,仅在 127.0.0.1 上:/metrics(Prometheus)、/api/outputs/grafana.json(Grafana JSON / Infinity)、/api/outputs/dashboard.json(docs/OUTPUTS.md,示例仪表板在 docs/grafana/)。
  - 中立的软件包:你的生态系统、目标和配置文件放在包外(ecosystems_file、targets_file、profiles_file;本地签名工具用 tools_dir);默认英语;文件和文件夹名称为英语。
  从 1.4.x 更新:以下名称已更改(旧名称在可能存在文件的地方仍会被读取;只写入新名称):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

1.4.2 的新内容(历史:CHANGELOG.md)
  A2 查询被隐藏 workflow 的最近一次运行时,进行中或已取消的运行不再算作“已看到”(它可能掩盖更早的红色):哨兵会取该 workflow 最近已完成的运行,
  使用第一个有真实结论的(cancelled 和 skipped 被忽略)。若默认分支上没有,则只有该 workflow 仍为不确定。

1.4.1 的新内容(历史:CHANGELOG.md)
  A2 不再仅因运行样本已满就把整个仓库判为无法判定:对克隆中未出现在样本里的每个 workflow,单独向 GitHub 查询该 workflow 在默认分支上的最近一次运行
  (只读,与 A10 相同的配额闸门,受 sentinel.a2_resolve_max_calls_per_tick 限制,答案保存 sentinel.a2_resolve_ttl_seconds 秒)。红色按红色计算;
  默认分支上没有运行的 workflow 仍然无法判定,面板会点名该 workflow。

1.4.0 的新内容(历史:CHANGELOG.md)
  A11“就绪”面板:按仓库显示发布就绪情况(默认分支的 CI 及其提交、版本是否高于最近一次发布、构建、签名、下一步),
  生态系统健康度(仅用真实计数计算得分,有数据的仓库太少时不显示),以及落后于其提供方的固定版本
  (从本地克隆中的固定文件读取,在 sentinel.readiness.pins.sources 中配置)。只读;不做任何估计。

1.3.0 的新内容（历史：CHANGELOG.md）
  页面、命令行、事件和报告支持 8 种语言；语言选择器；生态系统、目标和 GitHub 账户改为数据（github_owner、ecosystems_file、targets_file）；
  可选的工作区与如实说明的精简模式；每个文件都带有作者声明和 GPL-3.0-or-later；LICENSE、NOTICE、AUTHORS；8 种语言的 README 和 QUICKSTART。
许可证     GPL-3.0-or-later（见 LICENSE 和 NOTICE）。Copyright (C) 2026 JuanenRac (Electro Hobby 3D)。

帮助、关于与检查 (1.6.4)
------------------------
页面有帮助按钮（圆形 ?）和关于按钮（i）；在控制台使用 --help-topics、--help-search、--about 和 --doctor；--demo 用虚构数据显示页面。精简版以自己的横幅和窗口标题启动（LITE、端口 8766、无哨兵）；完整版显示 COMPLETE、端口 8765、哨兵已启用。新版本提示可以关闭（设置 > 基本）。
