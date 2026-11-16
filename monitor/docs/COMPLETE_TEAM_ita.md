<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# Edizione completa per una squadra

Più persone leggono lo stesso monitor, ciascuna con un accesso e un ruolo. È spenta per impostazione predefinita (`auth.enabled`) e l'edizione lite non la ha mai. L'elenco completo delle opzioni è nella sezione Modalità squadra di [ADVANCED_ita.md](ADVANCED_ita.md).

## Primi passi

- Con `auth.enabled` attivo non cambia nulla finché non esiste il primo amministratore: crealo sul computer che esegue il monitor (la pagina `/login` o `python -m github_actions_monitor.security.auth_cli create-admin`). In modalità di rete il monitor non parte senza.
- In rete usa HTTPS o una VPN: altrimenti il cookie di sessione e le password viaggerebbero in chiaro.

## Ruoli

- `viewer` legge; `maintainer` cambia anche la modalità di lavoro e, solo dal computer del monitor, silenzia e conferma gli avvisi; `admin` cambia anche impostazioni e utenti.
- Ogni utente vede solo gli account assegnati (un amministratore li vede tutti); un altro account risponde 403 `account_scope`.

## Sessioni e password

- Il browser riceve il cookie `monitor_session` e un token CSRF; uno script accede con `POST /api/auth/login` e, solo se `auth.allow_bearer` è attivo, invia `Authorization: Bearer`.
- Le password sono conservate come hash con sale e richiedono `auth.min_length` caratteri; dopo `auth.max_failed_logins` errori l'utente è bloccato per `auth.lockout_minutes`.

## Chi ha fatto cosa

- Il registro delle azioni annota chi ha cambiato cosa ([AUDIT_LOG_ita.md](AUDIT_LOG_ita.md)); un maintainer lo legge solo se `audit_log.maintainers_can_read` è attivo.
- La salute della squadra e il punteggio per account sono in [HEALTH_ita.md](HEALTH_ita.md) e [SCORE_ita.md](SCORE_ita.md); per un server sempre acceso, leggi [COMPLETE_SERVICE_ita.md](COMPLETE_SERVICE_ita.md).
