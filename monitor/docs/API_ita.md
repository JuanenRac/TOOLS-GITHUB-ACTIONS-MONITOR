<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# L'API per i client

Ciò su cui può contare uno script, uno schermo a parete o un client mobile. Dalla 2.0.0 gli endpoint di lettura sono congelati: una chiave del contratto mantiene nome e tipo, possono comparire chiavi nuove e nulla viene tolto o cambiato senza una nuova versione maggiore.

## Chiedere

- In modalità normale l'API risponde su `127.0.0.1` senza accesso. In modalità di rete ogni richiesta porta il token di accesso nell'intestazione `X-Monitor-Access` (o il cookie di sessione, o `POST /api/access` una volta). Con la modalità squadra uno script accede con `POST /api/auth/login`.
- Una parola della query che un endpoint non conosce viene ignorata. Le risposte sono JSON in UTF-8, tranne il riepilogo in Markdown e gli stream.

## Errori

- Un errore è JSON `{"error": "parola"}`, a volte con un `code`. `401 access` significa che il token manca o è errato, `403 forbidden` che la richiesta non viene da dove è consentito (anche un `Host` estraneo), `404` che il percorso non esiste in questa edizione (la lite risponde 404 a ciò che ha solo la completa), `429` che l'indirizzo è bloccato o gli ascoltatori sono pieni.
- Una scrittura rifiutata non cambia mai nulla. Le scritture non fanno parte del contratto.

## Il contratto

- `docs/schemas/api_contract.json` elenca ogni endpoint di lettura con chiavi e tipi in ogni edizione e i codici di errore. Le rotte leggibili ma non congelate (flussi, testo, esportazioni di altri strumenti) sono elencate sotto `unfrozen` nello stesso file, ciascuna con il suo motivo; `/api/data`, che fornisce le esecuzioni, i repository e la quota, è congelata. Le sue chiavi arrivano fino agli elementi delle liste: una lista scritta `[{...}]` nel file descrive i suoi elementi (i primi tre vengono controllati), così le esecuzioni, i repository e la quota di `/api/data`, gli avvisi di `/api/alerts` e `/api/auth/me` non possono cambiare senza che il controllo fallisca.
- `python tools/check_api_contract.py` verifica un monitor in esecuzione (`--lite`, `--url`, `--token-file`) e stampa `CONTRACT=PASS` o `CONTRACT=FAIL`; eseguilo dopo ogni aggiornamento del monitor o del tuo client.

## API di lettura v1 (automatica per impostazione predefinita)

