<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# Zeiträume vergleichen

Wie haben wir diese Woche im Vergleich zur letzten abgeschnitten? Der Vergleich beantwortet das mit dem, was der Monitor schon hat (das Buch der beendeten Läufe und Meldungen und die stündlichen Momentaufnahmen der Punktzahl). Er liest nichts von GitHub, schreibt nichts, braucht keine KI und erfindet nichts. Es gibt ihn nur in der Complete-Edition, und er ist **aus**, bis Sie `compare.enabled` einschalten.

## Die beiden Zeiträume

- **Zeitraum**: die letzten 7 Tage (oder 30 oder eine beliebige Zahl bis 90) oder ein genauer Bereich mit `from` und `to`.
- **Vergleichsbasis**: `previous` (der gleich lange Zeitraum davor, Standard), `year_ago` (dieselben Daten ein Jahr früher) oder `custom` (`base_from` und `base_to`).
- **Tage**: `all`, `workdays` oder `weekend`. Der Filter gilt für jede Kennzahl. Der Tag eines Zeitpunkts ist sein Tag in der Zeitzone von `display.timezone`; die Werktage sind `compare.workdays` (Montag = 1 bis Sonntag = 7, standardmäßig Montag bis Freitag). Feiertage sind nicht bekannt: Ein Feiertag zählt als der Wochentag, auf den er fällt.

Werktage und Wochenenden zu mischen verdeckt Dinge (ein Fehler, der nur samstags auftritt, fällt in einer Woche mit gemischten Daten kaum ins Gewicht); deshalb gibt es den Filter.

## Die Kennzahlen

| Kennzahl | Berechnung | Besser, wenn |
|---|---|---|
| `red_rate` | fehlgeschlagene Läufe / (erfolgreiche + fehlgeschlagene Läufe), die im Zeitraum begonnen haben | niedriger |
| `duration_p50` | Median der Sekunden der erfolgreichen Läufe | niedriger |
| `resolution` | Median der Zeit von der Eröffnung bis zum Schließen der Meldungen des Zusammenarbeits-Sentinels, die im Zeitraum geschlossen wurden | niedriger |
| `score_mean` | mittlere Punktzahl der stündlichen Momentaufnahmen mit einer Zahl | höher |
| `score_coverage` | mittlerer Anteil der Punktzahl, der Daten hatte | höher |

Jede Kennzahl kommt mit `now`, `base`, `delta`, einer `direction` (`better`, `worse`, `same`) und ihrem `state`. Abgebrochene, übersprungene und unfertige Läufe zählen in keine Richtung.

## Wenn es keine Kennzahl gibt

Der Vergleich zeigt nie eine Zahl, für die er nicht einstehen kann: Eine fehlende Kennzahl ist `null`, nie 0 oder 100.

- `insufficient_data`: in einem der beiden Zeiträume weniger beendete Läufe als `compare.min_runs_per_window`, weniger gelöste Meldungen als `compare.min_resolved` oder weniger Momentaufnahmen als `compare.min_snapshots`. Die Antwort sagt, welcher Zeitraum und warum (`missing`).
- `baseline_unavailable`: Der Vergleichszeitraum ist nicht verlässlich. Der Grund ist `history_too_short` (der Monitor beobachtet weniger als `compare.min_days_of_history` Tage), `before_history` (dieser Zeitraum liegt vor den gespeicherten Daten) oder `no_history`. Die Kennzahlen des aktuellen Zeitraums werden trotzdem gezeigt.
- `calibrating`: Der Monitor hat noch nicht `score.calibrating_hours` Stunden beobachtet. Es wird nichts verglichen.
- `off`: `compare.enabled` ist aus.

`data_quality` enthält die gezählten Läufe je Zeitraum und `truncated`, wenn das Buch alte Läufe verwerfen musste. `coverage` ist der Anteil der Kennzahlen, die verglichen werden konnten.

## Was sich geändert hat

Neben den Kennzahlen: die Repositories, die schlechter oder besser wurden (Änderung ihres Anteils fehlgeschlagener Läufe, nur Repositories mit mindestens `compare.min_repo_runs` Läufen in beiden Zeiträumen), die Workflows, die zu scheitern begannen, und die, die nicht mehr scheitern, sowie die Zahl der im Zeitraum geöffneten und an seinem Ende noch offenen Meldungen. Jede Liste hat höchstens `compare.top_changes` Zeilen, geordnet nach der Größe der Änderung und dann nach Namen. Das Buch speichert kein Repository für die Meldungen des Zusammenarbeits-Sentinels; sie erscheinen daher als Zahlen, nie mit Namen.

