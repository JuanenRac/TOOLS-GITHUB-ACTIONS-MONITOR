<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](KIOSK_por.md)

# キオスク：テレビや壁面のモニター

キオスクプロファイルは、誰も触れない画面のためのモニターのページです。ヘッダーもタブもなく、大きな文字になり、必要ならハイコントラストや数枚のタブの自動切り替えも使えます。ページがすでに知っているもの（`?screen=`、`?tabs=`、`?rotate=`、`?chrome=0`。[SCREENS_jpn.md](SCREENS_jpn.md) を参照）を再利用し、2つのパラメーターを加えます。GitHub からは何も読まず、何も書き込まず、ページの見た目を決めるだけです。

**既定ではオフ**です。`kiosk.enabled` がオフの間、ページはアドレスの `kiosk=1` を無視するので、どこかからコピーしたリンクで何かが変わることはありません。

## アドレス

`python bin/monitor_cli.py kiosk [プリセット] [--account ID]` が出力します。モニターが動いていなくても使えます。たとえば `kiosk ops` は次を出力します：

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| パラメーター | 意味 |
|---|---|
| `kiosk=1` | プロファイルをオンにします（`kiosk.enabled` がオンのときだけ） |
| `scale=%` | 文字サイズ（100〜400）。範囲外の値は範囲内に収められます |
| `contrast=1` / `contrast=0` | このウィンドウのハイコントラストのオン／オフ（既定は設定 `kiosk.high_contrast`） |
| `safe=PERCENT` | このウィンドウの安全マージン、0〜10（設定 `kiosk.safe_margin_percent` が既定値） |
| `fit=1` / `fit=0` | このウィンドウで文字をウィンドウに合わせて拡大するかどうか（設定 `kiosk.scale_with_window` が既定値） |
| `rotate=SECONDS` | `tabs=` のタブを順に切り替えます（既存のパラメーター。コマンドは切り替えがオンのときだけ追加します） |
| `chrome=0`, `screen=`, `tabs=`, `account=` | 既存のもの |

## プリセット

| プリセット | タブ |
|---|---|
| `ops` | 現在、アラート、グラフ |
| `team` | アラート、チームの健全性 |
| `release` | 現在、リポジトリ、レポート |
| `quiet` | アラートのみ |

## 設定（設定、コマンドライン、キオスク）

| 設定 | 既定 | 意味 |
|---|---|---|
| `kiosk.enabled` | オフ | プロファイルをオンにする |
| `kiosk.font_scale_percent` | 150 | 文字サイズ（100〜400） |
| `kiosk.high_contrast` | オフ | 黒い背景と白い線 |
| `kiosk.rotate_views` | オフ | 複数のタブを持つプリセットは自動でタブを切り替える。オフの場合、画面にはプリセットの最初のタブが表示される |
| `kiosk.rotate_seconds` | 30 | 各タブを表示する時間（5〜600） |
| `screens.version_check_seconds` | 300 | ページが `/api/version` を確認し、モニターが更新または再起動されたときに自動で再読み込みする間隔(0 = 確認しない、最小 30) |
| `kiosk.safe_margin_percent` | 0 | 端を切り取るテレビ（オーバースキャン）のために、ページが各端で空けておく割合（%）。0〜10 |
| `kiosk.scale_with_window` | オフ | 上の文字サイズは、短い辺が 1080 px のウィンドウでの大きさです。オンにするとウィンドウに合わせて大きくなり、4K テレビでもフルHDと同じ見た目になります |
| `screens.show_repo_names` | public | キオスクでのリポジトリ名。壁面画面と同じで、`public` は非公開リポジトリを `private-N` と表示し、その実行のタイトル・ブランチ・ワークフローを省き、`none` はすべて `repo-N` と呼び、`all` はすべて表示する（ページのデータ `/api/data` に適用） |

サイズはページのズームで適用されるため、すべての数値と表が一緒に大きくなります。範囲外の値はエラーではなく、既定値に置き換えられます。
