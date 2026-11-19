<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](AI_CONNECTION_por.md)

# AI ツールを接続する

モニターは、AI ツール(AI コーディングアシスタント、スクリプト、ファイルやアドレスを読めるもの何でも)に、**ページが伝えるすべて**を知らせられます。これにより AI は、失敗や保留中の作業に、あなたと同じ速さで反応できます。モニター自身は GitHub に書き込みません。伝えるだけで、AI が何をするかはあなたと AI ツールが決めます。

## AI が見るもの
ページと同じ**シグナル**の一つのインベントリです。「今」タブとそのタイル、アラート、リポジトリ、センチネルのパネル A1..A13 と 2 つ目のセンチネル(issue とプルリクエスト)、クォータ、接続、モニターの健全性。各シグナルにはレベル(`act` = 誰かが対応する、`watch` = 注意して見る、`info`)、要約、リポジトリ・リンク・経過時間・次の手順を持つ行があります。ブリーフは 3 つのブロック(**今やること**、**保留**、**モニターの健全性**)と「対応すべきシグナル」の数で構成されます。

| | Lite | 完全版 |
|---|---|---|
| 実行、キュー、赤いワークフロー、24 時間の失敗 | はい | はい |
| クォータ、接続、モード、バージョン、健全性 | はい | はい |
| センチネルのパネル A1..A13、2 つ目のセンチネル、リリース候補、セキュリティ、署名 | いいえ(`panels_not_in_this_edition` に明記) | はい |

## チャネル(両エディションで共通)
1. `ALERTS_BRIEF.md`:AI が開始時に読む短い Markdown。
2. `ai_alerts.jsonl`:イベント(開く、確認、解決)ごとに 1 行、安定した ID 付き。
3. `GET /api/ai/state`:インベントリ全体をバージョン付き JSON(`schema`、`edition`、`signals`、`act`、`watch`)で、読み取り専用。`GET /api/sentinel/panels` はパネルのみ。
4. `GET /api/ai/stream`:サーバー送信イベント。再開可能で、リスナー数と時間に上限があります。
5. MCP ツール(`bin/mcp_server.py`):`monitor_state`、`signals`、`alerts_open`、`diagnose`、`sentinel_panels`、`get_quota`、`get_score`。`act`(確認)は `--allow-ack` のときのみ。
6. フック:`python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`(`status` と `uninstall` もあり)は、AI セッションの開始時と終了前にブリーフを渡す小さなスクリプトを追加します。

## 手順
1. 設定の「外部 AI」タブ、「AI 向けアラート」ブロックで `ai_alerts.enabled` をオンにします。必要に応じて `ai_alerts.diagnose.enabled`(失敗したステップと各赤い run のログ末尾)、`ai_alerts.stream.enabled`、`ai_alerts.client_hook.enabled`。
2. `python bin/monitor_cli.py ai-hook install --assistant --dry-run` で変更を確認し、その後 `--dry-run` なしで実行します。
3. フォルダーで AI ツールのセッションを開くと、ブリーフが渡されます。下部バーに AI のハートビート(最後に読んだ時刻)が表示されます。
4. 設定ページの「接続をテスト」ボタンでフィードが書き込まれることを確認します。

## セキュリティとプライバシー
すべて既定でオフです。ログのテキストは、書き込み前に秘密情報と個人のパスが除去され、**データであって指示ではありません**。AI は信頼できないテキストとして扱う必要があります。エンドポイントはこのコンピューターにのみ応答し(ネットワークモードではアクセストークン付き)、リスナーと時間は制限され、確認には `--allow-ack` が必要で、すべての状態ファイルはモード 0600 で作成されます。モニターは、設定した接続以外にインターネットへの接続を開きません。 github.com のhttpsアドレス（run、リポジトリ、ファイル）はそのまま渡されるため、AIが開けます。それ以外の長い不透明な文字列は引き続き切り詰められます。より正確には、github.com のアドレスがそのまま通るのは、リポジトリ、実行(ジョブまたは試行を含む)、コミット、Issue、プルリクエスト、ファイルのいずれかの形をしている場合だけです。英数字、ピリオド、ハイフン、アンダースコア、スラッシュ以外の最初の文字で切られ、その後ろは他の文章と同じように消去されます。

