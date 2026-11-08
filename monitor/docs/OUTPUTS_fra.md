<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

# Sorties pour d'autres outils

Trois sorties facultatives, **toutes désactivées par défaut**, que l'on active dans l'onglet Paramètres (groupe « Sorties pour d'autres outils ») ou dans `actions_monitor.json` :

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

Elles sont servies par le même serveur web, uniquement sur `127.0.0.1`, avec les mêmes contrôles `Host` / `Origin` que le reste, et **n'exigent aucun jeton**. Elles lisent l'état que le moniteur détient déjà, si bien qu'un
scrape ou l'actualisation d'un tableau de bord ne consomme aucun quota de l'API GitHub. Leur activation ou désactivation s'applique immédiatement (sans redémarrage).

| Chemin | Format | Interrupteur |
|---|---|---|
| `/metrics` | Texte Prometheus, version 0.0.4 | `outputs.prometheus.enabled` (`per_repo` ajoute les séries par dépôt) |
| `/api/outputs/grafana.json` | Tables JSON pour la source de données « Infinity » / JSON de Grafana | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | le document de `ci_red.json` (schéma 2, voir CI_RED_SCHEMA_fra.md) pour un tableau de bord d'état | `outputs.dashboard.enabled` |

Une requête vers un chemin dont l'interrupteur est désactivé reçoit `404`. L'ancienne méthode pour fournir le même document à un tableau de bord, `ci_red.json` et `read_report.py --export-status`, reste inchangée : c'est un contrat.

## Métriques Prometheus

Tous les noms commencent par `ghamon_`. Uniquement des jauges (gauges). Une valeur inconnue est **omise**, jamais écrite comme 0.

| Métrique | Étiquettes | Signification |
|---|---|---|
| `ghamon_info` | `version` | toujours 1 |
| `ghamon_snapshot_complete` | | 1 lorsque l'instantané de la sentinelle est complet, 0 pendant son chargement ou lorsqu'il est réduit |
| `ghamon_red_workflows`, `ghamon_red_repos` | | workflows (dépôts) dont la dernière exécution terminée sur la branche par défaut est rouge |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | la même chose par écosystème |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | par dépôt (nécessite `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | exécutions rouges consécutives (nécessite `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | heures écoulées depuis le passage au rouge (nécessite `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | builds en attente de la signature ou de la publication locale, au-delà du seuil |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | l'attente la plus longue d'un dépôt (nécessite `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1 tant que les contrôles de surface (A10) attendent du quota GitHub, avec le quota restant et celui qui est nécessaire |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | le quota de l'API GitHub |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | les appels d'API de la sentinelle par rapport à son budget |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | les chiffres en direct de l'onglet Maintenant |

Un job de scrape :

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` est un tableau de bord importable (Grafana 10 ou plus récent) : des panneaux de statistiques pour les workflows rouges, les builds en attente de signature, le quota restant, l'
état de A10, la complétude de l'instantané et les exécutions bloquées ; un graphique en barres des workflows rouges par écosystème ; un graphique de la plus longue série rouge et de l'attente de signature ; et deux tables lues
depuis `/api/outputs/grafana.json` avec la source de données Infinity (`root_selector` `red` et `pending_sign`). À l'importation, Grafana demande les sources de données Prometheus et Infinity ; modifiez
le port dans l'URL des deux tables si le moniteur n'utilise pas 8765. Grafana doit s'exécuter sur la même machine (les sorties ne répondent que sur 127.0.0.1).

## Idées tirées de projets similaires

La lecture de ce que font d'autres outils pour GitHub Actions a fourni quelques idées ; aucun de leurs codes ni de leurs textes n'est utilisé. D'un exportateur de métriques Prometheus : l'état d'une exécution sous forme de nombre accompagné d'étiquettes, le
choix des étiquettes à exporter, ainsi qu'un port et un intervalle configurables. D'un tableau de bord pour écran de télévision alimenté par des webhooks : un état par dépôt avec des filtres, affiché en grand. D'un observateur en terminal : tous les
workflows d'un dépôt à la fois jusqu'à leur fin. D'un tableau de bord de webhooks avec des règles d'alerte : des filtres par dépôt, branche et workflow avant d'alerter. Ici, les mêmes idées apparaissent sous la forme de
`per_repo` (choisir les séries), la source JSON avec une ligne par workflow rouge, l'onglet Maintenant en direct et le fichier d'événements avec filtres dans la page.

## Le tableau Grafana minimal

`docs/grafana/red_by_ecosystem.json` est un tableau à un seul panneau : workflows rouges par écosystème (requête `ghamon_ecosystem_red_workflows`, légende `{{ecosystem}}`). Importez-le et choisissez votre source Prometheus. Un test de ce dépôt vérifie que la métrique et l'étiquette utilisées sont bien servies par `/metrics`.

## La file de signature par confiance

Chaque ligne de la file a un `trust` : `verified` (signature vérifiée avec la clé publique), `unknown` (le format ne peut pas être vérifié ici : jamais deviné) ou `failed` (vérifiée et non conforme). L'onglet Sentinelle a un filtre Signature avec le nombre de chaque sorte et marque les lignes (bord vert, gris ou rouge). En console : `py -3 read_report.py --export-sign-queue FILE --sign-trust failed`.

## En mode réseau

`/metrics` et `dashboard.json` listent vos dépôts et leur état : ce ne sont pas des pages publiques. Avec le mode réseau actif, ils exigent le jeton d'accès comme tout autre point d'accès ; désactivez `outputs.prometheus.enabled` / `outputs.dashboard.enabled` si vous ne voulez pas que cet inventaire soit joignable du tout.
