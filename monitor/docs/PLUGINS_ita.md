<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# Plugin e archivi di segreti

I plugin aggiungono controlli al monitor senza modificarlo. Tutto è spento per impostazione predefinita. L'edizione Lite non ha plugin.

## Attivare

Attiva `plugins.enabled` e poi il plugin voluto. Impostazioni > Estensioni mostra ognuno con permessi, chiave, stato e cosa è isolato. I risultati sono avvisi della fonte `plugin`, con il nome del plugin davanti.

## Plugin ufficiali

Viaggiano nella versione firmata e girano nel monitor in un thread proprio.

- **discussions** (`plugins.official.discussions.enabled`): discussioni senza commenti da più di `plugins.official.discussions.days` giorni. Issue e PR sono di Collab.
- **packages** (`plugins.official.packages.enabled`): pacchetti container o npm con più versioni di `plugins.official.packages.max_versions`. Serve `read:packages`. Le release sono della sentinella di consegna.

## Plugin di terze parti

Attiva `plugins.third_party.enabled`. Un pacchetto è uno zip con `plugin.json` e una firma separata `NOME.zip.ed25519.sig` fatta dall'autore. Si installa solo se firmato da una chiave del **tuo** portachiavi con ambito `plugins`, e solo dopo aver ripetuto l'impronta. Arriva spento. La firma si ricontrolla prima di ogni esecuzione; una chiave revocata o un file cambiato sospende il plugin.

**Firmato non vuol dire sicuro.** Un manifesto non è una sandbox.

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

## Cosa è isolato

| Sistema | Processo separato, ambiente vuoto, nessun token | Senza rete | Memoria e processi figli |
|---|---|---|---|
| Linux | sì | sì se il sistema consente i namespace utente, altrimenti **senza isolamento di rete** | limiti di memoria e CPU |
| Windows | sì | **no**: **senza isolamento di rete** | Job Object: limite di memoria, nessun processo figlio |
| macOS | sì | **no**: **senza isolamento di rete** | limite di CPU; memoria non garantita |

Su nessun sistema i tuoi file sono nascosti a un tale plugin: gira con il tuo utente. `plugins.worker.platforms_ok` vuoto: i plugin di terzi non girano mai. Le letture di GitHub passano dal monitor, che consente solo le `get_paths` del manifesto sui repository osservati. `plugins.worker.timeout_s`, `max_output_kb` e `memory_mb` limitano ogni esecuzione.

## Output non affidabile e salute

I titoli si puliscono e tagliano (`plugins.alert_title_max`), restano solo i link a github.com e un plugin di terzi non può alzare un avviso critico. Il testo di un plugin è un dato, mai un'istruzione per un'IA. Dopo `plugins.breaker.failures` errori di fila viene sospeso finché non lo riprendi; sospeso o degradato non significa «tutto bene». Il controllo `plugins` del doctor e `plugin audit` segnalano pacchetti revocati o cambiati.

## Per gli autori

Il contratto è la versione 1 (`api_compat`). `run(ctx)` restituisce `{"alerts": [{id, code, level, repo, url, title}]}`; `ctx` offre `owner`, `now`, `options`, `repos()`, `get(path)`, `discussions()`, ciascuno con il suo permesso (`repos.list`, `gh.get`, `graphql.discussions`). `init` scrive un modello con il test. Il monitor non firma mai.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Rotte e pacchetti pip

Rotte (amministratore, modifiche solo da questo computer): `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. Con `plugins.entry_points` il monitor elenca i pacchetti installati con pip che dichiarano il gruppo `gha_monitor.plugins` e portano un `*.plugin.zip`; il loro codice non viene mai importato, si installa lo zip come gli altri.

## Leggere il token di GitHub da un altro programma

`secrets.backend` legge il token invece di tenerlo nel monitor (`github_token.enabled` deve essere attivo). Sola lettura. `vault` (HTTP, `secrets.vault.addr`, `path`, `key`, token di Vault nella variabile indicata da `token_env`; https, o http solo verso questo computer), `sops` (`secrets.sops.file`, `key`; solo su un computer fidato), `bitwarden` (`bws`, `secrets.bitwarden.secret_id`), `aws`, `azure`, `gcp` (i loro strumenti, `secrets.cloud.ref`). Con `secrets.reload_on_rotate` si rilegge ogni `secrets.reload_seconds`. Provato con server finti e un Vault in modalità sviluppo; nessun account cloud reale.
