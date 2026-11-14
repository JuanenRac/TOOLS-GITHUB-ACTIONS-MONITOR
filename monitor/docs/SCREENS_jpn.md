<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SCREENS_por.md)

# 画面・サイズ・向き

ページはウィンドウの大きさ（スマートフォンから4Kまで、縦でも横でも）に合わせて変わり、1台のモニターが複数の画面を担当でき、それぞれ選んだタブを表示します。ポーリングは重複しません。すべての画面が同じ状態を読みます。

## アドレス

- `/` - ページ全体。
- `/screen/1`、`/screen/2`、`/screen/3` - その画面に設定したタブ（`ui.screen1_tabs` など）。それぞれを専用のモニターやテレビのウィンドウで開きます。
- `?orient=portrait` または `?orient=landscape` で1つのウィンドウのレイアウトを固定。`?tabs=now,charts` と `?rotate=30` で1つのウィンドウのタブと切り替え秒数を指定します。

## 設定

| 設定 | 内容 |
|---|---|
| `ui.orientation` | auto はウィンドウに従い、portrait はパネルを1列に積み、landscape は左右に並べたままにします。 |
| `ui.rotate_seconds` | 0 = オフ。複数のタブがある画面で、タブを切り替える秒数。 |
| `ui.screen1_tabs` | /screen/1 のタブ（カンマ区切り）：now, al, sent, charts, repos, hist, cfg。空 = すべて。 |
| `ui.screen1_orientation` | /screen/1 だけの auto、portrait、landscape。 |
| `ui.screen2_tabs` | /screen/2 のタブ。 |
| `ui.screen2_orientation` | /screen/2 の向き。 |
| `ui.screen3_tabs` | /screen/3 のタブ。 |
| `ui.screen3_orientation` | /screen/3 の向き。 |
| `ui.now_sort` | 並び順を選んでいない人向けの「今起きていること」の順序: ecosystem、severity、age、newest、repo、event、state。 |

## 一覧の並び順

最初のタブの **今起きていること** は、既定ではエコシステムごとに見出しを付けて並びます。セクション上のリストで変更できます: エコシステム、重大度(停止中、失敗したジョブがあるもの、実行中、待機中の順)、経過時間(実行時間が長い順)、新しい順、リポジトリ、トリガー(push、pull_request、schedule など)、状態(実行中を待機中より先に)。選択は人ごとに記憶されます。チームモードではサーバーがユーザーと一緒に保存し(`GET` と `POST /api/auth/me/view`、別のブラウザーでも引き継がれます)、それ以外はこのブラウザーが保存します。誰も選ばない間は設定ファイルの `ui.now_sort` が使われます(未設定または不正ならエコシステム)。

## テスト済みサイズ

ブラウザテストが各サイズでページを開き、すべてのタブを巡回して、横スクロールや枠からはみ出す文字があれば失敗します。幅2400 px以上では文字が大きく（3200 px以上ではさらに大きく）なり、レイアウトを引き伸ばしません。幅より高いウィンドウではパネルを縦に積みます。

| サイズ | 種類 |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## 2〜3画面のデスク向けレシピ

1. モニターを実行しているコンピューターで、`ui.screen1_tabs` を `now,al`、`ui.screen2_tabs` を `charts,repos` にし、回転したモニターなら `ui.screen2_orientation` を `portrait` にします。
2. 1台目のモニターのウィンドウで `http://このコンピューター:8765/screen/1`、2台目で `/screen/2` を開き、F11 で全画面にします。別のコンピューターからはネットワークモードとアクセストークンを使います。
3. 誰も触れない壁面の画面には複数のタブを割り当て、`ui.rotate_seconds` を 20〜30 にします。

## 画像

「現在」タブを4つのサイズで表示した例です(架空のデータ。4K、21:9モニター、回転したモニター、スマートフォン):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ウルトラワイド 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![回転 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![スマートフォン 390x844](../../docs/screenshots/web_size_phone_light.png)
