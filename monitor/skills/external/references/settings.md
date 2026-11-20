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
| `ai.airgap_hosts` (secure) | `-` | ai | Private addresses allowed |
| `ai.airgapped` (secure) | `-` | ai | Air-gapped mode of the AI |
| `ai.allow_private_targets` (secure) | `-` | ai | Allow an AI provider on a private address |
| `ai.allowed_repos` | `-` | ai | Repositories it may see |
| `ai.answer_language` | `-` | ai | Language of the answers |
| `ai.api_key_env` | `-` | ai | Key variable |
| `ai.assistant.enabled` (secure) | `-` | ai | Assistant panel |
| `ai.assistant.max_context` | `-` | ai | Context sent per question |
| `ai.assistant.max_tool_calls` | `-` | ai | Tool calls per question |
| `ai.assistant.tools` (secure) | `-` | ai | Tools it may use |
| `ai.base_url` (secure) | `-` | ai | Endpoint of an OpenAI-compatible service |
| `ai.catalog.enabled` (secure) | `-` | ai | Check the model against the provider's list |
| `ai.catalog.fit_context` | `-` | ai | Fit the input to the context window |
| `ai.catalog.max_requests_per_day` | `-` | ai | Requests for the list per day |
| `ai.catalog.ttl_minutes` | `-` | ai | Life of the list of models |
| `ai.cost_limit_daily` | `-` | ai | Estimated cost per day (all models) |
| `ai.daily_limit` | `-` | ai | Calls per day |
| `ai.events` | `-` | ai | Events it may analyse |
| `ai.fallback` (secure) | `-` | ai | Models to try when the main one fails |
| `ai.fallback_after_seconds` | `-` | ai | Give up the main model after |
| `ai.fallback_cloud_allowed` (secure) | `-` | ai | Providers on the internet allowed as a fallback |
| `ai.fallback_max_attempts` | `-` | ai | Most models tried per question |
| `ai.max_input_chars` | `-` | ai | Input size |
| `ai.max_output_chars` | `-` | ai | Answer size |
| `ai.model` | `-` | ai | Model |
| `ai.model_cost_limit_daily` | `-` | ai | Estimated cost per model per day |
| `ai.model_daily_limit` | `-` | ai | Calls per model per day |
| `ai.ollama_url` | `-` | ai | Ollama address |
| `ai.prompt_log.enabled` (secure) | `-` | ai | Local record of prompts |
| `ai.prompt_log.keep` | `-` | ai | Prompts kept |
| `ai.provider` (secure) | `"none"` | ai | AI service |
| `ai.redact.extra_patterns` (secure) | `-` | ai | Patterns to always hide |
| `ai.redact.extra_terms` (secure) | `-` | ai | Words to always hide |
| `ai.report_summary.enabled` | `-` | ai | AI draft for the summary of a report |
| `ai.similar.enabled` | `-` | ai | Similar alerts |
| `ai.similar.max` | `-` | ai | Most similar alerts |
| `ai.skill` | `-` | ai | Give the AI its guide |
| `ai.skill_max_chars` | `-` | ai | Size of the guide in the prompt |
| `ai.tasks.alert.max_input_chars` | `-` | ai | Input limit (0 = the general one) |
| `ai.tasks.alert.max_output_chars` | `-` | ai | Output limit (0 = the general one) |
| `ai.tasks.alert.model` | `-` | ai | Model (empty = the general one) |
| `ai.tasks.alert.provider` (secure) | `-` | ai | Provider (empty = the general one) |
| `ai.tasks.alert.timeout_seconds` | `-` | ai | Time limit (0 = the general one) |
| `ai.tasks.build.max_input_chars` | `-` | ai | Input limit (0 = the general one) |
| `ai.tasks.build.max_output_chars` | `-` | ai | Output limit (0 = the general one) |
| `ai.tasks.build.model` | `-` | ai | Model (empty = the general one) |
| `ai.tasks.build.provider` (secure) | `-` | ai | Provider (empty = the general one) |
| `ai.tasks.build.timeout_seconds` | `-` | ai | Time limit (0 = the general one) |
| `ai.tasks.codeql.max_input_chars` | `-` | ai | Input limit (0 = the general one) |
| `ai.tasks.codeql.max_output_chars` | `-` | ai | Output limit (0 = the general one) |
| `ai.tasks.codeql.model` | `-` | ai | Model (empty = the general one) |
| `ai.tasks.codeql.provider` (secure) | `-` | ai | Provider (empty = the general one) |
| `ai.tasks.codeql.timeout_seconds` | `-` | ai | Time limit (0 = the general one) |
| `ai.tasks.diagnose.max_input_chars` | `-` | ai | Input limit (0 = the general one) |
| `ai.tasks.diagnose.max_output_chars` | `-` | ai | Output limit (0 = the general one) |
| `ai.tasks.diagnose.model` | `-` | ai | Model (empty = the general one) |
| `ai.tasks.diagnose.provider` (secure) | `-` | ai | Provider (empty = the general one) |
| `ai.tasks.diagnose.timeout_seconds` | `-` | ai | Time limit (0 = the general one) |
| `ai.tasks.report.max_input_chars` | `-` | ai | Input limit (0 = the general one) |
| `ai.tasks.report.max_output_chars` | `-` | ai | Output limit (0 = the general one) |
| `ai.tasks.report.model` | `-` | ai | Model (empty = the general one) |
| `ai.tasks.report.provider` (secure) | `-` | ai | Provider (empty = the general one) |
| `ai.tasks.report.timeout_seconds` | `-` | ai | Time limit (0 = the general one) |
| `ai.timeout_seconds` | `-` | ai | Time limit |
| `ai.untrusted_text_max` | `-` | ai | Size of outside text |
| `ai_alerts.brief_max_bytes` | `2048` | ai | Size of the brief |
| `ai_alerts.briefs.access_log` | `false` | ai | Record of the briefs read |
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
| `alerts.digest.minutes` | `0` | sentinel | Minutes between summaries (0 = off) |
| `alerts.digest.threshold` | `10` | sentinel | Notifications per hour before summarising |
| `alerts.group.by_commit` | `false` | sentinel | Group new reds of the same commit |
| `alerts.group.min` | `3` | sentinel | Workflows needed to group |
| `alerts.mute_hours` | `-` | sentinel | Hours of a silence |
| `alerts.service.enabled` | `false` | sentinel | Treat short crons as services |
| `alerts.service.failures` | `3` | sentinel | Failures in a row before it alerts |
| `alerts.service.rate_percent` | `0` | sentinel | Or when this share of its last runs failed |
| `alerts.service.workflows` | `[]` | sentinel | More workflows of the service class |
| `alerts.silences` | `[]` | sentinel | Permanent silences |
| `alerts.silences_expire_days` | `0` | sentinel | Days after the review date when a silence expires |
| `analytics.enabled` | `-` | analytics | Analytics on |
| `analytics.flaky` | `-` | analytics | Flaky detection |
| `analytics.jobs_per_cycle` | `-` | analytics | Jobs read per cycle |
| `analytics.keep_days` | `-` | analytics | History |
| `analytics.max_samples` | `-` | analytics | Most samples |
| `analytics.min_samples` | `-` | analytics | Least samples |
| `analytics.slow_factor` | `-` | analytics | Slower than usual |
| `analytics.steps` | `-` | analytics | Time per step |
| `api.cursor_ttl_seconds` | `900` | advanced | Seconds a page cursor lives |
| `api.default_limit` | `50` | advanced | Items per page |
| `api.experimental_routes` | `false` | advanced | Routes that are not frozen in /api/v1/ |
| `api.gzip_min_bytes` | `1024` | advanced | Smallest answer to compress (bytes) |
| `api.max_limit` | `200` | advanced | Most items per page |
| `api.v1_enabled` | `"auto"` | advanced | Read API under /api/v1/ |
| `audit_dir` | `""` | paths | Folder of audit files |
| `audit_log.enabled` (secure) | `-` | sentinel | Log of actions on |
| `audit_log.keep_generations` (secure) | `-` | sentinel | Rotated files kept |
| `audit_log.maintainers_can_read` (secure) | `-` | sentinel | Maintainers may read it |
| `audit_log.max_mb` | `-` | sentinel | Size before it is rotated |
| `audit_log.required` (secure) | `-` | sentinel | No action without the log |
| `auth.allow_bearer` (secure) | `false` | advanced | Tokens for scripts and apps |
| `auth.audit` (secure) | `true` | advanced | Audit of the accesses |
| `auth.enabled` (secure) | `false` | advanced | Team mode: users and roles |
| `auth.lockout_minutes` (secure) | `15` | advanced | Lock time |
| `auth.max_failed_logins` (secure) | `5` | advanced | Wrong passwords before a lock |
| `auth.min_length` (secure) | `10` | advanced | Shortest password |
| `auth.session_hours` (secure) | `12` | advanced | Session length |
| `cache.etag.enabled` | `true` | cache | Conditional reads on |
| `cache.etag.revalidate_active` | `true` | cache | Read lists with running work in full |
| `cache.etag.skip_stateful` | `true` | cache | Always read live state in full |
| `cache.etag.ttl_hours` | `24` | cache | Entry lifetime |
| `cache.negative_ttl_s` | `300` | cache | Remember a refusal for |
| `central.max_age_minutes` | `120` | quota | Minutes before the central panel is behind |
| `central.source` (secure) | `"off"` | quota | Central panel as a base line |
| `chatops.allowed_channels` (secure) | `[]` | webhook | Allowed channels |
| `chatops.allowed_teams` (secure) | `[]` | webhook | Allowed teams or servers |
| `chatops.allowed_users` (secure) | `[]` | webhook | Allowed users |
| `chatops.allowed_words` (secure) | `["help", "status", "alerts", "red", "queue", "score"]` | webhook | Commands the chat may run |
| `chatops.discord.enabled` (secure) | `false` | webhook | Discord on |
| `chatops.discord.public_key_env` (secure) | `"MONITOR_DISCORD_PUBLIC_KEY"` | webhook | Environment variable with the Discord public key |
| `chatops.discord.state` | `-` | webhook | Discord public key |
| `chatops.enabled` (secure) | `false` | webhook | Chat commands (Slack and Discord) |
| `chatops.links` (secure) | `true` | webhook | Link to the repository |
| `chatops.max_age_seconds` | `300` | webhook | Oldest request accepted |
| `chatops.max_rows` | `8` | webhook | Rows per answer |
| `chatops.rate_per_channel_per_minute` | `20` | webhook | Commands per channel per minute |
| `chatops.rate_per_minute` | `60` | webhook | Commands per minute (whole chat) |
| `chatops.rate_per_user_per_minute` | `6` | webhook | Commands per user per minute |
| `chatops.show_repo_names` (secure) | `"all"` | webhook | Repository names in the chat |
| `chatops.slack.enabled` (secure) | `false` | webhook | Slack on |
| `chatops.slack.signing_secret_env` (secure) | `"MONITOR_SLACK_SIGNING_SECRET"` | webhook | Environment variable with the Slack signing secret |
| `chatops.slack.state` | `-` | webhook | Slack signing secret |
| `ci.automation_counts` | `false` | sentinel | Count automation workflows |
| `ci.copilot_alerts` | `false` | sentinel | Notice when Copilot workflows fail |
| `ci.count_fork_runs` | `false` | sentinel | Count runs of forks |
| `ci.dependabot_alerts` | `true` | sentinel | Alert when the Dependabot updates fail |
| `ci.disabled_apart` | `true` | sentinel | A workflow switched off by hand is not red |
| `ci.dormant_repos` | `true` | sentinel | Count dormant and inactive repositories apart |
| `ci.extra_branches` | `[]` | sentinel | Maintenance branches to watch |
| `ci.failed_jobs.enabled` | `false` | sentinel | Show which jobs of a red run failed |
| `ci.failed_jobs.group_by` | `"auto"` | sentinel | Group jobs by |
| `ci.failed_jobs.max_per_cycle` | `4` | sentinel | Runs read per cycle |
| `ci.fork_own_ci_days` | `90` | sentinel | Days of own CI that a fork needs |
| `ci.forks_need_own_ci` | `true` | sentinel | Judge only the forks that have a CI of their own |
| `ci.group.min` | `2` | sentinel | Workflows needed for a shared cause |
| `ci.group.reusable` | `false` | sentinel | Group reds by shared workflow |
| `ci.inactive_days` | `90` | sentinel | Days until a workflow is inactive |
| `ci.red_age_days` | `30` | sentinel | Days until a red ages |
| `ci.red_ages` | `true` | sentinel | A red nobody attends to ages |
| `ci.red_events` | `["push", "schedule", "workflow_dispatch", "merge_group", "workflow_run", "repository_dispatch"]` | sentinel | Events that can make a branch red |
| `ci.rerun_timing` | `false` | sentinel | Ask GitHub for the duration of re-runs |
| `ci.stuck.awaiting_stuck` | `true` | sentinel | A run waiting for approval can be stuck |
| `ci.stuck.ghost_days` | `7` | sentinel | Days in the queue until a run is a ghost |
| `ci.stuck.ghost_enabled` | `true` | sentinel | Tell apart runs queued for days |
| `ci.stuck.learned` | `false` | sentinel | Learn the limit of each workflow |
| `ci.stuck.margin` | `2.0` | sentinel | Margin over that duration |
| `ci.stuck.max_minutes` | `720` | sentinel | Largest learned limit |
| `ci.stuck.min_minutes` | `30` | sentinel | Smallest learned limit |
| `ci.stuck.min_samples` | `3` | sentinel | Finished runs needed to learn |
| `ci.stuck.no_runner_check` | `false` | sentinel | Name a label nobody has |
| `ci.stuck.percentile` | `95` | sentinel | Percentile of the durations |
| `ci.stuck.queue_minutes` | `0` | sentinel | Limit for a run waiting for a runner |
| `ci.stuck.runner_minutes` | `[]` | sentinel | Fixed limits per runner label |
| `ci.stuck.workflow_minutes` | `[]` | sentinel | Fixed limits per workflow |
| `cli.default_format` | `"text"` | general | Default format of the command line |
| `cli.prefer_v1` | `true` | advanced | The command line asks /api/v1/ first |
| `cli.watch.default_interval_seconds` | `5` | general | Usual interval of watch |
| `cli.watch.min_interval_seconds` | `2` | general | Fastest refresh of watch |
| `cold_refresh_seconds` | `600` | polling | Refresh of cold repositories |
| `cold_runs_per_repo` | `5` | polling | Runs read per cold repository |
| `compare.cache_seconds` | `60` | sentinel | Keep the answer (seconds) |
| `compare.default_days_filter` | `"all"` | sentinel | Days counted |
| `compare.default_window_days` | `7` | sentinel | Default period (days) |
| `compare.enabled` | `false` | sentinel | Compare periods |
| `compare.include_in_report` | `false` | sentinel | Add to the scheduled report |
| `compare.min_days_of_history` | `14` | sentinel | Least days watched |
| `compare.min_repo_runs` | `3` | sentinel | Least runs per repository |
| `compare.min_resolved` | `3` | sentinel | Least resolved alerts |
| `compare.min_runs_per_window` | `20` | sentinel | Least finished runs per period |
| `compare.min_snapshots` | `12` | sentinel | Least hourly snapshots |
| `compare.top_changes` | `10` | sentinel | Rows in the changes |
| `compare.workdays` | `["1", "2", "3", "4", "5"]` | sentinel | Workdays |
| `config_check.strict` | `false` | basic | Refuse to start with a bad configuration |
| `discover_limit` | `1000` | polling | Repositories listed |
| `discover_refresh_seconds` | `3600` | polling | Search for new repositories |
| `discovery.auto_frequency` | `false` | basic | Adjust the refresh to the real activity |
| `discovery.events` | `true` | basic | Tell me about new, vanished and archived repositories |
| `discovery.fork_checks_per_pass` | `30` | basic | Forks checked per listing |
| `discovery.fork_ci_days` | `90` | basic | A fork is maintained if its CI ran in the last |
| `discovery.fork_policy` | `"show"` | basic | Forks |
| `discovery.hide` | `[]` | basic | Leave out repositories of these kinds |
| `discovery.min_keep_pct` | `-` | basic | Smallest listing believed (%) |
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
| `fleet.show_all_active` | `true` | general | Every run that is going |
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
| `kiosk.enabled` | `false` | general | Kiosk profile |
| `kiosk.font_scale_percent` | `150` | general | Type size of the kiosk |
| `kiosk.high_contrast` | `false` | general | High contrast in the kiosk |
| `kiosk.rotate_seconds` | `30` | general | Seconds between tabs in the kiosk |
| `kiosk.rotate_views` | `false` | general | Turn through the tabs of a preset |
| `kiosk.safe_margin_percent` | `0` | general | Safe margin of the kiosk |
| `kiosk.scale_with_window` | `false` | general | Kiosk type grows with the window |
| `language` | `""` | general | Language of the tools |
| `lessons.allow_write` (secure) | `false` | ai | Allow writing lessons |
| `lessons.brief_max_bytes` | `3000` | ai | Size of ai/LESSONS.md |
| `lessons.enabled` | `true` | ai | Keep the book of failures |
| `lessons.max_entries` | `5000` | ai | Most lines in the book |
| `lessons.recurring_from` | `2` | ai | A kind of failure repeats from |
| `lessons.retention_days` | `180` | ai | Keep failures for |
| `lint.anonymous_public` (secure) | `-` | lint | Read public repositories without any credential |
| `lint.api.max_calls_per_tick` | `-` | lint | API calls per cycle for workflow files |
| `lint.api.max_files_per_repo` | `-` | lint | Workflow files read per repository |
| `lint.api.refresh_seconds` | `-` | lint | Read a repository again after |
| `lint.enabled` | `-` | lint | Linter on |
| `lint.ignore` | `-` | lint | Ignored findings |
| `lint.in_report` | `-` | lint | Warn in the report |
| `lint.maintenance.inactive` | `-` | lint | Also report actions without activity |
| `lint.maintenance.inactive_years` | `-` | lint | Years without activity |
| `lint.maintenance.max_calls_per_tick` | `-` | lint | Reads of actions per scan |
| `lint.maintenance.refresh_seconds` | `-` | lint | Ask about an action again after |
| `lint.own_owners` | `-` | lint | Accounts whose actions are your own |
| `lint.refresh_seconds` | `-` | lint | Scan every |
| `lint.rules.archived_action.enabled` | `-` | lint | lint.rules.archived_action.enabled |
| `lint.rules.injection.enabled` | `-` | lint | lint.rules.injection.enabled |
| `lint.rules.injection.severity` | `-` | lint | lint.rules.injection.severity |
| `lint.rules.no_timeout.enabled` | `-` | lint | lint.rules.no_timeout.enabled |
| `lint.rules.no_timeout.severity` | `-` | lint | lint.rules.no_timeout.severity |
| `lint.rules.own_action_main.enabled` | `-` | lint | lint.rules.own_action_main.enabled |
| `lint.rules.own_action_main.severity` | `-` | lint | lint.rules.own_action_main.severity |
| `lint.rules.permissions.enabled` | `-` | lint | lint.rules.permissions.enabled |
| `lint.rules.permissions.severity` | `-` | lint | lint.rules.permissions.severity |
| `lint.rules.permissions_top.enabled` | `-` | lint | lint.rules.permissions_top.enabled |
| `lint.rules.permissions_top.severity` | `-` | lint | lint.rules.permissions_top.severity |
| `lint.rules.pr_target.enabled` | `-` | lint | lint.rules.pr_target.enabled |
| `lint.rules.pr_target.severity` | `-` | lint | lint.rules.pr_target.severity |
| `lint.rules.secrets_in_clear.enabled` | `-` | lint | lint.rules.secrets_in_clear.enabled |
| `lint.rules.secrets_in_clear.severity` | `-` | lint | lint.rules.secrets_in_clear.severity |
| `lint.rules.secrets_inherit.enabled` | `-` | lint | lint.rules.secrets_inherit.enabled |
| `lint.rules.secrets_inherit.severity` | `-` | lint | lint.rules.secrets_inherit.severity |
| `lint.rules.unpinned_uses.enabled` | `-` | lint | lint.rules.unpinned_uses.enabled |
| `lint.rules.unpinned_uses.severity` | `-` | lint | lint.rules.unpinned_uses.severity |
| `lint.source` | `-` | lint | Where the workflow files are read |
| `lint.sparse.max_repos_per_tick` | `-` | lint | Sparse clones per cycle |
| `lint.sparse.refresh_seconds` | `-` | lint | Refresh a sparse clone after |
| `lint.unpinned_own` | `-` | lint | Own actions that are not pinned |
| `listen.allowed_hosts` (secure) | `[]` | advanced | Names the page may be opened with |
| `listen.host` (secure) | `"127.0.0.1"` | advanced | Address to listen on |
| `listen.local_port` (secure) | `0` | advanced | Local-only port for this computer |
| `listen.max_failed_attempts` (secure) | `10` | advanced | Wrong access tokens allowed |
| `listen.network` (secure) | `false` | advanced | Listen beyond this computer |
| `listen.proxy_public_host` (secure) | `""` | advanced | Public name of the HTTPS proxy (without a port) |
| `listen.query_access` (secure) | `false` | advanced | Accept the access token in the address (deprecated) |
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
| `logs.failed_step.max_per_minute` | `10` | ai | Lookups of a failed step per minute |
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
| `network.graphql_checks` | `true` | quota | Read quiet repositories through GraphQL (own allowance) |
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
| `ops.backup.compress_level` | `-` | paths | Compression level |
| `ops.backup.dir` | `-` | paths | Folder of the copies |
| `ops.backup.enabled` (secure) | `-` | paths | Make a backup on a schedule |
| `ops.backup.encrypt` (secure) | `-` | paths | Seal the copies with a key |
| `ops.backup.include_config` (secure) | `-` | paths | Include the settings (without secrets) |
| `ops.backup.interval_hours` | `-` | paths | Make a copy every |
| `ops.backup.keep` | `-` | paths | Copies to keep |
| `ops.backup.key_env` (secure) | `-` | paths | Variable that holds the key |
| `ops.doctor.backup_max_age_days` | `-` | paths | Warn when the last copy is older than |
| `ops.doctor.min_free_mb` | `-` | paths | Warn when the free disk is below |
| `ops.doctor.sqlite_check` | `-` | paths | Integrity check of SQLite |
| `ops.doctor.sqlite_timeout_s` | `-` | paths | Time limit of that check |
| `ops.doctor.strict_exit` | `-` | paths | Warnings make the doctor exit 3 |
| `ops.doctor.webhook_min_length` | `-` | paths | Shortest webhook secret accepted |
| `ops.purge.enabled` (secure) | `-` | paths | Allow "purge now" |
| `ops.purge.require_backup_hours` (secure) | `-` | paths | Require a good copy newer than |
| `organizations.discover` | `false` | advanced | List the organisations of the login |
| `otlp.enabled` (secure) | `false` | advanced | Export OpenTelemetry (OTLP) |
| `otlp.endpoint` (secure) | `""` | advanced | OTLP collector address |
| `otlp.interval_seconds` | `60` | advanced | Seconds between exports |
| `outputs.dashboard.enabled` (secure) | `-` | outputs | Document for the status dashboard |
| `outputs.json.enabled` (secure) | `-` | outputs | Grafana JSON source |
| `outputs.prometheus.enabled` (secure) | `-` | outputs | Prometheus: /metrics |
| `outputs.prometheus.per_repo` | `-` | outputs | Prometheus: series per repository |
| `pagination.collab_pages` | `3` | polling | Pages of issues and pull requests per repository |
| `pagination.cursor_pages` | `3` | polling | Pages followed by cursor (alerts) |
| `pagination.job_pages` | `2` | polling | Pages of jobs per run |
| `pagination.workflow_pages` | `3` | polling | Pages of workflows per repository |
| `ports.complete` | `8765` | general | Port of the complete edition |
| `ports.lite` | `8766` | general | Port of the lite edition |
| `profiles_file` | `-` | paths | Batch profiles file |
| `quota.alert_percent` | `90` | basic | Alert at this share of the included minutes |
| `quota.billing_api` (secure) | `false` | basic | Read the real usage from the billing report of GitHub |
| `quota.default_runner` | `"linux"` | basic | System assumed for the minute estimate |
| `quota.failover` | `false` | quota | When an allowance runs out, read with another source |
| `quota.failover_max_age_minutes` | `60` | quota | Oldest copy that may be shown |
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
| `report_export.json` | `false` | outputs | JSON marked |
| `report_export.name` | `"monitor-{tab}-{date}"` | outputs | Suggested file name |
| `report_export.paper` | `"a4"` | outputs | Paper of the PDF |
| `report_export.pdf` | `true` | outputs | PDF marked |
| `report_export.pdf_path` | `"auto"` | outputs | Way of making the PDF |
| `report_export.txt` | `true` | outputs | TXT marked |
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
| `runners.model.observed_reads_per_cycle` | `0` | advanced | Workflow files read to see what the self-hosted runners really run |
| `runners.model.queue_warn_minutes` | `20` | advanced | Minutes a job may wait for a self-hosted runner |
| `runners.model.runaway_ignore_events` | `["pull_request", "pull_request_target"]` | advanced | Events that do not count as runaway |
| `runners.model.runaway_runs_per_hour` | `20` | advanced | Runs per hour of a workflow that fires itself |
| `runners.model.self_labels` | `[]` | advanced | Extra labels of self-hosted runners |
| `runners.model.thirdparty_labels` | `["blacksmith", "buildjet", "namespace-profile", "depot", "warpbuild", "ubicloud", "runs-on", "actuated", "cirrus-runners", "codspeed"]` | advanced | Labels of paid third-party runners |
| `runners.model.thirdparty_usd_per_minute` | `0.0` | advanced | Price of a third-party minute |
| `runners.scope` | `"owner"` | advanced | Where to look |
| `runs_per_repo` | `20` | polling | Runs read per hot repository |
| `sampling.active_probe` | `false` | polling | Look at the runs still going |
| `sampling.api_budget_per_hour` | `0` | polling | Request budget per hour |
| `sampling.default_branch_probe` | `false` | polling | Second look at the default branch |
| `sampling.min_coverage_minutes` | `30` | polling | Low coverage below |
| `savings.feeds.enabled` (secure) | `false` | quota | Ask a free source first |
| `savings.feeds.max_age_minutes` | `240` | quota | Full read at least every (free sources) |
| `savings.feeds.method` | `"atom"` | quota | Which free source |
| `savings.webhook_first` | `false` | quota | Webhook first |
| `savings.webhook_full_minutes` | `360` | quota | Full read at least every |
| `savings.webhook_live_per_repo` | `false` | quota | Webhook alive for each repository |
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
| `score.source` | `-` | sentinel | Runs the score reads |
| `score.trend_flat` | `-` | sentinel | Flat trend below |
| `score.weights.collaboration` | `-` | sentinel | Weight: collaboration |
| `score.weights.recovery` | `-` | sentinel | Weight: recovery |
| `score.weights.reliability` | `-` | sentinel | Weight: reliability |
| `score.weights.security` | `-` | sentinel | Weight: security |
| `score.weights.speed` | `-` | sentinel | Weight: speed |
| `score.window_days` | `-` | sentinel | Score window |
| `screens.alert_hold_seconds` | `30` | general | Seconds on the screen of a new red |
| `screens.blink` | `true` | general | Blink failures |
| `screens.blink_calm_minutes` | `30` | general | Minutes until a failure stops blinking |
| `screens.burn_in_protection` | `true` | general | Protect against screen burn-in |
| `screens.default_density` | `"normal"` | general | Density of the wall screens |
| `screens.default_theme` | `"inherit"` | general | Theme of the wall screens |
| `screens.enabled` | `false` | general | Wall screens |
| `screens.group_map` | `true` | general | Group map on the overview screen |
| `screens.logo_corner` | `"top-right"` | general | Corner of the logo |
| `screens.logo_max_height` | `64` | general | Largest height of the logo |
| `screens.logo_max_width` | `160` | general | Largest width of the logo |
| `screens.logo_now` | `false` | general | Logo on the screen: Right now |
| `screens.logo_overview` | `true` | general | Logo on the screen: Overview |
| `screens.logo_sentinels` | `false` | general | Logo on the screen: Sentinels |
| `screens.menu` | `true` | general | Screens menu in the top bar |
| `screens.menu_max_windows` | `4` | general | Most windows of a multi-monitor set |
| `screens.menu_rotate_seconds` | `20` | general | Seconds per screen in the turning presets |
| `screens.menu_target` | `"new"` | general | Where the Screens menu opens a screen |
| `screens.menu_tv_scale` | `1.5` | general | Size of the TV preset |
| `screens.mode` | `"three"` | general | Wall screens mode |
| `screens.night_dim` | `false` | general | Dim at night |
| `screens.night_dim_from_hour` | `22` | general | Dim from (hour) |
| `screens.night_dim_to_hour` | `7` | general | Dim until (hour) |
| `screens.refresh_seconds` | `10` | general | Seconds between updates of a wall screen |
| `screens.rotate_every_seconds` | `20` | general | Seconds per screen when they rotate |
| `screens.rotate_seconds` | `0` | general | Seconds between wall screens |
| `screens.safe_margin_percent` | `0` | general | Safe margin of the screens |
| `screens.show_repo_names` (secure) | `"public"` | general | Repository names on wall screens |
| `screens.sound` | `false` | general | Sound on wall screens |
| `screens.theme_now` | `"inherit"` | general | Theme of the screen: Right now |
| `screens.theme_overview` | `"inherit"` | general | Theme of the screen: Overview |
| `screens.theme_sentinels` | `"inherit"` | general | Theme of the screen: Sentinels |
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
| `sentinel.bots_apart` | `-` | sentinel | Count bots apart from people |
| `sentinel.budget_per_hour` | `-` | sentinel | API calls per hour |
| `sentinel.candidate_days` | `-` | sentinel | Days of a release candidate |
| `sentinel.candidate_min_entries` | `-` | sentinel | Entries to be a candidate |
| `sentinel.ci_red_audit_copy` | `-` | paths | Copy ci_red.json to the audit folder |
| `sentinel.ci_red_file` | `-` | paths | File for ci_red.json |
| `sentinel.dependency_bots` | `-` | sentinel | Accounts that update dependencies |
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
| `sentinel.surface.checks.commit_state.enabled` | `-` | surface | sentinel.surface.checks.commit_state.enabled |
| `sentinel.surface.checks.commit_state.include_other_apps` | `-` | surface | Count the checks of other apps |
| `sentinel.surface.checks.commit_state.include_statuses` | `-` | surface | Count the commit statuses |
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
| `sentinel.surface.checks.release_assets.allow_empty` | `-` | surface | Allow releases without files |
| `sentinel.surface.checks.release_assets.enabled` | `-` | surface | sentinel.surface.checks.release_assets.enabled |
| `sentinel.surface.checks.release_assets.recent_days` | `-` | surface | sentinel.surface.checks.release_assets.recent_days |
| `sentinel.surface.checks.release_assets.require_sha256` | `-` | surface | Require a checksum file |
| `sentinel.surface.checks.release_assets.require_signature` | `-` | surface | Require a signature file |
| `sentinel.surface.checks.required_checks.enabled` | `-` | surface | sentinel.surface.checks.required_checks.enabled |
| `sentinel.surface.checks.secret_resolved.enabled` | `-` | surface | sentinel.surface.checks.secret_resolved.enabled |
| `sentinel.surface.checks.security_aged.days` | `-` | surface | sentinel.surface.checks.security_aged.days |
| `sentinel.surface.checks.security_aged.enabled` | `-` | surface | sentinel.surface.checks.security_aged.enabled |
| `sentinel.surface.checks.stuck_concurrency.enabled` | `-` | surface | sentinel.surface.checks.stuck_concurrency.enabled |
| `sentinel.surface.checks.stuck_concurrency.minutes` | `-` | surface | sentinel.surface.checks.stuck_concurrency.minutes |
| `sentinel.surface.checks.tag_vs_version.enabled` | `-` | surface | sentinel.surface.checks.tag_vs_version.enabled |
| `sentinel.surface.checks.tag_vs_version.prefixes` | `-` | surface | Prefixes of the tags |
| `sentinel.surface.checks.tag_vs_version.prerelease_ok` | `-` | surface | Betas of the same version are the same version |
| `sentinel.surface.checks.unpinned_uses.enabled` | `-` | surface | sentinel.surface.checks.unpinned_uses.enabled |
| `sentinel.surface.checks.workflows_disabled.enabled` | `-` | surface | sentinel.surface.checks.workflows_disabled.enabled |
| `sentinel.surface.enabled` | `-` | surface | Surface checks on |
| `sentinel.surface.local_seconds` | `-` | surface | Surface read of the clones |
| `sentinel.surface.max_repos_per_tick` | `-` | surface | Repositories per surface cycle |
| `sentinel.surface.min_rate_factor` | `-` | surface | Allowance factor to start A10 |
| `sentinel.surface.refresh_seconds` | `-` | surface | Surface read of GitHub |
| `sentinel.trend_green_pct` | `-` | sentinel | Line of green workflows |
| `sentinel.trend_health` | `-` | sentinel | Line of the health |
| `sentinel.trend_quota_pct` | `-` | sentinel | Line of the API quota used |
| `sentinel.trend_workflow_marks` | `-` | sentinel | Mark the days a workflow file changed |
| `sentinel.trend_workflow_marks_days` | `-` | sentinel | Days back to look for workflow changes |
| `sentinel.trend_workflow_marks_hours` | `-` | sentinel | Hours before a repository is asked again for workflow changes |
| `sentinel.trend_workflow_marks_per_tick` | `-` | sentinel | Repositories asked per round for workflow changes |
| `sentinel.workers` | `-` | sentinel | Sentinel parallel requests |
| `sentinels.collab.deadline_s` | `-` | sentinel | Time ceiling per round |
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
| `sentinels.delivery.changelog_paths` | `-` | sentinel | CHANGELOG files |
| `sentinels.delivery.deadline_s` | `-` | sentinel | Time ceiling per round |
| `sentinels.delivery.enabled` | `-` | sentinel | Delivery sentinel on |
| `sentinels.delivery.expected_assets` | `-` | sentinel | Expected release files |
| `sentinels.delivery.max_calls_per_tick` | `-` | sentinel | Calls per round |
| `sentinels.delivery.max_repos_per_tick` | `-` | sentinel | Repositories per round |
| `sentinels.delivery.min_rate_remaining` | `-` | sentinel | Allowance kept free |
| `sentinels.delivery.refresh_seconds` | `-` | sentinel | Delivery cycle |
| `sentinels.delivery.repos` | `-` | sentinel | Repositories watched for delivery |
| `sentinels.delivery.signals.assets_missing.enabled` | `-` | sentinel | Release without its files |
| `sentinels.delivery.signals.assets_missing.level` | `-` | sentinel | Release without its files: level |
| `sentinels.delivery.signals.ecosystem_drift.enabled` | `-` | sentinel | Behind a shared contract |
| `sentinels.delivery.signals.ecosystem_drift.level` | `-` | sentinel | Behind a shared contract: level |
| `sentinels.delivery.signals.release_without_notes.enabled` | `-` | sentinel | Release without notes |
| `sentinels.delivery.signals.release_without_notes.level` | `-` | sentinel | Release without notes: level |
| `sentinels.delivery.signals.tag_without_release.enabled` | `-` | sentinel | Tag without a release |
| `sentinels.delivery.signals.tag_without_release.level` | `-` | sentinel | Tag without a release: level |
| `sentinels.delivery.signals.unreleased_pending.enabled` | `-` | sentinel | Unreleased entries waiting |
| `sentinels.delivery.signals.unreleased_pending.level` | `-` | sentinel | Unreleased entries waiting: level |
| `sentinels.delivery.signals.version_mismatch.enabled` | `-` | sentinel | Versions that disagree |
| `sentinels.delivery.signals.version_mismatch.level` | `-` | sentinel | Versions that disagree: level |
| `sentinels.delivery.unreleased_days` | `-` | sentinel | Days before unreleased entries count |
| `sentinels.delivery.unreleased_min_entries` | `-` | sentinel | Least entries under Unreleased |
| `sentinels.delivery.version_files` | `-` | sentinel | Version files |
| `sentinels.security.deadline_s` | `-` | sentinel | Time ceiling per round |
| `sentinels.security.enabled` | `-` | sentinel | Security sentinel on |
| `sentinels.security.max_repos_per_tick` | `-` | sentinel | Repositories per round |
| `sentinels.security.min_rate_remaining` | `-` | sentinel | Allowance kept free |
| `sentinels.security.plan_na` | `-` | sentinel | Count what the plan lacks as N/A |
| `sentinels.security.refresh_seconds` | `-` | sentinel | Security cycle |
| `sentinels.security.repos` | `-` | sentinel | Repositories watched for security |
| `sentinels.security.signals.branch.enabled` | `-` | sentinel | Branch protection |
| `sentinels.security.signals.code_scanning.enabled` | `-` | sentinel | Code scanning alerts |
| `sentinels.security.signals.code_scanning.min_severity` | `-` | sentinel | Code scanning: least severity |
| `sentinels.security.signals.codeowners.enabled` | `-` | sentinel | CODEOWNERS file |
| `sentinels.security.signals.dependabot.enabled` | `-` | sentinel | Dependabot alerts |
| `sentinels.security.signals.dependabot.min_severity` | `-` | sentinel | Dependabot: least severity |
| `sentinels.security.signals.runs_deleted.check_window_days` | `-` | sentinel | Days a run is watched |
| `sentinels.security.signals.runs_deleted.enabled` | `-` | sentinel | Runs deleted after being seen |
| `sentinels.security.signals.runs_deleted.max_checks` | `-` | sentinel | Requests per repository |
| `sentinels.security.signals.secret.enabled` | `-` | sentinel | Secret scanning alerts |
| `sentinels.security.signals.workflow.enabled` | `-` | sentinel | Workflow permissions |
| `sentinels.supply.deadline_s` | `-` | sentinel | Time ceiling per round |
| `sentinels.supply.enabled` | `-` | sentinel | Supply chain sentinel on |
| `sentinels.supply.ignore` | `-` | sentinel | Workflow findings to ignore |
| `sentinels.supply.ignore_uses` | `-` | sentinel | Actions that cannot be judged |
| `sentinels.supply.incremental` | `-` | sentinel | Lint only what changed |
| `sentinels.supply.max_calls_per_tick` | `-` | sentinel | Calls per round |
| `sentinels.supply.max_files_per_repo` | `-` | sentinel | Workflow files per repository |
| `sentinels.supply.max_repos_per_tick` | `-` | sentinel | Repositories per round |
| `sentinels.supply.min_rate_remaining` | `-` | sentinel | Allowance kept free |
| `sentinels.supply.refresh_seconds` | `-` | sentinel | Supply chain cycle |
| `sentinels.supply.repos` | `-` | sentinel | Repositories watched for supply chain |
| `sentinels.supply.signals.mutable_ref.enabled` | `-` | sentinel | Actions on a moving branch |
| `sentinels.supply.signals.mutable_ref.level` | `-` | sentinel | Actions on a moving branch: level |
| `sentinels.supply.signals.permissions_missing.enabled` | `-` | sentinel | Workflow without permissions |
| `sentinels.supply.signals.permissions_missing.level` | `-` | sentinel | Workflow without permissions: level |
| `sentinels.supply.signals.permissions_wide.enabled` | `-` | sentinel | Workflow with write-all |
| `sentinels.supply.signals.permissions_wide.level` | `-` | sentinel | Workflow with write-all: level |
| `sentinels.supply.signals.pr_target_checkout.enabled` | `-` | sentinel | pull_request_target with checkout |
| `sentinels.supply.signals.pr_target_checkout.level` | `-` | sentinel | pull_request_target with checkout: level |
| `sentinels.supply.signals.unpinned.enabled` | `-` | sentinel | Actions not pinned to a commit |
| `sentinels.supply.signals.unpinned.level` | `-` | sentinel | Actions not pinned to a commit: level |
| `session_guard` (secure) | `true` | basic | One-use token for changes |
| `show_unclassified` | `true` | general | Show unclassified repositories |
| `signed_dir` | `""` | paths | Folder of signature records |
| `sound.cooldown_seconds` | `30` | general | Seconds between two sounds |
| `sound.enabled` | `true` | general | Sound alerts |
| `sound.on_connection_lost` | `true` | general | Sound when the connection drops |
| `sound.on_info` | `true` | general | Sound for a notice |
| `sound.on_lesson` | `true` | general | Sound for a new lesson |
| `sound.on_live_recovered` | `true` | general | Sound when the live view comes back |
| `sound.on_new_red` | `true` | general | Sound for a new red |
| `sound.on_report` | `true` | general | Sound for a new report |
| `sound.on_resolved` | `true` | general | Sound when it is solved |
| `sound.on_score_drop` | `true` | general | Sound when the score drops |
| `sound.on_sentinel` | `true` | general | Sound for a security or serious alert |
| `sound.on_stuck` | `true` | general | Sound for a stuck build or queue |
| `sound.on_warning` | `true` | general | Sound for a warning |
| `sound.quiet_enabled` | `false` | general | Quiet hours |
| `sound.quiet_from_hour` | `22` | general | Quiet from |
| `sound.quiet_to_hour` | `7` | general | Quiet until |
| `sound.server_beep` (secure) | `false` | general | Beep of this computer (page closed) |
| `sound.theme` | `"classic"` | general | Theme of the sounds |
| `sound.volume` | `40` | general | Volume of the page |
| `startup.resume_max_age_hours` | `12` | basic | Show the last picture after a restart (hours) |
| `stuck_minutes` | `120` | polling | A build is stuck after |
| `targets_file` | `-` | paths | Build targets file |
| `tools_dir` | `-` | paths | Folder of the local signing tools |
| `tui.refresh_seconds` | `-` | console | Refresh |
| `tui.theme` | `-` | console | Colours |
| `ui.about_org_logo` | `false` | general | Organization logo in About |
| `ui.alerts_sort` | `"server"` | general | Order of the alerts |
| `ui.now_sort` | `"ecosystem"` | general | Order of the runs happening now |
| `ui.orientation` | `"auto"` | general | Orientation of the page |
| `ui.remember_folds` | `true` | general | Remember folded sections |
| `ui.rotate_seconds` | `0` | general | Seconds between tabs of a screen |
| `ui.screen1_orientation` | `"auto"` | general | Orientation of screen 1 |
| `ui.screen1_tabs` | `""` | general | Tabs of screen 1 |
| `ui.screen2_orientation` | `"auto"` | general | Orientation of screen 2 |
| `ui.screen2_tabs` | `""` | general | Tabs of screen 2 |
| `ui.screen3_orientation` | `"auto"` | general | Orientation of screen 3 |
| `ui.screen3_tabs` | `""` | general | Tabs of screen 3 |
| `ui.theme` | `"auto"` | general | Colour theme |
| `updates.check` | `true` | basic | Tell me when a newer version is published |
| `updates.systemd_helper` | `false` | basic | Update from the page under a systemd user service |
| `upstream.enabled` | `false` | advanced | Follow the original repository of each fork |
| `upstream.forks_per_request` | `8` | advanced | Forks per request |
| `upstream.news_days` | `7` | advanced | Days a new release counts as news |
| `upstream.notify` | `false` | advanced | Tell me when the original is red or has a new release |
| `upstream.refresh_hours` | `12` | advanced | Hours between two readings of a fork |
| `upstream.repos` | `[]` | advanced | Forks to follow |
| `upstream.requests_per_hour` | `6` | advanced | Requests an hour |
| `watchdog_max_abandoned` | `8` | polling | Most calls to GitHub left hanging |
| `watchdog_minutes` | `10` | polling | Restart a stuck refresh after |
| `webhook.clock_skew_s` | `300` | webhook | Clock skew allowed |
| `webhook.enabled` (secure) | `false` | webhook | Receiver on |
| `webhook.live_events_keep` | `-` | webhook | Events kept |
| `webhook.max_bad_per_minute` | `120` | webhook | Requests with a bad signature per address |
| `webhook.max_per_minute` | `30` | webhook | Events accepted per repository |
| `webhook.max_verified_per_minute` | `120` | webhook | Requests with a good signature per address |
| `webhook.persist_deliveries` | `true` | webhook | Remember deliveries after a restart |
| `webhook.record_events` | `-` | webhook | Keep events |
| `webhook.reject_stale` | `false` | webhook | Refuse old events |
| `webhook.replay_seconds` | `3600` | webhook | Delivery ids remembered |
| `webhook.secret_env` (secure) | `"MONITOR_WEBHOOK_SECRET"` | webhook | Environment variable with the shared secret |
| `webhook.signing_state` | `-` | webhook | Shared secret |
| `workspace_root` | `""` | paths | Folder with your clones |
