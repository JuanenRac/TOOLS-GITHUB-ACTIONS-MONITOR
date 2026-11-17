<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# The log of actions

Complete only, on by default. Next to the audit of the accesses (logins, locks, refusals) the monitor keeps a log of **actions**: who changed what, when and on which account. A change of the settings, a silence or its removal, a change of users, passwords, notification preferences or credentials. It is one JSON line each in `logs/audit_actions.jsonl`, never rewritten. It also records what is confirmed: an action on GitHub (rerun, cancel, dispatch, merge), a run with `act`, saving or deleting the stored token, a change of the working mode, a group added by discovery, a lesson added, a report written now, the login of the account and the actions of the AI. The line says what was confirmed and the result, never the body of the request. Every POST route is either recorded or listed as exempt with its reason, and a test fails when a new route is neither.

## What a line says

`at`, `action` (a plain word such as `settings_change` or `alert_mute`), `user`, `role`, `account`, `target` (a short identifier: a setting name, an alert code), `result` (`ok`, `denied` or `error`) and, when it helps, `details`. **No value and no secret ever goes in**: a change of settings writes the names of the settings, not what they were set to; a key whose name looks like a secret (token, password, key, cookie, authorization, session...) is dropped; every text is cleaned like the notes for AIs and cut to 200 characters.

## The chain

Each line carries `prev` (the hash of the line before it) and `hash` (the hash of itself and `prev`). A line that is changed, cut out or put in later breaks the chain, and `GET /api/audit-log` says where (`chain.broken_at`). Past `audit_log.max_mb` the old part is kept as `audit_actions.jsonl.1` and the chain goes on in the new file. The chain shows tampering; it cannot stop someone with access to the file from deleting all of it, so keep a copy where it matters. With several accounts each account keeps its own file in its folder (`accounts/<id>/audit_actions.jsonl`) and the API only answers the lines of the account that is asked; the lines written before this change stay in the old shared file. The check covers the rotated file too and the link between the two (`segments`, `segment` when a line is broken); `complete: false` means the chain does not begin at its first link because a rotated file was replaced by a later rotation or deleted. Several processes can write the same file: each line is chained to the last line that is really in it, under a lock. The chain has no secret key: whoever can write the file can cut its most recent lines or rewrite it with new hashes, so copy it somewhere else if it must be proof. With `audit_log.keep_generations` (5 by default, 1 to 20) the old parts are kept as `.1`, `.2` and so on: the newest is `.1`, what is older than that many files is deleted, and `GET /api/audit-log` checks the chain across all of them.

## Who reads it

An administrator (and the person at the computer when there is no team mode). A maintainer only when `audit_log.maintainers_can_read` is on; nobody else. `GET /api/audit-log` answers the last 200 lines and the state of the chain. Lite has none of this. A viewer is refused at the door. Switching the log off writes its own last line (the change that did it). A line that cannot be written is counted: `write_failures` and `last_write_error_at` in the answer, and a degradation notice. Failed changes of one's own password are not written here (the audit of the accesses keeps them).

## Settings

Settings, Sentinel tab, block **Log of actions**: `audit_log.enabled` (on), `audit_log.max_mb` (10) and `audit_log.maintainers_can_read` (off). `audit_log.keep_generations` (5) is how many rotated files are kept. `audit_log.required` (off) refuses the actions that must be recorded (the confirmations of actions on GitHub, the mode, the silences, the credentials...) with a 503 while the log cannot be written; the settings stay open so that it can be put right.
