<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SENTINEL_por.md)

# センチネルとそのチェック A1〜A13

**センチネル**はフル版の後半部分です。*モニター*は「今」何が動いていて何が失敗したかを示し、*センチネル*はアカウント全体を数分おきに調べて別の問いに答えます。**人の手が必要なのは何か**。GitHub を読み取るだけで書き込みはせず、このコンピューターに短い履歴を保存し、見つけたものを番号付きの13のチェック（**A1〜A13**）にまとめ、それぞれに信号を付けます。

**ライト版には含まれません。** `MONITOR_LITE_GITHUB_ACTIONS`（ポート 8766）にはセンチネルがありません。モジュールはインポートすらされず、関連するエンドポイントは 404 を返します。フル版（`MONITOR_GITHUB_ACTIONS`、ポート 8765）は自動で起動し、`sentinel.enabled`（設定 > センチネル）で止められます。両版は「main で赤」（A2）に同じ規則を使うため、数値は一致します。

**日次トレンド** (アドレス `#sentinel-trend`) には専用のメニュー項目があり、シグナルごとに小さな曲線 (コードスキャン、Dependabot、シークレット、プルリクエスト、赤、候補) と最新の値を表示します。センチネルの概要には自身のパネルと、それを開くボタンだけが残ります。

`sentinel.trend_workflow_marks` をオンにすると(既定はオフ)、日次トレンドのグラフは、リポジトリの `.github/workflows` のファイルにコミットが触れた日にも四角の印を付け、所要時間や失敗数の急な変化の説明を横に示します。リポジトリごとに 1 リクエスト(`commits?path=.github/workflows`)かかり、1 回に `sentinel.trend_workflow_marks_per_tick` リポジトリ、同じリポジトリは `sentinel.trend_workflow_marks_hours` 経過後にのみ再確認し、`sentinel.trend_workflow_marks_days` 日分を遡ります。日次履歴にすでにある日だけに印が付き、モニターが止まっていた日は作られず、印は `GET /api/sentinel` の `a3.trend.workflows` にあります。

**コラボレーション**、**セキュリティ**、**デリバリー**、**サプライチェーン**の各パネルは、シグナルごとに 1 枚のカード (6、6、6、5 枚) を表示し、それぞれにカウンター、一覧、リポジトリでの絞り込み、ヘルプ 1 行があります。デリバリーとサプライチェーンにはコード別の表と、リポジトリ・レベルの絞り込みが加わります。**日次トレンド**は、センチネルがすでに保存している履歴から 25 系列を表示します (GitHub への呼び出しなし)。各カードには現在値、前日比と 7 日前比、小さな曲線があり、押すと大きく表示できます。7・30・60 日の選択、別の系列との比較、凡例での線の切り替え、ツールチップでの日ごとの値 (矢印キーも可)、しきい値、更新とインシデントの印、期間の CSV/JSON ダウンロードに対応します。系列ができる前に保存された日は 0 ではなく欠落として表示されます。 さらに 7 系列は、サイクルがすでに読んでいる情報 (実行の平均時間と p95、キューでの平均待ち時間、不安定なワークフロー、アーティファクトのサイズ、中レベルと低レベルのアラート) から作られます。最も多く使うリポジトリごとの Actions の分数を日ごとに描き、リリースを公開した日にはマークが付き、グラフの基準線は設定 (`sentinel.trend_green_pct`、`sentinel.trend_health`、`sentinel.trend_quota_pct`) です。折れ線と棒を選べ、グラフを画像としてコピーでき、タブのブリーフ (`strend`) は全系列をシグナル `trend.daily` に載せます。

