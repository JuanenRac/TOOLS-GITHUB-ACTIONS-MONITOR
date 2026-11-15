<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Le score d'un compte

Un nombre de 0 à 100, une lettre de A à E et une tendance, pour chaque compte, construits uniquement à partir de ce que le moniteur connaît déjà (les exécutions terminées et les alertes de la sentinelle de collaboration). Il existe dans l'édition Complete ; Lite n'a pas de score.

## De quoi il est fait

Une somme pondérée de quatre parties, chacune de 0 à 100. Une partie vaut 100 à sa limite **bonne**, 0 à sa limite **mauvaise**, et varie linéairement entre les deux. Les poids et les limites sont des réglages.

| Partie | Poids | Ce qu'elle mesure | Bonne | Mauvaise |
|---|---|---|---|---|
| Fiabilité | 40 | part des exécutions terminées qui réussissent (les annulées et ignorées ne comptent pas) | 98 % | 50 % |
| Rapidité | 20 | 95e centile de la durée des exécutions réussies | 10 min | 60 min |
| Rétablissement | 20 | durée médiane entre le premier échec d'un workflow et son succès suivant | 30 min | 24 h |
| Collaboration | 20 | durée médiane pendant laquelle une alerte de la sentinelle de collaboration reste ouverte jusqu'à sa disparition | 2 jours | 14 jours |

La lettre est A à partir de 90, B à partir de 80, C à partir de 70, D à partir de 55 et E en dessous. La tendance compare le score à la fenêtre qui précède : en hausse, en baisse ou stable (une variation inférieure à `score.trend_flat` points est stable).

## Quand il n'y a pas de nombre

Le score n'affiche jamais un nombre qu'il ne peut pas justifier. La réponse porte toujours son `state`, sa `coverage` et sa `data_quality` :

- **calibrating** (calibrage) : le compte est surveillé depuis moins de `score.calibrating_hours` (24 par défaut). Ni nombre ni lettre.
- **insufficient_data** (données insuffisantes) : moins de `score.min_runs` exécutions terminées dans la fenêtre (20 par défaut), ou les parties qui ont des données pèsent moins de `score.min_coverage` du total (la moitié par défaut). Pas de nombre.
- **scored** (noté) : un nombre, une lettre et une tendance. Une partie sans données est écartée et les autres sont remises à l'échelle ; cela abaisse la `coverage` (par exemple 0,8 quand la sentinelle de collaboration est éteinte). Elle ne compte jamais comme 0 ni comme 100.

La sécurité n'est pas encore une partie. D'ici là, chaque réponse indique `complete: false` et liste `security` dans `missing_parts` : un score de 85 ne se lit donc jamais comme « tout va bien ».

## La fenêtre

La fenêtre est le nombre de jours d'exécutions que regarde le score : `score.window_days`, 7 par défaut, choisi par l'utilisateur pour chaque compte. La fenêtre qui la précède, de même durée, donne la tendance. Le moniteur tient un petit registre des exécutions terminées qu'il a vues, si bien que la fenêtre peut être plus longue que la liste des dernières exécutions affichée par la page. Un instantané est enregistré chaque heure et conservé aussi longtemps que l'historique des analyses (`retention.analytics_days`).

## Par dépôt et par compte

Chaque compte a son propre score. Son détail le ventile par dépôt (les parties de CI seulement, les pires d'abord). Il n'y a pas de nombre unique pour toute l'installation.

## Sur la page

Une pastille dans l'en-tête, à côté des pastilles de préparation, montre le score : le nombre, la lettre, une flèche avec l'évolution par rapport à la fenêtre précédente et une petite courbe des derniers jours. Sa couleur suit la lettre (A et B vert, C ambre, D et E rouge). Tant qu'il n'y a pas de nombre, elle est neutre et dit pourquoi (calibrage, données insuffisantes). Une étoile après la lettre signifie qu'une partie n'est pas encore comptée (aujourd'hui, la sécurité) : un nombre élevé ne veut alors pas dire que tout va bien. Au survol, elle montre la couverture, les parties avec leurs poids et le dépôt le plus faible. La pastille n'apparaît pas dans Lite ni quand le score est désactivé (`score.enabled`).

## L'API

`GET /api/score` renvoie le dernier instantané du compte : `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` et `stale` (vrai quand l'instantané a plus de trois heures). `GET /api/score/history` renvoie les points dans le temps, du plus ancien au plus récent (`?hours=` en remontant depuis maintenant, 90 jours au plus, et `?limit=`, 2000 au plus). Un nombre absent vaut `null`, jamais 0. En mode équipe, quiconque peut voir le compte peut lire son score ; les poids et les limites sont des réglages que seul un administrateur modifie.

## L'alerte en cas de baisse

Quand le score baisse de `score.alert.drop_points` points (10 par défaut) ou plus par rapport à la fenêtre précédente, ou passe à une lettre inférieure, l'onglet Alertes affiche l'alerte `score.dropped` (un avertissement ; critique si la lettre est E), avec l'ancien et le nouveau score. Elle reste tant que l'instantané montre la baisse et disparaît quand le score se rétablit ; on peut la mettre en sourdine comme toute autre alerte. Elle est active pour le panneau par défaut. Elle sort par les canaux de notification externes (événement `score_dropped`) uniquement si `score.alert.notify_external` est activé, ce qui n'est pas le cas par défaut, et seulement au moment où elle apparaît. `score.alert.enabled` désactive l'alerte.

## Les réglages

Dans la page des réglages, sous-onglet Sentinelle, blocs Score du compte, Poids du score et Lettres du score : `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, de `score.grades.A` à `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` et `score.alert.notify_external` (désactivé par défaut). Les limites bonne et mauvaise de chaque partie sont lues dans le fichier, sous `score.limits` (voir le fichier d'exemple) ; elles ne s'éditent pas dans la page.
