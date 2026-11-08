<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# 控制台工具:工作流检查器与终端视图

两个可选的命令行工具。监视器本身不需要任何包;终端视图在你需要时使用 Rich。

## 工作流检查器:`lint_workflows.py`

- `py -3 lint_workflows.py [路径 ...] [--json] [--fail-on info|warn|bad]` 在推送前检查 `.github/workflows/*.yml`。不带路径时查看当前文件夹。它只打开文件。
- 规则(可在设置标签页的“工作流检查器”子标签页中分别关闭或调整严重程度):`unpinned_uses`(未固定到完整提交 SHA 的 Action)、`permissions`(没有 `permissions:` 块或为 `write-all`)、`secrets_in_clear`(看起来像写在文件里的令牌或密钥)、`injection`(第三方文本被粘贴进 `run:` 脚本)和 `pr_target`(检出拉取请求代码的 `pull_request_target`)。
- 当某项发现达到 `--fail-on`(默认 `bad`)时退出码为 1,因此可作为推送前钩子。当监视器能看到你的克隆时,还会在每日报告中增加一行。


## 终端视图:`tui.py`

- 先执行 `pip install rich`,然后 `py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`。它绘制一个实时表格,显示正在运行的内容、红色工作流、签名队列和报告,数据来自 `127.0.0.1` 上运行的监视器(不使用 GitHub 配额)。
- 它是只读的:没有任何按键会重新运行、关闭或写入内容。没有 Rich 时它会说明如何安装并以代码 3 退出;监视器及其测试从不需要 Rich。
