<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | [🇪🇸 Español](MODES_spa.md) | [🇫🇷 Français](MODES_fra.md) | [🇮🇹 Italiano](MODES_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# Arbeitsmodi: normal, schnell und Turbo

Wenn Sie etwas eine Weile genauer beobachten wollen (etwa eine Stunde), können Sie den Monitor auf einen schnelleren Modus stellen, auch wenn er das API-Kontingent schneller verbraucht. Die Auswahl mit dem Messer-Symbol steht in der Kopfzeile; in der Konsole nutzen Sie `--mode fast` oder `--mode turbo` mit `--mode-minutes 60`.

| Modus | Was sich ändert | Standardwerte |
|---|---|---|
| **normal** | nichts: Ihre eigene Konfiguration | Ihre |
| **fast** (schnell) | Aktualisierung, Kaltaktualisierung, Runs je Repository, heißes Fenster | 30 s, 300 s, 30 Runs, 6 h |
| **turbo** | dasselbe, mehr | 15 s, 90 s, 50 Runs, 12 h |

Die Voreinstellungen sind der Block `modes` in `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`); passen Sie sie an. Eine Voreinstellung macht einen Wert nie langsamer oder kleiner als Ihren eigenen, und nichts geht unter 10 Sekunden, um von den sekundären Limits von GitHub fernzubleiben (danach wartet der Monitor mindestens eine Minute und dann länger).

**Vor dem Start** zeigt die Seite die Aufrufe pro Stunde im schlimmsten Fall, was der Cache üblicherweise spart (ein bedingter Lesevorgang mit Antwort `304` kostet kein primäres Kontingent) und wie lange das verbleibende Kontingent reichen würde. **Er kehrt von selbst zu normal zurück**, wenn die Zeit um ist (die Kopfzeile zählt herunter) und wenn das verbleibende Kontingent unter `min_rate_remaining` fällt; ein Hinweis sagt warum, die Konsole gibt ihn aus. **Ohne Anmeldung gibt GitHub nur 60 Aufrufe pro Stunde**, daher sind schnell und Turbo mit Begründung deaktiviert (`gh auth login` ausführen).

Den Modus zu ändern ist eine lokale Einstellung: sie braucht wie jede Änderung das Einmal-Token der Seite, lebt nur im Speicher (ein Neustart führt zu normal, außer Sie schreiben `modes.start` selbst) und sendet nichts irgendwohin. Er funktioniert in beiden Ausgaben; der Wächter der vollständigen Ausgabe behält eigene Intervalle und ein eigenes Aufrufbudget (`sentinel.budget_per_hour`), beschrieben in [Der Wächter](SENTINEL_deu.md). Banner und Statuszeilen der Konsole nennen den aktiven Modus.

## Sparmodus (extremes Sparen des Kontingents)

Das Gegenteil von schnell und turbo, für den Fall, dass viele Werkzeuge (Agenten, KI-Werkzeuge, Skripte) dieselben 5000 Aufrufe pro Stunde des Kontos verbrauchen. In `low` liest der Monitor nur die heißen Repositories (ein laufender Lauf, ein roter Workflow) alle 4 Minuten, den Rest alle 30 Minuten, mit kurzen Lauflisten und nur 2 Stunden "heiß"; das Kontingent (`rate_limit`, kostenlos) wird weiterhin in jedem Zyklus gelesen. Er ist immer erlaubt (er verbraucht weniger), verlässt sich nie von selbst, wenn er von Hand gewählt wurde, und jede Zahl behält in der unteren Leiste die Zeit ihrer letzten Abfrage, damit eine alte Zahl nicht neu aussieht; die Zusammenfassung und `/api/ai/state` nennen `working mode low` mit dem Alter der Daten.

`modes.auto_low` (standardmäßig an): Fallen die verbleibenden Aufrufe unter `modes.auto_low_enter` (1000), wechselt der Monitor von selbst in den Sparmodus und kehrt zu normal zurück, wenn sie `modes.auto_low_exit` (2500) übersteigen oder das Kontingent erneuert wird; die beiden Zahlen sind absichtlich verschieden, damit er nicht hin- und herspringt. Die Werte des Sparmodus stehen in `modes.low` der Konfigurationsdatei (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`); eine langsamere eigene Einstellung wird nie beschleunigt. Bereits gelesene rote Warnungen bleiben in der Liste, solange der Sparmodus aktiv ist.
