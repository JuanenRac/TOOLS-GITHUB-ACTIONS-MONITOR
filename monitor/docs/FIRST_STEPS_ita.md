<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# I tuoi primi cinque minuti

**1. Installa il necessario.** Python 3.11 o successivo e la GitHub CLI (`gh`). Poi accedi una volta: `gh auth login`. Il monitor non salva mai un token: lo chiede a `gh`.

**2. Verifica tutto con un comando.** `python actions_monitor.py --doctor` indica, per ogni problema, il comando esatto che lo risolve. Vuoi dare prima un'occhiata? `python actions_monitor.py --demo` apre la pagina con dati inventati: senza `gh`, senza accesso, senza rete.

**3. Avvialo.** Doppio clic su `MONITOR_LITE_GITHUB_ACTIONS` per l'edizione semplice (porta 8766) o su `MONITOR_GITHUB_ACTIONS` per quella completa con sentinella (porta 8765). La finestra della console indica l'edizione, nel titolo e nella prima riga.

**4. Segui i tre passi di benvenuto.** La prima volta la pagina spiega cosa fa, mostra ciò che ha trovato nel tuo account e indica le impostazioni di base. Per impostazione predefinita nulla è nascosto: i repository che nessun gruppo reclama compaiono come *Non classificati*.

**5. Sai dove sta la guida.** Il pulsante rotondo **?** (o il tasto `?`) apre la Guida; il pulsante **i** apre Informazioni, con la tua versione, i tuoi file e un pulsante che copia le informazioni per l'assistenza (senza segreti). Da console: `--help-topics`, `--help-search PAROLE`, `--about`.

**Utile sapere.** Se usi un piano con repository privati, sceglilo in Impostazioni > Di base per vedere le tue quote ([Quote e piani](QUOTAS_ita.md)). La sentinella è spiegata in [La sentinella](SENTINEL_ita.md). Lo strumento legge soltanto GitHub; scrive solo dopo la tua conferma.
