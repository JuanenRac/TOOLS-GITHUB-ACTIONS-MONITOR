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
- In the Settings tab you choose the kinds of event it may analyse (`build`, `codeql`, `report`), the repositories it may see (empty = the ones the monitor watches), the language of the answers, the daily limit of calls and the size limits. A button tests the connection and the page shows the calls used today.


## Proposing and running actions

- Level 3 (`ai.actions.enabled`): a command in the answer is kept only if it matches the CLOSED LIST: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` and `act -W FILE -j JOB` (this last one is only ever shown). The command shown is rebuilt from the checked pieces, never copied from the model; the repository and the run or issue number must be ones the monitor already watches.
- Level 4 (`ai.actions.execute`, its own switch, off): each proposal has a confirm button; a dialog shows the whole command and nothing runs until you accept. It runs with your own `gh` login and no shell, at most `ai.actions.max_per_hour` per hour, each attempt goes to the local log shown in the page, and after two failures in a row the actions lock until you unlock them.
- Not in the list, on purpose: deleting branches, closing or merging pull requests, anything about secrets or settings.
