<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | [🇵🇹 Português](REPORT_SCHEDULE_por.md)

# Rapporti pianificati

Solo Complete, spento per impostazione predefinita. Il monitor può scrivere un rapporto dell'account secondo una pianificazione o su richiesta: il punteggio, cosa è cambiato dall'ultimo rapporto, i repository che richiedono una persona e gli avvisi aperti, come pagina HTML e come Markdown. Nasce da ciò che il monitor già possiede, non chiede nulla a GitHub e non invia nulla da nessuna parte: i file restano nella cartella `data/reports/`.

## Come attivarlo

Impostazioni, scheda Sentinella, blocco **Rapporti pianificati**:

| Impostazione | Predefinito | Cosa fa |
|---|---|---|
| `report_schedule.enabled` | spento | scrive un rapporto secondo la pianificazione |
| `report_schedule.cron` | `0 8 * * 1` | cinque campi (minuto, ora, giorno del mese, mese, giorno della settimana) nell'ora locale di questo computer; numeri, elenchi, intervalli e passi, senza nomi; `0 8 * * 1` è ogni lunedì alle 8:00 |
| `report_schedule.formats` | entrambi | `html`, `markdown` o `both` |
| `report_schedule.keep` | 12 | quante serie si conservano; le più vecchie vengono rimosse |
| `report_schedule.top` | 10 | quanti repository e avvisi mostra ogni elenco, i peggiori per primi |

Il primo rapporto aspetta il primo minuto pianificato dopo l'attivazione. Si scrive un rapporto per minuto pianificato, anche se il monitor è rimasto spento per giorni (allora ne scrive uno, non una pila). Un rapporto che fallisce viene annotato nella salute del monitor e il minuto pianificato successivo riprova. Una pianificazione che indica un giorno del mese è ancora dovuta dopo uno stop fino a un mese (se indica un mese, fino a un anno), e l'ora che si ripete quando l'orologio torna indietro in autunno non viene riportata due volte. Un rapporto è tutti i suoi formati o niente: se il secondo formato non si può scrivere, il primo file viene rimosso.

## Cosa contiene un rapporto

Il punteggio dell'account (con lettera e tendenza; mentre calibra o ha pochi dati lo dice e non mostra un numero), cosa è cambiato dall'ultimo rapporto (la differenza in punti, gli avvisi nuovi e quelli scomparsi), i repository della vista di salute che richiedono una persona per primi e gli avvisi aperti, i peggiori per primi. Un avviso silenziato non è aperto. Ogni testo che viene dai dati è sottoposto a escape: la pagina non ha script né indirizzi esterni.

## PDF

Non c'è un PDF proprio: apri la pagina HTML e stampala in PDF dal browser. La pagina ha uno stile di stampa per l'A4.

## Dove vederli e chiederli

- La scheda **Team** ha una sezione Rapporti: l'elenco, un link a ogni file e il pulsante **Scrivi un rapporto ora** (un amministratore, da questo computer).
- `GET /api/report-files` li elenca, `GET /api/report-files/file?name=...` ne apre uno (solo un file che il servizio ha scritto per questo account) e `POST /api/report-files/run` ne scrive uno ora.
- In modalità team chi può vedere l'account può leggerne i rapporti; scriverne uno ora spetta a un amministratore su questo computer. L'edizione Lite non ha nulla di tutto ciò.

## Confronto con il periodo precedente

Con `compare.include_in_report` attivo (disattivato per impostazione predefinita, e solo mentre `compare.enabled` è attivo) il rapporto contiene anche una breve sezione che mette questo periodo a confronto con il precedente, una riga per cifra. Vedi [COMPARE_ita.md](COMPARE_ita.md).
