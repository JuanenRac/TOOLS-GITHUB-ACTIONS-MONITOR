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

`github_app.share_token` : la commande ci-dessous affiche, sur cet ordinateur, un jeton d'installation de votre App GitHub valable une heure, pour que le `gh` de vos outils et agents lise avec le quota de l'App et non le vôtre (`GH_TOKEN`). Le jeton va seulement vers la sortie standard, jamais dans un fichier ni un journal, et la commande demande `--read-only` ; donnez à l'App des permissions en lecture seule à sa création. Sans `github_app.share_token`, elle refuse.

```
python bin/monitor_cli.py gh-token --read-only
```

## Pas encore là

Le panneau d'hygiène des workflows, le rapport de file d'attente, la vue version prête ou bloquée et le panneau de chaîne d'approvisionnement ne font pas partie de cette version.
