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

- `docs/schemas/api_contract.json` elenca ogni endpoint di lettura con chiavi e tipi in ogni edizione e i codici di errore. Le rotte leggibili ma non congelate (flussi, testo, esportazioni di altri strumenti) sono elencate sotto `unfrozen` nello stesso file, ciascuna con il suo motivo; `/api/data`, che fornisce le esecuzioni, i repository e la quota, è congelata.
- `python tools/check_api_contract.py` verifica un monitor in esecuzione (`--lite`, `--url`, `--token-file`) e stampa `CONTRACT=PASS` o `CONTRACT=FAIL`; eseguilo dopo ogni aggiornamento del monitor o del tuo client.

## Stream

- `GET /api/ai/stream` (gli avvisi) e `GET /api/live-events/stream` (gli eventi del webhook, `live.sse.enabled`) sono eventi inviati dal server, di sola lettura e spenti per impostazione predefinita; vedi [AI_ALERTS_ita.md](AI_ALERTS_ita.md) e [WEBHOOK_ita.md](WEBHOOK_ita.md).
