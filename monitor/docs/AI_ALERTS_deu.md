<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Meldungen für KIs

Ein roter Workflow nützt nichts, wenn niemand, der am Repository arbeitet, davon erfährt. Der Monitor schreibt einen kleinen Feed, den jedes KI-Werkzeug (Codex, Gemini CLI, Copilot) oder Skript lesen kann.

## Was er schreibt (lokal, nur lesend, kein Netz)
- `ai_alerts.jsonl`: eine Zeile pro Ereignis (geöffnet, bestätigt, gelöst) mit stabiler ID, Schweregrad, Repository, Workflow, Ergebnis, seit wann, Serie, Link, wahrscheinlicher Ursache (**echt** oder **vorübergehend**), empfohlener Aktion und Status.
- `ALERTS_BRIEF.md`: wird in jedem Zyklus neu geschrieben und ist kurz (`ai_alerts.brief_max_bytes`, standardmäßig 2 KB). Echte Meldungen stehen zuerst.
- Vorübergehende Ursachen (502/503/504, Zeitüberschreitungen, Ratenlimits, Download-Fehler, ein nie gestarteter Lauf) werden mit editierbaren Regeln in `ai_alerts.transient_patterns` von echten Fehlern unterschieden. Eine Meldung löst sich von selbst, wenn der Workflow wieder grün ist, und du kannst sie bestätigen (`ack`), was nur diesen lokalen Zustand ändert.
- Alles läuft zuerst durch einen Bereiniger: Tokens, Schlüssel, E-Mail-Adressen, IP-Adressen und dein Home-Ordner erreichen nie die Dateien, die Endpunkte oder den Hook.
- Der Ordner ist `ai_alerts.folder` (Standard: neben dem Monitor); wähle einen, den deine KI-Sitzungen lesen. `ci_red.json` enthält in jedem roten Workflow einen optionalen `ai_hint` (Klasse, Ursache, Aktion).

## Wie eine KI es liest
- Schreibe in die Anweisungen deines Projekts oder Skills: *„Lies zu Beginn ALERTS_BRIEF.md (Pfad) und nenne die offenen echten Meldungen.“*
- Oder frage den laufenden Monitor: `GET /api/ai/brief` (Markdown, oder `?fmt=json`) und `GET /api/ai/alerts?since=SEKUNDEN`. Es gelten dieselben Regeln wie für den Rest der Seite (dieser Rechner; im Netzwerkmodus das Zugriffstoken).
- Oder füge den MCP-Server hinzu (nur lesend): `python mcp_server.py`, Werkzeuge `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`; `--allow-ack` ergänzt `ack_alert` (nur lokaler Zustand). Gemini CLI, Codex und VS Code (Copilot): denselben Befehl als stdio-Server in den MCP-Einstellungen eintragen.

## Meldungen, die dich erreichen
- Eine NEUE echte Meldung geht an die Benachrichtigungskanäle, die du schon eingerichtet hast (Einstellungen > Benachrichtigungen).
- Optional, standardmäßig aus: `ai_alerts.hook` schickt die neue echte Meldung (geschlossene Liste bereinigter Felder) per POST an eine Adresse auf diesem Rechner, höchstens `max_per_hour`-mal pro Stunde, damit ein eigenes Skript eine KI-Sitzung wecken kann.
- Nichts davon sendet Daten an einen KI-Anbieter, führt einen Befehl aus oder schreibt auf GitHub.

## Der MCP-Server ist lokal

`mcp_server.py` spricht JSON über Standardeingabe und -ausgabe mit dem KI-Werkzeug, das ihn startet: Er hat keinen Netzwerkport und darf nie hinter einen gelegt werden. Eine fehlerhafte Nachricht erhält einen Fehler nur für diese Nachricht, eine Zeile über 64 KB wird abgelehnt, und `ack_alert` (nur mit `--allow-ack`) ändert nur den lokalen Zustand des Feeds. Der Feed kann Repository-Namen und kurze CI-Fehlermeldungen enthalten; alles wird vor der Ausgabe von Token, Schlüsseln, E-Mail-Adressen, IP-Adressen und dem Ordner einer Person bereinigt.
