<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# Extras facultatifs

Les deux sont **désactivés par défaut** et s'activent dans les Réglages.

## Le journal de l'étape en échec

`logs.failed_step.enabled` : une alerte d'une exécution en échec reçoit un bouton **Étape en échec**. Un appui lit chez GitHub les jobs et le journal d'échec de cette exécution (deux appels de votre quota), montre l'étape en échec et ses dernières lignes utiles (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) et garde la réponse en mémoire : appuyer de nouveau ne coûte rien. Le texte est nettoyé des jetons, clés, adresses et dossier personnel. Seuls les dépôts surveillés par le moniteur peuvent être demandés, par `GET /api/run-log?repo=&run=` ; en mode équipe, seulement un administrateur.

## Un jeton en lecture seule de l'App GitHub pour vos outils

`github_app.share_reads` : la commande ci-dessous affiche, sur cet ordinateur, un jeton d'installation de votre App GitHub valable une heure, pour que le `gh` de vos outils et agents lise avec le quota de l'App et non le vôtre (`GH_TOKEN`). Le jeton va seulement vers la sortie standard, jamais dans un fichier ni un journal, et la commande demande `--read-only` ; donnez à l'App des permissions en lecture seule à sa création. Sans `github_app.share_reads`, elle refuse. Le jeton est demandé à part de celui que garde le moniteur, avec des permissions en lecture seule ; si la réponse contient une permission d'écriture, la commande refuse de l'afficher.

```
python bin/monitor_cli.py gh-token --read-only
```

## Quatre rapports facultatifs

Les quatre sont désactivés par défaut. Ils apparaissent dans un bloc « Rapports facultatifs » en bas de l'onglet Alertes et dans `GET /api/reports`. Ceux qui lisent GitHub dépensent au plus `reports.max_calls_per_cycle` appels par cycle, lisent quelques dépôts à chaque fois et gardent ce qu'ils lisent en mémoire pendant un jour.

- `reports.workflow_hygiene.enabled` : lit les fichiers de workflow des dépôts et liste ce qui est mal écrit - actions non épinglées à un commit, permissions non limitées, un job sans `timeout-minutes`, pas de groupe `concurrency`, risques `pull_request_target` et injection, secrets en clair (les règles du linter du panneau A13, qui lit des clones locaux, plus les deux nouvelles).
- `reports.queue.enabled` : lit les jobs de quelques exécutions terminées qui ont attendu et dit combien un job a attendu avant de démarrer pour chaque sorte de runner (Linux, Windows, macOS, plus grands, auto-hébergés).
- `reports.release_view.enabled` : aucun appel ; d'après ce que sait le sentinelle, dit quels dépôts sont PRÊTS pour une version (entrées dans le changelog ou build vert que personne n'a publié, rien de rouge, aucune signature en attente) et lesquels sont BLOQUÉS, et pourquoi.
- `reports.supply_chain.enabled` : lit la dernière version des dépôts et dit, d'après les noms de ses fichiers, si elle porte une nomenclature logicielle (SBOM), des sommes de contrôle et une signature ou attestation. Les fichiers ne sont jamais téléchargés.
