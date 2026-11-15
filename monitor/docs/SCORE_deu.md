<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Die Punktzahl eines Kontos

Eine Zahl von 0 bis 100, ein Buchstabe von A bis E und ein Trend für jedes Konto, gebildet nur aus dem, was der Monitor ohnehin weiß (die beendeten Läufe und die Warnungen des Zusammenarbeits-Wächters). Sie gibt es in der Ausgabe Complete; Lite hat keine Punktzahl.

## Woraus sie besteht

Eine gewichtete Summe aus vier Teilen, jeder von 0 bis 100. Ein Teil ist an seiner **guten** Grenze 100, an seiner **schlechten** Grenze 0 und dazwischen linear. Die Gewichte und die Grenzen sind Einstellungen.

| Teil | Gewicht | Was er misst | Gut | Schlecht |
|---|---|---|---|---|
| Zuverlässigkeit | 40 | Anteil der beendeten Läufe, die gelingen (abgebrochene und übersprungene zählen nicht) | 98 % | 50 % |
| Geschwindigkeit | 20 | 95. Perzentil der Dauer der erfolgreichen Läufe | 10 Min. | 60 Min. |
| Wiederherstellung | 20 | mittlere Zeit vom ersten Fehlschlag eines Workflows bis zu seinem nächsten Erfolg | 30 Min. | 24 Std. |
| Zusammenarbeit | 20 | mittlere Zeit, die eine Warnung des Zusammenarbeits-Wächters offen bleibt, bis sie verschwindet | 2 Tage | 14 Tage |

Der Buchstabe ist A ab 90, B ab 80, C ab 70, D ab 55 und darunter E. Der Trend vergleicht die Punktzahl mit dem unmittelbar vorangehenden Fenster: steigend, fallend oder stabil (eine Änderung unter `score.trend_flat` Punkten ist stabil).

## Wenn es keine Zahl gibt

Die Punktzahl zeigt nie eine Zahl, die sie nicht belegen kann. Die Antwort enthält immer ihren `state`, ihre `coverage` und ihre `data_quality`:

- **calibrating** (Kalibrierung): das Konto wird seit weniger als `score.calibrating_hours` beobachtet (standardmäßig 24). Weder Zahl noch Buchstabe.
- **insufficient_data** (zu wenige Daten): weniger als `score.min_runs` beendete Läufe im Fenster (standardmäßig 20) oder die Teile mit Daten wiegen weniger als `score.min_coverage` des Ganzen (standardmäßig die Hälfte). Keine Zahl.
- **scored** (bewertet): eine Zahl, ein Buchstabe und ein Trend. Ein Teil ohne Daten wird weggelassen und die übrigen werden neu skaliert; das senkt die `coverage` (zum Beispiel 0,8, wenn der Zusammenarbeits-Wächter aus ist). Er zählt nie als 0 und nie als 100.

Sicherheit ist noch kein Teil. Bis dahin sagt jede Antwort `complete: false` und führt `security` unter `missing_parts` auf, damit eine 85 nie als „alles in Ordnung“ gelesen wird.

## Das Fenster

Das Fenster ist die Zahl der Tage an Läufen, die die Punktzahl betrachtet: `score.window_days`, standardmäßig 7, vom Benutzer für jedes Konto gewählt. Das unmittelbar davor liegende Fenster gleicher Länge ergibt den Trend. Der Monitor führt ein kleines Buch der beendeten Läufe, die er gesehen hat, sodass das Fenster länger sein kann als die Liste der letzten Läufe, die die Seite zeigt. Einmal pro Stunde wird eine Momentaufnahme gespeichert und so lange aufbewahrt wie der Analyseverlauf (`retention.analytics_days`).

## Nach Repository und nach Konto

Jedes Konto hat seine eigene Punktzahl. Das Detail gliedert sie nach Repository auf (nur die CI-Teile, die schlechtesten zuerst). Eine einzige Zahl für die ganze Installation gibt es nicht.

## Auf der Seite

Ein Chip in der Kopfzeile, neben den Bereitschafts-Chips, zeigt die Punktzahl: die Zahl, den Buchstaben, einen Pfeil mit der Änderung gegenüber dem vorherigen Fenster und eine kleine Linie der letzten Tage. Seine Farbe folgt dem Buchstaben (A und B grün, C bernstein, D und E rot). Solange es keine Zahl gibt, ist er neutral und sagt warum (Kalibrierung, zu wenige Daten). Ein Stern hinter dem Buchstaben bedeutet, dass ein Teil noch nicht eingerechnet ist (heute die Sicherheit): eine hohe Zahl heißt dann nicht, dass alles in Ordnung ist. Beim Darüberfahren zeigt er die Abdeckung, die Teile mit ihren Gewichten und das schwächste Repository. Der Chip erscheint weder in Lite noch bei ausgeschalteter Punktzahl (`score.enabled`).

## Die API

`GET /api/score` liefert die neueste Momentaufnahme des Kontos: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` und `stale` (wahr, wenn die Momentaufnahme älter als drei Stunden ist). `GET /api/score/history` liefert die Punkte über die Zeit, älteste zuerst (`?hours=` ab jetzt rückwärts, höchstens 90 Tage, und `?limit=`, höchstens 2000). Eine fehlende Zahl ist `null`, nie 0. Im Teammodus darf die Punktzahl lesen, wer das Konto sehen darf; die Gewichte und die Grenzen sind Einstellungen, die nur ein Administrator ändert.

## Die Einstellungen

Auf der Einstellungsseite, Unterreiter Wächter, Blöcke Punktzahl des Kontos, Gewichte der Punktzahl und Buchstaben der Punktzahl: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.grades.A` bis `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` und `score.alert.notify_external` (standardmäßig aus). Die guten und schlechten Grenzen jedes Teils werden aus der Datei gelesen, unter `score.limits` (siehe die Beispieldatei); sie werden nicht auf der Seite bearbeitet.
