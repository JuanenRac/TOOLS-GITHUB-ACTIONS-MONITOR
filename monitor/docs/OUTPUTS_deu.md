<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

# Ausgaben für andere Werkzeuge

Drei optionale Ausgaben, **alle standardmäßig aus**, die im Reiter Einstellungen (Gruppe „Ausgaben für andere Werkzeuge“) oder in `actions_monitor.json` eingeschaltet werden:

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

Sie werden vom selben Webserver bereitgestellt, nur auf `127.0.0.1`, mit denselben `Host`- / `Origin`-Prüfungen wie alles andere, und **benötigen kein Token**. Sie lesen den Zustand, den der Monitor ohnehin vorhält, daher kostet ein
Scrape oder die Aktualisierung eines Dashboards kein Kontingent der GitHub-API. Das Ein- oder Ausschalten wirkt sofort (kein Neustart).

| Pfad | Format | Schalter |
|---|---|---|
| `/metrics` | Prometheus-Text, Version 0.0.4 | `outputs.prometheus.enabled` (`per_repo` fügt die Serien je Repository hinzu) |
| `/api/outputs/grafana.json` | JSON-Tabellen für die Grafana-Datenquelle „Infinity“ / JSON | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | das Dokument von `ci_red.json` (Schema 2, siehe CI_RED_SCHEMA_deu.md) für ein Status-Dashboard | `outputs.dashboard.enabled` |

Eine Anfrage an einen Pfad, dessen Schalter aus ist, erhält `404`. Der ältere Weg, dasselbe Dokument an ein Dashboard zu geben, `ci_red.json` und `bin/read_report.py --export-status`, bleibt unverändert: Er ist ein Vertrag.

## Prometheus-Metriken

Jeder Name beginnt mit `ghamon_`. Nur Gauges. Ein unbekannter Wert wird **weggelassen**, nie als 0 geschrieben.

