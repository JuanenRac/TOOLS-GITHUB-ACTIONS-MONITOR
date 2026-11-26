<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# 插件与密钥存储

插件在不改动监视器的情况下增加检查项。全部默认关闭。Lite 版没有插件。

## 启用

开启 `plugins.enabled`，再开启需要的插件。设置 > 扩展会列出每个插件的权限、密钥、状态和隔离情况。插件的发现是来源为 `plugin` 的告警，前面带插件名。

## 官方插件

随签名发布版一起提供，在监视器内的独立线程中运行。

- **discussions**（`plugins.official.discussions.enabled`）：超过 `plugins.official.discussions.days` 天没有评论的讨论。Issue 与 PR 归 Collab。
- **packages**（`plugins.official.packages.enabled`）：版本数超过 `plugins.official.packages.max_versions` 的 container 或 npm 软件包。需要 `read:packages`。发布版归交付哨兵。

## 第三方插件

开启 `plugins.third_party.enabled`。软件包是含 `plugin.json` 的 zip，加上作者用自己工具生成的分离签名 `NAME.zip.ed25519.sig`。只有由**您**钥匙串中范围为 `plugins` 的密钥签名、且您复述该密钥指纹后才会安装，安装后默认关闭。每次运行前重新验证签名；密钥吊销或文件变化会暂停插件。

**已签名不等于安全。** 清单不是沙箱。

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## 隔离了什么

| 系统 | 独立进程、空环境、无令牌 | 无网络 | 内存与子进程 |
|---|---|---|---|
| Linux | 是 | 系统允许用户命名空间时是，否则标记**无网络隔离** | 内存与 CPU 限制 |
| Windows | 是 | **否**：标记**无网络隔离** | 作业对象：内存限制、禁止子进程 |
| macOS | 是 | **否**：标记**无网络隔离** | CPU 限制；不保证内存限制 |

任何系统上都不会对此类插件隐藏您的文件：它以您的用户身份运行。`plugins.worker.platforms_ok` 留空则永不运行第三方插件。读取 GitHub 须经监视器，仅允许清单中的 `get_paths` 且限于受监视仓库。`plugins.worker.timeout_s`、`max_output_kb`、`memory_mb` 限制每次运行。

## 不可信输出与健康

标题会清理并截断（`plugins.alert_title_max`），只保留指向 github.com 的链接，第三方插件不能发出严重告警。插件文本是数据，绝不是给 AI 的指令。连续失败 `plugins.breaker.failures` 次后暂停，直到您恢复；暂停或降级不代表“一切正常”。doctor 的 `plugins` 检查和 `plugin audit` 会报告已吊销或已变化的软件包。

## 面向作者

契约版本为 1（`api_compat`）。`run(ctx)` 返回 `{"alerts": [{id, code, level, repo, url, title}]}`；`ctx` 提供 `owner`、`now`、`options`、`repos()`、`get(path)`、`discussions()`，各需相应权限（`repos.list`、`gh.get`、`graphql.discussions`）。`init` 生成带测试的模板。监视器从不签名。

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## 路由与 pip 软件包

路由（管理员；修改仅限本机）：`/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`。开启 `plugins.entry_points` 后，监视器列出声明了 `gha_monitor.plugins` 组并带 `*.plugin.zip` 的 pip 软件包；从不导入其代码，按同样方式安装该 zip。

## 从其他程序读取 GitHub 令牌

`secrets.backend` 读取令牌而不在监视器中保存（需开启 `github_token.enabled`）。只读。`vault`（HTTP，`secrets.vault.addr`、`path`、`field`，Vault 令牌放在 `token_env` 指定的环境变量；https，http 仅限本机）、`sops`（`secrets.sops.file`、`field`；仅限可信计算机）、`bitwarden`（`bws`、`secrets.bitwarden.item`）、`aws`、`azure`、`gcp`（各自命令行工具，`secrets.cloud.ref`）。开启 `secrets.reload_on_rotate` 时每 `secrets.reload_seconds` 重读一次。已对模拟服务器和开发模式 Vault 测试；未使用真实云账户。