- Imposta `api.v1_enabled` (Impostazioni, Avanzate, API di lettura v1): `auto` (predefinito) risponde quando il monitor gira come servizio (un account della modalità team, l'immagine Docker, l'unità systemd) e resta chiusa per una persona su un solo computer; `on` sempre; `off` mai (i vecchi true e false equivalgono a on e off). Quando risponde, ogni rotta di lettura è servita anche su `/api/v1/` (per esempio `/api/v1/alerts`): la stessa risposta e gli stessi ruoli, più l'intestazione `X-API-Version: 1`. Finché è chiusa, nell'edizione lite e per qualsiasi altro numero di versione, il prefisso risponde 404.
- `/api/v1/me`: chi chiede: `mode` (`individual` o `team`), `authenticated`, `user`, e il `role` e gli `accounts` della sessione di squadra (null senza), ciò che la sessione può fare (`capabilities`: `read`, `write`, `admin` e `v1_write`, sempre falso perché il prefisso è in sola lettura), i `limits` delle liste, la versione del monitor e la versione del contratto (`contract`, `1.0`: cresce a ogni chiave aggiunta e non ne perde mai una).
- `/api/v1/repos`: i repository che il monitor controlla, una riga ciascuno (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtri `state`, `ecosystem` e `q`; `limit` (per impostazione predefinita `api.default_limit`, al massimo `api.max_limit`); `cursor` (il `next_cursor` della pagina precedente, firmato e valido per `api.cursor_ttl_seconds`); `fields=a,b` o `profile=compact` per righe più corte. La risposta è compressa con gzip quando il client lo accetta.
- `/api/v1/openapi.json`: la descrizione OpenAPI 3 di tutta l'API di lettura congelata, costruita dal contratto (`docs/schemas/api_contract.json`) e mai scritta a mano: ogni rotta congelata con le chiavi e i tipi che promette, `x-lite` (cosa risponde l'edizione lite) e `x-local-only`. Le rotte che il contratto non congela sono sperimentali: rispondono 404 su `/api/v1/` e non sono nel documento, a meno che `api.experimental_routes` sia attivo (allora sono elencate con `x-experimental`). Le vecchie rotte su `/api/` non cambiano mai. Scaricalo con `python bin/monitor_cli.py api openapi`.
- Una guida passo dopo passo per chi scrive un client, con i comandi in ordine e gli errori: [API_V1_ita.md](API_V1_ita.md).
- `python tools/api_contract_suite.py` è la suite di contratto per i client esterni (solo la libreria standard, solo lettura): dalle l'indirizzo di un server (`--url`) e un token di lettura (`--token-file`) e prende il documento che il server serve come descrizione di cosa verificare: la forma di ogni rotta senza parametri, l'intestazione `X-API-Version`, la busta di errore e i suoi codici stabili, le pagine e i loro cursori, `fields` e `profile=compact`, gzip e che nulla si possa scrivere sotto il prefisso. Stampa una riga per verifica e `API_CONTRACT=PASS` o `API_CONTRACT=FAIL` (`--json` per un documento); il codice di uscita è 0, 1 o 2 (nulla risponde). `python bin/monitor_cli.py api contract-check` la lancia contro il monitor della riga di comando.
- Le stesse tre cose sono strumenti del server MCP (`python bin/mcp_server.py`, sola lettura, senza opzioni): `api_me` (chi il monitor crede sia il client), `api_openapi` (il documento, o una rotta con `path`) e `api_contract_check` (la suite di contratto, risposta `{ok, checks, failed, rows}`). HTTP, la riga di comando (`api me`, `api openapi`, `api contract-check`) e MCP danno lo stesso documento; un test li confronta. Finché il prefisso è chiuso, gli strumenti lo dicono in una riga.
- Le due rotte proprie rispondono un errore come `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` e `code` sono stabili, `message` segue la lingua di `?lang=`. Codici: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tutto è di sola lettura: sotto `/api/v1/` non c'è nessuna scrittura. La forma è congelata nella sezione `v1_endpoints` del contratto e si verifica con `python tools/check_api_contract.py --v1` su un monitor con `api.v1_enabled` attivo.

### Esempi con curl

Il token è il token di accesso della modalità di rete (oppure usa una sessione della modalità team); senza modalità di rete non serve alcun token dallo stesso computer. Un client segue `next_cursor` finché è `null` e legge prima `/api/v1/me` per conoscere la versione del contratto e ciò che la sessione può fare.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Stream

- `GET /api/ai/stream` (gli avvisi) e `GET /api/live-events/stream` (gli eventi del webhook, `live.sse.enabled`) sono eventi inviati dal server, di sola lettura e spenti per impostazione predefinita; vedi [AI_ALERTS_ita.md](AI_ALERTS_ita.md) e [WEBHOOK_ita.md](WEBHOOK_ita.md).
- `POST /api/chatops/slack` e `POST /api/chatops/discord` ricevono i comandi di sola lettura di una chat (disattivati per impostazione predefinita, `chatops.enabled`). Non usano il token di accesso: la prova è la firma della piattaforma, e una richiesta senza firma valida viene rifiutata prima di leggere qualsiasi cosa. Vedi [CHATOPS_ita.md](CHATOPS_ita.md).

## Altre route della pagina

Queste route servono la pagina e gli strumenti di questo computer. Non fanno parte del contratto congelato e possono cambiare tra le versioni. POST cambia qualcosa; "questo computer" significa che solo il computer che esegue il monitor può usarla.

