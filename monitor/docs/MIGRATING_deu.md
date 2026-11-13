<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Aktualisieren von einer Version vor 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · **Deutsch** · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

Version 1.5.0 hat Dateien, Ordnern, Skripten und einer Einstellung englische Namen gegeben. Nichts geht verloren: Der Monitor LIEST die alten Namen weiterhin, du kannst also zuerst aktualisieren und danach aufräumen.

## Schritte

1. Beende den Monitor und entpacke die neue Version über den alten Ordner (behalte deine `actions_monitor.json`).
2. Sieh nach, was sich ändern würde: `python migrate_state.py` (Probelauf, ändert nichts).
3. Ausführen: `python migrate_state.py --apply` kopiert die alten Dateien auf die neuen Namen und behält die alten; mit `--move` werden sie stattdessen umbenannt. Vorhandenes wird nie überschrieben, und die Einstellung `parte_history_days` wird zu `report_history_days`, nachdem eine Kopie von `actions_monitor.json` gesichert wurde.
4. Starte den Monitor mit `MONITOR_GITHUB_ACTIONS` (derselbe Starter wie bisher) und nutze `BATCH_GITHUB_ACTIONS` für die Stapelwerkzeuge.
5. Lösche die alten Starter, die du noch hast: `LOTE_GITHUB_ACTIONS.bat`, `.sh` und `.command`.

## Alte und neue Namen

| Vor 1.5.0 | Ab 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, sein Schema und die Dateien von `--export-status` haben sich nicht geändert. Die Sprache ist Englisch, bis du in den Einstellungen eine andere wählst.

# Von 1.5.x auf 1.6.x

Es muss nichts umgewandelt werden: der Monitor liest weiter Ihre `actions_monitor.json` und ergänzt die neuen Schlüssel mit sicheren Standardwerten, wenn Sie das erste Mal aus den Einstellungen speichern.

1. Monitor beenden und die neue Version über den alten Ordner entpacken (Ihre `actions_monitor.json` und Katalogdateien behalten).
2. Wie bisher starten. Daneben erscheinen neue Dateien (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); sie dürfen jederzeit gelöscht werden.
3. Optional: `python actions_monitor.py --doctor` prüft die Installation.

Was anders ist: es gibt die **Lite-Ausgabe** (`MONITOR_LITE_GITHUB_ACTIONS`, Port 8766, eigene `actions_monitor_lite.json`, ohne Wächter); **Rot auf main** ist eine einzige Regel (der letzte abgeschlossene Run jedes Workflows auf dem Standard-Branch; abgebrochene, übersprungene, neutrale und veraltete Runs sagen nichts), eine Zahl kann also von 1.5.x abweichen; die Einstellungsseite beginnt mit dem Reiter **Grundlagen**; Benachrichtigungen, Analytik, Linter, Webhook-Ereignisse und KI-Assistent existieren und sind **aus**, bis Sie sie einschalten; Schreiben auf GitHub braucht weiter Ihre ausdrückliche Bestätigung. Rich und Textual bleiben optional; Python 3.11 oder neuer.

# Von 1.6.4 auf 1.6.5

Es muss nichts umgewandelt werden. Was sich jetzt bewusst anders verhält, weil Unbewiesenes nicht mehr als sicher gilt:

