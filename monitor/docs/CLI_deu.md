<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# Die Befehlszeile als Client des Monitors

`python bin/monitor_cli.py BEFEHL` fragt den laufenden Monitor, was er weiß (ein `GET` auf `127.0.0.1` oder auf die Adresse von `--url` / `MONITOR_URL`), und gibt es aus. Sie wiederholt nicht die Arbeit der Seite gegenüber GitHub, schreibt nie nach GitHub und ändert keine Einstellung. Die älteren Werkzeuge (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) funktionieren unverändert weiter.

## Befehle

| Befehl | Was er zeigt | Lite |
|---|---|---|
| `status` | Version, Ausgabe, Konto, Repositories, was läuft und fehlschlägt, das Kontingent | ja |
| `health` (oder `check`) | eine Schnellprüfung, bevor etwas Schweres gelesen wird: Ist der Monitor erreichbar, akzeptiert er diesen Client, antwortet die GitHub-Anmeldung des Kontos? | ja |
| `doctor` | die Prüfungen von `--doctor` für diese Installation (der Monitor muss nicht laufen) | ja |
| `backup` | die vollständige Sicherung der Installation (der Monitor muss nicht laufen): `backup create [DATEI] [--account ID]`, `verify DATEI [--deep]`, `restore DATEI [--account ID] [--to-dir ORDNER] [--force]`, `status`, `list`; `--encrypt` mit `--key-env NAME` verschlüsselt sie (optionale Bibliothek); siehe [OPS_deu.md](OPS_deu.md) | nein |
| `accounts` | die Konten des Supervisors (nur bei mehreren Konten) | nein |
| `alerts` | die Alarme aller Wächter in einer Liste: `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` listet die auf, die in dieser Zeit irgendwann offen waren, auch die geschlossenen (aus dem Verlauf, den der Monitor im Betrieb führt; ein Alarm gilt nach zehn Minuten Abwesenheit als geschlossen) | nein |
| `proposals` | die Aktionen, die die KI vorgeschlagen hat (`ai.actions.enabled`): `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (eine ID darf verkürzt werden). `approve` und `reject` halten nur die Entscheidung fest; `execute` führt aus, über dieselbe Tür wie die Seite, und braucht `ai.actions.execute`, mit `ai.actions.require_approval` zuvor eine Freigabe. Freigeben, Ablehnen und Ausführen gehen nur von diesem Rechner | nein |
| `score` | die Punktzahl des Kontos: Zahl, Buchstabe, Trend, Teile, Abdeckung und die Aufteilung nach Repository; `--compare` vergleicht sie mit dem Verlauf des Fensters | nein |
| `compare` | dieser Zeitraum gegen den davor: die Kennzahlen mit Änderung und Richtung, wer schlechter oder besser wurde; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv`; Exit 4, wenn eine Kennzahl zu wenig Daten hat, 5 mit `--fail-on`, wenn eine schlechter wurde; `--format csv` mit einem anderen Befehl ist eine falsche Verwendung (Exit 1) | nein |
| `api` | die Lese-API für Clients: `api openapi` gibt das OpenAPI-Dokument jeder eingefrorenen Route aus (in eine Datei umleiten), `api me` sagt, für wen der Monitor diesen Client hält (Modus, Benutzer, Rolle, was die Sitzung darf, Version des Vertrags); ein Monitor mit geschlossenem `api.v1_enabled` sagt das; `api contract-check` startet die Vertragssuite für Clients dagegen (Exit-Code 4, wenn eine Prüfung fehlschlägt) | nein |
| `team` | die Gesundheit der Repositorys als Rangliste, zuerst die, die einen Menschen brauchen; `--severity warn\|bad` behält die schlechteren und `--repo owner/name` zeigt die Einzelheiten eines Repositorys | nein |
| `live` | der Zustand des Webhook-Empfängers und die letzten Ereignisse | nein |
| `ai` | `ai models [--refresh]` listet die Modelle des KI-Anbieters mit den Daten jedes Modells; `ai test --provider NAME --model NAME` testet eines mit einem synthetischen Text (Latenz, Tokens, geschätzte Kosten); `ai doctor` sagt, warum eine KI nicht antwortet, ohne einen Schlüssel auszugeben | nein |
| `lessons` | was die Fehler dieser CI gelehrt haben: `lessons list`, `lessons brief --repo NAME` (vor einem Push lesen), `lessons failures`, `lessons close` | nein |
| `briefs` | die Briefs der Tabs, die KI-Werkzeuge lesen: `briefs index`, `briefs show TAB`, `briefs all` | ja |
| `docs` | die Anleitungen dieser Version, aus der Installation gelesen (ohne Monitor): `docs list` nennt sie mit Titel, `docs show NAME` gibt eine in der Sprache von `--lang` aus | nein |
| `screens` | das Menü Bildschirme der Seite: `screens list` (jede Art von Bildschirm und ob er geöffnet werden kann) und `screens urls` (die vollständigen Adressen, bereit für einen Kiosk-Befehl) | nein |
| `toolbox` | die kleinen Werkzeuge des Betreibers, die auf diesem Rechner ohne laufenden Monitor arbeiten: `toolbox limits [N]` (die Einrichtung gegen ihre Obergrenzen), `toolbox workspaces` (die Arbeitsbereiche und der verwendete), `toolbox ledger [--force]` (das Verzeichnis der bereits gesendeten Benachrichtigungen; `--force` vergisst es), `toolbox summary` (die Ereignisse nach Art, Repository und Tag) und `toolbox export-events FILE` (die Ereignisse als jsonl, csv, parquet oder duckdb nach der Endung des Namens; parquet und duckdb brauchen ihr Paket, die Datei muss neu sein) | nein |
| `credential` | ein anderer GitHub-Zugang für ein Konto, während alles läuft: `credential replace\|reload [--account ID] [--new-token-file DATEI\|-]`; gibt nie ein Token aus | nein |
| `install-skill` | kopiert einen Skill des Monitors (`internal` oder `external`) in den Ordner, aus dem ein KI-Werkzeug seine Skills liest: `install-skill external --dest ORDNER`; der Monitor muss nicht laufen | nein |
| `gh-token` | gibt ein einstündiges Installations-Token der GitHub-App aus, damit die Lesezugriffe eines Werkzeugs das Kontingent der App verbrauchen (nur mit `github_app.share_reads` an); ohne `--json` ausführen | nein |
| `watch` | dieselbe Abfrage immer wieder (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`); siehe [CLI_OPERATOR_deu.md](CLI_OPERATOR_deu.md) | nein |
| `completions` | das Vervollständigungsskript für `bash`, `zsh`, `fish` oder `powershell`, aus dem echten Parser erzeugt (es gibt nur aus) | nein |
| `kiosk` | die Adresse des Monitors für einen Fernseher oder eine Wand (`ops`, `team`, `release`, `quiet`); siehe [KIOSK_deu.md](KIOSK_deu.md) | nein |
| `metrics` | die Zahlen als Zeilen `name=wert` für cron und Mail; mit `--if-problem` schreibt es nichts, wenn alles in Ordnung ist; siehe [CLI_OPERATOR.md](CLI_OPERATOR.md) | nein |
| `posture` | Sicherheitslage von Repositorys und Organisation, nur lesend (`posture status|matrix|check --repo-name`); siehe [POSTURE.md](POSTURE_deu.md) | nein |
| `external-ci` | Externe CI-Quellen, nur lesend (`external-ci list|status|probe --source`); siehe [EXTERNAL_CI.md](EXTERNAL_CI_deu.md) | nein |

Optionen aller Befehle: `--json` (die Antwort als ein JSON-Dokument: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (Port 8766), `--timeout SEKUNDEN` (1 bis 60), `--lang CODE`. Im Netzwerkmodus gehört das Zugriffstoken in die Umgebungsvariable `MONITOR_ACCESS_TOKEN`, die der Monitor selbst liest (`MONITOR_TOKEN` wird als Alias akzeptiert; `--token TOKEN` ist der letzte Ausweg, weil eine Option in der Prozessliste erscheint). Die Reihenfolge: `MONITOR_ACCESS_TOKEN`, dann `MONITOR_TOKEN`, dann `--token`. Es reist im Header `X-Monitor-Access`, nie in der Adresse und nie auf dem Bildschirm. Ein `--url` mit unverschlüsseltem `http` zu einem anderen Rechner gibt eine Warnung auf stderr aus (Token und Antworten würden unverschlüsselt reisen): Nutze außerhalb eines Netzes, das du kontrollierst, `https`.

Jeder Befehl akzeptiert auch `--format text|table|plain|json|ndjson` (`--json` ist `--format json`); siehe [CLI_OPERATOR_deu.md](CLI_OPERATOR_deu.md).

Die Befehlszeile ist ein Client der Lese-API für Clients: Die Routen, die der Vertrag einfriert (`docs/schemas/api_contract.json`), werden zuerst unter `/api/v1/` abgefragt, und antwortet der Monitor dort mit 404 (die API ist geschlossen, `api.v1_enabled`), wird die alte Route abgefragt und das Präfix nicht erneut versucht. Das Dokument ist auf beiden Wegen dasselbe, die Ausgabe keines Befehls ändert sich also. `cli.prefer_v1` (standardmäßig an) schaltet es aus, und die Variable `MONITOR_CLI_PREFER_V1` (`0` oder `1`) hat Vorrang. Die Routen, die der Vertrag nicht einfriert, werden immer auf dem alten Weg abgefragt.

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
| 6 | `watch --exit-on-change` hat eine Änderung gesehen (nur wenn diese Option gegeben ist); siehe [CLI_OPERATOR_deu.md](CLI_OPERATOR_deu.md) |

Jeder Fehler trägt ein `help`: einen Satz mit dem nächsten Schritt, der oft die zu lesende Anleitung nennt (`docs show FIRST_STEPS`). Im Textformat ist es die letzte Zeile, die mit `Hilfe:` beginnt; mit `--json` ist es das Feld `help` neben `error`: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Beispiele

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` unterscheidet drei Dinge: Der Monitor antwortet nicht (2), die GitHub-Anmeldung schlägt fehl (3), und das Kontingent ist erschöpft oder GitHub ist nicht erreichbar (4); ein Monitor, der seine erste Lesung noch nicht beendet hat, sagt das (4), statt leere Zahlen zu zeigen.

## Die Lite-Ausgabe

`python bin/monitor_cli.py status --lite`, `doctor --lite` und `health --lite` sprechen mit Port 8766. Befehle, die Konten, Wächter oder den Webhook-Empfänger brauchen, werden mit Exit-Code 1 abgelehnt. Die Lite-Ausgabe hat weder Konten noch eine Alarm-API.

## `ai-hook`: einem KI-Werkzeug sagen, was der Monitor sieht

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` braucht keinen laufenden Monitor. Es trägt das Gate-Skript `bin/ai_hook.py` in die Hook-Einstellungen eines KI-Werkzeugs ein, zeigt oder entfernt es (siehe die Anleitung zu Warnungen für KI): die Einstellungsdatei wird zusammengeführt, eine Kopie bleibt erhalten, und die Antwort von `--json` ist reines ASCII. `status` ist die Standardaktion.

## Das Zugriffstoken in der Befehlszeile

Im Netzwerkmodus wird das Token aus `MONITOR_ACCESS_TOKEN`, dann `MONITOR_TOKEN`, dann der ersten Zeile von `--token-file DATEI` gelesen (halte diese Datei nur für dich lesbar: auf einem System mit Dateimodi warnt der Befehl, wenn andere sie lesen können) und zuletzt aus `--token`, das in der Prozessliste erscheint und deshalb eine Warnung auf stderr ausgibt.

## Die Speicher-Werkzeuge

`python tools/migrate_storage.py` verschiebt den Zustand zwischen Dateien und SQLite, und `python tools/backup_storage.py` erstellt, prüft und stellt Sicherungen von beiden wieder her (beide sind in [STORAGE_deu.md](STORAGE_deu.md) beschrieben). `--doctor` hat dafür zwei Prüfungen: Speicher und Aufbewahrung.

## Der Batch-Dispatcher: die Eingaben eines Workflows

`python bin/gha_dispatch_all.py plan --inputs` listet zusätzlich unter jedem Ziel die Eingaben auf, die sein Workflow beim manuellen Start verlangt (Name, Typ, erforderlich oder optional, Standardwert, Optionen einer Auswahl und Beschreibung). Sie werden mit `git show` aus der Workflow-Datei in `origin/main` des lokalen Klons gelesen: nichts wird ausgelöst oder gesendet und `gh` wird nicht aufgerufen. `--json` fügt jeder Zeile eine Liste `inputs` hinzu; sie ist `null`, wenn die Datei nicht in `origin/main` liegt oder eine dem Leser unbekannte Form nutzt (der Flussstil `inputs: {…}`), und `[]`, wenn der Workflow keine Eingabe verlangt.

## Sicherung und der Doctor

`backup` und `doctor` arbeiten auf den Ordnern der Installation und brauchen daher keinen laufenden Monitor. `doctor` endet mit `0`, wenn alles in Ordnung ist (auch mit Warnungen), mit `1`, wenn eine Prüfung fehlschlug, mit `3`, wenn es nur Warnungen gibt und `--strict` (oder `ops.doctor.strict_exit`) aktiv ist, und mit `4`, wenn der Doctor selbst nicht laufen konnte; das sind die Codes des Doctors, die anderen Befehle behalten die oben genannten Exit-Codes. `backup` endet mit `0`, wenn es erledigt ist, und mit `1`, wenn es abgelehnt wird oder das Paket die Prüfung nicht besteht. Die Anleitung [OPS_deu.md](OPS_deu.md) enthält die Prüfungen, die Wiederherstellung und die geplante Sicherung. Der Doctor hat außerdem `compare_window` (kann der Vergleich zweier Zeiträume zwei Fenster zurückschauen, mit dem Verlauf, den er verlangt und behält) und `etag` (Anteil der bedingten Abfragen, die mit 304 beantwortet wurden, im hier laufenden Monitor, und ob Antworten von GitHub ohne ETag ankommen).
