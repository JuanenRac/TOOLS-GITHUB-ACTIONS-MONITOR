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
5. MCP 工具(`mcp_server.py`):`monitor_state`、`signals`、`alerts_open`、`diagnose`、`sentinel_panels`、`get_quota`;`act`(确认)仅在 `--allow-ack` 时可用。
6. 钩子:`python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`(还有 `status` 和 `uninstall`)添加一个小脚本,在 AI 会话开始时和结束前把简报交给它。

## 逐步操作
1. 设置中的“外部 AI”标签页,“AI 警报”区块:打开 `ai_alerts.enabled`。可选 `ai_alerts.diagnose.enabled`(失败的步骤和每个红色运行日志的最后几行)、`ai_alerts.stream.enabled` 和 `ai_alerts.client_hook.enabled`。
2. 运行 `python monitor_cli.py ai-hook install --assistant --dry-run` 查看改动,然后去掉 `--dry-run` 再运行。
3. 在该文件夹中打开 AI 工具的会话:它会收到简报。底部状态栏显示 AI 的心跳(最近一次读取的时间)。
4. 使用设置页面的“测试连接”按钮检查信息流是否已写入。

## 安全与隐私
一切默认关闭。日志文本在写入前会清除机密和个人路径,并且**它是数据,绝不是指令**:AI 必须把它当作不可信文本。端点只响应本机,或在网络模式下需要访问令牌;监听者和时间有限制;确认需要 `--allow-ack`;所有状态文件以 0600 模式创建。除了你配置的连接,监视器不会为此打开任何互联网连接。

## 故障排除
- *简报太旧*:页面必须在运行(信息流随每次刷新更新);查看状态栏中的心跳。
- *钩子没有运行*:`ai-hook status` 会说明安装位置;有些工具只读取项目文件夹中的钩子。
- *什么都没写入*:`ai_alerts.enabled` 已关闭,或配额已用尽(简报会在“监视器健康”中说明)。

## 设置
`ai_alerts.enabled`、`ai_alerts.folder`、`ai_alerts.brief_max_bytes`、`ai_alerts.diagnose.*`、`ai_alerts.cascade.enabled`、`ai_alerts.stream.*`、`ai_alerts.heartbeat.*`、`ai_alerts.client_hook.*`;相关:`sound.enabled`、`display.blink_red_tiles`。参见 [SETTINGS_zho.md](SETTINGS_zho.md) 和 [AI_ALERTS_zho.md](AI_ALERTS_zho.md)。
