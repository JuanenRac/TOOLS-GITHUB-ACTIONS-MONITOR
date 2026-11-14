<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Scenarios for an AI outside the monitor

Each scenario: what to look at, what to do, what NOT to do.

## A real red
Look: the brief, then the alert with its `diagnosis`, then `GET /api/ai/lessons`. Do: read the first failing step, apply the lesson of the category, fix, push after the brief before a push. Do NOT: re-run a real failure hoping it passes; acknowledge an alert you did not fix.

## A transient red
Look: `class: transient` (502, timeout, rate limit, runner shut down, startup_failure). Do: re-run the failed jobs once and look again. If it repeats, it is real. Do NOT: change code for it.

## Low quota
Look: `GET /api/quota`, `/api/quota-pool/status`, `/api/mode`. Do: read the feed and the brief only, no `gh` calls, wait for the reset; the settings `readpool.*` and `savings.*` are for a person. Do NOT: poll, rotate tokens or accounts.

## A degraded monitor
Look: `/api/health?deep=1`, `/api/ai/state` (`warnings`, `stale`). A TypeError counted as degraded is a defect of the monitor: report it with its origin and kind. Do NOT: act on a brief that says it is old.

## A repeated failure
Look: `recurring`, `trend`, `repos`, `propose_guard`. Do: write the guard (`references/learning-cycle.md`) before the next push. Do NOT: close the round without it.

## A new lesson
Look: category `other`, or a reason no lesson covers. Do: draft with `POST /api/ai/lessons` (no `confirm`), show the draft to a person, write only with `lessons.allow_write`, an administrator and a confirmation. Do NOT: write it without all three.

## No network
Look: `/api/health` (`offline`). Do: say that the picture is the last complete one and read the files in `ai/`. Do NOT: say a run is green.

## Several screens
`/screen/1` to `/screen/3` are views of the same data; nothing differs for you. Do NOT: poll each one.
