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

## 互換性のあるAI

モニターがすでに通信方式に対応しているホスト型サービスとローカルサーバー(`openai-compatible`、`anthropic`、`ollama`)です。これは推奨ではなく中立の一覧です。初期状態ではどれも有効ではなく、キーは常に、名前を指定した環境変数から読み取られます(設定、ログ、レポート、APIには決して入力・出力されません)。プリセットは、アドレス、その変数名、例のモデルだけを入力します(編集可能。何もダウンロードされず、モデルの重みも同梱されません)。AI設定でプリセットを選び、入力ボタンを押し、確認して保存し、「接続テスト」を押してください。一覧はデータ(`ai_presets.json`)で、`GET /api/ai/presets` から読み取り専用で提供されます。

| 名前 | 種類 | プロバイダー | アドレス | キーの変数 | モデルの例 | プライバシー | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | ホスト型 | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Anthropic | ホスト型 | `anthropic` | `既定のアドレス` | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Google Gemini | ホスト型 | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| xAI Grok | ホスト型 | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Mistral | ホスト型 | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| DeepSeek | ホスト型 | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-chat` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Groq | ホスト型 | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| OpenRouter | ホスト型 | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
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
