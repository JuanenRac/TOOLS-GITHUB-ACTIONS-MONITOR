<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | [🇵🇹 Português](NOTIFICATIONS_por.md)

# Notifications

Optionnelles et **désactivées par défaut**. Les événements du flux (un nouveau rouge, un build bloqué, un build qui attend sa signature, une connexion perdue, un run échoué signalé par le webhook) peuvent être envoyés à un chat ou à un appareil. Une notification n'est qu'un message avec un lien : elle ne relance, n'annule et n'écrit jamais rien sur GitHub.

## Canaux

- `telegram` (un bot), `discord` et `slack` (webhook de canal), `matrix` (un salon), `mqtt` (un broker sur cet ordinateur, pour des lumières et balises) et `http_local` (un POST vers une adresse de cet ordinateur).
- Chaque canal a son interrupteur dans l'onglet Réglages (sous-onglet Notifications) et un bouton d'essai.


## Sécurité

- Les jetons et URL de webhook ne sont jamais enregistrés dans la configuration : vous indiquez le NOM d'une variable d'environnement, la valeur n'est lue qu'au moment de l'envoi, jamais affichée ni journalisée.
- `discord` n'accepte que `discord.com` et `slack` que `hooks.slack.com` ; `mqtt` et `http_local` n'acceptent que `127.0.0.1`, `localhost` ou `[::1]`.
- Une destination qui est, ou se résout vers, une adresse de boucle locale, privée (10.x, 172.16-31.x, 192.168.x, fc00::/7), de lien local (169.254.x avec l'adresse de métadonnées du cloud, fe80::/10), partagée (100.64.0.0/10) ou réservée est refusée tant que `notify.allow_private_targets` est désactivé (par défaut). Le nom est résolu une fois, la connexion va vers l'adresse vérifiée et chaque redirection suit la même règle. Ainsi un serveur Matrix mal saisi n'atteint ni votre routeur ni le service de métadonnées d'une machine cloud.
- Au plus `notify.max_per_hour` messages quittent l'ordinateur ; un envoi qui échoue est compté et ignoré, il n'arrête jamais le moniteur.


## Le contrat des adaptateurs

- Pour joindre un service absent de la liste, lancez un petit récepteur sur cet ordinateur et pointez `http_local` vers lui. Il reçoit un POST avec `Content-Type: application/json` et ce corps : `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` vaut `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`, `credential_blind` ou `credential_back`. Les champs ne font que s'ajouter. Répondez par un 2xx ; tout le reste compte comme un échec.
- `mqtt` publie le même JSON comme charge d'un message QoS 0 sur `notify.channels.mqtt.topic`.

## La limite par heure compte les messages

`notify.max_per_hour` limite les MESSAGES qui quittent l'ordinateur, pas les événements : un événement envoyé à trois canaux consomme trois unités, une par canal. Si le quota ne suffit pas pour tous les canaux, les premiers de la liste reçoivent le message et les autres sont écartés (la page les compte comme « limités »). Un canal qui ne peut pas envoyer (pas de secret, mauvaise adresse) ne consomme rien. Le décompte se fait sous un seul verrou : plusieurs threads ne peuvent donc jamais dépasser la limite.

## Notifications par utilisateur (mode équipe)

Désactivé par défaut (`notify.users.enabled`). Avec le mode équipe activé, chaque utilisateur choisit dans `GET/POST /api/auth/me/notify` les canaux (`ntfy`, `teams`, `email`), les sentinelles (`ci`, `collab`), le niveau minimal (`info`, `warn`, `bad`), s'il veut les événements du système et si les messages arrivent tout de suite ou réunis dans un résumé (`hourly`, `daily`). Le rôle décide de ce qu'un utilisateur peut apprendre : un lecteur, les événements de CI des comptes qu'il peut voir ; un mainteneur, en plus ce qui attend une personne (une compilation en attente de signature, une version à publier) ; un administrateur, en plus les événements du système. Un événement d'un compte n'atteint jamais quelqu'un qui ne peut pas voir ce compte. `notify.users.max_per_hour` limite les messages reçus par un utilisateur.

- `ntfy` : le sujet de chaque utilisateur sur le serveur `notify.channels.ntfy.server` (https, ou un serveur de cet ordinateur) ; un jeton d'accès est facultatif.
- `teams` : l'adresse du webhook entrant d'un canal Teams (hôtes de Microsoft seulement).
- `email` : l'adresse de l'utilisateur, envoyée par un relais de cet ordinateur sans connexion (`notify.channels.email`).

L'adresse du webhook Teams et le jeton ntfy sont gardés chiffrés par le système (DPAPI, Trousseau, Secret Service ou un fichier privé) et ne reviennent jamais dans une réponse, un journal ou la configuration ; supprimer un utilisateur les supprime. `MONITOR_SECRET_BACKEND=file` impose le fichier privé. Chaque canal est désactivé tant que l'administrateur ne l'active pas. Le résumé réunit les alertes que l'utilisateur n'a pas vues (jusqu'à `notify.digest.max_items`) ; `POST /api/auth/me/notify/seen` les marque comme vues et elles ne sont pas envoyées ; `POST /api/auth/me/notify/test` envoie un message d'essai aux canaux de l'utilisateur. Un administrateur lit les préférences de tous (jamais un secret) dans `GET /api/auth/notify`.
