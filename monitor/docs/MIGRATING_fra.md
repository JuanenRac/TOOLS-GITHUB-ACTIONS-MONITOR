<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Mise à jour depuis une version antérieure à la 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · **Français** · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La version 1.5.0 a donné des noms anglais aux fichiers, dossiers, scripts et à un réglage. Rien n'est perdu : le moniteur continue de LIRE les anciens noms, vous pouvez donc mettre à jour d'abord et ranger ensuite.

## Étapes

1. Arrêtez le moniteur et décompressez la nouvelle version sur l'ancien dossier (gardez votre `actions_monitor.json`).
2. Voyez ce qui changerait : `python migrate_state.py` (simulation, ne change rien).
3. Faites-le : `python migrate_state.py --apply` copie les anciens fichiers vers les nouveaux noms et garde les anciens ; ajoutez `--move` pour les renommer à la place. Rien d'existant n'est écrasé, et le réglage `parte_history_days` devient `report_history_days` après sauvegarde d'une copie de `actions_monitor.json`.
4. Démarrez le moniteur avec `MONITOR_GITHUB_ACTIONS` (le même lanceur qu'avant) et utilisez `BATCH_GITHUB_ACTIONS` pour les outils par lots.
5. Supprimez les anciens lanceurs qu'il vous reste : `LOTE_GITHUB_ACTIONS.bat`, `.sh` et `.command`.

## Anciens et nouveaux noms

| Avant la 1.5.0 | Depuis la 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, son schéma et les fichiers de `--export-status` n'ont pas changé. La langue est l'anglais tant que vous n'en choisissez pas une autre dans les réglages.

# De 1.5.x à 1.6.x

Rien n'est à convertir : le moniteur continue de lire votre `actions_monitor.json` et ajoute les nouvelles clés, avec des valeurs sûres, la première fois que vous enregistrez depuis les Réglages.

1. Arrêtez le moniteur et décompressez la nouvelle version sur l'ancien dossier (gardez votre `actions_monitor.json` et vos fichiers de catalogue).
2. Démarrez-le comme avant. De nouveaux fichiers apparaissent à côté (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`) ; ils peuvent être supprimés à tout moment.
3. Facultatif : `python actions_monitor.py --doctor` vérifie l'installation.

Ce qui change : l'**édition lite** existe (`MONITOR_LITE_GITHUB_ACTIONS`, port 8766, son propre `actions_monitor_lite.json`, sans sentinelle) ; le **rouge sur main** suit une seule règle (le dernier run terminé de chaque workflow sur la branche par défaut ; les runs annulés, ignorés, neutres et périmés ne disent rien), un chiffre peut donc différer de la 1.5.x ; la page Réglages commence par un onglet **Essentiel** ; les notifications, l'analytique, le linter, les événements du webhook et l'assistant IA existent et sont **désactivés** tant que vous ne les activez pas ; écrire sur GitHub exige toujours votre confirmation explicite. Rich et Textual restent facultatifs ; Python 3.11 ou plus récent.

# De la 1.6.4 à la 1.6.5

Rien n'est à convertir. Ce qui se comporte désormais autrement, volontairement, car ce qui n'est pas prouvé n'est plus tenu pour sûr :

- **Lots** : `finalize` ne propose à la signature qu'une exécution dont le lot ENREGISTRE qu'elle a été construite sur le commit vérifié. Un lot écrit par une version plus ancienne indique `needs_review`. Pour l'utiliser quand même : `finalize --accept-legacy` relit l'exécution sur GitHub, ne l'accepte que si son commit est celui enregistré et demande le mot LEGACY avant chaque signature. Ou relancez la compilation.
- **CI verte** signifie que les fichiers de workflow obligatoires ont réussi sur ce commit (par défaut `ci.yml` ; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), que rien n'a échoué ni n'attend une approbation, et que la liste des exécutions est complète. Un dépôt dont le fichier de CI porte un autre nom doit l'indiquer dans `dispatch.required_ci`.
- **Un `git fetch` en échec** (pas de réseau, pas d'identifiants) arrête le lancement de ce dépôt.
- **targets.json** : `tool` doit être un simple nom de fichier (sans dossier ni `..`) situé dans le dossier des outils ; `extra` n'accepte que des paires `-f clé=valeur` (pas `dry_run` ni `ref`) ; `finalize_flags` seulement des options longues comme `--bench`. Un catalogue non conforme est refusé avec la raison.
- **Notifications** : `max_per_hour` compte les messages (un par canal), pas les événements.
- **Webhook** : chaque requête a besoin de `X-GitHub-Delivery` (GitHub l'envoie toujours) ; un identifiant répété est ignoré ; le propriétaire de `full_name` doit être le compte surveillé.
- **act** : un clone qui est un lien vers un autre dossier est refusé (`act.allow_symlinks` l'autorise).
- **Mode réseau** : adresses IPv4 uniquement ; l'adresse affichée est celle où le serveur écoute ; `GET /api/sentinel/parte.txt?save=1` n'écrit plus (la copie est un POST avec le jeton à usage unique).
- Le jeton GitHub conservé n'est plus placé dans l'environnement du processus : seul `gh` le reçoit.
- Le test qui décompresse le zip dans un dossier propre ne fait plus partie de la batterie ordinaire ; `make_release.py` l'exécute comme étape à part.

# De la 1.6.5 à la 1.6.6

Rien à convertir. Ce qui se comporte autrement, volontairement :

- **Mode réseau en HTTPS** : les modifications faites depuis la page fonctionnent maintenant ; l'`Origin` doit porter le schéma de la session et le port du moniteur. Derrière un proxy, gardez le port du moniteur dans l'adresse, sinon le contrôle la refuse.
- **Mode réseau** : tout réglage que le schéma marque `secure` ne se change que depuis l'ordinateur lui-même (avant : seulement `listen.`, `github_token.`, `act.`, `github_actions.`). Un script sur un autre ordinateur qui changeait `webhook.*`, `notify.*` et similaires reçoit maintenant 403 `local_only`.
- **act** : après Stop l'exécution est libre aussitôt ; un démarrage immédiat ne répond plus `busy`.
- Nouveaux fichiers à côté du moniteur : `degraded.json` et `degraded_lite.json` (les compteurs d'échecs avalés) ; on peut les supprimer à tout moment.
- L'historique des modifications (Aide > Journal des modifications) est traduit : un fichier `docs/CHANGELOG_<langue>.md` par langue.

# De la 1.6.6 à la 1.6.7

Rien à convertir. Ce qui se comporte autrement, volontairement :

- **Mode réseau derrière un proxy HTTPS sur le port 443** : nouveau réglage `listen.proxy_public_host` (vide par défaut ; si vous le laissez ainsi, rien ne change). Indiquez-y le nom d'hôte public du proxy lorsqu'il transmet `Host` et `Origin` sans port ; ce seul nom est alors accepté tel quel, uniquement tant que le mode réseau est actif et que la session est en HTTPS. Il ne se change que depuis l'ordinateur lui-même. Derrière un proxy qui conserve le port, rien ne change.
- L'historique des modifications (Aide > Journal des modifications) est maintenant traduit pour la 1.6.7 et la 1.6.5 dans les sept autres langues ; les entrées plus anciennes montrent encore le texte anglais sous un avis traduit.

# De la 1.6.7 à la 1.6.8

Rien à convertir et aucun réglage ne change.

- Nouveau dans le dépôt (pas dans le paquet) : `python tools/manual_check_live.py proxy HÔTE [PORT] [CONNEXION]` vérifie votre vrai proxy HTTPS sur le port 443 face à `listen.proxy_public_host` ; définissez d'abord `MONITOR_ACCESS_TOKEN`, il est lu et jamais affiché.
- L'historique des modifications (Aide > Journal des modifications) est maintenant traduit dans les sept autres langues de la 1.6.8 à la 1.6.3.
