<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Le score d'un compte

Un nombre de 0 à 100, une lettre de A à E et une tendance, pour chaque compte, construits uniquement à partir de ce que le moniteur connaît déjà (les exécutions terminées et les alertes de la sentinelle de collaboration). Il existe dans l'édition Complete ; Lite n'a pas de score.

## De quoi il est fait

Une somme pondérée de cinq parties, chacune de 0 à 100. Une partie vaut 100 à sa limite **bonne**, 0 à sa limite **mauvaise**, et varie linéairement entre les deux. Les poids et les limites sont des réglages.

| Partie | Poids | Ce qu'elle mesure | Bonne | Mauvaise |
|---|---|---|---|---|
| Fiabilité | 30 | part des exécutions terminées qui réussissent (les annulées et ignorées ne comptent pas) | 98 % | 50 % |
| Rapidité | 15 | 95e centile de la durée des exécutions réussies | 10 min | 60 min |
| Rétablissement | 15 | durée médiane entre le premier échec d'un workflow et son succès suivant ; un workflow encore en rouge compte le temps qu'il est en rouge jusqu'ici | 30 min | 24 h |
| Collaboration | 15 | durée médiane pendant laquelle une alerte de la sentinelle de collaboration reste ouverte jusqu'à sa disparition | 2 jours | 14 jours |
| Sécurité | 25 | les points que les constats ouverts de la sentinelle de sécurité retirent à 100 (seulement tant que cette sentinelle est active) | 0 point | 100 points |

La lettre est A à partir de 90, B à partir de 80, C à partir de 70, D à partir de 55 et E en dessous. La tendance compare le score à la fenêtre qui précède : en hausse, en baisse ou stable (une variation inférieure à `score.trend_flat` points est stable).

## Quand il n'y a pas de nombre

Le score n'affiche jamais un nombre qu'il ne peut pas justifier. La réponse porte toujours son `state`, sa `coverage` et sa `data_quality` :

- **calibrating** (calibrage) : le compte est surveillé depuis moins de `score.calibrating_hours` (24 par défaut). Ni nombre ni lettre.
- **insufficient_data** (données insuffisantes) : moins de `score.min_runs` exécutions terminées dans la fenêtre (20 par défaut), ou les parties qui ont des données pèsent moins de `score.min_coverage` du total (la moitié par défaut). Pas de nombre.
- **scored** (noté) : un nombre, une lettre et une tendance. Une partie sans données est écartée et les autres sont remises à l'échelle ; cela abaisse la `coverage` (par exemple 0,85 quand la sentinelle de collaboration est éteinte). Elle ne compte jamais comme 0 ni comme 100.

La sécurité est une partie comme les autres, mais elle n'a de données que tant que la sentinelle de sécurité est active et a examiné assez de dépôts. Sans elle, la réponse dit `complete: false` et liste `security` sous `missing_parts`, et les autres parties sont remises à l'échelle : le nombre ne se lit donc jamais comme « tout va bien ». GitHub ne donne pas d'historique des constats, si bien que la partie sécurité est la même dans la fenêtre et dans celle d'avant : la tendance montre ce qu'ont fait la CI et la collaboration. Les poids sont 30, 15, 15, 15 et 25 par défaut. Une fenêtre avec des exécutions et aucun échec n'a rien à rétablir : sa partie rétablissement est pleine, comme un fait et non comme un manque.

Un workflow encore en rouge à la fin de la fenêtre n'est pas oublié : la partie rétablissement compte le temps qu'il est en rouge jusqu'ici, une borne inférieure qui grandit tant que le rouge dure ; un échec que personne ne corrige fait donc baisser le chiffre davantage chaque heure. Un échec corrigé compte sa durée réelle. Une relance d'une exécution compte comme une exécution de plus du workflow : le premier essai en échec et le second en vert sont tous deux vus. Si tu mets à jour depuis une version antérieure, les chiffres d'un compte avec un workflow en rouge peuvent être plus bas qu'avant. Quand aucune partie n'a de données, la réponse est `insufficient_data` avec la raison `no_data`. Le registre garde au plus 20000 exécutions : quand il a dû en écarter qui appartiennent à la fenêtre actuelle, `data_quality.truncated` est vrai et `truncated` figure parmi les raisons, pour qu'un taux de réussite qui ne voit qu'une partie de la fenêtre ne soit pas pris pour complet. Dans `GET /api/score/global`, un compte dont l'instantané est périmé est exclu de la moyenne et compté dans `accounts_stale`, et `/metrics` n'exporte pas `ghamon_score` pour un instantané périmé.

Un dépôt n'est pas sain parce qu'il n'a rien à montrer. Chaque dépôt surveillé est *actif* (une exécution propre plus récente que `ci.inactive_days` jours), *dormant* (il n'a jamais rien exécuté de lui-même) ou *inactif* (son exécution la plus récente est plus ancienne) : les dépôts dormants et inactifs ne sont ni verts ni rouges et sont comptés à part (`activity` de l'instantané, les chiffres `dormant` et `inactive_repos`, l'infobulle de la pastille), si bien qu'un compte avec des centaines de forks n'affiche pas un score fait de rien. Un dépôt que le moniteur n'a pas pu lire est *inconnu*, jamais dormant. `ci.dormant_repos` désactive le comptage.

