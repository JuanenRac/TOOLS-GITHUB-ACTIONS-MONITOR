<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# Package for the auditor

What an auditor needs to check the team mode, the network exposure and the handling of secrets of this tool: a checklist, the findings of earlier reviews with their fix and the test that keeps each one fixed, how to run the tests and what is known to be left.

## Security checklist of the team mode

- Team mode (`auth.enabled`) is off by default; turn it on only behind HTTPS or a trusted proxy (`listen.trusted_proxy`).
- With the team mode on and the network open, the monitor does not start before the first administrator exists.
- Until then only the computer itself is let in (the first administrator is created there).
- Tokens for scripts (`auth.allow_bearer`) are off by default; a session needs the CSRF token to write.
- The process of each account answers only to its supervisor (a key given at its start).
- No secret is written to the log or to the answers of the API; the settings file is saved under a lock.
- Every request that leaves the monitor (notifications, OpenTelemetry, runner exporters) obeys the same rule: no private address, no redirect to one.

## Findings, fixes and tests

| Finding | Fix | Test |
|---|---|---|
| With the team mode on and no user yet, every route was open to the network | Only this computer gets in until the first administrator exists, and the network mode does not start without one | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| The process of an account skipped the checks of the team mode | It asks for the key of its supervisor on every request | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| Saving the settings went on without the file lock after a time-out | The save is refused with a message when the lock stays taken for ten seconds | `test_184_audit_hardening.py::ConfigurationLock` |
| The command of the sentinel could be a shell with arguments | The command is a list whose first word is the full path of a program that is not a shell, without control characters | `test_184_audit_hardening.py::NotifyCommand` |
| Tokens for scripts (bearer) were on by default | Off by default; a real true turns them on | `test_184_audit_hardening.py::ScriptTokens` |
| The feed for the AIs was shared by all accounts, and refresh, acknowledgement and the cap of notices could overtake each other | One feed for each account; refresh, acknowledgement and status take one lock; the cap is reserved in one locked step | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| The pause of the hook of an AI tool was not reserved in one step; a runner exporter could redirect the monitor; calls to GitHub that never return piled up | The pause is kept with a lock; redirects are checked and limited; abandoned calls are counted and capped (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| A name that ends in a line feed passed the checks of ids, repositories and keys | Every check ends in the end of the text (`\Z`) | `test_184_audit_anchors.py` |
| The OpenTelemetry export did not obey the rule for outgoing requests; the proxy was not said to be a frontier of trust; the escaping of the page had no test | The export goes through the same guard (no private address, no redirect); the frontier is documented in the help; a test keeps every text of the API escaped | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Two monitors could listen on one port; openssl of Git for Windows was not found; failures swallowed on purpose left no trace of where they came from | The port is taken exclusively and a second monitor refuses to start; openssl is searched where Git for Windows keeps it; each swallowed failure writes a line with its kind and place | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| Runs without a duration (read through GraphQL) made the Sentinel fail on every cycle | A missing duration counts as zero | `test_186_unfinished_rows.py` |

## A harness and the reproductions for reviewers

`python tools/audit_harness.py --check` starts, in a temporary folder and with no GitHub (a fake `gh`), a supervisor with three accounts (`alpha`, `beta`, `default`) and four users (`admin`; `maintainer` of `alpha` only; `viewer` of `beta` only; `inactive`, switched off), asks the routes that decide the isolation of the accounts and prints one line for each answer (`ok` or `WRONG`); it exits with 0 when all are right. Without `--check` it prints the address and the users and waits. The reproductions of the independent review of 1.8.3 live in `tests/test_193_regressions.py`: each one failed on that version and passes now.

## How to run the tests

From the folder `monitor/`: `python -m unittest discover -s tests`. The tests need no network and no GitHub token. The browser tests run when Edge, Chrome or Chromium is installed (or with `MONITOR_BROWSER_TESTS=1`). The files named in the table are in `monitor/tests/`.

## Known limits

- The proxy of the environment (`network.use_proxy`, off by default) resolves names on its own: the check of the name happens before it. The strong guarantee has to come from the network (a firewall that refuses private addresses).
- Windows cannot make a file private with permissions alone: the secrets are encrypted with the key of the user where the system offers it.
- The tests do not prove anything about a real GitHub, a real proxy or a real mail server: they use local doubles.
