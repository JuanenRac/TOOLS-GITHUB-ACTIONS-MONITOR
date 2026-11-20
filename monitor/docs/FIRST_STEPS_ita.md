<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# I tuoi primi cinque minuti

**1. Installa il necessario.** Python 3.11 o successivo e la GitHub CLI (`gh`). Poi accedi una volta: `gh auth login`. Il monitor non salva mai un token: lo chiede a `gh` (a meno che tu non attivi il token opzionale del monitor in Impostazioni > Avanzate).

**2. Verifica tutto con un comando.** `python bin/actions_monitor.py --doctor` indica, per ogni problema, il comando esatto che lo risolve. Vuoi dare prima un'occhiata? `python bin/actions_monitor.py --demo` apre la pagina con dati inventati: senza `gh`, senza accesso, senza rete.

**3. Avvialo.** Doppio clic su `MONITOR_LITE_GITHUB_ACTIONS` per l'edizione semplice (porta 8766) o su `MONITOR_GITHUB_ACTIONS` per quella completa con sentinella (porta 8765). La finestra della console indica l'edizione, nel titolo e nella prima riga.

**4. Segui i tre passi di benvenuto.** La prima volta la pagina spiega cosa fa, mostra ciò che ha trovato nel tuo account e indica le impostazioni di base. Per impostazione predefinita nulla è nascosto: i repository che nessun gruppo reclama compaiono come *Non classificati*.

**5. Sai dove sta la guida.** Il pulsante rotondo **?** (o il tasto `?`) apre la Guida; il pulsante **i** apre Informazioni, con la tua versione, i tuoi file e un pulsante che copia le informazioni per l'assistenza (senza segreti). Da console: `--help-topics`, `--help-search PAROLE`, `--about`.

**6. Salvare o stampare un rapporto.** I due pulsanti in alto nella pagina salvano il rapporto della scheda aperta (TXT, PDF e, se vuoi, JSON, ciascuno dalla finestra **Salva con nome** del browser) oppure lo stampano come pagina pulita ([Uscite per altri strumenti](OUTPUTS.md)).

**Utile sapere.** Se usi un piano con repository privati, sceglilo in Impostazioni > Di base per vedere le tue quote ([Quote e piani](QUOTAS_ita.md)). La sentinella è spiegata in [La sentinella](SENTINEL_ita.md). Lo strumento legge soltanto GitHub; scrive solo dopo la tua conferma.

## Leggere comodamente

- **Densità** (`display.density`, oppure `?density=dense` per una finestra): `dense` riduce spazi e carattere di ogni scheda.
- **Meno movimento** (`display.reduce_motion`): `auto` segue l'impostazione del tuo sistema, `on` ferma ogni animazione e transizione. Lo stato di un workflow è sempre scritto a parole e disegnato anche con una forma, mai solo a colori.
- **Colori per il daltonismo** (`display.palette`, oppure `?palette=colorblind`): blu, vermiglio, giallo e un blu più chiaro, un set per il modo scuro e uno per il chiaro. La barriera di contrasto (`python tools/check_contrast.py`) verifica ogni tema e simula le tre forme di daltonismo.
- **Nessun salto mentre leggi** (`display.live_throttle_s`): finché il puntatore o il focus sono dentro la scheda che leggi, l'aggiornamento periodico attende; un aggiornamento che chiedi tu si applica subito.
- **Novità** (`display.whats_new`): dopo un aggiornamento un avviso offre le voci del registro delle modifiche delle versioni saltate; riaprilo dalla tavolozza. `GET /api/whats-new?since=2.1.5` risponde con le voci (sola lettura).
- **Glossario e limiti**: aprilo dalla tavolozza. `GET /api/glossary` risponde con le cifre scritte con i tuoi parametri reali, gli attacchi che cercano le regole, i limiti dell'analisi e alcuni posti dove saperne di più. Con `report_export.limits` acceso, i rapporti salvati e stampati terminano con i limiti.
- **Il filtro dell'intestazione** copre le schede Ora, Avvisi, Grafici, quelle della Sentinella (Sentinella, CI, Collaborazione, Sicurezza, Consegna, Catena di fornitura), Repository e Cronologia; le altre (Tendenza della Sentinella, Team, Flotta, Rapporti, Lezioni, Aggiornamenti e Impostazioni) sono sempre globali. Una nota sotto il filtro lo dice.
