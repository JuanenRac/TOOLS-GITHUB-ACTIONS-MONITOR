<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook in ingresso

Facoltativo e **spento per impostazione predefinita**. Permette a GitHub di avvisare il monitor che qualcosa è cambiato, così il repository viene aggiornato nel ciclo successivo invece di attendere la prossima interrogazione.

## Cosa fa (solo aggiornare)

Un evento accettato segna soltanto il repository indicato per un aggiornamento nel ciclo successivo. Non si scrive nulla su GitHub né su disco, nessun testo dell'evento viene conservato o mostrato, e si accettano solo i repository già osservati dal monitor. Eventi compresi: `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` e `ping`; ogni altro riceve `202` ed è ignorato.

## Sicurezza

- Il monitor ascolta ancora solo su `127.0.0.1`. GitHub lo raggiunge solo attraverso un tunnel che crei tu di proposito; lo strumento non ne apre mai uno.
- Spento finché `webhook.enabled` non è attivo **e** il segreto condiviso in `actions_monitor.json` non ha almeno 32 caratteri (altrimenti l'endpoint resta chiuso).
- Ogni richiesta deve portare `X-Hub-Signature-256: sha256=<hmac>`, calcolato con quel segreto; il resto riceve `401`. Il segreto non viene mai mostrato: la scheda Impostazioni dice solo se è definito.
- Un corpo oltre 256 KB riceve `413`.

## Come attivarlo

In `actions_monitor.json`: `"webhook": {"enabled": true, "secret": "<32 o più caratteri casuali>"}`; l'interruttore è anche nella scheda Impostazioni (sotto-scheda Webhook in ingresso), il segreto solo nel file. Riavvia il monitor. Nelle impostazioni del webhook di GitHub usa il tipo `application/json`, lo stesso segreto e l'URL del tuo tunnel terminante in `/api/webhook`.

## Eventi in tempo reale

- Con `webhook.record_events` attivo (predefinito), un evento `workflow_run` firmato aggiorna subito l'elenco dei run di quel repository, senza leggere GitHub: il repository non costa quota fino alla successiva lettura programmata. Un evento `workflow_job` porta anche il tempo in coda e quello di ogni passo per le analisi.
- Si conservano solo brevi campi validati (workflow, run, stato, conclusione, branch, commit corto, link al run, durate); mai il messaggio del commit né testo libero. Gli ultimi `webhook.live_events_keep` eventi si leggono su `GET /api/live-events` (solo questo computer).
- Un run che termina in rosso invia anche la notifica `workflow_failed` se le notifiche sono attive. Con `webhook.record_events` spento il webhook torna alla modalità di solo aggiornamento descritta sopra.
- GitHub non può raggiungere `127.0.0.1`: usa `gh webhook forward` (vedi la documentazione della CLI di GitHub) o un tunnel che crei di proposito, verso `http://127.0.0.1:PORTA/api/webhook`.

## Replay e inondazioni

Una richiesta firmata valida che qualcuno ha catturato e rinvia riceve risposta ma non viene eseguita: ogni consegna richiede il proprio id `X-GitHub-Delivery`, gli id già accettati sono ricordati per `webhook.replay_seconds` (un'ora di default, memoria limitata) e una ripetizione riceve `202 {"duplicate": true}`. (Una riconsegna manuale dalla pagina di GitHub riusa l'id, quindi viene ignorata in questa finestra.) Un repository può causare al massimo `webhook.max_per_minute` eventi accettati al minuto; gli altri ricevono risposta e vengono ignorati. Se il payload indica `full_name`, il suo proprietario deve essere l'account osservato (o uno di `webhook.allowed_owners`). In modalità rete un indirizzo può inviare 120 richieste al minuto. Dopo un evento accettato le letture condizionali salvate di quel repository vengono eliminate e il repository viene riletto al ciclo successivo, così un evento dal vivo è sempre riconciliato con GitHub.

## Lista di controllo della vista dal vivo

1. Definisci `webhook.secret` con almeno 32 caratteri e attiva il webhook.
2. Inoltra la porta (`gh webhook forward`) o apri un tunnel e usa il suo indirizzo che termina con `/api/webhook` in GitHub.
3. Invia l'evento di prova di GitHub (Recent deliveries > Redeliver) e cercalo in `?view=live`.
4. Tieni d'occhio la quota nell'intestazione: con i webhook basta un ciclo più lento.
