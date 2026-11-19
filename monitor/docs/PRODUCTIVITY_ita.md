<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PRODUCTIVITY.md) | [🇪🇸 Español](PRODUCTIVITY_spa.md) | [🇫🇷 Français](PRODUCTIVITY_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](PRODUCTIVITY_deu.md) | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | [🇵🇹 Português](PRODUCTIVITY_por.md)

# Cosa fa risparmiare il monitor: una stima e come misurarla

Questa guida spiega le cifre del README. Sono una stima fatta con un modello semplice, non una misura presa sui tuoi repository. Misura le tue prima di fidarti.

## Le cifre

- Circa l'85-95 % del tempo dedicato a sorvegliare la CI e a smistare i guasti.
- Circa il 15-25 % della produttività complessiva di un team, come conseguenza della prima cifra.

## Come è costruita la stima

Tempo risparmiato in una settimana = la somma, sulle attività, di (volte a settimana x minuti ogni volta senza il monitor) x il risparmio di quell'attività. Le attività sono: sorvegliare ogni workflow, decidere cosa è davvero rosso, trovare la causa di un'esecuzione fallita e accorgersi in tempo di un guasto. La stima presuppone che:

1. Ci siano molti repository con più workflow ciascuno, così guardarli a mano significa aprire di continuo molte pagine.
2. Senza il monitor, qualcuno controlla a mano le schede Actions e legge ogni log fallito per trovare la causa. Con il monitor, la pagina e gli avvisi dicono già quale workflow è rosso e perché.
3. I guasti si verifichino ogni settimana. Un team senza guasti non ha nulla da smistare.
4. Il risparmio riguardi solo sorveglianza e smistamento. Correggere un guasto richiede lo stesso tempo con o senza il monitor e non è conteggiato.

Le due cifre concordano solo se sorveglianza e smistamento occupano circa il 16-29 % del tempo di lavoro del team (0,15 / 0,95 a 0,25 / 0,85). Se nel tuo team ne occupano meno, il guadagno complessivo è minore.

## Quando fa risparmiare meno

- Pochi repository o un solo workflow: c'è poco da sorvegliare.
- Oggi nessuno sorveglia la CI a mano, oppure hai già avvisi che nominano la causa.
- Gli avvisi non vengono letti. Anche leggerli richiede tempo, e il risparmio svanisce se vengono ignorati o silenziati senza motivo.

## Come misurarlo nel proprio uso

1. Prima: per una settimana normale, annota ogni volta che guardi la CI a mano (minuti) e ogni esecuzione fallita che smisti (minuti fino a conoscere la causa).
2. Dopo: ripeti le stesse annotazioni per una settimana con il monitor aperto. Il punteggio (tempo di ripristino) e il libro dei guasti (tendenza a 24 ore e 7 giorni) mostrano se i guasti si chiudono prima.
3. Per ogni gruppo, il risparmio è 1 - dopo / prima. Confrontalo con l'85-95 %.
4. Per il guadagno complessivo, dividi le ore risparmiate per il totale delle ore lavorate in quella settimana. Confrontalo con il 15-25 %.

### Esempio con numeri inventati

Qualcuno dedica 20 minuti al giorno a guardare le schede Actions (100 minuti in una settimana di cinque giorni) e smista 4 esecuzioni fallite a settimana da 30 minuti ciascuna (120 minuti): 220 minuti in tutto. Con un risparmio dell'85-95 %, restano liberi tra 187 e 209 minuti. Questi numeri sono inventati per mostrare il calcolo; usa i tuoi.
