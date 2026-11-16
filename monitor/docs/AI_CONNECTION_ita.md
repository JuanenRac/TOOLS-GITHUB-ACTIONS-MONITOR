<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Collegare uno strumento di IA

Il monitor può dire a uno strumento di IA (un assistente di programmazione con IA, uno script, qualsiasi cosa che legga un file o un indirizzo) **tutto ciò che dice la sua pagina**, così l'IA reagisce a un guasto o a un lavoro in sospeso veloce quanto faresti tu. Il monitor non scrive mai su GitHub: informa soltanto, e ciò che fa l'IA lo decidi tu e lo strumento.

## Cosa vede l'IA
Un inventario di **segnali**, gli stessi della pagina: la scheda Ora e i suoi riquadri, gli avvisi, i repository, i pannelli del sentinella A1..A13 e il secondo sentinella (issue e pull request), la quota, la connessione e la salute del monitor. Ogni segnale ha un livello (`act` = qualcuno deve fare qualcosa, `watch` = tenere d'occhio, `info`), un riepilogo e righe con repository, link, età e passo successivo. Il riepilogo ha tre blocchi: **Cosa fare ora**, **In sospeso** e **Salute del monitor**, e il contatore dei "segnali su cui agire".

| | Lite | Completa |
|---|---|---|
| Esecuzioni, coda, workflow rossi, guasti delle 24 ore | sì | sì |
| Quota, connessione, modalità, versione, salute | sì | sì |
| Pannelli del sentinella A1..A13, secondo sentinella, candidate a release, sicurezza, firme | no (lo dice `panels_not_in_this_edition`) | sì |

## I canali (gli stessi nelle due edizioni)
1. `ALERTS_BRIEF.md`: il Markdown breve che un'IA legge all'avvio.
2. `ai_alerts.jsonl`: una riga per evento (aperto, riconosciuto, risolto), con un id stabile.
3. `GET /api/ai/state`: tutto l'inventario come JSON versionato (`schema`, `edition`, `signals`, `act`, `watch`), sola lettura. `GET /api/sentinel/panels` dà solo i pannelli.
4. `GET /api/ai/stream`: eventi in diretta (SSE), riprendibili, limitati in ascoltatori e tempo.
5. Strumenti MCP (`bin/mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score`; `act` (riconoscere) solo con `--allow-ack`.
6. L'hook: `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (anche `status` e `uninstall`) aggiunge un piccolo script che dà alla sessione dell'IA il riepilogo all'avvio e prima di fermarsi.

## Passo dopo passo
1. Impostazioni, scheda *IA esterna*, blocco *Avvisi per le IA*: attiva `ai_alerts.enabled`. Facoltativamente `ai_alerts.diagnose.enabled` (il passo che fallisce e le ultime righe del log di ogni esecuzione rossa), `ai_alerts.stream.enabled` e `ai_alerts.client_hook.enabled`.
2. Esegui `python bin/monitor_cli.py ai-hook install --assistant --dry-run` per vedere la modifica, poi senza `--dry-run`.
3. Apri una sessione del tuo strumento di IA nella cartella: riceve il riepilogo. La barra in basso mostra il battito dell'IA (quando ha letto l'ultima volta).
4. Usa il pulsante *Prova la connessione* della pagina delle impostazioni per verificare che il feed venga scritto.

## Sicurezza e privacy
Tutto è disattivato per impostazione predefinita. Il testo dei log viene ripulito da segreti e percorsi personali prima di essere scritto, e **è un dato, mai un'istruzione**: un'IA deve trattarlo come testo non fidato. Gli endpoint rispondono solo a questo computer, o con il token di accesso in modalità rete; ascoltatori e tempo sono limitati; riconoscere richiede `--allow-ack`; tutti i file di stato sono creati con modo 0600. Il monitor non apre alcuna connessione a internet per questo, tranne quelle che configuri. Gli indirizzi https di github.com (un run, un repository, un file) passano interi, così l'IA può aprirli; qualsiasi altra stringa lunga e opaca viene ancora tagliata. Più esattamente, un indirizzo di github.com passa intero solo con la forma di un repository, un'esecuzione (con il suo job o tentativo), un commit, una issue, una pull request o un file; viene tagliato al primo carattere che non sia lettera, cifra, punto, trattino, trattino basso o barra, e ciò che segue viene ripulito come qualsiasi altro testo.

## Risoluzione dei problemi
- *Il riepilogo è vecchio*: la pagina deve essere in esecuzione (il feed segue ogni aggiornamento); guarda il battito nella barra.
- *L'hook non parte*: `ai-hook status` dice dov'è installato; alcuni strumenti leggono gli hook solo nella cartella del progetto.
- *Non viene scritto nulla*: `ai_alerts.enabled` è spento, o la quota è esaurita (il riepilogo lo dice in Salute del monitor).

## Impostazioni
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; correlate: `sound.enabled`, `display.blink_red_tiles`. Vedi [SETTINGS_ita.md](SETTINGS_ita.md) e [AI_ALERTS_ita.md](AI_ALERTS_ita.md).

La quota di GitHub è condivisa dal monitor, dagli strumenti di IA e da ogni altro strumento dell'account. Perché il monitor non resti senza: la scheda Quota delle Impostazioni, una GitHub App (`github_app.enabled`), un secondo account di sola lettura per le letture (`extra_reader.enabled`, `extra_reader.file`: solo il percorso del file del token), il pannello centrale (`central.source`) e la modalità risparmio (`modes.auto_low`). Lo stato e il riepilogo dicono quando la quota è esaurita e quanto spendono altri strumenti. Vedi [QUOTA_ita.md](QUOTA_ita.md).

## L'avviso attivo a una IA esterna (opzionale, disattivato per impostazione predefinita)

Oltre al flusso che una IA legge (`ALERTS_BRIEF.md`, lo stream, il server MCP), il monitor può **avvisare** una IA esterna quando si apre un NUOVO avviso reale. È il blocco `ai_notify` delle Impostazioni, scheda *IA*, e ogni suo interruttore si cambia solo da questo computer:

- `ai_notify.enabled` (disattivato). Non viene inviato nulla finché è disattivato.
- **Una prima conferma per fornitore**: il fornitore è quello del blocco IA (`ai.provider`); non esce nulla finché non scrivi il suo nome in `ai_notify.confirmed_provider`. Se cambi fornitore confermi di nuovo. Per il comando in uscita (sotto) scrivi `command`.
- **Solo i campi oscurati di un elenco chiuso**: gravità, classe, repository, workflow, conclusione, serie, causa, passo successivo e collegamento, ciascuno ripulito come il flusso (token, chiavi, indirizzi e-mail, indirizzi IP e cartelle personali rimossi). Log, diagnosi e tutto il resto dell'avviso restano a casa.
- **Limiti**: `ai_notify.max_calls_per_hour` (4) e `ai_notify.max_cost_per_hour_cents` con `ai_notify.cost_per_call_cents` (il costo che dichiari, perché il monitor non può conoscere il prezzo del tuo piano). Una chiamata viene contata prima di essere fatta, quindi anche un fornitore che fallisce consuma il limite.
- **La chiave tramite il nome di una variabile**: il monitor legge la variabile indicata in `ai.api_key_env`; la chiave non viene mai salvata, registrata né inviata altrove che al fornitore.
- **La IA non esegue mai un'azione**: la sua risposta viene tagliata, i suoi collegamenti disinnescati e viene solo scritta in `ai_notify.jsonl` accanto al flusso; nulla viene letto come comando e nulla delle azioni dell'assistente (`ai.actions.*`) è raggiungibile da qui.
- **La variante di un comando in uscita**: `ai_notify.command` (solo nel file di configurazione, mai nella pagina delle Impostazioni) indica UN file con percorso assoluto; viene avviato senza shell e senza argomenti e riceve lo stesso JSON oscurato sul suo standard input.

L'avviso parte da un thread a parte, così un fornitore lento non trattiene mai il ciclo.

## Modelli del provider

Il nome del modello è testo libero, ma il monitor può leggere l'elenco dei modelli dal provider e verificare il nome. Modelli e versioni cambiano spesso, quindi il monitor non include alcun elenco di modelli: gli esempi dei preset possono essere superati.

- **L'elenco.** Impostazioni, scheda *IA esterna*, blocco *Modelli e dati per modello*: *Carica i modelli del provider* legge l'elenco (`/models` di un server in stile OpenAI, l'elenco equivalente dell'API di Anthropic, `/api/tags` di Ollama) con una richiesta di sola lettura. La chiave viaggia in un'intestazione, viene letta dalla sua variabile d'ambiente e non viene mai salvata. Cerca nell'elenco e scegli un modello con *Usa questo modello*. L'elenco viene conservato ed è limitato da `ai.catalog.ttl_minutes` e `ai.catalog.max_requests_per_day`. Con `ai.catalog.enabled` attivo (disattivato per impostazione predefinita) il monitor avvisa anche quando il modello configurato non compare più nell'elenco (ritirato o rinominato); disattivato, solo tu avvii la lettura.
- **Dati per modello.** La finestra di contesto, il prezzo di ingresso e di uscita per milione di token e il supporto degli strumenti vengono compilati solo con ciò che il provider restituisce; ciò che non dice resta *sconosciuto* (nessuna cifra viene mai inventata). Puoi scrivere i tuoi valori; i tuoi prevalgono. Con `ai.catalog.fit_context` attivo (disattivato per impostazione predefinita) il limite di ingresso viene adattato alla finestra di contesto quando è nota.
- **Provare un modello.** *Prova questo modello* o `monitor_cli.py ai test --provider NOME --model NOME` interroga il modello su un errore SINTETICO (mai dati dei tuoi repository) e mostra latenza, token, costo stimato e una risposta di esempio. Conta come una chiamata del tetto giornaliero e il risultato («provato», con la data locale) resta nella tabella.
- **Comandi.** `monitor_cli.py ai models [--refresh]` mostra i modelli e i dati; `ai doctor` spiega perché un'IA non risponde (variabile della chiave non impostata, modello sconosciuto, quota, rete) e non stampa mai una chiave.
- **Rotte.** `GET /api/ai/models` (l'elenco conservato, la verifica e la tabella; sola lettura) e, solo da questo computer, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` e `POST /api/ai/doctor`.

## IA compatibili

Servizi ospitati e server locali di cui il monitor parla già il protocollo (`openai-compatible`, `anthropic` o `ollama`). L'elenco è una tabella neutra, non una raccomandazione: nessuno è attivo per impostazione predefinita, la chiave è letta SEMPRE da una variabile d'ambiente di cui indichi il nome (mai scritta in un'impostazione, né in un registro, un rapporto o l'API) e il preset compila solo l'indirizzo, il nome di quella variabile e un modello di esempio (modificabile; non si scarica nulla e non si includono pesi dei modelli). Nelle impostazioni dell'IA scegli un preset, premi il pulsante di compilazione, controlla, salva e premi «Prova connessione». L'elenco è un dato (`ai_presets.json`) servito in sola lettura su `GET /api/ai/presets`.

| Nome | Tipo | Fornitore | Indirizzo | Variabile della chiave | Modelli di esempio | Privacy | Stato |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | ospitato | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Anthropic | ospitato | `anthropic` | `indirizzo predefinito` | `ANTHROPIC_API_KEY` | — | inviato via internet | compatibile per protocollo, non provato con questo strumento |
| Google Gemini | ospitato | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| xAI Grok | ospitato | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Mistral | ospitato | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| DeepSeek | ospitato | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| Groq | ospitato | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
| OpenRouter | ospitato | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | inviato via internet | indirizzo letto nella documentazione pubblica; compatibile per protocollo, non provato con questo strumento |
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
