# Politica di sicurezza

## Segnalare una vulnerabilità

Segnala i problemi di sicurezza in privato a `electrohobby3d@gmail.com` (o con un avviso di sicurezza privato di questo repository) e non aprire una issue pubblica.
Segnalazioni utili sono: un modo di raggiungere la pagina web locale da un'altra macchina, un modo di far scrivere il monitor fuori dalla propria cartella, un modo di leggere un token
o un file privato tramite la pagina o l'endpoint delle metriche, o un'iniezione tramite il nome di un repository, di un workflow o una riga di log.

## Punti di progetto su cui puoi contare
- La pagina web e l'endpoint opzionale delle metriche ascoltano solo su `127.0.0.1` e rifiutano richieste il cui `Host` o `Origin` non sia locale. La modalità rete opzionale (spenta di default) aggiunge un token di accesso per ogni richiesta, un elenco di nomi host accettati e un avviso persistente.
- Per impostazione predefinita il monitor non conserva né mostra token; chiama il tuo client `gh` autenticato. Il token opzionale conservato dal monitor vive nell'archivio sicuro del sistema e non viene mai scritto in un'impostazione, un log o una risposta.
- Tutto ciò che scrive su GitHub o esegue un programma è spento di default, ogni azione è confermata a parte con un token monouso, e l'assistente IA non può avviarne nessuna.
- La pagina di configurazione scrive solo un elenco fisso di chiavi, validate, dopo aver salvato una copia di riserva.
