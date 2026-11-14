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

**值得了解。** 如果你的套餐包含私有仓库，请在设置 > 基本中选择它以查看配额（[配额与套餐](QUOTAS_zho.md)）。哨兵的说明见[哨兵](SENTINEL_zho.md)。该工具只读取 GitHub，经你确认后才会写入。
