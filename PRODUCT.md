<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor: what it is

**English** · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## Purpose

To tell one person or a small team, on their own computer, whether the CI of all their repositories is really green, what failed and why, without having to open each repository.

## Who it is for

- Owners of many repositories (from a handful to several hundred).
- Small teams that share a screen or a wall display.
- AI tools that work on those repositories and need to read the state before they push.

## What it is and what it is not

It is a local program that reads GitHub with your own token or GitHub App. It is not a hosted service, it is not a CI system and it does not replace GitHub: it observes, and the few actions that write are switched off until you switch them on.

## Lasting rules

- No package is needed: the core is the Python standard library.
- Nothing leaves your computer unless a setting you can see says so; there is no telemetry.
- What was not checked is never shown as green.
- Anything that writes to GitHub or to the system is off by default and asks before it acts.
- Every text of the interface and of the help exists in eight languages.
- GPL-3.0-or-later.
