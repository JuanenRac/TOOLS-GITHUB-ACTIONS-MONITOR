<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | [🇪🇸 Español](TRAFFIC_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](TRAFFIC_ita.md) | [🇩🇪 Deutsch](TRAFFIC_deu.md) | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# Téléchargements et trafic

Un historique, gardé sur cet ordinateur, des téléchargements des fichiers de vos versions et des visites et clonages des dépôts que vous choisissez. GitHub ne garde les visites et clonages que 14 jours et ne donne pas d'historique des téléchargements : ce qui n'est pas enregistré est perdu. Édition Complete ; désactivé par défaut.

## Activation

Activez `traffic.enabled` (Réglages > Téléchargements et trafic) et écrivez les dépôts dans `traffic.repos`, un par ligne : un nom (du compte surveillé) ou propriétaire/nom, 50 au maximum. Avec une liste vide rien n'est lu. Le panneau apparaît dans l'onglet Dépôts.

## Ce qui est lu et ce que cela coûte

Requêtes GET seulement, après un cycle : chaque dépôt choisi au plus une fois par jour (UTC), `traffic.repos_per_cycle` par cycle. Un dépôt coûte d'une à cinq requêtes de votre quota GitHub (versions, jusqu'à 300 ; visites ; clonages). Quand le quota est épuisé, la lecture s'arrête et reprend plus tard. `traffic.views_clones` désactive les visites et clonages. Les installations sans réseau ne lisent rien. La lecture attend aussi tant que la connexion est perdue, pendant la première lecture et quand il ne reste pas plus du double de `min_rate_remaining` requêtes.

## Permissions

Les visites et clonages ne sont donnés qu'à un jeton ayant l'accès en écriture (push) au dépôt. Sans lui, le panneau le dit pour ce dépôt ; ce n'est pas une erreur et les téléchargements sont toujours enregistrés.

## Le sens des chiffres

Les téléchargements sont anonymes, comptent les robots et les miroirs, et ne comptent pas les archives "Source code" que GitHub ajoute à une version. Les nouveaux téléchargements comparent une lecture à la précédente, pour les fichiers encore présents. Un jour non lu est un trou, jamais un zéro.

## Export et confidentialité

Le panneau exporte deux fichiers CSV : une ligne par dépôt et par jour, et une par fichier de version et jour où son nombre a changé. `monitor_cli.py traffic export` affiche le premier. Les jours plus anciens que `traffic.keep_days` sont effacés. L'historique reste dans le dossier de données de cet ordinateur ; rien n'est envoyé.