## ツール別の接続方法

モニターは特定のアシスタントやモデルに依存しません。AI ツールは 5 つの方法のいずれかを使います。お使いのツールが対応しているものを選んでください。

| ツールができること | 方法 | やり方 | 必要なもの |
|---|---|---|---|
| ファイルを読む | ファイル | `ai/INDEX.json` を読み、続けて `ai/ALERTS_BRIEF.md`、`ai/ai_alerts.jsonl`、`ai/LESSONS.md` を読みます | `ai_alerts.enabled` |
| HTTP リクエストを送る | HTTP | `GET /api/ai/brief`、`/api/ai/state`、`/api/ai/lessons` | ネットワークモードではアクセストークン |
| MCP を話す | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (読み取り専用。書き込める少量のために `--allow-ack`、`--allow-lessons`) | そのコマンドを指すツールの MCP 設定 |
| 接続を開いたままにする | ストリーム | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| コマンドを実行する | コマンドライン | `python bin/monitor_cli.py alerts`、`lessons brief --repo 名前`、 `briefs show TAB`、`ai doctor`、`ai-hook install` | 同じコンピューター上の Python |

AI 向けの指示は 2 つのスキルです。`monitor_cli.py install-skill external --dest フォルダー` は、ツールがスキルやルールを読み込むフォルダーにコピーします。Markdown ファイルを読めるツールなら使え、本文は特定のアシスタント名を挙げません。スキルはモニターに同梱され、同じバージョンです。`GET /api/skills` は `monitor_version` を返し、`monitor_cli.py --version` が表示します。モニターを更新したら、空のフォルダーに再インストールするか、古いコピーを削除してください (編集したファイルは上書きされません)。

## トラブルシューティング
- *ブリーフが古い*:ページが動作している必要があります(フィードは更新ごとに追従)。バーのハートビートを確認してください。
- *フックが動かない*:`ai-hook status` でインストール先を確認します。ツールによってはプロジェクトフォルダーのフックしか読みません。
- *何も書き込まれない*:`ai_alerts.enabled` がオフか、クォータが尽きています(ブリーフの「モニターの健全性」に記載)。

## 設定
`ai_alerts.enabled`、`ai_alerts.folder`、`ai_alerts.brief_max_bytes`、`ai_alerts.diagnose.*`、`ai_alerts.cascade.enabled`、`ai_alerts.stream.*`、`ai_alerts.heartbeat.*`、`ai_alerts.client_hook.*`。関連:`sound.enabled`、`display.blink_red_tiles`。[SETTINGS_jpn.md](SETTINGS_jpn.md) と [AI_ALERTS_jpn.md](AI_ALERTS_jpn.md) を参照してください。

GitHub のクォータは、モニター、AI ツール、アカウントのその他すべてのツールで共有されます。モニターが枯渇しないように:設定の「クォータ」タブ、GitHub App(`github_app.enabled`)、読み取り用の 2 つ目の読み取り専用アカウント(`extra_reader.enabled`、`extra_reader.file`:トークンファイルのパスのみ)、中央パネル(`central.source`)、節約モード(`modes.auto_low`)。状態とブリーフは、クォータが尽きたときと他のツールの消費量を伝えます。[QUOTA_jpn.md](QUOTA_jpn.md) を参照してください。

## 外部 AI へのアクティブな通知(任意、既定ではオフ)

AI が読むフィード(`ALERTS_BRIEF.md`、ストリーム、MCP サーバー)とは別に、新しい本物のアラートが開いたとき、モニターから外部 AI に**知らせる**ことができます。設定の「AI」タブにある `ai_notify` ブロックで、すべてのスイッチはこのコンピューターからのみ変更できます。

