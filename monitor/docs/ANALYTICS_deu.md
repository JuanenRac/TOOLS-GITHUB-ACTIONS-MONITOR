<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# Analytik, bedingte Lesungen und verlorene Verbindung

Was der Monitor aus den ohnehin gelesenen Runs lernt, wie er Kontingent spart und einen Netzausfall übersteht. Alles ist lokal; nichts wird irgendwohin gesendet.

## Dauer, Wartezeit und Schritte

- `p50` und `p95` der Dauer der erfolgreichen Runs jedes Workflows; der Zeit, die ein Job vor dem Start wartete (erstellt bis gestartet); und jedes Schritts eines Workflows. Ein Workflow zeigt Werte, sobald er `analytics.min_samples` Stichproben hat.
- Job- und Schrittzeiten brauchen die Jobs abgeschlossener Runs: bis zu `analytics.jobs_per_cycle` Runs je Zyklus, jeder einmal gelesen (0 liest keinen). Der eingehende Webhook liefert sie gratis.
- Exportiert als `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` und `ghamon_step_duration_seconds` (Label `quantile` 0.5 / 0.95; braucht `per_repo`) und in der Grafana-JSON-Quelle (`durations`, `queue`). `slower` listet die Workflows, deren p50 das `analytics.slow_factor`-Fache des Üblichen beträgt.


## Instabile Workflows (flaky)

Ein Workflow, der auf demselben Commit FEHLSCHLUG und dann BESTAND (oder dessen Run einen weiteren Versuch brauchte), wird als instabil markiert: `ghamon_workflow_flaky_rate`. Es ist nur ein Etikett: Was als rot zählt, ändert sich nicht.


## Bedingte Lesungen (ETag)

- Jede Lesung der Run-Listen sendet `If-None-Match`; GitHub antwortet mit `304 Not Modified`, wenn sich nichts geändert hat, und das kostet kein Kontingent. Die Kopfzeile zeigt, wie viele Lesungen gespart wurden, `ghamon_etag_saved_total` zählt sie. `cache.etag.enabled` und `cache.etag.ttl_hours` stehen im Reiter Einstellungen.
- Der Cache ist die lokale Datei `etag_cache.json` (nie veröffentlicht); eine defekte Datei ist einfach ein leerer Cache.


## Wenn die Verbindung verloren geht

Scheitern alle Lesungen eines Zyklus an einem Verbindungsproblem (nicht an Login oder Kontingent), behält die Seite das letzte Bild und zeigt ein rotes Banner `keine Verbindung seit HH:MM`. Nichts löst eine Ausnahme aus; der Monitor macht von selbst weiter und schreibt je einmal ein `offline`- und ein `online`-Ereignis (benachrichtigbar). `ghamon_offline` ist währenddessen 1.
