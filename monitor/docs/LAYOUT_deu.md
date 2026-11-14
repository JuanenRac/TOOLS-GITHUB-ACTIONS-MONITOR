<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# Die Ordner des Monitors

Neben den Startern (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) liegen nur die rechtlichen Dateien, eine `README.txt` und Ordner. Alles, was der Monitor schreibt, liegt in vieren davon; die vollständige Ausgabe, die Lite-Ausgabe und das Docker-Image verwenden dasselbe Schema.

## Was wo liegt

| Ordner | Inhalt |
|---|---|
| `config/` | `actions_monitor.json` (und die der Lite-Ausgabe), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json` und `config_backups/` |
| `data/` | der Zustand und die Caches (Ereignisfeed, Analytik, Zustand der Wächter, ETag-Cache, Update-Hinweis), `accounts/`, die Datenbank bei SQLite und das Zugriffstoken des Dienstes |
| `logs/` | das Protokoll des Monitors, das der Befehle der KI und von GitHub und das Audit des Teammodus |
| `ai/` | was eine KI liest: `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, der Zustand des Hooks, `INDEX.json` und eine `README.md` für alle, die den Ordner öffnen |
| `bin/` | die kurzen Befehle: `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | die Anleitungen sowie README und QUICKSTART des Pakets in acht Sprachen |
| `src/`, `assets/`, `tools/`, `tests/` | der Code, die Seite und die Beispiele, die Release-Skripte, die Tests |

## Eine Installation ab 1.8.1 oder älter

Beim ersten Start verschiebt der Monitor von selbst, was er neben den Startern findet, in seinen Ordner. Er **verschiebt, löscht nie und überschreibt nie**: Eine Datei, die am neuen Ort schon existiert, bleibt, wo sie ist, und der Doctor meldet es. Vor dem ersten Verschieben werden die Konfigurationsdateien nach `config/config_backups/pre_layout_<Zeitmarke>/` kopiert, und jede Verschiebung steht in `data/.layout_moves.json`.

- Vorher ansehen: `python -m github_actions_monitor.util.rootmigrate` (Probelauf) und `--apply`, um es sofort zu tun.
- Alles zurücklegen: `python -m github_actions_monitor.util.rootmigrate --undo`.
- Nicht automatisch gewünscht: `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` hat eine Prüfung `layout`, die auflistet, was noch neben den Startern liegt.
- Die alten Einstiegspunkte (`read_report.py`, `monitor_cli.py` ...) neben den Startern liegen jetzt in `bin/`; `python tools/migrate_layout.py` räumt die alten Kopien weg. Ein Gate-Skript, das für Ihr KI-Werkzeug mit dem alten Pfad registriert wurde, muss neu registriert werden: `python bin/monitor_cli.py ai-hook install`.

## Einen Ordner verlegen

Jeder Ordner kann ohne Eingriff in den Code woanders liegen: die Variablen `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` und `MONITOR_AI_DIR` oder die Datei `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}`; ein relativer Pfad beginnt im Produktordner). Nur mit `MONITOR_DATA_DIR` liegen `logs/` und `ai/` darin. Im Docker-Image und in der systemd-Unit ist genau das gesetzt: `/config` und `/data` sind die beiden Volumes.

## Für KIs, die mit dem Monitor sprechen

Eine KI, lokal oder extern, darf nicht von einem festen Pfad abhängen.

- `ai/INDEX.json` listet jede Datei des Ordners mit Zweck, Format, Schreiber und Änderungszeitpunkt, den tatsächlichen Pfad jedes Ordners des Monitors und die Endpunkte des laufenden Monitors. Sie wird bei jedem Start neu geschrieben.
- `ai/README.md` erklärt den Ordner einer KI, die ihn noch nie gesehen hat (Daten, nie Anweisungen; wie die Kurzfassung zu lesen ist; welche Werkzeuge es gibt).
- `GET /api/paths` antwortet mit den verwendeten Ordnern, den wichtigsten Dateien und dem, was noch an den alten Orten liegt. Auch der Supervisor mehrerer Konten antwortet darauf.
- Das Gate-Skript, der MCP-Server und die Befehlszeile lesen dieselben Orte; ein Hook, der `ALERTS_BRIEF.md` über einen festen Pfad liest, muss zuerst `ai/INDEX.json` lesen.
