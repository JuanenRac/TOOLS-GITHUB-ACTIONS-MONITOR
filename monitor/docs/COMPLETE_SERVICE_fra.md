<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# Édition complète en service

Pour un moniteur qui tourne en permanence sur un serveur ou dans un conteneur et que lisent d'autres personnes ou d'autres programmes. Ceci résume les choix ; les détails, les commandes et le tableau des variables sont dans [DEPLOYMENT_fra.md](DEPLOYMENT_fra.md).

## Comment il écoute

- De trois façons : cet ordinateur seulement (par défaut, sans connexion), le réseau (`listen.network` activé, `listen.host` et le jeton d'accès à chaque requête) ou derrière un proxy (`listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`).
- Placez HTTPS (un certificat ou un proxy) ou un VPN devant le mode réseau : en HTTP simple, le jeton et les mots de passe circulent en clair.

## Comment le lancer

- L'image officielle, Docker Compose avec un proxy facultatif ou une installation classique avec systemd ; tous lancent `python -m github_actions_monitor.service` sans navigateur.
- Les ports sont 8765 pour l'édition complète et 8766 pour la lite (`ports.complete`, `ports.lite`).

## Le surveiller

- `GET /api/health` n'appelle pas GitHub ; `GET /api/health?deep=1` répond 503 quand un cycle de rafraîchissement est bloqué, et `python -m github_actions_monitor.cli.healthcheck` fait cet appel pour un conteneur ou un gestionnaire de services.
- Quand GitHub révoque l'accès, remplacez l'identifiant en ligne de commande, avec le point d'accès d'administration ou avec `SIGHUP` ; un redémarrage ne répare pas un accès perdu.

## Pendant des mois

- Choisissez fichiers ou SQLite et la rétention dans [STORAGE_fra.md](STORAGE_fra.md), faites une sauvegarde avant chaque mise à jour et lisez [MIGRATING_fra.md](MIGRATING_fra.md).
- Avec des personnes qui se connectent, le mode équipe est décrit dans [COMPLETE_TEAM_fra.md](COMPLETE_TEAM_fra.md) ; le contrat sur lequel les programmes peuvent compter est dans [API_fra.md](API_fra.md).
