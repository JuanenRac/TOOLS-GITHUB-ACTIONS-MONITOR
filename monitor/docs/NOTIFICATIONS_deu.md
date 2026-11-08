<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# Benachrichtigungen

Optional und **standardmäßig aus**. Die Ereignisse des Feeds (ein neues Rot, ein hängender Build, ein Build, der auf seine Signatur wartet, eine verlorene Verbindung, ein vom Webhook gemeldeter fehlgeschlagener Run) lassen sich an einen Chat oder ein Gerät senden. Eine Benachrichtigung ist nur eine Nachricht mit Link: Sie startet nie neu, bricht nie ab und schreibt nie etwas auf GitHub.

## Kanäle

- `telegram` (ein Bot), `discord` und `slack` (Kanal-Webhook), `matrix` (ein Raum), `mqtt` (ein Broker auf diesem Rechner, für Lichter und Signalgeber) und `http_local` (ein POST an eine Adresse auf diesem Rechner).
- Jeder Kanal hat im Reiter Einstellungen (Unterreiter Benachrichtigungen) einen eigenen Schalter und eine Schaltfläche für einen Test.


## Sicherheit

- Tokens und Webhook-URLs werden nie in der Konfiguration gespeichert: Sie tragen den NAMEN einer Umgebungsvariable ein, der Wert wird erst beim Senden gelesen, nie angezeigt, nie protokolliert.
- `discord` akzeptiert nur `discord.com`, `slack` nur `hooks.slack.com`; `mqtt` und `http_local` nur `127.0.0.1`, `localhost` oder `[::1]`.
- Höchstens `notify.max_per_hour` Nachrichten verlassen den Rechner; ein fehlgeschlagenes Senden wird gezählt und ignoriert, es stoppt den Monitor nie.


## Der Adapter-Vertrag

- Für einen Dienst, der nicht in der Liste steht, starten Sie einen kleinen Empfänger auf diesem Rechner und richten `http_local` darauf. Er erhält einen POST mit `Content-Type: application/json` und diesem Rumpf: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` ist eines von `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`. Felder kommen nur hinzu. Antworten Sie mit einem beliebigen 2xx; alles andere zählt als Fehler.
- `mqtt` veröffentlicht dasselbe JSON als Nutzlast einer QoS-0-Nachricht auf `notify.channels.mqtt.topic`.

## Das Limit pro Stunde zählt Nachrichten

`notify.max_per_hour` begrenzt die NACHRICHTEN, die den Computer verlassen, nicht die Ereignisse: Ein Ereignis, das an drei Kanäle geht, verbraucht drei Einheiten, eine je Kanal. Reicht das Kontingent nicht für alle Kanäle, erhalten die ersten Kanäle der Liste die Nachricht, der Rest wird verworfen (die Seite zählt sie als «begrenzt»). Ein Kanal, der nicht senden kann (kein Geheimnis, falsche Adresse), verbraucht nichts. Gezählt wird unter einer einzigen Sperre, mehrere Threads können das Limit also nie überschreiten.
