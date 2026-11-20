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
- Das gemeinsame Geheimnis ist die einzige Schranke: GitHub kann kein Zugriffstoken senden, daher verlangt der Empfänger keines und vertraut nur der Signatur. Bei eingeschaltetem Empfänger ohne Geheimnis weist er jede Lieferung mit `401` ab, und der Doctor meldet das in Rot. Halten Sie die Adresse hinter einem Tunnel oder Proxy, den Sie selbst kontrollieren.
- Jede Anfrage muss `X-Hub-Signature-256: sha256=<hmac>` tragen, mit diesem Geheimnis gebildet und in konstanter Zeit verglichen; alles andere erhält `401`, und vom Inhalt wird nichts angesehen, bevor die Signatur geprüft ist.
- Ein Body über `webhook.max_body_kb` (standardmäßig 1 MiB, bis 25 MiB) erhält `413`, bevor irgendetwas gelesen oder berechnet wird; die Ablehnungen werden in `stats.too_big` gezählt.
- Die Listen sind geschlossen: nur `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` und `ping` werden verarbeitet, von einem Ereignis werden nur kurze, geprüfte Felder behalten (nie eine Commit-Nachricht oder Freitext), alles andere wird mit `202` beantwortet und verworfen.

## So schalten Sie ihn ein

1. Erzeugen Sie ein Geheimnis aus 32 oder mehr Zufallszeichen, zum Beispiel `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Geben Sie es dem Monitor über seine Umgebung, nie über die Datei: `$env:MONITOR_WEBHOOK_SECRET = "<das Geheimnis>"` in PowerShell vor dem Start des Monitors, `export MONITOR_WEBHOOK_SECRET=...` in einer Shell, `Environment=` oder `EnvironmentFile=` (eine Datei, die nur Sie lesen können) in einem Dienst, `-e` oder eine Secret-Datei, die `MONITOR_WEBHOOK_SECRET_FILE` nennt, in einem Container.
3. Schalten Sie den Empfänger ein (Einstellungen > Eingehender Webhook > Empfänger an, oder `"webhook": {"enabled": true}` in `actions_monitor.json`) und starten Sie den Monitor neu.
4. Machen Sie die Adresse erreichbar: GitHub erreicht `127.0.0.1` nicht. Nutzen Sie einen Tunnel, den Sie absichtlich einrichten (eine HTTPS-Adresse mit der Endung `/api/webhook`) oder auf diesem Rechner `gh webhook forward` auf `http://127.0.0.1:PORT/api/webhook` (in der Dokumentation der GitHub-CLI steht, wie man ihm dasselbe Geheimnis gibt, ohne es in die Befehlszeile zu schreiben).
5. Öffnen Sie in GitHub das Repository (oder die Organisation) > Settings > Webhooks > Add webhook. **Payload URL**: die Adresse Ihres Tunnels mit der Endung `/api/webhook`. **Content type**: `application/json`. **Secret**: dasselbe Geheimnis. **SSL verification**: aktiviert. **Events**: „Let me select individual events“, dann Workflow runs und Workflow jobs, optional Check runs, Pushes und Releases. **Active**: an. Ein Webhook einer Organisation deckt alle ihre Repositories ab; der Monitor ignoriert die, die er nicht beobachtet.
6. Prüfen Sie es: In GitHub muss Recent deliveries für das erste `ping` `200` zeigen; im Monitor zeigt die Live-Ansicht den aktiven Empfänger, die Zähler und die Abdeckung.

## Echtzeit-Ereignisse

