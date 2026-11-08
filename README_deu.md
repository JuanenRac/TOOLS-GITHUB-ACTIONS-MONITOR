<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <b>🇩🇪 Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Überwacht die Workflows aller deiner Repositories und zeigt dir auf einer lokalen Seite, was rot ist, was hängt und was auf dich wartet.

**GitHub Actions Monitor** ist ein kleines Programm, das auf deinem eigenen Rechner läuft. Es fragt GitHub über dein eigenes `gh`-Login nach den letzten Läufen jedes Workflows deiner Repositories, entscheidet, was wirklich rot ist, meldet Wichtiges (Sicherheit, Hygiene, fertige Releases, Kontingent) und zeigt alles auf einer Webseite, die nur dein Rechner öffnen kann. Es braucht nur Python und `gh`, speichert nie ein Token und liest standardmäßig nur.

## Auf einen Blick

| | |
|---|---|
| **Version** | **1.6.6** · [alle Releases](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Voraussetzung** | Python 3.11+ und die GitHub-CLI (`gh auth login`); sonst nichts (die Konsolenansicht nutzt das optionale Paket `rich`) |
| **Öffnet** | eine Seite nur auf `127.0.0.1`, in acht Sprachen |
| **Schreibt auf GitHub** | nie von selbst: nur Stapelbefehle, die du mit ausdrücklichem `--go` startest |
| **Exportiert** | `ci_red.json`, Prometheus-Metriken und JSON für Grafana (alles aus, bis du es einschaltest) |

## Screenshots

### Die Seite

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Jetzt" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Wächter" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Signatur-Warteschlange (Dringendstes zuerst)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analytik: Dauer, Wartezeit, Schritte und instabile Workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Diagramme" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositories" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Verlauf" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="Über" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Hilfe, durchsuchbar und offline" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Einstellungen · Grundlagen: Tarif, Kontingente und Erkennung" width="92%"></picture></p>

<details><summary><b>Einstellungen, Unterreiter für Unterreiter</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Einstellungen · Dieser Browser" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Einstellungen · Allgemein" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Einstellungen · Aktualisierung und Grenzen" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Einstellungen · Lesen und Cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Einstellungen · Wächter" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Einstellungen · Oberflächenprüfungen (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Einstellungen · Bereitschaft (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Einstellungen · Ordner und Dateien" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Einstellungen · Ausgaben für andere Werkzeuge" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Einstellungen · Externe KI für den Wächter" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Einstellungen · Eingehender Webhook" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Einstellungen · Benachrichtigungen" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Einstellungen · Analytik" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Einstellungen · Workflow-Linter" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Einstellungen · Konsolenansicht" width="92%"></picture></p>

</details>

<details><summary><b>Konsolenwerkzeuge</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>Die Lite-Ausgabe</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Jetzt" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Diagramme" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · Verlauf" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Einstellungen" width="92%"></picture></p>

</details>

Jedes Bild folgt dem hellen oder dunklen Design Ihrer GitHub-Seite.

*Demodaten: Die Repositories und Namen in den Bildern sind erfunden.*

## Was es kann

- **Rot oder nicht, nach einer einzigen Regel**: der letzte beendete Lauf jedes Workflows auf dem Standard-Branch. Abgebrochene und übersprungene Läufe verdecken nie einen früheren Fehler.
- **Wächter**: Sicherheitswarnungen, Repository-Hygiene, alte Pull Requests, veröffentlichungsbereite Versionen, noch nicht signierte Builds und ein Bericht in einfacher Sprache.
- **Einstellungsseite**: Pfade, Intervalle, Kontingente und Schalter im Browser ändern; nur eine feste Liste geprüfter Schlüssel, mit Sicherung vor jedem Speichern.
- **Diagramme und Verlauf**: Rechenminuten, Fehler und Erfolge mit animierten Balken und Tagesverlauf (berücksichtigt reduzierte Bewegung).
- **Acht Sprachen** (en, es, de, fr, it, ja, zh, pt) mit Englisch als Basis; Wechsel in den Einstellungen.
- **Ausgaben für Dashboards**: `ci_red.json`, ein Prometheus-Endpunkt und eine JSON-Quelle für Grafana samt importierbarem Grafana-Dashboard.
- **Stapelwerkzeuge**: viele Builds auf einmal planen und starten; ohne `--go` wird nichts ausgelöst.
- **Über und Hilfe in der Seite**: die **i**-Taste zeigt Version, Ausgabe, Links, Dateien, Zustand und eine Taste, die die Informationen für den Support kopiert; die **?**-Taste (oder die Taste `?`) öffnet die gesamte Dokumentation, durchsuchbar und in Ihrer Sprache, ohne Internet. Die Konsole kennt `--about` und `--help-topics` und eine interaktive Terminalanwendung mit Reitern (optional `textual`).
- **Hinweis auf eine neuere Version**: ein dezentes Abzeichen, wenn eine neuere Version erscheint; es liest nur einmal am Tag die öffentliche Release-Seite, installiert nie etwas und lässt sich abschalten (bei netzgetrennter Installation immer aus).
- **Kontingente für jedes Konto**: Tarif, abrechenbare Minuten (öffentliche Repositorys kosten nichts), API-Kontingent aus den Headern von GitHub, Parallelität und Jobs nahe dem 6-Stunden-Limit; die Zahlen stehen in einer bearbeitbaren Datei.

## Architektur

<p align="center"><img src="images/architecture.svg" alt="Architektur" width="100%"></p>

## Hier beginnen: welche Ausgabe?

| Wenn Sie ... wollen | Start | Port |
|---|---|---|
| nur sehen, was läuft und was fehlschlägt (**hier beginnen**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| das ganze Konto für Sie überwacht: Alarme, Releases, Signatur, Bereitschaft, Analytik | `MONITOR_GITHUB_ACTIONS` (mit dem [Wächter](monitor/docs/SENTINEL_deu.md)) | 8765 |

Das Konsolenfenster nennt die laufende Ausgabe in Titel und erster Zeile. Noch unsicher? `python actions_monitor.py --demo` öffnet die Seite mit erfundenen Daten, `--doctor` prüft Ihre Installation. [Ihre ersten fünf Minuten](monitor/docs/FIRST_STEPS_deu.md)

## Schnellstart

1. Installiere Python 3.11 oder neuer und die [GitHub-CLI](https://cli.github.com/) und führe `gh auth login` aus.
2. Lade dieses Repository (oder das Zip des neuesten Releases) herunter und öffne den Ordner `monitor`.
3. Starte es: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS Doppelklick auf `MONITOR_GITHUB_ACTIONS.command`, oder überall `python actions_monitor.py`.
4. Öffne die ausgegebene Adresse (`http://127.0.0.1:<Port>`). Beim ersten Start entsteht `actions_monitor.json` aus dem Beispiel.
5. Öffne **Einstellungen**, um dein GitHub-Konto, die Ökosysteme (Gruppen von Repositories nach Namenspräfix) und alles Weitere festzulegen.

> Aktualisierst du von einer Version vor 1.5.0? [`monitor/docs/MIGRATING_deu.md`](monitor/docs/MIGRATING_deu.md)

## Die Lite-Ausgabe

Ein zweites, einfacheres Produkt im selben Paket: die Seite dessen, was läuft und was fehlschlägt, ohne den Wächter. Für alle, die nur ihre Runs beobachten wollen.

|  | Vollständig | Lite |
|---|---|---|
| Start | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (dieselben drei) |
| Port | 8765 | 8766 |
| Reiter | Jetzt, Wächter, Diagramme, Repositorys, Verlauf, Einstellungen | Jetzt, Diagramme, Repositorys, Verlauf, kurze Einstellungen |
| Kopfzeile | alle Kacheln, Bereitschaft, Signatur | laufend, wartend, Fehler und Erfolge der 24 h, Rechenminuten, Issues, Rot auf main, Repositorys, Kontingent, Verbindung |
| Wächter (Warnungen, Releases, Signatur-Warteschlange, Bereitschaft, Linter) | ja | nein: er wird nicht einmal importiert |
| Analytik, Benachrichtigungen, Webhook, KI, Prometheus-/Grafana-Ausgaben | ja, aus bis Sie sie einschalten | nein: diese Pfade antworten mit 404 |
| Konfiguration | `actions_monitor.json` | `actions_monitor_lite.json` (beim ersten Start angelegt; der Wächter ist darin aus) |
| Zustandsdateien | `etag_cache.json`, `analytics_history.json`... | dieselben Namen mit der Endung `_lite` |

[`monitor/docs/LITE_deu.md`](monitor/docs/LITE_deu.md)

## Einstellungen

Alles liegt in `actions_monitor.json` (aus `actions_monitor.example.json` erzeugt). Der Tab **Einstellungen** bearbeitet sie sicher; Tokens und Geheimnisse werden nie angezeigt oder gespeichert. Ökosysteme, Build-Ziele und Stapelprofile sind eigene Dateien, auf die du verweist (`ecosystems_file`, `targets_file`, `profiles_file`); neutrale `*.example.json`-Vorlagen liegen bei. Vollständige Referenz: [`monitor/docs/SETTINGS_deu.md`](monitor/docs/SETTINGS_deu.md).

## Ausgaben für Grafana und Dashboards

Standardmäßig aus, nur lokal (`127.0.0.1`) und ohne zusätzliches Token. Nach dem Einschalten in den Einstellungen gibt es `/metrics` (Prometheus-Format), `/api/outputs/grafana.json` und `/api/outputs/dashboard.json` sowie ein importierbares Grafana-Dashboard in [`monitor/docs/grafana`](monitor/docs/grafana). Details: [`monitor/docs/OUTPUTS_deu.md`](monitor/docs/OUTPUTS_deu.md). Das Format von `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_deu.md`](monitor/docs/CI_RED_SCHEMA_deu.md).

## Sicherheit

- Es lauscht nur auf `127.0.0.1` und weist Anfragen ab, deren `Host` oder `Origin` nicht lokal ist. Nie an `0.0.0.0` binden: Es hat keine Anmeldung.
- Es speichert kein Token: Es nutzt dein eigenes `gh` (außer Sie schalten das optionale Token des Monitors unter Einstellungen > Erweitert ein).
- Es schreibt von selbst nichts auf GitHub. Nur `dispatch --go`, `dispatch --real` und `finalize --execute` schreiben, und nur wenn du sie startest.
- **Analytik**: p50 / p95 von Dauer, Wartezeit und jedem Schritt jedes Workflows, instabile Workflows (fehlgeschlagen, dann bestanden auf demselben Commit) und langsamer gewordene Workflows; Export nach Prometheus und Grafana.
- **Spart Kontingent und übersteht einen Ausfall**: bedingte Lesungen (ein 304 kostet nichts) und ein Modus mit letztem Bild und Offline-Banner, der von selbst weitermacht.
- **Eingehender Webhook und Benachrichtigungen**: signierte Ereignisse aktualisieren ein Repository in Echtzeit; optionale Nachrichten an Telegram, Discord, Slack, Matrix, MQTT oder eine lokale Adresse (nie ein Schreibzugriff auf GitHub).
- **Workflow-Linter und Konsolenansicht**: `lint_workflows.py` prüft `.github/workflows` vor dem Push; `tui.py` (optional, mit `rich`) zeigt ein Live-Raster in der Konsole.
- **KI-Assistent (standardmäßig aus)**: Zusammenfassungen, Einordnung und Erklärungen mit Ollama, einem OpenAI-kompatiblen Dienst, Anthropic oder `gh copilot`; Befehle nur aus einer geschlossenen Liste, ausgeführt erst nach Bestätigung jedes einzelnen.
- Die Einstellungsseite schreibt eine feste Liste geprüfter Schlüssel, nachdem eine Sicherungskopie gespeichert wurde.

## Tests

Sie brauchen weder Netz noch zusätzliche Pakete:

```
python -m unittest discover -s monitor/tests
```

## Repository-Struktur

<p align="center"><img src="images/repository-structure.svg" alt="Repository-Struktur" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                             das Programm
├── docs/                                Architektur, Bilder, Fahrplan
├── tools/                               Bilder, Anleitungen, Demo
├── deploy/                              Container-Beispiel
├── images/                              Banner und Bilder
├── .github/                             CI und Formulare
├── CHANGELOG.md                         Änderungen je Version
├── LICENSE NOTICE AUTHORS               Lizenzen und Urheber
├── CONTRIBUTING.md SECURITY.md          mithelfen, melden
├── SUPPORT.md CODE_OF_CONDUCT.md        Support und Verhalten
└── monitor/
    ├── actions_monitor.py               lokaler Server
    ├── actions_monitor.html             die Webseite
    ├── MONITOR_LITE_GITHUB_ACTIONS.*    die Lite-Ausgabe
    ├── sentinel_local.py                Warnungen, Bericht
    ├── surface.py readiness.py          Prüfungen, Bereitschaft
    ├── settings_api.py outputs.py       Einstellungen, Metriken
    ├── signstate.py sigverify.py        Signatur: Stand, Prüfung
    ├── read_report.py                   Bericht im Terminal
    ├── gha_dispatch_all.py              Build-Stapel
    ├── events.py report_history.py      Ereignisse, Verlauf
    ├── ci_red.py export_status.py       Dateien für andere
    ├── etagcache.py resilience.py       bedingte Lesungen, Verbindung
    ├── analytics.py lint_workflows.py   Dauer, flaky, Workflow-Linter
    ├── notifiers.py ai_actions.py       Benachrichtigungen, KI-Liste
    ├── tui.py migrate_state.py          Konsolenansicht, Migration
    ├── about.py  helpdocs.py            Über- und Hilfe-Panels
    ├── quota.py  quotas.json            Tarif, Minuten, Kontingente
    ├── modes.py  updatecheck.py         Arbeitsmodi, Versionshinweis
    ├── doctor.py  demo_mode.py          --doctor und --demo
    ├── discovery.py  banner.py          Erkennung, Ausgaben-Banner
    ├── tui_textual.py                   interaktives Terminal
    ├── i18n.py locales/                 acht Sprachen
    ├── toolconfig.py workspace.py       Einstellungen, Klone
    ├── tests/                           Offline-Tests
    └── docs/                            Anleitungen, Schemas
```

## Dokumentation

- [`monitor/docs/SETTINGS_deu.md`](monitor/docs/SETTINGS_deu.md): alle Einstellungen
- [`monitor/docs/OUTPUTS_deu.md`](monitor/docs/OUTPUTS_deu.md): Metriken, Grafana und Exporte
- [`monitor/docs/CI_RED_SCHEMA_deu.md`](monitor/docs/CI_RED_SCHEMA_deu.md): das Format von ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_deu.md`](monitor/docs/CI_RED_BRIDGE_deu.md): ci_red.json in ein Dashboard bringen
- [`monitor/docs/WEBHOOK_deu.md`](monitor/docs/WEBHOOK_deu.md): der eingehende Webhook
- [`monitor/docs/LITE_deu.md`](monitor/docs/LITE_deu.md): Die Lite-Ausgabe
- [`monitor/docs/NOTIFICATIONS_deu.md`](monitor/docs/NOTIFICATIONS_deu.md): Benachrichtigungen und der Adapter-Vertrag
- [`monitor/docs/AI_deu.md`](monitor/docs/AI_deu.md): der KI-Assistent: Anbieter, Sicherheit und Aktionen
- [`monitor/docs/ANALYTICS_deu.md`](monitor/docs/ANALYTICS_deu.md): Analytik, bedingte Lesungen und verlorene Verbindung
- [`monitor/docs/CONSOLE_TOOLS_deu.md`](monitor/docs/CONSOLE_TOOLS_deu.md): der Workflow-Linter und die Konsolenansicht
- [`monitor/docs/DEPLOYMENT_deu.md`](monitor/docs/DEPLOYMENT_deu.md): als Dienst betreiben, hinter einem Proxy, Berechtigungen
- [`monitor/QUICKSTART_de.txt`](monitor/QUICKSTART_de.txt): erste Schritte, in acht Sprachen
- [`monitor/docs/FIRST_STEPS_deu.md`](monitor/docs/FIRST_STEPS_deu.md): Ihre ersten fünf Minuten
- [`monitor/docs/SENTINEL_deu.md`](monitor/docs/SENTINEL_deu.md): der Wächter und seine Prüfungen A1-A13
- [`monitor/docs/QUOTAS_deu.md`](monitor/docs/QUOTAS_deu.md): Kontingente und Tarife von GitHub
- [`monitor/docs/MODES_deu.md`](monitor/docs/MODES_deu.md): Arbeitsmodi: normal, schnell und Turbo

## Mitwirken

Lies [CONTRIBUTING.md](CONTRIBUTING.md). Melde Fehler und Ideen mit den Issue-Formularen; Sicherheitsprobleme wie in [SECURITY.md](SECURITY.md) beschrieben.

## Urheber

Geschrieben von **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Lizenz

Der Code steht unter GPL-3.0-or-later, die Dokumentation unter CC BY-SA 4.0. Siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
