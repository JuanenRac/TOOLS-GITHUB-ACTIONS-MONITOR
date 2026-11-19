<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | [🇪🇸 Español](STORAGE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](STORAGE_ita.md) | [🇩🇪 Deutsch](STORAGE_deu.md) | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# Stockage et conservation

Où l'édition complète garde ce qu'elle apprend, comment le changer et ce qu'elle supprime d'elle-même. L'édition lite garde toujours de simples fichiers, n'a ni base de données ni tâche de conservation et n'affiche rien de tout cela.

## Ce qui est conservé

Pour chaque compte : la configuration (`actions_monitor.json`), l'état des sentinelles, le flux d'événements, ce que le flux a déjà annoncé, les échantillons d'analyses, les mises en sourdine et l'avis de mise à jour. Pour toute l'installation : les utilisateurs, les comptes qu'ils peuvent voir et leurs sessions (le mode équipe les utilise). Les caches de lectures conditionnelles et les journaux sont toujours de simples fichiers.

## Les deux stockages

|  | `file` (par défaut) | `sqlite` |
|---|---|---|
| Où | `data/accounts/<id>/` (les fichiers de `data/` et `config/` s'il n'y a pas de `accounts/`) | `accounts/<id>/storage.sqlite3`, une base par compte |
| Écritures | un fichier temporaire, vidé sur le disque, puis renommé | une courte transaction, journal WAL |
| À choisir pour | une personne ; des fichiers lisibles et modifiables | un service qui tourne pendant des mois ; beaucoup d'événements |

Le choix se fait dans la configuration du compte (ou du moniteur) : `"storage": {"backend": "sqlite"}`. La configuration elle-même reste toujours un fichier JSON, car c'est elle qui nomme le stockage. Avec SQLite, le flux d'événements est dans la base, pas dans `events_monitor.jsonl`. Une base qui ne peut pas être ouverte empêche le démarrage : le moniteur n'écrit jamais son état ailleurs dans votre dos.

## Décision : un stockage par compte (modèle A)

*Contexte.* L'édition complète lance un processus par compte. *Décision.* Chaque processus a son propre stockage : ses fichiers, ou sa propre base `storage.sqlite3` dans `accounts/<id>/`. Deux processus n'écrivent jamais le même fichier : rien à verrouiller entre eux, et un problème dans un compte ne peut pas en abîmer un autre. *Coût.* Une question portant sur plusieurs comptes oblige à lire plusieurs bases.

*Gardé prêt : modèle B, une base partagée.* Mettez le même chemin dans le bloc `storage` de chaque compte (`"path": "/data/monitor.sqlite3"`). Cela fonctionne parce que chaque table porte le compte, que WAL laisse la page lire pendant que les sentinelles écrivent, que les transactions sont courtes et qu'une base occupée est attendue jusqu'à 5 secondes. C'est testé (deux processus qui font leur cycle en même temps ; une page qui répond en HTTP pendant qu'ils écrivent) mais ce n'est pas le défaut : plus fragile que A, il ne vaut que si vous avez besoin de SQL entre comptes.

## Ce qui est garanti

- Une écriture est atomique : un lecteur voit l'ancienne valeur ou la nouvelle. Un processus tué en plein travail (`kill -9`) laisse l'ancienne valeur ; avec SQLite, le démarrage suivant se rétablit tout seul.
- Le schéma est versionné (`schema_version`). Chaque migration s'exécute dans une seule transaction avec le changement de version : une migration interrompue laisse la base comme elle était et reprend au démarrage suivant. Une base écrite par une version plus récente est refusée, jamais rétrogradée.
- Un élément abîmé ou absent se lit comme vide : le moniteur démarre avec ce qu'il y a sur le disque.

