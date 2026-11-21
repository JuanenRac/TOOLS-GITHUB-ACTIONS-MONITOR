<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Den Monitor aktualisieren (der Updater)

[English](UPDATE.md) · [Español](UPDATE_spa.md) · [Français](UPDATE_fra.md) · [Italiano](UPDATE_ita.md) · **Deutsch** · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · [Português](UPDATE_por.md)

Der Updater bringt eine Installation von jeder veröffentlichten Version auf jede andere (aufwärts oder abwärts), migriert Ihre Konfiguration und lässt einen Rückweg offen. Er besteht aus EINER Datei, `monitor_updater.py`, die nur Python braucht und mit jeder installierten Version funktioniert; er liegt auch im Produkt (`tools/monitor_updater.py`) und als Befehl `monitor_cli.py update`. Er aktualisiert nie von selbst: nur auf Ihren Wunsch, und er löscht nichts (Ersetztes landet im Ordner der Kopien).

## Drei Wege, ihn zu öffnen

- `py -3 monitor_updater.py` öffnet eine Seite im Browser. Sie wird nur auf 127.0.0.1 und nur solange der Updater läuft ausgeliefert, mit einem einmaligen Token in der Adresse; sonst kann sie niemand nutzen.
- `py -3 monitor_updater.py --tk` öffnet dasselbe in einem Fenster (braucht Tkinter).
- `py -3 monitor_updater.py --console` ist ein Textmenü für Server, SSH und Container.
- `py -3 bin/monitor_cli.py update` ist dieselbe Datei, aus dem Produkt gestartet; `update plan`, `update apply` und die anderen Befehle unten nehmen die Optionen der Tabelle an.

## Das Menü Updates im Monitor

Die Komplett-Ausgabe hat denselben Updater in ihrer Seite: **System > Updates**. Es zeigt die installierte Version und die, die die Prüfung gefunden hat (Einstellung `updates.check`; GitHub wird nicht gefragt, solange sie aus ist oder der Monitor offline ist), die Hinweise jeder Version und mit der Schaltfläche „Versionen suchen“ die Liste der veröffentlichten. Nichts wird geladen oder eingespielt, ohne dass du eine Schaltfläche drückst. Das Einspielen braucht einen Administrator an dem Rechner, auf dem der Monitor läuft (die Routen `/api/updates/*` antworten aus dem Netz mit 403), und eine Bestätigung, die sagt, was passiert: das SHA-256 des ZIPs gegen SHA256SUMS, die zuerst angelegte Kopie (mit ihrem Ordner), die Migration der Konfiguration und der Neustart. Das Update läuft in einem eigenen Prozess: Der Monitor beendet sich selbst, das Update wird eingespielt, der Monitor startet mit der neuen Version neu und die Seite verbindet sich wieder; startet die neue Version nicht, wird die vorherige zurückgespielt und gestartet. „Zur vorherigen Version zurückkehren“ macht dasselbe rückwärts. Schritte, Verlauf und Ergebnis erscheinen auf der Seite und im Aktionslog. Es wird nicht in der Lite-Ausgabe, nicht in einem Container und nicht unter einem Dienstmanager angeboten (sie starten den Prozess selbst neu: nutze die Kommandozeile), und es läuft immer nur ein Update. Konfiguration, Daten, Schlüssel und Logs werden nicht ersetzt. Die eigenständige Datei bleibt der Weg zurück, wenn der Monitor nicht startet.

Unter einem Dienstmanager spielt die Seite standardmäßig keine Updates ein. Läuft der Monitor als systemd-BENUTZERDIENST (`systemctl --user`), kannst du `updates.systemd_helper` einschalten (standardmäßig aus): Die Seite bietet das Update dann an, und der Prozess, der es einspielt, hält diesen Dienst an, spielt das Update ein und startet den Dienst wieder, immer mit `systemctl --user` und nie mit `sudo`. Ein Systemdienst (einer, der den Administrator braucht) wird nicht angefasst und bleibt „nutze die Kommandozeile“. Dasselbe geht in der Kommandozeile mit `--systemd-unit EINHEIT` (`apply` und `rollback`); lässt sich der Dienst nicht anhalten, wird nichts gestartet, und startet die neue Version nicht, wird die vorherige zurückgespielt und der Dienst wieder gestartet.

**Vertrauen.** Die Prüfung vergleicht das Zip mit SHA256SUMS, und beides stammt aus demselben GitHub-Release: Sie erkennt einen beschädigten oder unvollständigen Download, nicht ein an der Quelle ausgetauschtes Release. Das Vertrauen in das Release beruht auf GitHub und auf deinem eigenen Konto dort.

## Was er tut, Schritt für Schritt Die Routen dahinter sind `/api/updates/status`, `/api/updates/progress`, `/api/updates/history`, `/api/updates/log` (die letzten Zeilen des Prozessprotokolls, Werte nach token oder secret ausgeblendet), `/api/updates/copies` (nur lesend) und `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback`, `/api/updates/discard` (Administrator, nur von diesem Rechner). Der Fortschritt kommt außerdem als Server-Sent Events über `/api/updates/stream` (die Seite nutzt das während einer Aktualisierung und fragt alle anderthalb Sekunden nach, wenn Browser oder Verbindung es nicht erlauben).

