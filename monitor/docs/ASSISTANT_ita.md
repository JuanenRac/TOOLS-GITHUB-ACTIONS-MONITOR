<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# L'assistente

Domande fisse all'IA che hai già configurato, con risposte dai dati del monitor, in sola lettura. Spento per impostazione predefinita.

## Accenderlo

1. Configura un fornitore di IA (`ai.provider`; vedi [AI_CONNECTION_ita.md](AI_CONNECTION_ita.md)).
2. In Impostazioni, IA, attiva `ai.assistant.enabled`. Il pannello compare nella scheda Avvisi. Non esiste nell'edizione Lite.
3. Fai una domanda; la risposta mostra le sue fonti, quanto è stato inviato e le chiamate del giorno.

## Le cinque domande

- `explain_alert`: perché un avviso è aperto (serve l'avviso).
- `summarize_week`: la situazione dell'account.
- `why_slow`: perché la CI di un repository è lenta o bloccata (serve il repository).
- `explain_repo`: la situazione di un repository, le sue esecuzioni e i suoi avvisi aperti.
- `prioritize`: gli avvisi aperti, lo stato e il punteggio messi in ordine, con i loro id.

Non c'è una chat libera.

## Cosa legge

Quattro strumenti, un elenco chiuso che `ai.assistant.tools` può restringere: `status`, `alerts`, `runs` e `score`. Al massimo `ai.assistant.max_tool_calls` letture per domanda e `ai.assistant.max_context` di testo inviato. Con `ai.similar.enabled` attivo, «spiega questo avviso» elenca anche avvisi simili, trovati confrontando parole, senza modello.

## Cosa non fa mai

Non scrive nulla e non tocca nulla su GitHub. Ciò che un repository ha scritto (un titolo, il nome di un workflow) viene tagliato, ripulito dai segreti e dalle parole che hai nascosto, e consegnato come dato tra segni, mai come istruzione. Ogni domanda spende l'unico budget giornaliero dell'IA (`ai.daily_limit`). Con `ai.airgapped` si usa solo un modello di questo computer o della tua rete privata.

## Verificarlo

`GET /api/assistant` dice cos'è e i suoi limiti; `POST /api/assistant/ask` prende `action` e, secondo il caso, `alert` o `repo`. Entrambe rispondono 404 finché è spento. La domanda finisce nel registro delle azioni (mai il testo); con `ai.prompt_log.enabled` i prompt ripuliti si conservano in un registro locale che puoi vedere e svuotare in Impostazioni.
