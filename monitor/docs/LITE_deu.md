<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# Die Lite-Ausgabe

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

So starten Sie sie: `MONITOR_LITE_GITHUB_ACTIONS.bat` unter Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` unter Linux, Doppelklick auf `MONITOR_LITE_GITHUB_ACTIONS.command` unter macOS oder `python actions_monitor.py --lite` (auch `MONITOR_MODE=lite`). Sie lauscht auf `127.0.0.1:8766`; die vollständige kann also gleichzeitig laufen.

Die kurzen Einstellungen enthalten das Konto (`github_owner`), die zu beobachtenden Repositorys und Ökosysteme (`repos`, `ecosystems`, `exclude`), die Aktualisierungszeit (`refresh_seconds`), die Sprache und das Design. „Rot auf main“ zählt die Workflows, deren letzter beendeter Run fehlschlug. Für den Wächter und den Rest starten Sie später die vollständige Ausgabe: Es muss nichts migriert werden. Beim ersten Start übernimmt `actions_monitor_lite.json` aus `actions_monitor.json` (falls vorhanden) das Konto, die zu beobachtenden Repositorys und Ökosysteme, die Katalogdateien und die Sprache und sagt das auf der Konsole; Wächter, KI, Webhook, Ausgaben und Benachrichtigungen werden nie übernommen. Ohne diese Datei beobachtet sie alle Ökosysteme (`"ecosystems": "all"`). Der Browser merkt sich das Design für jeden Port getrennt. Die Lite-Ausgabe schreibt weder `ci_red.json` noch eine Signatur-Warteschlange und führt eigene Zustandsdateien; falls Sie je beiden Ausgaben ein `sentinel.ci_red_file` geben, zeigen Sie nicht auf dieselbe Datei.

## Die Befehlszeile

`python monitor_cli.py status --lite`, `doctor --lite` und `health --lite` fragen den Lite-Monitor auf Port 8766 (siehe [CLI_deu.md](CLI_deu.md)); Befehle, die Konten oder Wächter brauchen, werden abgelehnt. Die Seite hat ebenfalls die Statusleiste am Fuß und die sortierbaren Tabellen.

## Speicherung

Die Lite-Ausgabe speichert nur gewöhnliche Dateien: keine Datenbank, kein Aufbewahrungsjob und keine der Optionen aus [STORAGE_deu.md](STORAGE_deu.md).
