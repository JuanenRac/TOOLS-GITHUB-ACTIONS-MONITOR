<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Strumenti da console: linter dei workflow e vista console

Due strumenti a riga di comando, facoltativi. Il monitor in sé non richiede alcun pacchetto; la vista console usa Rich quando la richiedi.

## Il linter dei workflow: `bin/lint_workflows.py`

- `py -3 bin/lint_workflows.py [PERCORSO ...] [--json] [--fail-on info|warn|bad]` controlla `.github/workflows/*.yml` prima del push. Senza percorso guarda la cartella corrente. Apre solo file. `--remote PROPRIETARIO/REPO` (ripetibile) legge i file di workflow di un repository da GitHub con `gh`, senza clone, e dice perché quando non può (SSO non autorizzato, nessun accesso).
- `--remote OWNER/REPO --anon` legge un repository PUBBLICO (di terzi, per esempio) senza alcuna credenziale, quando `lint.anonymous_public` è attiva (disattivata per impostazione predefinita): l'elenco della cartella dei workflow è una richiesta anonima e ogni file arriva da `raw.githubusercontent.com`, che non consuma nulla della quota del tuo token. Un file invariato non viene riletto, un file oltre 256 KiB viene saltato, un repository privato o inesistente dice «non trovato» (mai «pulito») e un monitor isolato dalla rete non legge mai. Non viene mai inviata un'intestazione con un segreto.
- Regole (ognuna si può spegnere e cambiare di gravità nella scheda Impostazioni, sotto-scheda Linter dei workflow): `unpinned_uses` (una action non fissata a un SHA di commit completo), `permissions` (nessun blocco `permissions:`, o `write-all`), `secrets_in_clear` (ciò che sembra un token o una chiave scritti nel file), `injection` (testo di terzi incollato in uno script `run:`) e `pr_target` (`pull_request_target` con checkout del codice della pull request).
- Regole opzionali, spente finché non le attivi: `no_timeout` (un job senza `timeout-minutes`), `secrets_inherit` (`secrets: inherit` nella chiamata di un workflow riutilizzabile), `own_action_main` (un'azione del tuo account che segue `@main`) e `permissions_top` (nessun blocco `permissions:` in cima al file anche se i job hanno il proprio). `unpinned_uses` dice se l'azione è tua o di terzi (`lint.own_owners`), e `lint.unpinned_own` può abbassare o nascondere le tue.
- Il codice di uscita è 1 quando un rilievo raggiunge `--fail-on` (predefinito `bad`), quindi può servire da hook pre-push. Quando il monitor vede i tuoi cloni, aggiunge anche una riga al rapporto giornaliero. Con `--remote` il codice di uscita è 2 quando un repository non ha potuto essere letto (non esiste o non è visibile al token, SSO non autorizzato, nessuna rete) o il suo nome non è `OWNER/REPO`: un repository non letto non viene mai dato per pulito. Lo stesso vale per una cartella o un file indicato che non esiste, e per un file di workflow che non si può leggere: viene nominato sull'uscita degli errori, gli altri vengono comunque controllati e il codice di uscita è 2.
- Un valore che sembra un segreto viene classificato senza mai stamparlo né salvarlo: un formato di token noto o una lunga stringa ad alta entropia è grave (`bad`), un riempitivo leggibile come `placeholder`, `dummy`, `changeme` o `ci` è solo informazione, tutto il resto è un avviso, e `${{ secrets.X }}`, `${X}` o un valore vuoto non è un rilievo. Per silenziare un rilievo scrivi un commento sulla sua riga o su quella prima: `# monitor-lint: ignore secrets_in_clear perché è un riempitivo per docker compose config` (un nome di regola o `all`); oppure elenca modelli `repository:file:regola`, con `*`, nell'impostazione `lint.ignore`.


## La vista console: `bin/tui.py`

- `pip install rich`, poi `py -3 bin/tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Disegna una griglia in tempo reale con ciò che è in corso, i workflow rossi, la coda di firma e il rapporto, letti dal monitor in esecuzione su `127.0.0.1` (nessuna quota GitHub).
- È di sola lettura: nessun tasto rilancia, chiude o scrive nulla. Senza Rich dice come installarlo ed esce con codice 3; il monitor e i suoi test non richiedono mai Rich.
- L'applicazione interattiva da terminale `bin/tui_textual.py` (`pip install textual`; aggiungi `--lite` per l'edizione lite) modifica nella scheda Impostazioni le impostazioni semplici dei gruppi che elenca, le **liste** (elementi separati da virgole: `a, b, c`) e le **mappe di numeri** (`name=3, other=5`); il server ricontrolla ogni valore, e le opzioni di sicurezza si cambiano solo nella pagina.
