<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Schermi, dimensioni e orientamento

La pagina si adatta alla dimensione della finestra, dal telefono al 4K, in verticale o in orizzontale, e un solo monitor può servire più schermi, ciascuno con le schede che scegli. Niente viene interrogato due volte: tutti gli schermi leggono lo stesso stato.


Per una TV o una parete con testo più grande, un alto contrasto o una rotazione tra poche schede, vedi [KIOSK_ita.md](KIOSK_ita.md).
## Indirizzi

- `/` - l'intera pagina.
- `/screen/1`, `/screen/2`, `/screen/3` - le schede impostate per quello schermo (`ui.screen1_tabs` ...). Apri ciascuna in una finestra del proprio monitor o TV.
- `?orient=portrait` o `?orient=landscape` forza la disposizione di una finestra; `?tabs=now,charts` e `?rotate=30` impostano le schede e i secondi tra loro per una finestra.

## Impostazioni

| Impostazione | Cosa fa |
|---|---|
| `ui.orientation` | auto segue la finestra; portrait impila i pannelli in una colonna; landscape mantiene l'affiancamento. |
| `ui.rotate_seconds` | 0 = spento. Secondi tra le schede di uno schermo che ne ha più di una. |
| `ui.screen1_tabs` | Schede di /screen/1, separate da virgole: now, al, charts, sent, sci, scol, ssec, team, fleet, repos, rep, trep, les, hist, cfg. Vuoto = tutte. |
| `ui.screen1_orientation` | auto, portrait o landscape solo per /screen/1. |
| `ui.screen2_tabs` | Schede di /screen/2. |
| `ui.screen2_orientation` | Orientamento di /screen/2. |
| `ui.screen3_tabs` | Schede di /screen/3. |
| `ui.screen3_orientation` | Orientamento di /screen/3. |
| `ui.now_sort` | Ordine di In corso adesso per chi non ha scelto: ecosystem, severity, age, newest, repo, event o state. |
| `ui.alerts_sort` | Ordine della scheda Avvisi per chi non ha scelto: server, severity, streak, class, age, newest, repo, origin o state. |

## Ordine degli elenchi

La sezione **In corso adesso** della prima scheda è ordinata per ecosistema, con un titolo per ciascuno. L'elenco sopra la sezione lo cambia: ecosistema, gravità (prima le esecuzioni bloccate, poi quelle con un job fallito, poi in corso, poi in coda), anzianità (la più lunga per prima), più recente per prima, repository, innesco (push, pull_request, schedule...) e stato (in corso prima di in coda). La scelta viene ricordata per ogni persona: in modalità team la conserva il server con l'utente (`GET` e `POST /api/auth/me/view`, quindi lo segue in un altro browser), altrimenti questo browser. Finché nessuno sceglie, l'ordine è `ui.now_sort` del file di configurazione (ecosistema se manca o è errato). I pulsanti **Espandi tutto** e **Comprimi tutto** accanto all'elenco espandono o comprimono in un colpo tutti i repository della sezione, con qualsiasi ordine; la scelta viene ricordata per ogni persona nello stesso posto e sopravvive a un aggiornamento (un repository aperto o chiuso a mano dopo conserva la tua scelta).

L'elenco della scheda **Avvisi** mantiene l'ordine inviato dal monitor finché qualcuno non ne sceglie un altro con l'elenco sopra: gravità (critico, errore, avviso, info), prima la serie di errori consecutivi più lunga, classe (un avviso di errore o critico è reale e va prima di quelli da tenere d'occhio), prima i più vecchi, prima i più recenti, repository, origine (la sentinella che lo ha sollevato) e stato (aperti prima di silenziati). Viene ricordato allo stesso modo; finché nessuno sceglie, vale `ui.alerts_sort` del file di configurazione (`server` se manca o è errato).

## Dimensioni provate

Un test del browser apre la pagina in ciascuna di queste dimensioni, percorre tutte le schede e fallisce se c'è uno scorrimento laterale o un testo che esce dal suo riquadro. Le finestre da 2400 px in su ricevono un carattere più grande (da 3200 px, ancora più grande) invece di una disposizione allungata; una finestra più alta che larga impila i pannelli.

| Dimensione | Tipo |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Ricetta per una postazione con due o tre schermi

