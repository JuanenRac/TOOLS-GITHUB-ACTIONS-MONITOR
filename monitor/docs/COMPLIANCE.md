<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# Compliance: what you can prove about your installation

Everything here is off by default and works only in the complete edition, except the two restrictions, which hold for every process of the monitor. None of it is a certification.

## Strict read-only mode

`security.read_only_strict` (off). With it on, nothing is written to GitHub whatever the edition or the other settings say: only reading commands of `gh` are started (anything not known to read is refused), no `git push`, no `act`, and no request to the API of GitHub other than GET or HEAD. It is enforced below every part, with an audit hook of Python that sees every program started. It can only be changed from the computer of the monitor and relaxing it needs a restart. The About window and `/api/about` (`restrictions`) say whether it is in force.

## Network policy

`security.egress_policy`: `default`, `github_only` or `none`; `security.egress_allow` adds hosts (`name`, `*.name`, an address) or `program:NAME`. With `github_only` the processes of the monitor reach only `api.github.com`, `uploads.github.com`, the host of `GH_HOST` (GitHub Enterprise) and what you allow; with `none`, this computer only, and `gh` is not started. Programs that open the network by themselves (`git` for network commands, `apprise`, `curl`, `docker`, secret stores' tools) are not started. A refused connection fails with an error that names the setting. `python bin/monitor_cli.py doctor` fails when a destination that is configured is outside the policy, and `doctor --egress` lists every destination. It is not a firewall: it does not govern what other programs of the computer do. The tools of the secret stores include `sops` and `bws`: when yours needs no network, add `program:sops` to `security.egress_allow`. A configuration file that is there but cannot be read or understood restricts instead of opening: strict read-only mode and `github_only` (or `none` when its text asks for that), until it is repaired and the monitor restarted; the doctor says so. `security.*` written in `actions_monitor_lite.json` holds for the lite edition too, on top of the main file.

## The compliance report

`python bin/monitor_cli.py compliance report` (add `--json`), `GET /api/compliance/report` (administrators) and a box at the end of the Security tab. Each line says whether it was **checked** (the monitor looked at the thing) or only **declared** (the configuration says so): version and support, edition, authentication and identity provider, network mode and TLS, the two restrictions and the destinations, retention and legal hold, the log of actions and its chain, copies and their encryption, encryption at rest (none), storage, plugins, deployment and profile. It holds no secret, no path and no name. `GET /api/compliance/state` gives the restrictions, the retention table and the state of the export. A restriction still in force is reported even if the file no longer asks for it, and what could not be looked at reads `unknown`.

## Retention and legal hold

Events, analytics and scores keep their settings (`retention.events_days`, `retention.analytics_days`, `retention.mode`). The other categories are kept for ever unless you give them days: `retention.audit_days` (whole rotated files of the log of actions), `retention.reports_days` (the newest report of each account stays), `retention.ai_log_days`, `retention.backups_days` (the newest copy stays). Every purge leaves a line in the log of actions. `retention.legal_hold` stops every removal: events, analytics, scores, reports, copies, the trimming of the feed and of the record of prompts, and the rotation and purge of the log. Proposals of the AI expire by themselves; paired devices stay until you remove them; postmortems, incidents and notes are not kept by this version.

## Signed checkpoints of the log of actions

`audit_checkpoints.enabled` (off) signs the chain (HMAC-SHA256) with a key of the installation: `config/audit_checkpoint.key`, or the file named in `MONITOR_AUDIT_KEY_FILE` to keep it apart. One checkpoint at the first line and then at least every hour and every 1000 lines; the anchor is signed too, and a cut of the end followed by a new line is written into the chain. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint`, and `audit purge --older-than-days N` (`--dry-run`), which removes whole rotated files and signs where the chain goes on. Whoever can read the key can sign: keep it away from whoever can write the log.

## Export of the log of actions

`audit_export.enabled` (off) with `audit_export.target` = `file` (`path`, rotated at `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 over TCP with TLS, `ca_file`) or `http` (`url`, POST of JSON lines, token from the variable named in `token_env`). Private addresses need `audit_export.allow_private_targets`. The log is the queue: what a destination did not take waits there; past `spool_mb` the doctor says `system.audit_export_lag`, and lines rotated away before they could be sent are counted as lost. `python bin/monitor_cli.py audit export` makes one pass now. Tested against receivers of this computer, not against a real syslog or SIEM product.

## Supported versions

Only the latest published version is supported: there is no long-term branch. The doctor (`compliance_support`) warns when it knows of a newer one.

## Evidence of the hardening

`[IMP]` = a test of this repository exercises the control; `[PAR]` = only part of it is exercised, and the line says what is missing. The list is `schemas/controls.json` and a test checks that this table and the tests it names agree.

| Control | State | Name |
|---|---|---|
| `sqlite_contention` | [IMP] | Several processes writing one database |
| `storage_migrations` | [IMP] | Migrations of the storage |
| `retention_by_category` | [IMP] | Retention by category and legal hold |
| `incoming_webhook` | [IMP] | Incoming webhook: signature, size, time |
| `metrics_labels` | [IMP] | Labels of /metrics |
| `timezone` | [IMP] | Time zones and change of the hour |
| `read_only_strict` | [IMP] | Strict read-only mode |
| `egress_policy` | [IMP] | Network policy |
| `audit_chain` | [IMP] | Chain and checkpoints of the log of actions |
| `service_and_volume` | [PAR] | Service on systemd, large database (network file systems are not tested) |

## Known limits

- Someone with a `viewer` account who sits at the computer of the monitor itself is treated as local and sees full paths.
- The incoming webhook checks the time window only for `workflow_run` and `workflow_job` deliveries.
- With `none` or `github_only`, a Python process the monitor starts applies the same policy only when it imports the monitor; a program you run yourself is outside it.
- Encryption at rest, a long-term branch and federation do not exist in this version.
