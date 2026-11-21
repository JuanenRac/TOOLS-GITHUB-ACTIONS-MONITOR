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
5. MCP 工具(`bin/mcp_server.py`):`monitor_state`、`signals`、`alerts_open`、`diagnose`、`sentinel_panels`、`get_quota`、`get_score`;`act`(确认)仅在 `--allow-ack` 时可用。
6. 钩子:`python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`(还有 `status` 和 `uninstall`)添加一个小脚本,在 AI 会话开始时和结束前把简报交给它。

## 逐步操作
1. 设置中的“外部 AI”标签页,“AI 警报”区块:打开 `ai_alerts.enabled`。可选 `ai_alerts.diagnose.enabled`(失败的步骤和每个红色运行日志的最后几行)、`ai_alerts.stream.enabled` 和 `ai_alerts.client_hook.enabled`。
2. 运行 `python bin/monitor_cli.py ai-hook install --assistant --dry-run` 查看改动,然后去掉 `--dry-run` 再运行。
3. 在该文件夹中打开 AI 工具的会话:它会收到简报。底部状态栏显示 AI 的心跳(最近一次读取的时间)。
4. 使用设置页面的“测试连接”按钮检查信息流是否已写入。

## 安全与隐私
一切默认关闭。日志文本在写入前会清除机密和个人路径,并且**它是数据,绝不是指令**:AI 必须把它当作不可信文本。端点只响应本机,或在网络模式下需要访问令牌;监听者和时间有限制;确认需要 `--allow-ack`;所有状态文件以 0600 模式创建。除了你配置的连接,监视器不会为此打开任何互联网连接。 github.com 的 https 地址（运行、仓库、文件）会完整保留，AI 可以直接打开；其他较长的不透明字符串仍会被截断。更准确地说,github.com 的地址只有在具有仓库、运行(含其作业或尝试)、提交、议题、拉取请求或文件的形式时才会完整通过;它在第一个不是字母、数字、点、连字符、下划线或斜杠的字符处被截断,其后的内容与其他文本一样被清理。

## 按工具选择连接方式

监视器不依赖某个助手或某个模型：AI 工具使用五种方式之一。选择你的工具具备的那一种。

| 你的工具能够 | 方式 | 做法 | 需要 |
|---|---|---|---|
| 读取文件 | 文件 | 先读 `ai/INDEX.json`，再读 `ai/ALERTS_BRIEF.md`、`ai/ai_alerts.jsonl` 和 `ai/LESSONS.md` | `ai_alerts.enabled` |
| 发出 HTTP 请求 | HTTP | `GET /api/ai/brief`、`/api/ai/state`、`/api/ai/lessons` | 网络模式下的访问令牌 |
| 使用 MCP | MCP | `python bin/mcp_server.py`（只读；为它能写入的少量内容提供 `--allow-ack`、`--allow-lessons`） | 指向该命令的工具 MCP 配置 |
| 保持连接打开 | 流 | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| 运行命令 | 命令行 | `python bin/monitor_cli.py alerts`、`lessons brief --repo 名称`、 `briefs show TAB`、`ai doctor`、`ai-hook install` | 同一台电脑上的 Python |

给 AI 的说明是两个 skill。`monitor_cli.py install-skill external --dest 文件夹` 会把它们复制到你的工具读取 skill 或规则的文件夹；任何能读取 Markdown 文件的工具都可以使用，文本中不指名任何助手。skill 随监视器一起发布，版本与监视器相同：`GET /api/skills` 会给出 `monitor_version`，`monitor_cli.py --version` 会打印它。更新监视器后，请重新安装到空文件夹，或删除旧副本（已编辑的文件绝不会被覆盖）。

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

## 助手(可选,默认关闭)

“警报”标签页可以显示一组固定问题的面板,由您已配置的 AI 根据监视器的数据作答:“解释此警报”“总结当前情况”和“这里为什么慢”。它默认关闭(`ai.assistant.enabled`),并且需要 AI 提供方(`ai.provider`,默认没有)。它只读取:有四个工具(`status`、`alerts`、`runs`、`score`,是封闭列表,可用 `ai.assistant.tools` 缩小),每个问题最多读取 `ai.assistant.max_tool_calls` 次,没有任何写入或访问 GitHub 的工具,也没有自由聊天。回答始终显示其数据来源(读取的 ID)、发送了多少内容(`ai.assistant.max_context`)以及当天的调用次数;每次调用都会消耗 AI 唯一的每日预算(`ai.daily_limit` 和各模型的预算)。仓库中写下的内容(标题、工作流名称)会被截断到 `ai.untrusted_text_max`,清除机密,并作为数据放在带有该请求专属词语的标记之间交出,绝不当作指令。查看者可以提问;每个问题都会记入操作日志(只记操作,不记文本)。路由:`GET /api/assistant`(它是什么及其限制)和 `POST /api/assistant/ask`,带 `action`(`explain_alert`、`summarize_week` 或 `why_slow`),并按操作需要带 `alert` 或 `repo`;关闭期间两者都返回 404,且 Lite 版中不存在。