1. Sul computer che esegue il monitor, imposta `ui.screen1_tabs` su `now,al`, `ui.screen2_tabs` su `charts,repos` e, per un monitor ruotato, `ui.screen2_orientation` su `portrait`.
2. Apri `http://questo-computer:8765/screen/1` in una finestra del primo monitor e `/screen/2` sul secondo; F11 per lo schermo intero. Da un altro computer usa la modalità rete con il suo token di accesso.
3. Per uno schermo a parete che nessuno tocca, dagli più schede e imposta `ui.rotate_seconds` su 20-30.

## Schermi da parete: panoramica, in questo momento e sentinelle

Tre pagine per un monitor o una TV che nessuno tocca. Non hanno menu laterale né navigazione, mostrano tutto in una sola vista con testo grande, animano ciò che è vivo e fanno lampeggiare dolcemente i guasti. Fanno solo lettura: nessun pulsante cambia nulla e non chiamano mai GitHub (mostrano ciò che il monitor ha già).

| Indirizzo | Cosa mostra |
|---|---|
| `/screen/overview` | Anello e lettera del punteggio; la flotta (verdi, rossi, bloccati, in attesa); le ultime 24 ore e 7 giorni in grafici ad area; una mappa di calore dei repository per ora; ciò che è rosso da più tempo; runner e minuti; gli ultimi eventi; la quota di GitHub come indicatore. La scheda della flotta mostra anche la mappa per gruppi: una barra per ogni gruppo della vista flotta (lo stesso raggruppamento, `fleet.group_by`) con i suoi repository in rosso, che richiedono attenzione, in ordine o senza dati; solo il nome del gruppo e i numeri. |
| `/screen/now` | Ciò che accade in questo minuto: esecuzioni in corso con avanzamento e durata, la coda, esecuzioni in attesa di approvazione, errori recenti, merge e release, release in arrivo e una linea in diretta delle ultime due ore. |
| `/screen/sentinels` | Una scheda per ogni sentinella (da A1 ad A12) con il suo livello, i rilievi aperti, se le sue fonti sono leggibili, l'ultima scansione e un anello che segue la scansione; un radar animato che segna ciò che non va e gli avvisi per gravità. |

### Parametri dell'indirizzo

Un indirizzo per ogni monitor. Un parametro può rendere una finestra più tranquilla o più piccola di quanto consentano le impostazioni, mai più rumorosa.