- Ist `webhook.record_events` an (Standard), aktualisiert ein signiertes `workflow_run`-Ereignis die Run-Liste dieses Repositorys sofort, ohne zuvor GitHub zu lesen: Der Run behält die Art des Ereignisses, die er schon hatte, seine Farbe ändert sich also nicht, und das Repository wird im nächsten Zyklus zur Bestätigung erneut gelesen (eine Lesung pro angenommenem Ereignis). Ein `workflow_job`-Ereignis liefert zudem Wartezeit und Zeit jedes Schritts für die Analytik.
- Es werden nur kurze, geprüfte Felder behalten (Workflow, Run, Status, Ergebnis, Branch, kurzer Commit, Link zum Run, Dauern); nie die Commit-Nachricht oder der Autor. Die kurzen Namen von Workflow, Branch, Job und Schritten werden ebenfalls behalten, einzeilig und wie jeder Text bereinigt, der den Monitor verlässt. Die neuesten `webhook.live_events_keep` Ereignisse lassen sich unter `GET /api/live-events` lesen (im Netzwerkmodus mit dem Zugriffstoken).
- Ist `webhook.record_events` an (Standard), aktualisiert ein signiertes `workflow_run`-Ereignis die Run-Liste dieses Repositorys sofort, ohne GitHub zu lesen: das Repository wird im nächsten Zyklus trotzdem erneut gelesen (das Ereignis ist die Nachricht, die Lesung der Beweis); eine Lieferung zeigt die Änderung also sofort, spart aber keine Lesung. Ein `workflow_job`-Ereignis liefert zudem Wartezeit und Zeit jedes Schritts für die Analytik.
- Es werden nur kurze, geprüfte Felder behalten (Workflow, Run, Status, Ergebnis, Branch, kurzer Commit, Link zum Run, Dauern); nie die Commit-Nachricht. Die Namen von Workflow, Branch und Job sind Text Dritter von bis zu 100 Zeichen: Sie werden behalten und als einfacher Text angezeigt, die Namen der Schritte gehen in die Statistik. Die neuesten `webhook.live_events_keep` Ereignisse lassen sich unter `GET /api/live-events` lesen (wer die Seite öffnen darf: das Zugriffs-Token im Netzwerkmodus, eine Sitzung im Teammodus).
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
| `413` | Der Body ist größer als `webhook.max_body_kb` (standardmäßig 1 MiB). |
| `503` | Die Warteschlange der Ereignisse ist voll: GitHub oder du sendet sie später erneut (`Retry-After`); die Zustellung wird nicht als Duplikat gemerkt. |
| `400` | Keine gültige `X-GitHub-Delivery`-ID oder ein nicht verständlicher Inhalt. |
| `202` | Angenommen und ignoriert: ein nicht beobachtetes Repository, ein Ereignis außerhalb der Liste, eine wiederholte Lieferung oder ein Repository über seinem Limit pro Minute. |
| `429` | Eine Adresse hat mehr als 120 korrekt signierte Anfragen in einer Minute geschickt oder mehr als `webhook.max_bad_per_minute` (standardmäßig 120), deren Signatur nicht stimmt. |

## Wiederholungen und Flut

Eine gültige signierte Anfrage, die jemand abgefangen hat und erneut sendet, wird beantwortet, aber nicht ausgeführt: Jede Lieferung braucht ihre `X-GitHub-Delivery`-Kennung, bereits akzeptierte Kennungen und der signierte Inhalt selbst werden `webhook.replay_seconds` lang gemerkt (standardmäßig eine Stunde, begrenzter Speicher); eine abgefangene Anfrage, die mit anderer Kennung erneut gesendet wird, ist also dieselbe Lieferung, und eine Wiederholung erhält `202 {"duplicate": true}`. (Eine manuelle erneute Zustellung von der GitHub-Seite wiederholt denselben Inhalt und wird in diesem Fenster ignoriert.) Ein Repository kann höchstens `webhook.max_per_minute` akzeptierte Ereignisse pro Minute auslösen; der Rest wird beantwortet und ignoriert. Nennt die Nutzlast `full_name`, muss dessen Eigentümer das beobachtete Konto sein (oder einer aus `webhook.allowed_owners`). Eine Adresse darf pro Minute 120 korrekt signierte Anfragen senden und `webhook.max_bad_per_minute` mit falscher Signatur; beide werden in jedem Modus getrennt gezählt, sodass Müll nie das Kontingent der echten Lieferungen aufbraucht (mit `listen.trusted_proxy` ist es die Adresse, die der Proxy gesehen hat). Nach einem akzeptierten Ereignis werden die gespeicherten bedingten Lesevorgänge dieses Repositorys verworfen und im nächsten Zyklus neu gelesen, so wird ein Live-Ereignis immer mit GitHub abgeglichen. Das Gedächtnis der Lieferungen liegt in einer privaten Datei im Datenordner (`webhook.persist_deliveries`, standardmäßig an; begrenzt, und eine beschädigte Datei ist ein leeres Gedächtnis), sodass ein Neustart eine abgefangene Lieferung nicht wieder gültig macht. Bei eingeschaltetem `webhook.reject_stale` (standardmäßig aus) wird ein signiertes Workflow-Ereignis, dessen eigene Zeit älter als `webhook.replay_seconds` ist, beantwortet und ignoriert. Das Kontingent korrekt signierter Anfragen einer Adresse ist `webhook.max_verified_per_minute` (120). `webhook.secret_env` nimmt nie eine Variable des Systems oder Ihrer GitHub-Anmeldung (PATH, GH_TOKEN...) an, auch kein Geheimnis, das zu einer anderen Einstellung gehört, und ein Name darf nur in einer Einstellung stehen.