- `ai_notify.enabled`(オフ)。オフの間は何も送られません。
- **プロバイダーごとの初回確認**:プロバイダーは AI ブロック(`ai.provider`)のものです。その名前を `ai_notify.confirmed_provider` に入力するまで何も送信されません。プロバイダーを変えたら再度確認します。送信コマンド(下記)の場合は `command` と入力します。
- **固定リストの伏せ字済みの項目のみ**:重大度、クラス、リポジトリ、ワークフロー、結論、連続回数、原因、次の手順、リンク。いずれもフィードと同様に整えられます(トークン、キー、メールアドレス、IP アドレス、個人フォルダーを除去)。ログ、診断、アラートのその他の内容は外に出ません。
- **上限**:`ai_notify.max_calls_per_hour`(4)と、`ai_notify.max_cost_per_hour_cents` および `ai_notify.cost_per_call_cents`(契約プランの価格はモニターには分からないため、申告するコスト)。呼び出しは実行前に数えられるので、失敗するプロバイダーも上限を消費します。
- **環境変数の名前によるキー**:モニターは `ai.api_key_env` で指定した変数を読みます。キーは保存・記録されず、プロバイダー以外には送られません。
- **AI は決してアクションを実行しません**:回答は切り詰められ、リンクは無効化され、フィードの隣の `ai_notify.jsonl` に書かれるだけです。コマンドとして読まれることはなく、アシスタントのアクション(`ai.actions.*`)にもここからは到達できません。
- **送信コマンドという変形**:`ai_notify.command` (設定ファイルのみ。設定ページからは変更できません) は絶対パスで 1 つのファイルを指定します。シェルも引数もなしで起動され、同じ伏せ字の JSON を標準入力で受け取ります。

通知は専用のスレッドから送られるため、遅いプロバイダーがサイクルを止めることはありません。

## アシスタント(任意、既定ではオフ)

アラートタブには、設定済みのAIがモニターのデータから答える定型の質問パネルを表示できます:「このアラートを説明」「状況を要約」「ここが遅い理由」。既定ではオフ(`ai.assistant.enabled`)で、AIプロバイダー(`ai.provider`、既定はなし)が必要です。読み取りだけを行います。ツールは4つ(`status`、`alerts`、`runs`、`score`。固定の一覧で、`ai.assistant.tools` で絞れます)、1つの質問につき最大 `ai.assistant.max_tool_calls` 回の読み取り、書き込みやGitHubへ届くツールはなく、自由なチャットもありません。回答には常に参照元(読み取ったID)、送信量(`ai.assistant.max_context`)、その日の呼び出し数が表示され、すべての呼び出しはAI共通の1日の予算(`ai.daily_limit` とモデルごとの予算)を消費します。リポジトリに書かれたもの(タイトル、ワークフロー名)は `ai.untrusted_text_max` に切り詰められ、秘密を除去し、その要求ごとの語を含む目印の間のデータとして渡され、指示としては扱われません。閲覧者も質問でき、各質問は操作ログに記録されます(操作のみで、本文は記録しません)。ルート: `GET /api/assistant`(内容と上限)と、`action`(`explain_alert`、`summarize_week`、`why_slow`)および操作に応じて `alert` または `repo` を指定する `POST /api/assistant/ask`。どちらもオフの間は404を返し、Lite版には存在しません。

`ai.similar.enabled` をオンにすると(既定ではオフ)、「このアラートを説明」は似たアラートを最大 `ai.similar.max` 件まで一覧にし、「同じことが別のリポジトリで既にあった」と答えに書けるようにします。未解決のアラートとフィードが覚えている解決済みのアラートの中から、単語の単純な比較(アラートのコード、ワークフロー、タイトルと原因の単語)で探します。モデルも埋め込みも使わず、このアカウントのデータだけを使い、同じデータなら同じ順序になり、それぞれIDで示されます。

アシスタントには5つの固定質問があり、すべて読み取り専用です。「このアラートを説明」(`explain_alert`)、「状況を要約」(`summarize_week`)、「ここが遅い理由」(`why_slow`)、「リポジトリの状況」(`explain_repo`: 実行と未解決のアラート)、「最初にやること」(`prioritize`: 未解決のアラート、状態、スコアをIDつきで順位付け)です。同じ4つのツール、同じ上限、同じ1日の予算を使います。自由チャットは引き続きありません。

