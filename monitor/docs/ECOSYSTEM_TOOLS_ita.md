<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# Gli strumenti attorno al monitor e fino a dove è supportato ciascuno

Un livello ciascuno. **consigliato**: usato e provato qui. **formato di esportazione**: il monitor scrive il formato; il prodotto che lo legge non è provato. **sperimentale**: provato solo con doppi o in laboratorio. L'elenco è `schemas/ecosystem_tools.json`; un test lo tiene allineato a questa pagina.

## Integrazioni

| Strumento | Livello | Guida |
|---|---|---|
| `workflow_lint` | consigliato | [SENTINEL.md](SENTINEL_ita.md) |
| `lessons` | consigliato | [LESSONS.md](LESSONS_ita.md) |
| `mcp_server` | consigliato | [AI_CONNECTION.md](AI_CONNECTION_ita.md) |
| `webhook_receiver` | consigliato | [WEBHOOK.md](WEBHOOK_ita.md) |
| `csv_ndjson` | formato di esportazione | [COMPARE.md](COMPARE_ita.md) |
| `siem_sinks` | formato di esportazione | [OUTPUTS.md](OUTPUTS_ita.md) |
| `otlp` | formato di esportazione | [OUTPUTS.md](OUTPUTS_ita.md) |
| `audit_export` | formato di esportazione | [COMPLIANCE.md](COMPLIANCE_ita.md) |
| `apprise` | sperimentale | [NOTIFICATIONS.md](NOTIFICATIONS_ita.md) |
| `external_ci_buildbot_gitlab` | sperimentale | [EXTERNAL_CI.md](EXTERNAL_CI_ita.md) |
| `external_ci_jenkins_azure` | sperimentale | [EXTERNAL_CI.md](EXTERNAL_CI_ita.md) |
| `plugins` | sperimentale | [PLUGINS.md](PLUGINS_ita.md) |
| `secret_stores` | sperimentale | [PLUGINS.md](PLUGINS_ita.md) |
| `ai_providers` | sperimentale | [AI.md](AI_ita.md) |

## Script di `tools/`

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
