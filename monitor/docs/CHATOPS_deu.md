<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# Chat-Befehle (Slack und Discord)

Optional, **standardmäßig aus**. Damit können Personen den Monitor aus einem Slack- oder Discord-Kanal nach einem kurzen Status fragen: wie viele Repositories rot sind, die offenen Warnungen, die Warteschlange und die Punktzahl. Es ist **nur lesend**.

## Was es tut (und nie tut)

- Die Befehle sind eine geschlossene Liste: `help`, `status`, `alerts`, `red`, `queue` und `score`. Alles andere wird mit "Diesen Befehl kenne ich nicht" beantwortet. `chatops.allowed_words` kann die Liste nur verkleinern.
- Ein Befehl liest, was der Monitor schon hat (den letzten Zyklus, die Warnungen, die Punktzahl). Er schreibt nie auf GitHub, führt nie eine Aktion aus, ändert nie eine Einstellung und liest nie ein Geheimnis; dafür gibt es keinen Befehl, und aus dem Chat lässt sich keiner hinzufügen.
- Die Antwort sieht nur, wer gefragt hat; sie erwähnt niemanden und enthält keinen Link außer einem: Ist `chatops.links` an (Standard), die Adresse eines Repositorys (`https://<Host>/<Eigentümer>/<Repository>`, geprüft) neben einem Namen, der unverändert angezeigt wird. Jeder Text von GitHub (Name eines Repositorys oder Workflows) wird bereinigt, gekürzt und für die Plattform maskiert.
- Jeder Befehl, der den Monitor erreicht, hinterlässt eine Zeile im Aktionsprotokoll (`chatops_command`) mit den IDs des Chats, nie dem Text der Anfrage.

## Sicherheit

- Aus, bis `chatops.enabled` und der Schalter der Plattform (`chatops.slack.enabled`, `chatops.discord.enabled`) an sind **und** der Nachweis in der Umgebung liegt. Die Einstellungen enthalten nur den NAMEN der Variablen (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), nie ihren Wert; der Wert wird nie geschrieben, angezeigt oder protokolliert.
- Slack: Jede Anfrage muss `X-Slack-Signature: v0=<hmac>` tragen, den HMAC-SHA256 von `v0:<Zeitstempel>:<Inhalt>` mit dem Signing Secret, und `X-Slack-Request-Timestamp` darf nicht älter als `chatops.max_age_seconds` sein (höchstens fünf Minuten). Der Vergleich dauert unabhängig von der Signatur gleich lang.
- Discord: Jede Anfrage muss `X-Signature-Ed25519` und `X-Signature-Timestamp` tragen: eine Ed25519-Signatur über Zeitstempel und Inhalt, geprüft mit dem öffentlichen Schlüssel Ihrer App (RFC 8032, Standardbibliothek; ohne Prüfung wird nichts akzeptiert).
- Eine falsche, alte oder aus der Zukunft stammende Signatur erhält `401`, vom Inhalt wird nichts angesehen. Eine bereits akzeptierte Signatur wird nie ein zweites Mal akzeptiert. Ein Inhalt über 16 KB erhält `413`. Eine Adresse darf 120 Anfragen pro Minute stellen.
- **Die Listen sind Pflicht**: `chatops.allowed_teams`, `chatops.allowed_channels` und `chatops.allowed_users`. Ist keine ausgefüllt, läuft kein Befehl (die Challenge der Plattform wird weiter beantwortet, damit Sie die Einrichtung abschließen können). Eine Liste mit Einträgen muss das Team, den Kanal oder den Benutzer der Anfrage enthalten.
- Grenzen pro Minute: `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` und `chatops.rate_per_minute`. Die Antwort muss in 3 Sekunden kommen: Der Monitor antwortet aus dem Speicher und meldet sich bei Verzögerung als beschäftigt.
- Die beiden Routen (`/api/chatops/slack`, `/api/chatops/discord`) verlangen nicht das Zugriffstoken des Netzwerkmodus, weil eine Plattform es nicht senden kann: Die Signatur ist ihr Nachweis, wie beim eingehenden Webhook. Der Monitor lauscht weiter nur auf `127.0.0.1`, solange Sie den Netzwerkmodus nicht öffnen; die Plattformen erreichen ihn nur über eine HTTPS-Adresse, die Sie absichtlich einrichten (Tunnel oder Reverse-Proxy; das Werkzeug öffnet keinen). Geben Sie darüber nur `/api/chatops/` frei.

## Die Befehle

