<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 从 1.5.0 之前的版本更新

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · **简体中文** · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

1.5.0 版给文件、文件夹、脚本和一项设置起了英文名称。不会丢失任何内容：监视器仍会读取旧名称，所以你可以先更新，之后再整理。

## 步骤

1. 停止监视器，把新版本解压到旧文件夹上（保留你的 `actions_monitor.json`）。
2. 查看会发生什么变化：`python migrate_state.py`（演练，不会改动任何内容）。
3. 执行：`python migrate_state.py --apply` 把旧文件复制到新名称并保留旧文件；加上 `--move` 则改为重命名。已存在的内容绝不会被覆盖，设置 `parte_history_days` 会在保存 `actions_monitor.json` 的副本之后改为 `report_history_days`。
4. 用 `MONITOR_GITHUB_ACTIONS`（与以前相同的启动器）启动监视器，批处理工具使用 `BATCH_GITHUB_ACTIONS`。
5. 删除你可能还留着的旧启动器：`LOTE_GITHUB_ACTIONS.bat`、`.sh` 和 `.command`。

## 旧名称与新名称

| 1.5.0 之前 | 1.5.0 起 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`、它的模式和 `--export-status` 的文件没有变化。在你于设置中选择其他语言之前，语言为英语。

# 从 1.5.x 到 1.6.x

无需转换任何内容：监视器继续读取你的 `actions_monitor.json`，并在你第一次从设置页保存时以安全的默认值添加新的键。

1. 停止监视器，把新版本解压覆盖到旧文件夹（保留你的 `actions_monitor.json` 和目录文件）。
2. 像以前一样启动。旁边会出现新文件（`etag_cache.json`、`analytics_history.json`、`update_check.json`、`sentinel_history.json`），可随时删除。
3. 可选：`python actions_monitor.py --doctor` 检查安装。

变化：出现了**精简版**（`MONITOR_LITE_GITHUB_ACTIONS`，端口 8766，独立的 `actions_monitor_lite.json`，无哨兵）；**main 上为红**统一为一条规则（每个工作流在默认分支上最后一次已完成的 run；已取消、已跳过、neutral 和 stale 的 run 不代表任何结论），因此某个数字可能与 1.5.x 不同；设置页以**基本**标签页开头；通知、分析、linter、webhook 事件和 AI 助手已存在，但在你开启之前都是**关闭**的；向 GitHub 写入仍需你明确确认。Rich 和 Textual 仍是可选的；需要 Python 3.11 或更高版本。

# 从 1.6.4 到 1.6.5

无需转换任何内容。以下行为是有意改变的，因为未经证明的事物不再被视为安全：

- **批次**：`finalize` 只会把批次中「记录了」基于已校验提交构建的运行提供给签名。旧版本写下的批次显示 `needs_review`。如仍要使用：`finalize --accept-legacy` 会从 GitHub 重新读取该运行，仅当其提交与记录一致时才接受，并在每次签名前要求输入 LEGACY。或者重新触发构建。
- **绿色 CI** 指必需的工作流文件在该提交上通过（默认 `ci.yml`；`dispatch.required_ci`、`dispatch.required_ci_repos`、`dispatch.required_ci_profiles`），没有失败或等待批准的项，且运行列表是完整的。CI 文件名不同的仓库需要把名称写入 `dispatch.required_ci`。
- **`git fetch` 失败**（无网络、无凭据）会阻止该仓库的触发。
- **targets.json**：`tool` 必须是工具文件夹内的普通文件名（无文件夹、无 `..`）；`extra` 只能包含 `-f 键=值` 对（不能是 `dry_run` 或 `ref`）；`finalize_flags` 只能是 `--bench` 这样的长选项。不符合的目录会连同原因被拒绝。
- **通知**：`max_per_hour` 统计的是消息（每个渠道一条），而不是事件。
- **Webhook**：每个请求都需要 `X-GitHub-Delivery`（GitHub 总会发送）；重复的 ID 会被忽略；`full_name` 的所有者必须是被监视的账户。
- **act**：作为指向其他文件夹的链接的克隆会被拒绝（`act.allow_symlinks` 可允许）。
- **网络模式**：仅 IPv4 地址；显示的地址就是服务器监听的地址；`GET /api/sentinel/parte.txt?save=1` 不再写入（副本改为带一次性令牌的 POST）。
- 保存的 GitHub 令牌不再放入进程环境：只有 `gh` 会收到它。
- 在干净文件夹中解压 zip 的测试不再属于常规测试集；`make_release.py` 将其作为独立阶段运行。

# 从 1.6.5 到 1.6.6

无需转换任何内容。以下行为是有意改变的:

- **HTTPS 下的网络模式**:现在可以从页面进行更改;`Origin` 必须带有会话的协议和监视器的端口。在代理之后请在地址中保留监视器的端口,否则检查会拒绝。
- **网络模式**:架构中标记为 `secure` 的所有设置只能在本机修改(以前只有 `listen.`、`github_token.`、`act.`、`github_actions.`)。在其他电脑上修改 `webhook.*`、`notify.*` 等的脚本现在会收到 403 `local_only`。
- **act**:Stop 之后运行立即空闲;紧接着的启动不再返回 `busy`。
- 监视器旁边新增文件 `degraded.json` 和 `degraded_lite.json`(被忽略失败的计数器);可随时删除。
- 更新历史(帮助 > 更新日志)已翻译:每种语言一个 `docs/CHANGELOG_<语言>.md` 文件。

# 从 1.6.6 到 1.6.7

无需转换任何内容。以下行为是有意改变的:

- **443 端口 HTTPS 代理之后的网络模式**:新设置 `listen.proxy_public_host`(默认为空;保持为空则没有任何变化)。当代理转发的 `Host` 和 `Origin` 不带端口时,请在这里填入代理的公开主机名;这一个名称随后会被原样接受,但仅限于网络模式开启且会话为 HTTPS 时。它只能在本机上更改。在保留端口的代理之后没有任何变化。
- 更新历史(帮助 > 更新日志)现在已将 1.6.7 和 1.6.5 翻译为其他七种语言;更早的条目仍在已翻译的提示下显示英文原文。
