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

## IA compatibili

Servizi ospitati e server locali di cui il monitor parla già il protocollo (`openai-compatible`, `anthropic` o `ollama`). L'elenco è una tabella neutra, non una raccomandazione: nessuno è attivo per impostazione predefinita, la chiave è letta SEMPRE da una variabile d'ambiente di cui indichi il nome (mai scritta in un'impostazione, né in un registro, un rapporto o l'API) e il preset compila solo l'indirizzo, il nome di quella variabile e un modello di esempio (modificabile; non si scarica nulla e non si includono pesi dei modelli). Nelle impostazioni dell'IA scegli un preset, premi il pulsante di compilazione, controlla, salva e premi «Prova connessione». L'elenco è un dato (`ai_presets.json`) servito in sola lettura su `GET /api/ai/presets`.

| Nome | Tipo | Fornitore | Indirizzo | Variabile della chiave | Modelli di esempio | Privacy | Stato |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | ospitato | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Anthropic | ospitato | `anthropic` | `indirizzo predefinito` | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Google Gemini | ospitato | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| xAI Grok | ospitato | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Mistral | ospitato | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| DeepSeek | ospitato | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-chat` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Groq | ospitato | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| OpenRouter | ospitato | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Together AI | ospitato | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Fireworks AI | ospitato | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Perplexity | ospitato | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Cohere | ospitato | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Ollama | locale | `ollama` | `http://127.0.0.1:11434` | nessuna (server locale) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
| LM Studio | locale | `openai-compatible` | `http://127.0.0.1:1234/v1` | nessuna (server locale) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
| llama.cpp server | locale | `openai-compatible` | `http://127.0.0.1:8080/v1` | nessuna (server locale) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
| vLLM | locale | `openai-compatible` | `http://127.0.0.1:8000/v1` | nessuna (server locale) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
| LocalAI | locale | `openai-compatible` | `http://127.0.0.1:8081/v1` | nessuna (server locale) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
| Jan | locale | `openai-compatible` | `http://127.0.0.1:1337/v1` | nessuna (server locale) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | resta su questo computer | compatibile per protocollo, non provato con questo strumento |