| Befehl | Antwort |
| --- | --- |
| `help` | die Liste der Befehle |
| `status` | Repositories rot, hängend, wartend, grün und untätig sowie die offenen Warnungen |
| `alerts` | die offenen Warnungen (Stufe, Code und Repository), bis zu `chatops.max_rows` |
| `red` | die roten Workflows mit der Dauer, seit der sie rot sind, bis zu `chatops.max_rows` |
| `queue` | laufend, in der Warteschlange, wartend auf Freigabe und Minuten in 24 Stunden |
| `score` | die Punktzahl, ihr Buchstabe und ihre Veränderung |

`chatops.show_repo_names` bestimmt die Namen: `all` (jeder Name, auch private Repositories), `public` (Standard: ein privates Repository heißt `private-N`, seine Workflows werden nicht genannt) oder `none`. **Risiko von `all`:** Die Namen privater Repositories und Workflows erreichen jeden Kanal und Benutzer, den Ihre Listen erlauben. Deshalb sind die Listen Pflicht und jede Liste mit Einträgen muss passen (Team, Kanal und Benutzer zugleich). Behalten Sie `public` oder wählen Sie `none`, wenn der Kanal größer ist als der Kreis, der diese Namen kennen darf.

## Slack, Schritt für Schritt

1. Öffnen Sie api.slack.com/apps > Create New App > From scratch. Vergeben Sie einen Namen und wählen Sie Ihren Workspace.
2. Slash Commands > Create New Command: Befehl `/monitor`, **Request URL** `https://<Ihre öffentliche Adresse>/api/chatops/slack`, eine kurze Beschreibung. Es ist kein Bot-Scope nötig.
3. Basic Information > App Credentials > **Signing Secret**: kopieren Sie es und geben Sie es dem Monitor über die Umgebung, nie über die Datei: `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` in PowerShell vor dem Start des Monitors, `export MONITOR_SLACK_SIGNING_SECRET=...` in einer Shell, ein Umgebungseintrag oder eine Secret-Datei in einem Dienst oder Container.
4. Installieren Sie die App im Workspace (Install App).
5. Füllen Sie die Listen: Ihre Team-ID (beginnt mit `T`), die Kanal-ID (Kanal öffnen, Details, die ID ganz unten: `C...`) und Ihre Mitglieds-ID (Profil > Copy member ID: `U...`). Tragen Sie sie unter Einstellungen > Chat-Befehle ein oder als `"chatops": {"allowed_channels": ["C0123456789"]}` in `actions_monitor.json`.
6. Schalten Sie Chat-Befehle und Slack ein und starten Sie den Monitor neu.

## Discord, Schritt für Schritt

1. Öffnen Sie discord.com/developers/applications > New Application. Kopieren Sie unter General Information den **Public Key** (64 Hexadezimalzeichen) und geben Sie ihn dem Monitor über die Umgebung: `$env:MONITOR_DISCORD_PUBLIC_KEY = "<öffentlicher Schlüssel>"` in PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` in einer Shell.
2. Füllen Sie die Listen, schalten Sie Chat-Befehle und Discord ein (Einstellungen > Chat-Befehle) und starten Sie den Monitor neu. Tun Sie das **vor** dem nächsten Schritt: Discord sendet beim Speichern der Adresse einen signierten Test und lehnt sie ab, wenn der Monitor nicht antwortet.
3. General Information > **Interactions Endpoint URL**: `https://<Ihre öffentliche Adresse>/api/chatops/discord`, dann Save.
4. Registrieren Sie den Befehl einmal mit Ihrem eigenen Werkzeug (Discord-API, `POST /applications/<Anwendungs-ID>/commands`) mit diesem Inhalt:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Laden Sie die App nur mit dem Scope `applications.commands` ein (OAuth2 > URL Generator); es ist keine Bot-Berechtigung nötig. IDs: Aktivieren Sie in Discord den Entwicklermodus (Erweitert) und nutzen Sie ID kopieren beim Server, beim Kanal und bei Ihrem Benutzer.

## Ausprobieren

Tippen Sie in einem erlaubten Kanal `/monitor help` (Slack) oder `/monitor command:status` (Discord). Andere Antworten:

| Was Sie sehen | Bedeutung |
| --- | --- |
| nichts oder "hat nicht geantwortet" | die Adresse ist nicht erreichbar, der Monitor ist aus oder er antwortete `401` (falsches Secret oder falscher Schlüssel oder eine Uhr, die mehr als fünf Minuten abweicht) |
| "Dieser Befehl ist hier nicht verfügbar." | Team, Kanal oder Benutzer stehen nicht in den Listen |
| "Zu viele Befehle." | eine der drei Grenzen pro Minute |
| "Der Monitor hat GitHub noch nicht gelesen." | der erste Zyklus ist noch nicht fertig |
