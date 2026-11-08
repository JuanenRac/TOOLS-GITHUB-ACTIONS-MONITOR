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
