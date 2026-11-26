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

## Vorschläge, die Menschen genehmigen

Jeder von einer KI vorgeschlagene Befehl (`ai.actions.enabled`) ist als KI-Vorschlag markiert, trägt den Fingerabdruck (SHA-256) dessen, was liefe, und bleibt bis zum Ablauf erhalten, auch nach einem Neustart. Er läuft nie von selbst. Genehmigen ist eine Entscheidung von Menschen: bei zwei oder mehr Benutzern braucht es zwei Personen (wer die KI gefragt hat, zählt als eine und kann nicht selbst genehmigen); allein tippen Sie die ersten acht Zeichen des Fingerabdrucks. Ablehnen kann eine Person. Mit `ai.assistant.can_propose` (aus) kann auch eine Chat-Antwort zum Vorschlag werden. Sie stehen im Reiter Meldungen.

## Freier Chat

`ai.chat.enabled` (aus) fügt einen Chat im Reiter Meldungen hinzu. Die KI darf nur lesen, mit den vier Werkzeugen oben; sie fragt an, der Monitor entscheidet. Gleiches Budget, gleicher Filter, gleiche Markierungen; jede Antwort nennt das Gelesene. Kein schreibendes Werkzeug.

## Ähnliche Meldungen mit lokalem Modell

Mit `ai.rag.enabled` (aus) und `ai.rag.model` ordnet „Meldung erklären“ nach Embeddings eines Modells auf diesem Rechner (Ollama-API; nur lokale Adressen). Der Index speichert Vektoren und Prüfsummen, nie den Text, bis `ai.rag.max_mb`; `ai_rag_index.json` zu löschen verliert nichts. Ohne Modell gilt der Wortvergleich. Nur gegen eine Attrappe getestet.

## Bericht eines Repositorys

Mit `ui.copy_report.enabled` kopiert der Reiter Meldungen den Bericht eines Repositorys in Markdown oder einen Triage-Entwurf zum Einfügen. Ohne KI, ohne GitHub-Abfrage, ohne Veröffentlichung.

Routen: `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`. Für MCP-Clients sind die Kurzberichte auch Ressourcen: `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`.
