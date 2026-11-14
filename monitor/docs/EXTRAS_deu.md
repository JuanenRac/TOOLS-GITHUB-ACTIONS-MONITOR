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

`github_app.share_reads`: Der folgende Befehl gibt auf diesem Rechner ein eine Stunde gültiges Installations-Token Ihrer GitHub-App aus, damit das `gh` Ihrer Werkzeuge und Agenten mit dem Kontingent der App liest und nicht mit Ihrem (`GH_TOKEN`). Das Token geht nur auf die Standardausgabe, nie in eine Datei oder ein Protokoll, und der Befehl braucht `--read-only`; geben Sie der App beim Anlegen nur Leseberechtigungen. Ohne `github_app.share_reads` verweigert er.

```
python bin/monitor_cli.py gh-token --read-only
```

## Noch nicht dabei

Das Panel zur Workflow-Hygiene, der Warteschlangenbericht, die Ansicht Release bereit oder blockiert und das Panel der Lieferkette gehören nicht zu dieser Version.