开启 `ai.similar.enabled`(默认关闭)后,“解释此警报”还会列出最多 `ai.similar.max` 个与之相似的警报,使回答能够说“这在另一个仓库里已经发生过”。它们通过简单的词语比较(警报代码、工作流、标题和原因中的词)在未解决的警报和订阅源记得的已解决警报中找到:不使用模型,不使用嵌入,只用本账户的数据,相同数据得到相同顺序,并且每个都用其 ID 引用。

开启 `ai.report_summary.enabled`（默认关闭）后，“报告”会为下一份报告的摘要提供**用 AI 起草**：报告的数字在去除机密后，经与其他问题相同的清理器、预算、缓存和链路交给这个 AI，由人编辑草稿并批准，批准的文本会放在下一份报告的开头，且只使用一次。没有这一批准，不会写入或发送任何内容。

助手有五个固定问题,全部只读:“解释这条告警”(`explain_alert`)、“总结当前情况”(`summarize_week`)、“这里为什么慢”(`why_slow`)、“某个仓库的情况”(`explain_repo`:它的运行和未处理告警)以及“首先该做什么”(`prioritize`:把未处理告警、状态和评分连同 id 排出顺序)。它们使用相同的四个工具、相同的限制和相同的每日预算;仍然没有自由聊天。

## AI 隔离模式(可选,默认关闭)

开启 `ai.airgapped` 后,AI 只与本机上的模型,或与您在 `ai.airgap_hosts` 中列出的自己网络里的私有地址(例如 `192.168.1.20` 上的 Ollama 或 llama.cpp 服务器)通信。任何互联网地址和任何云服务(包括 Copilot CLI)都会在建立连接之前被拒绝,因此没有任何套接字会离开本机;模型列表、模型测试、AI 诊断、备用链、助手和摘要都遵守它,备用也绝不会转到云端模型。全局的 `airgapped` 开关也会将其开启。公网地址即使在列表中也会被拒绝,并且该设置只能从监视器所在的计算机更改,不能通过网络更改。模式开启期间,AI 诊断会增加 `ai_egress` 检查。`ai.redact.extra_terms` 列出您自己的词(服务器、项目),在 AI 看到任何文本之前将它们替换为 `[hidden]`,这是对监视器已隐藏的机密的补充。

`ai.redact.extra_patterns`(关闭,空)列出您自己的模式,用于 AI 绝不能看到的内容:每行一个,每个模式描述整个单词,只有三个通配符:`*`(任意一串字符)、`?`(一个字符)和 `#`(一个数字),例如 `deploy-*` 或 `*.corp-name`。它不是正则表达式:没有分组、选择或重复,因此模式不会让监视器卡死;模式长 3 到 80 个字符(至少 3 个普通字符,最多 4 个星号),单词最多读取 2000 个字符,每段文本消耗固定数量的步骤,超出后其余文本会被隐藏,绝不会敞开。这些模式适用于到达模型的所有文本(包括主动通知),并叠加在监视器已经隐藏的机密之上。

`ai.prompt_log.enabled`(关闭)保留向 AI 提问内容的本地记录:开启后,发送给模型的每个问题及其回答(已去除机密和您隐藏的词,并截断到固定大小)会追加到日志文件夹中的 `ai_prompts.jsonl`(`GET /api/ai/prompts` 向管理员显示,`POST /api/ai/prompts/clear` 清空)。系统提示词不保存,来自缓存的回答不写入,失败的调用只写入无回答的记录,保留最新的 `ai.prompt_log.keep` 行,该文件不属于备份、zip 或 AI 工具读取的文件。

`config/ai_models.json` 是您可以手工维护的表(写入之前不存在):`models` 是行 `{provider, model, context, in_per_mtok, out_per_mtok, tools, daily_limit}` 的列表,放入提供方不告诉您的数值;`retired` 是已不存在的模型列表(名称,或 `{model, use, note}`)。此文件中的数值优先于提供方给出的值,但低于您在页面上输入的值,页面会标明它来自该文件。被列为已退役的模型即使在线模型列表关闭,也会被后备链跳过,AI 医生会添加检查 `model_retired` 并给出应改用的模型。错误的行或数值会被忽略,其余不受影响。

