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

- Jede Lesung der Run-Listen sendet `If-None-Match`; GitHub antwortet mit `304 Not Modified`, wenn sich nichts geändert hat, und das kostet kein Kontingent. Die Kopfzeile zeigt, wie viele Lesungen gespart wurden, `ghamon_etag_saved_total` zählt sie. `cache.etag.enabled` und `cache.etag.ttl_hours` stehen im Reiter Einstellungen. Jeder Eintrag gehört zu der Zugangsberechtigung, die ihn gelesen hat (ein kurzer Fingerabdruck des Tokens ist Teil des Schlüssels, nie das Token), daher liefert ein `304` nie den Inhalt einer anderen Identität. Ein Zustand, der sich noch bewegt, wird immer vollständig gelesen: die Jobs eines Laufs, ein einzelner Lauf, Check-Suites und Check-Runs (`cache.etag.skip_stateful`) und jede Laufliste, deren letzte Antwort noch einen wartenden oder laufenden Lauf enthielt (`cache.etag.revalidate_active`). Eine Ablehnung (404 oder 403, kein Ratelimit) wird `cache.negative_ttl_s` Sekunden gemerkt. `/metrics` zählt außerdem die Antworten ohne ETag, die absichtlich vollständigen Lesungen und die nicht wiederholten Ablehnungen; der Brief für die KI-Werkzeuge hat das Signal quota.etag.
- Der Brief für die KI-Werkzeuge nennt schema.drift, wenn GitHub einen dem Monitor unbekannten Zustand oder ein unbekanntes Ergebnis oder einen Lauf ohne brauchbare Nummer gesendet hat: Der unbekannte Wert wird gezeigt, wie er kam, und nie als rot oder grün gezählt.
- Der Cache ist die lokale Datei `etag_cache.json` (nie veröffentlicht); eine defekte Datei ist einfach ein leerer Cache.


## Wenn die Verbindung verloren geht

Scheitern alle Lesungen eines Zyklus an einem Verbindungsproblem (nicht an Login oder Kontingent), behält die Seite das letzte Bild und zeigt ein rotes Banner `keine Verbindung seit HH:MM`. Nichts löst eine Ausnahme aus; der Monitor macht von selbst weiter und schreibt je einmal ein `offline`- und ein `online`-Ereignis (benachrichtigbar). `ghamon_offline` ist währenddessen 1.

## Wie lange der Verlauf aufbewahrt wird

Neben `keep_days` des Analyseblocks entfernt der Aufbewahrungsdurchlauf die Tage des Verlaufs, die älter als `retention.analytics_days` sind (standardmäßig 180); die Messwerte selbst begrenzt `max_samples`. Siehe [STORAGE_deu.md](STORAGE_deu.md).


## Gesparte Zeit (eine Schätzung)

Standardmäßig aus (`productivity.enabled`). Eingeschaltet zeigt der Abschnitt Aufgabe für Aufgabe, wie viele Minuten pro Woche der Monitor spart, mit der Formel aus [PRODUCTIVITY_deu.md](PRODUCTIVITY_deu.md): Mal pro Woche x Minuten pro Mal ohne den Monitor x Ersparnis der Aufgabe.

- Zwei Aufgaben werden beziffert. **Beobachten** (die Actions-Tabs von Hand ansehen und entscheiden, was rot ist) nimmt Häufigkeit und Minuten aus Ihren Notizen (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Diagnose** (die Ursache eines fehlgeschlagenen Laufs finden) zählt die fehlgeschlagenen Läufe, die der Monitor in `productivity.window_days` im Blick hat, und nimmt die Minuten aus Ihren Notizen (`productivity.triage_minutes_before`).
- Der Monitor kann nicht sehen, was Sie vor seiner Installation getan haben. Eine Aufgabe ohne diese Notizen sagt **keine Daten**, und es wird keine Zahl erfunden. Auch die Summe sagt keine Daten, solange jeder Aufgabe die Notizen fehlen.
- Haben Sie zusätzlich die Minuten mit dem Monitor notiert (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), wird die Ersparnis aus Ihren Notizen gemessen: 1 - nachher / vorher. Sonst gilt der Prozentsatz aus `productivity.saving_percent` (standardmäßig 90), und die Tabelle sagt **angenommen (nicht gemessen)**.
- Mit `productivity.team_hours_per_week` sagt die Schätzung auch, welcher Anteil der Arbeitszeit die gesparten Minuten sind.
- Das Beheben eines Fehlers dauert mit oder ohne Monitor gleich lang und wird nie gezählt. Gezählt werden nur fehlgeschlagene Läufe, die der Monitor hält: Eine sehr lange Laufliste kann mehr Fehler enthalten als angezeigt.
- Lokal und nur lesend: kein Aufruf an GitHub, nichts verlässt den Rechner. Es steht in `/api/analytics` (`time_saved`), in der Zusammenfassung des Panels A12 und im Brief des Tabs Übersicht für die KI-Werkzeuge.
