<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor: was es ist

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · **Deutsch** · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## Zweck

Einer Person oder einem kleinen Team auf dem eigenen Rechner sagen, ob die CI aller Repositorys wirklich grün ist, was fehlgeschlagen ist und warum, ohne jedes Repository zu öffnen.

## Für wen

- Besitzer vieler Repositorys (von wenigen bis zu mehreren Hundert).
- Kleine Teams, die sich einen Bildschirm oder eine Wandanzeige teilen.
- KI-Werkzeuge, die in diesen Repositorys arbeiten und den Zustand vor dem Push lesen müssen.

## Was es ist und was nicht

Ein lokales Programm, das GitHub mit dem eigenen Token oder der eigenen GitHub App liest. Es ist kein gehosteter Dienst, kein CI-System und kein Ersatz für GitHub: Es beobachtet, und die wenigen schreibenden Aktionen sind aus, bis man sie einschaltet.

## Dauerhafte Regeln

- Es braucht kein Paket: der Kern ist die Python-Standardbibliothek.
- Nichts verlässt den Rechner, außer eine sichtbare Einstellung sagt es; es gibt keine Telemetrie.
- Was nicht geprüft wurde, erscheint nie grün.
- Alles, was auf GitHub oder ins System schreibt, ist standardmäßig aus und fragt vorher.
- Jeder Text der Oberfläche und der Hilfe existiert in acht Sprachen.
- GPL-3.0-or-later.