**昨日と今日**（アドレス `#sentinel-yesterday`）も専用のメニュー項目になったため、センチネルのレポートがページ全体を使います。最後に保存したレポート以降に現れたもの、解決したもの、残っているものを、赤いワークフローと保留中の署名について示します。

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
| **A1** | **ビルド。** 制限時間を超えて実行中または待機中の run は*停止*とみなします。ラベル `build-failed` または `build-stuck` の付いた未解決 issue も表示します。イベント `dynamic`（Dependabot の内部）の run は無視します。 各行は待機理由（ランナー、承認、ランナーのオフライン、長いビルド）を示します。`ci.stuck.*` でワークフローごとの上限を学習したり、ワークフローまたはランナーラベルごとに固定できます。 `ci.stuck.ghost_days` 日（既定 7、最初の試行のみ、スイッチは `ci.stuck.ghost_enabled`）より長くキューにある実行は*幽霊キュー*です。GitHub は決して開始しないため、待機中にも停止中にも数えず、アラームも出しません。別に数えて一覧にし（`a1.ghosts`）、リポジトリごとに情報の通知を 1 件出します（`ci.ghost_queue`）。どのランナーも持たないラベル(GitHub ホストのものでも汎用でもなく、一覧にあるどのランナーにもないもの)を待つ実行は `no_runner` と呼ばれます。誰もそれを拾えません。`ci.stuck.no_runner_check`(既定はオフ)と `runners.enabled` が必要です。より大きなランナーや別の組織のランナーはその一覧になく誤って名指しされるため、オンにするかどうかはあなた次第です。 | `stuck_minutes` | 停止または issue があれば **bad**。run を開いて取り消すか再実行し、直したら issue を閉じます。 |
| **A2** | **赤い CI。** 各ワークフローファイルについて、既定ブランチで**最後に完了した** run が失敗（`failure`, `timed_out`, `startup_failure`）なら赤です。`cancelled`、`skipped`、`neutral`、`stale` の run、実行中の run、他のブランチの run は判定に影響せず、過去の赤を隠しません。 判定するのは `push`、`schedule`、`workflow_dispatch`、`merge_group`、`workflow_run`、`repository_dispatch` の run だけです（`ci.red_events`）。プルリクエスト、コメント、issue は判定せず、ブランチ名が同じく `main` のフォークからのプルリクエストも判定しません（`ci.count_fork_runs`）。承認待ちの run（`action_required`、または環境に保留された job）は *承認待ち* で、赤でも待機中でもありません。`ci.inactive_days` 日間実行されていないワークフローは永久に赤ではなく *非アクティブ* です。マージキューでの失敗は `(マージキュー)` と表示され、`ci.extra_branches` で保守ブランチを追加し、`ci.automation_counts` でトリアージやボットのワークフローを数えるかを決めます。*連続*=続けて赤だった回数。リポジトリの run 一覧が要求したサンプルと同じ長さのとき、その先にワークフローが隠れている可能性があるため、センチネルは該当ワークフローごとに最後の run を GitHub に問い合わせます。連鎖したワークフロー(`workflow_run`、`repository_dispatch`)は、既定ブランチ上で、かつフォーク由来でない場合にのみ判定に使われます。 `ci.group.reusable` を有効にすると、同じ再利用可能ワークフローを呼ぶ赤のワークフローが1つの共通原因として表示され、通知も1回になります。`ci.failed_jobs` では、赤い実行で失敗したジョブがプラットフォーム別に表示されます。 GitHub が自分用に作るワークフロー（`dynamic/` で始まるパス：Dependabot の更新、依存関係グラフ、既定の CodeQL、Copilot のレビューとエージェント）にはファイルがありません。赤の CI にも *非アクティブ* にもなりません。失敗した Dependabot の更新は警告として、それ以外は情報として別に表示されます（`a2.services`）。 誰も対処しない赤は*古くなります*。失敗した実行が `ci.red_age_days` 日（既定 30、スイッチは `ci.red_ages`）より古く、判定に使うイベントの新しい実行がない場合、そのワークフローは赤ではなく非アクティブとして表示されます。 | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | 赤いワークフローがあれば **bad**。run データがない、またはワークフローを解決できない場合は **unknown**（緑にはなりません）。ワークフローを直すか再実行します。ライト版は既定ブランチを推測するため、同じ数値に「概算」と表示します。。 失敗した Dependabot の更新は、リポジトリごとに 1 件、中程度の重大度の独立したアラートにもなります(`ci.dependabot_failed`、スイッチ `ci.dependabot_alerts`、既定でオン)。失敗した Copilot のワークフローはお知らせになることがあります(`ci.copilot_activity`、スイッチ `ci.copilot_alerts`、既定でオフ)。どちらもほかのアラートと同じようにミュートできます |
| **A3** | **セキュリティアラート。** リポジトリごとの未解決の CodeQL、Dependabot、シークレットスキャンのアラートを重大度付きで表示し、履歴の前日からの新規件数も示します。 | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | シークレットまたは critical/high があれば **bad**、その他は **warn**、読み込み中は **unknown**。漏えいしたシークレットを最優先でローテーションし、残りを更新または却下します。 |
| **A4** | **Dependabot のプルリクエスト。** Dependabot の未マージ PR と、その経過日数、*メジャー*バージョンの跳躍、マージ競合。他の人の PR は件数のみ数えます。Renovate は Dependabot と同じ扱いです（`sentinel.dependency_bots`）。 | `sentinel.stale_pr_days` (7), `sentinel.dependency_bots`, `sentinel.bots_apart` | メジャー跳躍や競合があれば **warn**、PR のみなら **info**。緑のものはマージし、競合するものはリベースまたは閉じます。 |
| **A5** | **リリース。** (a) *候補*: CHANGELOG の `[Unreleased]` に `candidate_min_entries` 件以上あり、最後のリリースが `candidate_days` より古い（または無い）。(b) 最後のリリースより新しい、リリース用ワークフローの*緑のビルド*。(c) *署名待ち*: `pending_sign_hours` より古く、署名も公開もされていない緑のビルド。署名はエコシステムの公開鍵で検証できた場合のみ有効です。エントリ数は、クローンが今いるブランチではなく、リモートの既定ブランチ（クローンの `origin/main`、fetch なし）で数えます。作業ツリーしか読めない場合は行にその旨を表示します。入れ子のリスト行も数えます。 | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | 候補または署名待ちがあれば **warn**、未リリースの緑のビルドは **info**。リリースを切るか、ビルドに署名します。 |
| **A6** | **衛生。** リポジトリごとに、ルールセット `protect-main` が ACTIVE、ラベル `dependencies` が存在、必須ファイル（既定は README, LICENSE, CHANGELOG, SECURITY）が存在、SHA 固定が必須、`allowed_actions` が `selected`、GitHub に無効化された定期ワークフローが無いこと。ルールセット名は設定（`sentinel.hygiene.ruleset_names`、パターン可）で、`effective` モードではルールセットの名前に関係なく、GitHub が既定ブランチにルールまたは保護があると報告すれば保護済みとみなします。別名のライセンスファイル（LICENSE-MIT、COPYING）も有効で、コミュニティプロファイルやアカウントの `.github` リポジトリも含められます。トークンで判断できないこと（管理者権限なし）は「評価不可」と表示され、緑にも警告にもなりません。 `effective` モードでは 3 つの公開された回答（ルールセットのルール、`protected`、ブランチの従来の `protection`）を組み合わせます。従来の保護だけで守られたリポジトリも保護されているとみなし、ルールの一覧が空であること自体は「保護なし」ではありません。A6 の各行は、ブランチを何が守っているか（`ruleset`、`classic`、`both`、`none`）を示し、GitHub が答えなかったときは何も示しません。 `sentinel.hygiene.ruleset_mode` の既定値は `effective` です。`name` にすると、特定の名前のルールセットを求める従来の規則に戻ります。 フォークは、独自の CI がある場合にのみここで（ワークフローの lint とスコアでも）評価されます。独自の CI とは、直近 `ci.fork_own_ci_days` 日のあいだのプッシュ、プルリクエスト、手動、マージキューのいずれかによる自分の実行です（スイッチは `ci.forks_need_own_ci`）。コピーされたスケジュールは数えません。それ以外のフォークは別に一覧にされ（`a6.forks_idle`）、評価されません。 `upstream.enabled`(既定はオフ)を有効にすると、各フォークの元リポジトリのチェック状態と最新リリースも追跡し、`upstream.notify` を有効にすると情報通知 `ci.upstream_red` と `ci.upstream_release` も出します。 | `sentinel.required_files`, `sentinel.hygiene_seconds`, `sentinel.hygiene.ruleset_mode`, `sentinel.hygiene.ruleset_names`, `sentinel.hygiene.skip`, `sentinel.hygiene.community_fallback`, `upstream.enabled`, `upstream.notify` | 問題があれば **warn**、未確認のものがあれば **info**。各問題に修正方法が示されます。 |
| **A7** | **使用量。** リポジトリ・エコシステムごとの直近24時間と7日間の Actions 分数、残りの API クォータ、エコシステムごとの*予算*。上限の80%未満は **ok**、80%以上は **warn**、100%以上は **over**。≥ が付いた値は最小値です。実行リストが満杯でウィンドウの開始まで遡れないリポジトリは、表示より多くの実行を持ちます。 | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | クォータが下限未満、または予算が80%に達したら **warn**。更新間隔を延ばすか、長いワークフローを削ります。 |
| **A8** | **ラウンド。** 監査フォルダー内の監査・ラウンドのファイル（`sentinel.audit_files` のパターン）を読み、状態を表示します。監査フォルダーが無ければ空です。 | `sentinel.audit_files.*`, `audit_dir` | **info** のみ。対応不要。 |
| **A9** | **ロードマップ。** エコシステムの GitHub Projects ボードが*生きている*か。直近8日以内に照合され、定義より古くないこと。`gh` の `read:project` スコープが必要で、無い場合は定義だけで動作し、不足を表示します。定義はリモートの既定ブランチから読みます。シード用ワークフローの実行を読めないとき（クォータ、ネットワーク）、タブはエラーを表示し、「一度も実行されていない」とは言いません。 | (fixed: 8 days) | ボードが古い、または未照合なら **warn**、未設定なら **unknown**。 |
| **A10** | **Actions とリリースの表面。** クローンに対する25個の読み取り専用チェックと少数のコールドコール。下の表に一覧します。各チェックにスイッチがあり、必要なものには閾値があります。 | `sentinel.surface.*` | チェックごと（下記）。クォータが少ないと一時停止します（レポートに表示）。 |
| **A11** | **リリース準備、エコシステムの健全度、ピン。** リポジトリごとの準備状況（エントリ、CI、バージョン、ビルド、署名、次の手順）。エコシステムごとの0〜100の健全度は、赤、停止、シークレット、高アラート、アラート、古い PR、未署名ビルド、衛生に重み付けした減点を引いたもの。遅れている依存ピンも表示。スコアは `min_coverage` の割合のリポジトリにデータがあるときだけ表示します。 ワークフローが一つもないリポジトリ（ワークフローファイルも実行もないクローン）は対象外で、カバレッジを下げず、別に一覧表示されます。最低値を下回るグループは「データ不足」と表示し、データのあるリポジトリ数と不足しているものを示します。 | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | スコアが `warn_below` 未満なら **warn**、遅れたリポジトリがあれば **info**、データ不足なら **unknown**。 |
| **A12** | **分析。** 各ワークフロー、そのジョブの待機時間、各ステップの p50 / p95。通常より遅くなったワークフロー（`analytics.slow_factor`）と、*不安定（flaky）*なワークフロー（失敗後に同じコミットで成功）。ラベルにすぎず、赤の判定は変えません。 時間は run の最新の試行で測ります。再実行で最初の試行は使わず（数日の待機や数百日の所要時間は出ません。不明な待機は空欄）、承認後の再試行は flaky にしません（`ci.rerun_timing` は完了した再実行の実際の所要時間も GitHub に問い合わせます）。 | `analytics.*` | 専用の信号はありません。遅いものと flaky を先に確認します。 |
| **A13** | **ワークフローリンター。** ローカルのクローンに対する静的ルール(`lint.source` を `auto` または `sparse` にすると、クローンのないリポジトリのファイルも GitHub から読んで対象にします。1サイクルの呼び出しは予算内の少数で、SHA が変わっていないファイルは再読込しません。読めない・確認できないものは、SSO 未承認、スコープ不足、クローンなしなどの理由付きで*評価不可*と表示されます): `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`。指摘にはレベル（情報/警告/エラー）があり、コメント `# monitor-lint: ignore ルール 理由` または `lint.ignore` で抑制できます。 | `lint.*` | 最も重い指摘の色。エラーから直します。ページはレベルで絞り込めます。 |

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
| `commit_state` | 最新コミットの状態:すべてのアプリのすべてのチェックとステータス | off · include_other_apps, include_statuses |
| `release_assets` | 不完全な公開済みリリース | on · recent_days=30, required, require_sha256, require_signature, allow_empty（ファイルのないリリースを許可） |
| `tag_vs_version` | タグとマニフェストのバージョン | on · prefixes (`sentinel.surface.checks.tag_vs_version.prefixes`), prerelease_ok |
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