- **Stapel**: `finalize` bietet nur einen Lauf zum Signieren an, dessen Stapel AUFZEICHNET, dass er auf dem geprüften Commit gebaut wurde. Ein Stapel einer älteren Version meldet `needs_review`. Trotzdem nutzen: `finalize --accept-legacy` liest den Lauf erneut von GitHub, akzeptiert ihn nur, wenn sein Commit der aufgezeichnete ist, und verlangt vor jeder Signatur das Wort LEGACY. Oder den Build neu starten.
- **Grüne CI** heißt: Die erforderlichen Workflow-Dateien liefen auf diesem Commit erfolgreich (Standard `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nichts ist fehlgeschlagen oder wartet auf Freigabe, und die Liste der Läufe ist vollständig. Ein Repository mit anders benannter CI-Datei braucht diesen Namen in `dispatch.required_ci`.
- **Ein fehlgeschlagenes `git fetch`** (kein Netz, keine Zugangsdaten) stoppt den Start dieses Repositorys.
- **targets.json**: `tool` muss ein einfacher Dateiname (ohne Ordner, ohne `..`) im Werkzeugordner sein; `extra` darf nur `-f Schlüssel=Wert`-Paare enthalten (nicht `dry_run` oder `ref`); `finalize_flags` nur lange Optionen wie `--bench`. Ein Katalog, der das nicht erfüllt, wird mit Begründung abgelehnt.
- **Benachrichtigungen**: `max_per_hour` zählt Nachrichten (eine je Kanal), nicht Ereignisse.
- **Webhook**: Jede Anfrage braucht `X-GitHub-Delivery` (GitHub sendet es immer); eine wiederholte Kennung wird ignoriert; der Eigentümer in `full_name` muss das beobachtete Konto sein.
- **act**: Ein Klon, der ein Link auf einen anderen Ordner ist, wird abgelehnt (`act.allow_symlinks` erlaubt es).
- **Netzwerkmodus**: nur IPv4-Adressen; die angezeigte Adresse ist die, auf der der Server lauscht; `GET /api/sentinel/parte.txt?save=1` schreibt nicht mehr (die Kopie ist ein POST mit dem Einmal-Token).
- Das gespeicherte GitHub-Token wird nicht mehr in die Umgebung des Prozesses gelegt: Nur `gh` erhält es.
- Der Test, der das Zip in einem sauberen Ordner entpackt, gehört nicht mehr zur normalen Testreihe; `make_release.py` führt ihn als eigene Stufe aus.

# Von 1.6.5 auf 1.6.6

Es muss nichts umgewandelt werden. Was sich absichtlich anders verhält:

- **Netzwerkmodus über HTTPS**: Änderungen von der Seite aus funktionieren jetzt; der `Origin` muss das Schema der Sitzung und den Port des Monitors tragen. Hinter einem Proxy den Port des Monitors in der Adresse lassen, sonst lehnt die Prüfung ab.
- **Netzwerkmodus**: Jede Einstellung, die das Schema als `secure` markiert, kann nur vom Rechner selbst geändert werden (vorher nur `listen.`, `github_token.`, `act.`, `github_actions.`). Ein Skript auf einem anderen Rechner, das `webhook.*`, `notify.*` und Ähnliches änderte, erhält jetzt 403 `local_only`.
- **act**: Nach Stopp ist der Lauf sofort frei; ein Start direkt danach antwortet nicht mehr `busy`.
- Neue Dateien neben dem Monitor: `degraded.json` und `degraded_lite.json` (die Zähler verschluckter Fehler); sie können jederzeit gelöscht werden.
- Das Änderungsprotokoll (Hilfe > Änderungsprotokoll) ist übersetzt: eine Datei `docs/CHANGELOG_<Sprache>.md` je Sprache.

# Von 1.6.6 auf 1.6.7

Es muss nichts umgewandelt werden. Was sich absichtlich anders verhält:

- **Netzwerkmodus hinter einem HTTPS-Proxy auf Port 443**: neue Einstellung `listen.proxy_public_host` (standardmäßig leer; wenn du sie leer lässt, ändert sich nichts). Trage dort den öffentlichen Hostnamen des Proxys ein, wenn er `Host` und `Origin` ohne Port weiterleitet; dieser eine Name wird dann unverändert akzeptiert, nur solange der Netzwerkmodus an ist und die Sitzung HTTPS nutzt. Sie lässt sich nur vom Rechner selbst ändern. Hinter einem Proxy, der den Port beibehält, ändert sich nichts.
- Das Änderungsprotokoll (Hilfe > Änderungsprotokoll) ist jetzt für 1.6.7 und 1.6.5 in den anderen sieben Sprachen übersetzt; ältere Einträge zeigen weiterhin den englischen Text unter einem übersetzten Hinweis.

# Von 1.6.7 auf 1.6.8

Es muss nichts umgewandelt werden, und keine Einstellung ändert sich.

- Neu im Repository (nicht im Paket): `python tools/manual_check_live.py proxy HOST [PORT] [VERBINDEN]` prüft deinen echten HTTPS-Proxy auf Port 443 gegen `listen.proxy_public_host`; setze vorher `MONITOR_ACCESS_TOKEN`, es wird gelesen und nie ausgegeben.
- Das Änderungsprotokoll (Hilfe > Änderungsprotokoll) ist jetzt in den anderen sieben Sprachen von 1.6.8 bis 1.6.3 übersetzt.

# Von 1.6.8 auf 1.7.0

Es muss nichts umgewandelt werden: Ohne einen Ordner `accounts/` arbeitet der Monitor genau wie bisher.

- **Mehrere Konten** sind optional. Um sie zu nutzen, führe `python actions_monitor.py --migrate-accounts` aus (ein Probelauf) und füge dann `--apply` hinzu, um deine Dateien nach `accounts/default/` zu kopieren; die Originale bleiben, bis du sie löschst. Weitere Konten legst du als `accounts/<id>/actions_monitor.json` an. Siehe `ACCOUNTS.md`.
- Mit einem Ordner `accounts/` startet `python actions_monitor.py` einen Supervisor, der pro Konto einen Monitor ausführt; `--account <id>` führt nur eines aus. Die Lite-Ausgabe hat nichts davon.
- Neu: `?view=` und `?chrome=0` in der Adresse der Seite, `GET /api/accounts`, `GET /api/live-status` und ein einziger `POST /api/webhook` für alle Konten.

# Von 1.7.x zur neuen Ordnerstruktur

Der Code liegt jetzt in `src/github_actions_monitor/`, die Seite, die Beispieldateien und die Sprachen in `assets/`, die Release- und Migrationsskripte in `tools/`. Nichts, was Sie benutzen, ändert sich: Die Starter (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) bleiben, wo sie waren, und öffnen dieselbe Adresse und denselben Port, und die Befehle dieser Anleitung (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) funktionieren weiter, weil im Produktordner eine kleine Einstiegsdatei mit demselben Namen bleibt. Die Starter rufen `python -m github_actions_monitor` (komplett) und `python -m github_actions_monitor.lite` (Lite) mit `src/` im Pfad auf.

Ihre Daten wandern nicht: `actions_monitor.json`, die Caches, die Protokolle, `config_backups/`, `accounts/` und Ihre eigenen Katalogdateien bleiben im Produktordner neben den Startern, nie in `src/`. Die neutralen Beispiele und die `quotas.json`, die mit dem Programm kommen, liegen jetzt in `assets/examples/`; eine eigene `quotas.json` neben den Startern hat weiterhin Vorrang.

## Schritte

1. Monitor beenden und die neue Version über den alten Ordner entpacken (Ihre `actions_monitor.json` behalten).
2. Wie gewohnt starten. Es läuft auch, wenn Sie nichts weiter tun.
3. Um die Reste des alten flachen Layouts zu entfernen: `python tools/migrate_layout.py` (Probelauf) und danach `python tools/migrate_layout.py --apply`. Es kopiert Ihre Konfigurationsdateien nach `layout_backup_<Stempel>/config/` und verschiebt die alten Module, die alte Seite, die alten Beispiele und den alten Ordner `locales/` nach `layout_backup_<Stempel>/old_code/`. Nichts wird gelöscht, nichts Vorhandenes überschrieben, Ihre Daten bleiben unberührt. `python actions_monitor.py --doctor` warnt, solange alte Dateien übrig sind.
4. Ein eigenes Skript, das ein Modul unter seinem alten flachen Namen importiert hat (`import read_report`), importiert jetzt `github_actions_monitor.<Paket>.<Modul>` mit `src/` im Pfad.

| Paket | Inhalt |
|---|---|
| `app` | der Server, die Einstellungen, die Arbeitsmodi, die gemeinsame Konfiguration |
| `accounts` | mehrere Konten: Register, Supervisor, Kindprozess |
| `sentinels` | die Wächter, das Alarmzentrum, die Panels |
| `security` | lokale Wache, Geheimnisse, Webhook, Bestätigung, Netzwache, Signaturen, private Dateien |
| `data_pipeline` | Ereignisse, Analytik, bedingte Lesungen, Erkennung, Kontingente, die Rot-auf-main-Regel |
| `integrations` | GitHub, Benachrichtigungen, OpenTelemetry, Spiegel, Runner, MCP, KI-Feed und -Hook |
| `cli` | die Befehlszeilenwerkzeuge |
| `ui` | Info, Hilfedokumente, Terminalansichten |
| `i18n`, `util` | die acht Sprachen; kleine gemeinsame Helfer |

## Zustand zwischen Dateien und SQLite verschieben (1.8.0)

Zum Aktualisieren muss nichts migriert werden: Dateien bleiben der Standard. Wenn Sie den Zustand in SQLite wollen, zeigt `python tools/migrate_storage.py --from file --to sqlite`, was kopiert würde (Probelauf); mit `--apply` wird kopiert und geprüft. Ihre Dateien werden nie geändert oder gelöscht. Siehe [STORAGE_deu.md](STORAGE_deu.md).
