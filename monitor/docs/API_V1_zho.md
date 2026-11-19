<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# 只读 API v1 分步指南

写给为监视器只读 API 编写客户端(脚本、墙屏、手机应用、AI 工具)的人。每条路由的参考是监视器自己提供的 OpenAPI 文档;契约的规则(哪些已冻结、哪些可以增长)见 [API_zho.md](API_zho.md)。这里给出应遵循的步骤,命令均由测试针对监视器运行。

## 1. API 是否开放?

当监视器作为服务运行(团队模式的账户、Docker 镜像、systemd 单元)时,前缀 `/api/v1/` 会自动应答;一个人在一台电脑上使用时保持关闭并返回 404。由设置 `api.v1_enabled`(`auto`、`on`、`off`)决定。客户端先问“我是谁”:那里的 `404` 表示 API 已关闭,而不是客户端有错。

## 2. 表明身份

在同一台电脑上且未启用网络模式时无需令牌。网络模式下,每个请求都在请求头 `X-Monitor-Access` 中带上访问令牌,这里从文件读取,避免它出现在会保存进历史记录的命令行里;团队模式下脚本通过 `POST /api/auth/login` 登录。此 API 的客户端只需要一个读取令牌:前缀下没有任何写入。

## 3. 命令

依次是:你是谁以及契约版本(`/api/v1/me`)、每条冻结路由的描述(`/api/v1/openapi.json`)、分页的仓库(用 `state`、`ecosystem`、`q` 过滤;`limit`;用 `fields` 或 `profile=compact` 缩短每行;`cursor` 是上一页的 `next_cursor`,直到它为 `null`)、用 gzip 压缩的响应,以及旧 API 中前缀同样以相同响应提供的两条路由。

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. 错误

自有路由的错误是带三个键的 JSON 对象:`error` 和 `code` 稳定,供程序使用;`message` 跟随 `?lang=` 的语言,供人阅读。代码有 api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile 和 api.server_error。前缀下的每个响应(包括错误)都带有请求头 `X-API-Version: 1`。

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

响应头之后的内容是 `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. 命令行与 AI 工具中的相同操作

三个入口给出相同的文档,并由测试比较:如上的 HTTP、命令行(`python bin/monitor_cli.py api me`、`api openapi`、`api contract-check`;加 `--json` 以数据形式返回)以及 MCP 服务器(`python bin/mcp_server.py`,只读:工具 `api_me`、`api_openapi` 和 `api_contract_check`)。

## 6. 依赖服务器之前先检查

`python tools/api_contract_suite.py --url URL --token-file token.txt` 把服务器提供的文档当作检查内容的描述,每项检查输出一行,最后输出 `API_CONTRACT=PASS` 或 `API_CONTRACT=FAIL`。`python tools/check_api_contract.py --v1` 运行同一套件,并把响应与冻结的契约比较。每次升级监视器或你的客户端后运行其中之一;监视器的 CI 会针对服务模式的演示运行该套件。
