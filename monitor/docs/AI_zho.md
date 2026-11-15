<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# 哨兵的 AI 助手

可选功能,**默认关闭**。语言模型可以总结每日报告、对警报分类、解释失败的运行、起草发布说明,并回答关于某个仓库的问题。它写的所有内容都会显示为未经验证的建议。

## 提供方

- `ollama`:本机上的模型(仅限 `127.0.0.1`;没有任何内容离开本机)。
- `openai-compatible`:任何提供 OpenAI 风格聊天端点的服务。也适用于 Gemini(其 OpenAI 兼容端点)和 OpenAI 本身:设置 `base_url`、`model` 以及保存密钥的变量名称。
- `anthropic`:Anthropic 的 Messages API(`https://api.anthropic.com`,请求头 `x-api-key` 和 `anthropic-version`)。模型由你选择,没有内置的。
- `copilot`:使用你自己的 GitHub 登录运行 `gh copilot`(监视器中没有密钥),只返回文本且不使用工具。它会消耗你 Copilot 套餐的高级请求。请手动运行一次 `gh copilot` 以安装该 CLI。
- 密钥从不保存:你设置的是环境变量的名称。三个远程提供方会把你仓库的数据发送给第三方。


## 它能看到什么

- 所有输入都会被清理:去除控制字符、按模式遮盖密钥、限制长度、把内容放在随机分隔符之间并声明为不可信数据。回答会被截断,其中的链接会被失效处理。
- 在设置标签页中你可以选择它可分析的事件类型(`build`、`codeql`、`report`)、它可查看的仓库(留空=监视器监视的仓库)、回答语言、每日调用上限和大小上限。按钮可测试连接,页面显示今天的调用次数。


## 提出并执行操作

- 第 3 级(`ai.actions.enabled`):回答中的命令只有匹配封闭列表才会保留:`gh run rerun N --failed`、`gh run rerun N`、`gh issue close N` 和 `act -W 文件 -j 作业`(最后一个只显示)。显示的命令由已检查的部分重新组装,绝不从模型文本复制;仓库以及运行或 issue 编号必须是监视器已在监视的。
- 第 4 级(`ai.actions.execute`,独立开关,默认关闭):每个建议都有确认按钮;对话框显示完整命令,在你接受之前不会运行任何内容。它使用你自己的 `gh` 登录且不经过 shell,每小时最多 `ai.actions.max_per_hour` 次,每次尝试都记入页面显示的本地日志,连续失败两次后操作会锁定,直到你解锁。
- 刻意不在列表中的:删除分支、关闭或合并拉取请求、任何与密钥或设置有关的操作。

## 兼容的 AI

监视器已支持其协议的托管服务和本地服务器(`openai-compatible`、`anthropic` 或 `ollama`)。该列表是中立的表格,而非推荐:默认均未启用,密钥始终从您指定名称的环境变量中读取(绝不写入设置、日志、报告或 API),预设只填入地址、该变量的名称和一个示例模型(可编辑;不会下载任何内容,也不附带模型权重)。在 AI 设置中选择预设,按填入按钮,检查并保存,再按“测试连接”。该列表是数据(`ai_presets.json`),以只读方式通过 `GET /api/ai/presets` 提供。

| 名称 | 类型 | 提供方 | 地址 | 密钥变量 | 示例模型 | 隐私 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | 托管 | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Anthropic | 托管 | `anthropic` | `默认地址` | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Google Gemini | 托管 | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| xAI Grok | 托管 | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Mistral | 托管 | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| DeepSeek | 托管 | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-chat` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Groq | 托管 | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| OpenRouter | 托管 | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Together AI | 托管 | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Fireworks AI | 托管 | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Perplexity | 托管 | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Cohere | 托管 | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Ollama | 本地 | `ollama` | `http://127.0.0.1:11434` | 无(本地服务器) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | 保留在本机 | 协议兼容,尚未用本工具测试 |
| LM Studio | 本地 | `openai-compatible` | `http://127.0.0.1:1234/v1` | 无(本地服务器) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | 保留在本机 | 协议兼容,尚未用本工具测试 |
| llama.cpp server | 本地 | `openai-compatible` | `http://127.0.0.1:8080/v1` | 无(本地服务器) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | 保留在本机 | 协议兼容,尚未用本工具测试 |
| vLLM | 本地 | `openai-compatible` | `http://127.0.0.1:8000/v1` | 无(本地服务器) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | 保留在本机 | 协议兼容,尚未用本工具测试 |
| LocalAI | 本地 | `openai-compatible` | `http://127.0.0.1:8081/v1` | 无(本地服务器) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | 保留在本机 | 协议兼容,尚未用本工具测试 |
| Jan | 本地 | `openai-compatible` | `http://127.0.0.1:1337/v1` | 无(本地服务器) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | 保留在本机 | 协议兼容,尚未用本工具测试 |
