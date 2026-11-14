<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SENTINEL_por.md)

# センチネルとそのチェック A1〜A13

**センチネル**はフル版の後半部分です。*モニター*は「今」何が動いていて何が失敗したかを示し、*センチネル*はアカウント全体を数分おきに調べて別の問いに答えます。**人の手が必要なのは何か**。GitHub を読み取るだけで書き込みはせず、このコンピューターに短い履歴を保存し、見つけたものを番号付きの13のチェック（**A1〜A13**）にまとめ、それぞれに信号を付けます。

**ライト版には含まれません。** `MONITOR_LITE_GITHUB_ACTIONS`（ポート 8766）にはセンチネルがありません。モジュールはインポートすらされず、関連するエンドポイントは 404 を返します。フル版（`MONITOR_GITHUB_ACTIONS`、ポート 8765）は自動で起動し、`sentinel.enabled`（設定 > センチネル）で止められます。両版は「main で赤」（A2）に同じ規則を使うため、数値は一致します。

## 起動のしかたとコスト

フル版のモニターと同じプロセス内の専用スレッドで動き、GitHub 呼び出し用の専用予算（`sentinel.budget_per_hour`、既定 600、および `sentinel.max_calls_per_tick`）を持ちます。GitHub の残りクォータが `sentinel.min_rate_remaining` を下回ると問い合わせを止め、ページにクォータによる一時停止と表示します。GitHub への書き込みは一切行いません。

## 書き出すファイル（モニターのフォルダーに置かれ、公開されません）

| ファイル | 内容 |
|---|---|
| `ci_red.json` | スキーマ 2: リポジトリごとの赤いワークフローと、リリースが署名を待つ時間。他のツール向けの安定した契約で、`CI_RED_SCHEMA_jpn.md` と `CI_RED_BRIDGE_jpn.md` を参照。場所: `sentinel.ci_red_file`。 |
| `sentinel_history.json` | 傾向と「昨日からの新規」に使う日ごとの合計（アラート、赤、候補）。 |
| `sentinel_cache.json` | 遅い読み取りの最新の応答。再起動しても全部を問い合わせ直さないためのもの。 |
| `events_monitor.jsonl`, `events_state.json` | イベントの流れ（何が赤くなり、何が直ったか）。各イベントに安定した `code` が付きます。 |
| `SENTINEL_REPORT_*.txt` | 日次レポート。監査フォルダーがあればそこに保存されます。 |

## 読み方

各チェックは5つのレベルのいずれかです。**ok**（対応不要）、**info**（知っておくとよい）、**warn**（早めに確認）、**bad**（すぐ対応）、**unknown**（まだ確認できない。**unknown は決して緑で表示されません**）。タブ上部のレポートが数行で要約し、詳細はチェックごとに開きます。モニターで除外したリポジトリはチェックされません。

どのランプも色だけでなく形を持ちます(ok はチェックマーク、warn は感嘆符、bad は×、info は *i*、unknown は疑問符)。そのためレベルが色だけに頼ることはありません。ランプにマウスを重ねるか、キーボードで移動すると、レベルが言葉で表示され、変化する前の状態も確認できます。ランプはレベルに合わせたペースで呼吸するように明滅し、変化したランプは短いトランジションを一度再生します。システムが視差効果の軽減(モーション軽減)を求めている場合は、何も動きません。

## チェック一覧

