<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# 可选附加功能

两者都**默认关闭**，在设置中开启。

## 失败步骤的日志

`logs.failed_step.enabled`：失败运行的警报会多出一个**失败步骤**按钮。按一下就会从 GitHub 读取该运行的作业和失败日志(消耗两次配额)，显示失败的步骤及其最后的相关行(`logs.failed_step.lines`、`logs.failed_step.max_bytes`)，并把结果保存在内存中，再按一次不花任何配额。文本已去除令牌、密钥、地址和主目录。只能查询监视器所监视的仓库，通过 `GET /api/run-log?repo=&run=`；团队模式下仅管理员可用。

## 给您的工具使用的 GitHub App 只读令牌

`github_app.share_reads`：下面的命令会在本机打印您的 GitHub App 的一小时安装令牌，使您的工具和代理的 `gh` 使用 App 的配额而不是您的配额读取(`GH_TOKEN`)。令牌只输出到标准输出，绝不写入文件或日志，命令需要 `--read-only`；创建 App 时请只授予只读权限。未开启 `github_app.share_reads` 时命令会拒绝。 该令牌与监控自己保存的令牌分开申请，仅含读取权限；如果响应中带有任何写入权限，命令会拒绝输出。

```
python bin/monitor_cli.py gh-token --read-only
```

## 四个可选报告

四个都**默认关闭**。它们显示在警报标签页底部的“可选报告”区块和 `GET /api/reports` 中。读取 GitHub 的报告每个周期最多消耗 `reports.max_calls_per_cycle` 次调用，每次只读几个仓库，并把读到的内容在内存中保留一天。

- `reports.workflow_hygiene.enabled`：读取各仓库的工作流文件，列出写得不好的地方——未固定到提交的 action、未限制的权限、没有 `timeout-minutes` 的作业、没有 `concurrency` 组、`pull_request_target` 与注入风险、明文机密(即读取本地克隆的 A13 面板的 linter 规则，外加两条新规则)。
- `reports.queue.enabled`：读取几个等待过的已完成运行的作业，并按运行器类型(Linux、Windows、macOS、大型、自托管)说明作业在开始前等了多久。
- `reports.release_view.enabled`：完全不调用；根据哨兵已知的信息，说明哪些仓库“就绪”可发版(变更日志有条目或有无人发布的绿色构建、没有红色项、没有等待中的签名)，哪些“受阻”以及原因。
- `reports.supply_chain.enabled`：读取各仓库的最新版本，并根据文件名说明其是否带有软件物料清单(SBOM)、校验和以及签名或证明。绝不下载文件。
