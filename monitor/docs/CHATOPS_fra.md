<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# Commandes de chat (Slack et Discord)

Optionnel, **désactivé par défaut**. Il permet de demander au moniteur, depuis un canal Slack ou Discord, un court état : combien de dépôts sont en rouge, les alertes ouvertes, la file et le score. C'est en **lecture seule**.

## Ce qu'il fait (et ne fait jamais)

- Les commandes forment une liste fermée : `help`, `status`, `alerts`, `red`, `queue` et `score`. Tout le reste reçoit « Je ne connais pas cette commande ». `chatops.allowed_words` ne peut que réduire la liste.
- Une commande lit ce que le moniteur détient déjà (le dernier cycle, les alertes, le score). Elle n'écrit jamais sur GitHub, n'exécute jamais d'action, ne modifie jamais un réglage et ne lit jamais un secret ; il n'existe pas de commande pour cela et on ne peut pas en ajouter depuis le chat.
- La réponse n'est vue que par la personne qui a demandé, ne mentionne personne et ne contient aucun lien sauf un : si `chatops.links` est activé (par défaut), l'adresse d'un dépôt (`https://<hôte>/<propriétaire>/<dépôt>`, vérifiée) à côté d'un nom affiché tel quel. Tout texte venant de GitHub (un nom de dépôt ou de workflow) est nettoyé, tronqué et échappé pour la plateforme.
- Chaque commande qui atteint le moniteur laisse une ligne dans le journal des actions (`chatops_command`) avec les identifiants du chat, jamais le texte de la requête.

## Sécurité

- Désactivé tant que `chatops.enabled` et l'interrupteur de la plateforme (`chatops.slack.enabled`, `chatops.discord.enabled`) ne sont pas activés **et** que la preuve n'est pas dans l'environnement. Les réglages ne gardent que le NOM de la variable (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), jamais sa valeur ; la valeur n'est jamais écrite, affichée ni journalisée.
- Slack : chaque requête doit porter `X-Slack-Signature: v0=<hmac>`, le HMAC-SHA256 de `v0:<horodatage>:<corps>` fait avec le secret de signature, et `X-Slack-Request-Timestamp` pas plus ancien que `chatops.max_age_seconds` (cinq minutes au plus). La comparaison prend le même temps quelle que soit la signature.
- Discord : chaque requête doit porter `X-Signature-Ed25519` et `X-Signature-Timestamp` : une signature Ed25519 de l'horodatage suivi du corps, vérifiée avec la clé publique de votre application (RFC 8032, bibliothèque standard ; rien n'est accepté sans la vérification).
- Une signature mauvaise, ancienne ou venue du futur reçoit `401` et rien du corps n'est examiné. Une signature déjà acceptée n'est jamais acceptée une seconde fois. Un corps de plus de 16 Ko reçoit `413`. Une adresse peut faire 120 requêtes par minute.
- **Les listes sont obligatoires** : `chatops.allowed_teams`, `chatops.allowed_channels` et `chatops.allowed_users`. Si aucune n'est remplie, aucune commande ne s'exécute (le défi de la plateforme reçoit toujours une réponse pour que vous puissiez terminer la configuration). Une liste qui contient des entrées doit contenir l'équipe, le canal ou l'utilisateur de la requête.
- Limites par minute : `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` et `chatops.rate_per_minute`. La réponse doit arriver en 3 secondes : le moniteur répond depuis la mémoire et, s'il était plus lent, indique qu'il est occupé.
- Les deux routes (`/api/chatops/slack`, `/api/chatops/discord`) ne demandent pas le jeton d'accès du mode réseau, car une plateforme ne peut pas l'envoyer : la signature est leur preuve, comme pour le webhook entrant. Le moniteur n'écoute toujours que sur `127.0.0.1` tant que vous n'ouvrez pas le mode réseau ; les plateformes ne l'atteignent que par une adresse HTTPS que vous mettez en place exprès (un tunnel ou un proxy inverse ; l'outil n'en ouvre jamais). Ne publiez par là que `/api/chatops/`.

## Les commandes

