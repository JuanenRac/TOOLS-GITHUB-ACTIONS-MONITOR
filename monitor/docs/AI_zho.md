<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# 哨兵的 AI 助手

可选功能,**默认关闭**。语言模型可以总结每日报告、对警报分类、解释失败的运行、起草发布说明,并回答关于某个仓库的问题。它写的所有内容都会显示为未经验证的建议。

## 提供方

- `ollama`:本机上的模型(仅限 `127.0.0.1`;没有任何内容离开本机)。
- `openai-compatible`:任何提供 OpenAI 风格聊天端点的服务。也适用于 Gemini(其 OpenAI 兼容端点)和 OpenAI 本身:设置 `base_url`、`model` 以及保存密钥的变量名称。
- `anthropic`:Anthropic 的 Messages API(`https://api.anthropic.com`,请求头 `x-api-key` 和 `anthropic-version`)。模型由你选择,没有内置的。
- `copilot`:使用你自己的 GitHub 登录运行 `gh copilot`(监视器中没有密钥),只返回文本且不使用工具。它会消耗你 Copilot 套餐的高级请求。请手动运行一次 `gh copilot` 以安装该 CLI。
- 密钥从不保存:你设置的是环境变量的名称。三个远程提供方会把你仓库的数据发送给第三方。


## 它能看到什么

- 所有输入都会被清理:去除控制字符、按模式遮盖密钥、限制长度、把内容放在随机分隔符之间并声明为不可信数据。回答会被截断,其中的链接会被失效处理。
- 在设置标签页中你可以选择它可分析的事件类型(`build`、`codeql`、`report`)、它可查看的仓库(留空=监视器监视的仓库)、回答语言、每日调用上限和大小上限。按钮可测试连接,页面显示今天的调用次数。


## 提出并执行操作

- 第 3 级(`ai.actions.enabled`):回答中的命令只有匹配封闭列表才会保留:`gh run rerun N --failed`、`gh run rerun N`、`gh issue close N` 和 `act -W 文件 -j 作业`(最后一个只显示)。显示的命令由已检查的部分重新组装,绝不从模型文本复制;仓库以及运行或 issue 编号必须是监视器已在监视的。
- 第 4 级(`ai.actions.execute`,独立开关,默认关闭):每个建议都有确认按钮;对话框显示完整命令,在你接受之前不会运行任何内容。它使用你自己的 `gh` 登录且不经过 shell,每小时最多 `ai.actions.max_per_hour` 次,每次尝试都记入页面显示的本地日志,连续失败两次后操作会锁定,直到你解锁。
- 刻意不在列表中的:删除分支、关闭或合并拉取请求、任何与密钥或设置有关的操作。