## La fenêtre

La fenêtre est le nombre de jours d'exécutions que regarde le score : `score.window_days`, 7 par défaut, choisi par l'utilisateur pour chaque compte. La fenêtre qui la précède, de même durée, donne la tendance. Le moniteur tient un petit registre des exécutions terminées qu'il a vues, si bien que la fenêtre peut être plus longue que la liste des dernières exécutions affichée par la page. Un instantané est enregistré chaque heure et conservé aussi longtemps que l'historique des analyses (`retention.analytics_days`).

## Par dépôt et par compte

Chaque compte a son propre score. Son détail le ventile par dépôt (les parties de CI seulement, les pires d'abord). Il n'y a pas de nombre unique pour toute l'installation. À titre d'information seulement, `GET /api/score/global` du superviseur donne la moyenne des comptes notés que le demandeur peut voir, pondérée par leurs dépôts ayant un nombre, toujours avec le nombre de comptes pris en compte ; un compte sans nombre est listé et écarté.

## Sur la page

Une pastille dans l'en-tête, à côté des pastilles de préparation, montre le score : le nombre, la lettre, une flèche avec l'évolution par rapport à la fenêtre précédente et une petite courbe des derniers jours. Sa couleur suit la lettre (A et B vert, C ambre, D et E rouge). Tant qu'il n'y a pas de nombre, elle est neutre et dit pourquoi (calibrage, données insuffisantes). Une étoile après la lettre signifie qu'une partie n'est pas encore comptée (aujourd'hui, la sécurité) : un nombre élevé ne veut alors pas dire que tout va bien. Au survol, elle montre la couverture, les parties avec leurs poids et le dépôt le plus faible. La pastille n'apparaît pas dans Lite ni quand le score est désactivé (`score.enabled`). Pendant le calibrage, la pastille indique ce qu'il reste de `score.calibrating_hours` (`data_quality.calibrating_hours`), avec une barre et le jour et l'heure où le chiffre apparaîtra ; avec trop peu de données, elle indique la condition qui échoue (exécutions ou couverture), et l'infobulle dit aussi pourquoi une partie n'est pas comptée (une sentinelle éteinte, qui n'a pas fini son premier balayage ou qui a lu trop peu de dépôts).

## Pour d'autres outils

Les métriques (`/metrics`, quand la sortie Prometheus est activée) portent trois séries sans étiquettes : `ghamon_score_scored` (1 quand le compte a un nombre), `ghamon_score_coverage` (la part des poids qui ont des données, de 0 à 1) et `ghamon_score` (le nombre, seulement quand il y en a un : il n'est jamais exporté comme 0 quand il n'y en a pas). Le serveur MCP a un outil en lecture seule `get_score` avec la réponse de l'API. `--demo` montre un score inventé et n'écrit rien. Le tableau de bord Grafana d'exemple (`docs/grafana/monitor_dashboard.json`) a un panneau du score et un panneau du score dans le temps.

## L'API

`GET /api/score` renvoie le dernier instantané du compte : `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` et `stale` (vrai quand l'instantané a plus de trois heures). `GET /api/score/history` renvoie les points dans le temps, du plus ancien au plus récent (`?hours=` en remontant depuis maintenant, 90 jours au plus, et `?limit=`, 2000 au plus). Un nombre absent vaut `null`, jamais 0. En mode équipe, quiconque peut voir le compte peut lire son score ; les poids et les limites sont des réglages que seul un administrateur modifie.

## L'alerte en cas de baisse

Quand le score baisse de `score.alert.drop_points` points (10 par défaut) ou plus par rapport à la fenêtre précédente, ou passe à une lettre inférieure, l'onglet Alertes affiche l'alerte `score.dropped` (un avertissement ; critique si la lettre est E), avec l'ancien et le nouveau score. Elle reste tant que l'instantané montre la baisse et disparaît quand le score se rétablit ; on peut la mettre en sourdine comme toute autre alerte. Elle est active pour le panneau par défaut. Elle sort par les canaux de notification externes (événement `score_dropped`) uniquement si `score.alert.notify_external` est activé, ce qui n'est pas le cas par défaut, et seulement au moment où elle apparaît. `score.alert.enabled` désactive l'alerte.

## Les réglages

Dans la page des réglages, sous-onglet Sentinelle, blocs Score du compte, Poids du score et Lettres du score : `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, de `score.grades.A` à `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` et `score.alert.notify_external` (désactivé par défaut). Les limites bonne et mauvaise de chaque partie sont lues dans le fichier, sous `score.limits` (voir le fichier d'exemple) ; elles ne s'éditent pas dans la page.
