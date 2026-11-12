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
- `kind` è uno tra `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`. I campi si aggiungono soltanto. Rispondi con un 2xx qualsiasi; il resto conta come errore.
- `mqtt` pubblica lo stesso JSON come payload di un messaggio QoS 0 su `notify.channels.mqtt.topic`.

## Il limite orario conta i messaggi

`notify.max_per_hour` limita i MESSAGGI che escono dal computer, non gli eventi: un evento inviato a tre canali consuma tre unità, una per canale. Se la quota non basta per tutti i canali, i primi della lista ricevono il messaggio e gli altri vengono scartati (la pagina li conta come «limitati»). Un canale che non può inviare (nessun segreto, indirizzo errato) non consuma nulla. Il conteggio avviene sotto un unico blocco, quindi più thread non superano mai il limite.
