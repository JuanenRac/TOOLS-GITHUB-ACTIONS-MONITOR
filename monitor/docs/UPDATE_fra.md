<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Mettre à jour le moniteur (l'outil de mise à jour)

[English](UPDATE.md) · [Español](UPDATE_spa.md) · **Français** · [Italiano](UPDATE_ita.md) · [Deutsch](UPDATE_deu.md) · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · [Português](UPDATE_por.md)

L'outil de mise à jour fait passer une installation de n'importe quelle version publiée à une autre (vers le haut ou vers le bas), migre votre configuration et garde un retour en arrière. C'est UN seul fichier, `monitor_updater.py`, qui n'exige que Python et fonctionne quelle que soit la version installée ; il se trouve aussi dans le produit (`tools/monitor_updater.py`) et comme commande `monitor_cli.py update`. Il ne se met jamais à jour tout seul : seulement à votre demande, et il ne supprime rien (ce qui est remplacé va dans le dossier des copies).

## Trois façons de l'ouvrir

- `py -3 monitor_updater.py` ouvre une page dans votre navigateur. Elle est servie sur 127.0.0.1 uniquement tant que l'outil tourne, avec un jeton à usage unique dans l'adresse ; rien d'autre ne peut l'utiliser.
- `py -3 monitor_updater.py --tk` ouvre la même chose dans une fenêtre (Tkinter requis).
- `py -3 monitor_updater.py --console` est un menu texte pour les serveurs, SSH et conteneurs.
- `py -3 bin/monitor_cli.py update` est le même fichier lancé depuis le produit ; `update plan`, `update apply` et les autres commandes ci-dessous acceptent les options du tableau.

## Le menu Mises à jour dans le moniteur

L'édition Complète a le même outil de mise à jour dans sa page : **Système > Mises à jour**. Il montre la version installée et celle que la recherche a trouvée (réglage `updates.check` ; rien n'est demandé à GitHub tant qu'elle est désactivée ou que le moniteur est hors ligne), les notes de chaque version et, avec le bouton « Chercher des versions », la liste des versions publiées. Rien n'est téléchargé ni appliqué sans que vous appuyiez sur un bouton. Appliquer exige un administrateur sur l'ordinateur où tourne le moniteur (les routes `/api/updates/*` répondent 403 depuis le réseau) et une confirmation qui dit ce qui va se passer : le SHA-256 du zip comparé à SHA256SUMS, la copie faite d'abord (avec son dossier), la migration de la configuration et le redémarrage. La mise à jour tourne dans un processus à part : le moniteur s'arrête de lui-même, la mise à jour est appliquée, le moniteur redémarre avec la nouvelle version et la page se reconnecte ; si la nouvelle version ne démarre pas, la précédente est remise en place et démarrée. « Revenir à la version précédente » fait la même chose à l'envers. Les étapes, l'historique et le résultat s'affichent sur la page et sont notés dans le journal des actions. Elle n'est pas proposée dans l'édition Lite, dans un conteneur ni sous un gestionnaire de services (ils relancent le processus eux-mêmes : utilisez la ligne de commande), et une seule mise à jour tourne à la fois. Votre configuration, vos données, vos clés et vos journaux ne sont pas remplacés. Le fichier autonome reste le chemin de retour quand le moniteur ne démarre pas.

Sous un gestionnaire de services, la page n'applique pas les mises à jour par défaut. Si le moniteur tourne comme service UTILISATEUR systemd (`systemctl --user`), vous pouvez activer `updates.systemd_helper` (désactivé par défaut) : la page propose alors la mise à jour et le processus qui l'applique arrête ce service, applique la mise à jour et redémarre le service, toujours avec `systemctl --user` et jamais avec `sudo`. Un service système (qui demande l'administrateur) n'est pas touché et reste « utilisez la ligne de commande ». La même chose fonctionne en ligne de commande avec `--systemd-unit UNITÉ` (`apply` et `rollback`) ; si le service ne peut pas être arrêté, rien n'est lancé, et si la nouvelle version ne démarre pas, la précédente est remise et le service redémarré.

**Confiance.** La vérification compare le zip à SHA256SUMS, et les deux viennent de la même version GitHub : elle détecte un téléchargement abîmé ou incomplet, pas une version remplacée à la source. La confiance dans la version repose sur GitHub et sur votre propre compte là-bas.

## Ce qu'il fait, étape par étape Les routes qui le soutiennent sont `/api/updates/status`, `/api/updates/progress`, `/api/updates/history`, `/api/updates/log` (les dernières lignes du journal du processus, valeurs après token ou secret masquées), `/api/updates/copies` (lecture seule) et `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback`, `/api/updates/discard` (administrateur, depuis cet ordinateur seulement). La progression passe aussi en évènements envoyés par le serveur sur `/api/updates/stream` (la page l'utilise pendant une mise à jour et interroge toutes les secondes et demie si le navigateur ou la connexion ne le permettent pas).

1. Détecte l'installation : dossier, version, édition (Complète ou Lite), configuration, données, ports, moniteur en marche ou non, conteneur ou service.
2. Liste toutes les versions publiées sur GitHub (sans jeton) avec leur date et leurs notes, et repère l'installée et la dernière. Sans connexion, donnez-lui un zip avec `--zip`.
3. Vous choisissez la version cible. Une version plus basse est un retour en arrière : il faut `--allow-downgrade`.
4. Montre le PLAN en simulation : la chaîne d'étapes entre les deux versions (lue dans le registre des migrations), ce qui change dans VOTRE configuration, les changements de comportement que vous remarquerez et chaque incohérence trouvée.
5. L'applique : copie préalable, SHA-256 vérifié avec SHA256SUMS, zip extrait dans un dossier neuf et inspecté (chemins avec `..`, liens, taille), produit copié, vos propres lignes des lanceurs remises en place, configuration migrée, arborescence migrée et, si vous le voulez, moniteur démarré et `/api/health` vérifié.
6. Si quelque chose échoue, il revient seul à l'état précédent et écrit un rapport. Chaque mise à jour entre dans l'historique (`update_history.jsonl`) et la dernière peut être annulée avec la commande `rollback`.

## Commandes

Sans commande, la page s'ouvre. Les commandes répondent une fois (ajoutez `--json` pour un document) :

| Commande | Signification |
|---|---|
| `status` | ce qui est installé et ce que trouvent les contrôles |
| `releases` | toutes les versions publiées |
| `plan` | la simulation pour une cible |
| `apply` | l'exécuter (`--dry-run` montre seulement le plan) |
| `migrate` | migrer seulement un fichier de configuration, voir plus bas |
| `rollback` | revenir à la version d'avant la dernière mise à jour |
| `history` | les mises à jour faites sur cette installation |
| `copies` | les copies du dossier des copies : nom, état, versions, taille, et celle dont le retour en arrière a besoin |
| `discard` | `discard --name COPIE` supprime UNE copie après confirmation (`--yes` saute la question) ; la copie du retour en arrière seulement avec `--force` ; celle d'une mise à jour en cours, jamais |
| `log` | les dernières lignes (`--lines N`, 2000 au plus) du journal du processus de la dernière mise à jour, valeurs après token, secret ou password masquées |

## Options

| Option | Signification |
|---|---|
| `--dir` | l'installation (par défaut, là où se trouve le fichier, en remontant) |
| `--to` | version cible (par défaut, la dernière) |
| `--from` | migrate : la version d'où vient le fichier |
| `--config` | migrate : un fichier de configuration |
| `--zip` | utiliser ce zip au lieu de GitHub |
| `--sha256` | SHA-256 attendu du zip |
| `--dry-run` | montrer seulement le plan |
| `--apply` | migrate : écrire le résultat |
| `--yes` | ne pas demander de confirmation |
| `--json` | la réponse sous forme d'un document JSON |
| `--keep-old-defaults` | écrit l'ancienne valeur par défaut de chaque réglage jamais défini, pour que le comportement ne change pas |
| `--adopt-new-defaults` | déplace aussi vers la nouvelle valeur les réglages qui ont encore l'ancienne |
| `--start` | démarrer ensuite le moniteur et le vérifier |
| `--handover` | le moniteur qui a lancé ce processus s'arrête de lui-même : l'attendre, appliquer, le redémarrer (si le démarrage échoue, la version précédente revient) |
| `--status-file` | écrit la progression dans ce fichier JSON (le menu Mises à jour le lit) |
| `--edition` | complete ou lite, si on ne peut pas la déduire |
| `--allow-downgrade` | autoriser une version plus basse |
| `--allow-container` | travailler quand même dans un conteneur (l'image n'est pas remplacée) |
| `--no-gh` | ne pas utiliser le programme `gh`, seulement l'API publique |
| `--backups` | dossier des copies (par défaut, update_backups dans l'installation) |
| `--restore-data` | yes, no ou auto : ce que fait le retour avec les données |
| `--port` | port de la page |
| `--no-browser` | ne pas ouvrir le navigateur |
| `--tk` | la fenêtre |
| `--console` | le menu texte |
| `--lang` | langue : en es de fr it ja zh pt |

## Votre configuration et les valeurs par défaut qui changent

- Le registre des migrations (fichiers JSON versionnés dans chaque release, `assets/migrations/`) dit pour chaque version ce qui a changé : réglages renommés, supprimés ou nouveaux, nouvelles valeurs par défaut, fichiers déplacés, changements de comportement. L'outil applique la chaîne des versions que vous sautez.
- Par défaut il conserve ce que vous avez fixé explicitement et n'adopte une nouvelle valeur par défaut que là où vous n'aviez rien défini. Un changement de comportement (par exemple une fonction désormais désactivée par défaut) est signalé dans le rapport ; `--keep-old-defaults` fige l'ancien comportement, `--adopt-new-defaults` passe tout au nouveau.
- `migrate` travaille sur un fichier seul : `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config mon.json` montre le résultat et `--apply` l'écrit (après une copie). Les secrets sont masqués dans tout rapport.

## Contrôles avant d'appliquer

- Bloquants : le moniteur tourne, le SHA-256 ne correspond pas, le zip n'est pas sûr, espace disque insuffisant, données d'un schéma plus récent que la cible, un conteneur, une autre mise à jour en attente.
- Avertissements : réglages qui n'existent plus ou ont changé de type ou de plage, valeurs hors plage, clés en double, port pris par un autre programme, un lanceur que vous avez modifié, une étape qui en exige une autre avant. Chaque avertissement propose une action.

## Sécurité et retour en arrière

- Il n'écoute que sur 127.0.0.1 avec un jeton éphémère, refuse les requêtes venues d'autres sites, n'exécute rien du zip, n'utilise pas de shell et n'écrit que dans l'installation et le dossier des copies.
- Avant de modifier quoi que ce soit, il copie le paquet, la configuration et les données ; si une étape échoue la copie est restaurée et un rapport écrit. Si même le retour échoue, la copie reste intacte et le rapport explique comment la restaurer à la main.
- Hors ligne : `--zip FICHIER` avec `--sha256` (ou un SHA256SUMS à côté). Docker : le volume est mis à jour, l'image n'est pas remplacée de l'intérieur (`--allow-container` pour forcer).
- La page montre les copies et un bouton **Écarter la copie** pour chacune (il demande d'abord, et deux fois pour la copie du retour en arrière), et un bouton pour lire tout le journal du processus de la dernière mise à jour. Écarter supprime seulement cette copie, jamais l'installation ni les données, et c'est noté dans l'historique.

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | fait, ou rien à faire |
| 2 | mauvais usage |
| 3 | bloqué par un contrôle, rien n'a changé |
| 4 | échec du téléchargement, du SHA-256 ou du zip, rien n'a changé |
| 5 | échec et état précédent restauré |
| 6 | échec et le retour a échoué aussi : restaurez la copie à la main |
| 7 | pas de connexion à GitHub et pas de zip |
| 8 | non confirmé |

## L'avis nomme la commande de votre mode d'installation

L'avis d'une version plus récente (console, À propos, `/api/about`) donne maintenant la commande exacte du mode d'installation de ce moniteur, dans le champ `command` à côté de `channel` : le produit décompressé (`py -3 monitor/bin/monitor_cli.py update`), un gestionnaire de services (`... update apply --systemd-unit <unité>`), un conteneur (`docker pull ghcr.io/juanenrac/tools-github-actions-monitor:<version>`), pipx, uv ou une extension de la commande `gh`. L'avis n'exécute rien.
## Garde-fous de l'assistant de service

Avec `updates.systemd_helper` (ou `--systemd-unit`) le programme de mise à jour vérifie maintenant le service avant d'y toucher : une unité dont le répertoire de travail et la commande ne pointent pas vers CE dossier appartient à une autre installation et n'est ni arrêtée ni démarrée ; une unité n'est pas démarrée tant qu'autre chose (un moniteur au premier plan) répond sur son port ; un redémarrage n'est pas tenu pour fait tant que le processus est l'ancien (l'unité doit montrer un nouveau PID) ; et `update status --systemd-unit UNITÉ` ne liste que les erreurs du service depuis son dernier démarrage. Ce sont des questions en lecture seule à `systemctl --user show` et `journalctl --user` ; une question sans réponse ne bloque rien.
