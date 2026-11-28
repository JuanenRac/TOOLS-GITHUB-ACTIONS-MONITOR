<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | **🇵🇹 Português**

# As ferramentas à volta do monitor e até onde cada uma é suportada

Um nível cada. **recomendada**: usada e testada aqui. **exportável**: o monitor escreve o formato; o produto que o lê não foi testado. **experimental**: testada só contra duplos ou um laboratório. A lista é `schemas/ecosystem_tools.json`; um teste mantém-na junto desta página.

## Integrações

| Ferramenta | Nível | Guia |
|---|---|---|
| `workflow_lint` | recomendada | [SENTINEL.md](SENTINEL_por.md) |
| `lessons` | recomendada | [LESSONS.md](LESSONS_por.md) |
| `mcp_server` | recomendada | [AI_CONNECTION.md](AI_CONNECTION_por.md) |
| `webhook_receiver` | recomendada | [WEBHOOK.md](WEBHOOK_por.md) |
| `csv_ndjson` | exportável | [COMPARE.md](COMPARE_por.md) |
| `siem_sinks` | exportável | [OUTPUTS.md](OUTPUTS_por.md) |
| `otlp` | exportável | [OUTPUTS.md](OUTPUTS_por.md) |
| `audit_export` | exportável | [COMPLIANCE.md](COMPLIANCE_por.md) |
| `apprise` | experimental | [NOTIFICATIONS.md](NOTIFICATIONS_por.md) |
| `external_ci_buildbot_gitlab` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI_por.md) |
| `external_ci_jenkins_azure` | experimental | [EXTERNAL_CI.md](EXTERNAL_CI_por.md) |
| `plugins` | experimental | [PLUGINS.md](PLUGINS_por.md) |
| `secret_stores` | experimental | [PLUGINS.md](PLUGINS_por.md) |
| `ai_providers` | experimental | [AI.md](AI_por.md) |

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
