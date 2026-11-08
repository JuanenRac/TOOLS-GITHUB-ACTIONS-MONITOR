<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Avvisi per le IA

Un workflow rosso non serve a nulla se nessuno di chi lavora sul repository lo viene a sapere. Il monitor scrive un piccolo feed che qualsiasi strumento IA (Codex, Gemini CLI, Copilot) o script può leggere.

## Cosa scrive (locale, sola lettura, senza rete)
- `ai_alerts.jsonl`: una riga per evento (aperto, confermato, risolto) con id stabile, gravità, repository, workflow, esito, da quando, serie, link, una causa probabile (**reale** o **transitoria**), un'azione suggerita e lo stato.
- `ALERTS_BRIEF.md`: riscritto a ogni ciclo e breve (`ai_alerts.brief_max_bytes`, 2 KB di default). Gli avvisi reali vengono per primi.
- Le cause transitorie (502/503/504, timeout, limiti di frequenza, errori di download, un'esecuzione mai partita) si distinguono dai guasti reali con regole modificabili in `ai_alerts.transient_patterns`. Un avviso si risolve da solo quando il workflow torna verde e puoi confermarlo (`ack`), cosa che cambia solo questo stato locale.
- Tutto passa prima da un ripulitore: token, chiavi, indirizzi e-mail, indirizzi IP e la tua cartella personale non arrivano mai ai file, agli endpoint o all'hook.
- La cartella è `ai_alerts.folder` (di default accanto al monitor); scegline una letta dalle tue sessioni IA. `ci_red.json` porta un `ai_hint` opzionale (classe, causa, azione) in ogni workflow rosso.

## Come lo legge un'IA
- Metti questo nelle istruzioni del progetto o della skill: *«All'inizio leggi ALERTS_BRIEF.md (percorso) e dì quali avvisi reali sono aperti.»*
- Oppure interroga il monitor in esecuzione: `GET /api/ai/brief` (Markdown, o `?fmt=json`) e `GET /api/ai/alerts?since=SECONDI`. Valgono le stesse regole del resto della pagina (questo computer; con la modalità rete, il token di accesso).
- Oppure aggiungi il server MCP (sola lettura): `python mcp_server.py`, strumenti `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`; `--allow-ack` aggiunge `ack_alert` (solo stato locale). Gemini CLI, Codex e VS Code (Copilot): aggiungi lo stesso comando come server stdio nelle impostazioni MCP.

## Avvisi che ti raggiungono
- Un NUOVO avviso reale va ai canali di notifica che hai già configurato (Impostazioni > Notifiche).
- Opzionale, spento di default: `ai_alerts.hook` invia in POST il nuovo avviso reale (elenco chiuso di campi ripuliti) a un indirizzo di questo computer, al massimo `max_per_hour` volte all'ora, così un tuo script può svegliare una sessione IA.
- Nulla di tutto ciò invia dati a un fornitore di IA, esegue un comando o scrive su GitHub.

## Il server MCP è locale

`mcp_server.py` parla JSON su ingresso e uscita standard con lo strumento di IA che lo avvia: non ha porta di rete e non va mai messo dietro una porta. Un messaggio malformato riceve un errore solo per quel messaggio, una riga oltre 64 KB viene rifiutata, e `ack_alert` (solo con `--allow-ack`) cambia soltanto lo stato locale del feed. Il feed può contenere nomi di repository e brevi messaggi di errore della CI; tutto viene ripulito da token, chiavi, e-mail, indirizzi IP e dalla cartella di una persona prima di uscire.
