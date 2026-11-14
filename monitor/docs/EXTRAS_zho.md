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

`github_app.share_reads`：下面的命令会在本机打印您的 GitHub App 的一小时安装令牌，使您的工具和代理的 `gh` 使用 App 的配额而不是您的配额读取(`GH_TOKEN`)。令牌只输出到标准输出，绝不写入文件或日志，命令需要 `--read-only`；创建 App 时请只授予只读权限。未开启 `github_app.share_reads` 时命令会拒绝。

```
python bin/monitor_cli.py gh-token --read-only
```

## 尚未包含

工作流卫生面板、队列报告、版本就绪或受阻视图以及供应链面板不属于此版本。
