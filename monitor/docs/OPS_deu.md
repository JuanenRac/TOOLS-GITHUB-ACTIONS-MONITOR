<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# Die Installation betreiben

Für einen Monitor, der monatelang durchläuft (Edition Vollständig). Behandelt die vollständige Sicherung, die Wiederherstellung, die geplante Sicherung, den Doctor mit Exit-Codes, auf die sich ein Cron-Job verlassen kann, und die Einrichtung als Appliance (systemd oder Docker). Die Lite-Edition hat nichts davon.

## Das Sicherungspaket

`python bin/monitor_cli.py backup create [DATEI]` schreibt EINE `.zip`-Datei (Format 2) und prüft sie, bevor sie an ihren Platz kommt. Ohne `DATEI` landet sie im Ordner `backups` des Datenordners (`ops.backup.dir`) mit dem Namen `ghamon-backup-<UTC-Zeit>.zip`. Der Monitor muss nicht angehalten werden: Die Daten werden mit den atomaren Lesezugriffen des Speichers (Dateien oder SQLite) gelesen, nie durch Kopieren einer Datenbank, in die gerade geschrieben wird.

| Mitglied | Was es enthält |
|---|---|
| `dump.jsonl` | jedes Konto (seine Einstellungen, der Zustand der Wächter, die kleinen Dokumente, die Ereignisse, die Analysen, die Score-Schnappschüsse) und die globalen Datensätze (Benutzer und die Konten, die sie sehen dürfen; nie die Sitzungen) |
| `files.json` | die Einstellungen der Seite und die Listen der Installation (`targets.json`, `ecosystems.json`, `profiles.json`, die Stummschaltungen), bereinigt; außerdem die Speicher optionaler Module, wenn es sie gibt (`proposals.json`, `devices.json`) |
| `manifest.json` | das Format, die Produktversion, das Schema, die Zähler sowie Größe und SHA-256 jedes Mitglieds |

**Was nie mitreist:** Tokens und Schlüssel von GitHub oder einer App, Passwörter, der Wert jeder `*_env`-Variablen (nur ihr Name), das Geheimnis des Webhooks, die Schlüssel der KI-Anbieter, die Sitzungen und der Inhalt des Geheimnisspeichers. Die Einstellungen laufen durch eine Whitelist (dieselben Schlüssel, die die Einstellungsseite anzeigen kann) und dann durch eine Bereinigung, die jeden Schlüssel entfernt, der wie ein Geheimnis aussieht, und jeden Text, der wie ein Token oder ein privater Schlüssel aussieht. Ist `ops.backup.include_config` aus, bleiben Einstellungen und Listen ganz draußen. Eine Wiederherstellung bringt keine Zugangsdaten zurück: Richten Sie den GitHub-Zugang neu ein (die Checkliste sagt es).

Die Sicherung ist nur für ihren Eigentümer lesbar (Modus 600) und das Paket ist nur auf Wunsch verschlüsselt: siehe unten.

### Ein Paket für ein Konto

`backup create --account ID [DATEI]` schreibt das Paket EINES Kontos: seinen Dump (mit seinen Einstellungen, auf dieselbe Weise bereinigt) und sonst nichts. Es enthält keinen Benutzer und keine Sitzung und nicht die Einstellungen oder Listen der Installation; das Manifest sagt `scope: account`. `backup verify` prüft, dass es nur dieses Konto enthält, und `backup restore DATEI` stellt dieses Konto wieder her (`--account` ist nicht nötig), ohne die anderen Konten, die Benutzer oder die Dateien des Ziels anzufassen; es wird nur abgelehnt, wenn dieses Konto dort schon existiert und `--force` fehlt. So verschieben oder retten Sie ein einzelnes Konto.

### Die Sicherung verschlüsseln (optional)

`ops.backup.encrypt` (oder `--encrypt` für eine Sicherung) verschlüsselt das Paket mit AES-256-GCM mit einem Schlüssel aus der Umgebungsvariablen, die `ops.backup.key_env` nennt (`--key-env NAME`). Der Schlüssel ist nie eine Einstellung, wird nie aufgeschrieben und steht nie in einer Kommandozeile. Es braucht die optionale Bibliothek `cryptography` (`pip install cryptography`; der Kern des Monitors bleibt reine Standardbibliothek). Ohne die Bibliothek oder ohne einen Schlüssel mit 12 oder mehr Zeichen wird die Sicherung mit klarer Meldung **abgelehnt** und nichts geschrieben: Es entsteht nie eine unverschlüsselte Sicherung, wenn Sie eine verschlüsselte wollten, und nie eine mit etwas Schwächerem verschlüsselte. Eine verschlüsselte Datei endet auf `.enc`; `verify` und `restore` öffnen sie mit derselben Variablen. Bewahren Sie den Schlüssel getrennt von der Datei auf: Ohne ihn lässt sich die Sicherung nicht öffnen.

