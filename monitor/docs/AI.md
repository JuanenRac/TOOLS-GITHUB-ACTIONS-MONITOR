<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# The AI assistant of the sentinel

Optional and **off by default**. A language model can summarise the daily report, triage alerts, explain a failed run, draft release notes and answer a question about one repository. Everything it writes is shown as an unverified proposal.

## Providers

- `ollama`: a model on this computer (`127.0.0.1` only; nothing leaves the computer).
- `openai-compatible`: any service with an OpenAI-style chat endpoint. This also serves Gemini (its OpenAI-compatible endpoint) and OpenAI itself: set `base_url`, `model` and the NAME of the variable that holds the key.
- `anthropic`: the Messages API of Anthropic (`https://api.anthropic.com`, headers `x-api-key` and `anthropic-version`). You choose the model; none is built in.
- `copilot`: `gh copilot` with your own GitHub login (no key in the monitor), text answer only and no tools. It spends premium requests of your Copilot plan. Run `gh copilot` once by hand so that the CLI is installed.
- The key is never saved: you set the NAME of an environment variable. The three remote providers SEND data of your repositories to a third party.


## What it may see

- Every input is cleaned: control characters removed, secrets redacted by pattern, length capped, the content placed between random delimiters and declared untrusted data. The answer is cut and its links defused.
- The same single cleaner (tokens, keys, credentials inside addresses, e-mail addresses, IP addresses, your home folder) serves this assistant, the feed for AIs, the endpoints and the hook. It works by pattern: it lowers the risk, it is not a guarantee. A call to a provider never follows a redirect (the key would go on to another address) and does not use the proxy variables of the environment: a server on this computer is called directly, and a remote one only goes through the proxy with `network.use_proxy`.
- In the Settings tab you choose the kinds of event it may analyse (`build`, `codeql`, `report`), the repositories it may see (empty = the ones the monitor watches), the language of the answers, the daily limit of calls and the size limits. A button tests the connection and the page shows the calls used today.


## Proposing and running actions

- Level 3 (`ai.actions.enabled`): a command in the answer is kept only if it matches the CLOSED LIST: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` and `act -W FILE -j JOB` (this last one is only ever shown). The command shown is rebuilt from the checked pieces, never copied from the model; the repository and the run or issue number must be ones the monitor already watches.
- Level 4 (`ai.actions.execute`, its own switch, off): each proposal has a confirm button; a dialog shows the whole command and nothing runs until you accept. It runs with your own `gh` login and no shell, at most `ai.actions.max_per_hour` per hour, each attempt goes to the local log shown in the page, and after two failures in a row the actions lock until you unlock them.
- Not in the list, on purpose: deleting branches, closing or merging pull requests, anything about secrets or settings.

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
