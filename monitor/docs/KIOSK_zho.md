<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# 展示屏：电视或墙面上的监控器

展示屏配置是为无人操作的屏幕准备的监控器页面：没有页眉，没有标签页，字号更大，需要时还可使用高对比度，并在几个标签页之间轮播。它复用页面已有的功能（`?screen=`、`?tabs=`、`?rotate=`、`?chrome=0`；参见 [SCREENS_zho.md](SCREENS_zho.md)），并增加两个参数。它不从 GitHub 读取任何内容，也不写入任何内容：只决定页面的外观。

它**默认关闭**。`kiosk.enabled` 关闭时，页面会忽略地址中的 `kiosk=1`，因此从别处复制来的链接不会改变任何东西。

## 地址

`python bin/monitor_cli.py kiosk [预设] [--account ID]` 会打印它；不需要监控器正在运行。例如，`kiosk ops` 打印：

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| 参数 | 含义 |
|---|---|
| `kiosk=1` | 打开该配置（仅当 `kiosk.enabled` 打开时） |
| `scale=%` | 字号，100 到 400（超出范围的值会被调整到范围内） |
| `contrast=1` / `contrast=0` | 此窗口的高对比度开或关（默认取设置 `kiosk.high_contrast`） |
| `safe=PERCENT` | 此窗口的安全边距，0 到 10（设置 `kiosk.safe_margin_percent` 是默认值） |
| `fit=1` / `fit=0` | 此窗口的字号是否随窗口增大（设置 `kiosk.scale_with_window` 是默认值） |
| `rotate=SECONDS` | 在 `tabs=` 的标签页之间轮播（已有的参数；仅当轮播开启时命令才会加上它） |
| `chrome=0`, `screen=`, `tabs=`, `account=` | 已有的参数 |

## 预设

| 预设 | 标签页 |
|---|---|
| `ops` | 当前、警报、图表 |
| `team` | 警报、团队健康 |
| `release` | 当前、仓库、报告 |
| `quiet` | 仅警报 |

## 设置（设置，命令行和展示屏）

| 设置 | 默认值 | 含义 |
|---|---|---|
| `kiosk.enabled` | 关 | 打开该配置 |
| `kiosk.font_scale_percent` | 150 | 字号，100 到 400 |
| `kiosk.high_contrast` | 关 | 黑色背景和白色线条 |
| `kiosk.rotate_views` | 关 | 含有多个标签页的预设会自动切换标签页；关闭时，屏幕显示该预设的第一个标签页 |
| `kiosk.rotate_seconds` | 30 | 每个标签页停留的时间（5 到 600） |
| `kiosk.safe_margin_percent` | 0 | 页面为会裁掉边缘的电视（过扫描）在每条边上留空的百分比；0 到 10 |
| `kiosk.scale_with_window` | 关闭 | 上面的字号是短边为 1080 px 的窗口中的大小；开启后它随窗口增大，4K 电视看起来就和全高清电视一样 |

字号通过页面缩放来应用，所以每个数字和每个表格会一起放大。超出范围的值不是错误：它会被默认值取代。