## Prüfen, auflisten und Status

- `backup verify DATEI` liest das Paket erneut und prüft jede Größe und jeden SHA-256 sowie die Zähler. Ein geändertes Byte, ein fehlendes Mitglied oder eines, das das Manifest nicht auflistet, wird gemeldet. `--deep` stellt es zusätzlich in einem temporären Ordner wieder her und prüft das Ergebnis.
- `backup list` zeigt die Sicherungen im Ordner; `backup status` zeigt die letzte gute Sicherung, ihr Alter, den Zeitplan und den letzten Fehler.
- Ein Paket des ersten Formats (vor 2.1.0 erstellt) lässt sich weiter prüfen und wiederherstellen.

## Wiederherstellen

`python bin/monitor_cli.py backup restore DATEI`: Halten Sie zuerst den Monitor an (eine Wiederherstellung wird abgelehnt, solange einer auf seinem Port antwortet). Sie prüft das Paket und schreibt dann die Konten und Dateien.

- Ein Speicher, der schon Konten enthält, wird abgelehnt, außer Sie fügen `--force` hinzu (die Konten des Pakets werden dann darübergeschrieben; die Einstellungen werden **zusammengeführt**: ein Schlüssel, den das Paket nicht enthält, wird nie entfernt).
- `--account ID` stellt nur dieses Konto wieder her und lässt die anderen und die globalen Dateien, wie sie sind (abgelehnt nur, wenn dieses Konto existiert und `--force` fehlt).
- `--to-dir ORDNER` stellt in einem leeren Ordner wieder her (Dateien-Backend), ohne die Installation anzufassen: der Weg, eine Sicherung anzusehen oder auf eine andere Maschine umzuziehen.
- Sie schreibt `ops/restore_report.json` in den Datenordner und gibt aus, was noch zu tun ist: den GitHub-Zugang neu einrichten, die vom Paket ausgelassenen Einstellungen neu setzen, den Monitor neu starten, damit der Supervisor jedes Konto startet, den Doctor ausführen.

## Die geplante Sicherung

Zwei Wege, nutzen Sie einen:

1. Im Monitor: `ops.backup.enabled` (standardmäßig aus) erstellt alle `ops.backup.interval_hours` eine Sicherung in einem eigenen Thread, behält die neuesten `ops.backup.keep` (es werden nur Dateien mit dem Namen einer Sicherung entfernt) und vermerkt das Ergebnis in `ops/backup_status.json`. Ein Fehler (voller Datenträger, fehlender Schlüssel) wird vermerkt und im Panel Info und im Doctor angezeigt; er stoppt den Monitor nie.
2. Mit systemd: `deploy/github-actions-monitor-backup.service` und `deploy/github-actions-monitor-backup.timer` (siehe unten).

Das Panel Info hat eine Karte **Betrieb** mit dem Modus (Dienst oder lokal), der letzten guten Sicherung, dem Zeitplan, der geltenden Aufbewahrung und der Schaltfläche **Jetzt sichern** (ein Administrator, von diesem Rechner). `GET /api/ops/status` liefert dieselben Daten; `POST /api/ops/backup` erstellt eine Sicherung.

## Bereinigung auf Anforderung

Die Aufbewahrungs-Bereinigung läuft alle `retention.interval_hours` von selbst. Um sie jetzt auszuführen, gibt es eine Schaltfläche (und `POST /api/ops/purge`), die **nicht existiert**, bis `ops.purge.enabled` an ist (standardmäßig aus). Eine Anfrage ist ein Probelauf (die geltende Richtlinie und wie viele Ereignisse gingen), außer sie sagt `dry_run` false, und eine echte Bereinigung wird ohne eine gute Sicherung abgelehnt, die neuer ist als `ops.purge.require_backup_hours` (standardmäßig 24; 0 verlangt nichts). Sie hinterlässt ihre Zeile im Audit der Aufbewahrung und im Aktionsprotokoll.

