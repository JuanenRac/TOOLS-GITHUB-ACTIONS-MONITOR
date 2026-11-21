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

## `watch branch`: der Commit, den du gerade hochgeladen hast

```
git push && python bin/monitor_cli.py watch branch
python bin/monitor_cli.py watch branch --repo acme/widgets --branch main --wait 300
python bin/monitor_cli.py watch branch --single-pass --format json
```

`watch branch` fragt Git, auf welchem Repository (`origin`), Branch und Commit der aktuelle Ordner steht, und verfolgt im Monitor die Workflows dieses Commits: wartet, bis sie erscheinen, zeigt sie während des Laufs und endet von selbst. Der Exit-Code ist **0**, wenn jeder Workflow bestanden hat, und **1**, wenn einer fehlgeschlagen ist, abgebrochen wurde oder nicht rechtzeitig fertig wurde (ein Fehler wird nicht von einer Zeitüberschreitung unterschieden, damit `git push && monitor_cli.py watch branch` in einem Skript funktioniert). Es liest die Läufe, die der Monitor schon hat, nie GitHub, und verbraucht also kein Kontingent; das Repository muss eines sein, das der Monitor überwacht. Die Adresse des Remotes wird nur gelesen, um Besitzer und Namen zu finden, und nie ausgegeben (sie kann ein Token enthalten).

- `--repo BESITZER/NAME` und `--branch NAME` ersetzen, was Git sagt. Mit einem von beiden (oder ohne Commit) wird statt der Läufe eines Commits der neueste Lauf jedes Workflows des Branches verfolgt.
- `--single-pass` (oder `--once`): einmal lesen und beenden, mit dem Code dieses Moments (1, solange die Läufe nicht fertig sind).
- `--wait SEKUNDEN`: wie lange auf das Ende der Läufe gewartet wird, bevor mit 1 aufgegeben wird (10 bis 86400). Ohne sie gilt die Einstellung `cli.watch.branch_timeout_seconds` (900).
- Ein losgelöster Commit hat keinen Branch: gib `--branch` an. Ein Ordner ohne Remote namens `origin` auf GitHub braucht `--repo`.

## `monitor N`: ein Bildschirm, der sich aktualisiert

`monitor_cli.py monitor [N]` ist `watch status`, das alle N Sekunden neu liest (eine Zahl von 1 bis 9999, auf `cli.watch.min_interval_seconds` angehoben; ohne N der Standard von `cli.watch.default_interval_seconds`). Die übrigen Optionen funktionieren wie bei `watch` (`--format`, `--no-clear`, `--url`, `--status-codes operator` ...), und Strg-C beendet es mit 0.

## `doctor --latency`: wie spät die Ereignisse sind

`monitor_cli.py doctor --latency` fügt dem Doctor eine Prüfung hinzu. Sie liest die Ereignisse des Kontos (dieselbe Liste wie der kostenlose Änderungsdetektor `events_feed`) und für die letzten Pushes den Lauf desselben Commits und nennt die Antwortzeit, den Median und die größte Verzögerung zwischen Laufbeginn und Ereignis sowie die längste Wartezeit einer Änderung mit Ihrem `events_feed.interval_seconds` (im Feld `data` von `--json`). Sie liest nur: Auf GitHub wird nichts angelegt, weder Test-Issues noch Testläufe. Ein fehlgeschlagener Lesezugriff ergibt die Warnung „nicht auswertbar“ mit der Ursache, nie einen Fehler des Monitors. Ab 120 Sekunden Verzögerung warnt die Prüfung.

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

### Die Exit-Codes von `status` für einen Betreiber

Standardmäßig behält `status` die Codes der Tabelle oben, kein Skript ändert sich. Mit `--status-codes operator` (oder der Einstellung `cli.status_codes` auf `operator`) sagt der Befehl nur drei Dinge: **0** gesund, **1** nichts liefert (der Monitor ist nicht erreichbar oder lehnt die Zugangsdaten ab) und **2** läuft, braucht aber Aufmerksamkeit. Aufmerksamkeit heißt: der Monitor erreicht GitHub nicht, es gibt noch keine Daten, die Zugangsdaten sind blind, die Aktualisierung ist pausiert, weil das Kontingent unter seiner Untergrenze liegt, die Antwort enthält einen Fehler, eine Antwort, die nicht die eines Monitors ist, oder **der Code auf der Platte hat eine andere Version als der laufende Prozess** (ein Update wurde eingespielt und der Monitor nicht neu gestartet; `/api/health` meldet es als `code_stale`, und `--doctor` hat die Prüfung `running`). Ein Aufruffehler bleibt 1. Die Gründe stehen im Feld `attention` von `--json`. Fehler roter Workflows gehören nicht dazu: dafür `alerts --fail-on`. `watch status` folgt denselben Codes auch bei einem Lesefehler: Ein nicht erreichbarer Monitor oder eine abgelehnte Anmeldung beendet die Schleife mit 1, eine nicht lesbare Antwort mit 2.

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
| `cli.status_codes` | `classic` | die Exit-Codes von `status`: `classic` (die der Tabelle) oder `operator` (0 gesund, 1 nichts liefert, 2 läuft, braucht aber Aufmerksamkeit) |
| `cli.watch.branch_timeout_seconds` | 900 | wie lange `watch branch` auf das Ende der Läufe des Commits wartet (10 bis 86400) |

## Was diese Version nicht tut

- `completions` hat kein `--install`: Es schreibt nie in die Dateien eines Benutzers.
- Es gibt keinen Befehl `proposals`: Der Monitor hat noch keine Route für Vorschläge, auf die er wirken könnte.

## Umgeleitete Ausgabe, Farbe und Breite

- Ohne Terminal (Umleitung, `tee`, Pipe, cron) schreibt der Befehl keine Escape-Sequenz, nimmt die Breite aus `COLUMNS`, wenn es eine Zahl ist, sonst 80, und Text von GitHub (ein Titel, ein Name) wird von den Escape-Sequenzen befreit, die er tragen könnte.
- `--color auto|always|never` (Standard `auto`): `auto` schreibt Farbe nur im Terminal und nie, wenn `NO_COLOR` gesetzt (und nicht leer) oder `TERM=dumb` ist; `always` schreibt sie immer; `never` nie. Nur die Kopfzeile von `--format table` wird gefärbt (fett); `json` und `ndjson` bleiben unberührt.
- Ein Leser, der früher schließt (`monitor_cli.py alerts --format plain | head -1`), beendet den Befehl still: keine Traceback- und keine Fehlerausgabe.

## `metrics`: die Zahlen für cron und für Mail

`monitor_cli.py metrics` schreibt die Zahlen des Monitors als je eine Zeile `name=wert`, in fester Reihenfolge und ohne etwas anderes auf der Standardausgabe: `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` und `offline`. Eine unbekannte Zahl wird weggelassen, nie als 0 geschrieben. Es liest den Monitor, nie GitHub.

Mit `--if-problem` schreibt es nichts und endet mit 0, wenn kein Workflow rot ist und keine Warnung der Stufe `--fail-on` (Standard error) oder schlimmer vorliegt; sonst schreibt es die Zahlen und endet mit 5. cron schickt jede Ausgabe per Mail, so kommt diese Zeile nur an dem Tag, an dem etwas nicht stimmt: `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. Ein nicht erreichbarer Monitor ist nie Stille: Der Fehler geht auf die Fehlerausgabe und der Code ist 2.
