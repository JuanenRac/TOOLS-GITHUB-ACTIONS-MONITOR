<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# Exploiter l'installation

Pour un moniteur laissé en marche pendant des mois (édition Complète). Ce guide couvre la sauvegarde complète, la restauration, la sauvegarde planifiée, le doctor avec des codes de sortie sur lesquels un cron peut compter, et la mise en place comme appliance (systemd ou Docker). L'édition Lite n'a rien de tout cela.

## Le paquet de sauvegarde

`python bin/monitor_cli.py backup create [FICHIER]` écrit UN `.zip` (format 2) et le vérifie avant de le mettre en place. Sans `FICHIER`, il va dans le dossier `backups` du dossier de données (`ops.backup.dir`) sous le nom `ghamon-backup-<heure UTC>.zip`. Il n'est pas nécessaire d'arrêter le moniteur : les données sont lues avec les lectures atomiques du stockage (fichiers ou SQLite), jamais en copiant une base en cours d'écriture.

| Membre | Ce qu'il contient |
|---|---|
| `dump.jsonl` | chaque compte (ses réglages, l'état des sentinelles, les petits documents, les événements, les analyses, les instantanés du score) et les enregistrements globaux (utilisateurs et comptes qu'ils peuvent voir ; jamais les sessions) |
| `files.json` | les réglages de la page et les listes de l'installation (`targets.json`, `ecosystems.json`, `profiles.json`, les silences), nettoyés ; aussi les magasins des modules facultatifs s'ils existent (`proposals.json`, `devices.json`) |
| `manifest.json` | le format, la version du produit, le schéma, les comptages et la taille et le SHA-256 de chaque membre |

**Ce qui ne voyage jamais :** jetons et clés de GitHub ou d'une App, mots de passe, la valeur de toute variable `*_env` (seulement son nom), le secret du webhook, les clés des fournisseurs d'IA, les sessions et le contenu du magasin de secrets. Les réglages passent par une liste blanche (les mêmes clés que la page des Réglages peut montrer) puis par un nettoyage qui écarte toute clé qui ressemble à un secret et tout texte qui ressemble à un jeton ou à une clé privée. Avec `ops.backup.include_config` désactivé, les réglages et les listes restent entièrement dehors. Une restauration ne ramène aucun identifiant : remettez l'accès à GitHub en place (sa liste de tâches le dit).

La sauvegarde n'est lisible que par son propriétaire (mode 600) et le paquet n'est pas chiffré sauf demande : voir ci-dessous.

### Un paquet d'un seul compte

`backup create --account ID [FICHIER]` écrit le paquet d'UN compte : son dump (avec ses réglages, nettoyés de la même façon) et rien d'autre. Il ne contient aucun utilisateur ni session, ni les réglages ou listes de l'installation ; le manifeste dit `scope: account`. `backup verify` contrôle qu'il ne contient que ce compte, et `backup restore FICHIER` restaure ce compte (`--account` n'est pas nécessaire) sans toucher aux autres comptes, aux utilisateurs ni aux fichiers de la destination ; il n'est refusé que si ce compte y existe déjà et qu'il n'y a pas `--force`. C'est la façon de déplacer ou de récupérer un seul compte.

### Chiffrer la sauvegarde (facultatif)

`ops.backup.encrypt` (ou `--encrypt` pour une sauvegarde) chiffre le paquet en AES-256-GCM avec une clé prise dans la variable d'environnement que désigne `ops.backup.key_env` (`--key-env NOM`). La clé n'est jamais un réglage, n'est jamais écrite et n'est jamais sur une ligne de commande. Il faut la bibliothèque facultative `cryptography` (`pip install cryptography` ; le cœur du moniteur reste en bibliothèque standard seule). Sans la bibliothèque, ou sans clé de 12 caractères ou plus, la sauvegarde est **refusée** avec un message clair et rien n'est écrit : on ne fait jamais une sauvegarde en clair quand vous en avez demandé une chiffrée, ni une chiffrée avec quelque chose de plus faible. Un fichier chiffré se termine par `.enc` ; `verify` et `restore` l'ouvrent avec la même variable. Gardez la clé séparée du fichier : sans elle la sauvegarde ne s'ouvre pas.

## Vérifier, lister et état

- `backup verify FICHIER` relit le paquet et contrôle chaque taille et chaque SHA-256 ainsi que les comptages. Un octet modifié, un membre manquant ou un membre que le manifeste ne liste pas est signalé. `--deep` le restaure en plus dans un dossier temporaire et contrôle le résultat.
- `backup list` montre les sauvegardes du dossier ; `backup status` montre la dernière bonne sauvegarde, son âge, la planification et le dernier échec.
- Un paquet du premier format (fait avant la 2.1.0) se vérifie et se restaure toujours.

## Restaurer

`python bin/monitor_cli.py backup restore FICHIER` : arrêtez d'abord le moniteur (la restauration est refusée tant qu'un moniteur répond sur son port). Elle vérifie le paquet, puis écrit les comptes et les fichiers.

