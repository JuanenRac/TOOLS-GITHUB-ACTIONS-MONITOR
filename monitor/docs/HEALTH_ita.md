<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](HEALTH.md) | [🇪🇸 Español](HEALTH_spa.md) | [🇫🇷 Français](HEALTH_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](HEALTH_deu.md) | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | [🇵🇹 Português](HEALTH_por.md)

# La salute di un repository e del team

Solo Complete. Due viste di sola lettura, costruite con ciò che il monitor già possiede (esecuzioni, workflow rossi e bloccati, avvisi aperti di ogni sentinella e preparazione delle versioni). Non chiamano mai GitHub.

## Di cosa è fatta la salute di un repository

| Parte | Cosa dice |
|---|---|
| CI | successi e fallimenti delle ultime 24 ore, i workflow rossi adesso, le esecuzioni bloccate |
| Avvisi | tutti gli avvisi aperti delle sentinelle CI, Collab e Sicurezza, per sentinella e per livello |
| Versione | la riga della preparazione delle versioni, se il repository ce l'ha |
| Attività | quando è iniziata l'ultima esecuzione e quante ce ne sono state in 7 giorni |
| Chi l'ha guardato | il ciclo di vita di ogni sentinella: sana, degradata, in pausa, in errore o spenta |

Lo stato è **cattivo** (un workflow rosso, o un avviso di livello critico o errore), **avvertimento** (un avviso di avvertimento o un'esecuzione bloccata), **buono** o **non visto** (niente su cui giudicare). Un repository che nessuna sentinella ha guardato, o che una sentinella non ha potuto leggere, non è mai mostrato come buono: dice «non visto del tutto da» ed elenca chi. Il rischio è il numero con cui si ordina la classifica: ogni workflow rosso (30), esecuzione bloccata (10), avviso critico (25), di errore (10), di avvertimento (3) e informativo (1) aggiunge punti, uguali per tutti i repository. Quando tutte le sentinelle sono in errore, in pausa o degradate (o tutte spente e nulla è girato da una settimana), un repository tranquillo viene mostrato come non visto, mai come OK, e la sua riga nella classifica porta un asterisco ed elenca le sentinelle che non hanno potuto leggerlo (`not_fully_seen`; anche i totali le contano).

## Dove vederla

- La scheda **Team**: la classifica (prima i repository che richiedono una persona), i totali, i numeri per ecosistema e per sentinella, e tre filtri: ecosistema, gravità minima e una parte del nome. Clicca un repository per il dettaglio.
- Link diretti per schermi a parete: `?view=team&chrome=0`, `?view=repos&chrome=0` e `?view=repo&repo=owner/name&chrome=0`.
- L'API: `GET /api/team/health?ecosystem=&severity=&q=&label=` e `GET /api/repos/<owner>/<repo>/health`. Entrambe richiedono il permesso di vedere l'account; le risposte portano `schema: 1`. Un repository sconosciuto risponde 404 con `code: repo_unknown`.
- L'edizione Lite mantiene la sua vista semplice delle esecuzioni e non ha né la scheda né i percorsi.

## Migliaia di repository e un orologio spostato indietro

La salute del team raggruppa una sola volta per repository le esecuzioni, i workflow rossi, le esecuzioni in corso e gli avvisi, così il costo cresce con la quantità di dati e non con repository per esecuzioni; chiedere un solo repository costruisce solo la sua vista.

Un istante salvato che si trova nel futuro (un computer senza orologio a batteria che parte con una data vecchia, o un orologio corretto a mano) non viene creduto: il punteggio, la pulizia dei dati vecchi e i rapporti programmati sono dovuti subito e scrivono un istante corretto, invece di attendere che il vecchio orologio venga raggiunto.

## La vista della flotta (centinaia di repository)

La scheda **Team** ha una seconda sezione, *Flotta*, per gli account con centinaia di repository. Raggruppa i repository (`fleet.group_by`: ecosistema, etichetta, stato o nessuno), ordina ogni gruppo (`fleet.sort`: rischio, nome, ultima esecuzione o stato) e disegna `fleet.page_size` righe alla volta (50 per impostazione predefinita) con Precedente e Successivo. La pagina riceve tutte le righe una volta da `GET /api/team/fleet?ecosystem=&severity=&q=&label=&group=&sort=&saved=` (sola lettura, al massimo 5.000 righe; `truncated` segnala un taglio) e disegna una sola pagina, quindi la dimensione dell'account non la rallenta.

Una *etichetta* è un modello di nomi di repository: `fleet.labels` accetta righe come `team-*=backend`; il primo modello che corrisponde dà l'etichetta, e raggruppare per etichetta è il modo di distinguere organizzazioni o team in un solo monitor. `fleet.saved_filters` accetta righe come `attention=bad||backend|` (nome, gravità minima, ecosistema, etichetta, testo; ogni parte dopo il nome può essere vuota) e le mostra come filtri già pronti. La classifica sopra la flotta non cambia.
