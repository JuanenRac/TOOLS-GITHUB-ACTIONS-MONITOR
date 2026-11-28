<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# Plugins and secret stores

Plugins add checks to the monitor without changing it. Everything is off by default. The Lite edition has no plugins.

## Switch on

Turn on `plugins.enabled`, then the plugin you want. Settings > Extensions shows each one with its permissions, key, state and what is isolated. Their findings are alerts of the source `plugin`, with the plugin's name in front.

## Official plugins

They travel inside the signed release and run inside the monitor, in a thread of their own.

- **discussions** (`plugins.official.discussions.enabled`): discussions with no comment for more than `plugins.official.discussions.days` days. Issues and pull requests are Collab's business and are not repeated.
- **packages** (`plugins.official.packages.enabled`): container or npm packages with more versions than `plugins.official.packages.max_versions`. Needs `read:packages`. Releases belong to the delivery sentinel.

## Plugins of other people

Turn on `plugins.third_party.enabled`. A package is a zip with `plugin.json` plus a detached signature `NAME.zip.ed25519.sig` made by the author with their own tools. It is installed only when a key of **your** keyring with the scope `plugins` signed it, and only after you repeat the fingerprint of that key. It arrives switched off. The signature is checked again before every run; a revoked key or a changed file pauses the plugin.

**Signed does not mean safe**: a signature says who made it, not what it does. A manifest is not a sandbox.

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

## What is isolated

| System | Separate process, empty environment, no token | No network | Memory and child processes |
|---|---|---|---|
| Linux | yes | yes when the system allows user namespaces, else labelled **no network isolation** | memory and CPU limits |
| Windows | yes | **no**: labelled **no network isolation** | Job Object: memory limit, no child processes |
| macOS | yes | **no**: labelled **no network isolation** | CPU limit; memory not guaranteed |

On no system are your files hidden from such a plugin: it runs with your user. `plugins.worker.platforms_ok` empty means plugins of other people never run. Reads of GitHub are asked to the monitor, which only allows the `get_paths` of the manifest on watched repositories. `plugins.worker.timeout_s`, `max_output_kb` and `memory_mb` bound each run. While `security.read_only_strict` or `security.egress_policy` restricts the monitor, those limits cannot be enforced inside another program, so a plugin of another person runs only when its process really has no network (Linux with user namespaces); otherwise it is not run and its reason says `restricted`.

## Untrusted output and health

Titles are cleaned and cut (`plugins.alert_title_max`), only links to github.com are kept, and a plugin of another person cannot raise a critical alert. A plugin text is data, never an instruction for an AI. After `plugins.breaker.failures` failures in a row the plugin is paused until you resume it; a paused or degraded plugin is not "all fine". The doctor check `plugins` and `plugin audit` report revoked or changed packages.

## For authors

The contract is version 1 (`api_compat`). `run(ctx)` returns `{"alerts": [{id, code, level, repo, url, title}]}`; `ctx` offers `owner`, `now`, `options`, `repos()`, `get(path)` and `discussions()`, each needing its permission (`repos.list`, `gh.get`, `graphql.discussions`). `init` writes a template with its test. The monitor never signs anything.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Routes and pip packages

Routes (administrator, changes only from this computer): `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. With `plugins.entry_points` the monitor lists packages installed with pip that declare the group `gha_monitor.plugins` and carry a `*.plugin.zip`; their code is never imported, you install the zip like any other.

## Reading the GitHub token from another program

`secrets.backend` reads the token instead of storing it in the monitor (the stored token setting `github_token.enabled` must be on). Read only; nothing is written there. `vault` (HTTP, `secrets.vault.addr`, `path`, `field`, the Vault token in the environment variable named by `token_env`; https, or http only to this computer), `sops` (`secrets.sops.file`, `field`; only on a computer you trust), `bitwarden` (`bws`, `secrets.bitwarden.item`), `aws`, `azure`, `gcp` (their command line tools, `secrets.cloud.ref`). With `secrets.reload_on_rotate` it is read again every `secrets.reload_seconds`. Tested against fake servers and a Vault in development mode; no real cloud account has been tried.
