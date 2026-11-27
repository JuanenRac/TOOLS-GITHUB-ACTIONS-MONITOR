<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | [🇫🇷 Français](ECOSYSTEM_TOOLS_fra.md) | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# Die Werkzeuge rund um den Monitor und wie weit jedes unterstützt wird

Je eine Stufe. **empfohlen**: hier genutzt und getestet. **Exportformat**: der Monitor schreibt das Format; das lesende Produkt ist ungetestet. **experimentell**: nur gegen Attrappen oder ein Labor getestet. Die Liste ist `schemas/ecosystem_tools.json`; ein Test hält sie mit dieser Seite zusammen.

## Integrationen

| Werkzeug | Stufe | Anleitung |
|---|---|---|
| `workflow_lint` | empfohlen | [SENTINEL.md](SENTINEL_deu.md) |
| `lessons` | empfohlen | [LESSONS.md](LESSONS_deu.md) |
| `mcp_server` | empfohlen | [AI_CONNECTION.md](AI_CONNECTION_deu.md) |
| `webhook_receiver` | empfohlen | [WEBHOOK.md](WEBHOOK_deu.md) |
| `csv_ndjson` | Exportformat | [COMPARE.md](COMPARE_deu.md) |
| `siem_sinks` | Exportformat | [OUTPUTS.md](OUTPUTS_deu.md) |
| `otlp` | Exportformat | [OUTPUTS.md](OUTPUTS_deu.md) |
| `audit_export` | Exportformat | [COMPLIANCE.md](COMPLIANCE_deu.md) |
| `apprise` | experimentell | [NOTIFICATIONS.md](NOTIFICATIONS_deu.md) |
| `external_ci_buildbot_gitlab` | experimentell | [EXTERNAL_CI.md](EXTERNAL_CI_deu.md) |
| `external_ci_jenkins_azure` | experimentell | [EXTERNAL_CI.md](EXTERNAL_CI_deu.md) |
| `plugins` | experimentell | [PLUGINS.md](PLUGINS_deu.md) |
| `secret_stores` | experimentell | [PLUGINS.md](PLUGINS_deu.md) |
| `ai_providers` | experimentell | [AI.md](AI_deu.md) |

## Skripte in `tools/`

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
