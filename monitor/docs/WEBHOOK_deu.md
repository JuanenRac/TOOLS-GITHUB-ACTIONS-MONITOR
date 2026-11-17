<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Eingehender Webhook

Optional und **standardmäßig aus**. GitHub kann dem Monitor damit melden, dass sich etwas geändert hat, sodass das Repository im nächsten Zyklus aktualisiert wird, statt auf die nächste Abfrage zu warten.

## Was er tut (nur aktualisieren)

Ein akzeptiertes Ereignis markiert nur das darin genannte Repository für eine Aktualisierung im nächsten Zyklus. Es wird nichts nach GitHub oder auf die Platte geschrieben, kein Text des Ereignisses gespeichert oder angezeigt, und nur Repositorys, die der Monitor ohnehin beobachtet, werden akzeptiert. Verstandene Ereignisse: `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` und `ping`; alles andere wird mit `202` beantwortet und ignoriert.

## Sicherheit

- Der Monitor lauscht weiterhin nur auf `127.0.0.1`. GitHub erreicht ihn nur über einen Tunnel, den Sie absichtlich einrichten; das Werkzeug öffnet nie einen.
- Aus, bis `webhook.enabled` an ist **und** das gemeinsame Geheimnis (mindestens 32 Zeichen) in der Umgebungsvariable steht, die `webhook.secret_env` nennt (standardmäßig `MONITOR_WEBHOOK_SECRET`; `MONITOR_WEBHOOK_SECRET_FILE` kann eine Datei nennen, deren erste Zeile das Geheimnis ist, wie bei den Secrets eines Containers). Das Geheimnis wird nie in `actions_monitor.json` geschrieben, angezeigt, protokolliert oder an Programme vererbt, die der Monitor startet; der Reiter Einstellungen sagt nur, ob es definiert ist. Der alte Weg (ein `secret` in der Datei) wird nur gelesen, wenn `webhook.allow_config_secret` wahr ist, und die Live-Ansicht warnt, solange er benutzt wird.
- Jede Anfrage muss `X-Hub-Signature-256: sha256=<hmac>` tragen, mit diesem Geheimnis gebildet und in konstanter Zeit verglichen; alles andere erhält `401`, und vom Inhalt wird nichts angesehen, bevor die Signatur geprüft ist.
- Ein Body über 256 KB erhält `413`, bevor irgendetwas berechnet wird.
- Die Listen sind geschlossen: nur `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` und `ping` werden verarbeitet, von einem Ereignis werden nur kurze, geprüfte Felder behalten (nie eine Commit-Nachricht oder Freitext), alles andere wird mit `202` beantwortet und verworfen.

## So schalten Sie ihn ein

1. Erzeugen Sie ein Geheimnis aus 32 oder mehr Zufallszeichen, zum Beispiel `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Geben Sie es dem Monitor über seine Umgebung, nie über die Datei: `$env:MONITOR_WEBHOOK_SECRET = "<das Geheimnis>"` in PowerShell vor dem Start des Monitors, `export MONITOR_WEBHOOK_SECRET=...` in einer Shell, `Environment=` oder `EnvironmentFile=` (eine Datei, die nur Sie lesen können) in einem Dienst, `-e` oder eine Secret-Datei, die `MONITOR_WEBHOOK_SECRET_FILE` nennt, in einem Container.
3. Schalten Sie den Empfänger ein (Einstellungen > Eingehender Webhook > Empfänger an, oder `"webhook": {"enabled": true}` in `actions_monitor.json`) und starten Sie den Monitor neu.
4. Machen Sie die Adresse erreichbar: GitHub erreicht `127.0.0.1` nicht. Nutzen Sie einen Tunnel, den Sie absichtlich einrichten (eine HTTPS-Adresse mit der Endung `/api/webhook`) oder auf diesem Rechner `gh webhook forward` auf `http://127.0.0.1:PORT/api/webhook` (in der Dokumentation der GitHub-CLI steht, wie man ihm dasselbe Geheimnis gibt, ohne es in die Befehlszeile zu schreiben).
5. Öffnen Sie in GitHub das Repository (oder die Organisation) > Settings > Webhooks > Add webhook. **Payload URL**: die Adresse Ihres Tunnels mit der Endung `/api/webhook`. **Content type**: `application/json`. **Secret**: dasselbe Geheimnis. **SSL verification**: aktiviert. **Events**: „Let me select individual events“, dann Workflow runs und Workflow jobs, optional Check runs, Pushes und Releases. **Active**: an. Ein Webhook einer Organisation deckt alle ihre Repositories ab; der Monitor ignoriert die, die er nicht beobachtet.
6. Prüfen Sie es: In GitHub muss Recent deliveries für das erste `ping` `200` zeigen; im Monitor zeigt die Live-Ansicht den aktiven Empfänger, die Zähler und die Abdeckung.

## Echtzeit-Ereignisse

