<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# Der Reiter Einstellungen

Der Reiter Einstellungen (das Zahnradsymbol in der Kopfzeile oder in der Reiterleiste) ändert die Werte von `actions_monitor.json` direkt auf der Seite, sodass niemand die Datei von Hand bearbeiten muss.
Er ist in den acht Sprachen der Seite verfasst und folgt dem Erscheinungsbild des Rests.

<!-- settings:begin -->
## Was sich ändern lässt

Nur die Schlüssel der Liste in `settings_api.py` (das Schema). Jeder hat Typ und Bereich, und die Seite sagt, ob eine Änderung einen **Neustart** des Monitors braucht (die Schleife liest ihre Konfiguration einmal) oder **sofort gilt**.

Der Reiter ist in Unterreiter gegliedert, vom Gewöhnlichen zum Fortgeschrittenen: Dieser Browser, Allgemein, Aktualisierung und Grenzen, Wächter, Oberflächenprüfungen (A10), Bereitschaft (A11), Ordner und Dateien, Ausgaben, danach die Integrationen. In einem Unterreiter stehen die Einstellungen in Blöcken mit Titel; das erste Feld eines Blocks ist sein Hauptschalter, und solange er aus ist, ist der Rest des Blocks abgedunkelt und nicht editierbar. Jedes Feld zeigt Einheit (s, Min., Std., Tage, MB, Aufrufe), Bereich, ein Abzeichen (braucht Neustart / gilt sofort), ein Abzeichen für Sicherheitsoptionen mit konservativem Standard und eine Hilfezeile. Das Suchfeld filtert die Einstellungen aller Unterreiter; jeder Unterreiter zählt seine ungespeicherten Änderungen; Speichern und Verwerfen bleiben sichtbar; der Browser merkt sich den zuletzt benutzten Unterreiter. Die Reiter folgen dem Tastaturmuster für Reiter (Pfeiltasten, Pos1, Ende).

| Reiter | Blöcke und Einstellungen |
|---|---|
| Dieser Browser | Sprache der Seite, Design (auto / hell / dunkel), dichte Ansicht des Reiters Jetzt. Sie bleiben im Browser, nicht in der Datei. |
| Allgemein | **Identität**: `github_owner`, `language`<br>**Umfang**: `mode`, `repos`, `ecosystems`, `exclude`<br>**Verlauf**: `report_history_days` |
| Aktualisierung und Grenzen | **Heiße Repositorys**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**Kalte Repositorys**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**Hintergrundaufgaben**: `issues_refresh_seconds`, `discover_refresh_seconds`, `max_workers`<br>**API-Kontingent**: `min_rate_remaining` |
| Wächter | **Haupteinstellungen**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**Warnungen und Hygiene**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**API-Budget**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**Releases und Signaturen**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**Rot-Abfragen (A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**Pull Requests**: `sentinel.stale_pr_days`<br>**Pflichtdateien**: `sentinel.required_files`<br>**Actions-Minuten**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**Audit-Dateien**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra` |
| Oberflächenprüfungen (A10) | **Haupteinstellungen**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**Manuell deaktivierte Workflows**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**Zeitpläne ohne Ausführungen**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**uses: nicht per SHA fixiert**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**Zu weit gefasste Berechtigungen (write-all)**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**pull_request_target mit Checkout des PR**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**Festgefahrene Concurrency (wartende Läufe desselben Workflows)**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**Fehler nur auf einem System der Matrix**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**Artifact-Kosten**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**Pflicht-Checks, die rot sind oder fehlen**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**Unvollständig veröffentlichte Releases**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**Release-Tag vs. Version in Manifest/CHANGELOG**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**Vergessene Entwürfe und Vorab-Releases**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**Kritische/hohe Warnungen nach Alter (Repository-Rangliste)**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**Sicherheitsabdeckung (CodeQL / Dependabot)**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**Secret Scanning: offen vs. gelöst**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**Dependabot nach Priorität**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**Issues, die geschlossen werden könnten (nur Vorschlag)**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**Überfällige Meilensteine pro Ökosystem**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**Veraltete PRs von Menschen**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**PRs, die Workflows oder CODEOWNERS ändern (Priorität)**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**Merge-Warteschlange: genehmigt mit grüner CI**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**Reifegrad im Manifest vs. Nachweis**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**Gebrochene README-Parität der 8 Sprachen**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**Build-Attestierungen**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| Bereitschaft (A11) | **Haupteinstellungen**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**Gewichte der Gesundheit**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**Fixierte Versionen**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| Ordner und Dateien | **Lokale Ordner**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**Datendateien**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Ausgaben für andere Werkzeuge | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**Grafana-JSON**: `outputs.json.enabled`<br>**Status-Dashboard**: `outputs.dashboard.enabled` |
| Externe KI für den Wächter | **Dienst**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit` |
| Eingehender Webhook | **Eingehender Webhook**: `webhook.enabled`, `webhook.signing_state` |

Jede Einstellung steht nur an einer Stelle. Nur lesend: `webhook.signing_state` sagt nur, ob das gemeinsame Geheimnis definiert ist; das Geheimnis selbst wird nie angezeigt.

### Beispiel für Quellen der Fixierungen

Die Fixierungen werden nur gelesen, wenn eine Quelle eingetragen ist; bei leerer Liste wird nichts gelesen, und die Seite sagt es. Der folgende Text ist ein auskommentiertes Beispiel:

```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```
<!-- settings:end -->

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
