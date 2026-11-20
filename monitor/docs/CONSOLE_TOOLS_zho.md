<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# 控制台工具:工作流检查器与终端视图

两个可选的命令行工具。监视器本身不需要任何包;终端视图在你需要时使用 Rich。

## 工作流检查器:`bin/lint_workflows.py`

- `py -3 bin/lint_workflows.py [路径 ...] [--json] [--fail-on info|warn|bad]` 在推送前检查 `.github/workflows/*.yml`。不带路径时查看当前文件夹。它只打开文件。`--remote OWNER/REPO`(可重复)通过 `gh` 从 GitHub 读取仓库的工作流文件,无需克隆;读不到时会说明原因(SSO 未授权、无访问权限)。
- 当 `lint.anonymous_public` 开启时(默认关闭),`--remote OWNER/REPO --anon` 完全不使用凭据读取公开仓库(例如第三方仓库):工作流文件夹的列表是匿名请求,每个文件来自 `raw.githubusercontent.com`,不消耗你令牌的任何额度。未变化的文件不会重复读取,超过 256 KiB 的文件会被跳过,私有或不存在的仓库显示“未找到”(绝不是“干净”),与网络隔离的监视器从不读取。从不发送带有密钥的请求头。
- 规则(可在设置标签页的“工作流检查器”子标签页中分别关闭或调整严重程度):`unpinned_uses`(未固定到完整提交 SHA 的 Action)、`permissions`(没有 `permissions:` 块或为 `write-all`)、`secrets_in_clear`(看起来像写在文件里的令牌或密钥)、`injection`(第三方文本被粘贴进 `run:` 脚本)和 `pr_target`(检出拉取请求代码的 `pull_request_target`)。
- 可选规则（开启前默认关闭）：`no_timeout`（没有 `timeout-minutes` 的作业）、`secrets_inherit`（调用可复用工作流时的 `secrets: inherit`）、`own_action_main`（跟随 `@main` 的自有账户 action）和 `permissions_top`（作业有自己的 `permissions:`，但文件顶层没有）。`unpinned_uses` 会说明该 action 是自有的还是第三方的（`lint.own_owners`），`lint.unpinned_own` 可降低或隐藏自有的。
- 信息规则 `archived_action`(开启前不生效;需要 GitHub):列出文件所用的 GitHub Action 和可复用工作流中仓库已**归档**的,并且在开启 `lint.maintenance.inactive` 时,还列出已有 `lint.maintenance.inactive_years` 年(默认 2 年)没有推送的。每个 Action 只向 GitHub 查询一次(命令行用 `--check-actions` 和 `--inactive-years N`;监视器使用自己的配额读取,每次扫描最多 `lint.maintenance.max_calls_per_tick` 个 Action,并将每个回答保留 `lint.maintenance.refresh_seconds` 秒)。它只提供信息:始终是信息级别,绝不会使 `--fail-on` 失败,也不会改变退出码。无法连接 GitHub 时不会判断这些 Action,也不会就它们给出提示,输出会说明有多少个无法读取。
- 当某项发现达到 `--fail-on`(默认 `bad`)时退出码为 1,因此可作为推送前钩子。当监视器能看到你的克隆时,还会在每日报告中增加一行。使用 `--remote` 时,如果某个仓库无法读取(不存在或令牌看不到、SSO 未授权、无网络)或其名称不是 `OWNER/REPO`,退出码为 2:未读取的仓库绝不会被当作干净。 指定的文件夹或文件不存在,或某个工作流文件无法读取时同样如此:它会在错误输出中点名,其余文件仍会检查,退出码为 2。
- 看起来像密钥的值会被分类,但绝不会被打印或保存:已知的令牌格式或高熵的长字符串为严重(`bad`);`placeholder`、`dummy`、`changeme`、`ci` 之类可读的占位符只是信息;其他情况为警告;`${{ secrets.X }}`、`${X}` 或空值不算发现。要让某项发现不再出现,在它所在行或上一行写注释:`# monitor-lint: ignore secrets_in_clear 因为这是 docker compose config 的占位符`(规则名或 `all`);或在设置 `lint.ignore` 中列出 `仓库:文件:规则` 模式(可用 `*`)。


## 终端视图:`bin/tui.py`

- 先执行 `pip install rich`,然后 `py -3 bin/tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`。它绘制一个实时表格,显示正在运行的内容、红色工作流、签名队列和报告,数据来自 `127.0.0.1` 上运行的监视器(不使用 GitHub 配额)。
- 它是只读的:没有任何按键会重新运行、关闭或写入内容。没有 Rich 时它会说明如何安装并以代码 3 退出;监视器及其测试从不需要 Rich。
- 交互式终端应用 `bin/tui_textual.py`(`pip install textual`;精简版加 `--lite`)可在“设置”标签页中编辑其所列分组的简单设置、**列表**(各项以逗号分隔输入:`a, b, c`)和数字**映射**(`name=3, other=5`);服务器会再次校验每个值,安全相关选项只能在页面中修改。
