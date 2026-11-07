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
| **Version** | **1.5.1** · [alle Releases](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Voraussetzung** | Python 3.11+ und die GitHub-CLI (`gh auth login`); sonst nichts |
| **Öffnet** | eine Seite nur auf `127.0.0.1`, in acht Sprachen |
| **Schreibt auf GitHub** | nie von selbst: nur Stapelbefehle, die du mit ausdrücklichem `--go` startest |
| **Exportiert** | `ci_red.json`, Prometheus-Metriken und JSON für Grafana (alles aus, bis du es einschaltest) |

## Screenshots

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

*Demodaten: Die Repositories und Namen in den Bildern sind erfunden.*

## Was es kann

- **Rot oder nicht, nach einer einzigen Regel**: der letzte beendete Lauf jedes Workflows auf dem Standard-Branch. Abgebrochene und übersprungene Läufe verdecken nie einen früheren Fehler.
- **Wächter**: Sicherheitswarnungen, Repository-Hygiene, alte Pull Requests, veröffentlichungsbereite Versionen, noch nicht signierte Builds und ein Bericht in einfacher Sprache.
- **Einstellungsseite**: Pfade, Intervalle, Kontingente und Schalter im Browser ändern; nur eine feste Liste geprüfter Schlüssel, mit Sicherung vor jedem Speichern.
- **Diagramme und Verlauf**: Rechenminuten, Fehler und Erfolge mit animierten Balken und Tagesverlauf (berücksichtigt reduzierte Bewegung).
- **Acht Sprachen** (en, es, de, fr, it, ja, zh, pt) mit Englisch als Basis; Wechsel in den Einstellungen.
- **Ausgaben für Dashboards**: `ci_red.json`, ein Prometheus-Endpunkt und eine JSON-Quelle für Grafana samt importierbarem Grafana-Dashboard.
- **Stapelwerkzeuge**: viele Builds auf einmal planen und starten; ohne `--go` wird nichts ausgelöst.

## Architektur

<p align="center"><img src="images/architecture.svg" alt="Architektur" width="100%"></p>

## Schnellstart

1. Installiere Python 3.11 oder neuer und die [GitHub-CLI](https://cli.github.com/) und führe `gh auth login` aus.
2. Lade dieses Repository (oder das Zip des neuesten Releases) herunter und öffne den Ordner `monitor`.
3. Starte es: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS Doppelklick auf `MONITOR_GITHUB_ACTIONS.command`, oder überall `python actions_monitor.py`.
4. Öffne die ausgegebene Adresse (`http://127.0.0.1:<Port>`). Beim ersten Start entsteht `actions_monitor.json` aus dem Beispiel.
5. Öffne **Einstellungen**, um dein GitHub-Konto, die Ökosysteme (Gruppen von Repositories nach Namenspräfix) und alles Weitere festzulegen.

> Aktualisierst du von einer Version vor 1.5.0? [`monitor/docs/MIGRATING_deu.md`](monitor/docs/MIGRATING_deu.md)

## Einstellungen

Alles liegt in `actions_monitor.json` (aus `actions_monitor.example.json` erzeugt). Der Tab **Einstellungen** bearbeitet sie sicher; Tokens und Geheimnisse werden nie angezeigt oder gespeichert. Ökosysteme, Build-Ziele und Stapelprofile sind eigene Dateien, auf die du verweist (`ecosystems_file`, `targets_file`, `profiles_file`); neutrale `*.example.json`-Vorlagen liegen bei. Vollständige Referenz: [`monitor/docs/SETTINGS_deu.md`](monitor/docs/SETTINGS_deu.md).

## Ausgaben für Grafana und Dashboards

Standardmäßig aus, nur lokal (`127.0.0.1`) und ohne zusätzliches Token. Nach dem Einschalten in den Einstellungen gibt es `/metrics` (Prometheus-Format), `/api/outputs/grafana.json` und `/api/outputs/dashboard.json` sowie ein importierbares Grafana-Dashboard in [`monitor/docs/grafana`](monitor/docs/grafana). Details: [`monitor/docs/OUTPUTS_deu.md`](monitor/docs/OUTPUTS_deu.md). Das Format von `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_deu.md`](monitor/docs/CI_RED_SCHEMA_deu.md).

## Sicherheit

- Es lauscht nur auf `127.0.0.1` und weist Anfragen ab, deren `Host` oder `Origin` nicht lokal ist. Nie an `0.0.0.0` binden: Es hat keine Anmeldung.
- Es speichert kein Token: Es nutzt dein eigenes `gh`.
- Es schreibt von selbst nichts auf GitHub. Nur `dispatch --go`, `dispatch --real` und `finalize --execute` schreiben, und nur wenn du sie startest.
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
├── monitor/                          das Programm
├── docs/                             Architektur, Screenshots
├── tools/                            Bild-Generatoren
├── images/                           Banner und Bilder
├── .github/                          CI und Formulare
├── CHANGELOG.md                      Änderungen je Version
├── LICENSE NOTICE AUTHORS            Lizenzen und Urheber
├── CONTRIBUTING.md SECURITY.md       mithelfen, melden
├── SUPPORT.md CODE_OF_CONDUCT.md     Support und Verhalten
└── monitor/
    ├── actions_monitor.py            lokaler Server
    ├── actions_monitor.html          die Webseite
    ├── sentinel_local.py             Warnungen, Bericht
    ├── surface.py readiness.py       Prüfungen, Bereitschaft
    ├── settings_api.py outputs.py    Einstellungen, Metriken
    ├── signstate.py sigverify.py     Signatur: Stand, Prüfung
    ├── read_report.py                Bericht im Terminal
    ├── gha_dispatch_all.py           Build-Stapel
    ├── events.py report_history.py   Ereignisse, Verlauf
    ├── ci_red.py export_status.py    Dateien für andere
    ├── i18n.py locales/              acht Sprachen
    ├── toolconfig.py workspace.py    Einstellungen, Klone
    ├── tests/                        Offline-Tests
    └── docs/                         Einstellungen, Grafana
```

## Dokumentation

- [`monitor/docs/SETTINGS_deu.md`](monitor/docs/SETTINGS_deu.md): alle Einstellungen
- [`monitor/docs/OUTPUTS_deu.md`](monitor/docs/OUTPUTS_deu.md): Metriken, Grafana und Exporte
- [`monitor/docs/CI_RED_SCHEMA_deu.md`](monitor/docs/CI_RED_SCHEMA_deu.md): das Format von ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_deu.md`](monitor/docs/CI_RED_BRIDGE_deu.md): ci_red.json in ein Dashboard bringen
- [`monitor/QUICKSTART_de.txt`](monitor/QUICKSTART_de.txt): erste Schritte, in acht Sprachen

## Mitwirken

Lies [CONTRIBUTING.md](CONTRIBUTING.md). Melde Fehler und Ideen mit den Issue-Formularen; Sicherheitsprobleme wie in [SECURITY.md](SECURITY.md) beschrieben.

## Urheber

Geschrieben von **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Lizenz

Der Code steht unter GPL-3.0-or-later, die Dokumentation unter CC BY-SA 4.0. Siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
