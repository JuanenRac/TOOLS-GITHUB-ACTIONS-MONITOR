<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# 定时报告

仅 Complete，默认关闭。监视器可以按计划或在你需要时为账户生成报告：评分、自上一份报告以来的变化、需要人处理的仓库和未处理的警报，格式为 HTML 页面和 Markdown。报告由监视器已有的数据生成，不会向 GitHub 请求任何内容，也不会向任何地方发送内容：文件保存在 `data/reports/` 文件夹中。

## 如何开启

设置，哨兵标签页，**定时报告**区块：

| 设置 | 默认值 | 作用 |
|---|---|---|
| `report_schedule.enabled` | 关闭 | 按计划生成报告 |
| `report_schedule.cron` | `0 8 * * 1` | 五个字段（分钟、小时、日、月、星期），使用这台电脑的本地时间；可用数字、列表、范围和步长，不能用名称；`0 8 * * 1` 表示每周一 8:00 |
| `report_schedule.formats` | 两者 | `html`、`markdown` 或 `both` |
| `report_schedule.keep` | 12 | 保留多少次；较旧的会被删除 |
| `report_schedule.top` | 10 | 每个列表显示多少个仓库和警报（最差的在前） |

第一份报告等待开启后的第一个计划时间。每个计划时间只生成一份报告，即使监视器停了好几天也只生成一份（不会堆积一批）。失败的报告会记录在监视器的健康状态中，下一个计划时间会再次尝试。 指定了某月某日的计划在停止最多一个月后仍会补发（指定了月份的最多一年），秋季时钟回拨时出现两次的那个小时不会重复报告。报告要么所有格式齐全，要么一份都没有：第二种格式写不出来时，第一个文件会被删除。

## 报告的内容

账户的评分（含等级和趋势；校准中或数据不足时会说明，且不显示数值）、自上一份报告以来的变化（分差、新增警报和已消失的警报）、健康视图中需要人处理的仓库（在前）以及未处理的警报（最差的在前）。已静音的警报不算未处理。来自数据的所有文本都会被转义：页面没有脚本，也没有外部地址。

## PDF

没有自带的 PDF：打开 HTML 页面，用浏览器打印为 PDF 即可。页面带有 A4 打印样式。

## 在哪里查看和申请

- **团队**标签页有一个报告区：列表、每个文件的链接和**立即生成报告**按钮（需要这台电脑上的管理员）。
- `GET /api/report-files` 列出报告，`GET /api/report-files/file?name=...` 打开其中一份（只限服务为此账户写入的文件），`POST /api/report-files/run` 立即生成一份。
- 在团队模式下，能看到该账户的人都可以读取它的报告；立即生成报告需要这台电脑上的管理员。Lite 版没有这些功能。
