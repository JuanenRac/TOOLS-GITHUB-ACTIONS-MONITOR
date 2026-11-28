<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](PLUGINS_por.md)

# プラグインとシークレット保管庫

プラグインはモニターを変えずに確認項目を追加します。すべて既定でオフです。Lite 版にプラグインはありません。

## 有効化

`plugins.enabled` をオンにし、次に使うプラグインをオンにします。設定 > 拡張機能に権限・鍵・状態・分離の内容が表示されます。検出結果は発生元 `plugin` の通知で、先頭にプラグイン名が付きます。

## 公式プラグイン

署名済みリリースに含まれ、モニター内の専用スレッドで動きます。

- **discussions**（`plugins.official.discussions.enabled`）: `plugins.official.discussions.days` 日を超えてコメントのないディスカッション。Issue と PR は Collab の担当です。
- **packages**（`plugins.official.packages.enabled`）: `plugins.official.packages.max_versions` を超える版を持つ container・npm パッケージ。`read:packages` が必要です。リリースは delivery 監視の担当です。

## 第三者のプラグイン

`plugins.third_party.enabled` をオンにします。パッケージは `plugin.json` を含む zip と、作者が自分のツールで作る分離署名 `NAME.zip.ed25519.sig` です。**あなたの**鍵束の `plugins` 範囲の鍵で署名され、その鍵のフィンガープリントを繰り返し指定した場合のみインストールされ、オフの状態で入ります。実行のたびに署名を再確認し、鍵の失効やファイル変更があれば一時停止します。

**署名は安全を意味しません。** マニフェストはサンドボックスではありません。

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## 分離される内容

| OS | 別プロセス・空の環境・トークンなし | ネットワークなし | メモリと子プロセス |
|---|---|---|---|
| Linux | はい | ユーザー名前空間が使える場合は可、そうでなければ**ネットワーク分離なし** | メモリと CPU の上限 |
| Windows | はい | **不可**: **ネットワーク分離なし** | ジョブオブジェクト: メモリ上限、子プロセス不可 |
| macOS | はい | **不可**: **ネットワーク分離なし** | CPU 上限。メモリは保証しません |

どの OS でもファイルは隠されません。プラグインはあなたのユーザーで動きます。`plugins.worker.platforms_ok` が空なら第三者プラグインは動きません。GitHub の読み取りはモニター経由で、監視中リポジトリに対するマニフェストの `get_paths` のみ許可します。`plugins.worker.timeout_s`、`max_output_kb`、`memory_mb` が各実行を制限します。`security.read_only_strict` または `security.egress_policy` で制限している間は、その制限を別のプログラムの中で強制できません。そのため他者のプラグインは、プロセスが本当にネットワークを持たない場合(ユーザー名前空間のある Linux)にだけ実行されます。それ以外は実行されず、理由は `restricted` になります。

## 信頼しない出力と状態

題名は整えて切り詰め（`plugins.alert_title_max`）、github.com へのリンクだけを残し、第三者プラグインは重大通知を出せません。プラグインの文章はデータであり AI への指示ではありません。`plugins.breaker.failures` 回連続で失敗すると再開するまで一時停止します。停止や一部失敗は「問題なし」ではありません。doctor の `plugins` 項目と `plugin audit` が失効・変更を報告します。

## 作者向け

契約はバージョン 1（`api_compat`）です。`run(ctx)` は `{"alerts": [{id, code, level, repo, url, title}]}` を返します。`ctx` は `owner`、`now`、`options`、`repos()`、`get(path)`、`discussions()` を提供し、それぞれ権限（`repos.list`、`gh.get`、`graphql.discussions`）が必要です。`init` はテスト付きのひな形を作ります。モニターは署名しません。

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## ルートと pip パッケージ

ルート（管理者。変更はこのコンピューターからのみ）: `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`。`plugins.entry_points` をオンにすると、グループ `gha_monitor.plugins` を宣言し `*.plugin.zip` を持つ pip パッケージを一覧します。コードは読み込まず、zip を同じ手順でインストールします。

## 別のプログラムから GitHub トークンを読む

`secrets.backend` はトークンをモニターに保存せずに読み取ります（`github_token.enabled` がオンであること）。読み取り専用です。`vault`（HTTP、`secrets.vault.addr`、`path`、`field`、Vault トークンは `token_env` の環境変数。https、http はこの端末のみ）、`sops`（`secrets.sops.file`、`field`。信頼できる端末のみ）、`bitwarden`（`bws`、`secrets.bitwarden.item`）、`aws`・`azure`・`gcp`（各 CLI、`secrets.cloud.ref`）。`secrets.reload_on_rotate` がオンなら `secrets.reload_seconds` ごとに読み直します。疑似サーバーと開発モードの Vault で試験し、実際のクラウドアカウントは未確認です。
