<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](ACCOUNTS_por.md)

# 複数のアカウント

フル版は、複数の GitHub アカウント（個人または組織）を同時に監視できます。各アカウントは独立したモニターです。別プロセスで、専用のフォルダー、`127.0.0.1` 上の専用ポート、専用の設定、GitHub の枠の専用の読み取りを持ちます。1 つのアカウントのクラッシュ、応答の遅れ、レート制限が他に影響することはありません。lite 版はアカウントが 1 つで、以下のことは何もありません。下のオプションも表示されません。

## 何もする必要がないとき

`accounts/` フォルダーがなければ、モニターはこれまでとまったく同じように動作します。アカウントは 1 つで、ファイルはコードの隣にあります。複数が必要なときだけ読み進めてください。

## アカウントのフォルダー

```
accounts/
  global.json              任意: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   このアカウントの設定（github_owner、repos、センチネルなど）
  org-acme/
    actions_monitor.json
```

アカウントの ID は、フォルダー名になるため、英小文字、数字、`_`、`-`（最大 40 文字）です。それ以外は拒否されます。`enabled_accounts` は `"all"` またはリストで、`default_account` は何も指定されないときに開くアカウントです。`MONITOR_ACCOUNTS_DIR` でフォルダーを移せます。各アカウントはキャッシュ、イベント、分析、センチネルの状態、ログを自分のフォルダーの中に持つため、2 つのアカウントがファイルを共有することはありません。

## 1 つから複数へ移る

```
python actions_monitor.py --migrate-accounts          # コピーされるものを表示するだけで、何も書き込みません
python actions_monitor.py --migrate-accounts --apply  # accounts/default/ にコピーします
python actions_monitor.py --accounts                  # アカウントを一覧表示します
```

元のファイルは決して移動も削除もされません。確認したあとで自分で削除してください。2 回目の実行は拒否されるため、2 つの状態が混ざることはありません。アカウントを追加するには、`github_owner` を指定した `accounts/<id>/actions_monitor.json` を作成します（テンプレート `actions_monitor.example.json` をコピーしてください）。

## 実行

`accounts/` フォルダーがある状態で `python actions_monitor.py` を実行すると、スーパーバイザーが起動します。いつものポート（8765）で動く小さなプロセスで、アカウントごとに 1 つのモニターを起動し、ページとツールに単一のアドレスを提供します。GitHub からは何も読まず、何も書きません。アカウントが停止すると、待ち時間を延ばしながら（2、5、15、30、60、その後 120 秒）再起動し、その間は概要で停止中と表示します。`python actions_monitor.py --account personal` はそのアカウントだけを通常のモニターとして実行します。

## ページ

ページはおなじみのもので、サイドパネルの上部にアカウントの切り替えがあり、**すべてのアカウント** という項目では、アカウントごとに 1 枚のカード（状態、リポジトリ、実行中、失敗中）が表示され、どれでも開けます。各ウィンドウは自分のアカウントとビューを保持します。それらはアドレスから読み取られ、別のウィンドウに上書きされる単一の設定からは読み取られません。

| アドレス | 表示内容 |
|---|---|
| `/?account=org-acme` | そのアカウントのページ |
| `/?account=all` | すべてのアカウントのカード |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | 1 つのパネル |
| `/?chrome=0` | ヘッダーのボタン、タブ、フィルターなし: 壁面や 2 台目のモニター向けの画面 |

複数の画面にするには、ビューごとに 1 つのウィンドウを開きます。たとえば `?view=now&chrome=0`、`?view=alerts&chrome=0`、`?view=live&chrome=0` です。1 つのモニターがすべてに応えるので、枠を二重に消費しません。**ライブ** ビューには、GitHub が最後に送ったイベント、Webhook 受信の状態（オンかオフか、受理・無視・重複・拒否された配信の数。シークレットは決して表示されません）、作業モードの選択が表示されます。

## API

`GET /api/accounts` が概要、`GET /api/accounts/<id>/status` が 1 つのアカウントで、`/api/` 以下のそれ以外のリクエストは `?account=<id>` またはヘッダー `X-Account-Id` で指定したアカウントに送られます（指定がなければ既定のアカウント）。不明なアカウントは 404 です。アクセスのルールは単独のモニターと同じです。ホストとオリジンの同じ検査、ネットワークモードでの同じアクセストークンです。変更のワンタイムトークンは、その変更を送るのと同じアカウントに対して取得しなければなりません。

## すべてに 1 つの Webhook

`POST /api/webhook` は、インストール全体で単一のアドレスです。スーパーバイザーはペイロード内のリポジトリのオーナー（`repository.full_name`）だけを読み、その `github_owner` がそのオーナーであるアカウントへイベントをそのまま渡します。アカウントは自分のシークレットで署名を検証します。誰も監視していないオーナーには応答して無視します。アカウントを自分で選ぶには `?account=<id>` を付けます。

## 限界と正直な注意

- 複数のアカウントは複数のプロセスです。各プロセスが個別に GitHub を読むため、枠は使用するログインで共有されます。カードで確認し、必要ならアカウントごとに `refresh_seconds` や `max_workers` を下げてください。
- 実際のブラウザー、実際の GitHub アカウント、実際の Webhook トンネルが必要な確認はあなたの役目です。テストはアカウントのモニターの代役を使い、GitHub を呼び出すことはありません。
- 今後のバージョンでアカウントを 1 つのプロセスにまとめます。上のフォルダー構成と API は変わりません。