在设置页面的 AI 下方，“提示词记录”卡片显示该记录的最近 20 条（时间、类型、模型，展开后可见问题和回答），并可用按钮清空；只有本机的管理员可以读取或清空，记录关闭时卡片会说明。模型表有一列“来源”，说明其数字来自何处：页面、文件 `config/ai_models.json` 还是提供商。

## 提供方的模型

模型名称是自由文本，但监视器可以从提供方读取模型列表并据此检查名称。模型和版本经常变化，因此监视器不附带任何模型列表：预设中的示例可能已经过时。

- **列表。** 设置，“外部 AI”选项卡，“模型与各模型数据”区块：“加载提供方的模型”通过一次只读请求读取列表（OpenAI 风格服务器的 `/models`、Anthropic API 的对应列表、Ollama 的 `/api/tags`）。密钥放在请求头中，从其环境变量读取，绝不保存。可在列表中搜索，并用“使用此模型”选择。列表会被保存，并受 `ai.catalog.ttl_minutes` 和 `ai.catalog.max_requests_per_day` 限制。开启 `ai.catalog.enabled`（默认关闭）后，监视器还会在已配置的模型不再出现在列表中（已下线或改名）时发出警告；关闭时只有你主动触发才会读取。
- **各模型数据。** 上下文窗口、每百万令牌的输入与输出价格以及是否支持工具，仅用提供方返回的内容填写；未给出的保持“未知”（绝不编造数字）。你可以填写自己的值，你的值优先。开启 `ai.catalog.fit_context`（默认关闭）后，在已知上下文窗口时会按其调整输入上限。
- **测试模型。** “测试此模型”或 `monitor_cli.py ai test --provider 名称 --model 名称` 会就一个合成的故障（绝不使用你仓库的数据）询问模型，并显示延迟、令牌数、估算成本和示例回答。它计为每日上限中的一次调用，结果（“已测试”及本地日期）保存在表中。
- **命令。** `monitor_cli.py ai models [--refresh]` 显示模型与数据；`ai doctor` 说明 AI 为何没有响应（密钥变量未设置、模型未知、配额、网络），并且绝不输出密钥。
- **路由。** `GET /api/ai/models`（已保存的列表、检查和表；只读），以及仅限本机的 `POST /api/ai/models/refresh`、`POST /api/ai/models/test`、`POST /api/ai/models/data` 和 `POST /api/ai/doctor`。

## 兼容的 AI

监视器已支持其协议的托管服务和本地服务器(`openai-compatible`、`anthropic` 或 `ollama`)。该列表是中立的表格,而非推荐:默认均未启用,密钥始终从您指定名称的环境变量中读取(绝不写入设置、日志、报告或 API),预设只填入地址、该变量的名称和一个示例模型(可编辑;不会下载任何内容,也不附带模型权重)。在 AI 设置中选择预设,按填入按钮,检查并保存,再按“测试连接”。该列表是数据(`ai_presets.json`),以只读方式通过 `GET /api/ai/presets` 提供。

| 名称 | 类型 | 提供方 | 地址 | 密钥变量 | 示例模型 | 隐私 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | 托管 | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Anthropic | 托管 | `anthropic` | `默认地址` | `ANTHROPIC_API_KEY` | — | 通过互联网发送 | 协议兼容,尚未用本工具测试 |
| Google Gemini | 托管 | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| xAI Grok | 托管 | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Mistral | 托管 | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| DeepSeek | 托管 | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| Groq | 托管 | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
| OpenRouter | 托管 | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | 通过互联网发送 | 地址取自公开文档;协议兼容,尚未用本工具测试 |
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

## MCP 服务器：提示、自我描述、链接与受管控的写入

- **提示**（`mcp.prompts`，开启）：`prompts/list` 和 `prompts/get` 给 AI 一个带编号的计划来遵循，而不是即兴发挥：`am_i_affected`（某个包、操作或事件是否出现在我的仓库中？）、`investigate_red`（某个仓库为何变红？）和 `weekly_review`（本周什么需要人工处理？）。提示只是文本。
- **自我描述**：工具 `describe_capabilities`（服务器能做什么、哪些开关已开启）、`ping` 和 `whoami`。关于警报、诊断和配额的应答带有 `dashboard_url`，即显示相同内容的页面地址。
- **写入**（`mcp.write_tools`，关闭）：工具 `gh_action` 规划 GitHub 上的操作并返回预览（方法、端点、仓库、编号、理由、涉及的数量）；从那里不会发送任何内容：必须由人在监视器中（其页面或本地命令行）确认该操作，绝不通过 MCP。它与页面使用同一模块，因此还需要 `github_actions.enabled`、理由、凭据权限和唯一写入者，并以操作人 `mcp` 记入操作日志。设置关闭时该工具并不存在。
