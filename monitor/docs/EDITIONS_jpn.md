<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EDITIONS.md) | [🇪🇸 Español](EDITIONS_spa.md) | [🇫🇷 Français](EDITIONS_fra.md) | [🇮🇹 Italiano](EDITIONS_ita.md) | [🇩🇪 Deutsch](EDITIONS_deu.md) | [🇨🇳 简体中文](EDITIONS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](EDITIONS_por.md)

# 完全版と Lite: 各エディションの内容

一つのパッケージに二つのエディションがあります。**Lite** は実行中の状態、直近 24 時間の失敗、履歴、基本的なグラフだけで、センチネルもネットワークモードも下記モジュールもなく、GitHub には何も書きません。**完全版**はそれ以外のすべてを持ちます。第三のエディションはありません。GitHub に書く機能や外部に出る機能は完全版にあり、オンにするまで無効です。完全版の使い方 (個人、チーム、サービス) には各ガイドがあります。

[LITE](LITE_jpn.md) · [COMPLETE_INDIVIDUAL](COMPLETE_INDIVIDUAL_jpn.md) · [COMPLETE_TEAM](COMPLETE_TEAM_jpn.md) · [COMPLETE_SERVICE](COMPLETE_SERVICE_jpn.md)

## 完全版の追加モジュール

| スイッチ | 初期状態 |
|---|---|
| `plugins.enabled` | オフ |
| `plugins.official.discussions.enabled` | オフ |
| `plugins.official.packages.enabled` | オフ |
| `plugins.third_party.enabled` | オフ |
| `ai.chat.enabled` | オフ |
| `ai.rag.enabled` | オフ |
| `ui.copy_report.enabled` | オン |
| `external_ci.enabled` | オフ |
| `external_ci.jenkins.enabled` | オフ |
| `external_ci.azure.enabled` | オフ |
| `external_ci.alert.enabled` | オン |
| `external_ci.logs.enabled` | オフ |
| `posture.enabled` | オフ |
| `audit_checkpoints.enabled` | オフ |
| `audit_export.enabled` | オフ |
