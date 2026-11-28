<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Grands comptes : des centaines de dépôts

Un compte avec des centaines de dépôts, beaucoup de forks ou plusieurs organisations épuise vite le quota de l'API. Voici une recette, dans l'ordre qui économise le plus ; chaque réglage est dans l'onglet Réglages.

1. **Commencez par un profil.** Réglages > Base > Profil : *Organisation open source* fixe l'essentiel de ce qui suit en un clic (chaque réglage reste modifiable ensuite).
2. **Surveillez ce qui est entretenu.** `discovery.fork_policy` = `auto` ne garde que les forks avec une CI propre (le type de compte décide la fenêtre, `discovery.fork_ci_days`) ; `discovery.fork_checks_per_pass` répartit les questions sur plusieurs listes. `discovery.skip_archived` est activé par défaut. `exclude` et `ecosystems` restreignent la liste par nom. Une liste du compte qui arrive vide, ou avec moins de `discovery.min_keep_pct` pour cent de la dernière bonne, n'est pas crue : la dernière bonne liste est conservée, la liste est relue dans cinq minutes et le brief pour les outils d'IA a le signal repos.listing. `discovery.hide` accepte aussi `public` (et `private`, `fork`, `empty`) ; l'onglet Essentiel compte ce que chaque règle a écarté, donc rien d'écarté par un filtre n'est lu comme propre.
3. **Demandez moins.** `cold_runs_per_repo` et `cold_refresh_seconds` fixent le coût des dépôts calmes ; `runs_per_repo` et `refresh_seconds` font de même pour les actifs. `network.etag` rend gratuites les lectures répétées quand rien n'a changé, et le mode Bas (`modes.auto_low`) ralentit tout seul quand le quota baisse.
4. **Donnez un budget à la Sentinelle.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` et `sentinel.hygiene_seconds` (l'hygiène est une requête par dépôt toutes les six heures par défaut ; allongez-la) bornent la dépense des contrôles A3-A6.
5. **Ajoutez un second quota.** `github_app.share_reads` laisse une GitHub App répondre à une partie des lectures avec son propre quota.
6. **Ne vous noyez pas dans le bruit.** Le contrôle d'hygiène (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), ceux des fichiers des releases (`sentinel.surface.checks.release_assets.allow_empty`) et `sentinel.bots_apart` évitent l'accumulation de contrôles qui ne concernent pas vos dépôts.

L'onglet Quota montre ce qu'il reste à chaque source et ce que dépense le moniteur lui-même.

Le suivi des originaux des forks (`upstream.enabled`) indique dans son panneau combien de temps dure un tour de tous les forks au rythme de `upstream.requests_per_hour` et `upstream.forks_per_request` ; quand c'est plus que `upstream.refresh_hours`, le suivi ne se repose jamais (727 forks à 8 par requête et 6 requêtes par heure prennent 15,2 heures). Les requêtes de la dernière heure sont conservées au redémarrage : un redémarrage ne rend donc pas le quota.

Les appels d'un tick de la Sentinelle (`sentinel.max_calls_per_tick`) forment un seul décompte pour toutes ses étapes, et un dépôt dont les lectures échouent trois fois de suite est laissé tranquille 30 secondes, en doublant jusqu'à 10 minutes, pendant que les autres sont lus.

L'onglet Flotte porte aussi un cadre facultatif par [rôle de workflow et par groupe, avec un écran pour chaque groupe](FLEET_APIS_fra.md).

## File de lectures, limites et une lecture pour tous

- **Contre-pression** (`backpressure.enabled`, désactivée par défaut) : les lectures d'un cycle passent par une file bornée (d'abord les dépôts avec un workflow rouge, puis les chauds, les jamais lus et les lus il y a le plus longtemps). `backpressure.max_reads_per_cycle` fixe un nombre (0 = aucun) ; quand un cycle dure plus de `backpressure.shed_percent` pour cent de la pause entre cycles, le nombre permis est réduit de moitié (jamais sous `backpressure.min_reads`) et regagne un dixième après chaque cycle rapide. Ce qui attend garde sa dernière image et passe en premier au cycle suivant. `/metrics` montre `ghamon_read_queue_*`.
- **Limites et le doctor** : `monitor_cli.py doctor` a un contrôle `capacity` qui compare la configuration à ses plafonds (appels par heure face au quota et à `sampling.api_budget_per_hour`, la mémoire des exécutions gardées face à `limits.memory_mb`, les dépôts face à `discover_limit`) et avertit à partir de `limits.warn_percent`. `/metrics` montre ceux qui sont en cours en `ghamon_limit_used_percent{limit=...}` (événements gardés, flux, file de lectures, séries des histogrammes).
- **Une lecture pour tous** (`refresh.share_by_workflow`, désactivée par défaut) : quand le cycle, une page, un écran mural ou un client de l'API demandent les jobs de la même exécution au même moment, le premier lit sur GitHub et les autres prennent sa réponse, valable `refresh.share_seconds` secondes. `/metrics` compte les lectures épargnées (`ghamon_shared_reads_spared_total`).