## Der Doctor und seine Exit-Codes

`python bin/monitor_cli.py doctor [--strict] [--json]` (oder `python bin/actions_monitor.py --doctor`) prüft die Installation, ändert nichts und gibt kein Geheimnis aus. Die Edition Vollständig fügt nach den üblichen diese Prüfungen hinzu:

| Prüfung | Was sie ansieht |
|---|---|
| `volumes` | in den Ordnern für Daten, Protokolle und Sicherungen wird wirklich eine Datei geschrieben, gelesen und entfernt (ein als root oder schreibgeschützt eingebundenes Docker-Volume scheitert hier) |
| `supervisor` | ein laufender Monitor: die tiefe Gesundheitsprüfung des Supervisors und jedes Aktualisierungszyklus (es wird nichts gestartet) |
| `limits` | das Webhook-Geheimnis ist gesetzt und hat mindestens `ops.doctor.webhook_min_length` Zeichen (nur die Länge wird verglichen) sowie die Aufbewahrungsrichtlinie |
| `sqlite_hot` | jede SQLite-Datenbank nur lesend geöffnet: `quick_check` (Standard) oder `integrity_check` (`ops.doctor.sqlite_check` deep), bei `ops.doctor.sqlite_timeout_s` abgebrochen; eine nach einem Stromausfall beschädigte Datei scheitert |
| `backup_age` | die letzte gute Sicherung gegen `ops.doctor.backup_max_age_days` |
| `disk` | freier Platz des Datenvolumes gegen `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` antwortet, wenn die Prometheus-Ausgabe an ist und ein Monitor läuft |

**Exit-Codes (stabil, für Cron):** `0` alles in Ordnung (auch mit Warnungen, ohne `--strict`); `1` mindestens eine Prüfung ist fehlgeschlagen; `3` nur Warnungen und `--strict` (oder `ops.doctor.strict_exit`); `4` der Doctor selbst konnte nicht laufen. Das sind die Codes des Doctors; die übrigen Befehle von `monitor_cli.py` behalten ihre. Beispiel: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` und alarmieren Sie bei jedem Code außer 0.

## Als Appliance

**systemd** (ohne Container): Folgen Sie den Kommentaren in `deploy/github-actions-monitor.service` und installieren Sie dann die Sicherungseinheit und ihren Timer:

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

Für eine verschlüsselte Sicherung tragen Sie die von `ops.backup.key_env` genannte Variable in `/etc/github-actions-monitor/env` ein (Modus 600). Der Timer führt täglich `backup create` aus; sein Exit-Code ist 1, wenn die Sicherung nicht erstellt werden konnte.

**Docker:** `deploy/compose.yaml` legt die Sicherungen in ein eigenes Volume (`monitor-backups` unter `/data/backups`), damit der Verlust des Datenvolumes sie nicht mitnimmt. Kopieren Sie eine Datei mit `docker compose exec monitor python bin/monitor_cli.py backup list` und `docker cp` heraus und stellen Sie in einem angehaltenen Container oder mit `--to-dir` wieder her. TLS erneuert der Caddy aus `deploy/Caddyfile`.

**Aktualisieren, ohne die Konten zu verlieren:** `backup create` → `backup verify DATEI` → Monitor anhalten → Produktordner ersetzen (die Ordner `config/`, `data/`, `logs/` und `ai/` gehören Ihnen und bleiben) → `doctor` → starten. Geht etwas schief, `backup restore DATEI`. **Sauber entfernen:** Einheiten anhalten und deaktivieren, den Timer entfernen, dann den Produktordner und, nur wenn Sie die Daten verlieren wollen, die Ordner `config/`, `data/` oder die Docker-Volumes.

## Einstellungen

Alle stehen im Tab Einstellungen (Ordner und Dateien) und in [SETTINGS_deu.md](SETTINGS_deu.md): `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) und `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Jeder Schalter beginnt aus oder konservativ, und die sicherheitsrelevanten (die geplante Sicherung, das Einschließen der Einstellungen, die Verschlüsselung, die Bereinigung) sind als solche markiert.

Siehe auch [STORAGE_deu.md](STORAGE_deu.md) (die Backends und die Aufbewahrung), [DEPLOYMENT_deu.md](DEPLOYMENT_deu.md) (Dienst, Container, TLS) und [CLI_deu.md](CLI_deu.md).