Chaque enregistrement que garde le moniteur (l'état des sentinelles, les silences, l'état du flux, l'avis de mise à jour) porte `schema_version` en tête de son objet. Un enregistrement antérieur à la marque se lit comme la version 0, comme toujours. Un enregistrement d'une version PLUS RÉCENTE que celle que comprend le programme n'est jamais lu à moitié : il est mis de côté, le programme repart de ses valeurs par défaut pour cet enregistrement et le fichier est nommé dans la liste des dégradations (`records.newer`) ; un retour en arrière dit donc quel fichier il n'a pas compris au lieu de le mal lire.

## Déplacer les données et sauvegardes

```
python tools/migrate_storage.py --from file --to sqlite              # simulation : montre ce qui serait copié
python tools/migrate_storage.py --from file --to sqlite --apply      # copie, puis compare chaque élément et chaque événement
python tools/backup_storage.py backup backup.zip --backend sqlite    # un .zip avec manifeste et SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # dans un stockage vide (--force sur des comptes existants)
```

La migration ne modifie ni ne supprime jamais vos fichiers, reprend après une interruption (un compte est copié entièrement ou pas du tout) et se termine par un échec si les deux côtés diffèrent ; ensuite seulement, changez le stockage et redémarrez. Une sauvegarde faite depuis des fichiers se restaure dans SQLite et inversement. `--db FILE` choisit la base partagée du modèle B ; `--flat` est l'installation sans `accounts/`. `--doctor` vérifie la base (présente, intégrité, schéma) sans la modifier. Relancer la même commande est sans danger : un compte dont la cible contient déjà des événements ou des instantanés plus récents que la source est refusé (`la cible a des données plus récentes`, code de sortie 1, rien n'en est écrit) afin de ne pas effacer ce qui a été fait après la première copie ; `--force` fait gagner la source.

## Conservation

Un moniteur laissé en marche pendant des mois grossirait sans plafond ; un court passage à la fin d'une actualisation (toutes les `retention.interval_hours`, 24 par défaut) supprime donc ce qui est ancien :

| Réglage | Défaut | Signification |
|---|---|---|
| `retention.enabled` | activé | l'interrupteur |
| `retention.events_days` | 90 | les événements plus anciens sont supprimés |
| `retention.analytics_days` | 180 | les jours de l'historique d'analyses plus anciens, ainsi que les instantanés du score de ces jours, sont supprimés |
| `retention.mode` | `archive` | `archive` écrit d'abord les anciens événements dans un `.gz` de `events/archive/` |
| `retention.events_max_kb` | 512 | plafond de taille du fichier du flux avec le stockage en fichiers (comme toujours) |
| `retention.warn_events_mb` | 20 | `--doctor` avertit au-delà de cette taille |

La purge ne touche que les événements et les jours d'analyses plus anciens que leur limite ; elle ne touche jamais la configuration, l'état des sentinelles, les mises en sourdine ni un événement sans heure. Chaque passage laisse une ligne dans le document d'audit (quand, combien d'événements supprimés et conservés, le fichier d'archive, combien de jours d'analyses, l'erreur éventuelle). `--doctor` avertit de la taille des événements et, pour un moniteur qui tourne comme service (mode réseau, sans navigateur, un conteneur ou `MONITOR_SERVICE=1`), quand sa configuration n'a pas de bloc `retention`. Faites une sauvegarde avant de raccourcir les limites.

Par défaut (`archive`), ce qui est retiré reste dans des fichiers compressés relisibles ; `delete` le supprime définitivement.

## Le paquet de sauvegarde complet

`python bin/monitor_cli.py backup create` écrit le paquet de toute l'installation (format 2) : le dump de chaque compte et des enregistrements globaux plus les réglages et les listes nettoyés, avec la taille et le SHA-256 de chaque membre. Il peut être chiffré avec une clé issue d'une variable d'environnement (bibliothèque facultative), vérifié (`backup verify`, `--deep` le restaure dans un dossier temporaire), listé, restauré par compte ou dans un dossier, et fait de façon planifiée (`ops.backup.enabled`). `tools/backup_storage.py` fait le même paquet pour un dossier de comptes (`--account` pour un seul compte) et vérifie et restaure toujours les sauvegardes simples du premier format. Le guide [OPS_fra.md](OPS_fra.md) donne tout.
