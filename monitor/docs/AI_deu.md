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


## Die KI-Symbole der Leiste

Die Leiste oben rechts zeigt zwei Symbole: Der Chip ist die im Monitor eingebaute KI, die Wellen sind ein externes KI-Werkzeug, das den Monitor liest. Ein Abzeichen nennt den Zustand, ohne von der Farbe abzuhängen: ein Haken bedeutet aktiv, ein Schrägstrich (mit gestrichelter Zeichnung) inaktiv und ein Dreieck einen Fehler (die eingebaute KI ist eingerichtet, antwortet aber nicht). Der Mauszeiger zeigt den genauen Zustand; ein Klick auf das Symbol, oder Eingabe- bzw. Leertaste bei Fokus, öffnet die zugehörige Gruppe im KI-Bereich der Einstellungen (der Chip führt zu Anbieter und Modell, die Wellen zum Feed der externen KI-Werkzeuge; die Gruppe wird in den Blick gerollt, kurz hervorgehoben und ihr erstes Feld erhält den Fokus).

## Was sie sehen darf

- Jede Eingabe wird bereinigt: Steuerzeichen entfernt, Geheimnisse per Muster geschwärzt, Länge begrenzt, der Inhalt zwischen zufällige Trennzeichen gesetzt und als nicht vertrauenswürdig erklärt. Die Antwort wird gekürzt, ihre Links entschärft.
- Derselbe einzige Bereiniger (Token, Schlüssel, Zugangsdaten in Adressen, E-Mail-Adressen, IP-Adressen, Ihr Home-Ordner) bedient diesen Assistenten, den Feed für KIs, die Endpunkte und den Hook. Er arbeitet nach Mustern: Er senkt das Risiko, er ist keine Garantie. Ein Aufruf an einen Anbieter folgt nie einer Weiterleitung (der Schlüssel ginge an eine andere Adresse) und nutzt die Proxy-Variablen der Umgebung nicht: Ein Server auf diesem Rechner wird direkt aufgerufen, ein entfernter nur mit `network.use_proxy` über den Proxy.
- Im Reiter Einstellungen wählen Sie die analysierbaren Ereignisarten (`build`, `codeql`, `report`), die sichtbaren Repositorys (leer = die vom Monitor beobachteten), die Sprache der Antworten, das Tageslimit der Aufrufe und die Größenlimits. Eine Schaltfläche testet die Verbindung, die Seite zeigt die heutigen Aufrufe.


## Aktionen vorschlagen und ausführen

- Stufe 3 (`ai.actions.enabled`): Ein Befehl in der Antwort bleibt nur, wenn er zur GESCHLOSSENEN LISTE passt: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` und `act -W DATEI -j JOB` (letzterer wird nur angezeigt). Der gezeigte Befehl wird aus den geprüften Teilen neu gebaut, nie vom Modell kopiert; Repository und Run- oder Issue-Nummer müssen dem Monitor schon bekannt sein.
- Stufe 4 (`ai.actions.execute`, eigener Schalter, aus): Jeder Vorschlag hat eine Bestätigen-Schaltfläche; ein Dialog zeigt den ganzen Befehl, und nichts läuft, bis Sie zustimmen. Er läuft mit Ihrem eigenen `gh`-Login ohne Shell, höchstens `ai.actions.max_per_hour` pro Stunde, jeder Versuch kommt ins lokale Protokoll der Seite, und nach zwei Fehlern in Folge sperren sich die Aktionen, bis Sie sie entsperren.
- Absichtlich nicht in der Liste: Branches löschen, Pull Requests schließen oder mergen, alles zu Geheimnissen oder Einstellungen.

## Modelle des Anbieters

Der Modellname ist freier Text, aber der Monitor kann die Modellliste vom Anbieter lesen und den Namen damit prüfen. Modelle und Versionen ändern sich oft, deshalb liefert der Monitor keine Modellliste mit: Die Beispiele der Voreinstellungen können veraltet sein.

- **Die Liste.** Einstellungen, Reiter *Externe KI*, Block *Modelle und Daten je Modell*: *Modelle des Anbieters laden* liest die Liste (`/models` eines Servers im OpenAI-Stil, die entsprechende Liste der Anthropic-API, `/api/tags` von Ollama) mit einer lesenden Anfrage. Der Schlüssel geht in einem Header, wird aus seiner Umgebungsvariable gelesen und nie gespeichert. Durchsuche die Liste und wähle mit *Dieses Modell verwenden* ein Modell. Die Liste wird gespeichert und von `ai.catalog.ttl_minutes` und `ai.catalog.max_requests_per_day` begrenzt. Ist `ai.catalog.enabled` an (standardmäßig aus), warnt der Monitor auch, wenn das eingestellte Modell nicht mehr in der Liste steht (eingestellt oder umbenannt); ist es aus, löst nur du das Lesen aus.
- **Daten je Modell.** Kontextfenster, Preis für Eingabe und Ausgabe pro Million Tokens und ob Werkzeuge unterstützt werden, werden nur mit dem gefüllt, was der Anbieter liefert; was er nicht nennt, bleibt *unbekannt* (es wird nie eine Zahl erfunden). Du kannst eigene Werte eintragen; deine haben Vorrang. Ist `ai.catalog.fit_context` an (standardmäßig aus), wird das Eingabelimit an das Kontextfenster angepasst, wenn es bekannt ist.
- **Ein Modell testen.** *Dieses Modell testen* oder `monitor_cli.py ai test --provider NAME --model NAME` fragt das Modell zu einem SYNTHETISCHEN Fehler (nie Daten deiner Repositories) und zeigt Latenz, Tokens, geschätzte Kosten und eine Beispielantwort. Es zählt als ein Aufruf des Tageslimits, und das Ergebnis („getestet“, mit lokalem Datum) bleibt in der Tabelle.
- **Befehle.** `monitor_cli.py ai models [--refresh]` zeigt Modelle und Daten; `ai doctor` erklärt, warum eine KI nicht antwortet (Schlüsselvariable nicht gesetzt, unbekanntes Modell, Kontingent, Netzwerk) und gibt nie einen Schlüssel aus.
- **Routen.** `GET /api/ai/models` (die gespeicherte Liste, die Prüfung und die Tabelle; nur lesend) und, nur von diesem Rechner aus, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` und `POST /api/ai/doctor`.

