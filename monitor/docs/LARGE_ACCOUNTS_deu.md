<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Große Konten: hunderte Repositorys

Ein Konto mit hunderten Repositorys, vielen Forks oder mehreren Organisationen verbraucht das Kontingent der API schnell. Dies ist ein Rezept, in der Reihenfolge mit der größten Ersparnis; jede Einstellung steht im Tab Einstellungen.

1. **Mit einem Profil beginnen.** Einstellungen > Basis > Profil: *Open-Source-Organisation* setzt das meiste Folgende mit einem Klick (danach lässt sich jede Einstellung ändern).
2. **Überwachen, was gepflegt wird.** `discovery.fork_policy` = `auto` behält nur Forks mit eigener CI (die Kontoart bestimmt das Fenster, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` verteilt die Fragen auf mehrere Abrufe. `discovery.skip_archived` ist standardmäßig an. `exclude` und `ecosystems` grenzen die Liste nach Namen ein. Eine leer ankommende Kontenliste oder eine mit weniger als `discovery.min_keep_pct` Prozent der letzten guten wird nicht geglaubt: Die letzte gute Liste bleibt, die Liste wird in fünf Minuten erneut gelesen und der Brief für die KI-Werkzeuge hat das Signal repos.listing. `discovery.hide` akzeptiert auch `public` (und `private`, `fork`, `empty`); der Tab Grundlagen zählt, was jede Regel ausgelassen hat, sodass nichts durch einen Filter Ausgelassenes als sauber gelesen wird.
3. **Weniger fragen.** `cold_runs_per_repo` und `cold_refresh_seconds` bestimmen, was ruhige Repositorys kosten; `runs_per_repo` und `refresh_seconds` tun dasselbe für heiße. `network.etag` macht wiederholte Lesungen kostenlos, wenn sich nichts geändert hat, und der Low-Modus (`modes.auto_low`) bremst alles von selbst, wenn das Kontingent knapp wird.
4. **Dem Wächter ein Budget geben.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` und `sentinel.hygiene_seconds` (Hygiene ist standardmäßig eine Anfrage je Repository alle sechs Stunden; verlängern) begrenzen, was die Prüfungen A3-A6 verbrauchen.
5. **Ein zweites Kontingent hinzufügen.** `github_app.share_reads` lässt eine GitHub App einen Teil der Lesungen mit eigenem Kontingent beantworten.
6. **Nicht im Rauschen ertrinken.** Die Hygieneprüfung (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), die Prüfung der Release-Dateien (`sentinel.surface.checks.release_assets.allow_empty`) und `sentinel.bots_apart` verhindern, dass sich Prüfungen häufen, die für Ihre Repositorys nicht gelten.

Der Tab Kontingent zeigt, was jede Quelle noch hat und wie viel der Monitor selbst verbraucht.

Die Verfolgung der Originale von Forks (`upstream.enabled`) sagt in ihrer Anzeige, wie lange ein Durchgang über alle Forks im Tempo von `upstream.requests_per_hour` und `upstream.forks_per_request` dauert; ist das länger als `upstream.refresh_hours`, ruht die Verfolgung nie (727 Forks bei 8 je Anfrage und 6 Anfragen pro Stunde brauchen 15,2 Stunden). Die Anfragen der letzten Stunde bleiben beim Neustart erhalten, ein Neustart gibt das Kontingent also nicht zurück.

Die Aufrufe eines Ticks des Wächters (`sentinel.max_calls_per_tick`) sind eine einzige Zählung für alle seine Stufen, und ein Repository, dessen Lesungen dreimal hintereinander fehlschlagen, wird 30 Sekunden in Ruhe gelassen (bis auf 10 Minuten verdoppelt), während die anderen gelesen werden.
