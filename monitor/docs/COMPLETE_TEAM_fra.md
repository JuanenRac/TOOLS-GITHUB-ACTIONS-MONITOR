<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# Édition complète pour une équipe

Plusieurs personnes lisent le même moniteur, chacune avec une connexion et un rôle. Il est éteint par défaut (`auth.enabled`) et l'édition lite ne l'a jamais. La liste complète des options est dans la section Mode équipe de [ADVANCED_fra.md](ADVANCED_fra.md).

## Premiers pas

- Avec `auth.enabled` activé, rien ne change tant que le premier administrateur n'existe pas : créez-le sur l'ordinateur qui exécute le moniteur (la page `/login` ou `python -m github_actions_monitor.security.auth_cli create-admin`). En mode réseau le moniteur ne démarre pas sans lui.
- Sur un réseau, utilisez HTTPS ou un VPN : sinon le cookie de session et les mots de passe circuleraient en clair.

## Rôles

- `viewer` lit ; `maintainer` change aussi le mode de travail et, depuis l'ordinateur du moniteur seulement, met en sourdine et acquitte les alertes ; `admin` change aussi les réglages et les utilisateurs.
- Chaque utilisateur ne voit que les comptes qui lui sont attribués (un administrateur les voit tous) ; un autre compte répond 403 `account_scope`.

## Sessions et mots de passe

- Le navigateur reçoit le cookie `monitor_session` et un jeton CSRF ; un script se connecte avec `POST /api/auth/login` et, seulement si `auth.allow_bearer` est activé, envoie `Authorization: Bearer`.
- Les mots de passe sont conservés sous forme de hachage salé et exigent `auth.min_length` caractères ; après `auth.max_failed_logins` erreurs, l'utilisateur est bloqué `auth.lockout_minutes`.

## Qui a fait quoi

- Le journal des actions note qui a changé quoi ([AUDIT_LOG_fra.md](AUDIT_LOG_fra.md)) ; un maintainer ne le lit que si `audit_log.maintainers_can_read` est activé.
- La santé de l'équipe et le score par compte sont dans [HEALTH_fra.md](HEALTH_fra.md) et [SCORE_fra.md](SCORE_fra.md) ; pour un serveur qui reste allumé, lisez [COMPLETE_SERVICE_fra.md](COMPLETE_SERVICE_fra.md).
