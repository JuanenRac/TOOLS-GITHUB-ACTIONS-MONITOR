<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# External CI sources (read only)

A repository mirrored on GitHub may be built somewhere else. The monitor can read Buildbot, GitLab CI, Jenkins and Azure Pipelines and show their failures like those of Actions. It only reads (GET); it never starts, cancels or writes anything there. Complete and Full editions; off by default.

## Set up

Turn on `external_ci.enabled` and write one line per source in `external_ci.sources` (Settings > External CI). `repo` is the name under which the result is shown.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Red, fine or degraded

The last finished build of each builder, pipeline or job on its branch decides, as for Actions: pull or merge requests, cancelled, skipped and unknown states never decide. A service that does not answer, answers something else or misses a builder is **degraded**, never red; the failures seen before stay, marked stale. Failures raise `ci.external.red` (level `external_ci.alert.level`) and are counted, notified and silenced like a red of Actions; `ci.external.degraded` is information. Silencing them never silences a security alert. Each source is read at most once every `external_ci.refresh_seconds` (300 or more), and less often after `external_ci.breaker.failures` failures.

## Safety

The address is checked when connecting: this computer, private networks and cloud metadata are refused unless `external_ci.allow_private_targets` is on. No redirect is followed; links in answers are never followed. Answers are limited by `external_ci.max_bytes` and `external_ci.timeout_s`. A credential is never written in the configuration: `token_env` holds only the NAME of an environment variable (GitLab: access token with read scope; Jenkins: `user:token`; Azure: personal access token with Build read), and it is not sent without TLS to a public address. Requests do not use the GitHub allowance. Offline mode (`airgapped`) reads nothing; `doctor --egress` lists the hosts.

## Logs of a failed build

Off by default (`external_ci.logs.enabled`). Only the end of the log is asked for, limited by `external_ci.logs.max_kb` and `external_ci.logs.tail_lines`, without terminal sequences or control characters, redacted, kept in memory for `external_ci.logs.keep_hours`. It is untrusted text and is never given to an AI as an instruction. Redaction cannot recognise every secret.

## Test, status, command line

Settings > External CI has **Test connection**: one read, nothing saved (`POST /api/external-ci/probe`). The CI tab of the Sentinel area shows each source; `GET /api/external-ci/status` gives the same and `GET /api/external-ci/log` one log. Command line: `external-ci list`, `external-ci status` (exit code 1 when a source is red or degraded) and `external-ci probe --source "LINE"`.

## Not yet verified

All four adapters have been tested against fake servers only (`tools/extci_fake_servers.py`). Jenkins and Azure Pipelines carry the label **experimental** (`external_ci.experimental`) and need `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. To write another adapter: a function `(reader, source, cfg) -> (runs, missing)` in `integrations/external_ci/adapters.py`, reading only through `reader`.
