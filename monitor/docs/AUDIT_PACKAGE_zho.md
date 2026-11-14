<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# 审计员资料包

审计员检查本工具的团队模式、网络暴露和密钥处理所需的内容：检查清单、以往审查的发现及其修复和保持修复的测试、如何运行测试，以及已知遗留的问题。

## 团队模式安全检查清单

- 团队模式（`auth.enabled`）默认关闭；仅在 HTTPS 或受信任代理（`listen.trusted_proxy`）之后启用。
- 团队模式开启且网络开放时，在第一位管理员存在之前监控器不会启动。
- 在此之前只有本机可以进入（第一位管理员在本机创建）。
- 脚本令牌（`auth.allow_bearer`）默认关闭；会话写入需要 CSRF 令牌。
- 每个账户的进程只响应其监督进程（启动时给它的密钥）。
- 任何密钥都不会写入日志或 API 响应；设置文件在锁下保存。
- 所有离开监控器的请求（通知、OpenTelemetry、runner 导出器）遵循同一规则：不使用私有地址，也不重定向到私有地址。

## 发现、修复与测试

| 发现 | 修复 | 测试 |
|---|---|---|
| 团队模式下尚无用户时，所有路由对网络开放 | 在第一位管理员出现前只有本机可进入，没有管理员时网络模式不会启动 | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| 账户进程绕过了团队模式的检查 | 每个请求都要求其监督进程的密钥 | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| 超时后设置会在没有文件锁的情况下继续保存 | 锁被占用十秒时，保存会被拒绝并给出提示 | `test_184_audit_hardening.py::ConfigurationLock` |
| 哨兵命令可能是带参数的 shell | 命令是一个列表，首项是非 shell 程序的完整路径，且不含控制字符 | `test_184_audit_hardening.py::NotifyCommand` |
| 脚本令牌（bearer）默认开启 | 默认关闭；只有真正的 true 才会开启 | `test_184_audit_hardening.py::ScriptTokens` |
| 面向 AI 的信息流由所有账户共享，刷新、确认和通知上限可能互相抢先 | 每个账户一个信息流；刷新、确认和状态使用同一把锁；上限在一次加锁的步骤中预留 | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| AI 工具钩子的暂停没有一步到位地预留；runner 导出器可重定向监控器；永不返回的 GitHub 调用不断堆积 | 暂停通过锁保持；重定向会被检查并限制；被放弃的调用会被计数并设上限（`watchdog_max_abandoned`） | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| 以换行结尾的名称能通过 ID、仓库和密钥的检查 | 所有检查都以文本末尾结束（`\Z`） | `test_184_audit_anchors.py` |
| OpenTelemetry 导出不遵守出站请求规则；代理未被说明为信任边界；页面转义没有测试 | 导出经过同一道防护（无私有地址、无重定向）；边界已写入帮助；测试保证 API 的每段文本都被转义 | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| 两个监控器可以监听同一个端口；找不到 Git for Windows 的 openssl；有意吞掉的失败不留来源痕迹 | 端口以独占方式占用，第二个监控器拒绝启动；在 Git for Windows 存放的位置查找 openssl；每个被吞掉的失败都会写入一行包含类型和位置的日志 | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| 没有时长的运行（经 GraphQL 读取）使哨兵在每个周期失败 | 缺失的时长按零计 | `test_186_unfinished_rows.py` |

## 如何运行测试

在 `monitor/` 文件夹中运行：`python -m unittest discover -s tests`。测试不需要网络，也不需要 GitHub 令牌。安装了 Edge、Chrome 或 Chromium 时（或设置 `MONITOR_BROWSER_TESTS=1`）会运行浏览器测试。表中的文件位于 `monitor/tests/`。

## 已知限制

- 环境代理（`network.use_proxy`，默认关闭）会自行解析名称：名称检查发生在此之前。强保证必须来自网络（拒绝私有地址的防火墙）。
- Windows 无法仅靠权限使文件私有：在系统支持的地方，密钥使用用户密钥加密。
- 测试不能证明真实的 GitHub、真实的代理或真实邮件服务器的任何事情：它们使用本地替身。
