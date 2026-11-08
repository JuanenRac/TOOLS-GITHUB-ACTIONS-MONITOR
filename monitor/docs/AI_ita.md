<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# L'assistente IA della sentinella

Facoltativo e **spento per impostazione predefinita**. Un modello linguistico può riassumere il rapporto giornaliero, classificare gli avvisi, spiegare un run fallito, abbozzare note di release e rispondere a una domanda su un repository. Tutto ciò che scrive è mostrato come proposta non verificata.

## Provider

- `ollama`: un modello su questo computer (solo `127.0.0.1`; nulla esce dal computer).
- `openai-compatible`: qualsiasi servizio con endpoint di chat in stile OpenAI. Vale anche per Gemini (il suo endpoint compatibile OpenAI) e per OpenAI: imposta `base_url`, `model` e il NOME della variabile che contiene la chiave.
- `anthropic`: l'API Messages di Anthropic (`https://api.anthropic.com`, intestazioni `x-api-key` e `anthropic-version`). Il modello lo scegli tu; nessuno è incorporato.
- `copilot`: `gh copilot` con il tuo accesso GitHub (nessuna chiave nel monitor), solo risposta testuale e senza strumenti. Consuma richieste premium del tuo piano Copilot. Esegui `gh copilot` una volta a mano per installare la CLI.
- La chiave non viene mai salvata: si indica il NOME di una variabile d'ambiente. I tre provider remoti INVIANO dati dei tuoi repository a terzi.


## Cosa può vedere

- Ogni input viene pulito: caratteri di controllo rimossi, segreti oscurati per modello, lunghezza limitata, contenuto tra delimitatori casuali e dichiarato non attendibile. La risposta viene tagliata e i suoi link disinnescati.
- Nella scheda Impostazioni scegli i tipi di evento analizzabili (`build`, `codeql`, `report`), i repository visibili (vuoto = quelli osservati dal monitor), la lingua delle risposte, il limite giornaliero di chiamate e i limiti di dimensione. Un pulsante prova la connessione e la pagina mostra le chiamate di oggi.


## Proporre ed eseguire azioni

- Livello 3 (`ai.actions.enabled`): un comando nella risposta resta solo se corrisponde all'ELENCO CHIUSO: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` e `act -W FILE -j JOB` (quest'ultimo è solo mostrato). Il comando mostrato è ricostruito dai pezzi verificati, mai copiato dal modello; repository e numero di run o issue devono essere già osservati dal monitor.
- Livello 4 (`ai.actions.execute`, interruttore proprio, spento): ogni proposta ha un pulsante di conferma; una finestra mostra il comando intero e nulla viene eseguito finché non accetti. Gira con il tuo `gh`, senza shell, al massimo `ai.actions.max_per_hour` all'ora, ogni tentativo va nel registro locale mostrato dalla pagina, e dopo due errori di fila le azioni si bloccano finché non le sblocchi.
- Fuori dall'elenco, di proposito: eliminare branch, chiudere o fondere pull request, qualsiasi cosa su segreti o impostazioni.
