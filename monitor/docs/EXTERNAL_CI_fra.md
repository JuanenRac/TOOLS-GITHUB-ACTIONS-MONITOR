<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# Sources CI externes (lecture seule)

Un dépôt mis en miroir sur GitHub peut être construit ailleurs. Le moniteur lit Buildbot, GitLab CI, Jenkins et Azure Pipelines et affiche leurs échecs comme ceux d'Actions. Il ne fait que lire (GET) ; il ne lance, n'annule et n'écrit jamais rien. Éditions Complete et Full ; désactivé par défaut.

## Configuration

Activez `external_ci.enabled` et écrivez une ligne par source dans `external_ci.sources` (Réglages > CI externe). `repo` est le nom sous lequel le résultat est affiché.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Rouge, correct ou dégradé

Le dernier build terminé de chaque builder, pipeline ou job sur sa branche décide, comme pour Actions : les demandes de fusion et les états annulés, ignorés ou inconnus ne décident jamais. Un service muet, qui répond autre chose ou à qui manque un builder est **dégradé**, jamais rouge ; les échecs déjà vus restent, marqués comme anciens. Les échecs lèvent `ci.external.red` (niveau `external_ci.alert.level`), comptés, notifiés et mis en sourdine comme un rouge d'Actions ; `ci.external.degraded` est informatif. Les mettre en sourdine ne tait jamais une alerte de sécurité. Chaque source est lue au plus toutes les `external_ci.refresh_seconds` (300 ou plus), moins souvent après `external_ci.breaker.failures` échecs.

## Sécurité

L'adresse est contrôlée à la connexion : cet ordinateur, les réseaux privés et les métadonnées cloud sont refusés sauf avec `external_ci.allow_private_targets`. Aucune redirection ni aucun lien des réponses n'est suivi. Les réponses sont limitées par `external_ci.max_bytes` et `external_ci.timeout_s`. Aucun identifiant n'est écrit dans la configuration : `token_env` contient seulement le NOM d'une variable d'environnement (GitLab : jeton en lecture ; Jenkins : `utilisateur:jeton` ; Azure : jeton personnel avec lecture Build), jamais envoyé sans TLS vers une adresse publique. Le quota GitHub n'est pas utilisé. En mode hors ligne (`airgapped`) rien n'est lu ; `doctor --egress` liste les hôtes.

## Journaux d'un build en échec

Désactivé par défaut (`external_ci.logs.enabled`). Seule la fin est demandée, limitée par `external_ci.logs.max_kb` et `external_ci.logs.tail_lines`, sans séquences de terminal ni caractères de contrôle, expurgée, gardée en mémoire pendant `external_ci.logs.keep_hours`. C'est un texte non fiable, jamais donné à une IA comme instruction. L'expurgation ne peut pas reconnaître tous les secrets.

## Test, état, ligne de commande

Réglages > CI externe propose **Tester la connexion** : une lecture, rien d'enregistré (`POST /api/external-ci/probe`). L'onglet CI des sentinelles montre chaque source ; `GET /api/external-ci/status` donne la même chose et `GET /api/external-ci/log` un journal. Commandes : `external-ci list`, `external-ci status` (code 1 si rouge ou dégradé) et `external-ci probe --source "LIGNE"`.

## Pas encore vérifié

Les quatre adaptateurs n'ont été testés qu'avec des serveurs simulés (`tools/extci_fake_servers.py`). Jenkins et Azure Pipelines portent la mention **expérimental** (`external_ci.experimental`) et demandent `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. Autre adaptateur : une fonction `(reader, source, cfg) -> (runs, missing)` dans `integrations/external_ci/adapters.py`, lisant seulement via `reader`.
