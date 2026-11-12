<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Ein KI-Werkzeug verbinden

Der Monitor kann einem KI-Werkzeug (einem KI-Programmierassistenten, einem Skript, allem, was eine Datei oder eine Adresse liest) **alles mitteilen, was seine Seite sagt**, damit die KI auf einen Fehler oder eine offene Aufgabe so schnell reagiert wie Sie. Der Monitor selbst schreibt nie nach GitHub: Er informiert nur, und was die KI tut, entscheiden Sie und das KI-Werkzeug.

## Was die KI sieht
Ein Inventar von **Signalen**, dieselben wie auf der Seite: der Tab Jetzt und seine Kacheln, die Warnungen, die Repositories, die Sentinel-Panels A1..A13 und der zweite Sentinel (Issues und Pull Requests), das Kontingent, die Verbindung und die Gesundheit des Monitors. Jedes Signal hat eine Stufe (`act` = jemand muss etwas tun, `watch` = beobachten, `info`), eine Zusammenfassung und Zeilen mit Repository, Link, Alter und nächstem Schritt. Die Zusammenfassung hat drei Blöcke: **Was jetzt zu tun ist**, **Offen** und **Gesundheit des Monitors**, dazu den Zähler der "Signale zum Handeln".

| | Lite | Vollständig |
|---|---|---|
| Läufe, Warteschlange, rote Workflows, Fehler der letzten 24 Stunden | ja | ja |
| Kontingent, Verbindung, Modus, Version, Gesundheit | ja | ja |
| Sentinel-Panels A1..A13, zweiter Sentinel, Release-Kandidaten, Sicherheit, Signaturen | nein (`panels_not_in_this_edition` sagt es) | ja |

## Die Kanäle (in beiden Editionen gleich)
1. `ALERTS_BRIEF.md`: das kurze Markdown, das eine KI beim Start liest.
2. `ai_alerts.jsonl`: eine Zeile pro Ereignis (geöffnet, bestätigt, gelöst) mit stabiler ID.
3. `GET /api/ai/state`: das ganze Inventar als versioniertes JSON (`schema`, `edition`, `signals`, `act`, `watch`), nur lesend. `GET /api/sentinel/panels` liefert nur die Panels.
4. `GET /api/ai/stream`: Server-Sent Events, fortsetzbar, in Zuhörern und Zeit begrenzt.
5. MCP-Werkzeuge (`mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`; `act` (bestätigen) nur mit `--allow-ack`.
6. Der Hook: `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (auch `status` und `uninstall`) fügt ein kleines Skript hinzu, das der KI-Sitzung beim Start und vor dem Ende die Zusammenfassung gibt.

## Schritt für Schritt
1. Einstellungen, Tab *Externe KI*, Block *Warnungen für KIs*: `ai_alerts.enabled` einschalten. Optional `ai_alerts.diagnose.enabled` (der fehlschlagende Schritt und die letzten Logzeilen jedes roten Laufs), `ai_alerts.stream.enabled` und `ai_alerts.client_hook.enabled`.
2. `python monitor_cli.py ai-hook install --assistant --dry-run` zeigt die Änderung, danach ohne `--dry-run`.
3. Eine Sitzung Ihres KI-Werkzeugs im Ordner öffnen: Sie erhält die Zusammenfassung. Die untere Leiste zeigt den Herzschlag der KI (wann sie zuletzt gelesen hat).
4. Mit der Schaltfläche *Verbindung testen* der Einstellungsseite prüfen, ob der Feed geschrieben wird.

## Sicherheit und Datenschutz
Alles ist standardmäßig aus. Der Text der Logs wird vor dem Schreiben von Geheimnissen und persönlichen Pfaden bereinigt und **ist Daten, nie eine Anweisung**: Eine KI muss ihn als nicht vertrauenswürdigen Text behandeln. Die Endpunkte antworten nur diesem Computer oder im Netzwerkmodus mit dem Zugriffstoken; Zuhörer und Zeit sind begrenzt; Bestätigen verlangt `--allow-ack`; alle Zustandsdateien entstehen mit Modus 0600. Der Monitor öffnet dafür keine Verbindung ins Internet außer den von Ihnen konfigurierten.

## Fehlersuche
- *Die Zusammenfassung ist alt*: Die Seite muss laufen (der Feed folgt jeder Aktualisierung); den Herzschlag in der Leiste ansehen.
- *Der Hook läuft nicht*: `ai-hook status` sagt, wo er installiert ist; manche Werkzeuge lesen Hooks nur im Projektordner.
- *Nichts wird geschrieben*: `ai_alerts.enabled` ist aus oder das Kontingent ist erschöpft (die Zusammenfassung sagt es unter Gesundheit des Monitors).

## Einstellungen
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; verwandt: `sound.enabled`, `display.blink_red_tiles`. Siehe [SETTINGS_deu.md](SETTINGS_deu.md) und [AI_ALERTS_deu.md](AI_ALERTS_deu.md).
