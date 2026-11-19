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
