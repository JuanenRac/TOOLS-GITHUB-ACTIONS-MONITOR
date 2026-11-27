<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | [🇪🇸 Español](TRAFFIC_spa.md) | [🇫🇷 Français](TRAFFIC_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](TRAFFIC_deu.md) | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# Download e traffico

Uno storico, conservato su questo computer, di quante volte si scaricano i file delle release e delle visite e clonazioni dei repository scelti. GitHub conserva visite e clonazioni solo per 14 giorni e non dà uno storico dei download: ciò che non si salva è perso. Edizione Complete; spento all'inizio.

## Attivazione

Accendere `traffic.enabled` (Impostazioni > Download e traffico) e scrivere i repository in `traffic.repos`, uno per riga: un nome (dell'account sorvegliato) o proprietario/nome, al massimo 50. Con l'elenco vuoto non si legge nulla. Il pannello compare nella scheda Repository.

## Cosa si legge e quanto costa

Solo richieste GET, dopo un ciclo: ogni repository scelto al massimo una volta al giorno (UTC), `traffic.repos_per_cycle` per ciclo. Un repository costa da una a cinque richieste della quota di GitHub (release, fino a 300; visite; clonazioni). Se la quota finisce, si ferma e riprova più tardi. `traffic.views_clones` spegne visite e clonazioni. Le installazioni senza rete non leggono nulla. Attende anche se la connessione è persa, durante la prima lettura e quando restano non più del doppio di `min_rate_remaining` richieste.

## Permessi

Visite e clonazioni si ottengono solo con un token con accesso in scrittura (push) al repository. Senza, il pannello lo dice per quel repository; non è un errore e i download si salvano comunque.

## Cosa significano le cifre

I download sono anonimi, includono robot e mirror e non contano gli archivi "Source code" che GitHub aggiunge a una release. I nuovi download confrontano una lettura con la precedente, solo per i file ancora presenti. Un giorno non letto è un vuoto, mai uno zero.

## Esportazione e riservatezza

Il pannello esporta due file CSV: una riga per repository e giorno, e una per file di release e giorno in cui il conteggio è cambiato. `monitor_cli.py traffic export` stampa il primo. I giorni più vecchi di `traffic.keep_days` vengono cancellati. Lo storico resta nella cartella dei dati di questo computer; nulla viene inviato.
