<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# Più account

L'edizione completa può osservare più account GitHub (una persona o un'organizzazione) contemporaneamente. Ogni account è un monitor a sé: un processo separato, con la sua cartella, la sua porta su `127.0.0.1`, la sua configurazione e la sua lettura della quota di GitHub. Un guasto, una risposta lenta o un limite di frequenza di un account non tocca mai gli altri. L'edizione lite ha un solo account e nulla di tutto questo: non mostra nemmeno le opzioni qui sotto.

## Quando non c'è nulla da fare

Senza una cartella `accounts/` il monitor funziona esattamente come prima: un account, i suoi file nelle cartelle `config/`, `data/` e `logs/` (vedi LAYOUT). Continui a leggere solo se ne vuoi più di uno.

## La cartella degli account

```
accounts/
  global.json              facoltativo: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   la configurazione di questo account (il suo github_owner, repos, sentinella...)
  org-acme/
    actions_monitor.json
```

L'id di un account è formato da lettere minuscole, cifre, `_` e `-` (fino a 40 caratteri), perché è il nome di una cartella; tutto il resto viene rifiutato. `enabled_accounts` è `"all"` o un elenco; `default_account` è quello che si apre quando non se ne chiede nessuno. `MONITOR_ACCOUNTS_DIR` sposta la cartella. Ogni account tiene cache, eventi, analisi, stato della sentinella e registri nella propria cartella, così due account non condividono mai un file.

## Passare da un account a più

```
python bin/actions_monitor.py --migrate-accounts          # mostra cosa verrebbe copiato, non scrive nulla
python bin/actions_monitor.py --migrate-accounts --apply  # lo copia in accounts/default/
python bin/actions_monitor.py --accounts                  # elenca gli account
```

Gli originali non vengono mai spostati né eliminati: li elimini tu dopo aver controllato. Una seconda esecuzione si rifiuta, così due stati non si mescolano mai. Per aggiungere un account, crea `accounts/<id>/actions_monitor.json` con il suo `github_owner` (copia il modello `assets/examples/actions_monitor.example.json`).

## Esecuzione

`python bin/actions_monitor.py` con una cartella `accounts/` avvia il supervisore, un piccolo processo sulla porta di sempre (8765) che avvia un monitor per account e dà alla pagina e agli strumenti un unico indirizzo. Non legge nulla da GitHub e non scrive nulla. Se un account muore, lo riavvia con un'attesa crescente (2, 5, 15, 30, 60 e poi 120 secondi) e il riepilogo lo dichiara fermo nel frattempo. `python bin/actions_monitor.py --account personal` esegue solo quell'account, come un monitor normale.

## La pagina

La pagina è quella che conosci, con un selettore di account in cima al pannello laterale e una voce **Tutti gli account** che mostra una scheda per account (stato, repository, in esecuzione, in errore) e ne apre una qualsiasi. Ogni finestra mantiene il proprio account e la propria vista: si leggono dall'indirizzo, mai da un'unica impostazione che un'altra finestra sovrascriverebbe.

| Indirizzo | Cosa mostra |
|---|---|
| `/?account=org-acme` | la pagina di quell'account |
| `/?account=all` | le schede di tutti gli account |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | un pannello |
| `/?chrome=0` | senza pulsanti d'intestazione, schede né filtri: uno schermo per una parete o un secondo monitor |

Per più schermi apri una finestra per vista, ad esempio `?view=now&chrome=0`, `?view=alerts&chrome=0` e `?view=live&chrome=0`. Un solo monitor le serve tutte, così non spendi la quota due volte. La vista **Live** mostra gli ultimi eventi inviati da GitHub, lo stato del ricevitore webhook (attivo o spento, quante consegne sono state accettate, ignorate, ripetute o rifiutate, mai il segreto) e un selettore della modalità di lavoro.

## L'API

`GET /api/accounts` è il riepilogo, `GET /api/accounts/<id>/status` un account, e ogni altra richiesta sotto `/api/` va all'account indicato con `?account=<id>` o l'intestazione `X-Account-Id` (l'account predefinito se non ne è dato nessuno). Un account sconosciuto dà 404. Le regole di accesso sono quelle di un monitor singolo: lo stesso controllo di host e origine, e lo stesso token di accesso in modalità rete. Il token monouso di una modifica va chiesto allo stesso account a cui la modifica è inviata.

## Un webhook per tutti

`POST /api/webhook` è un unico indirizzo per l'intera installazione. Il supervisore legge solo il proprietario del repository nel payload (`repository.full_name`) e passa l'evento, intatto, all'account il cui `github_owner` è quel proprietario; l'account verifica la firma con il proprio segreto. Un proprietario che nessuno osserva riceve risposta e viene ignorato. Per scegliere tu l'account aggiungi `?account=<id>`.

## Limiti e onestà

- Più account sono più processi: ognuno legge GitHub per conto suo, quindi la quota è condivisa dal login che usi. Tienila d'occhio nelle schede e abbassa `refresh_seconds` o `max_workers` per account se serve.
- I controlli che richiedono un vero browser, veri account GitHub e un vero tunnel webhook spettano a te; i test usano sostituti del monitor di un account e non chiamano mai GitHub.
- Una versione successiva porterà gli account in un solo processo; la struttura delle cartelle e l'API qui sopra restano.

## Dove un account conserva il suo stato

Per impostazione predefinita in file dentro `accounts/<id>/`. Un account può conservarlo in un database: `"storage": {"backend": "sqlite"}` nella sua configurazione gli assegna `accounts/<id>/storage.sqlite3`, e solo il processo di quell'account lo scrive. La configurazione dell'account resta un file JSON. Vedi [STORAGE_ita.md](STORAGE_ita.md).

Anche il flusso per le IA di ogni account (i suoi avvisi, il suo riepilogo e il registro degli avvisi a una IA esterna) è suo: `ai/accounts/<id>/`. Ogni avviso porta il proprio account e l'aggiornamento di un account non chiude mai gli avvisi di un altro. Se scegli di proposito lo stesso `ai_alerts.folder` per più account, lo condividono senza rischi: ciascuno conserva e chiude solo i propri avvisi.
