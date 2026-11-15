<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# Le journal des actions

Complete seulement, activé par défaut. À côté de l'audit des accès (connexions, verrouillages, refus), le moniteur tient un journal des **actions** : qui a changé quoi, quand et sur quel compte. Un changement de réglages, un silence ou sa levée, un changement d'utilisateurs, de mots de passe, de préférences de notification ou d'identifiants. C'est une ligne JSON par action dans `logs/audit_actions.jsonl`, jamais réécrite.

## Ce que dit une ligne

`at`, `action` (un mot simple comme `settings_change` ou `alert_mute`), `user`, `role`, `account`, `target` (un identifiant court : un nom de réglage, un code d'alerte), `result` (`ok`, `denied` ou `error`) et, si utile, `details`. **Aucune valeur et aucun secret n'y entre jamais** : un changement de réglages écrit les noms des réglages, pas leurs valeurs ; une clé dont le nom ressemble à un secret (token, password, key, cookie, authorization, session...) est écartée ; tout texte est nettoyé comme les notes pour les IA et coupé à 200 caractères.

## La chaîne

Chaque ligne porte `prev` (le hachage de la ligne précédente) et `hash` (le hachage d'elle-même et de `prev`). Une ligne modifiée, retirée ou insérée après coup brise la chaîne, et `GET /api/audit-log` dit où (`chain.broken_at`). Au-delà de `audit_log.max_mb`, l'ancienne partie est gardée sous `audit_actions.jsonl.1` et la chaîne continue dans le nouveau fichier. La chaîne révèle une altération ; elle ne peut pas empêcher quelqu'un qui a accès au fichier de tout supprimer : gardez une copie là où c'est important.

## Qui le lit

Un administrateur (et la personne devant l'ordinateur quand il n'y a pas de mode équipe). Un mainteneur seulement quand `audit_log.maintainers_can_read` est activé ; personne d'autre. `GET /api/audit-log` répond les 200 dernières lignes et l'état de la chaîne. Lite n'a rien de tout cela.

## Réglages

Réglages, onglet Sentinelle, bloc **Journal des actions** : `audit_log.enabled` (activé), `audit_log.max_mb` (10) et `audit_log.maintainers_can_read` (désactivé).
