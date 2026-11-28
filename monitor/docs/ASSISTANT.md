<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# The assistant

Fixed questions to the AI you already set up, answered from the data of the monitor, read only. Off by default.

## Turn it on

1. Set up an AI provider (`ai.provider`; see [AI_CONNECTION.md](AI_CONNECTION.md)).
2. In Settings, AI, switch on `ai.assistant.enabled`. The panel appears in the Alerts tab. It does not exist in the Lite edition.
3. Ask a question; the answer shows its sources, how much was sent and the calls of the day.

## The five questions

- `explain_alert`: why one alert is open (needs the alert).
- `summarize_week`: the situation of the account.
- `why_slow`: why the CI of one repository is slow or stuck (needs the repository).
- `explain_repo`: the situation of one repository, its runs and its open alerts.
- `prioritize`: the open alerts, the status and the score put in order, with their ids.

There is no free chat.

## What it reads

Four tools, a closed list that `ai.assistant.tools` can narrow: `status`, `alerts`, `runs` and `score`. At most `ai.assistant.max_tool_calls` readings per question and `ai.assistant.max_context` of text sent. With `ai.similar.enabled` on, "explain this alert" also lists alerts that look like it, found by comparing words, with no model.

## What it never does

It writes nothing and reaches nothing on GitHub. What a repository wrote (a title, the name of a workflow) is cut, cleaned of secrets and of the words you hid, and handed over as data between marks, never as an instruction. Every question spends the one daily budget of the AI (`ai.daily_limit`). With `ai.airgapped` on, only a model on this computer or on your private network is used.

## Check it

`GET /api/assistant` says what it is and its limits; `POST /api/assistant/ask` takes `action` and, as it needs, `alert` or `repo`. Both answer 404 while it is off. The question is recorded in the log of actions (never its text); with `ai.prompt_log.enabled` the cleaned prompts are kept in a local record you can see and empty in Settings.

## Proposals that people approve

Every command an AI proposes (`ai.actions.enabled`) is marked as coming from an AI, carries a fingerprint (SHA-256) of what would run and is kept until it expires, also across a restart. It never runs by itself. Approving it from the page or the command line is a decision of people: with two or more users two persons are needed (whoever asked the AI counts as one and cannot approve their own); with one user you type the first eight characters of the fingerprint. One person may reject. With `ai.assistant.can_propose` (off) an answer of the chat may also become a proposal. The Alerts tab shows them.

## Free chat

`ai.chat.enabled` (off) adds a chat in the Alerts tab. The AI can only read, with the four tools above; it asks for them and the monitor decides. Same budget, same cleaner, same marks around what repositories wrote; each answer lists what was read. There is no tool that writes.

## Similar alerts with a local model

With `ai.rag.enabled` (off) and `ai.rag.model`, "explain this alert" ranks alerts by the embeddings of a model that runs on this computer (the API of Ollama; only a loopback address is accepted). The index keeps vectors and hashes, never the text, up to `ai.rag.max_mb`; deleting `ai_rag_index.json` loses nothing. Without the model the word comparison is used. It has been tested with a fake server only.

## Report of a repository

With `ui.copy_report.enabled` the Alerts tab copies the report of a repository in Markdown, or a draft of a triage comment, to paste by hand. No AI, no request to GitHub, nothing published.

Routes: `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`. For MCP clients the briefs are also resources: `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`.
