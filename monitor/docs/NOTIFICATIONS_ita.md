<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# Notifiche

Facoltative e **spenta per impostazione predefinita**. Gli eventi del feed (un nuovo rosso, una build bloccata, una build in attesa della firma, una connessione persa, un run fallito segnalato dal webhook) possono essere inviati a una chat o a un dispositivo. Una notifica è solo un messaggio con un link: non rilancia, non annulla e non scrive mai nulla su GitHub.

## Canali

- `telegram` (un bot), `discord` e `slack` (webhook di canale), `matrix` (una stanza), `mqtt` (un broker su questo computer, per luci e segnalatori) e `http_local` (un POST a un indirizzo di questo computer).
- Ogni canale ha il suo interruttore nella scheda Impostazioni (sotto-scheda Notifiche) e un pulsante di prova.


## Sicurezza

- Token e URL dei webhook non si salvano mai nella configurazione: si indica il NOME di una variabile d'ambiente e il valore si legge solo al momento dell'invio, senza mostrarlo né registrarlo.
- `discord` accetta solo `discord.com` e `slack` solo `hooks.slack.com`; `mqtt` e `http_local` accettano solo `127.0.0.1`, `localhost` o `[::1]`.
- Una destinazione che è, o si risolve in, un indirizzo di loopback, privato (10.x, 172.16-31.x, 192.168.x, fc00::/7), link-local (169.254.x con l'indirizzo dei metadati cloud, fe80::/10), condiviso (100.64.0.0/10) o riservato viene rifiutata finché `notify.allow_private_targets` è spento (predefinito). Il nome viene risolto una volta, la connessione va all'indirizzo verificato e ogni reindirizzamento segue la stessa regola. Così un server Matrix sbagliato non raggiunge il router né il servizio di metadati di una macchina cloud.
- Al massimo `notify.max_per_hour` messaggi escono dal computer; un invio fallito si conta e si ignora, non ferma mai il monitor.


## Il contratto degli adattatori

- Per raggiungere un servizio non in elenco, esegui un piccolo ricevitore su questo computer e punta `http_local` verso di esso. Riceve un POST con `Content-Type: application/json` e questo corpo: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` è uno tra `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `ai_alert`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`, `score_dropped`, `security_new`, `security_fixed`, `delivery_new`, `delivery_fixed`, `alerts_digest`, `silence_review`. I campi si aggiungono soltanto. Rispondi con un 2xx qualsiasi; il resto conta come errore.
- `mqtt` pubblica lo stesso JSON come payload di un messaggio QoS 0 su `notify.channels.mqtt.topic`.

## Apprise (facoltativo, spento per impostazione predefinita)

Il canale `apprise` consegna il messaggio al comando `apprise` (installalo tu, per esempio `pip install apprise`) per raggiungere uno qualsiasi dei servizi che conosce. Gli indirizzi contengono i segreti di quei servizi, quindi stanno in una variabile d'ambiente il cui NOME è `notify.channels.apprise.urls_env` (separati da spazi o virgole, al massimo dieci); vengono scritti in un file temporaneo privato per l'istante della chiamata, mai negli argomenti del comando, e il comando riceve un ambiente senza le chiavi del monitor. **Apprise apre connessioni proprie: la protezione del monitor contro gli indirizzi privati non si applica**, quindi ciò che raggiunge dipende dagli indirizzi che gli dai; per questo il canale ha un interruttore proprio, spento per impostazione predefinita, ed è segnato come impostazione di sicurezza. Se il comando manca il canale dice `not_installed`; un errore viene contato come gli altri e non ferma mai il monitor.

## Il limite orario conta i messaggi

`notify.max_per_hour` limita i MESSAGGI che escono dal computer, non gli eventi: un evento inviato a tre canali consuma tre unità, una per canale. Se la quota non basta per tutti i canali, i primi della lista ricevono il messaggio e gli altri vengono scartati (la pagina li conta come «limitati»). Un canale che non può inviare (nessun segreto, indirizzo errato) non consuma nulla. Il conteggio avviene sotto un unico blocco, quindi più thread non superano mai il limite.

## Notifiche per ogni utente (modalità team)

Disattivato per impostazione predefinita (`notify.users.enabled`). Con la modalità team attiva, ogni utente sceglie in `GET/POST /api/auth/me/notify` i canali (`ntfy`, `teams`, `email`), le sentinelle (`ci`, `collab`), il livello minimo (`info`, `warn`, `bad`), se vuole gli eventi del sistema e se i messaggi arrivano subito o raccolti in un riepilogo (`hourly`, `daily`). Il ruolo decide che cosa un utente può sapere: un lettore, gli eventi di CI degli account che può vedere; un manutentore, in più ciò che attende una persona (una build in attesa di firma, una versione da pubblicare); un amministratore, in più gli eventi del sistema. Un evento di un account non raggiunge mai chi non può vedere quell'account. `notify.users.max_per_hour` limita i messaggi di un utente.

- `ntfy`: l'argomento di ogni utente sul server `notify.channels.ntfy.server` (https, o uno su questo computer); un token di accesso è facoltativo.
- `teams`: l'indirizzo del webhook in ingresso di un canale Teams (solo host di Microsoft).
- `email`: l'indirizzo dell'utente, inviato tramite un relay di questo computer che non richiede accesso (`notify.channels.email`).

L'indirizzo del webhook di Teams e il token di ntfy sono custoditi cifrati dal sistema (DPAPI, Portachiavi, Secret Service o un file privato) e non tornano mai in una risposta, in un registro o nella configurazione; eliminando un utente vengono eliminati. `MONITOR_SECRET_BACKEND=file` impone il file privato. Ogni canale è spento finché l'amministratore non lo attiva. Il riepilogo raccoglie gli avvisi che l'utente non ha visto (fino a `notify.digest.max_items`); `POST /api/auth/me/notify/seen` li segna come visti e non vengono inviati; `POST /api/auth/me/notify/test` invia un messaggio di prova ai canali dell'utente. Un amministratore legge le preferenze di tutti (mai un segreto) in `GET /api/auth/notify`.

### Il pannello di ogni utente

In modalità team, il menu dell'utente connesso (il nome in alto) ha la voce **Notifiche**. Il pannello mostra e salva le stesse preferenze di `GET/POST /api/auth/me/notify`: se vuoi le notifiche, i canali (ntfy con il suo argomento e un token facoltativo, Teams con l'indirizzo web del canale, e-mail con un indirizzo), le sentinelle (CI, collaborazione), il livello minimo, gli eventi di sistema (solo per un amministratore) e se ogni avviso arriva subito o in un riepilogo orario o giornaliero. Un segreto già salvato è mostrato come salvato e non torna mai nella pagina; viene inviato solo se ne digiti uno nuovo, e una casella vuota lo mantiene. **Invia una prova** manda un messaggio ai tuoi canali e **Ho visto i miei avvisi** segna come visti quelli in attesa. Se l'amministratore non ha attivato `notify.users.enabled`, il pannello lo dice: puoi salvare le tue scelte, ancora non viene inviato nulla.

## Molti avvisi, o sempre gli stessi

Quattro impostazioni facoltative del blocco `alerts` (tutte disattivate o vuote per impostazione predefinita) decidono cosa arriva ai canali sopra. Gli elenchi, la scheda Avvisi e il registro degli eventi continuano a mostrare tutto.

- **Silenzi permanenti** (`alerts.silences`): una voce per riga, `repository:workflow:ramo;motivo;data di revisione`. Tutto tranne il repository è facoltativo e `*` corrisponde a qualsiasi testo. Gli avvisi corrispondenti sono mostrati come silenziati, nessuno viene notificato e alla data di revisione viene annunciato un promemoria; il silenzio resta attivo finché non lo rimuovi.
- **Servizi e cron brevi** (`alerts.service`): un workflow che gira solo pianificato o a mano e ogni tanto fallisce viene annunciato solo dopo `failures` fallimenti di fila, o quando `rate_percent` degli ultimi run è fallito; annunciato una volta e chiuso una volta invece di avvisare in ciclo. `workflows` aggiunge altri workflow a questa classe.
- **Raggruppa per commit** (`alerts.group`): quando `min` o più workflow di un repository diventano rossi sullo stesso commit, una notifica li elenca.
- **Riepilogo quando sono molti** (`alerts.digest`): dopo `threshold` notifiche nell'ultima ora, le altre vengono trattenute e comunicate in un riepilogo ogni `minutes` minuti. Gli eventi trattenuti restano nel registro degli eventi.
