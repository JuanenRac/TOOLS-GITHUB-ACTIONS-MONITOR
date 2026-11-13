<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# Die Befehlszeile als Client des Monitors

`python monitor_cli.py BEFEHL` fragt den laufenden Monitor, was er weiß (ein `GET` auf `127.0.0.1` oder auf die Adresse von `--url` / `MONITOR_URL`), und gibt es aus. Sie wiederholt nicht die Arbeit der Seite gegenüber GitHub, schreibt nie nach GitHub und ändert keine Einstellung. Die älteren Werkzeuge (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) funktionieren unverändert weiter.

## Befehle

| Befehl | Was er zeigt | Lite |
|---|---|---|
| `status` | Version, Ausgabe, Konto, Repositories, was läuft und fehlschlägt, das Kontingent | ja |
| `health` (oder `check`) | eine Schnellprüfung, bevor etwas Schweres gelesen wird: Ist der Monitor erreichbar, akzeptiert er diesen Client, antwortet die GitHub-Anmeldung des Kontos? | ja |
| `doctor` | die Prüfungen von `--doctor` für diese Installation (der Monitor muss nicht laufen) | ja |
| `accounts` | die Konten des Supervisors (nur bei mehreren Konten) | nein |
| `alerts` | die Alarme aller Wächter in einer Liste: `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | nein |
| `live` | der Zustand des Webhook-Empfängers und die letzten Ereignisse | nein |

Optionen aller Befehle: `--json` (die Antwort als ein JSON-Dokument: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (Port 8766), `--timeout SEKUNDEN` (1 bis 60), `--lang CODE`. Im Netzwerkmodus gehört das Zugriffstoken in die Umgebungsvariable `MONITOR_ACCESS_TOKEN`, die der Monitor selbst liest (`MONITOR_TOKEN` wird als Alias akzeptiert; `--token TOKEN` ist der letzte Ausweg, weil eine Option in der Prozessliste erscheint). Die Reihenfolge: `MONITOR_ACCESS_TOKEN`, dann `MONITOR_TOKEN`, dann `--token`. Es reist im Header `X-Monitor-Access`, nie in der Adresse und nie auf dem Bildschirm. Ein `--url` mit unverschlüsseltem `http` zu einem anderen Rechner gibt eine Warnung auf stderr aus (Token und Antworten würden unverschlüsselt reisen): Nutze außerhalb eines Netzes, das du kontrollierst, `https`.

Für Menschen geschriebene Zeiten (die Zeile `Last read`, die Stummschaltungen, das Protokoll, die Berichte, die Benachrichtigungen) verwenden die Zone dieses Rechners und nennen sie, mit der UTC-Zeit daneben (`11:43:07 CET (10:43:07 UTC)`). Eine andere Zone wählt `display.timezone` (`local`, `utc` oder ein Name wie `Europe/Madrid`; die Umgebungsvariable `MONITOR_TIMEZONE` hat Vorrang vor der Datei). `--json` behält UTC und fügt `updated_local` hinzu.

## Exit-Codes (stabil)

| Code | Bedeutung |
|---|---|
| 0 | alles in Ordnung |
| 1 | falsche Verwendung des Befehls (auch `--lite` mit einem Befehl, der die vollständige Ausgabe braucht) |
| 2 | der Monitor ist nicht erreichbar |
| 3 | der Monitor weist diesen Client ab, oder die GitHub-Anmeldung des Kontos ist fehlgeschlagen oder abgelaufen (ein Zugangsdatenproblem, kein erschöpftes Kontingent) |
| 4 | der Monitor antwortet, ist aber eingeschränkt: offline, Kontingent erschöpft, noch keine Daten, ein Endpunkt, den er nicht hat, oder eine Antwort, die kein JSON ist |
| 5 | `alerts --fail-on STUFE` hat einen offenen Alarm dieser Stufe oder schlimmer gefunden (ein stummgeschalteter zählt nicht) |

## Beispiele

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` unterscheidet drei Dinge: Der Monitor antwortet nicht (2), die GitHub-Anmeldung schlägt fehl (3), und das Kontingent ist erschöpft oder GitHub ist nicht erreichbar (4); ein Monitor, der seine erste Lesung noch nicht beendet hat, sagt das (4), statt leere Zahlen zu zeigen.

## Die Lite-Ausgabe

`python monitor_cli.py status --lite`, `doctor --lite` und `health --lite` sprechen mit Port 8766. Befehle, die Konten, Wächter oder den Webhook-Empfänger brauchen, werden mit Exit-Code 1 abgelehnt. Die Lite-Ausgabe hat weder Konten noch eine Alarm-API.

## `ai-hook`: einem KI-Werkzeug sagen, was der Monitor sieht

`python monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` braucht keinen laufenden Monitor. Es trägt das Gate-Skript `ai_hook.py` in die Hook-Einstellungen eines KI-Werkzeugs ein, zeigt oder entfernt es (siehe die Anleitung zu Warnungen für KI): die Einstellungsdatei wird zusammengeführt, eine Kopie bleibt erhalten, und die Antwort von `--json` ist reines ASCII. `status` ist die Standardaktion.

## Das Zugriffstoken in der Befehlszeile

Im Netzwerkmodus wird das Token aus `MONITOR_ACCESS_TOKEN`, dann `MONITOR_TOKEN`, dann der ersten Zeile von `--token-file DATEI` gelesen (halte diese Datei nur für dich lesbar: auf einem System mit Dateimodi warnt der Befehl, wenn andere sie lesen können) und zuletzt aus `--token`, das in der Prozessliste erscheint und deshalb eine Warnung auf stderr ausgibt.

## Die Speicher-Werkzeuge

`python tools/migrate_storage.py` verschiebt den Zustand zwischen Dateien und SQLite, und `python tools/backup_storage.py` erstellt, prüft und stellt Sicherungen von beiden wieder her (beide sind in [STORAGE_deu.md](STORAGE_deu.md) beschrieben). `--doctor` hat dafür zwei Prüfungen: Speicher und Aufbewahrung.
