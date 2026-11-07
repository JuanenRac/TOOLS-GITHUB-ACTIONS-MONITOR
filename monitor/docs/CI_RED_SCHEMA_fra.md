<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - schéma 2 (contrat stable)

`ci_red.json` est l'instantané que le moniteur écrit (de façon atomique, à côté de lui-même par défaut) afin que n'importe quel consommateur puisse lire l'état de la CI sans interroger
le moniteur ni GitHub : un tableau de bord, un script, un hook de notification. Le format est **stable : les champs sont seulement ajoutés, jamais renommés ni supprimés**.
Lisez-le avec `.get()` ; ignorez les champs que vous ne connaissez pas.

L'emplacement d'écriture se définit dans `actions_monitor.json` :

| clé (`sentinel.`) | signification |
|---|---|
| `ci_red_file` | `""` = `ci_red.json` à côté du moniteur (par défaut) ; `"off"` = non écrit ; un chemin = écrit à cet endroit (les chemins relatifs sont relatifs au dossier du moniteur ; un lecteur D:, un chemin UNC ou un lecteur que le système en cours d'exécution ne peut pas utiliser est refusé) |
| `ci_red_audit_copy` | `true` le copie aussi dans le dossier d'audit lorsque ce dossier existe |

## Structure

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
  "tool_version": "1.2.0",
  "complete": true,
  "red_repos": 1,
  "pending_sign_repos": 1,
  "pending_sign_hours_threshold": 24,
  "repos": {
    "REPO": {
      "ecosystem": "armor | urtc | hydra | eh3d | other",
      "red": [{"workflow": "CI", "conclusion": "failure", "since": "2026-01-01T10:00:00Z", "streak": 2, "url": "https://github.com/OWNER/REPO/actions/runs/1"}],
      "pending_sign_hours": 31.5,
      "pending_sign": [{"workflow": "firmware-build.yml", "hours": 31.5, "state": "built_on_gha | signed_local",
                         "signature_kind": "none | dev | release", "signature_verified": true,
                         "last_build_at": "2026-01-01T08:00:00Z", "url": "https://github.com/OWNER/REPO/actions/runs/2"}]
    }
  }
}
```

* `complete` vaut `false` tant que la sentinelle est encore en cours de chargement : dans ce cas, ne considérez pas un dépôt manquant comme vert.
* `signature_verified` vaut `true`, `false` ou la chaîne `"unknown"` (jamais une supposition : les formats que cet outil ne peut pas vérifier sont `"unknown"`).
* Les champs `pending_sign*` décrivent le **côté signature locale** et sont destinés à vos propres outils locaux. Un consommateur public doit les ignorer.

## La règle du « rouge » (une seule définition, partout)

On examine la **dernière exécution terminée de chaque workflow sur la branche par défaut**. Elle est rouge lorsque sa conclusion est `failure`, `timed_out`,
`startup_failure` ou `action_required` (elle attend une approbation). `cancelled`, `skipped`, `neutral` et `stale` ne disent rien et sont ignorées.
Le « vert » de l'état de signature utilise la même liste d'exécutions. Un consommateur qui recalcule la règle à partir des exécutions des workflows doit employer exactement cette
définition pour concorder avec le moniteur.

## La publication est une étape distincte et explicite

**Décision : ce PC ne publie pas `ci_red.json` et ne publie ni `pending_sign` ni aucune autre partie du côté signature dans un dépôt, un tableau de bord ou un
service quelconque.** Le fichier reste sur la machine (et, lorsque `ci_red_audit_copy` est activé, dans le dossier d'audit local). Un tableau de bord public doit recalculer la liste des workflows rouges à partir des
exécutions publiques des workflows avec la règle ci-dessus, ou utiliser l'export décrit ci-après, qui ne contient jamais l'état de signature.

Rien dans le moniteur ne publie ce fichier dans un dépôt. Si un tableau de bord public a besoin de la liste des workflows rouges, laissez-le soit recalculer la règle à partir des
données publiques des exécutions, soit exportez vous-même la partie non sensible :

```
python3 read_report.py --export-status DIR
```

Cette commande écrit `ci_status_public.json` et `ci_status_public.md` dans le dossier que vous indiquez, et **uniquement** la liste des workflows rouges (dépôt,
écosystème, workflow, conclusion, depuis quand, série, lien vers l'exécution). Aucun état de signature, aucun nom de clé, aucun chemin local, aucune commande. L'outil ne fait jamais de commit ni de
push ; ce qu'il advient ensuite du dossier relève de vous.

`python3 read_report.py --export-sign-queue FILE` (`.json` ou `.csv`) écrit la file de signature globale avec les commandes locales exactes. Ce fichier est
destiné au PC qui exécute le moniteur et l'indique à l'intérieur.