Maßgeblich ist immer die Uhr dieses Rechners, nie die der Zustellung. `webhook.clock_skew_s` (standardmäßig 300 Sekunden, 0 bis 3600) ist die Abweichung, die zwei Uhren haben dürfen: Ein Ereignis, das um so viel älter als das Fenster aussieht, gilt deshalb nicht als veraltet (`webhook.reject_stale`), und ein Ereignis, das markiert wurde, als die Uhr dieses Rechners vorging und später zurückgestellt wurde, zählt trotzdem als eingetroffen, sodass ein Repository nicht wegen einer Uhr als tot erscheint; es altert ab dem Moment, in dem es bemerkt wird. Eine Markierung, die mehr als einen Tag voraus ist, wird nicht geglaubt.

## Reihenfolge, Warteschlange und verlorene Zustellungen

- **Reihenfolge.** GitHub verspricht keine Reihenfolge der Zustellungen. Ein Lauf oder Job geht nur vorwärts (wartend, läuft, abgeschlossen): Ein Ereignis, das weniger sagt als das, was über denselben Lauf schon bekannt ist (auch das, was der letzte Zyklus las), ändert nichts und wird in `stats.out_of_order` von `GET /api/live-status` gezählt. Ein neuer Versuch eines Laufs beginnt von vorn.
- **Warteschlange.** Ein angenommenes Ereignis wartet in einer Warteschlange von höchstens `webhook.queue_max` Ereignissen (standardmäßig 500, 1 bis 10000), und ein Worker wendet es an, sodass GitHub schnell eine Antwort bekommt. Ist die Warteschlange voll, antwortet der Empfänger `503` mit `Retry-After` und vergisst die Zustellung, damit die erneute Zustellung von GitHub angenommen wird: Ein Ereignis geht nie stillschweigend verloren. Die Tiefe steht als `queue` in `GET /api/live-status`, die Ablehnungen als `stats.queue_full`.
- **Verlorene Zustellungen.** Ein Lauf, den ein Ereignis offen ließ (wartend oder laufend) und der innerhalb von `webhook.stale_after_h` Stunden (standardmäßig 6, 1 bis 168) kein Abschlussereignis bekommt, wird in der Laufliste als `stale` markiert, und sein Repository wird im nächsten Zyklus neu gelesen (`stats.stale`; `open_runs` zählt die offen gehaltenen Läufe).
- **Bereit.** `GET /readyz` (nur von diesem Rechner) antwortet `200`, wenn der Monitor Arbeit annehmen kann, und `503`, wenn nicht, mit der fehlschlagenden Prüfung: `loaded` (ein erstes Lesen liegt vor), `cycle` (die Aktualisierungsschleife hängt nicht und ist nicht beendet), `store` (der Datenordner ist beschreibbar) und `queue` (die Warteschlange hat Platz). `GET /api/health` sagt nur, dass der Prozess lebt.

## Ohne Webhook: die Ereignisse des Kontos (standardmäßig aus)

Mit eingeschaltetem `events_feed.enabled` liest der Monitor alle `events_feed.interval_seconds` (standardmäßig 60; `X-Poll-Interval` gilt, wenn es länger ist) mit einem ETag die Ereignisse des Kontos (`GET /orgs/OWNER/events` oder `/users/OWNER/events`; `events_feed.owner_kind` sagt welche, `auto` versucht zuerst die Organisation). Ein Lesevorgang ohne Neues antwortet `304` und kostet kein Kontingent; hat sich etwas geändert (ein Push, ein Pull Request, ein Tag oder ein Release), wird im nächsten Zyklus nur das im Ereignis genannte Repository neu gelesen, höchstens `events_feed.max_per_tick` pro Durchlauf. Der erste Lesevorgang lernt nur, wo die Liste steht. Es braucht weder Webhook noch Tunnel und kann neben einem laufen. Die Zähler stehen unter `feed` in `GET /api/live-status`.

## Checkliste für die Live-Ansicht

1. Lege ein Geheimnis mit mindestens 32 Zeichen in der Umgebungsvariable ab, die `webhook.secret_env` nennt, und schalte den Webhook ein.
2. Leite den Port weiter (`gh webhook forward`) oder öffne einen Tunnel und trage dessen Adresse mit der Endung `/api/webhook` bei GitHub ein.
3. Starte einen Workflow (oder pushe in ein beobachtetes Repository) und suche das Ereignis in `?view=live`. Der `ping` von GitHub beweist nur die Signatur: Er wird mit `200` beantwortet und nicht aufgelistet, und eine erneute Zustellung von GitHub wird als Wiederholung ignoriert.
4. Beobachte das Kontingent in der Kopfzeile: Mit Webhooks genügt ein langsamerer Zyklus.
