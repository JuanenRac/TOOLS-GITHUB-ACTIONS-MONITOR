<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Eingehender Webhook

Optional und **standardmäßig aus**. GitHub kann dem Monitor damit melden, dass sich etwas geändert hat, sodass das Repository im nächsten Zyklus aktualisiert wird, statt auf die nächste Abfrage zu warten.

## Was er tut (nur aktualisieren)

Ein akzeptiertes Ereignis markiert nur das darin genannte Repository für eine Aktualisierung im nächsten Zyklus. Es wird nichts nach GitHub oder auf die Platte geschrieben, kein Text des Ereignisses gespeichert oder angezeigt, und nur Repositorys, die der Monitor ohnehin beobachtet, werden akzeptiert. Verstandene Ereignisse: `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` und `ping`; alles andere wird mit `202` beantwortet und ignoriert.

## Sicherheit

- Der Monitor lauscht weiterhin nur auf `127.0.0.1`. GitHub erreicht ihn nur über einen Tunnel, den Sie bewusst einrichten; das Werkzeug öffnet nie einen.
- Aus, bis `webhook.enabled` an ist **und** das gemeinsame Geheimnis in `actions_monitor.json` mindestens 32 Zeichen hat (sonst bleibt der Endpunkt geschlossen).
- Jede Anfrage braucht `X-Hub-Signature-256: sha256=<hmac>`, mit diesem Geheimnis gebildet; alles andere bekommt `401`. Das Geheimnis wird nie angezeigt: der Reiter Einstellungen sagt nur, ob es definiert ist.
- Ein Rumpf über 256 KB bekommt `413`.

## So schalten Sie ihn ein

In `actions_monitor.json`: `"webhook": {"enabled": true, "secret": "<32 oder mehr Zufallszeichen>"}`; der Schalter steht auch im Reiter Einstellungen (Unterreiter Eingehender Webhook), das Geheimnis nur in der Datei. Starten Sie den Monitor neu. In den GitHub-Webhook-Einstellungen: Inhaltstyp `application/json`, dasselbe Geheimnis und die URL Ihres Tunnels mit Endung `/api/webhook`.

## Echtzeit-Ereignisse

- Ist `webhook.record_events` an (Standard), aktualisiert ein signiertes `workflow_run`-Ereignis die Run-Liste dieses Repositorys sofort, ohne GitHub zu lesen: Das Repository kostet bis zur nächsten geplanten Lesung kein Kontingent. Ein `workflow_job`-Ereignis liefert zudem Wartezeit und Zeit jedes Schritts für die Analytik.
- Es werden nur kurze, geprüfte Felder behalten (Workflow, Run, Status, Ergebnis, Branch, kurzer Commit, Link zum Run, Dauern); nie die Commit-Nachricht oder freier Text. Die neuesten `webhook.live_events_keep` Ereignisse lassen sich unter `GET /api/live-events` lesen (nur dieser Rechner).
- Ein rot endender Run löst bei aktiven Benachrichtigungen auch `workflow_failed` aus. Bei ausgeschaltetem `webhook.record_events` kehrt der Webhook zum oben beschriebenen reinen Aktualisierungsmodus zurück.
- GitHub erreicht `127.0.0.1` nicht: Nutzen Sie `gh webhook forward` (siehe Dokumentation der GitHub-CLI) oder einen bewusst eingerichteten Tunnel auf `http://127.0.0.1:PORT/api/webhook`.

## Wiederholungen und Flut

Eine gültige signierte Anfrage, die jemand abgefangen hat und erneut sendet, wird beantwortet, aber nicht ausgeführt: Jede Lieferung braucht ihre `X-GitHub-Delivery`-Kennung, bereits akzeptierte Kennungen werden `webhook.replay_seconds` lang gemerkt (standardmäßig eine Stunde, begrenzter Speicher), und eine Wiederholung erhält `202 {"duplicate": true}`. (Eine manuelle erneute Zustellung von der GitHub-Seite verwendet dieselbe Kennung und wird in diesem Fenster ignoriert.) Ein Repository kann höchstens `webhook.max_per_minute` akzeptierte Ereignisse pro Minute auslösen; der Rest wird beantwortet und ignoriert. Nennt die Nutzlast `full_name`, muss dessen Eigentümer das beobachtete Konto sein (oder einer aus `webhook.allowed_owners`). Im Netzwerkmodus darf eine Adresse 120 Anfragen pro Minute senden. Nach einem akzeptierten Ereignis werden die gespeicherten bedingten Lesevorgänge dieses Repositorys verworfen und im nächsten Zyklus neu gelesen, so wird ein Live-Ereignis immer mit GitHub abgeglichen.

## Checkliste für die Live-Ansicht

1. Lege `webhook.secret` mit mindestens 32 Zeichen fest und schalte den Webhook ein.
2. Leite den Port weiter (`gh webhook forward`) oder öffne einen Tunnel und trage dessen Adresse mit der Endung `/api/webhook` bei GitHub ein.
3. Sende das Testereignis von GitHub (Recent deliveries > Redeliver) und suche es in `?view=live`.
4. Beobachte das Kontingent in der Kopfzeile: Mit Webhooks genügt ein langsamerer Zyklus.