1. Erkennt die Installation: Ordner, Version, Ausgabe (Vollständig oder Lite), Konfiguration, Daten, Ports, ob der Monitor läuft, Container oder Dienst.
2. Listet alle auf GitHub veröffentlichten Versionen (ohne Token) mit Datum und Hinweisen auf und markiert die installierte und die neueste. Ohne Verbindung geben Sie ihm mit `--zip` ein Zip.
3. Sie wählen die Zielversion. Eine niedrigere ist ein Downgrade: dafür braucht es `--allow-downgrade`.
4. Zeigt den PLAN als Probelauf: die Kette der Schritte zwischen beiden Versionen (aus dem Register der Migrationen gelesen), was sich in IHRER Konfiguration ändert, die Verhaltensänderungen, die Sie bemerken werden, und jede gefundene Unstimmigkeit.
5. Wendet ihn an: vorherige Kopie, SHA-256 gegen SHA256SUMS geprüft, Zip in einen neuen Ordner entpackt und untersucht (Pfade mit `..`, Links, Größe), Produkt kopiert, Ihre eigenen Zeilen in den Startskripten zurückgesetzt, Konfiguration migriert, Ordnerstruktur migriert und auf Wunsch der Monitor gestartet und `/api/health` geprüft.
6. Schlägt etwas fehl, kehrt er selbst zum vorherigen Zustand zurück und schreibt einen Bericht. Jede Aktualisierung kommt in den Verlauf (`update_history.jsonl`), und die letzte lässt sich mit dem Befehl `rollback` rückgängig machen.

## Befehle

Ohne Befehl öffnet sich die Seite. Die Befehle antworten einmal (mit `--json` als Dokument):

| Befehl | Bedeutung |
|---|---|
| `status` | was installiert ist und was die Prüfungen finden |
| `releases` | alle veröffentlichten Versionen |
| `plan` | der Probelauf für ein Ziel |
| `apply` | ausführen (`--dry-run` zeigt nur den Plan) |
| `migrate` | nur eine Konfigurationsdatei migrieren, siehe unten |
| `rollback` | zur Version vor der letzten Aktualisierung zurück |
| `history` | die auf dieser Installation gemachten Aktualisierungen |
| `copies` | die Kopien im Kopienordner: Name, Zustand, Versionen, Größe und welche der Rückweg braucht |
| `discard` | `discard --name KOPIE` löscht EINE Kopie nach Bestätigung (`--yes` überspringt die Frage); die Kopie, die der Rückweg braucht, nur mit `--force`; die eines laufenden Updates nie |
| `log` | die letzten Zeilen (`--lines N`, höchstens 2000) des Protokolls des Prozesses des letzten Updates, Werte nach token, secret oder password ausgeblendet |

## Optionen

| Option | Bedeutung |
|---|---|
| `--dir` | die Installation (Standard: dort, wo die Datei liegt, aufwärts suchend) |
| `--to` | Zielversion (Standard: die neueste) |
| `--from` | migrate: die Version, aus der die Datei stammt |
| `--config` | migrate: eine Konfigurationsdatei |
| `--zip` | dieses Zip statt GitHub verwenden |
| `--sha256` | erwartetes SHA-256 des Zips |
| `--dry-run` | nur den Plan zeigen |
| `--apply` | migrate: das Ergebnis schreiben |
| `--yes` | nicht nach Bestätigung fragen |
| `--json` | die Antwort als ein JSON-Dokument |
| `--keep-old-defaults` | schreibt den alten Standardwert jeder nie gesetzten Einstellung, damit sich das Verhalten nicht ändert |
| `--adopt-new-defaults` | setzt auch Einstellungen, die noch den alten Standard haben, auf den neuen |
| `--start` | danach den Monitor starten und prüfen |
| `--handover` | der Monitor, der diesen Prozess gestartet hat, beendet sich selbst: auf ihn warten, einspielen, ihn neu starten (scheitert der Start, kommt die vorherige Version zurück) |
| `--status-file` | schreibt den Fortschritt in diese JSON-Datei (das Menü Updates liest sie) |
| `--edition` | complete oder lite, wenn sie sich nicht ableiten lässt |
| `--allow-downgrade` | eine niedrigere Version erlauben |
| `--allow-container` | trotzdem in einem Container arbeiten (das Image wird nicht ersetzt) |
| `--no-gh` | das Programm `gh` nicht verwenden, nur die öffentliche API |
| `--backups` | Ordner der Kopien (Standard: update_backups in der Installation) |
| `--restore-data` | yes, no oder auto: was der Rückweg mit den Daten macht |
| `--port` | Port der Seite |
| `--no-browser` | den Browser nicht öffnen |
| `--tk` | das Fenster |
| `--console` | das Textmenü |
| `--lang` | Sprache: en es de fr it ja zh pt |

## Ihre Konfiguration und die geänderten Standardwerte

