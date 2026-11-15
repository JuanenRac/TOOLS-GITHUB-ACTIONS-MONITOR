# Expansion work in progress (branch notes, not part of the product)

This branch adds isolated modules under `monitor/src/github_actions_monitor/phase4/` and tests `monitor/tests/test_p4_*.py`. Nothing in the existing product imports them yet; no shared file was edited.
Delete this file when the work is integrated.

## What exists

| Target | Module | Tests (run alone: `py -3 -m unittest test_p4_x` from `monitor/tests`) |
|---|---|---|
| 2.1 read API v1 | `phase4/apiv1.py` (envelope, cursors, compact fields, versioning, gzip, bearer scope, CONTRACT, OpenAPI), `phase4/msgs.py` | `test_p4_apiv1.py` |
| 2.1 phone web app | `phase4/pwa.py` (manifest, service worker text, `?view=`/`?chrome=`) | `test_p4_pwa.py` (also covers `phase4.settings`) |
| 2.2 plugins | `phase4/plugins.py` (manifest, trust, Guard, registry), `phase4/official_plugins.py` (Discussions, Releases, Packages) | `test_p4_plugins.py` |
| 2.3 proposals | `phase4/proposals.py` (store, hash binding, policy, executor, audit chain) | `test_p4_proposals.py` |
| 2.4 assistant | `phase4/assistant.py` (redaction, context, providers, air-gap, read-only tools, drafts) | `test_p4_assistant.py` |
| 2.5 scale + app server side | `phase4/scale.py` (queues, tick metrics, Prometheus text, limits), `phase4/mobile.py` (screens, devices, push planner, deep links) | `test_p4_scale.py`, `test_p4_mobile.py` |

All settings live under one `expansion` section (see `phase4.DEFAULTS`); everything is off by default (`execute_enabled` false, `airgapped` true, `allow_third_party` false, `merge_allowed` false).

## Common changes to integrate when rebasing (exact)

1. **Settings schema / docs generator**: add the `expansion` section (`phase4.DEFAULTS`, `BOUNDS`) to the settings schema and regenerate the settings reference. Keys avoid the words password/token/secret/key/command; `assistant.key_env` is a variable NAME and must be allowed explicitly (it is read by `Assistant`, default empty).
2. **Server routes** (`app/actions_monitor.py`): route `/api/v1/*` through `apiv1.strip_prefix`, call `apiv1.requested_version`, `authorize`, `scope_accounts`, `paginate`, `project`, `maybe_compress`, and answer errors with `ApiError.envelope(lang)`; add `/manifest.webmanifest` and `/sw.js` from `pwa`; add `/api/v1/openapi.json` from `apiv1.openapi`. Proposals endpoints (`/api/actions/proposals...`) go through `proposals.ProposalStore`; the executor route exists only when `Executor` can be built (full edition and `execute_enabled`). Update `ROUTES`/role tables (`auth.required_role`) for each new path.
3. **Page** (`assets/static/actions_monitor.html`): add `pwa.page_head_links()` to `<head>`, read `?view=`/`?chrome=`, and a pull-to-refresh that repeats `pwa.VIEW_ENDPOINTS[view]`. Two icons are needed: `static/icon-192.png`, `static/icon-512.png`.
4. **Texts**: the human sentences of this package are in `phase4/msgs.py` and `official_plugins.TITLES` (eight languages each). When integrated, move them into the locale catalogues (`i18n/locales/*.json`, same keys) so the catalogue tests and the help tests see them, then delete `msgs.py`.
5. **Help and docs** (same commit as the server routes, per the help-sync tests): tab help, `cfg.h.*` for the `expansion` keys, docs x8 (API guide "read API v1" with the examples of `apiv1.CONTRACT`, "how to write an official sentinel" using `official_plugins.py` as the checklist, Lite/Complete/Full guide, assistant and air-gap page, limits page from `scale.DOCUMENTED_LIMITS`), `help_index.json`, QUICKSTART, README x8, `--help`.
6. **CHANGELOG**: separate "core" from "plugins" entries (the changelog should name plugin changes under their own heading).
7. **`/metrics`**: append `scale.render_metrics(metrics, queues)` to `outputs.metrics_text` output (same `ghamon_` prefix and exposition format) or pass it through the existing `extra` argument; add the metric names to the metrics docs.
8. **Sentinel context**: the official plugins expect `ctx.plugin_repos()` and `ctx.plugin_fetch(kind, repo)`; back them with the conditional-GET reader and its cache. Register `official_plugins.official_factory` with `PluginRegistry`.
9. **Importing `ai_alerts`**: `assistant.py` imports `integrations.ai_alerts` for the shared cleaner; keep the import lazy if import time of the assistant matters.
10. **Layout test** (`test_layout`) and any module list that enumerates the package: `phase4/` is a new package (no entry point needed).
11. **Test counts**: seven new test files with 183 tests; README x8 / glance / manifest counters must be regenerated once by the integrator.
12. **Mobile**: the Android app itself is not in this branch (see decisions). The server side is `mobile.py`; routes for device registration (`POST /api/v1/devices`, `DELETE /api/v1/devices/<id>`) and the FCM sender (a transport function) are to be wired in the server.

## Open decisions (not decided here)

- PENDIENTE four eyes: `proposals.four_eyes` defaults to true (the person who created a proposal cannot approve it; sentinels and the assistant create as `system:*`). Options: keep true (safe, a one-person install needs a second admin or `four_eyes=false`); default false for single-user installs.
- PENDIENTE role that may create proposals: now `maintainer` or `admin` (and `system:*`). Options: admin only; viewer allowed in the complete edition.
- PENDIENTE the native app: Android first as planned. Options: native Kotlin app (new repository), or ship only the installable PWA for 2.5 and postpone the store app. The server side for push (FCM) and deep links is ready; FCM needs a Google project and key that only the maintainer can create.
- PENDIENTE hard timeout for plugins: a plugin that hangs (not raises) in `tick` blocks its own thread only if run by `BaseSentinel.start`; the guard does not preempt. Options: run third-party plugins in a worker process (documented future road) or give each plugin tick a watchdog thread with a deadline.
- PENDIENTE high availability (shared storage) is optional in the plan and is not implemented.
- PENDIENTE packaged entry points (setuptools entry points) for plugins: not implemented; official plugins are discovered by `plugin.json` plus the closed factory.
- PENDIENTE where the proposals store lives: `FileBackend` writes `proposals.json` and `proposals_audit.jsonl` into a folder; integration should point it at the installation's data folder and, for the other storage backends, add a table to the `Storage` contract.
- PENDIENTE unifying the redaction: `assistant.redact_text` adds a second layer over the alert cleaner; the extra patterns could move into `ai_alerts` so every output benefits.

## Limits of what was verified

Only the new tests were run (deterministic: injected clock, fake transports, no sockets, no sleeps). The complete suite, the page tests and the generators were not run on this branch.
