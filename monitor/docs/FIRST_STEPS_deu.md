<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Ihre ersten fünf Minuten

**1. Das Nötige installieren.** Python 3.11 oder neuer und die GitHub CLI (`gh`). Dann einmal anmelden: `gh auth login`. Der Monitor speichert nie ein Token: er fragt `gh` (außer Sie schalten das optionale Token des Monitors unter Einstellungen > Erweitert ein).

**2. Alles mit einem Befehl prüfen.** `python bin/actions_monitor.py --doctor` nennt zu jedem Problem den genauen Befehl, der es behebt. Erst umschauen? `python bin/actions_monitor.py --demo` öffnet die Seite mit erfundenen Daten: ohne `gh`, ohne Anmeldung, ohne Netz.

**3. Starten.** Doppelklick auf `MONITOR_LITE_GITHUB_ACTIONS` für die einfache Ausgabe (Port 8766) oder `MONITOR_GITHUB_ACTIONS` für die vollständige mit Wächter (Port 8765). Das Konsolenfenster nennt die Ausgabe in Titel und erster Zeile.

**4. Den drei Schritten der Begrüßung folgen.** Beim ersten Mal erklärt die Seite, was sie tut, zeigt, was sie in Ihrem Konto gefunden hat, und verweist auf die Grundeinstellungen. Standardmäßig wird nichts ausgeblendet: Repositorys ohne Gruppe erscheinen als *Nicht eingeordnet*.

**5. Wissen, wo die Hilfe ist.** Die runde **?**-Taste (oder die Taste `?`) öffnet die Hilfe; die **i**-Taste öffnet „Über“ mit Version, Dateien und einer Taste, die die Informationen für den Support kopiert (ohne Geheimnisse). In der Konsole: `--help-topics`, `--help-search WORTE`, `--about`.

**Gut zu wissen.** Bei einem Tarif mit privaten Repositorys wählen Sie ihn unter Einstellungen > Grundlagen, um Ihre Kontingente zu sehen ([Kontingente und Tarife](QUOTAS_deu.md)). Der Wächter steht in [Der Wächter](SENTINEL_deu.md). Das Werkzeug liest GitHub nur; es schreibt erst nach Ihrer Bestätigung.
