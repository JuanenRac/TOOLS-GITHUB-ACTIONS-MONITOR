<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# Rapports planifiés

Complete seulement, désactivé par défaut. Le moniteur peut écrire un rapport du compte selon un horaire ou à la demande : le score, ce qui a changé depuis le dernier rapport, les dépôts qui demandent une personne et les alertes ouvertes, sous forme de page HTML et de Markdown. Il est fait avec ce que le moniteur détient déjà, ne demande rien à GitHub et n'envoie rien nulle part : les fichiers restent dans le dossier `data/reports/`.

## L'activer

Réglages, onglet Sentinelle, bloc **Rapports planifiés** :

| Réglage | Défaut | Ce qu'il fait |
|---|---|---|
| `report_schedule.enabled` | désactivé | écrit un rapport selon l'horaire |
| `report_schedule.cron` | `0 8 * * 1` | cinq champs (minute, heure, jour du mois, mois, jour de la semaine) à l'heure locale de cet ordinateur ; nombres, listes, plages et pas, sans noms ; `0 8 * * 1` : chaque lundi à 8 h 00 |
| `report_schedule.formats` | les deux | `html`, `markdown` ou `both` |
| `report_schedule.keep` | 12 | combien de séries sont conservées ; les plus anciennes sont supprimées |
| `report_schedule.top` | 10 | combien de dépôts et d'alertes chaque liste montre, les pires d'abord |

Le premier rapport attend la première minute planifiée après l'activation. Un rapport est écrit par minute planifiée, même si le moniteur est resté éteint des jours (il en écrit alors un, pas un tas). Un rapport qui échoue est noté dans la santé du moniteur et la minute planifiée suivante réessaie. Un calendrier qui nomme un jour du mois reste dû après un arrêt allant jusqu'à un mois (s'il nomme un mois, jusqu'à un an), et l'heure qui se produit deux fois quand l'horloge recule en automne n'est pas rapportée deux fois. Un rapport est tous ses formats ou rien : si le second format ne peut pas être écrit, le premier fichier est supprimé.

## Ce que contient un rapport

Le score du compte (avec sa lettre et sa tendance ; en calibrage ou avec trop peu de données, il le dit et n'affiche pas de nombre), ce qui a changé depuis le dernier rapport (l'écart en points, les alertes nouvelles et celles qui ont disparu), les dépôts de la vue de santé qui demandent une personne d'abord, et les alertes ouvertes, les pires d'abord. Une alerte mise en silence n'est pas ouverte. Tout texte venant des données est échappé : la page n'a ni script ni adresse extérieure.

## PDF

Il n'y a pas de PDF propre : ouvrez la page HTML et imprimez-la en PDF depuis le navigateur. La page a un style d'impression pour l'A4.

## Où les voir et les demander

- L'onglet **Équipe** a une section Rapports : la liste, un lien vers chaque fichier et le bouton **Écrire un rapport maintenant** (un administrateur, depuis cet ordinateur).
- `GET /api/report-files` les liste, `GET /api/report-files/file?name=...` en ouvre un (seulement un fichier que le service a écrit pour ce compte) et `POST /api/report-files/run` en écrit un maintenant.
- En mode équipe, quiconque peut voir le compte peut lire ses rapports ; en écrire un maintenant est réservé à un administrateur sur cet ordinateur. L'édition Lite n'a rien de tout cela.

## Comparaison avec la période précédente

Avec `compare.include_in_report` activé (désactivé par défaut, et seulement tant que `compare.enabled` est actif), le rapport comporte aussi une courte section qui met cette période face à la précédente, une ligne par chiffre. Voir [COMPARE_fra.md](COMPARE_fra.md).
