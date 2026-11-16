<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# Edizione completa come servizio

Per un monitor che funziona sempre su un server o in un contenitore e che altre persone o altri programmi leggono. È un riassunto delle scelte; i dettagli, i comandi e la tabella delle variabili sono in [DEPLOYMENT_ita.md](DEPLOYMENT_ita.md).

## Come ascolta

- In tre modi: solo questo computer (predefinito, senza accesso), la rete (`listen.network` attivo, `listen.host` e il token di accesso in ogni richiesta) o dietro un proxy (`listen.proxy_public_host`, `listen.secure_cookie` o `listen.trusted_proxy`).
- Metti HTTPS (un certificato o un proxy) o una VPN davanti alla modalità di rete: con HTTP semplice il token e le password viaggiano in chiaro.

## Come eseguirlo

- L'immagine ufficiale, Docker Compose con un proxy facoltativo o un'installazione classica con systemd; tutti avviano `python -m github_actions_monitor.service` senza browser.
- Le porte sono 8765 per l'edizione completa e 8766 per la lite (`ports.complete`, `ports.lite`).

## Tenerlo d'occhio

- `GET /api/health` non chiama GitHub; `GET /api/health?deep=1` risponde 503 quando un ciclo di aggiornamento è bloccato, e `python -m github_actions_monitor.cli.healthcheck` fa quella chiamata per un contenitore o un gestore di servizi.
- Quando GitHub revoca l'accesso, sostituisci la credenziale da riga di comando, con l'endpoint di amministrazione o con `SIGHUP`; un riavvio non ripara un accesso perso.

## Per mesi

- Scegli file o SQLite e la conservazione in [STORAGE_ita.md](STORAGE_ita.md), fai una copia di sicurezza prima di ogni aggiornamento e leggi [MIGRATING_ita.md](MIGRATING_ita.md).
- Con persone che accedono, la modalità squadra è descritta in [COMPLETE_TEAM_ita.md](COMPLETE_TEAM_ita.md); il contratto su cui i programmi possono contare è in [API_ita.md](API_ita.md).
