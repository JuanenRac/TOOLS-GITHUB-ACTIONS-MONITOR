# Sicherheitsrichtlinie

## Eine Schwachstelle melden

Melde Sicherheitsprobleme bitte privat an `electrohobby3d@gmail.com` (oder mit einer privaten Sicherheitsmeldung dieses Repositorys) und eröffne kein öffentliches Issue.
Nützliche Meldungen sind: ein Weg, die lokale Webseite von einem anderen Rechner zu erreichen, ein Weg, den Monitor außerhalb seines eigenen Ordners schreiben zu lassen, ein Weg, ein Token
oder eine private Datei über die Seite oder den Metrik-Endpunkt zu lesen, oder eine Injektion über einen Repository-Namen, einen Workflow-Namen oder eine Logzeile.

## Entwurfspunkte, auf die du dich verlassen kannst
- Die Webseite und der optionale Metrik-Endpunkt lauschen nur auf `127.0.0.1` und weisen Anfragen ab, deren `Host` oder `Origin` nicht lokal ist. Der optionale Netzwerkmodus (standardmäßig aus) fügt ein Zugriffstoken für jede Anfrage, eine Liste akzeptierter Hostnamen und eine dauerhafte Warnung hinzu.
- Standardmäßig speichert oder zeigt der Monitor keine Tokens; er ruft deinen eigenen angemeldeten `gh`-Client auf. Das optionale, vom Monitor gespeicherte Token liegt im sicheren Speicher des Systems und wird nie in eine Einstellung, ein Log oder eine Antwort geschrieben.
- Alles, was auf GitHub schreibt oder ein Programm startet, ist standardmäßig aus, jede Aktion wird einzeln mit einem Einmal-Token bestätigt, und der KI-Assistent kann keine davon starten.
- Die Konfigurationsseite schreibt nur eine feste Liste von Schlüsseln, geprüft, nachdem eine Sicherungskopie gespeichert wurde.
