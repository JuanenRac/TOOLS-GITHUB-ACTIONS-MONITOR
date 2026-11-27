<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# Conformité : ce que vous pouvez démontrer sur votre installation

Tout est désactivé par défaut et réservé à l'édition complète, sauf les deux restrictions, qui valent pour tout processus du moniteur. Rien de cela n'est une certification.

## Mode lecture seule strict

`security.read_only_strict` (désactivé). Activé, rien n'est écrit sur GitHub quels que soient l'édition ou les autres réglages : seules les commandes de lecture de `gh` sont lancées (ce qui n'est pas connu comme lecture est refusé), ni `git push`, ni `act`, ni requête à l'API de GitHub autre que GET ou HEAD. Il est appliqué sous toutes les parties, par un crochet d'audit de Python qui voit chaque programme lancé. Modifiable seulement depuis l'ordinateur du moniteur ; l'assouplir demande un redémarrage. La fenêtre À propos et `/api/about` (`restrictions`) disent s'il est en vigueur.

## Politique réseau

`security.egress_policy` : `default`, `github_only` ou `none` ; `security.egress_allow` ajoute des hôtes (`nom`, `*.nom`, une adresse) ou `program:NOM`. Avec `github_only`, les processus du moniteur n'atteignent que `api.github.com`, `uploads.github.com`, l'hôte de `GH_HOST` (GitHub Enterprise) et ce que vous autorisez ; avec `none`, cet ordinateur seulement, et `gh` n'est pas lancé. Les programmes qui ouvrent le réseau eux-mêmes (`git` pour les commandes réseau, `apprise`, `curl`, `docker`, les outils des coffres de secrets) ne sont pas lancés. Une connexion refusée échoue avec une erreur qui nomme le réglage. `python bin/monitor_cli.py doctor` échoue quand une destination configurée sort de la politique, et `doctor --egress` liste toutes les destinations. Ce n'est pas un pare-feu : il ne régit pas les autres programmes de l'ordinateur. Les outils des coffres de secrets comprennent `sops` et `bws` : si le vôtre n'a pas besoin du réseau, ajoutez `program:sops` à `security.egress_allow`. Un fichier de configuration présent mais illisible ou incompréhensible restreint au lieu d'ouvrir : mode strict en lecture seule et `github_only` (ou `none` si son texte le demande), jusqu'à sa réparation et au redémarrage du moniteur ; le doctor le signale. `security.*` écrit dans `actions_monitor_lite.json` vaut aussi pour l'édition lite, en plus du fichier principal.

## Le rapport de conformité

`python bin/monitor_cli.py compliance report` (avec `--json`), `GET /api/compliance/report` (administrateurs) et un encadré à la fin de l'onglet Sécurité. Chaque ligne dit si elle est **vérifiée** (le moniteur a regardé) ou seulement **déclarée** (la configuration le dit) : version et prise en charge, édition, authentification et fournisseur d'identité, mode réseau et TLS, les deux restrictions et les destinations, conservation et conservation légale, journal des actions et sa chaîne, copies et leur chiffrement, chiffrement au repos (aucun), stockage, extensions, déploiement et profil. Ni secret, ni chemin, ni nom. `GET /api/compliance/state` donne les restrictions, le tableau de conservation et l'état de l'export. Une restriction toujours en vigueur est signalée même si le fichier ne la demande plus, et ce qui n'a pas pu être examiné apparaît comme `unknown`.

## Conservation et conservation légale

Événements, analyses et scores gardent leurs réglages (`retention.events_days`, `retention.analytics_days`, `retention.mode`). Les autres catégories sont gardées pour toujours sauf si vous leur donnez des jours : `retention.audit_days` (fichiers archivés entiers du journal des actions), `retention.reports_days` (le rapport le plus récent de chaque compte reste), `retention.ai_log_days`, `retention.backups_days` (la copie la plus récente reste). Chaque suppression laisse une ligne dans le journal des actions. `retention.legal_hold` arrête toute suppression : événements, analyses, scores, rapports, copies, la réduction du flux et du journal des prompts, ainsi que la rotation et la purge du journal. Les propositions de l'IA expirent seules ; les appareils appairés restent jusqu'à ce que vous les retiriez ; cette version ne garde ni postmortems, ni incidents, ni notes.

## Points de contrôle signés du journal des actions

`audit_checkpoints.enabled` (désactivé) signe la chaîne (HMAC-SHA256) avec une clé de l'installation : `config/audit_checkpoint.key`, ou le fichier nommé dans `MONITOR_AUDIT_KEY_FILE` pour la garder à part. Un point de contrôle à la première ligne puis au moins toutes les heures et toutes les 1000 lignes ; l'ancre est aussi signée, et une coupe de la fin suivie d'une nouvelle ligne est écrite dans la chaîne. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint` et `audit purge --older-than-days N` (`--dry-run`), qui supprime des fichiers archivés entiers et signe la suite de la chaîne. Qui peut lire la clé peut signer : tenez-la loin de qui peut écrire le journal.

## Export du journal des actions

`audit_export.enabled` (désactivé) avec `audit_export.target` = `file` (`path`, rotation à `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 sur TCP avec TLS, `ca_file`) ou `http` (`url`, POST de lignes JSON, jeton de la variable nommée dans `token_env`). Les adresses privées demandent `audit_export.allow_private_targets`. Le journal est la file d'attente : ce que la destination n'a pas pris y attend ; au-delà de `spool_mb`, le doctor signale `system.audit_export_lag`, et les lignes archivées avant envoi sont comptées comme perdues. `python bin/monitor_cli.py audit export` fait un passage immédiat. Testé avec des récepteurs de cet ordinateur, pas avec un vrai produit syslog ou SIEM.

## Versions prises en charge

Seule la dernière version publiée est prise en charge : il n'y a pas de branche à long terme. Le doctor (`compliance_support`) avertit quand il en connaît une plus récente.

## Preuves du durcissement

`[IMP]` = un test de ce dépôt exerce le contrôle ; `[PAR]` = seule une partie est exercée, et la ligne dit ce qui manque. La liste est `schemas/controls.json` et un test vérifie que ce tableau et les tests nommés concordent.

| Contrôle | État | Nom |
|---|---|---|
| `sqlite_contention` | [IMP] | Plusieurs processus écrivant une base |
| `storage_migrations` | [IMP] | Migrations du stockage |
| `retention_by_category` | [IMP] | Conservation par catégorie et légale |
| `incoming_webhook` | [IMP] | Webhook entrant : signature, taille, temps |
| `metrics_labels` | [IMP] | Étiquettes de /metrics |
| `timezone` | [IMP] | Fuseaux et changement d'heure |
| `read_only_strict` | [IMP] | Lecture seule stricte |
| `egress_policy` | [IMP] | Politique réseau |
| `audit_chain` | [IMP] | Chaîne et points de contrôle du journal |
| `service_and_volume` | [PAR] | Service systemd, grande base (systèmes de fichiers réseau non testés) |

## Limites connues

- Un compte `viewer` assis à l'ordinateur même du moniteur est traité comme local et voit les chemins complets.
- Le webhook entrant ne vérifie la fenêtre de temps que pour les livraisons `workflow_run` et `workflow_job`.
- Avec `none` ou `github_only`, un processus Python lancé par le moniteur n'applique la politique que s'il importe le moniteur ; un programme que vous lancez vous-même en est exclu.
- Le chiffrement au repos, une branche à long terme et la fédération n'existent pas dans cette version.