## どのセンチネルも隠さないこと

1 つの不良要素のためにアカウント全体を諦めることはありません。リポジトリ、ファイル、項目、段階のそれぞれが専用の保護の中で読まれ、失敗は原因とともに記録され(状態の `errors`)、他は続行されます。読めなかったものは**保持され、閉じられません**。今は読めないリポジトリの既知のアラートは、修正済みとして数えられる代わりに(未読として印を付けて)残り、そのリポジトリは「未確認」として名前で一覧され(状態の `unchecked`、`read_report.py` の「未確認」の行)、アラート 0 件とは決して数えられません。対象から外れたリポジトリは、そのアラートとエラーとともに消えます。CI センチネルの読み取りパス(コードスキャンとシークレットのアラート、各リポジトリの設定)にも時間上限 `sentinel.deadline_s`(30 秒、0 = なし)があり、それを過ぎると新しいリポジトリは始まらず、届かなかったものは次のサイクルに持ち越されて名前が示されます。ランナー一覧は、読まなかったリポジトリを示します(`/api/runners` の `unchecked`)。契約テストが、登録簿のすべてのセンチネルに同じ検査を行います。

## 2 つ目の番人とアラート一覧

この番人（CI）のほかに、完全版には **Collab 番人** があります。未解決の Issue とプルリクエストを独自の周期で見守り、GitHub には書き込みません：[COLLAB_jpn.md](COLLAB_jpn.md)。**アラート**タブは両方のアラートを 1 つの一覧にまとめ、由来とレベルでの絞り込みと、自動で終わるローカルのミュート（`alerts.mute_hours`）を備えます。同じ一覧を `GET /api/alerts` が返します。

