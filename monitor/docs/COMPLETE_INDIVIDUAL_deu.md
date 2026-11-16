<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# Vollausgabe für eine Person

Die Vollausgabe auf dem eigenen Rechner ist die übliche Art, den Monitor zu nutzen: eine Person, ein GitHub-Konto, keine Anmeldung und eine Seite, die sich nur auf `127.0.0.1` öffnet. Die einfache Ausgabe für alle, die nur ihre Läufe sehen wollen, ist [LITE_deu.md](LITE_deu.md).

## Start

- Melde dich einmal mit `gh auth login` bei GitHub an und starte dann `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` oder `.command`). Die Seite öffnet sich auf Port 8765 (`ports.complete`).
- Wähle in den Einstellungen die Repositories und Ökosysteme, die überwacht werden sollen. Die ersten fünf Minuten stehen in [FIRST_STEPS_deu.md](FIRST_STEPS_deu.md).

## Was du bekommst

- Drei Wächter (CI an; Collab und Security aus, bis du sie einschaltest) und eine Liste von Meldungen, die du von deinem Rechner aus stummschalten kannst.
- Die Bewertung des Kontos, den Zustand jedes Repositorys, geplante Berichte (standardmäßig aus) und ein Protokoll der ausgeführten Aktionen (standardmäßig an, `audit_log.enabled`).
- Die Arbeitsmodi normal, schnell und Turbo ([MODES_deu.md](MODES_deu.md)) und den Niedrig-Modus, wenn das Kontingent knapp ist ([QUOTA_deu.md](QUOTA_deu.md)).

## Auf diesem Rechner bleiben

- Mit ausgeschaltetem `auth.enabled` (Standard) gibt es keine Benutzer und nichts zu merken: Schalte den Teammodus nur ein, wenn mehr als eine Person den Monitor nutzt ([COMPLETE_TEAM_deu.md](COMPLETE_TEAM_deu.md)).
- `listen.network` ist standardmäßig aus: Seite und API antworten nur auf `127.0.0.1`. Für den Dauerbetrieb lies [COMPLETE_SERVICE_deu.md](COMPLETE_SERVICE_deu.md).

## Im Alltag

- `python bin/monitor_cli.py status`, `doctor` und `health` fragen den laufenden Monitor ab ([CLI_deu.md](CLI_deu.md)). Zum Aktualisieren lies [MIGRATING_deu.md](MIGRATING_deu.md).
- Eigene Skripte können die API lesen: [API_deu.md](API_deu.md) nennt, was sich nicht ändern soll.
