<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# L'API di lettura v1, passo dopo passo

Una guida per chi scrive un client (uno script, uno schermo a parete, un'app mobile, uno strumento di IA) contro l'API di lettura del monitor. Il riferimento di ogni rotta è il documento OpenAPI che serve il monitor stesso; le regole del contratto (cosa è congelato e cosa può crescere) sono in [API_ita.md](API_ita.md). Ecco il percorso da seguire, con comandi che un test esegue contro un monitor.

## 1. L'API è aperta?

Il prefisso `/api/v1/` risponde da solo quando il monitor gira come servizio (un account della modalità team, l'immagine Docker, l'unità systemd) e resta chiuso, con 404, per una persona su un computer. Lo decide l'impostazione `api.v1_enabled` (`auto`, `on`, `off`). Un client comincia chiedendo chi è: un `404` lì significa che l'API è chiusa, non che il client sbagli.

## 2. Identificarsi

Dallo stesso computer e senza modalità di rete non serve alcun token. In modalità di rete ogni richiesta porta il token di accesso nell'intestazione `X-Monitor-Access`, letto qui da un file perché non compaia mai in una riga di comando conservata nella cronologia; con la modalità team uno script accede a `POST /api/auth/login`. Un token di lettura è tutto ciò che serve a un client di questa API: sotto il prefisso non si scrive.

## 3. I comandi

In quest'ordine: chi sei e la versione del contratto (`/api/v1/me`), la descrizione di ogni rotta congelata (`/api/v1/openapi.json`), i repository a pagine (filtrano `state`, `ecosystem` e `q`; `limit`; `fields` o `profile=compact` per righe più corte; `cursor` è il `next_cursor` della pagina precedente, finché non è `null`), la risposta compressa con gzip e due rotte della vecchia API che il prefisso serve anche con la stessa risposta.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Errori

Un errore delle rotte proprie è un oggetto JSON con tre chiavi: `error` e `code` sono stabili e pensati per i programmi, `message` segue la lingua di `?lang=` ed è pensato per le persone. I codici sono api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile e api.server_error. Ogni risposta del prefisso, errori inclusi, porta l'intestazione `X-API-Version: 1`. Ogni errore porta anche `help`, una frase con il passo successivo e la guida da leggere, nella stessa lingua (il campo manca quando un codice non ne ha; un programma che lo ignora non perde nulla).

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

La risposta, dopo le intestazioni, è `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. Lo stesso dalla riga di comando e da uno strumento di IA

Tre accessi danno gli stessi documenti, e un test li confronta: HTTP come sopra, la riga di comando (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check`; aggiungi `--json` per la risposta come dati) e il server MCP (`python bin/mcp_server.py`, sola lettura: gli strumenti `api_me`, `api_openapi` e `api_contract_check`).

## 6. Controllare un server prima di fidarsene

`python tools/api_contract_suite.py --url URL --token-file token.txt` prende il documento che serve il server come descrizione di cosa controllare e stampa una riga per controllo e `API_CONTRACT=PASS` o `API_CONTRACT=FAIL`. `python tools/check_api_contract.py --v1` esegue la stessa suite e confronta anche le risposte con il contratto congelato. Eseguine uno dopo ogni aggiornamento del monitor o del tuo client; la CI del monitor esegue la suite contro una demo in modalità servizio.
