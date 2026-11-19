<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PRODUCTIVITY.md) | [🇪🇸 Español](PRODUCTIVITY_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](PRODUCTIVITY_ita.md) | [🇩🇪 Deutsch](PRODUCTIVITY_deu.md) | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | [🇵🇹 Português](PRODUCTIVITY_por.md)

# Ce que le moniteur fait gagner : une estimation et comment la mesurer

Ce guide explique les chiffres du README. Ils sont une estimation issue d'un modèle simple, pas une mesure prise sur vos dépôts. Mesurez les vôtres avant de vous y fier.

## Les chiffres

- Environ 85-95 % du temps passé à surveiller la CI et à trier les échecs.
- Environ 15-25 % de la productivité globale d'une équipe, en conséquence du premier chiffre.

## Comment l'estimation est construite

Temps gagné en une semaine = la somme, sur les tâches, de (fois par semaine x minutes à chaque fois sans le moniteur) x le gain de cette tâche. Les tâches sont : surveiller chaque workflow, décider ce qui est vraiment rouge, trouver la cause d'une exécution en échec et apprendre un échec à temps. L'estimation suppose que :

1. Il y a de nombreux dépôts avec plusieurs workflows chacun, si bien que les regarder à la main oblige à ouvrir sans cesse de nombreuses pages.
2. Sans le moniteur, quelqu'un consulte à la main les onglets Actions et lit chaque journal en échec pour trouver la cause. Avec lui, la page et les alertes disent déjà quel workflow est rouge et pourquoi.
3. Des échecs surviennent chaque semaine. Une équipe sans échecs n'a rien à trier.
4. Le gain ne couvre que la surveillance et le tri. Corriger un échec prend autant de temps avec ou sans le moniteur et n'est pas compté.

Les deux chiffres ne concordent que si la surveillance et le tri occupent environ 16-29 % du temps de travail de l'équipe (0,15 / 0,95 à 0,25 / 0,85). S'ils en occupent moins dans votre équipe, le gain global est plus faible.

## Quand il fait moins gagner

- Peu de dépôts ou un seul workflow : il y a peu à surveiller.
- Personne ne surveille la CI à la main aujourd'hui, ou vous avez déjà des alertes qui nomment la cause.
- Les alertes ne sont pas lues. Les lire prend aussi du temps, et le gain disparaît si elles sont ignorées ou mises en sourdine sans raison.

## Comment le mesurer dans votre propre usage

1. Avant : pendant une semaine normale, notez chaque fois que vous regardez la CI à la main (minutes) et chaque exécution en échec que vous triez (minutes jusqu'à connaître la cause).
2. Après : refaites les mêmes notes pendant une semaine avec le moniteur ouvert. Le score (temps de rétablissement) et le livre des échecs (tendance sur 24 heures et 7 jours) montrent si les échecs sont clos plus vite.
3. Pour chaque groupe, le gain est 1 - après / avant. Comparez-le à 85-95 %.
4. Pour le gain global, divisez les heures gagnées par le total des heures travaillées cette semaine-là. Comparez-le à 15-25 %.

### Exemple avec des chiffres inventés

Quelqu'un passe 20 minutes par jour à regarder les onglets Actions (100 minutes sur une semaine de cinq jours) et trie 4 exécutions en échec par semaine à 30 minutes chacune (120 minutes) : 220 minutes en tout. Avec 85-95 % de gain, entre 187 et 209 minutes sont libérées. Ces chiffres sont inventés pour montrer le calcul ; utilisez les vôtres.