| Metrik | Labels | Bedeutung |
|---|---|---|
| `ghamon_info` | `version` | immer 1 |
| `ghamon_snapshot_complete` | | 1, wenn der Snapshot des Wächters vollständig ist, 0 während des Ladens oder wenn er reduziert ist |
| `ghamon_red_workflows`, `ghamon_red_repos` | | Workflows (Repositories), deren letzter abgeschlossener Lauf auf dem Standard-Branch rot ist |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | dasselbe je Ökosystem |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | je Repository (erfordert `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | aufeinanderfolgende rote Läufe (erfordert `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | Stunden, seit er rot wurde (erfordert `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | Builds, die auf die lokale Signatur oder Veröffentlichung warten, über der Schwelle |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | die längste Wartezeit eines Repositorys (erfordert `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1, solange die Oberflächenprüfungen (A10) auf GitHub-Kontingent warten, mit dem verbleibenden und dem benötigten Kontingent |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | das Kontingent der GitHub-API |
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | die Punktzahl des Kontos (0 bis 100, nur solange sie eine Zahl hat), der Anteil ihrer Gewichte mit Daten und 1, wenn sie eine Zahl hat (nur Complete; siehe SCORE.md) |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | die API-Aufrufe des Wächters im Verhältnis zu seinem Budget |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | die Live-Zahlen des Reiters Jetzt |

Ein Scrape-Job:

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` ist ein importierbares Dashboard (Grafana 10 oder neuer): Stat-Panels für die roten Workflows, die auf eine Signatur wartenden Builds, das verbleibende Kontingent, den
Zustand von A10, ob der Snapshot vollständig ist, und die hängenden Läufe; ein Balkendiagramm der roten Workflows je Ökosystem; ein Diagramm der längsten roten Serie und der Wartezeit auf die Signatur; sowie zwei Tabellen, die
aus `/api/outputs/grafana.json` mit der Infinity-Datenquelle gelesen werden (`root_selector` `red` und `pending_sign`). Beim Import fragt Grafana nach den Datenquellen Prometheus und Infinity; ändern Sie
den Port in der URL der beiden Tabellen, falls der Monitor nicht 8765 verwendet. Grafana muss auf demselben Rechner laufen (die Ausgaben antworten nur auf 127.0.0.1).

## Ideen aus ähnlichen Projekten

Beim Lesen, was andere Werkzeuge für GitHub Actions leisten, ergaben sich einige Ideen; von ihrem Code oder ihren Texten wird nichts verwendet. Von einem Exporter für Prometheus-Metriken: der Status eines Laufs als Zahl plus Labels, die
Auswahl der zu exportierenden Labels sowie ein konfigurierbarer Port und Intervall. Von einem per Webhook gespeisten TV-Dashboard: ein Status je Repository mit Filtern, groß dargestellt. Von einem Terminal-Beobachter: alle
Workflows eines Repositorys auf einmal, bis sie beendet sind. Von einem Webhook-Dashboard mit Alarmregeln: Filter nach Repository, Branch und Workflow vor dem Alarmieren. Hier erscheinen dieselben Ideen als
`per_repo` (die Serien auswählen), die JSON-Quelle mit einer Zeile je rotem Workflow, der Live-Reiter Jetzt und die Ereignisdatei mit Filtern auf der Seite.

## Das minimale Grafana-Board

`docs/grafana/red_by_ecosystem.json` ist ein Board mit einem Panel: rote Workflows je Ökosystem (Abfrage `ghamon_ecosystem_red_workflows`, Legende `{{ecosystem}}`). Importieren und die Prometheus-Quelle wählen. Ein Test dieses Repositorys prüft, dass Metrik und Label wirklich von `/metrics` geliefert werden.

## Die Signatur-Warteschlange nach Vertrauen

Jede Zeile der Warteschlange hat ein `trust`: `verified` (Signatur gegen den öffentlichen Schlüssel geprüft), `unknown` (das Format lässt sich hier nicht prüfen: nie geraten) oder `failed` (geprüft und nicht passend). Der Reiter Wächter hat einen Filter Signatur mit der Anzahl je Art und markiert die Zeilen (grüner, grauer oder roter Rand). Auf der Konsole: `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`.

## Im Netzwerkmodus

`/metrics` und `dashboard.json` listen deine Repositories und ihren Zustand auf: Es sind keine öffentlichen Seiten. Bei aktivem Netzwerkmodus brauchen sie das Zugriffstoken wie jeder andere Endpunkt; schalte `outputs.prometheus.enabled` / `outputs.dashboard.enabled` aus, wenn dieses Inventar gar nicht erreichbar sein soll.

## Bericht eines Tabs speichern und drucken

Die Leiste am oberen Rand der Seite (in jedem Tab) erstellt EINEN Bericht des geöffneten Tabs und zeichnet ihn auf vier Arten aus denselben Daten, sodass die Formate nie voneinander abweichen:

- **Bericht speichern** öffnet ein Fenster mit drei Kästchen: **TXT** (angehakt), **PDF** (angehakt) und **JSON** (nicht angehakt: die Daten des Berichts für andere Werkzeuge). Nach dem Bestätigen öffnet sich das Fenster **Speichern unter** des Browsers einmal je Format, mit dem vorgeschlagenen Namen `monitor-<Tab>-<Datum>.<Endung>` und dem passenden Dateityp (der Browser verlangt einen Klick pro Fenster, daher springt die Schaltfläche zum nächsten Format). Ein Browser ohne dieses Fenster lädt die Datei herunter, und die Seite sagt, wo sie gelandet ist.
- **PDF**: Der Monitor schreibt das PDF selbst, ohne Bibliothek und mit der Standardschrift Helvetica, für Englisch, Spanisch, Deutsch, Französisch, Italienisch und Portugiesisch (`GET /api/report/tab.pdf`, nur von diesem Rechner; jede Nutzung hinterlässt eine Zeile im Aktionsprotokoll). Japanisch und Chinesisch brauchen Schriften, die ein so geschriebenes PDF nicht hat; für sie, oder wenn Sie im Fenster „Der Browser“ wählen, stammt das PDF aus dem Druckfenster des Browsers: Wählen Sie dort **Als PDF speichern**. Die Seite sagt das; sie schreibt nie ein PDF mit zerstörten Zeichen.
- **Drucken** zeigt denselben Bericht ohne Menüs und Leisten (Titel mit dem Tab-Namen, Datum und Uhrzeit, Version des Monitors, wichtigste Zahlen, Warnungen und die Tabellen des Tabs) und öffnet das Druckfenster.
- Den Bericht liefert `GET /api/report/tab?tab=now&lang=de` (`&fmt=json`, `&fmt=txt` oder `&fmt=options`), in beiden Editionen gleich.

Einstellungen (Einstellungen > Ausgaben für andere Werkzeuge > „Bericht eines Tabs speichern und drucken“): `report_export.txt`, `report_export.pdf` und `report_export.json` (welche Kästchen angehakt starten: TXT und PDF ja, JSON nein), `report_export.name` (vorgeschlagener Name, Standard `monitor-{tab}-{date}`), `report_export.paper` (`a4` oder `letter`, Standard `a4`) und `report_export.pdf_path` (`auto`, `own` oder `browser`, Standard `auto`).

## Wohin der Monitor ruft, und Ereignisse an ein SIEM

- **Tabelle der Netzwerkziele**: `monitor_cli.py doctor --egress` (auch mit `--json`) listet jeden Host, den die AKTUELLE Konfiguration aufrufen kann, wozu er dient, die Einstellung, die ihn zum Ziel macht, und was bei einer Sperre ausfällt: `api.github.com`, `github.com` und `objects.githubusercontent.com` (Updates), `raw.githubusercontent.com` (`lint.anonymous_public`), ntfy, Telegram, die Chat-Webhooks, der gewählte KI-Anbieter, der OTLP-Collector und die SIEM-Senken. Mit `airgapped` ist nichts in Verwendung. Ein Test hält die Tabelle gleich den vom Code genannten Hosts.
- **SIEM** (aus): `siem.sinks` in der Datei listet die Ziele, jedes mit `enabled: true`, um verwendet zu werden: `elasticsearch` (Bulk), `splunk_hec`, `loki`, `sentinel` (Log Analytics, mit dem gemeinsamen Schlüssel signiert), `bigquery` (`insertAll`) oder `http` (JSON-Zeilen). Der Token oder Schlüssel wird aus der durch `token_env` benannten Umgebungsvariable gelesen, nie aus der Datei. Jede Senke filtert mit `from_minutes` (5), `levels` und `repos_filter`; die Ereignisse haben eine geschlossene Feldliste (kein Token, kein Logtext); ein Empfänger auf einer privaten Adresse wird abgelehnt, außer die Senke hat `allow_private`; fällt ein Empfänger aus, warten die Ereignisse in einer Warteschlange von `siem.queue_max` (500), die ältesten werden zuerst verworfen. Im Offline-Modus wird nichts gesendet.