- Das Register der Migrationen (JSON-Dateien, mit jeder Release versioniert, `assets/migrations/`) sagt zu jeder Version, was sich geändert hat: umbenannte, entfernte oder neue Einstellungen, neue Standardwerte, verschobene Dateien, Verhaltensänderungen. Der Updater wendet die Kette der übersprungenen Versionen an.
- Standardmäßig behält er, was Sie ausdrücklich gesetzt haben, und übernimmt einen neuen Standard nur dort, wo Sie die Einstellung nie definiert hatten. Eine Verhaltensänderung (zum Beispiel eine Funktion, die nun standardmäßig aus ist) steht im Bericht; `--keep-old-defaults` hält das alte Verhalten fest, `--adopt-new-defaults` setzt alles auf das neue.
- `migrate` arbeitet an einer einzelnen Datei: `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config meine.json` zeigt das Ergebnis, `--apply` schreibt es (nach einer Kopie). Geheimnisse sind in jedem Bericht maskiert.

## Prüfungen vor dem Anwenden

- Blockierend: der Monitor läuft, das SHA-256 stimmt nicht, das Zip ist unsicher, zu wenig Speicherplatz, Daten eines neueren Schemas als das Ziel, ein Container, eine andere Aktualisierung steht aus.
- Warnungen: Einstellungen, die es nicht mehr gibt oder deren Typ oder Bereich sich geändert hat, Werte außerhalb des Bereichs, doppelte Schlüssel, ein von einem anderen Programm belegter Port, ein von Ihnen geändertes Startskript, ein Schritt, der einen anderen voraussetzt. Jede Warnung nennt eine empfohlene Maßnahme.

## Sicherheit und der Rückweg

- Er lauscht nur auf 127.0.0.1 mit einem flüchtigen Token, weist Anfragen von anderen Seiten ab, führt nichts aus dem Zip aus, nutzt keine Shell und schreibt nur in die Installation und den Ordner der Kopien.
- Vor jeder Änderung kopiert er Paket, Konfiguration und Daten; schlägt ein Schritt fehl, wird die Kopie zurückgespielt und ein Bericht geschrieben. Scheitert sogar der Rückweg, bleibt die Kopie unversehrt und der Bericht erklärt, wie man sie von Hand wiederherstellt.
- Offline: `--zip DATEI` mit `--sha256` (oder einer SHA256SUMS daneben). Docker: das Volume wird aktualisiert, das Image von innen nicht ersetzt (`--allow-container` erzwingt es).
- Die Seite zeigt die Kopien und bei jeder eine Schaltfläche **Kopie verwerfen** (sie fragt zuerst, bei der Kopie des Rückwegs zweimal) sowie eine Schaltfläche, um das ganze Protokoll des Prozesses des letzten Updates zu lesen. Verwerfen löscht nur diese Kopie, nie die Installation oder die Daten, und wird im Verlauf festgehalten.
- Der Updater, der ohne den Monitor läuft, kann dasselbe: seine Seite im Browser (Schaltflächen **Kopien** und **Prozessprotokoll** und **Kopie verwerfen** bei jeder Kopie, mit denselben Rückfragen), sein Textmenü (Punkte 7 bis 9) und sein Fenster (Tkinter).

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | erledigt, oder nichts zu tun |
| 2 | falsche Verwendung |
| 3 | von einer Prüfung blockiert, nichts geändert |
| 4 | Download, SHA-256 oder Zip fehlgeschlagen, nichts geändert |
| 5 | fehlgeschlagen und der vorherige Zustand wiederhergestellt |
| 6 | fehlgeschlagen und der Rückweg ebenfalls: Kopie von Hand wiederherstellen |
| 7 | keine Verbindung zu GitHub und kein Zip |
| 8 | nicht bestätigt |

## Der Hinweis nennt den Befehl Ihrer Installationsart

Der Hinweis auf eine neuere Version (Konsole, Info, `/api/about`) nennt jetzt den genauen Befehl für die Art, wie dieser Monitor installiert wurde, im Feld `command` neben `channel`: das entpackte Produkt (`py -3 monitor/bin/monitor_cli.py update`), ein Dienstmanager (`... update apply --systemd-unit <Einheit>`), ein Container (`docker pull ghcr.io/juanenrac/tools-github-actions-monitor:<Version>`), pipx, uv oder eine Erweiterung des Befehls `gh`. Der Hinweis führt nichts aus.
## Wächter des Dienst-Helfers

Mit `updates.systemd_helper` (oder `--systemd-unit`) prüft der Updater den Dienst jetzt, bevor er ihn anrührt: Eine Unit, deren Arbeitsverzeichnis und Befehl nicht auf DIESEN Ordner zeigen, gehört zu einer anderen Installation und wird weder gestoppt noch gestartet; eine Unit wird nicht gestartet, solange etwas anderes (ein Monitor im Vordergrund) ihren Port bedient; ein Neustart gilt nicht als erledigt, solange der Prozess der alte ist (die Unit muss eine neue PID zeigen); und `update status --systemd-unit UNIT` listet nur die Fehler des Dienstes seit seinem letzten Start. Das sind nur lesende Fragen an `systemctl --user show` und `journalctl --user`; eine unbeantwortbare Frage blockiert nichts.
