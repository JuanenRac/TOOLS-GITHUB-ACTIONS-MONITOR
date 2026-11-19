<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PRODUCTIVITY.md) | [🇪🇸 Español](PRODUCTIVITY_spa.md) | [🇫🇷 Français](PRODUCTIVITY_fra.md) | [🇮🇹 Italiano](PRODUCTIVITY_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | [🇵🇹 Português](PRODUCTIVITY_por.md)

# Was der Monitor spart: eine Schätzung und wie man sie misst

Diese Anleitung erklärt die Zahlen im README. Sie sind eine Schätzung aus einem einfachen Modell, keine Messung an Ihren Repositorys. Messen Sie selbst, bevor Sie sich darauf verlassen.

## Die Zahlen

- Etwa 85-95 % der Zeit für die Beobachtung der CI und die Sichtung von Fehlern.
- Etwa 15-25 % der Gesamtproduktivität eines Teams, als Folge der ersten Zahl.

## Wie die Schätzung entsteht

Eingesparte Zeit in einer Woche = die Summe über die Aufgaben von (Häufigkeit pro Woche x Minuten pro Mal ohne den Monitor) x Ersparnis der Aufgabe. Die Aufgaben sind: jeden Workflow beobachten, entscheiden, was wirklich rot ist, die Ursache eines fehlgeschlagenen Laufs finden und einen Fehler rechtzeitig bemerken. Die Schätzung nimmt an:

1. Es gibt viele Repositorys mit je mehreren Workflows, sodass das Nachsehen von Hand bedeutet, immer wieder viele Seiten zu öffnen.
2. Ohne den Monitor prüft jemand die Actions-Tabs von Hand und liest jedes fehlgeschlagene Protokoll, um die Ursache zu finden. Mit ihm sagen die Seite und die Alarme bereits, welcher Workflow rot ist und warum.
3. Jede Woche treten Fehler auf. Ein Team ohne Fehler hat nichts zu sichten.
4. Die Ersparnis umfasst nur Beobachten und Sichten. Einen Fehler zu beheben dauert mit oder ohne Monitor gleich lang und wird nicht mitgezählt.

Die beiden Zahlen passen nur zusammen, wenn Beobachten und Sichten etwa 16-29 % der Arbeitszeit des Teams beanspruchen (0,15 / 0,95 bis 0,25 / 0,85). Beansprucht es in Ihrem Team weniger, ist der Gesamtgewinn kleiner.

## Wann es weniger spart

- Wenige Repositorys oder ein einziger Workflow: es gibt wenig zu beobachten.
- Heute beobachtet niemand die CI von Hand, oder Sie haben schon Alarme, die die Ursache nennen.
- Die Alarme werden nicht gelesen. Auch das Lesen kostet Zeit, und die Ersparnis verschwindet, wenn sie ohne Grund ignoriert oder stummgeschaltet werden.

## Wie Sie es in Ihrer eigenen Nutzung messen

1. Vorher: Notieren Sie eine normale Woche lang jedes Mal, wenn Sie die CI von Hand ansehen (Minuten), und jeden fehlgeschlagenen Lauf, den Sie sichten (Minuten bis zur Ursache).
2. Nachher: Wiederholen Sie dieselben Notizen eine Woche lang mit geöffnetem Monitor. Die Bewertung (Zeit bis zur Wiederherstellung) und das Fehlerbuch (Trend über 24 Stunden und 7 Tage) zeigen, ob Fehler schneller geschlossen werden.
3. Für jede Gruppe ist die Ersparnis 1 - nachher / vorher. Vergleichen Sie sie mit 85-95 %.
4. Für den Gesamtgewinn teilen Sie die eingesparten Stunden durch die in dieser Woche insgesamt gearbeiteten Stunden. Vergleichen Sie ihn mit 15-25 %.

### Beispiel mit erfundenen Zahlen

Jemand verbringt täglich 20 Minuten mit den Actions-Tabs (100 Minuten in einer Fünftagewoche) und sichtet 4 fehlgeschlagene Läufe pro Woche zu je 30 Minuten (120 Minuten): zusammen 220 Minuten. Bei 85-95 % Ersparnis werden zwischen 187 und 209 Minuten frei. Diese Zahlen sind erfunden, um die Rechnung zu zeigen; nehmen Sie Ihre eigenen.