| チェック | 確認内容と正確な規則 | 設定場所 | レベルと対処 |
|---|---|---|---|
| **A1** | **ビルド。** 制限時間を超えて実行中または待機中の run は*停止*とみなします。ラベル `build-failed` または `build-stuck` の付いた未解決 issue も表示します。イベント `dynamic`（Dependabot の内部）の run は無視します。 | `stuck_minutes` | 停止または issue があれば **bad**。run を開いて取り消すか再実行し、直したら issue を閉じます。 |
| **A2** | **赤い CI。** 各ワークフローファイルについて、既定ブランチで**最後に完了した** run が失敗（`failure`, `timed_out`, `startup_failure`, `action_required`）なら赤です。`cancelled`、`skipped`、`neutral`、`stale` の run、実行中の run、他のブランチの run は判定に影響せず、過去の赤を隠しません。*連続*=続けて赤だった回数。リポジトリの run 一覧が要求したサンプルと同じ長さのとき、その先にワークフローが隠れている可能性があるため、センチネルは該当ワークフローごとに最後の run を GitHub に問い合わせます。 | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | 赤いワークフローがあれば **bad**。run データがない、またはワークフローを解決できない場合は **unknown**（緑にはなりません）。ワークフローを直すか再実行します。ライト版は既定ブランチを推測するため、同じ数値に「概算」と表示します。 |
| **A3** | **セキュリティアラート。** リポジトリごとの未解決の CodeQL、Dependabot、シークレットスキャンのアラートを重大度付きで表示し、履歴の前日からの新規件数も示します。 | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | シークレットまたは critical/high があれば **bad**、その他は **warn**、読み込み中は **unknown**。漏えいしたシークレットを最優先でローテーションし、残りを更新または却下します。 |
| **A4** | **Dependabot のプルリクエスト。** Dependabot の未マージ PR と、その経過日数、*メジャー*バージョンの跳躍、マージ競合。他の人の PR は件数のみ数えます。 | `sentinel.stale_pr_days` (7) | メジャー跳躍や競合があれば **warn**、PR のみなら **info**。緑のものはマージし、競合するものはリベースまたは閉じます。 |
| **A5** | **リリース。** (a) *候補*: CHANGELOG の `[Unreleased]` に `candidate_min_entries` 件以上あり、最後のリリースが `candidate_days` より古い（または無い）。(b) 最後のリリースより新しい、リリース用ワークフローの*緑のビルド*。(c) *署名待ち*: `pending_sign_hours` より古く、署名も公開もされていない緑のビルド。署名はエコシステムの公開鍵で検証できた場合のみ有効です。 | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | 候補または署名待ちがあれば **warn**、未リリースの緑のビルドは **info**。リリースを切るか、ビルドに署名します。 |
| **A6** | **衛生。** リポジトリごとに、ルールセット `protect-main` が ACTIVE、ラベル `dependencies` が存在、必須ファイル（既定は README, LICENSE, CHANGELOG, SECURITY）が存在、SHA 固定が必須、`allowed_actions` が `selected`、GitHub に無効化された定期ワークフローが無いこと。 | `sentinel.required_files`, `sentinel.hygiene_seconds` | 問題があれば **warn**、未確認のものがあれば **info**。各問題に修正方法が示されます。 |
| **A7** | **使用量。** リポジトリ・エコシステムごとの直近24時間と7日間の Actions 分数、残りの API クォータ、エコシステムごとの*予算*。上限の80%未満は **ok**、80%以上は **warn**、100%以上は **over**。 | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | クォータが下限未満、または予算が80%に達したら **warn**。更新間隔を延ばすか、長いワークフローを削ります。 |
| **A8** | **ラウンド。** 監査フォルダー内の監査・ラウンドのファイル（`sentinel.audit_files` のパターン）を読み、状態を表示します。監査フォルダーが無ければ空です。 | `sentinel.audit_files.*`, `audit_dir` | **info** のみ。対応不要。 |
| **A9** | **ロードマップ。** エコシステムの GitHub Projects ボードが*生きている*か。直近8日以内に照合され、定義より古くないこと。`gh` の `read:project` スコープが必要で、無い場合は定義だけで動作し、不足を表示します。 | (fixed: 8 days) | ボードが古い、または未照合なら **warn**、未設定なら **unknown**。 |
| **A10** | **Actions とリリースの表面。** クローンに対する25個の読み取り専用チェックと少数のコールドコール。下の表に一覧します。各チェックにスイッチがあり、必要なものには閾値があります。 | `sentinel.surface.*` | チェックごと（下記）。クォータが少ないと一時停止します（レポートに表示）。 |
| **A11** | **リリース準備、エコシステムの健全度、ピン。** リポジトリごとの準備状況（エントリ、CI、バージョン、ビルド、署名、次の手順）。エコシステムごとの0〜100の健全度は、赤、停止、シークレット、高アラート、アラート、古い PR、未署名ビルド、衛生に重み付けした減点を引いたもの。遅れている依存ピンも表示。スコアは `min_coverage` の割合のリポジトリにデータがあるときだけ表示します。 | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | スコアが `warn_below` 未満なら **warn**、遅れたリポジトリがあれば **info**、データ不足なら **unknown**。 |
| **A12** | **分析。** 各ワークフロー、そのジョブの待機時間、各ステップの p50 / p95。通常より遅くなったワークフロー（`analytics.slow_factor`）と、*不安定（flaky）*なワークフロー（失敗後に同じコミットで成功）。ラベルにすぎず、赤の判定は変えません。 | `analytics.*` | 専用の信号はありません。遅いものと flaky を先に確認します。 |
| **A13** | **ワークフローリンター。** ローカルのクローンに対する静的ルール: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`。指摘にはレベル（情報/警告/エラー）があり、コメント `# monitor-lint: ignore ルール 理由` または `lint.ignore` で抑制できます。 | `lint.*` | 最も重い指摘の色。エラーから直します。ページはレベルで絞り込めます。 |

