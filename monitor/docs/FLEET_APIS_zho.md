<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# 按角色与分组查看机群、只读 API 与演示站点

## 角色与分组

机群标签页末尾显示每个分组（生态）的最差状态及其专属屏幕 `/g/<键>` 链接，并按工作流角色分列（`fleet.roles`）。未读取记为 `未知`，绝不视为正常。

## 停用

`fleet.disabled` 接受名称、模式或 `group:<键>`；无需重启，下一周期起停止读取。Complete 与 Full 版本。

## 只读 API

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`。均为只读，沿用相同的访问检查；版本化 API 开启时也可经 `/api/v1/` 访问。`fleet.cctray` 提供 CCTray 订阅；`fleet.security_api` 提供各仓库机密与代码扫描告警计数（绝不含机密本身），并列出无法读取的部分。两者默认关闭。

## 报告摘要值

报告与 AI 简报带有 `report_digest`：对事实、监视器版本、规则版本和结论取 SHA-256。值相同即内容相同。它不是签名。

## 演示站点

生成演示的静态副本（虚构数据，无登录、无操作、不向别处发请求）以及用 Pyodide 在浏览器中运行的工作流检查（不上传任何内容）：

```
python tools/make_public_demo.py demo-site
```

*Demo site* 工作流将其保存为构建产物。发布到网址是仓库所有者另行决定的事，不会自动发布。浏览器检查尚未在已发布的站点上试过。

## 全部设置

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
