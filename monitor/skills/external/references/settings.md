<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Settings

Generated from the code: every key of the Settings page with its default. `secure` marks a switch that widens what leaves the computer or what may be done. Change them in the page, or with `POST /api/settings`.

| key | default | tab | label |
| --- | --- | --- | --- |
| `account.plan` | `"unknown"` | basic | Your GitHub plan |
| `act.allow_symlinks` (secure) | `false` | advanced | Allow clones that are links |
| `act.allowed` (secure) | `[]` | advanced | Workflows that can run (closed list) |
| `act.enabled` (secure) | `false` | advanced | Allow running workflows here with act |
| `act.timeout_seconds` | `900` | advanced | Time limit of a run |
| `ai.actions.allowed` | `-` | ai | Allowed actions |
| `ai.actions.enabled` (secure) | `-` | ai | Proposals on |
| `ai.actions.execute` (secure) | `-` | ai | Run with confirmation |
| `ai.actions.max_per_hour` | `-` | ai | Actions per hour |
| `ai.actions.ttl_seconds` | `-` | ai | Proposal lifetime |
| `ai.allowed_repos` | `-` | ai | Repositories it may see |
| `ai.answer_language` | `-` | ai | Language of the answers |
| `ai.api_key_env` | `-` | ai | Key variable |
| `ai.base_url` (secure) | `-` | ai | Endpoint of an OpenAI-compatible service |
| `ai.daily_limit` | `-` | ai | Calls per day |
| `ai.events` | `-` | ai | Events it may analyse |
| `ai.max_input_chars` | `-` | ai | Input size |
| `ai.max_output_chars` | `-` | ai | Answer size |
| `ai.model` | `-` | ai | Model |
| `ai.ollama_url` | `-` | ai | Ollama address |
| `ai.provider` (secure) | `"none"` | ai | AI service |
| `ai.skill` | `-` | ai | Give the AI its guide |
| `ai.skill_max_chars` | `-` | ai | Size of the guide in the prompt |
| `ai.timeout_seconds` | `-` | ai | Time limit |
| `ai_alerts.brief_max_bytes` | `2048` | ai | Size of the brief |
| `ai_alerts.cascade.enabled` | `true` | ai | Group alerts that fall together |
| `ai_alerts.client_hook.block_on_stop` (secure) | `false` | ai | Ask the AI to look before it ends a turn |
| `ai_alerts.client_hook.cooldown_minutes` | `20` | ai | Minutes between requests |
| `ai_alerts.client_hook.enabled` | `true` | ai | Gate script for AI tools |
| `ai_alerts.client_hook.max_chars` | `2400` | ai | Characters shown |
| `ai_alerts.client_hook.max_lines` | `12` | ai | Alert lines shown |
| `ai_alerts.client_hook.stale_hours` | `3` | ai | Warn when the brief is older than |
| `ai_alerts.diagnose.enabled` (secure) | `false` | ai | Read the failing step of a red run |
| `ai_alerts.diagnose.log_lines` | `10` | ai | Lines of log kept |
| `ai_alerts.diagnose.max_bytes` | `1500` | ai | Size of a diagnosis |
| `ai_alerts.diagnose.max_per_cycle` | `3` | ai | Diagnoses per cycle |
| `ai_alerts.enabled` | `false` | ai | Write the alert feed for AIs |
| `ai_alerts.folder` | `""` | ai | Folder of the feed |
| `ai_alerts.heartbeat.enabled` | `true` | ai | Note when an AI reads the feed |
| `ai_alerts.heartbeat.window_minutes` | `15` | ai | An AI counts as connected for |
| `ai_alerts.hook.enabled` (secure) | `false` | ai | Tell a script of mine about a new real alert |
| `ai_alerts.hook.max_per_hour` | `6` | ai | Hook calls per hour |
| `ai_alerts.hook.url` (secure) | `""` | ai | Local address of the hook |
| `ai_alerts.stream.enabled` (secure) | `false` | ai | Stream of alerts for AIs |
| `ai_alerts.stream.max_clients` | `3` | ai | Streams at once |
| `ai_alerts.stream.max_seconds` | `3600` | ai | Longest stream |
| `ai_notify.confirmed_provider` (secure) | `""` | ai | Confirm the provider (type its name) |
| `ai_notify.cost_per_call_cents` (secure) | `5` | ai | Cost of one notice (cents) |
| `ai_notify.enabled` (secure) | `false` | ai | Tell an external AI about new real alerts |
| `ai_notify.max_calls_per_hour` (secure) | `4` | ai | Notices per hour at most |
| `ai_notify.max_cost_per_hour_cents` (secure) | `50` | ai | Cost cap per hour (cents) |
| `ai_notify.timeout_seconds` (secure) | `30` | ai | Seconds to wait for the answer |
| `airgapped` (secure) | `false` | basic | Air-gapped installation |
| `alerts.mute_hours` | `-` | sentinel | Hours of a silence |
| `analytics.enabled` | `-` | analytics | Analytics on |
| `analytics.flaky` | `-` | analytics | Flaky detection |
| `analytics.jobs_per_cycle` | `-` | analytics | Jobs read per cycle |
| `analytics.keep_days` | `-` | analytics | History |
| `analytics.max_samples` | `-` | analytics | Most samples |
| `analytics.min_samples` | `-` | analytics | Least samples |
| `analytics.slow_factor` | `-` | analytics | Slower than usual |
| `analytics.steps` | `-` | analytics | Time per step |
| `audit_dir` | `-` | paths | Folder of audit files |
| `audit_log.enabled` (secure) | `-` | sentinel | Log of actions on |
| `audit_log.maintainers_can_read` (secure) | `-` | sentinel | Maintainers may read it |
| `audit_log.max_mb` | `-` | sentinel | Size before it is rotated |
| `auth.allow_bearer` (secure) | `false` | advanced | Tokens for scripts and apps |
| `auth.audit` (secure) | `true` | advanced | Audit of the accesses |
| `auth.enabled` (secure) | `false` | advanced | Team mode: users and roles |
| `auth.lockout_minutes` (secure) | `15` | advanced | Lock time |
| `auth.max_failed_logins` (secure) | `5` | advanced | Wrong passwords before a lock |
| `auth.min_length` (secure) | `10` | advanced | Shortest password |
| `auth.session_hours` (secure) | `12` | advanced | Session length |
| `cache.etag.enabled` | `true` | cache | Conditional reads on |
| `cache.etag.ttl_hours` | `24` | cache | Entry lifetime |
| `central.max_age_minutes` | `120` | quota | Minutes before the central panel is behind |
| `central.source` (secure) | `"off"` | quota | Central panel as a base line |
| `ci.automation_counts` | `false` | sentinel | Count automation workflows |
| `ci.count_fork_runs` | `false` | sentinel | Count runs of forks |
| `ci.extra_branches` | `[]` | sentinel | Maintenance branches to watch |
| `ci.failed_jobs.enabled` | `false` | sentinel | Show which jobs of a red run failed |
| `ci.failed_jobs.group_by` | `"auto"` | sentinel | Group jobs by |
| `ci.failed_jobs.max_per_cycle` | `4` | sentinel | Runs read per cycle |
| `ci.group.min` | `2` | sentinel | Workflows needed for a shared cause |
| `ci.group.reusable` | `false` | sentinel | Group reds by shared workflow |
| `ci.inactive_days` | `90` | sentinel | Days until a workflow is inactive |
| `ci.red_events` | `["push", "schedule", "workflow_dispatch", "merge_group"]` | sentinel | Events that can make a branch red |
| `ci.rerun_timing` | `false` | sentinel | Ask GitHub for the duration of re-runs |
| `cold_refresh_seconds` | `600` | polling | Refresh of cold repositories |
| `cold_runs_per_repo` | `5` | polling | Runs read per cold repository |
| `discover_limit` | `1000` | polling | Repositories listed |
| `discover_refresh_seconds` | `3600` | polling | Search for new repositories |
| `discovery.auto_frequency` | `false` | basic | Adjust the refresh to the real activity |
| `discovery.events` | `true` | basic | Tell me about new, vanished and archived repositories |
| `discovery.fork_checks_per_pass` | `30` | basic | Forks checked per listing |
| `discovery.fork_ci_days` | `90` | basic | A fork is maintained if its CI ran in the last |
| `discovery.fork_policy` | `"show"` | basic | Forks |
| `discovery.hide` | `[]` | basic | Leave out repositories of these kinds |
| `discovery.skip_archived` | `true` | basic | Leave out archived repositories |
| `discovery.suggest_groups` | `true` | basic | Suggest groups for unclassified repositories |
| `dispatch.required_ci` | `["ci.yml"]` | advanced | Workflows that must pass before a build is fired |
| `display.blink_red_tiles` | `true` | general | Blink red tiles |
| `display.timezone` | `"local"` | general | Time zone of the texts |
| `ecosystems` | `"all"` | general | Ecosystems watched |
| `ecosystems_file` | `-` | paths | Ecosystems file |
| `exclude` | `[]` | general | Repositories to skip |
| `extra_reader.any_folder` (secure) | `false` | quota | Accept the token file from any folder |
| `extra_reader.enabled` (secure) | `false` | quota | Read also with a second account |
| `extra_reader.file` (secure) | `""` | quota | File with the token of the second account |
| `finops.jobs_per_cycle` | `0` | advanced | Jobs read per cycle for their system |
| `fleet.group_by` | `"ecosystem"` | general | Group the fleet by |
| `fleet.labels` | `[]` | general | Labels by repository name |
| `fleet.page_size` | `50` | general | Repositories per page |
| `fleet.saved_filters` | `[]` | general | Saved filters |
| `fleet.sort` | `"risk"` | general | Order inside a group |
| `github_actions.allowed` (secure) | `["rerun_failed", "cancel"]` | advanced | Actions that can be planned |
| `github_actions.enabled` (secure) | `false` | advanced | Allow actions on GitHub |
| `github_actions.merge_method` (secure) | `"squash"` | advanced | Merge method |
| `github_app.app_id` (secure) | `""` | quota | App number (app_id) |
| `github_app.enabled` (secure) | `false` | quota | Read with a GitHub App |
| `github_app.installation_id` (secure) | `""` | quota | Installation number (optional) |
| `github_app.key_path` (secure) | `""` | quota | Path of the private key |
| `github_app.openssl_path` (secure) | `-` | quota | Path of the program openssl |
| `github_app.share_reads` (secure) | `false` | quota | Let tools take a read-only token of the App |
| `github_owner` | `""` | general | GitHub account |
| `github_token.enabled` (secure) | `false` | advanced | Keep a GitHub token in the monitor |
| `github_token.store` (secure) | `"auto"` | advanced | Where the token is kept |
| `hot_hours` | `3` | polling | A repository is hot for |
| `issues_refresh_seconds` | `180` | polling | Refresh of issues |
| `language` | `""` | general | Language of the tools |
| `lessons.allow_write` (secure) | `false` | ai | Allow writing lessons |
| `lessons.brief_max_bytes` | `3000` | ai | Size of ai/LESSONS.md |
| `lessons.enabled` | `true` | ai | Keep the book of failures |
| `lessons.max_entries` | `5000` | ai | Most lines in the book |
| `lessons.recurring_from` | `2` | ai | A kind of failure repeats from |
| `lessons.retention_days` | `180` | ai | Keep failures for |
| `lint.enabled` | `-` | lint | Linter on |
| `lint.ignore` | `-` | lint | Ignored findings |
| `lint.in_report` | `-` | lint | Warn in the report |
| `lint.refresh_seconds` | `-` | lint | Scan every |
| `lint.rules.injection.enabled` | `-` | lint | lint.rules.injection.enabled |
| `lint.rules.injection.severity` | `-` | lint | lint.rules.injection.severity |
| `lint.rules.permissions.enabled` | `-` | lint | lint.rules.permissions.enabled |
| `lint.rules.permissions.severity` | `-` | lint | lint.rules.permissions.severity |
| `lint.rules.pr_target.enabled` | `-` | lint | lint.rules.pr_target.enabled |
| `lint.rules.pr_target.severity` | `-` | lint | lint.rules.pr_target.severity |
| `lint.rules.secrets_in_clear.enabled` | `-` | lint | lint.rules.secrets_in_clear.enabled |
| `lint.rules.secrets_in_clear.severity` | `-` | lint | lint.rules.secrets_in_clear.severity |
| `lint.rules.unpinned_uses.enabled` | `-` | lint | lint.rules.unpinned_uses.enabled |
| `lint.rules.unpinned_uses.severity` | `-` | lint | lint.rules.unpinned_uses.severity |
| `listen.allowed_hosts` (secure) | `[]` | advanced | Names the page may be opened with |
| `listen.host` (secure) | `"127.0.0.1"` | advanced | Address to listen on |
| `listen.local_port` (secure) | `0` | advanced | Local-only port for this computer |
| `listen.max_failed_attempts` (secure) | `10` | advanced | Wrong access tokens allowed |
| `listen.network` (secure) | `false` | advanced | Listen beyond this computer |
| `listen.proxy_public_host` (secure) | `""` | advanced | Public name of the HTTPS proxy (without a port) |
| `listen.query_access` (secure) | `true` | advanced | Accept the access token in the address (deprecated) |
| `listen.secure_cookie` (secure) | `false` | advanced | Mark the access cookie as Secure |
| `listen.tls_cert_file` (secure) | `""` | advanced | Certificate file for HTTPS (PEM) |
| `listen.tls_key_file` (secure) | `""` | advanced | Private key file for HTTPS (PEM) |
| `listen.token_env` (secure) | `"MONITOR_ACCESS_TOKEN"` | advanced | Environment variable with the access token |
| `listen.trusted_proxies` (secure) | `[]` | advanced | Addresses of the proxy when it is not on this computer |
| `listen.trusted_proxy` (secure) | `false` | advanced | Trust the reverse proxy in front |
| `live.sse.enabled` (secure) | `false` | webhook | Stream of live events |
| `live.sse.max_clients` | `3` | webhook | Live streams at once |
| `live.sse.max_seconds` | `3600` | webhook | Longest live stream |
| `logs.failed_step.enabled` (secure) | `false` | ai | Show the log of the failed step |
| `logs.failed_step.lines` | `12` | ai | Lines of the failed step |
| `logs.failed_step.max_bytes` | `2000` | ai | Size of the failed step text |
| `max_workers` | `20` | polling | Parallel requests |
| `min_rate_remaining` | `800` | polling | Pause below this allowance |
| `mirror.enabled` (secure) | `false` | advanced | Keep a local copy of artifacts |
| `mirror.folder` | `""` | advanced | Folder of the copies |
| `mirror.keep_days` | `14` | advanced | Days to keep |
| `mirror.max_mb` | `500` | advanced | Size ceiling |
| `mirror.max_per_cycle` | `3` | advanced | Artifacts per cycle |
| `mode` | `"full"` | general | Mode |
| `modes.auto_low` | `-` | quota | Low mode by itself |
| `modes.auto_low_enter` | `-` | quota | Calls left to enter Low |
| `modes.auto_low_exit` | `-` | quota | Calls left to leave Low |
| `modes.low.cold_refresh_seconds` | `-` | quota | Low: seconds between readings of the rest |
| `modes.low.hot_hours` | `-` | quota | Low: hours a repository stays hot |
| `modes.low.refresh_seconds` | `-` | quota | Low: seconds between readings of hot repositories |
| `modes.low.runs_per_repo` | `-` | quota | Low: runs read per repository |
| `network.etag` | `true` | quota | Conditional reads (ETag) |
| `network.graphql_batch` | `20` | quota | Repositories per GraphQL batch |
| `network.graphql_checks` | `false` | quota | Read quiet repositories through GraphQL (own allowance) |
| `network.use_proxy` (secure) | `false` | notify | Use the proxy of the environment for notifications |
| `notify.allow_private_targets` (secure) | `-` | notify | Allow private destinations |
| `notify.channels.apprise.enabled` (secure) | `-` | notify | notify.channels.apprise.enabled |
| `notify.channels.apprise.urls_env` | `-` | notify | notify.channels.apprise.urls_env |
| `notify.channels.discord.enabled` | `-` | notify | notify.channels.discord.enabled |
| `notify.channels.discord.url_env` | `-` | notify | notify.channels.discord.url_env |
| `notify.channels.email.enabled` (secure) | `-` | notify | notify.channels.email.enabled |
| `notify.channels.email.host` (secure) | `-` | notify | notify.channels.email.host |
| `notify.channels.email.port` (secure) | `-` | notify | notify.channels.email.port |
| `notify.channels.email.sender` (secure) | `-` | notify | notify.channels.email.sender |
| `notify.channels.http_local.enabled` | `-` | notify | notify.channels.http_local.enabled |
| `notify.channels.http_local.url` | `-` | notify | notify.channels.http_local.url |
| `notify.channels.matrix.enabled` | `-` | notify | notify.channels.matrix.enabled |
| `notify.channels.matrix.homeserver` | `-` | notify | notify.channels.matrix.homeserver |
| `notify.channels.matrix.room` | `-` | notify | notify.channels.matrix.room |
| `notify.channels.matrix.token_env` | `-` | notify | notify.channels.matrix.token_env |
| `notify.channels.mqtt.enabled` | `-` | notify | notify.channels.mqtt.enabled |
| `notify.channels.mqtt.host` | `-` | notify | notify.channels.mqtt.host |
| `notify.channels.mqtt.port` | `-` | notify | notify.channels.mqtt.port |
| `notify.channels.mqtt.topic` | `-` | notify | notify.channels.mqtt.topic |
| `notify.channels.ntfy.enabled` (secure) | `-` | notify | notify.channels.ntfy.enabled |
| `notify.channels.ntfy.server` (secure) | `-` | notify | notify.channels.ntfy.server |
| `notify.channels.slack.enabled` | `-` | notify | notify.channels.slack.enabled |
| `notify.channels.slack.url_env` | `-` | notify | notify.channels.slack.url_env |
| `notify.channels.teams.enabled` (secure) | `-` | notify | notify.channels.teams.enabled |
| `notify.channels.telegram.chat_id` | `-` | notify | notify.channels.telegram.chat_id |
| `notify.channels.telegram.enabled` | `-` | notify | notify.channels.telegram.enabled |
| `notify.channels.telegram.token_env` | `-` | notify | notify.channels.telegram.token_env |
| `notify.digest.max_items` | `-` | notify | Alerts kept for a digest |
| `notify.enabled` (secure) | `-` | notify | Notifications on |
| `notify.events` | `-` | notify | Events that notify |
| `notify.max_per_hour` | `-` | notify | Messages per hour |
| `notify.users.enabled` (secure) | `-` | notify | Notifications for each user |
| `notify.users.max_per_hour` | `-` | notify | Messages per user per hour |
| `open_browser` | `true` | basic | Open the browser at start |
| `organizations.discover` | `false` | advanced | List the organisations of the login |
| `otlp.enabled` (secure) | `false` | advanced | Export OpenTelemetry (OTLP) |
| `otlp.endpoint` (secure) | `""` | advanced | OTLP collector address |
| `otlp.interval_seconds` | `60` | advanced | Seconds between exports |
| `outputs.dashboard.enabled` (secure) | `-` | outputs | Document for the status dashboard |
| `outputs.json.enabled` (secure) | `-` | outputs | Grafana JSON source |
| `outputs.prometheus.enabled` (secure) | `-` | outputs | Prometheus: /metrics |
| `outputs.prometheus.per_repo` | `-` | outputs | Prometheus: series per repository |
| `pagination.collab_pages` | `3` | polling | Pages of issues and pull requests per repository |
| `pagination.job_pages` | `2` | polling | Pages of jobs per run |
| `pagination.workflow_pages` | `3` | polling | Pages of workflows per repository |
| `ports.complete` | `8765` | general | Port of the complete edition |
| `ports.lite` | `8766` | general | Port of the lite edition |
| `profiles_file` | `-` | paths | Batch profiles file |
| `quota.alert_percent` | `90` | basic | Alert at this share of the included minutes |
| `quota.billing_api` (secure) | `false` | basic | Read the real usage from the billing report of GitHub |
| `quota.default_runner` | `"linux"` | basic | System assumed for the minute estimate |
| `quota.warn_percent` | `75` | basic | Warn at this share of the included minutes |
| `readpool.prefer.discovery` | `-` | quota | readpool.prefer.discovery |
| `readpool.prefer.history` | `-` | quota | readpool.prefer.history |
| `readpool.prefer.issues` | `-` | quota | readpool.prefer.issues |
| `readpool.prefer.other` | `-` | quota | readpool.prefer.other |
| `readpool.prefer.runs` | `-` | quota | readpool.prefer.runs |
| `readpool.prefer.security` | `-` | quota | readpool.prefer.security |
| `readpool.reserve.app` | `-` | quota | readpool.reserve.app |
| `readpool.reserve.extra` | `-` | quota | readpool.reserve.extra |
| `readpool.reserve.user` | `-` | quota | readpool.reserve.user |
| `refresh_seconds` | `45` | polling | Refresh of hot repositories |
| `report_history_days` | `30` | general | Days of report history kept |
| `report_schedule.cron` | `-` | sentinel | Schedule (cron) |
| `report_schedule.enabled` | `-` | sentinel | Reports on |
| `report_schedule.formats` | `-` | sentinel | Formats |
| `report_schedule.keep` | `-` | sentinel | Reports kept |
| `report_schedule.top` | `-` | sentinel | Rows in each list |
| `reports.max_calls_per_cycle` | `4` | sentinel | Most calls of the optional reports in a cycle |
| `reports.queue.enabled` (secure) | `false` | sentinel | Report on the wait for a runner |
| `reports.release_view.enabled` | `false` | sentinel | Show which releases are ready or blocked |
| `reports.supply_chain.enabled` (secure) | `false` | sentinel | Report on the supply chain of releases |
| `reports.workflow_hygiene.enabled` (secure) | `false` | sentinel | Report on workflow files |
| `repos` | `"all"` | general | Repositories |
| `retention.analytics_days` | `-` | paths | Keep analytics history for |
| `retention.enabled` (secure) | `-` | paths | Purge old events and analytics |
| `retention.events_days` | `-` | paths | Keep events for |
| `retention.events_max_kb` | `-` | paths | Largest size of the feed file |
| `retention.interval_hours` | `-` | paths | Purge every |
| `retention.mode` (secure) | `-` | paths | What to do with old events |
| `retention.warn_events_mb` | `-` | paths | Warn when the events are bigger than |
| `runners.enabled` | `false` | advanced | Watch self-hosted runners |
| `runners.model.alert_level` | `"warning"` | advanced | Level of those alerts |
| `runners.model.alerts` | `true` | advanced | Alerts of the runner model |
| `runners.model.enabled` | `false` | advanced | Model the runners |
| `runners.model.jobs_per_cycle` | `10` | advanced | Runs whose jobs are read per cycle |
| `runners.model.large_labels` | `[]` | advanced | Labels of your larger runners |
| `runners.model.queue_warn_minutes` | `20` | advanced | Minutes a job may wait for a self-hosted runner |
| `runners.model.runaway_ignore_events` | `["pull_request", "pull_request_target"]` | advanced | Events that do not count as runaway |
| `runners.model.runaway_runs_per_hour` | `20` | advanced | Runs per hour of a workflow that fires itself |
| `runners.model.self_labels` | `[]` | advanced | Extra labels of self-hosted runners |
| `runners.model.thirdparty_labels` | `["blacksmith", "buildjet", "namespace-profile", "depot", "warpbuild", "ubicloud", "runs-on", "actuated", "cirrus-runners"]` | advanced | Labels of paid third-party runners |
| `runners.model.thirdparty_usd_per_minute` | `0.0` | advanced | Price of a third-party minute |
| `runners.scope` | `"owner"` | advanced | Where to look |
| `runs_per_repo` | `20` | polling | Runs read per hot repository |
| `sampling.api_budget_per_hour` | `0` | polling | Request budget per hour |
| `sampling.default_branch_probe` | `false` | polling | Second look at the default branch |
| `sampling.min_coverage_minutes` | `30` | polling | Low coverage below |
| `savings.feeds.enabled` (secure) | `false` | quota | Ask a free source first |
| `savings.feeds.max_age_minutes` | `240` | quota | Full read at least every (free sources) |
| `savings.feeds.method` | `"atom"` | quota | Which free source |
| `savings.webhook_first` | `false` | quota | Webhook first |
| `savings.webhook_full_minutes` | `360` | quota | Full read at least every |
| `savings.webhook_window_minutes` | `60` | quota | The webhook counts as alive for |
| `score.alert.drop_points` | `-` | sentinel | Drop that raises the alert |
| `score.alert.enabled` | `-` | sentinel | Alert on a drop |
| `score.alert.notify_external` (secure) | `-` | sentinel | Notify outside the panel |
| `score.calibrating_hours` | `-` | sentinel | Calibration time |
| `score.enabled` | `-` | sentinel | Score on |
| `score.grades.A` | `-` | sentinel | Least score for A |
| `score.grades.B` | `-` | sentinel | Least score for B |
| `score.grades.C` | `-` | sentinel | Least score for C |
| `score.grades.D` | `-` | sentinel | Least score for D |
| `score.min_coverage` | `-` | sentinel | Least coverage for a score |
| `score.min_runs` | `-` | sentinel | Least finished runs |
| `score.trend_flat` | `-` | sentinel | Flat trend below |
| `score.weights.collaboration` | `-` | sentinel | Weight: collaboration |
| `score.weights.recovery` | `-` | sentinel | Weight: recovery |
| `score.weights.reliability` | `-` | sentinel | Weight: reliability |
| `score.weights.security` | `-` | sentinel | Weight: security |
| `score.weights.speed` | `-` | sentinel | Weight: speed |
| `score.window_days` | `-` | sentinel | Score window |
| `sentinel.a2_full_sample_unknown` | `-` | sentinel | Unknown when sample is full |
| `sentinel.a2_resolve_batch_min` | `-` | sentinel | A2 lookups in one request from |
| `sentinel.a2_resolve_batch_pages` | `-` | sentinel | A2 pages per repository |
| `sentinel.a2_resolve_max_calls_per_tick` | `-` | sentinel | A2 lookups per cycle |
| `sentinel.a2_resolve_ttl_seconds` | `-` | sentinel | A2 answers kept |
| `sentinel.alerts_cold_seconds` | `-` | sentinel | Alerts of cold repositories |
| `sentinel.alerts_hot_seconds` | `-` | sentinel | Alerts of hot repositories |
| `sentinel.audit_files.reconciliation` | `-` | sentinel | Reconciliation files |
| `sentinel.audit_files.rounds` | `-` | sentinel | Rounds files |
| `sentinel.audit_files.rounds_extra` | `-` | sentinel | Extra rounds files |
| `sentinel.budget_per_hour` | `-` | sentinel | API calls per hour |
| `sentinel.candidate_days` | `-` | sentinel | Days of a release candidate |
| `sentinel.candidate_min_entries` | `-` | sentinel | Entries to be a candidate |
| `sentinel.ci_red_audit_copy` | `-` | paths | Copy ci_red.json to the audit folder |
| `sentinel.ci_red_file` | `-` | paths | File for ci_red.json |
| `sentinel.enabled` | `true` | sentinel | Sentinel on |
| `sentinel.hot_hours` | `-` | sentinel | Hot period |
| `sentinel.hygiene.community_fallback` | `-` | sentinel | Count the community profile and the .github repository |
| `sentinel.hygiene.ruleset_mode` | `-` | sentinel | Branch protection check |
| `sentinel.hygiene.ruleset_names` | `-` | sentinel | Ruleset names |
| `sentinel.hygiene.skip` | `-` | sentinel | Hygiene checks to leave out |
| `sentinel.hygiene_seconds` | `-` | sentinel | Hygiene checks |
| `sentinel.max_calls_per_tick` | `-` | sentinel | API calls per cycle |
| `sentinel.min_rate_remaining` | `-` | sentinel | Sentinel pauses below |
| `sentinel.minutes_budget` | `-` | sentinel | Ceiling per ecosystem |
| `sentinel.minutes_budget_period` | `-` | sentinel | Period |
| `sentinel.pending_sign_hours` | `-` | sentinel | Pending signature after |
| `sentinel.readiness.enabled` | `-` | readiness | Readiness on |
| `sentinel.readiness.health.weights.alert` | `-` | readiness | sentinel.readiness.health.weights.alert |
| `sentinel.readiness.health.weights.high_alert` | `-` | readiness | sentinel.readiness.health.weights.high_alert |
| `sentinel.readiness.health.weights.hygiene` | `-` | readiness | sentinel.readiness.health.weights.hygiene |
| `sentinel.readiness.health.weights.red` | `-` | readiness | sentinel.readiness.health.weights.red |
| `sentinel.readiness.health.weights.secret` | `-` | readiness | sentinel.readiness.health.weights.secret |
| `sentinel.readiness.health.weights.stale_pr` | `-` | readiness | sentinel.readiness.health.weights.stale_pr |
| `sentinel.readiness.health.weights.stuck` | `-` | readiness | sentinel.readiness.health.weights.stuck |
| `sentinel.readiness.health.weights.unsigned` | `-` | readiness | sentinel.readiness.health.weights.unsigned |
| `sentinel.readiness.min_coverage` | `-` | readiness | Least coverage for a score |
| `sentinel.readiness.pins.max_depth` | `-` | readiness | Search depth |
| `sentinel.readiness.pins.refresh_seconds` | `-` | readiness | Pins reading |
| `sentinel.readiness.pins.sources` | `-` | readiness | Pin sources |
| `sentinel.readiness.warn_below` | `-` | readiness | Warn below this score |
| `sentinel.refresh_seconds` | `-` | sentinel | Sentinel cycle |
| `sentinel.require_verified_signature` (secure) | `-` | sentinel | Verified signature |
| `sentinel.required_files` | `-` | sentinel | Required files |
| `sentinel.skip_candidate_prefixes` | `-` | sentinel | Prefixes without release |
| `sentinel.stale_pr_days` | `-` | sentinel | A PR is stale after |
| `sentinel.surface.budget_share` | `-` | surface | Share of the budget for A10 |
| `sentinel.surface.checks.artifacts.enabled` | `-` | surface | sentinel.surface.checks.artifacts.enabled |
| `sentinel.surface.checks.artifacts.max_mb` | `-` | surface | sentinel.surface.checks.artifacts.max_mb |
| `sentinel.surface.checks.artifacts.retention_days` | `-` | surface | sentinel.surface.checks.artifacts.retention_days |
| `sentinel.surface.checks.attestation.enabled` | `-` | surface | sentinel.surface.checks.attestation.enabled |
| `sentinel.surface.checks.attestation.max_per_tick` | `-` | surface | sentinel.surface.checks.attestation.max_per_tick |
| `sentinel.surface.checks.broad_permissions.enabled` | `-` | surface | sentinel.surface.checks.broad_permissions.enabled |
| `sentinel.surface.checks.coverage.enabled` | `-` | surface | sentinel.surface.checks.coverage.enabled |
| `sentinel.surface.checks.dead_schedule.days` | `-` | surface | sentinel.surface.checks.dead_schedule.days |
| `sentinel.surface.checks.dead_schedule.enabled` | `-` | surface | sentinel.surface.checks.dead_schedule.enabled |
| `sentinel.surface.checks.dependabot_priority.enabled` | `-` | surface | sentinel.surface.checks.dependabot_priority.enabled |
| `sentinel.surface.checks.drafts.days` | `-` | surface | sentinel.surface.checks.drafts.days |
| `sentinel.surface.checks.drafts.enabled` | `-` | surface | sentinel.surface.checks.drafts.enabled |
| `sentinel.surface.checks.issue_close.enabled` | `-` | surface | sentinel.surface.checks.issue_close.enabled |
| `sentinel.surface.checks.matrix_os.enabled` | `-` | surface | sentinel.surface.checks.matrix_os.enabled |
| `sentinel.surface.checks.matrix_os.max_per_tick` | `-` | surface | sentinel.surface.checks.matrix_os.max_per_tick |
| `sentinel.surface.checks.maturity.enabled` | `-` | surface | sentinel.surface.checks.maturity.enabled |
| `sentinel.surface.checks.merge_queue.enabled` | `-` | surface | sentinel.surface.checks.merge_queue.enabled |
| `sentinel.surface.checks.milestones.enabled` | `-` | surface | sentinel.surface.checks.milestones.enabled |
| `sentinel.surface.checks.packages.enabled` | `-` | surface | sentinel.surface.checks.packages.enabled |
| `sentinel.surface.checks.parity.enabled` | `-` | surface | sentinel.surface.checks.parity.enabled |
| `sentinel.surface.checks.pr_human.days` | `-` | surface | sentinel.surface.checks.pr_human.days |
| `sentinel.surface.checks.pr_human.enabled` | `-` | surface | sentinel.surface.checks.pr_human.enabled |
| `sentinel.surface.checks.pr_target.enabled` | `-` | surface | sentinel.surface.checks.pr_target.enabled |
| `sentinel.surface.checks.pr_workflow_touch.enabled` | `-` | surface | sentinel.surface.checks.pr_workflow_touch.enabled |
| `sentinel.surface.checks.release_assets.enabled` | `-` | surface | sentinel.surface.checks.release_assets.enabled |
| `sentinel.surface.checks.release_assets.recent_days` | `-` | surface | sentinel.surface.checks.release_assets.recent_days |
| `sentinel.surface.checks.required_checks.enabled` | `-` | surface | sentinel.surface.checks.required_checks.enabled |
| `sentinel.surface.checks.secret_resolved.enabled` | `-` | surface | sentinel.surface.checks.secret_resolved.enabled |
| `sentinel.surface.checks.security_aged.days` | `-` | surface | sentinel.surface.checks.security_aged.days |
| `sentinel.surface.checks.security_aged.enabled` | `-` | surface | sentinel.surface.checks.security_aged.enabled |
| `sentinel.surface.checks.stuck_concurrency.enabled` | `-` | surface | sentinel.surface.checks.stuck_concurrency.enabled |
| `sentinel.surface.checks.stuck_concurrency.minutes` | `-` | surface | sentinel.surface.checks.stuck_concurrency.minutes |
| `sentinel.surface.checks.tag_vs_version.enabled` | `-` | surface | sentinel.surface.checks.tag_vs_version.enabled |
| `sentinel.surface.checks.unpinned_uses.enabled` | `-` | surface | sentinel.surface.checks.unpinned_uses.enabled |
| `sentinel.surface.checks.workflows_disabled.enabled` | `-` | surface | sentinel.surface.checks.workflows_disabled.enabled |
| `sentinel.surface.enabled` | `-` | surface | Surface checks on |
| `sentinel.surface.local_seconds` | `-` | surface | Surface read of the clones |
| `sentinel.surface.max_repos_per_tick` | `-` | surface | Repositories per surface cycle |
| `sentinel.surface.min_rate_factor` | `-` | surface | Allowance factor to start A10 |
| `sentinel.surface.refresh_seconds` | `-` | surface | Surface read of GitHub |
| `sentinel.workers` | `-` | sentinel | Sentinel parallel requests |
| `sentinels.collab.enabled` | `-` | sentinel | Collab sentinel on |
| `sentinels.collab.max_repos_per_tick` | `-` | sentinel | Repositories per round |
| `sentinels.collab.min_rate_remaining` | `-` | sentinel | Collab allowance floor |
| `sentinels.collab.refresh_seconds` | `-` | sentinel | Collab cycle |
| `sentinels.collab.repos` | `-` | sentinel | Collab repositories |
| `sentinels.collab.rules.ignore_labels` | `-` | sentinel | Ignored labels |
| `sentinels.collab.rules.issue_critical_labels` | `-` | sentinel | Critical labels |
| `sentinels.collab.rules.issue_stale_days` | `-` | sentinel | Days without activity (issue) |
| `sentinels.collab.rules.pr_conflict_days` | `-` | sentinel | Days with conflicts |
| `sentinels.collab.rules.pr_draft_max_days` | `-` | sentinel | Days of a draft |
| `sentinels.collab.rules.pr_review_pending_days` | `-` | sentinel | Days waiting for review |
| `sentinels.collab.rules.watch_external_comments` | `-` | sentinel | Watch outsiders |
| `sentinels.collab.search_api` | `-` | sentinel | Read issues and pull requests with the Search API |
| `sentinels.security.enabled` | `-` | sentinel | Security sentinel on |
| `sentinels.security.max_repos_per_tick` | `-` | sentinel | Repositories per round |
| `sentinels.security.min_rate_remaining` | `-` | sentinel | Allowance kept free |
| `sentinels.security.refresh_seconds` | `-` | sentinel | Security cycle |
| `sentinels.security.repos` | `-` | sentinel | Repositories watched for security |
| `sentinels.security.signals.branch.enabled` | `-` | sentinel | Branch protection |
| `sentinels.security.signals.code_scanning.enabled` | `-` | sentinel | Code scanning alerts |
| `sentinels.security.signals.code_scanning.min_severity` | `-` | sentinel | Code scanning: least severity |
| `sentinels.security.signals.codeowners.enabled` | `-` | sentinel | CODEOWNERS file |
| `sentinels.security.signals.dependabot.enabled` | `-` | sentinel | Dependabot alerts |
| `sentinels.security.signals.dependabot.min_severity` | `-` | sentinel | Dependabot: least severity |
| `sentinels.security.signals.secret.enabled` | `-` | sentinel | Secret scanning alerts |
| `sentinels.security.signals.workflow.enabled` | `-` | sentinel | Workflow permissions |
| `session_guard` (secure) | `true` | basic | One-use token for changes |
| `show_unclassified` | `true` | general | Show unclassified repositories |
| `signed_dir` | `-` | paths | Folder of signature records |
| `sound.cooldown_seconds` | `30` | general | Seconds between two sounds |
| `sound.enabled` | `true` | general | Sound alerts |
| `sound.on_connection_lost` | `true` | general | Sound when the connection drops |
| `sound.on_new_red` | `true` | general | Sound for a new red |
| `sound.server_beep` (secure) | `false` | general | Beep of this computer (page closed) |
| `sound.volume` | `40` | general | Volume of the page |
| `stuck_minutes` | `120` | polling | A build is stuck after |
| `targets_file` | `-` | paths | Build targets file |
| `tools_dir` | `-` | paths | Folder of the local signing tools |
| `tui.refresh_seconds` | `-` | console | Refresh |
| `tui.theme` | `-` | console | Colours |
| `ui.alerts_sort` | `"server"` | general | Order of the alerts |
| `ui.now_sort` | `"ecosystem"` | general | Order of the runs happening now |
| `ui.orientation` | `"auto"` | general | Orientation of the page |
| `ui.rotate_seconds` | `0` | general | Seconds between tabs of a screen |
| `ui.screen1_orientation` | `"auto"` | general | Orientation of screen 1 |
| `ui.screen1_tabs` | `""` | general | Tabs of screen 1 |
| `ui.screen2_orientation` | `"auto"` | general | Orientation of screen 2 |
| `ui.screen2_tabs` | `""` | general | Tabs of screen 2 |
| `ui.screen3_orientation` | `"auto"` | general | Orientation of screen 3 |
| `ui.screen3_tabs` | `""` | general | Tabs of screen 3 |
| `updates.check` | `true` | basic | Tell me when a newer version is published |
| `watchdog_max_abandoned` | `8` | polling | Most calls to GitHub left hanging |
| `watchdog_minutes` | `10` | polling | Restart a stuck refresh after |
| `webhook.enabled` (secure) | `false` | webhook | Receiver on |
| `webhook.live_events_keep` | `-` | webhook | Events kept |
| `webhook.max_per_minute` | `30` | webhook | Events accepted per repository |
| `webhook.record_events` | `-` | webhook | Keep events |
| `webhook.replay_seconds` | `3600` | webhook | Delivery ids remembered |
| `webhook.signing_state` | `-` | webhook | Shared secret |
| `workspace_root` | `-` | paths | Folder with your clones |
