<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor : ce que c'est

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · **Français** · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## But

Dire à une personne ou à une petite équipe, sur son propre ordinateur, si la CI de tous ses dépôts est réellement verte, ce qui a échoué et pourquoi, sans ouvrir chaque dépôt.

## Pour qui

- Les propriétaires de nombreux dépôts (de quelques-uns à plusieurs centaines).
- Les petites équipes qui partagent un écran ou un mur d'affichage.
- Les outils d'IA qui travaillent sur ces dépôts et doivent lire l'état avant de pousser.

## Ce qu'il est et ce qu'il n'est pas

C'est un programme local qui lit GitHub avec votre propre jeton ou GitHub App. Ce n'est pas un service hébergé, ni un système de CI, et il ne remplace pas GitHub : il observe, et les rares actions qui écrivent sont désactivées tant que vous ne les activez pas.

## Règles durables

- Aucun paquet n'est nécessaire : le noyau est la bibliothèque standard de Python.
- Rien ne quitte votre ordinateur sauf si un réglage visible le dit ; il n'y a pas de télémétrie.
- Ce qui n'a pas été vérifié n'est jamais affiché en vert.
- Tout ce qui écrit sur GitHub ou sur le système est désactivé par défaut et demande confirmation.
- Chaque texte de l'interface et de l'aide existe en huit langues.
- GPL-3.0-or-later.
