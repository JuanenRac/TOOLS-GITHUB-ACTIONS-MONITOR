<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# Le journal des actions

Complete seulement, activé par défaut. À côté de l'audit des accès (connexions, verrouillages, refus), le moniteur tient un journal des **actions** : qui a changé quoi, quand et sur quel compte. Un changement de réglages, un silence ou sa levée, un changement d'utilisateurs, de mots de passe, de préférences de notification ou d'identifiants. C'est une ligne JSON par action dans `logs/audit_actions.jsonl`, jamais réécrite. Il enregistre aussi ce qui est confirmé : une action sur GitHub (relancer, annuler, déclencher, fusionner), une exécution avec `act`, l'enregistrement ou la suppression du jeton conservé, un changement du mode de travail, un groupe ajouté par la découverte, une leçon ajoutée, un rapport écrit maintenant, la connexion du compte et les actions de l'IA. La ligne dit ce qui a été confirmé et le résultat, jamais le corps de la requête. Chaque route POST est soit enregistrée, soit listée comme exemptée avec sa raison, et un test échoue quand une nouvelle route n'est ni l'un ni l'autre.

## Ce que dit une ligne

`at`, `action` (un mot simple comme `settings_change` ou `alert_mute`), `user`, `role`, `account`, `target` (un identifiant court : un nom de réglage, un code d'alerte), `result` (`ok`, `denied` ou `error`) et, si utile, `details`. **Aucune valeur et aucun secret n'y entre jamais** : un changement de réglages écrit les noms des réglages, pas leurs valeurs ; une clé dont le nom ressemble à un secret (token, password, key, cookie, authorization, session...) est écartée ; tout texte est nettoyé comme les notes pour les IA et coupé à 200 caractères.

## La chaîne

Chaque ligne porte `prev` (le hachage de la ligne précédente) et `hash` (le hachage d'elle-même et de `prev`). Une ligne modifiée, retirée ou insérée après coup brise la chaîne, et `GET /api/audit-log` dit où (`chain.broken_at`). Au-delà de `audit_log.max_mb`, l'ancienne partie est gardée sous `audit_actions.jsonl.1` et la chaîne continue dans le nouveau fichier. La chaîne révèle une altération ; elle ne peut pas empêcher quelqu'un qui a accès au fichier de tout supprimer : gardez une copie là où c'est important. Avec plusieurs comptes, chaque compte garde son propre fichier dans son dossier (`accounts/<id>/audit_actions.jsonl`) et l'API ne répond qu'avec les lignes du compte interrogé ; les lignes écrites avant ce changement restent dans l'ancien fichier partagé. La vérification couvre aussi le fichier tourné et le lien entre les deux (`segments`, et `segment` quand une ligne est brisée) ; `complete: false` signifie que la chaîne ne commence pas à son premier maillon parce qu'un fichier tourné a été remplacé par une rotation ultérieure ou supprimé. Plusieurs processus peuvent écrire le même fichier : chaque ligne est chaînée à la dernière ligne réellement présente, sous un verrou. La chaîne n'a pas de clé secrète : qui peut écrire le fichier peut couper ses lignes les plus récentes ou le réécrire avec de nouveaux hachages ; s'il doit servir de preuve, garde une copie ailleurs.

## Qui le lit

Un administrateur (et la personne devant l'ordinateur quand il n'y a pas de mode équipe). Un mainteneur seulement quand `audit_log.maintainers_can_read` est activé ; personne d'autre. `GET /api/audit-log` répond les 200 dernières lignes et l'état de la chaîne. Lite n'a rien de tout cela. Un viewer est refusé à la porte. Éteindre le journal écrit sa propre dernière ligne (le changement qui l'a éteint). Une ligne qui ne peut pas être écrite est comptée : `write_failures` et `last_write_error_at` dans la réponse, et un avis de dégradation. Les changements ratés de son propre mot de passe ne sont pas écrits ici (l'audit des accès les garde).

## Réglages

Réglages, onglet Sentinelle, bloc **Journal des actions** : `audit_log.enabled` (activé), `audit_log.max_mb` (10) et `audit_log.maintainers_can_read` (désactivé).
