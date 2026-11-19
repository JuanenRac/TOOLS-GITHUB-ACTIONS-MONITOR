<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# 面向客户端的 API

脚本、墙屏或移动客户端可以依赖的内容。自 2.0.0 起读取类端点被冻结：契约中列出的键保持名称和类型，可以新增键，但不经新的主版本不会删除或更改任何内容。

## 发起请求

- 默认模式下，API 在 `127.0.0.1` 上无需登录即可响应。网络模式下，每个请求在请求头 `X-Monitor-Access` 中携带访问令牌（或会话 Cookie，或一次 `POST /api/access`）。使用团队模式时，脚本通过 `POST /api/auth/login` 登录。
- 端点不认识的查询参数会被忽略。响应为 UTF-8 的 JSON，Markdown 摘要和数据流除外。

## 错误

- 错误是 JSON `{"error": "词"}`，有时带 `code`。`401 access` 表示令牌缺失或错误，`403 forbidden` 表示请求并非来自允许的位置（包括陌生的 `Host`），`404` 表示该路径在此版本中不存在（简易版对仅完整版才有的内容返回 404），`429` 表示地址被锁定或监听者已满。
- 被拒绝的写入绝不会改变任何东西。写入不属于契约。

## 契约

- `docs/schemas/api_contract.json` 列出每个读取端点在各版本中的键和类型，以及错误码。可以读取但未冻结的路由（数据流、文本、其他工具的导出）在同一文件的 `unfrozen` 中列出，并各附原因；提供运行、仓库和配额的 `/api/data` 已冻结。 其键一直深入到列表的元素：文件中写成 `[{...}]` 的列表描述其元素（检查前三个），因此 `/api/data` 的运行、仓库和配额，`/api/alerts` 的警报以及 `/api/auth/me` 在不使检查失败的情况下无法改变。
- `python tools/check_api_contract.py` 用它检查正在运行的监视器（`--lite`、`--url`、`--token-file`），并输出 `CONTRACT=PASS` 或 `CONTRACT=FAIL`；每次升级监视器或你的客户端后都运行它。

## 只读 API v1(默认自动)

- 设置 `api.v1_enabled`(设置、高级、只读 API v1):`auto`(默认)在监视器作为服务运行时(团队模式的账户、Docker 镜像、systemd 单元)响应,一人一台电脑时保持关闭;`on` 始终开启;`off` 始终关闭(旧的 true 和 false 相当于 on 和 off)。响应时,每条读取路由也会在 `/api/v1/` 下提供(例如 `/api/v1/alerts`):相同的响应和相同的角色,另加头 `X-API-Version: 1`。关闭时、在精简版中以及对任何其他版本号,该前缀返回 404。
- `/api/v1/me`:谁在请求:`mode`(`individual` 或 `team`)、`authenticated`、`user`,以及团队会话的 `role` 和 `accounts`(没有会话时为 null)、该会话可做的事(`capabilities`:`read`、`write`、`admin` 和 `v1_write`,因前缀只读,`v1_write` 始终为 false)、列表的 `limits`、监视器版本和契约版本(`contract`,`1.0`:每增加一个键就增长,从不丢失键)。
- `/api/v1/repos`:监视器正在监视的仓库,每个一行(`repo`、`ecosystem`、`state`、`risk`、`runs_24h`、`failures_24h`、`red_workflows`、`stuck_runs`、`alerts`、`last_run_at`)。过滤参数 `state`、`ecosystem` 和 `q`;`limit`(默认 `api.default_limit`,最多 `api.max_limit`);`cursor`(上一页的 `next_cursor`,带签名,在 `api.cursor_ttl_seconds` 内有效);`fields=a,b` 或 `profile=compact` 可得到更短的行。客户端接受时,响应用 gzip 压缩。
- `/api/v1/openapi.json`:整个已冻结只读 API 的 OpenAPI 3 描述,由契约(`docs/schemas/api_contract.json`)生成,从不手写:每条已冻结路由及其承诺的键和类型、`x-lite`(精简版的响应)和 `x-local-only`。契约未冻结的路由是实验性的:它们在 `/api/v1/` 下返回 404,也不在文档中,除非开启 `api.experimental_routes`(此时以 `x-experimental` 列出)。`/api/` 下的旧路由永远不变。用 `python bin/monitor_cli.py api openapi` 下载。
- `python tools/api_contract_suite.py` 是面向外部客户端的契约套件(只用标准库,只读):给它服务器地址(`--url`)和只读令牌(`--token-file`),它把服务器提供的文档当作检查内容的描述:每条无需参数的路由的形状、头 `X-API-Version`、错误信封及其稳定代码、分页及游标、`fields` 与 `profile=compact`、gzip,以及前缀下无法写入任何内容。每项检查输出一行,最后是 `API_CONTRACT=PASS` 或 `API_CONTRACT=FAIL`(`--json` 输出一个文档);退出码为 0、1 或 2(无响应)。`python bin/monitor_cli.py api contract-check` 针对命令行的监视器运行它。
- 同样的三件事也是 MCP 服务器(`python bin/mcp_server.py`,只读,无需任何开关)的工具:`api_me`(监视器把客户端当作谁)、`api_openapi`(文档,或用 `path` 取某一条路由)和 `api_contract_check`(契约套件,返回 `{ok, checks, failed, rows}`)。HTTP、命令行(`api me`、`api openapi`、`api contract-check`)与 MCP 给出同一份文档,并由测试比较。前缀关闭时,工具会用一行话说明。
- 两条自有路由以 `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` 的形式返回错误:`error` 和 `code` 稳定,`message` 跟随 `?lang=` 的语言。代码:api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile, api.server_error。一切均为只读:`/api/v1/` 下没有任何写入。其形状已冻结在契约的 `v1_endpoints` 部分,可用 `python tools/check_api_contract.py --v1` 针对开启了 `api.v1_enabled` 的监视器进行检查。

### curl 示例

令牌是网络模式的访问令牌(或使用团队模式的会话);不在网络模式时,从同一台电脑访问无需令牌。客户端沿 `next_cursor` 翻页直到其为 `null`,并先读取 `/api/v1/me` 以了解契约版本和该会话可做的事。

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## 数据流

- `GET /api/ai/stream`（警报）和 `GET /api/live-events/stream`（webhook 事件，`live.sse.enabled`）是服务器发送事件，只读且默认关闭；参见 [AI_ALERTS_zho.md](AI_ALERTS_zho.md) 和 [WEBHOOK_zho.md](WEBHOOK_zho.md)。
- `POST /api/chatops/slack` 和 `POST /api/chatops/discord` 接收来自聊天的只读命令(默认关闭,`chatops.enabled`)。它们不使用访问令牌:平台的签名就是凭据,没有有效签名的请求会在读取任何内容之前被拒绝。参见 [CHATOPS_zho.md](CHATOPS_zho.md)。
