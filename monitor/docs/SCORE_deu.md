<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Die Punktzahl eines Kontos

Eine Zahl von 0 bis 100, ein Buchstabe von A bis E und ein Trend für jedes Konto, gebildet nur aus dem, was der Monitor ohnehin weiß (die beendeten Läufe und die Warnungen des Zusammenarbeits-Wächters). Sie gibt es in der Ausgabe Complete; Lite hat keine Punktzahl.

## Woraus sie besteht

Eine gewichtete Summe aus fünf Teilen, jeder von 0 bis 100. Ein Teil ist an seiner **guten** Grenze 100, an seiner **schlechten** Grenze 0 und dazwischen linear. Die Gewichte und die Grenzen sind Einstellungen.

| Teil | Gewicht | Was er misst | Gut | Schlecht |
|---|---|---|---|---|
| Zuverlässigkeit | 30 | Anteil der beendeten Läufe, die gelingen (abgebrochene und übersprungene zählen nicht) | 98 % | 50 % |
| Geschwindigkeit | 15 | 95. Perzentil der Dauer der erfolgreichen Läufe | 10 Min. | 60 Min. |
| Wiederherstellung | 15 | mittlere Zeit vom ersten Fehlschlag eines Workflows bis zu seinem nächsten Erfolg; ein Workflow, der noch rot ist, zählt die Zeit, die er bisher rot ist | 30 Min. | 24 Std. |
| Zusammenarbeit | 15 | mittlere Zeit, die eine Warnung des Zusammenarbeits-Wächters offen bleibt, bis sie verschwindet | 2 Tage | 14 Tage |
| Sicherheit | 25 | die Punkte, die die offenen Befunde des Sicherheitswächters von 100 abziehen (nur solange dieser Wächter an ist) | 0 Punkte | 100 Punkte |

Der Buchstabe ist A ab 90, B ab 80, C ab 70, D ab 55 und darunter E. Der Trend vergleicht die Punktzahl mit dem unmittelbar vorangehenden Fenster: steigend, fallend oder stabil (eine Änderung unter `score.trend_flat` Punkten ist stabil).

## Wenn es keine Zahl gibt

Die Punktzahl zeigt nie eine Zahl, die sie nicht belegen kann. Die Antwort enthält immer ihren `state`, ihre `coverage` und ihre `data_quality`:

- **calibrating** (Kalibrierung): das Konto wird seit weniger als `score.calibrating_hours` beobachtet (standardmäßig 24). Weder Zahl noch Buchstabe.
- **insufficient_data** (zu wenige Daten): weniger als `score.min_runs` beendete Läufe im Fenster (standardmäßig 20) oder die Teile mit Daten wiegen weniger als `score.min_coverage` des Ganzen (standardmäßig die Hälfte). Keine Zahl.
- **scored** (bewertet): eine Zahl, ein Buchstabe und ein Trend. Ein Teil ohne Daten wird weggelassen und die übrigen werden neu skaliert; das senkt die `coverage` (zum Beispiel 0,85, wenn der Zusammenarbeits-Wächter aus ist). Er zählt nie als 0 und nie als 100.

Sicherheit ist ein Teil wie die anderen, hat aber nur Daten, solange der Sicherheitswächter an ist und genug Repositories angesehen hat. Ohne ihn sagt die Antwort `complete: false` und führt `security` unter `missing_parts` auf, und die anderen Teile werden neu skaliert, damit die Zahl nie als „alles in Ordnung“ gelesen wird. GitHub liefert keinen Verlauf der Befunde, deshalb ist der Sicherheitsteil im Fenster und im davor liegenden derselbe: Der Trend zeigt, was die CI und die Zusammenarbeit getan haben. Die Gewichte sind standardmäßig 30, 15, 15, 15 und 25. Ein Fenster mit Läufen und ohne jeden Fehlschlag hat nichts wiederherzustellen: Sein Wiederherstellungsteil ist voll, als Tatsache und nicht als Lücke.

Ein Workflow, der am Ende des Fensters noch rot ist, wird nicht vergessen: Der Teil Wiederherstellung zählt die Zeit, die er bisher rot ist, eine untere Grenze, die wächst, solange das Rot dauert; ein Fehler, den niemand behebt, senkt die Zahl also jede Stunde stärker. Ein behobener Fehler zählt seine tatsächliche Zeit. Ein erneuter Lauf eines Laufs zählt als eine weitere Ausführung des Workflows, sodass der fehlgeschlagene erste und der grüne zweite Versuch beide gesehen werden. Wenn du von einer früheren Version aktualisierst, können die Zahlen eines Kontos mit einem roten Workflow niedriger sein als zuvor. Hat kein Teil Daten, lautet die Antwort `insufficient_data` mit dem Grund `no_data`. Das Buch hält höchstens 20000 Läufe: Musste es Läufe des aktuellen Fensters verwerfen, ist `data_quality.truncated` wahr und `truncated` steht unter den Gründen, damit eine Erfolgsquote, die nur einen Teil des Fensters sieht, nicht für vollständig gehalten wird. In `GET /api/score/global` wird ein Konto mit veraltetem Schnappschuss aus dem Mittelwert genommen und in `accounts_stale` gezählt, und `/metrics` exportiert `ghamon_score` für einen veralteten Schnappschuss nicht.

## Das Fenster

