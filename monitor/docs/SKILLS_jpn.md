<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SKILLS_por.md)

# AI 向けスキル

モニターには2つのスキルが付属しています。AI がモニターとどう連携するかを示す、短い英語のガイドです。パッケージの `skills/` フォルダー、ページ(設定、AI タブ)にあり、1つのコマンドでインストールできます。

## 2つのスキル

- `skills/internal`:モニターに組み込まれた AI 用。ローカル(Ollama、llama.cpp サーバー、LM Studio)でも外部(プロバイダーの API)でも使えます。モニターとは何か、何が見えるか、何を読めるか、決してしてはいけないこと、赤い実行の診断方法、黙るべき場面、レッスンの使い方と提案の仕方を示します。`ai.skill` がオンのとき、その核(`SKILL.md`)が `ai.skill_max_chars` で切り詰められて、その AI のすべてのプロンプトに加えられます。
- `skills/external`:外部からモニターとあらゆる方向でやり取りする AI 用。読む(`/api/ai/*`、`ai/` のファイル)、知らされる(ストリーム、または数分ごとの概要)、書く(確認応答、レッスン、失敗、通知設定。権限に応じて)、モニターとセッションの連携、プッシュ前の概要、そして自己学習サイクル全体を扱います。コマンドラインの AI、HTTP やファイルだけの AI、MCP の AI、ストリームの AI をカバーします。

## 中身

各スキルは短い `SKILL.md`(核)と、必要なときだけ読む `references/` フォルダーで構成されるため、コンテキストの小さいモデルは核だけを使えます。ステップごとのシナリオ(本物の赤、一時的な赤、クォータ不足、劣化したモニター、繰り返す失敗、新しいレッスン、ネットワークなし、複数画面)、自己学習サイクル、プロバイダーとその制限、セキュリティ(ログからのプロンプトインジェクション、シークレット、最小権限、AI が書いたものの監査)、そしてコードから生成された参照資料です。

## 漏れがないこと

参照資料(`api.md`、`cli.md`、`settings.md`、`files.md`、`roles.md`、`tabs.md`)と `skills/COVERAGE.md` は `python tools/make_skill_refs.py` によってコードから生成されます。各エンドポイントとそれを呼べる最小のロール、各コマンドとオプション、各設定と既定値、モニターが書く各ファイル、各ロール、各タブです。テストが同じ一覧をコードから読み取り、スキルに載っていないものがあれば失敗します。そのため、新しいエンドポイント、コマンド、設定、ファイルは AI に説明されないまま現れることはありません(説明が書かれるまでジェネレーターも止まります)。

## インストール

AI ツールがスキルを読み込むフォルダーにスキルをコピーします:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## インストーラーの安全性

指定したフォルダーの中に `github-actions-monitor-internal` または `github-actions-monitor-external` だけを書き込みます。パッケージのものと内容が異なるファイルは決して上書きせず(あなたのファイルを残し、どれかを知らせます)、D: ドライブとネットワークパスは拒否します。2回目の実行では何も変わりません。

## ページと HTTP

設定の AI タブにある **AI 向けスキル** ブロックで、各スキルをコピー(スキルの核)またはダウンロード(参照資料を含むスキル全体を1ファイルで)できます。`GET /api/skills` で一覧、`GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` でテキストを取得できます。読み取り専用です。

## 設定

`ai.skill`(オン)と `ai.skill_max_chars`(3000。小さなローカルモデルは1500)。外部から失敗を登録するには `POST /api/ai/failures` を使い、レッスンの書き込みと同じく `lessons.allow_write` と管理者が必要です。
