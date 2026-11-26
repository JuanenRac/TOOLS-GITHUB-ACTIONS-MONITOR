<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La ligne de commande comme client du moniteur

`python bin/monitor_cli.py COMMANDE` demande au moniteur en marche ce qu'il sait (un `GET` sur `127.0.0.1`, ou sur l'adresse de `--url` / `MONITOR_URL`) et l'affiche. Elle ne refait pas le travail de la page auprès de GitHub, n'écrit jamais sur GitHub et ne change aucun réglage. Les anciens outils (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) continuent de fonctionner comme avant.

## Commandes

| Commande | Ce qu'elle montre | Lite |
|---|---|---|
| `status` | version, édition, compte, dépôts, ce qui tourne et échoue, le quota | oui |
| `health` (ou `check`) | un contrôle rapide avant de lire quoi que ce soit de lourd : le moniteur est-il joignable, accepte-t-il ce client, la connexion GitHub du compte répond-elle ? | oui |
| `doctor` | les contrôles de `--doctor` pour cette installation (le moniteur n'a pas besoin de tourner) | oui |
| `backup` | la sauvegarde complète de l'installation (le moniteur n'a pas besoin de tourner) : `backup create [FICHIER] [--account ID]`, `verify FICHIER [--deep]`, `restore FICHIER [--account ID] [--to-dir DOSSIER] [--force]`, `status`, `list` ; `--encrypt` avec `--key-env NOM` la chiffre (bibliothèque facultative) ; voir [OPS_fra.md](OPS_fra.md) | non |
| `accounts` | les comptes du superviseur (plusieurs comptes seulement) | non |
| `alerts` | les alertes de toutes les sentinelles dans une liste : `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` liste celles qui ont été ouvertes à un moment de cette durée, les closes aussi (depuis l'historique que le moniteur garde en fonctionnant ; une alerte compte comme close après dix minutes d'absence) | non |
| `proposals` | les actions que l'IA a proposées (`ai.actions.enabled`) : `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (un identifiant peut être abrégé). `approve` et `reject` ne font qu'enregistrer la décision ; `execute` l'exécute par la même porte que la page et demande `ai.actions.execute`, et avec `ai.actions.require_approval` une approbation d'abord. Approuver, rejeter et exécuter ne se font que depuis cet ordinateur Avec un seul utilisateur, `approve` exige `--code` et les huit premiers caractères de l'empreinte ; à plusieurs, approuvez dans la page avec votre session (deux personnes). | non |
| `score` | le score du compte : nombre, lettre, tendance, parties, couverture et ventilation par dépôt ; `--compare` le compare à l'historique de la fenêtre | non |
| `compare` | cette période contre la précédente : les chiffres avec leur variation et leur sens, qui se dégrade ou s'améliore ; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv` ; sortie 4 si un chiffre manque de données, 5 avec `--fail-on` si l'un se dégrade ; `--format csv` avec une autre commande est un mauvais usage (sortie 1) | non |
| `api` | l'API de lecture pour les clients : `api openapi` affiche le document OpenAPI de chaque route figée (redirigez-le vers un fichier), `api me` dit pour qui le moniteur prend ce client (mode, utilisateur, rôle, ce que la session peut faire, version du contrat) ; un moniteur dont `api.v1_enabled` est fermé le dit ; `api contract-check` lance contre lui la suite de contrat pour les clients (sortie 4 si une vérification échoue) | non |
| `team` | la santé des dépôts classés, d'abord ceux qui demandent une personne ; `--severity warn\|bad` garde les pires et `--repo owner/name` donne le détail d'un dépôt | non |
| `live` | l'état du récepteur de webhook et les derniers évènements | non |
| `ai` | `ai models [--refresh]` liste les modèles du fournisseur d'IA avec les données de chacun ; `ai test --provider NOM --model NOM` en essaie un avec un texte synthétique (latence, jetons, coût estimé) ; `ai doctor` dit pourquoi une IA ne répond pas, sans afficher de clé | non |
| `lessons` | ce que les échecs de cette CI ont appris : `lessons list`, `lessons brief --repo NOM` (à lire avant un push), `lessons failures`, `lessons close` | non |
| `briefs` | les briefs des onglets que lisent les outils d'IA : `briefs index`, `briefs show ONGLET`, `briefs all` | oui |
| `docs` | les guides de cette version, lus dans l'installation (sans moniteur) : `docs list` les nomme avec leur titre, `docs show NOM` en affiche un dans la langue de `--lang` | non |
| `screens` | le menu Écrans de la page : `screens list` (chaque type d'écran et s'il peut être ouvert) et `screens urls` (les adresses complètes, prêtes pour une commande de borne) | non |
| `keyring` | les clés publiques autorisées à signer : `keyring list`, `add` (`--key-id`, `--public-key`, `--key-scope`, `--expires`), `revoke --key-id`, `verify --document FILE` ; sans moniteur, les clés privées sont refusées | non |
| `verify-release` | un dossier de fichiers de version téléchargés, vérifié sans réseau avec SHA256SUMS et sa signature : `verify-release --folder DIR` ; sortie 4 s'ils ne sont pas fiables Aussi `--installed` (cette installation contre la nomenclature), `--attestations`, `--fetch` (nécessite `ops.verify_release.fetch`) ; `doctor --verify-release DIR` vérifie l'installation ; `keyring check-rotation --document FILE` vérifie l'annonce d'une nouvelle clé. | non |
| `toolbox` | les petits outils de l'opérateur qui fonctionnent sur cet ordinateur, sans moniteur lancé : `toolbox limits [N]` (la configuration face à ses plafonds), `toolbox workspaces` (les espaces de travail et celui utilisé), `toolbox ledger [--force]` (le registre des notifications déjà envoyées ; `--force` l'oublie), `toolbox summary` (les événements par type, dépôt et jour) et `toolbox export-events FILE` (les événements en jsonl, csv, parquet ou duckdb selon la fin du nom ; parquet et duckdb demandent leur paquet, le fichier doit être nouveau) | non |
| `credential` | une autre connexion GitHub pour un compte pendant que tout tourne : `credential replace\|reload [--account ID] [--new-token-file FICHIER\|-]` ; n'affiche jamais de jeton | non |
| `install-skill` | copie une skill du moniteur (`internal` ou `external`) dans le dossier où un outil d'IA lit ses skills : `install-skill external --dest DOSSIER` ; le moniteur n'a pas besoin de tourner | non |
| `gh-token` | affiche un jeton d'installation d'une heure de la GitHub App pour que les lectures d'un outil consomment le quota de l'App (seulement avec `github_app.share_reads` activé) ; à lancer sans `--json` | non |
| `watch` | la même lecture, encore et encore (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`) ; voir [CLI_OPERATOR_fra.md](CLI_OPERATOR_fra.md) | non |
| `completions` | le script de complétion pour `bash`, `zsh`, `fish` ou `powershell`, écrit à partir de l'analyseur réel (il se contente d'afficher) | non |
| `kiosk` | l'adresse du moniteur pour une télévision ou un mur (`ops`, `team`, `release`, `quiet`) ; voir [KIOSK_fra.md](KIOSK_fra.md) | non |
| `metrics` | les chiffres en lignes `nom=valeur` pour cron et le courrier ; avec `--if-problem` il n'écrit rien quand tout va bien ; voir [CLI_OPERATOR.md](CLI_OPERATOR.md) | non |
| `posture` | Posture des dépôts et de l'organisation, lecture seule (`posture status|matrix|check --repo-name`) ; voir [POSTURE.md](POSTURE_fra.md) | non |
| `external-ci` | Sources CI externes, lecture seule (`external-ci list|status|probe --source`) ; voir [EXTERNAL_CI.md](EXTERNAL_CI_fra.md) | non |
| `plugin` | Greffons : `plugin list|validate|pack|verify|init|install|enable|disable|uninstall|audit` ; voir [PLUGINS.md](PLUGINS_fra.md) | non |

Options de toutes les commandes : `--json` (la réponse comme un document JSON : `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (port 8766), `--timeout SECONDES` (1 à 60), `--lang CODE`. En mode réseau, mettez le jeton d'accès dans la variable d'environnement `MONITOR_ACCESS_TOKEN`, celle que lit le moniteur lui-même (`MONITOR_TOKEN` est accepté comme alias ; `--token JETON` est le dernier recours, car une option apparaît dans la liste des processus). L'ordre : `MONITOR_ACCESS_TOKEN`, puis `MONITOR_TOKEN`, puis `--token`. Il voyage dans l'en-tête `X-Monitor-Access`, jamais dans l'adresse ni à l'écran. Un `--url` en `http` non chiffré vers un autre ordinateur affiche un avertissement sur stderr (le jeton et les réponses circuleraient en clair) : utilisez `https` hors d'un réseau que vous contrôlez.

Chaque commande accepte aussi `--format text|table|plain|json|ndjson` (`--json` est `--format json`) ; voir [CLI_OPERATOR_fra.md](CLI_OPERATOR_fra.md).

La ligne de commande est un client de l'API de lecture pour les clients : les routes que le contrat fige (`docs/schemas/api_contract.json`) sont demandées d'abord sous `/api/v1/` et, si le moniteur y répond 404 (l'API est fermée, `api.v1_enabled`), l'ancienne route est demandée et le préfixe n'est plus essayé. Le document est le même par les deux chemins : la sortie d'aucune commande ne change. `cli.prefer_v1` (activé par défaut) le désactive, et la variable `MONITOR_CLI_PREFER_V1` (`0` ou `1`) l'emporte. Les routes que le contrat ne fige pas sont toujours demandées à l'ancienne.

Les heures écrites pour les personnes (la ligne `Last read`, les sourdines, le journal, les rapports, les notifications) utilisent le fuseau de cet ordinateur et le nomment, avec l'heure UTC à côté (`11:43:07 CET (10:43:07 UTC)`). Choisissez un autre fuseau avec `display.timezone` (`local`, `utc` ou un nom comme `Europe/Madrid` ; la variable d'environnement `MONITOR_TIMEZONE` l'emporte sur le fichier). `--json` garde l'UTC et ajoute `updated_local`.

## Codes de sortie (stables)

| Code | Signification |
|---|---|
| 0 | tout va bien |
| 1 | mauvais usage de la commande (aussi `--lite` avec une commande qui demande l'édition complète) |
| 2 | le moniteur est injoignable |
| 3 | le moniteur refuse ce client, ou la connexion GitHub du compte a échoué ou expiré (un problème d'identifiant, pas un quota épuisé) |
| 4 | le moniteur répond mais est dégradé : hors ligne, quota épuisé, pas encore de données, un point d'accès qu'il n'a pas, ou une réponse qui n'est pas du JSON |
| 5 | `alerts --fail-on NIVEAU` a trouvé une alerte ouverte de ce niveau ou pire (une alerte en sourdine ne compte pas) |
| 6 | `watch --exit-on-change` a vu un changement (seulement quand cette option est donnée) ; voir [CLI_OPERATOR_fra.md](CLI_OPERATOR_fra.md) |

Chaque erreur porte un `help` : une phrase avec l'étape suivante, qui nomme souvent le guide à lire (`docs show FIRST_STEPS`). En format texte, c'est la dernière ligne, qui commence par `aide :` ; avec `--json`, c'est le champ `help` à côté de `error` : `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Exemples

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` distingue trois choses : le moniteur ne répond pas (2), la connexion GitHub échoue (3), et le quota est épuisé ou GitHub est injoignable (4) ; un moniteur qui n'a pas fini sa première lecture le dit (4) au lieu de montrer des chiffres vides.

## L'édition lite

`python bin/monitor_cli.py status --lite`, `doctor --lite` et `health --lite` parlent au port 8766. Les commandes qui demandent des comptes, des sentinelles ou le récepteur de webhook sont refusées avec le code de sortie 1. L'édition lite n'a ni comptes ni API d'alertes.

## `ai-hook` : dire à un outil d'IA ce que voit le moniteur

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` n'a pas besoin d'un moniteur en marche. Il ajoute, montre ou retire le script de liaison `bin/ai_hook.py` dans les réglages de crochets d'un outil d'IA (voir le guide des alertes pour IA) : le fichier de réglages est fusionné, une copie est gardée et la réponse de `--json` est de l'ASCII pur. `status` est l'action par défaut.

## Le jeton d'accès en ligne de commande

En mode réseau le jeton est lu dans `MONITOR_ACCESS_TOKEN`, puis `MONITOR_TOKEN`, puis la première ligne de `--token-file FICHIER` (garde ce fichier lisible par toi seul : sur un système avec des modes de fichier la commande avertit si d'autres peuvent le lire) et enfin `--token`, qui apparaît dans la liste des processus et affiche donc un avertissement sur stderr.

## Les outils de stockage

`python tools/migrate_storage.py` déplace l'état entre fichiers et SQLite, et `python tools/backup_storage.py` fait, vérifie et restaure des sauvegardes de l'un ou l'autre (les deux sont décrits dans [STORAGE_fra.md](STORAGE_fra.md)). `--doctor` a deux vérifications pour eux : le stockage et la conservation.

## Le répartiteur par lots : les entrées d'un workflow

`python bin/gha_dispatch_all.py plan --inputs` liste aussi, sous chaque cible, les entrées que son workflow demande quand il est lancé à la main (nom, type, obligatoire ou facultative, valeur par défaut, options d'un choix et description). Elles sont lues dans le fichier du workflow à `origin/main` du clone avec `git show` : rien n'est déclenché, rien n'est envoyé et `gh` n'est pas appelé. `--json` ajoute une liste `inputs` à chaque ligne ; elle vaut `null` quand le fichier n'est pas dans `origin/main` ou utilise une forme que le lecteur ne connaît pas (le style en flux `inputs: {…}`), et `[]` quand le workflow ne demande aucune entrée.

## Sauvegarde et le doctor

`backup` et `doctor` travaillent sur les dossiers de l'installation, ils n'ont donc pas besoin d'un moniteur en marche. `doctor` sort avec `0` quand tout va bien (avertissements compris), `1` quand un contrôle a échoué, `3` quand il n'y a que des avertissements et que `--strict` (ou `ops.doctor.strict_exit`) est actif, et `4` quand le doctor lui-même n'a pas pu s'exécuter ; ce sont les codes du doctor, les autres commandes gardent les codes de sortie ci-dessus. `backup` sort avec `0` quand c'est fait et `1` quand il est refusé ou que le paquet ne se vérifie pas. Le guide [OPS_fra.md](OPS_fra.md) donne les contrôles, la restauration et la sauvegarde planifiée. Le doctor a aussi `compare_window` (la comparaison de deux périodes peut-elle remonter de deux fenêtres avec l'historique qu'elle demande et garde) et `etag` (la part des lectures conditionnelles répondues par 304 dans le moniteur qui tourne ici, et si les réponses de GitHub arrivent sans ETag).

## Identité d'un dépôt, plusieurs propriétaires

Ligne de commande : `identity status`, `identity plan`, `identity apply`.

```
python bin/monitor_cli.py identity plan
```
