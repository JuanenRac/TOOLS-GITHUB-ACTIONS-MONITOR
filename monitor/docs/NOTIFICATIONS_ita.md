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
- Al massimo `notify.max_per_hour` messaggi escono dal computer; un invio fallito si conta e si ignora, non ferma mai il monitor.


## Il contratto degli adattatori

- Per raggiungere un servizio non in elenco, esegui un piccolo ricevitore su questo computer e punta `http_local` verso di esso. Riceve un POST con `Content-Type: application/json` e questo corpo: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` è uno tra `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`. I campi si aggiungono soltanto. Rispondi con un 2xx qualsiasi; il resto conta come errore.
- `mqtt` pubblica lo stesso JSON come payload di un messaggio QoS 0 su `notify.channels.mqtt.topic`.
