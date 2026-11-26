<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor：它是什么

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · **简体中文** · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## 目的

在用户自己的电脑上告诉个人或小团队：所有仓库的 CI 是否真的通过、什么失败了以及原因，而无需逐个打开仓库。

## 面向谁

- 拥有很多仓库的人（从几个到数百个）。
- 共享屏幕或墙面看板的小团队。
- 在这些仓库中工作、推送前需要读取状态的 AI 工具。

## 它是什么、不是什么

它是一个本地程序，用你自己的令牌或 GitHub App 读取 GitHub。它不是托管服务，不是 CI 系统，也不替代 GitHub：它只做观察，少数会写入的操作在你开启之前都是关闭的。

## 长期原则

- 不需要任何软件包：核心只用 Python 标准库。
- 除非某个可见的设置另有说明，任何内容都不会离开你的电脑；没有遥测。
- 没有检查过的内容绝不显示为通过。
- 任何写入 GitHub 或系统的功能默认关闭，并在执行前询问。
- 界面和帮助中的每一段文字都有八种语言。
- GPL-3.0-or-later。
