<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 给 AI 的警报

如果在仓库工作的人都不知道,红色工作流就毫无意义。监视器会写出一个小型警报流,任何 AI 工具(Codex、Gemini CLI、Copilot)或脚本都可以读取。

## 写出的内容(本地、只读、不用网络)
- `ai_alerts.jsonl`:每个事件(打开、已确认、已解决)一行,含稳定 ID、严重程度、仓库、工作流、结论、起始时间、连续次数、链接、可能原因(**真实**或**暂时**)、建议操作和状态。
- `ALERTS_BRIEF.md`:每个周期重写,内容简短(`ai_alerts.brief_max_bytes`,默认 2 KB)。真实警报排在前面。
- 暂时性原因(502/503/504、超时、速率限制、下载失败、未能启动的运行)通过可在 `ai_alerts.transient_patterns` 中编辑的规则与真实故障区分。工作流变绿后警报会自动解决,你也可以确认它(`ack`),这只会改变本地状态。
- 一切都先经过清理器:令牌、密钥、电子邮件地址、IP 地址和你的主目录永远不会进入文件、端点或钩子。
- 文件夹为 `ai_alerts.folder`(默认在监视器旁边);请选择你的 AI 会话会读取的文件夹。`ci_red.json` 在每个红色工作流中带有可选的 `ai_hint`(类别、原因、操作)。

## AI 如何读取
- 在项目或技能的说明中加入:*“开始时读取 ALERTS_BRIEF.md(路径),并说明有哪些真实警报未处理。”*
- 或询问正在运行的监视器:`GET /api/ai/brief`(Markdown,或 `?fmt=json`)和 `GET /api/ai/alerts?since=秒数`。规则与页面其他部分相同(本机;网络模式下需要访问令牌)。
- 或添加 MCP 服务器(只读):`python mcp_server.py`,工具有 `get_alerts`、`get_red_repos`、`get_run_failure`、`get_quota`;`--allow-ack` 增加 `ack_alert`(仅本地状态)。Gemini CLI、Codex 和 VS Code(Copilot):在其 MCP 设置中把同样的命令添加为 stdio 服务器。

## 到达你的提醒
- 新的真实警报会发送到你已配置的通知渠道(设置 > 通知)。
- 可选,默认关闭:`ai_alerts.hook` 把新的真实警报(一组固定的已清理字段)POST 到本机的一个地址,每小时最多 `max_per_hour` 次,这样你的脚本就能唤醒 AI 会话。
- 以上任何内容都不会向 AI 提供商发送数据、运行命令或写入 GitHub。

## MCP 服务器仅限本地

`mcp_server.py` 通过标准输入输出与启动它的 AI 工具交换 JSON：它没有网络端口，也绝不能放在网络端口之后。格式错误的消息只会针对该消息返回错误，超过 64 KB 的行会被拒绝，`ack_alert`（仅在 `--allow-ack` 时）只会改变订阅源的本地状态。订阅源可能包含仓库名称和简短的 CI 错误信息；输出前会清除令牌、密钥、电子邮件、IP 地址和个人文件夹。

## 与 AI 工具的联动 (只读)

