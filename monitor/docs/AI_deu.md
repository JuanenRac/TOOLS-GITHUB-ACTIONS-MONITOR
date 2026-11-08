<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# Der KI-Assistent des Wächters

Optional und **standardmäßig aus**. Ein Sprachmodell kann den Tagesbericht zusammenfassen, Warnungen einordnen, einen fehlgeschlagenen Run erklären, Release-Notizen entwerfen und eine Frage zu einem Repository beantworten. Alles, was es schreibt, wird als ungeprüfter Vorschlag angezeigt.

## Anbieter

- `ollama`: ein Modell auf diesem Rechner (nur `127.0.0.1`; nichts verlässt den Rechner).
- `openai-compatible`: jeder Dienst mit Chat-Endpunkt im OpenAI-Stil. Das gilt auch für Gemini (dessen OpenAI-kompatibler Endpunkt) und für OpenAI selbst: `base_url`, `model` und den NAMEN der Variable mit dem Schlüssel eintragen.
- `anthropic`: die Messages-API von Anthropic (`https://api.anthropic.com`, Header `x-api-key` und `anthropic-version`). Das Modell wählen Sie; es ist keines fest eingebaut.
- `copilot`: `gh copilot` mit Ihrem eigenen GitHub-Login (kein Schlüssel im Monitor), nur Textantwort und keine Werkzeuge. Es verbraucht Premium-Anfragen Ihres Copilot-Plans. Starten Sie `gh copilot` einmal von Hand, damit die CLI installiert wird.
- Der Schlüssel wird nie gespeichert: Sie tragen den NAMEN einer Umgebungsvariable ein. Die drei entfernten Anbieter SENDEN Daten Ihrer Repositorys an Dritte.


## Was sie sehen darf

- Jede Eingabe wird bereinigt: Steuerzeichen entfernt, Geheimnisse per Muster geschwärzt, Länge begrenzt, der Inhalt zwischen zufällige Trennzeichen gesetzt und als nicht vertrauenswürdig erklärt. Die Antwort wird gekürzt, ihre Links entschärft.
- Im Reiter Einstellungen wählen Sie die analysierbaren Ereignisarten (`build`, `codeql`, `report`), die sichtbaren Repositorys (leer = die vom Monitor beobachteten), die Sprache der Antworten, das Tageslimit der Aufrufe und die Größenlimits. Eine Schaltfläche testet die Verbindung, die Seite zeigt die heutigen Aufrufe.


## Aktionen vorschlagen und ausführen

- Stufe 3 (`ai.actions.enabled`): Ein Befehl in der Antwort bleibt nur, wenn er zur GESCHLOSSENEN LISTE passt: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` und `act -W DATEI -j JOB` (letzterer wird nur angezeigt). Der gezeigte Befehl wird aus den geprüften Teilen neu gebaut, nie vom Modell kopiert; Repository und Run- oder Issue-Nummer müssen dem Monitor schon bekannt sein.
- Stufe 4 (`ai.actions.execute`, eigener Schalter, aus): Jeder Vorschlag hat eine Bestätigen-Schaltfläche; ein Dialog zeigt den ganzen Befehl, und nichts läuft, bis Sie zustimmen. Er läuft mit Ihrem eigenen `gh`-Login ohne Shell, höchstens `ai.actions.max_per_hour` pro Stunde, jeder Versuch kommt ins lokale Protokoll der Seite, und nach zwei Fehlern in Folge sperren sich die Aktionen, bis Sie sie entsperren.
- Absichtlich nicht in der Liste: Branches löschen, Pull Requests schließen oder mergen, alles zu Geheimnissen oder Einstellungen.