- Ist `webhook.record_events` an (Standard), aktualisiert ein signiertes `workflow_run`-Ereignis die Run-Liste dieses Repositorys sofort, ohne GitHub zu lesen: Das Repository kostet bis zur nächsten geplanten Lesung kein Kontingent. Ein `workflow_job`-Ereignis liefert zudem Wartezeit und Zeit jedes Schritts für die Analytik.
- Es werden nur kurze, geprüfte Felder behalten (Workflow, Run, Status, Ergebnis, Branch, kurzer Commit, Link zum Run, Dauern); nie die Commit-Nachricht oder freier Text. Die neuesten `webhook.live_events_keep` Ereignisse lassen sich unter `GET /api/live-events` lesen (nur dieser Rechner).
- Optional, standardmäßig aus: Mit `live.sse.enabled` an sendet `GET /api/live-events/stream` dieselben Ereignisse beim Annehmen als Server-Sent Events (`hello`, dann ein `live`-Frame je Ereignis mit laufender `id` zum Fortsetzen über `Last-Event-ID` oder `?since=`, ein Keep-alive-Kommentar und ein abschließendes `bye`). Nur lesend; im Netzwerkmodus verlangt es wie jede Anfrage das Zugriffstoken; höchstens `live.sse.max_clients` Zuhörer, je `live.sse.max_seconds`. Die Lite-Edition hat es nicht.
- Ein rot endender Run löst bei aktiven Benachrichtigungen auch `workflow_failed` aus. Bei ausgeschaltetem `webhook.record_events` kehrt der Webhook zum oben beschriebenen reinen Aktualisierungsmodus zurück.
- GitHub erreicht `127.0.0.1` nicht: Nutzen Sie `gh webhook forward` (siehe Dokumentation der GitHub-CLI) oder einen bewusst eingerichteten Tunnel auf `http://127.0.0.1:PORT/api/webhook`.

## Abdeckung in der Zeit

Die Live-Ansicht sagt, wie viel der Zeit die Ereignisse den Zustand abdecken: **durch Ereignisse abgedeckt** (das letzte Ereignis ist neuer als `savings.webhook_window_minutes`, standardmäßig 60 Minuten), **seit ... kein Ereignis** (älter: ein ruhiges Repository oder ein verlorener Tunnel) oder **warte auf das erste Ereignis**. Die Abfrage bleibt immer der Rückfall: Eine Lieferung, die nie ankam (Monitor aus, Tunnel unterbrochen), wird beim nächsten Lesen des Repositorys nachgeholt; Ereignisse senken also die Lesezugriffe, ersetzen sie aber nie. Dieselben Werte stehen in `GET /api/live-status` unter `coverage` und `secret_source` (`env`, `config` oder `none`; nie das Geheimnis).

## Wenn es nicht funktioniert

| Antwort | Bedeutung |
|---|---|
| `404` | Der Empfänger ist aus, oder das Geheimnis fehlt oder ist in der Umgebungsvariable kürzer als 32 Zeichen. |
| `401` | Die Signatur stimmt nicht: auf beiden Seiten dasselbe Geheimnis und der Inhaltstyp `application/json`. |
| `413` | Der Body ist größer als 256 KB. |
| `400` | Keine gültige `X-GitHub-Delivery`-ID oder ein nicht verständlicher Inhalt. |
| `202` | Angenommen und ignoriert: ein nicht beobachtetes Repository, ein Ereignis außerhalb der Liste, eine wiederholte Lieferung oder ein Repository über seinem Limit pro Minute. |
| `429` | Eine Adresse hat mehr als 120 Anfragen in einer Minute geschickt (Netzwerkmodus). |

## Wiederholungen und Flut

Eine gültige signierte Anfrage, die jemand abgefangen hat und erneut sendet, wird beantwortet, aber nicht ausgeführt: Jede Lieferung braucht ihre `X-GitHub-Delivery`-Kennung, bereits akzeptierte Kennungen werden `webhook.replay_seconds` lang gemerkt (standardmäßig eine Stunde, begrenzter Speicher), und eine Wiederholung erhält `202 {"duplicate": true}`. (Eine manuelle erneute Zustellung von der GitHub-Seite verwendet dieselbe Kennung und wird in diesem Fenster ignoriert.) Ein Repository kann höchstens `webhook.max_per_minute` akzeptierte Ereignisse pro Minute auslösen; der Rest wird beantwortet und ignoriert. Nennt die Nutzlast `full_name`, muss dessen Eigentümer das beobachtete Konto sein (oder einer aus `webhook.allowed_owners`). Im Netzwerkmodus darf eine Adresse 120 Anfragen pro Minute senden. Nach einem akzeptierten Ereignis werden die gespeicherten bedingten Lesevorgänge dieses Repositorys verworfen und im nächsten Zyklus neu gelesen, so wird ein Live-Ereignis immer mit GitHub abgeglichen.

## Checkliste für die Live-Ansicht

1. Lege ein Geheimnis mit mindestens 32 Zeichen in der Umgebungsvariable ab, die `webhook.secret_env` nennt, und schalte den Webhook ein.
2. Leite den Port weiter (`gh webhook forward`) oder öffne einen Tunnel und trage dessen Adresse mit der Endung `/api/webhook` bei GitHub ein.
3. Sende das Testereignis von GitHub (Recent deliveries > Redeliver) und suche es in `?view=live`.
4. Beobachte das Kontingent in der Kopfzeile: Mit Webhooks genügt ein langsamerer Zyklus.