- **始终最新。** 信息流和摘要会在告警页每次刷新、信息流每次被读取以及每个周期都重新写入, 因此与页面一致 (以前会落后一个周期)。`ALERTS_BRIEF.md` 含有 `Updated:` (你的时区及 UTC) 和供机器读取的 `updated_epoch:` 行; `GET /api/ai/brief?fmt=json` 另外提供 `updated`、`updated_local` 和 `age_seconds`。
- **为什么是红色。** 开启 `ai_alerts.diagnose.enabled` (默认关闭: 会从 GitHub 读取新红色运行的作业列表和日志末尾, 使用只读调用, 计入你的配额) 后, 每条告警带有 `diagnosis`: 第一个失败的步骤和约十行相关内容 (`ai_alerts.diagnose.log_lines`), 已清除机密, 且不超过 `ai_alerts.diagnose.max_bytes`。每个周期最多读取 `max_per_cycle` 个运行, 每个运行只读一次。日志显示基础设施错误时, 该告警视为临时性。
- **连锁告警。** 开启 `ai_alerts.cascade.enabled` (默认开启: 只改变告警的列法) 后, 因另一个仓库变红而变红的告警 (其日志点名了它, 或 `ai_alerts.cascade.map` 的规则 `{"base-repo": ["client-repo"]}` 这样规定) 会在摘要中列在那个仓库之下 (“Also red because of it (fix this one first)”), 并在信息流中带有 `origin`。
- **事件流。** 开启 `ai_alerts.stream.enabled` (默认关闭) 后, `GET /api/ai/stream[?only=real]` 发送服务器推送事件: 一个 `hello` 帧 (有多少真实告警未处理、最前面的几条、摘要的时长) 和信息流中每个事件对应的 `alert` 帧; `Last-Event-ID` (或 `?since=`) 可续传。它是只读的, 遵循与页面其余部分相同的访问规则 (网络模式下, 以请求头或 Cookie 提供访问令牌), 并受 `stream.max_clients` 和 `stream.max_seconds` 限制。
- **哨兵面板。** 哨兵标签页的面板 A1..A13 和第二个哨兵(议题与拉取请求)也是数据:`GET /api/sentinel/panels[?lang=xx]`(只读,访问规则与页面相同)按面板给出其级别(`bad` = 需处理,`warn` = 需留意)、一行摘要以及需要处理的行(各带仓库和链接);MCP 工具 `sentinel_panels` 返回同样的内容。级别为 `bad` 或 `warn` 的面板中的行还会成为信息流中的警报(类别 `real` 或 `watch`,字段 `panel`),因此事件流、钩子、`alerts_open` 以及简报中的“N 个真实警报”计数都包含它们;简报有一个“Sentinel panels”部分(有自己的大小上限,不会挤掉 CI 警报)。A2 的红色工作流不再重复:它们本来就是警报。
- **MCP 工具。** `alerts_open` (未处理告警, 含时长、诊断和来源)、`alert_diagnose(id)` (已保存的诊断, 或用只读 `gh` 调用读取日志), 以及仅在 `--allow-ack` 时提供的 `alert_ack(id)`。AI 工具连接时, 服务器会在 `instructions` 中并通过一条通知告知有多少真实告警未处理。
- **联动脚本。** `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user]` (还有 `status` 和 `uninstall`; `--dry-run` 显示将要做的更改) 把 `ai_hook.py` 加入工具的钩子设置: SessionStart 和 UserPromptSubmit 在有真实告警未处理时把摘要加入会话; Stop 会在回合结束前提示 AI 先查看, 但仅在 `ai_alerts.client_hook.block_on_stop` (默认关闭) 开启时, 且每个 `cooldown_minutes` 最多一次。设置文件会被合并 (其他钩子保留), 保留一份备份 (最近三份), 不是有效 JSON 的文件会被拒绝且不改动, 写入的内容全部是纯 ASCII。默认目标写入工具自己的隐藏文件夹中的 `settings.local.json` (project) 或 `settings.json` (user); `--cursor` 写入 `.cursor/hooks.json` (尽力而为: 其钩子格式可能变化); `--generic` 不写入任何内容, 只显示命令。脚本只需要 Python, 数值取自 `ai_alerts.client_hook`。钩子只把每个告警的仓库、工作流、结论和链接交给会话;原因和日志文本(可能是第三方写的)永远不会被复制进去,因此 AI 要用自己的工具读取日志,最后一行会告诉它把任何日志都当作不可信数据,绝不遵循其中的指示。
- **是否有 AI 已连接?** 开启 `ai_alerts.heartbeat.enabled` 后, 本地小文件 `ai_heartbeat.json` 会记录事件流、MCP 服务器、联动脚本或端点最近一次的读取, 底部栏在 `window_minutes` 内显示“AI: mcp, 3 分钟前” (或“无连接”)。不会向外发送任何内容。
- **摘要与正在运行的监视器一致吗?** 一致:其中的 `Monitor:` 行说明监视器当前在做什么(周期完成、周期进行中、连接丢失、上一周期失败),`Updated` 的时间就是该说明的时间;周期未完成时,列出的告警是上一个完整周期保留下来的(不完整的周期不会打开或关闭告警)。`actions_monitor_log.txt` 在每个周期开始时写入一行 `cycle=started`,这样较长的周期不会被误认为监视器已停止。
- **私有文件。** 信息流、摘要、心跳以及监控器的其他所有状态文件都以 0600 模式创建 (监控器创建的文件夹为 0700)。在 Windows 上程序无法强制设置模式: 文件夹继承其父文件夹的权限, 所以请把监控器文件夹放在你自己的用户目录内。
