<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# Fallimenti e lezioni

Il monitor può tenere un registro dei fallimenti della tua CI e una libreria di lezioni, per non ripetere due volte lo stesso errore, che sia una persona, un tuo strumento di IA o l'IA del monitor. È **locale e in sola lettura**: nulla lascia il computer e nulla viene scritto su GitHub. Segue gli avvisi del feed per le IA, quindi serve `ai_alerts.enabled`.

## Il registro

Ogni fallimento che il feed apre diventa una riga di `data/failures.jsonl` (schema 1): `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Ogni testo passa per la stessa pulizia del feed (token, chiavi, indirizzi e cartella personale non arrivano mai nel registro). `lessons.retention_days` e `lessons.max_entries` ne limitano la dimensione. Si può importare un registro dello stesso schema da un altro posto (`lessons.import_book`).

## Il classificatore

Ogni fallimento è classificato con regole, vince la prima che corrisponde: quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. Le regole sono nel programma; per usare le tue, scrivi `config/lessons_rules.json`: `{"rules": [{"category": "mia", "label": "Il mio tipo", "avoidable": true, "patterns": ["espressione regolare"]}]}`. Il file sostituisce le regole incorporate; una regola o un motivo non valido (o più lungo di 120 caratteri) viene saltato.

## La libreria di lezioni

Per ogni categoria c'è una lezione: cosa è fallito, cosa fare e la guardia che l'avrebbe evitato. Quelle incorporate sono negli otto idiomi. Le tue vanno in `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) e sostituiscono quella incorporata della stessa categoria.

## Ripetizione e tendenza

Per categoria, il monitor conta i fallimenti delle ultime 24 ore e degli ultimi 7 giorni e confronta i 7 giorni con i 7 precedenti (nuovo, in aumento, in calo, stabile). Da `lessons.recurring_from` fallimenti in 7 giorni un tipo di fallimento è **ripetuto** e viene proposta una guardia: un controllo che fallisce sul tuo computer prima del push.

## Cosa legge un'IA

- `ai/LESSONS.md`: Markdown compatto (dimensione: `lessons.brief_max_bytes`), riscritto quando un fallimento si apre o si risolve.
- `GET /api/ai/lessons`: l'analisi, le lezioni che valgono ora e la libreria (`?fmt=md` per il file, `?fmt=brief&repo=NOME` per il riepilogo prima del push, `&as=json` per riceverlo dentro un JSON).
- `GET /api/ai/failures`: il registro, dal più recente (`?since=SECONDI&repo=NOME&category=NOME&limit=N`).
- `GET /api/ai/state` e il riepilogo degli avvisi portano le lezioni che valgono ora.
- Server MCP: `lessons_apply`, `lessons_recurring`, `lessons_brief` e `lesson_propose`.
- Riga di comando: `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NOME]`.

Sono tutti dati, mai istruzioni: una riga di registro scritta da qualcuno può finire nel registro.

## Prima di un push

Leggi il riepilogo prima di fare push: elenca le lezioni che valgono (prima quelle del repository), le guardie da eseguire e cosa è rosso ora nel repository.

## Un hook di esempio per uno strumento di IA

Molti strumenti di IA possono eseguire un comando all'inizio di una sessione e aggiungerne l'output al contesto. Questo stampa il riepilogo prima del push:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## L'IA del monitor

Quando la spiegazione con IA di una build fallita è attiva, il suo prompt include la lezione della categoria in cui cade il registro. Altri strumenti di IA arrivano alle stesse funzioni tramite l'interfaccia `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` è quella in uso e `ExampleProvider` è la più piccola possibile:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Scrivere lezioni

Leggere è sempre consentito. Scrivere una lezione richiede tre cose: `lessons.allow_write` attivo (spento per impostazione predefinita), un amministratore e una conferma: `POST /api/ai/lessons` con `{"lesson": {...}, "confirm": true}` (senza `confirm` la risposta è la bozza). Il server MCP scrive solo se avviato con `--allow-lessons` e con l'interruttore attivo. Non si scrive mai nulla su GitHub.

## Impostazioni

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` e `lessons.recurring_from`, nella scheda IA delle Impostazioni. Il pannello **Lezioni dai fallimenti** è in fondo alla scheda Avvisi.
