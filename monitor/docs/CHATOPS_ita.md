<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | [🇵🇹 Português](CHATOPS_por.md)

# Comandi di chat (Slack e Discord)

Opzionale, **disattivato per impostazione predefinita**. Permette di chiedere al monitor, da un canale Slack o Discord, un breve stato: quanti repository sono in rosso, gli avvisi aperti, la coda e il punteggio. È di **sola lettura**.

## Cosa fa (e cosa non fa mai)

- I comandi sono un elenco chiuso: `help`, `status`, `alerts`, `red`, `queue` e `score`. Tutto il resto riceve «Non conosco questo comando». `chatops.allowed_words` può solo restringere l'elenco.
- Un comando legge ciò che il monitor ha già (l'ultimo ciclo, gli avvisi, il punteggio). Non scrive mai su GitHub, non esegue mai un'azione, non cambia mai un'impostazione e non legge mai un segreto; non esiste un comando per questo e non se ne può aggiungere uno dalla chat.
- La risposta la vede solo chi ha chiesto, non menziona nessuno e non contiene link tranne uno: con `chatops.links` attivo (predefinito), l'indirizzo di un repository (`https://<host>/<proprietario>/<repository>`, verificato) accanto a un nome mostrato così com'è. Ogni testo che arriva da GitHub (il nome di un repository o di un workflow) è ripulito, accorciato e protetto con l'escape per la piattaforma.
- Ogni comando che raggiunge il monitor lascia una riga nel registro delle azioni (`chatops_command`) con gli ID della chat, mai il testo della richiesta.

## Sicurezza

- Disattivato finché `chatops.enabled` e l'interruttore della piattaforma (`chatops.slack.enabled`, `chatops.discord.enabled`) non sono attivi **e** la prova non è nell'ambiente. Le impostazioni conservano solo il NOME della variabile (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), mai il suo valore; il valore non viene mai scritto, mostrato o registrato.
- Slack: ogni richiesta deve portare `X-Slack-Signature: v0=<hmac>`, l'HMAC-SHA256 di `v0:<marca temporale>:<corpo>` fatto con il segreto di firma, e `X-Slack-Request-Timestamp` non più vecchia di `chatops.max_age_seconds` (cinque minuti al massimo). Il confronto richiede lo stesso tempo qualunque sia la firma.
- Discord: ogni richiesta deve portare `X-Signature-Ed25519` e `X-Signature-Timestamp`: una firma Ed25519 della marca temporale seguita dal corpo, verificata con la chiave pubblica della tua app (RFC 8032, libreria standard; nulla è accettato senza la verifica).
- Una firma errata, vecchia o dal futuro riceve `401` e del corpo non si guarda nulla. Una firma già accettata non viene mai accettata di nuovo. Un corpo oltre 16 KB riceve `413`. Un indirizzo può fare 120 richieste al minuto.
- **Le liste sono obbligatorie**: `chatops.allowed_teams`, `chatops.allowed_channels` e `chatops.allowed_users`. Se nessuna è compilata, nessun comando viene eseguito (la sfida della piattaforma riceve comunque risposta, così puoi finire la configurazione). Una lista con voci deve contenere il team, il canale o l'utente della richiesta.
- Limiti al minuto: `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` e `chatops.rate_per_minute`. La risposta deve arrivare in 3 secondi: il monitor risponde dalla memoria e, se fosse più lento, dice di essere occupato.
- Le due rotte (`/api/chatops/slack`, `/api/chatops/discord`) non chiedono il token di accesso della modalità di rete, perché una piattaforma non può inviarlo: la firma è la loro prova, come per il webhook in ingresso. Il monitor ascolta comunque solo su `127.0.0.1` finché non apri la modalità di rete; le piattaforme lo raggiungono solo tramite un indirizzo HTTPS che metti in piedi tu di proposito (un tunnel o un reverse proxy; lo strumento non ne apre mai uno). Pubblica da lì solo `/api/chatops/`.

## I comandi

| Comando | Risposta |
| --- | --- |
| `help` | l'elenco dei comandi |
| `status` | repository in rosso, bloccati, in attesa, in verde e inattivi, e avvisi aperti |
| `alerts` | gli avvisi aperti (livello, codice e repository), fino a `chatops.max_rows` |
| `red` | i workflow in rosso con il tempo trascorso, fino a `chatops.max_rows` |
| `queue` | in esecuzione, in coda, in attesa di approvazione e minuti usati in 24 ore |
| `score` | il punteggio, la sua lettera e la sua variazione |

`chatops.show_repo_names` decide i nomi: `all` (predefinito: tutti i nomi, anche dei repository privati), `public` (un repository privato diventa `private-N` e i suoi workflow non sono nominati) o `none`. **Rischio di `all`:** i nomi di repository e workflow privati arrivano a tutti i canali e utenti che le tue liste consentono. Per questo le liste sono obbligatorie e ogni lista con voci deve corrispondere (team, canale e utente insieme). Scegli `public` o `none` se il canale è più ampio delle persone che possono conoscere quei nomi.

## Slack, passo per passo

1. Apri api.slack.com/apps > Create New App > From scratch. Dagli un nome e scegli il tuo workspace.
2. Slash Commands > Create New Command: comando `/monitor`, **Request URL** `https://<il tuo indirizzo pubblico>/api/chatops/slack`, una breve descrizione. Non serve alcuno scope di bot.
3. Basic Information > App Credentials > **Signing Secret**: copialo e consegnalo al monitor tramite l'ambiente, mai tramite il file: `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` in PowerShell prima di avviare il monitor, `export MONITOR_SLACK_SIGNING_SECRET=...` in una shell, una voce di ambiente o un file di segreto in un servizio o in un container.
4. Installa l'app nel workspace (Install App).
5. Compila le liste: l'ID del tuo team (inizia con `T`), l'ID del canale (apri il canale, i dettagli, l'ID in fondo: `C...`) e il tuo ID di membro (il tuo profilo > Copy member ID: `U...`). Mettili in Impostazioni > Comandi di chat, oppure `"chatops": {"allowed_channels": ["C0123456789"]}` in `actions_monitor.json`.
6. Attiva Comandi di chat e Slack, e riavvia il monitor.

## Discord, passo per passo

1. Apri discord.com/developers/applications > New Application. In General Information copia la **Public Key** (64 caratteri esadecimali) e consegnala al monitor tramite l'ambiente: `$env:MONITOR_DISCORD_PUBLIC_KEY = "<chiave pubblica>"` in PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` in una shell.
2. Compila le liste, attiva Comandi di chat e Discord (Impostazioni > Comandi di chat) e riavvia il monitor. Fallo **prima** del passo successivo: Discord invia una prova firmata quando salvi l'indirizzo e lo rifiuta se il monitor non risponde.
3. General Information > **Interactions Endpoint URL**: `https://<il tuo indirizzo pubblico>/api/chatops/discord`, poi Save.
4. Registra il comando una volta con il tuo strumento (l'API di Discord, `POST /applications/<ID dell'applicazione>/commands`) con questo corpo:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Invita l'app con il solo scope `applications.commands` (OAuth2 > URL Generator); non serve alcun permesso di bot. ID: in Discord attiva la Modalità sviluppatore (Avanzate) e usa Copia ID su server, canale e utente.

## Prova

In un canale consentito scrivi `/monitor help` (Slack) o `/monitor command:status` (Discord). Altre risposte:

| Cosa vedi | Significato |
| --- | --- |
| niente, o «non ha risposto» | l'indirizzo non è raggiungibile, il monitor è spento, oppure ha risposto `401` (segreto o chiave sbagliati, o un orologio sfasato di oltre cinque minuti) |
| «Questo comando non è disponibile qui.» | il team, il canale o l'utente non è nelle liste |
| «Troppi comandi.» | uno dei tre limiti al minuto |
| «Il monitor non ha ancora letto GitHub.» | il primo ciclo non è finito |
