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
- Ein Ziel, das eine Loopback-, private (10.x, 172.16-31.x, 192.168.x, fc00::/7), Link-Local- (169.254.x mit der Cloud-Metadatenadresse, fe80::/10), gemeinsame (100.64.0.0/10) oder reservierte Adresse ist oder dorthin aufgelöst wird, wird abgelehnt, solange `notify.allow_private_targets` aus ist (Standard). Der Name wird einmal aufgelöst, die Verbindung geht zur geprüften Adresse, und jede Weiterleitung durchläuft dieselbe Regel. So erreicht ein falsch eingetragener Matrix-Server weder Ihren Router noch den Metadatendienst einer Cloud-Maschine.
- Höchstens `notify.max_per_hour` Nachrichten verlassen den Rechner; ein fehlgeschlagenes Senden wird gezählt und ignoriert, es stoppt den Monitor nie.


## Der Adapter-Vertrag

- Für einen Dienst, der nicht in der Liste steht, starten Sie einen kleinen Empfänger auf diesem Rechner und richten `http_local` darauf. Er erhält einen POST mit `Content-Type: application/json` und diesem Rumpf: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` ist eines von `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`. Felder kommen nur hinzu. Antworten Sie mit einem beliebigen 2xx; alles andere zählt als Fehler.
- `mqtt` veröffentlicht dasselbe JSON als Nutzlast einer QoS-0-Nachricht auf `notify.channels.mqtt.topic`.

## Das Limit pro Stunde zählt Nachrichten

`notify.max_per_hour` begrenzt die NACHRICHTEN, die den Computer verlassen, nicht die Ereignisse: Ein Ereignis, das an drei Kanäle geht, verbraucht drei Einheiten, eine je Kanal. Reicht das Kontingent nicht für alle Kanäle, erhalten die ersten Kanäle der Liste die Nachricht, der Rest wird verworfen (die Seite zählt sie als «begrenzt»). Ein Kanal, der nicht senden kann (kein Geheimnis, falsche Adresse), verbraucht nichts. Gezählt wird unter einer einzigen Sperre, mehrere Threads können das Limit also nie überschreiten.

## Benachrichtigungen je Benutzer (Teammodus)

Standardmäßig aus (`notify.users.enabled`). Bei eingeschaltetem Teammodus wählt jeder Benutzer unter `GET/POST /api/auth/me/notify` die Kanäle (`ntfy`, `teams`, `email`), die Sentinels (`ci`, `collab`), die Mindeststufe (`info`, `warn`, `bad`), ob er die Ereignisse des Systems möchte und ob die Nachrichten sofort oder gesammelt als Zusammenfassung kommen (`hourly`, `daily`). Die Rolle bestimmt, was ein Benutzer erfahren darf: ein Betrachter die CI-Ereignisse der Konten, die er sehen darf; ein Maintainer zusätzlich, was auf einen Menschen wartet (ein Build wartet auf die Signatur, ein Release ist fällig); ein Administrator zusätzlich die Ereignisse des Systems. Ein Ereignis eines Kontos erreicht nie jemanden, der dieses Konto nicht sehen darf. `notify.users.max_per_hour` begrenzt die Nachrichten je Benutzer.

- `ntfy`: das Thema jedes Benutzers auf dem Server `notify.channels.ntfy.server` (https oder einer auf diesem Rechner); ein Zugriffstoken ist optional.
- `teams`: die Adresse des eingehenden Webhooks eines Teams-Kanals (nur Hosts von Microsoft).
- `email`: die Adresse des Benutzers, gesendet über ein Relay auf diesem Rechner ohne Anmeldung (`notify.channels.email`).

Die Adresse des Teams-Webhooks und das ntfy-Token verwahrt das System verschlüsselt (DPAPI, Schlüsselbund, Secret Service oder eine private Datei); sie erscheinen nie in einer Antwort, einem Protokoll oder der Konfiguration; beim Löschen eines Benutzers werden sie gelöscht. `MONITOR_SECRET_BACKEND=file` erzwingt die private Datei. Jeder Kanal ist aus, bis der Administrator ihn einschaltet. Die Zusammenfassung sammelt die Meldungen, die der Benutzer noch nicht gesehen hat (bis `notify.digest.max_items`); `POST /api/auth/me/notify/seen` markiert sie als gesehen und sie werden nicht gesendet; `POST /api/auth/me/notify/test` sendet eine Testnachricht an die Kanäle des Benutzers. Ein Administrator liest die Einstellungen aller (nie ein Geheimnis) unter `GET /api/auth/notify`.
