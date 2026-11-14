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
