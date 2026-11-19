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
