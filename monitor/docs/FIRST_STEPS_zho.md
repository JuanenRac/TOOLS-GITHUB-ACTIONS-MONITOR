<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# 你的前五分钟

**1. 安装所需的两样东西。** Python 3.11 或更高版本，以及 GitHub CLI（`gh`）。然后登录一次：`gh auth login`。监视器从不保存令牌：它向 `gh` 索取（除非你在“设置 > 高级”中开启监视器的可选令牌）。

**2. 用一条命令检查一切。** `python bin/actions_monitor.py --doctor` 会为每个问题给出能修复它的确切命令。想先看看？`python bin/actions_monitor.py --demo` 用虚构数据打开页面：无需 `gh`、登录或网络。

**3. 启动。** 双击 `MONITOR_LITE_GITHUB_ACTIONS` 使用简易版（端口 8766），或双击 `MONITOR_GITHUB_ACTIONS` 使用带哨兵的完整版（端口 8765）。控制台窗口的标题和第一行会说明是哪个版本。

**4. 按欢迎页的三个步骤操作。** 第一次打开时，页面会说明它做什么、展示在你账户中发现的内容，并指向基本设置。默认不隐藏任何内容：没有分组认领的仓库显示为“未分类”。

**5. 知道帮助在哪里。** 圆形的 **?** 按钮（或 `?` 键）打开帮助；**i** 按钮打开“关于”，其中有版本、文件，以及一个复制支持信息的按钮（不含任何密钥）。在控制台：`--help-topics`、`--help-search 关键词`、`--about`。

**6. 保存或打印报告。** 页面顶部的两个按钮可保存当前标签页的报告(TXT、PDF,需要时还有 JSON,均通过浏览器的 **另存为** 窗口),或将其作为简洁的页面打印([供其他工具使用的输出](OUTPUTS.md))。

**值得了解。** 如果你的套餐包含私有仓库，请在设置 > 基本中选择它以查看配额（[配额与套餐](QUOTAS_zho.md)）。哨兵的说明见[哨兵](SENTINEL_zho.md)。该工具只读取 GitHub，经你确认后才会写入。

## 舒适地阅读

- **密度**(`display.density`,或用 `?density=dense` 只改变一个窗口):`dense` 会收紧所有标签页的间距和字号。
- **减少动效**(`display.reduce_motion`):`auto` 遵循系统设置,`on` 会停止所有动画和过渡。工作流的状态始终用文字写出并用形状绘制,绝不只靠颜色。
- **色觉障碍配色**(`display.palette`,或 `?palette=colorblind`):蓝、朱红、黄和较浅的蓝,深色模式一套、浅色模式一套。对比度检查(`python tools/check_contrast.py`)会检查每个主题并模拟三种色觉障碍。
- **阅读时不跳动**(`display.live_throttle_s`):当指针或焦点位于你正在阅读的标签页内时,定期刷新会等待;你主动要求的刷新会立即应用。
- **新功能**(`display.whats_new`):更新后会有提示列出你所跳过版本的更新日志条目;可随时通过命令面板再次打开。`GET /api/whats-new?since=2.1.5` 返回这些条目(只读)。
- **术语表和限制**:从命令面板打开。`GET /api/glossary` 返回用你的真实参数写成的各数字含义、规则所查找的攻击、分析的限制以及几个深入了解的地方。开启 `report_export.limits` 后,保存和打印的报告会以这些限制结尾。
- **顶部筛选**覆盖「现在」、警报、图表、哨兵的各标签页(哨兵、CI、协作、安全、交付、供应链)、仓库和历史;其余标签页(哨兵趋势、团队、车队、报告、经验、更新和设置)始终是全局的。筛选下方的备注也会这样说明。
