<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 助手

向您已配置的 AI 提出固定问题，仅用监视器的数据回答，只读，默认关闭。

## 开启

1. 配置一个 AI 提供商（`ai.provider`；见 [AI_CONNECTION_zho.md](AI_CONNECTION_zho.md)）。
2. 在设置的 AI 中开启 `ai.assistant.enabled`。面板出现在“警报”标签页。Lite 版没有它。
3. 提一个问题；回答会显示其来源、发送了多少内容以及当天的调用次数。

## 五个问题

- `explain_alert`：为何某条警报处于打开状态（需要该警报）。
- `summarize_week`：账户的情况。
- `why_slow`：某个仓库的 CI 为何缓慢或卡住（需要该仓库）。
- `explain_repo`：某个仓库的情况、其运行和未解决的警报。
- `prioritize`：把未解决的警报、状态和评分按顺序排列，并附上其 ID。

没有自由聊天。

## 它读取什么

四个工具，是一份封闭的清单，`ai.assistant.tools` 可以缩小它：`status`、`alerts`、`runs` 和 `score`。每个问题最多读取 `ai.assistant.max_tool_calls` 次，发送的文本不超过 `ai.assistant.max_context`。开启 `ai.similar.enabled` 后，“解释这条警报”还会列出相似的警报，通过比较词语找到，不使用模型。

## 它绝不做什么

它不写入任何内容，也不接触 GitHub。仓库写下的内容（标题、工作流名称）会被截短，去除机密和您隐藏的词，并作为标记之间的数据交出，绝不当作指令。每个问题都会消耗 AI 唯一的每日预算（`ai.daily_limit`）。开启 `ai.airgapped` 后，只使用本机或您私有网络上的模型。

## 检查

`GET /api/assistant` 说明它是什么及其限制；`POST /api/assistant/ask` 接收 `action`，并按需接收 `alert` 或 `repo`。关闭期间两者都返回 404。问题会记入操作日志（不含其文本）；开启 `ai.prompt_log.enabled` 后，清理过的提示词保存在本地记录中，您可在设置里查看和清空。

## 由人批准的提议

AI 提议的每条命令（`ai.actions.enabled`）都标记为来自 AI，带有将要执行内容的指纹（SHA-256），并保留到过期，重启后依然保留。绝不会自行执行。批准是人的决定：两个及以上用户时需要两人（向 AI 提问的人算作一人，且不能批准自己的提议）；单用户时需输入指纹前八位。一人即可拒绝。开启 `ai.assistant.can_propose`（默认关闭）后，聊天回答也可能成为提议。它们显示在告警页。

## 自由聊天

`ai.chat.enabled`（默认关闭）在告警页增加聊天。AI 只能用上面四个工具读取；由它请求，监视器决定。预算、脱敏和数据标记相同；每个回答列出读取内容。没有任何写入工具。

## 用本地模型查找相似告警

开启 `ai.rag.enabled`（默认关闭）并设置 `ai.rag.model` 后，“解释此告警”按本机模型的嵌入排序（Ollama 接口；仅限回环地址）。索引只保存向量和哈希，不存文本，上限 `ai.rag.max_mb`；删除 `ai_rag_index.json` 不丢失任何内容。没有模型时使用词语比较。仅用模拟服务器测试过。

## 仓库报告

开启 `ui.copy_report.enabled` 后，告警页可复制仓库的 Markdown 报告或分诊草稿供手动粘贴。不用 AI、不请求 GitHub、不发布任何内容。

路由：`GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`。MCP 客户端还可将摘要作为资源读取：`resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`。
