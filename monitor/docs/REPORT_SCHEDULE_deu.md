<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# Geplante Berichte

Nur Complete, standardmäßig aus. Der Monitor kann nach einem Zeitplan oder auf Wunsch einen Bericht des Kontos schreiben: die Punktzahl, was sich seit dem letzten Bericht geändert hat, die Repositorys, die einen Menschen brauchen, und die offenen Meldungen, als HTML-Seite und als Markdown. Er entsteht aus dem, was der Monitor schon hält, fragt GitHub nach nichts und sendet nichts irgendwohin: Die Dateien bleiben im Ordner `data/reports/`.

## Einschalten

Einstellungen, Tab Wächter, Block **Geplante Berichte**:

| Einstellung | Standard | Was sie tut |
|---|---|---|
| `report_schedule.enabled` | aus | schreibt nach dem Zeitplan einen Bericht |
| `report_schedule.cron` | `0 8 * * 1` | fünf Felder (Minute, Stunde, Tag des Monats, Monat, Wochentag) in der Ortszeit dieses Rechners; Zahlen, Listen, Bereiche und Schritte, keine Namen; `0 8 * * 1` ist jeden Montag um 8:00 |
| `report_schedule.formats` | beide | `html`, `markdown` oder `both` |
| `report_schedule.keep` | 12 | wie viele Läufe aufbewahrt werden; ältere werden entfernt |
| `report_schedule.top` | 10 | wie viele Repositorys und Meldungen jede Liste zeigt, die schlechtesten zuerst |

Der erste Bericht wartet auf die erste geplante Minute nach dem Einschalten. Je geplanter Minute wird ein Bericht geschrieben, auch wenn der Monitor tagelang aus war (dann einer, nicht ein Stapel). Ein fehlgeschlagener Bericht wird in der Gesundheit des Monitors vermerkt, die nächste geplante Minute versucht es erneut. Ein Zeitplan mit einem Tag im Monat wird nach einem Stillstand von bis zu einem Monat noch nachgeholt (mit einem Monat, bis zu einem Jahr), und die Stunde, die beim Zurückstellen der Uhr im Herbst doppelt vorkommt, wird nicht zweimal gemeldet. Ein Bericht ist alle seine Formate oder keines: lässt sich das zweite Format nicht schreiben, wird die erste Datei entfernt.

## Was ein Bericht enthält

Die Punktzahl des Kontos (mit Buchstabe und Trend; solange sie kalibriert oder zu wenig Daten hat, sagt er das und zeigt keine Zahl), was sich seit dem letzten Bericht geändert hat (Differenz in Punkten, neue und verschwundene Meldungen), die Repositorys der Gesundheitsansicht, die einen Menschen brauchen, zuerst, und die offenen Meldungen, die schlechtesten zuerst. Eine stumm geschaltete Meldung ist nicht offen. Jeder Text aus den Daten wird maskiert: Die Seite hat kein Skript und keine fremde Adresse.

## PDF

Es gibt kein eigenes PDF: Die HTML-Seite öffnen und im Browser als PDF drucken. Die Seite hat ein Druckformat für A4.

## Wo man sie sieht und anfordert

- Der Tab **Team** hat einen Bereich Berichte: die Liste, einen Link zu jeder Datei und die Schaltfläche **Jetzt einen Bericht schreiben** (ein Administrator, an diesem Rechner).
- `GET /api/report-files` listet sie auf, `GET /api/report-files/file?name=...` öffnet einen (nur eine Datei, die der Dienst für dieses Konto geschrieben hat) und `POST /api/report-files/run` schreibt jetzt einen.
- Im Teammodus kann jeder, der das Konto sehen darf, dessen Berichte lesen; jetzt einen zu schreiben ist Sache eines Administrators an diesem Rechner. Die Lite-Edition hat nichts davon.

## Vergleich mit dem Zeitraum davor

Ist `compare.include_in_report` an (standardmäßig aus und nur, solange `compare.enabled` an ist), enthält der Bericht zusätzlich einen kurzen Abschnitt, der diesen Zeitraum dem davor gegenüberstellt, eine Zeile je Kennzahl. Siehe [COMPARE_deu.md](COMPARE_deu.md).
