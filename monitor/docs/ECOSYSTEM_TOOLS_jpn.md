<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# モニター周辺のツールとそれぞれのサポート水準

それぞれ一つの水準です。**推奨**: ここで使い試験済み。**書き出し形式**: モニターは形式を書き出すが、読む側の製品は未試験。**実験的**: 代役や実験環境のみで試験。一覧は `schemas/ecosystem_tools.json` で、テストがこのページとの一致を保ちます。

## 連携

| ツール | 水準 | ガイド |
|---|---|---|
| `workflow_lint` | 推奨 | [SENTINEL.md](SENTINEL_jpn.md) |
| `lessons` | 推奨 | [LESSONS.md](LESSONS_jpn.md) |
| `mcp_server` | 推奨 | [AI_CONNECTION.md](AI_CONNECTION_jpn.md) |
| `webhook_receiver` | 推奨 | [WEBHOOK.md](WEBHOOK_jpn.md) |
| `csv_ndjson` | 書き出し形式 | [COMPARE.md](COMPARE_jpn.md) |
| `siem_sinks` | 書き出し形式 | [OUTPUTS.md](OUTPUTS_jpn.md) |
| `otlp` | 書き出し形式 | [OUTPUTS.md](OUTPUTS_jpn.md) |
| `audit_export` | 書き出し形式 | [COMPLIANCE.md](COMPLIANCE_jpn.md) |
| `apprise` | 実験的 | [NOTIFICATIONS.md](NOTIFICATIONS_jpn.md) |
| `external_ci_buildbot_gitlab` | 実験的 | [EXTERNAL_CI.md](EXTERNAL_CI_jpn.md) |
| `external_ci_jenkins_azure` | 実験的 | [EXTERNAL_CI.md](EXTERNAL_CI_jpn.md) |
| `plugins` | 実験的 | [PLUGINS.md](PLUGINS_jpn.md) |
| `secret_stores` | 実験的 | [PLUGINS.md](PLUGINS_jpn.md) |
| `ai_providers` | 実験的 | [AI.md](AI_jpn.md) |

## `tools/` のスクリプト

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
