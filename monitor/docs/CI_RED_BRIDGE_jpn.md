<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# モニターからダッシュボードへ：`ci_red.json`

モニターが何を書き出すのか、どうエクスポートするのか、そしてファイルの読み手に何が必要かを説明します。モニターは GitHub を読み取ってローカルのファイルを書くだけです。プッシュもコミットもせず、自分から何かをクローズすることもありません。

## モニターが書き出すもの

`bin/actions_monitor.py` の隣にある `ci_red.json` で、センチネルの各パスの後に更新されます（スキーマ 2）。

| フィールド | 意味 |
|---|---|
| `schema` | `2`。フィールドは追加されるだけで、名前が変更されることはありません。 |
| `generated` | そのパスの UTC 時刻。 |
| `tool_version` | ファイルを書き出したツールのバージョン。 |
| `complete` | そのパスで監視対象のすべてのリポジトリを読み取れた場合は `true`。読み込み中、API のクォータが不足した場合、またはクローンが欠けている場合は `false`。`true` になるまでは、赤のリポジトリの一覧や署名キューに基づいて動作しないでください。 |
| `red_repos` / `pending_sign_repos` | 件数。 |
| `repos.<NAME>.ecosystem` | `armor`、`urtc`、`hydra`、`eh3d`、または `other`。 |
| `repos.<NAME>.red[]` | デフォルトブランチで最後に完了した実行が失敗したワークフローごとに 1 件：`workflow`、`conclusion`、`since`、`streak`、`url`。 |
| `repos.<NAME>.pending_sign[]` と `pending_sign_hours` | ビルド済みでまだ署名されていないリリースと、最も古いものの経過時間。 |

## エクスポートの方法

```
py -3 bin/read_report.py --export-status DIR          # ci_status_public.json + .md、公開してよいものだけ
py -3 bin/read_report.py --export-sign-queue FILE     # 署名キュー
```

どちらも `127.0.0.1` で動作中のモニターを読み取ります（GitHub のクォータは消費しません）。スナップショットの読み込み中は書き出しを拒否して理由を示し、その場合の終了コードは 0 以外になります。

## 読み手（ダッシュボードのジェネレーター）に必要なこと

1. `schema` を読み、`>= 2` の値を受け入れ、未知のフィールドは無視する。
2. `complete` を読み、`false` のときは置き換えずに直前の完全なエクスポートを保持する。
3. 古いファイルがすぐ分かるよう、数値の隣に `generated` を表示する。
4. `repos.<NAME>.red[].url` をリンクとして使い、決して組み立て直さない。

## モニターが行わないこと

ファイルの公開、プロフィールリポジトリへのプッシュ、ワークフローへの変更は行いません。エクスポートをダッシュボードへ届けるのは、オーナーの作業（またはエクスポートされたファイルを読み取る、プロフィールリポジトリのワークフロー）です。

## プロフィールのダッシュボード(利用側の取り決め)

プロフィールリポジトリのステータスダッシュボードは、同じ文書を 2 通りで読めます。実行中のモニターから(`GET /api/outputs/dashboard.json`。`outputs.dashboard.enabled` をオンにするまで無効で、このコンピューターのみ)、または `py -3 bin/read_report.py --export-status DIR` が書くファイルから(赤のワークフローのみで、署名側は含みません)。ダッシュボードが前提にしてよいこと(このリポジトリのテストで確認済み):

1. `schema` は `2` で、フィールドは追加のみ。
2. 配信される文書は `ci_red.json` と完全に同じ。
3. `complete: false` は、最後の完全な状態を保つという意味。
4. 公開エクスポートのキーは `schema`、`generated`、`tool_version`、`complete`、`red_repos`、`red` のみで、署名状態は含まれません。

モニターがファイルをプロフィールリポジトリへ push することはありません。そこへ運ぶのは所有者の作業です。
