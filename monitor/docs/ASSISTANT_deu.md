<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Der Assistent

Feste Fragen an die bereits eingerichtete KI, beantwortet mit den Daten des Monitors, nur lesend. Standardmäßig aus.

## Einschalten

1. Richten Sie einen KI-Anbieter ein (`ai.provider`; siehe [AI_CONNECTION_deu.md](AI_CONNECTION_deu.md)).
2. Schalten Sie in den Einstellungen unter KI `ai.assistant.enabled` ein. Das Feld erscheint im Reiter Meldungen. In der Lite-Ausgabe gibt es es nicht.
3. Stellen Sie eine Frage; die Antwort zeigt ihre Quellen, wie viel gesendet wurde und die Aufrufe des Tages.

## Die fünf Fragen

- `explain_alert`: warum eine Meldung offen ist (braucht die Meldung).
- `summarize_week`: die Lage des Kontos.
- `why_slow`: warum die CI eines Repositorys langsam ist oder hängt (braucht das Repository).
- `explain_repo`: die Lage eines Repositorys, seine Läufe und offenen Meldungen.
- `prioritize`: die offenen Meldungen, der Status und die Bewertung in Reihenfolge, mit ihren IDs.

Einen freien Chat gibt es nicht.

## Was er liest

Vier Werkzeuge, eine geschlossene Liste, die `ai.assistant.tools` verkleinern kann: `status`, `alerts`, `runs` und `score`. Höchstens `ai.assistant.max_tool_calls` Lesevorgänge pro Frage und `ai.assistant.max_context` gesendeter Text. Ist `ai.similar.enabled` an, listet „diese Meldung erklären“ auch ähnliche Meldungen, durch Wortvergleich gefunden, ohne Modell.

## Was er nie tut

Er schreibt nichts und erreicht nichts auf GitHub. Was ein Repository geschrieben hat (ein Titel, der Name eines Workflows), wird gekürzt, von Geheimnissen und Ihren versteckten Wörtern befreit und als Daten zwischen Marken übergeben, nie als Anweisung. Jede Frage verbraucht das eine Tagesbudget der KI (`ai.daily_limit`). Mit `ai.airgapped` wird nur ein Modell auf diesem Rechner oder in Ihrem privaten Netz benutzt.

## Prüfen

`GET /api/assistant` sagt, was er ist und welche Grenzen er hat; `POST /api/assistant/ask` nimmt `action` und je nach Bedarf `alert` oder `repo`. Beide antworten 404, solange er aus ist. Die Frage steht im Aktionsprotokoll (nie ihr Text); mit `ai.prompt_log.enabled` werden die bereinigten Prompts in einem lokalen Protokoll gehalten, das Sie in den Einstellungen ansehen und leeren können.
