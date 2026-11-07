<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# Der Reiter Einstellungen

Der Reiter Einstellungen (das Zahnradsymbol in der Kopfzeile oder in der Reiterleiste) ändert die Werte von `actions_monitor.json` direkt auf der Seite, sodass niemand die Datei von Hand bearbeiten muss.
Er ist in den acht Sprachen der Seite verfasst und folgt dem Erscheinungsbild des Rests.

## Was sich ändern lässt

Nur die Schlüssel der Liste in `settings_api.py` (das Schema). Jeder hat einen Typ und einen Wertebereich, und die Seite zeigt an, ob eine Änderung einen **Neustart** des Monitors erfordert (die Schleife liest
ihre Konfiguration nur einmal) oder **sofort wirkt**.

| Gruppe | Schlüssel |
|---|---|
| Dieser Browser | Sprache der Seite, Design (auto / hell / dunkel), dichte Ansicht des Reiters Jetzt. Diese Werte bleiben im Browser und nicht in der Datei. |
| Allgemein | `language` (Standardsprache der Werkzeuge), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Aktualisierung und Grenzen | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Wächter | `sentinel.enabled`, die Zyklen, das API-Budget, die Schwellen für Kandidaten, veraltete Pull Requests und ausstehende Signaturen, `sentinel.require_verified_signature`, die Abfragen von A2 |
| Oberflächenprüfungen (A10) | `sentinel.surface.enabled`, deren Zyklen, die Repositories pro Zyklus, der Spielraumfaktor und der Anteil am Budget |
| Bereitschaft (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Ordner und Dateien | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Ausgaben für andere Werkzeuge | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (siehe OUTPUTS_deu.md) |
| Externe KI für den Wächter | `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (nur dieser Rechner), `ai.base_url` (https), `ai.api_key_env` (der NAME der Umgebungsvariable mit dem Schlüssel) und `ai.daily_limit`. Der Schlüssel selbst wird nie gespeichert. Standardmäßig aus; ein externer Dienst erhält Daten Ihrer Repositories. |

## Was sich von der Seite aus nie ändern oder einsehen lässt

Tokens, Geheimnisse, Signaturschlüssel, das Webhook-Geheimnis, der Befehl, den der Wächter ausführen darf (`sentinel.notify_command`), der API-Schlüssel der KI (nur der Name seiner Umgebungsvariable kann gesetzt werden) und jeder Schlüssel eines anderen Werkzeugs: Sie sind **nicht im
Schema** enthalten, daher zeigt die Seite sie weder an noch schreibt sie diese, und eine Anfrage, die einen davon nennt, wird abgelehnt. Alle übrigen Schlüssel der Datei bleiben genau so, wie sie waren.

## Wie ein Speichern abläuft

1. Es werden nur die geänderten Werte gesendet, als `POST /api/settings` mit `Content-Type: application/json` und einem Body von höchstens 16 KB.
2. Jeder Wert wird gegen seinen Typ und seinen Wertebereich geprüft; ein einziger ungültiger Wert lehnt die gesamte Anfrage ab, und nichts wird geschrieben. Pfade müssen Text ohne Steuerzeichen sein, niemals ein
   Netzwerkpfad (UNC) und niemals auf dem Laufwerk `D:`.
3. Die vorherige Datei wird nach `config_backups/actions_monitor-<time>.json` kopiert (die letzten zehn Kopien bleiben erhalten).
4. Die neue Datei wird in eine temporäre Datei geschrieben und über die alte verschoben (atomar), sodass ein Absturz nie eine halbe Datei hinterlässt. Eine Datei, die kein gültiges JSON ist, wird von der Seite aus nie überschrieben.
5. Die Seite zeigt an, welche gespeicherten Werte einen Neustart erfordern, und hält einen Hinweis bereit, bis Sie neu starten.

## Wer anfragen darf

Nur die Seite desselben Rechners: Der Server lauscht auf `127.0.0.1` und lehnt jede Anfrage ab, deren `Host` oder `Origin` nicht seine eigene Adresse ist (dieselben Prüfungen wie bei jedem anderen Endpunkt).
Ein Formular von einer fremden Seite kann ihn nicht erreichen, da die Anfrage JSON sein muss.

## Vor 1.5.0

Die Sprache der Werkzeuge wurde von der Systemsprache bestimmt; jetzt starten sie auf Englisch, und die Sprache ist eine Einstellung (hier `language`, `MONITOR_LANG` oder `--lang`).
`parte_history_days` heißt jetzt `report_history_days` (der alte Name wird weiterhin gelesen).
