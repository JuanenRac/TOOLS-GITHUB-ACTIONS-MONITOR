<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <b>🇮🇹 Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Controlla i workflow di tutti i tuoi repository e ti dice, su una pagina locale, cosa è rosso, cosa è bloccato e cosa ti aspetta.

**GitHub Actions Monitor** è un piccolo programma che gira sul tuo computer. Chiede a GitHub, con il tuo accesso `gh`, le ultime esecuzioni di ogni workflow dei tuoi repository, decide cosa è davvero rosso, segnala ciò che conta (sicurezza, igiene, versioni pronte, quota) e mostra tutto su una pagina web che solo il tuo computer può aprire. Richiede solo Python e `gh`, non memorizza mai un token e, per impostazione predefinita, legge soltanto.

## In breve

| | |
|---|---|
| **Versione** | **1.5.2** · [tutte le release](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Richiede** | Python 3.11+ e la CLI di GitHub (`gh auth login`); nient'altro |
| **Si apre** | su una pagina di `127.0.0.1` soltanto, in otto lingue |
| **Scrive su GitHub** | mai da solo: solo i comandi a lotti che avvii con un `--go` esplicito |
| **Esporta** | `ci_red.json`, metriche Prometheus e JSON per Grafana (tutto spento finché non lo accendi) |

## Schermate

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

*Dati dimostrativi: i repository e i nomi nelle immagini sono inventati.*

## Cosa fa

- **Rosso o no, con una sola regola**: l'ultima esecuzione terminata di ogni workflow sul ramo predefinito. Le esecuzioni annullate o saltate non nascondono mai un errore precedente.
- **Sentinella**: avvisi di sicurezza, igiene dei repository, pull request vecchie, versioni pronte da pubblicare, build in attesa di firma e un rapporto in linguaggio semplice.
- **Pagina delle impostazioni**: cambia percorsi, intervalli, quote e interruttori dal browser; solo un elenco fisso di chiavi validate, con copia di sicurezza prima di ogni salvataggio.
- **Grafici e storico**: minuti di calcolo, errori e successi con barre animate e uno storico giornaliero (rispetta il movimento ridotto).
- **Otto lingue** (en, es, de, fr, it, ja, zh, pt) con l'inglese come base; si cambia nelle impostazioni.
- **Uscite per dashboard**: `ci_red.json`, un endpoint Prometheus e una fonte JSON per Grafana, con una dashboard Grafana importabile.
- **Strumenti a lotti**: pianificano e avviano molte build insieme; nulla parte senza `--go`.

## Architettura

<p align="center"><img src="images/architecture.svg" alt="Architettura" width="100%"></p>

## Avvio rapido

1. Installa Python 3.11 o successivo e la [CLI di GitHub](https://cli.github.com/), poi esegui `gh auth login`.
2. Scarica questo repository (o lo zip dell'ultima release) e apri la cartella `monitor`.
3. Avvialo: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS doppio clic su `MONITOR_GITHUB_ACTIONS.command`, oppure `python actions_monitor.py` ovunque.
4. Apri l'indirizzo stampato (`http://127.0.0.1:<porta>`). Al primo avvio crea `actions_monitor.json` dall'esempio.
5. Apri **Impostazioni** per indicare il tuo account GitHub, gli ecosistemi (gruppi di repository per prefisso del nome) e il resto.

> Aggiorni da una versione precedente alla 1.5.0? [`monitor/docs/MIGRATING_ita.md`](monitor/docs/MIGRATING_ita.md)

## Impostazioni

Tutto vive in `actions_monitor.json` (creato da `actions_monitor.example.json`). La scheda **Impostazioni** lo modifica in modo sicuro; token e segreti non vengono mai mostrati né salvati. Ecosistemi, obiettivi di build e profili a lotti sono file separati che indichi tu (`ecosystems_file`, `targets_file`, `profiles_file`); sono inclusi modelli neutri `*.example.json`. Riferimento completo: [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md).

## Uscite per Grafana e dashboard

Tutto spento per impostazione predefinita, solo locale (`127.0.0.1`) e senza token aggiuntivi. Attivandolo nelle impostazioni ottieni `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, più una dashboard Grafana importabile in [`monitor/docs/grafana`](monitor/docs/grafana). Dettagli: [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md). Il formato di `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md).

## Sicurezza

- Ascolta solo su `127.0.0.1` e rifiuta le richieste il cui `Host` o `Origin` non è locale. Non associarlo mai a `0.0.0.0`: non ha login.
- Non memorizza alcun token: usa il tuo `gh`.
- Non scrive nulla su GitHub da solo. Solo `dispatch --go`, `dispatch --real` e `finalize --execute` scrivono, e solo quando li avvii tu.
- La pagina delle impostazioni scrive un elenco fisso di chiavi validate, dopo aver salvato una copia di sicurezza.

## Test

Non richiedono rete né pacchetti aggiuntivi:

```
python -m unittest discover -s monitor/tests
```

## Struttura del repository

<p align="center"><img src="images/repository-structure.svg" alt="Struttura del repository" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                          il programma
├── docs/                             architettura, schermate
├── tools/                            generatori di immagini e guide
├── images/                           banner e immagini
├── .github/                          CI e moduli
├── CHANGELOG.md                      modifiche per versione
├── LICENSE NOTICE AUTHORS            licenze e autore
├── CONTRIBUTING.md SECURITY.md       contribuire, segnalare
├── SUPPORT.md CODE_OF_CONDUCT.md     supporto e condotta
└── monitor/
    ├── actions_monitor.py            server locale
    ├── actions_monitor.html          la pagina web
    ├── sentinel_local.py             avvisi e rapporto
    ├── surface.py readiness.py       controlli, preparazione
    ├── settings_api.py outputs.py    impostazioni, metriche
    ├── signstate.py sigverify.py     firma: stato, verifica
    ├── read_report.py                rapporto da terminale
    ├── gha_dispatch_all.py           build a lotti
    ├── events.py report_history.py   eventi e storico
    ├── ci_red.py export_status.py    file per altri
    ├── i18n.py locales/              otto lingue
    ├── toolconfig.py workspace.py    impostazioni, cloni
    ├── tests/                        test offline
    └── docs/                         impostazioni, webhook
```

## Documentazione

- [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md): tutte le impostazioni
- [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md): metriche, Grafana ed esportazioni
- [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md): il formato di ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_ita.md`](monitor/docs/CI_RED_BRIDGE_ita.md): portare ci_red.json in una dashboard
- [`monitor/docs/WEBHOOK_ita.md`](monitor/docs/WEBHOOK_ita.md): il webhook in ingresso
- [`monitor/QUICKSTART_it.txt`](monitor/QUICKSTART_it.txt): primi passi, in otto lingue

## Contribuire

Leggi [CONTRIBUTING.md](CONTRIBUTING.md). Segnala bug e idee con i moduli delle issue; i problemi di sicurezza come descritto in [SECURITY.md](SECURITY.md).

## Autore

Scritto da **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licenza

Il codice è GPL-3.0-or-later; la documentazione è CC BY-SA 4.0. Vedi [LICENSE](LICENSE) e [NOTICE](NOTICE).
