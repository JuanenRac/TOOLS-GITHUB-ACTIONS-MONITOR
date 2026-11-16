<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# Edizione completa per una persona

L'edizione completa sul proprio computer è il modo abituale di usare il monitor: una persona, un account GitHub, nessun accesso e una pagina che si apre solo su `127.0.0.1`. L'edizione semplice per chi vuole solo vedere le proprie esecuzioni è [LITE_ita.md](LITE_ita.md).

## Avvio

- Accedi a GitHub una volta con `gh auth login`, poi avvia `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` o `.command`). La pagina si apre sulla porta 8765 (`ports.complete`).
- Scegli nelle Impostazioni i repository e gli ecosistemi da sorvegliare. I primi cinque minuti sono in [FIRST_STEPS_ita.md](FIRST_STEPS_ita.md).

## Cosa ottieni

- Tre sentinelle (CI attiva; Collab e Security spente finché non le accendi) e un elenco di avvisi che puoi silenziare dal tuo computer.
- Il punteggio dell'account, la salute di ogni repository, rapporti programmati (spenti per impostazione predefinita) e un registro delle azioni eseguite (attivo per impostazione predefinita, `audit_log.enabled`).
- Le modalità di lavoro normale, veloce e turbo ([MODES_ita.md](MODES_ita.md)) e la modalità Bassa quando la quota scarseggia ([QUOTA_ita.md](QUOTA_ita.md)).

## Tenerlo su questo computer

- Con `auth.enabled` spento (il valore predefinito) non ci sono utenti né nulla da ricordare: attiva la modalità squadra solo quando il monitor lo usa più di una persona ([COMPLETE_TEAM_ita.md](COMPLETE_TEAM_ita.md)).
- `listen.network` è spento per impostazione predefinita: la pagina e l'API rispondono solo a `127.0.0.1`. Per lasciarlo sempre acceso, leggi [COMPLETE_SERVICE_ita.md](COMPLETE_SERVICE_ita.md).

## Giorno per giorno

- `python bin/monitor_cli.py status`, `doctor` e `health` interrogano il monitor in esecuzione ([CLI_ita.md](CLI_ita.md)). Per aggiornare, leggi [MIGRATING_ita.md](MIGRATING_ita.md).
- I tuoi script possono leggere l'API: [API_ita.md](API_ita.md) elenca ciò che si promette non cambi.
