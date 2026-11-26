<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# Greffons et coffres de secrets

Les greffons ajoutent des contrôles au moniteur sans le modifier. Tout est désactivé par défaut. L'édition Lite n'a pas de greffons.

## Activer

Activez `plugins.enabled`, puis le greffon voulu. Réglages > Extensions montre chacun avec ses permissions, sa clé, son état et ce qui est isolé. Leurs constats sont des alertes de la source `plugin`, précédées du nom du greffon.

## Greffons officiels

Ils voyagent dans la version signée et tournent dans le moniteur, dans leur propre fil.

- **discussions** (`plugins.official.discussions.enabled`) : discussions sans commentaire depuis plus de `plugins.official.discussions.days` jours. Les issues et PR relèvent de Collab.
- **packages** (`plugins.official.packages.enabled`) : paquets container ou npm avec plus de versions que `plugins.official.packages.max_versions`. Nécessite `read:packages`. Les releases relèvent de la sentinelle de livraison.

## Greffons de tiers

Activez `plugins.third_party.enabled`. Un paquet est un zip avec `plugin.json` et une signature détachée `NOM.zip.ed25519.sig` faite par son auteur. Il n'est installé que si une clé de **votre** trousseau de portée `plugins` l'a signé, et seulement après avoir répété l'empreinte de cette clé. Il arrive désactivé. La signature est revérifiée avant chaque exécution ; une clé révoquée ou un fichier modifié met le greffon en pause.

**Signé ne veut pas dire sûr.** Un manifeste n'est pas un bac à sable.

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## Ce qui est isolé

| Système | Processus séparé, environnement vide, sans jeton | Sans réseau | Mémoire et processus enfants |
|---|---|---|---|
| Linux | oui | oui si le système autorise les espaces de noms utilisateur, sinon **sans isolation réseau** | limites de mémoire et de CPU |
| Windows | oui | **non** : **sans isolation réseau** | Job Object : limite de mémoire, aucun processus enfant |
| macOS | oui | **non** : **sans isolation réseau** | limite de CPU ; mémoire non garantie |

Sur aucun système vos fichiers ne sont cachés à un tel greffon : il tourne avec votre utilisateur. `plugins.worker.platforms_ok` vide : aucun greffon de tiers. Les lectures de GitHub passent par le moniteur, qui n'autorise que les `get_paths` du manifeste sur les dépôts surveillés. `plugins.worker.timeout_s`, `max_output_kb` et `memory_mb` bornent chaque exécution.

## Sortie non fiable et santé

Les titres sont nettoyés et coupés (`plugins.alert_title_max`), seuls les liens vers github.com sont gardés et un greffon de tiers ne peut pas lever d'alerte critique. Le texte d'un greffon est une donnée, jamais une consigne pour une IA. Après `plugins.breaker.failures` échecs consécutifs il est mis en pause jusqu'à reprise ; en pause ou dégradé ne signifie pas « tout va bien ». Le contrôle `plugins` du doctor et `plugin audit` signalent les paquets révoqués ou modifiés.

## Pour les auteurs

Le contrat est la version 1 (`api_compat`). `run(ctx)` renvoie `{"alerts": [{id, code, level, repo, url, title}]}` ; `ctx` offre `owner`, `now`, `options`, `repos()`, `get(path)`, `discussions()`, chacun avec sa permission (`repos.list`, `gh.get`, `graphql.discussions`). `init` écrit un modèle avec son test. Le moniteur ne signe jamais.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Routes et paquets pip

Routes (administrateur, modifications seulement depuis cet ordinateur) : `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. Avec `plugins.entry_points`, le moniteur liste les paquets installés par pip qui déclarent le groupe `gha_monitor.plugins` et portent un `*.plugin.zip` ; leur code n'est jamais importé, on installe le zip comme les autres.

## Lire le jeton GitHub depuis un autre programme

`secrets.backend` lit le jeton au lieu de le conserver dans le moniteur (`github_token.enabled` doit être activé). Lecture seule. `vault` (HTTP, `secrets.vault.addr`, `path`, `field`, jeton Vault dans la variable nommée par `token_env` ; https, ou http vers cet ordinateur seulement), `sops` (`secrets.sops.file`, `field` ; seulement sur une machine de confiance), `bitwarden` (`bws`, `secrets.bitwarden.item`), `aws`, `azure`, `gcp` (leurs outils, `secrets.cloud.ref`). Avec `secrets.reload_on_rotate` il est relu tous les `secrets.reload_seconds`. Testé contre des serveurs factices et un Vault en mode développement ; aucun compte cloud réel.
