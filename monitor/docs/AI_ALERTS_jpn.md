<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# AI向けアラート

リポジトリで作業する誰も知らなければ、赤いワークフローは意味がありません。モニターは、あらゆるAIツール(Codex、Gemini CLI、Copilot)やスクリプトが読める小さなフィードを書き出します。

## 書き出す内容(ローカル、読み取り専用、ネットワークなし)
- `ai_alerts.jsonl`: イベント(開始・確認済み・解決)ごとに1行。安定したID、重大度、リポジトリ、ワークフロー、結果、開始時期、連続回数、リンク、推定原因(**実際**または**一時的**)、推奨アクション、状態を含みます。
- `ALERTS_BRIEF.md`: サイクルごとに書き直される短い要約(`ai_alerts.brief_max_bytes`、既定 2 KB)。実際のアラートが先頭です。
- 一時的な原因(502/503/504、タイムアウト、レート制限、ダウンロード失敗、開始しなかった実行)は、`ai_alerts.transient_patterns` で編集できるルールで実際の失敗と区別されます。ワークフローが緑に戻るとアラートは自動で解決し、確認(`ack`)もできます(これはこのローカル状態だけを変えます)。
- すべては先にクリーナーを通ります。トークン、キー、メールアドレス、IPアドレス、ホームフォルダーはファイル、エンドポイント、フックに届きません。
- フォルダーは `ai_alerts.folder`(既定はモニターの隣)で、AIセッションが読むものを選んでください。`ci_red.json` には、赤い各ワークフローに任意の `ai_hint`(分類、原因、アクション)が付きます。

## AIの読み方
- プロジェクトやスキルの指示に次を入れます: *「開始時に ALERTS_BRIEF.md(パス)を読み、開いている実際のアラートを伝えること。」*
- または動作中のモニターに問い合わせます: `GET /api/ai/brief`(Markdown、または `?fmt=json`)と `GET /api/ai/alerts?since=秒`。ページの他の部分と同じ規則です(このPC。ネットワークモードではアクセストークン)。
- または MCP サーバー(読み取り専用)を追加します: `python mcp_server.py`、ツール `get_alerts`、`get_red_repos`、`get_run_failure`、`get_quota`。`--allow-ack` で `ack_alert`(ローカル状態のみ)が加わります。Gemini CLI、Codex、VS Code(Copilot)では同じコマンドを MCP 設定に stdio サーバーとして追加します。

## 届く通知
- 新しい実際のアラートは、すでに設定した通知チャネルに送られます(設定 > 通知)。
- 任意で、既定はオフ: `ai_alerts.hook` は新しい実際のアラート(整形済みの固定フィールド)をこのPC上のアドレスへ、1時間に最大 `max_per_hour` 回POSTし、あなたのスクリプトがAIセッションを起こせるようにします。
- これらのどれも、AIプロバイダーへのデータ送信、コマンド実行、GitHubへの書き込みは行いません。

## MCP サーバーはローカル専用です

`mcp_server.py` は、起動した AI ツールと標準入出力で JSON をやり取りします。ネットワークポートを持たず、ポートの背後に置いてはいけません。形式の誤ったメッセージにはそのメッセージ分のエラーだけを返し、64 KB を超える行は拒否します。`ack_alert`（`--allow-ack` のときのみ）が変えるのはフィードのローカル状態だけです。フィードにはリポジトリ名や CI の短いエラーメッセージが含まれ得ますが、外に出す前にトークン、キー、メールアドレス、IP アドレス、個人のフォルダーが除去されます。

## AI ツールとの連携 (読み取り専用)

