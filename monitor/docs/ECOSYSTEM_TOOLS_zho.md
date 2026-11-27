<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# 监控器周边工具及其支持程度

每项一个级别。**推荐**: 本项目实际使用并测试过。**可导出**: 监控器写出该格式, 读取它的产品未测试。**实验性**: 只在替身或实验环境中测试。清单见 `schemas/ecosystem_tools.json`, 有测试保证它与本页一致。

## 集成

| 工具 | 级别 | 指南 |
|---|---|---|
| `workflow_lint` | 推荐 | [SENTINEL.md](SENTINEL_zho.md) |
| `lessons` | 推荐 | [LESSONS.md](LESSONS_zho.md) |
| `mcp_server` | 推荐 | [AI_CONNECTION.md](AI_CONNECTION_zho.md) |
| `webhook_receiver` | 推荐 | [WEBHOOK.md](WEBHOOK_zho.md) |
| `csv_ndjson` | 可导出 | [COMPARE.md](COMPARE_zho.md) |
| `siem_sinks` | 可导出 | [OUTPUTS.md](OUTPUTS_zho.md) |
| `otlp` | 可导出 | [OUTPUTS.md](OUTPUTS_zho.md) |
| `audit_export` | 可导出 | [COMPLIANCE.md](COMPLIANCE_zho.md) |
| `apprise` | 实验性 | [NOTIFICATIONS.md](NOTIFICATIONS_zho.md) |
| `external_ci_buildbot_gitlab` | 实验性 | [EXTERNAL_CI.md](EXTERNAL_CI_zho.md) |
| `external_ci_jenkins_azure` | 实验性 | [EXTERNAL_CI.md](EXTERNAL_CI_zho.md) |
| `plugins` | 实验性 | [PLUGINS.md](PLUGINS_zho.md) |
| `secret_stores` | 实验性 | [PLUGINS.md](PLUGINS_zho.md) |
| `ai_providers` | 实验性 | [AI.md](AI_zho.md) |

## `tools/` 中的脚本

- `tools/api_contract_suite.py`
- `tools/backup_storage.py`
- `tools/check_api_contract.py`
- `tools/extci_fake_servers.py`
- `tools/make_migrations.py`
- `tools/make_release.py`
- `tools/migrate_layout.py`
- `tools/migrate_storage.py`
- `tools/monitor_updater.py`
- `tools/release_summary.py`
- `tools/sbom.py`
- `tools/sign_release.py`
