<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SETTINGS_por.md)

# 設定タブ

設定タブ（サイドパネルの設定項目）では、`actions_monitor.json` の値をページ上から変更できるため、ファイルを手作業で編集する必要はありません。
このタブはページの 8 つの言語で書かれており、ほかの部分と同じ外観になっています。

<!-- settings:begin -->
## 変更できるもの

`settings_api.py` の一覧(スキーマ)にあるキーだけです。それぞれに型と範囲があり、変更にモニターの**再起動**が必要か(ループは設定を一度だけ読みます)、**すぐ反映**されるかをページが表示します。

このタブは、一般的なものから高度なものの順にサブタブへ分かれています:このブラウザー、基本、一般、更新と上限、センチネル、表面チェック(A10)、準備状況(A11)、フォルダーとファイル、出力、続いて連携。サブタブ内では設定が見出し付きのブロックにまとまり、ブロックの最初の項目がメインのスイッチです。オフの間、ブロックの残りは薄く表示され編集できません。各項目には単位(秒・分・時間・日・MB・回)、範囲、バッジ(再起動が必要/すぐ反映)、保守的な既定値で始まる安全オプションのバッジ、1 行のヘルプが表示されます。検索ボックスは全サブタブの設定を絞り込み、各サブタブは未保存の変更数を数え、保存と破棄のボタンは常に見え、最後に使ったサブタブはブラウザーが覚えます。タブはキーボード操作(矢印キー、Home、End)に対応します。

