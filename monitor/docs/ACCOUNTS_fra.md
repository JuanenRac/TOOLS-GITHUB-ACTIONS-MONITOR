<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# Plusieurs comptes

L'édition complète peut surveiller plusieurs comptes GitHub (une personne ou une organisation) à la fois. Chaque compte est un moniteur à part : un processus séparé, avec son dossier, son port sur `127.0.0.1`, sa configuration et sa propre lecture du quota de GitHub. Une panne, une réponse lente ou une limite de débit d'un compte ne touche jamais les autres. L'édition lite a un seul compte et rien de tout cela : elle ne montre même pas les options ci-dessous.

## Quand il n'y a rien à faire

Sans dossier `accounts/`, le moniteur fonctionne exactement comme avant : un compte, ses fichiers à côté du code. Vous ne lisez la suite que si vous en voulez plus d'un.

## Le dossier des comptes

```
accounts/
  global.json              facultatif : {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   la configuration de ce compte (son github_owner, repos, sentinelle...)
  org-acme/
    actions_monitor.json
```

L'identifiant d'un compte se compose de lettres minuscules, de chiffres, de `_` et de `-` (jusqu'à 40 caractères), car c'est un nom de dossier ; tout le reste est refusé. `enabled_accounts` vaut `"all"` ou une liste ; `default_account` est celui qui s'ouvre quand aucun n'est demandé. `MONITOR_ACCOUNTS_DIR` déplace le dossier. Chaque compte garde son cache, ses événements, ses analyses, l'état de la sentinelle et ses journaux dans son propre dossier : deux comptes ne partagent jamais un fichier.

## Passer d'un compte à plusieurs

```
python actions_monitor.py --migrate-accounts          # montre ce qui serait copié, n'écrit rien
python actions_monitor.py --migrate-accounts --apply  # le copie dans accounts/default/
python actions_monitor.py --accounts                  # liste les comptes
```

Les originaux ne sont jamais déplacés ni supprimés : vous les supprimez vous-même après vérification. Une seconde exécution refuse, pour que deux états ne se mélangent jamais. Pour ajouter un compte, créez `accounts/<id>/actions_monitor.json` avec son `github_owner` (copiez le modèle `actions_monitor.example.json`).

## Exécuter

`python actions_monitor.py` avec un dossier `accounts/` démarre le superviseur, un petit processus sur le port habituel (8765) qui démarre un moniteur par compte et donne à la page et aux outils une seule adresse. Il ne lit rien de GitHub et n'écrit rien. Si un compte meurt, il le redémarre avec une attente croissante (2, 5, 15, 30, 60 puis 120 secondes) et le résumé le dit en panne entre-temps. `python actions_monitor.py --account personal` n'exécute que ce compte, comme un moniteur ordinaire.

## La page

La page est celle que vous connaissez, avec un sélecteur de comptes en haut du panneau latéral et une entrée **Tous les comptes** qui montre une carte par compte (état, dépôts, en cours, en échec) et ouvre n'importe lequel. Chaque fenêtre garde son propre compte et sa propre vue : ils se lisent dans l'adresse, jamais dans un réglage unique qu'une autre fenêtre écraserait.

| Adresse | Ce qu'elle montre |
|---|---|
| `/?account=org-acme` | la page de ce compte |
| `/?account=all` | les cartes de tous les comptes |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | un panneau |
| `/?chrome=0` | sans boutons d'en-tête, onglets ni filtres : un écran pour un mur ou un second moniteur |

Pour plusieurs écrans, ouvrez une fenêtre par vue, par exemple `?view=now&chrome=0`, `?view=alerts&chrome=0` et `?view=live&chrome=0`. Un seul moniteur les sert toutes : vous ne dépensez pas le quota deux fois. La vue **En direct** montre les derniers événements envoyés par GitHub, l'état du récepteur de webhook (actif ou non, combien de livraisons ont été acceptées, ignorées, répétées ou refusées, jamais le secret) et un sélecteur du mode de travail.

## L'API

`GET /api/accounts` est le résumé, `GET /api/accounts/<id>/status` un compte, et toute autre requête sous `/api/` va au compte nommé par `?account=<id>` ou l'en-tête `X-Account-Id` (le compte par défaut si aucun n'est donné). Un compte inconnu donne un 404. Les règles d'accès sont celles d'un moniteur seul : la même vérification d'hôte et d'origine, et le même jeton d'accès en mode réseau. Le jeton à usage unique d'une modification doit être demandé au même compte que celui auquel la modification est envoyée.

## Un webhook pour tous

`POST /api/webhook` est une adresse unique pour toute l'installation. Le superviseur lit seulement le propriétaire du dépôt dans la charge (`repository.full_name`) et transmet l'événement, intact, au compte dont le `github_owner` est ce propriétaire ; le compte vérifie la signature avec son propre secret. Un propriétaire que personne ne surveille reçoit une réponse et est ignoré. Pour choisir le compte vous-même, ajoutez `?account=<id>`.

## Limites et honnêteté

- Plusieurs comptes sont plusieurs processus : chacun lit GitHub de son côté, donc le quota est partagé par le compte connecté que vous utilisez. Surveillez-le dans les cartes et baissez `refresh_seconds` ou `max_workers` par compte si besoin.
- Les vérifications qui demandent un vrai navigateur, de vrais comptes GitHub et un vrai tunnel de webhook sont à votre charge ; les tests utilisent des remplaçants du moniteur d'un compte et n'appellent jamais GitHub.
- Une version ultérieure ramènera les comptes dans un seul processus ; l'organisation des dossiers et l'API ci-dessus restent.
