# Contribuire a GitHub Actions Monitor

## Stack tecnologico
- **Linguaggio**: Python 3.11 o successivo; il nucleo non richiede pacchetti (la vista da terminale, `bin/tui.py`, usa Rich, opzionale; i test saltano ciò che ne ha bisogno se manca).
- **Interfaccia**: una pagina web locale (`monitor/assets/static/actions_monitor.html`) servita su `127.0.0.1`, più strumenti da riga di comando.
- **Fonte dei dati**: il client ufficiale da riga di comando di GitHub, `gh` (chiamate di sola lettura per impostazione predefinita).

## Linee guida
1. **Prima i test**: `python -m unittest discover -s monitor/tests` deve passare prima di una pull request. Offline: i test non chiamano mai GitHub. Per provare a mano i servizi reali usa `python tools/manual_check_live.py`.
2. **Otto lingue**: ogni testo leggibile da un utente sta in `monitor/assets/locales/<lang>.json` per en, es, de, fr, it, ja, zh e pt (portoghese europeo). Una chiave nuova va in tutti e otto i file; i test verificano che abbiano le stesse chiavi.
3. **Niente segreti**: per impostazione predefinita il monitor non conserva token (lo chiede a `gh`); l'unico token opzionale vive solo nell'archivio sicuro del sistema (`secretstore.py`). Non aggiungere codice che legge, stampa, registra o scrive credenziali altrove e non committare mai un vero `actions_monitor.json`.
4. **Sicuro per impostazione predefinita**: tutto ciò che scrive su GitHub, esegue un programma, apre una porta di rete o invia dati all'esterno è spento di default, ha un interruttore proprio in Impostazioni > Avanzate, chiede una conferma propria e ascolta su `127.0.0.1` salvo modalità rete attiva. Una funzione così arriva con test che dimostrano che rifiuta senza interruttore, senza conferma e senza token, e che nulla finisce in un log.
5. **Piccoli passi**: una modifica per pull request, con la riga corrispondente in `CHANGELOG.md`.
6. **Immagini**: modifica `docs/architecture.json` o `docs/structure.json` ed esegui `python tools/make_architecture.py` / `python tools/make_structure.py`; non modificare mai l'SVG a mano.
7. **Registro delle modifiche in otto lingue**: ogni nuova voce di `monitor/CHANGELOG.md` riceve la sua traduzione in `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (stesse versioni e sezioni; una voce non ancora tradotta mantiene il testo inglese sotto un avviso tradotto). `python tools/make_help_index.py --check` e il controllo di rilascio falliscono se una versione manca in una traduzione.

## Aggiornare un pannello di stato dopo ogni versione

`.github/workflows/dashboard-dispatch.yml` viene eseguito quando il workflow `CI` termina in verde su `main` (solo eventi push). Se il responsabile definisce il secret opzionale del repository `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, chiede a un repository di dashboard di aggiornare la sua tabella delle versioni; senza il secret termina in silenzio, non ha permessi e non cambia né ritarda mai la CI. La versione in `electro-hobby-3d.project.json` deve essere uguale a `tool_version.py` a ogni versione; un test lo verifica.

- Lista di controllo dell'aiuto: l'aiuto delle Impostazioni (`cfg.h.<chiave>`) di ogni nuova impostazione, l'aiuto della scheda modificata, le guide in `monitor/docs/`, le otto lingue, l'indice dell'aiuto (`python tools/make_help_index.py`) e il registro delle modifiche.
