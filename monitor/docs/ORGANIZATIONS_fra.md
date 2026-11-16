<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | [🇪🇸 Español](ORGANIZATIONS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# Organisations et grands comptes

Comment pointer le moniteur vers une organisation, ou vers un compte personnel de plusieurs centaines de dépôts, et que faire quand une lecture revient vide.

## 1. Le plus petit jeton qui fonctionne

Le moniteur ne fait que lire. Utilisez la connexion de `gh` (`gh auth login`) ou un jeton dans `GH_TOKEN`, et donnez-lui le strict nécessaire.

| Type de jeton | Que lui donner |
|---|---|
| **Classique** (jeton d'accès personnel) | `repo` pour les dépôts privés (`public_repo` suffit si tout est public) et `read:org` pour lister les dépôts et les équipes d'une organisation. Facultatifs : `security_events` (alertes de code scanning, panneau A3), `read:project` (les tableaux Projects, panneau A9). Il n'a besoin ni de `workflow` ni d'aucune portée d'écriture. |
| **À granularité fine** | Un seul *propriétaire de la ressource* : créez un jeton par organisation (ou par compte personnel). Accès aux dépôts : tous, ou ceux choisis. Permissions en lecture seule : Metadata, Actions, Contents, Pull requests, Issues, Administration (rulesets et règles de branche), Code scanning alerts, Dependabot alerts, Secret scanning alerts. Une organisation peut exiger qu'un propriétaire approuve d'abord le jeton. |
| **GitHub App** | Lit avec le quota de l'App au lieu du vôtre (voir `QUOTA.md`). |

Un **compte personnel** (`github_owner` est un utilisateur) n'a besoin de rien de plus pour ses propres dépôts. Les dépôts d'une organisation dont vous faites partie se lisent avec un jeton dont le propriétaire de la ressource (granularité fine) ou les portées (classique) incluent cette organisation.

## 2. Authentification unique (SSO) et dépôts privés

Si l'organisation impose le SSO SAML, un jeton classique doit y être autorisé : sur GitHub ouvrez *Settings > Developer settings > Personal access tokens*, choisissez le jeton et cliquez sur *Configure SSO > Authorize*. Une connexion faite avec `gh auth login` est autorisée dans le navigateur quand vous acceptez l'organisation. Jusque-là GitHub répond `403` (*Resource protected by organization SAML enforcement*) ou, pire, répond `200` en omettant les dépôts privés (l'en-tête `X-GitHub-SSO: partial-results`), ce qui ressemble à une organisation avec peu de dépôts.

Un jeton qui ne voit pas un dépôt privé reçoit `404`, exactement comme s'il n'existait pas. Une réponse vide peut donc signifier : SSO non autorisé, une portée ou une permission manquante, un dépôt privé que l'accès ne voit pas, ou pas d'Actions du tout. La section suivante les distingue.

## 3. `--doctor` l'explique

`py -3 bin/actions_monitor.py --doctor` (aussi `bin/monitor_cli.py doctor`) fait trois petites lectures et rapporte deux lignes :

- **L'accès peut lire le compte ou l'organisation** (`access`) : `ok` avec l'identifiant et ses portées ; ou `warn` avec la cause dans le détail : `sso` (non autorisé, ou dépôts privés masqués), `rate_limited`, `scope` (une permission manque), `not_found` (le compte n'existe pas ou n'est pas visible), `forbidden` ; `fail` quand GitHub refuse les identifiants. Un jeton à granularité fine n'a pas de portées à lister et la ligne le dit.
- **Les lectures par heure tiennent dans le quota** (`estimate`) : les dépôts du compte et les lectures par heure que demanderaient les réglages actuels, face aux 5 000 par heure d'un jeton personnel. C'est une estimation sans appel : le sondage des runs (un dixième des dépôts chauds, toutes les `refresh_seconds` ; les autres toutes les `cold_refresh_seconds`), la Sentinelle (au plus `sentinel.budget_per_hour`) et, quand les fichiers de workflow sont lus sans clones, leur part. `warn` au-delà de 60 %. Pour la réduire : augmentez `cold_refresh_seconds`, activez le mode Low, surveillez moins de dépôts (`repos`) ou lisez avec une GitHub App.

Les mêmes causes sont écrites, avec le dépôt, partout où le moniteur n'a pas pu lire des fichiers de workflow : le panneau A13 de la Sentinelle les liste comme *non évaluables* avec le motif, jamais comme un « pas de données » muet.

## 4. Surveiller un compte qui n'est pas le vôtre (observateur sans permissions)

N'importe quel jeton peut lire les dépôts publics de n'importe quel compte : vous pouvez donc surveiller une organisation open source avec un jeton sans aucune portée. Ce qu'un observateur n'obtient pas, et que le moniteur traite comme *inconnu* et jamais comme *bon* : rulesets et protection de branche, alertes Dependabot, code scanning et secret scanning, paramètres, et listes de runs des dépôts dont Actions est désactivé. Les panneaux qui en dépendent (A3, parties de A6) sont vides ou marqués non évaluables pour ces dépôts. Rien n'est jamais écrit, aucune permission d'écriture n'est donc nécessaire.

## 5. Limites connues

- Le quota est de 5 000 lectures par heure pour un jeton personnel ; une GitHub App installée sur une grande organisation en a davantage (voir `QUOTA.md`). L'estimation ci-dessus est le moyen le plus rapide de savoir si vous y tenez.
- Le moniteur lit un échantillon des derniers runs de chaque dépôt. Un dépôt qui lance des centaines de runs par heure est vu à travers cet échantillon, pas run par run.
- GitHub conserve les journaux et artefacts d'un run 90 jours par défaut ; le moniteur ne peut pas lire ce que GitHub a supprimé.
- Un jeton à granularité fine appartient à un seul propriétaire : surveiller deux organisations demande deux jetons (deux comptes du moniteur, voir `ACCOUNTS.md`).
- Les organisations qui exigent l'approbation des jetons, ou bloquent les jetons classiques, demandent d'abord l'action d'un propriétaire ; aucun réglage du moniteur ne peut contourner cela.
