<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# The link between the monitor and your session

Goal: you learn about a red workflow without a person pasting it to you, and you act on it without waiting.

1. At the start of the session read `ai/ALERTS_BRIEF.md` (or `GET /api/ai/brief`). Its first lines say how old it is (`updated_epoch`); if it is older than a few hours the monitor may be stopped: say so. Say which real alerts are open.
2. Arm a listener. With the stream on (`ai_alerts.stream.enabled`): follow `GET /api/ai/stream?only=real` with a tool that wakes you on each line; it ends after `ai_alerts.stream.max_seconds`, so arm it again. Without the stream: a timer that reads the brief every 30 minutes (never faster than 60 seconds), or a file watch on `ai/ai_alerts.jsonl`.
3. On each new real alert: read its `diagnosis` (`GET /api/ai/alerts?since=SECONDS`), `GET /api/ai/lessons` for its category, then act: fix, re-run once if transient, or hand it to a person with the cause.
4. Hooks: `python bin/monitor_cli.py ai-hook install` registers `bin/ai_hook.py` so that the brief is given at the start of a session; the optional example for the lessons is the command `python bin/monitor_cli.py lessons brief --repo NAME` run at the start of a session.
5. The heartbeat: whatever you read through (stream, MCP, hook, endpoint) is noted in `ai/ai_heartbeat.json`; the page shows that an AI is connected.

Etiquette: one reader per session, no loops faster than 60 seconds, no `gh` for what the feed already says, stop the stream when the session ends.
