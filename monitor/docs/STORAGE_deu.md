<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | [🇪🇸 Español](STORAGE_spa.md) | [🇫🇷 Français](STORAGE_fra.md) | [🇮🇹 Italiano](STORAGE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# Speicherung und Aufbewahrung

Wo die vollständige Ausgabe das aufbewahrt, was sie lernt, wie man das ändert und was sie von selbst entfernt. Die Lite-Ausgabe speichert immer gewöhnliche Dateien, hat keine Datenbank und keinen Aufbewahrungsjob und zeigt nichts davon.

## Was gespeichert wird

Pro Konto: die Konfiguration (`actions_monitor.json`), der Zustand der Wächter, der Ereignisfeed, was der Feed schon gemeldet hat, die Analysemessungen, die Stummschaltungen und der Update-Hinweis. Für die ganze Installation: Benutzer, die Konten, die sie sehen dürfen, und ihre Sitzungen (der Teammodus nutzt sie). Die Caches der bedingten Abfragen und die Protokolle sind immer gewöhnliche Dateien.

## Die zwei Speicher

|  | `file` (Standard) | `sqlite` |
|---|---|---|
| Wo | `accounts/<id>/` (neben den Startdateien, wenn es kein `accounts/` gibt) | `accounts/<id>/storage.sqlite3`, eine Datenbank pro Konto |
| Schreiben | eine temporäre Datei, auf die Platte geschrieben, dann umbenannt | eine kurze Transaktion, WAL-Journal |
| Wählen Sie ihn für | eine Person; Dateien, die Sie lesen und bearbeiten können | einen Dienst, der monatelang läuft; viele Ereignisse |

Gewählt wird in der Konfiguration des Kontos (oder des Monitors): `"storage": {"backend": "sqlite"}`. Die Konfiguration selbst bleibt immer eine JSON-Datei, denn sie benennt den Speicher. Mit SQLite liegt der Ereignisfeed in der Datenbank, nicht in `events_monitor.jsonl`. Eine Datenbank, die sich nicht öffnen lässt, verhindert den Start: Der Monitor schreibt seinen Zustand nie hinter Ihrem Rücken woanders hin.

## Entscheidung: ein Speicher pro Konto (Modell A)

*Kontext.* Die vollständige Ausgabe startet einen Prozess pro Konto. *Entscheidung.* Jeder Prozess hat seinen eigenen Speicher: eigene Dateien oder eine eigene Datenbank `storage.sqlite3` in `accounts/<id>/`. Zwei Prozesse schreiben nie dieselbe Datei, also gibt es nichts zu sperren, und ein Problem in einem Konto kann kein anderes beschädigen. *Preis.* Eine Abfrage über mehrere Konten heißt, mehrere Datenbanken zu lesen.

*Bereitgehalten: Modell B, eine gemeinsame Datenbank.* Tragen Sie denselben Pfad in den Block `storage` jedes Kontos ein (`"path": "/data/monitor.sqlite3"`). Das funktioniert, weil jede Tabelle das Konto trägt, WAL der Seite das Lesen erlaubt, während die Wächter schreiben, die Transaktionen kurz sind und bei belegter Datenbank bis zu 5 Sekunden gewartet wird. Es ist getestet (zwei Prozesse im Takt gleichzeitig; eine Seite, die über HTTP antwortet, während sie schreiben), aber nicht der Standard: Es ist anfälliger als A und lohnt nur, wenn Sie SQL über Konten hinweg brauchen.

## Was garantiert ist

- Ein Schreibvorgang ist atomar: Ein Leser sieht den alten oder den neuen Wert. Ein mittendrin beendeter Prozess (`kill -9`) hinterlässt den alten Wert; bei SQLite erholt sich der nächste Start von selbst.
- Das Schema ist versioniert (`schema_version`). Jede Migration läuft in einer einzigen Transaktion zusammen mit dem Hochsetzen der Version; eine unterbrochene lässt die Datenbank, wie sie war, und läuft beim nächsten Start erneut. Eine Datenbank einer neueren Version wird abgelehnt, nie zurückgestuft.
- Ein beschädigtes oder fehlendes Element liest sich als leer: Der Monitor startet mit dem, was auf der Platte liegt.

## Daten verschieben und Sicherungen

```
python tools/migrate_storage.py --from file --to sqlite              # Probelauf: zeigt, was kopiert würde
python tools/migrate_storage.py --from file --to sqlite --apply      # kopiert und vergleicht dann jedes Element und jedes Ereignis
python tools/backup_storage.py backup backup.zip --backend sqlite    # eine .zip mit Manifest und SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # in einen leeren Speicher (--force über vorhandene Konten)
```

Die Migration ändert oder löscht Ihre Dateien nie, setzt nach einer Unterbrechung fort (ein Konto wird ganz oder gar nicht kopiert) und endet mit einem Fehler, wenn beide Seiten abweichen; erst danach stellen Sie den Speicher um und starten neu. Eine Sicherung aus Dateien lässt sich in SQLite wiederherstellen und umgekehrt. `--db FILE` wählt die gemeinsame Datenbank von Modell B; `--flat` ist die Installation ohne `accounts/`. `--doctor` prüft die Datenbank (vorhanden, Integrität, Schema), ohne sie zu ändern.

## Aufbewahrung

Ein monatelang laufender Monitor würde ohne Obergrenze wachsen, daher entfernt ein kurzer Durchlauf am Ende einer Aktualisierung (alle `retention.interval_hours`, standardmäßig 24) das Alte:

| Einstellung | Standard | Bedeutung |
|---|---|---|
| `retention.enabled` | an | der Schalter |
| `retention.events_days` | 90 | ältere Ereignisse werden entfernt |
| `retention.analytics_days` | 180 | ältere Tage des Analyseverlaufs werden entfernt |
| `retention.mode` | `archive` | `archive` schreibt die alten Ereignisse zuerst in eine `.gz` in `events/archive/` |
| `retention.events_max_kb` | 512 | Größenobergrenze der Feed-Datei beim Dateispeicher (wie immer) |
| `retention.warn_events_mb` | 20 | `--doctor` warnt oberhalb dieser Größe |

Die Bereinigung berührt nur Ereignisse und Analysetage, die älter als ihre Grenze sind; sie berührt nie die Konfiguration, den Zustand der Wächter, die Stummschaltungen oder ein Ereignis ohne Zeit. Jeder Durchlauf hinterlässt eine Zeile im Auditdokument (wann, wie viele Ereignisse entfernt und behalten, die Archivdatei, wie viele Analysetage, ein Fehler). `--doctor` warnt vor der Größe der Ereignisse und, bei einem Monitor, der als Dienst läuft (Netzwerkmodus, ohne Browser, ein Container oder `MONITOR_SERVICE=1`), wenn seine Konfiguration keinen `retention`-Block hat. Sichern Sie, bevor Sie die Grenzen verkürzen.

Der Standard `archive` bewahrt das Entfernte in komprimierten, wieder lesbaren Dateien auf; `delete` entfernt es endgültig.