| タブ | ブロックと設定 |
|---|---|
| このブラウザー | ページの言語、テーマ(自動/ライト/ダーク)、「今」タブの高密度表示。ファイルではなくブラウザーに保存されます。 |
| 基本 | **起動**: `open_browser`<br>**アップデート**: `updates.check`<br>**ネットワークで待ち受け**: `airgapped`<br>**プランとクォータ**: `account.plan`, `quota.default_runner`, `quota.warn_percent`, `quota.alert_percent`, `quota.billing_api`<br>**セキュリティ**: `session_guard`<br>**検出**: `discovery.events`, `discovery.suggest_groups`, `discovery.auto_frequency`<br>**ライフサイクル**: `discovery.hide` |
| 全般 | **アカウント**: `github_owner`, `language`, `display.timezone`, `display.blink_red_tiles`<br>**サウンド**: `sound.enabled`, `sound.on_new_red`, `sound.on_connection_lost`, `sound.cooldown_seconds`, `sound.volume`, `sound.server_beep`<br>**対象範囲**: `mode`, `repos`, `ecosystems`, `show_unclassified`, `exclude`<br>**履歴**: `report_history_days` |
| 更新と上限 | **アクティブなリポジトリ**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**バックグラウンド処理**: `watchdog_minutes`, `issues_refresh_seconds`, `discover_refresh_seconds`, `discover_limit`, `max_workers`<br>**非アクティブなリポジトリ**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**API の割り当て**: `min_rate_remaining` |
| 読み取りとキャッシュ | **条件付き読み取り**: `cache.etag.enabled`, `cache.etag.ttl_hours` |
| クォータ | **モードと節約モード**: `modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit`, `modes.low.refresh_seconds`, `modes.low.cold_refresh_seconds`, `modes.low.runs_per_repo`, `modes.low.hot_hours`<br>**節約**: `network.etag`<br>**2 つ目のアカウント(読み取り)**: `extra_reader.enabled`, `extra_reader.file`, `extra_reader.any_folder`<br>**GitHub App(読み取り)**: `github_app.enabled`, `github_app.app_id`, `github_app.key_path`, `github_app.installation_id`<br>**中央パネル**: `central.source`, `central.max_age_minutes` |
| センチネル | **基本**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**AI向けアラート**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**API の予算**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**リリースと署名**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**赤の照会(A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**プルリクエスト**: `sentinel.stale_pr_days`<br>**必須ファイル**: `sentinel.required_files`<br>**Actions の分数**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**監査ファイル**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra`<br>**イシューとプルリクエスト**: `sentinels.collab.enabled`, `sentinels.collab.refresh_seconds`, `sentinels.collab.max_repos_per_tick`, `sentinels.collab.min_rate_remaining`, `sentinels.collab.repos`, `sentinels.collab.rules.issue_stale_days`, `sentinels.collab.rules.issue_critical_labels`, `sentinels.collab.rules.pr_review_pending_days`, `sentinels.collab.rules.pr_draft_max_days`, `sentinels.collab.rules.pr_conflict_days`, `sentinels.collab.rules.watch_external_comments`, `sentinels.collab.rules.ignore_labels`, `alerts.mute_hours` |
| 表面チェック(A10) | **基本**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**手動で無効化された workflow**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**実行されていないスケジュール**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**SHA で固定されていない uses:**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**広すぎる権限（write-all）**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**PR をチェックアウトする pull_request_target**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**concurrency の詰まり（同じ workflow の待機中の実行）**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**マトリクスの 1 つの OS だけで失敗**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**アーティファクトのコスト**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**赤または欠落している必須チェック**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**不完全な公開済みリリース**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**リリースタグとマニフェスト/CHANGELOG のバージョンの比較**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**放置された下書きとプレリリース**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**経過日数別の重大/高アラート（リポジトリ順位）**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**セキュリティの適用範囲（CodeQL / Dependabot）**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**シークレットスキャン: 未対応と解決済み**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**優先度別の Dependabot**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**クローズできそうな issue（提案のみ）**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**エコシステムごとの期限切れマイルストーン**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**古くなった人間による PR**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**workflow または CODEOWNERS を変更する PR（優先）**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**マージキュー: 承認済みで CI が成功**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**マニフェストの成熟度と根拠の比較**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**8 言語の README の整合性が崩れています**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**ビルドの証明**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| 準備状況(A11) | **基本**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**健全性の重み**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**固定バージョン**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| フォルダーとファイル | **ローカルフォルダー**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**データファイル**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| 他のツール向けの出力 | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**Grafana JSON**: `outputs.json.enabled`<br>**ステータスダッシュボード**: `outputs.dashboard.enabled` |
| センチネル用の外部 AI | **サービス**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit`<br>**上限**: `ai.max_input_chars`, `ai.max_output_chars`, `ai.timeout_seconds`<br>**対象範囲**: `ai.events`, `ai.allowed_repos`, `ai.answer_language`<br>**アクション**: `ai.actions.enabled`, `ai.actions.execute`, `ai.actions.allowed`, `ai.actions.max_per_hour`, `ai.actions.ttl_seconds`<br>**AI向けアラート**: `ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.hook.enabled`, `ai_alerts.hook.url`, `ai_alerts.hook.max_per_hour`, `ai_alerts.diagnose.enabled`, `ai_alerts.diagnose.max_per_cycle`, `ai_alerts.diagnose.log_lines`, `ai_alerts.diagnose.max_bytes`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.enabled`, `ai_alerts.stream.max_seconds`, `ai_alerts.stream.max_clients`, `ai_alerts.heartbeat.enabled`, `ai_alerts.heartbeat.window_minutes`, `ai_alerts.client_hook.enabled`, `ai_alerts.client_hook.block_on_stop`, `ai_alerts.client_hook.cooldown_minutes`, `ai_alerts.client_hook.stale_hours`, `ai_alerts.client_hook.max_lines`, `ai_alerts.client_hook.max_chars` |
| 受信 Webhook | **受信 Webhook**: `webhook.enabled`, `webhook.signing_state`, `webhook.record_events`, `webhook.live_events_keep`, `webhook.replay_seconds`, `webhook.max_per_minute` |
| 通知 | **基本**: `notify.enabled`, `notify.allow_private_targets`, `network.use_proxy`, `notify.events`, `notify.max_per_hour`<br>**Telegram**: `notify.channels.telegram.enabled`, `notify.channels.telegram.token_env`, `notify.channels.telegram.chat_id`<br>**Discord**: `notify.channels.discord.enabled`, `notify.channels.discord.url_env`<br>**Slack**: `notify.channels.slack.enabled`, `notify.channels.slack.url_env`<br>**Matrix**: `notify.channels.matrix.enabled`, `notify.channels.matrix.homeserver`, `notify.channels.matrix.room`, `notify.channels.matrix.token_env`<br>**MQTT(このコンピューター)**: `notify.channels.mqtt.enabled`, `notify.channels.mqtt.host`, `notify.channels.mqtt.port`, `notify.channels.mqtt.topic`<br>**HTTP(このコンピューター)**: `notify.channels.http_local.enabled`, `notify.channels.http_local.url` |
| 分析 | **基本**: `analytics.enabled`, `analytics.keep_days`<br>**サンプル**: `analytics.min_samples`, `analytics.max_samples`, `analytics.jobs_per_cycle`, `analytics.steps`<br>**シグナル**: `analytics.slow_factor`, `analytics.flaky` |
| ワークフロー Lint | **基本**: `lint.enabled`, `lint.refresh_seconds`, `lint.in_report`, `lint.ignore`<br>**uses: が完全なコミット SHA に固定されていない**: `lint.rules.unpinned_uses.enabled`, `lint.rules.unpinned_uses.severity`<br>**permissions ブロックが無い、または write-all**: `lint.rules.permissions.enabled`, `lint.rules.permissions.severity`<br>**ファイルに書かれたシークレットのように見える**: `lint.rules.secrets_in_clear.enabled`, `lint.rules.secrets_in_clear.severity`<br>**第三者のテキストが run: スクリプトに埋め込まれている**: `lint.rules.injection.enabled`, `lint.rules.injection.severity`<br>**pull_request_target が PR のコードをチェックアウトする**: `lint.rules.pr_target.enabled`, `lint.rules.pr_target.severity` |
| 詳細設定(任意) | **ネットワークで待ち受け**: `listen.network`, `listen.host`, `listen.token_env`, `listen.allowed_hosts`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.proxy_public_host`, `listen.max_failed_attempts`, `listen.query_access`, `listen.trusted_proxy`, `listen.local_port`<br>**独自のGitHubトークン**: `github_token.enabled`, `github_token.store`<br>**GitHubでの操作**: `github_actions.enabled`, `github_actions.allowed`, `github_actions.merge_method`<br>**ここでワークフローを実行 (act)**: `act.enabled`, `act.allowed`, `act.timeout_seconds`, `act.allow_symlinks`<br>**バッチビルド**: `dispatch.required_ci`<br>**アーティファクトのローカルコピー**: `mirror.enabled`, `mirror.folder`, `mirror.max_mb`, `mirror.keep_days`, `mirror.max_per_cycle`<br>**セルフホストランナー**: `runners.enabled`, `runners.scope`<br>**OpenTelemetry エクスポート**: `otlp.enabled`, `otlp.endpoint`, `otlp.interval_seconds`<br>**組織**: `organizations.discover`<br>**分の費用 (FinOps)**: `finops.jobs_per_cycle` |
| ターミナル表示 | **ターミナル**: `tui.theme`, `tui.refresh_seconds` |

各設定は 1 か所にだけ現れます。読み取り専用:`webhook.signing_state` は共有シークレットが設定済みかどうかだけを示し、シークレット自体は表示されません。

どのリポジトリを監視するか:エコシステムのサンプルカタログは、他のどのグループにも属さないリポジトリをすべて受け取るグループ `rest`(接頭辞 `*`、「Everything else」)で終わるため、既定では何も漏れません。自分のカタログで漏れるリポジトリがある場合は、ページのバナーがその数を表示します(「エコシステムのフィルターがアカウントの M 件中 N 件を隠しています」)。

外部 AI:`ai.provider` は `ollama`(このコンピューター)、`openai-compatible`(OpenAI 形式の任意のエンドポイント。Gemini の OpenAI 互換エンドポイントや OpenAI 自体にも使えます)、`anthropic`(Messages API。モデルは自分で選びます)、`copilot`(自分のログインで `gh copilot` を実行。プレミアムリクエストを消費)のいずれかです。キーは保存されず、環境変数の名前だけを設定します。AI_jpn.md を参照。

### 固定バージョンの取得元の例

固定バージョンは取得元を指定したときだけ読み取られます。リストが空なら何も読まず、ページがそう表示します。次はコメントアウトした例です:

```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```
<!-- settings:end -->

## ページから変更も閲覧もできないもの

トークン、シークレット、署名キー、Webhook のシークレット、センチネルが実行できるコマンド（`sentinel.notify_command`）、AI の API キー（設定できるのは環境変数の名前だけです）、ほかのツールのキーは、**スキーマに含まれていません**。そのためページはこれらを表示も書き込みもせず、いずれかを指定したリクエストは拒否されます。ファイルのそのほかのキーは、まったく元のまま保持されます。

## 保存の仕組み

1. 変更された値だけが、`Content-Type: application/json` で本文が最大 16 KB の `POST /api/settings` として送信されます。
2. すべての値は型と範囲に照らして検証されます。無効な値が 1 つでもあればリクエスト全体が拒否され、何も書き込まれません。パスは制御文字を含まないテキストでなければならず、
   ネットワーク（UNC）パスや `D:` ドライブ上のパスは認められません。
3. 変更前のファイルは `config_backups/actions_monitor-<time>.json` にコピーされます（直近 10 件のコピーが保持されます）。
4. 新しいファイルは一時ファイルに書き込まれてから古いファイルの上に移動される（アトミック）ため、クラッシュしても中途半端なファイルが残ることはありません。有効な JSON ではないファイルは、ページから上書きされることはありません。
5. 再起動が必要な保存済みの値がページに表示され、再起動するまでバナーが表示され続けます。

## リクエストできる者

同じマシンのページだけです。サーバーは `127.0.0.1` で待ち受け、`Host` または `Origin` が自身のアドレスでないリクエストを拒否します（ほかのすべてのエンドポイントと同じチェックです）。
リクエストは JSON でなければならないため、別サイトのフォームからは到達できません。

## 1.5.0 より前

ツールの言語はシステムの言語で決まっていましたが、現在は英語で起動し、言語は設定項目になっています（ここでは `language`、`MONITOR_LANG`、または `--lang`）。
`parte_history_days` は `report_history_days` になりました（古い名前も引き続き読み込まれます）。
