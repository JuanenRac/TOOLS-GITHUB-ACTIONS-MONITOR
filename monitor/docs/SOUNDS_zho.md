<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | [🇪🇸 Español](SOUNDS_spa.md) | [🇫🇷 Français](SOUNDS_fra.md) | [🇮🇹 Italiano](SOUNDS_ita.md) | [🇩🇪 Deutsch](SOUNDS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# 声音

页面用 Web Audio API 自己发声,每种事件一种声音,不看屏幕也能凭听觉分辨发生了什么。没有音频文件:声音在浏览器中离线生成,不会发送到任何地方。每种声音都有对应的视觉提示(方块、标签页、徽标),声音绝不取代它。

| 类型 | 何时响起 | 声音 |
|---|---|---|
| 红色 | 原本不是红色的工作流变红(新的故障)。 | 两个上行音,经典的“叮叮”。 |
| 安全或严重 | 安全哨兵出现新警报、协作哨兵出现严重(错误或严重级)警报,或账户失明。 | 三个低沉的脉冲。 |
| 卡住 | 构建卡住、幽灵队列或运行器出问题。 | 一个长的下滑音。 |
| 评分 | 机群评分下降(`score.dropped`)。 | 三个下行音符。 |
| 连接 | 与 GitHub 的连接,或此页面与监视器的连接丢失。 | 两个低沉的长音。 |
| 警告 | 出现新的警告级别警报(待签名、过期的议题、等待中的拉取请求)。 | 两个相同的中音。 |
| 已解决 | 红色工作流恢复为绿色,或严重警报消失。 | 三个上行音符。 |
| 报告 | 某个可选报告出现了之前没有的发现。 | 两声轻柔的钟声,先高后低。 |
| 经验 | 失败经验出现新的类别,或某类别开始重复或开始适用。 | 三个快速的高音。 |
| 通知 | 出现新的信息级别警报(例如分叉原仓库的发布)。 | 一个柔和的提示音。 |
| 已恢复 | 与 GitHub 的连接,或本页面与监视器的连接,在中断后恢复。 | 四个上升的音符。 |

## 浏览器为什么可能静音,以及页面如何处理

- 浏览器只有在你点击、触摸或按键之后才允许页面发声。在此之前,状态栏会显示“声音被浏览器阻止:点击此处开启”。在任意位置点击一次即可解锁。
- 声音被阻止期间发生的事会被保留(最多十分钟),并在第一次机会时播放:点击、页面回到前台,或每两秒一次的下一次检查。两次读取之间不会丢失任何内容;超过十分钟的属于旧消息,不再播报。
- 页面的第一次读取只记住已有的内容;几小时内重新加载也会记住,因此页面关闭期间出现的故障算作新的。
- 后台标签页只要浏览器保持页面唤醒就会保留声音;有些浏览器会在一段时间后暂停隐藏的标签页。墙面屏幕和页面最好放在可见的窗口里。

## 不刷屏

- 刚响过的类型要等待 `sound.cooldown_seconds`(默认 30 秒)才会再次响起。
- 一次读取中出现多种类型只响一轮:最多三种模式,最严重的先响;其余的等下一轮。两轮不会重叠。
- 已静音的警报(“警报”标签页)不会响。

## 声音库

除了每种事件一直拥有的 11 种声音外，监视器还带有一个包含 54 种声音的声音库（共 65 种），可分配给任何事件。声音在浏览器中合成（本机蜂鸣也用同样的音符），无需下载音频文件。事件的声音是前 11 个，其余可自由分配：`bell`, `chime`, `ding_dong`, `doorbell`, `ding`, `ping_high`, `ping_low`, `tick_soft`, `tock_soft`, `double_tick`, `tick_tock`, `knock`, `knock_three`, `blip`, `bloop`, `bubble`, `drop`, `droplet`, `arpeggio_up`, `arpeggio_down`, `minor_up`, `minor_down`, `fanfare`, `level_up`, `coin`, `harp_up`, `harp_down`, `marimba`, `xylophone`, `pluck`, `cascade`, `sparkle`, `ascend`, `descend`, `notify_a`, `notify_b`, `notify_c`, `sweep_up`, `sweep_down`, `whistle_up`, `whistle_down`, `zap`, `laser`, `radar`, `sonar`, `beacon`, `heartbeat`, `alarm_fast`, `siren`, `klaxon`, `buzzer`, `gong`, `phone`, `cuckoo`。

要给某种事件换一种声音，在 `sound.voices` 中写入用逗号分隔的 `事件=声音` 对，例如 `new_red=coin,warning=drop`。事件有 `new_red`, `sentinel`, `stuck`, `score_drop`, `connection_lost`, `warning`, `resolved`, `report`, `lesson`, `info`, `live_recovered`。不在声音库中的名称会被忽略，该事件保持自己的声音。墙面屏幕可以在 `screens.sound_voices` 中使用自己的列表，在 `screens.sound_volume` 中使用自己的音量。没有声音超过一秒，且每种声音互不相同。

两个可选背景音，默认都关闭：`sound.ambient`（两个很轻的低音，没有红色时平和，有红色时变粗糙）和 `sound.tick`（每隔 `sound.tick_seconds` 一声极短的干脆咔哒声，让卡住的屏幕能被听出来）。两者都遵循静音标签、总开关和安静时段。

## 设置(设置,声音)

全部位于配置文件和“设置”标签页;音量、主题和开关立即生效。

| 设置 | 作用 |
|---|---|
| `sound.enabled` | 页面所有声音的总开关。 |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | 每种类型一个开关(默认全部开启)。 |
| `sound.theme` | `classic`(清晰的音色)或 `soft`(更低、更圆润、更慢的音色)。两种主题下每种类型的节奏不变。 |
| `sound.volume` | 1 到 100,默认适中。 |
| `sound.cooldown_seconds` | 同一类型两次声音之间的间隔。 |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | 静音时段(默认关闭):在本机的两个时刻之间不发声;可以跨过午夜。 |
| `sound.server_beep` | 默认关闭。没有打开页面或浏览器阻止声音时,监视器本身会在本机发声:上表中每种事件类型各有一种模式(Windows 音调、macOS 系统声音、Linux 的 canberra 事件),使用与页面相同的开关和静音时段,每次最多合并三种类型为一串;仅限本地。 |
| `sound.voices` | 给某种事件指定声音库中的另一种声音（用逗号分隔的 `事件=声音` 对）。默认为空。 |
| `sound.ambient`, `sound.ambient_volume` | 背景环境音（默认关闭）及其音量，1 到 50。 |
| `sound.tick`, `sound.tick_seconds` | 时钟滴答声（默认关闭）及滴答间隔秒数，1 到 60。 |
| `screens.sound_voices`, `screens.sound_volume` | 与 `sound.voices` 相同，但只用于墙面屏幕，并有自己的音量（0 = 使用 `sound.volume`）。 |

## 试听每种声音

在“设置”的“界面”中,“测试声音”按钮播放经典的“叮叮”,每种类型各有一个按钮,以设置中的音量和主题播放该类型。底部栏的“声音”徽标可使此浏览器中的一切静音。

## 墙面屏幕

墙面屏幕(`/screen/...`)使用相同的声音,以及相同的主题、音量、开关和静音时段。默认关闭:必须开启 `screens.sound`,且窗口需要 `?sound=on`。无人触碰的屏幕无法完成浏览器要求的点击:请用浏览器的“允许无手势播放音频”选项启动屏幕浏览器(Chromium 中为 `--autoplay-policy=no-user-gesture-required`),或在窗口中点击一次。

## 保存在哪里

静音徽标由各浏览器记住;页面对上一次读取的了解也保存在浏览器中。关于声音的任何内容都不会发送到服务器。
