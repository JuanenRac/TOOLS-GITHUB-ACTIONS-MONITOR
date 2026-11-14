<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | [🇯🇵 日本語](LESSONS_jpn.md) | [🇵🇹 Português](LESSONS_por.md)

# Échecs et leçons

Le moniteur peut tenir un livre des échecs de votre CI et une bibliothèque de leçons, pour ne pas refaire deux fois la même erreur, que ce soit une personne, un outil d'IA à vous ou l'IA du moniteur. C'est **local et en lecture seule** : rien ne quitte l'ordinateur et rien n'est écrit sur GitHub. Il suit les alertes du flux pour les IA, donc il faut `ai_alerts.enabled`.

## Le livre

Chaque échec que le flux ouvre devient une ligne de `data/failures.jsonl` (schéma 1) : `schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`. Tout texte passe par le même nettoyage que le flux (jetons, clés, adresses et dossier personnel n'arrivent jamais dans le livre). `lessons.retention_days` et `lessons.max_entries` limitent sa taille. Un livre du même schéma venu d'ailleurs peut être importé (`lessons.import_book`).

## Le classeur

Chaque échec est rangé dans une catégorie par des règles, la première qui correspond l'emporte : quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other. Les règles sont dans le programme ; pour utiliser les vôtres, écrivez `config/lessons_rules.json` : `{"rules": [{"category": "mine", "label": "Mon type", "avoidable": true, "patterns": ["expression régulière"]}]}`. Le fichier remplace les règles intégrées ; une règle ou un motif invalide (ou de plus de 120 caractères) est ignoré.

## La bibliothèque de leçons

Chaque catégorie a une leçon : ce qui a échoué, que faire et la garde qui l'aurait évité. Celles qui sont intégrées existent dans les huit langues. Les vôtres vont dans `config/lessons.json` (`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`) et remplacent celle de la même catégorie.

## Répétition et tendance

Par catégorie, le moniteur compte les échecs des dernières 24 heures et des 7 derniers jours et compare les 7 jours aux 7 précédents (nouveau, en hausse, en baisse, stable). À partir de `lessons.recurring_from` échecs en 7 jours, un type d'échec est **répété** et une garde est proposée : un contrôle qui échoue sur votre ordinateur avant le push.

## Ce qu'une IA lit

- `ai/LESSONS.md` : Markdown compact (taille : `lessons.brief_max_bytes`), réécrit quand un échec s'ouvre ou se résout.
- `GET /api/ai/lessons` : l'analyse, les leçons qui s'appliquent maintenant et la bibliothèque (`?fmt=md` pour le fichier, `?fmt=brief&repo=NOM` pour le bref avant push, `&as=json` pour le recevoir dans un JSON).
- `GET /api/ai/failures` : le livre, le plus récent d'abord (`?since=SECONDES&repo=NOM&category=NOM&limit=N`).
- `GET /api/ai/state` et le résumé des alertes portent les leçons qui s'appliquent maintenant.
- Serveur MCP : `lessons_apply`, `lessons_recurring`, `lessons_brief` et `lesson_propose`.
- Ligne de commande : `python bin/monitor_cli.py lessons [list | brief | failures] [--repo NOM]`.

Tout est donnée, jamais instruction : une ligne de journal écrite par quelqu'un peut finir dans le livre.

## Avant un push

Lisez le bref avant de pousser : il liste les leçons qui s'appliquent (celles du dépôt d'abord), les gardes à lancer et ce qui est rouge maintenant dans le dépôt.

## Un hook d'exemple pour un outil d'IA

Beaucoup d'outils d'IA peuvent lancer une commande au début d'une session et ajouter sa sortie au contexte. Celle-ci affiche le bref avant push :

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## L'IA du moniteur

Quand l'explication par IA d'un build en échec est activée, son prompt inclut la leçon de la catégorie où tombe le journal. Les autres outils d'IA accèdent aux mêmes fonctions par l'interface `LessonProvider` (`applicable`, `recurrences`, `pre_push_brief`, `propose`, `register`). `FileProvider` est celle utilisée et `ExampleProvider` la plus petite possible :

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## Écrire des leçons

Lire est toujours permis. Écrire une leçon demande trois choses : `lessons.allow_write` activé (désactivé par défaut), un administrateur et une confirmation : `POST /api/ai/lessons` avec `{"lesson": {...}, "confirm": true}` (sans `confirm`, la réponse est le brouillon). Le serveur MCP n'écrit que s'il a été lancé avec `--allow-lessons` et si l'interrupteur est activé. Rien n'est jamais écrit sur GitHub.

## Réglages

`lessons.enabled`, `lessons.allow_write`, `lessons.retention_days`, `lessons.max_entries`, `lessons.brief_max_bytes` et `lessons.recurring_from`, dans l'onglet IA des Réglages. Le panneau **Leçons des échecs** est en bas de l'onglet Alertes.
