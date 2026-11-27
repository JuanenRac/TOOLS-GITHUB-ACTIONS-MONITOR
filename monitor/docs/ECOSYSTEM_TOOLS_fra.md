<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ECOSYSTEM_TOOLS.md) | [🇪🇸 Español](ECOSYSTEM_TOOLS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](ECOSYSTEM_TOOLS_ita.md) | [🇩🇪 Deutsch](ECOSYSTEM_TOOLS_deu.md) | [🇨🇳 简体中文](ECOSYSTEM_TOOLS_zho.md) | [🇯🇵 日本語](ECOSYSTEM_TOOLS_jpn.md) | [🇵🇹 Português](ECOSYSTEM_TOOLS_por.md)

# Les outils autour du moniteur et leur niveau de prise en charge

Un niveau chacun. **recommandé** : utilisé et testé ici. **format d'export** : le moniteur écrit le format ; le produit qui le lit n'est pas testé. **expérimental** : testé seulement contre des doubles ou un laboratoire. La liste est `schemas/ecosystem_tools.json` ; un test la garde alignée avec cette page.

## Intégrations

| Outil | Niveau | Guide |
|---|---|---|
| `workflow_lint` | recommandé | [SENTINEL.md](SENTINEL_fra.md) |
| `lessons` | recommandé | [LESSONS.md](LESSONS_fra.md) |
| `mcp_server` | recommandé | [AI_CONNECTION.md](AI_CONNECTION_fra.md) |
| `webhook_receiver` | recommandé | [WEBHOOK.md](WEBHOOK_fra.md) |
| `csv_ndjson` | format d'export | [COMPARE.md](COMPARE_fra.md) |
| `siem_sinks` | format d'export | [OUTPUTS.md](OUTPUTS_fra.md) |
| `otlp` | format d'export | [OUTPUTS.md](OUTPUTS_fra.md) |
| `audit_export` | format d'export | [COMPLIANCE.md](COMPLIANCE_fra.md) |
| `apprise` | expérimental | [NOTIFICATIONS.md](NOTIFICATIONS_fra.md) |
| `external_ci_buildbot_gitlab` | expérimental | [EXTERNAL_CI.md](EXTERNAL_CI_fra.md) |
| `external_ci_jenkins_azure` | expérimental | [EXTERNAL_CI.md](EXTERNAL_CI_fra.md) |
| `plugins` | expérimental | [PLUGINS.md](PLUGINS_fra.md) |
| `secret_stores` | expérimental | [PLUGINS.md](PLUGINS_fra.md) |
| `ai_providers` | expérimental | [AI.md](AI_fra.md) |

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
