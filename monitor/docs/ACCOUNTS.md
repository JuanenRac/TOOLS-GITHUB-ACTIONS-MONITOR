<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# Several accounts

The complete edition can watch several GitHub accounts (a person or an organisation) at once. Every account is a monitor of its own: a separate process, with its own folder, its own port on `127.0.0.1`, its own configuration and its own reading of the GitHub allowance. A crash, a slow answer or a rate limit of one account never touches the others. The lite edition has one account and none of this: it does not even show the options below.

## When there is nothing to do

Without an `accounts/` folder the monitor works exactly as before: one account, its files next to the code. You only read on if you want more than one.

## The folder of accounts

```
accounts/
  global.json              optional: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   the configuration of this account (its github_owner, repos, sentinel...)
  org-acme/
    actions_monitor.json
```

The id of an account is lower case letters, digits, `_` and `-` (up to 40 characters), because it is a folder name; anything else is refused. `enabled_accounts` is `"all"` or a list; `default_account` is the one that opens when none is asked for. `MONITOR_ACCOUNTS_DIR` moves the folder. Each account keeps its cache, events, analytics, sentinel state and logs inside its own folder, so no two accounts share a file.

## Moving from one account to several

```
python actions_monitor.py --migrate-accounts          # shows what would be copied, writes nothing
python actions_monitor.py --migrate-accounts --apply  # copies it into accounts/default/
python actions_monitor.py --accounts                  # lists the accounts
```

The originals are never moved or deleted: you delete them yourself once you have checked. A second run refuses, so two states never mix. To add an account, create `accounts/<id>/actions_monitor.json` with its `github_owner` (copy the template `actions_monitor.example.json`).

## Running

`python actions_monitor.py` with an `accounts/` folder starts the supervisor, one small process on the usual port (8765) that starts one monitor per account and gives the page and the tools a single address. It reads nothing from GitHub and writes nothing. If an account dies it starts it again with a growing wait (2, 5, 15, 30, 60 and then 120 seconds) and the summary says it is down meanwhile. `python actions_monitor.py --account personal` runs only that account, as an ordinary monitor.

## The page

The page is the one you know, with a switcher of accounts under the header and an entry **All accounts** that shows one card per account (state, repositories, running, failing) and opens any of them. Every window keeps its own account and view: it is read from the address, never from one setting that another window would overwrite.

| Address | What it shows |
|---|---|
| `/?account=org-acme` | the page of that account |
| `/?account=all` | the cards of all the accounts |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | one panel |
| `/?chrome=0` | no header buttons, tabs or filters: a screen for a wall or a second monitor |

For several screens open one window per view, for example `?view=now&chrome=0`, `?view=alerts&chrome=0` and `?view=live&chrome=0`. One monitor serves them all, so you do not spend the allowance twice. The view **Live** shows the last events GitHub sent, the state of the webhook receiver (on or off, how many deliveries were accepted, ignored, repeated or refused, never the secret) and a selector of the working mode.

## The API

`GET /api/accounts` is the summary, `GET /api/accounts/<id>/status` one account, and every other request under `/api/` goes to the account named with `?account=<id>` or the header `X-Account-Id` (the default account when none is given). An unknown account is a 404. The access rules are the ones of a single monitor: the same host and origin check, and the same access token in the network mode. The one-use token of a change must be asked for the same account the change is sent to.

## One webhook for all of them

`POST /api/webhook` is a single address for the whole installation. The supervisor reads only the owner of the repository in the payload (`repository.full_name`) and passes the event, untouched, to the account whose `github_owner` is that owner; the account verifies the signature with its own secret. An owner nobody watches is answered and ignored. To choose the account yourself add `?account=<id>`.

## Limits and honesty

- Several accounts are several processes: each one reads GitHub on its own, so the allowance is shared by the login you use. Watch it in the cards, and lower `refresh_seconds` or `max_workers` per account if you need to.
- The checks that need a real browser, real GitHub accounts and a real webhook tunnel are for you to run; the tests use stand-ins for the monitor of an account and never call GitHub.
- A later version brings the accounts into one process; the folder layout and the API above stay.
