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
