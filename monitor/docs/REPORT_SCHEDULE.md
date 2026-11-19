<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# Scheduled reports

Complete only, off by default. The monitor can write a report of the account on a schedule or when you ask: the score, what changed since the last report, the repositories that need a person and the open alerts, as a page of HTML and as Markdown. It is made from what the monitor already holds, never asks GitHub for anything and sends nothing anywhere: the files stay in the `data/reports/` folder.

## Switch it on

Settings, Sentinel tab, block **Scheduled reports**:

| Setting | Default | What it does |
|---|---|---|
| `report_schedule.enabled` | off | writes a report on the schedule |
| `report_schedule.cron` | `0 8 * * 1` | five fields (minute, hour, day of the month, month, day of the week) in the local time of this computer; numbers, lists, ranges and steps, no names; `0 8 * * 1` is every Monday at 8:00 |
| `report_schedule.formats` | both | `html`, `markdown` or `both` |
| `report_schedule.keep` | 12 | how many runs are kept; the older ones are removed |
| `report_schedule.top` | 10 | how many repositories and alerts each list shows, the worst first |

The first report waits for the first scheduled minute after you switch it on. A report is written once for each scheduled minute, even if the monitor was off for days (then it writes one, not a pile). A report that fails is noted in the health of the monitor and the next scheduled minute tries again. A schedule that names a day of the month is still owed after a stop of up to a month (one that names a month, up to a year), and the hour that happens twice when the clock goes back in autumn is not reported twice. A report is all its formats or nothing: if the second format cannot be written, the first file is removed.

## What is in a report

The score of the account (with its letter and trend; while it is calibrating or has too little data it says so and shows no number), what changed since the last report (the difference in points, new alerts, alerts that are gone), the repositories of the health view that need a person first, and the open alerts, the worst first. A silenced alert is not open. Every text that comes from the data is escaped: the page has no script and no outside address.

## PDF

There is no PDF of its own: open the HTML page and print it to PDF from the browser. The page has a print style for A4.

## Where to see and ask for them

- The **Scheduled reports** tab (menu group *Reports and learning*, address `#team-reports`) has: the list, a link to each file and the button **Write a report now** (an administrator, from this computer).
- `GET /api/report-files` lists them, `GET /api/report-files/file?name=...` opens one (only a file the service wrote for this account) and `POST /api/report-files/run` writes one now.
- The **summary of the next report** is a few lines that a person writes, edits and approves; they open the next report, once. In the same tab a card offers **Draft from the figures** (plain sentences made from the report, no model) and, with `ai.report_summary.enabled` on (off by default) and an AI configured, **Draft with the AI** (the figures go to the AI of the monitor cleaned of secrets, inside its daily budget). Nothing is written until **Save for the next report**; **Discard** removes it. `POST /api/report-files/summary` does the same with `action` = `draft`, `draft_ai`, `save` (text and origin) or `clear`, for an administrator at this computer; `GET /api/report-files` says whether a summary is waiting. The text is plain, cut to 1200 characters and cleaned of markup and secrets, and the report prints it escaped, with a line that says who wrote it.
- In the team mode anyone who can see the account can read its reports; writing one now is for an administrator at this computer. The Lite edition has none of this.

## Comparison with the period before

With `compare.include_in_report` on (off by default, and only while `compare.enabled` is on) the report also has a short section that sets this period against the one before, one line per figure. See [COMPARE.md](COMPARE.md).
