<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# 从监视器到仪表板：`ci_red.json`

监视器写出什么、如何导出，以及读取该文件的一方需要什么。监视器只读取 GitHub 并写入本地文件：它绝不推送、绝不提交，也绝不会自行关闭任何内容。

## 监视器写出的内容

`ci_red.json` 位于 `bin/actions_monitor.py` 旁边，在每次哨兵巡检后刷新（模式 2）：

| 字段 | 含义 |
|---|---|
| `schema` | `2`。字段只会新增，绝不会重命名。 |
| `generated` | 本次巡检的 UTC 时间。 |
| `tool_version` | 写出该文件的工具版本。 |
| `complete` | 本次巡检读取了每个被监视仓库时为 `true`。加载期间、API 配额不足或缺少克隆时为 `false`：在其变为 `true` 之前，请勿依据红色仓库列表或签名队列采取行动。 |
| `red_repos` / `pending_sign_repos` | 计数。 |
| `repos.<NAME>.ecosystem` | `armor`、`urtc`、`hydra`、`eh3d` 或 `other`。 |
| `repos.<NAME>.red[]` | 每个在默认分支上最近一次完成的运行失败的工作流对应一项：`workflow`、`conclusion`、`since`、`streak`、`url`。 |
| `repos.<NAME>.pending_sign[]` 和 `pending_sign_hours` | 已构建但尚未签名的发布，以及其中最旧一项的存在时长。 |

## 如何导出

```
py -3 bin/read_report.py --export-status DIR          # ci_status_public.json + .md，仅包含可以公开的内容
py -3 bin/read_report.py --export-sign-queue FILE     # 签名队列
```

两者都读取运行中的、位于 `127.0.0.1` 的监视器（不消耗 GitHub 配额）。快照加载期间它们会拒绝写入并说明原因；此时退出码不为零。

## 读取方（仪表板生成器）需要做的事

1. 读取 `schema`；接受任何 `>= 2` 的值，并忽略未知字段。
2. 读取 `complete`；当其为 `false` 时，保留上一次完整的导出，而不是替换它。
3. 在数字旁边显示 `generated`，以便一眼看出文件已过期。
4. 使用 `repos.<NAME>.red[].url` 作为链接；绝不要自行重新拼装。

## 监视器不做的事

它不发布该文件，不推送到个人资料仓库，也不触碰任何工作流。把导出内容送到仪表板是所有者的一步操作（或由个人资料仓库中读取导出文件的某个工作流完成）。

## 个人主页仪表板(使用方约定)

个人主页仓库的状态仪表板可以通过两种方式读取同一份文档:从运行中的监视器(`GET /api/outputs/dashboard.json`,在开启 `outputs.dashboard.enabled` 之前关闭,仅限本机),或从 `py -3 bin/read_report.py --export-status DIR` 写出的文件(只含红色工作流,绝不含签名部分)。仪表板可以依赖的内容(由本仓库的测试检查):

1. `schema` 为 `2`,字段只会增加。
2. 提供的文档与 `ci_red.json` 完全一致。
3. `complete: false` 表示:保留你上一次完整的画面。
4. 公开导出只有 `schema`、`generated`、`tool_version`、`complete`、`red_repos` 和 `red` 这些键,不含任何签名状态。

监视器从不把该文件推送到个人主页仓库;把它放过去是所有者自己的一步。
