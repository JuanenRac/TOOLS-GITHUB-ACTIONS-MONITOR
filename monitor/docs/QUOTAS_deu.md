<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | [🇪🇸 Español](QUOTAS_spa.md) | [🇫🇷 Français](QUOTAS_fra.md) | [🇮🇹 Italiano](QUOTAS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# Kontingente und Tarife

Den Monitor nutzt jede Art von Konto, deshalb nimmt er keine an. Die Zahlen unten stehen in `monitor/quotas.json` (bearbeiten Sie die Datei, um GitHubs Änderungen ohne neue Monitor-Version zu übernehmen) und wurden mit der öffentlichen Dokumentation von GitHub abgeglichen; sie ändern sich, sehen Sie sie also als Ausgangspunkt und schauen Sie in die in der Datei genannten Seiten. Wählen Sie Ihren Tarif unter **Einstellungen > Grundlagen** (`account.plan`); solange er *unbekannt* ist, wird keine Kontingentzahl gezeigt.

## Das API-Kontingent

| Anmeldung | Aufrufe pro Stunde |
|---|---|
| Keine Anmeldung | 60 pro Stunde und Adresse |
| Eigene Anmeldung (`gh auth login`) oder persönliches Token | 5.000 |
| Token eines Workflows (innerhalb von Actions) | 1.000 pro Repository (15.000 bei Enterprise Cloud) |
| Eine App in Enterprise Cloud | 15.000 |
| Eine GitHub App sonst | 5.000, wächst mit der Installation bis 12.500 |

Die Seite zeigt das echte Limit aus den Headern von GitHub (`X-RateLimit-*`), nie ein angenommenes 5.000: so funktioniert auch GitHub Enterprise Server (`GH_HOST`). Ohne Anmeldung (60 pro Stunde) rät sie zu `gh auth login`. Es gibt auch ein *sekundäres* Limit (höchstens 100 gleichzeitige Anfragen und Bursts): antwortet GitHub damit, wartet der Monitor mindestens eine Minute, verdoppelt die Wartezeit bis fünf Minuten und hämmert nie.

## Actions-Minuten

| Tarif | Monatlich inklusive (als Geld) | In Linux-Minuten | Artefakt-Speicher |
|---|---|---|---|
| Free | 12 $ | 2.000 | 500 MB |
| Pro | 18 $ | 3.000 | 1 GB |
| Team | 18 $ | 3.000 | 2 GB |
| Enterprise Cloud | 300 $ | 50.000 | 50 GB |

**Öffentliche Repositorys kosten in keinem Tarif Minuten** (selbst gehostete Runner auch nicht); größere Runner werden immer berechnet. Eine Minute wird mit dem Satz ihres Systems multipliziert: Windows etwa das 1,67-Fache einer Linux-Minute, macOS etwa das 10,3-Fache (Sätze pro Minute in `quotas.json`: 0,006 $ Linux, 0,010 $ Windows, 0,062 $ macOS). Was der Monitor unter **Einstellungen > Grundlagen > Tarif und Kontingente** zeigt, ist eine **Schätzung**: die Dauer der Runs der letzten 24 Stunden, auf die Minute aufgerundet, nur für private Repositorys, mit dem in `quota.default_runner` angenommenen System, und das Tempo eines Tages mal den Tagen des Monats. Echte Zahlen kommen nur vom optionalen Schalter `quota.billing_api` (standardmäßig aus, nur lesend, braucht eine Anmeldung mit Abrechnungsrecht; bei 403 oder 404 bleibt die Schätzung und sagt es). Eine Warnung geht einmal im Monat über die Benachrichtigungen bei `quota.warn_percent` (75 %) und `quota.alert_percent` (90 %) der inklusiven Minuten.

## Parallelität und Grenzen

| Tarif | Jobs gleichzeitig | davon macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

Das Panel vergleicht laufende und wartende Jobs mit dem Limit Ihres Tarifs und warnt bei 90 % oder wenn Jobs bei vollem Limit warten. Ein Job darf auf einem GitHub-Runner höchstens 6 Stunden laufen (das Panel listet Jobs über 80 % davon), ein Workflow-Run dauert höchstens 35 Tage, eine Matrix hat bis zu 256 Jobs.

## Was nicht abgedeckt ist

Preise für zusätzliche Minuten, größere Runner, genutzter Speicher, Codespaces und Packages werden nicht verfolgt; die Tariftabelle ist ein Ausgangspunkt, und die macOS-Limits ändern sich. Nichts davon wurde bisher gegen einen echten Abrechnungsbericht erprobt: das Lesen von `usageItems` folgt der öffentlichen Beschreibung und fällt leise zurück.
