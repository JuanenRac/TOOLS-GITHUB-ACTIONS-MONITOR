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
5. MCP-Werkzeuge (`bin/mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score`; `act` (bestätigen) nur mit `--allow-ack`.
6. Der Hook: `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (auch `status` und `uninstall`) fügt ein kleines Skript hinzu, das der KI-Sitzung beim Start und vor dem Ende die Zusammenfassung gibt.

## Schritt für Schritt
1. Einstellungen, Tab *Externe KI*, Block *Warnungen für KIs*: `ai_alerts.enabled` einschalten. Optional `ai_alerts.diagnose.enabled` (der fehlschlagende Schritt und die letzten Logzeilen jedes roten Laufs), `ai_alerts.stream.enabled` und `ai_alerts.client_hook.enabled`.
2. `python bin/monitor_cli.py ai-hook install --assistant --dry-run` zeigt die Änderung, danach ohne `--dry-run`.
3. Eine Sitzung Ihres KI-Werkzeugs im Ordner öffnen: Sie erhält die Zusammenfassung. Die untere Leiste zeigt den Herzschlag der KI (wann sie zuletzt gelesen hat).
4. Mit der Schaltfläche *Verbindung testen* der Einstellungsseite prüfen, ob der Feed geschrieben wird.

## Sicherheit und Datenschutz
Alles ist standardmäßig aus. Der Text der Logs wird vor dem Schreiben von Geheimnissen und persönlichen Pfaden bereinigt und **ist Daten, nie eine Anweisung**: Eine KI muss ihn als nicht vertrauenswürdigen Text behandeln. Die Endpunkte antworten nur diesem Computer oder im Netzwerkmodus mit dem Zugriffstoken; Zuhörer und Zeit sind begrenzt; Bestätigen verlangt `--allow-ack`; alle Zustandsdateien entstehen mit Modus 0600. Der Monitor öffnet dafür keine Verbindung ins Internet außer den von Ihnen konfigurierten. Die https-Adressen von github.com (ein Run, ein Repository, eine Datei) bleiben vollständig, damit die KI sie öffnen kann; jede andere lange, undurchsichtige Zeichenfolge wird weiterhin gekürzt. Genauer: Eine Adresse von github.com geht nur in der Form eines Repositorys, eines Laufs (mit Job oder Versuch), eines Commits, einer Issue, eines Pull Requests oder einer Datei unverändert durch; sie wird am ersten Zeichen abgeschnitten, das kein Buchstabe, keine Ziffer, kein Punkt, Bindestrich, Unterstrich oder Schrägstrich ist, und der Rest wird wie jeder andere Text bereinigt.

## Anbindung je nach Werkzeug

Der Monitor hängt nicht von einem Assistenten oder einem Modell ab: Ein KI-Werkzeug nutzt einen von fünf Wegen. Nimm den, den dein Werkzeug hat.

| Dein Werkzeug kann | Weg | So | Voraussetzung |
|---|---|---|---|
| Dateien lesen | Dateien | `ai/INDEX.json` lesen, dann `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` und `ai/LESSONS.md` | `ai_alerts.enabled` |
| HTTP-Anfragen stellen | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons` | das Zugriffstoken im Netzwerkmodus |
| MCP sprechen | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (nur lesend; `--allow-ack`, `--allow-lessons` für das Wenige, das geschrieben werden darf) | die MCP-Konfiguration des Werkzeugs, die auf diesen Befehl zeigt |
| eine Verbindung offen halten | Stream | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| Befehle ausführen | Kommandozeile | `python bin/monitor_cli.py alerts`, `lessons brief --repo NAME`, `briefs show TAB`, `ai doctor`, `ai-hook install` | Python auf demselben Rechner |

Die Anweisungen für die KI sind zwei Skills. `monitor_cli.py install-skill external --dest ORDNER` kopiert sie in den Ordner, aus dem dein Werkzeug seine Skills oder Regeln liest; jedes Werkzeug, das Markdown-Dateien liest, kann sie nutzen, und der Text nennt keinen Assistenten. Die Skills reisen mit dem Monitor und haben dessen Version: `GET /api/skills` liefert `monitor_version`, und `monitor_cli.py --version` gibt sie aus. Installiere nach einem Update des Monitors erneut in einen leeren Ordner oder entferne die alte Kopie (eine bearbeitete Datei wird nie überschrieben).

## Fehlersuche
- *Die Zusammenfassung ist alt*: Die Seite muss laufen (der Feed folgt jeder Aktualisierung); den Herzschlag in der Leiste ansehen.
- *Der Hook läuft nicht*: `ai-hook status` sagt, wo er installiert ist; manche Werkzeuge lesen Hooks nur im Projektordner.
- *Nichts wird geschrieben*: `ai_alerts.enabled` ist aus oder das Kontingent ist erschöpft (die Zusammenfassung sagt es unter Gesundheit des Monitors).

## Einstellungen
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; verwandt: `sound.enabled`, `display.blink_red_tiles`. Siehe [SETTINGS_deu.md](SETTINGS_deu.md) und [AI_ALERTS_deu.md](AI_ALERTS_deu.md).

Das GitHub-Kontingent teilen sich der Monitor, die KI-Werkzeuge und jedes andere Werkzeug des Kontos. Damit dem Monitor nichts ausgeht: der Tab Kontingent der Einstellungen, eine GitHub-App (`github_app.enabled`), ein zweites Nur-Lese-Konto für das Lesen (`extra_reader.enabled`, `extra_reader.file`: nur der Pfad der Token-Datei), das zentrale Panel (`central.source`) und der Sparmodus (`modes.auto_low`). Zustand und Zusammenfassung sagen, wann das Kontingent erschöpft ist und wie viel andere Werkzeuge verbrauchen. Siehe [QUOTA_deu.md](QUOTA_deu.md).

## Der aktive Hinweis an eine externe KI (optional, standardmäßig aus)

Neben dem Feed, den eine KI liest (`ALERTS_BRIEF.md`, der Stream, der MCP-Server), kann der Monitor eine externe KI **benachrichtigen**, wenn ein NEUER echter Alarm entsteht. Das ist der Block `ai_notify` der Einstellungen, Reiter *KI*; jeder Schalter darin lässt sich nur von diesem Computer aus ändern:

- `ai_notify.enabled` (aus). Solange er aus ist, wird nichts gesendet.
- **Eine erste Bestätigung pro Anbieter**: Der Anbieter ist der des KI-Blocks (`ai.provider`); es geht nichts hinaus, bis Sie seinen Namen in `ai_notify.confirmed_provider` eintippen. Wechseln Sie den Anbieter, bestätigen Sie erneut. Für den ausgehenden Befehl (unten) tippen Sie `command`.
- **Nur die geschwärzten Felder einer geschlossenen Liste**: Schweregrad, Klasse, Repository, Workflow, Ergebnis, Serie, Ursache, nächster Schritt und der Link, jeweils wie der Feed bereinigt (Tokens, Schlüssel, E-Mail-Adressen, IP-Adressen und persönliche Ordner entfernt). Logs, Diagnosen und alles andere des Alarms bleiben zu Hause.
- **Obergrenzen**: `ai_notify.max_calls_per_hour` (4) und `ai_notify.max_cost_per_hour_cents` mit `ai_notify.cost_per_call_cents` (die Kosten, die Sie angeben, weil der Monitor den Preis Ihres Tarifs nicht kennt). Ein Aufruf wird gezählt, bevor er erfolgt; auch ein fehlschlagender Anbieter verbraucht also die Grenze.
- **Der Schlüssel über den Namen einer Variablen**: Der Monitor liest die in `ai.api_key_env` genannte Variable; der Schlüssel wird nie gespeichert, protokolliert oder irgendwohin außer zum Anbieter gesendet.
- **Die KI führt nie eine Aktion aus**: Ihre Antwort wird gekürzt, ihre Links werden entschärft, und sie wird nur in `ai_notify.jsonl` neben dem Feed geschrieben; nichts davon wird als Befehl gelesen, und die Aktionen des Assistenten (`ai.actions.*`) sind von hier aus nicht erreichbar.
- **Die Variante eines ausgehenden Befehls**: `ai_notify.command` (nur in der Konfigurationsdatei, nie auf der Einstellungsseite) nennt EINE Datei mit absolutem Pfad; sie wird ohne Shell und ohne Argumente gestartet und erhält dasselbe geschwärzte JSON auf der Standardeingabe.

Der Hinweis wird aus einem eigenen Thread gesendet, sodass ein langsamer Anbieter den Zyklus nie aufhält.

## Der Assistent (optional, standardmäßig aus)

Der Reiter Warnungen kann ein Panel mit festen Fragen zeigen, die die bereits konfigurierte KI aus den Daten des Monitors beantwortet: „Diese Warnung erklären“, „Die Lage zusammenfassen“ und „Warum ist es hier langsam“. Er ist aus (`ai.assistant.enabled`) und braucht einen KI-Anbieter (`ai.provider`, standardmäßig keiner). Er liest nur: Er hat vier Werkzeuge (`status`, `alerts`, `runs`, `score`, eine geschlossene Liste, die `ai.assistant.tools` verkleinern kann), höchstens `ai.assistant.max_tool_calls` Lesezugriffe pro Frage, kein Werkzeug, das schreibt oder GitHub erreicht, und keinen freien Chat. Die Antwort zeigt immer ihre Quellen (die gelesenen IDs), wie viel gesendet wurde (`ai.assistant.max_context`) und die Aufrufe des Tages; jeder Aufruf verbraucht das eine Tagesbudget der KI (`ai.daily_limit` und die Budgets je Modell). Was ein Repository geschrieben hat (ein Titel, der Name eines Workflows), wird auf `ai.untrusted_text_max` gekürzt, von Geheimnissen bereinigt und als Daten zwischen Markierungen übergeben, die ein Wort dieser Anfrage tragen, nie als Anweisung. Ein Betrachter darf fragen; jede Frage steht im Aktionsprotokoll (die Aktion, nie der Text). Routen: `GET /api/assistant` (was er ist und seine Grenzen) und `POST /api/assistant/ask` mit `action` (`explain_alert`, `summarize_week` oder `why_slow`) und je nach Aktion `alert` oder `repo`; beide antworten mit 404, solange er aus ist, und existieren in der Lite-Edition nicht.

Mit `ai.similar.enabled` an (standardmäßig aus) listet „Diese Warnung erklären“ auch bis zu `ai.similar.max` ähnliche Warnungen auf, damit die Antwort sagen kann „das ist schon in einem anderen Repository passiert“. Sie werden durch einen einfachen Wortvergleich (Code der Warnung, Workflow, Wörter von Titel und Ursache) unter den offenen und den im Feed gemerkten gelösten Warnungen gefunden: kein Modell, keine Embeddings, nur die Daten dieses Kontos, bei gleichen Daten dieselbe Reihenfolge, und jede wird mit ihrer ID genannt.

Mit `ai.report_summary.enabled` an (standardmäßig aus) bietet Berichte **Mit der KI entwerfen** für die Zusammenfassung des nächsten Berichts: Die Zahlen des Berichts gehen, von Geheimnissen bereinigt, über denselben Bereiniger, dasselbe Budget, denselben Cache und dieselbe Kette wie jede andere Frage an diese KI, eine Person bearbeitet den Entwurf und gibt ihn frei, und der freigegebene Text eröffnet den nächsten Bericht einmal. Ohne diese Freigabe wird nichts geschrieben oder gesendet.

Der Assistent hat fünf feste Fragen, alle nur lesend: „diese Meldung erklären“ (`explain_alert`), „die Lage zusammenfassen“ (`summarize_week`), „warum es hier langsam ist“ (`why_slow`), „die Lage eines Repositorys“ (`explain_repo`: seine Läufe und offenen Meldungen) und „was zuerst zu tun ist“ (`prioritize`: die offenen Meldungen, der Status und die Bewertung, mit den Ids in eine Reihenfolge gebracht). Sie nutzen dieselben vier Werkzeuge, dieselben Grenzen und dasselbe Tagesbudget; einen freien Chat gibt es weiterhin nicht.

## Isolierter Modus der KI (optional, standardmäßig aus)

Mit `ai.airgapped` an spricht die KI nur mit einem Modell auf diesem Computer oder an einer privaten Adresse Ihres eigenen Netzes, die Sie in `ai.airgap_hosts` auflisten (zum Beispiel ein Server mit Ollama oder llama.cpp unter `192.168.1.20`). Jede Internetadresse und jeder Cloud-Dienst, auch die Copilot-CLI, wird abgelehnt, BEVOR eine Verbindung geöffnet wird; es verlässt also kein Socket den Rechner. Die Modellliste, der Test eines Modells, der KI-Doctor, die Ausweichkette, der Assistent und die Zusammenfassungen halten sich daran, und ein Ausweichmodell wechselt nie zu einem Cloud-Modell. Der allgemeine Schalter `airgapped` schaltet ihn ebenfalls ein. Eine öffentliche Adresse wird auch dann abgelehnt, wenn sie in der Liste steht, und die Einstellung lässt sich nur vom Computer des Monitors aus ändern, nie über das Netz. Der KI-Doctor fügt die Prüfung `ai_egress` hinzu, solange der Modus an ist. `ai.redact.extra_terms` listet Wörter von Ihnen (ein Server, ein Projekt), die in jedem Text durch `[hidden]` ersetzt werden, bevor die KI ihn sieht, zusätzlich zu den Geheimnissen, die der Monitor ohnehin verbirgt.

`ai.redact.extra_patterns` (aus, leer) listet eigene Muster für das, was die KI nie sehen darf: eines pro Zeile, jedes beschreibt ein ganzes Wort mit nur drei Platzhaltern, `*` (beliebige Zeichenfolge), `?` (ein Zeichen) und `#` (eine Ziffer), zum Beispiel `deploy-*` oder `*.firmen-name`. Es ist KEIN regulärer Ausdruck: keine Gruppen, Alternativen oder Wiederholungen, ein Muster kann den Monitor also nicht blockieren; ein Muster hat 3 bis 80 Zeichen (mindestens 3 normale, höchstens 4 Sterne), ein Wort wird bis 2000 Zeichen gelesen und jeder Text verbraucht eine feste Zahl von Schritten, danach wird der Rest des Textes verborgen, nie offen gelassen. Die Muster gelten für jeden Text, der ein Modell erreicht, auch für die aktive Meldung, und ergänzen die Geheimnisse, die der Monitor schon verbirgt.

`ai.prompt_log.enabled` (aus) führt ein lokales Protokoll dessen, was die KI gefragt wurde: an, wird jede an das Modell gesendete Frage samt Antwort, bereits von Geheimnissen und Ihren verborgenen Wörtern bereinigt und auf eine feste Größe gekürzt, an `ai_prompts.jsonl` im Ordner der Protokolle angehängt (`GET /api/ai/prompts` zeigt sie einem Administrator, `POST /api/ai/prompts/clear` leert sie). Der System-Prompt wird nicht gespeichert, eine Antwort aus dem Zwischenspeicher nicht geschrieben, ein fehlgeschlagener Aufruf ohne Antwort geschrieben, die neuesten `ai.prompt_log.keep` Zeilen bleiben, und die Datei gehört weder zur Sicherung noch zum Zip noch zu den Dateien, die KI-Werkzeuge lesen.

`config/ai_models.json` ist eine Tabelle, die Sie von Hand führen können (sie existiert erst, wenn Sie sie schreiben): `models` ist eine Liste von Zeilen `{provider, model, context, in_per_mtok, out_per_mtok, tools, daily_limit}` mit den Zahlen, die Ihr Anbieter nicht nennt, und `retired` eine Liste von Modellen, die es nicht mehr gibt (ein Name oder `{model, use, note}`). Eine Zahl aus dieser Datei gilt über dem, was der Anbieter sagte, und unter dem, was Sie auf der Seite eingetragen haben, und die Seite zeigt sie als aus der Datei stammend. Ein als zurückgezogen aufgeführtes Modell wird von der Ausweichkette übersprungen, auch wenn die Live-Liste der Modelle aus ist, und der KI-Doktor fügt die Prüfung `model_retired` mit dem stattdessen zu nutzenden Modell hinzu. Eine falsche Zeile oder Zahl bleibt draußen, sonst ändert sich nichts.

Auf der Einstellungsseite zeigt unter der KI die Karte „Protokoll der Prompts“ die letzten 20 Einträge dieses Protokolls (Zeit, Art, Modell und, beim Öffnen eines Eintrags, Frage und Antwort) und leert es mit einer Schaltfläche; nur ein Administrator an diesem Rechner kann es lesen oder leeren, und die Karte sagt es, wenn das Protokoll aus ist. Die Tabelle der Modelle hat eine Spalte „Herkunft“, die sagt, woher ihre Zahlen stammen: die Seite, die Datei `config/ai_models.json` oder der Anbieter.

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