- **常に最新。** フィードと概要は、アラートタブの更新ごと、フィードの読み取りごと、各サイクルごとに書き直されるため、ページと一致します (以前は 1 サイクル遅れていました)。`ALERTS_BRIEF.md` には `Updated:` (お使いのタイムゾーンと UTC) と機械向けの行 `updated_epoch:` があり、`GET /api/ai/brief?fmt=json` は `updated`、`updated_local`、`age_seconds` を追加します。
- **なぜ赤いのか。** `ai_alerts.diagnose.enabled` (既定はオフ。新しい赤い実行のジョブ一覧とログの末尾を GitHub から読み取ります。読み取り専用の呼び出しですが割り当てに計上されます) をオンにすると、各アラートは `diagnosis` を持ちます。最初に失敗したステップと関連する約 10 行 (`ai_alerts.diagnose.log_lines`) で、シークレットは除去され `ai_alerts.diagnose.max_bytes` 以下に収まります。1 サイクルに読む実行は最大 `max_per_cycle` 件で、各実行は 1 回だけです。インフラのエラーを示すログのアラートは一時的として扱われます。
- **連鎖。** `ai_alerts.cascade.enabled` (既定はオン。表示のしかたを変えるだけです) では、別のリポジトリが赤いために赤くなったアラート (ログがそれを名指しする、または `ai_alerts.cascade.map` の規則 `{"base-repo": ["client-repo"]}` による) は、概要でそのリポジトリの下に並び (「Also red because of it (fix this one first)」)、フィードでは `origin` を持ちます。
- **ストリーム。** `ai_alerts.stream.enabled` (既定はオフ) をオンにすると、`GET /api/ai/stream[?only=real]` がサーバー送信イベントを送ります。`hello` フレーム (開いている実際のアラート数、先頭の数件、概要の経過時間) と、フィードのイベントごとの `alert` フレームです。`Last-Event-ID` (または `?since=`) で再開できます。読み取り専用で、ページの他の部分と同じアクセス規則に従い (ネットワークモードではヘッダーまたは Cookie のアクセストークン)、`stream.max_clients` と `stream.max_seconds` で制限されます。
- **センチネルのパネル。** センチネルタブのパネル A1..A13 と 2 つ目のセンチネル(issue とプルリクエスト)もデータとして取得できます。`GET /api/sentinel/panels[?lang=xx]`(読み取り専用、ページと同じアクセス規則)は、パネルごとにレベル(`bad` = 対応する、`warn` = 注意して見る)、1 行の要約、対応すべき行(リポジトリとリンク付き)を返し、MCP ツール `sentinel_panels` も同じ内容を返します。`bad` または `warn` のパネルの行はフィードのアラート(クラス `real` または `watch`、フィールド `panel`)にもなるため、ストリーム、フック、`alerts_open`、ブリーフの「N 件の実アラート」カウンターに含まれ、ブリーフには専用サイズ上限付きの「Sentinel panels」セクションが入ります(CI アラートを押し出しません)。A2 の赤いワークフローは既にアラートなので重複しません。
- **MCP ツール。** `alerts_open` (経過時間・診断・発生元つきの未解決アラート)、`alert_diagnose(id)` (保存済みの診断、または読み取り専用の `gh` 呼び出しによるログの読み取り)、`--allow-ack` のときだけ `alert_ack(id)`。AI ツールが接続すると、サーバーは `instructions` と通知で実際のアラートの件数を伝えます。
- **連携スクリプト。** `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user]` (`status`、`uninstall` もあり、`--dry-run` は変更内容を表示) は、ツールのフック設定に `ai_hook.py` を追加します。SessionStart と UserPromptSubmit は、実際のアラートが開いているときに概要をセッションに加えます。Stop はターンの終了前に AI へ確認を促しますが、`ai_alerts.client_hook.block_on_stop` (既定はオフ) のときだけで、`cooldown_minutes` ごとに最大 1 回です。設定ファイルはマージされ (他のフックは残ります)、コピーが保存され (直近 3 つ)、有効な JSON でないファイルは触らずに拒否され、書き込まれる内容はすべて純粋な ASCII です。既定の対象は、ツール固有の隠しフォルダー内の `settings.local.json` (project) または `settings.json` (user) に、`--cursor` は `.cursor/hooks.json` に書きます (ベストエフォート。フック形式は変わる可能性があります)。`--generic` は何も書かずにコマンドを表示します。スクリプトに必要なのは Python だけで、値は `ai_alerts.client_hook` から読みます。
- **AI は接続中か。** `ai_alerts.heartbeat.enabled` をオンにすると、小さなローカルファイル `ai_heartbeat.json` にストリーム・MCP サーバー・連携スクリプト・エンドポイントによる最後の読み取りが記録され、下部のバーに `window_minutes` の間「AI: mcp、3 分前」(または「接続なし」) と表示されます。何も外部に送りません。
- **非公開ファイル。** フィード、概要、ハートビート、その他のモニターの状態ファイルはモード 0600 で作成されます (モニターが作るフォルダーは 0700)。Windows ではプログラムがモードを強制できません。フォルダーは親フォルダーの権限を継承するため、モニターのフォルダーは自分のプロファイル内に置いてください。
