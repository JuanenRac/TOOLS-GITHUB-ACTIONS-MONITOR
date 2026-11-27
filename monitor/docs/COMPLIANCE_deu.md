<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# Compliance: was du über deine Installation belegen kannst

Alles hier ist ab Werk aus und gilt für die vollständige Edition, außer den beiden Einschränkungen, die für jeden Prozess des Monitors gelten. Nichts davon ist eine Zertifizierung.

## Strikter Nur-Lese-Modus

`security.read_only_strict` (aus). Eingeschaltet wird nichts nach GitHub geschrieben, egal was Edition oder andere Einstellungen sagen: nur lesende `gh`-Befehle werden gestartet (was nicht als Lesen bekannt ist, wird abgelehnt), kein `git push`, kein `act`, und keine Anfrage an die GitHub-API außer GET oder HEAD. Durchgesetzt wird es unterhalb aller Teile mit einem Audit-Hook von Python, der jedes gestartete Programm sieht. Änderbar nur am Computer des Monitors; Lockern erfordert einen Neustart. Das Info-Fenster und `/api/about` (`restrictions`) zeigen, ob es gilt.

## Netzwerkrichtlinie

`security.egress_policy`: `default`, `github_only` oder `none`; `security.egress_allow` ergänzt Hosts (`name`, `*.name`, eine Adresse) oder `program:NAME`. Mit `github_only` erreichen die Prozesse des Monitors nur `api.github.com`, `uploads.github.com`, den Host aus `GH_HOST` (GitHub Enterprise) und das Erlaubte; mit `none` nur diesen Computer, und `gh` wird nicht gestartet. Programme, die selbst ins Netz gehen (`git` bei Netzbefehlen, `apprise`, `curl`, `docker`, Werkzeuge der Geheimnisspeicher), werden nicht gestartet. Eine abgelehnte Verbindung scheitert mit einem Fehler, der die Einstellung nennt. `python bin/monitor_cli.py doctor` schlägt fehl, wenn ein konfiguriertes Ziel außerhalb der Richtlinie liegt, und `doctor --egress` listet alle Ziele. Es ist keine Firewall: was andere Programme des Computers tun, regelt es nicht.

## Der Compliance-Bericht

`python bin/monitor_cli.py compliance report` (mit `--json`), `GET /api/compliance/report` (Administratoren) und ein Kasten am Ende des Tabs Sicherheit. Jede Zeile sagt, ob sie **geprüft** (der Monitor hat nachgesehen) oder nur **angegeben** ist (die Konfiguration sagt es): Version und Support, Edition, Anmeldung und Identitätsanbieter, Netzwerkmodus und TLS, die beiden Einschränkungen und die Ziele, Aufbewahrung und Sperre, Aktionsprotokoll und Kette, Sicherungen und Verschlüsselung, Verschlüsselung ruhender Daten (keine), Speicher, Plugins, Betriebsform und Profil. Keine Geheimnisse, Pfade oder Namen. `GET /api/compliance/state` liefert Einschränkungen, Aufbewahrungstabelle und Exportstatus.

## Aufbewahrung und Aufbewahrungssperre

Ereignisse, Analysen und Bewertungen behalten ihre Einstellungen (`retention.events_days`, `retention.analytics_days`, `retention.mode`). Die übrigen Kategorien bleiben für immer, außer du gibst Tage an: `retention.audit_days` (ganze rotierte Dateien des Aktionsprotokolls), `retention.reports_days` (der neueste Bericht jedes Kontos bleibt), `retention.ai_log_days`, `retention.backups_days` (die neueste Sicherung bleibt). Jede Löschung hinterlässt eine Zeile im Aktionsprotokoll. `retention.legal_hold` stoppt jedes Entfernen: Ereignisse, Analysen, Bewertungen, Berichte, Sicherungen, das Kürzen des Feeds und des Prompt-Protokolls sowie Rotation und Bereinigung des Protokolls. KI-Vorschläge verfallen von selbst; gekoppelte Geräte bleiben, bis du sie entfernst; Postmortems, Vorfälle und Notizen speichert diese Version nicht.