## 左のメニュー: グループとセンチネル

メニューには、それぞれ見出しのある 5 つのグループがあります (折りたたみでき、モニターが状態を記憶します): 「監視」(現在、アラート、グラフ)、「センチネル」(概要、CI センチネル、コラボセンチネル、セキュリティセンチネル)、「チーム」(チームの状態、フリート、リポジトリ)、「レポートと学習」(レポート、定期レポート、教訓、履歴)、「システム」(設定)。各項目に固有のアドレスがあります: `#team-health`、`#fleet`、`#team-reports`、`#reports`、`#lessons`、`#sentinel`、`#sentinel-ci`、`#sentinel-collab`、`#sentinel-security` (同じ語での `?view=` も可)。古いアドレス (`#team`、`#sent`、`#alerts/reports`、`#team/fleet` など) も正しいパネルを開きます。

3 つのセンチネルはオン/オフできます (`sentinel.enabled`、`sentinels.collab.enabled`、`sentinels.security.enabled`)。センチネルの項目はオンの間だけメニューに表示され、どれもオンでなければ「センチネル」グループも消えます。ページは次の更新で状態に追従します。オフのセンチネルのアドレスもパネルを開き、オフであることと、設定のスイッチを開くボタンが表示されます。A1〜A13 のパネルは CI センチネルのもので、各項目のバッジは自分のセンチネルのアラートだけを数えます。

