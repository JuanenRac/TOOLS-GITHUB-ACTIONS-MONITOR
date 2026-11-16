<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# Vollausgabe für ein Team

Mehrere Personen lesen denselben Monitor, jede mit Anmeldung und Rolle. Er ist standardmäßig aus (`auth.enabled`) und die Lite-Ausgabe hat ihn nie. Die vollständige Liste der Optionen steht im Abschnitt Teammodus von [ADVANCED_deu.md](ADVANCED_deu.md).

## Erste Schritte

- Mit eingeschaltetem `auth.enabled` ändert sich nichts, bis der erste Administrator existiert: Lege ihn auf dem Rechner an, der den Monitor ausführt (die Seite `/login` oder `python -m github_actions_monitor.security.auth_cli create-admin`). Im Netzwerkmodus startet der Monitor ohne ihn nicht.
- Nutze im Netzwerk HTTPS oder ein VPN: Sonst liefen das Sitzungs-Cookie und die Passwörter im Klartext.

## Rollen

- `viewer` liest; `maintainer` ändert auch den Arbeitsmodus und schaltet, nur vom Rechner des Monitors aus, Meldungen stumm und bestätigt sie; `admin` ändert auch Einstellungen und Benutzer.
- Jeder Benutzer sieht nur die ihm zugewiesenen Konten (ein Administrator sieht alle); ein anderes Konto antwortet mit 403 `account_scope`.

## Sitzungen und Passwörter

- Der Browser erhält das Cookie `monitor_session` und ein CSRF-Token; ein Skript meldet sich mit `POST /api/auth/login` an und sendet nur bei eingeschaltetem `auth.allow_bearer` `Authorization: Bearer`.
- Passwörter werden als gesalzener Hash gespeichert und brauchen `auth.min_length` Zeichen; nach `auth.max_failed_logins` Fehlversuchen ist der Benutzer `auth.lockout_minutes` gesperrt.

## Wer was getan hat

- Das Aktionsprotokoll hält fest, wer was geändert hat ([AUDIT_LOG_deu.md](AUDIT_LOG_deu.md)); ein Maintainer liest es nur, wenn `audit_log.maintainers_can_read` an ist.
- Die Gesundheit des Teams und die Bewertung je Konto stehen in [HEALTH_deu.md](HEALTH_deu.md) und [SCORE_deu.md](SCORE_deu.md); für einen Server, der an bleibt, lies [COMPLETE_SERVICE_deu.md](COMPLETE_SERVICE_deu.md).
