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

## API di lettura v1 (disattivata per impostazione predefinita)

- Attiva `api.v1_enabled` (Impostazioni, Avanzate, API di lettura v1). Ogni rotta di lettura è allora servita anche su `/api/v1/` (per esempio `/api/v1/alerts`): la stessa risposta e gli stessi ruoli, più l'intestazione `X-API-Version: 1`. Finché è disattivata, nell'edizione lite e per qualsiasi altro numero di versione, il prefisso risponde 404.
- `/api/v1/me`: chi chiede: `mode` (`individual` o `team`), `authenticated`, `user`, e il `role` e gli `accounts` della sessione di squadra (null senza), i `limits` delle liste e la versione.
- `/api/v1/repos`: i repository che il monitor controlla, una riga ciascuno (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtri `state`, `ecosystem` e `q`; `limit` (per impostazione predefinita `api.default_limit`, al massimo `api.max_limit`); `cursor` (il `next_cursor` della pagina precedente, firmato e valido per `api.cursor_ttl_seconds`); `fields=a,b` o `profile=compact` per righe più corte. La risposta è compressa con gzip quando il client lo accetta.
- `/api/v1/openapi.json`: una descrizione OpenAPI 3 leggera di queste due rotte.
- Le due rotte proprie rispondono un errore come `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` e `code` sono stabili, `message` segue la lingua di `?lang=`. Codici: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tutto è di sola lettura: sotto `/api/v1/` non c'è nessuna scrittura. La forma è congelata nella sezione `v1_endpoints` del contratto e si verifica con `python tools/check_api_contract.py --v1` su un monitor con `api.v1_enabled` attivo.

## Stream

- `GET /api/ai/stream` (gli avvisi) e `GET /api/live-events/stream` (gli eventi del webhook, `live.sse.enabled`) sono eventi inviati dal server, di sola lettura e spenti per impostazione predefinita; vedi [AI_ALERTS_ita.md](AI_ALERTS_ita.md) e [WEBHOOK_ita.md](WEBHOOK_ita.md).
