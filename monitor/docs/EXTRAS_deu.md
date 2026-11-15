<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# Optionale Extras

Beide sind **standardmäßig aus** und werden in den Einstellungen eingeschaltet.

## Das Protokoll des fehlgeschlagenen Schritts

`logs.failed_step.enabled`: Ein Alarm eines fehlgeschlagenen Laufs erhält die Schaltfläche **Fehlgeschlagener Schritt**. Ein Druck liest die Jobs und das Fehlerprotokoll dieses Laufs von GitHub (zwei Aufrufe Ihres Kontingents), zeigt den fehlgeschlagenen Schritt und seine letzten relevanten Zeilen (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) und behält die Antwort im Speicher, ein erneuter Druck kostet also nichts. Der Text wird von Tokens, Schlüsseln, Adressen und Heimordner bereinigt. Nur vom Monitor beobachtete Repositories können abgefragt werden, mit `GET /api/run-log?repo=&run=`; im Teammodus nur von einem Administrator.

## Ein Nur-Lese-Token der GitHub-App für Ihre Werkzeuge

`github_app.share_reads`: Der folgende Befehl gibt auf diesem Rechner ein eine Stunde gültiges Installations-Token Ihrer GitHub-App aus, damit das `gh` Ihrer Werkzeuge und Agenten mit dem Kontingent der App liest und nicht mit Ihrem (`GH_TOKEN`). Das Token geht nur auf die Standardausgabe, nie in eine Datei oder ein Protokoll, und der Befehl braucht `--read-only`; geben Sie der App beim Anlegen nur Leseberechtigungen. Ohne `github_app.share_reads` verweigert er. Das Token wird getrennt von dem des Monitors und nur mit Leseberechtigungen angefordert; enthält die Antwort eine Schreibberechtigung, weigert sich der Befehl, es auszugeben.

```
python bin/monitor_cli.py gh-token --read-only
```

## Vier optionale Berichte

Alle vier sind standardmäßig aus. Sie erscheinen in einem Block "Optionale Berichte" am Ende des Reiters Alarme und in `GET /api/reports`. Die, die GitHub lesen, verbrauchen höchstens `reports.max_calls_per_cycle` Aufrufe pro Zyklus, lesen jedes Mal einige Repositories und halten das Gelesene einen Tag im Speicher.

- `reports.workflow_hygiene.enabled`: liest die Workflow-Dateien der Repositories und listet Schlechtgeschriebenes auf - nicht an einen Commit gebundene Actions, unbegrenzte Berechtigungen, einen Job ohne `timeout-minutes`, keine `concurrency`-Gruppe, `pull_request_target`- und Injection-Risiken, Geheimnisse im Klartext (die Regeln des Linters des Panels A13, das lokale Klone liest, plus die zwei neuen).
- `reports.queue.enabled`: liest die Jobs einiger beendeter Läufe, die gewartet haben, und sagt für jede Runner-Art (Linux, Windows, macOS, größere, selbst gehostete), wie lange ein Job vor dem Start wartete.
- `reports.release_view.enabled`: kein Aufruf; aus dem, was der Wächter weiß, sagt er, welche Repositories für ein Release BEREIT sind (Einträge im Changelog oder ein grüner Build, den niemand veröffentlicht hat, nichts rot, keine Signatur wartet) und welche BLOCKIERT sind, und warum.
- `reports.supply_chain.enabled`: liest das neueste Release der Repositories und sagt anhand der Dateinamen, ob es eine Software-Stückliste (SBOM), Prüfsummen und eine Signatur oder Attestierung enthält. Die Dateien werden nie heruntergeladen.
