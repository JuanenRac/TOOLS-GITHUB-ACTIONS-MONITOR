<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# Il registro delle azioni

Solo Complete, attivo per impostazione predefinita. Accanto all'audit degli accessi (accessi, blocchi, rifiuti), il monitor tiene un registro delle **azioni**: chi ha cambiato cosa, quando e su quale account. Una modifica delle impostazioni, un silenzio o la sua rimozione, una modifica di utenti, password, preferenze di notifica o credenziali. È una riga JSON per azione in `logs/audit_actions.jsonl`, mai riscritta.

## Cosa dice una riga

`at`, `action` (una parola semplice come `settings_change` o `alert_mute`), `user`, `role`, `account`, `target` (un identificatore breve: il nome di un'impostazione, un codice di avviso), `result` (`ok`, `denied` o `error`) e, se serve, `details`. **Non entra mai un valore né un segreto**: una modifica delle impostazioni scrive i nomi delle impostazioni, non i loro valori; una chiave il cui nome sembra un segreto (token, password, key, cookie, authorization, session...) viene scartata; ogni testo viene ripulito come le note per le IA e tagliato a 200 caratteri.

## La catena

Ogni riga porta `prev` (l'hash della riga precedente) e `hash` (l'hash di sé stessa e di `prev`). Una riga modificata, tolta o inserita dopo rompe la catena, e `GET /api/audit-log` dice dove (`chain.broken_at`). Oltre `audit_log.max_mb` la parte vecchia viene conservata come `audit_actions.jsonl.1` e la catena prosegue nel file nuovo. La catena rivela la manomissione; non può impedire a chi ha accesso al file di cancellarlo tutto, quindi conserva una copia dove conta. Con più account, ogni account tiene il proprio file nella sua cartella (`accounts/<id>/audit_actions.jsonl`) e l'API risponde solo con le righe dell'account richiesto; le righe scritte prima di questo cambiamento restano nel vecchio file condiviso. Il controllo copre anche il file ruotato e il collegamento tra i due (`segments`, e `segment` quando una riga è rotta); `complete: false` significa che la catena non inizia al suo primo anello perché un file ruotato è stato sostituito da una rotazione successiva o cancellato. Più processi possono scrivere lo stesso file: ogni riga è concatenata all'ultima riga realmente presente, sotto un blocco. La catena non ha una chiave segreta: chi può scrivere il file può tagliare le sue righe più recenti o riscriverlo con nuovi hash; se deve fare da prova, conserva una copia altrove.

## Chi lo legge

Un amministratore (e la persona al computer quando non c'è la modalità team). Un maintainer solo quando `audit_log.maintainers_can_read` è attivo; nessun altro. `GET /api/audit-log` risponde con le ultime 200 righe e lo stato della catena. Lite non ha nulla di tutto ciò.

## Impostazioni

Impostazioni, scheda Sentinella, blocco **Registro delle azioni**: `audit_log.enabled` (attivo), `audit_log.max_mb` (10) e `audit_log.maintainers_can_read` (spento).
