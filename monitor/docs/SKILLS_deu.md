<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | [🇮🇹 Italiano](SKILLS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# Skills für KIs

Der Monitor bringt zwei Skills mit: kurze Anleitungen, auf Englisch, die einer KI sagen, wie sie mit ihm arbeitet. Sie liegen im Ordner `skills/` des Pakets, in der Seite (Einstellungen, Reiter KI) und ein Befehl installiert sie.

## Die zwei Skills

- `skills/internal`: für die im Monitor eingebaute KI, lokal (Ollama, ein llama.cpp-Server, LM Studio) oder extern (die API eines Anbieters). Sie sagt, was der Monitor ist und was er sieht, was die KI lesen darf, was sie nie tun darf, wie man einen roten Lauf diagnostiziert, wann sie schweigt und wie sie Lehren nutzt und vorschlägt. Ihr Kern (`SKILL.md`) wird jedem Prompt dieser KI hinzugefügt, auf `ai.skill_max_chars` gekürzt, wenn `ai.skill` an ist.
- `skills/external`: für KIs, die von außen in jeder Richtung mit dem Monitor sprechen: lesen (`/api/ai/*`, die Dateien in `ai/`), benachrichtigt werden (der Stream oder die Zusammenfassung alle paar Minuten), schreiben (quittieren, Lehren, Fehler, Benachrichtigungseinstellungen) mit den passenden Berechtigungen, die Verbindung zwischen Monitor und Sitzung, das Briefing vor dem Push und der ganze Selbstlernzyklus. Sie deckt eine KI mit Kommandozeile, eine KI nur mit HTTP oder Dateien, eine KI mit MCP und eine KI am Stream ab.

## Was drin ist

Jede Skill besteht aus einer kurzen `SKILL.md` (dem Kern) und einem Ordner `references/`, der nur bei Bedarf gelesen wird, damit ein Modell mit kleinem Kontext nur den Kern nehmen kann: Szenarien Schritt für Schritt (ein echter roter Lauf, ein vorübergehender roter Lauf, wenig Kontingent, ein beeinträchtigter Monitor, ein wiederholter Fehler, eine neue Lehre, ohne Netz, mehrere Bildschirme), der Selbstlernzyklus, die Anbieter und ihre Grenzen, die Sicherheit (Prompt-Injection aus Protokollen, Geheimnisse, minimale Berechtigungen, Prüfung dessen, was eine KI schreibt) und die aus dem Code erzeugten Referenzen.

## Nichts bleibt außen vor

Die Referenzen (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) und `skills/COVERAGE.md` werden mit `python tools/make_skill_refs.py` aus dem Code ERZEUGT: jeder Endpunkt mit der kleinsten Rolle, die ihn aufrufen darf, jeder Befehl und jede Option, jede Einstellung mit ihrem Standardwert, jede vom Monitor geschriebene Datei, jede Rolle und jeder Reiter. Ein Test liest dieselben Listen aus dem Code und schlägt fehl, wenn etwas in den Skills nicht genannt ist; ein neuer Endpunkt, Befehl, eine neue Einstellung oder Datei kann also nicht erscheinen, ohne den KIs beschrieben zu werden (und der Generator hält an, bis seine Notiz geschrieben ist).

## Installieren

Kopieren Sie die Skill in den Ordner, aus dem Ihr KI-Werkzeug seine Skills liest:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Sicherheit des Installers

Er schreibt `github-actions-monitor-internal` oder `github-actions-monitor-external` in den angegebenen Ordner und sonst nichts. Er überschreibt nie eine Datei, die von der des Pakets abweicht (Ihre bleibt, und er sagt welche), und lehnt Laufwerk D: und Netzwerkpfade ab. Ein zweiter Lauf ändert nichts.

## In der Seite und per HTTP

In den Einstellungen, Reiter KI, hat der Block **Skills für KIs** je Skill Kopieren (der Kern) und Herunterladen (die ganze Skill mit Referenzen in einer Datei). `GET /api/skills` listet sie auf und `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` liefert den Text; nur lesend.

## Einstellungen

`ai.skill` (an) und `ai.skill_max_chars` (3000; 1500 für ein kleines lokales Modell). Fehler von außen zu registrieren geht mit `POST /api/ai/failures` und braucht `lessons.allow_write` und einen Administrator, wie das Schreiben einer Lehre.

## Veröffentlichung in einem Skill-Verzeichnis

`python tools/prepare_skill_bundle.py --out DIR` bereitet den Ordner des externen Skills zur Veröffentlichung vor (SKILL.md, Referenzen, `bundle.json` mit Monitor-Version und Lizenz, `SHA256SUMS`); gleiche Quellen ergeben gleiche Bytes. Es veröffentlicht nichts: das Hochladen zu ClawHub erfolgt von Hand mit dem Konto des Betreuers, nach Lesen der Bedingungen.

## Assistenten

Als getestet gilt nur, was wirklich ausprobiert wurde.

| Assistent oder Weg | Kommandozeile | HTTP und Dateien | MCP |
|---|---|---|---|
| Ein Coding-Assistent im Terminal | getestet | getestet | protokollkompatibel, nicht getestet |
| Andere Assistenten | protokollkompatibel, nicht getestet | protokollkompatibel, nicht getestet | protokollkompatibel, nicht getestet |