## Kompatible KIs

Gehostete Dienste und lokale Server, deren Protokoll der Monitor bereits spricht (`openai-compatible`, `anthropic` oder `ollama`). Die Liste ist eine neutrale Tabelle, keine Empfehlung: Keine ist standardmäßig aktiv, der Schlüssel wird IMMER aus einer Umgebungsvariable gelesen, deren Namen Sie festlegen (nie in einer Einstellung, einem Protokoll, einem Bericht oder der API), und die Voreinstellung füllt nur die Adresse, den Namen dieser Variable und ein Beispielmodell aus (änderbar; nichts wird heruntergeladen, keine Modellgewichte mitgeliefert). Wählen Sie in den KI-Einstellungen eine Voreinstellung, drücken Sie die Schaltfläche zum Ausfüllen, prüfen und speichern Sie, dann „Verbindung testen“. Die Liste sind Daten (`ai_presets.json`) und wird schreibgeschützt unter `GET /api/ai/presets` ausgeliefert.

| Name | Art | Anbieter | Adresse | Schlüsselvariable | Beispielmodelle | Datenschutz | Stand |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | gehostet | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Anthropic | gehostet | `anthropic` | `Standardadresse` | `ANTHROPIC_API_KEY` | — | wird über das Internet gesendet | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Google Gemini | gehostet | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| xAI Grok | gehostet | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Mistral | gehostet | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| DeepSeek | gehostet | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Groq | gehostet | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| OpenRouter | gehostet | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Together AI | gehostet | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Fireworks AI | gehostet | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Perplexity | gehostet | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Cohere | gehostet | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | wird über das Internet gesendet | Adresse in der öffentlichen Dokumentation gelesen; protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Ollama | lokal | `ollama` | `http://127.0.0.1:11434` | keine (lokaler Server) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| LM Studio | lokal | `openai-compatible` | `http://127.0.0.1:1234/v1` | keine (lokaler Server) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| llama.cpp server | lokal | `openai-compatible` | `http://127.0.0.1:8080/v1` | keine (lokaler Server) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| vLLM | lokal | `openai-compatible` | `http://127.0.0.1:8000/v1` | keine (lokaler Server) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| LocalAI | lokal | `openai-compatible` | `http://127.0.0.1:8081/v1` | keine (lokaler Server) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
| Jan | lokal | `openai-compatible` | `http://127.0.0.1:1337/v1` | keine (lokaler Server) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | bleibt auf diesem Computer | protokollkompatibel, mit diesem Werkzeug nicht getestet |