## AIの隔離モード(任意、既定ではオフ)

`ai.airgapped` をオンにすると、AIはこのコンピューター上のモデル、または `ai.airgap_hosts` に列挙した自分のネットワークのプライベートアドレス(たとえば `192.168.1.20` のOllamaやllama.cppのサーバー)のモデルとだけ通信します。インターネット上のアドレスやCopilot CLIを含むクラウドサービスは、接続を開く前に拒否されるため、ソケットは外へ出ません。モデル一覧、モデルのテスト、AIドクター、フォールバックの連鎖、アシスタント、要約のすべてがこれに従い、フォールバックがクラウドのモデルへ移ることはありません。全体の `airgapped` スイッチでもオンになります。公開アドレスはリストにあっても拒否され、この設定はモニターのあるコンピューターからのみ変更でき、ネットワーク越しには変更できません。モードがオンの間、AIドクターは `ai_egress` チェックを追加します。`ai.redact.extra_terms` には、モニターが既に隠している秘密に加えて、AIに見せる前に `[hidden]` に置き換える自分の語(サーバーやプロジェクト)を列挙します。

`ai.redact.extra_patterns`(オフ・空)は、AIに決して見せてはならないものの独自パターンを並べます。1行に1つ、各パターンは単語全体を表し、ワイルドカードは3つだけです。`*`(任意の文字列)、`?`(1文字)、`#`(1桁の数字)。例: `deploy-*`、`*.corp-name`。正規表現ではありません。グループ・選択・繰り返しがないため、パターンでモニターが固まることはありません。パターンは3〜80文字(通常の文字3文字以上、星は最大4つ)、単語は2000文字まで読み、1つの文章で使える手順は固定で、超えた場合は残りの文章を隠します(開いたままにはしません)。パターンはモデルに届くすべての文章(アクティブ通知を含む)に適用され、モニターがすでに隠している秘密に加わります。

`ai.prompt_log.enabled`(オフ)は、AIに何を尋ねたかのローカル記録を残します。オンにすると、モデルに送ったすべての質問とその回答が、秘密や隠す単語を除去し固定サイズに切り詰めた状態で、ログフォルダーの `ai_prompts.jsonl` に追記されます(`GET /api/ai/prompts` で管理者が表示、`POST /api/ai/prompts/clear` で空にします)。システムプロンプトは保存されず、キャッシュからの回答は書き込まれず、失敗した呼び出しは回答なしで書き込まれ、最新の `ai.prompt_log.keep` 行が保持されます。このファイルはバックアップ、zip、AIツールが読むファイルには含まれません。

`config/ai_models.json` は手で管理できる表です(書くまで存在しません)。`models` はプロバイダーが教えてくれない数値を持つ行 `{provider, model, context, in_per_mtok, out_per_mtok, tools, daily_limit}` の一覧、`retired` はもう存在しないモデルの一覧(名前、または `{model, use, note}`)です。このファイルの数値はプロバイダーが示した値より優先され、画面で入力した値より後になり、画面にはファイル由来と表示されます。廃止として載せたモデルは、モデルのライブ一覧がオフでもフォールバックチェーンでスキップされ、AIドクターは代わりに使うモデルを添えて `model_retired` の確認を追加します。間違った行や数値は除外され、他は何も変わりません。

設定ページの AI の下にある「プロンプトの記録」カードは、その記録の最新 20 件(時刻、種類、モデル、開くと質問と回答)を表示し、ボタンで消去できます。読み取りと消去ができるのはこのコンピューターの管理者だけで、記録がオフのときはそう表示します。モデルの表には「出どころ」列があり、数値がページ、ファイル `config/ai_models.json`、プロバイダーのどれから来たかを示します。

## プロバイダーのモデル

モデル名は自由入力ですが、モニターはプロバイダーからモデル一覧を読み取り、名前を照合できます。モデルやバージョンは頻繁に変わるため、モニターはモデル一覧を同梱しません。プリセットの例は古くなっている場合があります。