| Route | Cosa fa |
| --- | --- |
| `/api/about` | Il pannello Informazioni: versioni, collegamenti, file, salute, crediti e l'avviso di un aggiornamento; nessun segreto. |
| `/api/act/plan` | POST, questo computer. Prepara ciò che farebbe un'esecuzione locale con `act`; ancora non gira nulla. |
| `/api/act/confirm` | POST, questo computer. Esegue un workflow su questo computer con `act` dopo il piano; l'esecuzione viene registrata. |
| `/api/act/status` | Lo stato dell'esecuzione locale in corso. |
| `/api/act/stop` | POST, questo computer. Ferma l'esecuzione locale. |
| `/api/advanced` | Lo stato delle funzioni che si attivano per scelta: la rete, l'archivio del token di GitHub, le azioni su GitHub, l'esecuzione locale e la modalità demo; mai un token. |
| `/api/ai/actions` | Lo stato delle azioni dell'IA (bloccate o no), il loro registro, le proposte in attesa (`proposals`) e lo stato dell'IA. |
| `/api/ai/actions/confirm` | POST, questo computer. Esegue un'azione proposta dall'IA, dopo la tua conferma; viene registrata. |
| `/api/ai/actions/review` | POST, questo computer. Approva o rifiuta una proposta dell'IA (`id`, `decision`); viene registrato. Non viene eseguito nulla. |
| `/api/ai/actions/unlock` | POST, questo computer. Sblocca le azioni dell'IA per un tempo limitato; viene registrato. |
| `/api/ai/budget` | Le chiamate e il costo stimato di oggi per ogni modello di IA, i limiti e gli ultimi guasti; non interroga alcun fornitore. |
| `/api/ai/test` | POST, questo computer. Verifica la connessione dell'IA configurata; non cambia nulla. |
| `/api/alerts/unmute` | POST. Toglie il silenzio di un avviso; viene registrato. |
| `/api/analytics` | Il riepilogo dell'analisi delle esecuzioni: durate, coda, passaggi, test instabili ed esecuzioni più lente. |
| `/api/discovery` | Cosa ha trovato la scoperta: il riquadro con l'account e i repository mostrati e nascosti, gli ultimi eventi, i gruppi suggeriti, le sue impostazioni, i fork e le organizzazioni. |
| `/api/discovery/group` | POST. Aggiunge un gruppo suggerito al file degli ecosistemi, conservando una copia del file. |
| `/api/gh-action/plan` | POST, questo computer. Prepara ciò che verrebbe inviato a GitHub (una riesecuzione, un annullamento, un dispatch o un merge); ancora non si invia nulla. |
| `/api/gh-action/confirm` | POST, questo computer. Invia a GitHub ciò che diceva il piano, dopo la tua conferma; viene registrato. Se GitHub rifiuta, la risposta porta `reason`: forbidden, not_found, method, conflict o invalid. |
| `/api/github-token` | Solo questo computer. Lo stato dell'archivio del token di GitHub (il sistema e se ce n'è uno salvato); mai il suo valore. |
| `/api/help/search` | Cerca una parola negli argomenti di aiuto e restituisce quelli che corrispondono. |
| `/api/help/topic` | Il testo di un argomento di aiuto (`id=`) nella lingua della pagina. |
| `/api/help/topics` | L'elenco degli argomenti di aiuto con i loro titoli. |
| `/api/hot-only` | POST, questo computer. L'interruttore "solo ciò che scotta" della pagina; non cambia alcuno stato salvato. |
| `/api/mirror` | Lo stato dello specchio dei repository (spento per impostazione predefinita). |
| `/api/mode` | GET: la modalità di lavoro, la stima di ogni modalità e il tempo rimasto. POST, questo computer: cambia la modalità. |
| `/api/notify/test` | POST. Invia un messaggio di prova a un canale di notifica; non cambia nulla. |
| `/api/quota-pool/status` | Solo questo computer. La quota di ogni fonte di letture e ciò che manca alla GitHub App; mai una chiave né un token. |
| `/api/refresh-repos` | POST, questo computer. Aggiorna solo i repository indicati e riscrive il file di quelli rossi (lo usa `finalize --execute`). |
| `/api/screens/logo` | GET: il logo dell'organizzazione come immagine. POST: ne salva uno nuovo (al massimo 1 MB, controllato dal suo tipo reale). |
| `/api/screens/logo/remove` | POST. Rimuove il logo dell'organizzazione; viene registrato. |
| `/api/sentinel/ai` | POST. Chiede all'IA di spiegare un avviso o una build; la richiesta è piccola e la domanda viene prima ripulita dai segreti. Non esiste finché l'IA è spenta. |
| `/api/sentinel/historial` | Ieri contro oggi: i rossi e le firme in attesa che compaiono o scompaiono. |
| `/api/sentinel/parte/save` | POST. Salva una copia del rapporto giornaliero nella cartella di audit; un GET non scrive mai. |
| `/api/sentinel/security` | Ciò che GitHub dice di aperto o mancante sulla sicurezza (la sentinella Sicurezza; spenta per impostazione predefinita; sola lettura). |
| `/api/session-token` | Un token monouso per la prossima modifica di un'impostazione; la pagina lo chiede subito prima di scrivere. |
| `/api/statusbar` | Ciò che mostra la barra a piè di pagina: edizione, indirizzo, account e sentinelle; nessun segreto e nessuna chiamata a GitHub. |
| `/api/welcome` | GET: se la guida del primo avvio è completata. POST, questo computer: la segna come completata o no. |