セクション A1〜A13 で折りたたんだり開いたりしたものはそのまま保たれます。ページは更新のたびに描き直しますが、各セクションを名前で覚えています（`ui.remember_folds` は既定でオンで、選択をブラウザーにも保持します）。

## A5 の署名キュー

実行が署名キューに入るのは、(a) ドライランではなく（「Prepare the draft」ステップが実行された）、(b) リリースの下書きが待っているか、リポジトリに公開リリースがなく、(c) そのバージョンが署名付きで公開済みでない場合だけです。モニターはキューの各実行を 6 時間に 1 回確認します（実行のジョブとリポジトリのリリースの 2 回の読み取り、1 サイクルあたり最大 3 実行、同じ割当のゲートの内側）。キューから外れたものは、その下に「確認済み：vX は公開済み」または「ドライラン」として表示されます。まだ誰も確認していない行は残り、未確認と表示されます。
## リポジトリに関するメモ

ここにあるものはすべてモニターのメモです。読み取るだけでGitHubには書き込まず、既定ではオフか空です。

- **赤のきっかけ。** すべての赤には区分が付きます: `pr`(プルリクエスト)、`main`(push)、`nightly`(スケジュール)、`manual`(人または外部からの呼び出し)、`queue`(マージキュー)、`chained`(別のワークフロー)、`other`。アラートタブではタグとして表示され、それで絞り込めます(「起動元」)。どのイベントを赤として数えるかは引き続き `ci.red_events` で、監視する保守ブランチは `ci.extra_branches` で追加します。
- **想定済みの赤**(`expected_red.enabled`)。アラートタブまたはパレットから、ワークフロー(またはリポジトリ全体を表す `*`)を、理由・担当者・日数(`expected_red.max_days` まで)つきで意図的な赤としてマークします。マークの間、その赤は別に一覧表示され、数えられず、警告もされません。期限が切れると赤が戻り、マークを外すか付け直すまで、期限切れを知らせる警告が1件出ます。
- **ユーザーごとの異常なクローン**(`audit_feed.clone_alert.enabled`)。組織の監査ログから `git.clone` を読み取ります(提供するのは一部のプランのみで、お使いのプランにない場合は応答が `available: false` になります)。`window_hours` の間に `threshold` を超える数の異なるリポジトリをクローンしたユーザーが警告で名指しされます。ロボットは名前のパターンと `[bot]` で終わる名前で除外されます。
- **メタデータ列**(`fleet.meta_columns`)。`{"name", "path", "regex"}` のJSONリストで、最大5つ。最初に一致した行での式の最初のグループ(またはマッチ全体)が列の値になります。ファイルの先頭8 KBだけを見ます。
- **チーム外の人**(`sentinels.collab.rules.watch_external_comments`、`external_days`、`team_members`)。チーム外の人のissueまたはプルリクエストに、`external_days` 日たっても誰も応答も操作もしていなければ、コード `collab.issue.external` の警告になります。

| ルート | 内容 |
|---|---|
| `GET /api/expected-red` | マークと、その状態(`active` または `expired`) |
| `POST /api/expected-red` | `{"action": "add", "repo", "workflow", "reason", "owner", "days"}` または `{"action": "remove", "id"}`(メンテナー、ページの1回限りトークン付き。操作ログに記録されます) |
| `GET /api/clone-anomalies` | 監査ログから、しきい値を超えたユーザー(メンテナー) |
| `GET /api/meta-columns` | 列と、各リポジトリでこれまでに見つかった値 |