- **一覧。** 設定の「外部 AI」タブ、「モデルとモデルごとのデータ」ブロック: 「プロバイダーのモデルを読み込む」は、読み取り専用のリクエスト 1 回で一覧を読み取ります (OpenAI 形式サーバーの `/models`、Anthropic API の同等の一覧、Ollama の `/api/tags`)。キーはヘッダーで送られ、環境変数から読み取られ、保存されません。一覧を検索し、「このモデルを使う」で選びます。一覧は保存され、`ai.catalog.ttl_minutes` と `ai.catalog.max_requests_per_day` で制限されます。`ai.catalog.enabled` をオン (既定はオフ) にすると、設定したモデルが一覧から消えた (廃止または名称変更) ときにモニターが警告します。オフの間は、あなたが操作したときだけ読み取ります。
- **モデルごとのデータ。** コンテキストウィンドウ、100 万トークンあたりの入力・出力価格、ツール対応の有無は、プロバイダーが返した内容だけで埋められます。返されないものは「不明」のままです (数値を作ることはありません)。自分の値を入力することもでき、その値が優先されます。`ai.catalog.fit_context` をオン (既定はオフ) にすると、コンテキストウィンドウが分かっている場合に入力の上限を合わせます。
- **モデルのテスト。** 「このモデルをテスト」または `monitor_cli.py ai test --provider 名前 --model 名前` は、合成の障害 (リポジトリのデータは使いません) についてモデルに尋ね、遅延、トークン数、推定コスト、回答例を表示します。1 日の上限の 1 回分として数えられ、結果 (「テスト済み」とローカル日付) は表に保存されます。
- **コマンド。** `monitor_cli.py ai models [--refresh]` はモデルとデータを表示します。`ai doctor` は AI が応答しない理由 (キーの変数が未設定、不明なモデル、クォータ、ネットワーク) を説明し、キーは表示しません。
- **ルート。** `GET /api/ai/models` (保存済みの一覧、確認、表。読み取り専用) と、このコンピューターからのみ `POST /api/ai/models/refresh`、`POST /api/ai/models/test`、`POST /api/ai/models/data`、`POST /api/ai/doctor`。

## 互換性のあるAI

モニターがすでに通信方式に対応しているホスト型サービスとローカルサーバー(`openai-compatible`、`anthropic`、`ollama`)です。これは推奨ではなく中立の一覧です。初期状態ではどれも有効ではなく、キーは常に、名前を指定した環境変数から読み取られます(設定、ログ、レポート、APIには決して入力・出力されません)。プリセットは、アドレス、その変数名、例のモデルだけを入力します(編集可能。何もダウンロードされず、モデルの重みも同梱されません)。AI設定でプリセットを選び、入力ボタンを押し、確認して保存し、「接続テスト」を押してください。一覧はデータ(`ai_presets.json`)で、`GET /api/ai/presets` から読み取り専用で提供されます。

| 名前 | 種類 | プロバイダー | アドレス | キーの変数 | モデルの例 | プライバシー | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | ホスト型 | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Anthropic | ホスト型 | `anthropic` | `既定のアドレス` | `ANTHROPIC_API_KEY` | — | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Google Gemini | ホスト型 | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| xAI Grok | ホスト型 | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Mistral | ホスト型 | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| DeepSeek | ホスト型 | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Groq | ホスト型 | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| OpenRouter | ホスト型 | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Together AI | ホスト型 | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Fireworks AI | ホスト型 | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Perplexity | ホスト型 | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Cohere | ホスト型 | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Ollama | ローカル | `ollama` | `http://127.0.0.1:11434` | なし(ローカルサーバー) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| LM Studio | ローカル | `openai-compatible` | `http://127.0.0.1:1234/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| llama.cpp server | ローカル | `openai-compatible` | `http://127.0.0.1:8080/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| vLLM | ローカル | `openai-compatible` | `http://127.0.0.1:8000/v1` | なし(ローカルサーバー) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| LocalAI | ローカル | `openai-compatible` | `http://127.0.0.1:8081/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| Jan | ローカル | `openai-compatible` | `http://127.0.0.1:1337/v1` | なし(ローカルサーバー) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
