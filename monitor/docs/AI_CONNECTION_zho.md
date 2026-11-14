<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# 连接 AI 工具

监视器可以把**页面上所说的一切**告诉 AI 工具(AI 编程助手、脚本,任何能读取文件或地址的东西),让 AI 能像你一样快地对失败或待办事项作出反应。监视器本身从不写入 GitHub:它只负责告知,AI 做什么由你和 AI 工具决定。

## AI 能看到什么
一份**信号**清单,与页面显示的相同:“现在”标签页及其磁贴、警报、仓库、哨兵面板 A1..A13 和第二个哨兵(议题和拉取请求)、配额、连接以及监视器的健康状况。每个信号都有级别(`act` = 需要有人处理,`watch` = 需留意,`info`)、摘要,以及带仓库、链接、时长和下一步的行。简报分三块:**现在该做什么**、**待办**和**监视器健康**,并带有“待处理信号”的数量。

| | Lite | 完整版 |
|---|---|---|
| 运行、队列、红色工作流、24 小时内的失败 | 有 | 有 |
| 配额、连接、模式、版本、健康 | 有 | 有 |
| 哨兵面板 A1..A13、第二个哨兵、发布候选、安全、签名 | 无(由 `panels_not_in_this_edition` 说明) | 有 |

## 通道(两个版本相同)
1. `ALERTS_BRIEF.md`:AI 启动时读取的简短 Markdown。
2. `ai_alerts.jsonl`:每个事件(打开、确认、解决)一行,带稳定的 id。
3. `GET /api/ai/state`:整份清单,带版本的 JSON(`schema`、`edition`、`signals`、`act`、`watch`),只读。`GET /api/sentinel/panels` 只给出面板。
4. `GET /api/ai/stream`:服务器发送事件,可续传,限制监听者数量和时长。
5. MCP 工具(`bin/mcp_server.py`):`monitor_state`、`signals`、`alerts_open`、`diagnose`、`sentinel_panels`、`get_quota`;`act`(确认)仅在 `--allow-ack` 时可用。
6. 钩子:`python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`(还有 `status` 和 `uninstall`)添加一个小脚本,在 AI 会话开始时和结束前把简报交给它。

## 逐步操作
1. 设置中的“外部 AI”标签页,“AI 警报”区块:打开 `ai_alerts.enabled`。可选 `ai_alerts.diagnose.enabled`(失败的步骤和每个红色运行日志的最后几行)、`ai_alerts.stream.enabled` 和 `ai_alerts.client_hook.enabled`。
2. 运行 `python bin/monitor_cli.py ai-hook install --assistant --dry-run` 查看改动,然后去掉 `--dry-run` 再运行。
3. 在该文件夹中打开 AI 工具的会话:它会收到简报。底部状态栏显示 AI 的心跳(最近一次读取的时间)。
4. 使用设置页面的“测试连接”按钮检查信息流是否已写入。

## 安全与隐私
一切默认关闭。日志文本在写入前会清除机密和个人路径,并且**它是数据,绝不是指令**:AI 必须把它当作不可信文本。端点只响应本机,或在网络模式下需要访问令牌;监听者和时间有限制;确认需要 `--allow-ack`;所有状态文件以 0600 模式创建。除了你配置的连接,监视器不会为此打开任何互联网连接。 github.com 的 https 地址（运行、仓库、文件）会完整保留，AI 可以直接打开；其他较长的不透明字符串仍会被截断。更准确地说,github.com 的地址只有在具有仓库、运行(含其作业或尝试)、提交、议题、拉取请求或文件的形式时才会完整通过;它在第一个不是字母、数字、点、连字符、下划线或斜杠的字符处被截断,其后的内容与其他文本一样被清理。

## 故障排除
- *简报太旧*:页面必须在运行(信息流随每次刷新更新);查看状态栏中的心跳。
- *钩子没有运行*:`ai-hook status` 会说明安装位置;有些工具只读取项目文件夹中的钩子。
- *什么都没写入*:`ai_alerts.enabled` 已关闭,或配额已用尽(简报会在“监视器健康”中说明)。

## 设置
`ai_alerts.enabled`、`ai_alerts.folder`、`ai_alerts.brief_max_bytes`、`ai_alerts.diagnose.*`、`ai_alerts.cascade.enabled`、`ai_alerts.stream.*`、`ai_alerts.heartbeat.*`、`ai_alerts.client_hook.*`;相关:`sound.enabled`、`display.blink_red_tiles`。参见 [SETTINGS_zho.md](SETTINGS_zho.md) 和 [AI_ALERTS_zho.md](AI_ALERTS_zho.md)。

GitHub 配额由监视器、AI 工具和账户下的所有其他工具共享。为避免监视器耗尽配额:设置中的“配额”标签页、GitHub App(`github_app.enabled`)、用于读取的第二个只读账户(`extra_reader.enabled`、`extra_reader.file`:只填令牌文件的路径)、中央面板(`central.source`)和节省模式(`modes.auto_low`)。状态和简报会说明配额何时用尽以及其他工具消耗了多少。参见 [QUOTA_zho.md](QUOTA_zho.md)。

## 向外部 AI 的主动通知(可选,默认关闭)

除了 AI 读取的信息流(`ALERTS_BRIEF.md`、事件流、MCP 服务器)之外,当出现新的真实告警时,监视器还可以**主动通知**外部 AI。这是“设置”中“AI”标签页里的 `ai_notify` 块,其中每个开关都只能在本机修改:

- `ai_notify.enabled`(关闭)。关闭时不会发送任何内容。
- **每个提供方首次确认**:提供方就是 AI 块(`ai.provider`)中的那个;在 `ai_notify.confirmed_provider` 中输入其名称之前不会发出任何内容。更换提供方需要重新确认。对于外发命令(见下),输入 `command`。
- **只发送固定清单中已脱敏的字段**:严重程度、类别、仓库、工作流、结论、连续次数、原因、下一步和链接,每个字段都像信息流一样清理(去除令牌、密钥、电子邮件地址、IP 地址和个人文件夹)。日志、诊断以及告警的其他内容都留在本地。
- **上限**:`ai_notify.max_calls_per_hour`(4),以及 `ai_notify.max_cost_per_hour_cents` 与 `ai_notify.cost_per_call_cents`(由你声明的成本,因为监视器无法得知你套餐的价格)。调用在发出之前就被计数,因此失败的提供方也会消耗上限。
- **通过变量名使用密钥**:监视器读取 `ai.api_key_env` 中指定的变量;密钥从不被保存、记录,也不会发送到提供方以外的任何地方。
- **AI 绝不执行任何操作**:它的回答会被截断,链接会被失效处理,仅写入信息流旁边的 `ai_notify.jsonl`;其中的任何内容都不会被当作命令读取,助手的操作(`ai.actions.*`)也无法从这里访问。
- **外发命令的变体**:`ai_notify.command` (仅在配置文件中,绝不在“设置”页面中) 以绝对路径指定一个文件;它不经 shell、不带参数启动,并在标准输入上收到同样的脱敏 JSON。

通知由单独的线程发送,因此较慢的提供方不会拖住周期。