| Commande | Réponse |
| --- | --- |
| `help` | la liste des commandes |
| `status` | dépôts en rouge, bloqués, en attente, au vert et inactifs, et alertes ouvertes |
| `alerts` | les alertes ouvertes (niveau, code et dépôt), jusqu'à `chatops.max_rows` |
| `red` | les workflows en rouge avec leur durée, jusqu'à `chatops.max_rows` |
| `queue` | en cours, en file, en attente d'approbation et minutes utilisées en 24 heures |
| `score` | le score, sa lettre et sa variation |

`chatops.show_repo_names` décide des noms : `all` (par défaut : tous les noms, dépôts privés compris), `public` (un dépôt privé devient `private-N` et ses workflows ne sont pas nommés) ou `none`. **Risque de `all` :** les noms des dépôts et workflows privés arrivent à tous les canaux et utilisateurs que vos listes autorisent. C'est pourquoi les listes sont obligatoires et chaque liste qui contient des entrées doit correspondre (équipe, canal et utilisateur ensemble). Choisissez `public` ou `none` si le canal est plus large que les personnes qui peuvent connaître ces noms.

## Slack, pas à pas

1. Ouvrez api.slack.com/apps > Create New App > From scratch. Nommez-la et choisissez votre espace de travail.
2. Slash Commands > Create New Command : commande `/monitor`, **Request URL** `https://<votre adresse publique>/api/chatops/slack`, une courte description. Aucun scope de bot n'est nécessaire.
3. Basic Information > App Credentials > **Signing Secret** : copiez-le et donnez-le au moniteur par l'environnement, jamais par le fichier : `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` dans PowerShell avant de démarrer le moniteur, `export MONITOR_SLACK_SIGNING_SECRET=...` dans un shell, une entrée d'environnement ou un fichier de secret dans un service ou un conteneur.
4. Installez l'application dans l'espace de travail (Install App).
5. Remplissez les listes : l'identifiant de votre équipe (commence par `T`), celui du canal (ouvrez le canal, ses détails, l'identifiant en bas : `C...`) et votre identifiant de membre (votre profil > Copy member ID : `U...`). Placez-les dans Réglages > Commandes de chat, ou `"chatops": {"allowed_channels": ["C0123456789"]}` dans `actions_monitor.json`.
6. Activez Commandes de chat et Slack, puis redémarrez le moniteur.

## Discord, pas à pas

1. Ouvrez discord.com/developers/applications > New Application. Dans General Information, copiez la **Public Key** (64 caractères hexadécimaux) et donnez-la au moniteur par l'environnement : `$env:MONITOR_DISCORD_PUBLIC_KEY = "<clé publique>"` dans PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` dans un shell.
2. Remplissez les listes, activez Commandes de chat et Discord (Réglages > Commandes de chat) puis redémarrez le moniteur. Faites-le **avant** l'étape suivante : Discord envoie un test signé quand vous enregistrez l'adresse et la refuse si le moniteur ne répond pas.
3. General Information > **Interactions Endpoint URL** : `https://<votre adresse publique>/api/chatops/discord`, puis Save.
4. Enregistrez la commande une fois avec votre propre outil (l'API Discord, `POST /applications/<identifiant de l'application>/commands`) avec ce corps :

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Invitez l'application avec le seul scope `applications.commands` (OAuth2 > URL Generator) ; aucune permission de bot n'est nécessaire. Identifiants : dans Discord, activez le Mode développeur (Avancé) et utilisez Copier l'identifiant sur le serveur, le canal et votre utilisateur.

## Essai

Dans un canal autorisé, tapez `/monitor help` (Slack) ou `/monitor command:status` (Discord). Autres réponses :

| Ce que vous voyez | Signification |
| --- | --- |
| rien, ou « n'a pas répondu » | l'adresse n'est pas joignable, le moniteur est éteint ou il a répondu `401` (mauvais secret ou mauvaise clé, ou une horloge décalée de plus de cinq minutes) |
| « Cette commande n'est pas disponible ici. » | l'équipe, le canal ou l'utilisateur n'est pas dans les listes |
| « Trop de commandes. » | l'une des trois limites par minute |
| « Le moniteur n'a pas encore lu GitHub. » | le premier cycle n'est pas terminé |
