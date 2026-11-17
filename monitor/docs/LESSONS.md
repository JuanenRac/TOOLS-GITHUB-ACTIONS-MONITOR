<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# Failures and lessons

The monitor can keep a book of the failures of your CI and a library of lessons, so that the same mistake is not made twice by a person, by an AI tool of yours or by the AI of the monitor. It is **local and read only**: nothing leaves the computer and nothing is written to GitHub. It follows the alerts of the feed for AIs, so it needs `ai_alerts.enabled`.

## The book

Every failure that the feed opens becomes one line of `data/failures.jsonl` (schema 1): `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Every text goes through the same cleaning as the feed (tokens, keys, addresses and the home folder never reach the book). `lessons.retention_days` and `lessons.max_entries` limit its size. A book of the same schema from another place can be imported (`POST /api/ai/failures`).

## The classifier

Each failure is filed under a category by rules, the first that matches wins: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. The rules are in the program; to use your own, write `config/lessons_rules.json`: `{"rules": [{"category": "mine", "label": "My kind", "avoidable": true, "patterns": ["regular expression"]}]}`. The file replaces the built-in rules; a rule or a pattern that is not valid (or longer than 120 characters) is skipped.

## The library of lessons

For each category there is a lesson: what failed, what to do and the guard that would have stopped it. The built-in ones are written in the eight languages. Yours go in `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) and replace the built-in one of the same category.

## Repetition and trend

For each category the monitor counts the failures of the last 24 hours and of the last 7 days and compares the 7 days with the 7 before (new, rising, falling, steady). From `lessons.recurring_from` failures in 7 days a kind of failure is **repeated** and a guard is proposed: a check that fails on your computer before the push.

## What an AI reads

- `ai/LESSONS.md`: compact Markdown (size: `lessons.brief_max_bytes`), rewritten when a failure opens or resolves.
- `GET /api/ai/lessons`: the analysis, the lessons that apply now and the library (`?fmt=md` for the file, `?fmt=brief&repo=NAME` for the brief before a push, `&as=json` to get it inside a JSON).
- `GET /api/ai/failures`: the book, newest first (`?since=SECONDS&repo=NAME&category=NAME&limit=N`).
- `GET /api/ai/state` and the brief of the alerts carry the lessons that apply now.
- MCP server: `lessons_apply`, `lessons_recurring`, `lessons_brief` and `lesson_propose`.
- Command line: `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NAME]`.

Everything is data, never instructions: a log line that somebody wrote can end up in the book.

## Before a push

Read the brief before pushing: it lists the lessons that apply (those of the repository first), the guards to run and what is red now in the repository.

## An example hook for an AI tool

Many AI tools can run a command when a session starts and add its output to the context. This one prints the brief before a push:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## The AI of the monitor

When the AI explanation of a failed build is on, its prompt includes the lesson of the category the log falls in. Other AI tools reach the same functions through the interface `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` is the one in use and `ExampleProvider` is the smallest possible one:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Writing lessons

Reading is always allowed. Writing a lesson needs three things: `lessons.allow_write` on (off by default), an administrator, and a confirmation: `POST /api/ai/lessons` with `{"lesson": {...}, "confirm": true}` (without `confirm` the answer is the draft). The MCP server only writes when it was started with `--allow-lessons` and the switch is on. Nothing is ever written to GitHub.

## Settings

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` and `lessons.recurring_from`, in the AI tab of the Settings. The panel **Lessons from the failures** is the **Lessons** tab (menu entry on the left, address `#lessons`).

## Close of a round

At the end of a batch of work, `python bin/monitor_cli.py lessons close` lists the repeated kinds of failure that still have no lesson of your own with its guard (`needs_guard` in `GET /api/ai/lessons`) and exits with a non-zero code while there is one. Write the guard, or say why it cannot exist yet, and run it again.
