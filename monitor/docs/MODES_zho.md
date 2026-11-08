<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | [🇪🇸 Español](MODES_spa.md) | [🇫🇷 Français](MODES_fra.md) | [🇮🇹 Italiano](MODES_ita.md) | [🇩🇪 Deutsch](MODES_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# 工作模式：普通、快速和极速

当你想在一段时间（比如一小时）内更近地观察某些内容时，可以把监视器切换到更快的模式，即使它会更快地用掉 API 配额。带仪表图标的选择框在页眉中；在控制台使用 `--mode fast` 或 `--mode turbo`，并加上 `--mode-minutes 60`。

| 模式 | 变化 | 默认值 |
|---|---|---|
| **normal** | 无：使用你自己的配置 | 你的值 |
| **fast**（快速） | 刷新、冷刷新、每个仓库的 run 数、热窗口 | 30 秒、300 秒、30 个 run、6 小时 |
| **turbo**（极速） | 同上，更强 | 15 秒、90 秒、50 个 run、12 小时 |

预设是 `actions_monitor.json` 中的 `modes` 块（`modes.fast`、`modes.turbo`、`modes.default_minutes`、`modes.start`），可按需编辑。预设绝不会让某个值比你自己设置的更慢或更小，并且不会低于 10 秒，以避开 GitHub 的次级限制（触发后监视器至少等待一分钟，之后更久）。

**开始前**，页面会显示该模式在最坏情况下每小时的调用次数、缓存通常能节省的量（返回 `304` 的条件读取不消耗主配额），以及剩余配额能用多久。时间到（页眉会倒计时）或剩余配额低于 `min_rate_remaining` 时，**它会自动恢复为普通模式**，并给出原因，控制台也会打印。**未登录时 GitHub 每小时只允许 60 次调用**，因此快速和极速会被禁用并说明原因（请运行 `gh auth login`）。

切换模式是本地设置：和其他更改一样需要页面的一次性令牌，只保存在内存中（重启后回到普通模式，除非你自己写入 `modes.start`），不会向任何地方发送任何内容。两个版本都可使用；完整版的哨兵保持自己的间隔和调用预算（`sentinel.budget_per_hour`），见[哨兵](SENTINEL_zho.md)。控制台横幅和状态行会显示当前模式。