| Parametro | Effetto |
|---|---|
| `?monitor=1` a `9` | Il numero mostrato accanto al titolo. |
| `?theme=light` (o `dark`, `auto`, `contrast`, o il nome di uno dei sedici temi) | Colori dell'intera finestra, sopra ciò che dicono le impostazioni. `contrast` è bianco su nero, per uno schermo visto da lontano. |
| `?density=compact`, `normal` o `large` | Dimensione del testo. `?scale=1.5` ingrandisce tutto (da 0,5 a 3). |
| `?refresh=10` | Secondi tra gli aggiornamenti (da 5 a 120). |
| `?lang=de` | Lingua (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | La finestra passa da sola per panoramica, in questo momento e sentinelle ogni 30 secondi (minimo 5; 0 = resta su uno schermo). Con `screens.mode` = rotate ruota già; questo cambia il ritmo di una finestra. |
| `?jump=off` | Solo con `screens.mode` = rotate: la finestra ruota ma non salta mai a un nuovo rosso. |
| `?blink=off` | I guasti mantengono un alone fisso invece di lampeggiare. Non può attivare ciò che `screens.blink` tiene spento. |
| `?repo=WORD,WORD` | Solo i repository il cui nome contiene una delle parole (lettere, cifre e `. _ - /`, fino a otto parole). `/screen/overview` e `/screen/now` tengono solo i repository il cui nome è mostrato dalla schermata (un nome nascosto non corrisponde mai), le cifre seguono le righe tenute e il punteggio e la mappa dei gruppi, che riguardano l'intera flotta, non vengono mostrati; `/screen/sentinels` non è filtrata. |
| `?sound=on` | Un breve segnale acustico per un nuovo guasto, solo se `screens.sound` lo consente. Disattivato per impostazione predefinita. |

### Lingua degli schermi

La lingua di uno schermo si decide in quest'ordine: `?lang=xx` nell'indirizzo; poi la lingua scelta nella pagina principale dello stesso browser (lì viene salvata, e uno schermo aperto in quel browser la legge, così lo schermo segue la pagina senza alcun parametro); poi la lingua del monitor (`MONITOR_LANG`, o quella configurata). Uno schermo la cui lingua salvata differisce da quella in cui è stato servito si ricarica una volta, prima di disegnare, con `?lang=` aggiunto e gli altri parametri (tra cui `?rotate=`) mantenuti. Le otto lingue (en, es, de, fr, it, ja, zh, pt) sono le stesse della pagina: titoli, etichette, stati, gravità, unità e tempi relativi («5 min fa») vengono dal catalogo, e ora, data e numeri si scrivono con le impostazioni regionali della lingua (en-GB, es-ES, de-DE, fr-FR, it-IT, ja-JP, zh-CN, pt-PT). Il collegamento «Apri schermo» delle Impostazioni porta già `?lang=` con la lingua della pagina. Un computer che non sceglie una lingua resta in inglese: la lingua del browser non decide.

### Impostazioni degli schermi da parete

| Impostazione | Cosa fa |
|---|---|
| `screens.enabled` | Attiva le tre pagine. Disattivato: `/screen/overview`, `/screen/now`, `/screen/sentinels` e `/api/screens/data` rispondono 404 (da `/screen/1` a `/screen/3` sono la pagina stessa e non ne dipendono). Anche l'edizione lite serve gli schermi a parete, con lo schermo delle sentinelle vuoto. Disattivato per impostazione predefinita. |
| `screens.default_theme` | inherit (predefinito: il tema scelto per tutto il prodotto, vedi sotto), auto, light, dark, uno dei sedici temi o contrast. |
| `screens.default_density` | compact, normal (predefinito) o large. |
| `screens.refresh_seconds` | Secondi tra gli aggiornamenti di una finestra (10 per impostazione predefinita). Le pagine leggono dal monitor, mai da GitHub, quindi un tempo breve non consuma quota. |
| `screens.rotate_seconds` | Solo con `screens.mode` = three. 0 (predefinito) = nessuna rotazione; da 5 in su, una finestra passa per le tre pagine. |
| `screens.blink` | I guasti lampeggiano dolcemente (attivo per impostazione predefinita). |
| `screens.blink_calm_minutes` | Minuti dopo i quali un guasto di cui nessuno si occupa mantiene un alone fisso invece di lampeggiare (30 per impostazione predefinita; 0 = lampeggia finché non è risolto). |
| `screens.sound` | Un segnale acustico per un nuovo guasto (disattivato per impostazione predefinita). |
| `screens.burn_in_protection` | Sposta tutto di qualche pixel ogni minuto (attivo per impostazione predefinita). |
| `screens.night_dim` | Attenua gli schermi tra `screens.night_dim_from_hour` (22) e `screens.night_dim_to_hour` (7); disattivato per impostazione predefinita. |
| `screens.show_repo_names` | all, public (predefinito: i repository privati compaiono come private-1, private-2...) o none (ogni nome è nascosto). Usare public o none per uno schermo che altre persone possono vedere. Con un elenco di repository scritto a mano in `repos`, la visibilità si legge con un elenco dell'account ogni `discover_refresh_seconds`; un repository la cui visibilità non si è potuta leggere conta come privato. I numeri (private-1...) vanno solo ai repository nascosti, nell'ordine di un HMAC del nome con una chiave dell'installazione conservata in un file privato della cartella dei dati: non dicono nulla su dove cade un repository tra gli altri. |
| `screens.theme_overview`, `screens.theme_now`, `screens.theme_sentinels` | Il tema di uno schermo: inherit (predefinito: quello di `screens.default_theme`) o uno dei temi sopra. |
| `screens.mode` | three (predefinito: le tre pagine separate, una per finestra) o rotate (una sola pagina che passa per le tre e salta a un nuovo rosso). |
| `screens.rotate_every_seconds` | In modalità rotate, secondi su ogni schermo (20 per impostazione predefinita; da 5 a 300). |
| `screens.alert_hold_seconds` | In modalità rotate, secondi in cui un nuovo rosso tiene la finestra sul suo schermo (30 per impostazione predefinita; da 5 a 600), o finché il rosso sparisce. |
| `screens.logo_overview`, `screens.logo_now`, `screens.logo_sentinels` | Su quali schermi compare il logo (di default solo la panoramica). |
| `screens.logo_corner` | top-right (predefinito), top-left, bottom-right o bottom-left. |
| `screens.logo_max_width`, `screens.logo_max_height` | Dimensione massima del logo in pixel a 1920 x 1080 (160 x 64 per impostazione predefinita; cresce con lo schermo). |
| `screens.group_map` | Attivo per impostazione predefinita. Mostra la mappa della flotta per gruppi nella schermata generale (il raggruppamento della vista flotta). Disattivato: solo i quattro riquadri. |
| `screens.menu` | Attivo per impostazione predefinita. Il pulsante Schermi nella barra superiore. Disattivato: il pulsante scompare; gli schermi continuano a funzionare ai loro indirizzi. |
| `screens.menu_target` | new (predefinito): uno schermo si apre in una nuova finestra o scheda; same: nella scheda corrente. |
| `screens.menu_max_windows` | Massimo di finestre che un insieme multischermo apre in una volta (4 per impostazione predefinita; da 1 a 9). |
| `screens.menu_rotate_seconds` | Secondi per schermo nei preset a rotazione del menu (20 per impostazione predefinita; da 5 a 300). |
| `screens.menu_tv_scale` | Il `?scale=` del preset TV (1,5 per impostazione predefinita; da 0,5 a 3). |

### Tema degli schermi

Tutto ciò che mostra il monitor porta il tema scelto nelle Impostazioni (`ui.theme`: auto, light, dark o uno dei sedici temi): la pagina, gli schermi da parete e la pagina di accesso. Scegliere un tema nel selettore della scheda Questo browser lo salva anche come `ui.theme`, così un browser che non ha mai scelto prende quello del monitor. I rapporti HTML scritti su disco seguono l'impostazione chiara o scura del computer che li apre.

Gli schermi da parete lo ereditano: `screens.default_theme` è `inherit` per impostazione predefinita. Impostalo su un altro tema per fissare lo stesso su tutti gli schermi, e `screens.theme_overview`, `screens.theme_now` o `screens.theme_sentinels` per dare a uno schermo il suo. L'indirizzo può ancora fissare una finestra con `?theme=`. Nessuno schermo scrive un colore suo: tutti usano le palette del tema, quindi un tema aggiunto alla pagina compare anche sugli schermi.

### Modalità degli schermi: tre o rotazione

`screens.mode` = three (predefinito) mantiene le tre pagine separate, una per finestra. `screens.mode` = rotate fa di ogni finestra un solo schermo che passa per panoramica, in questo momento e sentinelle ogni `screens.rotate_every_seconds` secondi (20 per impostazione predefinita; da 5 a 300).

Un guasto in rosso fa saltare la finestra allo schermo che lo mostra: **In questo momento** per un workflow fallito, **Sentinelle** per un pannello di sentinella che diventa rosso. La finestra vi resta `screens.alert_hold_seconds` secondi (30 per impostazione predefinita; da 5 a 600) o finché quel rosso sparisce, quale delle due cose accada prima, e poi continua a ruotare. Un rosso già mostrato non fa saltare di nuovo la finestra finché non cambia o ritorna. Ciò che è rosso all'apertura della finestra è solo il punto di partenza e non la fa saltare. Se arriva un secondo rosso mentre la finestra tiene il primo, aspetta il suo turno. Per saperlo, una finestra legge gli altri due schermi in background con la stessa chiamata di sola lettura (mai GitHub). `?rotate=0` tiene una finestra sul suo schermo e `?jump=off` mantiene la rotazione senza i salti. Ogni schermo applica il suo tema e il suo logo quando compare.

### Logo dell'organizzazione

La scheda Questo browser delle Impostazioni ha un blocco per caricare il logo della tua organizzazione: PNG, JPEG, WebP o SVG, al massimo 1 MB. Il monitor controlla il tipo reale dai primi byte del file (non contano il nome né l'etichetta che lo accompagna), rifiuta un SVG con script, gestori di eventi, collegamenti ad altri file o indirizzi o un tipo di documento, e conserva l'immagine nella cartella `data/` di questo computer come `org_logo` con la sua estensione, mai nella configurazione. Esiste un solo logo: caricarne un altro lo sostituisce. Il registro delle azioni annota il caricamento e la rimozione, mai il file.

`screens.logo_overview`, `screens.logo_now` e `screens.logo_sentinels` scelgono su quali schermi da parete compare (di default solo la panoramica), `screens.logo_corner` l'angolo (in alto a destra per impostazione predefinita) e `screens.logo_max_width` e `screens.logo_max_height` la dimensione massima in pixel a 1920 x 1080 (160 x 64 per impostazione predefinita; il logo cresce con lo schermo). L'immagine si adatta a quella dimensione senza deformarsi e ha un posto suo nell'intestazione o nel piè di pagina, così non copre mai il contenuto. Lo sfondo resta trasparente: un logo con sfondo trasparente si vede bene nei temi chiari e in quelli scuri.

### Cosa mostrano e cosa nascondono

I dati arrivano da `/api/screens/data?screen=overview` (oppure `now`, `sentinels`): un elenco chiuso di campi costruito con l'ultimo ciclo, l'istantanea delle sentinelle, gli avvisi e il punteggio. Non contiene mai un collegamento, un titolo di commit, il nome di un job, il nome di una persona né un percorso di questo computer, e anche i nomi dei workflow dei repository nascosti sono nascosti. In modalità di rete le pagine richiedono lo stesso token di accesso del resto del monitor e la risposta è di sola lettura.

### Come si comportano

- I guasti lampeggiano meno di due volte al secondo (mai in modo stroboscopico); un nuovo guasto produce un solo lampo; un guasto di cui nessuno si occupa per `screens.blink_calm_minutes` minuti mantiene un alone fisso. Con l'impostazione del sistema per ridurre il movimento, oppure con `?blink=off`, nulla lampeggia né si muove. Un guasto non è mai indicato solo dal colore: porta un simbolo e una parola.
- Quando il monitor non risponde, la pagina lo dice, si attenua e riprova dopo 5, 10, 20... secondi (fino a 60).
- Uno schermo sempre acceso è protetto dal burn-in: tutto si sposta di qualche pixel ogni minuto e la pagina può attenuarsi di notte.

### Montare più monitor

1. Scegliere un indirizzo per ogni monitor, per esempio `/screen/overview?monitor=1`, `/screen/now?monitor=2` e `/screen/sentinels?monitor=3`; oppure aprire una sola finestra con `?rotate=20`.
2. Aprire ciascuna in Chrome o Edge in modalità chiosco: `msedge --kiosk "http://questo-computer:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` oppure `chrome --kiosk "http://questo-computer:8765/screen/now?monitor=2"`; con `--app=INDIRIZZO` al posto di `--kiosk` la finestra non ha barre. Senza modalità chiosco, il pulsante discreto a piè di pagina chiede lo schermo intero.
3. Da un altro computer usare la modalità di rete: basta il token di accesso di un visualizzatore, perché queste pagine non scrivono mai.

## Quale scheda è su quale schermo da parete

Ogni scheda della pagina ha una decisione, scritta nel codice (`TAB_DECISIONS` di `screens.py`) e verificata da un test: viene mostrata su uno degli schermi da parete oppure dice perché no. Una scheda mostrata ha i suoi dati nella risposta di `/api/screens/data` (la panoramica porta Avvisi, Grafici e Flotta; In questo momento porta Adesso; Sentinelle porta le carte delle schede delle sentinelle). Una scheda non mostrata indica il suo motivo:

- `people`: nomina persone, e uno schermo da parete non mostra mai un nome utente.
- `controls`: è fatta di pulsanti e campi che cambiano qualcosa, e uno schermo da parete non ne ha.
- `reading`: è fatta per essere letta, confrontata o salvata, non per essere vista da lontano.
- `text`: è fatta di titoli, cause e messaggi, che uno schermo da parete non mostra mai.

| Scheda | Nome | Schermo da parete | Motivo |
|---|---|---|---|
| `now` | Adesso | `/screen/now` | - |
| `al` | Avvisi | `/screen/overview` | - |
| `charts` | Grafici | `/screen/overview` | - |
| `sent` | Riepilogo | `/screen/sentinels` | - |
| `sci` | Sentinella CI | `/screen/sentinels` | - |
| `scol` | Sentinella collab | `/screen/sentinels` | - |
| `ssec` | Sentinella sicurezza | `/screen/sentinels` | - |
| `sdel` | Sentinella di consegna | `/screen/sentinels` | - |
| `ssup` | Sentinella della catena di fornitura | `/screen/sentinels` | - |
| `strend` | Andamento giornaliero | - | `reading` |
| `syvt` | Ieri vs oggi | - | `reading` |
| `team` | Salute del team | - | `people` |
| `fleet` | Flotta | `/screen/overview` | - |
| `repos` | Repository | - | `controls` |
| `rep` | Rapporti | - | `reading` |
| `trep` | Report pianificati | - | `reading` |
| `les` | Lezioni | - | `text` |
| `hist` | Cronologia | - | `text` |
| `upd` | Aggiornamenti | - | `controls` |
| `cfg` | Impostazioni | - | `controls` |

## Menu Schermi

Il pulsante **Schermi** nella barra superiore (l'icona di due monitor) apre un menu con ogni tipo di schermo del monitor, così nessuno deve ricordare gli indirizzi. Fa solo da navigazione: apre indirizzi, non scrive nulla e non legge nulla da GitHub. È attivo per impostazione predefinita e `screens.menu` lo disattiva.

| Schermo | Indirizzo | Che cos'è |
|---|---|---|
| Dashboard | `/` | L'intera pagina, per una persona alla scrivania. `?repo=` filtra i repository. |
| Chiosco | `/?chrome=0&view=now` | Una vista senza intestazione, schede né filtri, per un monitor che nessuno tocca. La vista è un parametro. |
| Vista del team | `/?chrome=0&view=team` | La vista del team come chiosco (edizione completa). |
| Schermi di schede da 1 a 3 | `/screen/1`, `/screen/2`, `/screen/3` | Le schede impostate per ogni monitor di una scrivania; `?tabs=`, `?orient=` e `?rotate=` le cambiano per una finestra. |
| Schermi a parete | `/screen/overview`, `/screen/now`, `/screen/sentinels` | I tre schermi a parete descritti sopra. |
| Parete a rotazione | `/screen/overview?rotate=20` | Una finestra che ruota tra i tre e salta a un nuovo rosso. |
| TV | `/screen/overview?theme=contrast&density=large&scale=1.5&rotate=20` | La parete a rotazione per uno schermo visto da lontano. |
| Più monitor | un indirizzo per finestra | Un insieme di finestre, una per monitor (vedi sotto). |

Ogni scheda mostra i parametri che quell'indirizzo accetta (tema, densità, aggiornamento, scala, lingua, rotazione, filtro dei repository...), ciascuno con il proprio testo di aiuto, e l'indirizzo risultante. **Apri** lo apre in una nuova finestra o scheda, o nella scheda corrente, come dice `screens.menu_target`; **Copia indirizzo** mette l'indirizzo completo negli appunti per aprirlo su un altro computer (mai con un token: in modalità rete quel computer accede come al solito). Gli schermi a parete rispondono 404 finché `screens.enabled` è disattivato, quindi la loro scheda lo dice invece di aprire una pagina vuota; la vista del team non c'è nell'edizione lite.

### Più monitor

Scegli quante finestre (al massimo `screens.menu_max_windows`), la disposizione (in fila, in colonna o in griglia) e cosa mostra ogni finestra (i tre schermi a parete a turno, pareti che ruotano da sole o gli schermi di schede). **Apri tutte le finestre** apre una finestra per monitor. In un browser con l'API di gestione delle finestre (Chrome ed Edge chiedono il permesso *gestione finestre*) ogni finestra è collocata sul suo monitor, ordinati come dice la disposizione; con più finestre che monitor condividono un monitor a riquadri. Senza di essa le finestre si aprono dove le mette il browser e la scheda elenca un comando chiosco per finestra (`msedge --kiosk INDIRIZZO --window-position=X,Y`) per avviarle a mano. Il browser deve consentire i pop-up per l'indirizzo del monitor.

Lo stesso catalogo è letto dagli strumenti: `GET /api/screens/menu`, `monitor_cli.py screens [list|urls]` e lo strumento MCP `screens_menu`. Tutti e tre sono di sola lettura.

## Immagini

La scheda Adesso in quattro dimensioni, con dati inventati (4K, un monitor 21:9, un monitor ruotato, un telefono):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![ruotato 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![telefono 390x844](../../docs/screenshots/web_size_phone_light.png)

I tre schermi da parete in 4K e su un monitor ruotato, con dati inventati:

![Panoramica 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![Panoramica 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![In questo momento 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![In questo momento 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Sentinelle 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Sentinelle 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)

Gli schermi da parete in altri temi, con il logo di un'organizzazione e la finestra che ruota da sola, con dati inventati:

![Panoramica, tema chiaro](../../docs/screenshots/web_screen_overview_light.png)

![Panoramica con il logo e il tema Midnight](../../docs/screenshots/web_screen_overview_midnight.png)

![Sentinelle, contrasto elevato](../../docs/screenshots/web_screen_sentinels_contrast.png)

![La finestra che ruota tra i tre schermi](../../docs/screenshots/web_screen_rotate.png)
