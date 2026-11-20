<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# Die Befehlszeile für den Betreiber

Die Grundlagen von `monitor_cli.py` stehen in [CLI_deu.md](CLI_deu.md). Diese Seite ist für alle, die im Terminal leben: wie die Antworten geschrieben werden (`--format`), wie man beobachtet (`watch`), wie man Befehle vervollständigt (`completions`), die Exit-Codes und die Adresse für einen Fernseher (`kiosk`). Alles hier liest die API des Monitors auf diesem Rechner (oder den von `--url`); nichts schreibt nach GitHub, und nichts verbraucht das Kontingent.

## Formate: `--format`

| Format | Was Sie bekommen |
|---|---|
| `text` | was jeder Befehl schon immer geschrieben hat. Das ist der Standard. |
| `table` | die Datensätze als Spalten, die in die Breite des Terminals passen (japanische und chinesische Zeichen zählen als zwei Zellen). Es gibt keine Farbe, daher wird `NO_COLOR` beachtet. |
| `plain` | ein Datensatz pro Zeile, die Felder durch einen Tabulator getrennt, ohne Kopfzeile: für `grep`, `cut` und `awk`. Ein Tabulator oder Zeilenumbruch in einem Text wird zu einem Leerzeichen. |
| `json` | das Dokument `{"ok", "exit", "data"}`. `--json` ist dasselbe. |
| `ndjson` | ein JSON-Objekt pro Zeile, eines pro Datensatz (ein Alarm, ein Konto, ein Repository, ein Ereignis). Ein Befehl, der nur eine Sache beantwortet (`status`, `health`), liefert eine Zeile. |

`--format` hat Vorrang vor `--json`, und beide haben Vorrang vor der Einstellung `cli.default_format` (Standard `text`). Die drei strukturierten Formate entstehen aus demselben Dokument wie `--json`, sie widersprechen sich also nie. Eine leere Liste gibt in `ndjson` und `plain` nichts aus.

## `watch`: dieselbe Abfrage immer wieder

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` wiederholt die Abfrage des Befehls. Es liest die API des Monitors, nicht GitHub, ein kurzes Intervall verbraucht also kein Kontingent. Die Optionen:

- `--interval SEKUNDEN`: die Pause zwischen zwei Abfragen. Die Untergrenze ist die Einstellung `cli.watch.min_interval_seconds` (standardmäßig 2): ein kürzeres Intervall wird darauf angehoben. Ohne `--interval` gilt `cli.watch.default_interval_seconds` (5).
- `--once`: einmal lesen und beenden (der Exit-Code ist der des Befehls).
- `--exit-on-change`: die Schleife endet mit dem Exit-Code **6**, wenn das Beobachtete nicht mehr dem der ersten Abfrage entspricht (die Menge der Alarme oder die Zahlen des Status). Eine tickende Uhr ist keine Änderung. Ohne die Option erscheint der Code 6 nie.
- `--no-clear`: den Bildschirm zwischen zwei Abfragen nicht löschen (er wird nur in einem Terminal und nur in `text` und `table` gelöscht).
- Ein Monitor, der nicht gelesen werden kann, wird mit immer längerer Pause erneut versucht (das Intervall verdoppelt, höchstens eine Minute), und der Fehler geht auf die Standardfehlerausgabe. **Strg-C** beendet die Schleife mit dem Code 0.

## `completions`: Befehle vervollständigen

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

Das Skript wird aus dem echten Parser der Befehlszeile erzeugt und bietet genau die Befehle, Wörter und Optionen an, die es gibt: Eine neue Option kann nicht vergessen werden, und ein Test vergleicht beides. Der Befehl **gibt nur aus**; er ändert keine Ihrer Dateien und braucht keinen Monitor. Legen Sie die Ausgabe dort ab, wo Ihre Shell Vervollständigungen liest, wie oben.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | alles in Ordnung (auch Strg-C in `watch`) |
| 1 | falsche Verwendung des Befehls |
| 2 | der Monitor ist nicht erreichbar |
| 3 | der Monitor oder GitHub lehnt die Anmeldedaten ab |
| 4 | der Monitor antwortet, ist aber eingeschränkt (offline, Kontingent erschöpft, noch keine Daten) oder die Antwort ist nicht lesbar |
| 5 | `alerts --fail-on STUFE` hat Alarme dieser Stufe oder schlimmer gefunden |
| 6 | `watch --exit-on-change` hat eine Änderung gesehen (nur wenn diese Option gegeben ist) |

Die Codes 0 bis 5 sind die aus [CLI_deu.md](CLI_deu.md); ein Test hält diese Tabelle und den Code in Einklang.

## Beispiele mit `jq`

Diese Beispiele verwenden nur Felder, die zur stabilen Form der Antworten gehören, und ein Test führt sie gegen einen falschen Monitor aus (wenn `jq` installiert ist).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`: die Adresse für einen Fernseher oder eine Wand

`monitor_cli.py kiosk [ops|team|release|quiet]` gibt die Adresse des Monitors für einen Bildschirm aus, den niemand berührt. Siehe [KIOSK_deu.md](KIOSK_deu.md).

## Einstellungen

| Einstellung | Standard | Bedeutung |
|---|---|---|
| `cli.default_format` | `text` | das Format, wenn weder `--format` noch `--json` gegeben ist: `text`, `table`, `plain`, `json` oder `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | die kürzeste Pause von `watch` (1 bis 3600) |
| `cli.watch.default_interval_seconds` | 5 | die Pause von `watch`, wenn `--interval` nicht gegeben ist (1 bis 3600) |

## Was diese Version nicht tut

- `completions` hat kein `--install`: Es schreibt nie in die Dateien eines Benutzers.
- Es gibt keinen Befehl `proposals`: Der Monitor hat noch keine Route für Vorschläge, auf die er wirken könnte.
