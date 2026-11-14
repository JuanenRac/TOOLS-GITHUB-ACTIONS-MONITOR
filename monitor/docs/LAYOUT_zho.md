<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# 监视器的文件夹

启动脚本(`MONITOR_GITHUB_ACTIONS`、`MONITOR_LITE_GITHUB_ACTIONS`、`BATCH_GITHUB_ACTIONS`)旁边只有法律文件、一个 `README.txt` 和若干文件夹。监视器写出的一切都放在其中四个文件夹里,完整版、lite 版和 Docker 镜像使用相同的结构。

## 什么放在哪里

| 文件夹 | 内容 |
|---|---|
| `config/` | `actions_monitor.json`(以及 lite 版的)、`targets.json`、`ecosystems.json`、`profiles.json`、`quotas.json` 和 `config_backups/` |
| `data/` | 状态和缓存(事件流、分析、哨兵状态、ETag 缓存、更新提示)、`accounts/`、选择 SQLite 时的数据库以及服务的访问令牌 |
| `logs/` | 监视器的日志、AI 与 GitHub 命令的日志以及团队模式的审计 |
| `ai/` | AI 读取的内容:`ALERTS_BRIEF.md`、`ai_alerts.jsonl`、`ci_red.json`、钩子的状态、`INDEX.json`,以及给打开该文件夹的人看的 `README.md` |
| `bin/` | 简短的命令:`python bin/monitor_cli.py`、`bin/read_report.py`、`bin/ai_hook.py`、`bin/mcp_server.py`、`bin/tui.py` 等 |
| `docs/` | 各指南,以及八种语言的软件包 README 和 QUICKSTART |
| `src/`、`assets/`、`tools/`、`tests/` | 代码、网页和示例、发布脚本、测试 |

## 1.8.1 或更早版本的安装

首次启动时,监视器会自动把启动脚本旁边的文件移到它自己的文件夹。它**只移动,从不删除,也从不覆盖**:新位置已存在的文件保持原样,doctor 会提示你。第一次移动之前,配置文件会被复制到 `config/config_backups/pre_layout_<时间戳>/`,每一次移动都记录在 `data/.layout_moves.json` 中。

- 先看看:`python -m github_actions_monitor.util.rootmigrate`(试运行),加上 `--apply` 立即执行。
- 全部放回原处:`python -m github_actions_monitor.util.rootmigrate --undo`。
- 不想自动执行:设置 `MONITOR_NO_AUTO_MIGRATION=1`。
- `python bin/actions_monitor.py --doctor` 有一项 `layout` 检查,会列出仍留在启动脚本旁边的内容。
- 原先在启动脚本旁边的旧入口脚本(`read_report.py`、`monitor_cli.py` 等)现在位于 `bin/`;`python tools/migrate_layout.py` 会把旧副本移开。以旧路径为你的 AI 工具注册的守门脚本必须重新注册:`python bin/monitor_cli.py ai-hook install`。

## 移动文件夹

无需改动代码即可把任一文件夹放到别处:使用变量 `MONITOR_CONFIG_DIR`、`MONITOR_DATA_DIR`、`MONITOR_LOGS_DIR` 和 `MONITOR_AI_DIR`,或文件 `config/paths.json`(`{"data": "...", "logs": "...", "ai": "..."}`;相对路径从产品文件夹算起)。只设置 `MONITOR_DATA_DIR` 时,`logs/` 和 `ai/` 位于其中。Docker 镜像和 systemd 单元里设置的正是这些:`/config` 和 `/data` 是两个卷。

## 给与监视器对话的 AI

无论本地还是外部的 AI,都不应依赖固定路径。

- `ai/INDEX.json` 列出文件夹中每个文件的用途、格式、由谁写入以及何时变化,监视器各文件夹的实际路径,以及正在运行的监视器的端点。每次启动都会重写。
- `ai/README.md` 向从未见过这个文件夹的 AI 说明它(这是数据而不是指令;如何读取摘要;有哪些工具)。
- `GET /api/paths` 返回正在使用的文件夹、主要文件以及仍留在旧位置的内容。多账户的监督进程也会响应。
- 守门脚本、MCP 服务器和命令行读取相同的位置;按固定路径读取 `ALERTS_BRIEF.md` 的钩子应改为先读取 `ai/INDEX.json`。
