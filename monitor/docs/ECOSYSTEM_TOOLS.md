<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# The tools around the monitor and how far each is supported

One level each. **recommended**: used and tested here. **export format**: the monitor writes the format; the product that reads it has not been tested. **experimental**: tested against doubles or a laboratory only. The list is `schemas/ecosystem_tools.json`; a test keeps it and this page together.

## Integrations

| Tool | Level | Guide |
|---|---|---|
| `workflow_lint` | recommended | [SENTINEL.md](SENTINEL.md) |
| `lessons` | recommended | [LESSONS.md](LESSONS.md) |
| `mcp_server` | recommended | [AI_CONNECTION.md](AI_CONNECTION.md) |
| `webhook_receiver` | recommended | [WEBHOOK.md](WEBHOOK.md) |
| `csv_ndjson` | export format | [COMPARE.md](COMPARE.md) |
| `siem_sinks` | export format | [OUTPUTS.md](OUTPUTS.md) |
| `otlp` | export format | [OUTPUTS.md](OUTPUTS.md) |
| `audit_export` | export format | [COMPLIANCE.md](COMPLIANCE.md) |
| `apprise` | experimental | [NOTIFICATIONS.md](NOTIFICATIONS.md) |
| `external_ci_buildbot_gitlab` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI.md) |
| `external_ci_jenkins_azure` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI.md) |
| `plugins` | experimental | [PLUGINS.md](PLUGINS.md) |
| `secret_stores` | experimental | [PLUGINS.md](PLUGINS.md) |
| `ai_providers` | experimental | [AI.md](AI.md) |

## Scripts of `tools/`

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
