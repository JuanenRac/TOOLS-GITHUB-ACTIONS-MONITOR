<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Konsolenwerkzeuge: Workflow-Linter und Konsolenansicht

Zwei optionale Kommandozeilenwerkzeuge. Der Monitor selbst braucht kein Paket; die Konsolenansicht nutzt Rich, wenn Sie sie starten.

## Der Workflow-Linter: `lint_workflows.py`

- `py -3 lint_workflows.py [PFAD ...] [--json] [--fail-on info|warn|bad]` prüft `.github/workflows/*.yml` vor dem Push. Ohne Pfad wird der aktuelle Ordner angesehen. Er öffnet nur Dateien.
- Regeln (jede lässt sich im Reiter Einstellungen, Unterreiter Workflow-Linter, ausschalten und anders gewichten): `unpinned_uses` (eine Action ohne vollständigen Commit-SHA), `permissions` (kein `permissions:`-Block oder `write-all`), `secrets_in_clear` (etwas, das wie ein Token oder Schlüssel in der Datei aussieht), `injection` (Text von Dritten in einem `run:`-Skript) und `pr_target` (`pull_request_target` mit Checkout des Pull-Request-Codes).
- Der Exit-Code ist 1, wenn ein Fund `--fail-on` erreicht (Standard `bad`); so eignet er sich als Pre-Push-Hook. Sieht der Monitor Ihre Klone, fügt er dem Tagesbericht außerdem eine Zeile hinzu.
- Ein Wert, der wie ein Geheimnis aussieht, wird eingestuft, ohne je ausgegeben oder gespeichert zu werden: ein bekanntes Token-Format oder eine lange Zeichenkette mit hoher Entropie ist ernst (`bad`), ein lesbarer Platzhalter wie `placeholder`, `dummy`, `changeme` oder `ci` ist nur eine Information, alles andere eine Warnung, und `${{ secrets.X }}`, `${X}` oder ein leerer Wert ist kein Fund. Um einen Fund zu unterdrücken, schreiben Sie einen Kommentar in seine Zeile oder die davor: `# monitor-lint: ignore secrets_in_clear weil es ein Platzhalter für docker compose config ist` (ein Regelname oder `all`); oder tragen Sie Muster `Repository:Datei:Regel`, mit `*`, in die Einstellung `lint.ignore` ein.


## Die Konsolenansicht: `tui.py`

- `pip install rich`, dann `py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Sie zeichnet ein Live-Raster mit dem, was läuft, den roten Workflows, der Signatur-Warteschlange und dem Bericht, gelesen vom laufenden Monitor auf `127.0.0.1` (kein GitHub-Kontingent).
- Sie ist nur lesend: Keine Taste startet neu, schließt oder schreibt etwas. Ohne Rich nennt sie die Installation und endet mit Code 3; der Monitor und seine Tests brauchen Rich nie.
- Die interaktive Terminalanwendung `tui_textual.py` (`pip install textual`; mit `--lite` für die Lite-Ausgabe) bearbeitet im Reiter Einstellungen die einfachen Einstellungen der aufgeführten Gruppen, **Listen** (Einträge durch Kommas getrennt: `a, b, c`) und **Zahlen-Maps** (`name=3, other=5`); der Server prüft jeden Wert erneut, und die Sicherheitsoptionen lassen sich nur auf der Seite ändern.
