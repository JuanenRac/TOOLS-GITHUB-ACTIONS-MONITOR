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
  <img src="https://img.shields.io/badge/Tests-6196_passing-brightgreen.svg" alt="6196 tests">
</p>

> Controlla i workflow di tutti i tuoi repository e ti dice, su una pagina locale, cosa è rosso, cosa è bloccato e cosa ti aspetta.

**GitHub Actions Monitor** è un piccolo programma che gira sul tuo computer. Chiede a GitHub, con il tuo accesso `gh`, le ultime esecuzioni di ogni workflow dei tuoi repository, decide cosa è davvero rosso, segnala ciò che conta (sicurezza, igiene, versioni pronte, quota) e mostra tutto su una pagina web che solo il tuo computer può aprire. Richiede solo Python e `gh`, non memorizza mai un token e, per impostazione predefinita, legge soltanto.

## Che cos'è

- **Un guardiano delle tue GitHub Actions**: con il tuo accesso `gh` legge le ultime esecuzioni di ogni workflow di ogni tuo repository e decide cosa è rosso, cosa è bloccato e cosa ti aspetta.
- **Tre sentinelle che non scrivono mai su GitHub**: CI (esecuzioni e workflow), Collab (issue e pull request che richiedono una persona) e Security (Dependabot, scansione del codice, scansione dei segreti, protezione dei rami) trasformano ciò che leggono in avvisi di un'unica lista.
- **Una pagina, più modi di guardarla**: una pagina locale su `127.0.0.1` che si adatta da un telefono a uno schermo a parete 4K (fino a tre schermi insieme), un client a riga di comando, una vista nel terminale, file e un endpoint per i tuoi pannelli.
- **Due edizioni**: Lite è per una persona e mostra solo le esecuzioni; Complete aggiunge più account, un team con ruoli, un punteggio, la salute di ogni repository, rapporti e un servizio per Docker.
- **Privato per progetto**: nulla lascia il tuo computer tranne le chiamate a GitHub fatte con il tuo accesso; la chiave di un'IA facoltativa resta in una variabile d'ambiente; si scrive su GitHub solo con i comandi a lotti che lanci con un `--go` esplicito.

## Cosa fa

