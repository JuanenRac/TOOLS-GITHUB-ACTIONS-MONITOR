<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | [🇫🇷 Français](SKILLS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# Skill per le IA

Il monitor include due skill: brevi guide, in inglese, che dicono a un'IA come lavorare con esso. Sono nella cartella `skills/` del pacchetto, nella pagina (Impostazioni, scheda IA) e un comando le installa.

## Le due skill

- `skills/internal`: per l'IA integrata nel monitor, locale (Ollama, un server llama.cpp, LM Studio) o esterna (l'API di un fornitore). Dice cos'è il monitor e cosa vede, cosa può leggere, cosa non deve mai fare, come diagnosticare un rosso, quando tacere e come usare e proporre lezioni. Il suo nucleo (`SKILL.md`) viene aggiunto a ogni prompt di quell'IA, tagliato a `ai.skill_max_chars`, quando `ai.skill` è attivo.
- `skills/external`: per le IA che parlano con il monitor dall'esterno, in ogni direzione: leggere (`/api/ai/*`, i file di `ai/`), essere avvisate (lo stream o il riepilogo ogni pochi minuti), scrivere (conferma di lettura, lezioni, fallimenti, preferenze di notifica) con i permessi dovuti, il collegamento tra monitor e sessione, il riepilogo prima del push e l'intero ciclo di autoapprendimento. Copre un'IA con riga di comando, un'IA con solo HTTP o file, un'IA con MCP e un'IA sullo stream.

## Cosa contiene

Ogni skill è un breve `SKILL.md` (il nucleo) e una cartella `references/` letta solo quando serve, così un modello con poco contesto può prendere solo il nucleo: scenari passo passo (un rosso reale, un rosso passeggero, quota bassa, un monitor degradato, un fallimento ripetuto, una nuova lezione, senza rete, più schermi), il ciclo di autoapprendimento, i fornitori e i loro limiti, la sicurezza (iniezione di istruzioni dai registri, segreti, permessi minimi, audit di ciò che scrive un'IA) e i riferimenti generati dal codice.

## Nulla è lasciato fuori

I riferimenti (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) e `skills/COVERAGE.md` sono GENERATI dal codice con `python tools/make_skill_refs.py`: ogni endpoint con il ruolo minimo che può chiamarlo, ogni comando e opzione, ogni impostazione con il suo valore predefinito, ogni file scritto dal monitor, ogni ruolo e ogni scheda. Un test legge le stesse liste dal codice e fallisce se qualcosa non è nominato nelle skill, quindi un endpoint, comando, impostazione o file nuovo non può apparire senza essere descritto alle IA (e il generatore si ferma finché non è scritta la sua nota).

## Installare

Copia la skill nella cartella da cui il tuo strumento di IA legge le sue skill:

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Sicurezza dell'installatore

Scrive `github-actions-monitor-internal` o `github-actions-monitor-external` dentro la cartella indicata e nient'altro. Non sovrascrive mai un file diverso da quello del pacchetto (mantiene il tuo e dice quale) e rifiuta l'unità D: e i percorsi di rete. Una seconda esecuzione non cambia nulla.

## Nella pagina e via HTTP

In Impostazioni, scheda IA, il blocco **Skill per le IA** ha Copia (il nucleo della skill) e Scarica (la skill intera con i riferimenti in un file) per ciascuna. `GET /api/skills` le elenca e `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` restituisce il testo; è in sola lettura.

## Impostazioni

`ai.skill` (attivo) e `ai.skill_max_chars` (3000; 1500 per un piccolo modello locale). Registrare fallimenti dall'esterno è `POST /api/ai/failures` e richiede `lessons.allow_write` e un amministratore, come scrivere una lezione.

## Pubblicazione in un registro di skill

`python tools/prepare_skill_bundle.py --out DIR` prepara la cartella della skill esterna (SKILL.md, riferimenti, `bundle.json` con la versione del monitor e la licenza, `SHA256SUMS`); le stesse fonti danno gli stessi byte. Non pubblica nulla: il caricamento su ClawHub si fa a mano, con l'account del responsabile, dopo aver letto le condizioni.

## Assistenti

Si dice provato solo ciò che è stato davvero provato.

| Assistente o via | Riga di comando | HTTP e file | MCP |
|---|---|---|---|
| Un assistente di codice in terminale | provato | provato | compatibile per protocollo, non provato |
| Altri assistenti | compatibile per protocollo, non provato | compatibile per protocollo, non provato | compatibile per protocollo, non provato |