## A10 のチェック

すべて人への読み取り専用の提案です。モニターが issue を閉じたり、プルリクエストをマージしたり、リリースを公開したりすることはありません。個別に止めるには `sentinel.surface.checks.<名前>.enabled` を使います。

| チェック | 探すもの | 既定 |
|---|---|---|
| `workflows_disabled` | 手動で無効化された workflow | on |
| `dead_schedule` | 実行されていないスケジュール | on · days=14 |
| `unpinned_uses` | SHA で固定されていない uses: | on |
| `broad_permissions` | 広すぎる権限（write-all） | on |
| `pr_target` | PR をチェックアウトする pull_request_target | on |
| `stuck_concurrency` | concurrency の詰まり（同じ workflow の待機中の実行） | on · minutes=60 |
| `matrix_os` | マトリクスの 1 つの OS だけで失敗 | on · max_per_tick=4 |
| `artifacts` | アーティファクトのコスト | on · max_mb=500, retention_days=30 |
| `required_checks` | 赤または欠落している必須チェック | on |
| `release_assets` | 不完全な公開済みリリース | on · recent_days=30, required |
| `tag_vs_version` | リリースタグとマニフェスト/CHANGELOG のバージョンの比較 | on |
| `packages` | GitHub Packages | on |
| `drafts` | 放置された下書きとプレリリース | on · days=14 |
| `security_aged` | 経過日数別の重大/高アラート（リポジトリ順位） | on · days=30 |
| `coverage` | セキュリティの適用範囲（CodeQL / Dependabot） | on |
| `secret_resolved` | シークレットスキャン: 未対応と解決済み | on |
| `dependabot_priority` | 優先度別の Dependabot | on |
| `issue_close` | クローズできそうな issue（提案のみ） | on |
| `milestones` | エコシステムごとの期限切れマイルストーン | on |
| `pr_human` | 古くなった人間による PR | on · days=7 |
| `pr_workflow_touch` | workflow または CODEOWNERS を変更する PR（優先） | on |
| `merge_queue` | マージキュー: 承認済みで CI が成功 | on |
| `maturity` | マニフェストの成熟度と根拠の比較 | on |
| `parity` | 8 言語の README の整合性が崩れています | on |
| `attestation` | ビルドの証明 | on · max_per_tick=3 |

## 設定の場所

上の閾値はすべて、設定ページの**センチネル**、**表面チェック（A10）**、**準備（A11）**、**フォルダーとファイル**、**分析**、**ワークフローリンター**の各タブの項目であり、`actions_monitor.json` のキーです。範囲を含む完全な一覧は `SETTINGS_jpn.md` にあります。ヘルプパネルと `--help-topics sentinel` でこのページをオフラインで表示できます。

## 2 つ目の番人とアラート一覧

この番人（CI）のほかに、完全版には **Collab 番人** があります。未解決の Issue とプルリクエストを独自の周期で見守り、GitHub には書き込みません：[COLLAB_jpn.md](COLLAB_jpn.md)。**アラート**タブは両方のアラートを 1 つの一覧にまとめ、由来とレベルでの絞り込みと、自動で終わるローカルのミュート（`alerts.mute_hours`）を備えます。同じ一覧を `GET /api/alerts` が返します。
