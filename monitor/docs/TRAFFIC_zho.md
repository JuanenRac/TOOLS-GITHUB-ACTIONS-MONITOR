<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | [🇪🇸 Español](TRAFFIC_spa.md) | [🇫🇷 Français](TRAFFIC_fra.md) | [🇮🇹 Italiano](TRAFFIC_ita.md) | [🇩🇪 Deutsch](TRAFFIC_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# 下载与流量

在本机保存一份历史: 你的发布文件被下载了多少次, 以及所选仓库的访问和克隆情况。GitHub 只保留 14 天的访问和克隆数据, 也不提供下载历史, 不保存就会丢失。仅 Complete 版; 默认关闭。

## 开启

打开 `traffic.enabled` (设置 > 下载与流量), 并在 `traffic.repos` 中填写仓库, 每行一个: 名称 (所监视账户的) 或 所有者/名称, 最多 50 个。列表为空时不读取任何内容。面板显示在“仓库”标签页中。

## 读取内容与开销

只在周期之后发送 GET 请求: 每个所选仓库每天 (UTC) 最多一次, 每个周期 `traffic.repos_per_cycle` 个。一个仓库消耗一到五个 GitHub 配额请求 (发布版本最多 300 个; 访问; 克隆)。配额用完时停止, 稍后再试。`traffic.views_clones` 可关闭访问和克隆。离线隔离的安装不读取任何内容。连接中断、首次读取进行中, 或剩余请求不超过 `min_rate_remaining` 的两倍时, 也会等待。

## 权限

访问和克隆数据只提供给对该仓库拥有 push 权限的令牌。没有权限时, 面板会针对该仓库说明; 这不是错误, 下载次数照常保存。

## 数字的含义

下载次数是匿名的, 包含机器人和镜像, 且不计 GitHub 附加在发布版本上的 "Source code" 压缩包。新增下载只对仍然存在的文件与上一次读取做比较。未读取的日期是空缺, 绝不记为零。

## 导出与隐私

面板可导出两个 CSV 文件: 每个仓库每天一行, 以及每个发布文件在次数变化的日期一行。`monitor_cli.py traffic export` 输出第一个。早于 `traffic.keep_days` 的日期会被删除。历史保存在本机的数据文件夹中, 不会发送到任何地方。
