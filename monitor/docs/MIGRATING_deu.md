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
