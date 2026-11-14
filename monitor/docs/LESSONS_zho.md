<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# 失败与经验

监视器可以维护一本 CI 失败记录簿和一个经验库，让同样的错误不再犯第二次，无论是人、您自己的 AI 工具，还是监视器自带的 AI。它是**本地且只读**的：不会有任何内容离开本机，也不会向 GitHub 写入任何内容。它跟随 AI 警报源，因此需要 `ai_alerts.enabled`。

## 记录簿

警报源打开的每个失败都会成为 `data/failures.jsonl` 中的一行(模式 1)：`schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`。所有文本都经过与警报源相同的清理(令牌、密钥、地址和主目录绝不会进入记录簿)。`lessons.retention_days` 和 `lessons.max_entries` 限制其大小。可以导入来自别处的同模式记录簿(`lessons.import_book`)。

## 分类器

每个失败按规则归入一个类别，第一条匹配的规则生效：quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other。规则内置于程序；若要使用自己的规则，请编写 `config/lessons_rules.json`：`{"rules": [{"category": "mine", "label": "我的类型", "avoidable": true, "patterns": ["正则表达式"]}]}`。该文件会替换内置规则；无效(或超过 120 个字符)的规则或模式会被跳过。

## 经验库

每个类别都有一条经验：什么失败了、该怎么做，以及本可以阻止它的防护。内置经验提供八种语言。您自己的写在 `config/lessons.json`(`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`)中，并替换同一类别的内置经验。

## 重复与趋势

按类别，监视器统计最近 24 小时和最近 7 天的失败，并把这 7 天与之前的 7 天比较(新增、上升、下降、持平)。7 天内达到 `lessons.recurring_from` 次失败时，该类失败视为**重复**，并建议添加防护：一个在推送前于您本机失败的检查。

## AI 读取什么

- `ai/LESSONS.md`：精简 Markdown(大小：`lessons.brief_max_bytes`)，在失败打开或解决时重写。
- `GET /api/ai/lessons`：分析结果、当前适用的经验和经验库(`?fmt=md` 取文件，`?fmt=brief&repo=NAME` 取推送前简报，`&as=json` 以 JSON 形式返回)。
- `GET /api/ai/failures`：记录簿，最新在前(`?since=秒&repo=NAME&category=NAME&limit=N`)。
- `GET /api/ai/state` 和警报简报都带有当前适用的经验。
- MCP 服务器：`lessons_apply`、`lessons_recurring`、`lessons_brief` 和 `lesson_propose`。
- 命令行：`python bin/monitor_cli.py lessons [list | brief | failures] [--repo NAME]`。

一切都是数据，绝不是指令：别人写下的日志行可能会进入记录簿。

## 推送之前

推送前先读简报：它列出适用的经验(该仓库的优先)、要运行的防护，以及该仓库当前为红色的内容。

## AI 工具的示例钩子

许多 AI 工具可以在会话开始时运行一条命令并把其输出加入上下文。下面这条会打印推送前简报：

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## 监视器的 AI

当开启失败构建的 AI 解释时，其提示词会包含日志所属类别的经验。其他 AI 工具通过接口 `LessonProvider`(`applicable`、`recurrences`、`pre_push_brief`、`propose`、`register`)使用同样的功能。`FileProvider` 是当前使用的，`ExampleProvider` 是最小的实现：

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## 写入经验

读取始终允许。写入一条经验需要三样东西：开启 `lessons.allow_write`(默认关闭)、管理员身份和确认：`POST /api/ai/lessons`，内容为 `{"lesson": {...}, "confirm": true}`(没有 `confirm` 时，响应是草稿)。MCP 服务器只有在以 `--allow-lessons` 启动且开关打开时才会写入。绝不会向 GitHub 写入任何内容。

## 设置

`lessons.enabled`、`lessons.allow_write`、`lessons.retention_days`、`lessons.max_entries`、`lessons.brief_max_bytes` 和 `lessons.recurring_from`，位于设置的 AI 标签页。面板**从失败中得到的经验**在警报标签页的底部。

## 一轮工作的收尾

完成一批工作后，`python bin/monitor_cli.py lessons close` 会列出仍没有自己的经验及其防护的重复失败类型(`GET /api/ai/lessons` 中的 `needs_guard`)，只要还有一种就以非零退出码结束。请写下防护，或说明为何暂时无法存在，然后再运行一次。
