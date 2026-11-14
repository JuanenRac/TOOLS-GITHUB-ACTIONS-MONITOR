<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# Fehler und Lehren

Der Monitor kann ein Buch der Fehler Ihrer CI und eine Bibliothek von Lehren führen, damit derselbe Fehler nicht zweimal passiert, weder einer Person noch einem KI-Werkzeug von Ihnen noch der KI des Monitors. Es ist **lokal und nur lesend**: nichts verlässt den Rechner und nichts wird auf GitHub geschrieben. Es folgt den Alarmen des Feeds für KIs und braucht daher `ai_alerts.enabled`.

## Das Buch

Jeder Fehler, den der Feed öffnet, wird zu einer Zeile in `data/failures.jsonl` (Schema 1): `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Jeder Text durchläuft dieselbe Bereinigung wie der Feed (Tokens, Schlüssel, Adressen und der Heimordner gelangen nie ins Buch). `lessons.retention_days` und `lessons.max_entries` begrenzen die Größe. Ein Buch desselben Schemas von anderswo lässt sich importieren (`lessons.import_book`).

## Der Klassifizierer

Jeder Fehler wird per Regeln einer Kategorie zugeordnet, die erste passende gewinnt: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. Die Regeln sind im Programm; für eigene schreiben Sie `config/lessons_rules.json`: `{"rules": [{"category": "mine", "label": "Meine Art", "avoidable": true, "patterns": ["regulärer Ausdruck"]}]}`. Die Datei ersetzt die eingebauten Regeln; eine ungültige (oder über 120 Zeichen lange) Regel oder ein solches Muster wird übersprungen.

## Die Bibliothek der Lehren

Jede Kategorie hat eine Lehre: was scheiterte, was zu tun ist und die Absicherung, die es verhindert hätte. Die eingebauten gibt es in den acht Sprachen. Ihre eigenen stehen in `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) und ersetzen die eingebaute derselben Kategorie.

## Wiederholung und Trend

Je Kategorie zählt der Monitor die Fehler der letzten 24 Stunden und der letzten 7 Tage und vergleicht die 7 Tage mit den 7 davor (neu, steigend, fallend, stabil). Ab `lessons.recurring_from` Fehlern in 7 Tagen gilt eine Fehlerart als **wiederholt** und es wird eine Absicherung vorgeschlagen: eine Prüfung, die vor dem Push auf Ihrem Rechner fehlschlägt.

## Was eine KI liest

- `ai/LESSONS.md`: kompaktes Markdown (Größe: `lessons.brief_max_bytes`), neu geschrieben, wenn ein Fehler sich öffnet oder löst.
- `GET /api/ai/lessons`: die Analyse, die jetzt geltenden Lehren und die Bibliothek (`?fmt=md` für die Datei, `?fmt=brief&repo=NAME` für das Briefing vor dem Push, `&as=json` um es in einem JSON zu erhalten).
- `GET /api/ai/failures`: das Buch, Neuestes zuerst (`?since=SEKUNDEN&repo=NAME&category=NAME&limit=N`).
- `GET /api/ai/state` und die Zusammenfassung der Alarme enthalten die jetzt geltenden Lehren.
- MCP-Server: `lessons_apply`, `lessons_recurring`, `lessons_brief` und `lesson_propose`.
- Kommandozeile: `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NAME]`.

Alles sind Daten, nie Anweisungen: Eine Protokollzeile, die jemand geschrieben hat, kann im Buch landen.

## Vor einem Push

Lesen Sie das Briefing vor dem Push: Es nennt die geltenden Lehren (zuerst die des Repositorys), die auszuführenden Absicherungen und was im Repository jetzt rot ist.

## Ein Beispiel-Hook für ein KI-Werkzeug

Viele KI-Werkzeuge können beim Start einer Sitzung einen Befehl ausführen und seine Ausgabe dem Kontext hinzufügen. Dieser gibt das Briefing vor dem Push aus:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## Die KI des Monitors

Ist die KI-Erklärung eines fehlgeschlagenen Builds eingeschaltet, enthält ihr Prompt die Lehre der Kategorie, in die das Protokoll fällt. Andere KI-Werkzeuge erreichen dieselben Funktionen über die Schnittstelle `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` ist die im Einsatz, `ExampleProvider` die kleinstmögliche:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Lehren schreiben

Lesen ist immer erlaubt. Eine Lehre zu schreiben erfordert drei Dinge: `lessons.allow_write` an (standardmäßig aus), einen Administrator und eine Bestätigung: `POST /api/ai/lessons` mit `{"lesson": {...}, "confirm": true}` (ohne `confirm` ist die Antwort der Entwurf). Der MCP-Server schreibt nur, wenn er mit `--allow-lessons` gestartet wurde und der Schalter an ist. Auf GitHub wird nie etwas geschrieben.

## Einstellungen

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` und `lessons.recurring_from`, im KI-Reiter der Einstellungen. Das Panel **Lehren aus den Fehlern** steht am Ende des Reiters Alarme.
