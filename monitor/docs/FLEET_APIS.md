<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# Fleet by role and group, read APIs and the demo site

## Roles and groups

At the end of the Fleet tab: the worst state of each group (ecosystem) with a link to its own screen `/g/<key>`, and one column per role of workflow (`fleet.roles`). Not read is `unknown`, never fine.

## Switching off

`fleet.disabled` takes names, patterns or `group:<key>`; the monitor stops reading them at the next cycle, without restarting. Complete and Full editions.

## Read APIs

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. All read only, behind the same access checks as the rest; also under `/api/v1/` while the versioned API is on. `fleet.cctray` serves the CCTray feed for CCMenu and similar tools; `fleet.security_api` serves counts of secret and code scanning alerts per repository (never a secret), with what could not be read named. Both off by default.

## Report digest

Reports and AI briefs carry `report_digest`: SHA-256 of the facts, the version of the monitor, the version of the rules and the verdict. Two readers with the same digest saw the same thing. It is not a signature.

## Demo site

A static copy of the demo (invented data, no login, no action, no request elsewhere) and a workflow check that runs in the browser with Pyodide (nothing is uploaded):

```
python tools/make_public_demo.py demo-site
```

The workflow *Demo site* keeps it as an artifact. Publishing it on a web address is a separate decision that the repository owner takes; nothing publishes it by itself. The browser check has not been tried on a published site.

## All settings

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
