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
