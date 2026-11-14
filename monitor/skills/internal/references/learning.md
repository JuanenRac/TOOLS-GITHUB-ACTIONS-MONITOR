<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# The book of failures and the library of lessons

Local and read only. When the feed of alerts opens a failure the monitor writes one line to the book (`failures.jsonl`, schema 1: repo, workflow, job, step, event, branch, actor_kind, category, root_cause, avoidable, run_id, lesson_ref, had_lesson, sha, url, source) after cleaning every secret. Rules (`lessons_rules.json`, editable) put it in a category: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other.

The library (`lessons.json`, editable; the built-in lessons exist in eight languages) gives, per category, what failed, why, what to do and the guard that would have stopped it. The analysis counts the failures of each category in 24 hours and 7 days, compares with the 7 days before (new, up, down, flat) and calls a kind repeated from `lessons.recurring_from` failures in 7 days.

How you use it: read `GET /api/ai/lessons` (`apply_now` first), quote the lesson, mention the trend. Before a person pushes, `GET /api/ai/lessons?fmt=brief&repo=NAME` is the brief to read. To propose: a draft with category (a lower-case word), what, why, do, guard. The code reaches all this through the interface `LessonProvider` (applicable, recurrences, pre_push_brief, propose, register); the one in use is `FileProvider`.
