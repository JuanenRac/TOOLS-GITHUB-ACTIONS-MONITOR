<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | **🇪🇸 Español** | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# Las herramientas que rodean al monitor y hasta dónde se soporta cada una

Un nivel cada una. **recomendada**: usada y probada aquí. **exportable**: el monitor escribe el formato; el producto que lo lee no se ha probado. **experimental**: probada solo contra dobles o un laboratorio. La lista es `schemas/ecosystem_tools.json`; una prueba la mantiene unida a esta página.

## Integraciones

| Herramienta | Nivel | Guía |
|---|---|---|
| `workflow_lint` | recomendada | [SENTINEL.md](SENTINEL_spa.md) |
| `lessons` | recomendada | [LESSONS.md](LESSONS_spa.md) |
| `mcp_server` | recomendada | [AI_CONNECTION.md](AI_CONNECTION_spa.md) |
| `webhook_receiver` | recomendada | [WEBHOOK.md](WEBHOOK_spa.md) |
| `csv_ndjson` | exportable | [COMPARE.md](COMPARE_spa.md) |
| `siem_sinks` | exportable | [OUTPUTS.md](OUTPUTS_spa.md) |
| `otlp` | exportable | [OUTPUTS.md](OUTPUTS_spa.md) |
| `audit_export` | exportable | [COMPLIANCE.md](COMPLIANCE_spa.md) |
| `apprise` | experimental | [NOTIFICATIONS.md](NOTIFICATIONS_spa.md) |
| `external_ci_buildbot_gitlab` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI_spa.md) |
| `external_ci_jenkins_azure` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI_spa.md) |
| `plugins` | experimental | [PLUGINS.md](PLUGINS_spa.md) |
| `secret_stores` | experimental | [PLUGINS.md](PLUGINS_spa.md) |
| `ai_providers` | experimental | [AI.md](AI_spa.md) |

## Scripts de `tools/`

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
