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
