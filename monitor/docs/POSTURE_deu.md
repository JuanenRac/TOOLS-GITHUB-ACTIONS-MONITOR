<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# Sicherheitslage von Repositorys und Organisation

Eine nur lesende Prüfliste, wie Ihre Repositorys und Organisation geschützt sind: Webhooks, Actions-Einstellungen, Scans, Branches, Deploy-Schlüssel, Alter von Secrets, Apps, Releases. Auf GitHub wird nichts geändert. Editionen Complete und Full; standardmäßig aus.

## Einschalten

`posture.enabled` setzen (Einstellungen > Sicherheitslage). Pro Zyklus werden wenige Repositorys gelesen (`posture.repos_per_cycle`), jedes höchstens alle `posture.refresh_hours`; das verbraucht GitHub-Kontingent. `posture.org_checks` nimmt die Organisation hinzu.

## Was geprüft wird

Jeder Befund nennt seinen Platz in den OWASP-Top-10-CI/CD-Risiken und im CIS-Leitfaden zur Lieferkette. Die Zuordnung hilft beim Lesen; sie ist keine Zertifizierung.

| Bereich | Kennungen |
|---|---|
| Webhook-Zustellungen | webhook.no_secret webhook.plain_http webhook.tls_off |
| Actions-Einstellungen | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Code und Abhängigkeiten | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Zweige | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Schlüssel und Secrets | deploy.write deploy.old stored.old |
| Organisation (Konto) | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed |
| Runner (Ausführer) | runner.not_hardened runner.coverage_lost |
| Releases (Veröffentlichungen) | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Ehrliche Abdeckung

Was GitHub verweigert oder nicht beantwortet, erscheint als **nicht geprüft**, nie als in Ordnung; frühere Befunde dieses Bereichs bleiben. Viele Einstellungen brauchen administratives Leserecht: Der Bericht nennt die Berechtigung je Gruppe und die verweigerten. Von einem Webhook wird nur der Host gespeichert, von einem Secret nur Name und Daten. Releases werden mit früher Gesehenem verglichen, die erste Abfrage merkt sich nur. Archivierte Repositorys und Forks werden übersprungen.

## Grundlinie und Optionen

`posture.profile` ist basic oder strict. `posture.types` ordnet Mustern eine Art zu (`standard`, `library`, `internal`, `sandbox`) mit eigener Grundlinie; `posture.skip` lässt Prüfungen aus. `posture.release_branches` sind Muster zu schützender Branches. `posture.deploy_max_days` und `posture.stored_max_days` legen Alter fest. Erst auf Wunsch: `posture.audit_log` (Audit-Log, GitHub Enterprise), `posture.review_sample` (ohne Genehmigung gemergte Änderungen), `posture.runner_runs` (tatsächlich ausgeführter Härtungsschritt). `posture.releases` überwacht ersetzte Dateien und verschobene Tags; `posture.release_window` legt das Zeitfenster fest.

## Wo man es sieht

Der Sicherheits-Reiter der Wächter zeigt Befunde, die Reife der Sicherheitskette je Repository, einen Tagesverlauf und die Berechtigungen. `posture.alerts` bringt jeden Befund zu den Warnungen, wo er stummgeschaltet werden kann. API: `GET /api/posture`. Befehlszeile:

```
posture status
posture matrix
posture check --repo-name my-repo
```

## Grenzen

Feingranulare Token der Mitglieder werden nicht gelesen (GitHub listet sie nur einer GitHub App), und eine zweite schreibende App wird nicht verwaltet. Die Organisationsprüfungen wurden nur mit erfundenen Antworten getestet.