## Signierte Prüfpunkte des Aktionsprotokolls

`audit_checkpoints.enabled` (aus) signiert die Kette (HMAC-SHA256) mit einem Schlüssel der Installation: `config/audit_checkpoint.key` oder die Datei aus `MONITOR_AUDIT_KEY_FILE`, um ihn getrennt zu halten. Ein Prüfpunkt bei der ersten Zeile, dann mindestens stündlich und alle 1000 Zeilen; auch der Anker wird signiert, und ein Abschneiden des Endes mit anschließender neuer Zeile wird in der Kette festgehalten. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint` und `audit purge --older-than-days N` (`--dry-run`), das ganze rotierte Dateien entfernt und signiert, wo die Kette weitergeht. Wer den Schlüssel lesen kann, kann signieren: halte ihn von Schreibern des Protokolls fern.

## Export des Aktionsprotokolls

`audit_export.enabled` (aus) mit `audit_export.target` = `file` (`path`, Rotation bei `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 über TCP mit TLS, `ca_file`) oder `http` (`url`, POST von JSON-Zeilen, Token aus der in `token_env` genannten Variable). Private Adressen brauchen `audit_export.allow_private_targets`. Das Protokoll ist die Warteschlange: was das Ziel nicht annahm, wartet dort; über `spool_mb` meldet der Doctor `system.audit_export_lag`, und vor dem Senden wegrotierte Zeilen zählen als verloren. `python bin/monitor_cli.py audit export` macht sofort einen Durchlauf. Getestet gegen Empfänger auf diesem Computer, nicht gegen ein echtes Syslog- oder SIEM-Produkt.

## Unterstützte Versionen

Unterstützt wird nur die neueste veröffentlichte Version: es gibt keinen Langzeit-Zweig. Der Doctor (`compliance_support`) warnt, wenn er eine neuere kennt.

## Belege der Härtung

`[IMP]` = ein Test dieses Repositorys übt die Kontrolle aus; `[PAR]` = nur ein Teil, und die Zeile sagt, was fehlt. Die Liste ist `schemas/controls.json`, und ein Test prüft, dass diese Tabelle und die genannten Tests übereinstimmen.

| Kontrolle | Stand | Name |
|---|---|---|
| `sqlite_contention` | [IMP] | Mehrere Prozesse schreiben eine Datenbank |
| `storage_migrations` | [IMP] | Migrationen des Speichers |
| `retention_by_category` | [IMP] | Aufbewahrung je Kategorie und Sperre |
| `incoming_webhook` | [IMP] | Eingehender Webhook: Signatur, Größe, Zeit |
| `metrics_labels` | [IMP] | Labels von /metrics |
| `timezone` | [IMP] | Zeitzonen und Zeitumstellung |
| `read_only_strict` | [IMP] | Strikter Nur-Lese-Modus |
| `egress_policy` | [IMP] | Netzwerkrichtlinie |
| `audit_chain` | [IMP] | Kette und Prüfpunkte des Protokolls |
| `service_and_volume` | [PAR] | Dienst unter systemd, große Datenbank (Netzwerkdateisysteme ungetestet) |

## Bekannte Grenzen

- Ein `viewer`-Konto direkt am Computer des Monitors gilt als lokal und sieht vollständige Pfade.
- Der eingehende Webhook prüft das Zeitfenster nur bei `workflow_run`- und `workflow_job`-Zustellungen.
- Bei `none` oder `github_only` wendet ein vom Monitor gestarteter Python-Prozess die Richtlinie nur an, wenn er den Monitor importiert; selbst gestartete Programme liegen außerhalb.
- Verschlüsselung ruhender Daten, ein Langzeit-Zweig und Föderation gibt es in dieser Version nicht.
