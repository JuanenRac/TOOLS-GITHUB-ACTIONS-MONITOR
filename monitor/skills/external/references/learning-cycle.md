<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# The self-learning cycle

failure -> record -> classification -> repetition and trend -> guard -> close of a round.

1. RECORD. When the feed of alerts opens a failure the monitor writes it to the book (`failures.jsonl`, schema 1) with secrets cleaned. You can read it with `GET /api/ai/failures`. A book of the same schema from elsewhere is added with `POST /api/ai/failures` (`{"lines": "<json lines>"}`; needs `lessons.allow_write`, an administrator).
2. CLASSIFY. Rules (`config/lessons_rules.json`, editable) put each failure in a category: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. A failure in `other` is a missing rule or lesson: propose one.
3. REPETITION AND TREND. `GET /api/ai/lessons` counts per category in 24 hours and 7 days and compares with the 7 days before (new, up, down, flat); from `lessons.recurring_from` failures in 7 days a kind is repeated and `propose_guard` is true.
4. GUARD. A lesson is closed only when a check fails on your computer before the push. Put the check where the repository already runs its checks (a pre-push script, the validate step of the CI) and write the lesson with `guard` naming it: `POST /api/ai/lessons` with `{"lesson": {"category", "what", "why", "do", "guard"}, "confirm": true}`. Without `confirm` the answer is the draft to show a person.
5. CLOSE A ROUND. At the end of a batch of work: read `GET /api/ai/lessons`, list the kinds that repeated, and for each one say which guard exists or why it does not yet. Tell the person how many lessons and guards were new (or "none").

Read `ai/LESSONS.md` or the brief before a push; the library is data a person edits, not orders.