## Wie weit es zurückreicht

Der Vergleich liest das Buch der Punktzahl. Solange `compare.enabled` an ist, behält das Buch zwei Zeiträume von `compare.default_window_days` (mindestens 15 Tage) statt der zwei Fenster der Punktzahl; es ist nie älter als der Monitor, eine neue Installation kann also erst 30 Tage mit 30 Tagen vergleichen, wenn sie 60 Tage Verlauf hat.

## Die API

`GET /api/compare?window=7&days=workdays&baseline=previous` (auch `from`, `to`, `base_from`, `base_to`). Sie antwortet mit `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` und `data_quality`. `format=ndjson` oder `format=csv` liefern eine Zeile je Kennzahl. Eine sinnlose Anfrage ergibt ein 400 mit stabilem `code`: `bad_range` (from nach to, länger als 90 Tage, in der Zukunft), `bad_window`, `bad_days`, `bad_baseline` oder `bad_format`. Ein Betrachter darf sie lesen; sie bedient das Konto des Prozesses, nie ein anderes. Mit eingeschalteter Lese-API v1 wird sie auch unter dem Präfix `/api/v1/` angeboten. In der Lite-Edition gibt es sie nicht.

## Die Befehlszeile

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Exit-Codes: 0 alles verglichen; 4 eine Kennzahl hat zu wenig Daten, es gibt keine Basis oder der Vergleich ist aus; 5 mit `--fail-on`, wenn sich eine Kennzahl verschlechtert hat. `score --compare` vergleicht weiterhin die Punktzahl mit dem Verlauf ihres Fensters.

## Auf der Seite

Der Reiter Diagramme zeigt den Abschnitt „Zeiträume vergleichen“, wenn der Vergleich an ist: eine Auswahl für Zeitraum, Tage und Basis, eine Zeile je Kennzahl mit ihrer Änderung, die Meldungen und die Listen der Änderungen.

## Frische, veraltete und langsame Antworten

Der Vergleich und die optionalen Berichte sind schwere Abfragen, daher wird ihre Antwort im Speicher gehalten, und jede Anfrage findet sie in einem von drei Zuständen. **Frisch** (jünger als `cache.heavy_fresh_s`, 5 Sekunden): unverändert ausgeliefert, ohne neu zu rechnen. **Veraltet** (älter und jünger als `cache.stale_serve_h` Stunden, 1 Stunde): sofort ausgeliefert und mit `freshness` = `{"state": "stale", "age_s": N}` markiert, während eine Berechnung sie im Hintergrund erneuert; eine frische Antwort trägt diesen Schlüssel nicht. **Abgelaufen** (älter oder nie berechnet): wird jetzt berechnet, und eine so alte Kopie wird nie ausgeliefert. Eine Berechnung hat ein Limit, `analytics.query_timeout_s` (120 Sekunden): danach lautet die Antwort `504` mit dem Code `query_timeout`, statt ewig zu warten; eine Berechnung lässt sich nicht abbrechen, sie endet von selbst, ihre Antwort wird für die nächste Anfrage aufbewahrt, und für dieselbe Abfrage wird währenddessen keine zweite gestartet. Nichts davon ruft GitHub auf.

## Die Einstellungen

Einstellungen, Reiter Sentinel, Block Vergleich von Zeiträumen: `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` und `compare.cache_seconds`. Eine Antwort wird `compare.cache_seconds` Sekunden behalten und dann neu berechnet.

## Lange Fenster bei einem großen Konto

Mit eingeschaltetem `compare.progressive` (standardmäßig aus) wird ein Vergleich über ein Fenster, das länger als `compare.progressive_days` (standardmäßig 7) ist, sofort mit seinen letzten Tagen beantwortet, und die Antwort sagt es (`partial`: die erfragten Tage, die gezeigten Tage und dass der Rest berechnet wird); das ganze Fenster wird im Hintergrund fertiggestellt, und die nächste Anfrage oder die nächste Aktualisierung der Seite erhält es. Eine Anfrage mit `from` und `to` wird nie geteilt.