- Un stockage qui contient déjà des comptes est refusé sauf si vous ajoutez `--force` (les comptes du paquet sont alors écrits par-dessus ; les réglages sont **fusionnés** : une clé que le paquet ne porte pas n'est jamais supprimée).
- `--account ID` restaure ce seul compte et laisse les autres et les fichiers globaux comme ils sont (refusé seulement quand ce compte existe et qu'il n'y a pas `--force`).
- `--to-dir DOSSIER` restaure dans un dossier vide (backend de fichiers) sans toucher à l'installation : la façon de regarder une sauvegarde ou de déménager vers une autre machine.
- Elle écrit `ops/restore_report.json` dans le dossier de données et affiche ce qui reste à faire : remettre l'accès à GitHub, refixer les réglages que le paquet a laissés de côté, redémarrer le moniteur pour que le superviseur lance chaque compte, lancer le doctor.

## La sauvegarde planifiée

Deux façons, utilisez-en une :

1. Dans le moniteur : `ops.backup.enabled` (désactivé par défaut) fait une sauvegarde toutes les `ops.backup.interval_hours` dans un thread à part, garde les `ops.backup.keep` plus récentes (seuls les fichiers portant un nom de sauvegarde sont supprimés) et note le résultat dans `ops/backup_status.json`. Un échec (disque plein, clé manquante) est noté et montré dans le panneau À propos et dans le doctor ; il n'arrête jamais le moniteur.
2. Avec systemd : `deploy/github-actions-monitor-backup.service` et `deploy/github-actions-monitor-backup.timer` (voir ci-dessous).

Le panneau À propos a une carte **Exploitation** avec le mode (service ou local), la dernière bonne sauvegarde, la planification, la rétention en vigueur et le bouton **Sauvegarder maintenant** (un administrateur, depuis cet ordinateur). `GET /api/ops/status` donne les mêmes données ; `POST /api/ops/backup` fait une sauvegarde.

## Purge à la demande

La purge de rétention s'exécute seule toutes les `retention.interval_hours`. Pour la lancer maintenant, il y a un bouton (et `POST /api/ops/purge`) qui **n'existe pas** tant que `ops.purge.enabled` n'est pas activé (désactivé par défaut). Une requête est un essai à blanc (la politique en vigueur et combien d'événements partiraient) sauf si elle dit `dry_run` false, et une vraie purge est refusée sans une bonne sauvegarde plus récente que `ops.purge.require_backup_hours` (24 par défaut ; 0 n'exige rien). Elle laisse sa ligne dans l'audit de la rétention et dans le journal des actions.

## Le doctor et ses codes de sortie

`python bin/monitor_cli.py doctor [--strict] [--json]` (ou `python bin/actions_monitor.py --doctor`) vérifie l'installation, ne change rien et n'affiche aucun secret. L'édition Complète ajoute ces contrôles après les contrôles habituels :

| Contrôle | Ce qu'il regarde |
|---|---|
| `volumes` | un fichier est vraiment écrit, lu et supprimé dans les dossiers de données, de journaux et de sauvegardes (un volume Docker monté en root ou en lecture seule échoue ici) |
| `supervisor` | un moniteur en marche : la santé approfondie du superviseur et de chaque cycle de rafraîchissement (rien n'est lancé) |
| `limits` | le secret du webhook est défini et fait au moins `ops.doctor.webhook_min_length` caractères (seule la longueur est comparée) et la politique de rétention |
| `sqlite_hot` | chaque base SQLite ouverte en lecture seule : `quick_check` (par défaut) ou `integrity_check` (`ops.doctor.sqlite_check` deep), interrompu à `ops.doctor.sqlite_timeout_s` ; un fichier corrompu après une coupure de courant échoue |
| `backup_age` | la dernière bonne sauvegarde face à `ops.doctor.backup_max_age_days` |
| `disk` | espace libre du volume de données face à `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` répond quand la sortie Prometheus est activée et qu'un moniteur tourne |

**Codes de sortie (stables, pour cron) :** `0` tout va bien (avertissements compris, sans `--strict`) ; `1` au moins un contrôle a échoué ; `3` seulement des avertissements et `--strict` (ou `ops.doctor.strict_exit`) ; `4` le doctor lui-même n'a pas pu s'exécuter. Ce sont les codes du doctor ; les autres commandes de `monitor_cli.py` gardent les leurs. Exemple : `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` et alertez sur tout code autre que 0.

## Comme appliance

**systemd** (sans conteneur) : suivez les commentaires de `deploy/github-actions-monitor.service`, puis installez l'unité de sauvegarde et son minuteur :

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

Pour une sauvegarde chiffrée, mettez la variable que désigne `ops.backup.key_env` dans `/etc/github-actions-monitor/env` (mode 600). Le minuteur lance `backup create` chaque jour ; son code de sortie est 1 quand la sauvegarde n'a pas pu être faite.

**Docker :** `deploy/compose.yaml` garde les sauvegardes dans un volume à part (`monitor-backups` sur `/data/backups`) pour que la perte du volume de données ne les emporte pas. Sortez un fichier avec `docker compose exec monitor python bin/monitor_cli.py backup list` et `docker cp`, et restaurez dans un conteneur arrêté ou avec `--to-dir`. Le TLS est renouvelé par le Caddy de `deploy/Caddyfile`.

**Mettre à jour sans perdre les comptes :** `backup create` → `backup verify FICHIER` → arrêter le moniteur → remplacer le dossier du produit (les dossiers `config/`, `data/`, `logs/` et `ai/` sont à vous et sont conservés) → `doctor` → démarrer. Si quelque chose se passe mal, `backup restore FICHIER`. **Le retirer proprement :** arrêtez et désactivez les unités, retirez le minuteur, puis le dossier du produit et, seulement si vous voulez perdre les données, les dossiers `config/`, `data/` ou les volumes Docker.

## Réglages

Tous sont dans l'onglet Réglages (Dossiers et fichiers) et dans [SETTINGS_fra.md](SETTINGS_fra.md) : `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) et `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Chaque interrupteur commence désactivé ou prudent, et ceux de sécurité (la sauvegarde planifiée, l'inclusion des réglages, le chiffrement, la purge) sont marqués comme tels.

Voir aussi [STORAGE_fra.md](STORAGE_fra.md) (les backends et la rétention), [DEPLOYMENT_fra.md](DEPLOYMENT_fra.md) (service, conteneur, TLS) et [CLI_fra.md](CLI_fra.md).
