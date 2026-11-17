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

- `docs/schemas/api_contract.json` 列出每个读取端点在各版本中的键和类型，以及错误码。可以读取但未冻结的路由（数据流、文本、其他工具的导出）在同一文件的 `unfrozen` 中列出，并各附原因；提供运行、仓库和配额的 `/api/data` 已冻结。
- `python tools/check_api_contract.py` 用它检查正在运行的监视器（`--lite`、`--url`、`--token-file`），并输出 `CONTRACT=PASS` 或 `CONTRACT=FAIL`；每次升级监视器或你的客户端后都运行它。

## 只读 API v1(默认关闭)

- 开启 `api.v1_enabled`(设置、高级、只读 API v1)。之后每条读取路由也会在 `/api/v1/` 下提供(例如 `/api/v1/alerts`):相同的响应和相同的角色,另加头 `X-API-Version: 1`。关闭时、在精简版中以及对任何其他版本号,该前缀返回 404。
- `/api/v1/me`:谁在请求:`mode`(`individual` 或 `team`)、`authenticated`、`user`,以及团队会话的 `role` 和 `accounts`(没有会话时为 null)、列表的 `limits` 和版本。
- `/api/v1/repos`:监视器正在监视的仓库,每个一行(`repo`、`ecosystem`、`state`、`risk`、`runs_24h`、`failures_24h`、`red_workflows`、`stuck_runs`、`alerts`、`last_run_at`)。过滤参数 `state`、`ecosystem` 和 `q`;`limit`(默认 `api.default_limit`,最多 `api.max_limit`);`cursor`(上一页的 `next_cursor`,带签名,在 `api.cursor_ttl_seconds` 内有效);`fields=a,b` 或 `profile=compact` 可得到更短的行。客户端接受时,响应用 gzip 压缩。
- `/api/v1/openapi.json`:这两条路由的轻量 OpenAPI 3 描述。
- 两条自有路由以 `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` 的形式返回错误:`error` 和 `code` 稳定,`message` 跟随 `?lang=` 的语言。代码:api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile, api.server_error。一切均为只读:`/api/v1/` 下没有任何写入。其形状已冻结在契约的 `v1_endpoints` 部分,可用 `python tools/check_api_contract.py --v1` 针对开启了 `api.v1_enabled` 的监视器进行检查。

## 数据流

- `GET /api/ai/stream`（警报）和 `GET /api/live-events/stream`（webhook 事件，`live.sse.enabled`）是服务器发送事件，只读且默认关闭；参见 [AI_ALERTS_zho.md](AI_ALERTS_zho.md) 和 [WEBHOOK_zho.md](WEBHOOK_zho.md)。