Das Fenster ist die Zahl der Tage an Läufen, die die Punktzahl betrachtet: `score.window_days`, standardmäßig 7, vom Benutzer für jedes Konto gewählt. Das unmittelbar davor liegende Fenster gleicher Länge ergibt den Trend. Der Monitor führt ein kleines Buch der beendeten Läufe, die er gesehen hat, sodass das Fenster länger sein kann als die Liste der letzten Läufe, die die Seite zeigt. Einmal pro Stunde wird eine Momentaufnahme gespeichert und so lange aufbewahrt wie der Analyseverlauf (`retention.analytics_days`).

## Nach Repository und nach Konto

Jedes Konto hat seine eigene Punktzahl. Das Detail gliedert sie nach Repository auf (nur die CI-Teile, die schlechtesten zuerst). Eine einzige Zahl für die ganze Installation gibt es nicht. Nur zur Information liefert `GET /api/score/global` des Supervisors den Mittelwert der bewerteten Konten, die der Fragende sehen darf, gewichtet nach ihren Repositories mit einer Zahl und immer mit der Angabe, wie viele Konten darin sind; ein Konto ohne Zahl wird aufgeführt und ausgelassen.

## Auf der Seite

Ein Chip in der Kopfzeile, neben den Bereitschafts-Chips, zeigt die Punktzahl: die Zahl, den Buchstaben, einen Pfeil mit der Änderung gegenüber dem vorherigen Fenster und eine kleine Linie der letzten Tage. Seine Farbe folgt dem Buchstaben (A und B grün, C bernstein, D und E rot). Solange es keine Zahl gibt, ist er neutral und sagt warum (Kalibrierung, zu wenige Daten). Ein Stern hinter dem Buchstaben bedeutet, dass ein Teil noch nicht eingerechnet ist (heute die Sicherheit): eine hohe Zahl heißt dann nicht, dass alles in Ordnung ist. Beim Darüberfahren zeigt er die Abdeckung, die Teile mit ihren Gewichten und das schwächste Repository. Der Chip erscheint weder in Lite noch bei ausgeschalteter Punktzahl (`score.enabled`). Während der Kalibrierung zeigt der Chip, wie viel von `score.calibrating_hours` noch fehlt, mit einem Balken und Tag und Uhrzeit, zu denen die Zahl erscheint; bei zu wenigen Daten nennt er die nicht erfüllte Bedingung (Läufe oder Abdeckung), und der Hinweistext sagt auch, warum ein Teil nicht zählt (ein ausgeschalteter Wächter, der seinen ersten Durchlauf nicht beendet oder zu wenige Repositories gelesen hat).

## Für andere Werkzeuge

Die Metriken (`/metrics`, wenn die Prometheus-Ausgabe an ist) enthalten drei Reihen ohne Labels: `ghamon_score_scored` (1, wenn das Konto eine Zahl hat), `ghamon_score_coverage` (der Anteil der Gewichte mit Daten, von 0 bis 1) und `ghamon_score` (die Zahl, nur solange es eine gibt: sie wird nie als 0 exportiert, wenn keine da ist). Der MCP-Server hat ein schreibgeschütztes Werkzeug `get_score` mit der Antwort der API. `--demo` zeigt eine erfundene Punktzahl und schreibt nichts. Das Beispiel-Dashboard für Grafana (`docs/grafana/monitor_dashboard.json`) hat ein Panel für die Punktzahl und eines für die Punktzahl im Zeitverlauf.

## Die API

`GET /api/score` liefert die neueste Momentaufnahme des Kontos: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` und `stale` (wahr, wenn die Momentaufnahme älter als drei Stunden ist). `GET /api/score/history` liefert die Punkte über die Zeit, älteste zuerst (`?hours=` ab jetzt rückwärts, höchstens 90 Tage, und `?limit=`, höchstens 2000). Eine fehlende Zahl ist `null`, nie 0. Im Teammodus darf die Punktzahl lesen, wer das Konto sehen darf; die Gewichte und die Grenzen sind Einstellungen, die nur ein Administrator ändert.

## Die Warnung bei Abfall

Fällt die Punktzahl gegenüber dem vorherigen Fenster um `score.alert.drop_points` Punkte (standardmäßig 10) oder mehr oder geht sie auf einen niedrigeren Buchstaben zurück, zeigt der Reiter Warnungen die Warnung `score.dropped` (eine Warnung; kritisch, wenn der Buchstabe E ist) mit der alten und der neuen Punktzahl. Sie bleibt, solange die Momentaufnahme den Abfall zeigt, und verschwindet, wenn sich die Punktzahl erholt; sie lässt sich wie jede andere Warnung stummschalten. Für das Panel ist sie standardmäßig an. Über die externen Benachrichtigungskanäle (Ereignis `score_dropped`) geht sie nur hinaus, wenn `score.alert.notify_external` an ist, was standardmäßig nicht der Fall ist, und nur in dem Moment, in dem sie erscheint. `score.alert.enabled` schaltet die Warnung aus.

## Die Einstellungen

Auf der Einstellungsseite, Unterreiter Wächter, Blöcke Punktzahl des Kontos, Gewichte der Punktzahl und Buchstaben der Punktzahl: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, `score.grades.A` bis `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` und `score.alert.notify_external` (standardmäßig aus). Die guten und schlechten Grenzen jedes Teils werden aus der Datei gelesen, unter `score.limits` (siehe die Beispieldatei); sie werden nicht auf der Seite bearbeitet.