- **Rosso o no, con una sola regola**: l'ultima esecuzione terminata di ogni workflow sul ramo predefinito. Le esecuzioni annullate o saltate non nascondono mai un errore precedente.
- **Sentinella**: avvisi di sicurezza, igiene dei repository, pull request vecchie, versioni pronte da pubblicare, build in attesa di firma e un rapporto in linguaggio semplice.
- **Sentinella Collab e un'unica lista di avvisi**: issue e pull request aperte che richiedono una persona (dimenticate, critiche, revisioni in attesa, vecchie bozze, conflitti), in sola lettura e con un orologio proprio, e una scheda Avvisi con tutte le sentinelle in un elenco, filtro per origine e silenziamenti locali che finiscono da soli.
- **Barra di stato, schermo intero e tabelle ordinabili**: l'avviso più importante (e una finestra con tutti), la connessione, la quota, l'ultima lettura, la modalità, l'indirizzo e l'orologio a piè di pagina; un pulsante a schermo intero; Repository e Cronologia si ordinano per una o più colonne, con le colonne a tua scelta.
- **La riga di comando come client**: `bin/monitor_cli.py` (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`, `score`) legge ciò che dice il monitor in esecuzione, con `--json` e codici di uscita stabili; non scrive mai su GitHub.
- **Due skill per le IA**: brevi guide, in inglese, per l'IA integrata nel monitor (locale o di un fornitore) e per le IA che gli parlano dall'esterno (riga di comando, solo HTTP o file, MCP, stream), generate dal codice perché non manchi nulla; si installano con `python bin/monitor_cli.py install-skill internal|external --dest CARTELLA` o si copiano dalla scheda IA delle Impostazioni (`monitor/docs/SKILLS_ita.md`).
- **Fallimenti e lezioni**: un registro locale dei fallimenti della tua CI, regole che classificano ciascuno in una categoria, una libreria di lezioni (`monitor/docs/LESSONS_ita.md`) con la guardia che l'avrebbe evitato, la tendenza su 24 ore e 7 giorni, `ai/LESSONS.md`, `/api/ai/lessons` e un riepilogo prima del push per qualsiasi strumento di IA; sola lettura, nulla lascia il computer.
- **Ogni dimensione di schermo e più schermi**: la pagina si adatta a una finestra dal telefono al 4K, dritta o ruotata, e un monitor può servire fino a tre schermi (da `/screen/1` a `/screen/3`), ciascuno con le sue schede e il suo orientamento (`monitor/docs/SCREENS_ita.md`).
- **Un punteggio per ogni account**: un numero da 0 a 100, una lettera da A a E e una tendenza, costruiti con l'affidabilità della CI, la sua velocità, il tempo di ripristino e la rapidità con cui si chiudono gli avvisi di collaborazione; dice «calibrazione» o «dati insufficienti» al posto di un numero che non può sostenere, mostra ciò che non copre ancora, sta nell'intestazione della pagina, ha un comando `score`, avvisa quando cala ed è nelle metriche e nel server MCP (`monitor/docs/SCORE.md`).
- **Una sentinella di sicurezza (solo Complete, spenta per impostazione predefinita)**: legge, senza scrivere nulla su GitHub, gli avvisi aperti di Dependabot, dell'analisi del codice e della scansione dei segreti, se il branch predefinito è protetto, il permesso predefinito dei workflow e, su richiesta, i proprietari del codice; genera un avviso per repository e segnale, conta i risultati come quinta parte del punteggio e dice ciò che non ha potuto leggere (`monitor/docs/SENTINEL_SECURITY_ita.md`).
- **Una sentinella della catena di fornitura (solo Complete, spenta per impostazione predefinita)**: legge, senza scrivere nulla su GitHub, i file di workflow di ogni repository tramite API (senza clone) e genera un avviso per repository e segnale quando un'action non è fissata a un commit o segue un branch mobile, un workflow dà `write-all` al token o non dichiara permessi, oppure `pull_request_target` scarica il codice di una pull request; i rilievi vengono dal linter dei workflow, il valore di un segreto non viene mai letto e un repository non leggibile viene elencato invece di essere contato come pulito (`monitor/docs/SENTINEL_SUPPLY_ita.md`).
- **La salute di ogni repository e del team (solo Complete)**: CI, avvisi delle tre sentinelle, preparazione delle versioni e attività in uno stato (cattivo, avvertimento, buono o non visto) con un numero di rischio; la scheda Team mette per primi i repository che richiedono una persona, con filtri, un dettaglio per ciascuno e link diretti per schermi a parete; gli stessi dati sono in `/api/team/health`, `/api/repos/<owner>/<repo>/health` e nel comando `team` (`monitor/docs/HEALTH_ita.md`).
- **Rapporti, registro delle azioni e Apprise (solo Complete)**: un rapporto dell'account (punteggio, cambiamenti, repository che richiedono una persona, avvisi aperti) scritto in HTML e Markdown secondo una pianificazione cron o su richiesta, spento per impostazione predefinita (`monitor/docs/REPORT_SCHEDULE_ita.md`); un registro di chi ha cambiato cosa, con una catena di hash e senza valori né segreti (`monitor/docs/AUDIT_LOG_ita.md`); e un canale Apprise facoltativo per le notifiche, spento per impostazione predefinita.
- **Come servizio**: l'immagine Docker ufficiale (senza root, in sola lettura), un file Compose con proxy facoltativo, un'unità systemd, un controllo di salute approfondito e il comando che crea il primo amministratore (`monitor/docs/DEPLOYMENT.md`).
- **Un'API congelata e una guida per ogni uso**: dalla 2.0.0 la forma di ogni endpoint di lettura e i codici di errore sono fissati in `monitor/docs/schemas/api_contract.json`, uno strumento verifica qualsiasi monitor in esecuzione rispetto a quel contratto (`monitor/tools/check_api_contract.py`) e c'è una guida breve per l'edizione lite, per una persona, per un servizio e per una squadra (`monitor/docs/API_ita.md`).
- **Più account, un team e un posto per i dati**: un processo per account, utenti con ruoli e propri account, i file in `config/`, `data/`, `logs/` e `ai/`, un archivio SQLite facoltativo con retention e backup, e le porte come impostazioni (`monitor/docs/ACCOUNTS.md`, `monitor/docs/STORAGE.md`, `monitor/docs/LAYOUT.md`).
- **Elenchi che si ordinano e si ripiegano**: «In corso adesso» in sette modi e la scheda Avvisi in nove, con un pulsante per ripiegare o aprire tutti i repository; la scelta viene ricordata per ogni utente.
- **Notifiche per ogni utente**: in modalità team ogni utente sceglie in un pannello della pagina i canali (ntfy, Teams, e-mail), il livello minimo e i riepiloghi (`monitor/docs/NOTIFICATIONS_ita.md`).
- **Pagina delle impostazioni**: cambia percorsi, intervalli, quote e interruttori dal browser; solo un elenco fisso di chiavi validate, con copia di sicurezza prima di ogni salvataggio.
- **Grafici e storico**: minuti di calcolo, errori e successi con barre animate e uno storico giornaliero (rispetta il movimento ridotto).
- **Otto lingue** (en, es, de, fr, it, ja, zh, pt) con l'inglese come base; si cambia nelle impostazioni.
- **Uscite per dashboard**: `ci_red.json`, un endpoint Prometheus e una fonte JSON per Grafana, con una dashboard Grafana importabile.
- **Salvare e stampare il rapporto di una scheda**: TXT, PDF (scritto dal monitor stesso) e JSON dalla finestra Salva con nome del browser, e una pagina stampata pulita; lo stesso rapporto in ogni formato.
- **Icone dell'IA nella barra, loghi in Informazioni e avviso sulle action abbandonate**: le due icone dell'IA della barra mostrano il loro stato e con un clic aprono le impostazioni; Informazioni mostra il logo del monitor e, se lo consenti, quello della tua organizzazione; il linter può anche segnalare, solo a titolo informativo, quali action usate dai tuoi workflow sono archiviate o non più mantenute.
- **Strumenti a lotti**: pianificano e avviano molte build insieme; nulla parte senza `--go`.
- **Informazioni e Guida nella pagina**: il pulsante **i** mostra versione, edizione, collegamenti, file, stato di salute e un pulsante che copia le informazioni per l'assistenza; il pulsante **?** (o il tasto `?`) apre tutta la documentazione, con ricerca e nella tua lingua, senza Internet. La console ha `--about` e `--help-topics`, e un'applicazione interattiva da terminale a schede (`textual` opzionale).
- **Avviso di nuova versione**: un badge discreto quando esce una versione più recente; legge la pagina pubblica dei rilasci una volta al giorno, non installa mai nulla e si può spegnere (sempre spento in un'installazione isolata).
- **Quote per ogni account**: piano, minuti fatturabili (i repository pubblici non costano), quota dell'API letta dalle intestazioni di GitHub, concorrenza e job vicini al limite di 6 ore; le cifre stanno in un file modificabile.

## Cosa fa risparmiare

Usare il monitor invece di controllare Actions a mano fa risparmiare tempo. È una **stima, non una misura**: circa l'**85-95 % del tempo dedicato a sorvegliare la CI e a smistare i guasti** e, di conseguenza, circa il **15-25 % della produttività complessiva di un team** che lavora su molti repository. Presuppone che, senza il monitor, qualcuno apra la scheda Actions di ogni repository per vedere cosa è rosso e legga ogni log fallito per trovare la causa, che i guasti si verifichino ogni settimana e che sorveglianza e smistamento occupino da un sesto a un terzo del tempo di lavoro (le due cifre concordano solo con questa ipotesi). Con pochi repository, o se oggi nessuno controlla a mano, il risparmio è molto minore.

| Attività | Senza il monitor | Con il monitor | Risparmio stimato |
| --- | --- | --- | --- |
| Sorvegliare ogni workflow di ogni repository | Aprire di continuo la scheda Actions di ogni repository | Una pagina e un elenco di avvisi che si aggiornano da soli | 85-95 % |
| Decidere cosa è davvero rosso | Confrontare le esecuzioni a occhio (quelle annullate e saltate nascondono i guasti) | Una regola: l'ultima esecuzione terminata di ogni workflow sul ramo predefinito | 85-95 % |
| Trovare la causa di un'esecuzione fallita | Aprire l'esecuzione, il job e il log | L'avviso nomina già il workflow e il guasto, con le lezioni corrispondenti | 85-95 % |
| Accorgersi in tempo di un guasto | Accorgersene dopo, o quando qualcuno lo dice | Avvisi, notifiche e un riepilogo per gli strumenti di IA | 85-95 % |
| Non ripetere un errore noto, sicurezza, igiene e versioni pronte | Dipende dalla memoria e da revisioni manuali | Biblioteca di lezioni e sentinelle | Non quantificato |

Metodo, ipotesi e come misurarlo nel proprio uso: [`monitor/docs/PRODUCTIVITY_ita.md`](monitor/docs/PRODUCTIVITY_ita.md).

## In breve

| | |
|---|---|
| **Versione** | **2.1.8** · [tutte le release](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Richiede** | Python 3.11+ e la CLI di GitHub (`gh auth login`); nient'altro (la vista console usa il pacchetto facoltativo `rich`) |
| **Si apre** | su una pagina di `127.0.0.1` soltanto, in otto lingue |
| **Scrive su GitHub** | mai da solo: solo i comandi a lotti che avvii con un `--go` esplicito |
| **Esporta** | `ci_red.json`, metriche Prometheus e JSON per Grafana (tutto spento finché non lo accendi) |

<!-- glance:begin -->

**Misurato oggi** (v2.1.8)

| | |
|---|---|
| **Maturità** | functional |
| **Test** | 6196 metodi di test (`python -m unittest discover -s monitor/tests`) |
| **Impostazioni** | 1030 impostazioni, tutte con aiuto |
| **Lingue** | 8 (inglese, spagnolo, tedesco, francese, italiano, giapponese, cinese e portoghese) |
| **Provato nel CI su** | ubuntu, windows, Python 3.11, 3.13 |

## Stato del progetto

Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi: ciò che i test e il CI possono mostrare e ciò che è girato davvero, non ciò che è previsto.

🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 In parte fatto o non ancora verificato · 🔴 Non fatto o non funzionante

| Area | Stato | Cosa significa qui |
|---|---|---|
| Monitor e pagina | 🟢 | Gira ogni giorno su un account reale; i test girano nel CI su Ubuntu e Windows. |
| Sentinella (A1..A13) | 🟢 | Gira ogni giorno su un account reale; livelli e righe sono testati con fixture. |
| Notifiche | 🟡 | Provate contro server simulati; non tutti i canali sono stati provati con il servizio reale. |
| Connessione a uno strumento di IA e MCP | 🟡 | Feed, stato, flusso, hook e strumenti MCP sono testati con un server reale e un client simulato; nessun utente indipendente li ha ancora usati. |
| Edizione lite | 🟡 | Provata nel CI e condivide canali e impostazioni di quella completa; finora poco uso reale. |
| GitHub App, pannello centrale e modalità risparmio | 🟠 | Novità: provato con server e file simulati; non ha ancora girato a lungo con il servizio reale. |
| Punteggio di ogni account | 🟡 | Provato con serie sintetiche, dati di prova e server simulati; non è ancora stato osservato per settimane su account reali. |
| Immagine Docker e modalità servizio | 🟡 | L'immagine è costruita e provata nella CI (senza root, in sola lettura, con un accesso revocato); ancora poco tempo come servizio di lunga durata. |
| Modalità squadra e più account | 🟡 | Provata con processi reali e utenti simulati; un vero team non l'ha usata a lungo. |
| Archiviazione (file e SQLite) | 🟡 | Provata con i due archivi e le migrazioni tra loro; un database vecchio di mesi non ha ancora attraversato un aggiornamento. |
| Linux e macOS | 🟠 | Linux è provato solo nel CI; macOS per ora non è provato nel CI; l'uso quotidiano è su Windows. |

<!-- glance:end -->

## Architettura

<p align="center"><img src="images/architecture.svg" alt="Architettura" width="100%"></p>

## Inizia da qui: quale edizione?

| Se vuoi... | Avvio | Porta |
|---|---|---|
| vedere cosa gira e cosa fallisce, nient'altro (**inizia da qui**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| tutto l'account sorvegliato per te: avvisi, release, firma, prontezza, analitica | `MONITOR_GITHUB_ACTIONS` (con la [sentinella](monitor/docs/SENTINEL_ita.md)) | 8765 |

La finestra della console indica quale gira, nel titolo e nella prima riga. Ancora un dubbio? `python bin/actions_monitor.py --demo` apre la pagina con dati inventati e `--doctor` verifica la tua installazione. [I tuoi primi cinque minuti](monitor/docs/FIRST_STEPS_ita.md)

## Avvio rapido

1. Installa Python 3.11 o successivo e la [CLI di GitHub](https://cli.github.com/), poi esegui `gh auth login`.
2. Scarica questo repository (o lo zip dell'ultima release) e apri la cartella `monitor`.
3. Avvialo: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS doppio clic su `MONITOR_GITHUB_ACTIONS.command`, oppure `python bin/actions_monitor.py` ovunque.
4. Apri l'indirizzo stampato (`http://127.0.0.1:<porta>`). Al primo avvio crea `actions_monitor.json` dall'esempio.
5. Apri **Impostazioni** per indicare il tuo account GitHub, gli ecosistemi (gruppi di repository per prefisso del nome) e il resto.

> Aggiorni da una versione precedente alla 1.5.0? [`monitor/docs/MIGRATING_ita.md`](monitor/docs/MIGRATING_ita.md)

## L'edizione lite

Un secondo prodotto, più semplice, nello stesso pacchetto: la pagina di ciò che è in corso e di ciò che fallisce, senza la sentinella. Per chi vuole solo osservare i propri run.

|  | Completa | Lite |
|---|---|---|
| Avvio | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (gli stessi tre) |
| Porta | 8765 | 8766 |
| Schede | Adesso, Sentinella, Grafici, Repository, Cronologia, Impostazioni | Adesso, Grafici, Repository, Cronologia, Impostazioni brevi |
| Intestazione | tutte le tessere, prontezza, firma | in corso, in coda, fallimenti e successi di 24 h, minuti di calcolo, issue, rossi su main, repository, quota, connessione |
| Sentinella (avvisi, release, coda di firma, prontezza, linter) | sì | no: non viene nemmeno importata |
| Analisi, notifiche, webhook, IA, uscite Prometheus / Grafana | sì, spente finché non le attivi | no: quei percorsi rispondono 404 |
| Configurazione | `actions_monitor.json` | `actions_monitor_lite.json` (creato al primo avvio; la sentinella vi è spenta) |
| File di stato | `etag_cache.json`, `analytics_history.json`... | gli stessi nomi con il suffisso `_lite` |

[`monitor/docs/LITE_ita.md`](monitor/docs/LITE_ita.md)

## Schermate

### La pagina

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Adesso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_menu_groups_light.png"><img src="docs/screenshots/web_menu_groups_dark.png" alt="Il menu a gruppi: Osservare, Sentinelle, Team, Report e apprendimento" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_palette_light.png"><img src="docs/screenshots/web_palette_dark.png" alt="La palette Ctrl+K: una casella di ricerca per qualsiasi scheda, repository o azione" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_ci_light.png"><img src="docs/screenshots/web_sentinel_ci_dark.png" alt="Sentinella: CI" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_external_ci_light.png"><img src="docs/screenshots/web_external_ci_dark.png" alt="Fonti CI esterne: cosa dice ciascuna e perché una non si è potuta leggere" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_collab_light.png"><img src="docs/screenshots/web_sentinel_collab_dark.png" alt="Sentinella: collaborazione" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_delivery_light.png"><img src="docs/screenshots/web_sentinel_delivery_dark.png" alt="Sentinella di consegna: ciò che è costruito ma non ancora consegnato" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_supply_light.png"><img src="docs/screenshots/web_sentinel_supply_dark.png" alt="Sentinella della catena di fornitura: azioni non fissate e permessi ampi" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_security_light.png"><img src="docs/screenshots/web_sentinel_security_dark.png" alt="Sentinella della sicurezza con risultati" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_posture_light.png"><img src="docs/screenshots/web_posture_dark.png" alt="Rapporto di postura di repository e organizzazione rispetto a OWASP e CIS" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_compliance_light.png"><img src="docs/screenshots/web_compliance_dark.png" alt="Rapporto di conformità dell'installazione: ogni riga verificata o dichiarata" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_collaboration_light.png"><img src="docs/screenshots/web_collaboration_dark.png" alt="Viste di collaborazione: che cosa aspetta una persona e che cosa si potrebbe fare" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_roles_groups_light.png"><img src="docs/screenshots/web_roles_groups_dark.png" alt="Flotta per ruolo del workflow e per gruppo" width="92%"></picture></p>
<p align="center"><img src="docs/screenshots/web_screen_group.png" alt="Schermo a parete di un gruppo" width="92%"></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_proposals_light.png"><img src="docs/screenshots/web_proposals_dark.png" alt="Proposte dell'IA decise da una persona" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_assistant_chat_light.png"><img src="docs/screenshots/web_assistant_chat_dark.png" alt="Chat con l'IA, con strumenti di sola lettura e le fonti lette" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_extensions_light.png"><img src="docs/screenshots/web_extensions_dark.png" alt="Estensioni: che cosa gira, con quali permessi e che cosa è isolato" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_trend_light.png"><img src="docs/screenshots/web_sentinel_trend_dark.png" alt="Andamento giornaliero: una linea per ogni cifra" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_fleet_light.png"><img src="docs/screenshots/web_fleet_dark.png" alt="Flotta: tutti i repository a colpo d'occhio" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_reports_light.png"><img src="docs/screenshots/web_reports_dark.png" alt="Report" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_report_dialog_light.png"><img src="docs/screenshots/web_report_dialog_dark.png" alt="Salvare il rapporto di una scheda: TXT, PDF o JSON, con la finestra Salva con nome del browser" width="92%"></picture></p>
<p align="center"><img src="docs/screenshots/web_theme_midnight.png" alt="L'intera pagina in un altro tema (Midnight)" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_overview_1080p.png" alt="Schermo da parete: panoramica" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_now_1080p.png" alt="Schermo da parete: in questo momento" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_sentinels_1080p.png" alt="Schermo da parete: sentinelle" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_rotate.png" alt="Schermo da parete che ruota da solo tra i tre schermi" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_overview_midnight.png" alt="Schermo da parete con il logo dell'organizzazione e un tema proprio" width="92%"></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_alerts_light.png"><img src="docs/screenshots/web_alerts_dark.png" alt="Avvisi: tutte le sentinelle in un elenco, con silenziamenti locali" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Coda di firma (prima il più urgente)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analisi: durate, tempo in coda, passi e workflow instabili" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_saved_light.png"><img src="docs/screenshots/web_sentinel_saved_dark.png" alt="Tempo risparmiato: una stima in minuti a settimana, attività per attività, nell'analisi della sentinella CI" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Grafici" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_compare_light.png"><img src="docs/screenshots/web_compare_dark.png" alt="Confronta periodi: questo periodo rispetto al precedente" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repository" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_team_light.png"><img src="docs/screenshots/web_team_dark.png" alt="Team: la salute dei repository, in classifica" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Cronologia" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="Informazioni" width="92%"></picture></p>
<p align="center"><img src="docs/screenshots/web_updater.png" alt="L'aggiornatore: tutte le versioni pubblicate, per passare a una qualsiasi" width="92%"></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_updates_light.png"><img src="docs/screenshots/web_updates_dark.png" alt="Menu Sistema, Aggiornamenti: versione installata e disponibile" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Guida, con ricerca e offline" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Impostazioni · Di base: piano, quote e rilevamento" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="La modalità rete: la barra rossa persistente" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_notices_light.png"><img src="docs/screenshots/web_network_notices_dark.png" alt="La barra a piè di pagina: l'avviso più importante e la finestra con tutti" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Impostazioni · la modalità rete con il suo avviso e il nome del proxy HTTPS" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="Tutti gli account: una scheda per account" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="La pagina di un account, con il selettore" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="Vista Live: il ricevitore webhook e la modalità di lavoro" width="92%"></picture></p>

<details><summary><b>Impostazioni, sotto-scheda per sotto-scheda</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Impostazioni · Questo browser" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Impostazioni · Generale" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Impostazioni · Aggiornamento e limiti" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Impostazioni · Letture e cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_quota_light.png"><img src="docs/screenshots/web_settings_quota_dark.png" alt="Impostazioni · Quota" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Impostazioni · Sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Impostazioni · Controlli di superficie (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Impostazioni · Preparazione (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Impostazioni · Cartelle e file" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Impostazioni · Uscite per altri strumenti" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Impostazioni · IA esterna per la sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Impostazioni · Webhook in ingresso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Impostazioni · Notifiche" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Impostazioni · Analisi" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Impostazioni · Linter dei workflow" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Impostazioni · Vista da console" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="Impostazioni · Avanzate (opzionali)" width="92%"></picture></p>

</details>

<details><summary><b>Strumenti da console</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>L'edizione lite</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Adesso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Grafici" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · Cronologia" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Impostazioni" width="92%"></picture></p>

</details>

Ogni immagine segue il tema chiaro o scuro della tua pagina GitHub.

*Dati dimostrativi: i repository e i nomi nelle immagini sono inventati.*

## Impostazioni

Tutto vive in `actions_monitor.json` (creato da `monitor/assets/examples/actions_monitor.example.json`). La scheda **Impostazioni** lo modifica in modo sicuro; token e segreti non vengono mai mostrati né salvati. Ecosistemi, obiettivi di build e profili a lotti sono file separati che indichi tu (`ecosystems_file`, `targets_file`, `profiles_file`); sono inclusi modelli neutri `*.example.json`. Riferimento completo: [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md).

## Uscite per Grafana e dashboard

Tutto spento per impostazione predefinita, solo locale (`127.0.0.1`) e senza token aggiuntivi. Attivandolo nelle impostazioni ottieni `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, più una dashboard Grafana importabile in [`monitor/docs/grafana`](monitor/docs/grafana). Dettagli: [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md). Il formato di `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md).

## Sicurezza

- Ascolta solo su `127.0.0.1` e rifiuta le richieste il cui `Host` o `Origin` non è locale. Non associarlo mai a `0.0.0.0`: non ha login.
- Non memorizza alcun token: usa il tuo `gh` (a meno che tu non attivi il token opzionale del monitor in Impostazioni > Avanzate).
- Non scrive nulla su GitHub da solo. Solo `dispatch --go`, `dispatch --real` e `finalize --execute` scrivono, e solo quando li avvii tu.
- La modalità di rete e la modalità squadra sono spente per impostazione predefinita; quando sono accese, l'accesso, i ruoli, i blocchi e il registro di audit proteggono la pagina, e ogni richiesta è valutata per un solo account (`monitor/docs/DEPLOYMENT.md`, `monitor/docs/ACCOUNTS.md`).
- **Analisi**: p50 / p95 della durata, del tempo in coda e di ogni passo di ogni workflow, workflow instabili (falliti e poi passati sullo stesso commit) e workflow diventati più lenti; esportati in Prometheus e Grafana.
- **Risparmia quota e sopravvive a un'interruzione**: letture condizionali (un 304 non costa nulla) e una modalità ultima immagine con avviso offline che riprende da sola.
- **Webhook in ingresso e notifiche**: eventi firmati aggiornano un repository in tempo reale; messaggi facoltativi a Telegram, Discord, Slack, Matrix, MQTT o un indirizzo locale (mai una scrittura su GitHub).
- **Linter dei workflow e vista console**: `bin/lint_workflows.py` controlla `.github/workflows` prima del push; `bin/tui.py` (facoltativo, con `rich`) mostra una griglia in tempo reale nella console.
- **Assistente IA (spento per impostazione predefinita)**: riassunti, classificazione e spiegazioni con Ollama, un servizio compatibile OpenAI, Anthropic o `gh copilot`; solo comandi di un elenco chiuso, eseguiti solo dopo aver confermato ciascuno.
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
├── monitor/                            il programma
├── docs/                               architettura, schermate, roadmap
├── tools/                              immagini, guide e demo
├── deploy/                             immagine, compose, systemd
├── images/                             banner e immagini
├── .github/                            CI e moduli
├── CHANGELOG.md                        modifiche per versione
├── LICENSE NOTICE AUTHORS              licenze e autore
├── CONTRIBUTING.md SECURITY.md         contribuire, segnalare
├── SUPPORT.md CODE_OF_CONDUCT.md       supporto e condotta
└── monitor/
    ├── MONITOR_GITHUB_ACTIONS.*        i lanciatori (doppio clic)
    ├── MONITOR_LITE_GITHUB_ACTIONS.*   l'edizione lite
    ├── BATCH_GITHUB_ACTIONS.*          il menu delle build a lotti
    ├── src/                            il pacchetto importabile
    ├── assets/                         esempi, pagina, lingue
    ├── bin/                            i comandi brevi (read_report, monitor_cli ...)
    ├── tests/                          test offline
    ├── docs/                           guide, avvii rapidi, schemi, Grafana
    ├── skills/                         le due skill per le IA
    └── tools/                          script di rilascio e migrazione
```

## Documentazione

- [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md): tutte le impostazioni
- [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md): metriche, Grafana ed esportazioni
- [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md): il formato di ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_ita.md`](monitor/docs/CI_RED_BRIDGE_ita.md): portare ci_red.json in una dashboard
- [`monitor/docs/WEBHOOK_ita.md`](monitor/docs/WEBHOOK_ita.md): il webhook in ingresso
- [`monitor/docs/CHATOPS_ita.md`](monitor/docs/CHATOPS_ita.md): comandi chat in sola lettura per Slack e Discord
- [`monitor/docs/SOUNDS_ita.md`](monitor/docs/SOUNDS_ita.md): un suono per ogni tipo di evento
- [`monitor/docs/UPDATE_ita.md`](monitor/docs/UPDATE_ita.md): l'updater: passare a un'altra versione e migrare la configurazione
- [`monitor/docs/OPS_ita.md`](monitor/docs/OPS_ita.md): Gestire l'installazione: backup completo, ripristino, backup pianificato, pulizia su richiesta, il doctor e i suoi codici di uscita, appliance con systemd e Docker
- [`monitor/docs/LITE_ita.md`](monitor/docs/LITE_ita.md): L'edizione lite
- [`monitor/docs/COMPLETE_INDIVIDUAL_ita.md`](monitor/docs/COMPLETE_INDIVIDUAL_ita.md): Edizione completa per una persona
- [`monitor/docs/COMPLETE_SERVICE_ita.md`](monitor/docs/COMPLETE_SERVICE_ita.md): Edizione completa come servizio
- [`monitor/docs/COMPLETE_TEAM_ita.md`](monitor/docs/COMPLETE_TEAM_ita.md): Edizione completa per una squadra
- [`monitor/docs/API_ita.md`](monitor/docs/API_ita.md): L'API per i client
- [`monitor/docs/API_V1_ita.md`](monitor/docs/API_V1_ita.md): L'API di lettura v1, passo dopo passo
- [`monitor/docs/ASSISTANT_ita.md`](monitor/docs/ASSISTANT_ita.md): L'assistente: domande fisse in sola lettura alla tua IA
- [`monitor/docs/NOTIFICATIONS_ita.md`](monitor/docs/NOTIFICATIONS_ita.md): notifiche e contratto degli adattatori
- [`monitor/docs/AI_ita.md`](monitor/docs/AI_ita.md): l'assistente IA: provider, sicurezza e azioni
- [`monitor/docs/ANALYTICS_ita.md`](monitor/docs/ANALYTICS_ita.md): analisi, letture condizionali e connessione persa
- [`monitor/docs/CONSOLE_TOOLS_ita.md`](monitor/docs/CONSOLE_TOOLS_ita.md): il linter dei workflow e la vista console
- [`monitor/docs/DEPLOYMENT_ita.md`](monitor/docs/DEPLOYMENT_ita.md): eseguirlo come servizio (l'immagine ufficiale, Compose, systemd), dietro un proxy, quando GitHub revoca l'accesso, permessi
- [`monitor/docs/LAYOUT_ita.md`](monitor/docs/LAYOUT_ita.md): le cartelle del monitor, il passaggio dalla 1.8.1 e la mappa per le IA
- [`monitor/docs/QUICKSTART_it.txt`](monitor/docs/QUICKSTART_it.txt): primi passi, in otto lingue
- [`monitor/docs/FIRST_STEPS_ita.md`](monitor/docs/FIRST_STEPS_ita.md): i tuoi primi cinque minuti
- [`monitor/docs/SENTINEL_ita.md`](monitor/docs/SENTINEL_ita.md): la sentinella e i suoi controlli A1-A13
- [`monitor/docs/COLLAB_ita.md`](monitor/docs/COLLAB_ita.md): la sentinella Collab, la scheda Avvisi e i silenziamenti
- [`monitor/docs/SENTINEL_SECURITY_ita.md`](monitor/docs/SENTINEL_SECURITY_ita.md): La sentinella di sicurezza: Dependabot, analisi del codice, segreti, protezione dei branch, permessi dei workflow e CODEOWNERS, e ciò che non ha potuto controllare
- [`monitor/docs/SENTINEL_SUPPLY_ita.md`](monitor/docs/SENTINEL_SUPPLY_ita.md): La sentinella della catena di fornitura: action non fissate, branch mobili, permessi dei workflow ampi o assenti e pull_request_target con checkout, e ciò che non ha potuto leggere
- [`monitor/docs/SENTINEL_DELIVERY_ita.md`](monitor/docs/SENTINEL_DELIVERY_ita.md): La sentinella di consegna: voci non rilasciate, tag senza release, release senza note o file, versioni che non coincidono e fissaggi indietro rispetto a un contratto condiviso, e ciò che non ha potuto leggere
- [`monitor/docs/AUDIT_LOG_ita.md`](monitor/docs/AUDIT_LOG_ita.md): Il registro delle azioni: chi ha cambiato cosa, la catena di hash, chi lo legge e le impostazioni
- [`monitor/docs/HEALTH_ita.md`](monitor/docs/HEALTH_ita.md): La salute di un repository e del team: di cosa è fatta, la scheda Team, i link diretti e l'API
- [`monitor/docs/REPORT_SCHEDULE_ita.md`](monitor/docs/REPORT_SCHEDULE_ita.md): Rapporti pianificati: il punteggio, cosa è cambiato, i repository che richiedono una persona e gli avvisi aperti in HTML e Markdown, la pianificazione e i file
- [`monitor/docs/CLI_ita.md`](monitor/docs/CLI_ita.md): la riga di comando come client del monitor
- [`monitor/docs/CLI_OPERATOR_ita.md`](monitor/docs/CLI_OPERATOR_ita.md): la riga di comando per l'operatore: formati, watch, completions e codici di uscita
- [`monitor/docs/KIOSK_ita.md`](monitor/docs/KIOSK_ita.md): il monitor su una TV o una parete
- [`monitor/docs/ACCOUNTS_ita.md`](monitor/docs/ACCOUNTS_ita.md): più account, un processo ciascuno
- [`monitor/docs/QUOTAS_ita.md`](monitor/docs/QUOTAS_ita.md): quote e piani di GitHub
- [`monitor/docs/MODES_ita.md`](monitor/docs/MODES_ita.md): modalità di lavoro: normale, veloce e turbo
- [`monitor/docs/EXTERNAL_CI_ita.md`](monitor/docs/EXTERNAL_CI_ita.md): Fonti CI esterne, sola lettura: Buildbot, GitLab CI, Jenkins, Azure Pipelines
- [`monitor/docs/PLUGINS_ita.md`](monitor/docs/PLUGINS_ita.md): Plugin (spenti per impostazione predefinita), pacchetti, isolamento e token da un archivio di segreti
- [`monitor/docs/POSTURE_ita.md`](monitor/docs/POSTURE_ita.md): Postura di repository e organizzazione, sola lettura
- [`monitor/docs/COMPLIANCE_ita.md`](monitor/docs/COMPLIANCE_ita.md): Conformità: sola lettura rigorosa, criterio di rete, rapporto, conservazione e blocco legale, registro delle azioni firmato ed esportato
- [`monitor/docs/ECOSYSTEM_TOOLS_ita.md`](monitor/docs/ECOSYSTEM_TOOLS_ita.md): Gli strumenti attorno al monitor e il loro livello di supporto
- [`monitor/docs/EDITIONS_ita.md`](monitor/docs/EDITIONS_ita.md): Completa e Lite: cosa c'è in ciascuna edizione
- [`monitor/docs/COLLABORATION_ita.md`](monitor/docs/COLLABORATION_ita.md): Viste di collaborazione e azioni facoltative su GitHub
- [`monitor/docs/FLEET_APIS_ita.md`](monitor/docs/FLEET_APIS_ita.md): Flotta per ruolo e gruppo, API CCTray e di sicurezza, impronta dei rapporti, sito dimostrativo
- [`monitor/docs/AI_CONNECTION_ita.md`](monitor/docs/AI_CONNECTION_ita.md): Collegare uno strumento di IA: tutto ciò che dice il monitor, come segnali, nel riepilogo, nell'endpoint, negli strumenti MCP e nell'hook
- [`monitor/docs/AI_SETUP_PROMPT_ita.md`](monitor/docs/AI_SETUP_PROMPT_ita.md): Configurare il monitor con un'IA: un prompt da incollare nel tuo assistente IA che lo installa, ti chiede cosa vuoi e scrive la configurazione
- [`monitor/docs/QUOTA_ita.md`](monitor/docs/QUOTA_ita.md): Più quota, meno spesa: modalità risparmio, il pannello centrale, una GitHub App e come condividere la quota
- [`monitor/docs/EXTRAS_ita.md`](monitor/docs/EXTRAS_ita.md): Extra facoltativi: il registro del passo fallito e un token di sola lettura della GitHub App
- [`monitor/docs/SCORE_ita.md`](monitor/docs/SCORE_ita.md): Il punteggio di un account: parti, stati, API, la pastiglia dell'intestazione, l'avviso e le impostazioni
- [`monitor/docs/COMPARE_ita.md`](monitor/docs/COMPARE_ita.md): Confrontare i periodi: questo periodo rispetto al precedente, le cifre, il filtro del calendario, gli stati senza numero, l'API, il comando e le impostazioni
- [`monitor/docs/STORAGE_ita.md`](monitor/docs/STORAGE_ita.md): Archiviazione e conservazione: file o SQLite, backup, migrazione e cosa si conserva
- [`monitor/docs/ADVANCED_ita.md`](monitor/docs/ADVANCED_ita.md): Funzioni avanzate (tutte spente di default)
- [`monitor/docs/AI_ALERTS_ita.md`](monitor/docs/AI_ALERTS_ita.md): Avvisi per le IA: il flusso, il riepilogo, l'hook e lo stream
- [`monitor/docs/AUDIT_PACKAGE_ita.md`](monitor/docs/AUDIT_PACKAGE_ita.md): Pacchetto per il revisore
- [`monitor/docs/LARGE_ACCOUNTS_ita.md`](monitor/docs/LARGE_ACCOUNTS_ita.md): Account grandi: centinaia di repository
- [`monitor/docs/ORGANIZATIONS_ita.md`](monitor/docs/ORGANIZATIONS_ita.md): Organizzazioni e account grandi
- [`monitor/docs/PRODUCTIVITY_ita.md`](monitor/docs/PRODUCTIVITY_ita.md): cosa fa risparmiare il monitor: una stima, le sue ipotesi e come misurarla

## Contribuire

Leggi [CONTRIBUTING.md](CONTRIBUTING.md). Segnala bug e idee con i moduli delle issue; i problemi di sicurezza come descritto in [SECURITY.md](SECURITY.md).

## Autore

Scritto da **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licenza

Il codice è GPL-3.0-or-later; la documentazione è CC BY-SA 4.0. Vedi [LICENSE](LICENSE) e [NOTICE](NOTICE).
