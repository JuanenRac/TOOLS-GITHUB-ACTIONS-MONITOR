<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# 面向 AI 的技能包

监视器自带两份技能包：简短的英文指南，告诉 AI 如何与它配合。它们位于安装包的 `skills/` 文件夹、页面(设置，AI 标签页)中，也可用一条命令安装。

## 两份技能包

- `skills/internal`：给监视器内置的 AI，本地(Ollama、llama.cpp 服务器、LM Studio)或外部(提供商的 API)均可。它说明监视器是什么、能看到什么、AI 可读取什么、绝不能做什么、如何诊断红色运行、何时保持沉默，以及如何使用和提出经验。当 `ai.skill` 开启时，其核心(`SKILL.md`)会按 `ai.skill_max_chars` 截断后加入该 AI 的每个提示词。
- `skills/external`：给从外部与监视器多向交互的 AI：读取(`/api/ai/*`、`ai/` 中的文件)、接收通知(事件流或每隔几分钟的简报)、写入(确认警报、经验、失败记录、通知偏好，按相应权限)、监视器与会话之间的联动、推送前简报以及完整的自学习循环。它涵盖有命令行的 AI、只有 HTTP 或文件的 AI、使用 MCP 的 AI 和使用事件流的 AI。

## 包含什么

每份技能包都有一个简短的 `SKILL.md`(核心)和一个只在需要时才读取的 `references/` 文件夹，因此上下文很小的模型只需取核心：逐步场景(真正的红色、暂时的红色、配额不足、降级的监视器、重复的失败、新经验、无网络、多块屏幕)、自学习循环、提供商及其限制、安全(来自日志的提示注入、机密、最小权限、对 AI 所写内容的审计)，以及由代码生成的参考资料。

## 没有遗漏

参考资料(`api.md`、`cli.md`、`settings.md`、`files.md`、`roles.md`、`tabs.md`)和 `skills/COVERAGE.md` 由 `python tools/make_skill_refs.py` 从代码中生成：每个端点及可调用它的最低角色、每个命令和选项、每个设置及其默认值、监视器写入的每个文件、每个角色和每个标签页。测试会从代码中读取同样的清单，若技能包中有未提及的内容就会失败，因此新的端点、命令、设置或文件不可能在未向 AI 说明的情况下出现(并且生成器会在写好说明之前停止)。

## 安装

把技能包复制到您的 AI 工具读取技能的文件夹：

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## 安装器的安全性

它只在您指定的文件夹中写入 `github-actions-monitor-internal` 或 `github-actions-monitor-external`，别无其他。它绝不会覆盖与安装包中内容不同的文件(保留您的文件并指出是哪个)，并拒绝 D: 盘和网络路径。再次运行不会有任何变化。

## 页面中与 HTTP

在设置的 AI 标签页中，**面向 AI 的技能包** 区块为每份技能包提供复制(技能包核心)和下载(整份技能包连同参考资料合为一个文件)。`GET /api/skills` 列出它们，`GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` 返回文本；只读。

## 设置

`ai.skill`(开启)和 `ai.skill_max_chars`(3000；小型本地模型用 1500)。从外部登记失败记录用 `POST /api/ai/failures`，需要 `lessons.allow_write` 和管理员，与写入经验相同。

## 发布到技能仓库

`python tools/prepare_skill_bundle.py --out DIR` 生成可发布的外部技能文件夹（SKILL.md、参考资料、记录监视器版本与许可证的 `bundle.json`、`SHA256SUMS`）；相同来源得到相同字节。它不发布任何内容：上传到 ClawHub 需维护者阅读条款后用自己的账户手动完成。

## 助手

只有实际试过的才标为已测试。

| 助手或方式 | 命令行 | HTTP 与文件 | MCP |
|---|---|---|---|
| 终端编码助手 | 已测试 | 已测试 | 协议兼容，未测试 |
| 其他助手 | 协议兼容，未测试 | 协议兼容，未测试 | 协议兼容，未测试 |
