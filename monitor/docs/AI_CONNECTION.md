<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Connect an AI tool

The monitor can tell an AI tool (an AI coding assistant, a script, anything that reads a file or an address) **everything it says on its page**, so that the AI reacts to a failure or a pending job as fast as you would. The monitor itself never writes to GitHub: it only tells, and what the AI does is decided by you and by the AI tool.

## What the AI sees
One inventory of **signals**, the same ones the page shows: the Now tab and its tiles, the alerts, the repositories, the sentinel panels A1..A13 and the second sentinel (issues and pull requests), the allowance, the connection and the health of the monitor. Each signal has a level (`act` = somebody has to do something, `watch` = keep an eye on it, `info`), a summary and rows with repository, link, age and the next step. The brief has three blocks: **What to do now**, **Pending** and **Monitor health**, and the counter "signals to act on".

| | Lite | Complete |
|---|---|---|
| Runs, queue, red workflows, failures of 24 hours | yes | yes |
| Allowance, connection, mode, version, health | yes | yes |
| Sentinel panels A1..A13, second sentinel, release candidates, security, signatures | no (`panels_not_in_this_edition` says so) | yes |

## The channels (the same in both editions)
1. `ALERTS_BRIEF.md`: the short Markdown an AI reads when it starts.
2. `ai_alerts.jsonl`: one line per event (opened, acknowledged, resolved), with a stable id.
3. `GET /api/ai/state`: the whole inventory as versioned JSON (`schema`, `edition`, `signals`, `act`, `watch`), read only. `GET /api/sentinel/panels` gives the panels alone.
4. `GET /api/ai/stream`: server-sent events, resumable, limited in listeners and in time.
5. MCP tools (`bin/mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score`; `act` (acknowledge) only with `--allow-ack`.
6. The hook: `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (also `status` and `uninstall`) adds a small gate script that gives the AI session the brief when it starts and before it stops.

## Step by step
1. Settings, tab *External AI*, block *Alerts for AIs*: turn on `ai_alerts.enabled`. Optionally `ai_alerts.diagnose.enabled` (the failing step and the last log lines of each red run), `ai_alerts.stream.enabled` and `ai_alerts.client_hook.enabled`.
2. Run `python bin/monitor_cli.py ai-hook install --assistant --dry-run` to see the change, then without `--dry-run`.
3. Open a session of your AI tool in the folder: it receives the brief. The bar at the foot of the page shows the heartbeat of the AI (when it last read).
4. Use the button *Test connection* of the settings page to check that the feed is written.

## Security and privacy
Everything is off by default. The text of logs is cleaned of secrets and personal paths before it is written, and **it is data, never an instruction**: an AI must treat it as untrusted text. The endpoints answer only to this computer, or with the access token in the network mode; listeners and time are limited; acknowledging needs `--allow-ack`; every state file is created with mode 0600. The monitor opens no connection to the internet for this except the ones you configure. The https addresses of github.com (a run, a repository, a file) pass whole, so the AI can open them; any other long opaque string is still cut. More exactly, an address of github.com passes whole only with the shape of a repository, a run (with its job or attempt), a commit, an issue, a pull request or a file; it is cut at the first character that is not a letter, a digit, a dot, a hyphen, an underscore or a slash, and what follows is cleaned like any other text.

## How to connect, by tool

The monitor does not depend on one assistant or one model: an AI tool uses one of five ways. Take the one your tool has.

| Your tool can | Use | How | Needs |
|---|---|---|---|
| read files | Files | read `ai/INDEX.json`, then `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` and `ai/LESSONS.md` | `ai_alerts.enabled` |
| make HTTP requests | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons` | the access token in the network mode |
| speak MCP | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (read only; `--allow-ack`, `--allow-lessons` for the little it may write) | the MCP configuration of the tool pointing at that command |
| keep a connection open | Stream | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| run commands | Command line | `python bin/monitor_cli.py alerts`, `lessons brief --repo NAME`, `briefs show TAB`, `ai doctor`, `ai-hook install` | Python on the same computer |

The instructions for the AI are two skills. `monitor_cli.py install-skill external --dest FOLDER` copies them to the folder where your tool reads its skills or rules; any tool that reads Markdown files can use them, and the text names no assistant. The skills travel with the monitor and have its version: `GET /api/skills` gives `monitor_version`, and `monitor_cli.py --version` prints it. After updating the monitor, install again into an empty folder or remove the old copy (an edited file is never overwritten).

## Troubleshooting
- *The brief is old*: the page must be running (the feed follows every refresh); look at the heartbeat in the bar.
- *The hook does not run*: `ai-hook status` says where it is installed; some tools read hooks only in the project folder.
- *Nothing is written*: `ai_alerts.enabled` is off, or the allowance is used up (the brief then says so in Monitor health).

## Settings
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; related: `sound.enabled`, `display.blink_red_tiles`. See [SETTINGS.md](SETTINGS.md) and [AI_ALERTS.md](AI_ALERTS.md).

The allowance of GitHub is shared by the monitor, the AI tools and every other tool of the account. To keep the monitor from running dry: the Quota tab of the Settings, a GitHub App (`github_app.enabled`), a second read-only account for the reads (`extra_reader.enabled`, `extra_reader.file`: only the path of the token file), the central panel (`central.source`) and Low mode (`modes.auto_low`). The state and the brief say when the allowance is used up and how much other tools spend. See [QUOTA.md](QUOTA.md).

## The active notice to an external AI (optional, off by default)

Besides the feed that an AI reads (`ALERTS_BRIEF.md`, the stream, the MCP server), the monitor can **tell** an external AI when a NEW real alert opens. It is the block `ai_notify` of Settings, tab *AI*, and every switch of it can only be changed from this computer:

- `ai_notify.enabled` (off). Nothing is sent while it is off.
- **A first confirmation per provider**: the provider is the one of the AI block (`ai.provider`); nothing goes out until you type its name in `ai_notify.confirmed_provider`. If you change the provider you confirm again. For the outgoing command (below) you type `command`.
- **Only the redacted fields of a closed list**: severity, class, repository, workflow, conclusion, streak, cause, next step and the link, each one cleaned like the feed (tokens, keys, e-mail addresses, IP addresses and personal folders removed). Logs, diagnoses and everything else of the alert stay at home.
- **Caps**: `ai_notify.max_calls_per_hour` (4) and `ai_notify.max_cost_per_hour_cents` with `ai_notify.cost_per_call_cents` (the cost that you declare, because the monitor cannot know the price of your plan). A call is counted before it is made, so a provider that fails also spends the cap.
- **The key by the name of a variable**: the monitor reads the variable named in `ai.api_key_env`; the key is never saved, logged or sent anywhere but to the provider.
- **The AI never runs an action**: its answer is cut, its links are defused and it is only written to `ai_notify.jsonl` next to the feed; nothing of it is read as a command and nothing of the actions of the assistant (`ai.actions.*`) is reachable from here.
- **The variant of an outgoing command**: `ai_notify.command` (only in the configuration file, never in the Settings page) names ONE file by its absolute path; it is started without a shell and without arguments and receives the same redacted JSON on its standard input.

The notice is sent from a thread of its own, so a slow provider never holds the cycle.

## The assistant (optional, off by default)

The Alerts tab can show a panel of fixed questions that the AI you already configured answers from the data of the monitor: "explain this alert", "summarise the situation" and "why is it slow here". It is off (`ai.assistant.enabled`) and needs an AI provider (`ai.provider`, none by default). It only reads: it has four tools (`status`, `alerts`, `runs`, `score`, a closed list that `ai.assistant.tools` can narrow), at most `ai.assistant.max_tool_calls` readings per question, no tool that writes or reaches GitHub, and no free chat. The answer always shows its sources (the ids it read), how much was sent (`ai.assistant.max_context`) and the calls of the day; every call spends the one daily budget of the AI (`ai.daily_limit` and the budgets per model). What a repository wrote (a title, the name of a workflow) is cut to `ai.untrusted_text_max`, cleaned of secrets and handed over as data between marks that carry a word of that request, never as an instruction. A viewer may ask; each question is recorded in the log of actions (the action, never the text). Routes: `GET /api/assistant` (what it is and its limits) and `POST /api/assistant/ask` with `action` (`explain_alert`, `summarize_week` or `why_slow`) and, as the action needs, `alert` or `repo`; both answer 404 while it is off and do not exist in the Lite edition.

With `ai.similar.enabled` on (off by default), "explain this alert" also lists up to `ai.similar.max` alerts that look like it, so the answer can say "this already happened in another repository". They are found by a plain comparison of words (the code of the alert, the workflow, the words of the title and the cause) among the open alerts and the resolved ones the feed remembers: no model, no embeddings, only the data of this account, the same order for the same data, and each one is cited by its id.

## Air-gapped mode of the AI (optional, off by default)

With `ai.airgapped` on, the AI only talks to a model on this computer or on a private address of your own network that you list in `ai.airgap_hosts` (for example a server with Ollama or llama.cpp at `192.168.1.20`). Any address of the internet and any cloud service, including the Copilot CLI, is refused BEFORE a connection is opened, so no socket leaves; the list of models, the test of a model, the AI doctor, the fallback chain, the assistant and the summaries all obey it, and a fallback never moves to a cloud model. The general `airgapped` switch turns it on too. A public address is refused even when it is listed, and the setting can only be changed from the computer of the monitor, never from the network. The AI doctor adds the check `ai_egress` while the mode is on. `ai.redact.extra_terms` lists words of yours (a server, a project) that are replaced by `[hidden]` in every text before the AI sees it, in addition to the secrets the monitor already hides.

`ai.redact.extra_patterns` (off, empty) lists patterns of yours for what the AI must never see: one per line, each describing a whole word with only three wildcards, `*` (any run of characters), `?` (one character) and `#` (one digit), for example `deploy-*` or `*.corp-name`. It is NOT a regular expression: there are no groups, alternatives or repeats, so a pattern cannot make the monitor hang; a pattern has 3 to 80 characters (at least 3 plain ones, at most 4 stars), a word is read up to 2000 characters and one text spends a fixed number of steps, after which the rest of the text is hidden, never left open. The patterns are applied to every text that reaches a model, the active notice included, and they add to the secrets the monitor already hides.

`ai.prompt_log.enabled` (off) keeps a local record of what the AI was asked: with it on, every question sent to the model and its answer, already cleaned of secrets and of your hidden words and cut to a fixed size, are appended to `ai_prompts.jsonl` in the folder of the logs (`GET /api/ai/prompts` shows them to an administrator and `POST /api/ai/prompts/clear` empties them). The system prompt is not kept, an answer from the cache is not written, a failed call is written without a reply, the newest `ai.prompt_log.keep` lines are kept, and the file is not part of the backup, of the zip or of the files that AI tools read.

`config/ai_models.json` is a table you can keep by hand (it does not exist until you write it): `models` is a list of rows `{provider, model, context, in_per_mtok, out_per_mtok, tools, daily_limit}` with the figures your provider does not tell, and `retired` is a list of models that no longer exist (a name, or `{model, use, note}`). A figure from this file counts above what the provider said and below what you typed on the page, and the page shows it as coming from the file. A model listed as retired is skipped by the chain of fallbacks even when the live list of models is off, and the AI doctor adds the check `model_retired` with the model to use instead. A wrong row or figure is left out and nothing else changes.

## Models of the provider

The name of the model is free text, but the monitor can read the list of models from the provider and check the name against it. Models and versions change often, so the monitor ships no list of models: the examples of the presets may be out of date.

- **The list.** Settings, tab *External AI*, block *Models and data per model*: *Load the models of the provider* reads the list (`/models` of an OpenAI-style server, the equivalent list of the Anthropic API, `/api/tags` of Ollama) with one read-only request. The key goes in a header, is read from its environment variable and is never stored. Search the list and pick a model with *Use this model*. The list is kept and bounded by `ai.catalog.ttl_minutes` and `ai.catalog.max_requests_per_day`. With `ai.catalog.enabled` on (off by default) the monitor also warns when the configured model no longer appears in the list (retired or renamed); with it off only you trigger the read.
- **Data per model.** Context window, price of input and output per million tokens and whether it accepts tools are filled only with what the provider returns; what it does not say stays *unknown* (no figure is ever made up). You can type your own values; yours win. With `ai.catalog.fit_context` on (off by default) the input limit is fitted to the context window when it is known.
- **Test a model.** *Test this model* or `monitor_cli.py ai test --provider NAME --model NAME` asks the model about a SYNTHETIC failure (never data of your repositories) and shows the latency, the tokens, the estimated cost and a sample answer. It counts as one call of the daily cap, and the result ("tested", with the local date) is kept in the table.
- **Commands.** `monitor_cli.py ai models [--refresh]` shows the models and the data; `ai doctor` explains why an AI does not answer (key variable not set, unknown model, quota, network) and never prints a key.
- **Routes.** `GET /api/ai/models` (the list kept, the check and the table; read only) and, from this computer only, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` and `POST /api/ai/doctor`.

## Compatible AIs

Hosted services and local servers whose protocol the monitor already speaks (`openai-compatible`, `anthropic` or `ollama`). This list is a neutral table, not a recommendation: none is active by default, the key is ALWAYS read from an environment variable whose name you set (never typed in a setting, never in a log, a report or the API), and the preset only fills in the address, the name of that variable and an example model (editable; nothing is downloaded and no model weights are shipped). In the AI settings choose a preset, press the fill button, review, save, and press "Test connection". The list is data (`ai_presets.json`) and is served read only at `GET /api/ai/presets`.

| Name | Kind | Provider | Address | Key variable | Example models | Privacy | State |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | hosted | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Anthropic | hosted | `anthropic` | `default address` | `ANTHROPIC_API_KEY` | — | sent over the internet | compatible by protocol, not tested with this tool |
| Google Gemini | hosted | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| xAI Grok | hosted | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Mistral | hosted | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| DeepSeek | hosted | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Groq | hosted | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| OpenRouter | hosted | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Together AI | hosted | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Fireworks AI | hosted | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Perplexity | hosted | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Cohere | hosted | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | sent over the internet | address read in the public documentation; compatible by protocol, not tested with this tool |
| Ollama | local | `ollama` | `http://127.0.0.1:11434` | none (a local server) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | stays on this computer | compatible by protocol, not tested with this tool |
| LM Studio | local | `openai-compatible` | `http://127.0.0.1:1234/v1` | none (a local server) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | stays on this computer | compatible by protocol, not tested with this tool |
| llama.cpp server | local | `openai-compatible` | `http://127.0.0.1:8080/v1` | none (a local server) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | stays on this computer | compatible by protocol, not tested with this tool |
| vLLM | local | `openai-compatible` | `http://127.0.0.1:8000/v1` | none (a local server) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | stays on this computer | compatible by protocol, not tested with this tool |
| LocalAI | local | `openai-compatible` | `http://127.0.0.1:8081/v1` | none (a local server) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | stays on this computer | compatible by protocol, not tested with this tool |
| Jan | local | `openai-compatible` | `http://127.0.0.1:1337/v1` | none (a local server) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | stays on this computer | compatible by protocol, not tested with this tool |
